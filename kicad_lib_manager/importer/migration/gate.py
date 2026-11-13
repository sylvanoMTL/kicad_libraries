"""Judge the migration plan's end state, never the disk (RESEARCH Pattern 1, P-02).

end_state_context builds an AtomicContext over what the plan is about to write, so a footprint or
model the transaction deletes fails the check even though the old file still exists until apply
runs. check_plan runs the unchanged atomic_check.check_symbol over every written library and turns
each violation into a plain-language StripLine: whole-set lines (plan-wide and inventory ERRORs)
first, then one line per part per broken rule, ordered by target library, new name and rule order
(D-15). No line ever shows a raw KiCad field name or an internal issue code (owner plain-language
rule). A part whose library is only a weak guess nobody has confirmed also blocks Run, with a plain
line that targets the Library field (plan 13-26) — part.issues ERRORs are already plain text by the time they reach here (13-09/13-10/13-11),
and atomic-rule violations go through form.atomic_reason, which strips ki_* names itself.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ...atomic_check import AtomicContext, check_symbol, repo_context
from ...kicad_files import parse_bytes
from ...models import Issue, Severity
from ..form import atomic_reason
from .inventory import SHARED_FOOTPRINT_LIBRARY, Inventory
from .plan import MigrationPlan, PartKey

_MODELS_PREFIX = "Custom/3DModels/"

# StripLine targets the migration window maps to its own controls (library picker, name field,
# footprint picker, Add 3D model...); field-level atomic-rule targets instead reuse
# form.ATOMIC_TARGETS values ("mpn", "manufacturer", "footprint_name", "datasheet", "description",
# "model"), via atomic_reason below.
TARGET_LIBRARY = "library"
# A library that is only a weak guess blocks Run until the owner picks one (gap G-13-1-f, D-01)
GUESSED_LIBRARY_TEXT = (
    "{name}: check the library. {library} is only a guess from similar part numbers; "
    "pick the right one from the Library list"
)
TARGET_NAME = "symbol_name"
TARGET_FOOTPRINT = "footprint"
TARGET_MODEL = "model"
# A whole-set conflict line's target is this prefix plus the unresolved Conflict's own key, e.g.
# "conflict:footprint:F1" (D-05, D-07, F-13); the window opens that conflict's own resolution control.
CONFLICT_TARGET_PREFIX = "conflict:"

# A PartPlan.issues ERROR code -> the control that fixes it; any other code (migration.unreadable,
# migration.broken_extends, migration.missing_symbol, ...) names no control (target None).
_PART_ISSUE_TARGETS = {
    "migration.no_library": TARGET_LIBRARY,
    "migration.parent_elsewhere": TARGET_LIBRARY,
    "migration.name_clash": TARGET_NAME,
    "migration.official_missing": TARGET_FOOTPRINT,
    "migration.model_unreadable": TARGET_MODEL,
}


@dataclass(frozen=True)
class StripLine:
    """One reason Run is off (or, once fixable, one line of a strip): the part, the text and the control."""

    key: PartKey | None
    text: str
    target: str | None


@dataclass(frozen=True)
class GateOutcome:
    """check_plan's result: every strip line and how many belong to each part."""

    lines: tuple[StripLine, ...]
    failing: Mapping[PartKey, int]

    @property
    def run_enabled(self) -> bool:
        return not self.lines


def end_state_context(plan: MigrationPlan, inventory: Inventory, kicad_fp_dir: Path | None) -> AtomicContext:
    """An AtomicContext over the plan's planned end state: what it writes, deletes and leaves untouched."""
    layout = plan.layout
    shared_prefix = f"{SHARED_FOOTPRINT_LIBRARY}:"
    shared_folder_rel = f"Custom/Footprints/{SHARED_FOOTPRINT_LIBRARY}.pretty/"

    planned_footprints: dict[str, tuple[str, bytes]] = {}
    written_rel: set[str] = set()
    for op in plan.ops:
        if op.kind == "write" and op.rel.startswith(shared_folder_rel) and op.rel.endswith(".kicad_mod"):
            stem = Path(op.rel).stem
            planned_footprints[f"{shared_prefix}{stem}"] = (op.rel, op.data or b"")
            written_rel.add(op.rel)

    deleted_rel = {op.rel for op in plan.ops if op.kind == "delete"}

    # Footprints already in Atomic_Footprints.pretty that this plan does not touch
    for fp in inventory.footprints:
        if fp.library != SHARED_FOOTPRINT_LIBRARY:
            continue
        key = f"{shared_prefix}{fp.name}"
        if key in planned_footprints or fp.rel_path in deleted_rel:
            continue
        data = (layout.repo_root / fp.rel_path).read_bytes()
        planned_footprints[key] = (fp.rel_path, data)

    deleted_models: set[str] = set()
    written_models: set[str] = set()
    for op in plan.ops:
        if not op.rel.startswith(_MODELS_PREFIX):
            continue
        name = op.rel[len(_MODELS_PREFIX):]
        if op.kind == "delete":
            deleted_models.add(name)
        elif op.kind == "write":
            written_models.add(name)
    model_names = (set(inventory.models) - deleted_models) | written_models

    # P-02: repo_context's own custom_model_names() unions planned_models with a live rglob() of
    # Custom/3DModels under repo_root — it has no way to SUBTRACT a model this plan deletes, so a
    # deleted-but-still-on-disk model would otherwise still resolve. Pointing it at a sibling path
    # that is guaranteed not to exist makes that live scan raise OSError (caught, treated as empty),
    # so model_names becomes the only source of truth. Every Custom footprint link still resolves:
    # fp_libs=[] means a footprint can only come from planned_footprints, whose FootprintTarget.path
    # is built from this same repo_root and looked up in planned_bytes (also keyed by this repo_root)
    # before any real file is read, so the substitution never touches footprint resolution.
    end_state_root = layout.repo_root / "__migration_end_state__"

    # No other Custom footprint library resolves after the migration (fp_libs=[]): a link to any
    # v1 .pretty folder fails ("will not exist after the migration") exactly as the research calls for.
    return repo_context(
        end_state_root, [], kicad_fp_dir, planned_footprints=planned_footprints, planned_models=model_names
    )


