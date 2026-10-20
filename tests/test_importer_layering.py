"""Layering guard for every module under kicad_lib_manager/importer/ (D-07, D-14).

Importer modules are read with ``ast`` and imported only inside a subprocess, so this
file works in a checkout where the importer package is not present yet. The rules are
proven on synthetic trees in ``tmp_path`` (``test_guard_*``, never skipped); the checks
on the real package (``test_importer_*``) skip only while ``kicad_lib_manager/importer/``
is absent from the checkout.

Rules held for every importer module:
- it is registered in ALLOWED (so a new adapter is reviewed here before it can land);
- its relative imports resolve into its ALLOWED entry;
- it never imports PySide6, shiboken6 or kicad_lib_manager by absolute name;
- it never uses the zip bulk-extraction methods (D-07: members are read one at a time);
- a package ``__init__.py`` holds nothing but a docstring.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "kicad_lib_manager"
IMPORTER = PACKAGE / "importer"

# Allowed package-internal imports per importer module, keyed by dotted path relative to
# kicad_lib_manager. Phase 7 adapters are registered here when they are added.
ALLOWED: dict[str, set[str]] = {
    "importer": set(),
    "importer.adapters": set(),
    "importer.package": {"models", "fsutil"},
    # naming is registered now for the name_check properties plan 03-05 adds;
    # naming itself imports only models, so there is no cycle
    "importer.candidate": {"models", "importer.package", "importer.naming"},
    "importer.naming": {"models"},
    "importer.layout": {"models", "importer.candidate"},
    "importer.suggest": {"models", "importer.candidate", "importer.naming"},
    "importer.adapters.base": {
        "models",
        "fsutil",
        "kicad_files",
        "sexpr",
        "importer.package",
        "importer.candidate",
    },
    "importer.adapters.ultralibrarian": {
        "models",
        "importer.package",
        "importer.adapters.base",
    },
    "importer.adapters.loose": {
        "models",
        "importer.package",
        "importer.adapters.base",
    },
    "importer.detect": {
        "models",
        "importer.package",
        "importer.candidate",
        "importer.adapters.base",
        "importer.adapters.ultralibrarian",
        "importer.adapters.loose",
    },
    # Phase 4 install modules. importer.kicad_cli is a forward registration (plan 04-03 creates it);
    # layering_errors only checks modules found on disk, so an unused key raises no error
    "importer.plan": {"models", "importer.package", "importer.layout"},
    "importer.kicad_cli": {"models", "kicad_files"},
    "importer.verify": {"models", "fsutil", "kicad_files", "sexpr", "importer.plan", "importer.layout"},
    "importer.planner": {
        "models",
        "fsutil",
        "kicad_files",
        "sexpr",
        "importer.plan",
        "importer.candidate",
        "importer.package",
        "importer.naming",
        "importer.layout",
        "importer.suggest",
        "importer.adapters.base",
        "importer.kicad_cli",
        "importer.verify",
    },
    "importer.applier": {
        "models",
        "fsutil",
        "kicad_files",
        "importer.plan",
        "importer.kicad_cli",
        "importer.verify",
        "importer.layout",
    },
}

CORE_MODULES = (
    "importer.package",
    "importer.candidate",
    "importer.detect",
    "importer.suggest",
    "importer.adapters.base",
    "importer.adapters.ultralibrarian",
    "importer.plan",
    "importer.planner",
    "importer.applier",
    "importer.verify",
    "importer.kicad_cli",
)

FORBIDDEN_TOP = ("PySide6", "shiboken6", "kicad_lib_manager")
BULK_EXTRACT_ATTRS = ("extractall", "extract")

requires_importer = pytest.mark.skipif(
    not IMPORTER.is_dir(),
    reason=(
        "kicad_lib_manager/importer not present yet: plan 03-01 builds it in the same wave; "
        "the wave-1 post-merge test run checks it"
    ),
)


# -- pure helpers --------------------------------------------------------------


def module_key(path: Path, package_root: Path) -> str:
    """Return the dotted key of a file below package_root; an __init__ keeps its package key."""
    parts = list(path.relative_to(package_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def discover(package_root: Path) -> dict[str, Path]:
    """Map the key of every .py file under package_root/importer to its path."""
    folder = package_root / "importer"
    if not folder.is_dir():
        return {}
    return {module_key(p, package_root): p for p in sorted(folder.rglob("*.py"))}


def resolve_relative(key: str, is_package: bool, level: int, module: str | None) -> str:
    """Return the dotted target of a relative import made from the module with this key."""
    parts = key.split(".")
    containing = parts if is_package else parts[:-1]
    up = level - 1
    if up > len(containing):
        # Climbs out of kicad_lib_manager: never a member of any ALLOWED entry
        return ".." + (module or "")
    base = containing[: len(containing) - up]
    if module:
        base = base + module.split(".")
    return ".".join(base)


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def layering_errors(
    package_root: Path, allowed: dict[str, set[str]] = ALLOWED
) -> list[str]:
    """Return one readable message per layering violation, each starting with the module key."""
    errors: list[str] = []
    for key, path in discover(package_root).items():
        is_package = path.name == "__init__.py"
        registered = key in allowed
        if not registered:
            errors.append(
                f"{key}: not registered in ALLOWED (add it to tests/test_importer_layering.py)"
            )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if is_package and any(not _is_docstring(n) for n in tree.body):
            errors.append(f"{key}: package __init__.py must hold no code, only a docstring")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    if not registered:
                        continue
                    if node.module:
                        targets = [resolve_relative(key, is_package, node.level, node.module)]
                    else:
                        targets = [
                            resolve_relative(key, is_package, node.level, alias.name)
                            for alias in node.names
                        ]
                    for target in targets:
                        if target not in allowed[key]:
                            errors.append(f"{key}: imports {target}, which its ALLOWED entry forbids")
                elif node.module and node.module.split(".")[0] in FORBIDDEN_TOP:
                    errors.append(f"{key}: absolute import of {node.module} is forbidden")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_TOP:
                        errors.append(f"{key}: absolute import of {alias.name} is forbidden")
            elif isinstance(node, ast.Attribute) and node.attr in BULK_EXTRACT_ATTRS:
                errors.append(
                    f"{key}: uses .{node.attr} (D-07: read members one at a time, never extract)"
                )
    return errors


# -- synthetic self-tests (never skipped) --------------------------------------


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _clean_files() -> dict[str, str]:
    return {
        "importer/__init__.py": '"""Importer package."""\n',
        "importer/adapters/__init__.py": "",
        "importer/package.py": "from ..models import Issue\n",
        "importer/naming.py": "from ..models import Issue\n",
        "importer/candidate.py": (
            "from .package import PackageFile\nfrom .naming import NameResult\n"
        ),
        "importer/adapters/base.py": (
            "from ...models import Issue\n"
            "from .. import package\n"
            "from ..candidate import PartMeta\n"
        ),
    }


def test_guard_clean_tree(tmp_path):
    root = tmp_path / "pkg"
    _write_tree(root, _clean_files())
    assert layering_errors(root) == []


VIOLATIONS = [
    pytest.param("importer/package.py", "\nimport PySide6.QtCore\n", "importer.package", id="qt-import"),
    pytest.param(
        "importer/naming.py",
        "\nfrom kicad_lib_manager.models import Issue\n",
        "importer.naming",
        id="absolute-package-import",
    ),
    pytest.param(
        "importer/naming.py",
        "\nfrom ..main_window import MainWindow\n",
        "importer.naming",
        id="upward-import",
    ),
    pytest.param(
        "importer/adapters/base.py",
        "\nfrom . import ultralibrarian\n",
        "importer.adapters.base",
        id="sibling-not-allowed",
    ),
    pytest.param("importer/extra.py", "", "importer.extra", id="unregistered"),
    pytest.param(
        "importer/package.py",
        "\ndef unpack(zf):\n    zf.extractall('somewhere')\n",
        "importer.package",
        id="bulk-extractall",
    ),
    pytest.param(
        "importer/package.py",
        "\ndef unpack(zf):\n    zf.extract('member', 'somewhere')\n",
        "importer.package",
        id="bulk-extract",
    ),
    pytest.param("importer/__init__.py", "\nX = 1\n", "importer", id="init-holds-code"),
]


@pytest.mark.parametrize(("rel", "addition", "key"), VIOLATIONS)
def test_guard_flags_violation(tmp_path, rel, addition, key):
    root = tmp_path / "pkg"
    files = _clean_files()
    files[rel] = files.get(rel, "") + addition
    _write_tree(root, files)
    errors = layering_errors(root)
    assert len(errors) == 1, errors
    assert errors[0].startswith(key), errors


def test_guard_resolves_relative_imports():
    assert resolve_relative("importer.adapters.base", False, 3, "models") == "models"
    assert resolve_relative("importer.adapters.base", False, 2, "package") == "importer.package"
    assert (
        resolve_relative("importer.adapters.base", False, 1, "ultralibrarian")
        == "importer.adapters.ultralibrarian"
    )
    assert resolve_relative("importer.adapters", True, 1, "base") == "importer.adapters.base"
    assert resolve_relative("importer.candidate", False, 1, "naming") == "importer.naming"
    # Climbing out of kicad_lib_manager never lands in an ALLOWED entry
    assert resolve_relative("importer.package", False, 4, "models").startswith("..")


def test_guard_module_key_and_discover(tmp_path):
    root = tmp_path / "pkg"
    _write_tree(root, _clean_files())
    found = discover(root)
    assert sorted(found) == [
        "importer",
        "importer.adapters",
        "importer.adapters.base",
        "importer.candidate",
        "importer.naming",
        "importer.package",
    ]
    assert module_key(root / "importer" / "adapters" / "__init__.py", root) == "importer.adapters"
    assert discover(tmp_path / "missing") == {}


# -- real-module checks (skip only while the importer package is absent) ------

_CODE = """
import importlib, sys
sys.path.insert(0, sys.argv[1])
for name in sys.argv[2:]:
    importlib.import_module("kicad_lib_manager." + name)
for name in sorted(sys.modules):
    top = name.split(".")[0]
    if (
        top in ("PySide6", "shiboken6")
        or name in ("kicad_lib_manager.main_window", "kicad_lib_manager.settings")
        or name.startswith("kicad_lib_manager.widgets")
    ):
        print(name)
"""


@requires_importer
def test_importer_core_modules_exist():
    found = discover(PACKAGE)
    missing = [key for key in CORE_MODULES if key not in found]
    assert missing == []


@requires_importer
def test_importer_modules_follow_layering():
    errors = layering_errors(PACKAGE)
    assert errors == [], "\n".join(errors)


@requires_importer
def test_importer_modules_load_no_qt():
    modules = sorted(discover(PACKAGE))
    result = subprocess.run(
        [sys.executable, "-I", "-c", _CODE, str(REPO_ROOT), *modules],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
