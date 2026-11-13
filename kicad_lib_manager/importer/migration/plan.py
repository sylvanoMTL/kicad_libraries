"""The migration contract: what every later Phase 13 plan builds against (interface first; MIG-02, MIG-03).

Everything here is a frozen value object, mirroring importer/plan.py's InstallPlan contract: the
objects describing what the migration will do are kept separate from the planner, gate and applier
code that fill and act on them. No planner, draft or window code exists yet; this module only fixes
the shape each later plan builds against, so plans 13-06..13-16 can run in parallel waves without
editing it.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ...models import Issue
from ..layout import RepoLayout
from ..plan import Conflict, FieldChange, PartText, Rename, Resolution, ToolContext
from ..siblings import SiblingIndex
from ..suggest import LibrarySuggestion

# Repo-relative posix path of the source .kicad_sym, paired with the original (pre-rename) symbol name.
PartKey = tuple[str, str]

OP_KINDS = ("mkdir", "write", "delete", "rmdir")
FOOTPRINT_TARGETS = ("shared", "official")
MAP_FILE = "MIGRATION-ATOMIC.md"


@dataclass(frozen=True)
class PartChoice:
    """One part's owner-editable choices; every field is optional and None means "let the planner derive it".

    library="" means the owner explicitly cleared the library, which blocks Run (D-01). The text
    fields (mpn, manufacturer, datasheet, description, keywords, fp_description, fp_tags) follow the
    importer's blank-means-unset convention once the planner applies them.
    """

    library: str | None = None
    symbol_name: str | None = None
    mpn: str | None = None
    manufacturer: str | None = None
    datasheet: str | None = None
    description: str | None = None
    keywords: str | None = None
    fp_description: str | None = None
    fp_tags: str | None = None
    footprint_target: str = "shared"
    # "Library:Footprint" of an official KiCad footprint to link instead of moving into Atomic_Footprints (D-08)
    official_footprint: str | None = None
    footprint_name: str | None = None
    model_name: str | None = None
    # A 3D model file the owner added separately, outside the part's own vendor history
    model_source: str | None = None
    derive: bool = True


@dataclass(frozen=True)
class MigrationChoices:
    """Every owner choice collected so far, keyed for lookup by the planner."""

    parts: Mapping[PartKey, PartChoice] = field(default_factory=dict)
    # Repo-relative path of a leftover footprint or model -> keep (D-10)
    leftovers: Mapping[str, bool] = field(default_factory=dict)
    # Atomic_Footprints name-clash key -> how the owner resolved it (D-07)
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanContext:
    """The external inputs the migration planner needs beyond the inventory and the owner's choices."""

    tools: ToolContext
    kicad_fp_dir: Path | None
    own: SiblingIndex
    stock: SiblingIndex | None
    suggestions: Mapping[PartKey, LibrarySuggestion]
    allowed: frozenset[str]
    today: str  # YYYY-MM-DD, for generated text that carries a date


@dataclass(frozen=True)
class MigrationOp:
    """One planned filesystem change; base_sha256 None means the path must not exist before this op runs."""

    kind: str  # one of OP_KINDS
    path: Path
    rel: str  # repo-relative posix
    data: bytes | None = None
    base_sha256: str | None = None
    note: str = ""
    # Repo-relative posix path of the file a moved or renamed file comes from
    source_rel: str | None = None


@dataclass(frozen=True)
class PartPlan:
    """One part's planned end state: what it is renamed to, where it moves and what changes with it."""

    key: PartKey
    source_library: str
    target_library: str  # "" = undecided, blocks Run
    suggestion: LibrarySuggestion | None
    old_name: str
    new_name: str
    mpn: str
    parent: str | None  # D-06: the family parent this part derives from, else None
    footprint_old: str
    footprint_new: str
    footprint_target: str  # "shared", "official" or "none"
    model_files: tuple[str, ...]
    field_changes: tuple[FieldChange, ...]
    generated_text: PartText
    part_text: PartText
    changed_since_draft: bool = False
    issues: tuple[Issue, ...] = ()
    library_basis: str = ""  # where the library came from: "chosen", "suggested", "guessed" or "" (none)


@dataclass(frozen=True)
class LeftoverRow:
    """One vendor footprint or model the migration leaves unlinked; the owner can untick to keep it (D-10)."""

    rel: str
    kind: str  # "footprint" or "model"
    keep: bool
    default_keep: bool
    reason: str


@dataclass(frozen=True)
class FamilyRow:
    """One derived-symbol decision: member becomes `(extends parent)` when derive is true (D-06)."""

    parent: PartKey
    member: PartKey
    derive: bool


@dataclass(frozen=True)
class MigrationPlan:
    """The whole previewable migration: every part, every file operation and the whole-set findings."""

    layout: RepoLayout
    parts: tuple[PartPlan, ...]
    ops: tuple[MigrationOp, ...]
    library_map: tuple[tuple[str, str], ...]
    symbol_renames: tuple[Rename, ...]
    footprint_links: tuple[tuple[str, str], ...]
    model_renames: tuple[Rename, ...]
    leftovers: tuple[LeftoverRow, ...]
    families: tuple[FamilyRow, ...]
    conflicts: tuple[Conflict, ...]
    removed_libraries: tuple[str, ...]
    bak_files: tuple[str, ...]
    map_text: str
    # Whole-set ERRORs (name clashes, undecided libraries, ...) block Run; see MigrationPlan.blocked below
    issues: tuple[Issue, ...] = ()
