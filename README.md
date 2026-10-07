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
- Opcional: API key de Gemini (pruebas) o de Anthropic (producción) para leer facturas automáticamente

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

La lectura de facturas con IA se configura en el archivo **`backend/.env`** (no se sube
al repositorio). Si no existe, copiar `backend/.env.example` como `backend/.env`.

**Para pruebas: Gemini (gratis)**

1. Entrar a https://aistudio.google.com/apikey con una cuenta de Google.
2. "Create API key" → copiar la key.
3. Pegarla en `backend/.env`:

   ```
   EXTRACCION_PROVEEDOR=gemini
   GEMINI_API_KEY=la-key-copiada
   ```

4. Reiniciar el backend (terminal 1: Ctrl+C y volver a iniciarlo).

> En el plan gratuito Google usa el contenido enviado para mejorar sus productos.
> Sirve para probar; para facturas reales de clientes en producción usar Claude.

**Para producción: Claude**

```
EXTRACCION_PROVEEDOR=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Sin key la aplicación funciona igual: avisa que la lectura no está configurada y los
consumos se cargan a mano.

### Configuración opcional (`backend/.env`)

| Variable | Para qué |
|---|---|
| `EXTRACCION_PROVEEDOR` | `gemini` (por defecto) o `claude` |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | Key del proveedor elegido |
| `EXTRACCION_MODELO` | Forzar un modelo (por defecto `gemini-3.8-flash` / `claude-sonnet-5-5`) |
| `EXTRACCION_ESFUERZO` | Solo Claude: `low` (por defecto) / `medium` / `high` |

En el frontend, `NEXT_PUBLIC_API_URL` permite apuntar a un backend que no esté en
`http://localhost:8000`.

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
