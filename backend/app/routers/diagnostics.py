"""Diagnóstico y ruta de formalización."""

from fastapi import APIRouter

from app.api_contracts import (
    DiagnosticAnswerWrite,
    DiagnosticQuestion,
    DiagnosticSessionCreate,
    DiagnosticSessionView,
    FormalizationRouteView,
)
from app.dependencies import DB, CurrentUser
from app.services import diagnostic_service

router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostic-questions", response_model=list[DiagnosticQuestion])
def list_questions(db: DB, user: CurrentUser) -> list[DiagnosticQuestion]:
    return diagnostic_service.list_questions(db, user)


@router.post("/diagnostic-sessions", response_model=DiagnosticSessionView, status_code=201)
def start_session(
    payload: DiagnosticSessionCreate, db: DB, user: CurrentUser
) -> DiagnosticSessionView:
    return diagnostic_service.start_session(db, user, payload)


@router.get("/diagnostic-sessions/{session_id}", response_model=DiagnosticSessionView)
def get_session(session_id: str, db: DB, user: CurrentUser) -> DiagnosticSessionView:
    return diagnostic_service.get_session(db, user, session_id)


@router.put("/diagnostic-sessions/{session_id}/answers", response_model=DiagnosticSessionView)
def save_answer(
    session_id: str, payload: DiagnosticAnswerWrite, db: DB, user: CurrentUser
) -> DiagnosticSessionView:
    return diagnostic_service.save_answer(db, user, session_id, payload)


@router.post(
    "/diagnostic-sessions/{session_id}/complete",
    response_model=FormalizationRouteView,
)
def complete_session(session_id: str, db: DB, user: CurrentUser) -> FormalizationRouteView:
    return diagnostic_service.complete_session(db, user, session_id)


@router.get("/formalization-routes", response_model=list[FormalizationRouteView])
def list_routes(business_id: str, db: DB, user: CurrentUser) -> list[FormalizationRouteView]:
    return diagnostic_service.list_routes(db, user, business_id)


@router.post("/formalization-steps/{step_id}/complete", response_model=FormalizationRouteView)
def complete_step(step_id: str, db: DB, user: CurrentUser) -> FormalizationRouteView:
    return diagnostic_service.complete_step(db, user, step_id)
