"""Endurecimiento de autenticación introducido en v0.2.0.

Cubre los cambios de comportamiento aprobados: registro sin enumeración,
límite de intentos y rechazo de secretos de ejemplo fuera de desarrollo.
"""

import uuid

import pytest
from conftest import requires_database
from pydantic import ValidationError

from app.config import PLACEHOLDER_SECRETS, Settings

VALID_SECRET = "un-secreto-suficientemente-largo-para-produccion"


def test_placeholder_secrets_are_rejected_outside_development() -> None:
    """`v0.1.0` arrancaba en cualquier entorno con las claves del repositorio."""
    with pytest.raises(ValidationError) as failure:
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret=PLACEHOLDER_SECRETS["jwt_secret"],
            content_encryption_key=PLACEHOLDER_SECRETS["content_encryption_key"],
        )
    assert "valor de ejemplo" in str(failure.value)


def test_short_secrets_are_rejected_outside_development() -> None:
    with pytest.raises(ValidationError) as failure:
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="corto",
            content_encryption_key="corto",
        )
    assert "32 caracteres" in str(failure.value)


def test_production_starts_with_proper_secrets() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret=VALID_SECRET,
        content_encryption_key=VALID_SECRET,
    )
    assert settings.app_env == "production"


def test_development_still_accepts_the_repository_defaults() -> None:
    """El arranque local no debe requerir configuración previa."""
    settings = Settings(
        _env_file=None,
        app_env="development",
        jwt_secret=PLACEHOLDER_SECRETS["jwt_secret"],
        content_encryption_key=PLACEHOLDER_SECRETS["content_encryption_key"],
    )
    assert settings.app_env == "development"


@requires_database
def test_registering_an_existing_contact_does_not_reveal_it(client) -> None:
    """El registro repetido responde igual que uno nuevo, sin crear nada."""
    from sqlalchemy import func, select

    from app.database import SessionLocal
    from app.models.identity import UserContact

    contact = f"repetida-{uuid.uuid4().hex[:16]}@ejemplo.test"
    payload = {
        "contact_type": "EMAIL",
        "value": contact,
        "password": "clave-de-prueba-2026",
        "accept_account_terms": True,
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == first.status_code, "un 409 permitiría enumerar cuentas"
    assert second.json()["message"] == first.json()["message"]
    assert set(second.json()) == set(first.json())
    assert second.json()["user_id"] != first.json()["user_id"], "no se revela el id real"

    with SessionLocal() as db:
        stored = db.scalar(
            select(func.count())
            .select_from(UserContact)
            .where(UserContact.value_normalized == contact)
        )
    assert stored == 1, "el segundo registro no debe crear una cuenta"


@requires_database
def test_repeated_registration_cannot_hijack_the_original_password(client) -> None:
    """Reintentar el registro con otra contraseña no cambia la existente."""
    contact = f"intruso-{uuid.uuid4().hex[:16]}@ejemplo.test"
    original = "clave-original-2026"
    client.post(
        "/auth/register",
        json={
            "contact_type": "EMAIL",
            "value": contact,
            "password": original,
            "accept_account_terms": True,
        },
    )
    client.post(
        "/auth/register",
        json={
            "contact_type": "EMAIL",
            "value": contact,
            "password": "clave-del-atacante-2026",
            "accept_account_terms": True,
        },
    )
    attacker = client.post(
        "/auth/login", json={"contact": contact, "password": "clave-del-atacante-2026"}
    )
    assert attacker.status_code == 401


@requires_database
def test_login_is_rate_limited(client, account) -> None:
    """Tras varios fallos consecutivos la cuenta queda temporalmente bloqueada."""
    wrong = {"contact": account.contact, "password": "una-contrasena-incorrecta"}
    for _ in range(5):
        assert client.post("/auth/login", json=wrong).status_code == 401

    blocked = client.post("/auth/login", json=wrong)
    assert blocked.status_code == 429
    assert "Demasiados intentos" in blocked.json()["detail"]

    # El bloqueo también protege frente a la contraseña correcta.
    correct = client.post(
        "/auth/login", json={"contact": account.contact, "password": account.password}
    )
    assert correct.status_code == 429


@requires_database
def test_a_successful_login_clears_the_counter(client, account) -> None:
    wrong = {"contact": account.contact, "password": "una-contrasena-incorrecta"}
    for _ in range(3):
        assert client.post("/auth/login", json=wrong).status_code == 401

    good = client.post(
        "/auth/login", json={"contact": account.contact, "password": account.password}
    )
    assert good.status_code == 200

    for _ in range(3):
        assert client.post("/auth/login", json=wrong).status_code == 401


@requires_database
def test_verification_is_rate_limited(client) -> None:
    for _ in range(10):
        response = client.post("/auth/verify-contact", json={"token": "x" * 40})
        assert response.status_code == 400

    assert client.post("/auth/verify-contact", json={"token": "x" * 40}).status_code == 429


@requires_database
def test_login_does_not_distinguish_unknown_from_wrong_password(client, account) -> None:
    unknown = client.post(
        "/auth/login",
        json={"contact": f"nadie-{uuid.uuid4().hex[:12]}@ejemplo.test", "password": "clave-cualquiera-2026"},
    )
    wrong = client.post(
        "/auth/login", json={"contact": account.contact, "password": "clave-incorrecta-2026"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()
