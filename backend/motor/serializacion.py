"""Conversión de Entradas/Resultado a dict JSON y de vuelta (snapshot §11)."""

from __future__ import annotations

import dataclasses
import types
import typing
from datetime import date
from enum import Enum
from typing import Any

from .modelos import Entradas


def a_dict(obj: Any) -> Any:
    """Dataclasses/enums/fechas → tipos JSON."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: a_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): a_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [a_dict(v) for v in obj]
    return obj


def entradas_desde_dict(datos: dict[str, Any]) -> Entradas:
    return _construir(Entradas, datos)


def _construir(tipo: Any, valor: Any) -> Any:
    if valor is None:
        return None
    origen = typing.get_origin(tipo)
    if origen in (typing.Union, types.UnionType):
        no_nulos = [t for t in typing.get_args(tipo) if t is not type(None)]
        return _construir(no_nulos[0], valor)
    if origen is list:
        (interno,) = typing.get_args(tipo)
        return [_construir(interno, v) for v in valor]
    if dataclasses.is_dataclass(tipo):
        pistas = typing.get_type_hints(tipo)
        nombres = {f.name for f in dataclasses.fields(tipo) if f.init}
        desconocidos = set(valor) - nombres
        if desconocidos:
            raise ValueError(f"Campos desconocidos en {tipo.__name__}: {sorted(desconocidos)}")
        return tipo(**{k: _construir(pistas[k], v) for k, v in valor.items()})
    if isinstance(tipo, type) and issubclass(tipo, Enum):
        return tipo(valor)
    if tipo is date:
        return date.fromisoformat(valor)
    if tipo is float:
        return float(valor)
    return valor
