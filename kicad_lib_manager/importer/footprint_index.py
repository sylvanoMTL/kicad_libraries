"""Official footprint index (LIB-06, D-16): KiCad's installed footprints, listed by name and ranked without reading files.

A leaf module of the importer: no Qt. Only KiCad's own footprints folder is listed, never a library of
the repo (D-16). Ranking needs file names only; pad numbers are read lazily for a short list, because
a full pad scan of KiCad's footprints takes minutes. A footprint link is accepted only when both of its
halves are exact-case names from the folder listing, so typed text never forms a path (T-10-06).
"""

import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..kicad_files import footprint_name, parse_bytes, unquote
from ..models import Issue
from .package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES
from .verify import footprint_pad_numbers

_PRETTY_SUFFIX = ".pretty"
_FOOTPRINT_SUFFIX = ".kicad_mod"
_TOKEN_SPLIT_RE = re.compile(r"[_\-. ]+")
_LEADING_LETTERS_RE = re.compile(r"[A-Za-z]+")

_MIN_LEADING_LETTERS = 3
_SCORE_LINKED = 100
_SCORE_FULL_CODE = 50
_SCORE_LEADING_LETTERS = 30
_SCORE_WORD = 5
_SCORE_PAD_COUNT = 20
_SCORE_PAD_NUMBERS = 20
# A top score below this means the match rests on the code's leading letters alone
FULL_CODE_SCORE = _SCORE_FULL_CODE
DEFAULT_LIMIT = 200


