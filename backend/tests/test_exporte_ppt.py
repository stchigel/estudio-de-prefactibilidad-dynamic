"""Generación del PowerPoint (§10.2)."""

import io
from dataclasses import replace

import pytest
from PIL import Image
from pptx import Presentation

from casos.definiciones import plecor
from exportes.powerpoint import DatosPpt, OpcionPpt, generar_ppt, numero
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
    assert roi == pytest.approx(r.curva_roi[:15])
    fin = graficos["GRAFICO:financiacion"].plots[0].series
    assert list(fin[0].values) == pytest.approx(r.financiacion.pagos)
    assert list(fin[1].values) == pytest.approx(r.financiacion.ahorros)


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
