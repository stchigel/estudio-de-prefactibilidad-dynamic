"""Consolidación de consumos a 12 meses (§5.3)."""

from __future__ import annotations

from dataclasses import dataclass

from .modelos import ConsumoMensual, OrigenConsumo


@dataclass
class LecturaMensual:
    """Un mes leído de una factura (su propio período) o de su historial."""

    anio: int
    mes: int  # 1..12
    valle: float
    resto: float
    pico: float
    origen: OrigenConsumo  # FACTURA o HISTORIAL


def mes_espejo(mes: int) -> int:
    """Mes simétrico respecto del solsticio: FEB↔NOV, MAR↔OCT, …, JUN↔JUL, ENE↔DIC."""
    return 13 - mes


def consolidar(lecturas: list[LecturaMensual]) -> list[ConsumoMensual | None]:
    """Devuelve ENE..DIC. Los meses sin dato propio ni espejo quedan en None.

    1. Por período (año, mes) prevalece la factura del propio período sobre los historiales.
    2. Por mes calendario se toma el período más reciente.
    3. Los meses faltantes se completan con su espejo y se marcan como estimados.
    """
    por_periodo: dict[tuple[int, int], LecturaMensual] = {}
    for lectura in lecturas:
        clave = (lectura.anio, lectura.mes)
        actual = por_periodo.get(clave)
        if actual is None or (
            lectura.origen == OrigenConsumo.FACTURA and actual.origen != OrigenConsumo.FACTURA
        ):
            por_periodo[clave] = lectura

    por_mes: dict[int, LecturaMensual] = {}
    for (anio, mes), lectura in sorted(por_periodo.items()):
        por_mes[mes] = lectura  # el orden ascendente deja el año más reciente

    meses: list[ConsumoMensual | None] = []
    for mes in range(1, 13):
        if mes in por_mes:
            l = por_mes[mes]
            meses.append(ConsumoMensual(l.valle, l.resto, l.pico, l.origen))
        elif mes_espejo(mes) in por_mes:
            l = por_mes[mes_espejo(mes)]
            meses.append(ConsumoMensual(l.valle, l.resto, l.pico, OrigenConsumo.ESTIMADO))
        else:
            meses.append(None)
    return meses
