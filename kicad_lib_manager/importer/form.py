"""The left-pane rules of the Import dialog, without Qt (Phase 5, plan 05-07).

The dialog collects what the user chose (items, names, field text) into a FormValues; build_options
turns that into the InstallOptions the planner takes. field_defaults gives what the planner would
write into each field when nothing is set, so the form shows the real result (RESEARCH Pitfall 9).
Keeping the rules here means they are tested without a display, and the dialog holds only widgets.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from ..kicad_files import replace_exact_tokens
from .candidate import ImportCandidate
from .plan import InstallOptions, Resolution
from .suggest import LibrarySuggestion, manufacturer_choice, placeholder_tokens

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


NEW_LIBRARY_BADGE = "new - creates .kicad_sym + .pretty"


def library_tokens(name: str, suggestion: LibrarySuggestion | None) -> list[tuple[str, bool]]:
    """Split a library name on "_" into (token, amber) pairs for the token line (D-11).

    A placeholder token (Phase 3 D-04) is always amber. While the text still equals the suggestion,
    a token of a low-confidence part of that suggestion is amber too; once the user edits the name
    that counts as confirmation of the rest, so only placeholders stay amber.
    """
    if not name:
        return []
    placeholders = {token.casefold() for token in placeholder_tokens(name)}
    guesses: set[str] = set()
    if suggestion is not None and name == suggestion.name:
        for choice in (suggestion.type, suggestion.subcategory, suggestion.manufacturer):
            if not choice.confident:
                guesses.update(choice.token.split("_"))
    return [(token, token.casefold() in placeholders or token in guesses) for token in name.split("_")]


def library_badge(name: str, existing: Collection[str]) -> str:
    """"existing" for an exact match, the "new" text otherwise, "" for a blank name (a case twin is new)."""
    name = name.strip()
    if not name:
        return ""
    return "existing" if name in existing else NEW_LIBRARY_BADGE


def field_defaults(candidate: ImportCandidate, symbol_name: str, final_name: str | None = None) -> FieldDefaults:
    """The field values build_plan writes for the vendor symbol symbol_name when no override is given.

    This mirrors planner._edit_symbol and the manufacturer step of build_plan: Value keeps the vendor
    value with the exact symbol-name tokens following the final name; Datasheet and Description are
    the vendor ones; Manufacturer is the vendor value, else the inferred token unless that is a
    placeholder; MPN is the vendor value, else the vendor symbol name. test_field_defaults_equivalence
    proves the equality against the planner.
    """
    item = next((s for s in candidate.symbols if s.name == symbol_name), None)
    if item is None:
        return FieldDefaults()
    meta = item.meta
    value = meta.value
    if final_name is not None and final_name != symbol_name:
        value = replace_exact_tokens(value, symbol_name, final_name)
    manufacturer = meta.manufacturer
    if not manufacturer:
        choice = manufacturer_choice(meta)
        if choice.source != "placeholder":
            manufacturer = choice.token
    return FieldDefaults(
        value=value,
        datasheet=meta.datasheet,
        description=meta.description,
        manufacturer=manufacturer,
        mpn=meta.mpn or symbol_name,
    )


def build_options(values: FormValues, defaults: FieldDefaults, linked_vendor: str | None = None) -> InstallOptions:
    """Turn the dialog's choices into InstallOptions.

    Only edited fields are passed (D-13). Text is passed exactly as typed. An emptied field whose
    default is not empty is passed as "" and named in cleared, so it installs blank; an emptied field
    whose default is already empty passes nothing. The footprint name, when edited, is passed for
    the linked footprint; an empty one is an explicit override that the planner refuses.
    """
    texts: dict[str, str] = {}
    cleared: set[str] = set()
    for name in FIELD_NAMES:
        if name not in values.fields:
            continue
        text = values.fields[name]
        if text.strip():
            texts[name] = text
        elif defaults.get(name).strip():
            texts[name] = ""
            cleared.add(name)
    footprint_names: dict[str, str] = {}
    if values.footprint_name is not None and linked_vendor:
        footprint_names[linked_vendor] = values.footprint_name.strip()
    return InstallOptions(
        library=values.library.strip(),
        symbol=values.symbol,
        footprints=tuple(values.footprints),
        model=values.model,
        no_model=values.no_model,
        footprint_names=footprint_names,
        resolutions=dict(values.resolutions),
        cleared=frozenset(cleared),
        **texts,
    )
