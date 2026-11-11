"""Read side of the Atomic_ migration: every existing part, footprint, model and backup (MIG-02, MIG-03, D-13).

read_inventory() parses every library and footprint of Custom/ once, under the same size and node
caps the importer uses, so an oversized or unparsable file becomes one ERROR Issue instead of a
crash or a silent drop (T-13-13). Listings never follow a symlink or a junction out of Custom
(T-13-14). migration_reason() is listing-only and parses nothing, so the Migrate menu's enable
check stays cheap (D-13).
"""

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ... import kicad_files
from ...atomic_check import ATOMIC_PREFIX, is_atomic
from ...models import Issue, Severity
from ..layout import RepoLayout
from ..package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES
from .plan import PartKey

_SYM_SUFFIX = ".kicad_sym"
_BAK_SUFFIX = ".bak"
_PRETTY_SUFFIX = ".pretty"
_MOD_SUFFIX = ".kicad_mod"
_MODEL_VAR_PREFIX = "${CUSTOM_3DMODEL_DIR}/"
# Not importer.stems.SHARED_FOOTPRINT_LIBRARY: stems is outside this module's ALLOWED import set (plan 13-03)
SHARED_FOOTPRINT_LIBRARY = ATOMIC_PREFIX + "Footprints"

# Skip a symlink or a junction wherever this module lists a folder (T-13-14); junctions are
# Windows-only, so the fallback never refuses anything on a platform without them.
_is_junction = getattr(os.path, "isjunction", lambda path: False)


@dataclass(frozen=True)
class InventoryPart:
    """One top-level symbol of a Custom/ library, exactly as it reads today."""

    key: PartKey
    library: str
    rel_path: str
    name: str
    extends: str | None
    fields: Mapping[str, str]
    footprint: str
    version: int | None
    block_sha256: str
    atomic: bool


@dataclass(frozen=True)
class InventoryFootprint:
    """One .kicad_mod of a Custom/ .pretty folder, with the models and parts that link it."""

    library: str
    name: str
    rel_path: str
    internal_name: str
    models: tuple[str, ...]
    sha256: str
    linked_by: tuple[PartKey, ...]


@dataclass(frozen=True)
class Inventory:
    """Everything read_inventory found under one Custom/."""

    layout: RepoLayout
    parts: tuple[InventoryPart, ...]
    footprints: tuple[InventoryFootprint, ...]
    # Every file under Custom/3DModels, as its path relative to that folder (posix, exact case)
    models: tuple[str, ...]
    model_linkers: Mapping[str, tuple[str, ...]]
    # Repo-relative posix paths of every *.bak in Custom/Symbols
    bak_files: tuple[str, ...]
    symbol_libraries: tuple[str, ...]
    footprint_libraries: tuple[str, ...]
    issues: tuple[Issue, ...]


def _real_children(folder: Path) -> list[Path]:
    """Direct children of folder, skipping symlinks and junctions; [] when folder is missing or unreadable."""
    try:
        children = list(folder.iterdir())
    except OSError:
        return []
    return [p for p in children if not p.is_symlink() and not _is_junction(p)]


def _safe_walk(folder: Path) -> list[Path]:
    """Every file below folder, recursively, skipping symlinks and junctions."""
    found: list[Path] = []
    stack = [folder]
    while stack:
        for child in _real_children(stack.pop()):
            if child.is_dir():
                stack.append(child)
            elif child.is_file():
                found.append(child)
    return found


def _rel(layout: RepoLayout, path: Path) -> str:
    return path.relative_to(layout.repo_root).as_posix()


