"""Cookie HttpOnly del refresh. El JSON de login/refresh no lo lleva."""

from fastapi import Response

from app.config import get_settings

COOKIE_NAME = "kawsay_refresh"
#: `/` cubre `/auth` (TestClient, OpenAPI) y `/api/auth` (rewrite del frontend).
COOKIE_PATH = "/"


def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "development",
        path=COOKIE_PATH,
        max_age=settings.refresh_token_ttl_days * 86400,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)
