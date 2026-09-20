"""Los cinco lugares de versión tienen que decir lo mismo.

`VERSION` se quedó en 0.6.0 mientras el resto ya era 0.7.0. Esta prueba
habría fallado entonces.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_published_versions_match() -> None:
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (REPO / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    main = (REPO / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    package = json.loads((REPO / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPO / "frontend" / "package-lock.json").read_text(encoding="utf-8"))

    found_pyproject = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    found_main = re.search(r'version="([^"]+)"', main)
    assert found_pyproject is not None, "falta version en pyproject.toml"
    assert found_main is not None, "falta version en app/main.py"
    assert found_pyproject.group(1) == version
    assert found_main.group(1) == version
    assert package["version"] == version
    assert lock["version"] == version
    assert lock["packages"][""]["version"] == version
