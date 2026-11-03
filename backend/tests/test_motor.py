"""Casos borde del motor (§12) y comportamientos provisorios (§14.2)."""

from dataclasses import replace

import pytest

from casos.definiciones import plecor
from motor import calcular, catalogo_vigente, parametros_vigentes
from motor import provisorios
from motor.calculo import canon_anual, dias_laborables
from motor.finanzas import irr, npv
from motor.modelos import Baterias, Financiacion, HorarioTrabajo, Inversor, Kit, ObjetivoBaterias, TipoInversor

HV16 = "High Voltage 16 kWh min 5 bat"


def test_siete_por_24_no_tiene_dias_no_laborables():
    r = calcular(replace(plecor(), horario_trabajo=HorarioTrabajo.SIETE_X_24, horas_por_dia=24))
    assert all(m.dias_no_laborables == 0 for m in r.mensual)
    assert all(m.excedente_no_laborable_kwh == 0 for m in r.mensual)


@pytest.mark.parametrize(
    "horario, esperado",
    [
        (HorarioTrabajo.SIETE_X_24, 31),
        (HorarioTrabajo.LU_A_VI, 21),
        (HorarioTrabajo.LU_A_SA, 26),
        (HorarioTrabajo.LU_A_MEDIO_SA, 23.5),
    ],
)
def test_dias_laborables(horario, esperado):
    assert dias_laborables(horario, 31, 5) == esperado


def test_kit2_vacio_equivale_a_sin_kit2():
    base = calcular(plecor())
    con_cero = calcular(replace(plecor(), kit2=Kit(22.04, 0, 50)))
    assert con_cero.inversion.total_usd == base.inversion.total_usd
    assert con_cero.kwp_total == base.kwp_total
    assert con_cero.inversion.precio_kwp_kit2 == 0


def test_cable_solo_desde_5_metros():
    e = plecor()
    assert calcular(replace(e, kit1=Kit(139.02, 1, 4.99))).inversion.cable_usd == 0
    assert calcular(replace(e, kit1=Kit(139.02, 2, 15))).inversion.cable_usd == 10 * 125 * 2


def test_inhibicion_si_desperdicia_y_no_retribuye():
    e = replace(plecor(), retribucion_inyeccion=100)
    si = calcular(replace(e, inhibicion_inyeccion=True))
    no = calcular(replace(e, inhibicion_inyeccion=False))
    assert si.energia.inyectada_kwh == 0
    assert si.energia.desperdiciada_kwh == si.energia.inyeccion_anual_kwh > 0
    assert no.energia.inyectada_kwh == no.energia.inyeccion_anual_kwh
    assert no.economia.ahorro_inyeccion_ars == pytest.approx(no.energia.inyectada_kwh * 100)
    assert no.economia.ahorro_anual_usd > si.economia.ahorro_anual_usd


def test_on_grid_ignora_baterias():
    """§6.10 #4: con ON GRID las baterías no reducen inyección ni suman costo."""
    sin = calcular(plecor())
    con = calcular(replace(plecor(), baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, HV16, 10, 1, 1)))
    assert con.energia.inyeccion_anual_kwh == sin.energia.inyeccion_anual_kwh
    assert con.inversion.baterias_usd == 0
    assert {"baterias_on_grid", "baterias_inversor"} <= {a.codigo for a in con.alertas}


def test_baterias_hibrido_reducen_inyeccion():
    sin = calcular(replace(plecor(), tipo_inversor=TipoInversor.HIBRIDO))
    con = calcular(replace(
        plecor(), tipo_inversor=TipoInversor.HIBRIDO, baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, HV16, 10, 1, 1)
    ))
    assert con.energia.inyeccion_anual_kwh < sin.energia.inyeccion_anual_kwh
    assert con.inversion.baterias_usd == 3750 * 10 + 1995 + 1140
    assert not [a for a in con.alertas if a.nivel == "error"]


def test_financiacion_sin_gracia():
    e = plecor()
    r = calcular(replace(e, financiacion=Financiacion(0.8, plazo_anios=4, gracia_anios=0, tasa=0.02, gastos_adm=0.01)))
    f = r.financiacion
    assert f.pagos[0] == pytest.approx(r.inversion.total_usd - f.monto_financiado + f.canon_anual)
    assert f.pagos[1:4] == [f.canon_anual] * 3
    assert f.pagos[4:] == [0, 0, 0]


