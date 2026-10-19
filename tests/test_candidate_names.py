"""Candidate items report their sanitised name beside the original: success criterion 5, LIB-03, D-15."""

import dataclasses

from zipfixtures import REPO_ROOT, STEP_BYTES, UL_ZIP, footprint, make_zip, symbol_lib

from kicad_lib_manager.importer.candidate import FootprintItem, ModelItem, SymbolItem
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.naming import NameResult
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.models import Severity


def _codes(result):
    return {i.code: i.severity for i in result.issues}


def test_candidate_names_ul():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        symbol = candidate.symbols[0]
        fp = candidate.footprints[0]
        model = candidate.models[0]
        assert symbol.name_check == NameResult("CSD85301Q2", "CSD85301Q2", ())
        assert fp.name_check.sanitized == "DQK0006B"
        assert model.name_check.sanitized == "DLV0006A.stp"
        assert not symbol.name_check.changed
        assert not fp.name_check.changed
        assert not model.name_check.changed


def test_candidate_names_hostile(tmp_path):
    zip_path = make_zip(
        tmp_path / "hostile.zip",
        [
            ("p.kicad_sym", symbol_lib(("a/b:c",))),
            ("f.kicad_mod", footprint("NUL")),
            ("my part (v2).STEP", STEP_BYTES),
        ],
    )
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        symbol = candidate.symbols[0]
        assert symbol.name == "a/b:c"
        assert symbol.name_check.original == "a/b:c"
        assert symbol.name_check.sanitized == "a_b_c"
        assert _codes(symbol.name_check)["naming.changed"] is Severity.INFO

        fp = candidate.footprints[0]
        assert fp.name == "NUL"
        assert fp.name_check.sanitized == "NUL_"
        assert _codes(fp.name_check)["naming.reserved"] is Severity.WARNING
        assert "naming.changed" in _codes(fp.name_check)

        model = candidate.models[0]
        assert model.filename == "my part (v2).STEP"
        assert model.name_check.original == "my part (v2).STEP"
        assert model.name_check.sanitized == "my_part_v2.STEP"
        assert "naming.changed" in _codes(model.name_check)


def test_candidate_names_follow_the_item():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        renamed = dataclasses.replace(candidate.symbols[0], name="CON")
        assert renamed.name_check.sanitized == "CON_"
    for cls in (SymbolItem, FootprintItem, ModelItem):
        assert "name_check" not in {f.name for f in dataclasses.fields(cls)}
