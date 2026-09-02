"""Visor de la traza de auditoría.

Sin esta pantalla, separar los roles dejaría a `ADMINISTRADORA` y
`AUDITORA_INVESTIGADORA` con la aplicación vacía.
"""

import pytest
from conftest import requires_database

pytestmark = requires_database


@pytest.fixture
def auditor(make_staff):
    """Cuenta con solo el rol AUDITORA_INVESTIGADORA."""
    return make_staff("AUDITORA_INVESTIGADORA")


def test_the_trail_never_exposes_the_real_actor(client, auditor) -> None:
    """La aplicación le promete a la usuaria una auditoría seudonimizada."""
    response = client.get("/audit-events", headers=auditor.headers)
    assert response.status_code == 200
    eventos = response.json()
    assert eventos, "el propio registro de las cuentas ya deja traza"
    for evento in eventos:
        assert "actor_user_id" not in evento
        assert len(evento["actor_pseudonym"]) == 32
        assert len(evento["integrity_hash"]) == 64
        assert evento["correlation_id"]


def test_an_entrepreneur_cannot_read_the_trail(client, account) -> None:
    response = client.get("/audit-events", headers=account.headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Permiso insuficiente"}


def test_the_administrator_reads_the_same_trail(client, administrator) -> None:
    assert client.get("/audit-events", headers=administrator.headers).status_code == 200


def test_the_trail_can_be_filtered_and_paged(client, account, auditor) -> None:
    client.post(
        "/businesses",
        headers=account.headers,
        json={"name": "Deja traza", "stage": "IDEA", "activity": "Servicios"},
    )

    filtrado = client.get(
        "/audit-events", headers=auditor.headers, params={"action": "business.create"}
    )
    assert filtrado.status_code == 200
    assert filtrado.json(), "la creación de un negocio deja su evento"
    assert all(item["action"] == "business.create" for item in filtrado.json())
    assert all(item["object_type"] == "business" for item in filtrado.json())

    primera = client.get("/audit-events", headers=auditor.headers, params={"limit": 1})
    assert len(primera.json()) == 1
    segunda = client.get(
        "/audit-events", headers=auditor.headers, params={"limit": 1, "offset": 1}
    )
    assert segunda.json()[0]["id"] != primera.json()[0]["id"]


def test_the_page_size_is_capped(client, auditor) -> None:
    """Un filtro amplio no puede arrastrar la tabla entera."""
    assert client.get(
        "/audit-events", headers=auditor.headers, params={"limit": 500}
    ).status_code == 422


def test_the_newest_events_come_first(client, auditor) -> None:
    eventos = client.get("/audit-events", headers=auditor.headers).json()
    fechas = [item["occurred_at"] for item in eventos]
    assert fechas == sorted(fechas, reverse=True)
