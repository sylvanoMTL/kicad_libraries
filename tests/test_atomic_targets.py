"""The Atomic_ name rule through build_plan and the form: a refused library name stops the plan with its plain reason (Phase 10, LIB-05)."""

import customfixtures
import pytest
from zipfixtures import CURRENT_ATOMIC_SYMBOL_LIBS

from kicad_lib_manager.importer import stems
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.form import FormStatus, blocking_reasons
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan, detect_tools
from kicad_lib_manager.models import Severity


def _errors(plan):
    return [i for i in plan.issues if i.severity is Severity.ERROR]


def _status(library):
    return FormStatus(
        updating=False,
        build_failed=False,
        library=library,
        mpn_text="x",
        resolutions={},
    )


def _assert_refused(plan, library):
    verdict = stems.name_verdict(library)
    assert not verdict.ok
    assert plan.blocked
    assert not plan.ops
    errors = _errors(plan)
    assert [i.code for i in errors] == ["install.invalid_library"]
    assert errors[0].text == verdict.reason


def test_a_bare_kicad_name_is_refused_with_its_reason(synthetic_custom, ul_package, snapshot):
    _, candidate = ul_package
    before = snapshot(synthetic_custom.custom_dir)
    plan = build_plan(candidate, InstallOptions(library="Transistor_FET"), synthetic_custom)
    _assert_refused(plan, "Transistor_FET")
    assert "Atomic_Transistor_FET" in _errors(plan)[0].text
    assert not apply_plan(plan).ok
    assert snapshot(synthetic_custom.custom_dir) == before


def test_an_atomic_name_that_is_absent_on_disk_builds(synthetic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=customfixtures.ABSENT_LIBRARY), synthetic_custom)
    assert customfixtures.ABSENT_LIBRARY == "Atomic_Transistor_FET"
    assert "install.invalid_library" not in [i.code for i in plan.issues]
    sym_ops = [op for op in plan.ops if op.kind == "symbol_lib"]
    assert [op.path for op in sym_ops] == [synthetic_custom.symbols_dir / "Atomic_Transistor_FET.kicad_sym"]
    assert plan.new_symbol_lib


@pytest.mark.parametrize("library", customfixtures.V1_LIBRARY_NAMES)
def test_an_existing_v1_library_is_refused_like_any_other_name(synthetic_custom, ul_package, library):
    _, candidate = ul_package
    assert (synthetic_custom.symbols_dir / f"{library}.kicad_sym").is_file()
    plan = build_plan(candidate, InstallOptions(library=library), synthetic_custom)
    _assert_refused(plan, library)


def test_a_case_variant_is_refused_naming_the_official_spelling(synthetic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library="atomic_transistor_fet"), synthetic_custom)
    _assert_refused(plan, "atomic_transistor_fet")
    assert "Atomic_Transistor_FET" in _errors(plan)[0].text
    assert not any(op.path.name.lower() == "atomic_transistor_fet.kicad_sym" for op in plan.ops)


def test_an_empty_name_is_refused(synthetic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=""), synthetic_custom)
    _assert_refused(plan, "")


def test_the_tools_allowed_stems_decide_the_name(synthetic_custom, ul_package):
    _, candidate = ul_package
    options = InstallOptions(library="Atomic_Brand_New")
    assert any(i.code == "install.invalid_library" for i in build_plan(candidate, options, synthetic_custom).issues)
    tools = ToolContext(allowed_stems=stems.allowed_stems(["Brand_New"]))
    plan = build_plan(candidate, options, synthetic_custom, tools)
    assert "install.invalid_library" not in [i.code for i in plan.issues]


def test_the_form_gives_the_verdict_reason_against_the_library_field():
    reasons = blocking_reasons(_status("Atomic_TI"), None)
    assert [(r.text, r.target) for r in reasons] == [(stems.name_verdict("Atomic_TI").reason, "library")]


def test_the_form_does_not_list_the_plan_error_a_second_time(synthetic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library="Atomic_TI"), synthetic_custom)
    reasons = blocking_reasons(_status("Atomic_TI"), plan)
    assert [r.target for r in reasons] == ["library"]
    assert reasons[0].text == stems.name_verdict("Atomic_TI").reason


def test_the_form_has_no_name_reason_for_an_allowed_name():
    assert blocking_reasons(_status("Atomic_Transistor_FET"), None) == []


def test_the_form_follows_the_allowed_stems_it_is_given():
    status = _status("Atomic_Brand_New")
    assert [r.target for r in blocking_reasons(status, None)] == ["library"]
    allowed = stems.allowed_stems(["Brand_New"])
    assert blocking_reasons(FormStatus(**{**status.__dict__, "allowed": allowed}), None) == []


def test_detect_tools_fills_the_footprints_folder_and_the_allowed_stems(tmp_path):
    footprints, _ = customfixtures.write_fake_kicad(tmp_path)
    tools = detect_tools(footprints)
    assert tools.kicad_footprints_dir == footprints
    assert "Transistor_FET" in tools.allowed_stems
    assert stems.EXCLUDED_STEMS.isdisjoint(tools.allowed_stems)


def test_detect_tools_without_a_footprints_folder_keeps_the_snapshot():
    tools = detect_tools(None)
    assert tools.kicad_footprints_dir is None
    assert stems.KICAD10_STEMS - stems.EXCLUDED_STEMS <= tools.allowed_stems


def test_every_atomic_install_target_of_the_fixtures_passes_the_rule():
    names = [lib.name for lib in customfixtures.SYNTHETIC_LIBRARIES]
    names += [
        customfixtures.BATTERY_CHARGER,
        customfixtures.IMU,
        customfixtures.MAGNETOMETER,
        customfixtures.POWER_MOSFET,
        customfixtures.WIRELESS,
        customfixtures.ABSENT_LIBRARY,
        *CURRENT_ATOMIC_SYMBOL_LIBS,
    ]
    refused = {name: stems.name_verdict(name).reason for name in names if not stems.name_verdict(name).ok}
    assert refused == {}
