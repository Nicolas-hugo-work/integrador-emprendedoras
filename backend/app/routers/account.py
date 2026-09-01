"""Cuenta de la usuaria autenticada."""

from fastapi import APIRouter

from app.api_contracts import UserView
from app.dependencies import DB, CurrentUser
from app.services import account_service

router = APIRouter(tags=["account"])


@router.get("/me", response_model=UserView)
def me(db: DB, user: CurrentUser) -> UserView:
    return account_service.current_account(db, user)
