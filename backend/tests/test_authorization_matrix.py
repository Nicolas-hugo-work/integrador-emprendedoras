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

    `body` solo hace falta en las rutas con permiso: la validación del cuerpo
    ocurre antes de que el servicio llame a `assert_permission`, así que sin un
    cuerpo válido la respuesta sería 422 en lugar de 403.
    """

    def __init__(self, access: str, body: dict | None = None) -> None:
        self.access = access
        self.body = body

    @property
    def is_public(self) -> bool:
        return self.access == PUBLIC

    @property
    def permission(self) -> str | None:
        return None if self.access in (PUBLIC, AUTHENTICATED) else self.access


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
    ("/businesses", "get"): Route(AUTHENTICATED),
    ("/businesses", "post"): Route(AUTHENTICATED),
    ("/businesses/{business_id}", "patch"): Route(AUTHENTICATED),
    ("/businesses/{business_id}", "delete"): Route(AUTHENTICATED),
    ("/finance/categories", "get"): Route(AUTHENTICATED),
    ("/finance/movements", "get"): Route(AUTHENTICATED),
    ("/finance/movements", "post"): Route(AUTHENTICATED),
    ("/finance/movements/{movement_id}", "patch"): Route(AUTHENTICATED),
    ("/finance/movements/{movement_id}", "delete"): Route(AUTHENTICATED),
    ("/finance/costs", "get"): Route(AUTHENTICATED),
    ("/finance/costs", "post"): Route(AUTHENTICATED),
    ("/finance/costs/{cost_id}", "patch"): Route(AUTHENTICATED),
    ("/finance/costs/{cost_id}", "delete"): Route(AUTHENTICATED),
    ("/finance/pricing", "post"): Route(AUTHENTICATED),
    ("/finance/summary", "get"): Route(AUTHENTICATED),
    ("/conversations", "get"): Route(AUTHENTICATED),
    ("/conversations", "post"): Route(AUTHENTICATED),
    ("/assistant/query", "post"): Route(AUTHENTICATED),
    ("/feedback", "post"): Route(AUTHENTICATED),
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
    response = client.request(method.upper(), _concrete(path), json=route.body or {})
    assert response.status_code == 401, f"{method.upper()} {path} respondió {response.status_code}"


@requires_database
@pytest.mark.parametrize(
    ("path", "method"),
    sorted(key for key, route in INVENTORY.items() if route.permission),
    ids=lambda value: str(value),
)
def test_permission_routes_reject_users_without_it(client, account, path, method) -> None:
    """Una emprendedora sin el permiso recibe 403, no 404 ni 422."""
    route = INVENTORY[(path, method)]
    assert route.permission not in (
        "profile.manage_own",
        "finance.read_own",
        "finance.write_own",
        "conversation.manage_own",
    ), "el permiso elegido no debe ser uno que la emprendedora ya tiene"

    response = client.request(
        method.upper(), _concrete(path), headers=account.headers, json=route.body or {}
    )
    assert response.status_code == 403, (
        f"{method.upper()} {path} respondió {response.status_code}, se esperaba 403"
    )
    assert response.json() == {"detail": "Permiso insuficiente"}


def test_every_declared_permission_exists_in_the_seeded_catalogue() -> None:
    """Evita clasificar una ruta con un permiso que la migración no siembra."""
    seeded = {
        "profile.manage_own", "finance.read_own", "finance.write_own",
        "conversation.manage_own", "source.review", "source.publish",
        "audit.read", "account.suspend", "research.read_anonymized", "jobs.execute",
    }
    declared = {route.permission for route in INVENTORY.values() if route.permission}
    assert declared <= seeded, f"permisos inexistentes: {sorted(declared - seeded)}"
