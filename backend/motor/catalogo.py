"""Catálogo de kits/baterías y parámetros técnicos (§9).

Hoy se cargan de motor/datos/*.json (extraídos de la planilla con
scripts/extraer_parametros.py). En la Etapa 3 se leerán de la base versionada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATOS = Path(__file__).parent / "datos"


@dataclass(frozen=True)
class KitCatalogo:
    kwp: float
    precio_usd_kwp: dict[str, float]  # por instalación
    adicional_inversor_usd_kwp: dict[str, float]  # por inversor
    cable_ca_usd_m: float


@dataclass(frozen=True)
class BateriaCatalogo:
    modelo: str
    kwh: float
    capacidad_calculo_kwh: float  # la que usa BAT!N1 para la inyección (ver A2)
    precio_usd: float
    precio_pdu_usd: float
    precio_rack_usd: float
    min_baterias: int | None
    max_baterias: int | None
    baterias_por_pdu: int | None
    baterias_por_rack: int | None


@dataclass(frozen=True)
class Catalogo:
    version: str
    kits: tuple[KitCatalogo, ...]
    baterias: tuple[BateriaCatalogo, ...]
    margen_baterias: float

    def kit(self, kwp: float) -> KitCatalogo:
        for k in self.kits:
            if abs(k.kwp - kwp) < 1e-6:
                return k
        raise KeyError(f"Kit de {kwp} kWp no está en el catálogo {self.version}")

    def bateria(self, modelo: str) -> BateriaCatalogo:
        for b in self.baterias:
            if b.modelo == modelo:
                return b
        raise KeyError(f"Batería '{modelo}' no está en el catálogo {self.version}")


@dataclass(frozen=True)
class Parametros:
    version: str
    meses: tuple[str, ...]
    dias_mes: tuple[int, ...]
    semanas_mes: tuple[int, ...]
    provincias: tuple[str, ...]
    acimuts: tuple[int, ...]
    inclinaciones: tuple[int, ...]
    hsp: dict[str, list[float]]
    coeficientes: dict[str, dict[str, dict[str, list[float]]]]
    perfil_horario: tuple[tuple[float, ...], ...]  # 12 meses × 13 franjas (7 a 19 h)
    factor_kwp_por_modulo: float
    factores_superficie: dict[str, float]
    huella: dict[str, float]
    degradacion: dict[str, float]
    horas_laborables_max: int
    cos_phi_objetivo: float

    def coeficientes_mes(self, provincia: str, acimut: int, inclinacion: int) -> list[float]:
        try:
            return self.coeficientes[provincia][str(acimut)][str(inclinacion)]
        except KeyError:
            raise KeyError(
                f"Sin coeficientes para provincia={provincia}, acimut={acimut}, inclinación={inclinacion}"
            ) from None

    def factor_degradacion(self, anio: int) -> float:
        """Factor que multiplica al año anterior (año 1 = 1)."""
        if anio <= 1:
            return 1.0
        return self.degradacion["anio_2"] if anio == 2 else self.degradacion["siguientes"]


def _leer(nombre: str) -> dict:
    return json.loads((DATOS / nombre).read_text(encoding="utf-8"))


@cache
def catalogo_vigente() -> Catalogo:
    d = _leer("catalogo.json")
    return Catalogo(
        version=d["version"],
        kits=tuple(KitCatalogo(**k) for k in d["kits"]),
        baterias=tuple(BateriaCatalogo(**b) for b in d["baterias"]),
        margen_baterias=d["margen_baterias"],
    )


@cache
def parametros_vigentes() -> Parametros:
    d = _leer("parametros.json")
    return Parametros(
        version=d["version"],
        meses=tuple(d["meses"]),
        dias_mes=tuple(d["dias_mes"]),
        semanas_mes=tuple(d["semanas_mes"]),
        provincias=tuple(d["provincias"]),
        acimuts=tuple(d["acimuts"]),
        inclinaciones=tuple(d["inclinaciones"]),
        hsp=d["hsp"],
        coeficientes=d["coeficientes"],
        perfil_horario=tuple(tuple(f) for f in d["perfil_horario"]),
        factor_kwp_por_modulo=d["factor_kwp_por_modulo"],
        factores_superficie=d["factores_superficie"],
        huella=d["huella"],
        degradacion=d["degradacion"],
        horas_laborables_max=d["horas_laborables_max"],
        cos_phi_objetivo=d["cos_phi_objetivo"],
    )
