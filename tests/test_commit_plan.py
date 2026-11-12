"""The commit plan and the commit messages (Phase 6): pure, no git involved.

Values are built directly from InstallPlan, InstallResult and FileOp, so every rule of
build_commit_plan, changed_since_install, pre_install_bytes and the message builders is proven
without running an install; one test runs a real Ultra Librarian install into a Custom copy.
"""

import hashlib
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from installfixtures import UL_DESCRIPTION
from zipfixtures import footprint_library_for

from kicad_lib_manager.importer import commit_plan
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import PackageFile
from kicad_lib_manager.importer.plan import (
    Conflict,
    FileOp,
    InstallOptions,
    InstallPlan,
    InstallResult,
    Resolution,
    ToolContext,
)
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.models import Severity

LIB = "Atomic_Battery_Management"
FP_LIB = footprint_library_for(LIB)
TODAY = date(2026, 10, 22)
UL_REL = [
    "Custom/3DModels/CSD85301Q2.stp",
    f"Custom/Footprints/{FP_LIB}.pretty/DQK0006B.kicad_mod",
    f"Custom/Symbols/{LIB}.kicad_sym",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def package_file(path: Path, data: bytes) -> PackageFile:
    return PackageFile(member=path.name, path=path, kind="model", size=len(data), sha256=sha(data), staged=False)


def make_plan(layout: RepoLayout, ops, *, symbol="P1", footprint="FP1", model="P1.step", library=LIB,
              new_library=False, conflicts=()) -> InstallPlan:
    return InstallPlan(
        vendor="ultra_librarian",
        source=Path("ul_P1.zip"),
        layout=layout,
        tools=ToolContext(),
        library=library,
        new_symbol_lib=new_library,
        new_footprint_lib=False,
        symbol_names=(symbol,) if symbol else (),
        footprint_names=(footprint,) if footprint else (),
        linked_footprint=footprint,
        footprint_library=FP_LIB if footprint else None,
        model_file=model,
        source_version=None,
        target_version=None,
        normalised=False,
        ops=tuple(ops),
        conflicts=tuple(conflicts),
        renames=(),
        issues=(),
    )


def make_result(touched, *, library=LIB, new_library=False, backup_dir=None, source=Path("ul_P1.zip")) -> InstallResult:
    return InstallResult(
        ok=True, library=library, new_library=new_library, touched=tuple(touched), issues=(),
        backup_dir=backup_dir, vendor="", source=source,
    )


class Install:
    """A small written install: a symbol library, a footprint folder with one footprint and a model."""

    def __init__(self, tmp_path: Path) -> None:
        self.layout = RepoLayout.for_repo(tmp_path / "repo")
        self.pretty = self.layout.footprints_dir / f"{FP_LIB}.pretty"
        self.old_symbols = b"(kicad_symbol_lib old)"
        self.symbols_data = b"(kicad_symbol_lib new)"
        self.footprint_data = b"(footprint FP1)"
        self.model_data = b"STEP model bytes"
        self.symbols = write(self.layout.symbols_dir / f"{LIB}.kicad_sym", self.symbols_data)
        self.footprint = write(self.pretty / "FP1.kicad_mod", self.footprint_data)
        self.model = write(self.layout.models_dir / "P1.step", self.model_data)
        self.ops = (
            FileOp("mkdir", self.pretty),
            FileOp("model", self.model, source=package_file(self.model, self.model_data)),
            FileOp("footprint", self.footprint, data=self.footprint_data),
            FileOp("symbol_lib", self.symbols, data=self.symbols_data, base_sha256=sha(self.old_symbols)),
        )
        # reverse of the sorted order, with the folder among the files
        self.touched = (self.symbols, self.pretty, self.footprint, self.model)

    def plan(self, **kwargs) -> InstallPlan:
        return make_plan(self.layout, self.ops, **kwargs)

    def result(self, **kwargs) -> InstallResult:
        return make_result(self.touched, **kwargs)

    def commit_plan(self, *, vendor_label="Ultra Librarian", plan_kwargs=None, **result_kwargs):
        return commit_plan.build_commit_plan(
            self.result(**result_kwargs), self.plan(**(plan_kwargs or {})), vendor_label=vendor_label, today=TODAY
        )


@pytest.fixture
def install(tmp_path) -> Install:
    return Install(tmp_path)


# ── The files of the commit ─────────────────────────────────────────────────────────────────


def test_build_files_only_sorted(install):
    cplan = install.commit_plan()

    assert [f.display for f in cplan.files] == [
        "Custom/3DModels/P1.step",
        f"Custom/Footprints/{FP_LIB}.pretty/FP1.kicad_mod",
        f"Custom/Symbols/{LIB}.kicad_sym",
    ]
    assert not any(f.path.is_dir() for f in cplan.files)
    assert cplan.issues == ()


def test_build_lists_each_file_once(install):
    result = make_result((*install.touched, install.model, install.symbols))

    cplan = commit_plan.build_commit_plan(result, install.plan(), vendor_label="Ultra Librarian", today=TODAY)

    assert [f.display for f in cplan.files].count("Custom/3DModels/P1.step") == 1
    assert len(cplan.files) == 3


def test_build_rel_and_display(install):
    cplan = install.commit_plan()

    assert cplan.custom_rel == "Custom"
    symbols = next(f for f in cplan.files if f.kind == "symbol_lib")
    assert symbols.rel == f"Symbols/{LIB}.kicad_sym"
    assert symbols.display == f"Custom/Symbols/{LIB}.kicad_sym"


def test_build_expected_hashes(install):
    cplan = install.commit_plan()
    by_kind = {f.kind: f for f in cplan.files}

    assert by_kind["footprint"].expected_sha256 == sha(install.footprint_data)
    assert by_kind["model"].expected_sha256 == sha(install.model_data)
    assert by_kind["symbol_lib"].expected_sha256 == sha(install.symbols_data)
    assert by_kind["symbol_lib"].base_sha256 == sha(install.old_symbols)
    assert by_kind["footprint"].base_sha256 is None


def test_build_refuses_outside_custom(install):
    outside = write(install.layout.repo_root / "Other" / "stray.txt")
    ops = (*install.ops, FileOp("footprint", outside, data=b"x"))
    result = make_result((*install.touched, outside))

    cplan = commit_plan.build_commit_plan(result, make_plan(install.layout, ops), vendor_label="V", today=TODAY)

    assert [i.code for i in cplan.issues] == ["commit.outside_custom"]
    assert cplan.issues[0].severity is Severity.ERROR
    assert "Other/stray.txt" in cplan.issues[0].text
    assert all("Other" not in f.display for f in cplan.files)


def test_build_refuses_unknown_touched(install):
    stray = write(install.layout.custom_dir / "Symbols" / "stray.kicad_sym")
    result = make_result((*install.touched, stray))

    cplan = commit_plan.build_commit_plan(result, install.plan(), vendor_label="V", today=TODAY)

    assert [i.code for i in cplan.issues] == ["commit.unknown_file"]
    assert cplan.issues[0].severity is Severity.ERROR
    assert all(f.path != stray for f in cplan.files)


def test_build_uses_disk_spelling(tmp_path):
    probe = tmp_path / "CaseProbe"
    probe.mkdir()
    if not (tmp_path / "caseprobe").exists():
        pytest.skip("case-sensitive volume")
    layout = RepoLayout.for_repo(tmp_path / "repo")
    on_disk = write(layout.symbols_dir / "conn_a.kicad_sym", b"data")
    planned = layout.symbols_dir / "Conn_A.kicad_sym"
    ops = (FileOp("symbol_lib", planned, data=b"data"),)

    cplan = commit_plan.build_commit_plan(
        make_result((planned,)), make_plan(layout, ops), vendor_label="V", today=TODAY
    )

    assert [f.rel for f in cplan.files] == ["Symbols/conn_a.kicad_sym"]
    assert cplan.files[0].display == "Custom/Symbols/conn_a.kicad_sym"
    assert on_disk.exists()


def test_build_from_real_ul_plan(atomic_custom, ul_package, tmp_path):
    package, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=LIB, description=UL_DESCRIPTION), atomic_custom)
    result = apply_plan(plan, backup_root=tmp_path / "backups")
    assert result.ok

    cplan = commit_plan.build_commit_plan(result, plan, vendor_label="Ultra Librarian", today=TODAY)

    assert [f.display for f in cplan.files] == UL_REL
    assert cplan.issues == ()
    assert commit_plan.changed_since_install(cplan) == ()


