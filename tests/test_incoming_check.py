"""The atomic check on a part that is not installed yet: planned footprint and model bytes (LIB-07, D-21)."""

from pathlib import Path

from customfixtures import atomic_lib, atomic_part
from installfixtures import vendor_footprint
from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer.incoming import incoming_context, incoming_issues
from kicad_lib_manager.models import Severity

SYMBOL_REL = "Custom/Symbols/Atomic_Transistor_FET.kicad_sym"
FOOTPRINT_REL = "Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod"
LINK = "Atomic_Footprints:DQK0006B"
MODEL = "CSD85301Q2.stp"
MODEL_LINK = f"${{CUSTOM_3DMODEL_DIR}}/{MODEL}"


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with an empty Custom/Footprints and Custom/3DModels; returns (repo root, footprints dir)."""
    footprints = tmp_path / "Custom" / "Footprints"
    footprints.mkdir(parents=True)
    (tmp_path / "Custom" / "3DModels").mkdir()
    return tmp_path, footprints


def _root(part) -> kicad_files.Node:
    loaded = kicad_files.parse_bytes(atomic_lib((part,)), "Atomic_Transistor_FET.kicad_sym")
    assert isinstance(loaded, kicad_files.LoadedFile), loaded
    return loaded.root


def _planned_part():
    return atomic_part("CSD85301Q2", replace={"Footprint": LINK, "Manufacturer": "Texas Instruments"})


def _planned_footprints(model: str = MODEL_LINK) -> dict[str, tuple[str, bytes]]:
    return {LINK: (FOOTPRINT_REL, vendor_footprint("DQK0006B", model=model))}


def test_a_planned_part_with_its_planned_footprint_and_model_passes(tmp_path):
    repo, footprints = _repo(tmp_path)
    ctx = incoming_context(
        repo, footprints, None, planned_footprints=_planned_footprints(), planned_models={MODEL}
    )
    assert incoming_issues(_root(_planned_part()), ["CSD85301Q2"], rel_path=SYMBOL_REL, ctx=ctx) == []


def test_the_same_part_without_its_planned_model_gives_the_model_error_only(tmp_path):
    repo, footprints = _repo(tmp_path)
    ctx = incoming_context(repo, footprints, None, planned_footprints=_planned_footprints())
    issues = incoming_issues(_root(_planned_part()), ["CSD85301Q2"], rel_path=SYMBOL_REL, ctx=ctx)
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (
            Severity.ERROR,
            "install.atomic.model_3d",
            '3D model "CSD85301Q2.stp" is not in Custom/3DModels (names are case-sensitive)',
        )
    ]
