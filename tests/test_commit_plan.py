"""The commit plan and the commit messages (Phase 6): pure, no git involved.

Values are built directly from InstallPlan, InstallResult and FileOp, so every rule of
build_commit_plan, changed_since_install, pre_install_bytes and the message builders is proven
without running an install; one test runs a real Ultra Librarian install into a Custom copy.
"""

import hashlib
from datetime import date
from pathlib import Path

import pytest

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

LIB = "IC_Battery_Charger_TI"
TODAY = date(2026, 10, 22)
UL_REL = [
    "Custom/3DModels/CSD85301Q2.stp",
    "Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
    "Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
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
        self.pretty = self.layout.footprints_dir / f"{LIB}.pretty"
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
        f"Custom/Footprints/{LIB}.pretty/FP1.kicad_mod",
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


def test_build_from_real_ul_plan(custom_copy, ul_package, tmp_path):
    package, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=LIB), custom_copy)
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
        f"Custom/Footprints/{LIB}.pretty/FP1.kicad_mod",
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
