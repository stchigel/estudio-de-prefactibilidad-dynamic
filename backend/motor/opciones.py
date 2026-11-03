"""Búsqueda automática de opciones de dimensionamiento (§7)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .calculo import _economia, _energia, _inversion, balance_mensual, calcular, superficie_m2
from .catalogo import Catalogo, Parametros, catalogo_vigente, parametros_vigentes
from .modelos import Entradas, Kit, Resultado


@dataclass
class ConfigBusqueda:
    # Con inhibición = SI se descartan opciones que desperdician más que esta fracción de la generación.
    max_desperdicio_inhibido: float = 0.15
    # Diferencias de ROI menores a esta se consideran empate y gana la mayor cobertura.
    tolerancia_roi_anios: float = 0.2
    max_opciones: int = 5
    # Salto mínimo de cobertura entre opciones presentadas (escalonado). Si con ese salto no se
    # llega a `max_opciones` (rango de cobertura angosto, p. ej. por la potencia contratada),
    # se achica a la mitad hasta `salto_cobertura_minimo`.
    salto_cobertura: float = 0.10
    salto_cobertura_minimo: float = 0.02
    # Tope de cobertura cuando no hay potencia contratada informada.
    cobertura_max_sin_potencia: float = 1.0


@dataclass
class Candidata:
    kit1: Kit
    kit2: Kit | None
    kwp: float
    cobertura: float
    desperdicio: float  # fracción de la generación desperdiciada
    superficie_m2: float
    inversion_usd: float
    ahorro_usd: float
    roi_anios: float | None
    motivo_descarte: str | None = None


@dataclass
class Opcion:
    kit1: Kit
    kit2: Kit | None
    recomendada: bool
    resultado: Resultado


@dataclass
class ResultadoBusqueda:
    opciones: list[Opcion]
    limitado_por_potencia: bool
    evaluadas: int
    validas: int
    descartes: dict[str, int] = field(default_factory=dict)


def combinaciones(e: Entradas, cat: Catalogo, kwp_max: float) -> list[tuple[Kit, Kit | None]]:
    """kit_a × n_a (+ kit_b × n_b) con kWp total ≤ kwp_max.

    El kit 1 es siempre el de mayor tamaño: por A1 el adicional por inversor del
    kit 2 se toma del kit 1, así que el orden afecta el precio.
    """
    kits = sorted(cat.kits, key=lambda k: k.kwp, reverse=True)
    distancia = e.kit1.distancia_tgbt_m
    combos: list[tuple[Kit, Kit | None]] = []
    for i, a in enumerate(kits):
        for n_a in range(1, int(kwp_max // a.kwp) + 1):
            combos.append((Kit(a.kwp, n_a, distancia), None))
            resto = kwp_max - n_a * a.kwp
            for b in kits[i + 1 :]:
                for n_b in range(1, int(resto // b.kwp) + 1):
                    combos.append((Kit(a.kwp, n_a, distancia), Kit(b.kwp, n_b, distancia)))
    return combos


def _evaluar(e: Entradas, cat: Catalogo, par: Parametros) -> Candidata:
    """Camino rápido: energía, inversión y ROI (sin VAN/TIR/PPA)."""
    kwp = e.kwp_total
    energia = _energia(e, balance_mensual(e, cat, par, kwp))
    economia = _economia(e, energia)
    inversion = _inversion(e, cat).total_usd
    ahorro = economia.ahorro_anual_usd
    gen = energia.generacion_anual_kwh
    return Candidata(
        kit1=e.kit1,
        kit2=e.kit2,
        kwp=kwp,
        cobertura=energia.cobertura,
        desperdicio=energia.desperdiciada_kwh / gen if gen else 0.0,
        superficie_m2=superficie_m2(kwp, e.instalacion, par),
        inversion_usd=inversion,
        ahorro_usd=ahorro,
        roi_anios=inversion / ahorro if ahorro > 0 else None,
    )


def _ordenar(candidatas: list[Candidata], tolerancia: float) -> list[Candidata]:
    """Menor ROI primero. La primera (recomendada) es la de mayor cobertura entre
    las que están a menos de `tolerancia` años del mejor ROI."""
    if not candidatas:
        return []
    por_roi = sorted(candidatas, key=lambda c: (c.roi_anios, -c.cobertura))
    mejor = por_roi[0].roi_anios
    empatadas = [c for c in por_roi if c.roi_anios - mejor < tolerancia]
    recomendada = max(empatadas, key=lambda c: (c.cobertura, -c.roi_anios))
    return [recomendada] + [c for c in por_roi if c is not recomendada]


def _motivo_descarte(c: Candidata, e: Entradas, cfg: ConfigBusqueda, controlar_potencia: bool) -> str | None:
    if c.roi_anios is None:
        return "sin_ahorro"
    if e.m2_disponibles is not None and c.superficie_m2 > e.m2_disponibles:
        return "superficie"
    if controlar_potencia and e.potencia_contratada_kw > 0 and c.kwp > e.potencia_contratada_kw:
        return "potencia"
    if e.inhibicion_inyeccion and c.desperdicio > cfg.max_desperdicio_inhibido:
        return "desperdicio"
    if e.potencia_contratada_kw <= 0 and c.cobertura > cfg.cobertura_max_sin_potencia:
        return "cobertura"
    return None


def _escalonar(ranking: list[Candidata], cfg: ConfigBusqueda) -> list[Candidata]:
    """La mejor por ROI + las siguientes mejores separadas por al menos un salto de cobertura."""
    salto = cfg.salto_cobertura
    while True:
        elegidas: list[Candidata] = []
        for c in ranking:
            if all(abs(c.cobertura - x.cobertura) >= salto for x in elegidas):
                elegidas.append(c)
            if len(elegidas) == cfg.max_opciones:
                return elegidas
        if salto / 2 < cfg.salto_cobertura_minimo:
            return elegidas
        salto /= 2


def buscar_opciones(
    e: Entradas,
    config: ConfigBusqueda | None = None,
    catalogo: Catalogo | None = None,
    parametros: Parametros | None = None,
) -> ResultadoBusqueda:
    cfg = config or ConfigBusqueda()
    cat = catalogo or catalogo_vigente()
    par = parametros or parametros_vigentes()

    # Tope de búsqueda: algo por encima de la potencia contratada para poder detectar
    # si es la restricción activa; sin potencia informada, por cobertura.
    if e.potencia_contratada_kw > 0:
        kwp_max = e.potencia_contratada_kw * 1.5
    else:
        cobertura_por_kwp = _evaluar(replace(e, kit1=Kit(1.0, 1), kit2=None), _catalogo_unitario(cat), par).cobertura
        if cobertura_por_kwp <= 0:
            return ResultadoBusqueda([], False, 0, 0, {"sin_consumo_o_generacion": 1})
        kwp_max = cfg.cobertura_max_sin_potencia / cobertura_por_kwp * 1.05
    if e.m2_disponibles is not None:
        kwp_max = min(kwp_max, e.m2_disponibles * par.factor_kwp_por_modulo / par.factores_superficie[e.instalacion])

    candidatas = [_evaluar(replace(e, kit1=k1, kit2=k2), cat, par) for k1, k2 in combinaciones(e, cat, kwp_max)]

    descartes: dict[str, int] = {}
    validas, sin_control_potencia = [], []
    for c in candidatas:
        motivo = _motivo_descarte(c, e, cfg, controlar_potencia=True)
        if motivo is None:
            validas.append(c)
        else:
            descartes[motivo] = descartes.get(motivo, 0) + 1
        if _motivo_descarte(c, e, cfg, controlar_potencia=False) is None:
            sin_control_potencia.append(c)

    validas = _ordenar(validas, cfg.tolerancia_roi_anios)
    sin_control_potencia = _ordenar(sin_control_potencia, cfg.tolerancia_roi_anios)
    limitado = bool(validas and sin_control_potencia) and sin_control_potencia[0].kwp > e.potencia_contratada_kw > 0

    elegidas = _escalonar(validas, cfg)
    opciones = [
        Opcion(c.kit1, c.kit2, recomendada=(i == 0), resultado=calcular(replace(e, kit1=c.kit1, kit2=c.kit2), cat, par))
        for i, c in enumerate(elegidas)
    ]
    opciones.sort(key=lambda o: o.resultado.energia.cobertura)
    return ResultadoBusqueda(
        opciones=opciones,
        limitado_por_potencia=limitado,
        evaluadas=len(candidatas),
        validas=len(validas),
        descartes=descartes,
    )


def _catalogo_unitario(cat: Catalogo) -> Catalogo:
    """Catálogo con un kit de 1 kWp para estimar la generación específica."""
    base = cat.kits[0]
    return replace(cat, kits=(replace(base, kwp=1.0),))
