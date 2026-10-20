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

MODEL_DIR_VAR = "${CUSTOM_3DMODEL_DIR}"


@dataclass(frozen=True)
class ToolContext:
    """External tools and stock-library locations the planner may use."""

    kicad_cli: Path | None = None
    cli_runner: Callable | None = None
    cli_timeout: float = 60.0
    kicad_symbols_dir: Path | None = None
    extra_symbol_dirs: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Resolution:
    """How the caller settled one conflict; there is no global default (D-05)."""

    action: str  # "overwrite" | "rename" | "skip"
    rename_to: str | None = None


_TEXT_OVERRIDES = ("value", "datasheet", "description", "manufacturer", "mpn")


@dataclass(frozen=True)
class InstallOptions:
    """The caller's choices. Item names refer to vendor items (SymbolItem.name, FootprintItem.name, ModelItem.filename).

    An empty or whitespace-only value, datasheet, description, manufacturer or mpn means "not set"
    and becomes None, so the vendor value is kept (WR-05; a Qt line edit returns "" for an untouched
    field). There is no way to ask for an empty value: an explicit "clear this field" outcome is a
    Phase 5 preview decision, so until then a deliberate blank edit installs the vendor value.
    """

    library: str
    symbol: str | None = None
    footprints: tuple[str, ...] = ()
    model: str | None = None
    no_model: bool = False
    # vendor footprint name -> caller-edited target name
    footprint_names: Mapping[str, str] = field(default_factory=dict)
    value: str | None = None
    datasheet: str | None = None
    description: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    resolutions: Mapping[str, Resolution] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in _TEXT_OVERRIDES:
            text = getattr(self, name)
            if isinstance(text, str) and not text.strip():
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
class InstallPlan:
    """A complete, previewable install.

    The Package that produced the candidate must stay open until apply_plan returns (WR-04):
    the model copy reads its bytes from the staged file at apply time.
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

    @property
    def symbol_name(self) -> str:
        """The chosen symbol; a derived symbol's parents come before it in symbol_names. Empty on a refused plan."""
        return self.symbol_names[-1] if self.symbol_names else ""

    @property
    def new_library(self) -> bool:
        return self.new_symbol_lib or self.new_footprint_lib

    @property
    def symbol_lib_path(self) -> Path:
        return self.layout.symbols_dir / f"{self.library}.kicad_sym"

    @property
    def pretty_path(self) -> Path:
        return self.layout.footprints_dir / f"{self.library}.pretty"

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
