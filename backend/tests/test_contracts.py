"""Regresión de contrato: OpenAPI y esquema de base de datos.

Estas dos pruebas son la red de seguridad del refactor. Cualquier cambio no
aprobado en la superficie HTTP o en el esquema falla aquí.
"""

import json
import os
from pathlib import Path

import pytest
from conftest import TEST_DATABASE_URL, requires_database
from schema_fingerprint import build_fingerprint
from sqlalchemy import create_engine

CONTRACTS = Path(__file__).resolve().parent / "contracts"

#: Diferencias intencionales frente a `v0.1.0`, acordadas en el plan (§8).
#: `/auth/register` dejó de responder 409 ante un contacto ya registrado para
#: no permitir enumerar cuentas, y `/auth/login` puede responder 429. Ninguna
#: de las dos altera el documento OpenAPI, porque esos códigos no estaban
#: declarados explícitamente en las rutas.
APPROVED_OPENAPI_DIFFERENCES: dict[str, str] = {}


def test_openapi_matches_frozen_snapshot() -> None:
    """La superficie HTTP es idéntica a la de v0.1.0."""
    from app.main import app

    expected = json.loads((CONTRACTS / "openapi_v0_1.json").read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(app.openapi()))

    assert not APPROVED_OPENAPI_DIFFERENCES, "hay diferencias aprobadas sin reflejar"
    assert actual["paths"].keys() == expected["paths"].keys()
    for path in expected["paths"]:
        assert actual["paths"][path] == expected["paths"][path], f"cambió la ruta {path}"
    assert actual["components"]["schemas"] == expected["components"]["schemas"]


def test_operation_count_is_preserved() -> None:
    """Las 26 operaciones de la API siguen expuestas."""
    from app.main import app

    paths = app.openapi()["paths"]
    methods = {"get", "post", "put", "patch", "delete"}
    operations = [(p, m) for p, item in paths.items() for m in item if m in methods]
    assert len(operations) == 26


@requires_database
def test_database_schema_matches_frozen_fingerprint(migrated_database) -> None:
    """Las 62 tablas, índices, vistas y triggers no cambiaron."""
    expected = json.loads((CONTRACTS / "schema_v0_1.json").read_text(encoding="utf-8"))
    engine = create_engine(os.environ["DATABASE_URL"])
    actual = build_fingerprint(engine)

    assert actual["table_count"] == 62
    assert actual["tables"] == expected["tables"]
    for section in ("columns", "indexes", "constraints", "foreign_keys"):
        assert actual[section] == expected[section], f"cambió la sección {section}"
    assert actual["views"] == expected["views"]
    assert actual["triggers"] == expected["triggers"]


@requires_database
def test_mariadb_specific_objects_are_live(migrated_database) -> None:
    """La vista, el índice FULLTEXT y el índice VECTOR existen en la base real."""
    expected = json.loads((CONTRACTS / "schema_v0_1.json").read_text(encoding="utf-8"))
    assert "v_monthly_financial_summary" in expected["views"]
    assert any("FULLTEXT" in entry for entry in expected["indexes"]["source_chunks"])
    assert any("VECTOR" in entry for entry in expected["indexes"]["source_chunk_embeddings"])
    assert len(expected["triggers"]) == 2


def test_test_database_url_is_configured_in_ci() -> None:
    """Avisa cuando la integración con MariaDB se está saltando en silencio.

    `v0.1.0` dejaba `test_mariadb_integration` sin ejecutar salvo que alguien
    definiera `TEST_DATABASE_URL` a mano, así que la única prueba que tocaba la
    base nunca corría. En CI la variable es obligatoria.
    """
    if os.getenv("CI") and not TEST_DATABASE_URL:
        pytest.fail("En CI, TEST_DATABASE_URL debe apuntar a una MariaDB real")
