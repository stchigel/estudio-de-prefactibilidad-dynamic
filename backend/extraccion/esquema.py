"""Datos que se extraen de una factura de distribuidora (§5.2).

Los escalares van envueltos con su confianza (0–1) para resaltar en la
revisión los campos dudosos (§5.5).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

Provincia = Literal[
    "Buenos Aires", "CABA AMBA", "Catamarca", "Chaco", "Chubut", "Córdoba", "Corrientes",
    "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones",
    "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe",
    "Santiago del Estero", "Tierra del Fuego", "Tucumán",
]  # mismos nombres que TRANSP!U1:AR1


class TipoDocumento(StrEnum):
    DISTRIBUIDORA = "factura_distribuidora"
    CAMMESA = "factura_cammesa"
    GENERADORA = "factura_generadora"
    OTRO = "otro"


class Jurisdiccion(StrEnum):
    NACIONAL = "nacional"
    PROVINCIAL = "provincial"
    MUNICIPAL = "municipal"
    IVA = "iva"
    OTRO = "otro"


class Texto(BaseModel):
    valor: str | None
    confianza: float = Field(description="0 a 1")


class Numero(BaseModel):
    valor: float | None
    confianza: float = Field(description="0 a 1")


class ProvinciaCampo(BaseModel):
    valor: Provincia | None
    confianza: float = Field(description="0 a 1")


class Impuesto(BaseModel):
    nombre: str
    jurisdiccion: Jurisdiccion
    porcentaje: float | None = Field(description="Alícuota en %, ej. 6.0 para 6 %. Null si es un monto fijo")
    base: str | None = Field(description="Sobre qué se aplica, tal como figura (ej. 'S/Subtotal')")
    importe: float | None


class MesHistorial(BaseModel):
    anio: int
    mes: int = Field(description="1 a 12")
    kwh_pico: float | None
    kwh_resto: float | None
    kwh_valle: float | None
    kwh_total: float | None
    kw_pico: float | None
    kw_fuera_pico: float | None
    leido_de_grafico: bool = Field(description="True si el valor se estimó leyendo un gráfico de barras")
    confianza: float = Field(description="0 a 1")


class FacturaExtraida(BaseModel):
    tipo_documento: TipoDocumento
    distribuidora: Texto
    cliente_razon_social: Texto
    cliente_cuit: Texto
    domicilio_suministro: Texto
    provincia: ProvinciaCampo
    tarifa: Texto
    periodo_anio: Numero
    periodo_mes: Numero = Field(description="Mes facturado, 1 a 12")
    dias_facturados: Numero
    potencia_contratada_pico_kw: Numero
    potencia_contratada_fuera_pico_kw: Numero
    kwh_pico: Numero
    kwh_resto: Numero
    kwh_valle: Numero
    kwh_total: Numero
    kw_registrados_pico: Numero
    kw_registrados_fuera_pico: Numero
    importe_basico_energia: Numero = Field(
        description="Importe básico / subtotal del servicio antes de tasas e impuestos ($)"
    )
    importe_energia_activa: Numero = Field(
        description="Solo los cargos por energía activa consumida ($), sin cargos fijos ni de potencia"
    )
    impuestos: list[Impuesto]
    importe_total: Numero
    energia_reactiva_kvarh: Numero
    historial: list[MesHistorial]
    notas: str = Field(description="Observaciones para quien revisa: datos ilegibles, ambigüedades, formato raro")
