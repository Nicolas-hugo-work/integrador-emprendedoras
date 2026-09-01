"""Auditoría seudonimizada.

Los eventos se añaden a la sesión pero **no** se confirman aquí: el `commit`
pertenece al caso de uso, de modo que la auditoría viaja en la misma
transacción que la mutación que describe.
"""

import hashlib
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.models.admin_research import AuditEvent
from app.models.identity import User

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
