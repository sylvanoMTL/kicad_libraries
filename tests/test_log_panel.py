"""LogPanel contract (Phase 1 D-07): severity colours, HTML escaping, Severity formatting (IN-02)."""

import pytest

from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.log_panel import COLORS, LogPanel


@pytest.fixture
def panel(qtbot):
    widget = LogPanel()
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize("severity", list(Severity))
def test_log_issue_uses_severity_colour(panel, severity):
    panel.log_issue(Issue(severity, "x.y", "msg"))
    assert COLORS[severity.value].lower() in panel._text.toHtml().lower()


def test_log_escapes_html(panel):
    panel.log("a <b> & c")
    assert "a <b> & c" in panel._text.toPlainText()
    html_out = panel._text.toHtml()
    assert "&lt;b&gt;" in html_out
    assert "<b>" not in html_out


@pytest.mark.parametrize("severity", list(Severity))
def test_severity_formats_as_value(severity):
    assert str(severity) == severity.value
    assert f"{severity}" == severity.value


def test_severity_lookup_by_value_unchanged():
    assert Severity("warning") is Severity.WARNING
    assert COLORS[Severity.ERROR.value] == COLORS["error"]
