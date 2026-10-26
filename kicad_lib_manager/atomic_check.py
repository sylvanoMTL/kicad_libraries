"""The one atomic rule check, reused unchanged by the scan, the Phase 10 Install, the Phase 11 commit gate and the Phase 13 migration.

It reads text only and writes nothing: a scan, a refused install or an interrupted run never leaves a
library half-changed. Every reason is plain language (MPN, Manufacturer, Value, Datasheet, Description),
never a raw KiCad field name. A Datasheet value is judged as a string and is never fetched or opened.
"""

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import kicad_files
from .importer import fieldrules
from .importer.package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES
from .models import FixSpec, FootprintLibrary, Issue, Severity, SymbolEntry, SymbolLibrary, Violation
from .sexpr import Node

ATOMIC_PREFIX = "Atomic_"
# The blocking rules of ATOM-01 in their reporting order
ATOMIC_RULES = ("mpn", "manufacturer", "footprint", "value", "datasheet", "description", "model_3d")

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_VARIABLE_PATH_RE = re.compile(r"\$\{[^}]+\}[/\\]")
_MIB = 1024 * 1024


def is_atomic(nickname: str) -> bool:
    """Return True for a library the atomic rules apply to: the exact, case-sensitive Atomic_ prefix."""
    return nickname.startswith(ATOMIC_PREFIX)


def datasheet_problem(value: str) -> str | None:
    """Return why a Datasheet value is not acceptable, or None when it is a link or a file path.

    A string check only: the link is never fetched and the path is never opened.
    """
    text = value.strip()
    if text in ("", "~"):
        return "no datasheet"
    if _URL_RE.fullmatch(text) or _VARIABLE_PATH_RE.match(text):
        return None
    if PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute():
        return None
    return "Datasheet is not a link or file path"


def _blank(value: str) -> bool:
    return fieldrules.is_placeholder(value) or value.strip() == "~"


def _find_property(properties: list[kicad_files.PropertyRef], name: str) -> kicad_files.PropertyRef | None:
    return next((p for p in properties if p.name == name), None)


def _datasheet_violation(
    properties: list[kicad_files.PropertyRef], symbol: str, rel_path: str, fixable: bool
) -> Violation | None:
    prop = _find_property(properties, "Datasheet")
    problem = datasheet_problem(prop.value if prop is not None else "")
    if problem is None:
        return None
    fill = None
    if fixable:
        fill = FixSpec("fill_datasheet", rel_path, symbol, "Fill in the datasheet link", {"property": "Datasheet", "value": ""})
    return Violation("datasheet", problem, fill=fill)


def _description_violation(
    root: Node,
    symbol_node: Node,
    properties: list[kicad_files.PropertyRef],
    symbol: str,
    rel_path: str,
    fixable: bool,
) -> Violation | None:
    if any(p.name in fieldrules.DESCRIPTION_FIELDS and not _blank(p.value) for p in properties):
        return None
    fill = None
    if fixable:
        field_name = kicad_files.description_field_name(symbol_node, kicad_files.file_version(root))
        fill = FixSpec("fill_description", rel_path, symbol, "Fill in the description", {"property": field_name, "value": ""})
    return Violation("description", "no description", fill=fill)


def check_symbol(root: Node, name: str, *, rel_path: str, fixable: bool) -> SymbolEntry:
    """Check one symbol of a parsed .kicad_sym and return its entry with one violation per broken rule."""
    ref = kicad_files.find_symbol(root, name)
    entry = SymbolEntry(name)
    if ref is None:
        return entry
    entry.extends = kicad_files.extends_name(ref.node)
    properties = kicad_files.list_properties(ref.node)
    found = [
        _datasheet_violation(properties, name, rel_path, fixable),
        _description_violation(root, ref.node, properties, name, rel_path, fixable),
    ]
    entry.violations = sorted((v for v in found if v is not None), key=lambda v: ATOMIC_RULES.index(v.rule))
    return entry


def _read_library(path: Path) -> tuple[Node | None, str | None]:
    """Return (parsed root, None), or (None, why the library could not be checked)."""
    try:
        if path.stat().st_size > MAX_KICAD_TEXT_BYTES:
            return None, f"the library file is larger than {MAX_KICAD_TEXT_BYTES // _MIB} MiB"
        data = path.read_bytes()
    except OSError as e:
        return None, f"the library file could not be read ({e.strerror or e})"
    loaded = kicad_files.parse_bytes(data, path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return None, loaded.text
    return loaded.root, None


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _summary(libraries_seen: int, failing: int, total: int, problems: int) -> Issue | None:
    if not libraries_seen:
        return None
    if failing:
        text = f"Atomic check: {failing} of {total} symbols fail ({_plural(problems, 'problem')})"
        return Issue(Severity.WARNING, "atomic.summary", text)
    if total == 0:
        return Issue(Severity.SUCCESS, "atomic.summary", "Atomic check: no symbols in the Atomic_ libraries")
    return Issue(Severity.SUCCESS, "atomic.summary", f"Atomic check: all {total} symbols pass")


def check_libraries(
    repo_root: Path,
    sym_libs: list[SymbolLibrary],
    fp_libs: list[FootprintLibrary],
    kicad_fp_dir: Path | None,
) -> list[Issue]:
    """Check every Atomic_ symbol library, attach the entries to it and return the log lines.

    Only libraries whose nickname starts with Atomic_ are judged. Fixes are attached only for
    libraries under Custom/. A library that cannot be read gets check_problem and the scan goes on.
    """
    issues: list[Issue] = []
    seen = failing = total = problems = 0
    for lib in sym_libs:
        if not is_atomic(lib.nickname):
            continue
        seen += 1
        lib.atomic = True
        lib.symbols = []
        lib.check_problem = None
        root, problem = _read_library(repo_root / lib.rel_path)
        if root is None:
            lib.check_problem = problem
            issues.append(Issue(Severity.WARNING, "atomic.unreadable", f"{lib.nickname}: could not be checked: {problem}"))
            continue
        fixable = lib.source == "Custom"
        for ref in kicad_files.find_symbols(root):
            entry = check_symbol(root, ref.name, rel_path=lib.rel_path, fixable=fixable)
            lib.symbols.append(entry)
            total += 1
            if entry.failing:
                failing += 1
            prefix = f"{lib.nickname} / {entry.name}: "
            for violation in entry.violations:
                problems += 1
                issues.append(Issue(Severity.WARNING, f"atomic.{violation.rule}", prefix + violation.text))
            for finding in entry.findings:
                issues.append(Issue(Severity.INFO, f"atomic.{finding.kind}", prefix + finding.text))
    summary = _summary(seen, failing, total, problems)
    if summary is not None:
        issues.append(summary)
    return issues
