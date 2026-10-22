"""D-13: an explicitly cleared field installs as an empty value, and Value / MPN cannot be cleared (Phase 5)."""

import dataclasses

import pytest
from zipfixtures import write_custom_layout

from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import InstallOptions
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes
from kicad_lib_manager.models import Severity

UL_LIBRARY = "IC_Battery_Charger_TI"


@pytest.fixture
def ul_layout(tmp_path):
    """A synthetic Custom/ holding the UL target pair, so these tests never depend on the Custom submodule."""
    write_custom_layout(tmp_path, [UL_LIBRARY], [UL_LIBRARY])
    return RepoLayout.for_repo(tmp_path)


def _chosen_symbol(plan):
    sym_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    return find_symbol(parse_bytes(sym_op.data, "lib").root, plan.symbol_name)


def _prop(plan, name):
    found = find_property(_chosen_symbol(plan).node, name)
    return None if found is None else found.value


def _errors(plan):
    return [i for i in plan.issues if i.severity is Severity.ERROR]


# -- InstallOptions.cleared ------------------------------------------------------


def test_cleared_options_store_empty():
    cleared = frozenset({"datasheet"})
    for blank in ("", "   ", None):
        assert InstallOptions(library="X", datasheet=blank, cleared=cleared).datasheet == ""
    assert InstallOptions(library="X", datasheet="https://a", cleared=cleared).datasheet == "https://a"
    # A field not named in cleared keeps the WR-05 rule
    assert InstallOptions(library="X", value="", cleared=cleared).value is None
    options = InstallOptions(library="X", manufacturer="", cleared=frozenset({"manufacturer"}))
    again = dataclasses.replace(options, value="V")
    assert again.manufacturer == ""
    assert again.cleared == frozenset({"manufacturer"})
    assert again.value == "V"
    with pytest.raises(ValueError, match="footprint"):
        InstallOptions(library="X", cleared=frozenset({"footprint"}))


# -- planner: cleared fields on the UL sample ------------------------------------


def test_cleared_datasheet_writes_empty_property(ul_layout, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({"datasheet"})), ul_layout)
    assert not plan.blocked, plan.issues
    assert _prop(plan, "Datasheet") == ""
    assert _prop(plan, "Value") == "CSD85301Q2"
    assert _prop(plan, "MPN") == "CSD85301Q2"
    assert _prop(plan, "Manufacturer") == "TI"
    assert plan.model_file == "CSD85301Q2.stp"


def test_cleared_manufacturer_skips_inference(ul_layout, ul_package):
    _, candidate = ul_package
    unset = build_plan(candidate, InstallOptions(library=UL_LIBRARY), ul_layout)
    assert _prop(unset, "Manufacturer") == "TI"
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({"manufacturer"})), ul_layout)
    assert not plan.blocked, plan.issues
    assert _prop(plan, "Manufacturer") == ""
    assert "install.manufacturer_missing" not in [i.code for i in plan.issues]
    sym_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    assert b'"TI"' not in sym_op.data


def test_cleared_description_creates_empty_property(ul_layout, ul_package):
    _, candidate = ul_package
    unset = build_plan(candidate, InstallOptions(library=UL_LIBRARY), ul_layout)
    assert _prop(unset, "ki_description") is None and _prop(unset, "Description") is None
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({"description"})), ul_layout)
    assert not plan.blocked, plan.issues
    assert [_prop(plan, "ki_description"), _prop(plan, "Description")].count("") == 1


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("value", "Value cannot be empty; enter a value"),
        ("mpn", "MPN cannot be empty: it names the 3D model file; enter a part number"),
    ],
)
def test_cleared_required_field_refused(ul_layout, ul_package, field, text):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({field})), ul_layout)
    assert plan.blocked and not plan.ops
    assert [(i.code, i.text) for i in _errors(plan)] == [("install.empty_required", text)]


def test_cleared_value_refused(ul_layout, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({"value"})), ul_layout)
    assert plan.blocked and not plan.ops
    assert [i.code for i in _errors(plan)] == ["install.empty_required"]


def test_cleared_mpn_refused(ul_layout, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, cleared=frozenset({"mpn"})), ul_layout)
    assert plan.blocked and not plan.ops
    assert [i.code for i in _errors(plan)] == ["install.empty_required"]
    assert plan.model_file is None


def test_override_text_written_exactly(ul_layout, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, value="Dual N-Channel  FET "), ul_layout)
    assert not plan.blocked, plan.issues
    assert _prop(plan, "Value") == "Dual N-Channel  FET "
