"""Consentimientos y derechos sobre los datos."""

from fastapi import APIRouter

from app.api_contracts import ConsentDecision, DeleteAccountRequest
from app.dependencies import DB, CurrentUser
from app.services import privacy_service

router = APIRouter(tags=["privacy"])


@router.post("/consents", status_code=201)
def decide_consent(payload: ConsentDecision, db: DB, user: CurrentUser) -> dict[str, str]:
    return privacy_service.decide_consent(db, user, payload)


@router.post("/privacy/deletion", status_code=202)
def request_account_deletion(
    payload: DeleteAccountRequest, db: DB, user: CurrentUser
) -> dict[str, str]:
    return privacy_service.request_account_deletion(db, user)


@router.post("/privacy/export", status_code=202)
def request_data_export(db: DB, user: CurrentUser) -> dict[str, str]:
    return privacy_service.request_data_export(db, user)
