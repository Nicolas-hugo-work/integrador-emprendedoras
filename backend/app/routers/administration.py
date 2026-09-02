"""Administración: cola de alertas y acciones sobre cuentas.

Leer la cola es de auditoría (`audit.read`), actuar sobre ella y sobre las
cuentas es de administración (`account.suspend`). La auditora ve lo mismo pero
no puede cambiar nada, igual que en el visor de auditoría.
"""

from fastapi import APIRouter, Query

from app.api_contracts import AccountView, SecurityAlertView, SuspendRequest
from app.dependencies import DB, CurrentUser
from app.services import account_service, security_service

router = APIRouter(tags=["admin"])


@router.get("/security-alerts", response_model=list[SecurityAlertView])
def list_security_alerts(
    db: DB,
    user: CurrentUser,
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SecurityAlertView]:
    return security_service.list_alerts(
        db, user, status=status, severity=severity, limit=limit, offset=offset
    )


@router.post("/security-alerts/{alert_id}/acknowledge")
def acknowledge_security_alert(alert_id: str, db: DB, user: CurrentUser) -> dict[str, str]:
    return security_service.acknowledge_alert(db, user, alert_id)


@router.post("/security-alerts/{alert_id}/resolve")
def resolve_security_alert(alert_id: str, db: DB, user: CurrentUser) -> dict[str, str]:
    return security_service.resolve_alert(db, user, alert_id)


@router.get("/accounts/lookup", response_model=AccountView)
def lookup_account(db: DB, user: CurrentUser, contact: str) -> AccountView:
    """Busca por contacto completo. No admite comodines ni devuelve listados."""
    return account_service.lookup_account(db, user, contact)


@router.get("/accounts/{user_id}", response_model=AccountView)
def read_account(user_id: str, db: DB, user: CurrentUser) -> AccountView:
    """Ficha de la cuenta a la que apunta una alerta."""
    return account_service.read_account(db, user, user_id)


@router.post("/accounts/{user_id}/suspend", response_model=AccountView)
def suspend_account(
    user_id: str, payload: SuspendRequest, db: DB, user: CurrentUser
) -> AccountView:
    return account_service.suspend_account(db, user, user_id, payload)


@router.post("/accounts/{user_id}/reactivate", response_model=AccountView)
def reactivate_account(user_id: str, db: DB, user: CurrentUser) -> AccountView:
    return account_service.reactivate_account(db, user, user_id)
