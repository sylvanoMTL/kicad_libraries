"""Hard post-write checks of an install, read back from disk (D-18).

Directory comparisons use exact-case os.listdir results, never an existence probe: Windows
ignores letter case there, so an exists() call would pass a link that is wrong on Linux.
Every check re-reads its files; nothing is taken from the bytes the plan carries.
"""

import os
import re
from collections.abc import Sequence
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
from ..sexpr import Node, quote, unquote
from .layout import RepoLayout
from .plan import MODEL_DIR_VAR, InstallPlan, ToolContext

_DIGITS = re.compile(r"(\d+)")
_WURTH_PREFIX = "WurthElektronik:"


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
        # Soft check: against the footprint the written Footprint field really resolves to (D-09)
        ref = footprint_name(footprint.root) if footprint is not None else None
        if ref is not None:
            issues.extend(
                pin_pad_issues(
                    plan.symbol_name,
                    f"{plan.library}:{plan.linked_footprint}",
                    symbol_pin_numbers(library.root, plan.symbol_name),
                    footprint_pad_numbers(ref.node),
                )
            )
    issues.extend(find_name_elsewhere(plan.symbol_names, plan.layout, exclude_library=plan.library, tools=plan.tools))
    return _unique(issues)


# -- pin/pad comparison (POST-04, D-20) -------------------------------------------


def _token_text(node: Node) -> str | None:
    """The unquoted text of a string or atom node, None for a list."""
    return unquote(node.text) if node.kind in ("str", "atom") else None


def _extends_parent(symbol_node: Node) -> str | None:
    for child in symbol_node.children:
        if child.head == "extends" and len(child.children) >= 2:
            return _token_text(child.children[1])
    return None


def _collect_pin_numbers(symbol_node: Node, found: set[str]) -> None:
    """Add the number of every pin below symbol_node, in any unit or body style."""
    stack = [symbol_node]
    while stack:
        node = stack.pop()
        if node.head == "pin":
            for child in node.children:
                if child.head == "number" and len(child.children) >= 2:
                    number = _token_text(child.children[1])
                    if number:
                        found.add(number)
        stack.extend(c for c in node.children if c.kind == "list")


def symbol_pin_numbers(root: Node, name: str) -> set[str]:
    """Pin numbers of the named top-level symbol, plus those of every extends ancestor in the same library."""
    by_name: dict[str, Node] = {}
    for ref in find_symbols(root):
        by_name.setdefault(ref.name, ref.node)
    pins: set[str] = set()
    seen: set[str] = set()
    current: str | None = name
    while current is not None and current in by_name and current not in seen:
        seen.add(current)
        _collect_pin_numbers(by_name[current], pins)
        current = _extends_parent(by_name[current])
    return pins


def footprint_pad_numbers(footprint_node: Node) -> set[str]:
    """Numbers of the footprint's direct pad children; pads with an empty number (mounting holes) are ignored."""
    found = set()
    for child in footprint_node.children:
        if child.head == "pad" and len(child.children) >= 2:
            number = _token_text(child.children[1])
            if number:
                found.add(number)
    return found


def _natural(value: str) -> list[tuple[int, int, str]]:
    """Sort key that puts 2 before 10 and A2 before A10."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in _DIGITS.split(value) if p]


def pin_pad_issues(symbol_name: str, footprint: str, pins: set[str], pads: set[str]) -> list[Issue]:
    """One WARNING when the symbol's pin numbers and the footprint's pad numbers differ in either direction."""
    no_pad = sorted(pins - pads, key=_natural)
    no_pin = sorted(pads - pins, key=_natural)
    if not no_pad and not no_pin:
        return []
    parts = []
    if no_pad:
        parts.append(f"pins with no pad: {', '.join(no_pad)}")
    if no_pin:
        parts.append(f"pads with no pin: {', '.join(no_pin)}")
    return [Issue(Severity.WARNING, "verify.pin_pad_mismatch", f"{symbol_name} does not match {footprint}; " + "; ".join(parts))]


# -- the same part name in another library (POST-03, D-21) ------------------------


def symbol_search_dirs(layout: RepoLayout, tools: ToolContext) -> list[tuple[str, Path]]:
    """(label prefix, folder) pairs searched for an existing part name, most local first."""
    dirs: list[tuple[str, Path]] = [("", layout.symbols_dir)]
    wurth = layout.repo_root / "WurthElektronik"
    if wurth.is_dir():
        dirs.append((_WURTH_PREFIX, wurth))
    if tools.kicad_symbols_dir is not None and tools.kicad_symbols_dir.is_dir():
        dirs.append(("KiCad:", tools.kicad_symbols_dir))
    dirs.extend(("", d) for d in tools.extra_symbol_dirs)
    return dirs


def _symbol_files(prefix: str, folder: Path) -> list[Path]:
    """The .kicad_sym files of one search folder; WurthElektronik is searched recursively, the rest are flat."""
    found: list[Path] = []
    try:
        if prefix == _WURTH_PREFIX:
            for here, _, files in os.walk(folder):
                found.extend(Path(here) / f for f in files if f.casefold().endswith(".kicad_sym"))
        else:
            found.extend(folder / f for f in os.listdir(folder) if f.casefold().endswith(".kicad_sym"))
    except OSError:
        pass
    return sorted(found)


def _declaration_pattern(needle: bytes) -> re.Pattern:
    """Match needle as a top-level symbol: one tab or one to two spaces of indent, or right after a one-line header."""
    return re.compile(
        rb"(?:^(?:\t| {1,2})|\(kicad_symbol_lib\b[^\n]*?[ \t)])" + re.escape(needle) + rb"(?=[\s)]|\Z)",
        re.MULTILINE,
    )


def find_name_elsewhere(
    names: Sequence[str], layout: RepoLayout, *, exclude_library: str, tools: ToolContext
) -> list[Issue]:
    """One WARNING per name that another library already declares; never blocks.

    A bytes-substring prefilter rejects almost every file, and a depth-1 regex confirms the
    rest. Libraries are never parsed: parsing KiCad's stock symbols costs about a minute.
    """
    wanted: dict[str, bytes] = {}
    for name in names:
        wanted.setdefault(name, ("(symbol " + quote(name)).encode("utf-8"))
    if not wanted:
        return []
    patterns: dict[str, re.Pattern] = {}
    labels: dict[str, list[str]] = {name: [] for name in wanted}
    for prefix, folder in symbol_search_dirs(layout, tools):
        for path in _symbol_files(prefix, folder):
            if not prefix and folder == layout.symbols_dir and path.stem == exclude_library:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            label = f"{prefix}{path.stem}"
            for name, needle in wanted.items():
                if needle not in data or label in labels[name]:
                    continue
                pattern = patterns.get(name) or patterns.setdefault(name, _declaration_pattern(needle))
                if pattern.search(data):
                    labels[name].append(label)
    return [
        Issue(
            Severity.WARNING,
            "verify.name_elsewhere",
            f"{name} already exists in: {', '.join(found)}; KiCad allows this, check it is intended",
        )
        for name, found in labels.items()
        if found
    ]


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
