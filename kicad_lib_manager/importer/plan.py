"""The install plan contract: what build_plan decides and apply_plan carries out (Phase 4).

Everything here is a frozen value object. The plan carries the final bytes of every file the
install will create or change, so applying it is a dumb write loop and the GUI can render the
same object as a preview.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ..models import Issue, Severity
from .layout import RepoLayout
from .package import PackageFile
from .stems import SHARED_FOOTPRINT_LIBRARY

MODEL_DIR_VAR = "${CUSTOM_3DMODEL_DIR}"


@dataclass(frozen=True)
class ToolContext:
    """External tools and stock-library locations the planner may use."""

    kicad_cli: Path | None = None
    cli_runner: Callable | None = None
    cli_timeout: float = 60.0
    kicad_symbols_dir: Path | None = None
    extra_symbol_dirs: tuple[Path, ...] = ()
    kicad_footprints_dir: Path | None = None
    # Stems of the KiCad symbol libraries a part may use; empty means the built-in KiCad 10 snapshot (D-07)
    allowed_stems: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Resolution:
    """How the caller settled one conflict; there is no global default (D-05)."""

    action: str  # "overwrite" | "rename" | "skip"
    rename_to: str | None = None


_TEXT_OVERRIDES = ("datasheet", "description", "manufacturer", "mpn")


@dataclass(frozen=True)
class PartText:
    """The three generated texts of a part (D-26 to D-30): the symbol's keywords and the footprint's description and tags.

    Each is one line of text exactly as it is written into the file; "" means none.
    """

    keywords: str = ""
    fp_description: str = ""
    fp_tags: str = ""


@dataclass(frozen=True)
class InstallOptions:
    """The caller's choices. Item names refer to vendor items (SymbolItem.name, FootprintItem.name, ModelItem.filename).

    An empty or whitespace-only datasheet, description, manufacturer or mpn means "not set"
    and becomes None, so the vendor value is kept (WR-05; a Qt line edit returns "" for an untouched
    field). A caller that wants an empty value names the field in `cleared` (D-13, the Phase 5
    preview): such a field with a blank or None value is stored as "" and installs as an empty
    property. Text is always kept exactly as typed. Mpn cannot be cleared; build_plan refuses an
    empty one, because mpn names the 3D model file. There is no Value option: every symbol's Value
    is its own final MPN (D-22). An unknown name in `cleared` raises
    ValueError, since it is a programming error.
    """

    library: str
    symbol: str | None = None
    # D-14: one vendor footprint per atomic part; None means the package's only footprint
    footprint: str | None = None
    model: str | None = None
    no_model: bool = False
    # vendor footprint name -> caller-edited target name
    footprint_names: Mapping[str, str] = field(default_factory=dict)
    datasheet: str | None = None
    description: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)
    cleared: frozenset[str] = frozenset()
    # D-30: None means the generated text; any string, an empty one too, is written exactly as given. They are
    # not part of the blank-to-None rule above.
    keywords: str | None = None
    fp_description: str | None = None
    fp_tags: str | None = None
    # Stems of the libraries the suggestion ranked below the chosen one; their words join the keywords (D-26)
    related_stems: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "cleared", frozenset(self.cleared))
        object.__setattr__(self, "related_stems", tuple(self.related_stems))
        unknown = self.cleared.difference(_TEXT_OVERRIDES)
        if unknown:
            raise ValueError(f"cleared names unknown field(s): {', '.join(sorted(unknown))}")
        for name in _TEXT_OVERRIDES:
            text = getattr(self, name)
            if name in self.cleared and (text is None or not text.strip()):
                object.__setattr__(self, name, "")
            elif isinstance(text, str) and not text.strip():
                object.__setattr__(self, name, None)


@dataclass(frozen=True)
class FileOp:
    """One write. base_sha256 None means the path must not exist; listed_path is the on-disk spelling when it differs by case."""

    kind: str  # "mkdir" | "model" | "footprint" | "symbol_lib"
    path: Path
    data: bytes | None = None
    source: PackageFile | None = None
    base_sha256: str | None = None
    listed_path: Path | None = None


@dataclass(frozen=True)
class Conflict:
    """A planned item that collides with an existing one; stays blocking until it has a resolution."""

    key: str
    kind: str  # "symbol" | "footprint" | "model"
    name: str
    existing: str
    suggested_name: str = ""
    resolution: Resolution | None = None


@dataclass(frozen=True)
class Rename:
    kind: str
    old: str
    new: str


@dataclass(frozen=True)
class FieldChange:
    """One incoming symbol property the planner dropped, cleaned, renamed or set (D-09).

    symbol is the final symbol name and field the property name before the change. old is the
    value before; new is the value after for a clean or a set and the new property name for a
    rename, and empty for a drop. action is drop | clean | rename | set; reason is volatile |
    placeholder | duplicate | whitespace | alias | follows_mpn | canonical | datasheet_host | generated.
    scope is "symbol", or "footprint" for a change of the footprint's description or tags, whose symbol
    is then the final footprint name.
    """

    symbol: str
    action: str
    field: str
    old: str = ""
    new: str = ""
    reason: str = ""
    scope: str = "symbol"


@dataclass(frozen=True)
class InstallPlan:
    """A complete, previewable install.

    The Package that produced the candidate must stay open until apply_plan returns (WR-04):
    the model copy reads its bytes from the staged file at apply time.

    field_changes lists every dropped, cleaned or renamed incoming property, in property order,
    for the preview (D-09). generated_text is what the generators made and part_text what the install
    writes, which differs where the caller typed a text of their own (D-30); both read the same plan the
    preview shows.
    """

    vendor: str
    source: Path
    layout: RepoLayout
    tools: ToolContext
    library: str
    new_symbol_lib: bool
    new_footprint_lib: bool
    symbol_names: tuple[str, ...]
    footprint_names: tuple[str, ...]
    linked_footprint: str | None
    model_file: str | None
    source_version: int | None
    target_version: int | None
    normalised: bool
    ops: tuple[FileOp, ...]
    conflicts: tuple[Conflict, ...]
    renames: tuple[Rename, ...]
    issues: tuple[Issue, ...]
    field_changes: tuple[FieldChange, ...] = ()
    footprint_library: str | None = None
    # D-14: vendor footprints the package holds that this part does not use; none of them is written
    unused_footprints: tuple[str, ...] = ()
    generated_text: PartText = PartText()
    part_text: PartText = PartText()

    @property
    def footprint_link(self) -> str | None:
        """The Library:Footprint text the symbol's Footprint field carries, or None when none is linked."""
        if self.footprint_library and self.linked_footprint:
            return f"{self.footprint_library}:{self.linked_footprint}"
        return None

    @property
    def symbol_name(self) -> str:
        """The chosen symbol; a derived symbol's parents come before it in symbol_names. Empty on a refused plan."""
        return self.symbol_names[-1] if self.symbol_names else ""

    @property
    def new_library(self) -> bool:
        """True when the symbol library is new; the shared footprint library's own state is new_footprint_lib."""
        return self.new_symbol_lib

    @property
    def symbol_lib_path(self) -> Path:
        return self.layout.symbols_dir / f"{self.library}.kicad_sym"

    @property
    def pretty_path(self) -> Path:
        return self.layout.footprints_dir / f"{SHARED_FOOTPRINT_LIBRARY}.pretty"

    @property
    def unresolved_conflicts(self) -> tuple[Conflict, ...]:
        return tuple(c for c in self.conflicts if c.resolution is None)

    @property
    def blocked(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues) or bool(self.unresolved_conflicts)

    @property
    def is_noop(self) -> bool:
        return not self.blocked and not self.ops


@dataclass(frozen=True)
class InstallResult:
    ok: bool
    library: str
    new_library: bool
    touched: tuple[Path, ...]
    issues: tuple[Issue, ...]
    backup_dir: Path | None = None
    vendor: str = ""
    source: Path | None = None
