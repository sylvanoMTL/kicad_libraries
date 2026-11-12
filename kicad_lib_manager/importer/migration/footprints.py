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
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath

from ... import fsutil
from ...kicad_files import (
    find_models,
    footprint_name,
    footprint_name_edit,
    footprint_text_edit,
    load,
    model_insert_edit,
    parse_bytes,
    retarget_model,
)
from ...models import Issue, Severity
from ...sexpr import apply_edits, token_stream
from ..footprint_index import build_index, pad_numbers
from ..footprint_text import describe, footprint_facts, generated_tags, vendor_texts
from ..keywords import manufacturer_words, merge_words
from ..naming import sanitize_filename, sanitize_name
from ..package import MAX_MEMBER_BYTES, open_model_source
from ..plan import MODEL_DIR_VAR, Conflict, FieldChange, PartText, Rename, Resolution
from ..planner import suggest_free_name
from ..verify import pin_pad_issues, symbol_pin_numbers
from .inventory import SHARED_FOOTPRINT_LIBRARY, Inventory, InventoryFootprint, InventoryPart
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


def _renamed_bytes(data: bytes, filename: str, target_stem: str) -> bytes:
    """data's bytes, with the footprint's internal name set to target_stem when it differs."""
    loaded = parse_bytes(data, filename)
    if isinstance(loaded, Issue):
        return data
    name_ref = footprint_name(loaded.root)
    if name_ref is None or name_ref.name == target_stem:
        return data
    edited = apply_edits(loaded.source.text, [footprint_name_edit(name_ref, target_stem)])
    return fsutil.encode_source(edited, loaded.source.bom)


def _plain_move_bytes(path: Path, target_stem: str) -> bytes:
    """path's bytes, with its internal name set to target_stem when it differs (no other change)."""
    return _renamed_bytes(path.read_bytes(), path.name, target_stem)


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


def _same_footprint_tokens(a: bytes, b: bytes, filename: str) -> bool:
    """True when a and b are byte-equal, or parse to the same token stream (D-19)."""
    if a == b:
        return True
    parsed_a, parsed_b = parse_bytes(a, filename), parse_bytes(b, filename)
    if isinstance(parsed_a, Issue) or isinstance(parsed_b, Issue):
        return False
    return token_stream(parsed_a.root) == token_stream(parsed_b.root)


def _suggest_clash_name(stem: str, mpn: str, taken_stems: set[str]) -> str:
    """<stem>_<mpn>, or the next free <stem>_<n> when that is taken or mpn is blank (D-19)."""
    if not mpn:
        return suggest_free_name(stem, taken_stems, casefold=True)
    base = sanitize_name(f"{stem}_{mpn}").sanitized
    if base.casefold() not in {name.casefold() for name in taken_stems}:
        return base
    return suggest_free_name(base, taken_stems, casefold=True)


