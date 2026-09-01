"""Tareas periódicas de privacidad y mantenimiento."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.business import Business, BusinessMembership, UserPreference
from app.models.conversation import (
    AudioArtifact,
    Conversation,
    EscalationEvent,
    GeneratedContent,
    ResponseFeedback,
)
from app.models.finance import FinancialMovement
from app.models.identity import (
    OrganizationMembership,
    PasswordCredential,
    Session,
    User,
    UserContact,
    UserRole,
)
from app.models.privacy import DataExportRequest, DeletionRequest, UserConsent

settings = get_settings()


def utc_now() -> datetime:
    return datetime.utcnow()


def purge_expired_sessions() -> int:
    with SessionLocal.begin() as db:
        result = db.execute(delete(Session).where(
            (Session.expires_at < utc_now())
            | (Session.revoked_at < utc_now() - timedelta(days=7))
        ))
        return result.rowcount or 0


def purge_audio_metadata() -> int:
    with SessionLocal.begin() as db:
        rows = db.scalars(select(AudioArtifact).where(
            AudioArtifact.purge_at <= utc_now(), AudioArtifact.deleted_at.is_(None)
        )).all()
        for row in rows:
            # El worker de objetos debe borrar primero row.storage_key.
            row.storage_key = "PURGED"
            row.transcription_status = "PURGED"
            row.deleted_at = utc_now()
        return len(rows)


def purge_due_accounts() -> int:
    with SessionLocal.begin() as db:
        requests = db.scalars(select(DeletionRequest).where(
            DeletionRequest.status == "PENDING",
            DeletionRequest.purge_due_at <= utc_now(),
        )).all()
        purged = 0
        for request in requests:
            user_id = request.user_id
            business_ids = list(db.scalars(select(Business.id).where(Business.owner_user_id == user_id)))
            db.execute(delete(ResponseFeedback).where(ResponseFeedback.user_id == user_id))
            db.execute(delete(AudioArtifact).where(AudioArtifact.user_id == user_id))
            db.execute(delete(GeneratedContent).where(GeneratedContent.user_id == user_id))
            db.execute(delete(EscalationEvent).where(EscalationEvent.user_id == user_id))
            db.execute(delete(Conversation).where(Conversation.user_id == user_id))
            db.execute(delete(FinancialMovement).where(FinancialMovement.user_id == user_id))
            db.execute(delete(BusinessMembership).where(BusinessMembership.user_id == user_id))
            db.execute(delete(OrganizationMembership).where(OrganizationMembership.user_id == user_id))
            db.execute(delete(UserConsent).where(UserConsent.user_id == user_id))
            db.execute(delete(DataExportRequest).where(DataExportRequest.user_id == user_id))
            db.execute(delete(Session).where(Session.user_id == user_id))
            db.execute(delete(UserRole).where(UserRole.user_id == user_id))
            db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
            db.execute(delete(PasswordCredential).where(PasswordCredential.user_id == user_id))
            db.execute(delete(UserContact).where(UserContact.user_id == user_id))
            if business_ids:
                db.execute(delete(Business).where(Business.id.in_(business_ids)))
            db.execute(delete(DeletionRequest).where(DeletionRequest.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            purged += 1
        return purged


def run_all() -> dict[str, int]:
    return {
        "expired_sessions": purge_expired_sessions(),
        "audio_records": purge_audio_metadata(),
        "accounts": purge_due_accounts(),
    }


if __name__ == "__main__":
    print(run_all())
