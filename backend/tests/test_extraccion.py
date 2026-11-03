"""Extracción de facturas: derivados (§5.3–5.4) y manejo de errores, sin llamar a la API.

El test `test_extraccion_real_*` llama a Claude con las facturas de ejemplo y solo
corre si hay credenciales (ANTHROPIC_API_KEY).
"""

import math
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from extraccion.derivados import sugerir, tasas_mun_prov
from extraccion.esquema import FacturaExtraida, Impuesto, Jurisdiccion, MesHistorial, Numero, ProvinciaCampo, Texto, TipoDocumento
from extraccion.extractor import ExtraccionFallida, ExtraccionNoConfigurada, extraer_factura
from motor.calculo import kvar_capacitores
from motor.modelos import OrigenConsumo

EJEMPLOS = Path(__file__).resolve().parents[2] / "ejemplos-facturas"


def T(v, c=1.0):
    return Texto(valor=v, confianza=c)


def N(v, c=1.0):
    return Numero(valor=v, confianza=c)


def factura_epe() -> FacturaExtraida:
    """Datos de ejemplos-facturas/07-2026.pdf (EPE Santa Fe, julio 2026)."""
    historial = [
        (2, 68, 174, 4735, 21038, 2192), (3, 67, 182, 5081, 22435, 2341), (4, 81, 125, 3002, 13356, 2099),
        (5, 124, 165, 2526, 12889, 1771), (6, 56, 153, 2789, 15070, 1795), (7, 52, 177, 2746, 15151, 1850),
    ]
    return FacturaExtraida(
        tipo_documento=TipoDocumento.DISTRIBUIDORA,
        distribuidora=T("EPE Santa Fe"),
        cliente_razon_social=T("SCIMACA S R L"),
        cliente_cuit=T("30-58921142-8"),
        domicilio_suministro=T("Callao 6002, Rosario"),
        provincia=ProvinciaCampo(valor="Santa Fe", confianza=1),
        tarifa=T("2 B1"),
        periodo_anio=N(2026),
        periodo_mes=N(7),
        dias_facturados=N(31),
        potencia_contratada_pico_kw=N(80),
        potencia_contratada_fuera_pico_kw=N(120),
        kwh_pico=N(2745.6),
        kwh_resto=N(15150.6),
        kwh_valle=N(1850.4),
        kwh_total=N(19746.6),
        kw_registrados_pico=N(51.84),
        kw_registrados_fuera_pico=N(176.64),
        importe_basico_energia=N(8565172.32),
        importe_energia_activa=N(2445734.67),
        precio_kwh_resto=N(130.5),
        impuestos=[
            Impuesto(nombre="Ley Nº 7797", jurisdiccion=Jurisdiccion.PROVINCIAL, porcentaje=6.0, base="S/Subtotal", importe=513910.34),
            Impuesto(nombre="Ordenanza Municipal Nº 1592/62", jurisdiccion=Jurisdiccion.MUNICIPAL, porcentaje=0.6, base="S/Subtotal", importe=51391.03),
            Impuesto(nombre="Ordenanza Municipal Nº 1618/62", jurisdiccion=Jurisdiccion.MUNICIPAL, porcentaje=1.8, base="S/Subtotal", importe=154173.10),
            Impuesto(nombre="Ley 13.414 (FER)", jurisdiccion=Jurisdiccion.PROVINCIAL, porcentaje=1.5, base="S/Subtotal", importe=128477.58),
            Impuesto(nombre="Ley Nº 12692 Energias Renovables", jurisdiccion=Jurisdiccion.PROVINCIAL, porcentaje=None, base="$/Mes", importe=230.81),
            Impuesto(nombre="IVA Responsable Inscripto", jurisdiccion=Jurisdiccion.IVA, porcentaje=27.0, base="S/Subtotal + CAP", importe=2331898.52),
        ],
        importe_total=N(12960728.37),
        energia_reactiva_kvarh=N(3619.8),
        cargo_factor_potencia=False,
        historial=[
            MesHistorial(anio=2026, mes=m, kwh_pico=p, kwh_resto=r, kwh_valle=v, kwh_total=None,
                         kw_pico=kp, kw_fuera_pico=kf, leido_de_grafico=False, confianza=1)
            for m, kp, kf, p, r, v in historial
        ],
        notas="",
    )


