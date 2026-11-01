import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import fsutil, kicad_files
from .kicad_files import LoadedFile
from .models import FootprintLibrary, Issue, Severity, SymbolLibrary
from .sexpr import Edit, Node, apply_edits, quote

ENV_VAR = "KICAD_LIB_GITHUB"
_MANAGED_MARKER = f"${{{ENV_VAR}}}/"

_TABLE_FILES = {"sym_lib_table": "sym-lib-table", "fp_lib_table": "fp-lib-table"}

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


def _tail(entry: kicad_files.LibEntry) -> str:
    """Repo-relative path of a managed entry: the URI text after the marker."""
    return entry.uri.split(_MANAGED_MARKER, 1)[1]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _insert_before_close(text: str, table_node: Node, eol: str, block: str) -> Edit:
    """Edit that puts block just before the table's closing paren, on its own line(s)."""
    p = table_node.end - 1
    line_start = p
    while line_start > 0 and text[line_start - 1] in " \t":
        line_start -= 1
    if line_start == 0 or text[line_start - 1] == "\n":
        return Edit(line_start, line_start, block)
    return Edit(p, p, eol + block)


def _merge_table(tag: str, existing: LoadedFile | None,
                 libs: list) -> MergeResult | Issue:
    """Splice the selected libraries into an existing table.

    Only entries owned by this tool (URI holds the managed marker) are removed;
    every other byte of the existing file is kept as it is.
    """
    filename = _TABLE_FILES[tag]
    selected = [lib for lib in libs if lib.selected]

    seen: dict[str, SymbolLibrary | FootprintLibrary] = {}
    for lib in selected:
        prior = seen.get(lib.nickname)
        if prior is not None:
            return Issue(
                Severity.ERROR,
                "table.duplicate_nickname",
                f"Did not write {filename}: '{lib.nickname}' is selected twice "
                f"({prior.rel_path}, {lib.rel_path}); keep only one selected",
            )
        seen[lib.nickname] = lib

    if existing is None or not existing.source.text.strip(" \t\r\n"):
        lines = [f"({tag}\n"]
        lines += [
            f"  {_entry_text(lib.nickname, f'{_MANAGED_MARKER}{lib.rel_path}')}\n"
            for lib in selected
        ]
        lines.append(")\n")
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
    issues: list[Issue] = []

    # Classify every child: managed ones are regenerated, all others are kept as they are
    managed: list[kicad_files.LibEntry] = []
    externals: dict[str, kicad_files.LibEntry] = {}
    external_count = 0
    unclassified: list[Node] = []
    for entry in table.entries:
        if entry.name is None or entry.uri is None:
            unclassified.append(entry.node)
        elif _is_managed(entry):
            managed.append(entry)
        else:
            external_count += 1
            externals.setdefault(entry.name, entry)
    unclassified += [n for n in table.others if n.head != "version"]
    unclassified.sort(key=lambda n: n.start)
    for node in unclassified:
        issues.append(Issue(
            Severity.WARNING,
            "table.unclassified",
            f"{filename}: kept an unrecognised item at line "
            f"{_line_of(text, node.start)} as it is",
        ))

    # An external entry owns its nickname; the repo library of that name is not added
    generated = []
    for lib in selected:
        clash = externals.get(lib.nickname)
        if clash is None:
            generated.append(lib)
            continue
        issues.append(Issue(
            Severity.WARNING,
            "table.external_clash",
            f"{filename}: '{lib.nickname}' is already defined by an external entry "
            f"({clash.uri}); kept it and did not add {_MANAGED_MARKER}{lib.rel_path}",
        ))
    block = "".join(
        f"  {_entry_text(lib.nickname, f'{_MANAGED_MARKER}{lib.rel_path}')}{eol}"
        for lib in generated
    )

    scanned_paths = {lib.rel_path for lib in libs}
    generated_paths = {lib.rel_path for lib in generated}
    removed: list[str] = []
    for entry in managed:
        tail = _tail(entry)
        if tail not in scanned_paths:
            issues.append(Issue(
                Severity.WARNING,
                "table.stale_managed",
                f"{filename}: removed stale entry '{entry.name}' ({entry.uri}); "
                "that library no longer exists in the repo (the backup still has it)",
            ))
        elif tail not in generated_paths:
            removed.append(entry.name)
        elif entry.flags or entry.extras:
            settings = [*entry.flags, *(x.head for x in entry.extras)]
            issues.append(Issue(
                Severity.WARNING,
                "table.managed_flags_dropped",
                f"{filename}: '{entry.name}' was regenerated without its "
                f"{', '.join(settings)} setting(s)",
            ))

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
        edits.append(_insert_before_close(text, table.node, eol, block))

    return MergeResult(
        apply_edits(text, edits),
        external_count + len(unclassified),
        len(generated),
        removed,
        issues,
    )


def generate_sym_lib_table(libs: list[SymbolLibrary],
                           existing: LoadedFile | None = None) -> MergeResult | Issue:
    return _merge_table("sym_lib_table", existing, libs)


