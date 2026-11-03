"""Validaciones de entradas y alertas de resultado (§6.2, §8)."""

from __future__ import annotations

import math

from .catalogo import BateriaCatalogo, Catalogo, Parametros
from .modelos import (
    HORAS_POR_DIA,
    PERIODOS_EVALUACION,
    Alerta,
    Entradas,
    Inversor,
    ObjetivoBaterias,
    OrigenConsumo,
    Resultado,
    TipoInversor,
)


def sugerir_pdu_rack(bateria: BateriaCatalogo, cantidad: int) -> tuple[int, int]:
    """PDU: 1 cada N baterías; rack: 1 cada 'máx por rack' (TRANSP!V46:W48)."""
    if cantidad <= 0:
        return 0, 0
    pdu = math.ceil(cantidad / bateria.baterias_por_pdu) if bateria.baterias_por_pdu else 0
    rack = math.ceil(cantidad / bateria.baterias_por_rack) if bateria.baterias_por_rack else 0
    return pdu, rack


def validar(e: Entradas, cat: Catalogo, par: Parametros) -> list[Alerta]:
    alertas: list[Alerta] = []

    def error(codigo: str, mensaje: str, campo: str | None = None) -> None:
        alertas.append(Alerta(codigo, "error", mensaje, campo))

    def advertencia(codigo: str, mensaje: str, campo: str | None = None) -> None:
        alertas.append(Alerta(codigo, "advertencia", mensaje, campo))

    if e.provincia not in par.provincias:
        error("provincia_desconocida", f"Provincia '{e.provincia}' sin datos de HSP", "provincia")
    if e.acimut not in par.acimuts:
        error("acimut_invalido", f"Acimut {e.acimut} fuera de {par.acimuts}", "acimut")
    if e.inclinacion not in par.inclinaciones:
        error("inclinacion_invalida", f"Inclinación {e.inclinacion} fuera de {par.inclinaciones}", "inclinacion")
    if e.horas_por_dia not in HORAS_POR_DIA:
        error("horas_invalidas", f"Horas por día {e.horas_por_dia} fuera de {HORAS_POR_DIA}", "horas_por_dia")
    if e.periodo_evaluacion not in PERIODOS_EVALUACION:
        error("periodo_invalido", f"Período {e.periodo_evaluacion} fuera de {PERIODOS_EVALUACION}", "periodo_evaluacion")
    if e.ppa.aplica and e.ppa.periodo_contrato not in PERIODOS_EVALUACION:
        error("periodo_ppa_invalido", f"Período de contrato fuera de {PERIODOS_EVALUACION}", "ppa.periodo_contrato")
    if e.dolar <= 0:
        error("dolar_invalido", "El valor del dólar debe ser mayor a 0", "dolar")
    if not 0 <= e.comision < 1:
        error("comision_invalida", "La comisión debe estar entre 0 % y 100 %", "comision")

    for nombre, kit in (("kit1", e.kit1), ("kit2", e.kit2)):
        if kit is None or kit.cantidad == 0:
            continue
        if kit.cantidad < 0:
            error("cantidad_kit_invalida", "La cantidad de kits no puede ser negativa", f"{nombre}.cantidad")
        try:
            cat.kit(kit.kwp)
        except KeyError as exc:
            error("kit_desconocido", str(exc.args[0]), f"{nombre}.kwp")
    if e.kwp_total <= 0:
        error("sin_potencia", "El sistema no tiene kits", "kit1.cantidad")

    alertas += _validar_baterias(e, cat)

    if e.financiacion.porcentaje > 0:
        if e.financiacion.plazo_anios <= 0:
            error("plazo_financiacion", "Con monto a financiar el plazo debe ser mayor a 0", "financiacion.plazo_anios")
        elif e.financiacion.gracia_anios >= e.financiacion.plazo_anios:
            error(
                "gracia_financiacion",
                "El plazo es el total de la financiación: tiene que ser mayor que los años de gracia",
                "financiacion.plazo_anios",
            )

    estimados = [par.meses[i] for i, c in enumerate(e.consumos) if c.origen == OrigenConsumo.ESTIMADO]
    if estimados:
        advertencia("meses_estimados", f"Consumos estimados por espejo: {', '.join(estimados)}", "consumos")
    return alertas


