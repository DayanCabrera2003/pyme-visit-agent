"""
Modulo de configuracion centralizado.

Lee todas las variables de entorno en un solo lugar.
Ningun otro modulo del proyecto debe importar os.environ directamente.
Lanza ValueError al inicio si faltan variables obligatorias, para detectar
problemas de configuracion antes de que el servidor arranque.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Variables obligatorias — el servidor no arranca sin ellas
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY no esta definida. "
        "Copia .env.example a .env y agrega tu API key de Google Gemini."
    )

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL no esta definida. "
        "Copia .env.example a .env y agrega la connection string de Supabase."
    )

# Variables opcionales con valores por defecto
PORT: int = int(os.environ.get("PORT", "8000"))
SESSION_TTL_MINUTES: int = int(os.environ.get("SESSION_TTL_MINUTES", "60"))
