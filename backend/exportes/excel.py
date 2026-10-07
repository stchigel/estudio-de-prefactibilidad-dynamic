"""Exporte a la planilla original (§10.1).

Se escriben solo las celdas de entrada de Hoja1 editando el XML del .xlsx, para
no perder gráficos, imágenes ni validaciones (openpyxl los descarta al guardar).
Las fórmulas se recalculan al abrir (fullCalcOnLoad).
"""

from __future__ import annotations

import re
import shutil
import warnings
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from lxml import etree

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
    OrigenConsumo,
    TipoFinanciacion,
    TipoInversor,
)

PLANILLA = Path(__file__).resolve().parents[2] / "PLANILLA DE Estimación Proyecto financiación.xlsx"
HOJA = "Hoja1"
SIN_BATERIA = "SIN BATERIA"
FILAS_CONSUMO = range(7, 19)  # Hoja1!W7:Y18

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def _si_no(valor: bool) -> str:
    return "SI" if valor else "NO"


def celdas_entrada(e: Entradas) -> dict[str, Any]:
    """Valor de cada celda de entrada de Hoja1 (§6.1)."""
    b = e.baterias
    activas = e.baterias_activas
    kit2 = e.kit2
    f = e.financiacion
    celdas: dict[str, Any] = {
        "K3": e.numero_propuesta,
        "M3": e.fecha,
        "R3": e.dolar,
        "D5": e.cliente,
        "L5": e.provincia,
        "O5": e.categoria.value,
        "E7": e.distribuidora,
        "I7": e.tarifa,
        "L7": e.potencia_contratada_kw,
        "O7": e.horario_trabajo.value,
        "R7": e.horas_por_dia,
        "E9": e.costo_mayorista,
        "H9": e.tasa_mayorista,
        "L9": e.costo_cammesa,
        "O9": e.tasa_cammesa,
        "R9": e.potencia_contratada_cammesa_kw,
        "E11": e.costo_distribuidora,
        "I11": e.tasas_mun_prov,
        "M11": e.tasa_976_aplicable,
        "R11": e.res281_usd_mwh,
        "F13": e.retribucion_inyeccion,
        "E15": e.tipo_inversor.value,
        "K15": _si_no(e.inhibicion_inyeccion),
        "O15": _si_no(e.banco_capacitores),
        "D18": e.instalacion.value,
        "H18": e.acimut,
        "K18": e.inclinacion,
        "N18": e.inversor.value,
        "E20": e.kit1.kwp,
        "G20": e.kit1.cantidad,
        "O20": e.kit1.distancia_tgbt_m,
        # Sin kit 2 se deja un kWp válido para que las búsquedas no den #N/A.
        "E22": kit2.kwp if kit2 else e.kit1.kwp,
        "G22": kit2.cantidad if kit2 else 0,
        "O22": kit2.distancia_tgbt_m if kit2 else 0,
        # Se exporta el estado efectivo de baterías (§6.10 #4): la planilla reduce
        # la inyección con cualquier modelo elegido aunque sea ON GRID.
        "D24": _si_no(activas),
        "F24": b.objetivo.value,
        "I24": b.autonomia_h,
        "E26": b.modelo if activas else SIN_BATERIA,
        "J26": b.cantidad if activas else 0,
        "O26": b.cantidad_pdu if activas else 0,
        "G28": b.cantidad_rack if activas else 0,
        "O28": e.k_incertidumbre,
        "R28": e.comision,
        "I31": e.tasa_descuento,
        "N31": e.periodo_evaluacion,
        "G40": e.capacitores.kvar,
        "L40": e.capacitores.inversion_usd,
        "P40": e.capacitores.ahorro_ars_anio,
        "F44": f.porcentaje,
        "H44": f.tipo.value,
        "K44": f.moneda.value,
        "N44": f.plazo_anios,
        "Q44": f.gracia_anios,
        "E46": f.tasa,
        "F46": f.gastos_adm,
        "J49": _si_no(e.ppa.aplica),
        "F51": e.ppa.periodo_contrato,
        "L51": e.ppa.precio_usd_mwh,
        "R51": e.ppa.inflacion_usd,
        "J53": e.ppa.fee_salida_usd,
        "M53": e.ppa.oem,
    }
    for fila, consumo in zip(FILAS_CONSUMO, e.consumos):
        celdas[f"W{fila}"] = consumo.valle
        celdas[f"X{fila}"] = consumo.resto
        celdas[f"Y{fila}"] = consumo.pico
    return celdas


