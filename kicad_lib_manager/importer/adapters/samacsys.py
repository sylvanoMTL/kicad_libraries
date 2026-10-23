"""SamacSys skeleton for the RED step: importable names, no behaviour yet."""

from ..fieldrules import GENERIC_VOLATILE, FieldRules
from ..package import Package
from .base import Detection

SAMACSYS_RULES = FieldRules(volatile=GENERIC_VOLATILE)


def parse_part_info(text: str) -> dict[str, str]:
    return {"unimplemented": text}


class SamacSysAdapter:
    name = "SamacSys"

    def detect(self, package: Package) -> Detection | None:
        return None
