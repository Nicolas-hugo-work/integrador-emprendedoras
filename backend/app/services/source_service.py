"""Curaduría documental: fuentes, versiones, fragmentos y publicación."""

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.exceptions import Conflict, Invalid, NotFound
from app.models.identity import User
from app.models.rag import Source, SourceChunk, SourcePublisher, SourceVersion
from app.services.audit_service import write_audit
from app.services.authorization import assert_permission


def create_source(db: Session, user: User, payload) -> dict[str, str]:
    """Da de alta una fuente en estado borrador."""
    assert_permission(db, user, "source.review")
    if db.get(SourcePublisher, payload.publisher_id) is None:
        raise Invalid("Institución emisora no encontrada")
    source = Source(
        publisher_id=payload.publisher_id,
        title=payload.title,
        canonical_url=str(payload.canonical_url),
        jurisdiction=payload.jurisdiction,
        topic=payload.topic,
        license_name=payload.license_name,
        status="DRAFT",
    )
    db.add(source)
    db.flush()
    write_audit(db, actor=user, action="source.create", object_type="source", object_id=source.id)
    db.commit()
    return {"id": source.id}


def create_source_version(db: Session, user: User, payload) -> dict[str, str]:
    """Registra una versión de la fuente pendiente de revisión."""
    assert_permission(db, user, "source.review")
    if db.get(Source, payload.source_id) is None:
        raise NotFound("Fuente no encontrada")
    version = SourceVersion(
        source_id=payload.source_id,
        version_label=payload.version_label,
        publication_date=payload.publication_date,
        consulted_at=utc_now(),
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        content_hash=payload.content_hash,
        storage_key=payload.storage_key,
        status="REVIEW",
    )
    db.add(version)
    db.commit()
    return {"id": version.id, "status": version.status}


def create_source_chunk(db: Session, user: User, payload) -> dict[str, str]:
    """Añade un fragmento indexable a una versión."""
    assert_permission(db, user, "source.review")
    if db.get(SourceVersion, payload.source_version_id) is None:
        raise NotFound("Versión no encontrada")
    chunk = SourceChunk(
        source_version_id=payload.source_version_id,
        chunk_number=payload.chunk_number,
        heading=payload.heading,
        content=payload.content,
        content_hash=hashlib.sha256(payload.content.encode()).hexdigest(),
        page_number=payload.page_number,
        token_count=payload.token_count,
    )
    db.add(chunk)
    db.commit()
    return {"id": chunk.id}


def publish_source_version(db: Session, user: User, version_id: str) -> dict[str, str]:
    """Publica una versión con fragmentos y su fuente."""
    assert_permission(db, user, "source.publish")
    version = db.get(SourceVersion, version_id)
    if version is None:
        raise NotFound("Versión no encontrada")
    chunk_count = db.scalar(
        select(func.count()).select_from(SourceChunk).where(SourceChunk.source_version_id == version.id)
    )
    if not chunk_count:
        raise Conflict("No se puede publicar sin fragmentos")
    source = db.get(Source, version.source_id)
    version.status = "PUBLISHED"
    if source:
        source.status = "PUBLISHED"
    write_audit(
        db, actor=user, action="source.publish", object_type="source_version", object_id=version.id
    )
    db.commit()
    return {"id": version.id, "status": version.status}
