"""Adapter for a folder of loose KiCad and 3D files."""

from ..package import Package
from .base import Detection

LOOSE_CONFIDENCE = 0.3


class LooseAdapter:
    name = "Loose"

    def detect(self, package: Package) -> Detection | None:
        return None