@dataclass(frozen=True)
class FootprintIndex:
    """The footprint names of KiCad's installed folder: library name -> footprint names, exact case."""

    folder: Path | None
    libraries: Mapping[str, tuple[str, ...]]
    _names: dict[str, frozenset[str]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_names", {lib: frozenset(names) for lib, names in self.libraries.items()})

    def contains(self, link: str) -> bool:
        """True when link is Lib:FP with both halves spelled exactly as the folder lists them."""
        library, separator, name = link.partition(":")
        return bool(separator) and name in self._names.get(library, frozenset())

    def links(self) -> list[str]:
        """Every Lib:FP link of the folder."""
        return [f"{library}:{name}" for library, names in self.libraries.items() for name in names]


EMPTY_FOOTPRINT_INDEX = FootprintIndex(None, {})

# Resolved folder -> (state, index); one entry per folder, replaced when the folder changes
_INDEX_CACHE: dict[Path, tuple[tuple[int, int], FootprintIndex]] = {}
# (resolved folder, link) -> what one read of the footprint file gave; None for an unreadable file
_FACTS_CACHE: dict[tuple[Path, str], "_Facts | None"] = {}


@dataclass(frozen=True)
class RankedFootprint:
    """One footprint link with its score; the higher, the closer to the vendor package."""

    link: str
    score: int


@dataclass(frozen=True)
class _Facts:
    pads: frozenset[str]
    descr: str
    tags: str


def _listing(folder: Path) -> list[os.DirEntry] | None:
    try:
        with os.scandir(folder) as entries:
            return [entry for entry in entries if entry.name.casefold().endswith(_PRETTY_SUFFIX) and entry.is_dir()]
    except OSError:
        return None


def _state(folder: Path, libraries: list[os.DirEntry]) -> tuple[int, int]:
    """(number of .pretty folders, newest modification time in ns of the folder and each .pretty)."""
    newest = 0
    try:
        newest = folder.stat().st_mtime_ns
        for entry in libraries:
            # os.stat, not DirEntry.stat: on NTFS a directory listing can carry a stale modification time
            newest = max(newest, os.stat(entry.path).st_mtime_ns)
    except OSError:
        pass
    return len(libraries), newest


def build_index(kicad_fp_dir: Path | None, progress: Callable | None = None) -> FootprintIndex:
    """List KiCad's installed footprints by file name only, cached per folder state.

    progress(message, current, total) is called once per library folder.
    """
    if kicad_fp_dir is None or not kicad_fp_dir.is_dir():
        return EMPTY_FOOTPRINT_INDEX
    libraries = _listing(kicad_fp_dir)
    if libraries is None:
        return EMPTY_FOOTPRINT_INDEX
    key = kicad_fp_dir.resolve()
    state = _state(kicad_fp_dir, libraries)
    cached = _INDEX_CACHE.get(key)
    if cached is not None and cached[0] == state:
        return cached[1]
    found: dict[str, tuple[str, ...]] = {}
    for number, entry in enumerate(sorted(libraries, key=lambda e: e.name), start=1):
        library = entry.name[: -len(_PRETTY_SUFFIX)]
        if progress is not None:
            progress(f"Listing footprints {library}", number, len(libraries))
        try:
            names = os.listdir(entry.path)
        except OSError:
            continue
        found[library] = tuple(
            sorted(n[: -len(_FOOTPRINT_SUFFIX)] for n in names if n.casefold().endswith(_FOOTPRINT_SUFFIX))
        )
    index = FootprintIndex(kicad_fp_dir, found)
    for stale in [k for k in _FACTS_CACHE if k[0] == key]:
        del _FACTS_CACHE[stale]
    _INDEX_CACHE[key] = (state, index)
    return index


def _tokens(name: str) -> set[str]:
    return {token for token in _TOKEN_SPLIT_RE.split(name.casefold()) if token}


def rank(
    index: FootprintIndex,
    *,
    package_code: str,
    words: Sequence[str] = (),
    linked: Mapping[str, int] = {},
    limit: int | None = DEFAULT_LIMIT,
) -> list[RankedFootprint]:
    """Score every footprint name against the vendor package code; best first, score 0 dropped.

    100 per sibling symbol linking it, 50 when the full code is inside the name, 30 when the code's
    leading letters (3 or more) are a whole word of the name, 5 per family word that is a whole word.
    A limit of None returns every scored footprint.
    """
    code = package_code.strip().casefold()
    lead = _LEADING_LETTERS_RE.match(package_code.strip())
    letters = lead.group().casefold() if lead and len(lead.group()) >= _MIN_LEADING_LETTERS else ""
    wanted = {word.casefold() for word in words if word}
    ranked = []
    for library, names in index.libraries.items():
        for name in names:
            link = f"{library}:{name}"
            tokens = _tokens(name)
            score = _SCORE_LINKED * linked.get(link, 0)
            if code and code in name.casefold():
                score += _SCORE_FULL_CODE
            if letters and letters in tokens:
                score += _SCORE_LEADING_LETTERS
            score += _SCORE_WORD * len(wanted & tokens)
            if score > 0:
                ranked.append(RankedFootprint(link, score))
    ranked.sort(key=lambda item: (-item.score, item.link.casefold()))
    return ranked[:limit]


def _read_facts(index: FootprintIndex, link: str) -> _Facts | None:
    """Read one footprint once: its pad numbers, description and tags; None when it is not in the index or unreadable."""
    if index.folder is None or not index.contains(link):
        return None
    key = (index.folder.resolve(), link)
    if key in _FACTS_CACHE:
        return _FACTS_CACHE[key]
    library, _, name = link.partition(":")
    path = index.folder / f"{library}{_PRETTY_SUFFIX}" / f"{name}{_FOOTPRINT_SUFFIX}"
    facts = None
    try:
        if path.stat().st_size <= MAX_KICAD_TEXT_BYTES:
            loaded = parse_bytes(path.read_bytes(), path.name, max_nodes=MAX_KICAD_TEXT_NODES)
            ref = None if isinstance(loaded, Issue) else footprint_name(loaded.root)
            if ref is not None:
                texts = {"descr": "", "tags": ""}
                for child in ref.node.children:
                    if child.head in texts and len(child.children) >= 2:
                        texts[child.head] = unquote(child.children[1].text)
                facts = _Facts(frozenset(footprint_pad_numbers(ref.node)), texts["descr"], texts["tags"])
    except OSError:
        facts = None
    _FACTS_CACHE[key] = facts
    return facts


def pad_numbers(index: FootprintIndex, link: str) -> set[str] | None:
    """The pad numbers of a footprint of the index; None when the link is not listed or the file is unreadable."""
    facts = _read_facts(index, link)
    return None if facts is None else set(facts.pads)


def footprint_texts(index: FootprintIndex, link: str) -> tuple[str, str]:
    """The footprint's (description, tags); empty strings when absent or unreadable."""
    facts = _read_facts(index, link)
    return ("", "") if facts is None else (facts.descr, facts.tags)


def rank_with_pads(
    index: FootprintIndex, ranked: Sequence[RankedFootprint], pads: set[str], top: int = DEFAULT_LIMIT
) -> list[RankedFootprint]:
    """Raise links whose pads fit: 20 for the same number of pads, 20 more for the same pad numbers.

    Pads are read only for the first top entries; the rest keep their name score.
    """
    if not pads:
        return list(ranked)
    result = []
    for position, item in enumerate(ranked):
        score = item.score
        found = pad_numbers(index, item.link) if position < top else None
        if found is not None:
            if len(found) == len(pads):
                score += _SCORE_PAD_COUNT
            if found == pads:
                score += _SCORE_PAD_NUMBERS
        result.append(RankedFootprint(item.link, score))
    result.sort(key=lambda item: -item.score)
    return result
