"""What changed in Custom/ since its last commit, by content and not by formatting (D-21).

Read-only: it runs rev-parse, status and cat-file through gitops and never stages, commits, switches or
resets. Only files the scan already found under Custom/ are read, so git output never names an arbitrary
file to open. Qt-free.
"""

import os
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from . import gitops, kicad_files, sexpr
from .importer.package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES
from .models import (
    STATUS_CHANGED,
    STATUS_NEW,
    ChangedFootprint,
    FootprintLibrary,
    Issue,
    Severity,
    SymbolEntry,
    SymbolLibrary,
)

_CUSTOM = "Custom"
_CUSTOM_PREFIX = f"{_CUSTOM}/"
_SKIPPED = "Change highlight skipped"


def _same_dir(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _read_current(path: Path) -> tuple[sexpr.Node | None, str | None]:
    """Return (parsed root, None) for a work-tree file, or (None, why it could not be compared)."""
    try:
        if path.stat().st_size > MAX_KICAD_TEXT_BYTES:
            return None, "the file is too large to compare"
        data = path.read_bytes()
    except OSError as e:
        return None, f"the file could not be read ({e.strerror or e})"
    loaded = kicad_files.parse_bytes(data, path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return None, loaded.text
    return loaded.root, None


def _read_head(ctx: gitops.GitContext, custom_dir: Path, rel: str) -> tuple[bool, sexpr.Node | None]:
    """Return (HEAD holds the file, its parsed root); the root is None when that version cannot be parsed."""
    data = gitops.head_blob(ctx, custom_dir, rel)
    if data is None:
        return False, None
    if len(data) > MAX_KICAD_TEXT_BYTES:
        return True, None
    loaded = kicad_files.parse_bytes(data, PurePosixPath(rel).name, max_nodes=MAX_KICAD_TEXT_NODES)
    return True, None if isinstance(loaded, Issue) else loaded.root


def _info(code: str, text: str) -> Issue:
    return Issue(Severity.INFO, code, text)


def _skipped_for(path: Path, reason: str) -> Issue:
    return _info("scan.changes_skipped", f"{_SKIPPED} for {path.name}: {reason}")


def _head_symbols(root: sexpr.Node) -> dict[str, tuple]:
    """Token stream of each top-level symbol by name; the first of a repeated name wins."""
    found: dict[str, tuple] = {}
    for ref in kicad_files.find_symbols(root):
        found.setdefault(ref.name, sexpr.token_stream(ref.node))
    return found


def _mark_symbols(
    ctx: gitops.GitContext, custom_dir: Path, lib: SymbolLibrary, rel: str
) -> list[Issue]:
    path = custom_dir / rel
    if not path.is_file():
        return []  # deleted since the last commit: there is no row for something that is gone
    root, reason = _read_current(path)
    if root is None:
        return [_skipped_for(path, reason)]
    in_head, head_root = _read_head(ctx, custom_dir, rel)
    if not in_head:
        before: dict[str, tuple] | None = {}  # a new file: every symbol is new
    elif head_root is None:
        before = None  # HEAD's version cannot be compared: every symbol counts as changed
    else:
        before = _head_symbols(head_root)

    issues: list[Issue] = []
    seen: set[str] = set()
    for ref in kicad_files.find_symbols(root):
        if ref.name in seen:
            continue
        seen.add(ref.name)
        if before is None:
            status = STATUS_CHANGED
        elif ref.name not in before:
            status = STATUS_NEW
        elif before[ref.name] != sexpr.token_stream(ref.node):
            status = STATUS_CHANGED
        else:
            continue
        entry = next((e for e in lib.symbols if e.name == ref.name), None)
        if entry is None:
            # A library without the Atomic_ prefix has no entries yet: it gets only the changed ones
            entry = SymbolEntry(ref.name, extends=kicad_files.extends_name(ref.node))
            lib.symbols.append(entry)
        entry.status = status
        code = "scan.symbol_new" if status == STATUS_NEW else "scan.symbol_changed"
        issues.append(_info(code, f"Symbol {lib.nickname} / {ref.name}: {status} since the last Custom commit"))
    return issues


def mark_changes(
    repo_root: Path,
    sym_libs: list[SymbolLibrary],
    fp_libs: list[FootprintLibrary],
    *,
    which: Callable[[str], str | None] | None = None,
) -> list[Issue]:
    """Mark the symbols of Custom/ libraries that are new or changed since Custom's last commit.

    Symbols get a status on their SymbolEntry (appended for libraries the atomic check did not list).
    Nothing outside Custom/ is ever marked. Returns the INFO lines for the log.
    """
    if not any(lib.source == _CUSTOM for lib in sym_libs) and not any(lib.source == _CUSTOM for lib in fp_libs):
        return []
    found = gitops.find_git(repo_root, which=which)
    if isinstance(found, Issue):
        return []
    ctx = gitops.GitContext(found)
    custom_dir = Path(repo_root) / _CUSTOM
    top = gitops.show_toplevel(ctx, custom_dir)
    if top is None or not _same_dir(top, custom_dir):
        return []
    paths = gitops.status_entries(ctx, custom_dir)
    if isinstance(paths, Issue):
        return []

    changed_syms = {_CUSTOM_PREFIX + p: p for p in paths if p.endswith(".kicad_sym")}
    issues: list[Issue] = []
    for lib in sym_libs:
        if lib.source == _CUSTOM and lib.rel_path in changed_syms:
            issues.extend(_mark_symbols(ctx, custom_dir, lib, changed_syms[lib.rel_path]))
    return issues
