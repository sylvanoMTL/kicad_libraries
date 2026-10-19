"""Name sanitising for library, symbol, footprint and 3D-model names."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..models import Issue

MAX_NAME_LEN = 64
PLACEHOLDER_NAME = "Unnamed"
RESERVED_NAMES = frozenset()
KNOWN_EXTENSIONS = (".kicad_sym", ".kicad_mod", ".step", ".stp", ".wrl")


@dataclass(frozen=True)
class NameResult:
    original: str
    sanitized: str
    issues: tuple[Issue, ...]

    @property
    def changed(self) -> bool:
        return self.original != self.sanitized


def sanitize_name(name: str, *, max_len: int | None = None) -> NameResult:
    """Sanitise a library, symbol, footprint or model name (stub)."""
    return NameResult(name, name, ())


def sanitize_filename(filename: str, *, extensions: Sequence[str] | None = None) -> NameResult:
    """Sanitise a file name's stem (stub)."""
    return NameResult(filename, filename, ())


def case_clash(name: str, existing: Iterable[str]) -> list[Issue]:
    """Report existing names that differ from name only by letter case (stub)."""
    return []
