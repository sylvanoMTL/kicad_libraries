"""Legacy KiCad 5 decision matrix on synthetic zips: D-10, D-11, D-12, D-18, A5, INTK-05.

Every package goes through ``open_package`` and ``detect_candidate``, so the matrix
is exercised the way the GUI will use it. A (module ...) footprint is a KiCad 6+
footprint (D-18) and never counts as a legacy file.
"""

from pathlib import Path

from zipfixtures import (
    LEGACY_DCM_BYTES,
    LEGACY_LIB_BYTES,
    LEGACY_MOD_BYTES,
    STEP_BYTES,
    footprint,
    make_zip,
    symbol_lib,
)

from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.models import Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
REDOWNLOAD = "re-download as KiCad v6+"

V6_SYMBOL = ("s.kicad_sym", symbol_lib(("S",)))
V6_FOOTPRINT = ("f.kicad_mod", footprint("F"))


def _detect(tmp_path, members, name="pkg.zip"):
    """Open a synthetic zip and return (candidate, issues); the staging folder is gone afterwards."""
    with open_package(make_zip(tmp_path / name, members), REPO_ROOT) as package:
        return detect_candidate(package)


def _codes(issues, code):
    return [i for i in issues if i.code == code]


def _only(issues, code, severity):
    found = _codes(issues, code)
    assert len(found) == 1, [(i.code, i.text) for i in issues]
    assert found[0].severity is severity
    return found[0]


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


def test_legacy_only_refused(tmp_path):
    members = [("x.lib", LEGACY_LIB_BYTES), ("x.dcm", LEGACY_DCM_BYTES), ("x.mod", LEGACY_MOD_BYTES)]
    for extra in ([], [("m.step", STEP_BYTES)]):
        candidate, issues = _detect(tmp_path, members + extra)
        assert candidate is None
        assert len(_errors(issues)) == 1
        issue = _only(issues, "intake.legacy_only", Severity.ERROR)
        assert REDOWNLOAD in issue.text
        for legacy_name in ("x.lib", "x.dcm", "x.mod"):
            assert legacy_name in issue.text


def test_legacy_case_insensitive(tmp_path):
    candidate, issues = _detect(
        tmp_path, [("x.LIB", LEGACY_LIB_BYTES), ("Y.Dcm", LEGACY_DCM_BYTES), ("z.MOD", LEGACY_MOD_BYTES)]
    )
    assert candidate is None
    issue = _only(issues, "intake.legacy_only", Severity.ERROR)
    assert all(n in issue.text for n in ("x.LIB", "Y.Dcm", "z.MOD"))


def test_legacy_mixed_uses_v6(tmp_path):
    members = [V6_SYMBOL, V6_FOOTPRINT, ("x.lib", LEGACY_LIB_BYTES), ("y.mod", LEGACY_MOD_BYTES)]
    candidate, issues = _detect(tmp_path, members)
    assert candidate is not None
    assert candidate.legacy_ignored == ("x.lib", "y.mod")
    note = _only(issues, "intake.legacy_ignored", Severity.INFO)
    assert "x.lib" in note.text and "y.mod" in note.text
    assert not _errors(issues)
    assert [s.name for s in candidate.symbols] == ["S"]
    assert [f.name for f in candidate.footprints] == ["F"]


def test_half_legacy_refused(tmp_path):
    candidate, issues = _detect(tmp_path, [V6_FOOTPRINT, ("x.lib", LEGACY_LIB_BYTES)], "a.zip")
    assert candidate is None
    assert REDOWNLOAD in _only(issues, "intake.half_legacy", Severity.ERROR).text
    assert len(_errors(issues)) == 1

    candidate, issues = _detect(tmp_path, [V6_SYMBOL, ("y.mod", LEGACY_MOD_BYTES)], "b.zip")
    assert candidate is None
    assert REDOWNLOAD in _only(issues, "intake.half_legacy", Severity.ERROR).text
    assert len(_errors(issues)) == 1

    candidate, issues = _detect(tmp_path, [V6_FOOTPRINT, ("x.dcm", LEGACY_DCM_BYTES)], "c.zip")
    assert candidate is None
    assert _codes(issues, "intake.half_legacy")


