import requests

from fastapi import HTTPException

from config import (
    META_API_VERSION,
    FACEBOOK_ACCESS_TOKEN
)


class MetaService:

    BASE_URL = "https://graph.facebook.com"


    @staticmethod
    def get(path, params=None):

        if not FACEBOOK_ACCESS_TOKEN:

            raise HTTPException(
                status_code=400,
                detail="FACEBOOK_ACCESS_TOKEN não configurado."
            )

        params = params or {}

        params["access_token"] = FACEBOOK_ACCESS_TOKEN

        response = requests.get(

            f"{MetaService.BASE_URL}/{META_API_VERSION}/{path}",

            params=params,

            timeout=30

        )

        data = response.json()

        if not response.ok:

            raise HTTPException(

                status_code=400,

                detail=data

            )

        return data