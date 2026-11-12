"""The atomic check on a part that is not installed yet: planned footprint and model bytes (LIB-07, D-21)."""

from pathlib import Path

from customfixtures import OFFICIAL_FOOTPRINT, OFFICIAL_LIBRARY, atomic_lib, atomic_part, write_fake_kicad
from installfixtures import vendor_footprint
from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer.incoming import incoming_context, incoming_issues
from kicad_lib_manager.models import Severity

SYMBOL_REL = "Custom/Symbols/Atomic_Transistor_FET.kicad_sym"
FOOTPRINT_REL = "Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod"
LINK = "Atomic_Footprints:DQK0006B"
MODEL = "CSD85301Q2.stp"
MODEL_LINK = f"${{CUSTOM_3DMODEL_DIR}}/{MODEL}"
OFFICIAL_LINK = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with an empty Custom/Footprints and Custom/3DModels; returns (repo root, footprints dir)."""
    footprints = tmp_path / "Custom" / "Footprints"
    footprints.mkdir(parents=True)
    (tmp_path / "Custom" / "3DModels").mkdir()
    return tmp_path, footprints


def _root(*parts) -> kicad_files.Node:
    loaded = kicad_files.parse_bytes(atomic_lib(tuple(parts)), "Atomic_Transistor_FET.kicad_sym")
    assert isinstance(loaded, kicad_files.LoadedFile), loaded
    return loaded.root


def _part(*, replace=None, **kwargs):
    """CSD85301Q2 linked to its planned footprint, with a manufacturer the table knows."""
    fields = {"Footprint": LINK, "Manufacturer": "Texas Instruments", **(replace or {})}
    return atomic_part("CSD85301Q2", replace=fields, **kwargs)


def _planned_footprints(model: str = MODEL_LINK) -> dict[str, tuple[str, bytes]]:
    return {LINK: (FOOTPRINT_REL, vendor_footprint("DQK0006B", model=model))}


def _issues(tmp_path: Path, *parts, names=None, planned=True, models=(MODEL,), kicad_fp_dir=None):
    """Run the incoming check on parts; by default the planned footprint and model are in place."""
    repo, footprints = _repo(tmp_path)
    ctx = incoming_context(
        repo,
        footprints,
        kicad_fp_dir,
        planned_footprints=_planned_footprints() if planned else {},
        planned_models=models,
    )
    names = names if names is not None else [parts[-1].name]
    return incoming_issues(_root(*parts), names, rel_path=SYMBOL_REL, ctx=ctx)


def _pairs(issues):
    return [(i.code, i.text) for i in issues]


# -- the tracer: a planned part with its planned footprint and model ----------------------------------


def test_a_planned_part_with_its_planned_footprint_and_model_passes(tmp_path):
    repo, footprints = _repo(tmp_path)
    ctx = incoming_context(
        repo, footprints, None, planned_footprints=_planned_footprints(), planned_models={MODEL}
    )
    assert incoming_issues(_root(_part()), ["CSD85301Q2"], rel_path=SYMBOL_REL, ctx=ctx) == []


def test_the_same_part_without_its_planned_model_gives_the_model_error_only(tmp_path):
    repo, footprints = _repo(tmp_path)
    ctx = incoming_context(repo, footprints, None, planned_footprints=_planned_footprints())
    issues = incoming_issues(_root(_part()), ["CSD85301Q2"], rel_path=SYMBOL_REL, ctx=ctx)
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (
            Severity.ERROR,
            "install.atomic.model_3d",
            '3D model "CSD85301Q2.stp" is not in Custom/3DModels (names are case-sensitive)',
        )
    ]


# -- every rule (LIB-07) ---------------------------------------------------------------------------


def test_a_part_with_no_mpn_gets_the_mpn_error(tmp_path):
    assert _pairs(_issues(tmp_path, _part(drop=("MPN",)))) == [("install.atomic.mpn", "no MPN")]


def test_a_part_with_a_blank_manufacturer_gets_the_manufacturer_error(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Manufacturer": ""}))
    assert _pairs(issues) == [("install.atomic.manufacturer", "no manufacturer")]


def test_a_value_that_is_not_the_mpn_gets_the_value_error(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Value": "X", "MPN": "Y"}))
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (Severity.ERROR, "install.atomic.value", 'Value "X" is not the MPN "Y"')
    ]


def test_a_tilde_datasheet_is_no_datasheet(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Datasheet": "~"}))
    assert _pairs(issues) == [("install.atomic.datasheet", "no datasheet")]


def test_a_blank_datasheet_is_no_datasheet(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Datasheet": ""}))
    assert _pairs(issues) == [("install.atomic.datasheet", "no datasheet")]


def test_a_datasheet_that_is_a_part_number_is_not_a_link(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Datasheet": "ATXK-H14-D-32.768KHZ-E50-T3"}))
    assert _pairs(issues) == [("install.atomic.datasheet", "Datasheet is not a link or file path")]


def test_a_whitespace_description_is_no_description(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Description": "   "}))
    assert _pairs(issues) == [("install.atomic.description", "no description")]


def test_a_part_failing_several_rules_gives_one_error_each_in_rule_order(tmp_path):
    part = _part(replace={"Description": "", "Datasheet": "~", "Manufacturer": "", "Footprint": ""}, drop=("MPN",))
    issues = _issues(tmp_path, part)
    assert [i.code for i in issues] == [
        "install.atomic.mpn",
        "install.atomic.manufacturer",
        "install.atomic.footprint",
        "install.atomic.datasheet",
        "install.atomic.description",
    ]
    assert all(i.severity is Severity.ERROR for i in issues)


def test_an_unknown_manufacturer_is_a_note_and_never_an_error(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Manufacturer": "Acme Widgets"}))
    assert [(i.severity, i.code) for i in issues] == [(Severity.INFO, "install.atomic_note.unknown_manufacturer")]


# -- parent symbols --------------------------------------------------------------------------------


def test_a_child_without_its_own_mpn_is_named_last_and_its_parent_is_prefixed(tmp_path):
    parent = atomic_part("PARENT_X", replace={"Footprint": LINK, "Datasheet": "~"})
    child = atomic_part("CHILD_Y", replace={"Footprint": LINK}, drop=("MPN",), extends="PARENT_X")
    issues = _issues(tmp_path, parent, child, names=["PARENT_X", "CHILD_Y"])
    assert _pairs(issues) == [
        ("install.atomic.datasheet", "PARENT_X: no datasheet"),
        ("install.atomic.mpn", "no MPN of its own (the parent's MPN does not count)"),
    ]


# -- footprints: planned, official, already shared ---------------------------------------------------


def test_a_link_to_a_library_that_is_neither_planned_nor_on_disk_is_not_found(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Footprint": "Atomic_Footprints:OTHER"}))
    assert _pairs(issues) == [("install.atomic.footprint", 'footprint library "Atomic_Footprints" was not found')]


def test_an_official_kicad_footprint_and_its_model_pass(tmp_path):
    kicad_fp_dir = write_fake_kicad(tmp_path)[0]
    part = _part(replace={"Footprint": OFFICIAL_LINK})
    assert _issues(tmp_path, part, planned=False, models=(), kicad_fp_dir=kicad_fp_dir) == []


def test_an_official_footprint_without_a_kicad_footprints_folder_is_not_found(tmp_path):
    part = _part(replace={"Footprint": OFFICIAL_LINK})
    issues = _issues(tmp_path, part, planned=False, models=(), kicad_fp_dir=None)
    assert _pairs(issues) == [
        ("install.atomic.footprint", f'footprint library "{OFFICIAL_LIBRARY}" was not found')
    ]


def test_an_existing_shared_footprint_and_model_on_disk_pass_with_nothing_planned(tmp_path):
    repo, footprints = _repo(tmp_path)
    pretty = footprints / "Atomic_Footprints.pretty"
    pretty.mkdir()
    (pretty / "DQK0006B.kicad_mod").write_bytes(vendor_footprint("DQK0006B", model=MODEL_LINK))
    (repo / "Custom" / "3DModels" / MODEL).write_bytes(b"ISO-10303-21;")
    ctx = incoming_context(repo, footprints, None)
    assert incoming_issues(_root(_part()), ["CSD85301Q2"], rel_path=SYMBOL_REL, ctx=ctx) == []


# -- a plan counts only for what it really carries (T-10-12) --------------------------------------------


def test_a_planned_model_in_another_case_does_not_satisfy_the_link(tmp_path):
    issues = _issues(tmp_path, _part(), models=("csd85301q2.stp",))
    assert _pairs(issues) == [
        (
            "install.atomic.model_3d",
            '3D model "CSD85301Q2.stp" is not in Custom/3DModels (names are case-sensitive)',
        )
    ]


def test_a_planned_footprint_counts_only_under_its_exact_link(tmp_path):
    issues = _issues(tmp_path, _part(replace={"Footprint": "Atomic_Footprints:dqk0006b"}))
    assert [i.code for i in issues] == ["install.atomic.footprint"]
