"""De facturas extraídas a datos del formulario (§5.3, §5.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from motor import provisorios
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
    costo_distribuidora: float | None = None  # §5.4: importe básico / kWh
    costo_energia_activa: float | None = None  # solo energía activa / kWh (informativo)
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

    # §5.4: promedio ponderado = Σ importes / Σ kWh de las facturas con ambos datos.
    # TODO(A6, §14.2): decidir si se precarga importe básico/kWh (actual) o solo energía activa/kWh.
    for atributo, destino in (("importe_basico_energia", "costo_distribuidora"), ("importe_energia_activa", "costo_energia_activa")):
        pares = [(getattr(f, atributo).valor, _kwh_facturados(f)) for f in facturas]
        pares = [(i, k) for i, k in pares if i and k]
        if pares:
            setattr(s, destino, sum(i for i, _ in pares) / sum(k for _, k in pares))

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
