"""Hard post-write checks of an install, read back from disk (D-18).

Directory comparisons use exact-case os.listdir results, never an existence probe: Windows
ignores letter case there, so an exists() call would pass a link that is wrong on Linux.
"""

import os

from ..kicad_files import (
    LoadedFile,
    footprint_name,
    find_models,
    find_property,
    find_symbol,
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


def _linked_footprint(plan: InstallPlan, library: LoadedFile) -> tuple[LoadedFile | None, list[Issue]]:
    """Resolve the symbol's Footprint field to a footprint file on disk."""
    symbol = find_symbol(library.root, plan.symbol_name)
    if symbol is None:
        return None, []
    prop = find_property(symbol.node, "Footprint")
    value = prop.value if prop is not None else ""
    lib, sep, name = value.partition(":")
    if not sep or not lib or not name:
        return None, [_err("verify.link_unresolved", f"The Footprint field of {plan.symbol_name} is {value!r}, not <Library>:<Footprint>")]
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


def verify_install(plan: InstallPlan) -> list[Issue]:
    """Re-read what the install wrote and return an ERROR Issue for every broken promise."""
    issues: list[Issue] = []
    library = load(plan.symbol_lib_path)
    if isinstance(library, Issue):
        return [_err("verify.parse_failed", library.text)]
    for op in plan.ops:
        if op.kind == "footprint":
            written = load(op.path)
            if isinstance(written, Issue):
                issues.append(_err("verify.parse_failed", written.text))
    names = [s.name for s in find_symbols(library.root)]
    for name in plan.symbol_names:
        if names.count(name) != 1:
            issues.append(_err("verify.symbol_missing", f"{plan.symbol_lib_path.name} holds {names.count(name)} symbols named {name}, expected 1"))
    if issues:
        return issues
    footprint, problems = _linked_footprint(plan, library)
    issues.extend(problems)
    if plan.model_file is not None and footprint is not None:
        ref = footprint_name(footprint.root)
        models = find_models(ref.node) if ref is not None else []
        expected = f"{MODEL_DIR_VAR}/{plan.model_file}"
        if not models or models[0].path != expected:
            found = models[0].path if models else None
            issues.append(_err("verify.model_missing", f"The footprint links the model {found!r}, expected {expected!r}"))
        elif plan.model_file not in _listing(plan.layout.models_dir):
            issues.append(_err("verify.model_missing", f"{plan.model_file} is not in Custom/3DModels"))
    return issues
