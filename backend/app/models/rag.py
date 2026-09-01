from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, Vector768
from app.models.base import DateTime6 as DateTime


class SourcePublisher(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_publishers"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    official_domain: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str] = mapped_column(String(2), default="BO", nullable=False)


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','IN_REVIEW','PUBLISHED','RETIRED')", name="valid_status"
        ),
        Index("ix_sources_status_jurisdiction", "status", "jurisdiction", "topic"),
    )

    publisher_id: Mapped[str] = mapped_column(
        ForeignKey("source_publishers.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(120), default="Bolivia", nullable=False)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    license_name: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)


class SourceVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_source_content_hash"),
        CheckConstraint(
            "status IN ('INGESTING','REVIEW','PUBLISHED','EXPIRED','RETIRED','FAILED')",
            name="valid_status",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="valid_dates"
        ),
        Index("ix_source_versions_validity", "source_id", "status", "valid_from", "valid_to"),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    version_label: Mapped[str] = mapped_column(String(120), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    consulted_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="INGESTING", nullable=False)


class SourceStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_status_history"
    __table_args__ = (
        Index("ix_source_status_history_version_date", "source_version_id", "changed_at"),
    )

    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    previous_status: Mapped[str | None] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    changed_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)


class IngestionJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','EXTRACTING','CHUNKING','EMBEDDING','COMPLETED','FAILED')",
            name="valid_status",
        ),
        Index("ix_ingestion_jobs_status_created", "status", "created_at"),
    )

    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", nullable=False)
    extractor_version: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())


class SourceChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("source_version_id", "chunk_number", name="uq_source_chunk_number"),
        UniqueConstraint("source_version_id", "content_hash", name="uq_source_chunk_hash"),
        CheckConstraint("chunk_number > 0", name="positive_number"),
        CheckConstraint("token_count > 0", name="positive_tokens"),
        Index("ix_source_chunks_version_number", "source_version_id", "chunk_number"),
    )

    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)


class EmbeddingModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "embedding_models"
    __table_args__ = (
        CheckConstraint("dimension = 768", name="dimension_768"),
        CheckConstraint("distance_metric = 'COSINE'", name="cosine_only"),
    )

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(180), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=768, nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(16), default="COSINE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SourceChunkEmbedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("source_chunk_id", name="uq_source_chunk_embedding"),
        Index("ix_chunk_embeddings_model", "embedding_model_id"),
    )

    source_chunk_id: Mapped[str] = mapped_column(
        ForeignKey("source_chunks.id", ondelete="CASCADE"), nullable=False
    )
    embedding_model_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_models.id", ondelete="RESTRICT"), nullable=False
    )
    embedding: Mapped[bytes] = mapped_column(Vector768(), nullable=False)


class SourceCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_checks"
    __table_args__ = (
        Index("ix_source_checks_source_checked", "source_id", "checked_at"),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    new_content_hash: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(String(500))
