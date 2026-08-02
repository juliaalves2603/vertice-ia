import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

META_API_VERSION = os.getenv("META_API_VERSION", "v25.0").strip()

TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()

VERTICE_SESSION_SECRET = os.getenv(
    "VERTICE_SESSION_SECRET",
    "vertice-dev-secret"
)

DB_PATH = Path(
    os.getenv(
        "VERTICE_DB_PATH",
        str(BASE_DIR / "vertice_ia_limpa.db")
    )
)