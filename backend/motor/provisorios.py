"""Comportamientos provisorios del cálculo (§14.2).

Cada función replica la planilla (salvo A4) hasta que el equipo defina el
criterio. Cambiar el comportamiento acá no debería requerir tocar otro módulo;
los tests en tests/test_provisorios.py documentan el comportamiento actual.
"""

from __future__ import annotations

from .catalogo import BateriaCatalogo, Catalogo


def adicional_inversor_kit2(
    catalogo: Catalogo, kwp_kit1: float, kwp_kit2: float, inversor: str
) -> float:
    """A1 — Hoja1!J22 busca el adicional por inversor con el kWp del kit 1."""
    return catalogo.kit(kwp_kit1).adicional_inversor_usd_kwp[inversor]


def capacidad_bateria_calculo(bateria: BateriaCatalogo) -> float:
    """A2 — BAT!N1 solo reconoce High Voltage; Low Voltage cuenta 0 kWh."""
    return bateria.capacidad_calculo_kwh


def ahorro_por_baterias_ars() -> float:
    """A3 — En la planilla el ahorro por baterías nunca se suma (V24 vacía)."""
    return 0.0


def potencia_contratada_sugerida(pico_kw: float | None, fuera_pico_kw: float | None) -> float | None:
    """A4 — Se precarga la mayor de las potencias contratadas de la factura."""
    valores = [v for v in (pico_kw, fuera_pico_kw) if v is not None]
    return max(valores) if valores else None


# A5 — Hoja1!R9 (Pot Contr kW, bloque CAMMESA) se guarda y exporta, sin efecto en cálculos.
