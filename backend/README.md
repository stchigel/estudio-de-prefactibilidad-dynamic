# Backend — Prefactibilidad Solar

Implementa la especificación de [docs/especificacion.md](../docs/especificacion.md).

| Carpeta | Contenido |
|---|---|
| `motor/` | Motor de cálculo puro (§6): réplica de la planilla, sin dependencias web |
| `motor/provisorios.py` | Comportamientos provisorios A1–A5 (§14.2), aislados para cambiarlos fácil |
| `motor/datos/` | Catálogo y parámetros extraídos de la planilla (§9) |
| `exportes/excel.py` | Exporte a la planilla original (§10.1), editando el XML para no perder gráficos |
| `api/` | API FastAPI (Etapa 1: sin persistencia) |
| `scripts/` | Extracción de parámetros y generación de casos de equivalencia con Excel |
| `tests/casos/` | Casos de equivalencia: entradas + salidas recalculadas por Excel |

## Instalación

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Linux/Mac: .venv/bin/python
```

## Uso

```bash
.venv/Scripts/python -m pytest                     # tests
.venv/Scripts/python -m uvicorn api.main:app --reload   # API en http://localhost:8000/docs
```

## Equivalencia con la planilla (§12)

`tests/test_equivalencia_excel.py` compara el motor contra resultados que calculó
Excel con tolerancia relativa 1e-6. Los esperados se regeneran (Windows con Excel
instalado) con:

```bash
.venv/Scripts/python scripts/generar_casos_excel.py            # todos los casos
.venv/Scripts/python scripts/generar_casos_excel.py plecor     # uno
```

Los casos se definen en `tests/casos/definiciones.py`. Si cambia la planilla,
volver a correr también `scripts/extraer_parametros.py`.

## Plantilla del PowerPoint (§10.2)

El generador (`exportes/powerpoint.py`) completa `exportes/plantillas/prefactibilidad.pptx`,
una copia de la plantilla del equipo con marcas `{{...}}` en lugar de los "xxx". Esa copia
se arma con:

```bash
.venv/Scripts/python scripts/preparar_plantilla_ppt.py "ruta/a/Presentación prefactibilidad SOLAR.pptx"
```

Cuando el equipo mande una plantilla nueva, correr el script con ella: si algún texto
esperado cambió, falla indicando cuál, y hay que ajustar el script. Para revisar el
resultado conviene abrir una presentación generada en PowerPoint (los tests verifican
contenido, no la disposición visual).
