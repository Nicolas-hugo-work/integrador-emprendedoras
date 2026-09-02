"""Administración: alertas de seguridad y suspensión de cuentas.

El límite de intentos que añadió `v0.2.0` bloqueaba una cuenta en memoria y no
dejaba nada sobre lo que actuar. `security_alerts` existía sin escribirse.
"""

import uuid

import pytest
from conftest import requires_database

pytestmark = requires_database

CLAVE_INCORRECTA = "una-contrasena-incorrecta"


def _fallar_login(client, contacto: str, veces: int) -> None:
    for _ in range(veces):
        client.post(
            "/auth/login", json={"contact": contacto, "password": CLAVE_INCORRECTA}
        )


def _alertas_de(client, administrator, **filtros) -> list[dict]:
    respuesta = client.get(
        "/security-alerts", headers=administrator.headers, params=filtros or None
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture
def sin_alertas_anonimas():
    """Limpia las alertas abiertas sin cuenta, que no son de esta prueba.

    Las alertas anónimas se deduplican globalmente mientras siguen `OPEN`, así
    que una dejada por otra prueba impediría crear la de esta.
    """
    from sqlalchemy import delete

    from app.database import SessionLocal
    from app.models.admin_research import SecurityAlert

    with SessionLocal() as db:
        db.execute(
            delete(SecurityAlert).where(
                SecurityAlert.user_id.is_(None), SecurityAlert.status == "OPEN"
            )
        )
        db.commit()


def test_five_failures_create_exactly_one_alert(client, account, administrator) -> None:
    """Cinco fallos generan una alerta, no cinco: se escribe en la transición."""
    _fallar_login(client, account.contact, 5)
    assert client.post(
        "/auth/login", json={"contact": account.contact, "password": CLAVE_INCORRECTA}
    ).status_code == 429, "el quinto fallo deja la cuenta bloqueada"

    propias = [
        alerta
        for alerta in _alertas_de(client, administrator)
        if alerta["user_id"] == account.user_id
    ]
    assert len(propias) == 1
    alerta = propias[0]
    assert alerta["alert_type"] == "login.contact_locked"
    assert alerta["severity"] == "MEDIUM"
    assert alerta["status"] == "OPEN"
    assert alerta["resolved_at"] is None


def test_the_alert_never_carries_the_contact_or_the_password(
    client, account, administrator
) -> None:
    """La cola no puede convertirse en un registro de quién intentó entrar dónde."""
    _fallar_login(client, account.contact, 5)
    alerta = next(
        a for a in _alertas_de(client, administrator) if a["user_id"] == account.user_id
    )
    assert account.contact not in alerta["description"]
    assert CLAVE_INCORRECTA not in alerta["description"]
    assert "5 intentos" in alerta["description"]


def test_an_unknown_contact_also_leaves_a_trace(
    client, administrator, sin_alertas_anonimas
) -> None:
    """Atacar un contacto inexistente también debe verse, con `user_id` nulo."""
    _fallar_login(client, f"fantasma-{uuid.uuid4().hex[:12]}@ejemplo.test", 5)

    anonimas = [
        a
        for a in _alertas_de(client, administrator, status="OPEN")
        if a["user_id"] is None and a["alert_type"] == "login.contact_locked"
    ]
    assert len(anonimas) == 1


def test_repeating_the_lockout_does_not_duplicate_an_open_alert(
    client, account, administrator
) -> None:
    from app.services.rate_limit import login_limiter

    _fallar_login(client, account.contact, 5)
    # Se olvida el bloqueo para poder volver a provocarlo dentro de la prueba.
    login_limiter.clear()
    _fallar_login(client, account.contact, 5)

    propias = [
        a for a in _alertas_de(client, administrator) if a["user_id"] == account.user_id
    ]
    assert len(propias) == 1, "mientras nadie la atienda, repetir no aporta nada"


def test_the_auditor_reads_but_cannot_act(client, account, administrator, make_staff) -> None:
    """Leer la cola es de auditoría; actuar sobre ella, de administración."""
    auditora = make_staff("AUDITORA_INVESTIGADORA")
    _fallar_login(client, account.contact, 5)
    alerta = next(
        a for a in _alertas_de(client, administrator) if a["user_id"] == account.user_id
    )

    assert client.get("/security-alerts", headers=auditora.headers).status_code == 200
    assert client.post(
        f"/security-alerts/{alerta['id']}/resolve", headers=auditora.headers
    ).status_code == 403
    assert client.post(
        f"/accounts/{account.user_id}/suspend",
        headers=auditora.headers,
        json={"reason": "No deberia poder"},
    ).status_code == 403


def test_an_alert_can_be_acknowledged_and_resolved(
    client, account, administrator
) -> None:
    _fallar_login(client, account.contact, 5)
    alerta = next(
        a for a in _alertas_de(client, administrator) if a["user_id"] == account.user_id
    )

    tomada = client.post(
        f"/security-alerts/{alerta['id']}/acknowledge", headers=administrator.headers
    )
    assert tomada.status_code == 200
    assert tomada.json()["status"] == "ACKNOWLEDGED"

    cerrada = client.post(
        f"/security-alerts/{alerta['id']}/resolve", headers=administrator.headers
    )
    assert cerrada.status_code == 200
    assert cerrada.json()["status"] == "RESOLVED"

    assert client.post(
        f"/security-alerts/{alerta['id']}/resolve", headers=administrator.headers
    ).status_code == 409


def test_suspending_cuts_access_immediately(client, account, administrator) -> None:
    """El token vigente deja de servir y no queda ninguna sesión activa."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.identity import Session as AuthSession

    assert client.get("/me", headers=account.headers).status_code == 200

    suspendida = client.post(
        f"/accounts/{account.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Actividad sospechosa en el piloto"},
    )
    assert suspendida.status_code == 200, suspendida.text
    assert suspendida.json()["status"] == "SUSPENDED"

    assert client.get("/me", headers=account.headers).status_code == 401
    assert client.post(
        "/auth/login", json={"contact": account.contact, "password": account.password}
    ).status_code == 401
    assert client.post(
        "/auth/refresh", json={"refresh_token": account.refresh_token}
    ).status_code == 401

    with SessionLocal() as db:
        vivas = db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == account.user_id, AuthSession.revoked_at.is_(None)
            )
        ).all()
    assert not vivas, "suspender debe revocar todas las sesiones"


def test_the_reason_is_kept_in_the_audit_trail(client, account, administrator) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.admin_research import AuditEvent

    client.post(
        f"/accounts/{account.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Motivo verificable"},
    )
    with SessionLocal() as db:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "account.suspend", AuditEvent.object_id == account.user_id
            )
        )
    assert evento is not None
    assert evento.metadata_json == {"reason": "Motivo verificable"}


def test_reactivating_gives_the_access_back(client, account, administrator) -> None:
    client.post(
        f"/accounts/{account.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Suspension temporal"},
    )
    devuelta = client.post(
        f"/accounts/{account.user_id}/reactivate", headers=administrator.headers
    )
    assert devuelta.status_code == 200
    assert devuelta.json()["status"] == "ACTIVE"

    reingreso = client.post(
        "/auth/login", json={"contact": account.contact, "password": account.password}
    )
    assert reingreso.status_code == 200, "vuelve a poder entrar"


def test_a_deleted_account_does_not_come_back(client, make_account, administrator) -> None:
    """Su purga ya está programada; revivirla contradiría lo prometido."""
    condenada = make_account()
    client.post(
        "/privacy/deletion",
        headers=condenada.headers,
        json={"confirmation": "ELIMINAR MI CUENTA"},
    )
    assert client.post(
        f"/accounts/{condenada.user_id}/reactivate", headers=administrator.headers
    ).status_code == 409
    assert client.post(
        f"/accounts/{condenada.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Ya esta eliminada"},
    ).status_code == 409


def test_nobody_can_leave_the_system_without_administration(
    client, administrator, make_staff
) -> None:
    otra = make_staff("ADMINISTRADORA")

    propia = client.post(
        f"/accounts/{administrator.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Autosuspension"},
    )
    assert propia.status_code == 409
    assert "propia cuenta" in propia.json()["detail"]

    ajena = client.post(
        f"/accounts/{otra.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Disputa entre administradoras"},
    )
    assert ajena.status_code == 409
    assert "administración" in ajena.json()["detail"]


def test_staff_without_the_permission_can_still_be_suspended(
    client, administrator, curator
) -> None:
    """La protección alcanza a quien administra, no a todo el personal."""
    respuesta = client.post(
        f"/accounts/{curator.user_id}/suspend",
        headers=administrator.headers,
        json={"reason": "Publico fuentes sin revisar"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["roles"] == ["CURADORA_RAG"]


def test_lookup_requires_the_full_contact(client, account, administrator) -> None:
    encontrada = client.get(
        "/accounts/lookup", headers=administrator.headers, params={"contact": account.contact}
    )
    assert encontrada.status_code == 200
    assert encontrada.json()["id"] == account.user_id
    assert encontrada.json()["roles"] == ["EMPRENDEDORA"]

    parcial = client.get(
        "/accounts/lookup",
        headers=administrator.headers,
        params={"contact": account.contact[:8]},
    )
    assert parcial.status_code == 404, "no admite búsquedas parciales"

    inexistente = client.get(
        "/accounts/lookup",
        headers=administrator.headers,
        params={"contact": "nadie@ejemplo.test"},
    )
    assert inexistente.status_code == 404
    assert inexistente.json() == parcial.json()


def test_the_lookup_is_audited(client, account, administrator) -> None:
    """Quién buscó a quién queda registrado."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.admin_research import AuditEvent

    client.get(
        "/accounts/lookup", headers=administrator.headers, params={"contact": account.contact}
    )
    with SessionLocal() as db:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "account.lookup",
                AuditEvent.object_id == account.user_id,
            )
        )
    assert evento is not None
    assert evento.actor_user_id == administrator.user_id


def test_alerts_can_be_filtered_by_status(client, account, administrator) -> None:
    _fallar_login(client, account.contact, 5)
    alerta = next(
        a for a in _alertas_de(client, administrator) if a["user_id"] == account.user_id
    )
    client.post(f"/security-alerts/{alerta['id']}/resolve", headers=administrator.headers)

    abiertas = _alertas_de(client, administrator, status="OPEN")
    assert alerta["id"] not in [a["id"] for a in abiertas]
    cerradas = _alertas_de(client, administrator, status="RESOLVED")
    assert alerta["id"] in [a["id"] for a in cerradas]
