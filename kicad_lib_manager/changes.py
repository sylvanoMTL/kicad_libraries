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


def _skip(reason: str) -> Issue:
    """The one line a scan logs when the highlight cannot run at all (the first line of a git message only)."""
    return _info("scan.changes_skipped", f"{_SKIPPED}: {reason.splitlines()[0] if reason else 'unknown reason'}")


def _skipped_for(path: Path, reason: str) -> Issue:
    return _info("scan.changes_skipped", f"{_SKIPPED} for {path.name}: {reason}")


def _head_symbols(root: sexpr.Node) -> dict[str, tuple]:
    """Token stream of each top-level symbol by name; the first of a repeated name wins."""
    found: dict[str, tuple] = {}
    for ref in kicad_files.find_symbols(root):
        found.setdefault(ref.name, sexpr.token_stream(ref.node))
    return found


def symbol_changes(ctx: gitops.GitContext, custom_dir: Path, rel: str, root: sexpr.Node) -> dict[str, str]:
    """The new or changed symbols of a work-tree library against HEAD, {name: status} in file order (Phase 9 D-21).

    A file HEAD lacks has every symbol new; a HEAD copy that does not parse makes every symbol changed;
    otherwise only a symbol whose token stream differs (or is absent from HEAD) is listed. The first of a
    repeated name wins.
    """
    in_head, head_root = _read_head(ctx, custom_dir, rel)
    if not in_head:
        before: dict[str, tuple] | None = {}  # a new file: every symbol is new
    elif head_root is None:
        before = None  # HEAD's version cannot be compared: every symbol counts as changed
    else:
        before = _head_symbols(head_root)

    found: dict[str, str] = {}
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
        found[ref.name] = status
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

    issues: list[Issue] = []
    refs = {ref.name: ref for ref in reversed(kicad_files.find_symbols(root))}  # the first of a repeated name
    for name, status in symbol_changes(ctx, custom_dir, rel, root).items():
        entry = next((e for e in lib.symbols if e.name == name), None)
        if entry is None:
            # A library without the Atomic_ prefix has no entries yet: it gets only the changed ones
            entry = SymbolEntry(name, extends=kicad_files.extends_name(refs[name].node))
            lib.symbols.append(entry)
        entry.status = status
        code = "scan.symbol_new" if status == STATUS_NEW else "scan.symbol_changed"
        issues.append(_info(code, f"Symbol {lib.nickname} / {name}: {status} since the last Custom commit"))
    return issues


def _mark_footprints(
    ctx: gitops.GitContext, custom_dir: Path, lib: FootprintLibrary, rels: list[str]
) -> list[Issue]:
    issues: list[Issue] = []
    found: list[ChangedFootprint] = []
    for rel in rels:
        path = custom_dir / rel
        if not path.is_file():
            continue
        root, reason = _read_current(path)
        if root is None:
            issues.append(_skipped_for(path, reason))
            continue
        in_head, head_root = _read_head(ctx, custom_dir, rel)
        if not in_head:
            status = STATUS_NEW
        elif head_root is None or sexpr.token_stream(head_root) != sexpr.token_stream(root):
            status = STATUS_CHANGED
        else:
            continue
        found.append(ChangedFootprint(PurePosixPath(rel).stem, status))
    found.sort(key=lambda item: (item.name.casefold(), item.name))
    lib.changed.extend(found)
    lib.changed.sort(key=lambda item: (item.name.casefold(), item.name))
    for item in found:
        code = "scan.footprint_new" if item.status == STATUS_NEW else "scan.footprint_changed"
        issues.append(_info(code, f"Footprint {lib.nickname} / {item.name}: {item.status} since the last Custom commit"))
    return issues


def mark_changes(
    repo_root: Path,
    sym_libs: list[SymbolLibrary],
    fp_libs: list[FootprintLibrary],
    *,
    which: Callable[[str], str | None] | None = None,
) -> list[Issue]:
    """Mark the symbols and footprints of Custom/ libraries that are new or changed since Custom's last commit.

    Symbols get a status on their SymbolEntry (appended for libraries the atomic check did not list);
    footprints are added to FootprintLibrary.changed, sorted by name. Nothing outside Custom/ is ever
    marked. Returns the INFO lines for the log, and one skip line when git cannot be used.
    """
    if not any(lib.source == _CUSTOM for lib in sym_libs) and not any(lib.source == _CUSTOM for lib in fp_libs):
        return []
    found = gitops.find_git(repo_root, which=which)
    if isinstance(found, Issue):
        return [_skip(found.text)]
    ctx = gitops.GitContext(found)
    custom_dir = Path(repo_root) / _CUSTOM
    top = gitops.show_toplevel(ctx, custom_dir)
    if top is None or not _same_dir(top, custom_dir):
        return [_skip("Custom is not a git checkout")]
    paths = gitops.status_entries(ctx, custom_dir)
    if isinstance(paths, Issue):
        return [_skip(paths.text)]

    changed_syms = {_CUSTOM_PREFIX + p: p for p in paths if p.endswith(".kicad_sym")}
    changed_mods: dict[str, list[str]] = {}
    for p in paths:
        if p.endswith(".kicad_mod"):
            changed_mods.setdefault(_CUSTOM_PREFIX + p.rpartition("/")[0], []).append(p)

    issues: list[Issue] = []
    for lib in sym_libs:
        if lib.source == _CUSTOM and lib.rel_path in changed_syms:
            issues.extend(_mark_symbols(ctx, custom_dir, lib, changed_syms[lib.rel_path]))
    for fp_lib in fp_libs:
        if fp_lib.source == _CUSTOM and fp_lib.rel_path in changed_mods:
            issues.extend(_mark_footprints(ctx, custom_dir, fp_lib, changed_mods[fp_lib.rel_path]))
    return issues
