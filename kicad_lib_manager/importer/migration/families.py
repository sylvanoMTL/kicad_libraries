"""Derived-symbol decisions for the Atomic_ migration (D-06); plan 13-11 fills both functions.

find_families always returns no families yet (empty outcome) and derived_edits always returns no
edits yet: this plan only fixes the final shape symbols.py and the window build against, so later
waves can land in parallel without editing this module's signature.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from ...kicad_files import Edit, LoadedFile, SymbolRef
from .plan import FamilyRow, MigrationChoices, PartKey


@dataclass(frozen=True)
class FamiliesOutcome:
    """find_families's result: which parts derive from which, and the rows a window would show."""

    derived: Mapping[PartKey, PartKey] = field(default_factory=dict)
    rows: tuple[FamilyRow, ...] = ()


def find_families(
    inventory,
    choices: MigrationChoices,
    *,
    targets: Mapping[PartKey, str],
    mpns: Mapping[PartKey, str],
) -> FamiliesOutcome:
    """No families are derived yet (D-06); plan 13-11 fills this in."""
    return FamiliesOutcome({}, ())


def derived_edits(loaded: LoadedFile, ref: SymbolRef, parent_name: str) -> list[Edit]:
    """No edits are made yet (D-06); plan 13-11 fills this in."""
    return []
