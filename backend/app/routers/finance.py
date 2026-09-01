"""Libro financiero: categorías, movimientos, costos, precios y resumen."""

from datetime import date

from fastapi import APIRouter, Query

from app.api_contracts import (
    CostItemCreate,
    FinancialMovementCreate,
    FinancialMovementView,
    PricingScenarioCreate,
)
from app.dependencies import DB, CurrentUser
from app.services import finance_service

router = APIRouter(prefix="/finance", tags=["finance"])


@router.post("/movements", response_model=FinancialMovementView, status_code=201)
def create_movement(
    payload: FinancialMovementCreate, db: DB, user: CurrentUser
) -> FinancialMovementView:
    return finance_service.create_movement(db, user, payload)


@router.get("/categories")
def list_financial_categories(db: DB, user: CurrentUser) -> list[dict[str, str]]:
    return finance_service.list_categories(db)


@router.get("/movements", response_model=list[FinancialMovementView])
def list_movements(
    db: DB,
    user: CurrentUser,
    business_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[FinancialMovementView]:
    return finance_service.list_movements(
        db, user, business_id=business_id, date_from=date_from, date_to=date_to
    )


@router.post("/costs", status_code=201)
def create_cost(payload: CostItemCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    return finance_service.create_cost(db, user, payload)


@router.post("/pricing")
def create_pricing_scenario(
    payload: PricingScenarioCreate, db: DB, user: CurrentUser
) -> dict[str, str]:
    return finance_service.create_pricing_scenario(db, user, payload)


@router.get("/summary")
def financial_summary(
    db: DB,
    user: CurrentUser,
    business_id: str,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict[str, str]:
    return finance_service.financial_summary(
        db, user, business_id=business_id, date_from=date_from, date_to=date_to
    )
