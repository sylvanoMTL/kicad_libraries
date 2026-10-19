"""Name sanitising for library, symbol, footprint and 3D-model names."""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..models import Issue, Severity

MAX_NAME_LEN = 64
PLACEHOLDER_NAME = "Unnamed"
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)
KNOWN_EXTENSIONS = (".kicad_sym", ".kicad_mod", ".step", ".stp", ".wrl")

# Characters NFKD does not turn into plain ASCII; applied before and after NFKD.
_TRANSLIT = {
    ord("µ"): "u",  # micro sign
    ord("μ"): "u",  # Greek small mu
    ord("Ω"): "Ohm",  # Ohm sign
    ord("Ω"): "Ohm",  # Greek capital omega
    ord("°"): "deg",  # degree sign
    ord("Ø"): "O",
    ord("ø"): "o",
    ord("ß"): "ss",
    ord("æ"): "ae",
    ord("Æ"): "AE",
}
_BAD = re.compile(r"[^A-Za-z0-9_.\-]")
_UNDERSCORES = re.compile(r"_+")
_STRIP = "_. "


@dataclass(frozen=True)
class NameResult:
    original: str
    sanitized: str
    issues: tuple[Issue, ...]

    @property
    def changed(self) -> bool:
        return self.original != self.sanitized


def _clean(text: str) -> str:
    """Transliterate, fold to ASCII and reduce to one safe path component."""
    text = text.translate(_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text.translate(_TRANSLIT) if not unicodedata.combining(c))
    text = _BAD.sub("_", text)
    text = _UNDERSCORES.sub("_", text)
    return text.strip(_STRIP)


def sanitize_name(name: str, *, max_len: int | None = None) -> NameResult:
    """Sanitise a library, symbol, footprint or model name; report every change."""
    limit = MAX_NAME_LEN if max_len is None else max_len
    issues: list[Issue] = []
    result = _clean(name)
    if len(result) > limit:
        result = result[:limit].strip(_STRIP)
        issues.append(
            Issue(Severity.WARNING, "naming.truncated", f"Name {name!r} was cut to {limit} characters")
        )
    head, dot, rest = result.partition(".")
    if head.upper() in RESERVED_NAMES:
        renamed = head + "_" + dot + rest
        if len(renamed) > limit:
            renamed = renamed[:limit].strip(_STRIP)
        issues.append(
            Issue(
                Severity.WARNING,
                "naming.reserved",
                f"{head!r} is a reserved Windows device name; renamed to {renamed!r}",
            )
        )
        result = renamed
    if not result:
        result = PLACEHOLDER_NAME
        issues.append(
            Issue(
                Severity.ERROR,
                "naming.empty",
                f"Name {name!r} has no usable characters; it was replaced with 'Unnamed' "
                "and must be edited before installing",
            )
        )
    if result != name:
        issues.append(Issue(Severity.INFO, "naming.changed", f"{name!r} -> {result!r}"))
    return NameResult(name, result, tuple(issues))


def sanitize_filename(filename: str, *, extensions: Sequence[str] | None = None) -> NameResult:
    """Sanitise a file name's stem (stub)."""
    return NameResult(filename, filename, ())


def case_clash(name: str, existing: Iterable[str]) -> list[Issue]:
    """Report existing names that differ from name only by letter case (stub)."""
    return []
