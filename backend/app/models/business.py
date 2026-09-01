from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.base import DateTime6 as DateTime


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("tts_speed BETWEEN 0.5 AND 2.0", name="valid_tts_speed"),
        CheckConstraint("response_length IN ('SHORT','MEDIUM','LONG')", name="valid_length"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    high_contrast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tts_speed: Mapped[float] = mapped_column(default=1.0, nullable=False)
    response_length: Mapped[str] = mapped_column(String(8), default="MEDIUM", nullable=False)


class Business(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('IDEA','STARTUP','OPERATING','GROWING','PAUSED')", name="valid_stage"
        ),
        CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="valid_status"),
        Index("ix_businesses_owner_status", "owner_user_id", "status", "deleted_at"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    activity: Mapped[str] = mapped_column(String(180), nullable=False)
    department_code: Mapped[str | None] = mapped_column(String(8))
    municipality: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)


class BusinessMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_memberships"
    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_business_member"),
        CheckConstraint("member_role IN ('OWNER','COLLABORATOR','VIEWER')", name="valid_role"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    member_role: Mapped[str] = mapped_column(String(16), nullable=False)


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class BusinessSkill(Base):
    __tablename__ = "business_skills"

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 5", name="valid_level"),)


class BusinessGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_goals"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','COMPLETED','CANCELLED')", name="valid_status"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_date: Mapped[datetime | None] = mapped_column(DateTime())
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)


class BusinessChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_channels"
    __table_args__ = (
        UniqueConstraint("business_id", "channel_code", name="uq_business_channel"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    channel_code: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DiagnosticSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('IN_PROGRESS','COMPLETED','ABANDONED')", name="valid_status"),
        Index("ix_diagnostics_business_created", "business_id", "created_at"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    questionnaire_version: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="IN_PROGRESS", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())


class DiagnosticAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnostic_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_code", name="uq_diagnostic_answer"),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_code: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_text_encrypted: Mapped[str] = mapped_column(Text, nullable=False)


class FormalizationRoute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "formalization_routes"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','COMPLETED','ARCHIVED')", name="valid_status"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    generated_by_ai_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_runs.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)


class FormalizationStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "formalization_steps"
    __table_args__ = (
        UniqueConstraint("route_id", "step_number", name="uq_formalization_step"),
        CheckConstraint("step_number > 0", name="positive_step"),
    )

    route_id: Mapped[str] = mapped_column(
        ForeignKey("formalization_routes.id", ondelete="CASCADE"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_versions.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())
