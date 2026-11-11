"""Plan the symbol side of the Atomic_ migration: who moves where, under what name (D-01, D-04, D-07).

Thin for this plan (13-09 completes it): one source file is loaded once per library, a part's
unit is normalised with the importer's own new_source/existing_source and edited with
edit_symbol, then spliced into the target library text being assembled. Name clashes within one
target are not yet turned into a blocking line (13-09); the fixtures this plan ships with have none.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ... import fsutil
from ...kicad_files import (
    LoadedFile,
    apply_edits,
    block_text,
    file_version,
    find_symbol,
    parse_bytes,
    rename_symbol_edits,
    symbol_insert_edit,
    symbol_unit,
)
from ...manufacturers import canonical
from ...models import Issue, Severity
from ..fieldrules import GENERIC_VOLATILE, MPN_FIELDS, FieldRules
from ..naming import sanitize_name
from ..planner import SymbolFields, edit_symbol, existing_source, new_source, unit_text
from .families import FamiliesOutcome
from .inventory import Inventory, InventoryPart
from .plan import MigrationChoices, MigrationOp, PartChoice, PartKey, PartPlan, PartText, Rename

# importer.migration.footprints is not in this module's ALLOWED entry (tests/test_importer_layering.py),
# so FootprintsOutcome is referenced by name in the `footprints` parameter below without being imported
# (`from __future__ import annotations` keeps the annotation unevaluated at runtime).

# D-04: a migrated part's volatile fields drop purchase-url too; its MPN aliases also recognise SnapEDA's own field
MIGRATION_RULES = FieldRules(
    volatile=GENERIC_VOLATILE + ("purchase-url",),
    mpn_aliases=MPN_FIELDS + ("SNAPEDA_PN",),
)


@dataclass(frozen=True)
class SymbolsOutcome:
    """plan_symbols's result: every part's plan row and the symbol-library file operations."""

    parts: tuple[PartPlan, ...]
    ops: tuple[MigrationOp, ...]
    library_map: tuple[tuple[str, str], ...]
    symbol_renames: tuple[Rename, ...]
    removed_libraries: tuple[str, ...]
    issues: tuple[Issue, ...] = ()


def target_libraries(inventory: Inventory, choices: MigrationChoices, ctx) -> dict[PartKey, str]:
    """The Atomic_ library each part is heading to: the owner's choice, else the suggestion ("" for ask, D-01)."""
    targets: dict[PartKey, str] = {}
    for part in inventory.parts:
        choice = choices.parts.get(part.key)
        if choice is not None and choice.library is not None:
            targets[part.key] = choice.library
            continue
        suggestion = ctx.suggestions.get(part.key)
        targets[part.key] = suggestion.name if suggestion is not None else ""
    return targets


def part_mpns(inventory: Inventory, choices: MigrationChoices) -> dict[PartKey, str]:
    """The MPN each part migrates with: the owner's choice, else its own MPN, MP, then Value field."""
    mpns: dict[PartKey, str] = {}
    for part in inventory.parts:
        choice = choices.parts.get(part.key)
        if choice is not None and choice.mpn is not None:
            mpns[part.key] = choice.mpn
            continue
        fields = part.fields
        mpns[part.key] = fields.get("MPN") or fields.get("MP") or fields.get("Value") or part.name
    return mpns


def _rel(layout, path: Path) -> str:
    return path.relative_to(layout.repo_root).as_posix()


def _loaded_text(data: bytes, name: str) -> LoadedFile | Issue:
    # No max_nodes cap here: importer.package is outside this module's ALLOWED entry
    # (tests/test_importer_layering.py). inventory.read_inventory already bounded every
    # source file this module re-reads; the text being reparsed here is always our own output.
    return parse_bytes(data, name)


