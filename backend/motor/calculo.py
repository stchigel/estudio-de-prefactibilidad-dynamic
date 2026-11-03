"""Motor de cálculo: réplica de la planilla (§6).

Las referencias entre corchetes indican la celda equivalente del Excel.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import provisorios
from .catalogo import Catalogo, Parametros, catalogo_vigente, parametros_vigentes
from .finanzas import irr, npv
from .modelos import (
    PERIODOS_EVALUACION,
    Economia,
    Energia,
    Entradas,
    HorarioTrabajo,
    Huella,
    Inversion,
    Mensual,
    ObjetivoBaterias,
    Resultado,
    ResultadoFinanciacion,
    ResultadoPPA,
    VanTir,
)
from .validaciones import alertas_resultado, validar

ANIOS_FLUJO = 25
ANIOS_FINANCIACION = 7
# El gráfico del repago muestra unos años más allá del ROI (con un mínimo) para que se vea el cruce por cero.
ANIOS_CURVA_ROI_MIN = 8
ANIOS_CURVA_ROI_MARGEN = 5
ANIOS_CURVA_ROI_SIN_REPAGO = 15
DISTANCIA_CABLE_INCLUIDA_M = 5
# Años en los que la planilla puede ubicar el fee de salida (VAN TIR!B6:B11 y B35:B40).
ANIOS_FEE_SALIDA = range(5, 11)


def calcular(
    e: Entradas, catalogo: Catalogo | None = None, parametros: Parametros | None = None
) -> Resultado:
    cat = catalogo or catalogo_vigente()
    par = parametros or parametros_vigentes()
    if len(e.consumos) != 12:
        raise ValueError(f"Se esperan 12 meses de consumo, hay {len(e.consumos)}")

    kwp = e.kwp_total
    mensual = balance_mensual(e, cat, par, kwp)
    energia = _energia(e, mensual)
    economia = _economia(e, energia)
    inversion = _inversion(e, cat)
    superficie = superficie_m2(kwp, e.instalacion, par)

    ahorro_usd = economia.ahorro_anual_usd
    roi = inversion.total_usd / ahorro_usd if ahorro_usd > 0 else None  # [ROI!D13]
    curva_roi = [k * ahorro_usd - inversion.total_usd for k in range(1, ANIOS_FLUJO + 1)]

    resultado = Resultado(
        kwp_total=kwp,
        superficie_m2=superficie,
        mensual=mensual,
        energia=energia,
        economia=economia,
        inversion=inversion,
        roi_anios=roi,
        curva_roi=curva_roi,
        anios_curva_roi=anios_curva_roi(roi),
        van_tir=_van_tir(e, par, ahorro_usd, inversion.total_usd),
        ppa=_ppa(e, par, energia, inversion.total_usd),
        financiacion=_financiacion(e, inversion.total_usd, ahorro_usd),
        huella=_huella(energia.generacion_anual_kwh, par),
        capacidad_bateria_recomendada_kwh=_capacidad_bateria_recomendada(e, mensual),
        potencia_sugerida_kw=_potencia_sugerida(e, par),
        alertas=[],
        version_catalogo=cat.version,
        version_parametros=par.version,
    )
    resultado.alertas = validar(e, cat, par) + alertas_resultado(e, resultado)
    return resultado


def anios_curva_roi(roi: float | None) -> int:
    """Años a mostrar en el gráfico de repago: dinámico según el ROI de cada caso."""
    if roi is None:
        return ANIOS_CURVA_ROI_SIN_REPAGO
    return min(ANIOS_FLUJO, max(ANIOS_CURVA_ROI_MIN, math.ceil(roi) + ANIOS_CURVA_ROI_MARGEN))


# ------------------------------------------------------------ generación y BAT


def dias_laborables(horario: HorarioTrabajo, dias: int, semanas: int) -> float:
    """[BAT!M5:M16]"""
    match horario:
        case HorarioTrabajo.SIETE_X_24:
            return dias
        case HorarioTrabajo.LU_A_VI:
            return dias - 2 * semanas
        case HorarioTrabajo.LU_A_SA:
            return dias - semanas
        case HorarioTrabajo.LU_A_MEDIO_SA:
            return dias - 1.5 * semanas
    raise ValueError(horario)


def capacidad_baterias_kwh(e: Entradas, cat: Catalogo) -> float:
    """[BAT!R1] Sin baterías activas la capacidad es 0 (§6.10 #4)."""
    if not e.baterias_activas:
        return 0.0
    bateria = cat.bateria(e.baterias.modelo)
    return provisorios.capacidad_bateria_calculo(bateria) * e.baterias.cantidad


def balance_mensual(e: Entradas, cat: Catalogo, par: Parametros, kwp: float) -> list[Mensual]:
    hsp = par.hsp[e.provincia]
    coef = par.coeficientes_mes(e.provincia, e.acimut, e.inclinacion)
    cap_bat = capacidad_baterias_kwh(e, cat)
    horas = min(e.horas_por_dia, par.horas_laborables_max)

    meses = []
    for m, consumo in enumerate(e.consumos):
        dias = par.dias_mes[m]
        lab = dias_laborables(e.horario_trabajo, dias, par.semanas_mes[m])
        no_lab = dias - lab
        kw_fuera = consumo.valle / dias / 6  # [BAT!O]
        if lab == 0:  # [BAT!P]
            kw_lab = consumo.resto / (no_lab * par.horas_laborables_max)
        else:
            kw_lab = (consumo.resto - kw_fuera * no_lab * horas) / (lab * horas)

        generacion = kwp * hsp[m] * coef[m] * dias  # [PERFIL!R5:R16]
        gen_horaria = [p * generacion / dias for p in par.perfil_horario[m]]  # [BAT!AA:AM]
        exc_no_lab = 0.0 if no_lab == 0 else sum(max(g - kw_fuera, 0.0) for g in gen_horaria)
        exc_lab = sum(max(g - kw_lab, 0.0) for g in gen_horaria)
        inyeccion = max(exc_no_lab - cap_bat, 0.0) * no_lab + max(exc_lab - cap_bat, 0.0) * lab

        meses.append(
            Mensual(
                mes=par.meses[m],
                consumo_kwh=consumo.total,
                generacion_kwh=generacion,
                hsp=hsp[m],
                coeficiente=coef[m],
                dias_laborables=lab,
                dias_no_laborables=no_lab,
                kw_fuera_horario=kw_fuera,
                kw_horario_laboral=kw_lab,
                excedente_no_laborable_kwh=exc_no_lab,
                excedente_laborable_kwh=exc_lab,
                inyeccion_kwh=inyeccion,
            )
        )
    return meses


def _energia(e: Entradas, mensual: list[Mensual]) -> Energia:
    consumo = sum(m.consumo_kwh for m in mensual)  # [Hoja1!E33]
    generacion = sum(m.generacion_kwh for m in mensual)  # [Hoja1!J33]
    excedente = sum(m.inyeccion_kwh for m in mensual)  # [PERFIL!V18]
    inyectada = 0.0 if e.inhibicion_inyeccion else excedente  # [Hoja1!E35]
    desperdiciada = excedente if e.inhibicion_inyeccion else 0.0  # [Hoja1!J35]
    autoconsumo = generacion - excedente  # [Hoja1!P33]
    return Energia(
        consumo_anual_kwh=consumo,
        generacion_anual_kwh=generacion,
        inyeccion_anual_kwh=excedente,
        inyectada_kwh=inyectada,
        desperdiciada_kwh=desperdiciada,
        autoconsumo_kwh=autoconsumo,
        cobertura=generacion / consumo if consumo else 0.0,  # [Hoja1!L33]
        autoconsumo_pct=autoconsumo / generacion if generacion else 0.0,  # [Hoja1!R33]
        ahorro_pct=(autoconsumo + inyectada) / consumo if consumo else 0.0,  # [Hoja1!N35]
    )


# ------------------------------------------------------------ economía


def precio_kwh_ars(e: Entradas) -> float:
    """[PERFIL!R20]"""
    return (
        e.costo_mayorista * (1 + e.tasa_mayorista)
        + e.costo_cammesa * (1 + e.tasa_cammesa)
        + e.costo_distribuidora * (1 + e.tasas_mun_prov) * (1 + e.tasa_976_aplicable)
        + e.res281_usd_mwh * e.dolar / 1000
    )


def _economia(e: Entradas, energia: Energia) -> Economia:
    precio = precio_kwh_ars(e)
    autoconsumo = energia.autoconsumo_kwh * precio  # [PERFIL!R22]
    inyeccion = energia.inyectada_kwh * e.retribucion_inyeccion  # [PERFIL!V22]
    capacitores = e.capacitores.ahorro_ars_anio if e.banco_capacitores else 0.0  # [PERFIL!R24]
    baterias = provisorios.ahorro_por_baterias_ars()  # [PERFIL!V24]
    total = autoconsumo + inyeccion + capacitores + baterias  # [PERFIL!T26]
    return Economia(
        precio_kwh_ars=precio,
        precio_kwh_usd=precio / e.dolar,  # [PERFIL!R33] sin R21 (§6.10 #1)
        ahorro_autoconsumo_ars=autoconsumo,
        ahorro_inyeccion_ars=inyeccion,
        ahorro_capacitores_ars=capacitores,
        ahorro_baterias_ars=baterias,
        ahorro_anual_ars=total,
        ahorro_anual_usd=total / e.dolar,  # [PERFIL!T30]
    )


def precios_kwp(e: Entradas, cat: Catalogo) -> tuple[float, float]:
    """Precio de venta U$D/kWp de cada kit [Hoja1!J20, J22]."""
    kit1 = cat.kit(e.kit1.kwp)
    p1 = kit1.precio_usd_kwp[e.instalacion] + kit1.adicional_inversor_usd_kwp[e.inversor]
    p2 = 0.0
    if e.kit2 is not None and e.kit2.cantidad >= 1:
        p2 = cat.kit(e.kit2.kwp).precio_usd_kwp[e.instalacion] + provisorios.adicional_inversor_kit2(
            cat, e.kit1.kwp, e.kit2.kwp, e.inversor
        )
    return p1, p2


def _inversion(e: Entradas, cat: Catalogo) -> Inversion:
    p1, p2 = precios_kwp(e, cat)
    paneles = e.kit1.kwp * p1 * e.kit1.cantidad
    if e.kit2 is not None:
        paneles += e.kit2.kwp * p2 * e.kit2.cantidad

    cable = 0.0  # [Hoja1!R20, R22]
    for kit in (e.kit1, e.kit2):
        if kit is not None and kit.cantidad > 0 and kit.distancia_tgbt_m >= DISTANCIA_CABLE_INCLUIDA_M:
            usd_m = cat.kit(kit.kwp).cable_ca_usd_m
            cable += (kit.distancia_tgbt_m - DISTANCIA_CABLE_INCLUIDA_M) * usd_m * kit.cantidad

    capacitores = e.capacitores.inversion_usd if e.banco_capacitores else 0.0
    baterias = 0.0  # [Hoja1!J28]
    if e.baterias_activas:
        b = cat.bateria(e.baterias.modelo)
        baterias = (
            b.precio_usd * e.baterias.cantidad
            + b.precio_pdu_usd * e.baterias.cantidad_pdu
            + b.precio_rack_usd * e.baterias.cantidad_rack
        )

    total = (paneles + cable + capacitores + baterias) * (1 + e.k_incertidumbre) / (1 - e.comision)
    return Inversion(
        precio_kwp_kit1=p1,
        precio_kwp_kit2=p2,
        paneles_usd=paneles,
        cable_usd=cable,
        capacitores_usd=capacitores,
        baterias_usd=baterias,
        total_usd=total,  # [Hoja1!E37]
    )


def superficie_m2(kwp: float, instalacion: str, par: Parametros) -> float:
    """[Hoja1!Q31] con factor Engrafado corregido (§6.10 #2)."""
    return kwp / par.factor_kwp_por_modulo * par.factores_superficie[instalacion]


# ------------------------------------------------------------ indicadores financieros


def _serie_degradada(inicial: float, par: Parametros, anios: int = ANIOS_FLUJO) -> list[float]:
    serie = [inicial]
    for anio in range(2, anios + 1):
        serie.append(serie[-1] * par.factor_degradacion(anio))
    return serie


def _capex(inversion: float, ppa_aplica: bool, anio_fee: int, fee: float) -> list[float]:
    capex = [0.0] * ANIOS_FLUJO
    capex[0] = inversion
    if ppa_aplica and anio_fee in ANIOS_FEE_SALIDA:
        capex[anio_fee - 1] = -fee
    return capex


def _buscar_periodo(tabla: dict[int, float], periodo: int):
    """HLOOKUP aproximado sobre los períodos de evaluación."""
    candidatos = [p for p in tabla if p <= periodo]
    return tabla[max(candidatos)] if candidatos else None


def _van_tir(e: Entradas, par: Parametros, ahorro_usd: float, inversion: float) -> VanTir:
    """[VAN TIR!A1:S26]"""
    ingresos = _serie_degradada(ahorro_usd, par)
    capex = _capex(inversion, e.ppa.aplica, e.periodo_evaluacion, e.ppa.fee_salida_usd)
    flujos = [i - c for i, c in zip(ingresos, capex)]
    van = {n: npv(e.tasa_descuento, flujos[:n]) for n in PERIODOS_EVALUACION}
    return VanTir(
        flujos=flujos,
        van_por_periodo=van,
        van=_buscar_periodo(van, e.periodo_evaluacion),
        tir=irr(flujos),
    )


def _ppa(e: Entradas, par: Parametros, energia: Energia, inversion: float) -> ResultadoPPA:
    """[VAN TIR!A30:S55] y [Hoja1!E53, P53]"""
    p = e.ppa
    energia_1 = (energia.autoconsumo_kwh + energia.inyectada_kwh) * (1 - p.oem)
    energias = _serie_degradada(energia_1, par)
    precios = [p.precio_usd_mwh / 1000 * (1 + p.inflacion_usd) ** k for k in range(ANIOS_FLUJO)]
    capex = _capex(inversion, p.aplica, p.periodo_contrato, p.fee_salida_usd)
    flujos = [en * pr - c for en, pr, c in zip(energias, precios, capex)]
    van = {n: npv(e.tasa_descuento, flujos[:n]) for n in PERIODOS_EVALUACION}
    tir = {n: irr(flujos[:n]) for n in PERIODOS_EVALUACION}
    return ResultadoPPA(
        flujos=flujos,
        van_por_periodo=van,
        tir_por_periodo=tir,
        tir=_buscar_periodo(tir, p.periodo_contrato),
        ventas_anio1_usd=p.precio_usd_mwh * energia.autoconsumo_kwh / 1000,
    )


def canon_anual(financiado: float, plazo: int, gracia: int, interes: float) -> float:
    """Cuota anual de la etapa de amortización: sistema francés mensual a `plazo − gracia` años.

    `plazo` es el total de la financiación (gracia incluida): 5 años con 1 de gracia
    son 1 año de solo intereses y 4 de capital más intereses.
    """
    anios = plazo - gracia
    if financiado == 0 or anios <= 0:
        return 0.0
    cuotas = 12 * anios
    r = interes / 12
    if r == 0:
        return 12 * financiado / cuotas
    return 12 * financiado * r / (1 - (1 + r) ** -cuotas)


def _financiacion(e: Entradas, inversion: float, ahorro_usd: float) -> ResultadoFinanciacion:
    """Pagos de los primeros años. Los años de gracia pagan solo intereses sobre el
    monto financiado (no se capitalizan); después, cuotas de capital más intereses.
    El año 1 incluye además el anticipo (la parte no financiada)."""
    f = e.financiacion
    financiado = inversion * f.porcentaje
    interes = f.tasa + f.gastos_adm
    canon = canon_anual(financiado, f.plazo_anios, f.gracia_anios, interes)
    propio = inversion - financiado

    def pago(anio: int) -> float:
        if anio <= f.gracia_anios:
            return financiado * interes
        return canon if anio <= f.plazo_anios else 0.0

    pagos = [propio + pago(1)] + [pago(k) for k in range(2, ANIOS_FINANCIACION + 1)]

    # Semestral: las cuotas y los intereses se reparten parejo en los dos semestres del año;
    # el anticipo se paga en el primero. El ahorro es constante, así que también se parte en dos.
    pagos_sem = []
    for anio in range(1, ANIOS_FINANCIACION + 1):
        mitad = pago(anio) / 2
        pagos_sem += [mitad + (propio if anio == 1 else 0.0), mitad]
    ahorros_sem = [ahorro_usd / 2] * (2 * ANIOS_FINANCIACION)
    acumulado, total = [], 0.0
    for a in ahorros_sem:
        total += a
        acumulado.append(total)
    return ResultadoFinanciacion(
        monto_financiado=financiado,
        canon_anual=canon,
        pagos=pagos,
        ahorros=[ahorro_usd] * ANIOS_FINANCIACION,
        pagos_semestrales=pagos_sem,
        ahorros_semestrales=ahorros_sem,
        ahorro_acumulado_semestral=acumulado,
    )


# ------------------------------------------------------------ otros indicadores


def _huella(generacion_kwh: float, par: Parametros) -> Huella:
    """[Hoja1!I60:R60]"""
    mwh = generacion_kwh / 1000
    tco2 = mwh * par.huella["tco2_por_mwh"]
    return Huella(
        tco2_anio=tco2,
        tco2_25_anios=tco2 * 25,
        arboles=mwh * par.huella["arboles_por_mwh"],
        autos=mwh * par.huella["autos_por_mwh"],
    )


COS_PHI_OBJETIVO = 0.95


def kvar_capacitores(
    potencia_kw: float, activa_kwh: float, reactiva_kvarh: float, cos_phi_objetivo: float = COS_PHI_OBJETIVO
) -> float:
    """[Bco Capac!C18] Qc = P · (tan φ − tan φ_obj), con tan φ = E_reactiva / E_activa."""
    if potencia_kw <= 0 or activa_kwh <= 0 or reactiva_kvarh < 0:
        return 0.0
    tan_objetivo = math.tan(math.acos(cos_phi_objetivo))
    return max(0.0, potencia_kw * (reactiva_kvarh / activa_kwh - tan_objetivo))


def _capacidad_bateria_recomendada(e: Entradas, mensual: list[Mensual]) -> float:
    """[Hoja1!M24]"""
    match e.baterias.objetivo:
        case ObjetivoBaterias.AHORRO:
            return max(m.excedente_laborable_kwh for m in mensual)
        case ObjetivoBaterias.CORTES:
            promedio_kw_lab = sum(m.kw_horario_laboral for m in mensual) / len(mensual)
            return promedio_kw_lab * e.baterias.autonomia_h
    return 0.0


def _potencia_sugerida(e: Entradas, par: Parametros) -> float:
    """[PERFIL!I4] Consumo medio diario en horario 'resto' sobre HSP promedio."""
    resto_diario = sum(c.resto for c in e.consumos) / 12 / 30
    return resto_diario / promedio(par.hsp[e.provincia])


def promedio(valores: Sequence[float]) -> float:
    return sum(valores) / len(valores)