def _read_bounded(path: Path) -> bytes | Issue:
    """Read path's bytes, refusing anything over MAX_KICAD_TEXT_BYTES without holding the excess in memory."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_KICAD_TEXT_BYTES + 1)
    except OSError as e:
        return Issue(Severity.ERROR, "migration.unreadable", f"Could not read {path.name}: {e.strerror or e}")
    if len(data) > MAX_KICAD_TEXT_BYTES:
        return Issue(
            Severity.ERROR,
            "migration.unreadable",
            f"Could not read {path.name}: it is larger than {MAX_KICAD_TEXT_BYTES} bytes",
        )
    return data


def _load_bounded(path: Path) -> kicad_files.LoadedFile | Issue:
    """Read and parse path under the importer's size and node caps; any failure becomes one migration.unreadable ERROR."""
    data = _read_bounded(path)
    if isinstance(data, Issue):
        return data
    loaded = kicad_files.parse_bytes(data, path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return Issue(Severity.ERROR, "migration.unreadable", f"Could not read {path.name}: {loaded.text}")
    return loaded


def _model_rel(path_text: str) -> str | None:
    """The exact name of a model path written as ${CUSTOM_3DMODEL_DIR}/<name>, or None for any other form."""
    if path_text.startswith(_MODEL_VAR_PREFIX):
        return path_text[len(_MODEL_VAR_PREFIX):]
    return None


def _split_link(footprint_field: str) -> tuple[str, str] | None:
    """A symbol's Footprint field as (library, name), or None when it is empty or not Lib:FP."""
    if not footprint_field or ":" not in footprint_field:
        return None
    library, _, name = footprint_field.partition(":")
    if not library or not name:
        return None
    return library, name


def _symbol_libraries(layout: RepoLayout) -> list[Path]:
    return sorted(
        (p for p in _real_children(layout.symbols_dir) if p.is_file() and p.suffix.casefold() == _SYM_SUFFIX),
        key=lambda p: (p.stem.casefold(), p.stem),
    )


def _bak_paths(layout: RepoLayout) -> list[Path]:
    return sorted(
        (p for p in _real_children(layout.symbols_dir) if p.is_file() and p.suffix.casefold() == _BAK_SUFFIX),
        key=lambda p: (p.name.casefold(), p.name),
    )


def _pretty_dirs(layout: RepoLayout) -> list[Path]:
    return sorted(
        (p for p in _real_children(layout.footprints_dir) if p.is_dir() and p.suffix.casefold() == _PRETTY_SUFFIX),
        key=lambda p: (p.stem.casefold(), p.stem),
    )


def read_inventory(layout: RepoLayout) -> Inventory:
    """Parse every Custom/ symbol library, footprint and model, and list every *.bak (MIG-02, MIG-03)."""
    issues: list[Issue] = []

    sym_paths = _symbol_libraries(layout)
    bak_files = tuple(sorted(_rel(layout, p) for p in _bak_paths(layout)))
    symbol_libraries = tuple(p.stem for p in sym_paths)

    pretty_dirs = _pretty_dirs(layout)
    footprint_libraries = tuple(p.stem for p in pretty_dirs)

    model_names = tuple(sorted((p.relative_to(layout.models_dir).as_posix() for p in _safe_walk(layout.models_dir))))
    model_name_set = set(model_names)

    parts: list[InventoryPart] = []
    for sym_path in sym_paths:
        library = sym_path.stem
        rel_path = _rel(layout, sym_path)
        loaded = _load_bounded(sym_path)
        if isinstance(loaded, Issue):
            issues.append(Issue(Severity.ERROR, "migration.unreadable", f"Could not read {rel_path}: {loaded.text}"))
            continue
        version = kicad_files.file_version(loaded.root)
        atomic = is_atomic(library)
        for ref in kicad_files.find_symbols(loaded.root):
            fields = {prop.name: prop.value for prop in kicad_files.list_properties(ref.node)}
            block = kicad_files.block_text(loaded.source.text, ref.node)
            parts.append(
                InventoryPart(
                    key=(rel_path, ref.name),
                    library=library,
                    rel_path=rel_path,
                    name=ref.name,
                    extends=kicad_files.extends_name(ref.node),
                    fields=fields,
                    footprint=fields.get("Footprint", ""),
                    version=version,
                    block_sha256=hashlib.sha256(block.encode("utf-8")).hexdigest(),
                    atomic=atomic,
                )
            )

    footprints: list[InventoryFootprint] = []
    for pretty in pretty_dirs:
        library = pretty.stem
        mod_paths = sorted(
            (p for p in _real_children(pretty) if p.is_file() and p.suffix.casefold() == _MOD_SUFFIX),
            key=lambda p: (p.stem.casefold(), p.stem),
        )
        for mod_path in mod_paths:
            rel_path = _rel(layout, mod_path)
            loaded = _load_bounded(mod_path)
            if isinstance(loaded, Issue):
                issues.append(
                    Issue(Severity.ERROR, "migration.unreadable", f"Could not read {rel_path}: {loaded.text}")
                )
                continue
            name_ref = kicad_files.footprint_name(loaded.root)
            if name_ref is None:
                continue
            models = tuple(
                sorted(
                    {
                        stripped
                        for ref in kicad_files.find_models(name_ref.node)
                        if (stripped := _model_rel(ref.path)) is not None and stripped in model_name_set
                    }
                )
            )
            block = kicad_files.block_text(loaded.source.text, name_ref.node)
            footprints.append(
                InventoryFootprint(
                    library=library,
                    name=mod_path.stem,
                    rel_path=rel_path,
                    internal_name=name_ref.name,
                    models=models,
                    sha256=hashlib.sha256(block.encode("utf-8")).hexdigest(),
                    linked_by=(),
                )
            )

    # Resolve each part's Footprint field against the Custom footprints by exact library and file name
    linked_by: dict[tuple[str, str], list[PartKey]] = {}
    footprint_keys = {(f.library, f.name) for f in footprints}
    for part in parts:
        link = _split_link(part.footprint)
        if link is not None and link in footprint_keys:
            linked_by.setdefault(link, []).append(part.key)

    footprints = [
        InventoryFootprint(
            library=f.library,
            name=f.name,
            rel_path=f.rel_path,
            internal_name=f.internal_name,
            models=f.models,
            sha256=f.sha256,
            linked_by=tuple(linked_by.get((f.library, f.name), ())),
        )
        for f in footprints
    ]

    model_linkers: dict[str, list[str]] = {name: [] for name in model_names}
    for f in footprints:
        label = f"{f.library}:{f.name}"
        for model in f.models:
            model_linkers.setdefault(model, []).append(label)

    return Inventory(
        layout=layout,
        parts=tuple(sorted(parts, key=lambda p: (p.rel_path, p.name))),
        footprints=tuple(sorted(footprints, key=lambda f: f.rel_path)),
        models=model_names,
        model_linkers={name: tuple(sorted(labels)) for name, labels in model_linkers.items()},
        bak_files=bak_files,
        symbol_libraries=symbol_libraries,
        footprint_libraries=footprint_libraries,
        issues=tuple(issues),
    )


def migration_reason(layout: RepoLayout) -> str | None:
    """Plain reason the Migrate menu stays enabled, or None once Custom has nothing left to migrate (D-13).

    Listing only: no file is parsed.
    """
    for path in _symbol_libraries(layout):
        if not is_atomic(path.stem):
            return f"Custom still has the v1 library {path.stem}"
    for path in _pretty_dirs(layout):
        if path.stem != SHARED_FOOTPRINT_LIBRARY:
            return f"Custom still has the footprint folder {path.stem}"
    for path in _bak_paths(layout):
        return f"Custom/Symbols still holds {path.name}"
    return None
