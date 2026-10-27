"""Qt-free left-pane rules of the import dialog (plan 05-07): item choices and field text become InstallOptions."""

from kicad_lib_manager.importer.form import FIELD_NAMES, FieldDefaults, FormValues, build_options
from kicad_lib_manager.importer.plan import Resolution

DEFAULTS = FieldDefaults(
    value="PART",
    datasheet="https://example.com/part",
    description="",
    manufacturer="TI",
    mpn="PART",
)


def values(**changes) -> FormValues:
    base = {
        "library": "Lib",
        "symbol": None,
        "footprint": None,
        "model": None,
        "no_model": False,
        "footprint_name": None,
        "fields": {},
        "resolutions": {},
    }
    base.update(changes)
    return FormValues(**base)


def test_field_names_are_the_five_planner_overrides():
    assert FIELD_NAMES == ("value", "datasheet", "description", "manufacturer", "mpn")


def test_build_options_items():
    options = build_options(
        FormValues(
            library=" Lib ",
            symbol="S2",
            footprint="F2",
            model=None,
            no_model=True,
            footprint_name=None,
            fields={},
            resolutions={},
        ),
        DEFAULTS,
    )
    assert options.library == "Lib"
    assert options.symbol == "S2"
    assert options.footprint == "F2"
    assert options.no_model is True
    assert options.model is None
    assert dict(options.footprint_names) == {}
    assert options.cleared == frozenset()
    assert [getattr(options, name) for name in FIELD_NAMES] == [None] * 5


def test_build_options_copies_resolutions():
    chosen = {"footprint:F1": Resolution("skip")}
    options = build_options(values(resolutions=chosen), DEFAULTS)
    assert dict(options.resolutions) == chosen
    assert options.resolutions is not chosen


