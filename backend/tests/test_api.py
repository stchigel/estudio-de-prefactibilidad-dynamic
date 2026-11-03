import io
import json
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from api.main import app

cliente = TestClient(app)
PLECOR = json.loads((Path(__file__).parent / "casos" / "plecor.json").read_text(encoding="utf-8"))


def test_opciones():
    r = cliente.get("/api/opciones")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos["provincias"]) == 24
    assert "Deye Hib" in datos["inversores"]
    assert len(datos["kits"]) == 10


def test_calcular_coincide_con_excel():
    r = cliente.post("/api/calcular", json=PLECOR["entradas"])
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["inversion"]["total_usd"] == pytest.approx(PLECOR["excel"]["inversion"])
    assert datos["roi_anios"] == pytest.approx(PLECOR["excel"]["roi"])
    assert datos["van_tir"]["van_por_periodo"]["25"] == pytest.approx(PLECOR["excel"]["van"])


def test_calcular_rechaza_entradas_invalidas():
    malo = {**PLECOR["entradas"], "horario_trabajo": "Domingos"}
    assert cliente.post("/api/calcular", json=malo).status_code == 422
    sin_meses = {**PLECOR["entradas"], "consumos": PLECOR["entradas"]["consumos"][:3]}
    assert cliente.post("/api/calcular", json=sin_meses).status_code == 422
    provincia = {**PLECOR["entradas"], "provincia": "Atlántida"}
    assert cliente.post("/api/calcular", json=provincia).status_code == 422


def test_consolidar():
    lecturas = [{"anio": 2026, "mes": m, "valle": 1, "resto": 2, "pico": 3, "origen": "historial"} for m in range(7, 13)]
    r = cliente.post("/api/consumos/consolidar", json=lecturas)
    assert r.status_code == 200, r.text
    meses = r.json()
    assert meses[0]["origen"] == "estimado" and meses[11]["origen"] == "historial"


def test_sugerir_baterias():
    r = cliente.post("/api/baterias/sugerir", json={"modelo": "High Voltage 16 kWh min 5 bat", "cantidad": 17})
    assert r.json() == {"cantidad_pdu": 2, "cantidad_rack": 2}


def test_exportar_excel():
    r = cliente.post("/api/exportes/excel", json=PLECOR["entradas"])
    assert r.status_code == 200
    ws = openpyxl.load_workbook(io.BytesIO(r.content))["Hoja1"]
    assert ws["D5"].value == "PLECOR"
    assert ws["E26"].value == "SIN BATERIA"


def test_buscar_opciones():
    r = cliente.post("/api/opciones/buscar", json=PLECOR["entradas"])
    assert r.status_code == 200, r.text
    datos = r.json()
    assert sum(o["recomendada"] for o in datos["opciones"]) == 1


def test_extraer_sin_credenciales_responde_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    import api.main as m

    def falla(*_):
        raise m.ExtraccionNoConfigurada("Falta configurar ANTHROPIC_API_KEY")

    monkeypatch.setattr(m, "extraer_factura", falla)
    r = cliente.post("/api/facturas/extraer", files=[("archivos", ("f.pdf", b"%PDF", "application/pdf"))])
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_extraer_devuelve_sugerencias(monkeypatch):
    import api.main as m
    from test_extraccion import factura_epe

    monkeypatch.setattr(m, "extraer_factura", lambda *_: factura_epe())
    r = cliente.post("/api/facturas/extraer", files=[("archivos", ("07-2026.pdf", b"%PDF", "application/pdf"))])
    assert r.status_code == 200, r.text
    s = r.json()["sugerencias"]
    assert s["provincia"] == "Santa Fe" and s["potencia_contratada_kw"] == 120


def test_exportar_ppt():
    from pptx import Presentation

    datos = json.dumps({"entradas": PLECOR["entradas"], "incluir_opciones": True})
    r = cliente.post("/api/exportes/ppt", data={"datos": datos})
    assert r.status_code == 200, r.text
    assert "PLECOR" in r.headers["content-disposition"]
    prs = Presentation(io.BytesIO(r.content))
    assert len(prs.slides) == 15  # con tabla de opciones (139,02 kWp se agrega como fila elegida)


def test_exportar_ppt_imagen_invalida():
    datos = json.dumps({"entradas": PLECOR["entradas"], "incluir_opciones": False})
    r = cliente.post("/api/exportes/ppt", data={"datos": datos}, files={"logo": ("logo.png", b"no es imagen", "image/png")})
    assert r.status_code == 415


def test_opciones_lista_las_diapositivas():
    d = cliente.get("/api/opciones").json()["diapositivas"]
    assert [x["numero"] for x in d] == list(range(1, 17))
    assert next(x for x in d if x["numero"] == 7)["condicion"] == "opciones"


def test_exportar_ppt_con_selector_de_paginas():
    from pptx import Presentation

    base = {"entradas": PLECOR["entradas"], "incluir_opciones": True}
    r = cliente.post("/api/exportes/ppt", data={"datos": json.dumps(base)})
    todas = len(Presentation(io.BytesIO(r.content)).slides)
    r = cliente.post("/api/exportes/ppt", data={"datos": json.dumps({**base, "diapositivas_excluidas": [6, 12]})})
    assert r.status_code == 200 and len(Presentation(io.BytesIO(r.content)).slides) == todas - 2
    r = cliente.post("/api/exportes/ppt", data={"datos": json.dumps({**base, "diapositivas_excluidas": [99]})})
    assert r.status_code == 422


def test_exportar_ppt_solo_con_las_opciones_tildadas():
    from pptx import Presentation

    busqueda = cliente.post("/api/opciones/buscar", json=PLECOR["entradas"]).json()["opciones"]
    assert len(busqueda) >= 4
    tildada = busqueda[0]
    pedido = {
        "entradas": PLECOR["entradas"],
        "opciones_incluidas": [{"kit1": tildada["kit1"], "kit2": tildada["kit2"]}],
    }
    r = cliente.post("/api/exportes/ppt", data={"datos": json.dumps(pedido)})
    assert r.status_code == 200, r.text
    prs = Presentation(io.BytesIO(r.content))
    tabla = next(
        f.table for s in prs.slides for f in s.shapes if getattr(f, "has_table", False) and f.has_table and f.name == "TABLA:opciones"
    )
    assert len(list(tabla.rows)) == 1 + 2  # la tildada + la elegida (PLECOR de las entradas)
