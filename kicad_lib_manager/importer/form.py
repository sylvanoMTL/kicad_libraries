"""The left-pane rules of the Import dialog, without Qt (Phase 5, plan 05-07).

The dialog collects what the user chose (items, names, field text) into a FormValues; build_options
turns that into the InstallOptions the planner takes. field_defaults gives what the planner would
write into each field when nothing is set, so the form shows the real result (RESEARCH Pitfall 9).
Keeping the rules here means they are tested without a display, and the dialog holds only widgets.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from ..kicad_files import replace_exact_tokens
from ..models import Issue, Severity
from .candidate import ImportCandidate
from .fieldrules import clean_description
from .plan import Conflict, InstallOptions, InstallPlan, Resolution
from .stems import name_verdict
from .suggest import manufacturer_choice

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

    symbol, footprint and model are vendor item names (or None), never blank strings.
    footprint is the one footprint the part uses (D-14). footprint_name None means the name was not
    edited, and fields holds only the fields the user edited.
    """

    library: str
    symbol: str | None
    footprint: str | None
    model: str | None
    no_model: bool
    footprint_name: str | None
    fields: Mapping[str, str] = field(default_factory=dict)
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)


# A new library creates only its .kicad_sym: every part uses the shared footprint library (D-12, D-15)
NEW_LIBRARY_BADGE = "new - creates .kicad_sym"

# -- the blocking reasons (D-09, PREV-07) ----------------------------------------------------------

UPDATING_REASON = "Updating preview..."
BUILD_FAILED_REASON = "Error: Preview could not be built - see the log"
_KIND_LABELS = {"symbol": "symbol", "footprint": "footprint", "model": "3D model"}


def kind_label(kind: str) -> str:
    """The word for a conflict kind in the user's copy."""
    return _KIND_LABELS.get(kind, kind)


@dataclass(frozen=True)
class Reason:
    """One reason Install is off, and the control that fixes it.

    target is "plan" (no control), "library", "footprint_name", "value", "mpn", "footprints" (the footprint choice), "model"
    (the 3D model row), "conflict:{key}" or "rename:{key}".
    """

    text: str
    target: str


@dataclass(frozen=True)
class FormStatus:
    """What the dialog's controls say right now, for blocking_reasons."""

    updating: bool
    build_failed: bool
    library: str
    value_text: str
    mpn_text: str
    resolutions: Mapping[str, Resolution]
    model_error: str = ""  # the ERROR text of a rejected 3D model source; empty when none is held
    allowed: frozenset[str] = frozenset()  # allowed KiCad library stems; empty means the built-in snapshot


def _blank_renames(status: FormStatus, plan: InstallPlan | None) -> list[Conflict]:
    """The plan's conflicts whose chosen Rename has no text yet, in plan order."""
    if plan is None:
        return []
    blank = []
    for conflict in plan.conflicts:
        chosen = status.resolutions.get(conflict.key)
        if chosen is not None and chosen.action == "rename" and not (chosen.rename_to or "").strip():
            blank.append(conflict)
    return blank


def _issue_target(issue: Issue) -> str:
    """The control a plan ERROR is about; "plan" when it is about no single control."""
    code, text = issue.code, issue.text
    if code in ("install.invalid_library", "install.library_case_clash"):
        return "library"
    if code == "install.empty_required":
        return "mpn" if text.startswith("MPN") else "value"
    if code == "install.invalid_name":
        lowered = text.lower()
        if "footprint name" in lowered:
            return "footprint_name"
        if "part number" in lowered:
            return "mpn"
    if code == "install.choice_required" and "footprints" in text:
        return "footprints"
    return "plan"


