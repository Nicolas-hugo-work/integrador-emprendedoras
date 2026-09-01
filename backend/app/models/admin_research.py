from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.base import DateTime6 as DateTime


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("result IN ('SUCCESS','DENIED','FAILED')", name="valid_result"),
        Index("ix_audit_events_actor_time", "actor_user_id", "occurred_at"),
        Index("ix_audit_events_object_time", "object_type", "object_id", "occurred_at"),
        Index("ix_audit_events_correlation", "correlation_id"),
    )

    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    actor_pseudonym: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(36))
    result: Mapped[str] = mapped_column(String(12), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    integrity_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class SecurityAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "security_alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="valid_severity"),
        CheckConstraint("status IN ('OPEN','ACKNOWLEDGED','RESOLVED')", name="valid_status"),
        Index("ix_security_alerts_status_severity", "status", "severity", "created_at"),
    )

    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime())


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    setting_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class BackgroundJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')",
            name="valid_status",
        ),
        Index("ix_background_jobs_queue", "status", "scheduled_at", "job_type"),
    )

    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime())
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class EvaluationSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_sets"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint("name", "version", name="uq_evaluation_set_version"),)


class EvaluationCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint("evaluation_set_id", "case_code", name="uq_evaluation_case"),
        CheckConstraint(
            "category IN ('FORMALIZATION','FINANCE','MARKETING','SAFETY','INJECTION','PII','NO_EVIDENCE')",
            name="valid_category",
        ),
    )

    evaluation_set_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_sets.id", ondelete="CASCADE"), nullable=False
    )
    case_code: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    expected_source_ids: Mapped[dict | None] = mapped_column(JSON)


class EvaluationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('RUNNING','COMPLETED','FAILED')", name="valid_status"),
        Index("ix_evaluation_runs_set_created", "evaluation_set_id", "created_at"),
    )

    evaluation_set_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_sets.id", ondelete="RESTRICT"), nullable=False
    )
    executed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    model_name: Mapped[str] = mapped_column(String(180), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="RUNNING", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())


class EvaluationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint("evaluation_run_id", "evaluation_case_id", name="uq_eval_result"),
        CheckConstraint("retrieval_recall >= 0 AND retrieval_recall <= 1", name="valid_recall"),
    )

    evaluation_run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retrieval_recall: Mapped[Decimal] = mapped_column(Numeric(6, 5), default=0, nullable=False)
    citation_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ResearchParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_participants"

    participant_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    encrypted_user_reference: Mapped[str | None] = mapped_column(String(500))
    research_consent_event_id: Mapped[str] = mapped_column(
        ForeignKey("user_consents.id", ondelete="RESTRICT"), nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime())


class UsabilitySession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usability_sessions"
    __table_args__ = (
        Index("ix_usability_sessions_participant_date", "participant_id", "scheduled_at"),
    )

    participant_id: Mapped[str] = mapped_column(
        ForeignKey("research_participants.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())
    facilitator_code: Mapped[str | None] = mapped_column(String(64))
    notes_anonymized: Mapped[str | None] = mapped_column(Text)


class TaskResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_results"
    __table_args__ = (
        UniqueConstraint("usability_session_id", "task_code", name="uq_task_result"),
        CheckConstraint("duration_seconds >= 0", name="nonnegative_duration"),
    )

    usability_session_id: Mapped[str] = mapped_column(
        ForeignKey("usability_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_code: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_without_help: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes_anonymized: Mapped[str | None] = mapped_column(Text)


class SurveyResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint("usability_session_id", "question_code", name="uq_survey_response"),
    )

    usability_session_id: Mapped[str] = mapped_column(
        ForeignKey("usability_sessions.id", ondelete="CASCADE"), nullable=False
    )
    instrument_code: Mapped[str] = mapped_column(String(40), default="SUS", nullable=False)
    question_code: Mapped[str] = mapped_column(String(64), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    text_value_anonymized: Mapped[str | None] = mapped_column(Text)
