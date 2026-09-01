"""Emprendimientos."""

from fastapi import APIRouter

from app.api_contracts import BusinessCreate, BusinessUpdate, BusinessView
from app.dependencies import DB, CurrentUser
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessView, status_code=201)
def create_business(payload: BusinessCreate, db: DB, user: CurrentUser) -> BusinessView:
    return business_service.create_business(db, user, payload)


@router.get("", response_model=list[BusinessView])
def list_businesses(db: DB, user: CurrentUser) -> list[BusinessView]:
    return business_service.list_businesses(db, user)


@router.patch("/{business_id}", response_model=BusinessView)
def update_business(
    business_id: str, payload: BusinessUpdate, db: DB, user: CurrentUser
) -> BusinessView:
    return business_service.update_business(db, user, business_id, payload)


@router.delete("/{business_id}", status_code=204)
def delete_business(business_id: str, db: DB, user: CurrentUser) -> None:
    business_service.delete_business(db, user, business_id)
