"""Skipping one source's 3D model path check while the libraries load (G-12-21).

The synthetic repo has the atomic Custom inventory plus a hand-written WurthElektronik source, so the
read-only Würth submodule is never touched.
"""

from pathlib import Path

import pytest
from customfixtures import write_atomic_custom, write_fake_kicad

from kicad_lib_manager import library_scanner
from kicad_lib_manager.library_scanner import rescan_library, scan_all
from kicad_lib_manager.models import Severity

WURTH = "WurthElektronik"
WE_ROOT = "WurthElektronik/KiCad-Library"
WE_TEST = f"{WE_ROOT}/footprints/WE_Test.pretty"
WE_OTHER = f"{WE_ROOT}/footprints/WE_Other.pretty"
CUSTOM_PRETTY = "Custom/Footprints/Atomic_Footprints.pretty"

MODEL_CODES = {"scan.unreadable", "scan.model_var", "scan.model_missing", "scan.model_absolute"}
SKIP_CODE = "scan.models_skipped"
SKIP_TEXT = "3D model paths of WurthElektronik were not checked: skipped while the libraries loaded. Rescan checks them."
SKIP_TEXT_EXCEPT = (
    "3D model paths of WurthElektronik were not checked, except WE_Test (rescanned since): "
    "skipped while the libraries loaded. Rescan checks them."
)

SYMBOL_TEXT = (
    '(kicad_symbol_lib (version 20231120) (generator "test")\n'
    '  (symbol "WE_SYM" (property "Reference" "U" (at 0 0 0))\n'
    '    (property "Footprint" "WE_Test:WE_FP_A" (at 0 0 0)))\n'
    ")\n"
)


