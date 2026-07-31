from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"

DATABASE_PATH = Path(
    os.getenv(
        "VERTICE_DB_PATH",
        str(BASE_DIR / "data" / "vertice.db")
    )
)

META_API_VERSION = os.getenv(
    "META_API_VERSION",
    "v25.0"
).strip()

FACEBOOK_ACCESS_TOKEN = os.getenv(
    "FACEBOOK_ACCESS_TOKEN"
)

FACEBOOK_PAGE_ID = os.getenv(
    "FACEBOOK_PAGE_ID"
)

META_APP_ID = os.getenv(
    "META_APP_ID"
)

META_APP_SECRET = os.getenv(
    "META_APP_SECRET"
)

VERTICE_PASSWORD = os.getenv(
    "VERTICE_PASSWORD"
)

APP_URL = os.getenv(
    "APP_URL",
    "https://appverticeia.com.br"
)

DEBUG = os.getenv(
    "DEBUG",
    "False"
).lower() == "true"