def _whole_set_lines(plan: MigrationPlan, inventory: Inventory) -> list[StripLine]:
    """Every whole-set ERROR as a StripLine, in encounter order; inventory ERRORs already folded into
    plan.issues by build_migration_plan are not repeated (Issue is a frozen, hashable value)."""
    unresolved_conflicts = iter(conflict.key for conflict in plan.conflicts if conflict.resolution is None)
    seen: set[Issue] = set()
    lines: list[StripLine] = []
    for issue in (*inventory.issues, *plan.issues):
        if issue.severity is not Severity.ERROR or issue in seen:
            continue
        seen.add(issue)
        target: str | None = None
        if issue.code == "migration.conflict_unresolved":
            key = next(unresolved_conflicts, None)
            if key is not None:
                target = CONFLICT_TARGET_PREFIX + key
        lines.append(StripLine(None, issue.text, target))
    return lines


def _order(by_key: Mapping[PartKey, tuple[str, str]]) -> Callable[[tuple[int, StripLine]], tuple]:
    """A sort key for (sequence, StripLine) pairs: target library, then part name, then original sequence.

    The original append sequence already reflects rule order within one part (check_symbol's own
    violations are pre-sorted by ATOMIC_RULES), so a stable sort on just (library, name, sequence)
    reproduces "target library, part name, then rule order" without re-deriving the rule index.
    """

    def key(entry: tuple[int, StripLine]) -> tuple:
        sequence, line = entry
        target_library, new_name = by_key.get(line.key, ("", ""))
        return (target_library.casefold(), new_name.casefold(), sequence)

    return key


def check_plan(plan: MigrationPlan, inventory: Inventory, ctx: AtomicContext) -> GateOutcome:
    """Judge every planned part against ctx; a violation, an undecided or unconfirmed guessed library, or a whole-set ERROR blocks Run.

    Whole-set lines (D-05, D-07, F-13) always come first; part lines are ordered by target library,
    part name and atomic rule order (D-15).
    """
    failing: dict[PartKey, int] = {}

    def bump(key: PartKey | None) -> None:
        if key is not None:
            failing[key] = failing.get(key, 0) + 1

    whole_set = _whole_set_lines(plan, inventory)
    for line in whole_set:
        bump(line.key)

    write_ops_by_rel = {op.rel: op for op in plan.ops if op.kind == "write" and op.rel.endswith(".kicad_sym")}

    by_key: dict[PartKey, tuple[str, str]] = {}
    part_entries: list[tuple[int, StripLine]] = []

    for part in plan.parts:
        by_key[part.key] = (part.target_library, part.new_name)

        if not part.target_library:
            line = StripLine(part.key, f"Choose a library for {part.new_name}", TARGET_LIBRARY)
            part_entries.append((0, line))
            bump(part.key)
            continue

        if part.library_basis == "guessed":
            line = StripLine(
                part.key,
                GUESSED_LIBRARY_TEXT.format(name=part.new_name, library=part.target_library),
                TARGET_LIBRARY,
            )
            part_entries.append((0, line))
            bump(part.key)

        has_error = False
        for issue in part.issues:
            if issue.severity is Severity.ERROR:
                target = _PART_ISSUE_TARGETS.get(issue.code)
                part_entries.append((0, StripLine(part.key, issue.text, target)))
                bump(part.key)
                has_error = True
        if has_error:
            continue

        target_rel = f"Custom/Symbols/{part.target_library}.kicad_sym"
        op = write_ops_by_rel.get(target_rel)
        if op is None or op.data is None:
            continue

        loaded = parse_bytes(op.data, f"{part.target_library}.kicad_sym")
        if isinstance(loaded, Issue):
            part_entries.append((0, StripLine(part.key, loaded.text, None)))
            bump(part.key)
            continue

        entry = check_symbol(loaded.root, part.new_name, rel_path=target_rel, fixable=False, ctx=ctx)
        for rule_index, violation in enumerate(entry.violations):
            issue = Issue(Severity.ERROR, f"install.atomic.{violation.rule}", violation.text)
            reason = atomic_reason(issue)
            line = StripLine(part.key, f"{part.new_name}: {reason.text}", reason.target)
            part_entries.append((rule_index + 1, line))
            bump(part.key)

    part_entries.sort(key=_order(by_key))
    lines = [*whole_set, *(line for _, line in part_entries)]

    return GateOutcome(tuple(lines), dict(failing))
