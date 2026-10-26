"""The one atomic rule check, reused unchanged by the scan, the Phase 10 Install, the Phase 11 commit gate and the Phase 13 migration.

It reads text only and writes nothing: a scan, a refused install or an interrupted run never leaves a
library half-changed. Every reason is plain language (MPN, Manufacturer, Value, Datasheet, Description),
never a raw KiCad field name. A Datasheet value is judged as a string and is never fetched or opened.
"""

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import kicad_files, manufacturers
from .importer import fieldrules
from .importer.package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES
from .models import FixSpec, Finding, FootprintLibrary, Issue, Severity, SymbolEntry, SymbolLibrary, Violation
from .sexpr import Node

ATOMIC_PREFIX = "Atomic_"
# The blocking rules of ATOM-01 in their reporting order
ATOMIC_RULES = ("mpn", "manufacturer", "footprint", "value", "datasheet", "description", "model_3d")

# The D-13 list: the only edits a one-click fix may make
SAFE_FIX_KINDS = ("value_to_mpn", "rename_alias", "canonical_manufacturer", "merge_alias", "remove_leftover")
# Templates the dialog completes with typed or picked input
FILL_KINDS = ("fill_datasheet", "fill_description", "attach_model")

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


def _filled(properties: list[kicad_files.PropertyRef], names: tuple[str, ...]) -> list[kicad_files.PropertyRef]:
    """The group's properties that hold a real value, in file order."""
    return [p for p in properties if p.name in names and not _blank(p.value)]


def _agreed_mpn(filled: list[kicad_files.PropertyRef]) -> kicad_files.PropertyRef | None:
    """The property to read the MPN from when every filled field holds the same value, else None."""
    if not filled or len({p.value.strip() for p in filled}) != 1:
        return None
    return next((p for p in filled if p.name == fieldrules.MPN_FIELDS[0]), filled[0])


def effective_mpn(symbol_node: Node) -> str | None:
    """Return the symbol's own MPN, or None when it has none or its MPN fields disagree.

    Only the symbol's own properties count: a derived symbol never takes its parent's MPN (ATOM-02).
    """
    chosen = _agreed_mpn(_filled(kicad_files.list_properties(symbol_node), fieldrules.MPN_FIELDS))
    return chosen.value if chosen is not None else None


def _quoted(names: list[str]) -> str:
    return " and ".join(f'"{n}"' for n in names) if len(names) <= 2 else (
        ", ".join(f'"{n}"' for n in names[:-1]) + f' and "{names[-1]}"'
    )


