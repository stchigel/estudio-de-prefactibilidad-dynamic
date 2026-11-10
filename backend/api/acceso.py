"""Acceso con contraseña compartida (opcional) y límite de pedidos.

Pensado para cuando la API queda publicada en internet: sin esto, cualquiera que conozca la URL podría
gastar crédito de IA en /api/facturas/extraer.

- Sin ACCESS_PASSWORD en el entorno, el acceso es libre (uso local en una PC). Es el comportamiento anterior.
- Con ACCESS_PASSWORD, todos los endpoints /api/* piden la cookie de sesión, salvo salud, sesion, login y logout.
  Hace falta también SESSION_SECRET (texto largo al azar) para firmar la cookie.

La cookie es HttpOnly; Secure cuando el pedido llega por HTTPS. Si el frontend y la API están en
subdominios del mismo dominio (app.empresa.com y api.empresa.com) el navegador la envía sin más configuración.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

COOKIE = "sesion"
DURACION_SESION_S = 7 * 24 * 3600
PUBLICAS = frozenset({"/api/salud", "/api/sesion", "/api/login", "/api/logout"})

router = APIRouter()


def _password() -> str | None:
    return os.environ.get("ACCESS_PASSWORD") or None


def verificar_configuracion() -> None:
    """Falla al arrancar (en vez de dejar la API abierta o rota) si la configuración está incompleta."""
    if _password() and len(os.environ.get("SESSION_SECRET", "")) < 16:
        raise RuntimeError(
            "ACCESS_PASSWORD está definida pero falta SESSION_SECRET (mínimo 16 caracteres, al azar). Ver backend/.env.example."
        )


def _firma(expira: int) -> str:
    # La contraseña entra en la firma: cambiarla invalida todas las sesiones abiertas.
    huella = hashlib.sha256((_password() or "").encode()).hexdigest()
    clave = os.environ.get("SESSION_SECRET", "").encode()
    return hmac.new(clave, f"{expira}:{huella}".encode(), hashlib.sha256).hexdigest()


def _crear_token() -> str:
    expira = int(time.time()) + DURACION_SESION_S
    return f"{expira}.{_firma(expira)}"


def _token_valido(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expira_txt, _, firma = token.partition(".")
    if not expira_txt.isdigit() or int(expira_txt) < time.time():
        return False
    return hmac.compare_digest(firma, _firma(int(expira_txt)))


def requiere_sesion(request: Request) -> None:
    """Dependencia global de la app: rechaza con 401 si hay contraseña configurada y no hay sesión."""
    if _password() is None or request.url.path in PUBLICAS:
        return
    if not _token_valido(request.cookies.get(COOKIE)):
        raise HTTPException(401, "Hace falta iniciar sesión")


class Limitador:
    """Cuenta eventos por clave (IP) en una ventana de tiempo. En memoria: alcanza para un solo proceso."""

    def __init__(self, maximo: int, ventana_s: int) -> None:
        self.maximo, self.ventana_s = maximo, ventana_s
        self._eventos: dict[str, deque[float]] = defaultdict(deque)

    def _purgar(self, clave: str) -> deque[float]:
        cola, ahora = self._eventos[clave], time.monotonic()
        while cola and ahora - cola[0] > self.ventana_s:
            cola.popleft()
        return cola

    def bloqueado(self, clave: str) -> bool:
        return len(self._purgar(clave)) >= self.maximo

    def registrar(self, clave: str, cantidad: int = 1) -> None:
        self._purgar(clave).extend([time.monotonic()] * cantidad)

    def consumir(self, clave: str, cantidad: int = 1) -> None:
        """Registra `cantidad` eventos o, si pasaría el máximo, responde 429 sin registrar nada."""
        if len(self._purgar(clave)) + cantidad > self.maximo:
            raise HTTPException(429, "Demasiados pedidos seguidos; esperar un rato antes de reintentar.")
        self.registrar(clave, cantidad)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


# Intentos de contraseña fallidos por IP.
intentos_fallidos = Limitador(maximo=5, ventana_s=300)
# Facturas enviadas a la IA por IP y hora (cada una cuesta crédito de la API de IA).
facturas_por_hora = Limitador(maximo=int(os.environ.get("LIMITE_FACTURAS_HORA", "100")), ventana_s=3600)


def limitar_facturas(request: Request, cantidad: int) -> None:
    facturas_por_hora.consumir(_ip(request), cantidad)


class PedidoLogin(BaseModel):
    password: str


@router.get("/api/sesion")
def estado_sesion(request: Request) -> dict[str, bool]:
    requiere = _password() is not None
    return {"requiere_login": requiere, "autenticado": not requiere or _token_valido(request.cookies.get(COOKIE))}


@router.post("/api/login")
def iniciar_sesion(pedido: PedidoLogin, request: Request, response: Response) -> dict[str, bool]:
    esperada = _password()
    if esperada is None:
        return {"autenticado": True}
    ip = _ip(request)
    if intentos_fallidos.bloqueado(ip):
        raise HTTPException(429, "Demasiados intentos fallidos; esperar unos minutos.")
    if not hmac.compare_digest(pedido.password.encode(), esperada.encode()):
        intentos_fallidos.registrar(ip)
        raise HTTPException(401, "Contraseña incorrecta")
    response.set_cookie(
        COOKIE,
        _crear_token(),
        max_age=DURACION_SESION_S,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    return {"autenticado": True}


@router.post("/api/logout")
def cerrar_sesion(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE, path="/")
    return {"autenticado": False}