def _resolve_clash(
    *,
    wanted_filename: str,
    data: bytes,
    shared_dir: Path,
    known: dict[str, bytes],
    taken_stems: set[str],
    resolutions: Mapping[str, Resolution],
    mpn: str,
    queued: set[str],
) -> tuple[str, bytes | None, Conflict | None, list[Issue]]:
    """Settle one footprint's name against Atomic_Footprints.pretty (D-07, Phase 10 D-19).

    Returns (final stem, bytes to write (None = reuse, nothing to write), conflict, issues).

    `queued` holds the casefolded filenames this run has already queued a write op for (gap
    CR-01); both call sites add to it after emitting a write. When the owner chooses Overwrite for
    a name already in `queued`, that name is this run's OWN new footprint for another part, not an
    on-disk file -- overwriting it would queue a second write op for the same path, so it is
    refused instead (migration.overwrite_refused).
    """
    if wanted_filename not in known:
        existing_path = shared_dir / wanted_filename
        if existing_path.exists():
            known[wanted_filename] = existing_path.read_bytes()
    stem = wanted_filename[: -len(".kicad_mod")] if wanted_filename.endswith(".kicad_mod") else wanted_filename
    if wanted_filename not in known:
        known[wanted_filename] = data
        taken_stems.add(stem)
        return stem, data, None, []
    existing_bytes = known[wanted_filename]
    if _same_footprint_tokens(data, existing_bytes, wanted_filename):
        return stem, None, None, []

    key = CLASH_PREFIX + stem
    suggested = _suggest_clash_name(stem, mpn, taken_stems)
    base_conflict = Conflict(
        key=key,
        kind="footprint",
        name=stem,
        existing=f"Atomic_Footprints already holds {wanted_filename} with different content",
        suggested_name=suggested,
    )
    resolution = resolutions.get(key)
    if resolution is None:
        return stem, None, base_conflict, [
            Issue(
                Severity.ERROR,
                "migration.conflict_unresolved",
                f"{stem} is already in Atomic_Footprints with different content. Choose Overwrite, Rename or Skip.",
            )
        ]
    resolved = replace(base_conflict, resolution=resolution)
    if resolution.action == "overwrite":
        if wanted_filename.casefold() in queued:
            return stem, None, resolved, [
                Issue(
                    Severity.ERROR,
                    "migration.overwrite_refused",
                    f"{wanted_filename} is the footprint this migration is already creating for "
                    "another part; choose Rename or Skip instead",
                )
            ]
        known[wanted_filename] = data
        return stem, data, resolved, []
    if resolution.action == "skip":
        return stem, None, resolved, []

    chosen = resolution.rename_to if resolution.rename_to else suggested
    new_filename = sanitize_filename(chosen + ".kicad_mod").sanitized
    new_stem = new_filename[: -len(".kicad_mod")] if new_filename.endswith(".kicad_mod") else new_filename
    if new_filename in known or (shared_dir / new_filename).exists():
        existing2 = known.get(new_filename)
        if existing2 is None:
            existing2 = (shared_dir / new_filename).read_bytes()
            known[new_filename] = existing2
        if _same_footprint_tokens(data, existing2, new_filename):
            return new_stem, None, resolved, []
        return stem, None, resolved, [
            Issue(
                Severity.ERROR,
                "migration.conflict_unresolved",
                f"{stem}: {new_filename} is already taken; choose another name",
            )
        ]
    known[new_filename] = data
    taken_stems.add(new_stem)
    return new_stem, data, resolved, []


def _open_added_model(source: str, repo_root: Path) -> tuple[str, bytes, list[Issue]]:
    """Open an owner-added 3D model source through the importer's intake checks (D-15).

    Follows atomic_fixes._open_model's pattern (one member, size cap, sha256 re-check);
    returns ("", b"", issues) on any refusal.
    """
    issues: list[Issue] = []
    package = open_model_source(Path(source), repo_root)
    try:
        if package.refused:
            issues.extend(i for i in package.issues if i.severity is Severity.ERROR)
            return "", b"", [Issue(Severity.ERROR, "migration.model_unreadable", i.text) for i in issues]
        if len(package.files) != 1 or package.files[0].kind != "model":
            return "", b"", [
                Issue(Severity.ERROR, "migration.model_unreadable", f"{Path(source).name} must be one 3D model file")
            ]
        entry = package.files[0]
        name = PurePosixPath(entry.member.replace("\\", "/")).name
        try:
            with open(entry.path, "rb") as handle:
                data = handle.read(MAX_MEMBER_BYTES + 1)
        except OSError as e:
            return "", b"", [
                Issue(Severity.ERROR, "migration.model_unreadable", f"Could not read {name} ({e.strerror or e})")
            ]
        if len(data) > MAX_MEMBER_BYTES or hashlib.sha256(data).hexdigest() != entry.sha256:
            return "", b"", [
                Issue(Severity.ERROR, "migration.model_unreadable", f"{name} changed while it was read; choose it again")
            ]
        return name, data, []
    finally:
        package.close()


