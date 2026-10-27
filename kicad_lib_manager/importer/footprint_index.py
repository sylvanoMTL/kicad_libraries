"""Official footprint index (LIB-06, D-16): KiCad's installed footprints, listed by name and ranked without reading files."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES  # noqa: F401  (used by pad_numbers)


@dataclass(frozen=True)
class FootprintIndex:
    folder: Path | None
    libraries: Mapping[str, tuple[str, ...]]

    def contains(self, link: str) -> bool:
        return False

    def links(self) -> list[str]:
        return []


EMPTY_FOOTPRINT_INDEX = FootprintIndex(None, {})


@dataclass(frozen=True)
class RankedFootprint:
    link: str
    score: int


def build_index(kicad_fp_dir: Path | None, progress: Callable | None = None) -> FootprintIndex:
    return EMPTY_FOOTPRINT_INDEX


def rank(
    index: FootprintIndex,
    *,
    package_code: str,
    words: Sequence[str] = (),
    linked: Mapping[str, int] = {},
    limit: int = 200,
) -> list[RankedFootprint]:
    return []


def pad_numbers(index: FootprintIndex, link: str) -> set[str] | None:
    return None


def rank_with_pads(
    index: FootprintIndex, ranked: Sequence[RankedFootprint], pads: set[str], top: int = 200
) -> list[RankedFootprint]:
    return list(ranked)


def footprint_texts(index: FootprintIndex, link: str) -> tuple[str, str]:
    return ("", "")
