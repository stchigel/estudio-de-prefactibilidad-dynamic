"""Generación del PowerPoint (§10.2)."""

import io
from dataclasses import replace

import pytest
from PIL import Image
from pptx import Presentation

from casos.definiciones import plecor
from exportes.powerpoint import DIAPOSITIVAS, DatosPpt, OpcionPpt, generar_ppt, numero
from motor import calcular
from motor.modelos import Capacitores, Financiacion, OrigenConsumo
from motor.opciones import buscar_opciones

TITULOS_BASE = [
    "Estudio de", "EL OBJETIVO", "EL DIAGNÓSTICO", "LA SOLUCIÓN", "ARQUITECTURA DEL SISTEMA", "PREVISIBILIDAD",
    "EL CASO DE NEGOCIO", "RETORNO Y PROYECCIÓN", "FINANCIAMIENTO", "BENEFICIOS FISCALES", "IMPACTO AMBIENTAL",
    "POSICIONAMIENTO", "TRACK RECORD", "SIGUIENTES PASOS",
]


def _formas(contenedor):
    for f in contenedor.shapes:
        yield f
        if f.shape_type == 6:
            yield from _formas(f)


def _textos(prs) -> list[str]:
    textos = []
    for slide in prs.slides:
        partes = []
        for f in _formas(slide):
            if f.has_text_frame:
                partes.append(f.text_frame.text)
            if getattr(f, "has_table", False) and f.has_table:
                partes += [c.text for fila in f.table.rows for c in fila.cells]
        textos.append("\n".join(partes))
    return textos


def _generar(datos: DatosPpt):
    prs = Presentation(io.BytesIO(generar_ppt(datos)))
    return prs, _textos(prs)


def _titulo(texto: str) -> str:
    return next(t for t in TITULOS_BASE if t in texto)


@pytest.fixture(scope="module")
def simple():
    e = plecor()
    return e, calcular(e)


def test_no_quedan_marcas(simple):
    e, r = simple
    _, textos = _generar(DatosPpt(e, r))
    for i, t in enumerate(textos, 1):
        assert "{{" not in t and "[[si:" not in t, f"diapositiva {i}"


def test_diapositivas_condicionales(simple):
    e, r = simple
    prs, textos = _generar(DatosPpt(e, r))  # PLECOR: financia 80 %, 1 opción, sin bancaria
    assert len(prs.slides) == 14
    assert [_titulo(t) for t in textos] == TITULOS_BASE
    assert "Bancaria" not in "\n".join(textos)

    sin_fin = replace(e, financiacion=Financiacion())
    prs, _ = _generar(DatosPpt(sin_fin, calcular(sin_fin)))
    assert len(prs.slides) == 13

    prs, textos = _generar(DatosPpt(e, r, texto_bancario="CFI: hasta 60 meses"))
    assert len(prs.slides) == 15 and any("CFI: hasta 60 meses" in t for t in textos)


def test_numeros_del_proyecto(simple):
    e, r = simple
    _, textos = _generar(DatosPpt(e, r))
    portada, numeros, retorno, huella = textos[0], textos[6], textos[7], textos[10]
    assert "N° 12508" in portada and "25/09/2026" in portada and "ON-GRID LLAVE EN MANO" in portada
    assert "Los Números del Proyecto" in numeros
    assert numero(r.inversion.total_usd) in numeros and "139" in numeros
    assert "menos de 5 Años" in retorno  # ROI 4,33
    assert "Año 4,33" in retorno and "menos de 52 meses" in retorno and "20 años de ahorro neto" in retorno
    assert numero(r.energia.generacion_anual_kwh) in huella


def test_parrafos_condicionales(simple):
    e, r = simple
    _, textos = _generar(DatosPpt(e, r))
    assert "factor de potencia" not in textos[2]  # sin banco de capacitores
    assert "meses no" not in textos[1]  # sin meses estimados
    c = list(e.consumos)
    c[1] = replace(c[1], origen=OrigenConsumo.ESTIMADO)
    con = replace(e, banco_capacitores=True, capacitores=Capacitores(40, 3500, 1_000_000), consumos=c)
    _, textos = _generar(DatosPpt(con, calcular(con)))
    assert "factor de potencia" in textos[2]
    assert "meses no" in textos[1] and "35.467 *" in textos[1]


