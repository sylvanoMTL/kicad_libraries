import re
import shutil
from pathlib import Path

from .models import FootprintLibrary, SymbolLibrary

ENV_VAR = "KICAD_LIB_GITHUB"
_MANAGED_MARKER = f"${{{ENV_VAR}}}/"

# Regex to extract individual (lib ...) entries from a table file
_LIB_ENTRY_RE = re.compile(
    r'\(lib\s+\(name\s+"([^"]*)"\)'
    r'\(type\s+"([^"]*)"\)'
    r'\(uri\s+"([^"]*)"\)'
    r'\(options\s+"([^"]*)"\)'
    r'\(descr\s+"([^"]*)"\)\)',
)


def parse_lib_table(path: Path) -> list[dict]:
    """Parse an existing sym-lib-table or fp-lib-table file.

    Returns a list of dicts with keys: name, type, uri, options, descr, raw.
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    entries = []
    for m in _LIB_ENTRY_RE.finditer(text):
        entries.append({
            "name": m.group(1),
            "type": m.group(2),
            "uri": m.group(3),
            "options": m.group(4),
            "descr": m.group(5),
            "raw": m.group(0),
        })
    return entries


def count_table_entries(path: Path) -> int:
    """Count the number of library entries in an existing table file."""
    return len(parse_lib_table(path))


def _format_entry(name: str, lib_type: str, uri: str,
                   options: str = "", descr: str = "") -> str:
    return (
        f'  (lib (name "{name}")(type "{lib_type}")'
        f'(uri "{uri}")'
        f'(options "{options}")(descr "{descr}"))'
    )


class MergeResult:
    """Result of a table merge operation."""
    __slots__ = ("content", "preserved", "added", "removed")

    def __init__(self, content: str, preserved: int, added: int,
                 removed: list[str] | None = None):
        self.content = content
        self.preserved = preserved
        self.added = added
        self.removed = removed or []


def _merge_table(table_tag: str, existing_path: Path,
                 new_entries: list[str],
                 new_nicknames: set[str]) -> MergeResult:
    """Merge new entries with existing non-managed entries.

    Preserves external entries, replaces managed entries with new selection.
    Reports which managed entries were removed (deselected).
    """
    existing = parse_lib_table(existing_path)

    preserved = [e for e in existing if _MANAGED_MARKER not in e["uri"]]
    old_managed = [e for e in existing if _MANAGED_MARKER in e["uri"]]

    # Entries that were managed but are no longer in the selection
    removed = [e["name"] for e in old_managed if e["name"] not in new_nicknames]

    lines = [f"({table_tag}"]
    for e in preserved:
        lines.append(f"  {e['raw']}")
    lines.extend(new_entries)
    lines.append(")")

    return MergeResult(
        content="\n".join(lines) + "\n",
        preserved=len(preserved),
        added=len(new_entries),
        removed=removed,
    )


def generate_sym_lib_table(libs: list[SymbolLibrary],
                           existing_path: Path | None = None) -> MergeResult:
    selected = [lib for lib in libs if lib.selected]
    new_entries = [
        _format_entry(lib.nickname, "KiCad", f"${{{ENV_VAR}}}/{lib.rel_path}")
        for lib in selected
    ]
    new_nicknames = {lib.nickname for lib in selected}

    if existing_path and existing_path.exists():
        return _merge_table("sym_lib_table", existing_path,
                            new_entries, new_nicknames)

    lines = ["(sym_lib_table"] + new_entries + [")"]
    return MergeResult("\n".join(lines) + "\n", 0, len(new_entries))


def generate_fp_lib_table(libs: list[FootprintLibrary],
                          existing_path: Path | None = None) -> MergeResult:
    selected = [lib for lib in libs if lib.selected]
    new_entries = [
        _format_entry(lib.nickname, "KiCad", f"${{{ENV_VAR}}}/{lib.rel_path}")
        for lib in selected
    ]
    new_nicknames = {lib.nickname for lib in selected}

    if existing_path and existing_path.exists():
        return _merge_table("fp_lib_table", existing_path,
                            new_entries, new_nicknames)

    lines = ["(fp_lib_table"] + new_entries + [")"]
    return MergeResult("\n".join(lines) + "\n", 0, len(new_entries))


def _check_nickname_collisions(existing_path: Path,
                               new_libs: list) -> list[str]:
    """Warn if a new entry has the same name as a preserved external entry."""
    existing = parse_lib_table(existing_path)
    external_names = {
        e["name"] for e in existing if _MANAGED_MARKER not in e["uri"]
    }
    new_names = {lib.nickname for lib in new_libs if lib.selected}
    collisions = external_names & new_names
    return [
        f"Warning: nickname '{n}' exists in both external table and selection"
        for n in sorted(collisions)
    ]


def backup_existing(file_path: Path) -> Path | None:
    if not file_path.exists():
        return None

    base_name = file_path.name
    parent = file_path.parent
    max_num = 0
    pattern = re.compile(re.escape(base_name) + r"_backup_(\d+)$")

    for f in parent.iterdir():
        m = pattern.match(f.name)
        if m:
            max_num = max(max_num, int(m.group(1)))

    backup_name = f"{base_name}_backup_{max_num + 1}"
    backup_path = parent / backup_name
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_tables(dest_folder: Path,
                 sym_libs: list[SymbolLibrary],
                 fp_libs: list[FootprintLibrary]) -> list[str]:
    messages = []
    dest_folder.mkdir(parents=True, exist_ok=True)

    sym_path = dest_folder / "sym-lib-table"
    fp_path = dest_folder / "fp-lib-table"

    # Check for nickname collisions
    for path, libs, label in [
        (sym_path, sym_libs, "sym-lib-table"),
        (fp_path, fp_libs, "fp-lib-table"),
    ]:
        collisions = _check_nickname_collisions(path, libs)
        messages.extend(collisions)

    # Generate merged content
    sym_result = generate_sym_lib_table(sym_libs, sym_path)
    fp_result = generate_fp_lib_table(fp_libs, fp_path)

    for path, result, label in [
        (sym_path, sym_result, "sym-lib-table"),
        (fp_path, fp_result, "fp-lib-table"),
    ]:
        backup = backup_existing(path)
        if backup:
            messages.append(f"Backed up {label} -> {backup.name}")
        path.write_text(result.content, encoding="utf-8")

        parts = [f"Written {label}:"]
        if result.preserved:
            parts.append(f"preserved {result.preserved} external")
        parts.append(f"added {result.added} from selection")
        if result.removed:
            parts.append(f"removed {len(result.removed)} "
                         f"({', '.join(result.removed)})")
        messages.append(" | ".join(parts))

    return messages


def list_backups(folder: Path) -> list[Path]:
    backups = []
    pattern = re.compile(r"(sym-lib-table|fp-lib-table)_backup_\d+$")
    if folder.exists():
        for f in sorted(folder.iterdir()):
            if f.is_file() and pattern.match(f.name):
                backups.append(f)
    return backups


def list_backup_pairs(folder: Path) -> list[tuple[int, Path | None, Path | None]]:
    """List backups grouped by number. Returns (number, sym_path, fp_path) tuples."""
    sym_pattern = re.compile(r"sym-lib-table_backup_(\d+)$")
    fp_pattern = re.compile(r"fp-lib-table_backup_(\d+)$")
    sym_map: dict[int, Path] = {}
    fp_map: dict[int, Path] = {}

    if folder.exists():
        for f in folder.iterdir():
            if not f.is_file():
                continue
            m = sym_pattern.match(f.name)
            if m:
                sym_map[int(m.group(1))] = f
                continue
            m = fp_pattern.match(f.name)
            if m:
                fp_map[int(m.group(1))] = f

    all_nums = sorted(set(sym_map) | set(fp_map), reverse=True)
    return [(n, sym_map.get(n), fp_map.get(n)) for n in all_nums]


def restore_backup(backup_path: Path) -> list[str]:
    messages = []
    name = backup_path.name
    # Extract base name: remove _backup_N suffix
    base_name = re.sub(r"_backup_\d+$", "", name)
    current_path = backup_path.parent / base_name

    # Back up current file before restoring
    backup = backup_existing(current_path)
    if backup:
        messages.append(f"Backed up current {base_name} -> {backup.name}")

    shutil.copy2(backup_path, current_path)
    messages.append(f"Restored {name} -> {base_name}")
    return messages


def restore_backup_pair(folder: Path, backup_num: int) -> list[str]:
    """Restore both sym-lib-table and fp-lib-table for a given backup number."""
    messages = []
    for base_name in ("sym-lib-table", "fp-lib-table"):
        backup_path = folder / f"{base_name}_backup_{backup_num}"
        if backup_path.exists():
            current_path = folder / base_name
            existing_backup = backup_existing(current_path)
            if existing_backup:
                messages.append(f"Backed up current {base_name} -> {existing_backup.name}")
            shutil.copy2(backup_path, current_path)
            messages.append(f"Restored {backup_path.name} -> {base_name}")
    return messages