# ── The stale check and the backup lookup ───────────────────────────────────────────────────


def test_changed_since_install(install):
    cplan = install.commit_plan()
    assert commit_plan.changed_since_install(cplan) == ()

    install.footprint.write_bytes(b"edited by hand")
    install.model.unlink()

    assert commit_plan.changed_since_install(cplan) == (
        "Custom/3DModels/P1.step",
        f"Custom/Footprints/{FP_LIB}.pretty/FP1.kicad_mod",
    )


def test_pre_install_bytes_picks_matching_backup(install, tmp_path):
    cplan = install.commit_plan()
    symbols = next(f for f in cplan.files if f.kind == "symbol_lib")
    backups = tmp_path / "backups"
    name = symbols.path.name
    write(backups / f"{name}_backup_1", b"some other file with this name")
    write(backups / f"{name}_backup_2", install.old_symbols)

    assert commit_plan.pre_install_bytes(symbols, backups) == install.old_symbols
    assert commit_plan.pre_install_bytes(symbols, None) is None
    assert commit_plan.pre_install_bytes(symbols, tmp_path / "no_backups") is None
    footprint = next(f for f in cplan.files if f.kind == "footprint")
    assert footprint.base_sha256 is None
    assert commit_plan.pre_install_bytes(footprint, backups) is None
    write(backups / f"{name}_backup_2", b"changed since")
    assert commit_plan.pre_install_bytes(symbols, backups) is None


