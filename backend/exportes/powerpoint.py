"""Generación de la presentación de la propuesta (§10.2).

Completa la plantilla con marcas (exportes/plantillas/prefactibilidad.pptx, ver
scripts/preparar_plantilla_ppt.py) conservando el diseño: textos, tablas,
gráficos nativos, imágenes y diapositivas condicionales.
"""

from __future__ import annotations

import copy
import io
import math
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.util import Cm, Emu, Pt

from motor.catalogo import catalogo_vigente
from motor.modelos import Entradas, HorarioTrabajo, Kit, Moneda, OrigenConsumo, OrigenSuperficie, Resultado, TipoInversor

PLANTILLA = Path(__file__).parent / "plantillas" / "prefactibilidad.pptx"
NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
MARCA = re.compile(r"\{\{(\w+)\}\}")
CONDICION = re.compile(r"^\[\[si:(\w+)\]\]")
ANIOS_VIDA_UTIL = 25
RESALTADO_RECOMENDADA = RGBColor(0xFD, 0xE4, 0xE4)  # rojo muy claro, acorde a la marca
# Párrafos condicionales que se vacían en lugar de quitarse, para no desalinear íconos.
VACIAR_EN_LUGAR_DE_QUITAR = {"capacitores"}


@dataclass(frozen=True)
class Diapositiva:
    numero: int  # posición en la plantilla (desde 1)
    titulo: str
    condicion: str | None = None  # clave de _condiciones: sin ella la diapositiva se omite sola
    nota: str = ""


# Selector de páginas: se puede desactivar cualquiera. Las condicionales, además, se omiten
# si no corresponden aunque estén activadas.
DIAPOSITIVAS = (
    Diapositiva(1, "Portada"),
    Diapositiva(2, "El objetivo"),
    Diapositiva(3, "La oportunidad detectada"),
    Diapositiva(4, "La solución"),
    Diapositiva(5, "Arquitectura del sistema"),
    Diapositiva(6, "Previsibilidad"),
    Diapositiva(7, "Opciones propuestas", "opciones", "Solo si hay más de una opción"),
    Diapositiva(8, "Los números del proyecto"),
    Diapositiva(9, "Retorno de la inversión"),
    Diapositiva(10, "Financiamiento propio", "financiacion", "Solo si se financia un porcentaje"),
    Diapositiva(11, "Financiamiento bancario", "bancaria", "Solo si se completa el texto bancario"),
    Diapositiva(12, "Beneficios fiscales"),
    Diapositiva(13, "Impacto ambiental"),
    Diapositiva(14, "Posicionamiento"),
    Diapositiva(15, "Track record"),
    Diapositiva(16, "Siguientes pasos"),
)
DIAPOSITIVA_OPCIONES = 7


@dataclass
class OpcionPpt:
    kit1: Kit
    kit2: Kit | None
    recomendada: bool
    resultado: Resultado


@dataclass
class DatosPpt:
    entradas: Entradas
    resultado: Resultado  # opción elegida
    opciones: list[OpcionPpt] = field(default_factory=list)  # tabla de la diapositiva 7
    limitado_por_potencia: bool = False
    texto_bancario: str | None = None  # diapositiva 11 (opcional)
    texto_cfi: str | None = None  # bloque CFI de la diapositiva 10 (vacío = sin bloque)
    diapositivas_excluidas: frozenset[int] = frozenset()  # números de DIAPOSITIVAS desactivadas
    imagenes: dict[str, bytes] = field(default_factory=dict)  # logo, planta, montaje


# ------------------------------------------------------------------ formato es-AR


def numero(v: float | None, decimales: int = 0) -> str:
    if v is None:
        return "—"
    texto = f"{v:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def compacto(v: float | None) -> str:
    """Un decimal si hace falta (33,6) y ninguno si es entero o grande (139)."""
    if v is None:
        return "—"
    return numero(v, 0) if v >= 100 or float(v).is_integer() else numero(v, 1).rstrip("0").rstrip(",")


def porcentaje(v: float | None, decimales: int = 0) -> str:
    return "—" if v is None else numero(v * 100, decimales)


def anios(n: int) -> str:
    return f"{n} año{'s' if n != 1 else ''}"


HORARIOS = {
    HorarioTrabajo.SIETE_X_24: "Todos los días, las 24 h",
    HorarioTrabajo.LU_A_VI: "Lunes a viernes",
    HorarioTrabajo.LU_A_SA: "Lunes a sábado",
    HorarioTrabajo.LU_A_MEDIO_SA: "Lunes a viernes y sábado medio día",
}