# -- Task 2: footprint name, field text and the defaults the planner writes ------------------------

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from vendorfixtures import (  # noqa: E402
    SNAPEDA_DESCRIPTION,
    SNAPEDA_MANUFACTURER,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    snapeda_zip,
)
from zipfixtures import (  # noqa: E402
    STEP_BYTES,
    footprint,
    footprint_library_for,
    make_zip,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer import form  # noqa: E402
from kicad_lib_manager.importer.detect import detect_candidate  # noqa: E402
from kicad_lib_manager.importer.layout import RepoLayout  # noqa: E402
from kicad_lib_manager.importer.package import open_package  # noqa: E402
from kicad_lib_manager.importer.planner import build_plan  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_LIBRARY = "Atomic_Battery_Management"
TEST_LIBRARY = "Atomic_Analog"
_TI_DATASHEET = {"Datasheet": "https://www.ti.com/lit/gpn/part"}


@pytest.fixture
def eq_layout(tmp_path):
    write_custom_layout(
        tmp_path / "repo",
        [UL_LIBRARY, TEST_LIBRARY],
        [footprint_library_for(UL_LIBRARY), footprint_library_for(TEST_LIBRARY)],
    )
    return RepoLayout.for_repo(tmp_path / "repo")


def _synthetic(tmp_path: Path, symbol: bytes, name: str = "pkg.zip") -> Path:
    return make_zip(
        tmp_path / name,
        [("part.kicad_sym", symbol), ("FP.kicad_mod", footprint("FP")), ("m.step", STEP_BYTES)],
    )


def _equivalence_package(case: str, tmp_path: Path) -> tuple[Path, str]:
    """(zip, library) for one defaults-equivalence case."""
    if case == "ul":
        return UL_ZIP, UL_LIBRARY
    if case == "aliases":
        props = {**_TI_DATASHEET, "MF": "Acme Corp", "MP": "ACME-123", "ki_description": "A test part"}
        return _synthetic(tmp_path, symbol_lib(("PART",), props=props)), TEST_LIBRARY
    if case == "inferred":
        # No manufacturer property: the planner infers TI from the datasheet host
        return _synthetic(tmp_path, symbol_lib(("PART",), props=_TI_DATASHEET)), TEST_LIBRARY
    if case == "snapeda":
        # SnapEDA rules: MF/MP renamed, MANUFACTURER/SNAPEDA_PN dropped, the raw description collapsed
        return snapeda_zip(tmp_path / "snapeda.zip", with_model=True), TEST_LIBRARY
    if case == "placeholder_mf":
        # A placeholder alias counts as absent, so the planner infers TI from the datasheet host
        return _synthetic(tmp_path, symbol_lib(("PART",), props={**_TI_DATASHEET, "MF": "N/A"})), TEST_LIBRARY
    # "renamed": the vendor name changes when it is sanitised, and Value follows it
    return _synthetic(tmp_path, symbol_lib(("PART/1",), props=_TI_DATASHEET)), TEST_LIBRARY


@pytest.mark.parametrize("case", ["ul", "aliases", "inferred", "renamed", "snapeda", "placeholder_mf"])
def test_field_defaults_equivalence(case, eq_layout, tmp_path):
    """What the form shows equals what the planner writes: typing every default changes nothing (Pitfall 9)."""
    zip_path, library = _equivalence_package(case, tmp_path)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        symbol = candidate.symbols[0]
        base = FormValues(
            library=library,
            symbol=symbol.name,
            footprint=candidate.footprints[0].name,
            model=candidate.models[0].filename,
            no_model=False,
            footprint_name=None,
            fields={},
            resolutions={},
        )
        untouched = build_plan(candidate, build_options(base, FieldDefaults()), eq_layout)
        assert not untouched.blocked, untouched.issues
        defaults = form.field_defaults(candidate, symbol.name, final_name=untouched.symbol_name)
        typed_values = FormValues(**{**base.__dict__, "fields": {n: defaults.get(n) for n in FIELD_NAMES}})
        typed = build_plan(candidate, build_options(typed_values, defaults), eq_layout)
        assert typed.ops == untouched.ops
        assert typed.issues == untouched.issues
        assert typed.model_file == untouched.model_file
    if case == "ul":
        assert defaults == FieldDefaults(
            value="CSD85301Q2",
            datasheet="https://www.ti.com/lit/gpn/csd85301q2",
            description="",
            manufacturer="TI",
            mpn="CSD85301Q2",
        )
    if case == "aliases":
        assert (defaults.manufacturer, defaults.mpn, defaults.description) == ("Acme Corp", "ACME-123", "A test part")
    if case == "inferred":
        assert defaults.manufacturer == "TI"
    if case == "renamed":
        assert (defaults.value, defaults.mpn) == ("PART_1", "PART/1")
    if case == "snapeda":
        assert defaults == FieldDefaults(
            value=SNAPEDA_SYMBOL,
            datasheet="",
            description=SNAPEDA_DESCRIPTION,
            manufacturer=SNAPEDA_MANUFACTURER,
            mpn=SNAPEDA_MPN,
        )
    if case == "placeholder_mf":
        assert defaults.manufacturer == "TI"


def test_field_defaults_value_follows_final_name(tmp_path):
    zip_path = _synthetic(tmp_path, symbol_lib(("PART",), props=_TI_DATASHEET))
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        same = form.field_defaults(candidate, "PART")
        renamed = form.field_defaults(candidate, "PART", final_name="PART_2")
    assert same.value == "PART"
    assert renamed.value == "PART_2"
    assert renamed.mpn == "PART"  # the MPN fallback is the vendor name, as in the planner


def test_build_options_fields():
    defaults = FieldDefaults(value="V", datasheet="https://d", description="", manufacturer="TI", mpn="M")
    options = build_options(
        values(
            fields={
                "manufacturer": "Acme",
                "datasheet": "",
                "description": "",
                "value": "",
                "mpn": " M2 ",
            }
        ),
        defaults,
    )
    assert options.manufacturer == "Acme"
    assert options.mpn == " M2 "  # passed exactly
    assert options.datasheet == "" and "datasheet" in options.cleared
    assert options.value == "" and "value" in options.cleared
    assert options.description is None and "description" not in options.cleared
    assert options.cleared == frozenset({"datasheet", "value"})
    # not edited: nothing is passed
    untouched = build_options(values(fields={"manufacturer": "Acme"}), defaults)
    assert (untouched.value, untouched.datasheet, untouched.description, untouched.mpn) == (None,) * 4
    # whitespace counts as empty
    blank = build_options(values(fields={"datasheet": "   "}), defaults)
    assert blank.datasheet == "" and blank.cleared == frozenset({"datasheet"})


def test_build_options_footprint_name():
    edited = build_options(values(footprint_name="  X1 "), DEFAULTS, linked_vendor="F1")
    assert dict(edited.footprint_names) == {"F1": "X1"}
    assert dict(build_options(values(footprint_name=None), DEFAULTS, linked_vendor="F1").footprint_names) == {}
    # an empty name is an explicit override that the planner refuses
    assert dict(build_options(values(footprint_name=""), DEFAULTS, linked_vendor="F1").footprint_names) == {"F1": ""}
    # nothing is linked, so there is nothing to rename
    assert dict(build_options(values(footprint_name="X"), DEFAULTS, linked_vendor=None).footprint_names) == {}


def test_empty_footprint_name_blocks_the_plan(eq_layout):
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        fp = candidate.footprints[0].name
        blank = build_options(
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprint=fp, footprint_name=""),
            DEFAULTS,
            linked_vendor=fp,
        )
        plan = build_plan(candidate, blank, eq_layout)
        typed = build_options(
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprint=fp, footprint_name="DQK/0006B"),
            DEFAULTS,
            linked_vendor=fp,
        )
        sanitised = build_plan(candidate, typed, eq_layout)
    assert plan.blocked and "install.invalid_name" in [i.code for i in plan.issues]
    assert not sanitised.blocked
    assert sanitised.footprint_names == ("DQK_0006B",)
    assert sanitised.linked_footprint == "DQK_0006B"
    assert [op.path.name for op in sanitised.ops if op.kind == "footprint"] == ["DQK_0006B.kicad_mod"]


