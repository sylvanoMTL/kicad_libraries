"""The commit panel's state machine, driven with fake CommitPlan, CommitProbe and CommitOutcome values (Phase 6)."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import QLabel, QListWidgetItem, QPushButton

from kicad_lib_manager.importer.commit_plan import (
    CommitFile, CommitPlan, default_message, parent_only_preview, parent_preview, subject_of,
)
from kicad_lib_manager.importer.commit_gate import AtomicFailure, GateResult
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



# -- Task 2: committing, outcomes, git output, long text -----------------------------------------


def ready_panel(qtbot, tmp_path, **probe_fields):
    panel, cplan = new_panel(qtbot, tmp_path, make_probe(**probe_fields))
    assert panel.state() == "ready"
    return panel, cplan


def issue(severity: Severity, code: str, text: str) -> Issue:
    return Issue(severity, code, text)


def test_panel_committing_locks_inputs(qtbot, tmp_path):
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QProgressBar

    panel, _ = ready_panel(qtbot, tmp_path)
    requests = []
    panel.commit_requested.connect(lambda text, bump: requests.append((text, bump)))

    panel.commit_button.click()
    assert requests == [(panel.message(), True)]
    panel.set_committing()

    assert panel.state() == "committing"
    assert panel._message.isReadOnly()
    assert not panel._parent_check.isEnabled()
    assert panel.commit_button.text() == "Committing..." and not panel.commit_button.isEnabled()
    assert not panel._step_row.isHidden()
    bar = panel._step_row.findChild(QProgressBar)
    assert bar.minimum() == bar.maximum() == 0
    assert bar.minimumSize() == bar.maximumSize() == QSize(theme.SP_XL * 8, theme.SP_MD)
    panel.commit_button.click()
    panel._on_commit_clicked()
    assert len(requests) == 1


def test_panel_step_text(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()

    panel.set_step("Committing Custom ref in parent...")

    assert panel._step.text() == "Committing Custom ref in parent..."
    assert theme.MUTED in panel._step.styleSheet()


def test_panel_done_read_only(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    outcome = make_outcome(
        custom_commit="abc1234",
        parent_commit="def5678",
        issues=(
            issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
            issue(Severity.INFO, "commit.not_pushed", "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)"),
            issue(Severity.SUCCESS, "commit.parent_done", "Committed def5678 on main in the parent repo"),
            issue(Severity.INFO, "commit.not_pushed", "Not pushed — the parent repo is 3 commits ahead of origin/main (as last fetched)"),
        ),
    )

    panel.show_outcome(outcome)

    assert panel.state() == "done"
    assert panel.outcome_lines() == [
        "✓ Committed abc1234 on main in Custom",
        "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)",
        "✓ Committed def5678 on main in the parent repo",
        "Not pushed — the parent repo is 3 commits ahead of origin/main (as last fetched)",
    ]
    assert panel._message.isReadOnly()
    assert not panel._parent_check.isEnabled()
    assert panel.commit_button.text() == "Committed" and not panel.commit_button.isEnabled()
    assert panel.committed()
    assert panel._step_row.isHidden()
    assert theme.SUCCESS in panel._outcome_labels[0].styleSheet()


def test_panel_partial_failure_keeps_hash_no_retry(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    manual = 'git -C "C:/x" commit -m "Update Custom: Add P to L" -- Custom'
    failure = (
        "The Custom commit abc1234 was kept, but the parent commit failed (git exit 1).\n"
        f"hook said no\nFinish it by hand: {manual}"
    )
    outcome = make_outcome(
        custom_commit="abc1234",
        manual_command=manual,
        output="hook said no",
        issues=(
            issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
            issue(Severity.ERROR, "commit.parent_failed", failure),
        ),
    )

    panel.show_outcome(outcome)

    assert panel.state() == "failed"
    assert panel.commit_button.text() == "Committed in Custom only"
    lines = panel.outcome_lines()
    assert "✓ Committed abc1234 on main in Custom" in lines
    assert "✖ The Custom commit abc1234 was kept, but the parent commit failed (git exit 1)." in lines
    assert panel._manual_label.text() == f"Finish it by hand: {manual}"
    assert not panel._manual_label.isHidden()
    assert panel._manual_label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert not panel.commit_button.isEnabled()
    assert not [b for b in panel.findChildren(QPushButton) if "retry" in b.text().lower()]
    assert panel._output.toPlainText() == "hook said no"


_PS_LABEL = "Finish it by hand. In PowerShell:"
_PS_MANUAL = "git -C 'C:/x' commit -m 'Update Custom: Add P to L' -- 'Custom'"


def test_panel_manual_label_partial_failure(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    failure = f"The Custom commit abc1234 was kept, but the parent commit failed (git exit 1).\nhook said no\n{_PS_LABEL} {_PS_MANUAL}"
    outcome = make_outcome(
        custom_commit="abc1234",
        manual_command=_PS_MANUAL,
        manual_label=_PS_LABEL,
        output="",
        issues=(
            issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
            issue(Severity.ERROR, "commit.parent_failed", failure),
        ),
    )

    panel.show_outcome(outcome)

    assert panel._manual_label.text() == f"{_PS_LABEL} {_PS_MANUAL}"
    assert not panel._manual_label.isHidden()
    assert not any(line.startswith("Finish it by hand") for line in panel._output.toPlainText().splitlines())
    assert panel._output.toPlainText() == "hook said no"


def test_panel_manual_label_late_commit(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    outcome = make_outcome(
        custom_commit="abc1234",
        manual_command=_PS_MANUAL,
        manual_label=_PS_LABEL,
        issues=(
            issue(Severity.WARNING, "commit.custom_unfinished", "Committed abc1234 in Custom, but git did not finish in time"),
            issue(
                Severity.WARNING, "commit.parent_not_started",
                f"The parent repo was not updated, because git may still be running in Custom.\n{_PS_LABEL} {_PS_MANUAL}",
            ),
        ),
    )

    panel.show_outcome(outcome)

    assert panel.state() == "done"
    assert panel._manual_label.text() == f"{_PS_LABEL} {_PS_MANUAL}"
    assert not panel._manual_label.isHidden()
    assert not any(_PS_MANUAL in line for line in panel.outcome_lines())  # shown once, in its own selectable line


def test_panel_manual_label_falls_back_to_plain_label(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    manual = "git -C /x commit -m msg -- Custom"

    panel.show_outcome(make_outcome(
        custom_commit="abc1234", manual_command=manual,
        issues=(issue(Severity.ERROR, "commit.parent_failed", "The parent commit failed"),),
    ))

    assert panel._manual_label.text() == f"Finish it by hand: {manual}"


_REFUSAL = "The Custom branch changed from main to feature/x since the preview; nothing was committed"


def refused_panel(qtbot, tmp_path):
    """A ready panel whose user edited the message and unticked the parent box, then got a refusal."""
    panel, _ = ready_panel(qtbot, tmp_path, parent_dir=tmp_path)
    panel._message.setPlainText("My own message")
    panel._parent_check.setChecked(False)
    panel.set_committing()
    panel.show_outcome(make_outcome(issues=(issue(Severity.ERROR, "commit.branch_changed", _REFUSAL),)))
    return panel


def test_panel_refusal_waits_for_reprobe(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)

    assert panel.state() == "probing"
    assert not panel.commit_button.isEnabled()
    assert panel.outcome_lines() == [f"✖ {_REFUSAL}"]
    assert panel.message() == "My own message"
    assert panel.committed() is False


def test_panel_reprobe_keeps_refusal_message_and_parent_choice(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)

    panel.apply_probe(make_probe(branch="feature/x", not_main=True, parent_dir=tmp_path))

    assert panel.state() == "ready"
    assert panel._branch_label.text() == "Custom branch: feature/x (not main)"
    assert panel.outcome_lines()[0] == f"✖ {_REFUSAL}"
    assert panel.message() == "My own message"
    assert panel._parent_check.isEnabled() and not panel._parent_check.isChecked()
    assert panel.commit_button.isEnabled()


def test_panel_own_refusal_replaces_pending(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)

    panel.apply_probe(CommitProbe(state="refused", reason="R"))

    assert panel.state() == "refused"
    assert not panel.commit_button.isEnabled()
    assert panel.outcome_lines() == []
    assert panel._strip.text() == "⚠ Commit refused: R"
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel.outcome_lines() == []


def test_panel_pending_refusal_cleared_by_commit_click(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)
    requests = []
    panel.commit_requested.connect(lambda text, bump: requests.append((text, bump)))
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel.outcome_lines() == [f"✖ {_REFUSAL}"]

    panel.commit_button.click()

    assert requests == [("My own message", False)]
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel.outcome_lines() == []


def test_panel_pending_refusal_cleared_by_switch_click(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)
    requested = []
    panel.switch_requested.connect(lambda: requested.append(True))
    panel.apply_probe(CommitProbe(state="offer_switch", head="abc1234def", reason="Custom is on a detached HEAD."))

    panel._switch_button.click()

    assert requested == [True]
    assert panel._pending_refusal == ()


def test_panel_parent_choice_kept_across_probes(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe(parent_dir=tmp_path))
    assert panel._parent_check.isChecked()

    panel._parent_check.setChecked(False)
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert not panel._parent_check.isChecked() and panel._parent_check.isEnabled()

    panel.apply_probe(make_probe(parent_ok=False, parent_reason="detached", parent_branch=None, parent_dir=tmp_path))
    assert not panel._parent_check.isChecked() and not panel._parent_check.isEnabled()

    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert not panel._parent_check.isChecked() and panel._parent_check.isEnabled()

    panel.show_plan(make_cplan(tmp_path))
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel._parent_check.isChecked()


def test_panel_ticked_choice_comes_back_after_disabled_probe(qtbot, tmp_path):
    panel, _ = new_panel(qtbot, tmp_path, make_probe(parent_dir=tmp_path))

    panel.apply_probe(make_probe(parent_ok=False, parent_reason="detached", parent_branch=None, parent_dir=tmp_path))
    assert not panel._parent_check.isChecked()
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel._parent_check.isChecked()


def test_panel_begin_reprobe_with_new_plan(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel._message.setPlainText("Keep me")

    panel.begin_reprobe(make_cplan(tmp_path, 4))

    assert panel.state() == "probing"
    assert panel.message() == "Keep me"
    assert panel._files_list.count() == 4
    assert panel._files_heading.text() == "Files to commit (4)"
    assert panel._branch_label.text() == "Custom branch: checking..."
    assert not panel.commit_button.isEnabled()

    panel.begin_reprobe()
    assert panel._files_list.count() == 4 and panel.message() == "Keep me"


def test_panel_hook_output_box_capped_and_filtered(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    lines = [f"hook line {index}" for index in range(20)]
    lines[3] = "warning: in the working copy of 'a.kicad_sym', LF will be replaced by CRLF"
    lines[9] = "warning: in the working copy of 'b.kicad_mod', LF will be replaced by CRLF"
    panel.set_committing()
    failed = issue(Severity.ERROR, "commit.custom_failed", "Commit in Custom failed (git exit 1); nothing was committed")

    panel.show_outcome(make_outcome(output="\n".join(lines), issues=(failed,)))

    box = panel._output
    shown = box.toPlainText().splitlines()
    assert len(shown) == 18 and not any(line.startswith("warning: in the working copy of") for line in shown)
    assert box.isReadOnly() and not box.isHidden()
    assert box.minimumHeight() == box.maximumHeight() >= 8 * box.fontMetrics().lineSpacing()
    assert box.minimumHeight() < 18 * box.fontMetrics().lineSpacing()

    panel.show_outcome(make_outcome(issues=(failed,)))
    assert box.isHidden()


def test_panel_switching_and_switch_failed(qtbot, tmp_path):
    probe = CommitProbe(state="offer_switch", head="abc1234def", reason="Custom is on a detached HEAD at abc1234.")
    panel, _ = new_panel(qtbot, tmp_path, probe)

    panel.set_switching()
    assert panel.state() == "switching"
    assert not panel._switch_button.isEnabled() and not panel._switch_button.isHidden()
    assert panel._strip.text() == "Switching Custom to main..."
    assert not panel.commit_button.isEnabled()

    panel.show_switch_failed(
        "git refused to switch Custom to main; nothing was committed\nerror: Your local changes would be overwritten"
    )
    assert panel.state() == "offer_switch"
    assert panel._switch_button.isEnabled()
    assert panel.outcome_lines() == ["✖ git refused to switch Custom to main; nothing was committed"]
    assert theme.ERROR in panel._outcome_labels[0].styleSheet()
    assert panel._output.toPlainText() == "error: Your local changes would be overwritten"
    assert panel._strip.text().endswith("Switch to main before committing.")


def test_panel_long_paths_elide_with_tooltip(qtbot, tmp_path):
    long_parent = tmp_path / ("p" * 200)
    long_name = "Custom/Symbols/" + "x" * 150 + ".kicad_sym"
    panel = CommitPanel()
    qtbot.addWidget(panel)
    cplan = make_cplan(tmp_path)
    long_file = CommitFile("Symbols/" + "x" * 150 + ".kicad_sym", long_name, tmp_path / long_name, "symbol", "0" * 64, None)
    panel.show_plan(make_cplan(tmp_path, files=(long_file, *cplan.files[1:])))
    panel.apply_probe(make_probe(parent_dir=long_parent))

    assert panel.sizeHint().width() <= 600
    assert panel._parent_label.full_text().startswith("Parent repo: ") and "p" * 200 in panel._parent_label.full_text()
    assert "p" * 200 in panel._parent_label.toolTip()
    assert long_name in panel._files_list.item(0).toolTip()


# -- UI-02: primary Commit, tinted outcome strip, honest partial label, theme sizes ----------------


def partial_outcome():
    manual = 'git -C "C:/x" commit -m "Update Custom: Add P to L" -- Custom'
    return make_outcome(
        custom_commit="abc1234",
        manual_command=manual,
        output="hook said no",
        issues=(
            issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
            issue(Severity.ERROR, "commit.parent_failed", "The Custom commit abc1234 was kept, but the parent commit failed"),
        ),
    )


def test_panel_commit_button_primary(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)

    assert panel.commit_button.styleSheet() == theme.PRIMARY_BUTTON_QSS
    assert panel._switch_button.styleSheet() == ""


def test_panel_outcome_tint_success(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()

    panel.show_outcome(make_outcome(issues=(
        issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
        issue(Severity.INFO, "commit.not_pushed", "Not pushed"),
    )))

    assert theme.SUCCESS_TINT in panel._outcome_frame.styleSheet()
    assert not panel._outcome_frame.isHidden()
    assert theme.SUCCESS in panel._outcome_labels[0].styleSheet()


def test_panel_outcome_tint_error(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()
    panel.show_outcome(partial_outcome())
    assert theme.ERROR_TINT in panel._outcome_frame.styleSheet()
    assert panel._outcome_frame.objectName() == "outcomeStrip"

    refused, _ = ready_panel(qtbot, tmp_path)
    refused.set_committing()
    refused.show_outcome(make_outcome(issues=(issue(Severity.ERROR, "commit.stale_file", "Not committed: x"),)))
    assert theme.ERROR_TINT in refused._outcome_frame.styleSheet()

    switching = CommitProbe(state="offer_switch", head="abc1234def", reason="Custom is on a detached HEAD at abc1234.")
    other, _ = new_panel(qtbot, tmp_path, switching)
    other.show_switch_failed("git refused to switch Custom to main\nerror: x")
    assert theme.ERROR_TINT in other._outcome_frame.styleSheet()


def test_panel_outcome_tint_warning(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()

    panel.show_outcome(make_outcome(issues=(
        issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom"),
        issue(Severity.WARNING, "commit.parent_skipped", "The parent repo was left alone"),
    )))

    assert theme.AMBER_TINT in panel._outcome_frame.styleSheet()
    assert theme.ERROR_TINT not in panel._outcome_frame.styleSheet()


def test_panel_outcome_frame_hidden_when_empty(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    assert panel._outcome_frame.isHidden()
    panel.set_committing()
    panel.show_outcome(partial_outcome())
    assert not panel._outcome_frame.isHidden()

    panel.show_plan(make_cplan(tmp_path))

    assert panel._outcome_frame.isHidden()
    assert panel._outcome_frame.styleSheet() == ""


def test_panel_failed_label_custom_only(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    panel.set_committing()

    panel.show_outcome(partial_outcome())

    assert panel.state() == "failed"
    assert not panel.commit_button.isEnabled()
    assert panel.commit_button.text() == "Committed in Custom only"
    lines = panel.outcome_lines()
    assert lines[0].startswith("✓ ") and lines[1].startswith("✖ ")


def test_panel_sizes_on_theme_scale(qtbot, tmp_path):
    panel = CommitPanel()
    qtbot.addWidget(panel)

    assert panel._progress.width() == theme.SP_XL * 8
    assert panel._progress.height() == theme.SP_MD
    panel.show_plan(make_cplan(tmp_path, 0))
    files = panel._files_list
    assert files.height() == files.fontMetrics().height() + theme.SP_SM + 2 * files.frameWidth()


# -- Phase 11 (GIT-06, D-06, D-07): the gated state and its two ways forward ----------------------


def failure(library: str, part: str, text: str = "no datasheet", rule: str = "datasheet") -> AtomicFailure:
    return AtomicFailure(library, f"Custom/Symbols/{library}.kicad_sym", part, rule, text)


def gated_probe(*failures: AtomicFailure, **fields) -> CommitProbe:
    count = len({(f.library, f.part) for f in failures})
    gate = GateResult(blocking=tuple(failures))
    values = dict(state="gated", reason=f"{count} parts break the atomic rule.", gate=gate)
    values.update(fields)
    return make_probe(**values)


def gated_panel(qtbot, tmp_path, *failures: AtomicFailure, **fields):
    panel, _ = new_panel(qtbot, tmp_path, gated_probe(*failures, parent_dir=tmp_path, **fields))
    assert panel.state() == "gated"
    return panel


def test_panel_gated_lists_failures_and_disables_commit(qtbot, tmp_path):
    panel = gated_panel(
        qtbot, tmp_path,
        failure("Atomic_Sensor_Motion", "LIS3MDL"),
        failure("Atomic_IC_LDO_TI", "TPS7A02", "no footprint"),
    )

    assert panel._strip.text() == "⚠ Commit refused: 2 parts break the atomic rule."
    assert theme.AMBER_TINT in panel._strip.styleSheet()
    assert panel._gate_lines.text().splitlines() == [
        "Atomic_Sensor_Motion / LIS3MDL: no datasheet",
        "Atomic_IC_LDO_TI / TPS7A02: no footprint",
    ]
    assert not panel._gate_lines.isHidden()
    assert theme.AMBER in panel._gate_lines.styleSheet()
    assert not panel.commit_button.isEnabled()
    assert not panel._message.isReadOnly()
    assert panel._parent_check.isEnabled()
    panel.commit_button.click()  # a click on a disabled button does nothing; the state guard also holds
    panel._on_commit_clicked()


def test_panel_gated_commit_never_emits(qtbot, tmp_path):
    panel = gated_panel(qtbot, tmp_path, failure("Atomic_A", "P1"))
    requests = []
    panel.commit_requested.connect(lambda text, bump: requests.append((text, bump)))

    panel.commit_button.click()
    panel._on_commit_clicked()
    panel._message.setPlainText("Another message")

    assert requests == []
    assert not panel.commit_button.isEnabled()
    assert panel.message() == "Another message"


def test_panel_gated_lines_capped(qtbot, tmp_path):
    panel = gated_panel(qtbot, tmp_path, *(failure("Atomic_A", f"P{index}") for index in range(13)))

    lines = panel._gate_lines.text().splitlines()
    assert lines[:10] == [f"Atomic_A / P{index}: no datasheet" for index in range(10)]
    assert lines[10] == "…and 3 more"
    assert len(lines) == 11


def test_panel_gated_buttons_secondary_and_signals(qtbot, tmp_path):
    first = failure("Atomic_A", "P1")
    panel = gated_panel(qtbot, tmp_path, first, failure("Atomic_B", "P2"))
    opened, again = [], []
    panel.open_check_requested.connect(lambda rel, part: opened.append((rel, part)))
    panel.check_again_requested.connect(lambda: again.append(True))

    for button in (panel._open_check_button, panel._check_again_button):
        assert not button.isHidden()
        assert button.styleSheet() == ""
        assert not button.autoDefault() and not button.isDefault()
    assert panel._open_check_button.text() == "Open Check Atomic Parts…"
    assert panel._check_again_button.text() == "Check again"
    panel._open_check_button.click()
    panel._check_again_button.click()
    assert opened == [(first.rel_path, "P1")]
    assert again == [True]

    # a stale-only gated probe (no refused gate) offers Check again but not Open Check Atomic Parts
    panel.apply_probe(make_probe(state="gated", reason="A file changed after the install.", parent_dir=tmp_path))
    assert not panel._check_again_button.isHidden()
    assert panel._open_check_button.isHidden()
    assert panel._gate_lines.isHidden()

    panel.apply_probe(make_probe(state="gated", reason="x", gate=GateResult(), parent_dir=tmp_path))
    assert panel._open_check_button.isHidden() and panel._gate_lines.isHidden()

    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel.state() == "ready"
    assert panel._open_check_button.isHidden() and panel._check_again_button.isHidden()
    assert panel._gate_lines.isHidden()


def test_panel_gated_unchecked_libraries_hide_open_check(qtbot, tmp_path):
    gate = GateResult(problems=("Atomic_A: the library could not be checked (unreadable)",))
    panel, _ = new_panel(qtbot, tmp_path, make_probe(
        state="gated", reason="1 library could not be checked.", gate=gate, parent_dir=tmp_path
    ))

    assert panel._gate_lines.text() == "Atomic_A: the library could not be checked (unreadable)"
    assert panel._open_check_button.isHidden()
    assert not panel._check_again_button.isHidden()


def test_panel_check_again_clears_pending_refusal(qtbot, tmp_path):
    panel = refused_panel(qtbot, tmp_path)
    again = []
    panel.check_again_requested.connect(lambda: again.append(True))
    panel.apply_probe(gated_probe(failure("Atomic_A", "P1"), parent_dir=tmp_path))
    assert panel.outcome_lines() == [f"✖ {_REFUSAL}"]

    panel._check_again_button.click()

    assert again == [True]
    assert panel._pending_refusal == ()
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert panel.outcome_lines() == []


def test_panel_check_again_only_in_gated_state(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path)
    again = []
    panel.check_again_requested.connect(lambda: again.append(True))

    panel._on_check_again_clicked()
    panel._on_open_check_clicked()

    assert again == []


def test_panel_gated_text_is_plain(qtbot, tmp_path):
    panel = gated_panel(qtbot, tmp_path, failure("Atomic_A", "P<b>1</b>", "<b>bold</b> rule"))

    assert panel._gate_lines.text() == "Atomic_A / P<b>1</b>: <b>bold</b> rule"
    assert panel._gate_lines.textFormat() == Qt.TextFormat.PlainText
    assert all(label.textFormat() == Qt.TextFormat.PlainText for label in labels(panel))


# -- Phase 11 (D-02, D-08, D-10): the old-failure note and the changed / added file markers ----------


def test_panel_old_failures_note_keeps_commit(qtbot, tmp_path):
    gate = GateResult(old=(
        failure("Atomic_A", "P1"), failure("Atomic_A", "P2"), failure("Atomic_A", "P2", "no footprint", "footprint"),
        failure("Atomic_B", "P3"),
    ))
    panel, _ = ready_panel(qtbot, tmp_path, gate=gate, parent_dir=tmp_path)

    assert panel.state() == "ready"
    assert panel._old_label.text().splitlines() == [
        "Atomic_A also holds 2 parts that already failed before this import",
        "Atomic_B also holds 1 part that already failed before this import",
    ]
    assert not panel._old_label.isHidden()
    assert theme.AMBER in panel._old_label.styleSheet()
    assert panel.commit_button.isEnabled()
    assert panel._gate_lines.isHidden()

    panel.apply_probe(make_probe(parent_dir=tmp_path))  # no gate at all
    assert panel._old_label.isHidden()
    panel.apply_probe(make_probe(gate=GateResult(), parent_dir=tmp_path))
    assert panel._old_label.isHidden()
    panel.apply_probe(make_probe(gate=gate, parent_dir=tmp_path))
    panel.begin_reprobe()
    assert panel._old_label.isHidden()


def test_panel_old_failures_shown_beside_gated_lines(qtbot, tmp_path):
    old = (failure("Atomic_B", "P3"),)
    panel = gated_panel(qtbot, tmp_path, failure("Atomic_A", "P1"), gate=GateResult(blocking=(failure("Atomic_A", "P1"),), old=old))

    assert not panel._old_label.isHidden()
    assert not panel._gate_lines.isHidden()
    assert not panel.commit_button.isEnabled()


def test_panel_changed_and_added_markers(qtbot, tmp_path):
    base = make_cplan(tmp_path).files
    files = (replace(base[0], note="changed"), replace(base[1], note="added"), base[2])
    probe = make_probe(stale=(base[2].display,), parent_dir=tmp_path)
    panel, _ = new_panel(qtbot, tmp_path, probe, files=files)
    activated = []
    panel.file_activated.connect(activated.append)

    assert rows(panel) == [
        f"⚠ {base[0].display} (changed since install)",
        f"+ {base[1].display} (added by a fix)",
        f"⚠ {base[2].display} (changed since install)",
    ]
    for index in range(3):
        item = panel._files_list.item(index)
        assert item.foreground().color() == QColor(theme.AMBER)
        assert "Double-click" in item.toolTip()
    assert "changed after the install" in panel._files_list.item(0).toolTip()
    assert "committed because a committed part links it" in panel._files_list.item(1).toolTip()
    assert not panel._changed_hint.isHidden()
    assert theme.AMBER in panel._changed_hint.styleSheet()
    for index, base_file in enumerate(base):
        panel._files_list.itemActivated.emit(panel._files_list.item(index))
    assert activated == [base[0].rel, base[1].rel, base[2].rel]


def test_panel_plain_row_has_no_marker_and_does_not_activate(qtbot, tmp_path):
    base = make_cplan(tmp_path).files
    panel, _ = new_panel(qtbot, tmp_path, make_probe(parent_dir=tmp_path), files=(replace(base[0], note="changed"), *base[1:]))
    activated = []
    panel.file_activated.connect(activated.append)

    assert rows(panel)[1] == base[1].display
    assert panel._files_list.item(1).data(Qt.ItemDataRole.ForegroundRole) is None
    panel._files_list.itemActivated.emit(panel._files_list.item(1))
    assert activated == []

    # a later probe without changes resets the marks
    panel.show_plan(make_cplan(tmp_path))
    panel.apply_probe(make_probe(parent_dir=tmp_path))
    assert rows(panel) == [f.display for f in base]
    assert panel._changed_hint.isHidden()


def test_panel_changed_beats_dirty_before(qtbot, tmp_path):
    base = make_cplan(tmp_path).files
    probe = make_probe(dirty_before=frozenset({base[0].rel}), stale=(base[0].display,), parent_dir=tmp_path)
    panel, _ = new_panel(qtbot, tmp_path, probe)

    assert rows(panel)[0] == f"⚠ {base[0].display} (changed since install)"


# -- Phase 11 (D-14): nothing to commit and the parent-only bump -----------------------------------


_NOTHING = "⚠ Nothing to commit: Custom already holds these files"


def test_panel_nothing_to_commit(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="abc1234def5678", parent_dir=tmp_path)

    assert panel._strip.text() == _NOTHING
    assert not panel._strip.isHidden()
    assert theme.AMBER_TINT in panel._strip.styleSheet()
    assert not panel.commit_button.isEnabled()
    assert panel.commit_button.text() == "Commit"

    panel._parent_check.setChecked(False)  # still nothing to do for the parent: the gitlink is current
    assert not panel.commit_button.isEnabled() and panel.commit_button.text() == "Commit"


def test_panel_nothing_to_commit_strip_gone_when_files_differ(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="abc1234def5678", parent_dir=tmp_path)

    panel.apply_probe(make_probe(parent_dir=tmp_path))

    assert panel._strip.isHidden()
    assert panel.commit_button.isEnabled() and panel.commit_button.text() == "Commit"


def test_panel_parent_only_bump_label_and_preview(qtbot, tmp_path):
    earlier = (("abc1234", "Earlier"), ("def5678", "Tip"))
    panel, cplan = ready_panel(
        qtbot, tmp_path, all_identical=True, earlier=earlier, gitlink_old="1111111aaaa", parent_dir=tmp_path
    )
    requests = []
    panel.commit_requested.connect(lambda text, bump: requests.append((text, bump)))

    assert panel._strip.text() == _NOTHING
    assert panel.commit_button.isEnabled()
    assert panel.commit_button.text() == "Commit parent ref"
    expected = parent_only_preview(
        subject_of(panel.message()), "Custom", "1111111aaaa", "abc1234def5678", earlier, listed=True
    )
    assert panel._parent_preview.toPlainText() == expected
    assert "<new commit>" not in expected
    assert not panel._parent_preview.isHidden()

    panel._parent_check.setChecked(False)
    assert not panel.commit_button.isEnabled()
    assert panel.commit_button.text() == "Commit"

    panel._parent_check.setChecked(True)
    assert panel.commit_button.isEnabled() and panel.commit_button.text() == "Commit parent ref"
    panel.commit_button.click()
    assert requests == [(panel.message(), True)]


def test_panel_parent_only_needs_message_and_parent(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="1111111aaaa", parent_dir=tmp_path)

    panel._message.setPlainText("   ")
    assert not panel.commit_button.isEnabled()

    panel._message.setPlainText("Bump")
    assert panel.commit_button.isEnabled()
    panel.apply_probe(make_probe(
        all_identical=True, gitlink_old="1111111aaaa", parent_ok=False, parent_reason="detached",
        parent_branch=None, parent_dir=tmp_path,
    ))
    assert not panel.commit_button.isEnabled() and panel.commit_button.text() == "Commit"


def test_panel_parent_only_label_resets_after_state_change(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="1111111aaaa", parent_dir=tmp_path)
    assert panel.commit_button.text() == "Commit parent ref"

    panel.set_committing()
    assert panel.commit_button.text() == "Committing..."
    panel.show_outcome(make_outcome(parent_only=True, parent_commit="1234567", issues=(
        issue(Severity.SUCCESS, "commit.parent_done", "Committed 1234567 on main in the parent repo"),
    )))
    assert panel.commit_button.text() == "Committed"


def test_panel_parent_only_outcome_done(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="1111111aaaa", parent_dir=tmp_path)
    panel.set_committing()

    panel.show_outcome(make_outcome(parent_only=True, parent_commit="1234567", issues=(
        issue(Severity.SUCCESS, "commit.parent_done", "Committed 1234567 on main in the parent repo"),
        issue(Severity.INFO, "commit.not_pushed", "Not pushed"),
    )))

    assert panel.state() == "done"
    assert panel.committed() is True
    assert theme.SUCCESS_TINT in panel._outcome_frame.styleSheet()
    assert not panel.commit_button.isEnabled()


def test_panel_parent_only_failure_reprobes(qtbot, tmp_path):
    panel, _ = ready_panel(qtbot, tmp_path, all_identical=True, gitlink_old="1111111aaaa", parent_dir=tmp_path)
    panel.set_committing()
    failed = issue(Severity.ERROR, "commit.parent_failed", "The parent commit failed (git exit 1)")

    panel.show_outcome(make_outcome(parent_only=True, manual_command="git -C x commit", issues=(failed,)))

    assert panel.state() == "probing"
    assert panel.committed() is False
    assert panel._pending_refusal == (failed,)
    assert not panel.commit_button.isEnabled()
    assert not panel._manual_label.isHidden()
