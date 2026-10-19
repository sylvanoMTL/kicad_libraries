"""Hard post-write checks of an install, read back from disk (D-18).

Directory comparisons use exact-case os.listdir results, never an existence probe: Windows
ignores letter case there, so an exists() call would pass a link that is wrong on Linux.
Every check re-reads its files; nothing is taken from the bytes the plan carries.
"""

import os
from pathlib import Path

from ..kicad_files import (
    LoadedFile,
    footprint_name,
    find_models,
    find_property,
    find_symbols,
    load,
)
from ..models import Issue, Severity
from .plan import MODEL_DIR_VAR, InstallPlan


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _listing(folder) -> set[str]:
    try:
        return set(os.listdir(folder))
    except OSError:
        return set()


def _listed_file(base: Path, relative: str) -> bool:
    """True when every segment of the posix path relative is in an exact-case listing below base."""
    folder = base
    parts = [p for p in relative.split("/") if p]
    if not parts:
        return False
    for part in parts:
        if part not in _listing(folder):
            return False
        folder = folder / part
    return True


def _linked_footprint(plan: InstallPlan, library: LoadedFile) -> tuple[LoadedFile | None, list[Issue]]:
    """Resolve the symbol's Footprint field to a footprint file on disk."""
    symbol = next(s for s in find_symbols(library.root) if s.name == plan.symbol_name)
    prop = find_property(symbol.node, "Footprint")
    value = prop.value if prop is not None else ""
    expected = f"{plan.library}:{plan.linked_footprint}"
    if value != expected:
        return None, [_err("verify.link_unresolved", f"The Footprint field of {plan.symbol_name} is {value!r}, expected {expected!r}")]
    lib, _, name = value.partition(":")
    pretty = f"{lib}.pretty"
    if pretty not in _listing(plan.layout.footprints_dir):
        return None, [_err("verify.link_unresolved", f"{value} points to {pretty}, which is not in Custom/Footprints")]
    pretty_dir = plan.layout.footprints_dir / pretty
    if f"{name}.kicad_mod" not in _listing(pretty_dir):
        return None, [_err("verify.link_unresolved", f"{value} points to {name}.kicad_mod, which is not in {pretty}")]
    loaded = load(pretty_dir / f"{name}.kicad_mod")
    if isinstance(loaded, Issue):
        return None, [_err("verify.parse_failed", loaded.text)]
    ref = footprint_name(loaded.root)
    if ref is None or ref.name != name:
        found = ref.name if ref is not None else None
        return None, [_err("verify.link_unresolved", f"{name}.kicad_mod holds a footprint named {found!r}, not {name!r}")]
    return loaded, []


def _model_issues(plan: InstallPlan, footprint: LoadedFile) -> list[Issue]:
    ref = footprint_name(footprint.root)
    models = find_models(ref.node) if ref is not None else []
    expected = f"{MODEL_DIR_VAR}/{plan.model_file}"
    if not models or models[0].path != expected:
        found = models[0].path if models else None
        return [_err("verify.model_missing", f"The footprint links the model {found!r}, expected {expected!r}")]
    if not _listed_file(plan.layout.models_dir, plan.model_file):
        return [_err("verify.model_missing", f"{plan.model_file} is not in Custom/3DModels")]
    return []


def verify_install(plan: InstallPlan) -> list[Issue]:
    """Re-read what the install wrote and return an ERROR Issue for every broken promise."""
    issues: list[Issue] = []

    # Every written file must re-parse; the symbol library is always checked
    paths = [op.path for op in plan.ops if op.kind in ("symbol_lib", "footprint")]
    if plan.symbol_lib_path not in paths:
        paths.append(plan.symbol_lib_path)
    loaded: dict[Path, LoadedFile] = {}
    for path in paths:
        result = load(path)
        if isinstance(result, Issue):
            issues.append(_err("verify.parse_failed", result.text))
        else:
            loaded[path] = result

    library = loaded.get(plan.symbol_lib_path)
    if library is None:
        return _unique(issues)

    names = [s.name for s in find_symbols(library.root)]
    for name in plan.symbol_names:
        count = names.count(name)
        if count == 1:
            continue
        code = "verify.symbol_missing" if count == 0 else "verify.symbol_duplicated"
        issues.append(_err(code, f"{plan.symbol_lib_path.name} holds {count} symbols named {name}, expected 1"))

    # A symbol that is missing or duplicated has no single Footprint field to follow
    if plan.linked_footprint is not None and names.count(plan.symbol_name) == 1:
        footprint, problems = _linked_footprint(plan, library)
        issues.extend(problems)
        if plan.model_file is not None and footprint is not None:
            issues.extend(_model_issues(plan, footprint))
    return _unique(issues)


def _unique(issues: list[Issue]) -> list[Issue]:
    """Drop repeats: one broken file can be reported by both the re-parse and the link walk."""
    seen: set[tuple[str, str]] = set()
    found = []
    for issue in issues:
        key = (issue.code, issue.text)
        if key not in seen:
            seen.add(key)
            found.append(issue)
    return found
