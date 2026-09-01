"""Reglas de capas verificadas sobre el árbol de sintaxis.

Impide que el refactor se deshaga poco a poco: si un router vuelve a consultar
SQLAlchemy o un servicio importa FastAPI, esta batería falla.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"

ROUTERS = sorted((APP / "routers").glob("*.py"))
SERVICES = sorted((APP / "services").glob("*.py"))

STDLIB_ONLY_MODULES = [APP / "domain_rules.py", APP / "core" / "clock.py", APP / "core" / "exceptions.py"]

TRANSACTION_METHODS = {"commit", "flush", "refresh"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


#: Nombres que denotan una sesión de SQLAlchemy. Se comprueba el receptor de la
#: llamada, no solo el nombre del método: `auth_service.refresh(...)` es un caso
#: de uso, mientras que `db.refresh(...)` es manejo de transacción.
SESSION_NAMES = {"db", "session", "sess"}


def _session_transaction_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in TRANSACTION_METHODS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in SESSION_NAMES
    }


def test_router_modules_exist() -> None:
    assert len(ROUTERS) >= 9, "se esperan 8 routers y su __init__"


@pytest.mark.parametrize("path", ROUTERS, ids=lambda p: p.name)
def test_routers_do_not_reach_the_database(path: Path) -> None:
    """Un router no importa SQLAlchemy ni modelos persistentes."""
    for module in _imports(path):
        assert not module.startswith("sqlalchemy"), f"{path.name} importa {module}"
        assert not module.startswith("app.models"), f"{path.name} importa {module}"


@pytest.mark.parametrize("path", ROUTERS, ids=lambda p: p.name)
def test_routers_do_not_manage_transactions(path: Path) -> None:
    """La transacción pertenece al servicio, nunca al router."""
    offending = _session_transaction_calls(path)
    assert not offending, f"{path.name} ejecuta {sorted(offending)} sobre la sesión"


@pytest.mark.parametrize("path", SERVICES, ids=lambda p: p.name)
def test_services_do_not_import_fastapi(path: Path) -> None:
    """Un servicio señala errores con `app.core.exceptions`, no con HTTP."""
    for module in _imports(path):
        assert not module.startswith("fastapi"), f"{path.name} importa {module}"
        assert not module.startswith("starlette"), f"{path.name} importa {module}"


@pytest.mark.parametrize("path", STDLIB_ONLY_MODULES, ids=lambda p: p.name)
def test_pure_modules_only_use_the_standard_library(path: Path) -> None:
    """Las reglas de dominio y el núcleo no dependen del framework ni del ORM."""
    for module in _imports(path):
        assert not module.startswith(("fastapi", "sqlalchemy", "pydantic", "app.")), (
            f"{path.name} importa {module}"
        )


def test_main_is_only_composition() -> None:
    """`main.py` crea la aplicación y registra routers; no define endpoints."""
    main = APP / "main.py"
    source = main.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 80, "main.py debe quedar por debajo de 80 líneas"
    assert "create_app" in source
    for decorator in ("@app.get", "@app.post", "@app.put", "@app.delete", "@app.patch"):
        assert decorator not in source, f"main.py todavía define un endpoint ({decorator})"
    for module in _imports(main):
        assert not module.startswith("sqlalchemy"), f"main.py importa {module}"
        assert not module.startswith("app.models"), f"main.py importa {module}"


def test_services_do_not_import_each_others_routers() -> None:
    """La dependencia va de router a servicio, nunca al revés."""
    for path in SERVICES:
        for module in _imports(path):
            assert not module.startswith("app.routers"), f"{path.name} importa {module}"
