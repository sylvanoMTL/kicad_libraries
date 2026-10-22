"""The commit panel's state machine, driven with fake CommitPlan, CommitProbe and CommitOutcome values (Phase 6)."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import QLabel, QListWidgetItem, QPushButton

from kicad_lib_manager.importer.commit_plan import (
    CommitFile, CommitPlan, default_message, parent_preview, subject_of,
)
from kicad_lib_manager.importer.commit_step import CommitOutcome, CommitProbe
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets import theme
from kicad_lib_manager.widgets.commit_panel import CommitPanel

_FILE_KINDS = (
    ("Symbols/IC_Test.kicad_sym", "symbol"),
    ("Footprints/IC_Test.pretty/FP_X.kicad_mod", "footprint"),
    ("3DModels/x.step", "model"),
)


def make_cplan(tmp_path: Path, n: int = 3, **overrides) -> CommitPlan:
    files = []
    for index in range(n):
        rel, kind = _FILE_KINDS[index % len(_FILE_KINDS)]
        if index >= len(_FILE_KINDS):
            rel = rel.replace(".", f"_{index}.", 1)
        files.append(CommitFile(rel, f"Custom/{rel}", tmp_path / "Custom" / rel, kind, "0" * 64, None))
    fields = dict(
        repo_root=tmp_path,
        custom_dir=tmp_path / "Custom",
        custom_rel="Custom",
        files=tuple(files),
        library="IC_Test",
        new_library=False,
        symbol="PartX",
        footprint="IC_Test:FP_X",
        model="x.step",
        vendor="Ultra Librarian",
        package="x.zip",
        date="2026-01-02",
        overwrite=False,
        backup_dir=None,
        issues=(),
    )
    fields.update(overrides)
    return CommitPlan(**fields)


def make_probe(**fields) -> CommitProbe:
    values = dict(
        state="ready", branch="main", head="abc1234def5678", parent_ok=True, parent_branch="main",
        gitlink_old="1111111aaaa",
    )
    values.update(fields)
    return CommitProbe(**values)


def make_outcome(**fields) -> CommitOutcome:
    return CommitOutcome(**fields)


def new_panel(qtbot, tmp_path, probe: CommitProbe | None = None, *, n: int = 3, **plan_overrides):
    """A panel with a plan shown and, when given, a probe applied. The plan is on the panel as ._plan."""
    panel = CommitPanel()
    qtbot.addWidget(panel)
    cplan = make_cplan(tmp_path, n, **plan_overrides)
    panel.show_plan(cplan)
    if probe is not None:
        if probe.parent_dir is None and probe.state == "ready":
            probe = make_probe(**{**probe.__dict__, "parent_dir": tmp_path})
        panel.apply_probe(probe)
    return panel, cplan


def rows(panel) -> list[str]:
    return [panel._files_list.item(i).text() for i in range(panel._files_list.count())]


def labels(panel) -> list[QLabel]:
    return panel.findChildren(QLabel)


# -- Task 1: every probe state -------------------------------------------------------------------


def test_panel_probing_state(qtbot, tmp_path):
    panel, cplan = new_panel(qtbot, tmp_path)

    assert panel.state() == "probing"
    assert panel._strip.text() == "Checking Custom and the parent repo..."
    assert theme.MUTED in panel._strip.styleSheet()
    assert not panel.commit_button.isEnabled()
    assert rows(panel) == [f.display for f in cplan.files]


def test_panel_ready_shows_branch_files_message(qtbot, tmp_path):
    probe = make_probe(branch="main", parent_branch="feature/part-importer", parent_dir=tmp_path)
    panel, cplan = new_panel(qtbot, tmp_path, probe)

    assert panel.state() == "ready"
    assert panel._branch_label.text() == "Custom branch: main"
    assert panel._parent_label.full_text() == f"Parent repo: {tmp_path.as_posix()} (feature/part-importer)"
    assert panel._files_heading.text() == "Files to commit (3)"
    assert panel.message() == default_message(cplan)
    assert panel._parent_check.isChecked()
    assert panel._parent_check.text() == "Also commit the Custom ref in the parent repo (feature/part-importer)"
    assert panel.commit_button.isEnabled()


def test_panel_not_main_branch_amber(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe(branch="feature/y", not_main=True))

    assert panel._branch_label.text() == "Custom branch: feature/y (not main)"
    assert theme.AMBER in panel._branch_label.styleSheet()
    assert panel.commit_button.isEnabled()


def test_panel_unavailable_reason(qtbot, tmp_path):
    probe = CommitProbe(state="unavailable", reason="git was not found on PATH")
    panel, cplan = new_panel(qtbot, tmp_path, probe)

    assert panel.state() == "unavailable"
    assert panel._strip.text() == "⚠ Commit unavailable: git was not found on PATH"
    assert theme.AMBER_TINT in panel._strip.styleSheet()
    assert panel._message.isReadOnly()
    assert not panel._parent_check.isEnabled()
    assert not panel.commit_button.isEnabled()
    assert not panel._files_list.isHidden() and panel._files_list.count() == len(cplan.files)


def test_panel_refused_reason(qtbot, tmp_path):
    probe = CommitProbe(state="refused", reason="Custom has a merge in progress")
    panel, _ = new_panel(qtbot, tmp_path, probe)

    assert panel.state() == "refused"
    assert panel._strip.text() == "⚠ Commit refused: Custom has a merge in progress"
    assert theme.AMBER_TINT in panel._strip.styleSheet()
    assert panel._message.isReadOnly()
    assert not panel._parent_check.isEnabled()
    assert not panel.commit_button.isEnabled()


def test_panel_offer_switch_row(qtbot, tmp_path):
    reason = "Custom is on a detached HEAD at abc1234 that is on main's history. main is 2 commits ahead."
    probe = CommitProbe(state="offer_switch", head="abc1234def", reason=reason)
    panel, _ = new_panel(qtbot, tmp_path, probe)
    requested = []
    panel.switch_requested.connect(lambda: requested.append(True))

    assert panel.state() == "offer_switch"
    assert panel._branch_label.text() == "Custom: detached HEAD at abc1234"
    assert panel._strip.text() == f"⚠ {reason} Switch to main before committing."
    assert not panel._switch_button.isHidden()
    assert panel._switch_button.text() == "Switch to main"
    assert not panel.commit_button.isEnabled()
    panel._switch_button.click()
    assert requested == [True]


def test_panel_parent_disabled_with_reason(qtbot, tmp_path):
    probe = make_probe(parent_ok=False, parent_reason="the parent repo is on a detached HEAD", parent_branch=None)
    panel, _ = new_panel(qtbot, tmp_path, probe)
    requests = []
    panel.commit_requested.connect(lambda text, bump: requests.append((text, bump)))

    assert not panel._parent_check.isChecked() and not panel._parent_check.isEnabled()
    assert panel._parent_reason.text() == "Parent commit unavailable: the parent repo is on a detached HEAD"
    assert not panel._parent_reason.isHidden()
    panel.commit_button.click()
    assert requests == [(panel.message(), False)]


def test_panel_earlier_commits_listed_and_capped(qtbot, tmp_path):
    earlier = tuple((f"{index:07x}", f"Subject {index}") for index in range(12))
    panel, _ = new_panel(qtbot, tmp_path, make_probe(earlier=earlier))

    lines = panel._earlier_label.text().splitlines()
    assert not panel._earlier_label.isHidden()
    assert lines[0] == "Parent bump also includes 12 earlier Custom commits:"
    assert lines[1:11] == [f"- {h} {s}" for h, s in earlier[:10]]
    assert lines[11] == "…and 2 more"
    assert len(lines) == 12

    panel.apply_probe(make_probe(earlier=earlier[:1], parent_dir=tmp_path))
    assert panel._earlier_label.text() == "Parent bump also includes 1 earlier Custom commit:\n- 0000000 Subject 0"

    panel.apply_probe(make_probe(earlier=(), parent_dir=tmp_path))
    assert panel._earlier_label.isHidden()

    panel.apply_probe(make_probe(earlier=earlier, parent_dir=tmp_path))
    assert not panel._earlier_label.isHidden()
    panel._parent_check.setChecked(False)
    assert panel._earlier_label.isHidden()


def test_panel_parent_preview_follows_subject(qtbot, tmp_path):
    earlier = (("2222222", "Earlier part"),)
    panel, cplan = new_panel(qtbot, tmp_path, make_probe(earlier=earlier))

    expected = parent_preview(subject_of(panel.message()), "Custom", "1111111aaaa", earlier, listed=True)
    assert panel._parent_preview.toPlainText() == expected
    assert "<new commit>" in expected
    assert panel._parent_preview.isReadOnly()
    assert not panel._parent_preview.isHidden()

    panel._message.setPlainText("Add X to Y\n\nbody")
    assert panel._parent_preview.toPlainText().splitlines()[0] == "Update Custom: Add X to Y"

    panel._parent_check.setChecked(False)
    assert panel._parent_preview.isHidden()


def test_panel_blank_message_disables_commit(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe())
    assert panel._blank_label.isHidden()

    panel._message.setPlainText("  \n ")
    assert not panel.commit_button.isEnabled()
    assert panel._blank_label.text() == "Enter a commit message"
    assert not panel._blank_label.isHidden()
    assert theme.AMBER in panel._blank_label.styleSheet()

    panel._message.setPlainText("Add X")
    assert panel.commit_button.isEnabled()
    assert panel._blank_label.isHidden()


def test_panel_file_list_read_only_no_checkboxes(qtbot, tmp_path):
    panel, cplan = new_panel(qtbot, tmp_path, make_probe())

    for index, commit_file in enumerate(cplan.files):
        item = panel._files_list.item(index)
        assert not item.flags() & Qt.ItemFlag.ItemIsUserCheckable
        assert not item.flags() & Qt.ItemFlag.ItemIsEditable
        assert commit_file.display in item.toolTip()


def test_panel_dirty_file_amber_and_activation(qtbot, tmp_path):
    panel, cplan = new_panel(qtbot, tmp_path, make_probe(dirty_before=frozenset({"Footprints/IC_Test.pretty/FP_X.kicad_mod"})))
    activated = []
    panel.file_activated.connect(activated.append)
    dirty, clean = panel._files_list.item(1), panel._files_list.item(0)

    assert dirty.text() == f"⚠ {cplan.files[1].display}"
    assert dirty.foreground().color() == QColor(theme.AMBER)
    assert "also contains uncommitted changes made before this import" in dirty.toolTip()
    assert clean.text() == cplan.files[0].display
    assert not panel._dirty_hint.isHidden()

    panel._files_list.itemActivated.emit(clean)
    assert activated == []
    panel._files_list.itemActivated.emit(dirty)
    assert activated == ["Footprints/IC_Test.pretty/FP_X.kicad_mod"]

    panel._files_list.setCurrentItem(dirty)
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    event.ignore()
    panel._files_list.keyPressEvent(event)
    assert event.isAccepted()
    assert activated == ["Footprints/IC_Test.pretty/FP_X.kicad_mod"] * 2

    panel._files_list.setCurrentItem(clean)
    panel._files_list.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert len(activated) == 2


def test_panel_other_changes_line(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe(other_changes=3))
    assert panel._other_label.text() == "3 other changes in Custom stay uncommitted"
    assert theme.MUTED in panel._other_label.styleSheet()
    assert not panel._other_label.isHidden()

    panel.apply_probe(make_probe(other_changes=1, parent_dir=tmp_path))
    assert panel._other_label.text() == "1 other change in Custom stays uncommitted"

    panel.apply_probe(make_probe(other_changes=0, parent_dir=tmp_path))
    assert panel._other_label.isHidden()


def test_panel_buttons_not_default(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe())

    for button in (panel.commit_button, panel._switch_button):
        assert not button.autoDefault() and not button.isDefault()


def test_panel_text_is_plain(qtbot, tmp_path):
    probe = CommitProbe(state="unavailable", reason="<b>x</b> is bold")
    panel, _ = new_panel(qtbot, tmp_path, probe)

    assert panel._strip.text() == "⚠ Commit unavailable: <b>x</b> is bold"
    assert labels(panel)
    assert all(label.textFormat() == Qt.TextFormat.PlainText for label in labels(panel))
    assert isinstance(panel._switch_button, QPushButton) and isinstance(panel._files_list.item(0), QListWidgetItem)
