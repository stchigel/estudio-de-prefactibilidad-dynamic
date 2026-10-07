"""API HTTP (§4). Etapa 1: endpoints sin estado sobre el motor y el exporte Excel.

Correr:  uvicorn api.main:app --reload   (desde backend/)
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import UnidentifiedImageError
from pydantic import BaseModel, ValidationError
from starlette.background import BackgroundTask

from exportes.excel import exportar_excel
from exportes.powerpoint import DatosPpt, OpcionPpt, generar_ppt
from extraccion.derivados import sugerir
from extraccion.esquema import FacturaExtraida
from extraccion.extractor import ExtraccionFallida, ExtraccionNoConfigurada, extraer_factura
from motor import calcular, catalogo_vigente, parametros_vigentes
from motor.consumos import LecturaMensual, consolidar
from motor.modelos import (
    HORAS_POR_DIA,
    PERIODOS_EVALUACION,
    Alerta,
    Categoria,
    ConsumoMensual,
    Entradas,
    HorarioTrabajo,
    Instalacion,
    Inversor,
    Kit,
    Moneda,
    ObjetivoBaterias,
    OrigenSuperficie,
    TipoFinanciacion,
    TipoInversor,
)
from motor.opciones import buscar_opciones
from motor.serializacion import a_dict
from motor.validaciones import sugerir_pdu_rack, validar

app = FastAPI(title="Prefactibilidad Solar — Dynamic Energy", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(KeyError)
async def _clave_desconocida(_, exc: KeyError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=422, content={"detail": str(exc.args[0])})


@app.get("/api/salud")
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@app.get("/api/opciones")
def opciones() -> dict[str, Any]:
    """Listas para el formulario (§6.1) y catálogo vigente."""
    cat, par = catalogo_vigente(), parametros_vigentes()
    return {
        "version_catalogo": cat.version,
        "version_parametros": par.version,
        "provincias": par.provincias,
        "acimuts": par.acimuts,
        "inclinaciones": par.inclinaciones,
        "horas_por_dia": HORAS_POR_DIA,
        "periodos_evaluacion": PERIODOS_EVALUACION,
        "categorias": [c.value for c in Categoria],
        "horarios": [h.value for h in HorarioTrabajo],
        "tipos_inversor": [t.value for t in TipoInversor],
        "instalaciones": [i.value for i in Instalacion],
        "inversores": [i.value for i in Inversor],
        "objetivos_baterias": [o.value for o in ObjetivoBaterias],
        "tipos_financiacion": [t.value for t in TipoFinanciacion],
        "monedas": [m.value for m in Moneda],
        "origenes_superficie": [o.value for o in OrigenSuperficie],
        "kits": [a_dict(k) for k in cat.kits],
        "baterias": [a_dict(b) for b in cat.baterias],
    }


# Errores que impiden calcular (búsquedas en catálogo/parámetros).
ERRORES_BLOQUEANTES = {
    "provincia_desconocida",
    "acimut_invalido",
    "inclinacion_invalida",
    "kit_desconocido",
    "baterias_modelo",
    "sin_potencia",
    "dolar_invalido",
    "comision_invalida",
}


@app.post("/api/calcular")
def calcular_propuesta(entradas: Entradas) -> dict[str, Any]:
    bloqueantes = [
        a for a in validar(entradas, catalogo_vigente(), parametros_vigentes()) if a.codigo in ERRORES_BLOQUEANTES
    ]
    if bloqueantes:
        raise HTTPException(422, [a_dict(a) for a in bloqueantes])
    try:
        return a_dict(calcular(entradas))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/opciones/buscar")
def buscar(entradas: Entradas) -> dict[str, Any]:
    """Opciones automáticas (§7). Los kits de las entradas se ignoran."""
    bloqueantes = [
        a
        for a in validar(entradas, catalogo_vigente(), parametros_vigentes())
        if a.codigo in ERRORES_BLOQUEANTES - {"kit_desconocido", "sin_potencia"}
    ]
    if bloqueantes:
        raise HTTPException(422, [a_dict(a) for a in bloqueantes])
    return a_dict(buscar_opciones(entradas))


class PedidoPpt(BaseModel):
    entradas: Entradas
    incluir_opciones: bool = True
    texto_bancario: str | None = None


def _mismos_kits(a: Kit, b: Kit | None, c: Kit, d: Kit | None) -> bool:
    clave = lambda k: None if k is None or k.cantidad == 0 else (k.kwp, k.cantidad)  # noqa: E731
    return clave(a) == clave(c) and clave(b) == clave(d)


@app.post("/api/exportes/ppt")
async def exportar_ppt(
    datos: str = Form(..., description="JSON de PedidoPpt"),
    logo: UploadFile | None = None,
    planta: UploadFile | None = None,
    montaje: UploadFile | None = None,
) -> Response:
    """Presentación de la propuesta (§10.2) con la opción de las entradas como elegida."""
    try:
        pedido = PedidoPpt.model_validate_json(datos)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False)) from exc
    e = pedido.entradas
    bloqueantes = [a for a in validar(e, catalogo_vigente(), parametros_vigentes()) if a.codigo in ERRORES_BLOQUEANTES]
    if bloqueantes:
        raise HTTPException(422, [a_dict(a) for a in bloqueantes])

    resultado = calcular(e)
    opciones: list[OpcionPpt] = []
    limitado = False
    if pedido.incluir_opciones:
        busqueda = await run_in_threadpool(buscar_opciones, e)
        limitado = busqueda.limitado_por_potencia
        for o in busqueda.opciones:
            elegida = _mismos_kits(o.kit1, o.kit2, e.kit1, e.kit2)
            opciones.append(OpcionPpt(o.kit1, o.kit2, o.recomendada, resultado if elegida else o.resultado))
        if not any(o.resultado is resultado for o in opciones):
            opciones.append(OpcionPpt(e.kit1, e.kit2, False, resultado))
            opciones.sort(key=lambda o: o.resultado.energia.cobertura)

    imagenes = {}
    for nombre, archivo in (("logo", logo), ("planta", planta), ("montaje", montaje)):
        if archivo is not None:
            contenido = await archivo.read()
            if contenido:
                imagenes[nombre] = contenido
    try:
        contenido = await run_in_threadpool(
            generar_ppt,
            DatosPpt(e, resultado, opciones, limitado, pedido.texto_bancario, imagenes),
        )
    except UnidentifiedImageError as exc:
        raise HTTPException(415, "Alguna de las imágenes no es un JPG o PNG válido") from exc

    nombre = re.sub(r"[^\w\- ]", "", f"{e.numero_propuesta or ''} {e.cliente}").strip() or "propuesta"
    return Response(
        contenido,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{quote(nombre + ' Prefactibilidad SOLAR.pptx')}"},
    )


TAMANIO_MAXIMO_FACTURA = 30 * 1024 * 1024  # límite de la API de Claude: 32 MB por pedido


@app.post("/api/facturas/extraer")
async def extraer_facturas(archivos: list[UploadFile]) -> dict[str, Any]:
    """Extrae cada factura (§5.2) y devuelve los datos sugeridos para el formulario (§5.3–5.4)."""
    extraidas = []
    for archivo in archivos:
        contenido = await archivo.read()
        if len(contenido) > TAMANIO_MAXIMO_FACTURA:
            raise HTTPException(413, f"{archivo.filename}: supera 30 MB")
        try:
            factura = await run_in_threadpool(extraer_factura, contenido, archivo.content_type or "")
        except ExtraccionNoConfigurada as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(415, f"{archivo.filename}: {exc}") from exc
        except ExtraccionFallida as exc:
            raise HTTPException(502, f"{archivo.filename}: {exc}") from exc
        extraidas.append({"archivo": archivo.filename, "datos": factura.model_dump(mode="json")})
    sugerencias = sugerir([FacturaExtraida.model_validate(e["datos"]) for e in extraidas])
    return {"facturas": extraidas, "sugerencias": a_dict(sugerencias)}


@app.post("/api/validar")
def validar_entradas(entradas: Entradas) -> list[Alerta]:
    return validar(entradas, catalogo_vigente(), parametros_vigentes())


class PedidoPduRack(BaseModel):
    modelo: str
    cantidad: int


@app.post("/api/baterias/sugerir")
def sugerir_baterias(pedido: PedidoPduRack) -> dict[str, int]:
    pdu, rack = sugerir_pdu_rack(catalogo_vigente().bateria(pedido.modelo), pedido.cantidad)
    return {"cantidad_pdu": pdu, "cantidad_rack": rack}


@app.post("/api/consumos/consolidar")
def consolidar_consumos(lecturas: list[LecturaMensual]) -> list[ConsumoMensual | None]:
    return consolidar(lecturas)


@app.post("/api/exportes/excel")
def exportar(entradas: Entradas) -> FileResponse:
    carpeta = Path(tempfile.mkdtemp(prefix="exporte-"))
    nombre = re.sub(r"[^\w\- ]", "", f"{entradas.numero_propuesta or ''} {entradas.cliente}").strip() or "propuesta"
    ruta = exportar_excel(entradas, carpeta / f"{nombre} Prefactibilidad.xlsx")
    return FileResponse(
        ruta,
        filename=ruta.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: (ruta.unlink(missing_ok=True), carpeta.rmdir())),
    )
