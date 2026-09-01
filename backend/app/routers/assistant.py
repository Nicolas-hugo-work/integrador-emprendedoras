"""Conversaciones, consulta al asistente y retroalimentación."""

from fastapi import APIRouter

from app.api_contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    ConversationCreate,
    ConversationView,
    FeedbackCreate,
)
from app.dependencies import DB, CurrentUser
from app.services import assistant_service

router = APIRouter(tags=["assistant"])


@router.post("/conversations", response_model=ConversationView, status_code=201)
def create_conversation(payload: ConversationCreate, db: DB, user: CurrentUser) -> ConversationView:
    return assistant_service.create_conversation(db, user, payload)


@router.get("/conversations", response_model=list[ConversationView])
def list_conversations(db: DB, user: CurrentUser) -> list[ConversationView]:
    return assistant_service.list_conversations(db, user)


@router.post("/assistant/query", response_model=AssistantQueryResponse)
def assistant_query(
    payload: AssistantQueryRequest, db: DB, user: CurrentUser
) -> AssistantQueryResponse:
    return assistant_service.answer_query(db, user, payload)


@router.post("/feedback", status_code=201)
def create_feedback(payload: FeedbackCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return assistant_service.create_feedback(db, user, payload)
