"""Comprobación de dependencias del proceso."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import Unavailable


def check(db: Session) -> dict[str, str]:
    """Confirma que MariaDB responde. Si no, 503: el proceso está vivo, la base no."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        error = Unavailable("La base de datos no responde")
        error.status = 503
        raise error from exc
    return {
        "status": "ok",
        "service": "pwa-autonomia-backend",
        "database": "up",
    }