SOLUCION = {
    TipoInversor.ON_GRID: (
        "Los paneles abastecen los consumos de la planta durante el día.",
        "El inversor sincroniza la energía solar con la red interna y prioriza el autoconsumo.",
        "De noche opera con red normal; el excedente diurno puede inyectarse a la red.",
    ),
    TipoInversor.HIBRIDO: (
        "Los paneles abastecen los consumos de la planta durante el día y el eventual excedente se almacena en baterías.",
        "El inversor sincroniza la energía solar con la red interna y, cuando la generación solar es insuficiente, "
        "descarga las baterías priorizando el autoconsumo.",
        "De noche opera con red normal y/o baterías; el excedente diurno puede inyectarse a la red.",
    ),
}


def tipo_sistema(e: Entradas) -> str:
    return "ON-GRID" if e.tipo_inversor == TipoInversor.ON_GRID else "HÍBRIDO"


def _valores(d: DatosPpt) -> dict[str, str]:
    e, r = d.entradas, d.resultado
    f = e.financiacion
    roi = r.roi_anios
    dolares = f.moneda == Moneda.DOLARES

    if e.m2_disponibles is not None:
        superficie = f"{numero(e.m2_disponibles)} m² de techo disponible"
        # Una sola línea: la plantilla alinea con tabulaciones y un salto perdería la sangría.
        detalle_superficie = {
            OrigenSuperficie.CLIENTE: "Superficie informada por el cliente",
            OrigenSuperficie.DYNAMIC: "Superficie relevada por Dynamic",
        }.get(e.origen_m2, "Superficie útil sobre las naves existentes")
    else:
        superficie = f"{numero(r.superficie_m2)} m² de techo requeridos"
        detalle_superficie = "Estimada para el sistema propuesto"

    amortizacion = max(f.plazo_anios - f.gracia_anios, 0)
    # El plazo es el total: 5 años con 1 de gracia = 4 años de capital más intereses y 1 de solo intereses.
    gracia = ""
    if f.gracia_anios:
        gracia = f" ({anios(amortizacion)} de capital más intereses y {anios(f.gracia_anios)} de gracia, solo intereses)"
    gastos = f" + {numero(f.gastos_adm * 100, 1).rstrip('0').rstrip(',')}% de gastos" if f.gastos_adm else ""
    tasa = numero(f.tasa * 100, 2).rstrip("0").rstrip(",")

    elegida = next((o for o in d.opciones if o.resultado is r), None)
    if len(d.opciones) > 1:
        titulo_numeros = " de la Opción Recomendada" if elegida is None or elegida.recomendada else " de la Opción Elegida"
    else:
        titulo_numeros = " del Proyecto"

    tarifa = e.tarifa + (f" ({e.distribuidora})" if e.distribuidora else "")
    horario = HORARIOS[e.horario_trabajo]
    if e.horario_trabajo != HorarioTrabajo.SIETE_X_24:
        horario += f" · {e.horas_por_dia} h por día"

    arquitectura = (
        f"El sistema arranca dimensionado para cubrir el {porcentaje(r.energia.cobertura)}% de la demanda energética "
        f"actual{' (limitado por la potencia contratada)' if d.limitado_por_potencia else ''}, destinando al "
        f"autoconsumo el {porcentaje(r.energia.autoconsumo_pct)}% de lo generado, pero su arquitectura permite crecer "
        "por módulos a medida que aumenta la demanda — sin rehacer la instalación."
    )

    return {
        "tipo_sistema": tipo_sistema(e),
        "numero": str(e.numero_propuesta) if e.numero_propuesta else "—",
        "fecha": (e.fecha or date.today()).strftime("%d/%m/%Y"),
        "cliente": e.cliente,
        "horario": horario,
        "inyeccion": "NO (inhibida)" if e.inhibicion_inyeccion else "SI",
        "consumo_anual": numero(r.energia.consumo_anual_kwh),
        "potencia_contratada": numero(e.potencia_contratada_kw),
        "tarifa": tarifa,
        "texto_superficie": superficie,
        "detalle_superficie": detalle_superficie,
        "solucion_1": SOLUCION[e.tipo_inversor][0],
        "solucion_2": SOLUCION[e.tipo_inversor][1],
        "solucion_3": SOLUCION[e.tipo_inversor][2],
        "texto_arquitectura": arquitectura,
        "kwp_fase1": compacto(r.kwp_total),
        "titulo_numeros": titulo_numeros,
        "kwp": compacto(r.kwp_total),
        "inversion": numero(r.inversion.total_usd),
        "generacion": numero(r.energia.generacion_anual_kwh),
        "autoconsumo": porcentaje(r.energia.autoconsumo_pct),
        "cobertura": porcentaje(r.energia.cobertura),
        "superficie": numero(r.superficie_m2),
        "ahorro": numero(r.economia.ahorro_anual_usd),
        "roi": numero(roi, 1),
        "tir": porcentaje(r.van_tir.tir, 1),
        "roi_techo": str(math.floor(roi) + 1) if roi is not None else "—",
        "roi_decimal": numero(roi, 2),
        "roi_meses": str(math.ceil(roi * 12)) if roi is not None else "—",
        "anios_ahorro_neto": str(max(0, math.floor(ANIOS_VIDA_UTIL - roi))) if roi is not None else "—",
        "titulo_financiacion": f"Propia en {'Dólares' if dolares else 'Pesos'} a Tasa {tasa}%",
        "texto_financiacion": (
            f"Financiación propia en {'USD' if dolares else 'pesos'}, sin bancos: el {porcentaje(f.porcentaje)}% de la inversión "
            f"(USD {numero(r.financiacion.monto_financiado)}) a {f.plazo_anios} años{gracia}, tasa {tasa}% anual{gastos}. "
            "El ahorro empieza a trabajar a favor desde el día uno."
        ),
        "financiacion_cuotas": f"{f.plazo_anios} años en {'USD' if dolares else 'pesos'}",
        "financiacion_detalle": (
            f"Anticipo del {porcentaje(1 - f.porcentaje)}% + saldo: "
            + (f"{anios(f.gracia_anios)} de solo intereses y " if f.gracia_anios else "")
            + f"{12 * amortizacion} cuotas mensuales."
        ),
        "moneda_texto": "dólares" if dolares else "pesos",
        "texto_bancario": d.texto_bancario or "",
        "texto_cfi": (d.texto_cfi or "").strip(),
        "tco2_anio": compacto(r.huella.tco2_anio),
        "tco2_25": numero(r.huella.tco2_25_anios),
        "arboles": numero(r.huella.arboles),
        "autos": numero(r.huella.autos),
    }