def _write_footprint(folder: Path, name: str, model: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.kicad_mod").write_bytes(f'(footprint "{name}"\n  (model "{model}")\n)\n'.encode())


@pytest.fixture
def two_sources(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    write_atomic_custom(root)
    symbols = root / WE_ROOT / "symbols"
    symbols.mkdir(parents=True, exist_ok=True)
    (symbols / "WE_Test.kicad_sym").write_text(SYMBOL_TEXT, encoding="utf-8")
    _write_footprint(root / WE_TEST, "WE_FP_A", "C:/models/a.step")
    _write_footprint(root / WE_TEST, "WE_FP_B", "C:/models/b.step")
    footprints, _models = write_fake_kicad(tmp_path)
    return root, footprints


def _add_we_other(root: Path) -> None:
    _write_footprint(root / WE_OTHER, "WE_FP_C", "C:/models/c.step")


def _model_lines(issues, source=None):
    lines = [i for i in issues if i.code in MODEL_CODES]
    if source is not None:
        lines = [i for i in lines if i.text.startswith(f"[{source}/")]
    return lines


def _skip_lines(issues):
    return [i for i in issues if i.code == SKIP_CODE]


def _skip_wurth(source: str) -> bool:
    return source == WURTH


def _assert_skip_line_in_place(issues) -> None:
    """The skip line sits after the last 3D path line and before the first atomic line."""
    codes = [i.code for i in issues]
    last_model = max(n for n, code in enumerate(codes) if code in MODEL_CODES)
    first_atomic = min(n for n, code in enumerate(codes) if code.startswith("atomic."))
    assert last_model < codes.index(SKIP_CODE) < first_atomic


# ── Skip through scan_all ────────────────────────────────────────────

def test_scan_without_skip_is_unchanged(two_sources):
    root, fp = two_sources
    plain = scan_all(root, kicad_fp_dir=fp)
    seen: list = []
    hooked = scan_all(root, kicad_fp_dir=fp, skip=lambda s: False, checking=seen.append)

    assert hooked.symbol_libs == plain.symbol_libs
    assert hooked.footprint_libs == plain.footprint_libs
    assert hooked.issues == plain.issues
    assert hooked.skipped_sources == [] and plain.skipped_sources == []
    assert hooked.models_unchecked == []
    assert _skip_lines(hooked.issues) == []

    # One report per change of source, then None at the end
    assert seen[-1] is None
    sources = seen[:-1]
    assert None not in sources and len(sources) == len(set(sources))
    assert sources.index("Custom") < sources.index(WURTH)


def test_skipped_source_has_no_3d_path_lines(two_sources, monkeypatch):
    root, fp = two_sources
    plain = scan_all(root, kicad_fp_dir=fp)
    assert len(_model_lines(plain.issues, WURTH)) == 2

    loaded: list[Path] = []
    real_load = library_scanner.kicad_files.load

    def recording_load(path, *args, **kwargs):
        loaded.append(Path(path))
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(library_scanner.kicad_files, "load", recording_load)
    result = scan_all(root, kicad_fp_dir=fp, skip=_skip_wurth)

    assert result.skipped_sources == [WURTH]
    assert result.models_unchecked == [WE_TEST]
    assert _model_lines(result.issues, WURTH) == []
    assert _model_lines(result.issues, "Custom") == _model_lines(plain.issues, "Custom")
    assert not [p for p in loaded if WURTH in p.parts]

    lines = _skip_lines(result.issues)
    assert len(lines) == 1
    assert lines[0].severity is Severity.INFO
    assert lines[0].text == SKIP_TEXT
    _assert_skip_line_in_place(result.issues)


def test_skip_answered_late_still_leaves_no_3d_path_line(two_sources):
    root, fp = two_sources
    asked = {"wurth": 0}

    def late_skip(source: str) -> bool:
        if source != WURTH:
            return False
        asked["wurth"] += 1
        return asked["wurth"] >= 2

    result = scan_all(root, kicad_fp_dir=fp, skip=late_skip)

    assert asked["wurth"] == 2
    assert result.skipped_sources == [WURTH]
    assert _model_lines(result.issues, WURTH) == []
    assert [i.text for i in _skip_lines(result.issues)] == [SKIP_TEXT]


def test_skip_keeps_every_library_and_link(two_sources):
    root, fp = two_sources
    plain = scan_all(root, kicad_fp_dir=fp)
    skipped = scan_all(root, kicad_fp_dir=fp, skip=_skip_wurth)

    assert skipped.symbol_libs == plain.symbol_libs
    assert skipped.footprint_libs == plain.footprint_libs
    we_symbols = [lib for lib in skipped.symbol_libs if lib.nickname == "WE_Test"]
    assert [lib.source for lib in we_symbols] == [WURTH]
    refs = we_symbols[0].footprint_refs
    assert [(r.library_name, r.footprint_name, r.found_in_repo) for r in refs] == [("WE_Test", "WE_FP_A", True)]
    assert [lib.nickname for lib in skipped.footprint_libs if lib.source == WURTH] == ["WE_Test"]

    def rest(result):
        return [
            i for i in result.issues
            if i.code != SKIP_CODE and not (i.code in MODEL_CODES and i.text.startswith(f"[{WURTH}/"))
        ]

    assert rest(skipped) == rest(plain)


def test_library_rescan_keeps_the_skip_line(two_sources):
    root, fp = two_sources
    _add_we_other(root)
    result = scan_all(root, kicad_fp_dir=fp, skip=_skip_wurth)
    assert result.models_unchecked == [WE_OTHER, WE_TEST]

    # (a) A Custom library keeps the line as it was
    a = rescan_library(root, result, "footprint", CUSTOM_PRETTY, fp)
    assert not hasattr(a, "code"), a
    assert a.result.skipped_sources == [WURTH]
    assert a.result.models_unchecked == [WE_OTHER, WE_TEST]
    assert [i.text for i in _skip_lines(a.result.issues)] == [SKIP_TEXT]
    _assert_skip_line_in_place(a.result.issues)

    # (b) A rescanned WurthElektronik library shows its lines again and is named as rescanned since
    b = rescan_library(root, result, "footprint", WE_TEST, fp).result
    assert len(_model_lines(b.issues, f"{WE_TEST}")) == 2
    assert _model_lines(b.issues, f"{WE_OTHER}") == []
    assert b.models_unchecked == [WE_OTHER]
    assert b.skipped_sources == [WURTH]
    assert library_scanner.models_rechecked(b) == ["WE_Test"]
    assert [i.text for i in _skip_lines(b.issues)] == [SKIP_TEXT_EXCEPT]
    _assert_skip_line_in_place(b.issues)

    # (c) Once every library was rescanned the line is gone
    c = rescan_library(root, b, "footprint", WE_OTHER, fp).result
    assert len(_model_lines(c.issues, f"{WE_OTHER}")) == 1
    assert c.models_unchecked == []
    assert c.skipped_sources == []
    assert _skip_lines(c.issues) == []

    # The skip line never calls a library unchecked while the result holds a line of it
    for r in (a.result, b, c):
        text = " ".join(i.text for i in _skip_lines(r.issues))
        for lib in ("WE_Test", "WE_Other"):
            if _model_lines(r.issues, f"{WE_ROOT}/footprints/{lib}.pretty"):
                assert not text or lib in text


def test_skip_line_texts():
    assert library_scanner.models_skipped_issue([WURTH]).text == SKIP_TEXT
    assert library_scanner.models_skipped_issue(["B", "A"]).text.startswith("3D model paths of A and B were not checked:")
    assert library_scanner.models_skipped_issue([WURTH], ["WE_Test"]).text == SKIP_TEXT_EXCEPT
    assert library_scanner.models_skipped_issue([WURTH], ["B", "A"]).text.startswith(
        "3D model paths of WurthElektronik were not checked, except A, B (rescanned since):"
    )


# ── One progress scale ───────────────────────────────────────────────

def test_progress_rises_from_0_to_100(two_sources):
    root, fp = two_sources
    reports: list[tuple[str, int, int]] = []

    scan_all(root, progress=lambda text, current, total: reports.append((text, current, total)), kicad_fp_dir=fp)

    assert {total for _, _, total in reports} == {100}
    values = [current for _, current, _ in reports]
    assert values == sorted(values)
    assert values[0] == 0 and values[-1] == 100
    checking = [current for text, current, _ in reports if text.startswith("Checking 3D paths:")]
    assert checking and all(10 <= value <= 92 for value in checking)
    assert [current for text, current, _ in reports if text == "Checking atomic parts..."] == [92]
