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

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.base import DateTime6 as DateTime


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','ARCHIVED','DELETED')", name="valid_status"),
        Index("ix_conversations_user_updated", "user_id", "updated_at", "deleted_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    business_id: Mapped[str | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL")
    )
    title_encrypted: Mapped[str | None] = mapped_column(Text)
    topic_code: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime())


class Message(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_number", name="uq_message_sequence"),
        CheckConstraint("sender IN ('USER','ASSISTANT','SYSTEM','TOOL')", name="valid_sender"),
        CheckConstraint(
            "moderation_status IN ('PENDING','ALLOWED','WARNED','BLOCKED')",
            name="valid_moderation",
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sender: Mapped[str] = mapped_column(String(16), nullable=False)
    content_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(16), default="PENDING", nullable=False
    )


class AIRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        CheckConstraint(
            "response_status IN ('COMPLETED','ABSTAINED','BLOCKED','FAILED')",
            name="valid_response_status",
        ),
        Index("ix_ai_runs_message", "assistant_message_id"),
        Index("ix_ai_runs_trace", "trace_id"),
    )

    assistant_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(180), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    response_status: Mapped[str] = mapped_column(String(16), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_flags: Mapped[dict | None] = mapped_column(JSON)


class AIRetrieval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_retrievals"
    __table_args__ = (
        UniqueConstraint("ai_run_id", "rank_position", name="uq_ai_retrieval_rank"),
        CheckConstraint("rank_position > 0", name="positive_rank"),
        CheckConstraint("distance >= 0", name="nonnegative_distance"),
    )

    ai_run_id: Mapped[str] = mapped_column(
        ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_embedding_id: Mapped[str] = mapped_column(
        ForeignKey("source_chunk_embeddings.id", ondelete="RESTRICT"), nullable=False
    )
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    distance: Mapped[Decimal] = mapped_column(Numeric(12, 9), nullable=False)
    selected_for_prompt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MessageCitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        UniqueConstraint("message_id", "source_chunk_id", name="uq_message_citation_chunk"),
        Index("ix_message_citations_message", "message_id", "display_order"),
    )

    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False
    )
    source_chunk_id: Mapped[str] = mapped_column(
        ForeignKey("source_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    institution_snapshot: Mapped[str] = mapped_column(String(240), nullable=False)
    title_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    url_snapshot: Mapped[str] = mapped_column(String(1000), nullable=False)
    version_snapshot: Mapped[str | None] = mapped_column(String(120))
    consulted_at_snapshot: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    excerpt_snapshot: Mapped[str | None] = mapped_column(Text)


class ResponseFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "response_feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
        CheckConstraint(
            "feedback_type IN ('USEFUL','ERROR','OUTDATED_SOURCE')", name="valid_type"
        ),
        CheckConstraint("status IN ('OPEN','REVIEWED','RESOLVED')", name="valid_status"),
    )

    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(24), nullable=False)
    comment_encrypted: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)


class GeneratedContent(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "generated_contents"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('SALES_TEXT','DESCRIPTION','IDEA','CONTENT_CALENDAR')",
            name="valid_type",
        ),
        CheckConstraint("status IN ('DRAFT','APPROVED','COPIED','DELETED')", name="valid_status"),
        Index("ix_generated_contents_user_status", "user_id", "status", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    business_id: Mapped[str | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL")
    )
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    content_type: Mapped[str] = mapped_column(String(24), nullable=False)
    channel_code: Mapped[str | None] = mapped_column(String(32))
    draft_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime())


class AudioArtifact(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "audio_artifacts"
    __table_args__ = (
        CheckConstraint(
            "transcription_status IN ('UPLOADED','TRANSCRIBING','READY','CONFIRMED','FAILED','PURGED')",
            name="valid_transcription_status",
        ),
        Index("ix_audio_artifacts_purge", "purge_at", "deleted_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    consent_event_id: Mapped[str] = mapped_column(
        ForeignKey("user_consents.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    transcription_status: Mapped[str] = mapped_column(
        String(16), default="UPLOADED", nullable=False
    )
    purge_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime())


class EscalationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "escalation_events"
    __table_args__ = (
        Index("ix_escalation_events_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    warning_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    official_url: Mapped[str | None] = mapped_column(String(1000))
