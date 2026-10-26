"""scan_all over the synthetic Atomic_ tree: which libraries are judged, what is logged, what is attached (SCAN-01, ATOM-03).

Only issues whose code starts with "atomic." are looked at, so other scan lines never matter here.
"""

import pytest

from customfixtures import (
    ATOMIC_EXPECTED,
    ATOMIC_LIBRARIES,
    atomic_lib,
    digest_tree,
    write_atomic_custom,
    write_fake_kicad,
    write_synthetic_custom,
)
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import FixSpec, Severity

UNCHECKED = ("Connector_Legacy", "atomic_Lower", "ATOMIC_Upper", "AtomicNoUnderscore", "WE-Connectors")
CHECKED = tuple(lib.name for lib in ATOMIC_LIBRARIES if lib.name.startswith("Atomic_"))


def _root(tmp_path):
    return tmp_path / "repo"


def _scan(tmp_path):
    """Write the atomic inventory and scan it, with the fake KiCad folders."""
    root = _root(tmp_path)
    write_atomic_custom(root)
    footprints, _ = write_fake_kicad(tmp_path)
    return scan_all(root, kicad_fp_dir=footprints)


def _atomic_issues(result):
    return [i for i in result.issues if i.code.startswith("atomic.")]


def _lib(result, nickname):
    return next(lib for lib in result.symbol_libs if lib.nickname == nickname)


def _summary_text():
    failing = sum(1 for rules in ATOMIC_EXPECTED.values() if rules)
    problems = sum(len(rules) for rules in ATOMIC_EXPECTED.values())
    noun = "problem" if problems == 1 else "problems"
    return f"Atomic check: {failing} of {len(ATOMIC_EXPECTED)} symbols fail ({problems} {noun})"


def test_every_atomic_library_has_its_symbols_in_file_order_with_the_expected_rules(tmp_path):
    result = _scan(tmp_path)

    for lib in ATOMIC_LIBRARIES:
        if lib.name not in CHECKED:
            continue
        scanned = _lib(result, lib.name)
        assert scanned.atomic is True
        assert [e.name for e in scanned.symbols] == [s.name for s in lib.symbols]
        for entry in scanned.symbols:
            got = frozenset(v.rule for v in entry.violations)
            assert got == ATOMIC_EXPECTED[(lib.name, entry.name)], (lib.name, entry.name)


def test_each_broken_rule_is_one_warning_with_library_symbol_and_reason(tmp_path):
    issues = _atomic_issues(_scan(tmp_path))

    expected = sorted(
        (f"atomic.{rule}", f"{library} / {symbol}")
        for (library, symbol), rules in ATOMIC_EXPECTED.items()
        for rule in rules
    )
    got = sorted(
        (i.code, i.text.split(":")[0]) for i in issues if i.code not in ("atomic.summary",) and i.severity is Severity.WARNING
    )
    assert got == expected
    texts = {i.text for i in issues}
    assert "Atomic_Connector / DS-EMPTY: no datasheet" in texts
    assert "Atomic_Connector / DS-WORDS: Datasheet is not a link or file path" in texts
    assert "Atomic_Connector / DESC-EMPTY: no description" in texts


def test_the_summary_line_is_last_and_counts_symbols_and_problems(tmp_path):
    issues = _atomic_issues(_scan(tmp_path))

    assert issues[-1].code == "atomic.summary"
    assert issues[-1].severity is Severity.WARNING
    assert issues[-1].text == _summary_text()
    assert [i for i in issues if i.code == "atomic.summary"] == [issues[-1]]


@pytest.mark.parametrize("nickname", UNCHECKED)
def test_a_library_without_the_exact_prefix_is_never_judged(tmp_path, nickname):
    scanned = _lib(_scan(tmp_path), nickname)

    assert scanned.atomic is False
    assert scanned.symbols == []
    assert scanned.check_problem is None


def test_no_issue_names_an_unchecked_library(tmp_path):
    issues = _atomic_issues(_scan(tmp_path))

    for nickname in UNCHECKED:
        assert not any(nickname in i.text for i in issues), nickname


def test_a_library_outside_custom_is_judged_but_gets_no_fix_and_no_fill(tmp_path):
    scanned = _lib(_scan(tmp_path), "Atomic_Elsewhere")

    violations = [v for e in scanned.symbols for v in e.violations]
    assert [v.rule for v in violations] == ["datasheet"]
    assert violations[0].fixes == ()
    assert violations[0].fill is None


