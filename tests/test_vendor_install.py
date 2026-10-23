"""Vendor packages installed into a synthetic Custom/ (D-03): intake, plan, preview, apply and commit message.

Every test builds its own Custom/ under ``tmp_path`` and its own vendor zip from ``vendorfixtures``.
No test reads the owner's real ``Custom/`` tree or a real vendor download.
"""

from contextlib import contextmanager
from pathlib import Path

from vendorfixtures import (
    SNAPEDA_FOOTPRINT,
    SNAPEDA_MANUFACTURER,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    snapeda_zip,
)
from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, write_custom_layout

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.commit_plan import build_commit_plan, default_message
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes
from kicad_lib_manager.models import Issue

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "Connector_USB_GCT"


def _snapeda_layout(tmp_path):
    """A synthetic Custom/ holding the current library names, built under tmp_path only (D-03)."""
    write_custom_layout(tmp_path / "repo", CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open_snapeda(tmp_path, **members_kwargs):
    """Open a synthetic SnapEDA zip, yielding (package, candidate); the package stays open for apply_plan."""
    zip_path = snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip", **members_kwargs)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _plan_snapeda(candidate, layout, **options):
    """Plan the candidate into Connector_USB_GCT with no external tools (ToolContext())."""
    chosen = InstallOptions(library=LIBRARY, **options)
    return build_plan(candidate, chosen, layout, ToolContext()), chosen


def _symbol_in(data, name=SNAPEDA_SYMBOL):
    loaded = parse_bytes(data, "lib")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None
    return symbol


def _op(plan, kind):
    return next(op for op in plan.ops if op.kind == kind)


def test_tracer_snapeda_end_to_end(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (package, candidate):
        assert candidate.vendor == "SnapEDA"
        assert candidate.confidence >= 0.7
        assert "intake.unknown_vendor" not in [i.code for i in candidate.issues]

        plan, options = _plan_snapeda(candidate, layout)
        assert not plan.blocked, [i.text for i in plan.issues]
        assert plan.vendor == "SnapEDA"
        sections = preview_sections(plan, candidate, options)
        assert sections[0].name == "Files"

        symbol = _symbol_in(_op(plan, "symbol_lib").data)
        assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:{SNAPEDA_FOOTPRINT}"
        assert find_property(symbol.node, "Manufacturer").value == SNAPEDA_MANUFACTURER
        assert find_property(symbol.node, "MPN").value == SNAPEDA_MPN
        assert find_property(symbol.node, "SnapEDA_Link") is not None
        assert find_property(symbol.node, "MAXIMUM_PACKAGE_HEIGHT") is not None
        assert "install.no_model" in [i.code for i in plan.issues]

        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]

        installed = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
        assert installed.read_bytes() == _op(plan, "symbol_lib").data
        assert (layout.footprints_dir / f"{LIBRARY}.pretty" / f"{SNAPEDA_FOOTPRINT}.kicad_mod").is_file()

        message = default_message(build_commit_plan(result, plan, vendor_label=plan.vendor))
        assert "Import-Vendor: SnapEDA" in message.splitlines()
