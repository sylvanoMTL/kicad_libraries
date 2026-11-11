"""Plan the footprint side of the Atomic_ migration (D-07..D-23): moves, clashes, official footprints,
model renames, multi-model footprints, leftovers, footprint text and added 3D models.

Every Custom footprint a "shared" part links (the default) moves into
Custom/Footprints/Atomic_Footprints.pretty once, however many parts link it; an official link (a
library outside Custom, D-08) is kept untouched and never written to. A footprint's single 3D model
is renamed to its first linking part's MPN (D-09); a footprint with several models keeps every file
under its own name (D-23). 13-10 (this plan) completes the module: 13-06 left clashes, leftovers,
footprint text and added models for later.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ... import fsutil
from ...kicad_files import (
    find_models,
    footprint_name,
    footprint_name_edit,
    load,
    parse_bytes,
    retarget_model,
)
from ...models import Issue, Severity
from ...sexpr import apply_edits
from ..footprint_index import build_index, pad_numbers
from ..naming import sanitize_filename
from ..plan import MODEL_DIR_VAR, Conflict, FieldChange, PartText, Rename
from ..verify import pin_pad_issues, symbol_pin_numbers
from .inventory import SHARED_FOOTPRINT_LIBRARY, Inventory, InventoryFootprint
from .plan import LeftoverRow, MigrationChoices, MigrationOp, PartChoice, PartKey

SHARED = SHARED_FOOTPRINT_LIBRARY
CLASH_PREFIX = "footprint:"
_MODEL_VAR_PREFIX = f"{MODEL_DIR_VAR}/"


@dataclass(frozen=True)
class FootprintsOutcome:
    """plan_footprints's result: where every part's footprint ends up, and the .pretty file operations."""

    links: Mapping[PartKey, str] = field(default_factory=dict)
    models: Mapping[PartKey, tuple[str, ...]] = field(default_factory=dict)
    targets: Mapping[PartKey, str] = field(default_factory=dict)
    ops: tuple[MigrationOp, ...] = ()
    footprint_links: tuple[tuple[str, str], ...] = ()
    model_renames: tuple[Rename, ...] = ()
    leftovers: tuple = ()
    conflicts: tuple[Conflict, ...] = ()
    texts: Mapping[PartKey, tuple[PartText, PartText]] = field(default_factory=dict)
    package_words: Mapping[PartKey, tuple[str, ...]] = field(default_factory=dict)
    field_changes: Mapping[PartKey, tuple[FieldChange, ...]] = field(default_factory=dict)
    removed_folders: tuple[str, ...] = ()
    issues: tuple[Issue, ...] = ()


def _rel(layout, path: Path) -> str:
    return path.relative_to(layout.repo_root).as_posix()


def _target_for(choices: MigrationChoices, key: PartKey) -> str:
    return choices.parts.get(key, PartChoice()).footprint_target


def _shared_linkers(fp: InventoryFootprint, choices: MigrationChoices) -> list[PartKey]:
    """fp's linking parts that still want the shared target, in part-key order."""
    return sorted(key for key in fp.linked_by if _target_for(choices, key) != "official")


def _loaded_footprint(data: bytes, name: str):
    """Parse one footprint's bytes; None on a parse failure (never raised)."""
    loaded = parse_bytes(data, name)
    return None if isinstance(loaded, Issue) else loaded


def _resolvable_models(loaded, model_name_set: frozenset[str]) -> list:
    """The footprint's own (model ...) refs whose path is a ${CUSTOM_3DMODEL_DIR}/ name on disk."""
    ref = footprint_name(loaded.root)
    if ref is None:
        return []
    refs = find_models(ref.node)
    return [
        r for r in refs
        if r.path.startswith(_MODEL_VAR_PREFIX) and r.path[len(_MODEL_VAR_PREFIX):] in model_name_set
    ]


def _model_name_of(path_text: str) -> str:
    return path_text[len(_MODEL_VAR_PREFIX):]


def _plain_move_bytes(path: Path, target_stem: str) -> bytes:
    """path's bytes, with its internal name set to target_stem when it differs (no other change)."""
    data = path.read_bytes()
    loaded = parse_bytes(data, path.name)
    if isinstance(loaded, Issue):
        return data
    name_ref = footprint_name(loaded.root)
    if name_ref is None or name_ref.name == target_stem:
        return data
    edited = apply_edits(loaded.source.text, [footprint_name_edit(name_ref, target_stem)])
    return fsutil.encode_source(edited, loaded.source.bom)


