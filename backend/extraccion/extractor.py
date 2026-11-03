"""Extracción de facturas con IA (§5.2).

El documento se manda tal cual (PDF con texto, PDF escaneado o foto) y la
salida se valida contra FacturaExtraida.

Proveedor según EXTRACCION_PROVEEDOR:
  - "gemini" (por defecto, para pruebas): plan gratuito de Google AI Studio.
    Credencial: GEMINI_API_KEY. Ojo: en el plan gratis Google usa el contenido
    para mejorar sus productos; no usarlo con datos sensibles en producción.
  - "claude": API de Anthropic, recomendado para producción.
    Credencial: ANTHROPIC_API_KEY (o `ant auth login`).
"""

from __future__ import annotations

import base64
import logging
import os

from .esquema import FacturaExtraida

logger = logging.getLogger(__name__)

MODELOS_POR_DEFECTO = {"gemini": "gemini-3.5-flash", "claude": "claude-sonnet-5-5"}
# Si el modelo de Gemini está sobrecargado o agotó su cupo diario gratuito (cada modelo
# tiene el suyo, p. ej. 20 pedidos/día en gemini-3.8-flash), se prueban estos.
RESPALDOS_GEMINI = ["gemini-3.1-flash-lite", "gemini-3.8-flash"]


# Se leen en cada llamada para respetar el .env cargado al iniciar la API.
def proveedor() -> str:
    return os.environ.get("EXTRACCION_PROVEEDOR", "gemini").strip().lower()


def modelo() -> str:
    return os.environ.get("EXTRACCION_MODELO") or MODELOS_POR_DEFECTO.get(proveedor(), "")


def esfuerzo() -> str:  # solo Claude
    return os.environ.get("EXTRACCION_ESFUERZO", "low")

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
- precio_kwh_resto: el precio unitario por kWh de la energía en la franja resto (sin impuestos), como figura en su renglón. No uses el importe total ni el básico dividido por los kWh: eso incluye cargos fijos y de potencia que la generación solar no reduce.
- cargo_factor_potencia: true solo si hay un renglón que cobra cargo o recargo por factor de potencia (coseno phi bajo). Si el factor de potencia solo se informa, o no figura, false.
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
PEDIDO = "Extraé los datos de esta factura."


class ExtraccionNoConfigurada(RuntimeError):
    """No hay credenciales del proveedor de IA configuradas."""


class ExtraccionFallida(RuntimeError):
    pass


def _validar_tipo(media_type: str) -> None:
    if media_type != TIPO_PDF and media_type not in TIPOS_IMAGEN:
        raise ValueError(f"Tipo de archivo no soportado: {media_type}. Usar PDF, JPG o PNG.")


def extraer_factura(contenido: bytes, media_type: str, cliente=None) -> FacturaExtraida:
    """Extrae los datos de una factura con el proveedor configurado.

    `cliente` permite inyectar el cliente del SDK (tests).
    """
    _validar_tipo(media_type)
    match proveedor():
        case "gemini":
            return _extraer_con_gemini(contenido, media_type, cliente)
        case "claude":
            return _extraer_con_claude(contenido, media_type, cliente)
        case otro:
            raise ExtraccionNoConfigurada(f"EXTRACCION_PROVEEDOR desconocido: {otro!r} (usar 'gemini' o 'claude')")


# ------------------------------------------------------------------ Gemini


def _extraer_con_gemini(contenido: bytes, media_type: str, cliente=None) -> FacturaExtraida:
    from google import genai
    from google.genai import errors, types

    # El plan gratuito responde seguido 503 (sobrecarga): se reintenta con espera creciente
    # (2 y 4 s) y después se pasa al modelo de respaldo. Los 429 no se reintentan: cada
    # intento consume el cupo diario.
    reintentos = types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=3, initial_delay=2, max_delay=10, http_status_codes=[500, 502, 503, 504])
    )
    try:
        cliente = cliente or genai.Client(http_options=reintentos)  # lee GEMINI_API_KEY
    except ValueError as exc:
        raise ExtraccionNoConfigurada("Falta configurar GEMINI_API_KEY") from exc

    documento = types.Part.from_bytes(
        data=contenido,
        mime_type=media_type,
        media_resolution=types.PartMediaResolutionLevel.MEDIA_RESOLUTION_HIGH,  # letra chica de las facturas
    )
    modelos = [modelo()] + [m for m in RESPALDOS_GEMINI if m != modelo()]
    for i, nombre in enumerate(modelos):
        try:
            respuesta = cliente.models.generate_content(
                model=nombre,
                contents=[documento, PEDIDO],
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCCIONES,
                    response_mime_type="application/json",
                    response_json_schema=FacturaExtraida.model_json_schema(),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # no usa herramientas
                ),
            )
            break
        except errors.ClientError as exc:
            if exc.code in (401, 403) or "API_KEY" in str(exc):
                raise ExtraccionNoConfigurada("La API key de Gemini es inválida") from exc
            if exc.code != 429:
                raise ExtraccionFallida(f"Error de la API de Gemini ({exc.code}): {exc.message}") from exc
            por_dia = "PerDay" in str(exc)
            if i == len(modelos) - 1:
                raise ExtraccionFallida(
                    "Se agotó el cupo diario gratuito de Gemini en todos los modelos; se renueva en unas horas"
                    if por_dia
                    else "Se alcanzó el límite por minuto del plan gratuito de Gemini; esperar un minuto y reintentar"
                ) from exc
            logger.warning("Gemini %s: límite %s alcanzado; se prueba %s", nombre, "diario" if por_dia else "por minuto", modelos[i + 1])
        except errors.ServerError as exc:
            if i == len(modelos) - 1:
                raise ExtraccionFallida(
                    f"Gemini está sobrecargado ({exc.code}) en todos los modelos gratuitos; reintentar en unos minutos"
                ) from exc
            logger.warning("Gemini %s sobrecargado (%s); se prueba %s", nombre, exc.code, modelos[i + 1])

    candidatos = respuesta.candidates or []
    fin = str(getattr(candidatos[0], "finish_reason", "") or "") if candidatos else ""
    if "MAX_TOKENS" in fin:
        raise ExtraccionFallida("La respuesta quedó incompleta; reintentar")
    if not respuesta.text:
        raise ExtraccionFallida(f"Gemini no devolvió datos ({fin or 'sin respuesta'})")
    try:
        return FacturaExtraida.model_validate_json(respuesta.text)
    except ValueError as exc:
        raise ExtraccionFallida("La respuesta de Gemini no respeta el formato esperado; reintentar") from exc


# ------------------------------------------------------------------ Claude (desactivado para pruebas)


def _extraer_con_claude(contenido: bytes, media_type: str, cliente=None) -> FacturaExtraida:
    import anthropic

    datos = base64.standard_b64encode(contenido).decode("ascii")
    tipo_bloque = "document" if media_type == TIPO_PDF else "image"
    bloque = {"type": tipo_bloque, "source": {"type": "base64", "media_type": media_type, "data": datos}}
    cliente = cliente or anthropic.Anthropic()
    try:
        respuesta = cliente.beta.messages.parse(
            model=modelo(),
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": esfuerzo()},
            system=INSTRUCCIONES,
            messages=[{"role": "user", "content": [bloque, {"type": "text", "text": PEDIDO}]}],
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
