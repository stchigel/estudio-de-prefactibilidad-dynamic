"""Funciones financieras con la semántica de Excel (NPV, IRR)."""

from __future__ import annotations

from collections.abc import Sequence


def npv(tasa: float, flujos: Sequence[float]) -> float:
    """NPV de Excel: el primer flujo se descuenta un período."""
    return sum(f / (1 + tasa) ** k for k, f in enumerate(flujos, start=1))


def _vpn_t0(tasa: float, flujos: Sequence[float]) -> float:
    return sum(f / (1 + tasa) ** k for k, f in enumerate(flujos))


def irr(flujos: Sequence[float], tol: float = 1e-12) -> float | None:
    """IRR de Excel (flujo 0 sin descontar). None si no hay cambio de signo."""
    if not any(f < 0 for f in flujos) or not any(f > 0 for f in flujos):
        return None
    bajo, alto = -0.9999, 1.0
    f_bajo = _vpn_t0(bajo, flujos)
    while _vpn_t0(alto, flujos) * f_bajo > 0:
        alto *= 2
        if alto > 1e6:
            return None
    for _ in range(300):
        medio = (bajo + alto) / 2
        f_medio = _vpn_t0(medio, flujos)
        if abs(f_medio) < tol or (alto - bajo) / 2 < tol:
            return medio
        if f_medio * f_bajo > 0:
            bajo, f_bajo = medio, f_medio
        else:
            alto = medio
    return (bajo + alto) / 2
