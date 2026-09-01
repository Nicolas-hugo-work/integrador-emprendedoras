import os
import subprocess

import pytest
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="Requiere una base MariaDB de prueba aislada")
def test_migration_up_and_vector_query() -> None:
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT VERSION()"))
        assert version.scalar_one()
        tables = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
            )
        ).scalar_one()
        assert tables == 62
        vector_indexes = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND index_name = 'idx_chunk_embedding'"
            )
        ).scalar_one()
        assert vector_indexes == 1
    subprocess.run(["alembic", "downgrade", "base"], check=True, env=env)