def plan_symbols(
    inventory: Inventory,
    choices: MigrationChoices,
    ctx,
    *,
    targets: Mapping[PartKey, str],
    mpns: Mapping[PartKey, str],
    footprints: FootprintsOutcome,
    families: FamiliesOutcome,
) -> SymbolsOutcome:
    """Build the library text of every Atomic_ target and the PartPlan row for every part."""
    layout = inventory.layout
    issues: list[Issue] = []
    part_plans: list[PartPlan] = []
    ops: list[MigrationOp] = []
    library_map: set[tuple[str, str]] = set()
    symbol_renames: list[Rename] = []

    by_target: dict[str, list[InventoryPart]] = {}
    for part in inventory.parts:
        target = targets.get(part.key, "")
        if target:
            by_target.setdefault(target, []).append(part)

    loaded_cache: dict[str, LoadedFile] = {}

    def get_loaded(rel_path: str) -> LoadedFile | None:
        cached = loaded_cache.get(rel_path)
        if cached is not None:
            return cached
        path = layout.repo_root / rel_path
        try:
            data = path.read_bytes()
        except OSError as e:
            issues.append(Issue(Severity.ERROR, "migration.unreadable", f"Could not read {rel_path}: {e.strerror or e}"))
            return None
        loaded = _loaded_text(data, path.name)
        if isinstance(loaded, Issue):
            issues.append(loaded)
            return None
        loaded_cache[rel_path] = loaded
        return loaded

    for target in sorted(by_target):
        target_path = layout.symbols_dir / f"{target}.kicad_sym"
        target_rel = _rel(layout, target_path)
        existing_data = target_path.read_bytes() if target_path.exists() else None
        base_sha256 = hashlib.sha256(existing_data).hexdigest() if existing_data is not None else None
        assembled: LoadedFile | None = None
        base_version: int | None = None
        if existing_data is not None:
            loaded_target = _loaded_text(existing_data, target_path.name)
            if isinstance(loaded_target, Issue):
                issues.append(loaded_target)
                continue
            assembled = loaded_target
            base_version = file_version(assembled.root)

        ordered_parts = sorted(by_target[target], key=lambda p: (p.rel_path, p.name))
        for part in ordered_parts:
            choice = choices.parts.get(part.key, PartChoice())
            source_loaded = get_loaded(part.rel_path)
            if source_loaded is None:
                continue
            unit = symbol_unit(source_loaded.root, part.name)
            if unit is None:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "migration.broken_extends",
                        f"{part.name} in {part.rel_path} has a broken extends chain",
                    )
                )
                continue
            utext = unit_text(source_loaded, unit)
            if assembled is None:
                source, src_issues = new_source(source_loaded, utext, part.name, ctx.tools)
            else:
                source, src_issues = existing_source(source_loaded, utext, part.name, target, base_version, ctx.tools)
            issues.extend(src_issues)
            if source is None:
                continue
            work = source.loaded
            ref = find_symbol(work.root, part.name)
            if ref is None:
                issues.append(
                    Issue(Severity.ERROR, "migration.missing_symbol", f"{part.name} was lost while preparing {target}")
                )
                continue
            mpn = mpns.get(part.key, part.name)
            new_name = sanitize_name(choice.symbol_name if choice.symbol_name is not None else mpn).sanitized
            manufacturer_candidate = choice.manufacturer if choice.manufacturer is not None else ""
            fields = SymbolFields(
                footprint=footprints.links.get(part.key, part.footprint),
                filters=part.fields.get("ki_fp_filters", ""),
                manufacturer=canonical(manufacturer_candidate),
                manufacturer_forced=False,
                mpn=mpn,
                datasheet=choice.datasheet,
                description=choice.description,
            )
            edits, final_mpn, changes, _keywords = edit_symbol(
                work, ref, new_name, fields, source.version, MIGRATION_RULES
            )
            edits = [*edits, *rename_symbol_edits(work.root, part.name, new_name)]
            edited_text = apply_edits(work.source.text, edits)
            edited = _loaded_text(fsutil.encode_source(edited_text, work.source.bom), "the edited symbol")
            if isinstance(edited, Issue):
                issues.append(edited)
                continue
            placed = find_symbol(edited.root, new_name)
            if placed is None:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "migration.missing_symbol",
                        f"{new_name} was lost while editing it for {target}",
                    )
                )
                continue
            block = block_text(edited.source.text, placed.node)  # noqa: F841 (13-09 splices this in)

            # Tracer scope (plan 13-06 Task 1): one part per target, so the edited unit is the
            # whole library. 13-09 generalises this to splice additional parts in with
            # symbol_insert_edit when several parts and sources share one target.
            assembled = edited
            base_version = source.version

            footprint_new = footprints.links.get(part.key, part.footprint)
            field_changes = tuple(changes) + tuple(footprints.field_changes.get(part.key, ()))
            texts = footprints.texts.get(part.key, (PartText(), PartText()))
            part_plans.append(
                PartPlan(
                    key=part.key,
                    source_library=part.library,
                    target_library=target,
                    suggestion=ctx.suggestions.get(part.key),
                    old_name=part.name,
                    new_name=new_name,
                    mpn=final_mpn,
                    parent=families.derived.get(part.key),
                    footprint_old=part.footprint,
                    footprint_new=footprint_new,
                    footprint_target=footprints.targets.get(part.key, "official"),
                    model_files=footprints.models.get(part.key, ()),
                    field_changes=field_changes,
                    generated_text=texts[0],
                    part_text=texts[1],
                    issues=(),
                )
            )
            library_map.add((part.library, target))
            symbol_renames.append(Rename("symbol", f"{part.library}:{part.name}", f"{target}:{new_name}"))

        if assembled is not None:
            data = fsutil.encode_source(assembled.source.text, assembled.source.bom)
            ops.append(MigrationOp("write", target_path, target_rel, data=data, base_sha256=base_sha256))

    removed_libraries: list[str] = []
    for rel_path in sorted({part.rel_path for part in inventory.parts}):
        stem = Path(rel_path).stem
        if stem in by_target:
            # The source is overwritten in place under the same name; it is not "removed" separately.
            continue
        parts_of_lib = [part for part in inventory.parts if part.rel_path == rel_path]
        if parts_of_lib and all(targets.get(part.key, "") for part in parts_of_lib):
            path = layout.repo_root / rel_path
            ops.append(
                MigrationOp(
                    "delete",
                    path,
                    rel_path,
                    base_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    note="emptied v1 library",
                )
            )
            removed_libraries.append(rel_path)

    for part in inventory.parts:
        if targets.get(part.key, ""):
            continue
        choice = choices.parts.get(part.key, PartChoice())
        texts = footprints.texts.get(part.key, (PartText(), PartText()))
        part_plans.append(
            PartPlan(
                key=part.key,
                source_library=part.library,
                target_library="",
                suggestion=ctx.suggestions.get(part.key),
                old_name=part.name,
                new_name=choice.symbol_name or part.name,
                mpn=mpns.get(part.key, part.name),
                parent=families.derived.get(part.key),
                footprint_old=part.footprint,
                footprint_new=footprints.links.get(part.key, part.footprint),
                footprint_target=footprints.targets.get(part.key, "official"),
                model_files=footprints.models.get(part.key, ()),
                field_changes=(),
                generated_text=texts[0],
                part_text=texts[1],
                issues=(),
            )
        )

    return SymbolsOutcome(
        parts=tuple(part_plans),
        ops=tuple(ops),
        library_map=tuple(sorted(library_map)),
        symbol_renames=tuple(symbol_renames),
        removed_libraries=tuple(removed_libraries),
        issues=tuple(issues),
    )
