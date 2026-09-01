"""Registro, verificación, inicio y cierre de sesión."""

from fastapi import APIRouter, Request

from app.api_contracts import (
    ContactRegistration,
    LoginRequest,
    RefreshRequest,
    RegistrationResult,
    TokenPair,
    VerifyContactRequest,
)
from app.dependencies import DB, CurrentUser
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    """Identifica al cliente para el límite de intentos."""
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=RegistrationResult, status_code=201)
def register(payload: ContactRegistration, db: DB) -> RegistrationResult:
    return auth_service.register(db, payload)


@router.post("/verify-contact")
def verify_contact(payload: VerifyContactRequest, db: DB, request: Request) -> dict[str, str]:
    return auth_service.verify_contact(db, payload, client_key=_client_key(request))


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DB, request: Request) -> TokenPair:
    return auth_service.login(db, payload, client_key=_client_key(request))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DB) -> TokenPair:
    return auth_service.refresh(db, payload)


@router.post("/logout")
def logout(payload: RefreshRequest, db: DB, user: CurrentUser) -> dict[str, str]:
    return auth_service.logout(db, payload, user)
