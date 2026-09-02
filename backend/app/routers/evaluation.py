"""Banco de evaluación del asistente: conjuntos, casos y corridas."""

from fastapi import APIRouter, Query

from app.api_contracts import (
    EvaluationCaseCreate,
    EvaluationCaseView,
    EvaluationRunDetail,
    EvaluationRunView,
    EvaluationSetCreate,
    EvaluationSetView,
)
from app.dependencies import DB, CurrentUser
from app.services import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/sets", response_model=list[EvaluationSetView])
def list_sets(db: DB, user: CurrentUser) -> list[EvaluationSetView]:
    return evaluation_service.list_sets(db, user)


@router.post("/sets", status_code=201)
def create_set(payload: EvaluationSetCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return evaluation_service.create_set(db, user, payload)


@router.get("/sets/{set_id}/cases", response_model=list[EvaluationCaseView])
def list_cases(set_id: str, db: DB, user: CurrentUser) -> list[EvaluationCaseView]:
    return evaluation_service.list_cases(db, user, set_id)


@router.post("/sets/{set_id}/cases", status_code=201)
def create_case(
    set_id: str, payload: EvaluationCaseCreate, db: DB, user: CurrentUser
) -> dict[str, str]:
    return evaluation_service.create_case(db, user, set_id, payload)


@router.post("/sets/{set_id}/runs", status_code=201, response_model=EvaluationRunDetail)
def run_evaluation(set_id: str, db: DB, user: CurrentUser) -> EvaluationRunDetail:
    """Ejecuta el conjunto y devuelve la corrida con su detalle."""
    return evaluation_service.run_evaluation(db, user, set_id)


@router.get("/runs", response_model=list[EvaluationRunView])
def list_runs(
    db: DB, user: CurrentUser, evaluation_set_id: str | None = Query(default=None)
) -> list[EvaluationRunView]:
    return evaluation_service.list_runs(db, user, evaluation_set_id=evaluation_set_id)


@router.get("/runs/{run_id}", response_model=EvaluationRunDetail)
def read_run(run_id: str, db: DB, user: CurrentUser) -> EvaluationRunDetail:
    return evaluation_service.read_run(db, user, run_id)
