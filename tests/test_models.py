import dataclasses

import pytest

from kicad_lib_manager.models import (
    STATUS_CHANGED, STATUS_NEW, ChangedFootprint, Finding, FixSpec, FootprintLibrary, Issue,
    Severity, SymbolEntry, SymbolLibrary, Violation,
)
from kicad_lib_manager.widgets.log_panel import COLORS


def test_severity_values_equal_log_panel_color_keys():
    assert {s.value for s in Severity} == set(COLORS)


def test_severity_is_constructible_from_its_value():
    assert Severity("error") is Severity.ERROR
    assert Severity("success") is Severity.SUCCESS


def test_issue_has_the_contract_fields_in_order():
    assert [f.name for f in dataclasses.fields(Issue)] == ["severity", "code", "text"]


def test_issue_is_frozen():
    issue = Issue(Severity.INFO, "x.y", "hello")
    with pytest.raises(dataclasses.FrozenInstanceError):
        issue.text = "changed"


# ── Phase 9 result contract: shared by the atomic check, change detection and fix dialog ──

def test_result_contract_dataclasses_have_the_fields_in_order():
    def names(cls):
        return [f.name for f in dataclasses.fields(cls)]

    assert names(FixSpec) == ["kind", "rel_path", "symbol", "label", "params"]
    assert names(Violation) == ["rule", "text", "fixes", "fill", "choices"]
    assert names(Finding) == ["kind", "text", "fix"]
    assert names(SymbolEntry) == ["name", "extends", "status", "violations", "findings"]
    assert names(ChangedFootprint) == ["name", "status"]


def test_status_words():
    assert (STATUS_NEW, STATUS_CHANGED) == ("new", "changed")


@pytest.mark.parametrize("make", [
    lambda: FixSpec("k", "a/b.kicad_sym", "S", "label"),
    lambda: Violation("r", "text"),
    lambda: Finding("k", "text"),
    lambda: ChangedFootprint("A", STATUS_NEW),
])
def test_contract_value_objects_are_frozen(make):
    obj = make()
    field_name = dataclasses.fields(obj)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field_name, "changed")


def test_symbol_entry_failing_follows_violations():
    entry = SymbolEntry("S")
    assert entry.failing is False
    entry.violations.append(Violation("r", "text"))
    assert entry.failing is True


def test_symbol_entry_defaults_are_not_shared():
    a, b = SymbolEntry("A"), SymbolEntry("B")
    a.violations.append(Violation("r", "text"))
    a.findings.append(Finding("k", "text"))
    assert b.violations == [] and b.findings == []


def test_libraries_built_with_old_positional_arguments_get_the_new_defaults():
    sym = SymbolLibrary("N", "Custom/N.kicad_sym", "Custom", [], True, ["x"])
    assert (sym.selected, sym.collision_peers) == (True, ["x"])
    assert (sym.atomic, sym.symbols, sym.check_problem) == (False, [], None)

    fp = FootprintLibrary("N", "Custom/N.pretty", "Custom", True, ["y"])
    assert (fp.selected, fp.collision_peers) == (True, ["y"])
    assert fp.changed == []
