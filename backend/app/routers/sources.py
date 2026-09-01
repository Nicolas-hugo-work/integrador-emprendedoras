"""Curaduría documental para el asistente RAG."""

from fastapi import APIRouter, Query

from app.api_contracts import (
    PublisherView,
    RetireRequest,
    SourceChunkCreate,
    SourceChunkView,
    SourceCreate,
    SourceVersionCreate,
    SourceVersionView,
    SourceView,
)
from app.dependencies import DB, CurrentUser
from app.services import source_service

router = APIRouter(tags=["rag-admin"])


@router.get("/source-publishers", response_model=list[PublisherView])
def list_publishers(db: DB, user: CurrentUser) -> list[PublisherView]:
    return source_service.list_publishers(db, user)


@router.get("/sources", response_model=list[SourceView])
def list_sources(
    db: DB, user: CurrentUser, status: str | None = Query(default=None)
) -> list[SourceView]:
    return source_service.list_sources(db, user, status=status)


@router.post("/sources", status_code=201)
def create_source(payload: SourceCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source(db, user, payload)


@router.get("/sources/{source_id}/versions", response_model=list[SourceVersionView])
def list_source_versions(source_id: str, db: DB, user: CurrentUser) -> list[SourceVersionView]:
    return source_service.list_versions(db, user, source_id)


@router.post("/source-versions", status_code=201)
def create_source_version(payload: SourceVersionCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source_version(db, user, payload)


@router.get("/source-versions/{version_id}/chunks", response_model=list[SourceChunkView])
def list_source_chunks(version_id: str, db: DB, user: CurrentUser) -> list[SourceChunkView]:
    return source_service.list_chunks(db, user, version_id)


@router.post("/source-chunks", status_code=201)
def create_source_chunk(payload: SourceChunkCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source_chunk(db, user, payload)


@router.post("/source-versions/{version_id}/publish")
def publish_source_version(version_id: str, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.publish_source_version(db, user, version_id)


@router.post("/source-versions/{version_id}/retire")
def retire_source_version(
    version_id: str, payload: RetireRequest, db: DB, user: CurrentUser
) -> dict[str, str]:
    return source_service.retire_source_version(db, user, version_id, payload)
