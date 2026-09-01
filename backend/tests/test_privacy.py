"""Consentimientos, exportación, eliminación y auditoría."""

from datetime import UTC, datetime, timedelta

from conftest import requires_database

pytestmark = requires_database


def test_optional_consent_can_be_granted_and_withdrawn(client, account) -> None:
    for decision in ("GRANTED", "WITHDRAWN"):
        response = client.post(
            "/consents",
            headers=account.headers,
            json={"purpose_code": "AUDIO", "version": "1.0", "decision": decision},
        )
        assert response.status_code == 201, response.text
        assert response.json()["decision"] == decision


def test_withdrawing_an_optional_consent_does_not_close_the_account(client, account) -> None:
    """Retirar audio o investigación desactiva la función, no la cuenta."""
    for purpose in ("AUDIO", "RESEARCH"):
        withdrawn = client.post(
            "/consents",
            headers=account.headers,
            json={"purpose_code": purpose, "version": "1.0", "decision": "WITHDRAWN"},
        )
        assert withdrawn.status_code == 201, withdrawn.text

    still_active = client.get("/me", headers=account.headers)
    assert still_active.status_code == 200
    assert still_active.json()["status"] == "ACTIVE"


def test_consents_start_with_the_account_purpose_granted(client, account) -> None:
    """El alta otorga ACCOUNT; el resto queda sin decidir, no en falso."""
    response = client.get("/consents", headers=account.headers)
    assert response.status_code == 200
    by_code = {item["purpose_code"]: item for item in response.json()}
    assert {"ACCOUNT", "AUDIO", "RESEARCH", "SECONDARY_USE"} == set(by_code)

    assert by_code["ACCOUNT"]["decision"] == "GRANTED"
    assert by_code["ACCOUNT"]["allowed"] is True
    assert by_code["ACCOUNT"]["is_required"] is True

    assert by_code["AUDIO"]["decision"] is None
    assert by_code["AUDIO"]["allowed"] is False
    assert by_code["AUDIO"]["decided_at"] is None
    assert by_code["AUDIO"]["withdrawal_effect"], "la interfaz explica qué implica retirar"


def test_the_stored_consent_survives_a_reload(client, account) -> None:
    """El defecto que motivó la fase: la pantalla mostraba estado local."""
    granted = client.post(
        "/consents",
        headers=account.headers,
        json={"purpose_code": "AUDIO", "version": "1.0", "decision": "GRANTED"},
    )
    assert granted.status_code == 201

    audio = next(
        item
        for item in client.get("/consents", headers=account.headers).json()
        if item["purpose_code"] == "AUDIO"
    )
    assert audio["decision"] == "GRANTED"
    assert audio["allowed"] is True
    assert audio["version"] == "1.0"
    assert audio["decided_at"]

    client.post(
        "/consents",
        headers=account.headers,
        json={"purpose_code": "AUDIO", "version": "1.0", "decision": "WITHDRAWN"},
    )
    audio = next(
        item
        for item in client.get("/consents", headers=account.headers).json()
        if item["purpose_code"] == "AUDIO"
    )
    assert audio["decision"] == "WITHDRAWN", "vale la última decisión, no la primera"
    assert audio["allowed"] is False


def test_consents_are_isolated_between_accounts(client, make_account) -> None:
    alice, bob = make_account(), make_account()
    client.post(
        "/consents",
        headers=alice.headers,
        json={"purpose_code": "RESEARCH", "version": "1.0", "decision": "GRANTED"},
    )
    research = next(
        item
        for item in client.get("/consents", headers=bob.headers).json()
        if item["purpose_code"] == "RESEARCH"
    )
    assert research["decision"] is None, "la decisión de otra usuaria no se filtra"


def test_a_consent_version_that_is_not_current_is_rejected(client, account) -> None:
    response = client.post(
        "/consents",
        headers=account.headers,
        json={"purpose_code": "AUDIO", "version": "9.9", "decision": "GRANTED"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Versión no vigente"}


def test_data_export_is_accepted(client, account) -> None:
    response = client.post("/privacy/export", headers=account.headers)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["request_id"]


def test_account_deletion_deactivates_now_and_schedules_the_purge(client, make_account) -> None:
    doomed = make_account()
    response = client.post(
        "/privacy/deletion",
        headers=doomed.headers,
        json={"confirmation": "ELIMINAR MI CUENTA"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["request_id"]

    purge_due_at = datetime.fromisoformat(body["purge_due_at"])
    now = datetime.now(UTC).replace(tzinfo=None)
    assert timedelta(days=29) < purge_due_at - now <= timedelta(days=30)

    # La desactivación es inmediata: el token deja de servir.
    assert client.get("/me", headers=doomed.headers).status_code == 401
    assert client.post("/auth/login", json={"contact": doomed.contact, "password": doomed.password}).status_code == 401


def test_deletion_requires_the_exact_confirmation(client, account) -> None:
    response = client.post(
        "/privacy/deletion", headers=account.headers, json={"confirmation": "borrar"}
    )
    assert response.status_code == 422


def test_mutations_leave_a_pseudonymised_audit_trail(client, make_account) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.admin_research import AuditEvent

    actor = make_account()
    client.post(
        "/businesses",
        headers=actor.headers,
        json={"name": "Auditada", "stage": "IDEA", "activity": "Servicios"},
    )

    with SessionLocal() as db:
        events = list(
            db.scalars(select(AuditEvent).where(AuditEvent.actor_user_id == actor.user_id))
        )
    actions = {event.action for event in events}
    assert {"account.register", "contact.verify", "auth.login", "business.create"} <= actions
    for event in events:
        assert event.actor_pseudonym and len(event.actor_pseudonym) == 32
        assert event.integrity_hash and len(event.integrity_hash) == 64
        assert event.correlation_id
