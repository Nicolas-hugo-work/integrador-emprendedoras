"""Denegación por defecto: ninguna ruta queda sin clasificar.

En v0.1.0 se sembraron 10 permisos y solo 2 llegaron a verificarse. El resto
existía en la base sin que ningún código los exigiera. Nada impedía agregar un
endpoint sensible y olvidar `assert_permission`.

Este inventario cierra ese hueco: cada operación expuesta debe declararse como
pública, autenticada o exigente de un permiso, y las pruebas comprueban que la
API se comporta como dice el inventario. Una ruta nueva sin clasificar hace
fallar la batería.
"""

import uuid

import pytest
from conftest import requires_database

PUBLIC = "público"
AUTHENTICATED = "autenticado"

#: Identificador con forma válida que no existe: sirve para rellenar rutas con
#: parámetros. La autorización se resuelve antes de buscar el recurso, así que
#: un id inexistente no altera el código de respuesta esperado.
ANY_ID = str(uuid.uuid4())


class Route:
    """Una operación expuesta, con su exigencia de acceso.

    `body` y `params` solo hacen falta en las rutas con permiso: FastAPI valida
    cuerpo y parámetros antes de que el servicio llame a `assert_permission`,
    así que sin datos válidos la respuesta sería 422 en lugar de 403.
    """

    def __init__(
        self, access: str, body: dict | None = None, params: dict | None = None
    ) -> None:
        self.access = access
        self.body = body
        self.params = params

    @property
    def is_public(self) -> bool:
        return self.access == PUBLIC

    @property
    def permission(self) -> str | None:
        return None if self.access in (PUBLIC, AUTHENTICATED) else self.access


_BUSINESS_BODY = {"name": "Prueba", "stage": "IDEA", "activity": "Servicios"}
_MOVEMENT_BODY = {
    "category_id": ANY_ID,
    "movement_type": "INCOME",
    "scope": "HOUSEHOLD",
    "amount": "10.00",
    "currency": "BOB",
    "occurred_on": "2026-08-31",
}
_COST_BODY = {
    "business_id": ANY_ID,
    "name": "Insumo",
    "cost_type": "VARIABLE",
    "amount": "10.00",
    "currency": "BOB",
    "unit": "kg",
    "periodicity": "MENSUAL",
    "quantity_base": "1",
}
_PRICING_BODY = {
    "business_id": ANY_ID,
    "product_name": "Producto",
    "units": "10",
    "margin_percent": "20",
    "cost_item_ids": [ANY_ID],
    "currency": "BOB",
}
_FEEDBACK_BODY = {"message_id": ANY_ID, "feedback_type": "USEFUL"}
_QUERY_BODY = {"message": "consulta de prueba"}
#: Un PATCH parcial admite cuerpo vacío: todos sus campos son opcionales.
_EMPTY: dict = {}

_SOURCE_BODY = {
    "publisher_id": ANY_ID,
    "title": "Guía de prueba",
    "canonical_url": "https://ejemplo.test/guia",
    "topic": "formalización",
}
_VERSION_BODY = {
    "source_id": ANY_ID,
    "version_label": "2026-01",
    "content_hash": "a" * 64,
    "storage_key": "sources/x.pdf",
}
_CHUNK_BODY = {
    "source_version_id": ANY_ID,
    "chunk_number": 1,
    "content": "contenido suficientemente largo para pasar",
    "token_count": 10,
}

