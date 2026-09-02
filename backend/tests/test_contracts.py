"""Regresión de contrato: OpenAPI y esquema de base de datos.

Desde v0.3.0 la comprobación es **aditiva**, no de identidad: la API crece, así
que exigir un documento idéntico bloquearía cualquier endpoint nuevo. Lo que se
protege es la compatibilidad hacia atrás.

- Ninguna operación de la línea base puede desaparecer ni cambiar.
- Toda operación nueva debe estar declarada aquí.
- Ningún schema puede perder propiedades; los cambios deben ser aditivos y
  estar declarados.
"""

import json
import os
from pathlib import Path

import pytest
from conftest import TEST_DATABASE_URL, requires_database
from schema_fingerprint import build_fingerprint
from sqlalchemy import create_engine

CONTRACTS = Path(__file__).resolve().parent / "contracts"
METHODS = {"get", "post", "put", "patch", "delete"}

#: Línea base: el contrato publicado en v0.2.0.
BASELINE = json.loads((CONTRACTS / "openapi_v0_2.json").read_text(encoding="utf-8"))

#: Operaciones que v0.3.0 agrega, con el motivo. Una ruta nueva que no figure
#: aquí hace fallar la batería: obliga a declarar cada ampliación de la API.
APPROVED_NEW_OPERATIONS = {
    ("/source-publishers", "get"): "Curaduría: instituciones emisoras para el alta",
    ("/sources", "get"): "Curaduría: listar fuentes y su estado",
    ("/sources/{source_id}/versions", "get"): "Curaduría: versiones de una fuente",
    ("/source-versions/{version_id}/chunks", "get"): "Curaduría: fragmentos de una versión",
    ("/source-versions/{version_id}/retire", "post"): "Retirar una fuente desactualizada",
    ("/businesses/{business_id}", "patch"): "Corregir datos del emprendimiento",
    ("/businesses/{business_id}", "delete"): "Borrado lógico del emprendimiento",
    ("/finance/movements/{movement_id}", "patch"): "Corregir un movimiento mal registrado",
    ("/finance/movements/{movement_id}", "delete"): "Borrado lógico de un movimiento",
    ("/finance/costs", "get"): "Listar costos para poder corregirlos",
    ("/finance/costs/{cost_id}", "patch"): "Corregir un costo",
    ("/finance/costs/{cost_id}", "delete"): "Borrado lógico de un costo",
    ("/consents", "get"): "Leer el consentimiento vigente por finalidad",
    ("/audit-events", "get"): "Visor de auditoría para administración e investigación",
    ("/privacy/export/{request_id}", "get"): "Descarga de la copia de datos",
    ("/security-alerts", "get"): "Cola de alertas de seguridad",
    ("/security-alerts/{alert_id}/acknowledge", "post"): "Tomar una alerta",
    ("/security-alerts/{alert_id}/resolve", "post"): "Cerrar una alerta",
    ("/accounts/lookup", "get"): "Buscar una cuenta por contacto completo",
    ("/accounts/{user_id}", "get"): "Ficha de la cuenta que señala una alerta",
    ("/accounts/{user_id}/suspend", "post"): "Suspender una cuenta",
    ("/accounts/{user_id}/reactivate", "post"): "Reactivar una cuenta suspendida",
}

#: Schemas que cambian respecto de v0.2.0. El cambio debe ser aditivo: se
#: comprueba que ninguna propiedad previa desaparezca ni se altere.
APPROVED_SCHEMA_CHANGES = {
    "UserView": "v0.3.0 añade roles y permissions para condicionar la interfaz por capacidad",
}


def _operations(spec: dict) -> dict[tuple[str, str], dict]:
    return {
        (path, method): operation
        for path, item in spec["paths"].items()
        for method, operation in item.items()
        if method in METHODS
    }


@pytest.fixture(scope="module")
def current() -> dict:
    from app.main import app

    return json.loads(json.dumps(app.openapi()))


def test_no_baseline_operation_disappeared(current) -> None:
    """Ninguna operación publicada en v0.2.0 puede desaparecer."""
    missing = set(_operations(BASELINE)) - set(_operations(current))
    assert not missing, f"operaciones eliminadas: {sorted(missing)}"


def test_baseline_operations_are_unchanged(current) -> None:
    """Las operaciones heredadas conservan schemas, códigos y seguridad."""
    baseline, actual = _operations(BASELINE), _operations(current)
    for key, operation in baseline.items():
        assert actual[key] == operation, f"cambió la operación {key[1].upper()} {key[0]}"


def test_new_operations_are_declared(current) -> None:
    """Una ruta nueva sin declarar hace fallar la batería a propósito."""
    added = set(_operations(current)) - set(_operations(BASELINE))
    undeclared = added - set(APPROVED_NEW_OPERATIONS)
    assert not undeclared, (
        f"operaciones nuevas sin declarar en APPROVED_NEW_OPERATIONS: {sorted(undeclared)}"
    )


def test_schema_changes_are_declared_and_additive(current) -> None:
    """Un schema puede ganar propiedades, nunca perderlas ni cambiarlas."""
    old = BASELINE["components"]["schemas"]
    new = current["components"]["schemas"]

    assert not set(old) - set(new), f"schemas eliminados: {sorted(set(old) - set(new))}"

    for name, definition in old.items():
        if definition == new[name]:
            continue
        assert name in APPROVED_SCHEMA_CHANGES, f"cambio de schema sin declarar: {name}"
        previous = definition.get("properties", {})
        current_properties = new[name].get("properties", {})
        for field, shape in previous.items():
            assert field in current_properties, f"{name}.{field} desapareció"
            assert current_properties[field] == shape, f"{name}.{field} cambió de forma"


@requires_database
def test_database_schema_matches_frozen_fingerprint(migrated_database) -> None:
    """Las 62 tablas, índices, vistas y triggers no cambiaron.

    v0.3.0 no toca el esquema: toda su funcionalidad se apoya en columnas que ya
    existían (`deleted_at`, `source_status_history`, `user_consents`).
    """
    expected = json.loads((CONTRACTS / "schema_v0_1.json").read_text(encoding="utf-8"))
    engine = create_engine(os.environ["DATABASE_URL"])
    actual = build_fingerprint(engine)
    engine.dispose()

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


@pytest.mark.parametrize("name", ["openapi_v0_1", "openapi_v0_2", "schema_v0_1"])
def test_frozen_snapshots_keep_their_canonical_form(name: str) -> None:
    """Una línea base congelada no debe reformatearse.

    Un `oxfmt` ejecutado por error sobre `backend/tests` colapsó estos archivos
    a un elemento por línea. El contenido parseado no cambiaba, así que ninguna
    prueba fallaba, pero un snapshot que se reescribe solo deja de servir como
    referencia y ensucia todos los diffs posteriores.
    """
    path = CONTRACTS / f"{name}.json"
    raw = path.read_text(encoding="utf-8")
    canonical = json.dumps(
        json.loads(raw), indent=2, ensure_ascii=False, sort_keys=True
    )
    assert raw == canonical + chr(10), f"{name}.json perdió su formato canónico"


def test_test_database_url_is_configured_in_ci() -> None:
    """Avisa cuando la integración con MariaDB se está saltando en silencio."""
    if os.getenv("CI") and not TEST_DATABASE_URL:
        pytest.fail("En CI, TEST_DATABASE_URL debe apuntar a una MariaDB real")
