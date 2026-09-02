"""Consulta de la traza de auditoría."""

from datetime import datetime

from fastapi import APIRouter, Query

from app.api_contracts import AuditEventView
from app.dependencies import DB, CurrentUser
from app.services import audit_service

router = APIRouter(tags=["audit"])


@router.get("/audit-events", response_model=list[AuditEventView])
def list_audit_events(
    db: DB,
    user: CurrentUser,
    action: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEventView]:
    return audit_service.list_events(
        db,
        user,
        action=action,
        object_type=object_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
