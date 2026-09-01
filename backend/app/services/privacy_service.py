"""Consentimientos, exportación de datos y eliminación de cuenta."""

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.exceptions import Conflict, NotFound
from app.domain_rules import account_purge_deadline
from app.models.identity import User
from app.models.privacy import (
    ConsentPurpose,
    ConsentVersion,
    DataExportRequest,
    DeletionRequest,
    UserConsent,
)
from app.services.audit_service import write_audit


def decide_consent(db: Session, user: User, payload) -> dict[str, str]:
    """Registra el otorgamiento o retiro de un consentimiento versionado.

    Retirar una finalidad opcional desactiva esa función pero no cierra la
    cuenta: solo `/privacy/deletion` cambia el estado de la usuaria.
    """
    purpose = db.scalar(select(ConsentPurpose).where(ConsentPurpose.code == payload.purpose_code))
    if purpose is None:
        raise NotFound("Finalidad no encontrada")
    version = db.scalar(
        select(ConsentVersion).where(
            ConsentVersion.purpose_id == purpose.id,
            ConsentVersion.version == payload.version,
            ConsentVersion.retired_at.is_(None),
        )
    )
    if version is None:
        raise Conflict("Versión no vigente")
    event = UserConsent(
        user_id=user.id,
        purpose_id=purpose.id,
        consent_version_id=version.id,
        decision=payload.decision,
        decided_at=utc_now(),
        source="WEB",
        evidence_hash=hashlib.sha256(
            f"{user.id}|{purpose.code}|{payload.decision}|{version.notice_hash}".encode()
        ).hexdigest(),
    )
    db.add(event)
    db.flush()
    write_audit(db, actor=user, action="consent.decide", object_type="user_consent", object_id=event.id)
    db.commit()
    return {"id": event.id, "decision": event.decision}


def request_account_deletion(db: Session, user: User) -> dict[str, str]:
    """Desactiva la cuenta y programa la purga física."""
    requested_at = utc_now()
    deletion = DeletionRequest(
        user_id=user.id,
        requested_at=requested_at,
        purge_due_at=account_purge_deadline(requested_at),
        status="PENDING",
        scope="ACCOUNT",
    )
    db.add(deletion)
    user.status = "DELETED"
    user.deleted_at = requested_at
    write_audit(db, actor=user, action="account.delete_request", object_type="user", object_id=user.id)
    db.commit()
    return {"request_id": deletion.id, "purge_due_at": deletion.purge_due_at.isoformat()}


def request_data_export(db: Session, user: User) -> dict[str, str]:
    """Registra una solicitud de copia de los datos de la usuaria."""
    export = DataExportRequest(user_id=user.id, format="JSON", status="PENDING")
    db.add(export)
    db.flush()
    write_audit(
        db,
        actor=user,
        action="account.export_request",
        object_type="data_export_request",
        object_id=export.id,
    )
    db.commit()
    return {"request_id": export.id, "status": export.status}