INVENTORY: dict[tuple[str, str], Route] = {
    ("/health", "get"): Route(PUBLIC),
    ("/auth/register", "post"): Route(PUBLIC),
    ("/auth/verify-contact", "post"): Route(PUBLIC),
    ("/auth/login", "post"): Route(PUBLIC),
    ("/auth/refresh", "post"): Route(PUBLIC),
    ("/auth/logout", "post"): Route(AUTHENTICATED),
    ("/me", "get"): Route(AUTHENTICATED),
    ("/businesses", "get"): Route("business.manage_own"),
    ("/businesses", "post"): Route("business.manage_own", _BUSINESS_BODY),
    ("/businesses/{business_id}", "patch"): Route("business.manage_own", _EMPTY),
    ("/businesses/{business_id}", "delete"): Route("business.manage_own"),
    ("/finance/categories", "get"): Route("finance.read_own"),
    ("/finance/movements", "get"): Route("finance.read_own"),
    ("/finance/movements", "post"): Route("finance.write_own", _MOVEMENT_BODY),
    ("/finance/movements/{movement_id}", "patch"): Route("finance.write_own", _EMPTY),
    ("/finance/movements/{movement_id}", "delete"): Route("finance.write_own"),
    ("/finance/costs", "get"): Route("finance.read_own", params={"business_id": ANY_ID}),
    ("/finance/costs", "post"): Route("finance.write_own", _COST_BODY),
    ("/finance/costs/{cost_id}", "patch"): Route("finance.write_own", _EMPTY),
    ("/finance/costs/{cost_id}", "delete"): Route("finance.write_own"),
    ("/finance/pricing", "post"): Route("finance.write_own", _PRICING_BODY),
    ("/finance/summary", "get"): Route("finance.read_own", params={"business_id": ANY_ID}),
    ("/conversations", "get"): Route("conversation.manage_own"),
    ("/conversations", "post"): Route("conversation.manage_own", _EMPTY),
    ("/assistant/query", "post"): Route("conversation.manage_own", _QUERY_BODY),
    ("/feedback", "post"): Route("conversation.manage_own", _FEEDBACK_BODY),
    ("/consents", "get"): Route(AUTHENTICATED),
    ("/consents", "post"): Route(AUTHENTICATED),
    ("/privacy/deletion", "post"): Route(AUTHENTICATED),
    ("/privacy/export", "post"): Route(AUTHENTICATED),
    ("/source-publishers", "get"): Route("source.review"),
    ("/sources", "get"): Route("source.review"),
    ("/sources", "post"): Route("source.review", _SOURCE_BODY),
    ("/sources/{source_id}/versions", "get"): Route("source.review"),
    ("/source-versions/{version_id}/chunks", "get"): Route("source.review"),
    ("/source-versions", "post"): Route("source.review", _VERSION_BODY),
    ("/source-chunks", "post"): Route("source.review", _CHUNK_BODY),
    ("/source-versions/{version_id}/publish", "post"): Route("source.publish"),
    ("/source-versions/{version_id}/retire", "post"): Route(
        "source.publish", {"reason": "La norma fue derogada"}
    ),
}


def _exposed_operations() -> set[tuple[str, str]]:
    from app.main import app

    methods = {"get", "post", "put", "patch", "delete"}
    return {
        (path, method)
        for path, item in app.openapi()["paths"].items()
        for method in item
        if method in methods
    }


def _concrete(path: str) -> str:
    """Sustituye los parámetros de ruta por un identificador cualquiera."""
    while "{" in path:
        start, end = path.index("{"), path.index("}")
        path = path[:start] + ANY_ID + path[end + 1 :]
    return path


def test_inventory_covers_every_exposed_route() -> None:
    """Una ruta nueva sin clasificar hace fallar la batería a propósito."""
    exposed = _exposed_operations()
    declared = set(INVENTORY)
    assert not exposed - declared, (
        f"rutas sin clasificar en INVENTORY: {sorted(exposed - declared)}"
    )
    assert not declared - exposed, (
        f"rutas declaradas que ya no existen: {sorted(declared - exposed)}"
    )


@requires_database
@pytest.mark.parametrize(
    ("path", "method"),
    sorted(key for key, route in INVENTORY.items() if not route.is_public),
    ids=lambda value: str(value),
)
def test_protected_routes_reject_anonymous_requests(client, path, method) -> None:
    """Toda ruta no pública responde 401 sin token."""
    route = INVENTORY[(path, method)]
    response = client.request(
        method.upper(), _concrete(path), json=route.body or {}, params=route.params
    )
    assert response.status_code == 401, f"{method.upper()} {path} respondió {response.status_code}"