def test_tasas_mun_prov_suma_provinciales_y_municipales():
    assert tasas_mun_prov(factura_epe()) == pytest.approx(0.099)  # = Hoja1!I11 de PLECOR


def test_sugerencias_epe():
    s = sugerir([factura_epe()])
    assert s.cliente == "SCIMACA S R L" and s.provincia == "Santa Fe"
    assert s.potencia_contratada_kw == 120  # A4: la mayor
    # A6: el costo sugerido es el precio del kWh en resto, no el monómico (importe básico / kWh).
    assert s.costo_distribuidora == pytest.approx(130.5) and s.costo_distribuidora_origen == "resto"
    assert s.costo_monomico == pytest.approx(8565172.32 / 19746.6)
    assert s.costo_energia_activa == pytest.approx(2445734.67 / 19746.6)
    assert s.energia_reactiva_kvarh == 3619.8
    assert not s.cargo_factor_potencia and s.kvar_sugeridos is None
    assert not s.campos_dudosos


def test_costo_distribuidora_pondera_por_kwh_resto():
    otra = factura_epe().model_copy(update={"precio_kwh_resto": N(100.0), "kwh_resto": N(5000.0)})
    s = sugerir([factura_epe(), otra])
    esperado = (130.5 * 15150.6 + 100.0 * 5000.0) / (15150.6 + 5000.0)
    assert s.costo_distribuidora == pytest.approx(esperado)


def test_sin_precio_en_resto_se_usa_energia_activa_y_nunca_el_monomico():
    f = factura_epe().model_copy(update={"precio_kwh_resto": N(None)})
    s = sugerir([f])
    assert s.costo_distribuidora == pytest.approx(2445734.67 / 19746.6)
    assert s.costo_distribuidora_origen == "energia_activa"
    assert s.costo_distribuidora < s.costo_monomico / 3


def test_cargo_por_factor_de_potencia_sugiere_banco_de_capacitores():
    f = factura_epe().model_copy(update={"cargo_factor_potencia": True})
    s = sugerir([f])
    assert s.cargo_factor_potencia
    # [Bco Capac!C18]: Qc = P · (tan φ − tan φ_obj), P = 120 kW (la mayor), cos φ objetivo 0,95
    tan_objetivo = math.tan(math.acos(0.95))
    esperado = 120 * (3619.8 / 19746.6 - tan_objetivo)
    assert s.kvar_sugeridos == pytest.approx(max(esperado, 0), abs=0.05)


def test_kvar_replica_la_hoja_bco_capac():
    # Hoja "Bco Capac": activa 30900, reactiva 12810, 75 kW → Qc = 75·(tan φ − tan φ_obj)
    assert kvar_capacitores(75, 30900, 12810) == pytest.approx(75 * (12810 / 30900 - math.tan(math.acos(0.95))))
    assert kvar_capacitores(75, 30900, 0) == 0  # sin reactiva no hay nada que compensar
    assert kvar_capacitores(0, 30900, 12810) == 0


def test_consumos_epe_completa_con_espejo():
    c = sugerir([factura_epe()]).consumos
    julio = c[6]
    assert julio.origen == OrigenConsumo.FACTURA and julio.resto == 15150.6  # prevalece la factura
    assert c[2].origen == OrigenConsumo.HISTORIAL and c[2].resto == 22435
    assert c[9].origen == OrigenConsumo.ESTIMADO and c[9].resto == 22435  # OCT ← MAR
    # Historial FEB–JUL: el espejo cubre AGO–NOV; ENE y DIC (espejo entre sí) faltan.
    assert c[0] is None and c[11] is None
    assert sum(m is not None for m in c) == 10


