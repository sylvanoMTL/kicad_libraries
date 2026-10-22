"""The left-pane rules of the Import dialog, without Qt (Phase 5, plan 05-07).

The dialog collects what the user chose (items, names, field text) into a FormValues; build_options
turns that into the InstallOptions the planner takes. Keeping the rules here means they are tested
without a display, and the dialog holds only widgets.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from .plan import InstallOptions, Resolution

# The five symbol fields the dialog lets the user edit; the names are the InstallOptions text overrides
FIELD_NAMES = ("value", "datasheet", "description", "manufacturer", "mpn")
FIELD_LABELS = {
    "value": "Value",
    "datasheet": "Datasheet",
    "description": "Description",
    "manufacturer": "Manufacturer",
    "mpn": "MPN",
}


@dataclass(frozen=True)
class FieldDefaults:
    """What the planner would write into each field when the caller sets nothing."""

    value: str = ""
    datasheet: str = ""
    description: str = ""
    manufacturer: str = ""
    mpn: str = ""

    def get(self, name: str) -> str:
        return getattr(self, name)


@dataclass(frozen=True)
class FormValues:
    """The dialog's choices at one moment.

    symbol, footprints and model are vendor item names (or None / empty), never blank strings.
    footprints lists the linked footprint first. footprint_name None means the name was not edited,
    and fields holds only the fields the user edited.
    """

    library: str
    symbol: str | None
    footprints: tuple[str, ...]
    model: str | None
    no_model: bool
    footprint_name: str | None
    fields: Mapping[str, str] = field(default_factory=dict)
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)


def build_options(values: FormValues, defaults: FieldDefaults, linked_vendor: str | None = None) -> InstallOptions:
    """Turn the dialog's choices into InstallOptions."""
    return InstallOptions(
        library=values.library.strip(),
        symbol=values.symbol,
        footprints=tuple(values.footprints),
        model=values.model,
        no_model=values.no_model,
        resolutions=dict(values.resolutions),
    )
