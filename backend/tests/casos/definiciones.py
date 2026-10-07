"""Casos de equivalencia contra la planilla (§12).

Cada caso es una función que devuelve Entradas. Tras modificar o agregar casos,
regenerar los JSON con:  python scripts/generar_casos_excel.py
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from motor.modelos import (
    PPA,
    Baterias,
    Capacitores,
    Categoria,
    ConsumoMensual,
    Entradas,
    Financiacion,
    HorarioTrabajo,
    Instalacion,
    Inversor,
    Kit,
    Moneda,
    ObjetivoBaterias,
    TipoFinanciacion,
    TipoInversor,
)

CONSUMOS_PLECOR = [  # Hoja1!W7:Y18 (valle, resto, pico)
    (7548, 26059, 6116), (6322, 24041, 5104), (8755, 31205, 7373), (8021, 33550, 7205),
    (10621, 37129, 8969), (11000, 38000, 9000), (11000, 38000, 9000), (10621, 37129, 8969),
    (8021, 33550, 7205), (8755, 31205, 7373), (6322, 24041, 5104), (4828, 22842, 4252),
]


def _consumos(tabla, escala: float = 1.0) -> list[ConsumoMensual]:
    return [ConsumoMensual(v * escala, r * escala, p * escala) for v, r, p in tabla]


def plecor() -> Entradas:
    """PLECOR tal como está en la planilla, sin baterías (es ON GRID, §6.10 #4)."""
    return Entradas(
        numero_propuesta=12508,
        fecha=date(2026, 9, 25),
        dolar=1540,
        cliente="PLECOR",
        provincia="Mendoza",
        categoria=Categoria.INDUSTRIAL,
        distribuidora="EPE",
        tarifa="T2 b1",
        potencia_contratada_kw=280,
        horario_trabajo=HorarioTrabajo.LU_A_SA,
        horas_por_dia=12,
        tasa_cammesa=0.085,
        potencia_contratada_cammesa_kw=2500,
        costo_distribuidora=146.7743,
        tasas_mun_prov=0.099,
        retribucion_inyeccion=110.79,
        tipo_inversor=TipoInversor.ON_GRID,
        inhibicion_inyeccion=True,
        banco_capacitores=False,
        instalacion=Instalacion.LOSA,
        acimut=30,
        inclinacion=15,
        inversor=Inversor.DEYE_HIB,
        kit1=Kit(139.02, 1, 0),
        kit2=None,
        baterias=Baterias(objetivo=ObjetivoBaterias.AHORRO),
        tasa_descuento=0.12,
        periodo_evaluacion=25,
        financiacion=Financiacion(0.8, TipoFinanciacion.PRESTAMO, Moneda.DOLARES, 4, 1, 0.02, 0.01),
        ppa=PPA(aplica=True, periodo_contrato=7, precio_usd_mwh=100, inflacion_usd=0, fee_salida_usd=0, oem=0.1),
        consumos=_consumos(CONSUMOS_PLECOR),
    )


def plecor_hibrido_baterias() -> Entradas:
    """Híbrido con 10 baterías HV 16 kWh: reduce inyección y suma costo."""
    return replace(
        plecor(),
        tipo_inversor=TipoInversor.HIBRIDO,
        baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, "High Voltage 16 kWh min 5 bat", 10, 1, 1),
    )


def inyeccion_retribuida_gudi() -> Entradas:
    """Inhibición NO, GUDI con tasa 976, 7x24, dos kits (A1), cable, K y comisión,
    capacitores, PPA con fee en el año de evaluación, financiación sin gracia."""
    return replace(
        plecor(),
        categoria=Categoria.GUDI,
        provincia="Buenos Aires",
        horario_trabajo=HorarioTrabajo.SIETE_X_24,
        horas_por_dia=24,
        costo_mayorista=62.5,
        tasa_mayorista=0.05,
        costo_cammesa=18.3,
        tasa_976=0.12,
        res281_usd_mwh=4.5,
        inhibicion_inyeccion=False,
        banco_capacitores=True,
        capacitores=Capacitores(kvar=40, inversion_usd=3500, ahorro_ars_anio=2_400_000),
        instalacion=Instalacion.COPLANAR,
        acimut=0,
        inclinacion=20,
        inversor=Inversor.HUAWEI,
        kit1=Kit(55.68, 2, 25),
        kit2=Kit(22.04, 1, 12),
        k_incertidumbre=0.05,
        comision=0.08,
        tasa_descuento=0.15,
        periodo_evaluacion=8,
        financiacion=Financiacion(0.6, TipoFinanciacion.LEASING, Moneda.PESOS, 5, 0, 0.08, 0.02),
        ppa=PPA(aplica=True, periodo_contrato=8, precio_usd_mwh=85, inflacion_usd=0.02, fee_salida_usd=15000, oem=0.05),
    )


