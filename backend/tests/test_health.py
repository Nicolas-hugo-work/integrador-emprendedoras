"""`/health` no puede decir ok si MariaDB no responde."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import Unavailable
from app.services.health_service import check


def test_check_reports_the_database_when_the_ping_works() -> None:
    db = MagicMock()
    assert check(db) == {
        "status": "ok",
        "service": "pwa-autonomia-backend",
        "database": "up",
    }
    db.execute.assert_called_once()


def test_check_is_unavailable_when_the_database_is_down() -> None:
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("down")
    with pytest.raises(Unavailable) as raised:
        check(db)
    assert raised.value.status == 503
    assert raised.value.detail == "La base de datos no responde"
