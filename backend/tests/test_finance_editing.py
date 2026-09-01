"""Corrección de errores en el libro financiero.

Hasta v0.2.0 la API era de solo escritura: un monto mal tipeado era permanente.
"""

from conftest import CATEGORY_COST, CATEGORY_EXPENSE, CATEGORY_INCOME, CATEGORY_TRANSFER, requires_database

pytestmark = requires_database


def _movement(client, account, business, **extra) -> dict:
    payload = {
        "business_id": business,
        "category_id": CATEGORY_INCOME,
        "movement_type": "INCOME",
        "scope": "BUSINESS",
        "amount": "1500.50",
        "currency": "BOB",
        "occurred_on": "2026-08-31",
        **extra,
    }
    response = client.post("/finance/movements", headers=account.headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _summary(client, account, business) -> dict:
    return client.get(
        "/finance/summary", headers=account.headers, params={"business_id": business}
    ).json()


def test_a_mistyped_amount_can_be_corrected(client, account, business) -> None:
    """El caso que motivó la fase: se quiso poner 150.50 y salió 1500.50."""
    created = _movement(client, account, business)
    assert _summary(client, account, business)["income"] == "1500.50"

    corrected = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"amount": "150.50"},
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["amount"] == "150.50"
    assert _summary(client, account, business) == {
        "income": "150.50",
        "outflow": "0",
        "balance": "150.50",
    }


def test_editing_only_touches_the_fields_sent(client, account, business) -> None:
    created = _movement(client, account, business, note="Venta de la feria")
    patched = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"occurred_on": "2026-07-01"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["occurred_on"] == "2026-07-01"
    assert body["amount"] == "1500.50", "el monto no se envió y no debe cambiar"
    assert body["note"] == "Venta de la feria", "la nota cifrada se conserva"


def test_a_note_can_be_rewritten_and_cleared(client, account, business) -> None:
    created = _movement(client, account, business, note="Nota original")
    rewritten = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"note": "Nota corregida"},
    )
    assert rewritten.json()["note"] == "Nota corregida"

    cleared = client.patch(
        f"/finance/movements/{created['id']}", headers=account.headers, json={"note": None}
    )
    assert cleared.json()["note"] is None


def test_deleting_a_movement_removes_it_from_listing_and_summary(
    client, account, business
) -> None:
    keep = _movement(client, account, business, amount="100.00")
    drop = _movement(client, account, business, amount="900.00")
    assert _summary(client, account, business)["income"] == "1000.00"

    removed = client.delete(f"/finance/movements/{drop['id']}", headers=account.headers)
    assert removed.status_code == 204

    listed = client.get(
        "/finance/movements", headers=account.headers, params={"business_id": business}
    ).json()
    assert [item["id"] for item in listed] == [keep["id"]]
    assert _summary(client, account, business)["income"] == "100.00"

    # Un segundo borrado ya no encuentra nada.
    assert client.delete(f"/finance/movements/{drop['id']}", headers=account.headers).status_code == 404


def test_an_incoherent_transfer_is_rejected_on_update(client, account, business) -> None:
    """La regla vive en domain_rules y se aplica sobre el estado resultante."""
    created = _movement(client, account, business)
    response = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"movement_type": "TRANSFER", "category_id": CATEGORY_TRANSFER},
    )
    assert response.status_code == 422
    assert "transferencia" in response.text.casefold()


def test_a_transfer_can_be_completed_with_a_counter_scope(client, account, business) -> None:
    created = _movement(client, account, business)
    response = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={
            "movement_type": "TRANSFER",
            "category_id": CATEGORY_TRANSFER,
            "counter_scope": "HOUSEHOLD",
        },
    )
    assert response.status_code == 200, response.text
    # Una transferencia no altera ingresos ni salidas.
    assert _summary(client, account, business) == {
        "income": "0",
        "outflow": "0",
        "balance": "0",
    }


def test_a_category_incompatible_with_the_new_type_is_rejected(
    client, account, business
) -> None:
    created = _movement(client, account, business)
    response = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"movement_type": "EXPENSE"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Categoría incompatible con el movimiento"}


