"""Adapter registry and vendor detection; later vendors are appended to ADAPTERS, callers never change."""

from ..models import Issue
from .adapters.base import GENERIC_CONFIDENCE, GENERIC_VENDOR, Adapter, Detection, locate
from .adapters.ultralibrarian import UltraLibrarianAdapter
from .candidate import ImportCandidate
from .package import Package

ADAPTERS: list[Adapter] = [UltraLibrarianAdapter()]


def detect_candidate(package: Package) -> tuple[ImportCandidate | None, list[Issue]]:
    """Pick the best-scoring adapter (registry order breaks ties) and locate the package contents."""
    if package.refused:
        return None, []
    best: Detection | None = None
    for adapter in ADAPTERS:
        found = adapter.detect(package)
        if found is not None and (best is None or found.confidence > best.confidence):
            best = found
    if best is None:
        best = Detection(GENERIC_VENDOR, GENERIC_CONFIDENCE, ("no vendor markers",))
    return locate(package, best)
