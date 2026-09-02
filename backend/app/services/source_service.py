"""Curaduría documental: fuentes, versiones, fragmentos y publicación."""

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api_contracts import (
    PublisherView,
    SourceChunkBulkCreate,
    SourceChunkView,
    SourceVersionView,
    SourceView,
)
from app.core.clock import utc_now
from app.core.exceptions import Conflict, Invalid, NotFound
from app.models.identity import User
from app.models.rag import (
    Source,
    SourceChunk,
    SourcePublisher,
    SourceStatusHistory,
    SourceVersion,
)
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
    previous_status = version.status
    version.status = "PUBLISHED"
    if source:
        source.status = "PUBLISHED"
    _record_status_change(
        db,
        version,
        previous_status=previous_status,
        new_status="PUBLISHED",
        user=user,
        reason=None,
    )
    write_audit(
        db, actor=user, action="source.publish", object_type="source_version", object_id=version.id
    )
    db.commit()
    return {"id": version.id, "status": version.status}


def _record_status_change(
    db: Session,
    version: SourceVersion,
    *,
    previous_status: str,
    new_status: str,
    user: User,
    reason: str | None,
) -> None:
    """Anota la transición en `source_status_history`.

    La tabla existe desde el esquema inicial y hasta v0.2.0 nunca se escribió,
    de modo que no había forma de saber quién publicó o retiró una fuente.
    """
    db.add(
        SourceStatusHistory(
            source_version_id=version.id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by_user_id=user.id,
            reason=reason,
            changed_at=utc_now(),
        )
    )


def list_publishers(db: Session, user: User) -> list[PublisherView]:
    """Instituciones emisoras disponibles.

    Sin esta lectura, dar de alta una fuente obligaría a pegar el UUID de la
    institución a mano. La migración siembra SEPREC, SIN, INE y la Gaceta
    Oficial.
    """
    assert_permission(db, user, "source.review")
    rows = db.scalars(select(SourcePublisher).order_by(SourcePublisher.name)).all()
    return [PublisherView.model_validate(row) for row in rows]


def list_sources(db: Session, user: User, *, status: str | None = None) -> list[SourceView]:
    """Fuentes con su institución emisora, opcionalmente filtradas por estado."""
    assert_permission(db, user, "source.review")
    query = (
        select(Source, SourcePublisher)
        .join(SourcePublisher, SourcePublisher.id == Source.publisher_id)
        .order_by(Source.created_at.desc())
    )
    if status:
        query = query.where(Source.status == status)
    return [
        SourceView(
            id=source.id,
            publisher_id=source.publisher_id,
            publisher_name=publisher.name,
            title=source.title,
            canonical_url=source.canonical_url,
            jurisdiction=source.jurisdiction,
            topic=source.topic,
            license_name=source.license_name,
            status=source.status,
        )
        for source, publisher in db.execute(query).all()
    ]


def list_versions(db: Session, user: User, source_id: str) -> list[SourceVersionView]:
    """Versiones de una fuente, con cuántos fragmentos tiene cada una."""
    assert_permission(db, user, "source.review")
    if db.get(Source, source_id) is None:
        raise NotFound("Fuente no encontrada")
    counts = (
        select(SourceChunk.source_version_id, func.count().label("total"))
        .group_by(SourceChunk.source_version_id)
        .subquery()
    )
    rows = db.execute(
        select(SourceVersion, func.coalesce(counts.c.total, 0))
        .outerjoin(counts, counts.c.source_version_id == SourceVersion.id)
        .where(SourceVersion.source_id == source_id)
        .order_by(SourceVersion.created_at.desc())
    ).all()
    return [
        SourceVersionView(
            id=version.id,
            source_id=version.source_id,
            version_label=version.version_label,
            publication_date=version.publication_date,
            consulted_at=version.consulted_at,
            valid_from=version.valid_from,
            valid_to=version.valid_to,
            content_hash=version.content_hash,
            storage_key=version.storage_key,
            status=version.status,
            chunk_count=int(total),
        )
        for version, total in rows
    ]


def list_chunks(db: Session, user: User, version_id: str) -> list[SourceChunkView]:
    """Fragmentos indexables de una versión."""
    assert_permission(db, user, "source.review")
    if db.get(SourceVersion, version_id) is None:
        raise NotFound("Versión no encontrada")
    rows = db.scalars(
        select(SourceChunk)
        .where(SourceChunk.source_version_id == version_id)
        .order_by(SourceChunk.chunk_number)
    ).all()
    return [SourceChunkView.model_validate(row) for row in rows]


