"""Ciclo completo de migración sobre MariaDB real.

Usa una base **distinta** de la de las pruebas funcionales: `alembic downgrade
base` deja el esquema vacío, así que compartirla destruiría los datos del resto
de la batería.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND_DIR = Path(__file__).resolve().parents[1]

#: Base dedicada al ciclo upgrade/downgrade/upgrade.
TEST_MIGRATION_DATABASE_URL = os.getenv("TEST_MIGRATION_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_MIGRATION_DATABASE_URL,
    reason="Requiere TEST_MIGRATION_DATABASE_URL apuntando a una MariaDB desechable",
)


def _alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": TEST_MIGRATION_DATABASE_URL or ""}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args], check=True, cwd=BACKEND_DIR, env=env
    )


def _count_application_tables(connection) -> int:
    """Cuenta las tablas de la aplicación, sin la de control de Alembic."""
    return connection.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' "
            "AND table_name <> 'alembic_version'"
        )
    ).scalar_one()


def test_migration_up_and_vector_query() -> None:
    """`upgrade head` crea las 62 tablas, el índice vectorial y los triggers.

    El recuento excluye `alembic_version`: la versión anterior de esta prueba
    comparaba contra 62 incluyéndola, de modo que habría fallado en cuanto
    llegara a ejecutarse.
    """
    _alembic("upgrade", "head")
    engine = create_engine(TEST_MIGRATION_DATABASE_URL)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT VERSION()")).scalar_one()
        assert _count_application_tables(connection) == 62
        vector_indexes = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND index_name = 'idx_chunk_embedding'"
            )
        ).scalar_one()
        assert vector_indexes == 1
        triggers = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.triggers "
                "WHERE trigger_schema = DATABASE()"
            )
        ).scalar_one()
        assert triggers == 2
        views = connection.execute(
            text("SELECT COUNT(*) FROM information_schema.views WHERE table_schema = DATABASE()")
        ).scalar_one()
        assert views == 1
    engine.dispose()


def test_downgrade_and_upgrade_again_is_reversible() -> None:
    """`downgrade base` deja la base vacía y un segundo `upgrade` la reconstruye."""
    _alembic("upgrade", "head")
    _alembic("downgrade", "base")
    engine = create_engine(TEST_MIGRATION_DATABASE_URL)
    with engine.connect() as connection:
        assert _count_application_tables(connection) == 0
    _alembic("upgrade", "head")
    with engine.connect() as connection:
        assert _count_application_tables(connection) == 62
    engine.dispose()
