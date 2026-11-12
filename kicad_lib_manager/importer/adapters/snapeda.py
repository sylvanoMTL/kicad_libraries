"""SnapEDA marker scoring (D-14) and SNAPEDA_RULES (D-05, D-08).

Weights; a package is claimed from 5 points, confidence is min(points, 10) / 10:
  SnapEDA property (SnapEDA_Link, SNAPEDA_PN, ...) in a staged symbol   5
  snapeda.com anywhere in a staged symbol head                          2
  a how-to-import.htm / .html member                                    2
  that page's text mentions snapeda.com (Package.markers, D-13)         3

SNAPEDA_RULES travel on the Detection, then on ImportCandidate.field_rules, where the planner
reads them.
"""

from ..fieldrules import GENERIC_VOLATILE, MPN_FIELDS, FieldRules
from ..package import Package
from .base import SNIFF_FILES, Detection, read_head

SNAPEDA_CLAIM_POINTS = 5

# "purchase-url" is a tracking/purchase link seen in most existing SnapEDA symbols (flagged assumption)
SNAPEDA_RULES = FieldRules(
    volatile=GENERIC_VOLATILE + ("purchase-url",),
    mpn_aliases=MPN_FIELDS + ("SNAPEDA_PN",),
)

_PROPERTY_MARKERS = (b"snapeda_link", b"snapeda_pn", b"snapeda_package_id")
_SITE = b"snapeda.com"
_HOW_TO = ("how-to-import.htm", "how-to-import.html")


class SnapEDAAdapter:
    name = "SnapEDA"

    def detect(self, package: Package) -> Detection | None:
        symbols = [pf for pf in package.files if pf.kind == "symbol"][:SNIFF_FILES]
        heads = [read_head(pf).lower() for pf in symbols]
        points = 0
        reasons: list[str] = []
        if any(marker in head for head in heads for marker in _PROPERTY_MARKERS):
            points += 5
            reasons.append("SnapEDA symbol property")
        if any(_SITE in head for head in heads):
            points += 2
            reasons.append("snapeda.com URL in the symbol")
        if any(name.replace("\\", "/").rsplit("/", 1)[-1].casefold() in _HOW_TO for name in package.names):
            points += 2
            reasons.append("how-to-import.htm")
        if any(_SITE.decode() in (package.marker_text(page) or "").casefold() for page in _HOW_TO):
            points += 3
            reasons.append("how-to-import.htm points to snapeda.com")
        if points < SNAPEDA_CLAIM_POINTS:
            return None
        return Detection(self.name, min(points, 10) / 10, tuple(reasons), rules=SNAPEDA_RULES)
