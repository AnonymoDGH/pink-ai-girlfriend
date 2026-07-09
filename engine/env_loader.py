"""
Cargador minimo de archivos .env, sin dependencias externas. Lee
pares CLAVE=valor y los inyecta en os.environ si no estan ya
definidos (para no pisar variables de entorno reales del sistema).
"""
from __future__ import annotations
import os


def load_dotenv(path: str = ".env"):
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
