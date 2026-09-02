"""Infraestructura común de pruebas.

Las variables de entorno se fijan **antes** de importar `app`, porque
`app.config.get_settings()` está memorizado con `lru_cache` y `app.database`
crea el motor en tiempo de importación.

Las pruebas funcionales corren contra MariaDB real, no SQLite: el esquema usa
`VECTOR`, `FULLTEXT`, una vista y triggers que SQLite no reproduce.
"""

import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

#: Base de datos de las pruebas funcionales.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("JWT_SECRET", "clave-de-pruebas-con-mas-de-32-caracteres")
os.environ.setdefault("CONTENT_ENCRYPTION_KEY", "clave-de-cifrado-de-pruebas-32-chars")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

requires_database = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Requiere TEST_DATABASE_URL apuntando a una MariaDB de prueba aislada",
)


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Aplica las migraciones una vez por sesión sobre la base de prueba."""
    if not TEST_DATABASE_URL:
        pytest.skip("Requiere TEST_DATABASE_URL")
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    # `sys.executable -m alembic` en lugar de `alembic`: el ejecutable del
    # entorno virtual no siempre está en el PATH del proceso de pruebas.
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=BACKEND_DIR,
        env=env,
    )


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    """Evita que el límite de intentos de una prueba afecte a la siguiente."""
    from app.services.rate_limit import reset_all

    reset_all()
    yield
    reset_all()


@pytest.fixture
def client(migrated_database):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@dataclass
class Account:
    """Una usuaria registrada, verificada y autenticada."""

    user_id: str
    contact: str
    password: str
    access_token: str
    refresh_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def _register_account(client, *, password: str = "clave-de-prueba-2026") -> Account:
    contact = f"prueba-{uuid.uuid4().hex[:16]}@ejemplo.test"
    registration = client.post(
        "/auth/register",
        json={
            "contact_type": "EMAIL",
            "value": contact,
            "password": password,
            "accept_account_terms": True,
        },
    )
    assert registration.status_code == 201, registration.text
    token = registration.json()["verification_token"]
    assert token, "en APP_ENV=development el registro nuevo devuelve el código"
    verified = client.post("/auth/verify-contact", json={"token": token})
    assert verified.status_code == 200, verified.text
    logged_in = client.post("/auth/login", json={"contact": contact, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    tokens = logged_in.json()
    return Account(
        user_id=registration.json()["user_id"],
        contact=contact,
        password=password,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@pytest.fixture
def make_account(client):
    """Fábrica de usuarias independientes."""

    def factory(password: str = "clave-de-prueba-2026") -> Account:
        return _register_account(client, password=password)

    return factory


@pytest.fixture
def account(make_account) -> Account:
    return make_account()


@pytest.fixture
def curator(make_account) -> Account:
    """Usuaria con **solo** el rol CURADORA_RAG.

    El rol se reemplaza en vez de acumularse, igual que hace
    `scripts/seed_test_users.py`. Si conservara el `EMPRENDEDORA` que otorga el
    registro tendría todos los permisos y no serviría para probar que el staff
    no alcanza las pantallas de emprendedora.
    """
    from sqlalchemy import delete, select

    from app.database import SessionLocal
    from app.models.identity import Role, UserRole

    created = make_account()
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == "CURADORA_RAG"))
        assert role is not None, "la migración siembra el rol CURADORA_RAG"
        db.execute(delete(UserRole).where(UserRole.user_id == created.user_id))
        db.add(UserRole(user_id=created.user_id, role_id=role.id))
        db.commit()
    return created


@pytest.fixture
def business(client, account) -> str:
    """Un emprendimiento de `account`; devuelve su identificador."""
    response = client.post(
        "/businesses",
        headers=account.headers,
        json={"name": "Tejidos Esperanza", "stage": "OPERATING", "activity": "Artesanía"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


CATEGORY_INCOME = "01990000-0000-7000-8300-000000000001"
CATEGORY_COST = "01990000-0000-7000-8300-000000000003"
CATEGORY_EXPENSE = "01990000-0000-7000-8300-000000000004"
CATEGORY_TRANSFER = "01990000-0000-7000-8300-000000000005"