def test_a_custom_library_gets_a_fill_template_for_datasheet_and_description(tmp_path):
    entries = {e.name: e for e in _lib(_scan(tmp_path), "Atomic_Connector").symbols}

    datasheet = entries["DS-EMPTY"].violations[0].fill
    description = entries["DESC-EMPTY"].violations[0].fill
    assert isinstance(datasheet, FixSpec) and datasheet.kind == "fill_datasheet"
    assert datasheet.symbol == "DS-EMPTY" and datasheet.rel_path == "Custom/Symbols/Atomic_Connector.kicad_sym"
    assert datasheet.params == {"property": "Datasheet", "value": ""}
    assert description.kind == "fill_description"
    assert description.params == {"property": "Description", "value": ""}


def test_an_atomic_library_with_no_symbols_is_atomic_and_empty(tmp_path):
    scanned = _lib(_scan(tmp_path), "Atomic_Empty")

    assert scanned.atomic is True
    assert scanned.symbols == []
    assert scanned.check_problem is None


def test_a_scan_without_an_atomic_library_has_no_atomic_issue(tmp_path):
    root = _root(tmp_path)
    write_synthetic_custom(root)

    result = scan_all(root, kicad_fp_dir=tmp_path / "no_kicad")

    assert _atomic_issues(result) == []


def test_the_scan_changes_nothing_on_disk(tmp_path):
    root = _root(tmp_path)
    write_atomic_custom(root)
    before = digest_tree(root)

    scan_all(root, kicad_fp_dir=tmp_path / "no_kicad")

    assert digest_tree(root) == before


def test_an_unreadable_library_is_reported_and_the_others_are_still_checked(tmp_path):
    root = _root(tmp_path)
    write_atomic_custom(root)
    (root / "Custom" / "Symbols" / "Atomic_Broken.kicad_sym").write_bytes(b"(kicad_symbol_lib \xff\xfe broken")

    result = scan_all(root, kicad_fp_dir=write_fake_kicad(tmp_path)[0])

    broken = _lib(result, "Atomic_Broken")
    assert broken.atomic is True
    assert broken.check_problem and "UTF-8" in broken.check_problem
    assert broken.symbols == []
    unreadable = [i for i in _atomic_issues(result) if i.code == "atomic.unreadable"]
    assert len(unreadable) == 1
    assert unreadable[0].severity is Severity.WARNING
    assert unreadable[0].text.startswith("Atomic_Broken: could not be checked: ")
    assert [e.name for e in _lib(result, "Atomic_Connector").symbols][0] == "USB4105-GF-A"
    assert _atomic_issues(result)[-1].text == _summary_text()


# -- plain language, imports and real KiCad ------------------------------------------------------


def test_no_message_names_an_internal_field(tmp_path):
    result = _scan(tmp_path)
    texts = [i.text for i in _atomic_issues(result)]
    for lib in result.symbol_libs:
        for entry in lib.symbols:
            for violation in entry.violations:
                texts.append(violation.text)
                texts.extend(f.label for f in violation.fixes)
                if violation.fill is not None:
                    texts.append(violation.fill.label)
            for finding in entry.findings:
                texts.append(finding.text)
                if finding.fix is not None:
                    texts.append(finding.fix.label)

    assert texts
    assert not [t for t in texts if "ki_" in t.casefold()]


def test_a_derived_symbol_is_judged_in_the_scan_on_its_own_fields(tmp_path):
    result = _scan(tmp_path)
    entries = {e.name: e for e in _lib(result, "Atomic_Regulator").symbols}

    assert entries["TLV75518PDBVR"].extends == "TLV75533PDBVR"
    assert entries["TLV75518PDBVR"].violations == []
    assert [v.text for v in entries["TLV75525PDBVR"].violations] == [
        "no MPN of its own (the parent's MPN does not count)"
    ]
    orphan = _lib(result, "Atomic_Orphan").symbols[0]
    assert orphan.violations[0].text == 'no manufacturer (its parent symbol "NOT-THERE" is missing)'


def test_the_check_never_imports_network_or_process_modules():
    import ast

    from kicad_lib_manager import atomic_check

    with open(atomic_check.__file__, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            imported.add(node.module.split(".")[0])

    assert not imported & {"urllib", "http", "socket", "webbrowser", "subprocess"}


@pytest.mark.kicad_cli
@pytest.mark.parametrize(
    "library", [lib for lib in ATOMIC_LIBRARIES if lib.name != "Atomic_Orphan"], ids=lambda lib: lib.name
)
def test_kicad_cli_loads_every_fixture_library(kicad_cli_path, library):
    from kicad_lib_manager.importer.kicad_cli import load_gate

    issues = load_gate(kicad_cli_path, library=library.name, symbol_lib=atomic_lib(library.symbols), footprints=[])

    assert issues == []
