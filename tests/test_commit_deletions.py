"""Fast real-git checks of a migration-shaped commit (MIG-04): deletions, a moved footprint and new

files committed in one Custom commit, judged by the unchanged Phase 11 atomic gate. One throwaway
superproject per test (gitfixtures.make_superproject); the slow tests/test_commit_gate.py and
tests/test_commit_step.py stay the wave gate proving the unchanged importer commit path still holds.
"""

import hashlib
from pathlib import Path

from customfixtures import atomic_lib, atomic_part
from gitfixtures import GIT, commit_file, make_superproject, requires_git
from installfixtures import vendor_footprint
from zipfixtures import STEP_BYTES

from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_plan, commit_step
from kicad_lib_manager.importer.commit_plan import CommitFile, CommitPlan

MODEL_DIR_VAR = "${CUSTOM_3DMODEL_DIR}"


def _ctx() -> GitContext:
    return GitContext(Path(GIT))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _plan(repos, files, **overrides) -> CommitPlan:
    fields = dict(
        repo_root=repos.parent,
        custom_dir=repos.custom,
        custom_rel="Custom",
        files=tuple(files),
        library="Atomic_Connector",
        new_library=False,
        symbol="PART1",
        footprint="Atomic_Footprints:F1",
        model="F1.step",
        vendor="Migration",
        package=None,
        date="2026-11-11",
        overwrite=False,
        backup_dir=None,
        issues=(),
        message=None,
    )
    fields.update(overrides)
    return CommitPlan(**fields)


