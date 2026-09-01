"""Cuenta de la usuaria autenticada."""

from fastapi import APIRouter

from app.api_contracts import UserView
from app.dependencies import CurrentUser

router = APIRouter(tags=["account"])


@router.get("/me", response_model=UserView)
def me(user: CurrentUser) -> UserView:
    return user
