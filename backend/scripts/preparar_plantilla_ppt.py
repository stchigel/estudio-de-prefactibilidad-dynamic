"""Prepara la plantilla de PowerPoint con marcas para el generador (§10.2).

Toma la plantilla original del equipo y reemplaza los "xxx" por marcas
{{nombre}} que exportes/powerpoint.py completa. También:
  - nombra formas especiales: IMG:<x> (imagen), TABLA:<x>, GRAFICO:<x>, ETIQUETA:<x>
    (rótulo a quitar cuando hay imagen), COND:<x> (diapositiva condicional) y
    COND_FORMA:<x> (forma condicional);
  - marca párrafos condicionales con el prefijo [[si:<x>]];
  - ordena las diapositivas como la spec (Arquitectura antes de Previsibilidad).

Cada reemplazo verifica que el texto original exista: si la plantilla cambia,
el script falla indicando qué no encontró.

Uso:  python scripts/preparar_plantilla_ppt.py [plantilla_original.pptx]
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

RAIZ = Path(__file__).resolve().parents[2]
ORIGEN = RAIZ / "ejemplos-prefactibilidad" / "Presentación prefactibilidad SOLAR.pptx"
DESTINO = Path(__file__).resolve().parents[1] / "exportes" / "plantillas" / "prefactibilidad.pptx"


class PlantillaDistinta(Exception):
    pass


def formas(contenedor):
    for f in contenedor.shapes:
        yield f
        if f.shape_type == 6:  # grupo
            yield from formas(f)


def forma(slide, shape_id: int):
    for f in formas(slide):
        if f.shape_id == shape_id:
            return f
    raise PlantillaDistinta(f"No existe la forma {shape_id}")


def reemplazar(f, viejo: str, nuevo: str, prefijo_parrafo: str = "") -> None:
    """Reemplaza texto que puede estar repartido en varios runs de un mismo párrafo.

    El resultado queda en el primer run involucrado (con su formato).
    """
    encontrados = 0
    for parrafo in f.text_frame.paragraphs:
        runs = parrafo.runs
        texto = "".join(r.text for r in runs)
        inicio = texto.find(viejo)
        if inicio < 0:
            continue
        encontrados += 1
        fin = inicio + len(viejo)
        pos = 0
        primero = None
        for r in runs:
            r_ini, r_fin = pos, pos + len(r.text)
            pos = r_fin
            if r_fin <= inicio or r_ini >= fin:
                continue
            antes = r.text[: max(0, inicio - r_ini)]
            despues = r.text[max(0, fin - r_ini) :] if r_fin > fin else ""
            if primero is None:
                primero = r
                r.text = antes + nuevo + despues
            else:
                r.text = despues
        if prefijo_parrafo:
            runs[0].text = prefijo_parrafo + runs[0].text
    if encontrados != 1:
        raise PlantillaDistinta(f"'{viejo}' aparece {encontrados} veces en {f.name!r} (se esperaba 1)")


def parrafo_completo(f, contiene: str, nuevo: str) -> None:
    """Reemplaza todo el texto del párrafo que contiene `contiene`."""
    for parrafo in f.text_frame.paragraphs:
        texto = "".join(r.text for r in parrafo.runs)
        if contiene in texto:
            reemplazar(f, texto, nuevo)
            return
    raise PlantillaDistinta(f"No se encontró un párrafo con '{contiene}' en {f.name!r}")


def condicional(f, contiene: str, condicion: str) -> None:
    for parrafo in f.text_frame.paragraphs:
        if contiene in "".join(r.text for r in parrafo.runs):
            parrafo.runs[0].text = f"[[si:{condicion}]]" + parrafo.runs[0].text
            return
    raise PlantillaDistinta(f"No se encontró '{contiene}' en {f.name!r}")


def eliminar(f) -> None:
    f._element.getparent().remove(f._element)


def desvincular_graficos(p) -> int:
    """Quita vínculos de gráficos a planillas externas: el generador embebe los datos."""
    quitados = 0
    for slide in p.slides:
        for f in formas(slide):
            if not getattr(f, "has_chart", False) or not f.has_chart:
                continue
            parte = f.chart.part
            externo = parte._element.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}externalData")
            if externo is None:
                continue
            rid = externo.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            if parte.rels[rid].is_external:
                parte._element.remove(externo)
                parte.drop_rel(rid)
                quitados += 1
    return quitados


def preparar(origen: Path, destino: Path) -> None:
    p = Presentation(origen)
    s = list(p.slides)
    if len(s) != 16:
        raise PlantillaDistinta(f"Se esperaban 16 diapositivas, hay {len(s)}")

    # 1 · Portada
    t = forma(s[0], 2)
    reemplazar(t, "PROPUESTA DE ENERGÍA SOLAR  · LLAVE EN MANO", "PROPUESTA DE ENERGÍA SOLAR  ·  {{tipo_sistema}} LLAVE EN MANO")
    reemplazar(t, " N° XXXXXX", " N° {{numero}}")
    reemplazar(t, "XX/XX/2026", "{{fecha}}")
    forma(s[0], 11).name = "IMG:logo"

    # 2 · El objetivo
    c = forma(s[1], 3)
    reemplazar(c, "GENERACIÓN FOTOVOLTAICA IN SITU ", "GENERACIÓN FOTOVOLTAICA IN SITU PARA {{cliente}}")
    reemplazar(c, "Lu a Vi de 7 a 19\tSabado: No opera", "{{horario}}")
    reemplazar(c, "\tSI/NO", "\t{{inyeccion}}")
    reemplazar(c, "XXXXXXX kWh/", "{{consumo_anual}} kWh/")
    reemplazar(c, "XXX kW", "{{potencia_contratada}} kW")
    reemplazar(c, "Xxxxxxxx 2026", "{{tarifa}}")
    condicional(c, "meses no", "meses_estimados")
    condicional(c, "Perfil de consumo", "meses_estimados")
    forma(s[1], 14).name = "IMG:planta"
    forma(s[1], 12).name = "ETIQUETA:planta"
    forma(s[1], 9).name = "TABLA:consumos"
    forma(s[1], 15).name = "ETIQUETA:consumos"

    # 3 · La oportunidad detectada
    c = forma(s[2], 3)
    reemplazar(c, "disponible de PLECOR SRL ", "disponible de {{cliente}} ")
    condicional(c, "Corrección del factor de potencia", "capacitores")
    condicional(c, "Mejora la calidad", "capacitores")
    parrafo_completo(c, "m2 de techo disponible", "            {{texto_superficie}}")
    parrafo_completo(c, "Superficie útil sobre", "	{{detalle_superficie}}")
    forma(s[2], 9).name = "COND_FORMA:capacitores"  # ícono del factor de potencia
    forma(s[2], 13).name = "COND_FORMA:capacitores"
    forma(s[2], 16).name = "IMG:montaje"

    # 4 · La solución
    reemplazar(forma(s[3], 2), " ON-GRID/HÍBRIDO", " {{tipo_sistema}}")
    parrafo_completo(forma(s[3], 30), "Los paneles abastecen", "{{solucion_1}}")
    parrafo_completo(forma(s[3], 36), "El inversor sincroniza", "{{solucion_2}}")
    parrafo_completo(forma(s[3], 42), "De noche opera", "{{solucion_3}}")

    # 6 · Arquitectura (pasa a ser la 5)
    parrafo_completo(forma(s[5], 3), "El sistema arranca", "{{texto_arquitectura}}")
    reemplazar(forma(s[5], 24), "139 ", "{{kwp_fase1}} ")

    # 7 · Opciones propuestas
    t = forma(s[6], 2)
    reemplazar(t, "564.235", "{{consumo_anual}}")
    t.name = "COND:opciones"
    forma(s[6], 26).name = "TABLA:opciones"

    # 8 · Los números
    reemplazar(forma(s[7], 2), " de la Opción recomendada", "{{titulo_numeros}}")
    for shape_id, viejo, marca in [
        (12, "xxx", "kwp"), (19, "xxxx", "inversion"), (64, "xxxx", "generacion"), (60, "XX", "cobertura"),
        (57, "XXX", "superficie"), (53, "xxxxx", "ahorro"), (49, "xx", "roi"), (45, "XXXX", "tir"), (28, "XX", "autoconsumo"),
    ]:
        reemplazar(forma(s[7], shape_id), viejo, "{{" + marca + "}}")

    # 9 · Retorno
    reemplazar(forma(s[8], 2), " de X ", " de {{roi_techo}} ")
    t = forma(s[8], 30)
    reemplazar(t, "XXx", "{{roi_decimal}}")
    reemplazar(t, "xxxx", "{{roi_meses}}")
    reemplazar(forma(s[8], 34), "20 años", "{{anios_ahorro_neto}} años")
    forma(s[8], 7).name = "GRAFICO:roi"

    # 10 · Financiamiento propio
    t = forma(s[9], 2)
    reemplazar(t, "Propia en Dólares a Tasa 0%", "{{titulo_financiacion}}")
    t.name = "COND:financiacion"
    parrafo_completo(forma(s[9], 8), "Dynamic Energy ofrece", "{{texto_financiacion}}")
    reemplazar(forma(s[9], 15), "12 cuotas en USD", "{{financiacion_cuotas}}")
    parrafo_completo(forma(s[9], 16), "Anticipo + saldo", "{{financiacion_detalle}}")
    reemplazar(forma(s[9], 20), "en dólares", "en {{moneda_texto}}")
    forma(s[9], 3).name = "GRAFICO:financiacion"
    # Bloque CFI ("CFI" + condiciones de la línea): se completa desde la app y se oculta si no hay texto.
    forma(s[9], 36).name = "COND_FORMA:cfi"
    t = forma(s[9], 37)
    t.name = "COND_FORMA:cfi"
    parrafo_completo(t, "Plazos hasta", "{{texto_cfi}}")
    for parrafo in t.text_frame.paragraphs[1:]:  # el resto de las líneas las genera el exporte
        parrafo._p.getparent().remove(parrafo._p)

    # 11 · Financiamiento bancario (opcional)
    t = forma(s[10], 2)
    t.name = "COND:bancaria"
    parrafo_completo(forma(s[10], 8), "Dynamic Energy le gestiona", "{{texto_bancario}}")

    # 13 · Impacto ambiental
    reemplazar(forma(s[12], 7), "XX,xx", "{{tco2_anio}}")
    reemplazar(forma(s[12], 12), "x.xxx", "{{tco2_25}}")
    parrafo_completo(forma(s[12], 18), "árboles", "≈ {{arboles}} árboles")
    parrafo_completo(forma(s[12], 23), "autos", "≈ {{autos}} autos")
    reemplazar(forma(s[12], 44), "XXXXXXXX", "{{generacion}}")

    print("Gráficos desvinculados de planillas externas:", desvincular_graficos(p))

    # Orden de la spec: 5 Arquitectura, 6 Previsibilidad.
    lista = p.slides._sldIdLst
    ids = list(lista)
    lista.remove(ids[5])
    lista.insert(4, ids[5])

    destino.parent.mkdir(parents=True, exist_ok=True)
    p.save(destino)
    print("Plantilla preparada:", destino)


if __name__ == "__main__":
    preparar(Path(sys.argv[1]) if len(sys.argv) > 1 else ORIGEN, DESTINO)