def exportar_excel(e: Entradas, destino: Path, plantilla: Path = PLANILLA) -> Path:
    escribir_celdas(plantilla, destino, HOJA, celdas_entrada(e))
    return destino


# ------------------------------------------------------------------ lectura


def leer_entradas(ruta: Path) -> Entradas:
    """Arma Entradas desde una planilla completada (valores cacheados)."""
    import openpyxl

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws = openpyxl.load_workbook(ruta, data_only=True)[HOJA]

    def v(celda: str, defecto: Any = 0.0) -> Any:
        valor = ws[celda].value
        return defecto if valor is None or valor == "" else valor

    def si(celda: str) -> bool:
        return str(v(celda, "NO")).strip().upper() == "SI"

    def instalacion(valor: str) -> Instalacion:
        return next(i for i in Instalacion if i.value.lower() == valor.strip().lower())

    fecha = v("M3", None)
    modelo = v("E26", None)
    tiene_baterias = si("D24") and modelo not in (None, SIN_BATERIA)
    cant2 = int(v("G22", 0))
    return Entradas(
        numero_propuesta=int(v("K3")) if v("K3", None) is not None else None,
        fecha=fecha.date() if isinstance(fecha, datetime) else fecha,
        dolar=float(v("R3")),
        cliente=str(v("D5", "")),
        provincia=str(v("L5")),
        categoria=Categoria(v("O5")),
        distribuidora=str(v("E7", "")),
        tarifa=str(v("I7", "")),
        potencia_contratada_kw=float(v("L7")),
        horario_trabajo=HorarioTrabajo(v("O7")),
        horas_por_dia=int(v("R7")),
        costo_mayorista=float(v("E9")),
        tasa_mayorista=float(v("H9")),
        costo_cammesa=float(v("L9")),
        tasa_cammesa=float(v("O9")),
        potencia_contratada_cammesa_kw=v("R9", None),
        costo_distribuidora=float(v("E11")),
        tasas_mun_prov=float(v("I11")),
        tasa_976=float(v("M11")),
        res281_usd_mwh=float(v("R11")),
        retribucion_inyeccion=float(v("F13")),
        tipo_inversor=TipoInversor(v("E15")),
        inhibicion_inyeccion=si("K15"),
        banco_capacitores=si("O15"),
        instalacion=instalacion(v("D18")),
        acimut=int(v("H18")),
        inclinacion=int(v("K18")),
        inversor=Inversor(v("N18")),
        kit1=Kit(float(v("E20")), int(v("G20")), float(v("O20"))),
        kit2=Kit(float(v("E22")), cant2, float(v("O22"))) if cant2 > 0 else None,
        baterias=Baterias(
            incluye=tiene_baterias,
            objetivo=ObjetivoBaterias(v("F24", "--")),
            autonomia_h=float(v("I24")),
            modelo=modelo if tiene_baterias else None,
            cantidad=int(v("J26")) if tiene_baterias else 0,
            cantidad_pdu=int(v("O26")) if tiene_baterias else 0,
            cantidad_rack=int(v("G28")) if tiene_baterias else 0,
        ),
        k_incertidumbre=float(v("O28")),
        comision=float(v("R28")),
        tasa_descuento=float(v("I31")),
        periodo_evaluacion=int(v("N31")),
        capacitores=Capacitores(float(v("G40")), float(v("L40")), float(v("P40"))),
        financiacion=Financiacion(
            porcentaje=float(v("F44")),
            tipo=TipoFinanciacion(v("H44")),
            moneda=Moneda(v("K44")),
            plazo_anios=int(v("N44")),
            gracia_anios=int(v("Q44")),
            tasa=float(v("E46")),
            gastos_adm=float(v("F46")),
        ),
        ppa=PPA(
            aplica=si("J49"),
            periodo_contrato=int(v("F51")),
            precio_usd_mwh=float(v("L51")),
            inflacion_usd=float(v("R51")),
            fee_salida_usd=float(v("J53")),
            oem=float(v("M53")),
        ),
        consumos=[
            ConsumoMensual(float(v(f"W{f}")), float(v(f"X{f}")), float(v(f"Y{f}")), OrigenConsumo.MANUAL)
            for f in FILAS_CONSUMO
        ],
    )


# ------------------------------------------------------------------ edición de XML


def _indice_columna(ref: str) -> tuple[int, int]:
    letras, fila = re.fullmatch(r"([A-Z]+)(\d+)", ref).groups()
    col = 0
    for letra in letras:
        col = col * 26 + ord(letra) - 64
    return int(fila), col


