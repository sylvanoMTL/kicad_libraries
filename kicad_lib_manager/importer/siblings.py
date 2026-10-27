"""Sibling symbols of a part number: the family-prefix vote that suggests an Atomic_ library (LIB-04, D-01 to D-03).

A leaf module of the importer: no Qt, and it never parses a KiCad library. The names of the top-level
symbols are read with a byte regex, because parsing KiCad's stock symbols costs about a minute; the
result is a small index of (library, name, Footprint field) entries that the vote counts over.
"""

import os
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .stems import ATOMIC_PREFIX, EXCLUDED_STEMS, name_verdict

_SYMBOL_SUFFIX = ".kicad_sym"
# A stock library is far smaller than this; a bigger file is not a symbol library worth reading
_MAX_LIBRARY_BYTES = 64 * 1024 * 1024
_EXCLUDED_FOLD = frozenset(stem.casefold() for stem in EXCLUDED_STEMS)

# A top-level symbol: one tab or one to two spaces of indent, or right after a one-line library header.
# Unit sub-symbols such as NAME_1_1 sit one level deeper and never match (RESEARCH Pitfall 1).
_TOP_SYMBOL_RE = re.compile(
    rb'(?:^(?:\t| {1,2})|\(kicad_symbol_lib\b[^\n]*?[ \t)])\(symbol "([^"]+)"',
    re.MULTILINE,
)
_FOOTPRINT_FIELD_RE = re.compile(rb'\(property\s+"Footprint"\s+"((?:[^"\\]|\\.)*)"')

_MIN_LETTERS = 3


@dataclass(frozen=True)
class SiblingEntry:
    """One top-level symbol of one library: the KiCad stem it lives in, its name and its Footprint field."""

    library: str
    name: str
    footprint: str


@dataclass(frozen=True)
class SiblingIndex:
    """Every top-level symbol of a set of libraries."""

    entries: tuple[SiblingEntry, ...]

    def matches(self, prefix: str) -> list[SiblingEntry]:
        """The entries whose symbol name starts with prefix, ignoring letter case."""
        wanted = prefix.casefold()
        return [entry for entry in self.entries if entry.name.casefold().startswith(wanted)]


EMPTY_INDEX = SiblingIndex(())


@dataclass(frozen=True)
class SiblingPick:
    """The outcome of the vote: the winning KiCad stem (None when there is none), the prefix step that
    found siblings, and the per-stem counts kept as alternatives, largest first."""

    stem: str | None
    prefix: str
    counts: tuple[tuple[str, int], ...]


def family_prefixes(part_number: str) -> list[str]:
    """The leading letters plus the first digit run, then the letters plus the first digit, then the letters.

    CSD85301Q2 gives CSD85301, CSD8, CSD. Nothing comes back for fewer than 3 leading letters, so a
    part such as RS3-1212S/H3 or LM7805 never looks up siblings.
    """
    found = re.match(r"([A-Za-z]+)(\d+)?", part_number)
    if not found or len(found.group(1)) < _MIN_LETTERS:
        return []
    letters, digits = found.group(1), found.group(2) or ""
    steps = []
    if digits:
        steps.append(letters + digits)
        if len(digits) > 1:
            steps.append(letters + digits[0])
    steps.append(letters)
    return list(dict.fromkeys(steps))


def read_library(data: bytes) -> list[tuple[str, str]]:
    """Each top-level symbol name of a .kicad_sym with the first Footprint field inside its block."""
    found = list(_TOP_SYMBOL_RE.finditer(data))
    symbols = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(data)
        field = _FOOTPRINT_FIELD_RE.search(data, match.end(), end)
        footprint = field.group(1).decode("utf-8", "replace") if field else ""
        symbols.append((match.group(1).decode("utf-8", "replace"), footprint))
    return symbols


def _library_files(symbols_dir: Path) -> list[str]:
    """The .kicad_sym file names of a folder; an unlistable folder gives none."""
    try:
        names = os.listdir(symbols_dir)
    except OSError:
        return []
    return sorted(name for name in names if name.casefold().endswith(_SYMBOL_SUFFIX))


def _read_entries(symbols_dir: Path, file_name: str, library: str) -> list[SiblingEntry]:
    path = symbols_dir / file_name
    try:
        if path.stat().st_size > _MAX_LIBRARY_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    return [SiblingEntry(library, name, footprint) for name, footprint in read_library(data)]


def _folder_state(symbols_dir: Path, files: list[str]) -> tuple[int, int]:
    """(number of library files, newest modification time in ns of the folder and its libraries)."""
    newest = 0
    try:
        newest = symbols_dir.stat().st_mtime_ns
        for name in files:
            newest = max(newest, (symbols_dir / name).stat().st_mtime_ns)
    except OSError:
        pass
    return len(files), newest


# Resolved folder -> (state, index); one entry per folder, replaced when the folder changes
_STOCK_CACHE: dict[Path, tuple[tuple[int, int], SiblingIndex]] = {}


def stock_index(symbols_dir: Path | None, progress: Callable | None = None) -> SiblingIndex:
    """Index KiCad's installed symbol libraries, leaving out the libraries that hold no parts (D-10).

    The result is cached per folder and reused while the number of library files and the newest
    modification time stay the same; progress(message, current, total) is called once per file.
    """
    if symbols_dir is None or not symbols_dir.is_dir():
        return EMPTY_INDEX
    files = _library_files(symbols_dir)
    key = symbols_dir.resolve()
    state = _folder_state(symbols_dir, files)
    cached = _STOCK_CACHE.get(key)
    if cached is not None and cached[0] == state:
        return cached[1]
    entries: list[SiblingEntry] = []
    for number, file_name in enumerate(files, start=1):
        stem = file_name[: -len(_SYMBOL_SUFFIX)]
        if progress is not None:
            progress(f"Reading symbols {stem}", number, len(files))
        if stem.casefold() in _EXCLUDED_FOLD:
            continue
        entries.extend(_read_entries(symbols_dir, file_name, stem))
    index = SiblingIndex(tuple(entries))
    _STOCK_CACHE[key] = (state, index)
    return index


def own_index(symbols_dir: Path, allowed: frozenset[str] | None = None) -> SiblingIndex:
    """Index the owner's Atomic_ libraries, keyed by the KiCad stem after Atomic_ (D-01, D-13).

    Only a library whose name passes the name rule counts: v1 names and hand-made Atomic_ libraries
    are ignored. Read fresh on every call, because the owner's folder changes while the dialog is open.
    """
    entries: list[SiblingEntry] = []
    for file_name in _library_files(symbols_dir):
        stem = file_name[: -len(_SYMBOL_SUFFIX)]
        if not name_verdict(stem, allowed).ok:
            continue
        entries.extend(_read_entries(symbols_dir, file_name, stem[len(ATOMIC_PREFIX) :]))
    return SiblingIndex(tuple(entries))


def pick(index: SiblingIndex, part_number: str) -> SiblingPick:
    """Vote the part's family into a library: the first prefix step with any sibling decides.

    The library holding more than half of those siblings wins; otherwise there is no suggestion and
    the counts stay as alternatives (D-03, a split family falls through to the category map).
    """
    for prefix in family_prefixes(part_number):
        found = index.matches(prefix)
        if not found:
            continue
        votes = Counter(entry.library for entry in found)
        counts = tuple(sorted(votes.items(), key=lambda item: (-item[1], item[0])))
        stem, top = counts[0]
        return SiblingPick(stem if top * 2 > len(found) else None, prefix, counts)
    return SiblingPick(None, "", ())
