"""Aislamiento entre usuarias.

Una usuaria no debe alcanzar datos de otra ni deducir su existencia por la
diferencia entre respuestas: un recurso ajeno responde exactamente igual que uno
inexistente.
"""

import uuid

from conftest import CATEGORY_INCOME, requires_database

pytestmark = requires_database

#: Identificador con forma válida que no existe en la base.
ABSENT_ID = str(uuid.uuid4())


def _assistant_message_id(conversation_id: str) -> str:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.conversation import Message

    with SessionLocal() as db:
        message = db.scalar(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.sender == "ASSISTANT")
            .order_by(Message.sequence_number.desc())
        )
        assert message is not None
        return message.id


def test_businesses_are_not_visible_across_accounts(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    created = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    )
    assert created.status_code == 201
    assert client.get("/businesses", headers=bob.headers).json() == []


def test_foreign_business_is_indistinguishable_from_missing(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]

    foreign = client.get("/finance/summary", headers=bob.headers, params={"business_id": business})
    missing = client.get("/finance/summary", headers=bob.headers, params={"business_id": ABSENT_ID})
    assert foreign.status_code == 404
    assert foreign.status_code == missing.status_code
    assert foreign.json() == missing.json(), "la respuesta revela si el negocio existe"


def test_movements_cannot_target_a_foreign_business(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]

    created = client.post(
        "/finance/movements",
        headers=bob.headers,
        json={
            "business_id": business,
            "category_id": CATEGORY_INCOME,
            "movement_type": "INCOME",
            "scope": "BUSINESS",
            "amount": "10.00",
            "currency": "BOB",
            "occurred_on": "2026-08-31",
        },
    )
    assert created.status_code == 404

    listed = client.get(
        "/finance/movements", headers=bob.headers, params={"business_id": business}
    )
    assert listed.status_code == 404


def test_costs_and_pricing_cannot_target_a_foreign_business(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]

    cost = client.post(
        "/finance/costs",
        headers=bob.headers,
        json={
            "business_id": business,
            "name": "Harina",
            "cost_type": "VARIABLE",
            "amount": "10.00",
            "currency": "BOB",
            "unit": "kg",
            "periodicity": "MENSUAL",
            "quantity_base": "1",
        },
    )
    assert cost.status_code == 404

    pricing = client.post(
        "/finance/pricing",
        headers=bob.headers,
        json={
            "business_id": business,
            "product_name": "Pan",
            "units": "10",
            "margin_percent": "20",
            "cost_item_ids": [ABSENT_ID],
            "currency": "BOB",
        },
    )
    assert pricing.status_code == 404


def test_a_movement_of_another_account_never_appears(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]
    client.post(
        "/finance/movements",
        headers=alice.headers,
        json={
            "business_id": business,
            "category_id": CATEGORY_INCOME,
            "movement_type": "INCOME",
            "scope": "BUSINESS",
            "amount": "999.00",
            "currency": "BOB",
            "occurred_on": "2026-08-31",
        },
    )
    assert client.get("/finance/movements", headers=bob.headers).json() == []


