"""Plan the symbol side of the Atomic_ migration: who moves where, under what name (D-01, D-04, D-07).

One source file is loaded once per library; a part's unit is normalised with the importer's own
new_source/existing_source and edited with edit_symbol, then spliced into the target library text
being assembled (several parts and sources can share one target, D-01 "an old library can be
split"). A chosen or suggested target that fails stems.name_verdict blocks that one part with
migration.no_library (D-01); a part already in its own target Atomic_ library is rewritten in
place, never duplicated (D-03).
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
    find_symbols,
    parse_bytes,
    rename_symbol_edits,
    symbol_insert_edit,
    symbol_unit,
    unit_library_text,
)
from ...manufacturers import canonical
from ...models import Issue, Severity
from .. import stems
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

    # D-01: a chosen or suggested target that stems.name_verdict refuses blocks that one part;
    # it never becomes a real target (no op is planned for it, as if it were still undecided).
    refused: dict[PartKey, str] = {}
    by_target: dict[str, list[InventoryPart]] = {}
    for part in inventory.parts:
        target = targets.get(part.key, "")
        if not target:
            continue
        # ctx.allowed empty means "use the built-in KiCad 10 snapshot" (ToolContext.allowed_stems'
        # own documented default); name_verdict only applies that fallback for None, not "".
        verdict = stems.name_verdict(target, ctx.allowed or None)
        if verdict.ok:
            by_target.setdefault(target, []).append(part)
        else:
            refused[part.key] = verdict.reason

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
            # D-03: a part already in this exact target library is rewritten in place, not
            # duplicated. Every symbol of this file that is itself migrating in this pass (staying
            # here or being replaced by its own edited block below) is dropped from the preseed; any
            # symbol that is not part of this migration at all (foreign content) survives untouched.
            migrating_here = {part.name for part in by_target[target] if part.rel_path == target_rel}
            existing_names = {ref.name for ref in find_symbols(loaded_target.root)}
            keep_names = existing_names - migrating_here
            if keep_names:
                if keep_names != existing_names:
                    stripped = unit_library_text(loaded_target, keep=keep_names)
                    reparsed = _loaded_text(fsutil.encode_source(stripped, loaded_target.source.bom), target_path.name)
                    if isinstance(reparsed, Issue):
                        issues.append(reparsed)
                        continue
                    loaded_target = reparsed
                assembled = loaded_target
                base_version = file_version(assembled.root)
            # else: every existing symbol of this file is migrating in this same pass; nothing
            # survives to preseed, so this target starts fresh (assembled stays None below).

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
            # D-01, D-12: the owner's typed manufacturer always wins (forced); without one, the vendor's
            # own Manufacturer or SnapEDA MF value is the fallback, spelled canonically either way.
            manufacturer_value = (
                choice.manufacturer
                if choice.manufacturer is not None
                else (part.fields.get("Manufacturer") or part.fields.get("MF") or "")
            )
            fields = SymbolFields(
                footprint=footprints.links.get(part.key, part.footprint),
                filters=part.fields.get("ki_fp_filters", ""),
                manufacturer=canonical(manufacturer_value),
                manufacturer_forced=choice.manufacturer is not None,
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
            block = block_text(edited.source.text, placed.node)

            if assembled is None:
                # The first part for a brand-new target: the edited unit is the whole library.
                assembled = edited
                base_version = source.version
            else:
                # Every later part (several parts/sources sharing one target, or a target that
                # already existed on disk): splice its block in after the last symbol (D-01).
                insert_edit = symbol_insert_edit(assembled, block)
                assembled_text = apply_edits(assembled.source.text, [insert_edit])
                reparsed = _loaded_text(fsutil.encode_source(assembled_text, assembled.source.bom), target_path.name)
                if isinstance(reparsed, Issue):
                    issues.append(reparsed)
                    continue
                assembled = reparsed

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

    def _really_moves(part: InventoryPart) -> bool:
        """True only for a part with a usable (valid, non-refused) target."""
        target = targets.get(part.key, "")
        return bool(target) and part.key not in refused

    removed_libraries: list[str] = []
    for rel_path in sorted({part.rel_path for part in inventory.parts}):
        stem = Path(rel_path).stem
        if stem in by_target:
            # The source is overwritten in place under the same name; it is not "removed" separately.
            continue
        parts_of_lib = [part for part in inventory.parts if part.rel_path == rel_path]
        if parts_of_lib and all(_really_moves(part) for part in parts_of_lib):
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
        if _really_moves(part):
            continue
        target = targets.get(part.key, "")
        choice = choices.parts.get(part.key, PartChoice())
        texts = footprints.texts.get(part.key, (PartText(), PartText()))
        part_issues: tuple[Issue, ...] = ()
        if part.key in refused:
            part_issues = (Issue(Severity.ERROR, "migration.no_library", refused[part.key]),)
        part_plans.append(
            PartPlan(
                key=part.key,
                source_library=part.library,
                target_library=target,
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
                issues=part_issues,
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
