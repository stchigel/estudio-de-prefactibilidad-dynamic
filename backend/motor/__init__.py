"""Motor de cálculo de prefactibilidad solar (§6). Sin dependencias web."""

from .calculo import calcular
from .catalogo import Catalogo, Parametros, catalogo_vigente, parametros_vigentes
from .modelos import Entradas, Resultado

__all__ = [
    "Catalogo",
    "Entradas",
    "Parametros",
    "Resultado",
    "calcular",
    "catalogo_vigente",
    "parametros_vigentes",
]