def test_plazo_es_el_total_y_la_gracia_paga_solo_intereses():
    """5 años con 1 de gracia = 1 año de solo intereses + 4 de capital más intereses."""
    e = plecor()
    r = calcular(replace(e, financiacion=Financiacion(0.8, plazo_anios=5, gracia_anios=1, tasa=0.02, gastos_adm=0.01)))
    f = r.financiacion
    intereses = f.monto_financiado * 0.03
    assert f.pagos[0] == pytest.approx(r.inversion.total_usd - f.monto_financiado + intereses)  # anticipo + intereses
    assert f.canon_anual == pytest.approx(canon_anual(f.monto_financiado, 5, 1, 0.03))
    assert f.canon_anual > intereses  # las cuotas siguientes incluyen capital
    assert f.pagos[1:5] == [pytest.approx(f.canon_anual)] * 4
    assert f.pagos[5:] == [0, 0]
    # Lo que se devuelve en 4 años de amortización cubre exactamente el capital financiado.
    r_mensual = 0.03 / 12
    saldo = f.monto_financiado
    for _ in range(4 * 12):
        saldo = saldo * (1 + r_mensual) - f.canon_anual / 12
    assert saldo == pytest.approx(0, abs=1e-6)


def test_financiacion_semestral():
    e = plecor()
    r = calcular(replace(e, financiacion=Financiacion(0.8, plazo_anios=5, gracia_anios=1, tasa=0.02, gastos_adm=0.01)))
    f = r.financiacion
    assert len(f.pagos_semestrales) == len(f.ahorros_semestrales) == len(f.ahorro_acumulado_semestral) == 14
    # Los dos semestres de cada año suman el pago anual (el anticipo cae en el primer semestre).
    for anio in range(7):
        assert f.pagos_semestrales[2 * anio] + f.pagos_semestrales[2 * anio + 1] == pytest.approx(f.pagos[anio])
    anticipo = r.inversion.total_usd - f.monto_financiado
    assert f.pagos_semestrales[0] - f.pagos_semestrales[1] == pytest.approx(anticipo)
    assert f.ahorros_semestrales == [pytest.approx(r.economia.ahorro_anual_usd / 2)] * 14
    assert f.ahorro_acumulado_semestral[-1] == pytest.approx(7 * r.economia.ahorro_anual_usd)
    assert f.ahorro_acumulado_semestral == sorted(f.ahorro_acumulado_semestral)


def test_varios_anios_de_gracia():
    e = plecor()
    r = calcular(replace(e, financiacion=Financiacion(0.8, plazo_anios=5, gracia_anios=2, tasa=0.02, gastos_adm=0.01)))
    g = r.financiacion
    assert g.pagos[1] == pytest.approx(g.monto_financiado * 0.03)  # 2º año de gracia: solo intereses
    assert g.pagos[2:5] == [pytest.approx(g.canon_anual)] * 3
    assert g.pagos[5:] == [0, 0]


def test_gracia_igual_o_mayor_al_plazo_es_error():
    e = plecor()
    for plazo, gracia in ((2, 2), (1, 3)):
        mala = replace(e, financiacion=Financiacion(0.8, plazo_anios=plazo, gracia_anios=gracia, tasa=0.02))
        assert any(a.codigo == "gracia_financiacion" for a in calcular(mala).alertas)


def test_canon_sin_interes_y_sin_plazo():
    assert canon_anual(12000, 2, 0, 0.0) == pytest.approx(6000)
    assert canon_anual(12000, 3, 1, 0.0) == pytest.approx(6000)  # plazo total 3 con 1 de gracia = 2 de capital
    assert canon_anual(12000, 2, 2, 0.05) == 0
    assert canon_anual(12000, 0, 0, 0.05) == 0
    assert canon_anual(0, 3, 0, 0.05) == 0


def test_roi_es_inversion_sobre_ahorro_y_curva_cruza_cero():
    r = calcular(plecor())
    assert r.roi_anios == pytest.approx(r.inversion.total_usd / r.economia.ahorro_anual_usd)
    anio = int(r.roi_anios)
    assert r.curva_roi[anio - 1] < 0 <= r.curva_roi[anio]


def test_sin_ahorro_no_hay_roi():
    r = calcular(replace(plecor(), costo_distribuidora=0, tasa_cammesa=0))
    assert r.roi_anios is None
    assert "sin_ahorro" in {a.codigo for a in r.alertas}


