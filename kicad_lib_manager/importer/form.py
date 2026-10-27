"""The left-pane rules of the Import dialog, without Qt (Phase 5, plan 05-07).

The dialog collects what the user chose (items, names, field text) into a FormValues; build_options
turns that into the InstallOptions the planner takes. field_defaults gives what the planner would
write into each field when nothing is set, so the form shows the real result (RESEARCH Pitfall 9).
Keeping the rules here means they are tested without a display, and the dialog holds only widgets.
"""

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from ..atomic_check import datasheet_problem
from ..manufacturers import canonical
from ..models import Issue, Severity
from .candidate import ImportCandidate
from .fieldrules import clean_description, is_placeholder
from .plan import Conflict, InstallOptions, InstallPlan, Resolution
from .stems import name_verdict
from .suggest import manufacturer_from_datasheet

# The five symbol fields the dialog shows. Value is shown read-only: it always follows the MPN (D-22), so it has
# no InstallOptions override; OVERRIDE_NAMES are the four the user can edit and InstallOptions takes
FIELD_NAMES = ("value", "datasheet", "description", "manufacturer", "mpn")
OVERRIDE_NAMES = tuple(name for name in FIELD_NAMES if name != "value")
FIELD_LABELS = {
    "value": "Value",
    "datasheet": "Datasheet",
    "description": "Description",
    "manufacturer": "Manufacturer",
    "mpn": "MPN",
}
# The three generated texts the dialog shows under the fields (D-30): the symbol's keywords and the footprint's
# description and tags. They are InstallOptions fields of the same names; the plan's part_text holds what is written.
TEXT_NAMES = ("keywords", "fp_description", "fp_tags")
TEXT_LABELS = {
    "keywords": "Keywords",
    "fp_description": "Footprint description",
    "fp_tags": "Footprint tags",
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
    edited, and fields holds only the fields the user edited. texts holds only the generated texts the user
    edited, by TEXT_NAMES; related_stems are the suggestion's runner-up library stems, whose words join the keywords.
    """

    library: str
    symbol: str | None
    footprint: str | None
    model: str | None
    no_model: bool
    footprint_name: str | None
    fields: Mapping[str, str] = field(default_factory=dict)
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)
    texts: Mapping[str, str] = field(default_factory=dict)
    related_stems: tuple[str, ...] = ()


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

    target is "plan" (no control), "library", "footprint_name", "mpn", "manufacturer", "datasheet", "description",
    "footprints" (the footprint choice), "model" (the Add 3D model... button), "model_rejected" (the Remove button
    of a rejected 3D model source), "conflict:{key}" or "rename:{key}".
    """

    text: str
    target: str


@dataclass(frozen=True)
class FormStatus:
    """What the dialog's controls say right now, for blocking_reasons."""

    updating: bool
    build_failed: bool
    library: str
    mpn_text: str
    resolutions: Mapping[str, Resolution]
    model_error: str = ""  # the ERROR text of a rejected 3D model source; empty when none is held
    allowed: frozenset[str] = frozenset()  # allowed KiCad library stems; empty means the built-in snapshot
    # The live field texts: a typed fix lifts its reason before the rebuild (D-25)
    datasheet_text: str = ""
    description_text: str = ""
    manufacturer_text: str = ""


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


_ATOMIC_PREFIX = "install.atomic."
# The control each atomic rule is fixed in: Value follows the MPN (D-22), the model is the Add 3D model... button
ATOMIC_TARGETS = {
    "mpn": "mpn",
    "manufacturer": "manufacturer",
    "footprint": "footprint_name",
    "value": "mpn",
    "datasheet": "datasheet",
    "description": "description",
    "model_3d": "model",
}
_RULE_LABELS = {"footprint": "Footprint", "model_3d": "3D model", **FIELD_LABELS}
# What the Phase 9 check says for a missing value, and the sentence the owner reads instead
_ATOMIC_SENTENCES = (
    ("mpn", "no MPN", "Enter the MPN"),
    ("manufacturer", "no manufacturer", "Enter the Manufacturer"),
    ("datasheet", "no datasheet", "Enter a Datasheet link"),
    ("datasheet", "Datasheet is not a link or file path", "The Datasheet must be a link or a file path"),
    ("description", "no description", "Type a Description"),
)
# How each rule's own texts start, so "<parent>: <text>" is told from a text that holds a colon itself
_ATOMIC_STARTS = {
    "mpn": ("no MPN", "MPN "),
    "manufacturer": ("no manufacturer", "Manufacturer ", '"'),
    "footprint": ("no footprint", "Footprint ", "footprint "),
    "value": ("no Value", "Value "),
    "datasheet": ("no datasheet", "Datasheet "),
    "description": ("no description",),
    "model_3d": ("the footprint has no 3D model", "Could not check the 3D model", "3D model "),
}
_RAW_FIELD_RE = re.compile(r'"?\bki_([a-z_]+)\b"?')


def _plain(text: str) -> str:
    """The text with each raw KiCad field name in words (ki_fp_filters reads as fp filters), never the name."""
    return _RAW_FIELD_RE.sub(lambda m: m.group(1).replace("_", " "), text)


def _atomic_parts(issue: Issue) -> tuple[str, str | None, str]:
    """Split an install.atomic.<rule> Issue into (rule, parent symbol name or None, the check's own text).

    A failure of a parent symbol of an extends unit reads "<name>: <text>", text being one of the rule's wordings.
    """
    rule = issue.code[len(_ATOMIC_PREFIX):]
    text = issue.text
    starts = _ATOMIC_STARTS.get(rule, ())
    if starts and not text.startswith(starts):
        head, sep, rest = text.partition(": ")
        if sep and head and rest.startswith(starts):
            return rule, head, rest
    return rule, None, text


def _atomic_sentence(rule: str, text: str) -> str:
    """The plain sentence for one rule's text; a text the table does not know reads "<Label>: <text>"."""
    for known_rule, known, sentence in _ATOMIC_SENTENCES:
        if rule == known_rule and text.startswith(known):
            return sentence
    label = _RULE_LABELS.get(rule, rule)
    if rule == "model_3d":
        return f"{label}: {_plain(text).rstrip('.')}. Use Add 3D model..."
    return f"{label}: {_plain(text)}"


def atomic_reason(issue: Issue) -> Reason:
    """The reason for one broken atomic rule: a plain sentence and the control that fixes it (D-25).

    A failure of a parent symbol names the parent and targets no control: the dialog edits only the chosen symbol.
    """
    rule, parent, text = _atomic_parts(issue)
    sentence = _atomic_sentence(rule, text)
    if parent is not None:
        return Reason(f"{parent} (parent symbol): {sentence}", "plan")
    return Reason(sentence, ATOMIC_TARGETS.get(rule, "plan"))


def _filled(text: str) -> bool:
    return bool(text.strip()) and not is_placeholder(text)


def _atomic_fixed_live(issue: Issue, status: FormStatus) -> bool:
    """True when the live field text already fixes a missing-value ERROR of the chosen symbol (D-25)."""
    rule, parent, text = _atomic_parts(issue)
    if parent is not None:
        return False
    if rule == "description":
        return _filled(status.description_text)
    if rule == "manufacturer":
        return text.startswith("no manufacturer") and _filled(status.manufacturer_text)
    if rule == "datasheet":
        return datasheet_problem(status.datasheet_text) is None
    if rule == "mpn":
        # A blank MPN field has its own reason ("MPN is empty ...") beside this one
        return text.startswith("no MPN")
    if rule == "value":
        return _filled(status.mpn_text)
    return False


def _issue_target(issue: Issue) -> str:
    """The control a plan ERROR is about; "plan" when it is about no single control."""
    code, text = issue.code, issue.text
    if code in ("install.invalid_library", "install.library_case_clash"):
        return "library"
    if code == "install.empty_required":
        return "mpn"
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
    a rejected 3D model source; the library name; MPN; unresolved conflicts in plan order;
    empty rename names. A plan ERROR is dropped when the form reason beside it says the same thing
    (refused library name, empty MPN, empty rename).
    """
    if status.updating:
        return [Reason(UPDATING_REASON, "plan")]
    library = status.library.strip()
    verdict = name_verdict(library, status.allowed or None)
    mpn_blank = not status.mpn_text.strip()
    # A failed build leaves the previous plan on screen; what it said could be stale
    plan = None if status.build_failed else plan
    renames = _blank_renames(status, plan)

    def explained(issue: Issue) -> bool:
        code, text = issue.code, issue.text
        if code == "install.invalid_library":
            return not verdict.ok
        if code == "install.empty_required":
            return mpn_blank
        if code == "install.bad_rename":
            return any(text.startswith(f"{c.key}:") for c in renames)
        if code.startswith(_ATOMIC_PREFIX):
            return _atomic_fixed_live(issue, status)
        return False

    reasons: list[Reason] = []
    if status.build_failed:
        reasons.append(Reason(BUILD_FAILED_REASON, "plan"))
    elif plan is not None:
        for issue in plan.issues:
            if issue.severity is not Severity.ERROR or explained(issue):
                continue
            if issue.code.startswith(_ATOMIC_PREFIX):
                reasons.append(atomic_reason(issue))
            else:
                reasons.append(Reason(f"Error: {issue.text}", _issue_target(issue)))
    if status.model_error.strip():
        reasons.append(Reason(f"Error: {status.model_error}", "model_rejected"))
    if not verdict.ok:
        reasons.append(Reason(verdict.reason, "library"))
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

    This mirrors planner._edit_symbol and the manufacturer step of build_plan: Value is the MPN (D-22);
    Datasheet is the vendor one and
    Description the vendor one with its whitespace collapsed (D-07); Manufacturer is the vendor value in its
    canonical spelling, else the company the datasheet link names (D-23); MPN is meta.mpn, which is the vendor value or
    one supplied by package metadata, else the vendor symbol name. part_meta keeps the raw description on
    purpose: tests/test_locate_text_caps.py compares the raw text of an 8 MiB symbol, and the cleaning is
    cheap here. test_field_defaults_equivalence proves the equality against the planner.
    """
    item = next((s for s in candidate.symbols if s.name == symbol_name), None)
    if item is None:
        return FieldDefaults()
    meta = item.meta
    mpn = meta.mpn or symbol_name
    manufacturer = canonical(meta.manufacturer) if meta.manufacturer else manufacturer_from_datasheet(meta.datasheet)[0]
    return FieldDefaults(
        value=mpn,
        datasheet=meta.datasheet,
        description=clean_description(meta.description),
        manufacturer=manufacturer,
        mpn=mpn,
    )


def build_options(values: FormValues, defaults: FieldDefaults, linked_vendor: str | None = None) -> InstallOptions:
    """Turn the dialog's choices into InstallOptions.

    Only edited fields are passed (D-13). Text is passed exactly as typed. An emptied field whose
    default is not empty is passed as "" and named in cleared, so it installs blank; an emptied field
    whose default is already empty passes nothing. The footprint name, when edited, is passed for
    the linked footprint; an empty one is an explicit override that the planner refuses. An edited generated
    text is passed exactly as typed, an empty one too (D-30).
    """
    texts: dict[str, str] = {}
    cleared: set[str] = set()
    for name in OVERRIDE_NAMES:
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
        related_stems=tuple(values.related_stems),
        **{name: values.texts[name] for name in TEXT_NAMES if name in values.texts},
        **texts,
    )
