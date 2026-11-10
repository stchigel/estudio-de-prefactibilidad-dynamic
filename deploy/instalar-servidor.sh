#!/usr/bin/env bash
# Instala el backend en un servidor Ubuntu 24.04 limpio (por ejemplo, un VPS de Hetzner).
#
#   sudo ./deploy/instalar-servidor.sh api.tuempresa.com https://app.tuempresa.com
#                                      └ dominio de la API   └ dónde se publica el frontend
#
# Correr desde la raíz del repositorio ya copiado al servidor (git clone o scp), que debe quedar
# en una ruta fija (se recomienda /opt/prefactibilidad). Antes, el registro DNS "A" de la API
# tiene que apuntar a la IP del servidor: Caddy pide el certificado HTTPS al arrancar.
# Se puede volver a correr: no pisa un backend/.env existente.
set -euo pipefail

DOMINIO_API="${1:-}"
ORIGEN_FRONTEND="${2:-}"
if [[ -z "$DOMINIO_API" || -z "$ORIGEN_FRONTEND" ]]; then
    echo "Uso: sudo $0 <dominio-de-la-api> <url-del-frontend>" >&2
    echo "Ej.: sudo $0 api.tuempresa.com https://app.tuempresa.com" >&2
    exit 1
fi
[[ $EUID -eq 0 ]] || { echo "Correr con sudo." >&2; exit 1; }

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$RAIZ/backend/pyproject.toml" ]] || { echo "No encuentro backend/pyproject.toml en $RAIZ" >&2; exit 1; }
USUARIO=prefactibilidad
ORIGEN_FRONTEND="${ORIGEN_FRONTEND%/}"

echo "==> Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip caddy ufw
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' \
    || { echo "Hace falta Python 3.12 o superior (Ubuntu 24.04 lo trae)." >&2; exit 1; }

echo "==> Usuario de servicio y backend"
id "$USUARIO" >/dev/null 2>&1 || useradd --system --home-dir "$RAIZ" --shell /usr/sbin/nologin "$USUARIO"
chown -R "$USUARIO":"$USUARIO" "$RAIZ"
sudo -u "$USUARIO" python3 -m venv "$RAIZ/backend/.venv"
sudo -u "$USUARIO" "$RAIZ/backend/.venv/bin/pip" install --quiet --upgrade pip
sudo -u "$USUARIO" "$RAIZ/backend/.venv/bin/pip" install --quiet -e "$RAIZ/backend"

ENV="$RAIZ/backend/.env"
if [[ -f "$ENV" ]]; then
    echo "==> Ya existe $ENV: no se modifica."
else
    echo "==> Configuración (se guarda en $ENV)"
    read -r -s -p "Contraseña de acceso al sistema (la van a usar los usuarios): " ACCESO; echo
    [[ ${#ACCESO} -ge 8 ]] || { echo "Usar al menos 8 caracteres." >&2; exit 1; }
    read -r -p "Proveedor de IA para leer facturas [claude/gemini] (claude): " PROVEEDOR
    PROVEEDOR="${PROVEEDOR:-claude}"
    [[ "$PROVEEDOR" == "claude" || "$PROVEEDOR" == "gemini" ]] || { echo "Elegir claude o gemini." >&2; exit 1; }
    read -r -s -p "API key de $PROVEEDOR (Enter para cargarla después): " CLAVE_IA; echo
    umask 077
    {
        echo "EXTRACCION_PROVEEDOR=$PROVEEDOR"
        if [[ "$PROVEEDOR" == "claude" ]]; then echo "ANTHROPIC_API_KEY=$CLAVE_IA"; else echo "GEMINI_API_KEY=$CLAVE_IA"; fi
        echo "ACCESS_PASSWORD=$ACCESO"
        echo "SESSION_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
        echo "CORS_ORIGINS=$ORIGEN_FRONTEND"
    } > "$ENV"
    chown "$USUARIO":"$USUARIO" "$ENV"
    chmod 600 "$ENV"
fi

echo "==> Servicio (systemd)"
cat > /etc/systemd/system/prefactibilidad.service <<UNIT
[Unit]
Description=Prefactibilidad Solar - API
After=network.target

[Service]
User=$USUARIO
WorkingDirectory=$RAIZ/backend
ExecStart=$RAIZ/backend/.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=3
# Un trabajo pesado no puede dejar sin memoria al resto del servidor.
MemoryMax=1500M
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable prefactibilidad >/dev/null
systemctl restart prefactibilidad

echo "==> HTTPS (Caddy)"
cat > /etc/caddy/Caddyfile <<CADDY
$DOMINIO_API {
    # Facturas: hasta 30 MB cada una (ver TAMANIO_MAXIMO_FACTURA en api/main.py).
    request_body {
        max_size 100MB
    }
    reverse_proxy 127.0.0.1:8000
}
CADDY
systemctl reload caddy || systemctl restart caddy

echo "==> Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> Comprobando"
sleep 3
systemctl is-active --quiet prefactibilidad || { echo "El servicio no arrancó:"; journalctl -u prefactibilidad -n 20 --no-pager; exit 1; }
curl -fsS http://127.0.0.1:8000/api/salud && echo
echo
echo "Listo. Probar desde afuera (cuando el DNS ya apunte acá):  curl https://$DOMINIO_API/api/salud"
echo "Logs:  journalctl -u prefactibilidad -f"
