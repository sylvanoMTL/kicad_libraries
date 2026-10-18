"""Mechanical layering checks: foundation modules are Qt-free and import only downward."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "kicad_lib_manager"

# Allowed package-internal imports per foundation module (T-01-20)
ALLOWED = {
    "models": set(),
    "sexpr": set(),
    "fsutil": {"models"},
    "kicad_files": {"sexpr", "fsutil", "models"},
}

_CODE = """
import sys
sys.path.insert(0, sys.argv[1])
import kicad_lib_manager.models, kicad_lib_manager.sexpr
import kicad_lib_manager.fsutil, kicad_lib_manager.kicad_files
for name in sorted(sys.modules):
    if name.split(".")[0] in ("PySide6", "shiboken6"):
        print(name)
"""


def test_foundation_modules_load_no_qt():
    result = subprocess.run(
        [sys.executable, "-I", "-c", _CODE, str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def _imports(module: str) -> tuple[set[str], set[str]]:
    """Return (relative package-internal module names, absolute top-level module names)."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    relative: set[str] = set()
    absolute: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                # `from .x import y` -> x ; `from . import x` -> x
                if node.module:
                    relative.add(node.module.split(".")[0])
                else:
                    relative.update(a.name for a in node.names)
            elif node.module:
                absolute.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            absolute.update(a.name.split(".")[0] for a in node.names)
    return relative, absolute


@pytest.mark.parametrize("module", sorted(ALLOWED))
def test_imports_point_only_downward(module):
    relative, absolute = _imports(module)
    assert relative <= ALLOWED[module], f"{module} imports upward: {relative - ALLOWED[module]}"
    assert "PySide6" not in absolute and "shiboken6" not in absolute
    assert "kicad_lib_manager" not in absolute


def test_package_init_holds_no_code():
    tree = ast.parse((PACKAGE / "__init__.py").read_text(encoding="utf-8"))
    # A module docstring is allowed; anything else is code
    body = [
        n for n in tree.body
        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str))
    ]
    assert body == []
