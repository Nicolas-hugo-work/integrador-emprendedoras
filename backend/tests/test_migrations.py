"""Convenciones de las migraciones.

`0001_initial_schema.py` ejecuta `Base.metadata.create_all()`: describe el
esquema por referencia a los modelos en lugar de declararlo. Ya está aplicada en
todas partes y reescribirla sería más riesgoso que útil, así que lo que se fija
aquí es que **de `0002` en adelante** las migraciones sean reales.

La detección de deriva entre modelos y migraciones la aporta `alembic check`,
que corre en CI. Funciona desde v0.4.0: antes fallaba al reflejar la columna
`VECTOR(768)`.
"""

import ast
from pathlib import Path

import pytest

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"

#: Única revisión a la que se le permite `create_all`, por ser la línea base.
BASELINE = "0001_initial_schema"


def _revisions() -> list[Path]:
    return sorted(path for path in VERSIONS.glob("*.py") if not path.name.startswith("_"))


def _assign(tree: ast.Module, name: str) -> str | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            if isinstance(node.value, ast.Constant):
                return node.value.value
    return None


def test_there_is_at_least_one_revision_after_the_baseline() -> None:
    assert len(_revisions()) >= 2, "v0.4.0 añade la primera migración real"


@pytest.mark.parametrize("path", _revisions(), ids=lambda p: p.stem)
def test_only_the_baseline_may_use_create_all(path: Path) -> None:
    """Una migración nueva debe declarar sus cambios, no delegarlos al modelo."""
    source = path.read_text(encoding="utf-8")
    if path.stem == BASELINE:
        return
    assert "create_all" not in source, (
        f"{path.name} usa create_all: describa los cambios explícitamente "
        "(op.create_table, op.add_column, op.execute...)"
    )


@pytest.mark.parametrize("path", _revisions(), ids=lambda p: p.stem)
def test_every_revision_declares_an_identity(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert _assign(tree, "revision") == path.stem, "revision debe coincidir con el archivo"
    if path.stem != BASELINE:
        assert _assign(tree, "down_revision"), "toda revisión salvo la base tiene predecesora"


@pytest.mark.parametrize("path", _revisions(), ids=lambda p: p.stem)
def test_every_revision_is_reversible(path: Path) -> None:
    """Un `downgrade` vacío convierte el ciclo de migración en un viaje de ida."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    downgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
        ),
        None,
    )
    assert downgrade is not None, f"{path.name} no define downgrade()"
    cuerpo = [node for node in downgrade.body if not isinstance(node, ast.Expr | ast.Pass)]
    tiene_llamadas = any(
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) for node in downgrade.body
    )
    assert cuerpo or tiene_llamadas, f"{path.name} tiene un downgrade vacío"


def test_the_chain_is_linear() -> None:
    """Sin ramas: cada revisión apunta a una distinta, y solo una es la base."""
    predecesoras = {}
    for path in _revisions():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        predecesoras[path.stem] = _assign(tree, "down_revision")

    bases = [nombre for nombre, previa in predecesoras.items() if previa is None]
    assert bases == [BASELINE], f"debe haber exactamente una base, hay {bases}"

    apuntadas = [previa for previa in predecesoras.values() if previa]
    assert len(apuntadas) == len(set(apuntadas)), "dos revisiones comparten predecesora"
    for previa in apuntadas:
        assert previa in predecesoras, f"down_revision inexistente: {previa}"
