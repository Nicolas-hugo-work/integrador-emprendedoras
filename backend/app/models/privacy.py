from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.base import DateTime6 as DateTime


class ConsentPurpose(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_purposes"

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    withdrawal_effect: Mapped[str] = mapped_column(String(500), nullable=False)


class ConsentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_versions"
    __table_args__ = (
        Index("ix_consent_versions_purpose_published", "purpose_id", "published_at"),
    )

    purpose_id: Mapped[str] = mapped_column(
        ForeignKey("consent_purposes.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(24), nullable=False)
    notice_text: Mapped[str] = mapped_column(Text, nullable=False)
    notice_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime())


class UserConsent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_consents"
    __table_args__ = (
        CheckConstraint("decision IN ('GRANTED','WITHDRAWN')", name="valid_decision"),
        Index("ix_user_consents_user_purpose", "user_id", "purpose_id", "decided_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose_id: Mapped[str] = mapped_column(
        ForeignKey("consent_purposes.id", ondelete="RESTRICT"), nullable=False
    )
    consent_version_id: Mapped[str] = mapped_column(
        ForeignKey("consent_versions.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="WEB", nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DataExportRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_export_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','READY','EXPIRED','FAILED')",
            name="valid_status",
        ),
        Index("ix_data_exports_user_status", "user_id", "status", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(8), default="JSON", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())


class DeletionRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','COMPLETED','CANCELLED','FAILED')",
            name="valid_status",
        ),
        Index("ix_deletion_requests_user_status", "user_id", "status", "requested_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    purge_due_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    scope: Mapped[str] = mapped_column(String(24), default="ACCOUNT", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())
    failure_reason: Mapped[str | None] = mapped_column(String(500))