def test_conversations_are_isolated(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    conversation = client.post(
        "/conversations", headers=alice.headers, json={"title": "Privado"}
    ).json()["id"]

    assert client.get("/conversations", headers=bob.headers).json() == []

    foreign = client.post(
        "/assistant/query",
        headers=bob.headers,
        json={"conversation_id": conversation, "message": "hola"},
    )
    missing = client.post(
        "/assistant/query",
        headers=bob.headers,
        json={"conversation_id": ABSENT_ID, "message": "hola"},
    )
    assert foreign.status_code == 404
    assert foreign.json() == missing.json()


def test_conversation_cannot_be_bound_to_a_foreign_business(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = client.post(
        "/businesses",
        headers=alice.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]

    response = client.post(
        "/conversations", headers=bob.headers, json={"business_id": business, "title": "Ajena"}
    )
    assert response.status_code == 404


def test_feedback_cannot_target_a_foreign_message(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    answered = client.post(
        "/assistant/query", headers=alice.headers, json={"message": "consulta de prueba"}
    )
    assert answered.status_code == 200, answered.text
    conversation_id = client.get("/conversations", headers=alice.headers).json()[0]["id"]
    message_id = _assistant_message_id(conversation_id)

    foreign = client.post(
        "/feedback", headers=bob.headers, json={"message_id": message_id, "feedback_type": "USEFUL"}
    )
    missing = client.post(
        "/feedback", headers=bob.headers, json={"message_id": ABSENT_ID, "feedback_type": "USEFUL"}
    )
    assert foreign.status_code == 404
    assert foreign.json() == missing.json()

    # La propietaria sí puede opinar, y solo una vez.
    own = client.post(
        "/feedback",
        headers=alice.headers,
        json={"message_id": message_id, "feedback_type": "USEFUL"},
    )
    assert own.status_code == 201
    repeated = client.post(
        "/feedback",
        headers=alice.headers,
        json={"message_id": message_id, "feedback_type": "USEFUL"},
    )
    assert repeated.status_code == 409


def _business_of(client, owner) -> str:
    return client.post(
        "/businesses",
        headers=owner.headers,
        json={"name": "Panadería Alba", "stage": "OPERATING", "activity": "Alimentos"},
    ).json()["id"]


def _movement_of(client, owner, business: str) -> str:
    return client.post(
        "/finance/movements",
        headers=owner.headers,
        json={
            "business_id": business,
            "category_id": CATEGORY_INCOME,
            "movement_type": "INCOME",
            "scope": "BUSINESS",
            "amount": "500.00",
            "currency": "BOB",
            "occurred_on": "2026-08-31",
        },
    ).json()["id"]


def _cost_of(client, owner, business: str) -> str:
    return client.post(
        "/finance/costs",
        headers=owner.headers,
        json={
            "business_id": business,
            "name": "Harina",
            "cost_type": "VARIABLE",
            "amount": "50.00",
            "currency": "BOB",
            "unit": "kg",
            "periodicity": "MENSUAL",
            "quantity_base": "1",
        },
    ).json()["id"]


def test_a_foreign_movement_cannot_be_edited_or_deleted(client, make_account) -> None:
    """Los verbos de mutación son superficie IDOR nueva en v0.3.0."""
    alice, bob = make_account(), make_account()
    movement = _movement_of(client, alice, _business_of(client, alice))

    patched = client.patch(
        f"/finance/movements/{movement}", headers=bob.headers, json={"amount": "1.00"}
    )
    missing_patch = client.patch(
        f"/finance/movements/{ABSENT_ID}", headers=bob.headers, json={"amount": "1.00"}
    )
    assert patched.status_code == 404
    assert patched.json() == missing_patch.json()

    removed = client.delete(f"/finance/movements/{movement}", headers=bob.headers)
    assert removed.status_code == 404

    # El movimiento de Alice sigue intacto.
    assert len(client.get("/finance/movements", headers=alice.headers).json()) == 1


def test_a_foreign_cost_cannot_be_edited_or_deleted(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = _business_of(client, alice)
    cost = _cost_of(client, alice, business)

    assert (
        client.patch(
            f"/finance/costs/{cost}", headers=bob.headers, json={"name": "Robado"}
        ).status_code
        == 404
    )
    assert client.delete(f"/finance/costs/{cost}", headers=bob.headers).status_code == 404
    assert (
        client.get(
            "/finance/costs", headers=bob.headers, params={"business_id": business}
        ).status_code
        == 404
    )
    assert len(
        client.get(
            "/finance/costs", headers=alice.headers, params={"business_id": business}
        ).json()
    ) == 1


def test_a_foreign_business_cannot_be_edited_or_deleted(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    business = _business_of(client, alice)

    patched = client.patch(
        f"/businesses/{business}", headers=bob.headers, json={"name": "Secuestrado"}
    )
    missing = client.patch(
        f"/businesses/{ABSENT_ID}", headers=bob.headers, json={"name": "Secuestrado"}
    )
    assert patched.status_code == 404
    assert patched.json() == missing.json()
    assert client.delete(f"/businesses/{business}", headers=bob.headers).status_code == 404
    assert client.get("/businesses", headers=alice.headers).json()[0]["name"] == "Panadería Alba"


def test_source_curation_requires_a_permission(client, account) -> None:
    """Una emprendedora sin rol de curaduría no puede crear fuentes."""
    response = client.post(
        "/sources",
        headers=account.headers,
        json={
            "publisher_id": ABSENT_ID,
            "title": "Guía de prueba",
            "canonical_url": "https://ejemplo.test/guia",
            "topic": "formalización",
        },
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Permiso insuficiente"}
