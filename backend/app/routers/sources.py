"""Curaduría documental para el asistente RAG."""

from fastapi import APIRouter

from app.api_contracts import SourceChunkCreate, SourceCreate, SourceVersionCreate
from app.dependencies import DB, CurrentUser
from app.services import source_service

router = APIRouter(tags=["rag-admin"])


@router.post("/sources", status_code=201)
def create_source(payload: SourceCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source(db, user, payload)


@router.post("/source-versions", status_code=201)
def create_source_version(payload: SourceVersionCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source_version(db, user, payload)


@router.post("/source-chunks", status_code=201)
def create_source_chunk(payload: SourceChunkCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.create_source_chunk(db, user, payload)


@router.post("/source-versions/{version_id}/publish")
def publish_source_version(version_id: str, db: DB, user: CurrentUser) -> dict[str, str]:
    return source_service.publish_source_version(db, user, version_id)
