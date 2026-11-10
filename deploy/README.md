# Publicar en internet

El sistema se parte en dos:

| Parte | Dónde corre | Qué es |
|---|---|---|
| **Frontend** (asistente, gráficos) | Hosting con cPanel | Archivos estáticos HTML/JS; no hace falta Node ni Python ahí |
| **Backend** (cálculo, IA, PowerPoint/Excel, API keys) | Un VPS (por ejemplo Hetzner) | FastAPI con systemd + Caddy (HTTPS automático) |

Las dos partes deben estar en **subdominios del mismo dominio** (por ejemplo `app.tuempresa.com` y
`api.tuempresa.com`): así la cookie de sesión viaja sin configuración extra.

> Para uso en una sola PC no hace falta nada de esto: `iniciar.bat` sigue funcionando igual.

## 1. DNS

Crear dos registros en la zona DNS del dominio (en cPanel: *Editor de zona*):

- `api` → registro **A** con la IP del VPS.
- `app` → el subdominio que apunta al hosting cPanel (crearlo en *Dominios* y anotar su carpeta raíz).

## 2. Backend en el VPS

Servidor recomendado: Ubuntu 24.04 (trae Python 3.12), 2 vCPU y 2–4 GB de RAM alcanzan para 2 usuarios a la vez.
Conviene activar los backups automáticos del proveedor y entrar por clave SSH.

```bash
sudo git clone <url-del-repositorio> /opt/prefactibilidad     # o copiar la carpeta con scp
cd /opt/prefactibilidad
sudo ./deploy/instalar-servidor.sh api.tuempresa.com https://app.tuempresa.com
```

El script pregunta la contraseña de acceso y la API key de IA, y deja instalado el servicio
(`prefactibilidad`), Caddy con HTTPS y el firewall (solo SSH, 80 y 443). El DNS de `api` tiene que apuntar
al servidor *antes* de correrlo. Si la key se carga después: editar `backend/.env` y
`sudo systemctl restart prefactibilidad`.

Comprobar: `curl https://api.tuempresa.com/api/salud` → `{"estado":"ok"}`.

## 3. Frontend en cPanel

En tu PC, desde `frontend/`:

```bash
# PowerShell
$env:NEXT_PUBLIC_API_URL="https://api.tuempresa.com"; npm run build:estatico
# Linux / macOS / Git Bash
NEXT_PUBLIC_API_URL=https://api.tuempresa.com npm run build:estatico
```

Queda el sitio en `frontend/out/`. Subir **el contenido** de esa carpeta (comprimido en .zip y extraído desde el
*Administrador de archivos*) a la carpeta raíz del subdominio `app`. Activar en cPanel *Forzar redireccionamiento
HTTPS* para ese dominio.

- `out/` incluye un `.htaccess` (archivo oculto) para que, después de actualizar, el navegador no siga mostrando la
  versión vieja. Subirlo también; en el *Administrador de archivos* se ve activando "Mostrar archivos ocultos".
- La URL de la API queda escrita en los archivos al compilar: si cambia, hay que compilar y subir de nuevo.
- Publicarlo en una subcarpeta (`tuempresa.com/prefactibilidad`) no está soportado; usar un subdominio.

## 4. Probar

Abrir `https://app.tuempresa.com`: debe pedir la contraseña y, al entrar, funcionar igual que en local.

## Mantenimiento

| Tarea | Comando |
|---|---|
| Actualizar el backend | `sudo ./deploy/actualizar-servidor.sh` (en el VPS) |
| Ver logs | `journalctl -u prefactibilidad -f` |
| Reiniciar | `sudo systemctl restart prefactibilidad` |
| Cambiar la contraseña | editar `ACCESS_PASSWORD` en `backend/.env` y reiniciar (cierra todas las sesiones) |

El backend no guarda datos: el único archivo que vale la pena resguardar es `backend/.env`.

## Qué protege el acceso

Con `ACCESS_PASSWORD` definida, todos los endpoints piden sesión (cookie firmada, HttpOnly, 7 días). Además hay un
límite de 5 contraseñas erróneas cada 5 minutos por IP y de 100 facturas por hora por IP enviadas a la IA
(`LIMITE_FACTURAS_HORA`). Variables completas: [backend/.env.example](../backend/.env.example).
