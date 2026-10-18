from importlib.metadata import version
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _requirement_lines(name: str) -> list[str]:
    lines = (REPO_ROOT / name).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def test_requirements_are_exact_pins():
    assert _requirement_lines("requirements.txt") == ["PySide6==6.12.0"]
    assert _requirement_lines("requirements-dev.txt") == [
        "-r requirements.txt",
        "pytest==9.1.1",
        "pytest-qt==4.5.0",
    ]
    for name in ("requirements.txt", "requirements-dev.txt"):
        for line in _requirement_lines(name):
            assert line.startswith("-r") or "==" in line


def test_installed_versions_match_pins():
    assert version("PySide6") == "6.12.0"
    assert version("pytest") == "9.1.1"
    assert version("pytest-qt") == "4.5.0"


def test_pyproject_is_pytest_config_only():
    # tomllib is 3.11+; the production floor is 3.10
    tomllib = pytest.importorskip("tomllib")
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert set(data) == {"tool"}
    assert set(data["tool"]) == {"pytest"}
    ini = data["tool"]["pytest"]["ini_options"]
    assert "." in ini["pythonpath"]
    assert ini["testpaths"] == ["tests"]
    assert ini["qt_api"] == "pyside6"
    assert "--strict-markers" in ini["addopts"]
    markers = ini["markers"]
    assert any(m.startswith("wurth:") for m in markers)
    assert any(m.startswith("local_kicad:") for m in markers)