def _ruta_hoja(z: zipfile.ZipFile, hoja: str) -> str:
    wb = etree.fromstring(z.read("xl/workbook.xml"))
    rid = None
    for s in wb.iter(f"{{{NS}}}sheet"):
        if s.get("name") == hoja:
            rid = s.get(f"{{{NS_REL}}}id")
    if rid is None:
        raise KeyError(f"No existe la hoja {hoja}")
    rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for r in rels:
        if r.get("Id") == rid:
            destino = r.get("Target").lstrip("/")
            return destino if destino.startswith("xl/") else f"xl/{destino}"
    raise KeyError(rid)


def _poner_valor(celda: etree._Element, valor: Any) -> None:
    for hijo in list(celda):
        if hijo.tag == f"{{{NS}}}f" and hijo.get("t") == "shared" and hijo.get("ref"):
            raise ValueError(f"{celda.get('r')} es origen de una fórmula compartida")
        celda.remove(hijo)
    celda.attrib.pop("t", None)
    if valor is None or valor == "":
        return
    if isinstance(valor, bool):
        raise TypeError("Los booleanos se exportan como 'SI'/'NO'")
    if isinstance(valor, (date, datetime)):
        valor = (date(valor.year, valor.month, valor.day) - date(1899, 12, 30)).days
    if isinstance(valor, (int, float)):
        etree.SubElement(celda, f"{{{NS}}}v").text = repr(valor) if isinstance(valor, float) else str(valor)
    else:
        celda.set("t", "inlineStr")
        is_ = etree.SubElement(celda, f"{{{NS}}}is")
        etree.SubElement(is_, f"{{{NS}}}t").text = str(valor)


def _celda(sheet_data: etree._Element, ref: str) -> etree._Element:
    num_fila, num_col = _indice_columna(ref)
    fila = None
    for f in sheet_data.iter(f"{{{NS}}}row"):
        r = int(f.get("r"))
        if r == num_fila:
            fila = f
            break
        if r > num_fila:
            fila = etree.Element(f"{{{NS}}}row", r=str(num_fila))
            f.addprevious(fila)
            break
    if fila is None:
        fila = etree.SubElement(sheet_data, f"{{{NS}}}row", r=str(num_fila))
    for c in fila.iter(f"{{{NS}}}c"):
        _, col = _indice_columna(c.get("r"))
        if col == num_col:
            return c
        if col > num_col:
            nueva = etree.Element(f"{{{NS}}}c", r=ref)
            c.addprevious(nueva)
            return nueva
    return etree.SubElement(fila, f"{{{NS}}}c", r=ref)


def escribir_celdas(origen: Path, destino: Path, hoja: str, celdas: dict[str, Any]) -> None:
    """Copia el libro escribiendo valores en las celdas indicadas."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    with zipfile.ZipFile(origen) as z:
        ruta_hoja = _ruta_hoja(z, hoja)
        hoja_xml = etree.fromstring(z.read(ruta_hoja))
        sheet_data = hoja_xml.find(f"{{{NS}}}sheetData")
        for ref, valor in celdas.items():
            _poner_valor(_celda(sheet_data, ref), valor)

        # Excel reconstruye la cadena de cálculo; si queda desactualizada pide "reparar".
        wb = etree.fromstring(z.read("xl/workbook.xml"))
        calc = wb.find(f"{{{NS}}}calcPr")
        if calc is None:
            calc = etree.SubElement(wb, f"{{{NS}}}calcPr")
        calc.set("fullCalcOnLoad", "1")
        rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        for r in list(rels):
            if r.get("Target", "").endswith("calcChain.xml"):
                rels.remove(r)
        tipos = etree.fromstring(z.read("[Content_Types].xml"))
        for o in list(tipos):
            if o.get("PartName", "").endswith("calcChain.xml"):
                tipos.remove(o)

        reemplazos = {
            ruta_hoja: hoja_xml,
            "xl/workbook.xml": wb,
            "xl/_rels/workbook.xml.rels": rels,
            "[Content_Types].xml": tipos,
        }
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as salida:
            for item in z.infolist():
                if item.filename == "xl/calcChain.xml":
                    continue
                if item.filename in reemplazos:
                    xml = etree.tostring(reemplazos[item.filename], xml_declaration=True, encoding="UTF-8", standalone=True)
                    salida.writestr(item, xml)
                else:
                    salida.writestr(item, z.read(item.filename))
    shutil.move(temporal, destino)