def test_module_syntax_is_not_legacy(tmp_path):
    module_fp = ("old.kicad_mod", footprint("OLD", head="module", version=None))
    candidate, issues = _detect(tmp_path, [V6_SYMBOL, module_fp], "pair.zip")
    assert candidate is not None
    _only(issues, "intake.legacy_footprint_syntax", Severity.WARNING)
    assert not _codes(issues, "intake.legacy_only")
    assert not _codes(issues, "intake.half_legacy")
    assert not _errors(issues)

    candidate, issues = _detect(tmp_path, [module_fp], "alone.zip")
    assert candidate is not None
    _only(issues, "intake.no_symbol", Severity.WARNING)
    assert not _codes(issues, "intake.legacy_only")
    assert not _errors(issues)


def test_symbol_only_and_footprint_only(tmp_path):
    candidate, issues = _detect(tmp_path, [V6_SYMBOL], "sym.zip")
    assert candidate is not None
    _only(issues, "intake.no_footprint", Severity.WARNING)
    _only(issues, "intake.no_model", Severity.INFO)
    assert not _codes(issues, "intake.no_symbol")

    candidate, issues = _detect(tmp_path, [V6_FOOTPRINT], "fp.zip")
    assert candidate is not None
    _only(issues, "intake.no_symbol", Severity.WARNING)
    assert not _codes(issues, "intake.no_footprint")

    candidate, issues = _detect(tmp_path, [V6_SYMBOL, ("x.dcm", LEGACY_DCM_BYTES)], "symdcm.zip")
    assert candidate is not None
    _only(issues, "intake.no_footprint", Severity.WARNING)
    _only(issues, "intake.legacy_ignored", Severity.INFO)

    candidate, issues = _detect(tmp_path, [V6_FOOTPRINT, ("y.mod", LEGACY_MOD_BYTES)], "fpmod.zip")
    assert candidate is not None
    _only(issues, "intake.no_symbol", Severity.WARNING)
    _only(issues, "intake.legacy_ignored", Severity.INFO)


def test_nothing_found(tmp_path):
    empty = _detect(tmp_path, [], "empty.zip")
    step_only = _detect(tmp_path, [("m.step", STEP_BYTES)], "step.zip")
    for candidate, issues in (empty, step_only):
        assert candidate is None
        assert len(_errors(issues)) == 1
        _only(issues, "intake.nothing_found", Severity.ERROR)
        assert not _codes(issues, "intake.legacy_only")


def test_unreadable_symbol_does_not_count(tmp_path):
    members = [("bad.kicad_sym", b"(kicad_symbol_lib \xff\xfe)"), ("x.lib", LEGACY_LIB_BYTES)]
    candidate, issues = _detect(tmp_path, members)
    assert candidate is None
    _only(issues, "intake.legacy_only", Severity.ERROR)
    assert _codes(issues, "intake.unreadable_file")


def test_legacy_refusal_cleans_up(tmp_path):
    zip_path = make_zip(tmp_path / "legacy.zip", [("x.lib", LEGACY_LIB_BYTES), ("m.step", STEP_BYTES)])
    with open_package(zip_path, REPO_ROOT) as package:
        staging = package.staging_dir
        assert staging is not None and staging.is_dir()
        candidate, issues = detect_candidate(package)
        assert candidate is None
        _only(issues, "intake.legacy_only", Severity.ERROR)
    assert not staging.exists()


def test_no_model_is_valid(tmp_path):
    candidate, issues = _detect(tmp_path, [V6_SYMBOL, V6_FOOTPRINT])
    assert candidate is not None
    assert candidate.has_model is False
    _only(issues, "intake.no_model", Severity.INFO)
    assert not _errors(issues)

    candidate, issues = _detect(tmp_path, [V6_SYMBOL, V6_FOOTPRINT, ("m.step", STEP_BYTES)], "model.zip")
    assert candidate.has_model is True
    assert not _codes(issues, "intake.no_model")


def test_legacy_name_list_is_capped(tmp_path):
    members = [(f"p{i:02d}.lib", LEGACY_LIB_BYTES) for i in range(25)]
    candidate, issues = _detect(tmp_path, members)
    assert candidate is None
    issue = _only(issues, "intake.legacy_only", Severity.ERROR)
    assert "p00.lib" in issue.text and "p19.lib" in issue.text
    assert "p20.lib" not in issue.text
    assert "and 5 more" in issue.text