@requires_git
def test_migration_shaped_commit_records_deletions_and_moves(tmp_path):
    repos = make_superproject(tmp_path / "git")
    custom = repos.custom

    old_symbol_data = b"(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor))\n"
    old_atomic_data = b"(kicad_symbol_lib (version 20251024) (generator kicad_symbol_editor))\n"
    footprint_data = vendor_footprint("F1", model=f"{MODEL_DIR_VAR}/F1.step")

    commit_file(repos, custom, "Symbols/IC_Old_TI.kicad_sym", old_symbol_data, "Seed IC_Old_TI")
    commit_file(repos, custom, "Symbols/Atomic_Oscillator.kicad_sym", old_atomic_data, "Seed Atomic_Oscillator")
    commit_file(repos, custom, "Footprints/IC_Old_TI.pretty/F1.kicad_mod", footprint_data, "Seed IC_Old_TI footprint")

    old_atomic_connector = (custom / "Symbols" / "Atomic_Connector.kicad_sym").read_bytes()

    (custom / "Symbols" / "IC_Old_TI.kicad_sym").unlink()
    (custom / "Symbols" / "Atomic_Oscillator.kicad_sym").unlink()
    (custom / "Footprints" / "IC_Old_TI.pretty" / "F1.kicad_mod").unlink()

    new_symbol_data = atomic_lib((atomic_part("PART1", replace={"Footprint": "Atomic_Footprints:F1"}),))
    new_symbol_path = custom / "Symbols" / "Atomic_Connector.kicad_sym"
    new_symbol_path.write_bytes(new_symbol_data)
    new_footprint_path = custom / "Footprints" / "Atomic_Footprints.pretty" / "F1.kicad_mod"
    new_footprint_path.write_bytes(footprint_data)
    new_model_path = custom / "3DModels" / "F1.step"
    new_model_path.write_bytes(STEP_BYTES)
    map_data = b"# Migration to Atomic libraries\n\nIC_Old_TI -> Atomic_Connector\n"
    map_path = custom / "MIGRATION-ATOMIC.md"
    map_path.write_bytes(map_data)

    files = (
        CommitFile(
            "Symbols/IC_Old_TI.kicad_sym", "Custom/Symbols/IC_Old_TI.kicad_sym",
            custom / "Symbols" / "IC_Old_TI.kicad_sym", "symbol_lib", "", _sha(old_symbol_data), deleted=True,
        ),
        CommitFile(
            "Symbols/Atomic_Oscillator.kicad_sym", "Custom/Symbols/Atomic_Oscillator.kicad_sym",
            custom / "Symbols" / "Atomic_Oscillator.kicad_sym", "symbol_lib", "", _sha(old_atomic_data), deleted=True,
        ),
        CommitFile(
            "Footprints/IC_Old_TI.pretty/F1.kicad_mod", "Custom/Footprints/IC_Old_TI.pretty/F1.kicad_mod",
            custom / "Footprints" / "IC_Old_TI.pretty" / "F1.kicad_mod", "footprint", "", _sha(footprint_data),
            deleted=True,
        ),
        CommitFile(
            "Symbols/Atomic_Connector.kicad_sym", "Custom/Symbols/Atomic_Connector.kicad_sym",
            new_symbol_path, "symbol_lib", _sha(new_symbol_data), _sha(old_atomic_connector),
        ),
        CommitFile(
            "Footprints/Atomic_Footprints.pretty/F1.kicad_mod", "Custom/Footprints/Atomic_Footprints.pretty/F1.kicad_mod",
            new_footprint_path, "footprint", _sha(footprint_data), None,
        ),
        CommitFile("3DModels/F1.step", "Custom/3DModels/F1.step", new_model_path, "model", _sha(STEP_BYTES), None),
        CommitFile("MIGRATION-ATOMIC.md", "Custom/MIGRATION-ATOMIC.md", map_path, "doc", _sha(map_data), None),
    )
    cplan = _plan(repos, files, message="Migrate Custom parts to Atomic_ libraries")

    probe = commit_step.probe_commit(cplan, git=_ctx())
    assert probe.state == "ready"
    assert probe.stale == ()
    assert probe.gate is not None and not probe.gate.refused

    message = commit_plan.default_message(cplan)
    assert message == "Migrate Custom parts to Atomic_ libraries"
    outcome = commit_step.run_commit(cplan, message, True, git=_ctx())

    assert outcome.custom_commit is not None
    assert outcome.parent_commit is not None
    assert any(i.code == "commit.custom_done" for i in outcome.issues)

    names = set(repos.git(custom, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    assert names == {
        "Symbols/IC_Old_TI.kicad_sym",
        "Symbols/Atomic_Oscillator.kicad_sym",
        "Footprints/IC_Old_TI.pretty/F1.kicad_mod",
        "Symbols/Atomic_Connector.kicad_sym",
        "Footprints/Atomic_Footprints.pretty/F1.kicad_mod",
        "3DModels/F1.step",
        "MIGRATION-ATOMIC.md",
    }
    subject = repos.git(custom, "log", "-1", "--format=%s").strip()
    assert subject == "Migrate Custom parts to Atomic_ libraries"

    parent_log = repos.git(repos.parent, "log", "-1", "--format=%s").strip()
    assert "Custom" in parent_log


@requires_git
def test_deleted_only_commit_is_committed(tmp_path):
    repos = make_superproject(tmp_path / "git")
    custom = repos.custom
    data = b"(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor))\n"
    commit_file(repos, custom, "Symbols/ToDelete.kicad_sym", data, "Seed ToDelete")
    path = custom / "Symbols" / "ToDelete.kicad_sym"
    path.unlink()

    cfile = CommitFile("Symbols/ToDelete.kicad_sym", "Custom/Symbols/ToDelete.kicad_sym", path, "symbol_lib", "", _sha(data), deleted=True)
    cplan = _plan(repos, (cfile,), message="Remove ToDelete")

    outcome = commit_step.run_commit(cplan, commit_plan.default_message(cplan), False, git=_ctx())

    assert outcome.custom_commit is not None
    assert not any(i.code == "commit.nothing_to_commit" for i in outcome.issues)
    names = set(repos.git(custom, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    assert names == {"Symbols/ToDelete.kicad_sym"}


@requires_git
def test_ignored_file_in_plan_is_refused(tmp_path):
    repos = make_superproject(tmp_path / "git")
    custom = repos.custom
    bak_path = custom / "Symbols" / "IC_X.bak"
    bak_path.write_bytes(b"backup")

    cfile = CommitFile("Symbols/IC_X.bak", "Custom/Symbols/IC_X.bak", bak_path, "doc", _sha(b"backup"), None)
    cplan = _plan(repos, (cfile,))

    outcome = commit_step.run_commit(cplan, commit_plan.default_message(cplan), False, git=_ctx())

    assert outcome.custom_commit is None
    assert any(i.code == "commit.ignored" for i in outcome.issues)


def test_deleted_views(tmp_path):
    custom = tmp_path / "Custom"
    custom.mkdir(parents=True)
    cfile = CommitFile(
        "Symbols/Gone.kicad_sym", "Custom/Symbols/Gone.kicad_sym", custom / "Symbols" / "Gone.kicad_sym",
        "symbol_lib", "", _sha(b"old"), deleted=True,
    )
    cplan = CommitPlan(
        repo_root=tmp_path, custom_dir=custom, custom_rel="Custom", files=(cfile,), library="L", new_library=False,
        symbol="S", footprint=None, model=None, vendor="V", package=None, date="2026-11-11", overwrite=False,
        backup_dir=None, issues=(),
    )

    pre = commit_step.pre_import_diff(cplan, cfile.rel)
    changed = commit_step.changed_diff(cplan, cfile.rel)

    assert pre.kind == "text" and pre.body == commit_step.DELETED_TEXT
    assert changed.kind == "text" and changed.body == commit_step.DELETED_TEXT
