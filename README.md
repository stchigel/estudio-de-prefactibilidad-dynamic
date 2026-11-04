# Estudios de prefactibilidad solar — Dynamic Energy

Aplicación interna que reemplaza el flujo facturas → Excel → PowerPoint.
Especificación: [docs/especificacion.md](docs/especificacion.md) · pendientes en §14.

| Carpeta | Contenido |
|---|---|
| [backend/](backend/) | Motor de cálculo (réplica validada de la planilla), búsqueda de opciones, lectura de facturas con IA (Gemini o Claude), exportes Excel/PowerPoint y API (FastAPI) |
| [frontend/](frontend/) | Asistente web (Next.js): facturas → consumos → proyecto → opciones → resultados |

## Requisitos

- Python 3.12 o superior
- Node.js 20 o superior (probado con 24 LTS)
- Opcional: API key de Gemini (Google) o de Claude (Anthropic) para leer facturas automáticamente

## Primer paso: configurar la API key (Windows)

Doble clic en **`setup-key.bat`**, en la carpeta del repositorio. El script:

1. Crea `backend/.env` a partir de `backend/.env.example` (si ya existe lo conserva y solo actualiza lo que sigue).
2. Pide elegir el proveedor de IA, **Gemini** o **Claude**, con las flechas arriba/abajo y Enter.
3. Pide pegar la API key (no se muestra en pantalla) y completa el `.env` con el proveedor y la key.

La key se obtiene en https://aistudio.google.com/apikey (Gemini) o https://console.anthropic.com (Claude).
Se puede volver a correr cuando haga falta cambiar de proveedor o de key; después hay que reiniciar el sistema.
Este paso es opcional: sin key la aplicación funciona igual y los consumos se cargan a mano.

## Iniciar el sistema (Windows)

Doble clic en el script de la carpeta del repositorio:

| Script | Para qué |
|---|---|
| `setup-key.bat` | Configura el proveedor de IA y su API key en `backend/.env` (ver "Primer paso") |
| `iniciar.bat` | Uso normal. Compila el frontend y abre backend y frontend en dos ventanas; al terminar abre el navegador y muestra la dirección para otras PCs (Tailscale) |
| `iniciar-desarrollo.bat` | Para trabajar en el código: recarga automática al guardar cambios |
| `detener.bat` | Apaga los dos servidores (también alcanza con cerrar sus ventanas) |

La primera vez los scripts instalan solos las dependencias si faltan. Después de actualizar
el código con dependencias nuevas, correr los comandos de "Primera vez".

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

## Iniciar a mano

Sin los scripts hacen falta **dos terminales**, una para cada servidor.

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

Se configura en el archivo **`backend/.env`** (no se sube al repositorio). En Windows lo más
simple es correr `setup-key.bat` (ver "Primer paso"). A mano: copiar `backend/.env.example`
como `backend/.env` y completar según el proveedor.

**Gemini** (key en https://aistudio.google.com/apikey → "Create API key"):

```
EXTRACCION_PROVEEDOR=gemini
GEMINI_API_KEY=la-key-copiada
```

**Claude** (key en https://console.anthropic.com):

```
EXTRACCION_PROVEEDOR=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Después reiniciar el backend (terminal 1: Ctrl+C y volver a iniciarlo).

> En el plan gratuito de Gemini, Google usa el contenido enviado para mejorar sus productos;
> tenerlo en cuenta si se procesan facturas reales de clientes.

Sin key la aplicación funciona igual: avisa que la lectura no está configurada y los
consumos se cargan a mano.

### Configuración opcional (`backend/.env`)

| Variable | Para qué |
|---|---|
| `EXTRACCION_PROVEEDOR` | `gemini` (por defecto) o `claude` |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | Key del proveedor elegido |
| `EXTRACCION_MODELO` | Forzar un modelo (por defecto `gemini-3.5-flash` / `claude-sonnet-5-5`) |
| `EXTRACCION_ESFUERZO` | Solo Claude: `low` (por defecto) / `medium` / `high` |

El frontend reenvía las llamadas a `/api` al backend (`BACKEND_URL`, por defecto
`http://127.0.0.1:8000`), así que desde otras PCs solo hace falta llegar al puerto 3000.
Para abrir la aplicación en modo desarrollo desde otra IP o nombre de host, agregarlo a
`allowedDevOrigins` en [frontend/next.config.ts](frontend/next.config.ts).

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
