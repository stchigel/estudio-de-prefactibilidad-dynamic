#!/usr/bin/env bash
# Actualiza el backend en el servidor: trae el código nuevo y reinicia el servicio.
#   sudo ./deploy/actualizar-servidor.sh
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Correr con sudo." >&2; exit 1; }
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USUARIO=prefactibilidad

sudo -u "$USUARIO" git -C "$RAIZ" pull --ff-only
sudo -u "$USUARIO" "$RAIZ/backend/.venv/bin/pip" install --quiet -e "$RAIZ/backend"
systemctl restart prefactibilidad
sleep 2
curl -fsS http://127.0.0.1:8000/api/salud && echo
