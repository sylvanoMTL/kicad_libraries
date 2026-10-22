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
        "footprints": (),
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
            footprints=("F2", "F1"),
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
    assert options.footprints == ("F2", "F1")
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
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib, write_custom_layout  # noqa: E402

from kicad_lib_manager.importer import form  # noqa: E402
from kicad_lib_manager.importer.detect import detect_candidate  # noqa: E402
from kicad_lib_manager.importer.layout import RepoLayout  # noqa: E402
from kicad_lib_manager.importer.package import open_package  # noqa: E402
from kicad_lib_manager.importer.planner import build_plan  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_LIBRARY = "IC_Battery_Charger_TI"
TEST_LIBRARY = "IC_Test_TI"
_TI_DATASHEET = {"Datasheet": "https://www.ti.com/lit/gpn/part"}


@pytest.fixture
def eq_layout(tmp_path):
    write_custom_layout(tmp_path / "repo", [UL_LIBRARY, TEST_LIBRARY], [UL_LIBRARY, TEST_LIBRARY])
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
    # "renamed": the vendor name changes when it is sanitised, and Value follows it
    return _synthetic(tmp_path, symbol_lib(("PART/1",), props=_TI_DATASHEET)), TEST_LIBRARY


@pytest.mark.parametrize("case", ["ul", "aliases", "inferred", "renamed"])
def test_field_defaults_equivalence(case, eq_layout, tmp_path):
    """What the form shows equals what the planner writes: typing every default changes nothing (Pitfall 9)."""
    zip_path, library = _equivalence_package(case, tmp_path)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        symbol = candidate.symbols[0]
        base = FormValues(
            library=library,
            symbol=symbol.name,
            footprints=tuple(f.name for f in candidate.footprints),
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
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprints=(fp,), footprint_name=""),
            DEFAULTS,
            linked_vendor=fp,
        )
        plan = build_plan(candidate, blank, eq_layout)
        typed = build_options(
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprints=(fp,), footprint_name="DQK/0006B"),
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
    pretty = eq_layout.footprints_dir / f"{UL_LIBRARY}.pretty"
    (pretty / "DQK0006B.kicad_mod").write_bytes(footprint("DQK0006B"))
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        fp = candidate.footprints[0].name
        options = build_options(
            values(library=UL_LIBRARY, symbol=candidate.symbols[0].name, footprints=(fp,), footprint_name="dqk0006b"),
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
from kicad_lib_manager.importer.suggest import LibrarySuggestion, TokenChoice  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_cli_cache():
    kicad_cli.clear_cache()
    yield
    kicad_cli.clear_cache()


def _suggestion(name: str = "IC_SubCategory_TI") -> LibrarySuggestion:
    """The UL sample's suggestion: SubCategory is a placeholder, TI is a low-confidence host guess."""
    return LibrarySuggestion(
        name=name,
        type=TokenChoice("IC", "reference", True),
        subcategory=TokenChoice("SubCategory", "placeholder", False),
        manufacturer=TokenChoice("TI", "host_guess", False),
        confidence="low",
        placeholders=("SubCategory",),
        matches_existing=False,
        alternatives=(),
        issues=(),
    )


def test_library_tokens():
    suggestion = _suggestion()
    # the untouched suggestion: the placeholder and the low-confidence guess are amber
    assert form.library_tokens("IC_SubCategory_TI", suggestion) == [("IC", False), ("SubCategory", True), ("TI", True)]
    # an edit counts as confirmation of the rest: only placeholders stay amber
    assert form.library_tokens("IC_Power_TI", suggestion) == [("IC", False), ("Power", False), ("TI", False)]
    assert form.library_tokens("IC_Manufacturer_TI", suggestion) == [("IC", False), ("Manufacturer", True), ("TI", False)]
    # no suggestion: placeholders only
    assert form.library_tokens("IC_SubCategory_TI", None) == [("IC", False), ("SubCategory", True), ("TI", False)]
    assert form.library_tokens("", suggestion) == []
    assert form.library_tokens("", None) == []


def test_library_badge():
    names = ["IC_Battery_Charger_TI", "Connector_USB_GCT"]
    assert form.library_badge("IC_Battery_Charger_TI", names) == "existing"
    assert form.library_badge("IC_New_TI", names) == "new - creates .kicad_sym + .pretty"
    # a case twin is not the same library
    assert form.library_badge("ic_battery_charger_ti", names) == "new - creates .kicad_sym + .pretty"
    assert form.library_badge("", names) == ""
    assert form.library_badge("   ", names) == ""


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
            InstallOptions(library="IC_Power_TI", symbol=symbol, footprints=(fp,)),
            InstallOptions(library="IC_Power2_TI", symbol=symbol, footprints=(fp,)),
            InstallOptions(
                library="IC_Power2_TI", symbol=symbol, footprints=(fp,), footprint_names={fp: "DQK6"}, manufacturer="Acme"
            ),
        ]
        for options in steps:
            plan = build_plan(candidate, options, eq_layout, tools)
            assert not plan.blocked, plan.issues
    assert upgrades() == 1, cli.calls
