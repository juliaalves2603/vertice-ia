import os
from dotenv import load_dotenv

load_dotenv()

VERTICE_SESSION_SECRET = os.getenv(
    "VERTICE_SESSION_SECRET",
    "vertice-dev-secret"
)