def retire_source_version(db: Session, user: User, version_id: str, payload) -> dict[str, str]:
    """Retira una versión para que el asistente deje de citarla.

    Es la contraparte de `publish`: sin ella, sacar de circulación una norma
    desactualizada exigía un `UPDATE` manual en la base. La fuente pasa a
    `RETIRED` solo si no le queda ninguna otra versión publicada.
    """
    assert_permission(db, user, "source.publish")
    version = db.get(SourceVersion, version_id)
    if version is None:
        raise NotFound("Versión no encontrada")
    if version.status == "RETIRED":
        raise Conflict("La versión ya está retirada")

    previous_status = version.status
    version.status = "RETIRED"

    source = db.get(Source, version.source_id)
    remaining = db.scalar(
        select(func.count())
        .select_from(SourceVersion)
        .where(
            SourceVersion.source_id == version.source_id,
            SourceVersion.id != version.id,
            SourceVersion.status == "PUBLISHED",
        )
    )
    if source and not remaining:
        source.status = "RETIRED"

    _record_status_change(
        db,
        version,
        previous_status=previous_status,
        new_status="RETIRED",
        user=user,
        reason=payload.reason,
    )
    write_audit(
        db, actor=user, action="source.retire", object_type="source_version", object_id=version.id
    )
    db.commit()
    return {"id": version.id, "status": version.status}


def _count_words(text: str) -> int:
    return max(1, len(text.split()))


def create_source_chunks(
    db: Session, user: User, version_id: str, payload: SourceChunkBulkCreate
) -> dict[str, int]:
    """Carga una tanda completa de fragmentos en una sola transacción.

    Una petición por fragmento dejaría, ante un fallo a media carga, una versión
    publicable con el contenido incompleto: el asistente citaría un documento
    truncado sin que nadie lo note.

    `source_chunks` tiene unicidad sobre `(source_version_id, content_hash)`, y
    en un documento normativo los párrafos repetidos son frecuentes. En vez de
    dejar que estalle una violación de integridad, se comprueba antes y se dice
    cuáles son: es la diferencia entre un mensaje accionable y un error de base.
    """
    assert_permission(db, user, "source.review")
    version = db.get(SourceVersion, version_id)
    if version is None:
        raise NotFound("Versión no encontrada")

    hashes = [hashlib.sha256(item.content.encode()).hexdigest() for item in payload.chunks]

    vistos: dict[str, int] = {}
    repetidos_en_la_tanda = []
    for posicion, huella in enumerate(hashes, start=1):
        if huella in vistos:
            repetidos_en_la_tanda.append(f"{posicion} repite el {vistos[huella]}")
        else:
            vistos[huella] = posicion
    if repetidos_en_la_tanda:
        raise Invalid(
            "Hay fragmentos con el mismo contenido: " + "; ".join(repetidos_en_la_tanda)
        )

    ya_presentes = set(
        db.scalars(
            select(SourceChunk.content_hash).where(
                SourceChunk.source_version_id == version_id,
                SourceChunk.content_hash.in_(hashes),
            )
        )
    )
    if ya_presentes:
        posiciones = [str(vistos[huella]) for huella in sorted(ya_presentes)]
        raise Invalid(
            "Estos fragmentos ya están cargados en esta versión: "
            + ", ".join(sorted(posiciones, key=int))
        )

    siguiente = (
        db.scalar(
            select(func.coalesce(func.max(SourceChunk.chunk_number), 0)).where(
                SourceChunk.source_version_id == version_id
            )
        )
        or 0
    ) + 1

    for desplazamiento, (item, huella) in enumerate(zip(payload.chunks, hashes, strict=True)):
        db.add(
            SourceChunk(
                source_version_id=version_id,
                chunk_number=siguiente + desplazamiento,
                heading=item.heading,
                content=item.content,
                content_hash=huella,
                page_number=item.page_number,
                token_count=_count_words(item.content),
            )
        )

    write_audit(
        db,
        actor=user,
        action="source.chunks_bulk",
        object_type="source_version",
        object_id=version_id,
        metadata={"count": len(payload.chunks)},
    )
    db.commit()
    return {
        "created": len(payload.chunks),
        "first_chunk_number": siguiente,
        "last_chunk_number": siguiente + len(payload.chunks) - 1,
    }