def test_graficos_nativos(simple):
    e, r = simple
    prs, _ = _generar(DatosPpt(e, r))
    graficos = {f.name: f.chart for s in prs.slides for f in _formas(s) if getattr(f, "has_chart", False) and f.has_chart}
    roi = list(graficos["GRAFICO:roi"].plots[0].series[0].values)
    assert len(roi) == r.anios_curva_roi == 10  # ROI 4,33 → ROI + 5 años, no 15 fijos
    assert roi == pytest.approx(r.curva_roi[: r.anios_curva_roi])
    # Financiación por semestre (14) con el ahorro acumulado como línea sobre las barras.
    plots = graficos["GRAFICO:financiacion"].plots
    barras, linea = plots[0].series, plots[1].series
    assert list(barras[0].values) == pytest.approx(r.financiacion.pagos_semestrales)
    assert list(barras[1].values) == pytest.approx(r.financiacion.ahorros_semestrales)
    assert list(linea[0].values) == pytest.approx(r.financiacion.ahorro_acumulado_semestral)
    assert len(barras[0].values) == 14 and len(plots) == 2


def test_tabla_de_opciones():
    e = plecor()
    b = buscar_opciones(e)
    opciones = [OpcionPpt(o.kit1, o.kit2, o.recomendada, o.resultado) for o in b.opciones]
    rec = next(o for o in opciones if o.recomendada)
    prs, textos = _generar(DatosPpt(replace(e, kit1=rec.kit1, kit2=rec.kit2), rec.resultado, opciones))
    assert len(prs.slides) == 15
    tabla = next(f.table for s in prs.slides for f in _formas(s) if f.name == "TABLA:opciones")
    filas = list(tabla.rows)
    assert len(filas) == 1 + len(opciones)
    resaltadas = [i for i, fila in enumerate(filas[1:]) if fila.cells[0].text_frame.paragraphs[0].runs[0].font.bold]
    assert resaltadas == [opciones.index(rec)]
    assert "Opción Recomendada" in textos[7]


def test_imagenes(simple):
    e, r = simple
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "red").save(buf, "PNG")
    sin, _ = _generar(DatosPpt(e, r))
    con, _ = _generar(DatosPpt(e, r, imagenes={"logo": buf.getvalue(), "planta": buf.getvalue()}))

    def imagenes(prs, i):
        return sum(1 for f in _formas(prs.slides[i]) if f.shape_type == 13)

    assert imagenes(con, 0) == imagenes(sin, 0) + 1
    assert imagenes(con, 1) == imagenes(sin, 1) + 1
    assert not any(f.name == "IMG:logo" for f in _formas(con.slides[0]))  # el rótulo se reemplaza
    assert any(f.name == "IMG:logo" for f in _formas(sin.slides[0]))  # sin imagen queda el marcador


def test_el_grafico_roi_se_adapta_a_cada_caso():
    from motor.calculo import anios_curva_roi

    assert anios_curva_roi(1.2) == 8  # mínimo
    assert anios_curva_roi(4.33) == 10
    assert anios_curva_roi(9.5) == 15
    assert anios_curva_roi(22.0) == 25  # tope: la vida útil
    assert anios_curva_roi(None) == 15  # sin repago


def test_selector_de_paginas(simple):
    e, r = simple
    prs, textos = _generar(DatosPpt(e, r, diapositivas_excluidas=frozenset({6, 12, 14})))
    assert len(prs.slides) == 11
    todo = "\n".join(textos)
    for ausente in ("PREVISIBILIDAD", "BENEFICIOS FISCALES", "POSICIONAMIENTO"):
        assert ausente not in todo
    assert "IMPACTO AMBIENTAL" in todo


