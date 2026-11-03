from dataclasses import replace

from casos.definiciones import plecor
from motor.opciones import Candidata, ConfigBusqueda, _ordenar, buscar_opciones, combinaciones
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
    assert 1 <= len(r.opciones) <= 5
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
