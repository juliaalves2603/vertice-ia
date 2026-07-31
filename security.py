import secrets

from fastapi import HTTPException

from config import VERTICE_PASSWORD


def verify_password(password: str):

    if not VERTICE_PASSWORD:

        raise RuntimeError(
            "VERTICE_PASSWORD não configurada."
        )

    if password != VERTICE_PASSWORD:

        raise HTTPException(
            status_code=401,
            detail="Senha inválida."
        )


def generate_session():

    return secrets.token_urlsafe(64)