def test_changing_type_and_category_together_updates_the_summary(
    client, account, business
) -> None:
    created = _movement(client, account, business, amount="200.00")
    response = client.patch(
        f"/finance/movements/{created['id']}",
        headers=account.headers,
        json={"movement_type": "EXPENSE", "category_id": CATEGORY_EXPENSE},
    )
    assert response.status_code == 200, response.text
    assert _summary(client, account, business) == {
        "income": "0",
        "outflow": "200.00",
        "balance": "-200.00",
    }


def _cost(client, account, business, name="Lana", amount="80.00") -> dict:
    response = client.post(
        "/finance/costs",
        headers=account.headers,
        json={
            "business_id": business,
            "name": name,
            "cost_type": "VARIABLE",
            "amount": amount,
            "currency": "BOB",
            "unit": "kg",
            "periodicity": "MENSUAL",
            "quantity_base": "1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_costs_can_be_listed_edited_and_deleted(client, account, business) -> None:
    created = _cost(client, account, business, "Lana")
    listed = client.get(
        "/finance/costs", headers=account.headers, params={"business_id": business}
    )
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Lana"]

    edited = client.patch(
        f"/finance/costs/{created['id']}",
        headers=account.headers,
        json={"name": "Lana de alpaca", "amount": "95.00"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Lana de alpaca"
    assert edited.json()["amount"] == "95.00"
    assert edited.json()["unit"] == "kg", "lo no enviado no cambia"

    assert client.delete(f"/finance/costs/{created['id']}", headers=account.headers).status_code == 204
    assert (
        client.get(
            "/finance/costs", headers=account.headers, params={"business_id": business}
        ).json()
        == []
    )


def test_deleting_a_cost_does_not_alter_a_calculated_scenario(
    client, account, business
) -> None:
    """`pricing_scenario_costs` guarda la fotografía; la FK es ON DELETE SET NULL."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.finance import PricingScenarioCost

    first = _cost(client, account, business, "Lana", "80.00")
    second = _cost(client, account, business, "Tintes", "20.00")
    scenario = client.post(
        "/finance/pricing",
        headers=account.headers,
        json={
            "business_id": business,
            "product_name": "Chompa",
            "units": "10",
            "margin_percent": "25",
            "cost_item_ids": [first["id"], second["id"]],
            "currency": "BOB",
        },
    )
    assert scenario.status_code == 200
    assert scenario.json()["unit_cost"] == "10.00"

    assert client.delete(f"/finance/costs/{first['id']}", headers=account.headers).status_code == 204

    with SessionLocal() as db:
        snapshots = list(
            db.scalars(
                select(PricingScenarioCost).where(
                    PricingScenarioCost.scenario_id == scenario.json()["id"]
                )
            )
        )
    labels = {snapshot.label_snapshot for snapshot in snapshots}
    assert labels == {"Lana", "Tintes"}, "la fotografía histórica se conserva"
    assert sum(snapshot.amount_snapshot for snapshot in snapshots) == 100


def test_a_business_can_be_corrected_and_deleted(client, account, business) -> None:
    edited = client.patch(
        f"/businesses/{business}",
        headers=account.headers,
        json={"name": "Tejidos Esperanza SRL", "municipality": "Viacha"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Tejidos Esperanza SRL"
    assert edited.json()["municipality"] == "Viacha"
    assert edited.json()["activity"] == "Artesanía", "lo no enviado no cambia"

    _movement(client, account, business, category_id=CATEGORY_COST, movement_type="COST")

    assert client.delete(f"/businesses/{business}", headers=account.headers).status_code == 204
    assert client.get("/businesses", headers=account.headers).json() == []

    # El negocio ya no es alcanzable, pero el historial financiero se conserva.
    assert (
        client.get(
            "/finance/summary", headers=account.headers, params={"business_id": business}
        ).status_code
        == 404
    )
    assert len(client.get("/finance/movements", headers=account.headers).json()) == 1
