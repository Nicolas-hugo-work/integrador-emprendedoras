"""Auditoría seudonimizada.

Los eventos se añaden a la sesión pero **no** se confirman aquí: el `commit`
pertenece al caso de uso, de modo que la auditoría viaja en la misma
transacción que la mutación que describe.
"""

import hashlib
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_contracts import AuditEventView
from app.core.clock import utc_now
from app.models.admin_research import AuditEvent
from app.models.identity import User
from app.services.authorization import assert_permission

#: Valores admitidos por la restricción `ck_audit_events_valid_result`.
VALID_RESULTS = frozenset({"SUCCESS", "DENIED", "FAILED"})


def write_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    object_type: str,
    object_id: str | None,
    result: str = "SUCCESS",
) -> None:
    """Registra un evento de auditoría dentro de la transacción en curso."""
    if result not in VALID_RESULTS:
        raise ValueError(f"result debe ser uno de {sorted(VALID_RESULTS)}, no {result!r}")
    occurred_at = utc_now()
    pseudonym = hashlib.sha256((actor.id if actor else "system").encode()).hexdigest()[:32]
    raw = f"{pseudonym}|{action}|{object_type}|{object_id}|{occurred_at.isoformat()}|{result}"
    db.add(
        AuditEvent(
            actor_user_id=actor.id if actor else None,
            actor_pseudonym=pseudonym,
            action=action,
            object_type=object_type,
            object_id=object_id,
            result=result,
            occurred_at=occurred_at,
            correlation_id=str(uuid4()),
            integrity_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
    )


#: Tope de la página, para que un filtro amplio no arrastre la tabla entera.
MAX_PAGE = 200


def list_events(
    db: Session,
    user: User,
    *,
    action: str | None = None,
    object_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditEventView]:
    """Traza de auditoría, seudonimizada, para `ADMINISTRADORA` y `AUDITORA`.

    Aprovecha `ix_audit_events_object_time` cuando se filtra por tipo de objeto
    y fecha. Devuelve lo más reciente primero.
    """
    assert_permission(db, user, "audit.read")

    query = select(AuditEvent)
    if action:
        query = query.where(AuditEvent.action == action)
    if object_type:
        query = query.where(AuditEvent.object_type == object_type)
    if date_from:
        query = query.where(AuditEvent.occurred_at >= date_from)
    if date_to:
        query = query.where(AuditEvent.occurred_at <= date_to)

    rows = db.scalars(
        query.order_by(AuditEvent.occurred_at.desc())
        .limit(min(max(limit, 1), MAX_PAGE))
        .offset(max(offset, 0))
    ).all()
    return [AuditEventView.model_validate(row) for row in rows]