@requires_database
@pytest.mark.parametrize(
    ("path", "method"),
    sorted(key for key, route in INVENTORY.items() if route.permission),
    ids=lambda value: str(value),
)
def test_permission_routes_reject_users_without_it(
    client, account, curator, path, method
) -> None:
    """Quien no tiene el permiso recibe 403, no 404 ni 422.

    Se elige a propósito la cuenta que **carece** del permiso: la curadora para
    las rutas de emprendedora y la emprendedora para las de curaduría. Así la
    separación queda probada en las dos direcciones.
    """
    route = INVENTORY[(path, method)]
    de_curaduria = route.permission in ("source.review", "source.publish")
    intruder = account if de_curaduria else curator

    response = client.request(
        method.upper(),
        _concrete(path),
        headers=intruder.headers,
        json=route.body or {},
        params=route.params,
    )
    assert response.status_code == 403, (
        f"{method.upper()} {path} respondió {response.status_code}, se esperaba 403"
    )
    assert response.json() == {"detail": "Permiso insuficiente"}


@requires_database
def test_staff_keeps_its_rights_over_its_own_account(client, curator) -> None:
    """Separar roles no puede quitarle a nadie el control de sus datos.

    `/me`, los consentimientos y la eliminación de cuenta quedan deliberadamente
    fuera del gateo por permiso: son derechos de toda cuenta, no funciones de un
    rol. Gatearlos dejaría a la curadora sin poder borrar su propia cuenta.
    """
    perfil = client.get("/me", headers=curator.headers)
    assert perfil.status_code == 200
    assert perfil.json()["roles"] == ["CURADORA_RAG"]
    assert perfil.json()["permissions"] == ["source.publish", "source.review"]

    assert client.get("/consents", headers=curator.headers).status_code == 200
    otorgado = client.post(
        "/consents",
        headers=curator.headers,
        json={"purpose_code": "AUDIO", "version": "1.0", "decision": "WITHDRAWN"},
    )
    assert otorgado.status_code == 201
    assert client.post("/privacy/export", headers=curator.headers).status_code == 202
    assert client.post(
        "/privacy/deletion",
        headers=curator.headers,
        json={"confirmation": "ELIMINAR MI CUENTA"},
    ).status_code == 202


@requires_database
def test_staff_cannot_reach_the_entrepreneur_application(client, curator) -> None:
    """La curadora no ve ni usa negocio, finanzas ni asistente."""
    assert client.get("/businesses", headers=curator.headers).status_code == 403
    assert client.get("/finance/movements", headers=curator.headers).status_code == 403
    assert client.get("/finance/categories", headers=curator.headers).status_code == 403
    assert client.get("/conversations", headers=curator.headers).status_code == 403
    assert client.post(
        "/assistant/query", headers=curator.headers, json={"message": "hola"}
    ).status_code == 403


@requires_database
def test_a_newly_registered_account_keeps_full_access(client, account) -> None:
    """Quien se registra sigue teniendo todo lo suyo tras el gateo."""
    assert client.get("/businesses", headers=account.headers).status_code == 200
    assert client.get("/finance/movements", headers=account.headers).status_code == 200
    assert client.get("/finance/categories", headers=account.headers).status_code == 200
    assert client.get("/conversations", headers=account.headers).status_code == 200
    creado = client.post(
        "/businesses",
        headers=account.headers,
        json={"name": "Sigue funcionando", "stage": "IDEA", "activity": "Servicios"},
    )
    assert creado.status_code == 201, "0002 concede business.manage_own a EMPRENDEDORA"


def test_every_declared_permission_exists_in_the_seeded_catalogue() -> None:
    """Evita clasificar una ruta con un permiso que la migración no siembra."""
    seeded = {
        "profile.manage_own", "finance.read_own", "finance.write_own",
        "conversation.manage_own", "source.review", "source.publish",
        "audit.read", "account.suspend", "research.read_anonymized", "jobs.execute",
        "business.manage_own",
    }
    declared = {route.permission for route in INVENTORY.values() if route.permission}
    assert declared <= seeded, f"permisos inexistentes: {sorted(declared - seeded)}"
