# Estudios de prefactibilidad solar — Dynamic Energy

Aplicación interna que reemplaza el flujo facturas → Excel → PowerPoint.
Especificación: [docs/especificacion.md](docs/especificacion.md) · pendientes en §14.

| Carpeta | Contenido |
|---|---|
| [backend/](backend/) | Motor de cálculo (réplica validada de la planilla), búsqueda de opciones, extracción de facturas con Claude, exportes Excel/PowerPoint y API (FastAPI) |
| [frontend/](frontend/) | Asistente web (Next.js): facturas → consumos → proyecto → opciones → resultados |

## Requisitos

- Python 3.12 o superior
- Node.js 20 o superior (probado con 24 LTS)
- Opcional: API key de Anthropic para leer facturas automáticamente

## Primera vez

Desde la carpeta del repositorio, en una terminal (Git Bash o PowerShell):

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # en Linux/Mac: .venv/bin/python
cd ..

# Frontend
cd frontend
npm install
cd ..
```

## Iniciar el sistema

Hacen falta **dos terminales**, una para cada servidor.

**Terminal 1 — backend (API)**

```bash
cd backend
.venv/Scripts/python -m uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — frontend (aplicación)**

```bash
cd frontend
npm run dev
```

Después abrir **http://localhost:3000**. La documentación interactiva de la API queda en
http://localhost:8000/docs.

### Lectura automática de facturas

Necesita la variable de entorno `ANTHROPIC_API_KEY` en la terminal del backend
**antes** de iniciarlo:

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

```bash
# Git Bash / Linux / Mac
export ANTHROPIC_API_KEY="sk-ant-..."
```

Sin la key la aplicación funciona igual: avisa que la extracción no está configurada
y los consumos se cargan a mano.

### Configuración opcional

| Variable | Dónde | Para qué |
|---|---|---|
| `ANTHROPIC_API_KEY` | backend | Extracción de facturas |
| `EXTRACCION_MODELO` | backend | Modelo de Claude (por defecto `claude-opus-5-5`) |
| `EXTRACCION_ESFUERZO` | backend | `low` / `medium` / `high` (por defecto `high`) |
| `NEXT_PUBLIC_API_URL` | frontend | URL del backend si no es `http://localhost:8000` |

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest
```

Ver [backend/README.md](backend/README.md) para regenerar los casos de equivalencia con Excel.

## Problemas comunes

- **"No se pudo conectar con el servidor"** en la app: el backend no está corriendo (terminal 1).
- **`npm` no se reconoce** en una terminal abierta antes de instalar Node: cerrarla y abrir una nueva.
- **Empezar de cero**: botón "Nueva propuesta" arriba a la derecha. Hasta que exista la base de
  datos (SQLite), la propuesta en curso se guarda en el navegador.