def _condiciones(d: DatosPpt) -> dict[str, bool]:
    return {
        "opciones": len(d.opciones) > 1,
        "financiacion": d.entradas.financiacion.porcentaje > 0,
        "bancaria": bool(d.texto_bancario and d.texto_bancario.strip()),
        "cfi": bool(d.texto_cfi and d.texto_cfi.strip()),
        "capacitores": d.entradas.banco_capacitores,
        "meses_estimados": any(c.origen == OrigenConsumo.ESTIMADO for c in d.entradas.consumos),
    }


# ------------------------------------------------------------------ utilidades de pptx


def _formas(contenedor):
    for f in list(contenedor.shapes):
        yield f
        if f.shape_type == 6:
            yield from _formas(f)


def _buscar(slide, nombre: str):
    return next((f for f in _formas(slide) if f.name == nombre), None)


def _eliminar_forma(f) -> None:
    f._element.getparent().remove(f._element)


def _eliminar_diapositiva(prs, slide) -> None:
    lista = prs.slides._sldIdLst
    for sld_id in list(lista):
        if prs.part.related_part(sld_id.rId) is slide.part:
            prs.part.drop_rel(sld_id.rId)
            lista.remove(sld_id)
            return


def _parrafos(slide):
    for f in _formas(slide):
        if f.has_text_frame:
            yield from f.text_frame.paragraphs
        if getattr(f, "has_table", False) and f.has_table:
            for fila in f.table.rows:
                for celda in fila.cells:
                    yield from celda.text_frame.paragraphs


def _completar_textos(slide, valores: dict[str, str], condiciones: dict[str, bool]) -> None:
    for parrafo in list(_parrafos(slide)):
        runs = parrafo.runs
        if not runs:
            continue
        m = CONDICION.match(runs[0].text)
        if m:
            runs[0].text = runs[0].text[m.end() :]
            if not condiciones[m.group(1)]:
                if m.group(1) in VACIAR_EN_LUGAR_DE_QUITAR:
                    for r in runs:
                        r.text = ""
                else:
                    parrafo._p.getparent().remove(parrafo._p)
                continue
        for i, r in enumerate(runs):
            if "{{" in r.text:
                r.text = MARCA.sub(lambda x: valores[x.group(1)], r.text)
                if "\n" in r.text:
                    _desdoblar_parrafo(parrafo, i)


