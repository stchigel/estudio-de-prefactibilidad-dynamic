from dataclasses import replace

from casos.definiciones import plecor
from motor.opciones import Candidata, ConfigBusqueda, _ordenar, _seleccionar, _seleccionar_priorizando_sistema_unico, buscar_opciones, combinaciones
from motor import catalogo_vigente
from motor.modelos import Kit


def _cand(roi, cob):
    return Candidata(Kit(11.02), None, 11.02, cob, 0, 0, 0, 0, roi)


def test_desempate_por_cobertura_dentro_de_tolerancia():
    a, b, c = _cand(4.0, 0.2), _cand(4.15, 0.5), _cand(4.3, 0.9)
    assert _ordenar([a, b, c], 0.2) == [b, a, c]


def test_sin_empate_gana_menor_roi():
    a, b = _cand(4.0, 0.2), _cand(4.25, 0.5)
    assert _ordenar([b, a], 0.2)[0] is a


def test_combinaciones_respetan_tope_y_orden_de_kits():
    combos = combinaciones(plecor(), catalogo_vigente(), 60)
    assert combos
    for k1, k2 in combos:
        total = k1.kwp * k1.cantidad + (k2.kwp * k2.cantidad if k2 else 0)
        assert total <= 60
        if k2:
            assert k1.kwp > k2.kwp


def test_busqueda_plecor():
    r = buscar_opciones(plecor())
    assert 5 <= len(r.opciones) <= 9  # 5 tamaños, con hasta 2 combinaciones por tamaño
    assert sum(o.recomendada for o in r.opciones) == 1
    coberturas = [o.resultado.energia.cobertura for o in r.opciones]
    assert coberturas == sorted(coberturas)
    for o in r.opciones:
        assert o.resultado.kwp_total <= 280
        x = o.resultado.energia
        assert x.desperdiciada_kwh / x.generacion_anual_kwh <= ConfigBusqueda().max_desperdicio_inhibido
    recomendada = next(o for o in r.opciones if o.recomendada).resultado
    mejor_roi = min(o.resultado.roi_anios for o in r.opciones)
    assert recomendada.roi_anios - mejor_roi < 0.2


def test_respeta_superficie_disponible():
    r = buscar_opciones(replace(plecor(), m2_disponibles=400))
    assert r.opciones
    assert all(o.resultado.superficie_m2 <= 400 for o in r.opciones)


def test_limitado_por_potencia_contratada():
    e = replace(plecor(), inhibicion_inyeccion=False, potencia_contratada_kw=40)
    r = buscar_opciones(e)
    assert r.limitado_por_potencia
    assert all(o.resultado.kwp_total <= 40 for o in r.opciones)


def test_sin_potencia_contratada_limita_por_cobertura():
    r = buscar_opciones(replace(plecor(), potencia_contratada_kw=0, inhibicion_inyeccion=False))
    assert r.opciones
    assert all(o.resultado.energia.cobertura <= 1.0 for o in r.opciones)


def _c(kwp, roi, cob=None, n=1):
    return Candidata(Kit(kwp / n, n), None, kwp, cob if cob is not None else kwp / 300, 0, 0, 0, 0, roi)


def test_recomendada_con_dos_tamanos_menores_y_dos_mayores():
    cands = [_c(k, 4.0 + abs(k - 100) / 100) for k in (20, 40, 60, 80, 100, 120, 140, 160, 180, 200)]
    orden = _ordenar(cands, 0.2)
    elegidas = _seleccionar(orden, ConfigBusqueda())
    assert sorted(c.kwp for c in elegidas) == [60, 80, 100, 120, 140]
    assert orden[0].kwp == 100


def test_si_de_un_lado_no_hay_se_completa_con_el_otro():
    cands = [_c(k, 4.0) for k in (50, 100, 150, 200, 250, 300)]
    orden = _ordenar(cands, 0.2)
    elegidas = _seleccionar(orden, ConfigBusqueda())
    assert len(elegidas) == 5 and orden[0] in elegidas


def test_empate_de_roi_muestra_las_dos_combinaciones():
    """2 x 55,68 y 1 x 110,2: ROI a menos de 0,2 años: se muestran las dos."""
    dos_de_55 = _c(111.36, 4.00, cob=0.40, n=2)
    una_de_110 = _c(110.2, 4.10, cob=0.39)
    otras = [_c(k, 4.5) for k in (60, 85, 140, 170)]
    orden = _ordenar([dos_de_55, una_de_110, *otras], 0.2)
    assert orden[0] is dos_de_55
    elegidas = _seleccionar(orden, ConfigBusqueda())
    assert dos_de_55 in elegidas and una_de_110 in elegidas


def test_si_la_segunda_combinacion_tiene_peor_roi_no_se_muestra():
    a, b = _c(111.36, 4.0, n=2), _c(110.2, 4.6)
    elegidas = _seleccionar(_ordenar([a, b], 0.2), ConfigBusqueda())
    assert elegidas == [a]


# ----------------------------------------------- prioridad a los sistemas de un solo inversor


def _elegir(candidatas):
    return _seleccionar_priorizando_sistema_unico(_ordenar(candidatas, 0.2), ConfigBusqueda())


def test_un_inversor_gana_a_dos_aunque_el_roi_sea_peor():
    """1 x 110,2 antes que 2 x 55,68 aun con ROI bastante peor; la de dos inversores también se muestra."""
    dos_de_55 = _c(111.36, 3.5, cob=0.40, n=2)
    una_de_110 = _c(110.2, 4.6, cob=0.39)
    otras = [_c(k, 5.0) for k in (60, 85, 140, 170)]
    ranking, elegidas = _elegir([dos_de_55, una_de_110, *otras])
    assert ranking[0] is una_de_110
    assert dos_de_55 in elegidas and una_de_110 in elegidas


def test_si_el_tamano_igual_no_tiene_un_inversor_sube_al_unico_mayor_que_entra():
    """2 x 22 (44 kWp) y no hay 1 x 44: se prefiere el de 55 si es válido."""
    dos_de_22 = _c(44.0, 3.5, n=2)
    una_de_55 = _c(55.68, 4.4)
    una_de_88 = _c(88.16, 4.8)
    ranking, elegidas = _elegir([dos_de_22, una_de_55, una_de_88])
    assert ranking[0] is una_de_55
    assert dos_de_22 in elegidas


def test_si_ningun_un_inversor_alcanza_se_mantiene_la_de_varios():
    dos_de_55 = _c(111.36, 3.5, n=2)
    una_chica = _c(55.68, 3.6)  # un solo inversor, pero más chica que la recomendada
    ranking, _ = _elegir([dos_de_55, una_chica])
    assert ranking[0] is dos_de_55


def test_dos_kits_distintos_cuentan_como_dos_inversores():
    mixta = Candidata(Kit(88.16), Kit(22.04), 110.2, 0.4, 0, 0, 0, 0, 3.5)
    una_de_110 = _c(110.2, 4.2)
    ranking, elegidas = _elegir([mixta, una_de_110])
    assert ranking[0] is una_de_110 and mixta in elegidas


def test_si_la_recomendada_ya_es_de_un_inversor_no_cambia():
    una, dos = _c(110.2, 3.5), _c(111.36, 4.5, n=2)
    ranking, elegidas = _elegir([una, dos])
    assert ranking[0] is una and elegidas == [una]


def test_la_recomendada_de_la_busqueda_es_de_un_solo_inversor():
    r = buscar_opciones(plecor())
    rec = next(o for o in r.opciones if o.recomendada)
    assert rec.kit2 is None and rec.kit1.cantidad == 1
