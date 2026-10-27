"""The install gate: build_plan runs the atomic check on the part as it would be installed (LIB-07, D-21, D-24).

Every install targets an isolated Custom/ built in code or a tmp_path folder. A broken rule is an ERROR
install.atomic.<rule> on the plan, so the plan is blocked and apply_plan refuses it before any write.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest
from customfixtures import ABSENT_LIBRARY
from installfixtures import ATOMIC_PROPS, UL_DESCRIPTION, extends_pair
from PySide6.QtCore import QSettings
from test_import_dialog import core_with, set_library, type_description, wait_plan
from zipfixtures import STEP_BYTES, footprint, footprint_library_for, make_zip, symbol_lib, write_custom_layout

from kicad_lib_manager import atomic_check, settings
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.models import FootprintLibrary, Severity, SymbolLibrary
from kicad_lib_manager.widgets.import_dialog import ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
LIBRARY = ABSENT_LIBRARY
SHARED = footprint_library_for(LIBRARY)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def _atomic_errors(plan) -> list[str]:
    return [i.code for i in plan.issues if i.severity is Severity.ERROR and i.code.startswith("install.atomic.")]


def _errors(plan) -> list[str]:
    return [i.code for i in plan.issues if i.severity is Severity.ERROR]


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# -- the tracer: the UL sample blocked on its missing Description, installed once one is typed -----------


def test_the_ul_sample_without_a_description_is_blocked_by_that_rule_alone(ul_package, synthetic_custom, tmp_path):
    _package, candidate = ul_package
    before = _snapshot(synthetic_custom.repo_root)

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), synthetic_custom, ToolContext())

    assert _errors(plan) == ["install.atomic.description"]
    assert plan.blocked
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert _snapshot(synthetic_custom.repo_root) == before


def test_the_ul_sample_with_a_description_installs_and_the_scan_agrees(ul_package, synthetic_custom, tmp_path):
    _package, candidate = ul_package

    plan = build_plan(
        candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), synthetic_custom, ToolContext()
    )

    assert _atomic_errors(plan) == []
    assert not plan.blocked, plan.issues
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues

    # The next scan's check, run over what was installed, finds nothing wrong with the part (gate and scan agree)
    repo = synthetic_custom.repo_root
    sym_libs = [SymbolLibrary(LIBRARY, f"Custom/Symbols/{LIBRARY}.kicad_sym", "Custom")]
    fp_libs = [
        FootprintLibrary(p.name[: -len(".pretty")], f"Custom/Footprints/{p.name}", "Custom")
        for p in sorted(synthetic_custom.footprints_dir.glob("*.pretty"))
    ]
    atomic_check.check_libraries(repo, sym_libs, fp_libs, None)
    entries = {entry.name: entry for entry in sym_libs[0].symbols}
    assert not entries["CSD85301Q2"].failing, entries["CSD85301Q2"].violations


def test_the_dialog_blocks_install_until_the_description_is_typed(qtbot, atomic_custom, tmp_path):
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core_with(), backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)

    set_library(dialog, LIBRARY, fill=False)
    wait_plan(qtbot, dialog)
    assert not dialog._install_btn.isEnabled()
    assert "no description" in dialog._strip.text()

    type_description(dialog)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    wait_plan(qtbot, dialog)
    assert dialog._install_btn.isEnabled()


# -- every rule through the gate (D-21, D-24) ------------------------------------------------------------


@pytest.fixture
def layout(tmp_path) -> RepoLayout:
    """A synthetic Custom/ with an empty Atomic_Footprints folder and no symbol library yet."""
    write_custom_layout(tmp_path, [], [SHARED])
    return RepoLayout.for_repo(tmp_path)


@contextmanager
def _open(tmp_path, members, name="pkg.zip"):
    """Open a synthetic zip, yielding its candidate."""
    folder = tmp_path / "src"
    folder.mkdir(exist_ok=True)
    zip_path = make_zip(folder / name, members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield candidate


def _members(props=None, *, models=("part.step",)):
    """One symbol with the atomic fields (unless props says otherwise), footprint FP and the given STEP models."""
    symbol = symbol_lib(("PART",), props=ATOMIC_PROPS if props is None else props)
    return [("part.kicad_sym", symbol), ("FP.kicad_mod", footprint("FP")), *((name, STEP_BYTES) for name in models)]


def _plan(tmp_path, layout, members, options=None):
    with _open(tmp_path, members) as candidate:
        return build_plan(candidate, options or InstallOptions(library=LIBRARY), layout, ToolContext())


def _apply(tmp_path, layout, members, options=None):
    """Plan and apply with the package still open (the model is read again when the plan is applied); returns (plan, result)."""
    with _open(tmp_path, members) as candidate:
        plan = build_plan(candidate, options or InstallOptions(library=LIBRARY), layout, ToolContext())
        return plan, apply_plan(plan, backup_root=tmp_path / "bk")


def _text(plan, code) -> str:
    return next(i.text for i in plan.issues if i.code == code)


def test_an_atomic_part_with_its_model_installs(tmp_path, layout):
    plan, result = _apply(tmp_path, layout, _members())
    assert _errors(plan) == []
    assert not plan.blocked, plan.issues
    assert result.ok, result.issues


def test_a_part_without_a_model_is_blocked_by_the_model_rule(tmp_path, layout):
    before = _snapshot(layout.custom_dir)
    plan, result = _apply(tmp_path, layout, _members(models=()))
    assert _errors(plan) == ["install.atomic.model_3d"]
    assert plan.blocked
    assert not result.ok
    assert _snapshot(layout.custom_dir) == before


def test_declining_the_model_gives_no_way_around_the_model_rule(tmp_path, layout):
    before = _snapshot(layout.custom_dir)
    members = _members(models=("a.step", "b.step"))
    plan, result = _apply(tmp_path, layout, members, InstallOptions(library=LIBRARY, no_model=True))
    assert _errors(plan) == ["install.atomic.model_3d"]
    assert "install.model_declined" in [i.code for i in plan.issues]
    assert plan.blocked
    assert not result.ok
    assert _snapshot(layout.custom_dir) == before


@pytest.mark.parametrize(
    ("props", "expected"),
    [
        ({**ATOMIC_PROPS, "Datasheet": "~"}, "install.atomic.datasheet"),
        ({**ATOMIC_PROPS, "Description": ""}, "install.atomic.description"),
        (
            {"Description": "Test part", "Datasheet": "https://example.com/part.pdf"},
            "install.atomic.manufacturer",
        ),
    ],
    ids=["no datasheet", "no description", "no manufacturer"],
)
def test_one_missing_field_is_one_gate_error(tmp_path, layout, props, expected):
    plan, result = _apply(tmp_path, layout, _members(props))
    assert _atomic_errors(plan) == [expected]
    assert plan.blocked
    assert not result.ok


def test_a_footprint_and_model_already_in_the_library_count_as_present(tmp_path, layout):
    _first, result = _apply(tmp_path, layout, _members())
    assert result.ok, result.issues
    # The same footprint and model go to another library: both are on disk, so nothing is planned for them
    plan = _plan(tmp_path, layout, _members(), InstallOptions(library="Atomic_Sensor_Pressure"))
    assert _errors(plan) == []
    assert not plan.blocked, plan.issues
    assert [op.kind for op in plan.ops] == ["symbol_lib"]
    assert "install.footprint_reused" in [i.code for i in plan.issues]


def test_an_open_footprint_conflict_is_listed_beside_the_gate_verdict_of_the_planned_bytes(tmp_path, layout):
    # The folder holds a different FP that links a model nobody installed; the part is judged on what it would write
    folder = layout.footprints_dir / f"{SHARED}.pretty"
    (folder / "FP.kicad_mod").write_bytes(footprint("FP", model="${CUSTOM_3DMODEL_DIR}/gone.step"))
    plan = _plan(tmp_path, layout, _members())
    assert [c.kind for c in plan.conflicts] == ["footprint"]
    assert _atomic_errors(plan) == []
    assert plan.blocked

    # The same conflict beside a part that fails the rule lists both
    plan = _plan(tmp_path, layout, _members({**ATOMIC_PROPS, "Description": ""}))
    assert [c.kind for c in plan.conflicts] == ["footprint"]
    assert _atomic_errors(plan) == ["install.atomic.description"]


def test_a_parent_without_a_description_is_named_and_the_child_is_judged_on_its_own_fields(tmp_path, layout):
    props = {key: value for key, value in ATOMIC_PROPS.items() if key != "Description"}
    members = [
        ("part.kicad_sym", extends_pair("PARENT_X", "CHILD_Y", props=props)),
        ("FP.kicad_mod", footprint("FP")),
        ("part.step", STEP_BYTES),
    ]
    options = InstallOptions(library=LIBRARY, symbol="CHILD_Y", description=UL_DESCRIPTION)
    plan = _plan(tmp_path, layout, members, options)
    assert _atomic_errors(plan) == ["install.atomic.description"]
    assert _text(plan, "install.atomic.description") == "PARENT_X: no description"
    assert plan.blocked


def test_a_symbol_kept_with_skip_gets_no_gate_check(tmp_path, layout):
    # PART exists in the library already and differs from the vendor symbol; Skip keeps it, so nothing is written
    sym_path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    sym_path.write_bytes(symbol_lib(("PART",), props={"Footprint": "x:y"}))
    members = _members({"Datasheet": "https://example.com/part.pdf"}, models=())
    options = InstallOptions(library=LIBRARY, resolutions={f"symbol:{LIBRARY}:PART": Resolution("skip")})
    plan = _plan(tmp_path, layout, members, options)
    assert _atomic_errors(plan) == []
    assert "install.symbol_kept" in [i.code for i in plan.issues]


def test_an_unknown_manufacturer_is_a_note_and_never_an_error(tmp_path, layout):
    options = InstallOptions(library=LIBRARY, manufacturer="Acme Widgets")
    plan = _plan(tmp_path, layout, _members(), options)
    assert _errors(plan) == []
    notes = [i for i in plan.issues if i.code == "install.atomic_note.unknown_manufacturer"]
    assert [i.severity for i in notes] == [Severity.INFO]
    assert not plan.blocked, plan.issues
