"""De facturas extraídas a datos del formulario (§5.3, §5.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from motor import provisorios
from motor.calculo import kvar_capacitores
from motor.consumos import LecturaMensual, consolidar
from motor.modelos import ConsumoMensual, OrigenConsumo

from .esquema import FacturaExtraida, Jurisdiccion, MesHistorial

UMBRAL_CONFIANZA = 0.7


@dataclass
class Sugerencias:
    """Valores sugeridos para precargar el formulario; todos editables."""

    cliente: str | None = None
    cuit: str | None = None
    provincia: str | None = None
    distribuidora: str | None = None
    tarifa: str | None = None
    potencia_contratada_kw: float | None = None
    potencias_contratadas: list[float | None] = field(default_factory=list)  # pico, fuera de pico (A4)
    # §5.4 (A6): precio del kWh en resto, NO el monómico (importe básico / kWh), que incluye
    # cargos fijos y de potencia que la solar no reduce. Si la factura no trae el precio unitario
    # se cae a energía activa / kWh; `costo_distribuidora_origen` dice cuál se usó.
    costo_distribuidora: float | None = None
    costo_distribuidora_origen: str | None = None  # "resto" | "energia_activa"
    costo_energia_activa: float | None = None  # solo energía activa / kWh (informativo)
    costo_monomico: float | None = None  # importe básico / kWh (informativo, no se usa)
    cargo_factor_potencia: bool = False  # la factura cobra por factor de potencia → banco de capacitores
    kvar_sugeridos: float | None = None  # kVAr para llegar a cos φ 0,95 (Bco Capac)
    tasas_mun_prov: float | None = None
    energia_reactiva_kvarh: float | None = None
    energia_activa_kwh: float | None = None
    consumos: list[ConsumoMensual | None] = field(default_factory=list)
    campos_dudosos: list[str] = field(default_factory=list)
    meses_sin_franjas: list[int] = field(default_factory=list)


def _lectura(anio: int, mes: int, pico, resto, valle, total, origen: OrigenConsumo) -> LecturaMensual | None:
    if pico is None and resto is None and valle is None:
        if total is None:
            return None
        # Tarifa sin franjas: el total va a "resto" y se marca para revisar.
        return LecturaMensual(anio, mes, 0.0, total, 0.0, origen)
    return LecturaMensual(anio, mes, valle or 0.0, resto or 0.0, pico or 0.0, origen)


def lecturas(factura: FacturaExtraida) -> list[LecturaMensual]:
    resultado = []
    for h in factura.historial:
        l = _lectura(h.anio, h.mes, h.kwh_pico, h.kwh_resto, h.kwh_valle, h.kwh_total, OrigenConsumo.HISTORIAL)
        if l:
            resultado.append(l)
    anio, mes = factura.periodo_anio.valor, factura.periodo_mes.valor
    if anio and mes:
        l = _lectura(
            int(anio), int(mes), factura.kwh_pico.valor, factura.kwh_resto.valor,
            factura.kwh_valle.valor, factura.kwh_total.valor, OrigenConsumo.FACTURA,
        )
        if l:
            resultado.append(l)
    return resultado


def _sin_franjas(h: MesHistorial) -> bool:
    return h.kwh_pico is None and h.kwh_resto is None and h.kwh_valle is None and h.kwh_total is not None


def _kwh_facturados(f: FacturaExtraida) -> float | None:
    if f.kwh_total.valor:
        return f.kwh_total.valor
    partes = [f.kwh_pico.valor, f.kwh_resto.valor, f.kwh_valle.valor]
    return sum(p for p in partes if p) or None


def tasas_mun_prov(factura: FacturaExtraida) -> float | None:
    """Suma de alícuotas provinciales y municipales sobre el subtotal, como fracción."""
    alicuotas = [
        i.porcentaje
        for i in factura.impuestos
        if i.jurisdiccion in (Jurisdiccion.PROVINCIAL, Jurisdiccion.MUNICIPAL) and i.porcentaje is not None
    ]
    return sum(alicuotas) / 100 if alicuotas else None


def _mas_frecuente(valores: list[str | None]) -> str | None:
    presentes = [v for v in valores if v]
    return max(set(presentes), key=presentes.count) if presentes else None


def _promedio_ponderado(pares: list[tuple[float | None, float | None]]) -> float | None:
    """Σ importes / Σ kWh (o Σ precio·kWh / Σ kWh) de los pares con ambos datos."""
    validos = [(i, k) for i, k in pares if i and k]
    return sum(i for i, _ in validos) / sum(k for _, k in validos) if validos else None


def _costo_distribuidora(facturas: list[FacturaExtraida]) -> tuple[float | None, str | None]:
    """Precio del kWh en resto; si ninguna factura lo trae, energía activa / kWh."""
    pares = []
    for f in facturas:
        peso = f.kwh_resto.valor or _kwh_facturados(f)
        if f.precio_kwh_resto.valor and peso:
            pares.append((f.precio_kwh_resto.valor * peso, peso))
    if pares:
        return _promedio_ponderado(pares), "resto"
    activa = _promedio_ponderado([(f.importe_energia_activa.valor, _kwh_facturados(f)) for f in facturas])
    return (activa, "energia_activa") if activa else (None, None)


def _kvar_sugeridos(s: "Sugerencias") -> float | None:
    if not s.cargo_factor_potencia or not s.potencia_contratada_kw:
        return None
    if not s.energia_activa_kwh or s.energia_reactiva_kvarh is None:
        return None
    return round(kvar_capacitores(s.potencia_contratada_kw, s.energia_activa_kwh, s.energia_reactiva_kvarh), 1)


def sugerir(facturas: list[FacturaExtraida]) -> Sugerencias:
    s = Sugerencias()
    if not facturas:
        return s
    reciente = max(facturas, key=lambda f: (f.periodo_anio.valor or 0, f.periodo_mes.valor or 0))

    s.cliente = _mas_frecuente([f.cliente_razon_social.valor for f in facturas])
    s.cuit = _mas_frecuente([f.cliente_cuit.valor for f in facturas])
    s.provincia = _mas_frecuente([f.provincia.valor for f in facturas])
    s.distribuidora = _mas_frecuente([f.distribuidora.valor for f in facturas])
    s.tarifa = reciente.tarifa.valor
    s.potencias_contratadas = [reciente.potencia_contratada_pico_kw.valor, reciente.potencia_contratada_fuera_pico_kw.valor]
    s.potencia_contratada_kw = provisorios.potencia_contratada_sugerida(*s.potencias_contratadas)
    s.tasas_mun_prov = tasas_mun_prov(reciente)
    s.energia_reactiva_kvarh = reciente.energia_reactiva_kvarh.valor
    s.energia_activa_kwh = _kwh_facturados(reciente)

    # §5.4: promedio ponderado por kWh de las facturas que traen el dato.
    s.costo_distribuidora, s.costo_distribuidora_origen = _costo_distribuidora(facturas)
    s.costo_energia_activa = _promedio_ponderado([(f.importe_energia_activa.valor, _kwh_facturados(f)) for f in facturas])
    s.costo_monomico = _promedio_ponderado([(f.importe_basico_energia.valor, _kwh_facturados(f)) for f in facturas])

    s.cargo_factor_potencia = any(f.cargo_factor_potencia for f in facturas)
    s.kvar_sugeridos = _kvar_sugeridos(s)

    todas = [l for f in facturas for l in lecturas(f)]
    s.consumos = consolidar(todas)
    s.meses_sin_franjas = sorted({
        h.mes for f in facturas for h in f.historial if _sin_franjas(h)
    } | {
        int(f.periodo_mes.valor) for f in facturas
        if f.periodo_mes.valor and f.kwh_total.valor and f.kwh_pico.valor is None
        and f.kwh_resto.valor is None and f.kwh_valle.valor is None
    })

    for i, f in enumerate(facturas):
        for nombre, valor in f:
            confianza = getattr(valor, "confianza", None)
            if confianza is not None and getattr(valor, "valor", None) is not None and confianza < UMBRAL_CONFIANZA:
                s.campos_dudosos.append(f"factura {i + 1}: {nombre}")
        for h in f.historial:
            if h.confianza < UMBRAL_CONFIANZA:
                s.campos_dudosos.append(f"factura {i + 1}: historial {h.mes:02d}/{h.anio}")
    return s