def _desdoblar_parrafo(parrafo, indice_run: int) -> None:
    """Un valor con saltos de línea ocupa un párrafo por línea, con el formato del original."""
    lineas = parrafo.runs[indice_run].text.split("\n")
    parrafo.runs[indice_run].text = lineas[0]
    ancla = parrafo._p
    for linea in lineas[1:]:
        copia = copy.deepcopy(parrafo._p)
        runs = copia.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}r")
        for j, run in enumerate(runs):
            run.find("{http://schemas.openxmlformats.org/drawingml/2006/main}t").text = linea if j == indice_run else ""
        ancla.addnext(copia)
        ancla = copia


def _poner_texto_celda(celda, texto: str, negrita: bool | None = None) -> None:
    parrafo = celda.text_frame.paragraphs[0]
    for p in celda.text_frame.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    runs = parrafo.runs
    if not runs:
        runs = [parrafo.add_run()]
    runs[0].text = texto
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    if negrita is not None:
        runs[0].font.bold = negrita


# ------------------------------------------------------------------ elementos


def _tabla_opciones(slide, d: DatosPpt) -> None:
    f = _buscar(slide, "TABLA:opciones")
    if f is None:
        return
    tabla = f.table
    filas = list(tabla.rows)
    plantilla_fila = filas[1]._tr
    for fila in filas[1:]:
        fila._tr.getparent().remove(fila._tr)
    for o in d.opciones:
        tr = copy.deepcopy(plantilla_fila)
        tabla._tbl.append(tr)
    capacidad_bat = 0.0
    if d.entradas.baterias_activas:
        capacidad_bat = catalogo_vigente().bateria(d.entradas.baterias.modelo).kwh * d.entradas.baterias.cantidad
    for fila, o in zip(list(tabla.rows)[1:], d.opciones):
        r = o.resultado
        valores = [
            tipo_sistema(d.entradas).replace("-", " "),
            numero(r.kwp_total, 1),
            numero(capacidad_bat) if capacidad_bat else "--------",
            numero(r.energia.generacion_anual_kwh),
            porcentaje(r.energia.cobertura),
            porcentaje(r.energia.autoconsumo_pct),
            numero(r.inversion.total_usd),
            numero(r.economia.ahorro_anual_usd),
            numero(r.roi_anios, 1),
            porcentaje(r.van_tir.tir, 1),
            numero(r.superficie_m2),
        ]
        for celda, valor in zip(fila.cells, valores):
            _poner_texto_celda(celda, valor, negrita=o.recomendada)
            if o.recomendada:
                celda.fill.solid()
                celda.fill.fore_color.rgb = RESALTADO_RECOMENDADA