def lu_a_vi_coplanar_growatt() -> Entradas:
    """Santa Fe, Lu a Vi 8 h, Growatt, gracia 2 años, sin PPA."""
    return replace(
        plecor(),
        provincia="Santa Fe",
        horario_trabajo=HorarioTrabajo.LU_A_VI,
        horas_por_dia=8,
        instalacion=Instalacion.COPLANAR,
        acimut=0,
        inclinacion=10,
        inversor=Inversor.GROWATT,
        kit1=Kit(88.16, 1, 4),
        financiacion=Financiacion(0.5, TipoFinanciacion.PRESTAMO, Moneda.DOLARES, 3, 2, 0.06, 0.01),
        ppa=PPA(aplica=False),
        periodo_evaluacion=10,
        consumos=_consumos(CONSUMOS_PLECOR, 0.6),
    )


def medio_sabado_piso_huawei() -> Entradas:
    """Lu a 1/2 Sab 24 h, piso, Huawei, consumo bajo (mucho excedente), fee con período 15."""
    return replace(
        plecor(),
        provincia="Córdoba",
        horario_trabajo=HorarioTrabajo.LU_A_MEDIO_SA,
        horas_por_dia=24,
        instalacion=Instalacion.PISO,
        acimut=45,
        inclinacion=30,
        inversor=Inversor.HUAWEI,
        kit1=Kit(110.2, 2, 40),
        inhibicion_inyeccion=False,
        periodo_evaluacion=15,
        ppa=PPA(aplica=True, periodo_contrato=15, precio_usd_mwh=90, inflacion_usd=0.01, fee_salida_usd=20000, oem=0.08),
        financiacion=Financiacion(0.0, TipoFinanciacion.PRESTAMO, Moneda.DOLARES, 0, 0, 0, 0),
        consumos=_consumos(CONSUMOS_PLECOR, 0.3),
    )


def engrafado_cortes_hv768() -> Entradas:
    """Engrafado (§6.10 #2), objetivo Cortes con autonomía, HV 7,68 kWh × 7."""
    return replace(
        plecor(),
        provincia="Salta",
        instalacion=Instalacion.ENGRAFADO,
        acimut=15,
        inclinacion=25,
        tipo_inversor=TipoInversor.HIBRIDO,
        kit1=Kit(33.64, 2, 8),
        baterias=Baterias(True, ObjetivoBaterias.CORTES, 4, "High Voltage 7,68 kWh min 7 bat", 7, 1, 1),
        periodo_evaluacion=6,
    )


def low_voltage_a2() -> Entradas:
    """Batería Low Voltage: capacidad 0 en inyección pero suma costo (A2)."""
    return replace(
        plecor(),
        tipo_inversor=TipoInversor.HIBRIDO,
        kit1=Kit(27.84, 3, 0),
        baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, "Low Voltage 16 kWh", 4, 0, 0),
        periodo_evaluacion=9,
    )


def kit2_distinto_tamanio_a1() -> Entradas:
    """Kit 2 más grande que el kit 1: el adicional por inversor sale del kit 1 (A1)."""
    return replace(
        plecor(),
        inversor=Inversor.HUAWEI,
        kit1=Kit(16.24, 1, 6),
        kit2=Kit(139.02, 1, 30),
        horario_trabajo=HorarioTrabajo.LU_A_VI,
        horas_por_dia=10,
        periodo_evaluacion=5,
        ppa=PPA(aplica=True, periodo_contrato=5, precio_usd_mwh=110, inflacion_usd=0.03, fee_salida_usd=8000, oem=0.1),
    )


def sistema_chico_sin_excedente() -> Entradas:
    """Sistema chico frente al consumo: inyección nula."""
    return replace(
        plecor(),
        kit1=Kit(11.02, 1, 0),
        horario_trabajo=HorarioTrabajo.SIETE_X_24,
        horas_por_dia=24,
        consumos=_consumos(CONSUMOS_PLECOR, 2.0),
    )


CASOS = {
    f.__name__: f
    for f in (
        plecor,
        plecor_hibrido_baterias,
        inyeccion_retribuida_gudi,
        lu_a_vi_coplanar_growatt,
        medio_sabado_piso_huawei,
        engrafado_cortes_hv768,
        low_voltage_a2,
        kit2_distinto_tamanio_a1,
        sistema_chico_sin_excedente,
    )
}