def _model_final_names(
    model_groups: Mapping[str, list],
    choices: MigrationChoices,
    mpns: Mapping[PartKey, str],
    model_name_set: frozenset[str],
) -> tuple[dict[str, str], list[Issue]]:
    """Decide every single-model group's final name; no two groups may ever claim one file name.

    Walks sorted(model_groups.items()) so the first claimer is deterministic across runs. `claimed`
    is this run's own growing name registry (casefolded candidate -> the old_name that claimed it,
    gap CR-01): a later group whose candidate collides with an earlier claim keeps its own old name,
    and the earlier claimer's final name is reset back to its old name too, so the colliding pair
    never both end up pointing at the same file. Exactly one migration.model_clash ERROR is raised
    per colliding candidate, however many groups want it.
    """
    model_final_name: dict[str, str] = {}
    issues: list[Issue] = []
    claimed: dict[str, str] = {}
    clashed: set[str] = set()
    model_names_cf = {name.casefold() for name in model_name_set}

    for old_name, group in sorted(model_groups.items()):
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
        if candidate.casefold() in model_names_cf:
            issues.append(
                Issue(
                    Severity.INFO,
                    "migration.model_kept_name",
                    f"{old_name}: kept, {candidate} is already used by a different model",
                )
            )
            model_final_name[old_name] = old_name
            continue

        claim_key = candidate.casefold()
        claiming_old_name = claimed.get(claim_key)
        if claiming_old_name is not None and claiming_old_name != old_name:
            model_final_name[old_name] = old_name
            model_final_name[claiming_old_name] = claiming_old_name
            if claim_key not in clashed:
                first_name, second_name = sorted((claiming_old_name, old_name))
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "migration.model_clash",
                        f"{first_name} and {second_name} would both be renamed to {candidate}; "
                        "give one of them a different 3D model name",
                    )
                )
                clashed.add(claim_key)
            continue

        claimed[claim_key] = old_name
        model_final_name[old_name] = candidate

    return model_final_name, issues


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
    conflicts: list[Conflict] = []
    texts: dict[PartKey, tuple[PartText, PartText]] = {}
    package_words: dict[PartKey, tuple[str, ...]] = {}
    field_changes: dict[PartKey, tuple[FieldChange, ...]] = {}

    shared_dir = layout.footprints_dir / f"{SHARED}.pretty"
    shared_rel = _rel(layout, shared_dir)
    mkdir_added = shared_dir.exists()
    deleted_rels: set[str] = set()
    final_model_names: set[str] = set()
    part_index: dict[PartKey, InventoryPart] = {part.key: part for part in inventory.parts}

    try:
        shared_taken_stems: set[str] = {p.stem for p in shared_dir.glob("*.kicad_mod")}
    except OSError:
        shared_taken_stems = set()
    shared_known: dict[str, bytes] = {}
    # Casefolded filenames this run has already queued a write op for (gap CR-01, D-07): both
    # _resolve_clash call sites add to this after emitting a write, so an Overwrite choice made for
    # a name this run is also creating for another part is refused rather than queuing a second
    # write op for the same path.
    queued: set[str] = set()

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

    # Decide the final name of every single-model group, by the smallest first-linker key; the
    # helper owns the claimed-name registry so two groups can never both claim one file (gap CR-01).
    model_final_name, model_final_issues = _model_final_names(model_groups, choices, mpns, model_name_set)
    issues.extend(model_final_issues)

    # The registry an owner-added model (D-15) must not collide with: every pre-migration model
    # name, plus every final name the rename pass above just assigned. Grown in place as this run's
    # own added models claim a name, so a second added model cannot take the first one's name either.
    claimed_model_names: set[str] = {name.casefold() for name in model_name_set}
    claimed_model_names.update(new_name.casefold() for new_name in model_final_name.values())

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
        wanted_name = sanitize_filename((choice.footprint_name or fp.name) + ".kicad_mod").sanitized
        wanted_stem = wanted_name[: -len(".kicad_mod")] if wanted_name.endswith(".kicad_mod") else wanted_name
        name_ref = footprint_name(loaded.root) if loaded is not None else None

        edits = []
        own_model_names: list[str] = []
        if name_ref is not None and name_ref.name != wanted_stem:
            edits.append(footprint_name_edit(name_ref, wanted_stem))
        for ref in resolvable:
            old_model_name = _model_name_of(ref.path)
            new_model_name = model_final_name.get(old_model_name, old_model_name)
            own_model_names.append(new_model_name)
            new_path_text = f"{MODEL_DIR_VAR}/{new_model_name}"
            if new_path_text != ref.path:
                edits.append(retarget_model(ref, new_path_text))

        # Added 3D model (D-15): only when the footprint carries none of its own to resolve.
        if name_ref is not None and not resolvable and choice.model_source:
            model_file_name, model_data, added_model_issues = _open_added_model(
                choice.model_source, layout.repo_root
            )
            issues.extend(added_model_issues)
            if model_file_name:
                mpn = mpns.get(first_key, "")
                ext = Path(model_file_name).suffix
                stem = choice.model_name if choice.model_name else (mpn or Path(model_file_name).stem)
                new_model_name = sanitize_filename(f"{stem}{ext}").sanitized
                claim_key = new_model_name.casefold()
                if claim_key in claimed_model_names:
                    issues.append(
                        Issue(
                            Severity.ERROR,
                            "migration.model_clash",
                            f"{new_model_name} is already the 3D model file name of another part; "
                            "choose a different 3D model name",
                        )
                    )
                else:
                    claimed_model_names.add(claim_key)
                    own_model_names.append(new_model_name)
                    model_path = layout.models_dir / new_model_name
                    model_rel = _rel(layout, model_path)
                    existing_model_bytes = model_path.read_bytes() if model_path.exists() else None
                    model_base_sha256 = (
                        hashlib.sha256(existing_model_bytes).hexdigest() if existing_model_bytes is not None else None
                    )
                    ops.append(
                        MigrationOp("write", model_path, model_rel, data=model_data, base_sha256=model_base_sha256)
                    )
                    edits.append(
                        model_insert_edit(
                            loaded.source.text, name_ref.node, f"{MODEL_DIR_VAR}/{new_model_name}", loaded.source.eol
                        )
                    )
                    final_model_names.add(new_model_name)

        # Footprint text (D-11): the description is always regenerated, tags merged; never on an
        # official footprint (those never reach this loop at all).
        field_change_list: list[FieldChange] = []
        package_word_list: tuple[str, ...] = ()
        generated_text = PartText()
        written_text = PartText()
        if name_ref is not None:
            old_descr, old_tags = vendor_texts(name_ref.node)
            first_part = part_index.get(first_key)
            manufacturer = first_part.fields.get("Manufacturer", "") if first_part is not None else ""
            maker_list = manufacturer_words(manufacturer)
            facts = footprint_facts(name_ref.node, code=fp.name, maker=maker_list[0] if maker_list else "")
            package_word_list = tuple(word for word in (facts.family, fp.name) if word)
            generated_description = describe(facts)
            generated_tags_text = merge_words(old_tags, generated_tags(facts))
            written_description = choice.fp_description if choice.fp_description is not None else generated_description
            written_tags = choice.fp_tags if choice.fp_tags is not None else generated_tags_text
            generated_text = PartText(fp_description=generated_description, fp_tags=generated_tags_text)
            written_text = PartText(fp_description=written_description, fp_tags=written_tags)
            if written_description != old_descr:
                edits.append(
                    footprint_text_edit(loaded.source.text, name_ref.node, "descr", written_description, loaded.source.eol)
                )
                field_change_list.append(
                    FieldChange(
                        symbol=wanted_stem, action="set", field="descr", old=old_descr,
                        new=written_description, reason="generated", scope="footprint",
                    )
                )
            if written_tags != old_tags:
                edits.append(
                    footprint_text_edit(loaded.source.text, name_ref.node, "tags", written_tags, loaded.source.eol)
                )
                field_change_list.append(
                    FieldChange(
                        symbol=wanted_stem, action="set", field="tags", old=old_tags,
                        new=written_tags, reason="generated", scope="footprint",
                    )
                )

        if loaded is not None:
            data = apply_edits(loaded.source.text, edits) if edits else loaded.source.text
            data_bytes = fsutil.encode_source(data, loaded.source.bom)
        else:
            data_bytes = (layout.repo_root / fp.rel_path).read_bytes()

        if not mkdir_added:
            ops.append(MigrationOp("mkdir", shared_dir, shared_rel, note="Atomic_Footprints folder"))
            mkdir_added = True

        resolved_stem, write_data, conflict, clash_issues = _resolve_clash(
            wanted_filename=wanted_name,
            data=data_bytes,
            shared_dir=shared_dir,
            known=shared_known,
            taken_stems=shared_taken_stems,
            resolutions=choices.resolutions,
            mpn=mpns.get(first_key, ""),
            queued=queued,
        )
        issues.extend(clash_issues)
        if conflict is not None:
            conflicts.append(conflict)
        if write_data is not None:
            if resolved_stem != wanted_stem:
                write_data = _renamed_bytes(write_data, wanted_name, resolved_stem)
            new_rel = f"{shared_rel}/{resolved_stem}.kicad_mod"
            new_path = layout.repo_root / new_rel
            existing_target_bytes = new_path.read_bytes() if new_path.exists() else None
            base_sha256 = hashlib.sha256(existing_target_bytes).hexdigest() if existing_target_bytes is not None else None
            ops.append(MigrationOp("write", new_path, new_rel, data=write_data, base_sha256=base_sha256))
            queued.add(f"{resolved_stem}.kicad_mod".casefold())

        old_path = layout.repo_root / fp.rel_path
        ops.append(
            MigrationOp(
                "delete", old_path, fp.rel_path, base_sha256=fp.sha256, note="moved into Atomic_Footprints"
            )
        )
        deleted_rels.add(fp.rel_path)
        footprint_links.append((f"{fp.library}:{fp.name}", f"{SHARED}:{resolved_stem}"))
        for key in shared_linkers_list:
            links[key] = f"{SHARED}:{resolved_stem}"
            targets[key] = "shared"
            models[key] = tuple(own_model_names)
            if field_change_list:
                field_changes[key] = tuple(field_change_list)
            if package_word_list:
                package_words[key] = package_word_list
            if name_ref is not None:
                texts[key] = (generated_text, written_text)
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
        wanted_name = f"{fp.name}.kicad_mod"
        if not mkdir_added:
            ops.append(MigrationOp("mkdir", shared_dir, shared_rel, note="Atomic_Footprints folder"))
            mkdir_added = True
        resolved_stem, write_data, conflict, clash_issues = _resolve_clash(
            wanted_filename=wanted_name,
            data=data,
            shared_dir=shared_dir,
            known=shared_known,
            taken_stems=shared_taken_stems,
            resolutions=choices.resolutions,
            mpn="",
            queued=queued,
        )
        issues.extend(clash_issues)
        if conflict is not None:
            conflicts.append(conflict)
        if write_data is not None:
            if resolved_stem != fp.name:
                write_data = _renamed_bytes(write_data, wanted_name, resolved_stem)
            new_rel = f"{shared_rel}/{resolved_stem}.kicad_mod"
            new_path = layout.repo_root / new_rel
            existing_bytes = new_path.read_bytes() if new_path.exists() else None
            base_sha256 = hashlib.sha256(existing_bytes).hexdigest() if existing_bytes is not None else None
            ops.append(MigrationOp("write", new_path, new_rel, data=write_data, base_sha256=base_sha256))
            queued.add(f"{resolved_stem}.kicad_mod".casefold())
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
        conflicts=tuple(conflicts),
        texts=texts,
        package_words=package_words,
        field_changes=field_changes,
        removed_folders=tuple(removed_folders),
        issues=tuple(issues),
    )
