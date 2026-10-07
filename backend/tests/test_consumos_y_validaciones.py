from motor.catalogo import catalogo_vigente
from motor.consumos import LecturaMensual, consolidar, mes_espejo
from motor.modelos import OrigenConsumo
from motor.validaciones import sugerir_pdu_rack

F, H = OrigenConsumo.FACTURA, OrigenConsumo.HISTORIAL


def test_espejo_respecto_del_solsticio():
    assert [mes_espejo(m) for m in (2, 3, 4, 5, 6, 1)] == [11, 10, 9, 8, 7, 12]


def test_factura_prevalece_sobre_historial_del_mismo_periodo():
    meses = consolidar([
        LecturaMensual(2026, 7, 1, 1, 1, H),
        LecturaMensual(2026, 7, 9, 9, 9, F),
        LecturaMensual(2026, 7, 5, 5, 5, H),
    ])
    assert (meses[6].valle, meses[6].origen) == (9, F)


def test_mes_calendario_toma_el_periodo_mas_reciente():
    meses = consolidar([LecturaMensual(2026, 3, 2, 2, 2, H), LecturaMensual(2025, 3, 1, 1, 1, F)])
    assert meses[2].valle == 2


def test_meses_faltantes_se_estiman_por_espejo():
    """Caso EPE: dos facturas con historial de 6 meses cubren el año; con una sola se espeja."""
    lecturas = [LecturaMensual(2026, m, m, 10 * m, 100 * m, H) for m in range(7, 13)]
    meses = consolidar(lecturas)
    assert all(m is not None for m in meses)
    assert meses[1].origen == OrigenConsumo.ESTIMADO and meses[1].valle == 11  # FEB ← NOV
    assert meses[5].valle == 7  # JUN ← JUL
    assert meses[6].origen == H


def test_mes_sin_dato_ni_espejo_queda_vacio():
    meses = consolidar([LecturaMensual(2026, 1, 1, 1, 1, F)])
    assert meses[11].origen == OrigenConsumo.ESTIMADO  # DIC ← ENE
    assert meses[1] is None


def test_sugerir_pdu_rack():
    cat = catalogo_vigente()
    assert sugerir_pdu_rack(cat.bateria("High Voltage 16 kWh min 5 bat"), 10) == (1, 1)
    assert sugerir_pdu_rack(cat.bateria("High Voltage 16 kWh min 5 bat"), 17) == (2, 2)
    assert sugerir_pdu_rack(cat.bateria("High Voltage 7,68 kWh min 7 bat"), 14) == (1, 2)
    assert sugerir_pdu_rack(cat.bateria("High Voltage 12,03 kWh min 5 bat"), 5) == (1, 0)
    assert sugerir_pdu_rack(cat.bateria("Low Voltage 16 kWh"), 4) == (0, 0)
