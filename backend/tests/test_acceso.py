"""Contraseña de acceso, sesión por cookie, CORS y límites de pedidos (api/acceso.py)."""

import time

import pytest
from fastapi.testclient import TestClient

from api import acceso
from api.main import app

CLAVE = "clave-de-prueba"


@pytest.fixture(autouse=True)
def _limpiar_limitadores():
    acceso.intentos_fallidos._eventos.clear()
    acceso.facturas_por_hora._eventos.clear()


@pytest.fixture
def libre(monkeypatch):
    monkeypatch.delenv("ACCESS_PASSWORD", raising=False)
    return TestClient(app)


@pytest.fixture
def protegida(monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", CLAVE)
    monkeypatch.setenv("SESSION_SECRET", "secreto-largo-para-pruebas-123456")
    return TestClient(app)


def test_sin_contrasena_el_acceso_es_libre(libre):
    assert libre.get("/api/opciones").status_code == 200
    assert libre.get("/api/sesion").json() == {"requiere_login": False, "autenticado": True}


def test_con_contrasena_la_api_pide_sesion(protegida):
    assert protegida.get("/api/opciones").status_code == 401
    assert protegida.post("/api/calcular", json={}).status_code == 401
    assert protegida.post("/api/facturas/extraer", files=[("archivos", ("a.pdf", b"x", "application/pdf"))]).status_code == 401
    # Las rutas públicas responden igual.
    assert protegida.get("/api/salud").status_code == 200
    assert protegida.get("/api/sesion").json() == {"requiere_login": True, "autenticado": False}


def test_login_correcto_habilita_la_api_y_logout_la_cierra(protegida):
    r = protegida.post("/api/login", json={"password": CLAVE})
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower()
    assert protegida.get("/api/opciones").status_code == 200
    assert protegida.get("/api/sesion").json()["autenticado"] is True

    protegida.post("/api/logout")
    assert protegida.get("/api/opciones").status_code == 401


def test_login_con_contrasena_incorrecta(protegida):
    r = protegida.post("/api/login", json={"password": "otra"})
    assert r.status_code == 401
    assert "set-cookie" not in r.headers
    assert protegida.get("/api/opciones").status_code == 401


def test_bloquea_tras_cinco_intentos_fallidos_aun_con_la_clave_correcta(protegida):
    for _ in range(5):
        assert protegida.post("/api/login", json={"password": "mal"}).status_code == 401
    assert protegida.post("/api/login", json={"password": CLAVE}).status_code == 429


def test_cookie_adulterada_o_vencida_se_rechaza(protegida):
    protegida.post("/api/login", json={"password": CLAVE})
    valido = protegida.cookies.get(acceso.COOKIE)
    expira, _, firma = valido.partition(".")

    for malo in (f"{int(expira) + 1000}.{firma}", f"{expira}.{'0' * len(firma)}", "basura", ""):
        protegida.cookies.set(acceso.COOKIE, malo)
        assert protegida.get("/api/opciones").status_code == 401, malo

    vencido = int(time.time()) - 10
    protegida.cookies.set(acceso.COOKIE, f"{vencido}.{acceso._firma(vencido)}")
    assert protegida.get("/api/opciones").status_code == 401


def test_cambiar_la_contrasena_invalida_las_sesiones(protegida, monkeypatch):
    protegida.post("/api/login", json={"password": CLAVE})
    assert protegida.get("/api/opciones").status_code == 200
    monkeypatch.setenv("ACCESS_PASSWORD", "nueva-clave")
    assert protegida.get("/api/opciones").status_code == 401


def test_falta_session_secret_impide_arrancar(monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", CLAVE)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        acceso.verificar_configuracion()
    monkeypatch.delenv("ACCESS_PASSWORD")
    acceso.verificar_configuracion()  # sin contraseña no hace falta secreto


def test_cors_permite_el_frontend_local_con_credenciales(libre):
    r = libre.options(
        "/api/opciones",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert r.headers["access-control-allow-credentials"] == "true"
    otro = libre.get("/api/opciones", headers={"Origin": "https://sitio-ajeno.example"})
    assert "access-control-allow-origin" not in otro.headers


def test_el_preflight_no_pide_sesion(protegida):
    r = protegida.options(
        "/api/calcular",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert r.status_code == 200


def test_limite_de_facturas_por_hora(libre, monkeypatch):
    monkeypatch.setattr(acceso, "facturas_por_hora", acceso.Limitador(maximo=2, ventana_s=3600))
    tres = [("archivos", (f"{i}.pdf", b"x", "application/pdf")) for i in range(3)]
    assert libre.post("/api/facturas/extraer", files=tres).status_code == 429
