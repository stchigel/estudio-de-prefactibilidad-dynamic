"""Extracción de facturas con Claude (§5.2).

Se manda el documento tal cual: los PDF con texto y los escaneados van como
bloque `document` (Claude lee también las páginas como imagen) y las fotos
como bloque `image`. La salida se valida contra FacturaExtraida.

Credenciales: variable de entorno ANTHROPIC_API_KEY (o `ant auth login`).
"""

from __future__ import annotations

import base64
import os

import anthropic

from .esquema import FacturaExtraida

MODELO = os.environ.get("EXTRACCION_MODELO", "claude-opus-5-5")
ESFUERZO = os.environ.get("EXTRACCION_ESFUERZO", "high")

TIPOS_IMAGEN = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TIPO_PDF = "application/pdf"

INSTRUCCIONES = """\
Sos un analista de Dynamic Energy que lee facturas de energía eléctrica argentinas \
para estudios de prefactibilidad solar. Extraé los datos de la factura adjunta.

Criterios:
- Copiá los números tal como figuran, convertidos a número (formato argentino: \
"12.960.728,37" = 12960728.37). No inventes datos: si un campo no figura, valor null \
y confianza 1. Usá confianza baja cuando el dato está borroso, cortado o lo inferiste.
- periodo_anio/periodo_mes: el mes de consumo que se factura (no la fecha de emisión).
- Franjas horarias: pico, resto y valle. Si la tarifa no discrimina franjas, dejá \
pico/resto/valle en null y completá solo kwh_total.
- importe_basico_energia: el importe básico o subtotal del servicio antes de tasas, \
contribuciones e impuestos. importe_energia_activa: solo los renglones de energía \
activa consumida (sin cargo comercial/fijo ni cargos por capacidad o potencia).
- impuestos: cada renglón de tasa, contribución, ley u ordenanza e IVA, con su \
alícuota en % si figura. Jurisdicción: "municipal" para ordenanzas y tasas \
municipales, "provincial" para leyes y fondos provinciales, "nacional" para leyes \
nacionales, "iva" para IVA y percepciones de IVA.
- historial: todos los meses de la tabla o gráfico de consumos anteriores, \
incluido el mes facturado si aparece. Si solo hay un gráfico de barras sin valores, \
estimá cada barra con la escala del eje, marcá leido_de_grafico=true y confianza ≤ 0,5.
- provincia: la del domicilio del suministro, con el nombre exacto de la lista.
- tipo_documento: factura de distribuidora, de CAMMESA, de generadora (contratos \
MAT/GUME) u otro documento.
"""


class ExtraccionNoConfigurada(RuntimeError):
    """No hay credenciales de Anthropic configuradas."""


class ExtraccionFallida(RuntimeError):
    pass


def _bloque_documento(contenido: bytes, media_type: str) -> dict:
    datos = base64.standard_b64encode(contenido).decode("ascii")
    if media_type == TIPO_PDF:
        return {"type": "document", "source": {"type": "base64", "media_type": TIPO_PDF, "data": datos}}
    if media_type in TIPOS_IMAGEN:
        return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": datos}}
    raise ValueError(f"Tipo de archivo no soportado: {media_type}. Usar PDF, JPG o PNG.")


def extraer_factura(
    contenido: bytes, media_type: str, cliente: anthropic.Anthropic | None = None
) -> FacturaExtraida:
    bloque = _bloque_documento(contenido, media_type)
    cliente = cliente or anthropic.Anthropic()
    try:
        respuesta = cliente.beta.messages.parse(
            model=MODELO,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": ESFUERZO},
            system=INSTRUCCIONES,
            messages=[{"role": "user", "content": [bloque, {"type": "text", "text": "Extraé los datos de esta factura."}]}],
            output_format=FacturaExtraida,
        )
    except anthropic.AuthenticationError as exc:
        raise ExtraccionNoConfigurada("La API key de Anthropic es inválida") from exc
    except TypeError as exc:
        if "authentication" in str(exc).lower():
            raise ExtraccionNoConfigurada("Falta configurar ANTHROPIC_API_KEY") from exc
        raise
    except anthropic.APIStatusError as exc:
        raise ExtraccionFallida(f"Error de la API de Claude ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ExtraccionFallida("No se pudo conectar con la API de Claude") from exc

    if respuesta.stop_reason == "refusal":
        raise ExtraccionFallida("Claude no procesó el documento")
    if respuesta.stop_reason == "max_tokens" or respuesta.parsed_output is None:
        raise ExtraccionFallida("La respuesta quedó incompleta; reintentar")
    return respuesta.parsed_output