def _tabla_consumos(slide, d: DatosPpt) -> None:
    caja = _buscar(slide, "TABLA:consumos")
    if caja is None:
        return
    etiqueta = _buscar(slide, "ETIQUETA:consumos")
    if etiqueta is not None:
        _eliminar_forma(etiqueta)
    meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    margen = Cm(0.4)
    forma = slide.shapes.add_table(
        7, 4, caja.left + margen, caja.top + margen, caja.width - 2 * margen, caja.height - 2 * margen
    )
    tabla = forma.table
    # Sin estilo de tabla: solo texto sobre la caja de la plantilla.
    tbl_pr = tabla._tbl.tblPr
    for hijo in list(tbl_pr):
        tbl_pr.remove(hijo)
    etree.SubElement(tbl_pr, "{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId").text = (
        "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    )
    tbl_pr.set("firstRow", "1")
    encabezado = ["Mes", "kWh", "Mes", "kWh"]
    for c, texto in enumerate(encabezado):
        _poner_texto_celda(tabla.cell(0, c), texto, negrita=True)
    for i, consumo in enumerate(d.entradas.consumos):
        fila, col = 1 + i % 6, 0 if i < 6 else 2
        marca = " *" if consumo.origen == OrigenConsumo.ESTIMADO else ""
        _poner_texto_celda(tabla.cell(fila, col), meses[i], negrita=False)
        _poner_texto_celda(tabla.cell(fila, col + 1), numero(consumo.total) + marca, negrita=False)
    for fila in tabla.rows:
        for celda in fila.cells:
            celda.margin_top = celda.margin_bottom = Cm(0.05)
            for p in celda.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(11)


def _grafico_roi(slide, d: DatosPpt) -> None:
    f = _buscar(slide, "GRAFICO:roi")
    if f is None:
        return
    curva = d.resultado.curva_roi[: d.resultado.anios_curva_roi]  # dinámico según el ROI de cada caso
    datos = CategoryChartData()
    datos.categories = [str(i) for i in range(1, len(curva) + 1)]
    datos.add_series("Capital", curva)
    grafico = f.chart
    grafico.replace_data(datos)
    # Barras negativas en rojo: se rehacen los puntos con color propio.
    ser = grafico._chartSpace.find(f".//{{{NS_C}}}ser")
    puntos = ser.findall(f"{{{NS_C}}}dPt")
    rojo = next((p for p in puntos if p.find(".//{*}srgbClr") is not None and p.find(".//{*}srgbClr").get("val") == "FF0000"), None)
    for p in puntos:
        ser.remove(p)
    if rojo is None:
        return
    ancla = ser.find(f"{{{NS_C}}}invertIfNegative")
    for i, v in reversed(list(enumerate(curva))):
        if v < 0:
            nuevo = copy.deepcopy(rojo)
            nuevo.find(f"{{{NS_C}}}idx").set("val", str(i))
            ancla.addnext(nuevo)


def _grafico_financiacion(slide, d: DatosPpt) -> None:
    f = _buscar(slide, "GRAFICO:financiacion")
    if f is None:
        return
    fin = d.resultado.financiacion
    moneda = "dólares" if d.entradas.financiacion.moneda == Moneda.DOLARES else "pesos"
    datos = CategoryChartData()
    datos.categories = [f"año{i}" for i in range(1, len(fin.pagos) + 1)]
    datos.add_series(f"Pagos en {moneda}", fin.pagos)
    datos.add_series(f"Ahorros en {moneda}", fin.ahorros)
    f.chart.replace_data(datos)


def _imagen(slide, nombre: str, contenido: bytes | None) -> None:
    caja = _buscar(slide, f"IMG:{nombre}")
    if caja is None or not contenido:
        return  # sin imagen queda el marcador (§10.2)
    with Image.open(io.BytesIO(contenido)) as img:
        ancho_img, alto_img = img.size
    left, top, ancho, alto = caja.left, caja.top, caja.width, caja.height
    if nombre == "logo":  # el rótulo es chico: se le da un área razonable centrada
        cx, cy = left + ancho // 2, top + alto // 2
        ancho, alto = max(ancho, Cm(9)), max(alto, Cm(3.5))
        left, top = cx - ancho // 2, cy - alto // 2
    escala = min(ancho / ancho_img, alto / alto_img)
    w, h = int(ancho_img * escala), int(alto_img * escala)
    slide.shapes.add_picture(io.BytesIO(contenido), Emu(left + (ancho - w) // 2), Emu(top + (alto - h) // 2), Emu(w), Emu(h))
    etiqueta = _buscar(slide, f"ETIQUETA:{nombre}")
    if etiqueta is not None:
        _eliminar_forma(etiqueta)
    if caja.shape_type == 17:  # cuadro de texto que solo era el rótulo
        _eliminar_forma(caja)
    elif caja.has_text_frame:
        caja.text_frame.text = ""


# ------------------------------------------------------------------ generación


def generar_ppt(d: DatosPpt, plantilla: Path = PLANTILLA) -> bytes:
    prs = Presentation(plantilla)
    valores = _valores(d)
    condiciones = _condiciones(d)

    for numero, slide in enumerate(list(prs.slides), start=1):
        if numero in d.diapositivas_excluidas:
            _eliminar_diapositiva(prs, slide)
            continue
        condicion = next((f.name[5:] for f in _formas(slide) if f.name.startswith("COND:")), None)
        if condicion and not condiciones[condicion]:
            _eliminar_diapositiva(prs, slide)
            continue
        for f in list(_formas(slide)):
            if f.name.startswith("COND_FORMA:") and not condiciones[f.name[11:]]:
                _eliminar_forma(f)
        _tabla_opciones(slide, d)
        _tabla_consumos(slide, d)
        _grafico_roi(slide, d)
        _grafico_financiacion(slide, d)
        for nombre in ("logo", "planta", "montaje"):
            _imagen(slide, nombre, d.imagenes.get(nombre))
        _completar_textos(slide, valores, condiciones)

    salida = io.BytesIO()
    prs.save(salida)
    return salida.getvalue()