def generate_fp_lib_table(libs: list[FootprintLibrary],
                          existing: LoadedFile | None = None) -> MergeResult | Issue:
    return _merge_table("fp_lib_table", existing, libs)


def _next_backup_number(folder: Path) -> int:
    """One more than the highest backup number of either table, so a pair shares it."""
    pattern = re.compile(r"^(?:sym|fp)-lib-table_backup_(\d+)$")
    highest = 0
    try:
        names = os.listdir(folder)
    except OSError:
        return 1
    for name in names:
        m = pattern.match(name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def write_tables(dest_folder: Path,
                 sym_libs: list[SymbolLibrary],
                 fp_libs: list[FootprintLibrary]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        dest_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return [Issue(Severity.ERROR, "fs.write_failed",
                      f"Could not create {dest_folder}: {e.strerror or e}")]

    backup_number = _next_backup_number(dest_folder)

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

        if existing is not None and result.content == existing.source.text:
            issues.append(Issue(Severity.INFO, "table.unchanged",
                                f"{filename} is already up to date; not rewritten"))
            issues.extend(result.issues)
            continue

        if existing is not None:
            backup = fsutil.backup_file(path, path.parent, number=backup_number)
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


def _same_rel(a: str, b: str, *, fold: bool | None = None) -> bool:
    """True when two repo-relative paths name the same place.

    Slash direction and a trailing slash never matter; letter case matters only when fold is
    true. fold=None means "on Windows", where the file system ignores case (D-03).
    """
    if fold is None:
        fold = os.name == "nt"

    def norm(value: str) -> str:
        value = value.strip().replace("\\", "/").rstrip("/")
        return value.casefold() if fold else value

    return norm(a) == norm(b)


def _add_entry(tag: str, path: Path, nickname: str, rel_path: str,
               backup_number: int, issues: list[Issue], *, repo_root: Path,
               add_missing: bool = True, fold: bool | None = None) -> str:
    """Add or repoint one managed entry in one table.

    Returns "added", "listed", "updated", "skipped" or "missing" (add_missing is false and the
    table does not list the nickname).
    """
    filename = _TABLE_FILES[tag]
    lib_cls = SymbolLibrary if tag == "sym_lib_table" else FootprintLibrary
    uri = f"{_MANAGED_MARKER}{rel_path}"

    if not path.exists():
        if not add_missing:
            return "missing"
        template = _merge_table(tag, None, [lib_cls(nickname, rel_path, "", selected=True)])
        failure = fsutil.atomic_write_text(path, template.content, bom=False)
        if failure is not None:
            issues.append(failure)
            return "skipped"
        return "added"

    loaded = kicad_files.load(path)
    if isinstance(loaded, Issue):
        issues.append(loaded)
        return "skipped"
    issues.extend(loaded.source.issues)

    text = loaded.source.text
    outcome = "added"
    if not text.strip(" \t\r\n"):
        if not add_missing:
            return "missing"
        new_text = _merge_table(
            tag, None, [lib_cls(nickname, rel_path, "", selected=True)]
        ).content
    else:
        table = kicad_files.lib_table(loaded.root)
        if table is None or table.tag != tag:
            issues.append(Issue(
                Severity.ERROR,
                "table.unrecognised",
                f"Could not update {filename}: no ({tag} ...) table found; "
                "file left unchanged",
            ))
            return "skipped"
        # One outcome for all entries under this nickname, by precedence: a matching entry, then
        # a live tool-owned entry, then a hand-added entry, then a stale tool-owned entry
        same = [entry for entry in table.entries if entry.name == nickname]
        managed = [entry for entry in same if _is_managed(entry)]
        if any(_same_rel(_tail(entry), rel_path, fold=fold) for entry in managed):
            return "listed"
        live = next((entry for entry in managed if (repo_root / _tail(entry)).exists()), None)
        if live is not None:
            issues.append(Issue(
                Severity.WARNING,
                "table.path_clash",
                f"Not added to {filename}: the name {nickname} already points at "
                f"{_tail(live)}; KiCad still loads that library. Rename one of them.",
            ))
            return "skipped"
        by_hand = next((entry for entry in same if not _is_managed(entry)), None)
        if by_hand is not None:
            issues.append(Issue(
                Severity.WARNING,
                "table.external_clash",
                f"Not added to {filename}: {nickname} is already used by an entry you added "
                f"by hand ({by_hand.uri}); KiCad keeps loading that one.",
            ))
            return "skipped"
        if managed:
            # Every tool-owned entry under the name points at a library that is gone: repoint
            # the first one, changing only its URI value
            node = managed[0].value_nodes["uri"]
            new_text = apply_edits(text, [Edit(node.start, node.end, quote(uri))])
            outcome = "updated"
        elif not add_missing:
            return "missing"
        else:
            block = f"  {_entry_text(nickname, uri)}{loaded.source.eol}"
            new_text = apply_edits(
                text, [_insert_before_close(text, table.node, loaded.source.eol, block)]
            )

    backup = fsutil.backup_file(path, path.parent, number=backup_number)
    if isinstance(backup, Issue):
        issues.append(backup)
        return "skipped"
    issues.append(Issue(Severity.INFO, "table.backed_up",
                        f"Backed up {filename} -> {backup.name}"))
    failure = fsutil.atomic_write_text(path, new_text, bom=loaded.source.bom)
    if failure is not None:
        issues.append(failure)
        return "skipped"
    return outcome


def add_library_entries(dest_folder: Path, *, symbol: tuple[str, str] | None = None,
                        footprint: tuple[str, str] | None = None, repo_root: Path,
                        add_missing: bool = True, fold: bool | None = None) -> list[Issue]:
    """Add managed entries to sym-lib-table and fp-lib-table, each under its own nickname.

    symbol and footprint are (nickname, repo-relative posix path) pairs; only the ones given are
    handled. Never reorders or removes any entry, and never creates the destination folder
    (D-17). A table that already lists the nickname at that path is left alone. A tool-owned
    entry under the nickname whose target is gone from repo_root is repointed (the table is
    backed up first, only the URI changes); one whose target still exists, and any entry added
    by hand, is never edited and gives a warning. A missing table is created from the same
    template Generate uses. With add_missing false no entry is ever added or created: a table
    that does not list the nickname gives "table.not_listed" (an install into an existing library).
    """
    if not dest_folder.is_dir():
        return [Issue(Severity.ERROR, "table.dest_missing",
                      f"Destination folder does not exist: {dest_folder}")]

    issues: list[Issue] = []
    requested = [
        (tag, pair) for tag, pair in (("sym_lib_table", symbol), ("fp_lib_table", footprint))
        if pair is not None
    ]
    if not requested:
        return issues
    backup_number = _next_backup_number(dest_folder)
    outcomes: list[tuple[str, str, str, str]] = []  # (filename, nickname, outcome, rel_path)
    for tag, (nickname, rel_path) in requested:
        filename = _TABLE_FILES[tag]
        outcome = _add_entry(tag, dest_folder / filename, nickname, rel_path, backup_number, issues,
                             repo_root=repo_root, add_missing=add_missing, fold=fold)
        outcomes.append((filename, nickname, outcome, rel_path))

    if len(outcomes) == 2 and all(outcome == "added" for _, _, outcome, _ in outcomes):
        issues.append(Issue(Severity.SUCCESS, "table.entries_added",
                            f"Added {outcomes[0][1]} to sym-lib-table and {outcomes[1][1]} to fp-lib-table"))
        return issues
    for filename, nickname, outcome, rel_path in outcomes:
        if outcome == "added":
            issues.append(Issue(Severity.SUCCESS, "table.entry_added",
                                f"Added {nickname} to {filename}"))
        elif outcome == "updated":
            issues.append(Issue(Severity.SUCCESS, "table.entry_updated",
                                f"Updated: {nickname} in {filename} now points at {rel_path}"))
        elif outcome == "listed":
            issues.append(Issue(Severity.INFO, "table.already_listed",
                                f"{filename} already lists {nickname}; not changed"))
        elif outcome == "missing":
            issues.append(Issue(Severity.INFO, "table.not_listed",
                                f"{filename} does not list {nickname}"))
    return issues


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


def restore_backup_pair(folder: Path, backup_num: int) -> list[Issue]:
    """Restore both sym-lib-table and fp-lib-table for a given backup number."""
    issues: list[Issue] = []
    backup_number = _next_backup_number(folder)
    for base_name in ("sym-lib-table", "fp-lib-table"):
        backup_path = folder / f"{base_name}_backup_{backup_num}"
        if not backup_path.is_file():
            continue
        try:
            data = backup_path.read_bytes()
        except OSError as e:
            issues.append(Issue(Severity.ERROR, "fs.read_failed",
                                f"Could not read {backup_path.name}: {e.strerror or e}"))
            continue

        current_path = folder / base_name
        # Never overwrite a table without a safety copy of it
        if current_path.exists():
            safety = fsutil.backup_file(current_path, folder, number=backup_number)
            if isinstance(safety, Issue):
                issues.append(safety)
                continue
            issues.append(Issue(Severity.INFO, "table.backed_up",
                                f"Backed up current {base_name} -> {safety.name}"))

        failure = fsutil.atomic_write_bytes(current_path, data)
        if failure is not None:
            issues.append(failure)
            continue
        issues.append(Issue(Severity.SUCCESS, "table.restored",
                            f"Restored {backup_path.name} -> {base_name}"))
    return issues


@dataclass(frozen=True)
class TableInfo:
    entry_count: int
    managed: frozenset[str]  # repo-relative paths (URI tails) of managed entries


def table_info(path: Path) -> TableInfo | Issue | None:
    """Read a lib table's entry count and managed rel_paths; None when the file is absent."""
    if not path.exists():
        return None
    loaded = kicad_files.load(path)
    if isinstance(loaded, Issue):
        return loaded
    table = kicad_files.lib_table(loaded.root)
    if table is None:
        return Issue(Severity.ERROR, "table.unrecognised",
                     f"Could not read {path.name}: no lib table found")
    managed = frozenset(
        _tail(e) for e in table.entries if _is_managed(e)
    )
    return TableInfo(len(table.entries), managed)
