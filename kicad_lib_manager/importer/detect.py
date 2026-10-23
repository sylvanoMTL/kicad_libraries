"""Adapter registry and vendor detection; later vendors are appended to ADAPTERS, callers never change."""

from dataclasses import replace

from ..models import Issue, Severity
from .adapters.base import GENERIC_CONFIDENCE, GENERIC_VENDOR, Adapter, Detection, locate
from .adapters.loose import LooseAdapter
from .adapters.samacsys import SamacSysAdapter
from .adapters.snapeda import SnapEDAAdapter
from .adapters.ultralibrarian import UltraLibrarianAdapter
from .candidate import ImportCandidate
from .package import Package

# Vendors come before Loose so a vendor folder beats Loose's low score; ties go to registry order
ADAPTERS: list[Adapter] = [UltraLibrarianAdapter(), SnapEDAAdapter(), SamacSysAdapter(), LooseAdapter()]

_IGNORED_CODE = "intake.ignored_members"


def detect_candidate(package: Package) -> tuple[ImportCandidate | None, list[Issue]]:
    """Pick the best-scoring adapter (registry order breaks ties) and locate the package contents.

    candidate.issues holds the package's own Issues first, then the unknown-vendor note when it
    applies, then the locate Issues, then the winning adapter's notes, each exactly once (WR-03).
    The returned list is the detection Issues only and excludes package.issues, so a caller showing
    both never repeats one.

    When the winning Detection carries an ignored_note, it replaces the package's generic
    intake.ignored_members Issue in package.issues itself (D-16). That mutates the Package once, by
    design: the import dialog logs package.issues, and only the winning vendor may change its note.
    The swap is idempotent, so detecting the same Package again leaves exactly one such Issue.
    """
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
    if best.ignored_note is not None:
        swapped = (best.ignored_note if i.code == _IGNORED_CODE else i for i in package.issues)
        package.issues[:] = dict.fromkeys(swapped)
    candidate, issues = locate(package, best)
    if best.notes:
        issues = [*issues, *best.notes]
        if candidate is not None:
            candidate = replace(candidate, issues=(*candidate.issues, *best.notes))
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
    if candidate is not None:
        # WR-03: intake Issues travel with the candidate, so no caller has to forward them
        candidate = replace(candidate, issues=tuple(dict.fromkeys((*package.issues, *candidate.issues))))
    return candidate, issues
