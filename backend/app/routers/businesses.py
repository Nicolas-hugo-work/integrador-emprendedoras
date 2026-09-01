"""Emprendimientos."""

from fastapi import APIRouter

from app.api_contracts import BusinessCreate, BusinessView
from app.dependencies import DB, CurrentUser
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessView, status_code=201)
def create_business(payload: BusinessCreate, db: DB, user: CurrentUser) -> BusinessView:
    return business_service.create_business(db, user, payload)


@router.get("", response_model=list[BusinessView])
def list_businesses(db: DB, user: CurrentUser) -> list[BusinessView]:
    return business_service.list_businesses(db, user)
