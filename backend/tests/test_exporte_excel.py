import zipfile

from casos.definiciones import CASOS, plecor_hibrido_baterias
from exportes.excel import PLANILLA, exportar_excel, leer_entradas
from motor.serializacion import a_dict, entradas_desde_dict


def _sin_origenes(d):
    d = dict(d)
    d["consumos"] = [{**c, "origen": "manual"} for c in d["consumos"]]
    return d


def test_ida_y_vuelta_conserva_entradas(tmp_path):
    for nombre, construir in CASOS.items():
        e = construir()
        ruta = exportar_excel(e, tmp_path / f"{nombre}.xlsx")
        leido = leer_entradas(ruta)
        esperado = a_dict(e)
        if not e.baterias_activas:  # se exporta el estado efectivo (§6.10 #4)
            esperado["baterias"] = {**a_dict(leido.baterias), "objetivo": esperado["baterias"]["objetivo"],
                                    "autonomia_h": esperado["baterias"]["autonomia_h"]}
        assert _sin_origenes(a_dict(leido)) == _sin_origenes(esperado), nombre


def test_preserva_graficos_e_imagenes(tmp_path):
    ruta = exportar_excel(plecor_hibrido_baterias(), tmp_path / "x.xlsx")
    with zipfile.ZipFile(PLANILLA) as original, zipfile.ZipFile(ruta) as nuevo:
        nombres_orig = set(original.namelist()) - {"xl/calcChain.xml"}
        assert nombres_orig == set(nuevo.namelist())
        for n in nombres_orig:
            if n.startswith(("xl/charts/", "xl/drawings/", "xl/media/")):
                assert original.read(n) == nuevo.read(n), n
        assert b'fullCalcOnLoad="1"' in nuevo.read("xl/workbook.xml")


def test_serializacion_ida_y_vuelta():
    for construir in CASOS.values():
        e = construir()
        assert entradas_desde_dict(a_dict(e)) == e