def test_typed_footprint_name_case_twin_is_a_conflict(eq_layout):
    """A typed name that differs from an installed footprint only by letter case collides (casefold)."""
    pretty = eq_layout.footprints_dir / f"{footprint_library_for(UL_LIBRARY)}.pretty"
    (pretty / "DQK0006B.kicad_mod").write_bytes(footprint("DQK0006B"))
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        fp = candidate.footprints[0].name
        options = build_options(
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprint=fp, footprint_name="dqk0006b"),
            DEFAULTS,
            linked_vendor=fp,
        )
        plan = build_plan(candidate, options, eq_layout)
    assert plan.blocked
    clash = [c for c in plan.conflicts if c.kind == "footprint"]
    assert len(clash) == 1 and "letter case" in clash[0].existing


# -- plan 05-09 Task 1: library tokens, badge and the kicad-cli cache across rebuilds ----------------

from fakecli import FakeCli  # noqa: E402

from kicad_lib_manager.importer import kicad_cli  # noqa: E402
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_cli_cache():
    kicad_cli.clear_cache()
    yield
    kicad_cli.clear_cache()


def test_the_form_has_no_token_line_rule():
    assert not hasattr(form, "library_tokens")


def test_library_badge():
    names = ["Atomic_Battery_Management", "Atomic_Connector"]
    assert form.NEW_LIBRARY_BADGE == "new - creates .kicad_sym"
    assert form.library_badge("Atomic_Battery_Management", names) == "existing"
    assert form.library_badge("Atomic_Sensor_Temperature", names) == "new - creates .kicad_sym"
    assert form.library_badge("  Atomic_Sensor_Temperature  ", names) == "new - creates .kicad_sym"
    # a name the rule refuses gets no badge: a case twin, a v1 name, a hand-made name, a bare KiCad name
    assert form.library_badge("atomic_battery_management", names) == ""
    assert form.library_badge("IC_Battery_Charger_TI", names) == ""
    assert form.library_badge("Atomic_MyStuff", names) == ""
    assert form.library_badge("Battery_Management", names) == ""
    assert form.library_badge("", names) == ""
    assert form.library_badge("   ", names) == ""


