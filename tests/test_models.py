import dataclasses

import pytest

from kicad_lib_manager.models import Issue, Severity
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
