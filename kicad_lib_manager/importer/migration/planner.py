"""Orchestrate the Atomic_ migration plan: inventory in, one MigrationPlan out (MIG-02, MIG-03).

build_migration_plan calls the other migration modules in a fixed order (targets, MPNs, families,
footprints, symbols, map) so each can be deepened independently in parallel plans without touching
this file. Nothing here writes to disk; that is applier.apply_migration's job.
"""

import hashlib
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ...models import Issue
from ..candidate import PartMeta
from ..fieldrules import clean_description
from ..plan import ToolContext
from ..siblings import own_index, stock_index
from ..suggest import suggest_library
from . import families, footprints, symbols
from .inventory import Inventory, InventoryPart
from .mapfile import map_text
from .plan import MAP_FILE, MigrationChoices, MigrationOp, MigrationPlan, PartKey, PlanContext


def part_meta(part: InventoryPart) -> PartMeta:
    """The PartMeta suggest_library needs, read straight from an inventory part's own fields."""
    fields = part.fields
    return PartMeta(
        symbol_name=part.name,
        reference=fields.get("Reference", ""),
        value=fields.get("Value", ""),
        datasheet=fields.get("Datasheet", ""),
        description=clean_description(fields.get("Description", "")),
        keywords=fields.get("ki_keywords", ""),
        footprint_field=part.footprint,
        fp_filters=fields.get("ki_fp_filters", ""),
        manufacturer=fields.get("Manufacturer") or fields.get("MF") or "",
        mpn=fields.get("MPN") or fields.get("MP") or "",
        category="",
    )


def prepare_context(
    inventory: Inventory,
    tools: ToolContext,
    kicad_fp_dir: Path | None,
    *,
    progress: Callable | None = None,
    today: str | None = None,
) -> PlanContext:
    """Index the owner's and KiCad's siblings once, and suggest a library for every part (D-01)."""
    layout = inventory.layout
    allowed = tools.allowed_stems
    own = own_index(layout.symbols_dir, allowed)
    stock = stock_index(tools.kicad_symbols_dir, progress) if tools.kicad_symbols_dir is not None else None
    suggestions = {
        part.key: suggest_library(part_meta(part), own=own, stock=stock, allowed=allowed)
        for part in inventory.parts
    }
    return PlanContext(
        tools=tools,
        kicad_fp_dir=kicad_fp_dir,
        own=own,
        stock=stock,
        suggestions=suggestions,
        allowed=allowed,
        today=today if today is not None else date.today().isoformat(),
    )


_OP_ORDER = {"mkdir": 0, "write": 1, "delete": 2, "rmdir": 3}


def build_migration_plan(inventory: Inventory, choices: MigrationChoices, ctx: PlanContext) -> MigrationPlan:
    """Plan one migration: who moves where, the file operations it takes, and the map file it writes."""
    layout = inventory.layout

    targets: dict[PartKey, str] = symbols.target_libraries(inventory, choices, ctx)
    mpns: dict[PartKey, str] = symbols.part_mpns(inventory, choices)
    fam = families.find_families(inventory, choices, targets=targets, mpns=mpns)
    fps = footprints.plan_footprints(inventory, choices, ctx, mpns=mpns)
    syms = symbols.plan_symbols(
        inventory, choices, ctx, targets=targets, mpns=mpns, footprints=fps, families=fam
    )

    ops: list[MigrationOp] = [*syms.ops, *fps.ops]

    for rel in inventory.bak_files:
        path = layout.repo_root / rel
        ops.append(
            MigrationOp(
                "delete", path, rel, base_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), note=".bak backup"
            )
        )

    map_path = layout.custom_dir / MAP_FILE
    map_rel = map_path.relative_to(layout.repo_root).as_posix()
    previous_text: str | None = None
    previous_bytes: bytes | None = None
    if map_path.exists():
        previous_bytes = map_path.read_bytes()
        previous_text = previous_bytes.decode("utf-8", "replace")

    generated_map_text = map_text(
        library_map=syms.library_map,
        symbol_renames=syms.symbol_renames,
        footprint_links=fps.footprint_links,
        model_renames=fps.model_renames,
        today=ctx.today,
        previous=previous_text,
    )
    ops.append(
        MigrationOp(
            "write",
            map_path,
            map_rel,
            data=generated_map_text.encode("utf-8"),
            base_sha256=hashlib.sha256(previous_bytes).hexdigest() if previous_bytes is not None else None,
        )
    )

    ops.sort(key=lambda op: _OP_ORDER[op.kind])

    issues: list[Issue] = [*inventory.issues, *fps.issues, *syms.issues]

    return MigrationPlan(
        layout=layout,
        parts=syms.parts,
        ops=tuple(ops),
        library_map=syms.library_map,
        symbol_renames=syms.symbol_renames,
        footprint_links=fps.footprint_links,
        model_renames=fps.model_renames,
        leftovers=fps.leftovers,
        families=fam.rows,
        conflicts=fps.conflicts,
        removed_libraries=syms.removed_libraries,
        bak_files=inventory.bak_files,
        map_text=generated_map_text,
        issues=tuple(issues),
    )
