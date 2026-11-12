"""Fresh, read-only listings of the Custom/ library layout (D-03).

Every function reads the disk again on each call: nothing is cached and nothing comes
from a previous scan, so a library added between two calls shows up on the second.
Listings only read names; they never open files and never create or change a folder.
"""

from dataclasses import dataclass
from pathlib import Path

from .candidate import ExistingLibrary


@dataclass(frozen=True)
class RepoLayout:
    repo_root: Path
    custom_dir: Path
    symbols_dir: Path
    footprints_dir: Path
    models_dir: Path

    @classmethod
    def for_repo(cls, repo_root: Path) -> "RepoLayout":
        custom = repo_root / "Custom"
        return cls(
            repo_root=repo_root,
            custom_dir=custom,
            symbols_dir=custom / "Symbols",
            footprints_dir=custom / "Footprints",
            models_dir=custom / "3DModels",
        )


def _sorted(names) -> list[str]:
    return sorted(set(names), key=lambda n: (n.casefold(), n))


def _children(folder: Path) -> list[Path]:
    """Return the direct children of a folder, or [] when it is missing or unreadable."""
    try:
        return list(folder.iterdir())
    except OSError:
        return []


def list_symbol_libs(layout: RepoLayout) -> list[str]:
    """Return the stems of the .kicad_sym files directly in Custom/Symbols."""
    return _sorted(
        p.stem for p in _children(layout.symbols_dir) if p.suffix.casefold() == ".kicad_sym" and p.is_file()
    )


def list_footprint_libs(layout: RepoLayout) -> list[str]:
    """Return the stems of the .pretty folders directly in Custom/Footprints."""
    return _sorted(
        p.stem for p in _children(layout.footprints_dir) if p.suffix.casefold() == ".pretty" and p.is_dir()
    )


def list_model_files(layout: RepoLayout) -> list[str]:
    """Return every file below Custom/3DModels as a posix path relative to it."""
    try:
        found = [p.relative_to(layout.models_dir).as_posix() for p in layout.models_dir.rglob("*") if p.is_file()]
    except OSError:
        return []
    return _sorted(found)


def list_existing_libraries(layout: RepoLayout) -> list[ExistingLibrary]:
    """Return the union of the symbol and footprint libraries, marking which parts each one has."""
    symbols = set(list_symbol_libs(layout))
    footprints = set(list_footprint_libs(layout))
    return [ExistingLibrary(name, name in symbols, name in footprints) for name in _sorted(symbols | footprints)]