def _group_violation(
    kind: str,
    properties: list[kicad_files.PropertyRef],
    symbol: str,
    rel_path: str,
    fixable: bool,
    *,
    absent: str,
    suffix: str = "",
    label_suffix: str = "",
) -> tuple[Violation | None, Finding | None]:
    """Judge the MPN or the Manufacturer group of one symbol: absent, aliased, duplicated, disagreeing or mis-spelled.

    kind is "mpn" or "manufacturer"; absent is the full reason when no field holds a value. suffix is
    appended to every other reason and label_suffix to every fix label (they name an inherited owner).
    """
    is_mpn = kind == "mpn"
    names = fieldrules.MPN_FIELDS if is_mpn else fieldrules.MANUFACTURER_FIELDS
    label = "MPN" if is_mpn else "Manufacturer"
    canonical = names[0]
    members = [p for p in properties if p.name in names]
    filled = _filled(properties, names)
    if not filled:
        return Violation(kind, absent), None

    def match(prop: kicad_files.PropertyRef):
        return None if is_mpn else manufacturers.lookup(prop.value)

    def spelled(prop: kicad_files.PropertyRef) -> str:
        found = match(prop)
        return found.entry.name if found is not None else prop.value.strip()

    def make(text: str, fixes: list[FixSpec], *, choices: tuple[str, ...] = (), fill: FixSpec | None = None):
        if not fixable:
            return Violation(kind, text + suffix)
        return Violation(kind, text + suffix, tuple(fixes), fill, choices)

    def merge_label(group: list[kicad_files.PropertyRef], value: str) -> str:
        return f'Merge {_quoted([p.name for p in group])} into "{canonical}" = "{value}"' + label_suffix

    if len(filled) == 1:
        prop = filled[0]
        found = match(prop)
        reasons: list[str] = []
        alias = prop.name != canonical
        if alias:
            reasons.append(f'{label} is stored as "{prop.name}", not as "{canonical}"')
        bad_spelling = found is not None and not found.exact
        if bad_spelling:
            quoted = f'"{prop.value}" is not written as "{found.entry.name}"'
            reasons.append(quoted if alias else f'{label} {quoted}')
        if not reasons:
            unknown = None
            if not is_mpn and found is None:
                unknown = Finding("unknown_manufacturer", f'manufacturer "{prop.value.strip()}" is not in the manufacturer table')
            return None, unknown
        fixes: list[FixSpec] = []
        blank_canonical = next((p for p in members if p.name == canonical), None)
        if alias and blank_canonical is not None:
            # Renaming would create a second field with the canonical name, so the two are merged
            value = spelled(prop)
            fixes.append(FixSpec(
                "merge_alias", rel_path, symbol, merge_label([prop, blank_canonical], value),
                {"group": kind, "keep": canonical, "value": value},
            ))
        else:
            if alias:
                fixes.append(FixSpec(
                    "rename_alias", rel_path, symbol, f'Rename "{prop.name}" to "{canonical}"' + label_suffix,
                    {"property": prop.name, "new_name": canonical},
                ))
            if bad_spelling:
                fixes.append(FixSpec(
                    "canonical_manufacturer", rel_path, symbol,
                    f'Manufacturer "{prop.value}" → "{found.entry.name}"' + label_suffix,
                    {"property": prop.name, "value": found.entry.name},
                ))
        return make("; ".join(reasons), fixes), None

    keep = next((p for p in members if p.name == canonical), filled[0])
    if is_mpn:
        agree = len({p.value.strip() for p in filled}) == 1
    else:
        entries = {found.entry.name for found in (match(p) for p in filled) if found is not None}
        unmatched = [p for p in filled if match(p) is None]
        agree = (len(entries) == 1 and not unmatched) or (
            not entries and len({manufacturers.fold(p.value) for p in filled}) == 1
        )
    if agree:
        value = spelled(keep if keep in filled else filled[0])
        fix = FixSpec(
            "merge_alias", rel_path, symbol, merge_label(filled, value), {"group": kind, "keep": keep.name, "value": value}
        )
        return make(f'{label} is stored in several fields ({_quoted_list([p.name for p in filled])})', [fix]), None
    shown = ", ".join(f'"{p.value.strip()}" in "{p.name}"' for p in filled)
    choices = tuple(dict.fromkeys(spelled(p) for p in filled))
    fill = FixSpec(
        "merge_alias", rel_path, symbol, f"Keep one {label if is_mpn else label.lower()} value" + label_suffix,
        {"group": kind, "keep": keep.name, "value": ""},
    )
    return make(f"{label} fields disagree ({shown})", [], choices=choices, fill=fill), None


def _quoted_list(names: list[str]) -> str:
    return ", ".join(f'"{n}"' for n in names)


def _value_violation(
    node: Node, properties: list[kicad_files.PropertyRef], symbol: str, rel_path: str, fixable: bool
) -> Violation | None:
    mpn = effective_mpn(node)
    if mpn is None:
        return None
    prop = _find_property(properties, "Value")
    if prop is not None and prop.value == mpn:
        return None
    if prop is None:
        return Violation("value", f'no Value (it should be the MPN "{mpn}")')
    fixes = ()
    if fixable:
        fixes = (FixSpec(
            "value_to_mpn", rel_path, symbol, f'Value "{prop.value}" → "{mpn}"', {"property": "Value", "value": mpn}
        ),)
    return Violation("value", f'Value "{prop.value}" is not the MPN "{mpn}"', fixes)


def _leftover_findings(properties: list[kicad_files.PropertyRef], symbol: str, rel_path: str, fixable: bool) -> list[Finding]:
    found = []
    for prop in properties:
        if not fieldrules.is_volatile(prop.name) or fieldrules.is_protected(prop.name):
            continue
        fix = None
        if fixable:
            fix = FixSpec("remove_leftover", rel_path, symbol, f'Remove "{prop.name}"', {"property": prop.name})
        found.append(Finding("leftover", f'leftover price/stock data "{prop.name}"', fix))
    return found


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
    mpn, _ = _group_violation("mpn", properties, name, rel_path, fixable, absent="no MPN")
    manufacturer, unknown = _group_violation("manufacturer", properties, name, rel_path, fixable, absent="no manufacturer")
    found = [
        mpn,
        manufacturer,
        _value_violation(ref.node, properties, name, rel_path, fixable),
        _datasheet_violation(properties, name, rel_path, fixable),
        _description_violation(root, ref.node, properties, name, rel_path, fixable),
    ]
    entry.violations = sorted((v for v in found if v is not None), key=lambda v: ATOMIC_RULES.index(v.rule))
    if unknown is not None:
        entry.findings.append(unknown)
    entry.findings.extend(_leftover_findings(properties, name, rel_path, fixable))
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