def test_tarifa_sin_franjas_va_a_resto_y_se_marca():
    f = factura_epe().model_copy(update={
        "kwh_pico": N(None), "kwh_resto": N(None), "kwh_valle": N(None), "kwh_total": N(7459),
        "historial": [MesHistorial(anio=2025, mes=9, kwh_pico=None, kwh_resto=None, kwh_valle=None, kwh_total=4100,
                                   kw_pico=None, kw_fuera_pico=None, leido_de_grafico=True, confianza=0.4)],
    })
    s = sugerir([f])
    assert s.consumos[6].resto == 7459 and s.consumos[6].valle == 0
    assert s.meses_sin_franjas == [7, 9]
    assert "factura 1: historial 09/2025" in s.campos_dudosos


def _cliente_falso(respuesta=None, error=None):
    def parse(**kwargs):
        parse.kwargs = kwargs
        if error:
            raise error
        return respuesta

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse))), parse


@pytest.fixture
def con_claude(monkeypatch):
    monkeypatch.setenv("EXTRACCION_PROVEEDOR", "claude")


def test_claude_envia_pdf_e_imagen(con_claude):
    cliente, parse = _cliente_falso(SimpleNamespace(stop_reason="end_turn", parsed_output=factura_epe()))
    assert extraer_factura(b"%PDF-1.4", "application/pdf", cliente).cliente_razon_social.valor == "SCIMACA S R L"
    bloque = parse.kwargs["messages"][0]["content"][0]
    assert bloque["type"] == "document" and bloque["source"]["media_type"] == "application/pdf"
    assert parse.kwargs["output_format"] is FacturaExtraida
    assert parse.kwargs["model"] == "claude-sonnet-5-5"
    extraer_factura(b"\xff\xd8", "image/jpeg", cliente)
    assert parse.kwargs["messages"][0]["content"][0]["type"] == "image"


def test_tipo_no_soportado():
    with pytest.raises(ValueError):
        extraer_factura(b"x", "application/zip", _cliente_falso()[0])


def test_claude_sin_credenciales(con_claude):
    error = TypeError("Could not resolve authentication method. Expected one of api_key...")
    with pytest.raises(ExtraccionNoConfigurada):
        extraer_factura(b"%PDF", "application/pdf", _cliente_falso(error=error)[0])


def test_claude_rechazo_o_respuesta_incompleta(con_claude):
    for r in (SimpleNamespace(stop_reason="refusal", parsed_output=None),
              SimpleNamespace(stop_reason="max_tokens", parsed_output=None)):
        with pytest.raises(ExtraccionFallida):
            extraer_factura(b"%PDF", "application/pdf", _cliente_falso(r)[0])


def test_proveedor_desconocido(monkeypatch):
    monkeypatch.setenv("EXTRACCION_PROVEEDOR", "otro")
    with pytest.raises(ExtraccionNoConfigurada):
        extraer_factura(b"%PDF", "application/pdf", _cliente_falso()[0])


# ------------------------------------------------------------------ Gemini (proveedor por defecto)


def _gemini_falso(texto=None, error=None, fin="STOP"):
    def generate_content(**kwargs):
        generate_content.kwargs = kwargs
        if error:
            raise error
        return SimpleNamespace(text=texto, candidates=[SimpleNamespace(finish_reason=fin)])

    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)), generate_content


@pytest.fixture
def con_gemini(monkeypatch):
    monkeypatch.delenv("EXTRACCION_PROVEEDOR", raising=False)
    monkeypatch.delenv("EXTRACCION_MODELO", raising=False)


def test_gemini_es_el_proveedor_por_defecto_y_valida_el_esquema(con_gemini):
    cliente, llamada = _gemini_falso(factura_epe().model_dump_json())
    f = extraer_factura(b"%PDF-1.4", "application/pdf", cliente)
    assert f.cliente_razon_social.valor == "SCIMACA S R L"
    assert llamada.kwargs["model"] == "gemini-3.5-flash"
    config = llamada.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == FacturaExtraida.model_json_schema()
    documento = llamada.kwargs["contents"][0]
    assert documento.inline_data.mime_type == "application/pdf"


