"""Ultra Librarian marker scoring: folder names, bundled guides and timestamped symbol files."""

import re

from ..package import Package
from .base import Detection

UL_CLAIM_POINTS = 5

_TIMESTAMP_SYMBOL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.kicad_sym$", re.IGNORECASE)
_FOLDER_MARKERS = ("kicadv6", "kicadv5")
_GUIDE_NAMES = ("importguides.html", "importguide.html")


class UltraLibrarianAdapter:
    name = "UltraLibrarian"

    def detect(self, package: Package) -> Detection | None:
        points = 0
        reasons: list[str] = []
        segments = [name.split("/") for name in package.names]
        if any(seg.casefold() in _FOLDER_MARKERS for parts in segments for seg in parts[:-1]):
            points += 4
            reasons.append("KiCADv6/KiCADv5 folder")
        if any(parts[-1].casefold() in _GUIDE_NAMES for parts in segments):
            points += 3
            reasons.append("ImportGuide(s).html")
        if any(_TIMESTAMP_SYMBOL_RE.match(parts[-1]) for parts in segments):
            points += 2
            reasons.append("timestamp-named .kicad_sym")
        if package.kind == "zip" and package.source.stem.casefold().startswith("ul_"):
            points += 1
            reasons.append("ul_ file name")
        if points < UL_CLAIM_POINTS:
            return None
        return Detection(self.name, points / 10, tuple(reasons))
