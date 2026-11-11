"""check_custom and ensure_tag, the migration's pre-write gate (Phase 13, MIG-01, D-02).

Every repo here is a throwaway superproject built by gitfixtures.make_superproject under
tmp_path; the live Custom/ is never touched.
"""

from pathlib import Path

from gitfixtures import GIT, make_superproject, requires_git

from kicad_lib_manager.gitops import GitContext, tag_commit
from kicad_lib_manager.importer.migration.precheck import PRE_ATOMIC_TAG, check_custom, ensure_tag
from kicad_lib_manager.models import Severity

UNTRACKED_SYMBOL = "Symbols/Atomic_Transistor_FET_NEW.kicad_sym"
UNTRACKED_FOOTPRINT = "Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod"


@requires_git
def test_uncommitted_files_refuse_by_name(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / UNTRACKED_SYMBOL).write_bytes(b"(kicad_symbol_lib)\n")
    (repos.custom / UNTRACKED_FOOTPRINT).write_bytes(b'(footprint "DQK0006B")\n')
    ctx = GitContext(Path(GIT))

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "migration.uncommitted"
    expected_listing = "\n".join(sorted((UNTRACKED_SYMBOL, UNTRACKED_FOOTPRINT)))
    assert expected_listing in issue.text
    assert tag_commit(ctx, repos.custom, PRE_ATOMIC_TAG) is None


@requires_git
def test_clean_custom_is_tagged_at_head(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx = GitContext(Path(GIT))
    head = repos.git(repos.custom, "rev-parse", "HEAD").strip()

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is True
    assert result.tag_action == "create"
    assert result.head == head

    issues = ensure_tag(repos.custom, repos.parent, git=ctx)

    assert len(issues) == 1
    assert issues[0].severity is Severity.INFO
    assert issues[0].code == "migration.tagged"
    short = repos.git(repos.custom, "rev-parse", "--short", "HEAD").strip()
    assert short in issues[0].text

    tagged = repos.git(repos.custom, "rev-parse", f"{PRE_ATOMIC_TAG}^{{commit}}").strip()
    assert tagged == head