def test_el_selector_cubre_las_diapositivas_de_la_plantilla():
    from pptx import Presentation as P
    from exportes.powerpoint import PLANTILLA

    assert [d.numero for d in DIAPOSITIVAS] == list(range(1, len(P(PLANTILLA).slides) + 1))


def test_diapositiva_condicional_desactivada_no_se_genera(simple):
    e, r = simple
    prs, textos = _generar(DatosPpt(e, r, diapositivas_excluidas=frozenset({10})))  # financiamiento propio
    assert len(prs.slides) == 13 and "FINANCIAMIENTO" not in "\n".join(textos)


def test_bloque_cfi_con_varias_lineas(simple):
    e, r = simple
    cfi = "Plazos hasta 60 meses con 1 año de gracia\n1% de gastos administrativos\nHasta el 80% de la inversión"
    prs, textos = _generar(DatosPpt(e, r, texto_cfi=cfi))
    financiamiento = textos[8]
    assert "CFI" in financiamiento
    assert all(linea in financiamiento for linea in cfi.splitlines())
    assert "{{" not in financiamiento

    prs, textos = _generar(DatosPpt(e, r))  # sin texto CFI el bloque se oculta
    assert "CFI" not in textos[8]


def test_texto_de_financiacion_con_plazo_total_y_gracia(simple):
    e, r = simple  # PLECOR: 80 %, plazo 4 con 1 de gracia en la definición del caso
    fin = replace(e, financiacion=Financiacion(0.8, plazo_anios=5, gracia_anios=1, tasa=0.02, gastos_adm=0.01))
    _, textos = _generar(DatosPpt(fin, calcular(fin)))
    t = textos[8]
    assert "5 años (4 años de capital más intereses y 1 año de gracia, solo intereses)" in t
    assert "1 año de solo intereses y 48 cuotas mensuales" in t
    assert "5 años en USD" in t


def test_tabla_de_opciones_con_las_tildadas():
    e = plecor()
    b = buscar_opciones(e)
    assert len(b.opciones) > 6  # más filas que las de la plantilla: la tabla se achica
    opciones = [OpcionPpt(o.kit1, o.kit2, o.recomendada, o.resultado) for o in b.opciones]
    prs, textos = _generar(DatosPpt(e, opciones[-1].resultado, opciones))
    tabla = next(f.table for s in prs.slides for f in _formas(s) if f.name == "TABLA:opciones")
    assert len(list(tabla.rows)) == 1 + len(opciones)
    assert 2_473_575 + sum(f.height for f in tabla.rows) < 5_620_231  # no pisa la nota al pie (Text 12)
    # Combinaciones de igual potencia se distinguen por sus kits.
    potencias = [round(o.resultado.kwp_total, 1) for o in opciones]
    repetida = next(p for p in potencias if potencias.count(p) > 1)
    assert any(f"{repetida:.1f}".replace(".", ",") + " (" in c.text for fila in tabla.rows for c in fila.cells)


def test_la_tabla_resalta_la_elegida_y_no_la_recomendada():
    e = plecor()
    b = buscar_opciones(e)
    opciones = [OpcionPpt(o.kit1, o.kit2, o.recomendada, o.resultado) for o in b.opciones]
    elegida = next(o for o in opciones if not o.recomendada)
    prs, textos = _generar(DatosPpt(replace(e, kit1=elegida.kit1, kit2=elegida.kit2), elegida.resultado, opciones))
    tabla = next(f.table for s in prs.slides for f in _formas(s) if f.name == "TABLA:opciones")
    filas = list(tabla.rows)[1:]
    resaltadas = [i for i, fila in enumerate(filas) if fila.cells[0].text_frame.paragraphs[0].runs[0].font.bold]
    assert resaltadas == [opciones.index(elegida)]
    todo = "\n".join(textos)
    assert "Opción Elegida" in todo and "Se marca la opción elegida" in todo and "{{" not in todo