# ── The note, the pre-image, re-baseline and added files (Phase 11: D-08, D-10) ─────────────


def test_commit_file_positional_construction_still_works(tmp_path):
    cfile = commit_plan.CommitFile("Symbols/A.kicad_sym", "Custom/Symbols/A.kicad_sym", tmp_path / "A", "symbol_lib", "abc", None)

    assert cfile.note == ""
    assert cfile.installed is None


def test_build_commit_plan_keeps_installed_bytes(install):
    cplan = install.commit_plan()
    by_kind = {f.kind: f for f in cplan.files}

    assert by_kind["footprint"].installed == install.footprint_data
    assert by_kind["symbol_lib"].installed == install.symbols_data
    assert by_kind["model"].installed is None


def test_rebaseline_takes_current_bytes(install):
    cplan = install.commit_plan()
    install.footprint.write_bytes(b"edited by hand")
    assert commit_plan.changed_since_install(cplan) != ()

    new_plan = commit_plan.rebaseline(cplan)

    by_kind = {f.kind: f for f in new_plan.files}
    assert by_kind["footprint"].expected_sha256 == sha(b"edited by hand")
    assert by_kind["footprint"].note == commit_plan.NOTE_CHANGED
    assert by_kind["footprint"].installed == install.footprint_data
    assert by_kind["symbol_lib"].note == "" and by_kind["model"].note == ""
    assert commit_plan.changed_since_install(new_plan) == ()
    # the input plan is unchanged
    assert {f.kind: f for f in cplan.files}["footprint"].expected_sha256 == sha(install.footprint_data)
    assert commit_plan.changed_since_install(cplan) != ()


def test_rebaseline_keeps_missing_file_stale(install):
    cplan = install.commit_plan()
    install.model.unlink()

    new_plan = commit_plan.rebaseline(cplan)

    model = next(f for f in new_plan.files if f.kind == "model")
    assert model.expected_sha256 == sha(install.model_data)
    assert model.note == ""
    assert commit_plan.changed_since_install(new_plan) == ("Custom/3DModels/P1.step",)


