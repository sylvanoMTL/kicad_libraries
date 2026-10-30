"""The commit gate end to end (Phase 11, GIT-06): real git, the probe, the commit panel and the click.

Every repo is a throwaway superproject under tmp_path; the live Custom/ is never read or written. The
probes run with no KiCad folder unless a test passes a stand-in one, so nothing depends on the workstation.
"""

import subprocess
from pathlib import Path

from customfixtures import atomic_lib
from gitfixtures import GIT, GitRepos, commit_file, import_files, make_superproject, populate_custom, requires_git
from installfixtures import vendor_footprint
from zipfixtures import STEP_BYTES

from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_step
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR
from kicad_lib_manager.models import Severity
from kicad_lib_manager.widgets.commit_panel import CommitPanel

pytestmark = requires_git

SHARED = "Atomic_Footprints"
SHARED_MODEL = f"{MODEL_DIR_VAR}/GENERIC-2PIN.step"
FOOTPRINT = "Footprints/Atomic_Footprints.pretty/GENERIC-2PIN.kicad_mod"
BROKEN_REL = "Symbols/Atomic_Broken.kicad_sym"
LINKED = "Atomic_Linked"
LINKED_REL = f"Symbols/{LINKED}.kicad_sym"
MESSAGE = "Update a shared footprint"


def _populate(custom: Path) -> None:
    """The scratch Custom/ with a shared footprint library and one model, and no part linking them."""
    populate_custom(custom)
    (custom / "3DModels" / "GENERIC-2PIN.step").write_bytes(STEP_BYTES)
    (custom / "Footprints" / "Atomic_Footprints.pretty" / "GENERIC-2PIN.kicad_mod").write_bytes(
        vendor_footprint("GENERIC-2PIN", models=(SHARED_MODEL,))
    )


def _repos(tmp_path: Path) -> GitRepos:
    return make_superproject(tmp_path / "git", populate=_populate)


def _overwrite_footprint(repos: GitRepos):
    """Stand in for an install that rewrites the shared footprint with three pads and the same model line."""
    data = vendor_footprint("GENERIC-2PIN", models=(SHARED_MODEL,), pads=("1", "2", "3"))
    return import_files(repos, {FOOTPRINT: data}, library=SHARED, symbol="GENERIC-2PIN")


def _recording_ctx():
    """A context whose runner records every argv and then runs git for real."""
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.run(argv, **kwargs)

    return GitContext(Path(GIT), runner), calls


def _head(repos: GitRepos, repo: Path) -> str:
    return repos.git(repo, "rev-parse", "HEAD").strip()


def _show(qtbot, plan, probe) -> CommitPanel:
    panel = CommitPanel()
    qtbot.addWidget(panel)
    panel.show_plan(plan)
    panel.apply_probe(probe)
    return panel


def test_unreadable_linked_library_refuses_probe_panel_and_click(qtbot, tmp_path):
    repos = _repos(tmp_path)
    commit_file(repos, repos.custom, BROKEN_REL, b"(kicad_symbol_lib (version", "Add a damaged library")
    plan = _overwrite_footprint(repos)
    custom_head, parent_head = _head(repos, repos.custom), _head(repos, repos.parent)

    probe = commit_step.probe_commit(plan, git=GitContext(Path(GIT)))

    assert probe.state == "gated"
    assert probe.reason == "1 library could not be checked."
    assert probe.gate is not None and len(probe.gate.problems) == 1
    line = probe.gate.problems[0]
    assert line.startswith("Atomic_Broken: the parts in this library could not be checked")

    panel = _show(qtbot, plan, probe)

    assert panel.state() == "gated"
    assert panel._strip.text() == "⚠ Commit refused: 1 library could not be checked."
    assert panel._gate_lines.text() == line
    assert not panel._check_again_button.isHidden()
    assert panel._open_check_button.isHidden()
    assert not panel.commit_button.isEnabled()

    ctx, calls = _recording_ctx()
    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.custom_commit is None
    (issue,) = outcome.issues
    assert issue.severity is Severity.ERROR and issue.code == "commit.atomic"
    assert issue.text.startswith("Not committed: 1 library could not be checked.")
    assert "Atomic_Broken" in issue.text
    assert not {"add", "reset", "commit"} & {argv[6] for argv in calls}
    assert _head(repos, repos.custom) == custom_head
    assert _head(repos, repos.parent) == parent_head
