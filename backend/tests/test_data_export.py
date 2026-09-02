"""Exportación de datos.

Hasta v0.3.0 `POST /privacy/export` devolvía `202 PENDING` y nadie cumplía la
solicitud nunca: era un derecho registrado y no ejercido.
"""

import ast
import uuid
from pathlib import Path

from conftest import CATEGORY_INCOME, requires_database

from app.services.export_service import EXCLUDED_TABLES, EXPORTED_SECTIONS

pytestmark = requires_database

BACKEND = Path(__file__).resolve().parents[1]


def _request_export(client, account) -> str:
    response = client.post("/privacy/export", headers=account.headers)
    assert response.status_code == 202, response.text
    return response.json()["request_id"]


def test_the_export_carries_the_users_own_data(client, account, business) -> None:
    client.post(
        "/finance/movements",
        headers=account.headers,
        json={
            "business_id": business,
            "category_id": CATEGORY_INCOME,
            "movement_type": "INCOME",
            "scope": "BUSINESS",
            "amount": "1500.50",
            "currency": "BOB",
            "occurred_on": "2026-08-31",
            "note": "Venta de la feria",
        },
    )
    client.post(
        "/assistant/query", headers=account.headers, json={"message": "consulta propia"}
    )

    descarga = client.get(
        f"/privacy/export/{_request_export(client, account)}", headers=account.headers
    )
    assert descarga.status_code == 200, descarga.text
    contenido = descarga.json()

    assert contenido["perfil"]["id"] == account.user_id
    assert [c["valor"] for c in contenido["contactos"]] == [account.contact]
    assert [n["nombre"] for n in contenido["emprendimientos"]] == ["Tejidos Esperanza"]

    movimiento = contenido["movimientos_financieros"][0]
    assert movimiento["monto"] == "1500.50"
    assert movimiento["nota"] == "Venta de la feria", "la nota viaja descifrada"

    conversacion = contenido["conversaciones"][0]
    assert conversacion["mensajes"][0]["contenido"] == "consulta propia"

    assert contenido["preferencias"]["largo_de_respuesta"] == "MEDIUM"
    assert any(c["finalidad"] == "ACCOUNT" for c in contenido["consentimientos"])


def test_every_declared_section_is_present(client, account) -> None:
    contenido = client.get(
        f"/privacy/export/{_request_export(client, account)}", headers=account.headers
    ).json()
    for seccion in EXPORTED_SECTIONS:
        assert seccion in contenido, f"falta la sección {seccion}"


def test_the_export_never_carries_credentials(client, account) -> None:
    """Entregar credenciales sería crear el problema que esto resuelve."""
    crudo = client.get(
        f"/privacy/export/{_request_export(client, account)}", headers=account.headers
    ).text
    assert "$argon2" not in crudo, "no puede viajar el hash de la contraseña"
    for prohibido in ("password_hash", "refresh_token_hash", "token_hash", "password"):
        assert prohibido not in crudo, f"la exportación contiene {prohibido}"
    assert account.access_token not in crudo
    assert account.refresh_token not in crudo


def test_the_request_is_marked_as_fulfilled(client, account) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.privacy import DataExportRequest

    request_id = _request_export(client, account)
    assert client.get(
        f"/privacy/export/{request_id}", headers=account.headers
    ).status_code == 200

    with SessionLocal() as db:
        solicitud = db.scalar(
            select(DataExportRequest).where(DataExportRequest.id == request_id)
        )
    assert solicitud.status == "READY"
    assert solicitud.completed_at is not None


def test_a_foreign_export_is_indistinguishable_from_a_missing_one(
    client, make_account
) -> None:
    alice, bob = make_account(), make_account()
    ajena = client.get(
        f"/privacy/export/{_request_export(client, alice)}", headers=bob.headers
    )
    inexistente = client.get(f"/privacy/export/{uuid.uuid4()}", headers=bob.headers)
    assert ajena.status_code == 404
    assert ajena.json() == inexistente.json()


def test_a_curator_can_export_her_own_data(client, curator) -> None:
    """La exportación es un derecho: no depende de tener permisos de función."""
    descarga = client.get(
        f"/privacy/export/{_request_export(client, curator)}", headers=curator.headers
    )
    assert descarga.status_code == 200
    assert descarga.json()["perfil"]["id"] == curator.user_id
    assert descarga.json()["emprendimientos"] == []


def test_no_user_table_is_forgotten_by_the_export() -> None:
    """Guardia contra la desincronización con la purga.

    `tasks.purge_due_accounts` borra todas las tablas con datos de la usuaria.
    Cada una debe estar exportada o excluida a propósito: si v0.5.0 añade una
    tabla y solo la conecta a la purga, esta prueba lo detecta.
    """
    fuente = (BACKEND / "app" / "tasks.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    purga = next(
        nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "purge_due_accounts"
    )
    borradas = {
        nodo.args[0].id
        for nodo in ast.walk(purga)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "delete"
        and nodo.args
        and isinstance(nodo.args[0], ast.Name)
    }
    assert borradas, "no se pudo leer la lista de tablas de la purga"

    from app.models import Base

    por_clase = {
        mapeada.class_.__name__: mapeada.class_.__tablename__
        for mapeada in Base.registry.mappers
    }
    #: `users` es el perfil mismo, que siempre se exporta.
    exportadas = {
        "users",
        "user_preferences",
        "user_contacts",
        "businesses",
        "financial_movements",
        "cost_items",
        "pricing_scenarios",
        "conversations",
        "messages",
        "user_consents",
        "response_feedback",
        "deletion_requests",
    }

    sin_decidir = {
        por_clase[nombre]
        for nombre in borradas
        if por_clase.get(nombre) not in exportadas | EXCLUDED_TABLES.keys()
    }
    assert not sin_decidir, (
        f"tablas que la purga borra pero la exportación ignora: {sorted(sin_decidir)}. "
        "Añádalas a la exportación o justifíquelas en EXCLUDED_TABLES."
    )