def test_rebaseline_keeps_added_note(install):
    cplan = install.commit_plan()
    footprint = next(f for f in cplan.files if f.kind == "footprint")
    marked = replace(cplan, files=tuple(replace(f, note=commit_plan.NOTE_ADDED) if f is footprint else f for f in cplan.files))
    install.footprint.write_bytes(b"changed again")

    new_plan = commit_plan.rebaseline(marked)

    assert next(f for f in new_plan.files if f.kind == "footprint").note == commit_plan.NOTE_ADDED


def test_with_added_files_marks_and_sorts(install):
    cplan = install.commit_plan()
    added = write(install.layout.models_dir / "NEW.step", b"new model")

    new_plan = commit_plan.with_added_files(cplan, [("3DModels/NEW.step", "model", None)])

    assert [f.display for f in new_plan.files] == [
        "Custom/3DModels/NEW.step",
        "Custom/3DModels/P1.step",
        f"Custom/Footprints/{FP_LIB}.pretty/FP1.kicad_mod",
        f"Custom/Symbols/{LIB}.kicad_sym",
    ]
    new = new_plan.files[0]
    assert (new.rel, new.kind, new.note, new.base_sha256, new.path) == ("3DModels/NEW.step", "model", "added", None, added)
    assert new.expected_sha256 == sha(b"new model")
    assert new_plan.issues == ()
    assert len(cplan.files) == 3


def test_with_added_files_does_not_add_a_planned_file_twice(install):
    cplan = install.commit_plan()

    new_plan = commit_plan.with_added_files(
        cplan, [("3dmodels/P1.STEP", "model", None), ("3DModels/P1.step", "model", None)]
    )

    assert new_plan.files == cplan.files


def test_with_added_files_refuses_a_path_outside_custom(install):
    cplan = install.commit_plan()
    write(install.layout.repo_root / "outside.txt", b"x")

    new_plan = commit_plan.with_added_files(cplan, [("../outside.txt", "model", None)])

    assert new_plan.files == cplan.files
    (issue,) = new_plan.issues
    assert issue.code == "commit.outside_custom" and issue.severity is Severity.ERROR
    assert issue.text == "Custom/../outside.txt is outside Custom; it is not committed"


def test_with_added_files_skips_a_file_that_cannot_be_read(install):
    cplan = install.commit_plan()

    new_plan = commit_plan.with_added_files(cplan, [("3DModels/MISSING.step", "model", None)])

    assert new_plan.files == cplan.files and new_plan.issues == ()


# ── Deleted files (Phase 13, MIG-04) ────────────────────────────────────────────────────────


def _deleted_file(install) -> commit_plan.CommitFile:
    missing = install.layout.custom_dir / "Symbols" / "Gone.kicad_sym"
    return commit_plan.CommitFile(
        "Symbols/Gone.kicad_sym", "Custom/Symbols/Gone.kicad_sym", missing, "symbol_lib", "", sha(b"old"), deleted=True,
    )


def test_deleted_file_is_fresh_while_absent(install):
    cplan = install.commit_plan()
    deleted = _deleted_file(install)
    with_deleted = replace(cplan, files=(*cplan.files, deleted))

    assert commit_plan.changed_since_install(with_deleted) == ()


def test_reappeared_deleted_file_is_stale(install):
    cplan = install.commit_plan()
    deleted = _deleted_file(install)
    with_deleted = replace(cplan, files=(*cplan.files, deleted))
    deleted.path.parent.mkdir(parents=True, exist_ok=True)
    deleted.path.write_bytes(b"reappeared")

    assert commit_plan.changed_since_install(with_deleted) == ("Custom/Symbols/Gone.kicad_sym",)

    new_plan = commit_plan.rebaseline(with_deleted)
    assert next(f for f in new_plan.files if f.rel == "Symbols/Gone.kicad_sym") == deleted
    assert commit_plan.changed_since_install(new_plan) == ("Custom/Symbols/Gone.kicad_sym",)


# ── The default message (D-18) ──────────────────────────────────────────────────────────────


