"""The chooser setup of TBL-02: pins the Atomic_ libraries and sets the MPN/Manufacturer
columns in KiCad's symbol chooser. Same config-write contract as sync_kicad_path_vars
(library_scanner.py): old -> new shown first, backup, verified atomic write, KiCad-open
aware, re-read merge. Qt-free.
"""

import copy
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import fsutil, kicad_files
from .kicad_process import kicad_running
from .library_scanner import (
    _KICAD_COMMON_BACKUPS_KEPT,
    _PATH_VAR_PASSES,
    ConfirmAnswer,
    _as_answer,
    _norm_path,
    _prune_backups,
    _read_config,
    find_kicad_config_dir,
)
from .models import Issue, Severity

EESCHEMA_FILE = "eeschema.json"
COMMON_FILE = "kicad_common.json"
MPN_COLUMN_WIDTH = 200
STRAY_COLUMN = "MANUFACTURER"
ATOMIC_COLUMNS = ("MPN", "Manufacturer")


@dataclass(frozen=True)
class ChooserChange:
    """One old -> new line shown to the owner before any write."""

    file: str  # "common" or "eeschema"
    label: str
    old: str
    new: str


def _format_list(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _format_widths(widths: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in widths.items()) if widths else "(none)"


def chooser_tables(dest_tables: Path) -> tuple[list[str], list[str], list[Issue]]:
    """Atomic_ symbol and footprint library nicknames listed in the Destination tables.

    Returns (symbol names, footprint names, issues). Footprint names holds
    ["Atomic_Footprints"] when fp-lib-table lists it, else []. An unreadable table
    is an Issue in the third element; INFO chooser.tables_read is always appended.
    """
    symbol_names: list[str] = []
    fp_names: list[str] = []
    issues: list[Issue] = []

    for filename, is_symbol_table in (("sym-lib-table", True), ("fp-lib-table", False)):
        path = dest_tables / filename
        if not path.exists():
            issues.append(Issue(
                Severity.WARNING,
                "chooser.no_tables",
                f"No {filename} found in {dest_tables}",
            ))
            continue
        loaded = kicad_files.load(path)
        if isinstance(loaded, Issue):
            issues.append(loaded)
            continue
        table = kicad_files.lib_table(loaded.root)
        if table is None:
            continue
        for entry in table.entries:
            if not entry.name:
                continue
            if is_symbol_table:
                if entry.name.startswith("Atomic_") and entry.name not in symbol_names:
                    symbol_names.append(entry.name)
            elif entry.name == "Atomic_Footprints" and "Atomic_Footprints" not in fp_names:
                fp_names.append("Atomic_Footprints")

    issues.append(Issue(
        Severity.INFO,
        "chooser.tables_read",
        f"Read the Atomic_ libraries from the tables in {dest_tables}",
    ))
    return symbol_names, fp_names, issues


def plan_pins(
    session: dict, symbol_libs: Sequence[str], fp_libs: Sequence[str]
) -> tuple[list[str], list[str]]:
    """New (pinned_symbol_libs, pinned_fp_libs): hand pins kept in order, stale Atomic_
    pins removed, wanted names not yet pinned appended sorted case-insensitively."""

    def _plan(existing: Sequence[str], wanted: Sequence[str]) -> list[str]:
        wanted_set = set(wanted)
        kept = [
            name for name in existing
            if not (name.startswith("Atomic_") and name not in wanted_set)
        ]
        kept_set = set(kept)
        additions = sorted(
            (name for name in wanted if name not in kept_set),
            key=str.casefold,
        )
        return kept + additions

    old_sym = session.get("pinned_symbol_libs")
    old_sym = old_sym if isinstance(old_sym, list) else []
    old_fp = session.get("pinned_fp_libs")
    old_fp = old_fp if isinstance(old_fp, list) else []
    return _plan(old_sym, symbol_libs), _plan(old_fp, fp_libs)


def plan_columns(lib_tree: dict) -> tuple[list[str], dict[str, int]]:
    """New (columns, column_widths): MPN and Manufacturer inserted right after
    Description (or Item, or at the front), the stray MANUFACTURER column removed,
    its width moved to Manufacturer when Manufacturer has none, MPN gets a default
    width when it has none. Other columns and their order are kept."""
    columns = lib_tree.get("columns")
    if not isinstance(columns, list) or not columns:
        columns = ["Item", "Description"]
    columns = [c for c in columns if isinstance(c, str)]

    widths_in = lib_tree.get("column_widths")
    widths_in = widths_in if isinstance(widths_in, dict) else {}

    def _valid_width(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    stray_width = widths_in.get(STRAY_COLUMN)
    stray_width = stray_width if _valid_width(stray_width) else None

    columns = [c for c in columns if c != STRAY_COLUMN]
    remainder = [c for c in columns if c not in ATOMIC_COLUMNS]

    if "Description" in remainder:
        idx = remainder.index("Description") + 1
    elif "Item" in remainder:
        idx = remainder.index("Item") + 1
    else:
        idx = 0
    new_columns = remainder[:idx] + list(ATOMIC_COLUMNS) + remainder[idx:]

    new_widths: dict[str, int] = {
        key: value for key, value in widths_in.items()
        if key != STRAY_COLUMN and _valid_width(value)
    }
    if "Manufacturer" not in new_widths and stray_width is not None:
        new_widths["Manufacturer"] = stray_width
    if "MPN" not in new_widths:
        new_widths["MPN"] = MPN_COLUMN_WIDTH

    return new_columns, new_widths


_CHOOSER_KEY_PATHS = {
    "common": (("session", "pinned_symbol_libs"), ("session", "pinned_fp_libs")),
    "eeschema": (("lib_tree", "columns"), ("lib_tree", "column_widths")),
}


def _get_path(obj: dict, path: tuple[str, ...]) -> object:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _only_chooser_keys_changed(before: dict, after: dict, file: str) -> bool:
    """True when after equals before with just this file's chooser keys set to after's values."""
    expected = copy.deepcopy(before)
    for path in _CHOOSER_KEY_PATHS[file]:
        node = expected
        for key in path[:-1]:
            node = node.setdefault(key, {})
        node[path[-1]] = _get_path(after, path)
    return after == expected


def _plan_chooser_changes(
    old_sym_pins: list[str],
    new_sym_pins: list[str],
    old_fp_pins: list[str],
    new_fp_pins: list[str],
    lib_tree: dict | None,
    new_columns: list[str] | None,
    new_widths: dict[str, int] | None,
) -> list[ChooserChange]:
    changes: list[ChooserChange] = []
    if new_sym_pins != old_sym_pins:
        changes.append(ChooserChange(
            "common", "Pinned symbol libraries",
            _format_list(old_sym_pins), _format_list(new_sym_pins),
        ))
    if new_fp_pins != old_fp_pins:
        changes.append(ChooserChange(
            "common", "Pinned footprint libraries",
            _format_list(old_fp_pins), _format_list(new_fp_pins),
        ))
    if lib_tree is not None:
        old_columns = lib_tree.get("columns")
        old_columns = old_columns if isinstance(old_columns, list) else []
        if new_columns != old_columns:
            changes.append(ChooserChange(
                "eeschema", "Symbol chooser columns",
                _format_list(old_columns), _format_list(new_columns or []),
            ))
        old_widths = lib_tree.get("column_widths")
        old_widths = old_widths if isinstance(old_widths, dict) else {}
        if new_widths != old_widths:
            changes.append(ChooserChange(
                "eeschema", "Symbol chooser column widths",
                _format_widths(old_widths), _format_widths(new_widths or {}),
            ))
    return changes


def sync_kicad_chooser(
    repo_root: Path,
    dest_tables: Path,
    *,
    config_base: Path | None = None,
    backup_root: Path | None = None,
    running: Callable[[], list[str]] | None = None,
    confirm: Callable[[list[ChooserChange]], bool | ConfirmAnswer] | None = None,
) -> list[Issue]:
    """Pin every Atomic_ library from dest_tables and set the MPN/Manufacturer columns
    in the newest kicad_common.json and eeschema.json.

    Nothing is written unless confirm(changes) answers True or ConfirmAnswer.WRITE.
    changes lists every old -> new line for both files. A missing confirm writes
    nothing. Refusal and re-read-merge handling land in a later revision of this
    function; this version implements the confirmed-write path only.
    """
    config_dir = find_kicad_config_dir(config_base)
    if not config_dir:
        return [Issue(
            Severity.WARNING,
            "chooser.dir_not_found",
            "Could not find KiCad config directory; KiCad's chooser was not set up",
        )]

    common_path = config_dir / COMMON_FILE
    if not common_path.exists():
        return [Issue(
            Severity.WARNING,
            "chooser.not_found",
            f"KiCad's settings file was not found "
            f"(start and close KiCad {config_dir.name} once, then try again)",
        )]

    read = _read_config(common_path)
    if isinstance(read, Issue):
        return [read]
    common_src, common_config, old_vars = read

    issues: list[Issue] = []
    sym_names, fp_names, table_issues = chooser_tables(dest_tables)
    issues.extend(table_issues)

    session = common_config.get("session")
    session = session if isinstance(session, dict) else {}
    new_sym_pins, new_fp_pins = plan_pins(session, sym_names, fp_names)
    old_sym_pins = session.get("pinned_symbol_libs")
    old_sym_pins = old_sym_pins if isinstance(old_sym_pins, list) else []
    old_fp_pins = session.get("pinned_fp_libs")
    old_fp_pins = old_fp_pins if isinstance(old_fp_pins, list) else []

    eeschema_path = config_dir / EESCHEMA_FILE
    eeschema_missing = not eeschema_path.exists()
    eeschema_src = None
    eeschema_config: dict | None = None
    lib_tree: dict | None = None
    new_columns: list[str] | None = None
    new_widths: dict[str, int] | None = None

    if eeschema_missing:
        issues.append(Issue(
            Severity.WARNING,
            "chooser.not_found",
            "KiCad's schematic editor settings were not found; start and close the "
            "Schematic Editor once to add the MPN and Manufacturer columns",
        ))
    else:
        eeschema_src = fsutil.read_source(eeschema_path)
        if isinstance(eeschema_src, Issue):
            return [eeschema_src]
        try:
            eeschema_config = json.loads(eeschema_src.text)
        except json.JSONDecodeError:
            return issues + [Issue(
                Severity.ERROR,
                "chooser.bad_json",
                "Could not read KiCad's schematic editor settings: invalid JSON; "
                "nothing was written",
            )]
        bad_shape = not isinstance(eeschema_config, dict)
        lib_tree = {} if bad_shape else eeschema_config.get("lib_tree", {})
        bad_shape = bad_shape or not isinstance(lib_tree, dict)
        if not bad_shape:
            columns_in = lib_tree.get("columns")
            widths_in = lib_tree.get("column_widths")
            bad_shape = (
                not (columns_in is None or isinstance(columns_in, list))
                or not (widths_in is None or isinstance(widths_in, dict))
            )
        if bad_shape:
            return issues + [Issue(
                Severity.ERROR,
                "chooser.bad_shape",
                "KiCad's schematic editor settings have an unexpected structure "
                "(its chooser columns cannot be read); nothing was written",
            )]
        new_columns, new_widths = plan_columns(lib_tree)

    changes = _plan_chooser_changes(
        old_sym_pins, new_sym_pins, old_fp_pins, new_fp_pins,
        lib_tree, new_columns, new_widths,
    )
    if not changes:
        return issues + [Issue(
            Severity.INFO,
            "chooser.ok",
            "KiCad's chooser is already set up; nothing to change",
        )]

    if confirm is None:
        return issues + [Issue(
            Severity.WARNING,
            "chooser.confirm_required",
            "Not setting up KiCad's chooser: no confirmation step was provided",
        )]

    answer = _as_answer(confirm(changes))
    if answer is not ConfirmAnswer.WRITE:
        return issues + [Issue(
            Severity.INFO,
            "chooser.declined",
            "KiCad's chooser left unchanged (change declined)",
        )]

    common_changed = any(c.file == "common" for c in changes)
    eeschema_changed = any(c.file == "eeschema" for c in changes)

    new_common_text = None
    if common_changed:
        new_common = copy.deepcopy(common_config)
        new_session = new_common.setdefault("session", {})
        new_session["pinned_symbol_libs"] = new_sym_pins
        new_session["pinned_fp_libs"] = new_fp_pins
        new_common_text = json.dumps(new_common, indent=2, ensure_ascii=False) + "\n"
        if not _only_chooser_keys_changed(common_config, json.loads(new_common_text), "common"):
            return issues + [Issue(
                Severity.ERROR,
                "chooser.verify_failed",
                "Did not write KiCad's settings file: the new content would change "
                "more than the chooser keys",
            )]
        new_common_text = fsutil.normalize_eol(new_common_text, common_src.eol)

    new_eeschema_text = None
    if eeschema_changed:
        new_eeschema = copy.deepcopy(eeschema_config)
        new_lib_tree = new_eeschema.setdefault("lib_tree", {})
        new_lib_tree["columns"] = new_columns
        new_lib_tree["column_widths"] = new_widths
        new_eeschema_text = json.dumps(new_eeschema, indent=2, ensure_ascii=False) + "\n"
        if not _only_chooser_keys_changed(eeschema_config, json.loads(new_eeschema_text), "eeschema"):
            return issues + [Issue(
                Severity.ERROR,
                "chooser.verify_failed",
                "Did not write KiCad's schematic editor settings: the new content "
                "would change more than the chooser columns",
            )]
        new_eeschema_text = fsutil.normalize_eol(new_eeschema_text, eeschema_src.eol)

    if common_changed:
        common_backup_dir = (backup_root or fsutil.default_backup_dir()) / "kicad_common" / config_dir.name
        backup = fsutil.backup_file(common_path, common_backup_dir)
        if isinstance(backup, Issue):
            return issues + [backup]
        issues.append(Issue(
            Severity.INFO, "chooser.backed_up", f"Backed up KiCad's settings file to {backup}"
        ))
        failure = fsutil.atomic_write_text(common_path, new_common_text, bom=common_src.bom)
        if failure is not None:
            return issues + [failure]
        issues.append(Issue(
            Severity.SUCCESS, "chooser.written",
            "Updated KiCad's settings file (restart KiCad to apply)",
        ))
        issues.extend(_prune_backups(common_backup_dir, common_path.name, keep=_KICAD_COMMON_BACKUPS_KEPT))

    if eeschema_changed:
        eeschema_backup_dir = (backup_root or fsutil.default_backup_dir()) / "eeschema" / config_dir.name
        backup2 = fsutil.backup_file(eeschema_path, eeschema_backup_dir)
        if isinstance(backup2, Issue):
            return issues + [backup2]
        issues.append(Issue(
            Severity.INFO, "chooser.backed_up",
            f"Backed up KiCad's schematic editor settings to {backup2}",
        ))
        failure2 = fsutil.atomic_write_text(eeschema_path, new_eeschema_text, bom=eeschema_src.bom)
        if failure2 is not None:
            return issues + [failure2]
        issues.append(Issue(
            Severity.SUCCESS, "chooser.written",
            "Updated KiCad's schematic editor settings (restart KiCad to apply)",
        ))
        issues.extend(_prune_backups(eeschema_backup_dir, eeschema_path.name, keep=_KICAD_COMMON_BACKUPS_KEPT))

    return issues