def test_tasa_976_solo_gudi():
    e = replace(plecor(), tasa_976=0.5)
    from motor.modelos import Categoria

    assert calcular(e).economia.precio_kwh_ars == calcular(plecor()).economia.precio_kwh_ars
    gudi = calcular(replace(e, categoria=Categoria.GUDI))
    assert gudi.economia.precio_kwh_ars > calcular(plecor()).economia.precio_kwh_ars


def test_superficie_engrafado_igual_a_coplanar():
    from motor.modelos import Instalacion

    cop = calcular(replace(plecor(), instalacion=Instalacion.COPLANAR)).superficie_m2
    eng = calcular(replace(plecor(), instalacion=Instalacion.ENGRAFADO)).superficie_m2
    assert eng == cop == pytest.approx(139.02 / 0.58 * 2.9)


def test_alertas_superficie_y_potencia():
    r = calcular(replace(plecor(), m2_disponibles=500, potencia_contratada_kw=100))
    codigos = {a.codigo for a in r.alertas}
    assert {"superficie_insuficiente", "kwp_sobre_contratada", "potencia_sugerida_sobre_contratada"} <= codigos


def test_consumos_incompletos():
    with pytest.raises(ValueError):
        calcular(replace(plecor(), consumos=plecor().consumos[:11]))


def test_npv_e_irr_como_excel():
    flujos = [-100, 30, 40, 50, 20]
    assert npv(0.1, flujos) == pytest.approx(sum(f / 1.1**k for k, f in enumerate(flujos, 1)))
    tasa = irr(flujos)
    assert sum(f / (1 + tasa) ** k for k, f in enumerate(flujos)) == pytest.approx(0, abs=1e-8)
    assert irr([10, 20]) is None


# ------------------------------------------------------------ §14.2 provisorios


def test_a1_kit2_usa_adicional_del_kit1():
    cat = catalogo_vigente()
    e = replace(plecor(), inversor=Inversor.HUAWEI, kit1=Kit(16.24, 1), kit2=Kit(139.02, 1))
    r = calcular(e)
    esperado = cat.kit(139.02).precio_usd_kwp["Losa"] + cat.kit(16.24).adicional_inversor_usd_kwp["Huawei"]
    assert r.inversion.precio_kwp_kit2 == pytest.approx(esperado)


def test_a2_low_voltage_capacidad_cero_pero_con_costo():
    cat = catalogo_vigente()
    assert provisorios.capacidad_bateria_calculo(cat.bateria("Low Voltage 16 kWh")) == 0
    assert provisorios.capacidad_bateria_calculo(cat.bateria(HV16)) == 16.1
    base = replace(plecor(), tipo_inversor=TipoInversor.HIBRIDO)
    con_lv = calcular(replace(base, baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, "Low Voltage 16 kWh", 4)))
    assert con_lv.energia.inyeccion_anual_kwh == calcular(base).energia.inyeccion_anual_kwh
    assert con_lv.inversion.baterias_usd == 3523.5 * 4


def test_a3_ahorro_por_baterias_es_cero():
    r = calcular(replace(
        plecor(), tipo_inversor=TipoInversor.HIBRIDO, baterias=Baterias(True, ObjetivoBaterias.AHORRO, 0, HV16, 10, 1, 1)
    ))
    assert r.economia.ahorro_baterias_ars == 0


def test_a4_potencia_contratada_toma_la_mayor():
    assert provisorios.potencia_contratada_sugerida(80, 120) == 120
    assert provisorios.potencia_contratada_sugerida(None, 75) == 75
    assert provisorios.potencia_contratada_sugerida(None, None) is None


def test_a5_potencia_cammesa_sin_efecto():
    a = calcular(replace(plecor(), potencia_contratada_cammesa_kw=10))
    b = calcular(replace(plecor(), potencia_contratada_cammesa_kw=99999))
    assert a.economia == b.economia and a.inversion == b.inversion


def test_parametros_consistentes():
    par = parametros_vigentes()
    assert len(par.provincias) == 24
    for prov in par.provincias:
        assert len(par.hsp[prov]) == 12
        for a in par.acimuts:
            for i in par.inclinaciones:
                assert len(par.coeficientes_mes(prov, a, i)) == 12
    assert len(par.perfil_horario) == 12 and all(len(f) == 13 for f in par.perfil_horario)
