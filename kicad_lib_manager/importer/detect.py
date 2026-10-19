"""Adapter registry and vendor detection; later vendors are appended to ADAPTERS, callers never change."""

from dataclasses import replace

from ..models import Issue, Severity
from .adapters.base import GENERIC_CONFIDENCE, GENERIC_VENDOR, Adapter, Detection, locate
from .adapters.loose import LooseAdapter
from .adapters.ultralibrarian import UltraLibrarianAdapter
from .candidate import ImportCandidate
from .package import Package

ADAPTERS: list[Adapter] = [UltraLibrarianAdapter(), LooseAdapter()]


def detect_candidate(package: Package) -> tuple[ImportCandidate | None, list[Issue]]:
    """Pick the best-scoring adapter (registry order breaks ties) and locate the package contents."""
    if package.refused:
        return None, []
    best: Detection | None = None
    for adapter in ADAPTERS:
        found = adapter.detect(package)
        if found is not None and (best is None or found.confidence > best.confidence):
            best = found
    generic = best is None
    if best is None:
        best = Detection(GENERIC_VENDOR, GENERIC_CONFIDENCE, ("no vendor markers",))
    candidate, issues = locate(package, best)
    if generic and package.kind == "zip" and candidate is not None:
        # D-09: an unrecognised zip is read as a generic KiCad package, and the user is told
        note = Issue(
            Severity.INFO,
            "intake.unknown_vendor",
            f"Vendor of {package.source.name} not recognised; reading it as a generic KiCad package "
            "(no vendor-specific fixes applied)",
        )
        issues = [note, *issues]
        candidate = replace(candidate, issues=(note, *candidate.issues))
    return candidate, issues