def test_default_message_layout(install):
    message = commit_plan.default_message(install.commit_plan())

    assert message == (
        f"Add P1 to {LIB}\n"
        "\n"
        "Symbol: P1\n"
        f"Footprint: {FP_LIB}:FP1\n"
        "3D model: P1.step\n"
        "\n"
        "Import-Vendor: Ultra Librarian\n"
        "Import-Package: ul_P1.zip\n"
        "Import-Date: 2026-10-22"
    )


def test_plan_message_overrides_default(install):
    cplan = install.commit_plan()

    assert commit_plan.default_message(replace(cplan, message=None)) == commit_plan.default_message(cplan)
    assert commit_plan.default_message(replace(cplan, message="X\n\nY")) == "X\n\nY"


def test_default_message_date_is_the_local_date(install):
    cplan = commit_plan.build_commit_plan(install.result(), install.plan(), vendor_label="V")

    assert cplan.date == date.today().isoformat()


def test_default_message_new_library_verb(install):
    cplan = install.commit_plan(plan_kwargs={"new_library": True}, new_library=True)

    assert commit_plan.default_message(cplan).splitlines()[0] == f"Add P1 to new library {LIB}"


def test_default_message_overwrite_verb(install):
    conflict = Conflict("symbol:P1", "symbol", "P1", "existing", resolution=Resolution("overwrite"))
    cplan = install.commit_plan(plan_kwargs={"conflicts": (conflict,)})

    assert commit_plan.default_message(cplan).splitlines()[0] == f"Update P1 in {LIB}"


def test_default_message_omits_missing_lines(install):
    cplan = install.commit_plan(vendor_label="", plan_kwargs={"footprint": None, "model": None}, source=None)

    lines = commit_plan.default_message(cplan).splitlines()

    assert not any(line.startswith(("Footprint:", "3D model:", "Import-Package:")) for line in lines)
    assert "Symbol: P1" in lines
    assert "Import-Vendor: Unknown vendor" in lines
    assert "Import-Date: 2026-10-22" in lines


def test_default_message_blank_vendor_label_says_unknown(install):
    cplan = replace(install.commit_plan(), vendor="  \t ")

    assert "Import-Vendor: Unknown vendor" in commit_plan.default_message(cplan).splitlines()


def test_default_message_sanitises_controls(install):
    cplan = install.commit_plan(source=Path("ev\r\nil\tImport-Vendor: X.zip"))

    message = commit_plan.default_message(cplan)

    assert [line for line in message.splitlines() if line.startswith("Import-Vendor:")] == ["Import-Vendor: Ultra Librarian"]
    assert "Import-Package: ev il Import-Vendor: X.zip" in message.splitlines()
    assert not any(ord(char) < 32 for char in message.replace("\n", ""))


def test_default_message_cannot_be_split_by_unicode_line_breaks(install):
    cplan = replace(install.commit_plan(), symbol="a\x85b\N{LINE SEPARATOR}c\N{PARAGRAPH SEPARATOR}d\x1b[31m")

    message = commit_plan.default_message(cplan)

    assert message.splitlines()[0] == f"Add a b c d [31m to {LIB}"
    assert len(message.splitlines()) == len(message.split("\n"))


def test_default_message_skips_values_that_sanitise_to_nothing(install):
    cplan = replace(install.commit_plan(), package="\r\n\t", footprint=" \n ", model="\x00")

    lines = commit_plan.default_message(cplan).splitlines()

    assert not any(line.startswith(("Footprint:", "3D model:", "Import-Package:")) for line in lines)


def test_default_message_keeps_unicode(install):
    cplan = replace(install.commit_plan(), symbol="Pièce—1")

    lines = commit_plan.default_message(cplan).splitlines()

    assert lines[0] == f"Add Pièce—1 to {LIB}"
    assert "Symbol: Pièce—1" in lines


def test_default_message_has_no_local_paths(install):
    source = Path.home() / "Downloads" / "ul_P1.zip"
    message = commit_plan.default_message(install.commit_plan(source=source))

    assert "ul_P1.zip" in message
    for private in (str(Path.home()), Path.home().as_posix(), "Downloads", str(install.layout.repo_root)):
        assert private not in message


