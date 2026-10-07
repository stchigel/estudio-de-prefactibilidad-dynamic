"""Genera los casos de equivalencia contra la planilla (§12).

Para cada caso de tests/casos/definiciones.py: exporta las entradas a una copia de
la planilla, la recalcula con Excel (COM, solo Windows) y guarda entradas +
salidas en tests/casos/<nombre>.json. Los tests luego corren sin Excel.

Uso:  python scripts/generar_casos_excel.py [nombre_caso ...]
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

import win32com.client  # noqa: E402

from casos.definiciones import CASOS  # noqa: E402
from exportes.excel import exportar_excel  # noqa: E402
from motor.serializacion import a_dict  # noqa: E402

SALIDA = BACKEND / "tests" / "casos"

# Celdas de salida a leer: nombre lógico -> (hoja, rango)
SALIDAS = {
    "precio_kwp_kit1": ("Hoja1", "J20"),
    "precio_kwp_kit2": ("Hoja1", "J22"),
    "cable_kit1": ("Hoja1", "R20"),
    "cable_kit2": ("Hoja1", "R22"),
    "baterias_usd": ("Hoja1", "J28"),
    "capacidad_bateria_recomendada": ("Hoja1", "M24"),
    "superficie_m2": ("Hoja1", "Q31"),
    "consumo_anual": ("Hoja1", "E33"),
    "generacion_anual": ("Hoja1", "J33"),
    "cobertura": ("Hoja1", "L33"),
    "autoconsumo": ("Hoja1", "P33"),
    "autoconsumo_pct": ("Hoja1", "R33"),
    "inyectada": ("Hoja1", "E35"),
    "desperdiciada": ("Hoja1", "J35"),
    "ahorro_pct": ("Hoja1", "N35"),
    "ahorro_usd": ("Hoja1", "Q35"),
    "inversion": ("Hoja1", "E37"),
    "roi": ("Hoja1", "J37"),
    "tir": ("Hoja1", "M37"),
    "van": ("Hoja1", "Q37"),
    "monto_financiado": ("Hoja1", "J46"),
    "canon": ("Hoja1", "O46"),
    "ventas_anio1": ("Hoja1", "E53"),
    "tir_ppa": ("Hoja1", "P53"),
    "huella": ("Hoja1", "I60:R60"),
    "precio_kwh": ("PERFIL DE CONSUMO", "R20"),
    "ahorro_ars": ("PERFIL DE CONSUMO", "T26"),
    "precio_kwh_usd": ("PERFIL DE CONSUMO", "R33"),
    "potencia_sugerida": ("PERFIL DE CONSUMO", "I4"),
    "generacion_mensual": ("PERFIL DE CONSUMO", "R5:R16"),
    "inyeccion_mensual": ("PERFIL DE CONSUMO", "V5:V16"),
    "dias_laborables": ("BAT", "M5:M16"),
    "kw_fuera": ("BAT", "O5:O16"),
    "kw_lab": ("BAT", "P5:P16"),
    "exc_no_lab": ("BAT", "Q5:Q16"),
    "exc_lab": ("BAT", "R5:R16"),
    "flujos": ("VAN TIR", "G2:G26"),
    "van_por_periodo": ("VAN TIR", "L3:S3"),
    "flujos_ppa": ("VAN TIR", "G31:G55"),
    "van_ppa_por_periodo": ("VAN TIR", "L32:S32"),
    "tir_ppa_por_periodo": ("VAN TIR", "L33:S33"),
    "pagos_financiacion": ("Financiación", "C12:I12"),
}


def _limpiar(valor):
    """Errores de Excel (#N/A, #DIV/0!, …) llegan como enteros negativos."""
    if isinstance(valor, int) and valor < -2146820000:
        return None
    return valor


def _leer(libro, hoja: str, rango: str):
    valor = libro.Worksheets(hoja).Range(rango).Value2
    if isinstance(valor, tuple):
        planos = [v for fila in valor for v in fila]
        return [_limpiar(v) for v in planos]
    return _limpiar(valor)


def main(nombres: list[str]) -> None:
    casos = {n: c for n, c in CASOS.items() if not nombres or n in nombres}
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for nombre, construir in casos.items():
                entradas = construir()
                ruta = Path(tmp) / f"{nombre}.xlsx"
                exportar_excel(entradas, ruta)
                libro = excel.Workbooks.Open(str(ruta), UpdateLinks=0, ReadOnly=True)
                try:
                    excel.CalculateFull()
                    salidas = {k: _leer(libro, h, r) for k, (h, r) in SALIDAS.items()}
                finally:
                    libro.Close(SaveChanges=False)
                destino = SALIDA / f"{nombre}.json"
                destino.write_text(
                    json.dumps({"entradas": a_dict(entradas), "excel": salidas}, ensure_ascii=False, indent=1),
                    encoding="utf-8",
                )
                print(f"{nombre}: inversión={salidas['inversion']:.2f} roi={salidas['roi']} -> {destino.name}")
    finally:
        excel.Quit()


if __name__ == "__main__":
    main(sys.argv[1:])
