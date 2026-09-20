"""Estado del servicio."""

from fastapi import APIRouter

from app.dependencies import DB
from app.services import health_service

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: DB) -> dict[str, str]:
    return health_service.check(db)
