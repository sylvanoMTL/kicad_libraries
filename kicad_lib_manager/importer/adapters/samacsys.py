"""SamacSys / Component Search Engine marker scoring (D-14), the part_info.txt reader (D-13) and the
other-CAD folder summary (D-16).

Weights; a package is claimed from 5 points, confidence is min(points, 10) / 10:
  SamacSys_ECAD_Model generator in a staged symbol head                  5
  part_info.txt with Manufacturer and PartNumber lines                   3
    (a part_info.txt without them                                        1)
  license.txt that names SamacSys                                        2
  a version.bin member at the zip root                                   1
  a KiCad folder beside at least two other subfolders                    1
  a zip file name starting with LIB_                                     1

SAMACSYS_RULES travel on the Detection, then on ImportCandidate.field_rules, where the planner reads
them. part_info.txt is only ever read in memory (Package.markers), bounded in lines, key length and
value length, so its text never reaches a file name, symbol text or log line unfiltered.
"""

import unicodedata

from ...models import Issue, Severity
from ..fieldrules import GENERIC_VOLATILE, FieldRules
from ..package import Package
from .base import SNIFF_FILES, Detection, PartHints, read_head

SAMACSYS_CLAIM_POINTS = 5

# Mouser Price/Stock and Arrow Price/Stock match the generic "*price/stock"; the Manufacturer_Name and
# Manufacturer_Part_Number aliases are generic too, so the adapter needs no rules of its own beyond naming them
SAMACSYS_RULES = FieldRules(volatile=GENERIC_VOLATILE)

PART_INFO_MAX_LINES = 100
PART_INFO_KEY_MAX = 40
PART_INFO_VALUE_MAX = 200
_SUMMARY_NAMES = 6
_GENERATOR = b"samacsys_ecad_model"


def parse_part_info(text: str) -> dict[str, str]:
    """Read the key=value lines of a part_info.txt into a dict; never raises.

    At most the first PART_INFO_MAX_LINES lines are read. A line splits at its first "=", the key is
    casefolded and dropped when longer than PART_INFO_KEY_MAX, and the value loses its control
    characters and is cut to PART_INFO_VALUE_MAX. Lines without "=" are ignored; the first occurrence
    of a key wins.
    """
    found: dict[str, str] = {}
    for line in text.splitlines()[:PART_INFO_MAX_LINES]:
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = _printable(key).strip().casefold()
        if not key or len(key) > PART_INFO_KEY_MAX or key in found:
            continue
        found[key] = _printable(value).strip()[:PART_INFO_VALUE_MAX]
    return found


def part_hints(info: dict[str, str]) -> PartHints | None:
    """The PartHints a parsed part_info.txt gives, or None when it names no category, manufacturer or part number."""
    hints = PartHints(
        category=info.get("partcategory", ""),
        manufacturer=info.get("manufacturer", ""),
        mpn=info.get("partnumber", ""),
    )
    return hints if (hints.category or hints.manufacturer or hints.mpn) else None


def _printable(text: str) -> str:
    """text without its control characters (NUL, TAB, ESC, DEL and the like)."""
    return "".join(c for c in text if unicodedata.category(c) != "Cc")


def _kicad_base(package: Package) -> str | None:
    """The folder path that holds the KiCad folder of the first staged symbol or footprint, or None.

    "" means the KiCad folder sits at the package root.
    """
    for pf in package.files:
        if pf.kind not in ("symbol", "footprint"):
            continue
        parts = pf.member.replace("\\", "/").split("/")[:-1]
        for index, part in enumerate(parts):
            if part.casefold() == "kicad":
                return "/".join(parts[:index])
    return None


def _below(base: str, name: str) -> str | None:
    """The part of name below the folder base, or None when name is not inside it."""
    name = name.replace("\\", "/")
    if not base:
        return name
    prefix = base + "/"
    return name[len(prefix):] if name.startswith(prefix) else None


def folder_summary(package: Package) -> Issue | None:
    """The one INFO Issue that replaces the generic ignored-members list for a SamacSys package (D-16).

    Folders are the first path segments below the folder that holds the KiCad folder, in first-appearance
    order, with the KiCad folder itself left out. None when there is no KiCad folder or no other folder,
    so the generic list stays.
    """
    base = _kicad_base(package)
    if base is None:
        return None
    folders: list[str] = []
    for name in package.ignored:
        rest = _below(base, name)
        if rest is None or "/" not in rest:
            continue
        folder = rest.split("/", 1)[0]
        if folder.casefold() != "kicad" and folder not in folders:
            folders.append(folder)
    if not folders:
        return None
    names = ", ".join(folders[:_SUMMARY_NAMES])
    if len(folders) > _SUMMARY_NAMES:
        names += ", ..."
    return Issue(Severity.INFO, "intake.ignored_members", f"Not imported: other-CAD folders {names} ({len(package.ignored)} files)")


def _sibling_folders(package: Package, base: str) -> set[str]:
    """The first-level subfolders below base, the KiCad folder excluded."""
    folders: set[str] = set()
    for name in package.names:
        rest = _below(base, name)
        if rest is None or "/" not in rest:
            continue
        folder = rest.split("/", 1)[0]
        if folder.casefold() != "kicad":
            folders.add(folder)
    return folders


class SamacSysAdapter:
    name = "SamacSys"

    def detect(self, package: Package) -> Detection | None:
        symbols = [pf for pf in package.files if pf.kind == "symbol"][:SNIFF_FILES]
        points = 0
        reasons: list[str] = []
        notes: list[Issue] = []
        if any(_GENERATOR in read_head(pf).lower() for pf in symbols):
            points += 5
            reasons.append("SamacSys_ECAD_Model generator")
        text = package.marker_text("part_info.txt")
        info: dict[str, str] = {}
        if text is not None:
            info = parse_part_info(text)
            if "manufacturer" in info and "partnumber" in info:
                points += 3
                reasons.append("part_info.txt")
            else:
                points += 1
                reasons.append("part_info.txt (unreadable)")
                if not any(key in info for key in ("manufacturer", "partnumber", "partcategory")):
                    notes.append(
                        Issue(
                            Severity.INFO,
                            "intake.part_info_ignored",
                            f"part_info.txt in {package.source.name} has no Manufacturer, PartNumber or PartCategory line; "
                            "it was ignored",
                        )
                    )
        if "samacsys" in (package.marker_text("license.txt") or "").casefold():
            points += 2
            reasons.append("license.txt names SamacSys")
        if any(name.replace("\\", "/").casefold() == "version.bin" for name in package.names):
            points += 1
            reasons.append("version.bin")
        base = _kicad_base(package)
        if base is not None and len(_sibling_folders(package, base)) >= 2:
            points += 1
            reasons.append("KiCad folder beside other-CAD folders")
        if package.kind == "zip" and package.source.stem.casefold().startswith("lib_"):
            points += 1
            reasons.append("LIB_ file name")
        if points < SAMACSYS_CLAIM_POINTS:
            return None
        return Detection(
            self.name,
            min(points, 10) / 10,
            tuple(reasons),
            rules=SAMACSYS_RULES,
            hints=part_hints(info),
            ignored_note=folder_summary(package),
            notes=tuple(notes),
        )
