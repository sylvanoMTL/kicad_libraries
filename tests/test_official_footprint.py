"""Linking an official KiCad footprint instead of installing the vendor one (plan 10-24, LIB-06, D-16 to D-18, D-29).

Every install goes into an isolated Custom/ built in code, and KiCad's footprints folder is a stand-in built under
tmp_path (write_fake_kicad holds Package_TO_SOT_SMD:SOT-23-5 with five pads and its model; write_stock_sample
holds the CSD family's Package_SON:Texas_DQK). Nothing here writes into the live Custom/ or a real KiCad install.
"""

from contextlib import contextmanager
from pathlib import Path

from customfixtures import (
    ABSENT_LIBRARY,
    OFFICIAL_FOOTPRINT,
    OFFICIAL_LIBRARY,
    write_fake_kicad,
)
from installfixtures import ATOMIC_PROPS, vendor_footprint, vendor_symbol_lib
from zipfixtures import STEP_BYTES, make_zip

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import find_property, find_symbol, load
from kicad_lib_manager.models import Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ABSENT_LIBRARY  # Atomic_Transistor_FET, absent from the atomic_custom layout
OFFICIAL_LINK = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
SYMBOL = "PART"


@contextmanager
def synthetic_package(tmp_path, *, footprint_pads=("1", "2"), footprints=("FP",), models=("FP.step",)):
    """Open a synthetic package: the symbol PART (pins 1 and 2), vendor footprints with the given pads and STEP models."""
    members = [("part.kicad_sym", vendor_symbol_lib(SYMBOL, props=ATOMIC_PROPS))]
    members += [(f"{name}.kicad_mod", vendor_footprint(name, pads=footprint_pads)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    source = tmp_path / "src"
    source.mkdir(exist_ok=True)
    with open_package(make_zip(source / "pkg.zip", members), REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def official_options(link: str | None = OFFICIAL_LINK, **changes) -> InstallOptions:
    return InstallOptions(library=LIBRARY, footprint_target="official", official_footprint=link, **changes)


def codes(plan, severity: Severity) -> list[str]:
    return [issue.code for issue in plan.issues if issue.severity is severity]


# -- the tracer: a part linked to Package_TO_SOT_SMD:SOT-23-5, planned, gated, applied, verified and shown --------


def test_a_part_links_the_official_footprint_end_to_end(atomic_custom, tmp_path):
    footprints, _ = write_fake_kicad(tmp_path)
    tools = ToolContext(kicad_footprints_dir=footprints)
    with synthetic_package(tmp_path) as (_, candidate):
        plan = build_plan(candidate, official_options(), atomic_custom, tools)
        assert not plan.blocked, plan.issues
        # Only the symbol library is written: no footprint, no model and no Atomic_Footprints folder
        assert [op.kind for op in plan.ops] == ["symbol_lib"]
        assert plan.footprint_link == OFFICIAL_LINK
        assert plan.footprint_library == OFFICIAL_LIBRARY
        assert plan.footprint_names == ()
        assert plan.model_file is None
        assert plan.unused_footprints == ("FP",)
        assert plan.unused_models == ("FP.step",)
        assert not [code for code in codes(plan, Severity.ERROR) if code.startswith("install.atomic")]
        # The pads differ from the symbol's pins and from the vendor footprint, which is a warning and nothing more
        warnings = codes(plan, Severity.WARNING)
        assert "verify.pin_pad_mismatch" in warnings
        assert "install.pad_mismatch" in warnings
        mismatch = next(issue for issue in plan.issues if issue.code == "install.pad_mismatch")
        assert mismatch.text == f"{OFFICIAL_LINK} has different pads from the vendor footprint FP: extra 3, 4, 5"
        sections = {section.name: section for section in preview_sections(plan, candidate, official_options())}
        assert [row.detail for row in sections["Not used"].rows] == [
            "footprint, not installed: an official KiCad footprint is used",
            "3D model, not installed: KiCad's own 3D model is used",
        ]
        result = apply_plan(plan, backup_root=tmp_path / "backups")
        assert result.ok, result.issues
    assert [issue for issue in verify_install(plan) if issue.severity is Severity.ERROR] == []
    library = load(plan.symbol_lib_path)
    assert find_property(find_symbol(library.root, SYMBOL).node, "Footprint").value == OFFICIAL_LINK
    assert not (atomic_custom.footprints_dir / "Atomic_Footprints.pretty" / "FP.kicad_mod").exists()
    assert not (atomic_custom.models_dir / "PART.step").exists()
