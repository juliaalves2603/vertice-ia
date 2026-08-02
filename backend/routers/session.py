import hashlib
import hmac

from fastapi import APIRouter, Request

from config import VERTICE_SESSION_SECRET

router = APIRouter()


def _vertice_token():
    return hmac.new(
        VERTICE_SESSION_SECRET.encode("utf-8"),
        b"VERTICE_IA_SESSION",
        hashlib.sha256,
    ).hexdigest()


def _vertice_logged(request: Request):
    cookie = request.cookies.get("vertice_session", "")
    return bool(cookie) and hmac.compare_digest(cookie, _vertice_token())


@router.get("/api/session-check")
def api_session_check(request: Request):
    return {
        "logged": _vertice_logged(request),
        "cookies": list(request.cookies.keys()),
        "status": "ok",
    }