def test_default_message_package_folder_carries_the_folder_name(install):
    source = Path.home() / "Downloads" / "LIB_P1_folder"

    message = commit_plan.default_message(install.commit_plan(source=source))

    assert "Import-Package: LIB_P1_folder" in message.splitlines()
    assert "Downloads" not in message


# ── The parent message (D-18, D-19) ─────────────────────────────────────────────────────────


def test_parent_message_lists_commits():
    message = commit_plan.parent_message(
        "Add P1 to L", "Custom", "a" * 40, "bbbbbbb", [("1111111", "First"), ("2222222", "Add P1 to L")]
    )

    assert message == "Update Custom: Add P1 to L\n\nCustom aaaaaaa..bbbbbbb\n- 1111111 First\n- 2222222 Add P1 to L"


def test_parent_message_shows_the_new_short_verbatim():
    message = commit_plan.parent_message("S", "Custom", "a" * 40, "bbbbbbbb", [("bbbbbbbb", "S")])

    assert message.splitlines()[2] == "Custom aaaaaaa..bbbbbbbb"


def test_parent_message_without_old_lists_the_commits_and_never_the_unlisted_line():
    for listed in (True, False):
        message = commit_plan.parent_message("S", "Custom", None, "bbbbbbb", [("bbbbbbb", "S")], listed=listed)

        assert message.splitlines() == ["Update Custom: S", "", "Custom bbbbbbb", "- bbbbbbb S"]
        assert "could not be listed" not in message
        assert "Custom .." not in message


def test_parent_message_with_old_and_unlisted():
    unlisted = commit_plan.parent_message("S", "Custom", "a" * 40, "bbbbbbb", [], listed=False)

    assert "Custom aaaaaaa..bbbbbbb" in unlisted.splitlines()
    assert "(the Custom commits since aaaaaaa could not be listed)" in unlisted.splitlines()
    assert not any(line.startswith("- ") for line in unlisted.splitlines())


def test_parent_message_sanitises_the_subject_and_commit_lines():
    message = commit_plan.parent_message("S\nTrailer: x", "Custom", "a" * 40, "bbbbbbb", [("1111111", "A\r\nB")])

    assert message.splitlines()[0] == "Update Custom: S Trailer: x"
    assert "- 1111111 A B" in message.splitlines()


def test_parent_preview_placeholder():
    preview = commit_plan.parent_preview("S", "Custom", "a" * 40, [("1111111", "First")])

    lines = preview.splitlines()
    assert "Custom aaaaaaa..<new commit>" in lines
    assert "- 1111111 First" in lines
    assert "- <new commit> S" in lines


def test_parent_preview_without_old_lists_the_new_commit_line():
    preview = commit_plan.parent_preview("S", "Custom", None, (), listed=True)

    assert preview.splitlines() == ["Update Custom: S", "", "Custom <new commit>", "- <new commit> S"]


def test_parent_only_preview_uses_the_last_pair_as_range_end_and_keeps_subjects():
    earlier = [("1111111", "First"), ("2222222", "Second")]

    preview = commit_plan.parent_only_preview("Bump", "Custom", "a" * 40, "c" * 40, earlier)

    assert preview.splitlines() == [
        "Update Custom: Bump", "", "Custom aaaaaaa..2222222", "- 1111111 First", "- 2222222 Second",
    ]


def test_parent_only_preview_falls_back_to_head_without_pairs():
    no_old = commit_plan.parent_only_preview("Bump", "Custom", None, "c" * 40, ())
    unlisted = commit_plan.parent_only_preview("Bump", "Custom", "a" * 40, "c" * 40, (), listed=False)

    assert no_old.splitlines()[2] == "Custom ccccccc"
    assert unlisted.splitlines()[2] == "Custom aaaaaaa..ccccccc"
    assert "(the Custom commits since aaaaaaa could not be listed)" in unlisted.splitlines()


def test_subject_of():
    assert commit_plan.subject_of("\n\n  Add X  \nbody") == "Add X"
    assert commit_plan.subject_of("   ") == ""