def _official_switch(
    part_rel_path: str,
    part_name: str,
    choice: PartChoice,
    ctx,
    *,
    symbol_cache: dict[str, object | None],
    repo_root: Path,
) -> tuple[str, list[Issue]]:
    """Resolve one part's "Use an official KiCad footprint" choice (D-08): (link, issues)."""
    link = choice.official_footprint or ""
    if not link:
        return "", [
            Issue(Severity.ERROR, "migration.official_missing", f"{part_name}: choose an official KiCad footprint")
        ]
    index = build_index(ctx.kicad_fp_dir)
    if not index.contains(link):
        return link, [
            Issue(Severity.ERROR, "migration.official_missing", f"{part_name}: {link} is not in KiCad's footprints")
        ]
    issues: list[Issue] = []
    pads = pad_numbers(index, link)
    if pads is not None:
        if part_rel_path not in symbol_cache:
            result = load(repo_root / part_rel_path)
            symbol_cache[part_rel_path] = None if isinstance(result, Issue) else result
        loaded = symbol_cache[part_rel_path]
        pins = symbol_pin_numbers(loaded.root, part_name) if loaded is not None else set()
        mismatch = pin_pad_issues(part_name, link, pins, pads)
        if mismatch:
            issues.append(Issue(Severity.WARNING, "migration.pad_mismatch", mismatch[0].text))
    return link, issues


