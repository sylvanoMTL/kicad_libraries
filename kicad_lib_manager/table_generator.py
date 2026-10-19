import re
import shutil
from pathlib import Path

from . import fsutil, kicad_files
from .kicad_files import LoadedFile
from .models import FootprintLibrary, Issue, Severity, SymbolLibrary
from .sexpr import Edit, apply_edits, quote

ENV_VAR = "KICAD_LIB_GITHUB"
_MANAGED_MARKER = f"${{{ENV_VAR}}}/"

_TABLE_FILES = {"sym_lib_table": "sym-lib-table", "fp_lib_table": "fp-lib-table"}

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


def _entry_text(name: str, uri: str) -> str:
    return (
        f'(lib (name {quote(name)})(type {quote("KiCad")})'
        f'(uri {quote(uri)})(options {quote("")})(descr {quote("")}))'
    )


def _whole_line(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Span of the full source line(s) holding only this node, else None."""
    left = start
    while left > 0 and text[left - 1] in " \t":
        left -= 1
    if not (left == 0 or text[left - 1] == "\n"):
        return None
    right = end
    while right < len(text) and text[right] in " \t":
        right += 1
    if right == len(text):
        return left, right
    if text.startswith("\r\n", right):
        return left, right + 2
    if text[right] == "\n":
        return left, right + 1
    return None  # another token follows on the same line


class MergeResult:
    """Result of a table merge operation."""
    __slots__ = ("content", "preserved", "added", "removed", "issues")

    def __init__(self, content: str, preserved: int, added: int,
                 removed: list[str] | None = None,
                 issues: list[Issue] | None = None):
        self.content = content
        self.preserved = preserved
        self.added = added
        self.removed = removed or []
        self.issues = issues or []


def _is_managed(entry: kicad_files.LibEntry) -> bool:
    return entry.uri is not None and _MANAGED_MARKER in entry.uri


def _merge_table(tag: str, existing: LoadedFile | None,
                 libs: list) -> MergeResult | Issue:
    """Splice the selected libraries into an existing table.

    Only entries owned by this tool (URI holds the managed marker) are removed;
    every other byte of the existing file is kept as it is.
    """
    filename = _TABLE_FILES[tag]
    selected = [lib for lib in libs if lib.selected]
    entries = [
        _entry_text(lib.nickname, f"{_MANAGED_MARKER}{lib.rel_path}")
        for lib in selected
    ]

    if existing is None or not existing.source.text.strip(" \t\r\n"):
        lines = [f"({tag}\n"] + [f"  {e}\n" for e in entries] + [")\n"]
        return MergeResult("".join(lines), 0, len(selected))

    table = kicad_files.lib_table(existing.root)
    if table is None or table.tag != tag:
        return Issue(
            Severity.ERROR,
            "table.unrecognised",
            f"Could not update {filename}: no ({tag} ...) table found; "
            "file left unchanged",
        )

    text = existing.source.text
    eol = existing.source.eol
    block = "".join(f"  {e}{eol}" for e in entries)
    managed = [e for e in table.entries if _is_managed(e)]
    selected_paths = {lib.rel_path for lib in selected}

    edits: list[Edit] = []
    placed = False
    for i, entry in enumerate(managed):
        span = _whole_line(text, entry.node.start, entry.node.end)
        if i == 0 and span is not None:
            edits.append(Edit(span[0], span[1], block))
            placed = True
        else:
            lo, hi = span if span is not None else (entry.node.start, entry.node.end)
            edits.append(Edit(lo, hi, ""))

    if not placed and block:
        p = table.node.end - 1
        line_start = p
        while line_start > 0 and text[line_start - 1] in " \t":
            line_start -= 1
        if line_start == 0 or text[line_start - 1] == "\n":
            edits.append(Edit(line_start, line_start, block))
        else:
            edits.append(Edit(p, p, eol + block))

    removed = [
        e.name or e.uri
        for e in managed
        if e.uri.split(_MANAGED_MARKER, 1)[1] not in selected_paths
    ]
    return MergeResult(
        apply_edits(text, edits),
        sum(1 for e in table.entries if not _is_managed(e)),
        len(selected),
        removed,
    )


def generate_sym_lib_table(libs: list[SymbolLibrary],
                           existing: LoadedFile | None = None) -> MergeResult | Issue:
    return _merge_table("sym_lib_table", existing, libs)


def generate_fp_lib_table(libs: list[FootprintLibrary],
                          existing: LoadedFile | None = None) -> MergeResult | Issue:
    return _merge_table("fp_lib_table", existing, libs)


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
                 fp_libs: list[FootprintLibrary]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        dest_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return [Issue(Severity.ERROR, "fs.write_failed",
                      f"Could not create {dest_folder}: {e.strerror or e}")]

    # Each table is processed on its own: one failure never blocks the other
    for tag, libs in (("sym_lib_table", sym_libs), ("fp_lib_table", fp_libs)):
        filename = _TABLE_FILES[tag]
        path = dest_folder / filename

        existing = None
        bom = False
        if path.exists():
            loaded = kicad_files.load(path)
            if isinstance(loaded, Issue):
                issues.append(loaded)
                continue
            issues.extend(loaded.source.issues)
            existing = loaded
            bom = loaded.source.bom

        result = _merge_table(tag, existing, libs)
        if isinstance(result, Issue):
            issues.append(result)
            continue

        if existing is not None:
            backup = fsutil.backup_file(path, path.parent)
            if isinstance(backup, Issue):
                issues.append(backup)
                continue
            issues.append(Issue(Severity.INFO, "table.backed_up",
                                f"Backed up {filename} -> {backup.name}"))

        failure = fsutil.atomic_write_text(path, result.content, bom=bom)
        if failure is not None:
            issues.append(failure)
            continue

        issues.append(Issue(
            Severity.SUCCESS, "table.written",
            f"Written {filename}: preserved {result.preserved} external | "
            f"added {result.added} from selection",
        ))
        if result.removed:
            issues.append(Issue(
                Severity.INFO, "table.removed",
                f"Removed from {filename} (deselected): {', '.join(result.removed)}",
            ))
        issues.extend(result.issues)

    return issues


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
