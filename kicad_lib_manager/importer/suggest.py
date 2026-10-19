"""Library-name suggestion skeleton (RED stub: signatures only, behavior follows in the GREEN commit)."""

from collections.abc import Sequence
from dataclasses import dataclass

from ..models import Issue
from .candidate import ExistingLibrary, PartMeta


@dataclass(frozen=True)
class TokenChoice:
    token: str
    source: str
    confident: bool


@dataclass(frozen=True)
class LibrarySuggestion:
    name: str
    type: TokenChoice
    subcategory: TokenChoice
    manufacturer: TokenChoice
    confidence: str
    placeholders: tuple[str, ...]
    matches_existing: bool
    alternatives: tuple
    issues: tuple[Issue, ...]


def placeholder_tokens(name: str) -> list[str]:
    return []


def suggest_library(meta: PartMeta, existing: Sequence[ExistingLibrary] = ()) -> LibrarySuggestion:
    empty = TokenChoice("", "placeholder", False)
    return LibrarySuggestion("", empty, empty, empty, "low", (), False, (), ())
