"""Equivalencia del motor con la planilla (§12).

Los valores esperados vienen de recalcular la planilla con Excel
(scripts/generar_casos_excel.py). Diferencias intencionales (§6.10) se testean
contra el valor corregido.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from motor import calcular
from motor.modelos import Instalacion
from motor.serializacion import entradas_desde_dict

CASOS = sorted((Path(__file__).parent / "casos").glob("*.json"))
TOLERANCIA = 1e-6  # relativa; la spec pide < 0,1 %
PERIODOS = [5, 6, 7, 8, 9, 10, 15, 25]


def _cargar(ruta: Path):
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    entradas = entradas_desde_dict(datos["entradas"])
    # El JSON guarda el N44 de la planilla (años de amortización); en el sistema el plazo es el total.
    f = entradas.financiacion
    entradas = replace(entradas, financiacion=replace(f, plazo_anios=f.plazo_anios + f.gracia_anios))
    return entradas, calcular(entradas), datos["excel"]


@pytest.fixture(params=CASOS, ids=[c.stem for c in CASOS])
def caso(request):
    return _cargar(request.param)


def igual(obtenido, esperado):
    if isinstance(esperado, list):
        assert len(obtenido) == len(esperado)
        for o, x in zip(obtenido, esperado):
            igual(o, x)
        return
    assert obtenido == pytest.approx(esperado, rel=TOLERANCIA, abs=1e-6)


def test_hay_casos():
    assert len(CASOS) >= 5


def test_energia(caso):
    _, r, x = caso
    m = r.mensual
    igual([v.generacion_kwh for v in m], x["generacion_mensual"])
    igual([v.dias_laborables for v in m], x["dias_laborables"])
    igual([v.kw_fuera_horario for v in m], x["kw_fuera"])
    igual([v.kw_horario_laboral for v in m], x["kw_lab"])
    igual([v.excedente_no_laborable_kwh for v in m], x["exc_no_lab"])
    igual([v.excedente_laborable_kwh for v in m], x["exc_lab"])
    igual([v.inyeccion_kwh for v in m], x["inyeccion_mensual"])
    e = r.energia
    igual(e.consumo_anual_kwh, x["consumo_anual"])
    igual(e.generacion_anual_kwh, x["generacion_anual"])
    igual(e.cobertura, x["cobertura"])
    igual(e.autoconsumo_kwh, x["autoconsumo"])
    igual(e.autoconsumo_pct, x["autoconsumo_pct"])
    igual(e.inyectada_kwh, x["inyectada"])
    igual(e.desperdiciada_kwh, x["desperdiciada"])
    igual(e.ahorro_pct, x["ahorro_pct"])
    igual(r.potencia_sugerida_kw, x["potencia_sugerida"])
    igual(r.capacidad_bateria_recomendada_kwh, x["capacidad_bateria_recomendada"])


def test_economia_e_inversion(caso):
    _, r, x = caso
    igual(r.economia.precio_kwh_ars, x["precio_kwh"])
    igual(r.economia.precio_kwh_usd, x["precio_kwh_usd"])
    igual(r.economia.ahorro_anual_ars, x["ahorro_ars"])
    igual(r.economia.ahorro_anual_usd, x["ahorro_usd"])
    igual(r.inversion.precio_kwp_kit1, x["precio_kwp_kit1"])
    igual(r.inversion.precio_kwp_kit2, x["precio_kwp_kit2"])
    igual(r.inversion.cable_usd, x["cable_kit1"] + x["cable_kit2"])
    igual(r.inversion.baterias_usd, x["baterias_usd"])
    igual(r.inversion.total_usd, x["inversion"])


def test_superficie(caso):
    e, r, x = caso
    esperado = x["superficie_m2"]
    if e.instalacion == Instalacion.ENGRAFADO:
        esperado = esperado / 5 * 2.9  # §6.10 #2: la planilla usa factor 5
    igual(r.superficie_m2, esperado)


def test_indicadores_financieros(caso):
    _, r, x = caso
    igual(r.roi_anios, x["roi"])
    igual(r.van_tir.flujos, x["flujos"])
    igual([r.van_tir.van_por_periodo[p] for p in PERIODOS], x["van_por_periodo"])
    igual(r.van_tir.van, x["van"])
    igual(r.van_tir.tir, x["tir"])


def test_ppa(caso):
    _, r, x = caso
    igual(r.ppa.flujos, x["flujos_ppa"])
    igual([r.ppa.van_por_periodo[p] for p in PERIODOS], x["van_ppa_por_periodo"])
    for p, esperado in zip(PERIODOS, x["tir_ppa_por_periodo"]):
        if esperado is None:  # Excel no converge (sin cambio de signo)
            assert r.ppa.tir_por_periodo[p] is None
        else:
            igual(r.ppa.tir_por_periodo[p], esperado)
    igual(r.ppa.ventas_anio1_usd, x["ventas_anio1"])
    if x["tir_ppa"] is not None:
        igual(r.ppa.tir, x["tir_ppa"])


def test_financiacion(caso):
    e, r, x = caso
    igual(r.financiacion.monto_financiado, x["monto_financiado"])
    if e.financiacion.plazo_anios == 0:
        # La planilla da #DIV/0!; el sistema informa canon 0.
        assert x["canon"] is None
        assert r.financiacion.canon_anual == 0
        return
    f = e.financiacion
    if f.gracia_anios == 0:
        igual(r.financiacion.canon_anual, x["canon"])
        igual(r.financiacion.pagos, x["pagos_financiacion"])
        return

    # Diferencia intencional (§6.10 #6): la planilla capitaliza la gracia en el saldo; el sistema
    # paga solo intereses durante la gracia y amortiza el monto financiado sin capitalizar.
    i, n = f.tasa + f.gastos_adm, f.plazo_anios - f.gracia_anios
    financiado = r.financiacion.monto_financiado
    canon = 12 * financiado * (i / 12) / (1 - (1 + i / 12) ** (-12 * n))
    igual(r.financiacion.canon_anual, canon)
    anticipo = r.inversion.total_usd - financiado
    esperados = [anticipo + (financiado * i if f.gracia_anios >= 1 else canon)]
    esperados += [financiado * i if k <= f.gracia_anios else canon if k <= f.plazo_anios else 0.0 for k in range(2, 8)]
    igual(r.financiacion.pagos, esperados)


def test_huella(caso):
    _, r, x = caso
    h = x["huella"]  # Hoja1!I60:R60
    igual(r.huella.tco2_anio, h[0])
    igual(r.huella.tco2_25_anios, h[3])
    igual(r.huella.arboles, h[6])
    igual(r.huella.autos, h[9])