def blocking_reasons(status: FormStatus, plan: InstallPlan | None) -> list[Reason]:
    """Every reason Install is off, in the UI-SPEC order, without repeating one a form reason already gives.

    Order: Updating (alone, the others could be stale); the build failure or the plan's ERROR Issues;
    a rejected 3D model source; the library name; Value and MPN; unresolved conflicts in plan order;
    empty rename names. A plan ERROR is dropped when the form reason beside it says the same thing
    (refused library name, empty Value or MPN, empty rename).
    """
    if status.updating:
        return [Reason(UPDATING_REASON, "plan")]
    library = status.library.strip()
    verdict = name_verdict(library, status.allowed or None)
    value_blank = not status.value_text.strip()
    mpn_blank = not status.mpn_text.strip()
    # A failed build leaves the previous plan on screen; what it said could be stale
    plan = None if status.build_failed else plan
    renames = _blank_renames(status, plan)

    def explained(issue: Issue) -> bool:
        code, text = issue.code, issue.text
        if code == "install.invalid_library":
            return not verdict.ok
        if code == "install.empty_required":
            return mpn_blank if text.startswith("MPN") else value_blank
        if code == "install.bad_rename":
            return any(text.startswith(f"{c.key}:") for c in renames)
        return False

    reasons: list[Reason] = []
    if status.build_failed:
        reasons.append(Reason(BUILD_FAILED_REASON, "plan"))
    elif plan is not None:
        for issue in plan.issues:
            if issue.severity is Severity.ERROR and not explained(issue):
                reasons.append(Reason(f"Error: {issue.text}", _issue_target(issue)))
    if status.model_error.strip():
        reasons.append(Reason(f"Error: {status.model_error}", "model"))
    if not verdict.ok:
        reasons.append(Reason(verdict.reason, "library"))
    if value_blank:
        reasons.append(Reason("Value is empty", "value"))
    if mpn_blank:
        reasons.append(Reason("MPN is empty - it names the 3D model file", "mpn"))
    if plan is not None:
        skipped = {c.key for c in renames}  # a Rename was chosen: it needs a name, not a choice
        for conflict in plan.unresolved_conflicts:
            if conflict.key not in skipped:
                reasons.append(Reason(
                    f"Choose Overwrite, Rename or Skip for {kind_label(conflict.kind)} {conflict.name}",
                    f"conflict:{conflict.key}",
                ))
        for conflict in renames:
            reasons.append(Reason(
                f"Enter a new name for {kind_label(conflict.kind)} {conflict.name}", f"rename:{conflict.key}"
            ))
    return reasons


def carry_resolutions(old: Mapping[str, Resolution], plan: InstallPlan) -> dict[str, Resolution]:
    """The conflict choices that still apply to a new plan: only those whose key the plan still has (D-14a).

    A key that vanished (another library, a renamed footprint) drops its choice, so an Overwrite never
    moves to another item; a key that is new starts unresolved.
    """
    keys = {conflict.key for conflict in plan.conflicts}
    return {key: resolution for key, resolution in old.items() if key in keys}


def ready_text(counts) -> str:
    """The strip line for a plan that can be installed; counts is a preview.FileCounts."""
    return f"✓ Ready to install: {counts.new} new, {counts.modified} modified, {counts.unchanged} unchanged files"


def noop_text(library: str) -> str:
    return f"Nothing to install: this part is already in {library}."


def library_badge(name: str, existing: Collection[str], allowed: frozenset[str] | None = None) -> str:
    """"existing" for a listed library, the "new" text for an allowed name, "" for a blank or refused name."""
    name = name.strip()
    if not name or not name_verdict(name, allowed).ok:
        return ""
    return "existing" if name in existing else NEW_LIBRARY_BADGE


def field_defaults(candidate: ImportCandidate, symbol_name: str, final_name: str | None = None) -> FieldDefaults:
    """The field values build_plan writes for the vendor symbol symbol_name when no override is given.

    This mirrors planner._edit_symbol and the manufacturer step of build_plan: Value keeps the vendor
    value with the exact symbol-name tokens following the final name; Datasheet is the vendor one and
    Description the vendor one with its whitespace collapsed (D-07); Manufacturer is the vendor value,
    else the inferred token unless that is a placeholder; MPN is meta.mpn, which is the vendor value or
    one supplied by package metadata, else the vendor symbol name. part_meta keeps the raw description on
    purpose: tests/test_locate_text_caps.py compares the raw text of an 8 MiB symbol, and the cleaning is
    cheap here. test_field_defaults_equivalence proves the equality against the planner.
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
        description=clean_description(meta.description),
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
    chosen = values.footprint or linked_vendor
    if values.footprint_name is not None and chosen:
        footprint_names[chosen] = values.footprint_name.strip()
    return InstallOptions(
        library=values.library.strip(),
        symbol=values.symbol,
        footprint=values.footprint,
        model=values.model,
        no_model=values.no_model,
        footprint_names=footprint_names,
        resolutions=dict(values.resolutions),
        cleared=frozenset(cleared),
        **texts,
    )
