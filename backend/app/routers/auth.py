"""Registro, verificación, inicio y cierre de sesión."""

from fastapi import APIRouter, Cookie, Request, Response

from app.api_contracts import (
    ContactRegistration,
    LoginRequest,
    RefreshRequest,
    RegistrationResult,
    TokenPair,
    VerifyContactRequest,
)
from app.auth_cookies import (
    COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.core.exceptions import Unauthorized
from app.dependencies import DB, CurrentUser
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    """Identifica al cliente para el límite de intentos."""
    return request.client.host if request.client else "unknown"


def _refresh_value(
    cookie: str | None,
    payload: RefreshRequest | None,
) -> str:
    token = cookie or (payload.refresh_token if payload else None)
    if not token:
        raise Unauthorized("Sesión inválida o vencida")
    return token


@router.post("/register", response_model=RegistrationResult, status_code=201)
def register(payload: ContactRegistration, db: DB) -> RegistrationResult:
    return auth_service.register(db, payload)


@router.post("/verify-contact")
def verify_contact(payload: VerifyContactRequest, db: DB, request: Request) -> dict[str, str]:
    return auth_service.verify_contact(db, payload, client_key=_client_key(request))


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DB, request: Request, response: Response) -> TokenPair:
    issued = auth_service.login(db, payload, client_key=_client_key(request))
    set_refresh_cookie(response, issued.refresh_token)
    return issued.tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(
    db: DB,
    response: Response,
    payload: RefreshRequest | None = None,
    kawsay_refresh: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> TokenPair:
    issued = auth_service.refresh(db, _refresh_value(kawsay_refresh, payload))
    set_refresh_cookie(response, issued.refresh_token)
    return issued.tokens


@router.post("/logout")
def logout(
    db: DB,
    user: CurrentUser,
    response: Response,
    payload: RefreshRequest | None = None,
    kawsay_refresh: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict[str, str]:
    result = auth_service.logout(db, kawsay_refresh or (payload.refresh_token if payload else None), user)
    clear_refresh_cookie(response)
    return result