def plan_footprints(
    inventory: Inventory,
    choices: MigrationChoices,
    ctx,
    *,
    mpns: Mapping[PartKey, str],
) -> FootprintsOutcome:
    """Move every Custom footprint a "shared" part links into Atomic_Footprints.pretty, once per footprint."""
    layout = inventory.layout
    links: dict[PartKey, str] = {}
    targets: dict[PartKey, str] = {}
    models: dict[PartKey, tuple[str, ...]] = {}
    footprint_links: list[tuple[str, str]] = []
    ops: list[MigrationOp] = []
    removed_folders: list[str] = []
    issues: list[Issue] = []
    model_renames: list[Rename] = []

    shared_dir = layout.footprints_dir / f"{SHARED}.pretty"
    shared_rel = _rel(layout, shared_dir)
    mkdir_added = shared_dir.exists()
    deleted_rels: set[str] = set()
    final_model_names: set[str] = set()

    model_name_set = frozenset(inventory.models)

    # -- Stage A: "Use an official KiCad footprint" (D-08) -- an active per-part choice, never an op
    # under KiCad's own folders; the vendor footprint and model this orphans become leftovers below.
    symbol_cache: dict[str, object | None] = {}
    for part in inventory.parts:
        choice = choices.parts.get(part.key, PartChoice())
        if choice.footprint_target != "official":
            continue
        link, official_issues = _official_switch(
            part.rel_path, part.name, choice, ctx, symbol_cache=symbol_cache, repo_root=layout.repo_root
        )
        issues.extend(official_issues)
        links[part.key] = link
        targets[part.key] = "official"

    # -- Pass 1: already-shared footprints are untouched; their linkers resolve directly (D-07) ----
    for fp in inventory.footprints:
        if fp.library != SHARED:
            continue
        if not _shared_linkers(fp, choices):
            continue
        for key in fp.linked_by:
            if _target_for(choices, key) == "official":
                continue
            links[key] = f"{SHARED}:{fp.name}"
            targets[key] = "shared"
            models[key] = fp.models
        final_model_names.update(fp.models)

    # -- Pass 2: plan each moved v1 footprint once, in key order of its first linker (determinism) --
    move_candidates: list[tuple[PartKey, InventoryFootprint, list[PartKey]]] = []
    for fp in inventory.footprints:
        if fp.library == SHARED:
            continue
        shared_linkers = _shared_linkers(fp, choices)
        if not shared_linkers:
            continue
        move_candidates.append((shared_linkers[0], fp, shared_linkers))
    move_candidates.sort(key=lambda item: item[0])

    # Model renames are decided once per *old* model file name, by the globally-first linking part,
    # so a model shared by two different footprints (P-07) is renamed only once (D-09).
    model_groups: dict[str, list[tuple[PartKey, InventoryFootprint]]] = {}
    footprint_models: dict[tuple[str, str], list] = {}
    footprint_loaded: dict[tuple[str, str], object] = {}

    for first_key, fp, _shared_linkers_list in move_candidates:
        path = layout.repo_root / fp.rel_path
        data = path.read_bytes()
        loaded = _loaded_footprint(data, path.name)
        footprint_loaded[(fp.library, fp.name)] = loaded
        if loaded is None:
            issues.append(Issue(Severity.ERROR, "migration.unreadable", f"Could not read {fp.rel_path}"))
            footprint_models[(fp.library, fp.name)] = []
            continue
        resolvable = _resolvable_models(loaded, model_name_set)
        footprint_models[(fp.library, fp.name)] = resolvable
        if len(resolvable) == 1:
            old_name = _model_name_of(resolvable[0].path)
            model_groups.setdefault(old_name, []).append((first_key, fp))

    # Decide the final name of every single-model group, by the smallest first-linker key.
    model_final_name: dict[str, str] = {}
    for old_name, group in model_groups.items():
        winner_key, winner_fp = min(group, key=lambda item: item[0])
        choice = choices.parts.get(winner_key, PartChoice())
        mpn = mpns.get(winner_key, "")
        stem = choice.model_name if choice.model_name else (mpn or None)
        if stem is None:
            model_final_name[old_name] = old_name
            continue
        ext = Path(old_name).suffix
        candidate = sanitize_filename(f"{stem}{ext}").sanitized
        if candidate.casefold() == old_name.casefold():
            # Case-only difference or no real change: keep the on-disk spelling (Phase 12 D-14).
            model_final_name[old_name] = old_name
            continue
        if candidate in model_name_set and candidate != old_name:
            issues.append(
                Issue(
                    Severity.INFO,
                    "migration.model_kept_name",
                    f"{old_name}: kept, {candidate} is already used by a different model",
                )
            )
            model_final_name[old_name] = old_name
            continue
        model_final_name[old_name] = candidate

    for old_name, new_name in model_final_name.items():
        if new_name == old_name:
            continue
        old_path = layout.models_dir / old_name
        new_path = layout.models_dir / new_name
        new_rel = _rel(layout, new_path)
        old_rel = _rel(layout, old_path)
        data = old_path.read_bytes()
        existing_bytes = new_path.read_bytes() if new_path.exists() else None
        base_sha256 = hashlib.sha256(existing_bytes).hexdigest() if existing_bytes is not None else None
        ops.append(MigrationOp("write", new_path, new_rel, data=data, base_sha256=base_sha256, source_rel=old_rel))
        ops.append(MigrationOp("delete", old_path, old_rel, base_sha256=hashlib.sha256(data).hexdigest()))
        model_renames.append(Rename("model", old_name, new_name))

    # -- Move each v1 footprint: rewrite its name and model paths, write once, link every linker ----
    for first_key, fp, shared_linkers_list in move_candidates:
        loaded = footprint_loaded.get((fp.library, fp.name))
        resolvable = footprint_models.get((fp.library, fp.name), [])

        choice = choices.parts.get(first_key, PartChoice())
        final_name = sanitize_filename((choice.footprint_name or fp.name) + ".kicad_mod").sanitized
        final_stem = final_name[: -len(".kicad_mod")] if final_name.endswith(".kicad_mod") else final_name

        edits = []
        own_model_names: list[str] = []
        if loaded is not None:
            name_ref = footprint_name(loaded.root)
            if name_ref is not None and name_ref.name != final_stem:
                edits.append(footprint_name_edit(name_ref, final_stem))
            for ref in resolvable:
                old_model_name = _model_name_of(ref.path)
                new_model_name = model_final_name.get(old_model_name, old_model_name)
                own_model_names.append(new_model_name)
                new_path_text = f"{MODEL_DIR_VAR}/{new_model_name}"
                if new_path_text != ref.path:
                    edits.append(retarget_model(ref, new_path_text))
            data = apply_edits(loaded.source.text, edits) if edits else loaded.source.text
            data_bytes = fsutil.encode_source(data, loaded.source.bom)
        else:
            data_bytes = (layout.repo_root / fp.rel_path).read_bytes()

        new_rel = f"{shared_rel}/{final_name}"
        new_path = layout.repo_root / new_rel
        if not mkdir_added:
            ops.append(MigrationOp("mkdir", shared_dir, shared_rel, note="Atomic_Footprints folder"))
            mkdir_added = True
        existing_target_bytes = new_path.read_bytes() if new_path.exists() else None
        base_sha256 = hashlib.sha256(existing_target_bytes).hexdigest() if existing_target_bytes is not None else None
        ops.append(MigrationOp("write", new_path, new_rel, data=data_bytes, base_sha256=base_sha256))

        old_path = layout.repo_root / fp.rel_path
        ops.append(
            MigrationOp(
                "delete", old_path, fp.rel_path, base_sha256=fp.sha256, note="moved into Atomic_Footprints"
            )
        )
        deleted_rels.add(fp.rel_path)
        footprint_links.append((f"{fp.library}:{fp.name}", f"{SHARED}:{final_stem}"))
        for key in shared_linkers_list:
            links[key] = f"{SHARED}:{final_stem}"
            targets[key] = "shared"
            models[key] = tuple(own_model_names)
        final_model_names.update(own_model_names)

    # -- Leftovers (D-10, D-21): every Custom footprint no planned part links, after all parts are
    # planned. default_keep is True only when the file was already unlinked before the migration;
    # a kept v1 footprint moves into Atomic_Footprints.pretty under its own name (Task 3 adds the
    # name-clash rules this move pathway shares with the main one). A kept footprint's own model(s)
    # are not auto-kept: a model's default follows its own original linkage, independently (D-10).
    leftover_rows: list[LeftoverRow] = []
    footprint_leftover_reason: dict[tuple[str, str], str] = {}

    for fp in inventory.footprints:
        if fp.library == SHARED:
            if _shared_linkers(fp, choices):
                continue
        elif fp.rel_path in deleted_rels:
            continue

        default_keep = not fp.linked_by
        if default_keep:
            reason = "no part links it"
        else:
            cause_key = sorted(fp.linked_by)[0]
            reason = f"no part links it after the switch to {links.get(cause_key, '')}"
        footprint_leftover_reason[(fp.library, fp.name)] = reason

        rel = fp.rel_path
        keep = choices.leftovers.get(rel, default_keep)
        leftover_rows.append(LeftoverRow(rel=rel, kind="footprint", keep=keep, default_keep=default_keep, reason=reason))

        if fp.library == SHARED:
            if not keep:
                ops.append(
                    MigrationOp(
                        "delete", layout.repo_root / rel, rel, base_sha256=fp.sha256, note="leftover, not kept"
                    )
                )
                deleted_rels.add(rel)
            continue

        old_path = layout.repo_root / rel
        if not keep:
            ops.append(MigrationOp("delete", old_path, rel, base_sha256=fp.sha256, note="leftover, not kept"))
            deleted_rels.add(rel)
            continue

        data = _plain_move_bytes(old_path, fp.name)
        new_rel = f"{shared_rel}/{fp.name}.kicad_mod"
        new_path = layout.repo_root / new_rel
        if not mkdir_added:
            ops.append(MigrationOp("mkdir", shared_dir, shared_rel, note="Atomic_Footprints folder"))
            mkdir_added = True
        existing_bytes = new_path.read_bytes() if new_path.exists() else None
        base_sha256 = hashlib.sha256(existing_bytes).hexdigest() if existing_bytes is not None else None
        ops.append(MigrationOp("write", new_path, new_rel, data=data, base_sha256=base_sha256))
        ops.append(MigrationOp("delete", old_path, rel, base_sha256=fp.sha256, note="moved into Atomic_Footprints"))
        deleted_rels.add(rel)

    models_rel_dir = _rel(layout, layout.models_dir)
    for name in inventory.models:
        # model_final_name's *keys* are old model names tied to a moving footprint's single model
        # (whether renamed or not); final_model_names holds every moved footprint's final name(s).
        # A renamed model's old name is in the former but not the latter, and must not re-enter here.
        if name in final_model_names or name in model_final_name:
            continue
        linkers = inventory.model_linkers.get(name, ())
        default_keep = not linkers
        if default_keep:
            reason = "no footprint links it"
        else:
            cause_lib, _, cause_fp = linkers[0].partition(":")
            reason = footprint_leftover_reason.get((cause_lib, cause_fp), "no footprint links it")
        rel = f"{models_rel_dir}/{name}"
        keep = choices.leftovers.get(rel, default_keep)
        leftover_rows.append(LeftoverRow(rel=rel, kind="model", keep=keep, default_keep=default_keep, reason=reason))
        if not keep:
            path = layout.models_dir / name
            ops.append(
                MigrationOp(
                    "delete", path, rel, base_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    note="leftover, not kept",
                )
            )

    for library in inventory.footprint_libraries:
        if library == SHARED:
            continue
        library_footprints = [fp for fp in inventory.footprints if fp.library == library]
        if library_footprints and all(fp.rel_path in deleted_rels for fp in library_footprints):
            folder = layout.footprints_dir / f"{library}.pretty"
            folder_rel = _rel(layout, folder)
            removed_folders.append(folder_rel)
            ops.append(MigrationOp("rmdir", folder, folder_rel, note="emptied v1 footprint folder"))

    for part in inventory.parts:
        if part.key not in links:
            links[part.key] = part.footprint
            targets[part.key] = "official"

    return FootprintsOutcome(
        links=links,
        models=models,
        targets=targets,
        ops=tuple(ops),
        footprint_links=tuple(footprint_links),
        model_renames=tuple(model_renames),
        leftovers=tuple(leftover_rows),
        conflicts=(),
        texts={},
        package_words={},
        field_changes={},
        removed_folders=tuple(removed_folders),
        issues=tuple(issues),
    )
