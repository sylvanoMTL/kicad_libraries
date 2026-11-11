"""Judge the migration plan's end state, never the disk (RESEARCH Pattern 1, P-02).

end_state_context builds an AtomicContext over what the plan is about to write, so a footprint or
model the transaction deletes fails the check even though the old file still exists until apply
runs. check_plan runs the unchanged atomic_check.check_symbol over every written library and turns
each violation into a plain-language StripLine (13-12 adds per-code ordering and targets).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ...atomic_check import AtomicContext, check_symbol, repo_context
from ...kicad_files import parse_bytes
from ...models import Issue, Severity
from ..form import atomic_reason
from .inventory import SHARED_FOOTPRINT_LIBRARY, Inventory
from .plan import MigrationPlan, PartKey

_MODELS_PREFIX = "Custom/3DModels/"


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

    # No other Custom footprint library resolves after the migration (fp_libs=[]): a link to any
    # v1 .pretty folder fails ("will not exist after the migration") exactly as the research calls for.
    return repo_context(
        layout.repo_root, [], kicad_fp_dir, planned_footprints=planned_footprints, planned_models=model_names
    )


def check_plan(plan: MigrationPlan, inventory: Inventory, ctx: AtomicContext) -> GateOutcome:
    """Judge every planned part against ctx; a violation, an undecided library or a plan-wide ERROR blocks Run."""
    lines: list[StripLine] = []
    failing: dict[PartKey, int] = {}

    def bump(key: PartKey | None) -> None:
        if key is not None:
            failing[key] = failing.get(key, 0) + 1

    write_ops_by_rel = {op.rel: op for op in plan.ops if op.kind == "write" and op.rel.endswith(".kicad_sym")}

    for part in plan.parts:
        if not part.target_library:
            lines.append(StripLine(part.key, f"Choose a library for {part.new_name}", "library"))
            bump(part.key)
            continue

        has_error = False
        for issue in part.issues:
            if issue.severity is Severity.ERROR:
                lines.append(StripLine(part.key, issue.text, None))
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
            lines.append(StripLine(part.key, loaded.text, None))
            bump(part.key)
            continue

        entry = check_symbol(loaded.root, part.new_name, rel_path=target_rel, fixable=False, ctx=ctx)
        for violation in entry.violations:
            issue = Issue(Severity.ERROR, f"install.atomic.{violation.rule}", violation.text)
            reason = atomic_reason(issue)
            lines.append(StripLine(part.key, f"{part.new_name}: {reason.text}", reason.target))
            bump(part.key)

    for issue in plan.issues:
        if issue.severity is Severity.ERROR:
            lines.append(StripLine(None, issue.text, None))

    return GateOutcome(tuple(lines), dict(failing))
