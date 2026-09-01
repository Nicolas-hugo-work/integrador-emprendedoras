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
