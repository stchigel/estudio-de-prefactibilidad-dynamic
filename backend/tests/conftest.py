from pathlib import Path

from dotenv import load_dotenv

# Las pruebas contra la API real usan la misma configuración que el servidor (backend/.env).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
