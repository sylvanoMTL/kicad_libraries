"""Plan the footprint side of the Atomic_ migration: move every shared footprint into Atomic_Footprints (D-15).

Thin for this plan (13-10 completes it): a footprint linked by a "shared" choice (the default) moves
into Custom/Footprints/Atomic_Footprints.pretty once, however many parts link it; an official link
(a library outside Custom) is kept untouched. Footprint description/tag generation and the leftover
and conflict rows are left for 13-10.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ... import fsutil
from ...kicad_files import footprint_name, footprint_name_edit, parse_bytes
from ...models import Issue
from ...sexpr import apply_edits
from ..plan import Conflict, FieldChange, PartText, Rename
from .inventory import SHARED_FOOTPRINT_LIBRARY, Inventory, InventoryFootprint
from .plan import MigrationChoices, MigrationOp, PartChoice, PartKey


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


def _renamed_footprint_bytes(layout, fp: InventoryFootprint) -> bytes:
    """fp's bytes, with its internal name set to the file stem when it differs (no other change yet)."""
    path = layout.repo_root / fp.rel_path
    data = path.read_bytes()
    loaded = parse_bytes(data, path.name)
    if isinstance(loaded, Issue):
        return data
    name_ref = footprint_name(loaded.root)
    if name_ref is None or name_ref.name == fp.name:
        return data
    edited = apply_edits(loaded.source.text, [footprint_name_edit(name_ref, fp.name)])
    return fsutil.encode_source(edited, loaded.source.bom)


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
    footprint_links: list[tuple[str, str]] = []
    ops: list[MigrationOp] = []
    removed_folders: list[str] = []
    issues: list[Issue] = []

    shared_dir = layout.footprints_dir / f"{SHARED_FOOTPRINT_LIBRARY}.pretty"
    shared_rel = _rel(layout, shared_dir)
    mkdir_added = shared_dir.exists()
    moved_from: dict[str, int] = {}

    for fp in inventory.footprints:
        if fp.library == SHARED_FOOTPRINT_LIBRARY:
            for key in fp.linked_by:
                links[key] = f"{SHARED_FOOTPRINT_LIBRARY}:{fp.name}"
                targets[key] = "shared"
            continue
        if not fp.linked_by:
            continue
        wants_move = any(
            choices.parts.get(key, PartChoice()).footprint_target == "shared" for key in fp.linked_by
        )
        if not wants_move:
            continue

        new_rel = f"{shared_rel}/{fp.name}.kicad_mod"
        new_path = layout.repo_root / new_rel
        data = _renamed_footprint_bytes(layout, fp)
        if not mkdir_added:
            ops.append(MigrationOp("mkdir", shared_dir, shared_rel, note="Atomic_Footprints folder"))
            mkdir_added = True
        existing_target_bytes = new_path.read_bytes() if new_path.exists() else None
        base_sha256 = hashlib.sha256(existing_target_bytes).hexdigest() if existing_target_bytes is not None else None
        ops.append(MigrationOp("write", new_path, new_rel, data=data, base_sha256=base_sha256))

        old_path = layout.repo_root / fp.rel_path
        ops.append(
            MigrationOp(
                "delete", old_path, fp.rel_path, base_sha256=fp.sha256, note="moved into Atomic_Footprints"
            )
        )
        footprint_links.append((f"{fp.library}:{fp.name}", f"{SHARED_FOOTPRINT_LIBRARY}:{fp.name}"))
        for key in fp.linked_by:
            links[key] = f"{SHARED_FOOTPRINT_LIBRARY}:{fp.name}"
            targets[key] = "shared"
        moved_from[fp.library] = moved_from.get(fp.library, 0) + 1

    for library in inventory.footprint_libraries:
        if library == SHARED_FOOTPRINT_LIBRARY:
            continue
        total = sum(1 for fp in inventory.footprints if fp.library == library)
        if total and moved_from.get(library, 0) == total:
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
        models={},
        targets=targets,
        ops=tuple(ops),
        footprint_links=tuple(footprint_links),
        model_renames=(),
        leftovers=(),
        conflicts=(),
        texts={},
        package_words={},
        field_changes={},
        removed_folders=tuple(removed_folders),
        issues=tuple(issues),
    )