def test_library_badge_follows_the_allowed_stems():
    assert form.library_badge("Atomic_Brand_New", []) == ""
    assert form.library_badge("Atomic_Brand_New", [], frozenset({"Brand_New"})) == "new - creates .kicad_sym"
    # an allowed set that lacks a snapshot stem refuses it
    assert form.library_badge("Atomic_Diode", [], frozenset({"Brand_New"})) == ""


def test_cli_runs_once_across_rebuilds(eq_layout):
    """Edge PREV-06/concurrency: only the symbol pick reaches kicad-cli; library, name and field edits hit the cache."""
    cli = FakeCli()
    tools = ToolContext(kicad_cli=Path("kicad-cli-for-tests.exe"), cli_runner=cli)

    def upgrades() -> int:
        return sum(1 for argv in cli.calls if "sym" in argv and "upgrade" in argv)

    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        symbol = candidate.symbols[0].name
        fp = candidate.footprints[0].name
        steps = [
            InstallOptions(library="Atomic_Sensor_Temperature", symbol=symbol, footprint=fp),
            InstallOptions(library="Atomic_Sensor_Pressure", symbol=symbol, footprint=fp),
            InstallOptions(
                library="Atomic_Sensor_Pressure",
                symbol=symbol,
                footprint=fp,
                footprint_names={fp: "DQK6"},
                manufacturer="Acme",
            ),
        ]
        for options in steps:
            plan = build_plan(candidate, options, eq_layout, tools)
            assert not plan.blocked, plan.issues
    assert upgrades() == 1, cli.calls


# -- plan 05-09 Task 2: the blocking reasons, in the UI-SPEC order ------------------------------------

from kicad_lib_manager.importer.form import FormStatus, Reason, blocking_reasons, noop_text, ready_text  # noqa: E402
from kicad_lib_manager.importer.plan import Conflict, InstallPlan  # noqa: E402
from kicad_lib_manager.importer.preview import FileCounts  # noqa: E402
from kicad_lib_manager.importer.stems import name_verdict  # noqa: E402
from kicad_lib_manager.models import Issue, Severity  # noqa: E402

ERR = Severity.ERROR


def status(**changes) -> FormStatus:
    base = {
        "updating": False,
        "build_failed": False,
        "library": TEST_LIBRARY,
        "value_text": "V",
        "mpn_text": "M",
        "resolutions": {},
    }
    base.update(changes)
    return FormStatus(**base)


def fake_plan(issues=(), conflicts=()) -> InstallPlan:
    """A plan carrying only what blocking_reasons reads: its Issues and Conflicts."""
    return InstallPlan(
        vendor="Test",
        source=Path("pkg.zip"),
        layout=None,
        tools=ToolContext(),
        library=TEST_LIBRARY,
        new_symbol_lib=False,
        new_footprint_lib=False,
        symbol_names=("S",),
        footprint_names=("F1",),
        linked_footprint="F1",
        model_file=None,
        source_version=None,
        target_version=None,
        normalised=False,
        ops=(),
        conflicts=tuple(conflicts),
        renames=(),
        issues=tuple(issues),
    )


def pairs(reasons: list[Reason]) -> list[tuple[str, str]]:
    return [(r.text, r.target) for r in reasons]


def test_kind_label():
    assert [form.kind_label(k) for k in ("symbol", "footprint", "model")] == ["symbol", "footprint", "3D model"]


def test_blocking_reasons_order():
    plan = fake_plan(
        issues=(
            Issue(Severity.WARNING, "install.no_model", "A warning is not a reason"),
            Issue(ERR, "install.no_symbol", "The package holds no symbol to install"),
        ),
        conflicts=(
            Conflict("footprint:Lib:f1", "footprint", "F1", "Lib.pretty"),
            Conflict("model:m.step", "model", "m.step", "3DModels"),
            Conflict("symbol:S", "symbol", "S", "Lib.kicad_sym", resolution=Resolution("skip")),
        ),
    )
    reasons = blocking_reasons(status(value_text=""), plan)
    assert pairs(reasons) == [
        ("Error: The package holds no symbol to install", "plan"),
        ("Value is empty", "value"),
        ("Choose Overwrite, Rename or Skip for footprint F1", "conflict:footprint:Lib:f1"),
        ("Choose Overwrite, Rename or Skip for 3D model m.step", "conflict:model:m.step"),
    ]
    # the library and MPN reasons follow the plan Issues
    reasons = blocking_reasons(status(library="", mpn_text="  "), None)
    assert pairs(reasons) == [("Pick or type a library name", "library"), ("MPN is empty - it names the 3D model file", "mpn")]
    assert blocking_reasons(status(), fake_plan()) == []
    assert blocking_reasons(status(), None) == []


