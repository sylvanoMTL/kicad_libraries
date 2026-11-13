"""Import, annotation and Python 3.10 grammar gate over every module of the package (gap G-13-1-a).

Python 3.14 defers annotation evaluation (PEP 649/749), so on the project's only test interpreter
a parameter annotation naming an unbound class never runs at import. Python 3.10-3.13 evaluate it
when the class body runs, and the whole app then fails to start with a NameError. This gate makes
the 3.14 suite read every annotation explicitly, which raises the same NameError on 3.14, and it
checks the grammar of every module against 3.10.

eval_str stays False on purpose: a module with `from __future__ import annotations` keeps its hints
as strings on every version, so a deliberate string hint is not this bug class.
"""

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import kicad_lib_manager

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "kicad_lib_manager"
LAUNCHER = REPO_ROOT / "kicad_lib_manager.py"
MIN_OBJECTS = 2000


def _module_names() -> list[str]:
    prefix = kicad_lib_manager.__name__ + "."
    names = [kicad_lib_manager.__name__]
    names += sorted(info.name for info in pkgutil.walk_packages(kicad_lib_manager.__path__, prefix=prefix))
    return names


def _import_all() -> tuple[list, list[str]]:
    """Import every module of the package, returning (modules, one failure line per broken module)."""
    modules = []
    failures = []
    for name in _module_names():
        try:
            modules.append(importlib.import_module(name))
        except Exception as exc:  # the message names every broken module at once
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    return modules, failures


def _members(owner) -> list:
    """The functions and classes held by one class body: plain, static/class methods, property accessors, nested classes."""
    found = []
    for value in vars(owner).values():
        if isinstance(value, (staticmethod, classmethod)):
            value = value.__func__
        if isinstance(value, property):
            found.extend(part for part in (value.fget, value.fset, value.fdel) if part is not None)
        elif inspect.isfunction(value) or inspect.isclass(value):
            found.append(value)
    return found


def _read_annotations(module, failures: list[str]) -> int:
    """Read the annotations of everything the module defines; append one line per NameError; return the count examined."""
    seen: set[int] = set()
    examined = 0
    pending = [obj for obj in vars(module).values() if inspect.isfunction(obj) or inspect.isclass(obj)]
    while pending:
        obj = pending.pop()
        if id(obj) in seen or getattr(obj, "__module__", None) != module.__name__:
            continue
        seen.add(id(obj))
        examined += 1
        try:
            inspect.get_annotations(obj)
        except NameError as exc:
            failures.append(f"{module.__name__}.{getattr(obj, '__qualname__', obj)}: {exc}")
        if inspect.isclass(obj):
            pending.extend(_members(obj))
    return examined


def test_every_module_imports():
    _, failures = _import_all()
    assert failures == [], "modules that fail to import:\n" + "\n".join(failures)


def test_every_annotation_resolves():
    modules, _ = _import_all()
    failures: list[str] = []
    examined = sum(_read_annotations(module, failures) for module in modules)
    assert failures == [], "annotations naming an unbound name (a NameError at import on Python 3.10-3.13):\n" + "\n".join(
        failures
    )
    assert examined >= MIN_OBJECTS, f"only {examined} annotated objects examined; the module walk is broken"


def test_every_module_parses_as_python_3_10():
    # Best effort: feature_version rejects newer grammar (except*, PEP 695, the type statement), not newer library APIs
    paths = sorted(PACKAGE_DIR.rglob("*.py")) + [LAUNCHER]
    failures = []
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT).as_posix()}: line {exc.lineno}: {exc.msg}")
    assert len(paths) > 50, "the module list is broken"
    assert failures == [], "modules that do not parse with the Python 3.10 grammar:\n" + "\n".join(failures)
