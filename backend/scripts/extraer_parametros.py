"""Extrae catálogo y parámetros técnicos de la planilla original a JSON (§9).

Uso:  python scripts/extraer_parametros.py [ruta_planilla.xlsx]

Genera motor/datos/catalogo.json y motor/datos/parametros.json. Se corre una vez
por versión de la planilla; a partir de la Etapa 3 estos datos se administran
desde la aplicación.
"""

import json
import sys
import warnings
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
PLANILLA = RAIZ / "PLANILLA DE Estimación Proyecto financiación.xlsx"
DESTINO = Path(__file__).resolve().parents[1] / "motor" / "datos"

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
INSTALACIONES = ["Coplanar", "Engrafado", "Losa", "Piso"]
INVERSORES = ["Growatt", "Huawei", "Deye Hib"]

# Reglas de PDU / rack / mínimos (TRANSP!T43:Z48 y AB31:AD37, en texto en la planilla).
REGLAS_BATERIAS = {
    "Low Voltage 5,12 kWh": dict(min_baterias=None, max_baterias=None, baterias_por_pdu=None, baterias_por_rack=None),
    "Low Voltage 16 kWh": dict(min_baterias=None, max_baterias=None, baterias_por_pdu=None, baterias_por_rack=None),
    "High Voltage 7,68 kWh min 7 bat": dict(min_baterias=7, max_baterias=None, baterias_por_pdu=21, baterias_por_rack=13),
    "High Voltage 12,03 kWh min 5 bat": dict(min_baterias=5, max_baterias=16, baterias_por_pdu=16, baterias_por_rack=None),
    "High Voltage 16 kWh min 5 bat": dict(min_baterias=5, max_baterias=16, baterias_por_pdu=16, baterias_por_rack=16),
}
# kWh nominal y capacidad que usa BAT!N1 para la inyección (Low Voltage = 0, pendiente A2).
KWH_BATERIAS = {
    "Low Voltage 5,12 kWh": (5.12, 0.0),
    "Low Voltage 16 kWh": (16.0, 0.0),
    "High Voltage 7,68 kWh min 7 bat": (7.68, 7.68),
    "High Voltage 12,03 kWh min 5 bat": (12.03, 12.03),
    "High Voltage 16 kWh min 5 bat": (16.0, 16.1),
}
MARGEN_BATERIAS = 1.5  # TRANSP!Z32:AD36 = costo × 1,5


def main(ruta: Path) -> None:
    warnings.filterwarnings("ignore")
    ws = openpyxl.load_workbook(ruta, data_only=True)["TRANSP"]

    provincias = [ws.cell(1, c).value for c in range(21, 45)]  # U1:AR1
    hsp = {
        prov: [float(ws.cell(f, c).value) for f in range(2, 14)]
        for prov, c in zip(provincias, range(21, 45))
    }

    coeficientes = {}
    for f in range(2, 962):
        acimut, inclinacion, prov = (ws.cell(f, c).value for c in (1, 2, 3))
        valores = [float(ws.cell(f, c).value) for c in range(4, 16)]
        coeficientes.setdefault(prov, {}).setdefault(str(acimut), {})[str(inclinacion)] = valores
    acimuts = sorted({int(a) for p in coeficientes.values() for a in p})
    inclinaciones = sorted({int(i) for p in coeficientes.values() for a in p.values() for i in a})

    bat = openpyxl.load_workbook(ruta, data_only=True)["BAT"]
    perfil = [[float(bat.cell(f, c).value) for c in range(27, 40)] for f in range(20, 32)]  # AA20:AM31

    kits = []
    for f in range(19, 29):  # TRANSP!Y19:AG28
        fila = [ws.cell(f, c).value for c in range(25, 34)]
        kits.append({
            "kwp": fila[0],
            "precio_usd_kwp": dict(zip(INSTALACIONES, fila[1:5])),
            "adicional_inversor_usd_kwp": dict(zip(INVERSORES, fila[5:8])),
            "cable_ca_usd_m": fila[8],
        })

    baterias = []
    for f in range(51, 56):  # TRANSP!T51:W55 (precios ya con margen)
        modelo, precio, pdu, rack = (ws.cell(f, c).value for c in range(20, 24))
        kwh, capacidad = KWH_BATERIAS[modelo]
        baterias.append({
            "modelo": modelo,
            "kwh": kwh,
            "capacidad_calculo_kwh": capacidad,
            "precio_usd": precio,
            "precio_pdu_usd": pdu,
            "precio_rack_usd": rack,
            **REGLAS_BATERIAS[modelo],
        })

    catalogo = {
        "version": "planilla-2026-09",
        "kits": kits,
        "baterias": baterias,
        "margen_baterias": MARGEN_BATERIAS,
    }
    parametros = {
        "version": "planilla-2026-09",
        "meses": MESES,
        "dias_mes": [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
        "semanas_mes": [int(bat.cell(f, 25).value) for f in range(5, 17)],  # BAT!Y5:Y16
        "provincias": provincias,
        "acimuts": acimuts,
        "inclinaciones": inclinaciones,
        "hsp": hsp,
        "coeficientes": coeficientes,
        "perfil_horario": perfil,
        "horas_perfil": [f"{h}:00" for h in range(7, 20)],
        "factor_kwp_por_modulo": 0.58,
        "factores_superficie": {"Coplanar": 2.9, "Engrafado": 2.9, "Losa": 3.5, "Piso": 5.0},
        "huella": {"tco2_por_mwh": 0.35, "arboles_por_mwh": 16.6, "autos_por_mwh": 0.15},
        "degradacion": {"anio_2": 0.99, "siguientes": 0.994},
        "horas_laborables_max": 11,
        "cos_phi_objetivo": 0.95,
    }

    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, datos in (("catalogo.json", catalogo), ("parametros.json", parametros)):
        (DESTINO / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        print("escrito", DESTINO / nombre)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else PLANILLA)