def test_blocking_reasons_model_error():
    """A rejected 3D model source is a blocking reason on the model row, after the plan errors (G-07-5)."""
    plan = fake_plan(issues=(Issue(ERR, "install.no_symbol", "x"),))
    text = "m.step holds no usable 3D model"
    reasons = blocking_reasons(status(model_error=text, value_text=""), plan)
    assert pairs(reasons) == [
        ("Error: x", "plan"),
        (f"Error: {text}", "model"),
        ("Value is empty", "value"),
    ]
    reasons = blocking_reasons(status(model_error=text, build_failed=True), plan)
    assert pairs(reasons) == [
        ("Error: Preview could not be built - see the log", "plan"),
        (f"Error: {text}", "model"),
    ]
    assert blocking_reasons(status(model_error=text, updating=True), plan) == [Reason("Updating preview...", "plan")]
    for blank in ("", "  "):
        assert blocking_reasons(status(model_error=blank), fake_plan()) == []


def test_blocking_reasons_updating_alone():
    plan = fake_plan(issues=(Issue(ERR, "install.no_symbol", "x"),))
    reasons = blocking_reasons(status(updating=True, value_text="", library=""), plan)
    assert reasons == [Reason("Updating preview...", "plan")]


def test_blocking_reasons_build_failed():
    plan = fake_plan(issues=(Issue(ERR, "install.no_symbol", "stale plan error"),))
    reasons = blocking_reasons(status(build_failed=True, value_text=""), plan)
    assert pairs(reasons) == [
        ("Error: Preview could not be built - see the log", "plan"),
        ("Value is empty", "value"),
    ]


def test_blocking_reasons_dedup():
    """A plan ERROR that a form reason already explains is not repeated (D-09)."""
    conflict = Conflict("footprint:F1", "footprint", "F1", "Lib.pretty")
    cases = [
        # a v1 library name: the verdict reason is the only line
        (
            status(library="IC_SubCategory_TI"),
            Issue(ERR, "install.invalid_library", name_verdict("IC_SubCategory_TI").reason),
            [(name_verdict("IC_SubCategory_TI").reason, "library")],
        ),
        # empty library name
        (
            status(library=""),
            Issue(ERR, "install.invalid_library", name_verdict("").reason),
            [("Pick or type a library name", "library")],
        ),
        # empty Value and empty MPN
        (status(value_text=""), Issue(ERR, "install.empty_required", "Value cannot be empty; enter a value"), [("Value is empty", "value")]),
        (
            status(mpn_text=""),
            Issue(ERR, "install.empty_required", "MPN cannot be empty: it names the 3D model file; enter a part number"),
            [("MPN is empty - it names the 3D model file", "mpn")],
        ),
        # several footprints and no choice: the plan's own refusal is shown, aimed at the footprint choice
        (
            status(),
            Issue(ERR, "install.choice_required", "The package holds several footprints; choose from: F1, F2"),
            [("Error: The package holds several footprints; choose from: F1, F2", "footprints")],
        ),
    ]
    for form_status, issue, expected in cases:
        assert pairs(blocking_reasons(form_status, fake_plan(issues=(issue,)))) == expected, issue.code

    # an empty rename key: the bad_rename Issue and the plain conflict reason give way to "Enter a new name"
    blank = status(resolutions={"footprint:F1": Resolution("rename", rename_to="  ")})
    bad = Issue(ERR, "install.bad_rename", "footprint:F1: '' has no usable characters; enter another name")
    assert pairs(blocking_reasons(blank, fake_plan(issues=(bad,), conflicts=(conflict,)))) == [
        ("Enter a new name for footprint F1", "rename:footprint:F1")
    ]
    # a bad_rename for a name that is typed but taken is a different problem and stays
    taken = status(resolutions={"footprint:F1": Resolution("rename", rename_to="Other")})
    taken_issue = Issue(ERR, "install.bad_rename", "footprint:F1: Lib.pretty already holds Other, so Other is not free; enter another name")
    assert pairs(blocking_reasons(taken, fake_plan(issues=(taken_issue,), conflicts=(conflict,)))) == [
        ("Error: " + taken_issue.text, "plan"),
        ("Choose Overwrite, Rename or Skip for footprint F1", "conflict:footprint:F1"),
    ]