def _validar_baterias(e: Entradas, cat: Catalogo) -> list[Alerta]:
    b = e.baterias
    if not b.incluye:
        return []
    alertas: list[Alerta] = []

    def error(codigo: str, mensaje: str, campo: str) -> None:
        alertas.append(Alerta(codigo, "error", mensaje, campo))

    def advertencia(codigo: str, mensaje: str, campo: str) -> None:
        alertas.append(Alerta(codigo, "advertencia", mensaje, campo))

    if e.tipo_inversor == TipoInversor.ON_GRID:
        error("baterias_on_grid", "Un sistema ON GRID no admite baterías", "baterias.incluye")
    if e.inversor != Inversor.DEYE_HIB or e.tipo_inversor != TipoInversor.HIBRIDO:
        error("baterias_inversor", "Con baterías el inversor debe ser Deye Hib y el tipo HIBRIDO", "inversor")
    if b.objetivo == ObjetivoBaterias.CORTES and b.autonomia_h <= 0:
        advertencia("autonomia", "Con objetivo 'Cortes' indicar la autonomía en horas", "baterias.autonomia_h")
    if b.modelo is None:
        error("baterias_modelo", "Elegir un modelo de batería", "baterias.modelo")
        return alertas
    try:
        bat = cat.bateria(b.modelo)
    except KeyError as exc:
        error("baterias_modelo", str(exc.args[0]), "baterias.modelo")
        return alertas

    if bat.min_baterias is not None and b.cantidad < bat.min_baterias:
        error("baterias_minimo", f"{bat.modelo}: mínimo {bat.min_baterias} baterías", "baterias.cantidad")
    if bat.max_baterias is not None and b.cantidad > bat.max_baterias:
        error("baterias_maximo", f"{bat.modelo}: máximo {bat.max_baterias} baterías", "baterias.cantidad")
    pdu, rack = sugerir_pdu_rack(bat, b.cantidad)
    if b.cantidad_pdu != pdu:
        advertencia("pdu_sugerido", f"Para {b.cantidad} baterías se sugieren {pdu} PDU", "baterias.cantidad_pdu")
    if b.cantidad_rack != rack:
        advertencia("rack_sugerido", f"Para {b.cantidad} baterías se sugieren {rack} rack", "baterias.cantidad_rack")
    return alertas


def alertas_resultado(e: Entradas, r: Resultado) -> list[Alerta]:
    alertas = []
    if e.potencia_contratada_kw > 0:
        if r.potencia_sugerida_kw > e.potencia_contratada_kw:  # [PERFIL!I7]
            alertas.append(Alerta(
                "potencia_sugerida_sobre_contratada",
                "advertencia",
                f"La potencia sugerida ({r.potencia_sugerida_kw:.1f} kW) supera la contratada "
                f"({e.potencia_contratada_kw:.0f} kW)",
                "potencia_contratada_kw",
            ))
        if r.kwp_total > e.potencia_contratada_kw:
            alertas.append(Alerta(
                "kwp_sobre_contratada",
                "advertencia",
                f"El sistema ({r.kwp_total:.2f} kWp) supera la potencia contratada "
                f"({e.potencia_contratada_kw:.0f} kW)",
                "kit1.cantidad",
            ))
    if e.m2_disponibles is not None and r.superficie_m2 > e.m2_disponibles:
        alertas.append(Alerta(
            "superficie_insuficiente",
            "advertencia",
            f"Se requieren {r.superficie_m2:.0f} m² y hay {e.m2_disponibles:.0f} m² disponibles",
            "m2_disponibles",
        ))
    if r.economia.ahorro_anual_usd <= 0:
        alertas.append(Alerta("sin_ahorro", "advertencia", "El ahorro anual es nulo o negativo", None))
    return alertas
