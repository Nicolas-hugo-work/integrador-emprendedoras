"""Recorrido completo de la API contra MariaDB real."""

from conftest import (
    CATEGORY_COST,
    CATEGORY_EXPENSE,
    CATEGORY_INCOME,
    CATEGORY_TRANSFER,
    requires_database,
)

pytestmark = requires_database


def test_health_is_public(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pwa-autonomia-backend"}


def test_me_returns_the_authenticated_account(client, account) -> None:
    response = client.get("/me", headers=account.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == account.user_id
    assert body["status"] == "ACTIVE"
    assert set(body) == {"id", "status", "locale", "timezone", "roles", "permissions"}
    # Quien se registra recibe EMPRENDEDORA y sus cuatro permisos sembrados.
    assert body["roles"] == ["EMPRENDEDORA"]
    assert body["permissions"] == [
        "conversation.manage_own",
        "finance.read_own",
        "finance.write_own",
        "profile.manage_own",
    ]
    assert "source.review" not in body["permissions"]


def test_me_requires_authentication(client) -> None:
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer no-sirve"}).status_code == 401


def test_business_lifecycle(client, account) -> None:
    created = client.post(
        "/businesses",
        headers=account.headers,
        json={
            "name": "Tejidos Esperanza",
            "stage": "OPERATING",
            "activity": "Artesanía",
            "department_code": "LP",
            "municipality": "El Alto",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Tejidos Esperanza"
    assert body["status"]

    listed = client.get("/businesses", headers=account.headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]


def test_financial_categories_are_seeded(client, account) -> None:
    response = client.get("/finance/categories", headers=account.headers)
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert {"SALES", "OTHER_INCOME", "SUPPLIES", "SERVICES", "TRANSFER"} <= codes


def test_movements_and_summary_are_consistent(client, account, business) -> None:
    def movement(category: str, kind: str, amount: str, **extra) -> dict:
        payload = {
            "business_id": business,
            "category_id": category,
            "movement_type": kind,
            "scope": "BUSINESS",
            "amount": amount,
            "currency": "BOB",
            "occurred_on": "2026-08-31",
            **extra,
        }
        response = client.post("/finance/movements", headers=account.headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    income = movement(CATEGORY_INCOME, "INCOME", "1500.50", note="Venta de la feria")
    assert income["note"] == "Venta de la feria", "la nota se descifra al devolverla"
    movement(CATEGORY_COST, "COST", "300.25")
    movement(CATEGORY_EXPENSE, "EXPENSE", "199.75")

    summary = client.get(
        "/finance/summary", headers=account.headers, params={"business_id": business}
    )
    assert summary.status_code == 200
    assert summary.json() == {"income": "1500.50", "outflow": "500.00", "balance": "1000.50"}

    # Una transferencia hogar-negocio no puede inflar los ingresos.
    movement(CATEGORY_TRANSFER, "TRANSFER", "800.00", counter_scope="HOUSEHOLD")
    after = client.get(
        "/finance/summary", headers=account.headers, params={"business_id": business}
    )
    assert after.json() == {"income": "1500.50", "outflow": "500.00", "balance": "1000.50"}

    listed = client.get(
        "/finance/movements", headers=account.headers, params={"business_id": business}
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 4


def test_transfer_without_counter_scope_is_rejected(client, account, business) -> None:
    response = client.post(
        "/finance/movements",
        headers=account.headers,
        json={
            "business_id": business,
            "category_id": CATEGORY_TRANSFER,
            "movement_type": "TRANSFER",
            "scope": "BUSINESS",
            "amount": "10.00",
            "currency": "BOB",
            "occurred_on": "2026-08-31",
        },
    )
    assert response.status_code == 422
    assert "transferencia" in response.text.casefold()


def test_costs_and_pricing_are_reproducible(client, account, business) -> None:
    cost_ids = []
    for name, amount in (("Lana", "80.00"), ("Tintes", "20.00")):
        created = client.post(
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
        assert created.status_code == 201, created.text
        cost_ids.append(created.json()["id"])

    scenario = client.post(
        "/finance/pricing",
        headers=account.headers,
        json={
            "business_id": business,
            "product_name": "Chompa",
            "units": "10",
            "margin_percent": "25",
            "cost_item_ids": cost_ids,
            "currency": "BOB",
        },
    )
    assert scenario.status_code == 200, scenario.text
    # (80 + 20) / 10 = 10.00 ; 10.00 * 1.25 = 12.50
    assert scenario.json()["unit_cost"] == "10.00"
    assert scenario.json()["suggested_price"] == "12.50"


def test_conversations_round_trip(client, account, business) -> None:
    created = client.post(
        "/conversations",
        headers=account.headers,
        json={"business_id": business, "title": "Dudas de formalización", "topic_code": "LEGAL"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["title"] == "Dudas de formalización"

    listed = client.get("/conversations", headers=account.headers)
    assert listed.status_code == 200
    assert created.json()["id"] in [item["id"] for item in listed.json()]


def test_session_can_be_refreshed_and_closed(client, account) -> None:
    refreshed = client.post("/auth/refresh", json={"refresh_token": account.refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    rotated = refreshed.json()
    assert rotated["refresh_token"] != account.refresh_token, "el token de refresco rota"

    # El token anterior queda revocado.
    assert client.post("/auth/refresh", json={"refresh_token": account.refresh_token}).status_code == 401

    headers = {"Authorization": f"Bearer {rotated['access_token']}"}
    closed = client.post(
        "/auth/logout", headers=headers, json={"refresh_token": rotated["refresh_token"]}
    )
    assert closed.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401