def test_blocking_reasons_issue_targets_link_the_control():
    """A plan ERROR about the library, the footprint name or a field links to that control."""
    clash = Issue(ERR, "install.library_case_clash", "ic_x differs from the existing library IC_x only by letter case")
    assert pairs(blocking_reasons(status(), fake_plan(issues=(clash,)))) == [("Error: " + clash.text, "library")]
    bad_name = Issue(ERR, "install.invalid_name", "The footprint name '' has no usable characters; enter another name")
    assert pairs(blocking_reasons(status(), fake_plan(issues=(bad_name,)))) == [("Error: " + bad_name.text, "footprint_name")]
    # a plan ERROR about a name the form accepts is not explained by the form, so it stays and links the library field
    invalid = Issue(ERR, "install.invalid_library", "The library name was refused")
    assert pairs(blocking_reasons(status(), fake_plan(issues=(invalid,)))) == [("Error: " + invalid.text, "library")]


def test_blocking_reasons_library_verdict_text():
    reasons = blocking_reasons(status(library="IC_SubCategory_TI"), None)
    assert pairs(reasons) == [(name_verdict("IC_SubCategory_TI").reason, "library")]
    assert "Atomic_" in reasons[0].text
    two = blocking_reasons(status(library="Transistor_FET"), None)
    assert pairs(two) == [(name_verdict("Transistor_FET").reason, "library")]
    assert "Atomic_Transistor_FET" in two[0].text


def test_blocking_reasons_empty_rename():
    conflict = Conflict("footprint:F1", "footprint", "F1", "Lib.pretty")
    key = conflict.key
    reasons = blocking_reasons(status(resolutions={key: Resolution("rename", rename_to="  ")}), fake_plan(conflicts=(conflict,)))
    assert pairs(reasons) == [("Enter a new name for footprint F1", f"rename:{key}")]
    # a rename with text, a skip and a rename for a key the plan no longer has give no reason
    fine = status(resolutions={key: Resolution("rename", rename_to="G"), "model:gone": Resolution("rename", rename_to="")})
    assert blocking_reasons(fine, fake_plan(conflicts=(replace_resolution(conflict, Resolution("rename", rename_to="G")),))) == []


def replace_resolution(conflict: Conflict, resolution: Resolution) -> Conflict:
    from dataclasses import replace

    return replace(conflict, resolution=resolution)


def test_ready_and_noop_text():
    assert ready_text(FileCounts(2, 1, 0)) == "✓ Ready to install: 2 new, 1 modified, 0 unchanged files"
    assert noop_text("Lib") == "Nothing to install: this part is already in Lib."


# -- plan 05-10 Task 1: conflict choices are kept by key (D-14a) ----------------------------------


def test_carry_resolutions():
    from kicad_lib_manager.importer.form import carry_resolutions

    r1, r2 = Resolution("skip"), Resolution("overwrite")
    old = {"footprint:L:a": r1, "model:x.step": r2}
    kept = carry_resolutions(old, fake_plan(conflicts=(Conflict("footprint:L:a", "footprint", "a", "L.pretty"),)))
    assert kept == {"footprint:L:a": r1}
    assert kept is not old
    assert carry_resolutions(old, fake_plan()) == {}
    assert carry_resolutions({}, fake_plan(conflicts=(Conflict("model:x.step", "model", "x.step", "3D"),))) == {}