def test_gemini_sin_key(con_gemini, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ExtraccionNoConfigurada, match="GEMINI_API_KEY"):
        extraer_factura(b"%PDF", "application/pdf")


def test_gemini_errores(con_gemini):
    from google.genai import errors

    cuota = errors.ClientError(429, {"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
    with pytest.raises(ExtraccionFallida, match="por minuto"):
        extraer_factura(b"%PDF", "application/pdf", _gemini_falso(error=cuota)[0])
    key = errors.ClientError(400, {"error": {"code": 400, "message": "API key not valid", "status": "INVALID_ARGUMENT",
                                             "details": [{"reason": "API_KEY_INVALID"}]}})
    with pytest.raises(ExtraccionNoConfigurada):
        extraer_factura(b"%PDF", "application/pdf", _gemini_falso(error=key)[0])
    with pytest.raises(ExtraccionFallida, match="incompleta"):
        extraer_factura(b"%PDF", "application/pdf", _gemini_falso("{", fin="MAX_TOKENS")[0])
    with pytest.raises(ExtraccionFallida, match="formato"):
        extraer_factura(b"%PDF", "application/pdf", _gemini_falso('{"tipo_documento": "x"}')[0])


# ------------------------------------------------------------------ con la API real (solo si hay key)


def _hay_credenciales() -> bool:
    # Optativos: consumen el cupo del proveedor (en Gemini gratis es chico). Correr con PRUEBAS_API_REAL=1.
    if os.environ.get("PRUEBAS_API_REAL") != "1":
        return False
    if os.environ.get("EXTRACCION_PROVEEDOR", "gemini").lower() == "claude":
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


hay_credenciales = pytest.mark.skipif(not _hay_credenciales(), reason="Pruebas con la API real: PRUEBAS_API_REAL=1 y API key")


@hay_credenciales
def test_extraccion_real_epe():
    f = extraer_factura((EJEMPLOS / "07-2026.pdf").read_bytes(), "application/pdf")
    assert f.provincia.valor == "Santa Fe"
    assert f.kwh_resto.valor == pytest.approx(15150.6, rel=1e-3)
    assert tasas_mun_prov(f) == pytest.approx(0.099)
    assert len(f.historial) >= 6


@hay_credenciales
def test_extraccion_real_edenor_escaneada():
    f = extraer_factura((EJEMPLOS / "edenor Santamaria vto 24-08-26.pdf").read_bytes(), "application/pdf")
    assert f.tipo_documento == TipoDocumento.DISTRIBUIDORA
    assert f.kwh_total.valor or f.kwh_resto.valor


def test_gemini_pasa_al_modelo_de_respaldo_si_esta_sobrecargado(con_gemini):
    from google.genai import errors

    usados = []

    def generate_content(**kwargs):
        usados.append(kwargs["model"])
        if kwargs["model"] == "gemini-3.5-flash":
            raise errors.ServerError(503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}})
        return SimpleNamespace(text=factura_epe().model_dump_json(), candidates=[SimpleNamespace(finish_reason="STOP")])

    cliente = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    assert extraer_factura(b"%PDF", "application/pdf", cliente).cliente_razon_social.valor == "SCIMACA S R L"
    assert usados == ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

    def siempre_503(**kwargs):
        raise errors.ServerError(503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}})

    with pytest.raises(ExtraccionFallida, match="todos los modelos"):
        extraer_factura(b"%PDF", "application/pdf", SimpleNamespace(models=SimpleNamespace(generate_content=siempre_503)))


def test_gemini_cupo_diario_agotado_pasa_al_respaldo(con_gemini):
    from google.genai import errors

    usados = []
    diario = {"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED",
                        "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}

    def generate_content(**kwargs):
        usados.append(kwargs["model"])
        raise errors.ClientError(429, diario)

    with pytest.raises(ExtraccionFallida, match="cupo diario"):
        extraer_factura(b"%PDF", "application/pdf", SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    assert usados == ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
