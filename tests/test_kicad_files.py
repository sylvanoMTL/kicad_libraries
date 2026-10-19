"""Read-side locators of kicad_files: spans, exact matching, Issue-returning loaders (D-12)."""

import re
import zipfile
from pathlib import Path

import pytest

from kicad_lib_manager.kicad_files import (
    LoadedFile,
    file_kind,
    file_version,
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    lib_table,
    lib_table_entries,
    load,
    parse_bytes,
)
from kicad_lib_manager.models import Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_SYMBOL = "KiCADv6/2026-10-18_09-12-49.kicad_sym"
UL_FOOTPRINT = "KiCADv6/footprints.pretty/DQK0006B.kicad_mod"
MAX_ZIP_MEMBER = 5 * 1024 * 1024
CUSTOM_SKIP = "Custom submodule not checked out (git submodule update --init Custom)"
UNIT_RE = re.compile(r"_\d+_\d+$")


def _fixture(rel: str) -> LoadedFile:
    loaded = parse_bytes((FIXTURES_DIR / rel).read_bytes(), Path(rel).name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def _zip_member(member: str) -> LoadedFile:
    with zipfile.ZipFile(UL_ZIP) as z:
        assert z.getinfo(member).file_size < MAX_ZIP_MEMBER
        data = z.read(member)
    loaded = parse_bytes(data, Path(member).name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def _custom_files(pattern: str) -> list[Path]:
    custom = REPO_ROOT / "Custom"
    return sorted(custom.rglob(pattern)) if custom.is_dir() else []


def _slice(loaded: LoadedFile, node) -> str:
    return loaded.source.text[node.start:node.end]


SYMBOL_FIXTURES = ["lf", "crlf", "bom", "mixed_eol"]


# -- symbols -------------------------------------------------------------------


@pytest.mark.parametrize("name", SYMBOL_FIXTURES)
def test_find_symbols_top_level_only_in_document_order(name):
    loaded = _fixture(f"sexpr/{name}.kicad_sym")
    names = [s.name for s in find_symbols(loaded.root)]
    assert names == ["FIX_R", "FIX_U"]
    for ref in find_symbols(loaded.root):
        assert _slice(loaded, ref.name_node) == ref.name_node.text
        assert _slice(loaded, ref.node).startswith("(symbol")


def test_find_symbol_is_exact():
    loaded = _fixture("sexpr/lf.kicad_sym")
    found = find_symbol(loaded.root, "FIX_R")
    assert found is not None and found.name == "FIX_R"
    assert find_symbol(loaded.root, "FIX_U").name == "FIX_U"
    assert find_symbol(loaded.root, "FIX") is None
    assert find_symbol(loaded.root, "FIX_R_1_1") is None
    assert find_symbol(loaded.root, "fix_r") is None


@pytest.mark.parametrize("name", SYMBOL_FIXTURES)
def test_find_property_values_and_spans(name):
    loaded = _fixture(f"sexpr/{name}.kicad_sym")
    fix_r = find_symbol(loaded.root, "FIX_R")
    prop = find_property(fix_r.node, "Footprint")
    assert prop.value == "Fixture_Lib:FIX_FP"
    assert _slice(loaded, prop.value_node) == prop.value_node.text == '"Fixture_Lib:FIX_FP"'
    assert _slice(loaded, prop.name_node) == prop.name_node.text == '"Footprint"'
    assert find_property(fix_r.node, "Datasheet").value == ""
    assert find_property(fix_r.node, "Value").value == "FIX_R"
    fix_u = find_symbol(loaded.root, "FIX_U")
    assert find_property(fix_u.node, "Footprint").value == "Fixture_Lib:FIX_FP2"


def test_find_property_is_exact_and_direct_only():
    loaded = _fixture("sexpr/lf.kicad_sym")
    fix_r = find_symbol(loaded.root, "FIX_R")
    assert find_property(fix_r.node, "footprint") is None
    assert find_property(fix_r.node, "Foot") is None
    assert find_property(fix_r.node, "Missing") is None
    # FIX_U has no Datasheet; FIX_R's must not leak across symbols
    assert find_property(find_symbol(loaded.root, "FIX_U").node, "Datasheet") is None
    # A property nested in a sub-symbol is never returned for the parent
    text = (
        '(kicad_symbol_lib (symbol "P" (symbol "P_1_1" (property "Deep" "x" (at 0 0 0))))'
        ' (symbol "Q" (property "Deep" "y")))'
    )
    loaded = parse_bytes(text.encode(), "nested.kicad_sym")
    assert find_property(find_symbol(loaded.root, "P").node, "Deep") is None
    assert find_property(find_symbol(loaded.root, "Q").node, "Deep").value == "y"


def test_escapes_decode_and_slice():
    loaded = _fixture("sexpr/escapes.kicad_sym")
    node = find_symbol(loaded.root, "FIX_ESC").node
    expected = {
        "Value": "R (0.1%)",
        "Description": 'say "hi" (twice)',
        "Datasheet": "C:\\docs\\a.pdf",
        "Note": "line1\nline2",
        "Tabbed": "tab\there",
        "Unit": "10k\u03a9",
    }
    for name, value in expected.items():
        prop = find_property(node, name)
        assert prop.value == value
        assert _slice(loaded, prop.value_node) == prop.value_node.text


# -- footprints ------------------------------------------------------------------


def test_footprint_name_quoted():
    loaded = _fixture("sexpr/bare_atoms.kicad_mod")
    ref = footprint_name(loaded.root)
    assert ref.name == "FIX_BARE"
    assert ref.name_node.kind == "str"
    assert ref.node.head == "footprint"
    assert _slice(loaded, ref.name_node) == ref.name_node.text


def test_footprint_name_legacy_module_bare_atom():
    loaded = _fixture("sexpr/legacy_module.kicad_mod")
    ref = footprint_name(loaded.root)
    assert ref.name == "FIX_LEGACY"
    assert ref.name_node.kind == "atom"
    assert ref.node.head == "module"
    assert _slice(loaded, ref.name_node) == "FIX_LEGACY"


def test_footprint_name_ul_member():
    loaded = _zip_member(UL_FOOTPRINT)
    ref = footprint_name(loaded.root)
    assert ref.name == "DQK0006B"
    assert _slice(loaded, ref.name_node) == ref.name_node.text


def test_footprint_name_absent_on_symbol_file():
    assert footprint_name(_fixture("sexpr/lf.kicad_sym").root) is None


def _paths(loaded: LoadedFile) -> list[str]:
    ref = footprint_name(loaded.root)
    return [m.path for m in find_models(ref.node)]


def test_find_models_none():
    assert _paths(_fixture("sexpr/bare_atoms.kicad_mod")) == []
    assert _paths(_zip_member(UL_FOOTPRINT)) == []


def test_find_models_two_in_document_order():
    loaded = _fixture("sexpr/two_models.kicad_mod")
    models = find_models(footprint_name(loaded.root).node)
    assert [m.path for m in models] == [
        "${CUSTOM_3DMODEL_DIR}/FIX_A.step",
        "${CUSTOM_3DMODEL_DIR}/FIX_B.stp",
    ]
    for m in models:
        assert m.node.head == "model"
        assert _slice(loaded, m.path_node) == m.path_node.text
        assert m.path_node.kind == "str"


def test_find_models_bare_atom_path():
    loaded = _fixture("sexpr/legacy_module.kicad_mod")
    models = find_models(footprint_name(loaded.root).node)
    assert [m.path for m in models] == ["${KIPRJMOD}/3d/FIX_LEGACY.wrl"]
    assert models[0].path_node.kind == "atom"
    assert _slice(loaded, models[0].path_node) == "${KIPRJMOD}/3d/FIX_LEGACY.wrl"


def test_find_models_no_trailing_newline():
    loaded = _fixture("sexpr/no_trailing_newline.kicad_mod")
    assert loaded.source.text.endswith(")")
    assert _paths(loaded) == ["${CUSTOM_3DMODEL_DIR}/FIX_NO_EOL.step"]


def test_find_models_direct_children_only():
    text = '(footprint "F" (fp_text user "x" (model "nested.step")) (model "real.step"))'
    loaded = parse_bytes(text.encode(), "f.kicad_mod")
    assert _paths(loaded) == ["real.step"]


# -- lib tables --------------------------------------------------------------------


def _entries(rel: str):
    loaded = _fixture(rel)
    return loaded, lib_table_entries(loaded.root)


def test_lib_table_basic():
    loaded, entries = _entries("tables/basic.sym-lib-table")
    assert [e.name for e in entries] == ["Fixture_A", "Fixture_B"]
    assert entries[0].type == "KiCad"
    assert entries[0].uri == "${KICAD_LIB_GITHUB}/Custom/Symbols/Fixture_A.kicad_sym"
    assert entries[0].options == "" and entries[0].descr == ""
    assert entries[1].descr == "Second fixture"
    assert entries[0].flags == () and entries[0].extras == ()
    for e in entries:
        assert _slice(loaded, e.node).startswith("(lib")
        for field, node in e.value_nodes.items():
            assert _slice(loaded, node) == node.text, field


def test_lib_table_escaped_decodes():
    loaded, entries = _entries("tables/escaped.sym-lib-table")
    (e,) = entries
    assert e.name == "Escaped_Lib"
    assert e.uri == "C:\\KiCad\\libs\\Escaped.kicad_sym"
    assert e.descr == 'Has "quotes" and (parens)'
    assert _slice(loaded, e.value_nodes["uri"]) == e.value_nodes["uri"].text


def test_lib_table_empty():
    assert _entries("tables/empty.sym-lib-table")[1] == []


def test_lib_table_reordered_and_minimal():
    loaded, entries = _entries("tables/reordered.fp-lib-table")
    reordered, minimal = entries
    assert reordered.name == "Reordered"
    assert reordered.type == "KiCad"
    assert reordered.uri == "${KICAD_LIB_GITHUB}/Custom/Footprints/Reordered.pretty"
    assert reordered.descr == "fields out of order"
    assert reordered.options == ""
    assert minimal.name == "Minimal"
    assert minimal.uri == "/abs/path/Minimal.pretty"
    assert minimal.options is None and minimal.descr is None
    assert set(minimal.value_nodes) == {"name", "type", "uri"}
    for e in entries:
        for field, node in e.value_nodes.items():
            assert _slice(loaded, node) == node.text, field


def test_lib_table_flags_and_unknown_children():
    loaded, entries = _entries("tables/flags.fp-lib-table")
    disabled, hidden, future = entries
    assert disabled.flags == ("disabled",)
    assert hidden.flags == ("hidden",)
    assert future.flags == ()
    assert disabled.extras == () and hidden.extras == ()
    (extra,) = future.extras
    assert extra.head == "future_field"
    assert _slice(loaded, extra) == '(future_field "x")'


def test_lib_table_ignores_version_and_non_table_roots():
    assert lib_table_entries(_fixture("sexpr/lf.kicad_sym").root) == []


# -- UL sample --------------------------------------------------------------------


def test_ul_symbol_member():
    loaded = _zip_member(UL_SYMBOL)
    symbols = find_symbols(loaded.root)
    assert [s.name for s in symbols] == ["CSD85301Q2"]
    assert find_property(symbols[0].node, "Footprint").value == "DQK0006B"
    assert find_symbol(loaded.root, "CSD85301Q2_1_1") is None


# -- loaders return Issues ----------------------------------------------------------


def test_parse_bytes_unbalanced_is_issue():
    result = parse_bytes(b"(a))", "x.kicad_sym")
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "sexpr.unbalanced"
    assert result.text.startswith("Could not parse x.kicad_sym")


@pytest.mark.parametrize(
    ("data", "code"),
    [(b"(a", "sexpr.unclosed"), (b'(a "b', "sexpr.unterminated")],
)
def test_parse_bytes_other_sexpr_errors(data, code):
    result = parse_bytes(data, "z")
    assert isinstance(result, Issue) and result.code == code


def test_parse_bytes_bad_encoding_is_issue():
    result = parse_bytes(b"\xff(a)", "y")
    assert isinstance(result, Issue)
    assert result.code == "fs.bad_encoding"


def test_load_missing_file_is_issue(tmp_path):
    result = load(tmp_path / "missing.kicad_mod")
    assert isinstance(result, Issue)
    assert result.code == "fs.read_failed"


def test_load_reads_and_parses(tmp_path):
    path = tmp_path / "a.kicad_sym"
    path.write_bytes((FIXTURES_DIR / "sexpr" / "bom.kicad_sym").read_bytes())
    loaded = load(path)
    assert isinstance(loaded, LoadedFile)
    assert loaded.source.bom is True
    assert [s.name for s in find_symbols(loaded.root)] == ["FIX_R", "FIX_U"]


def test_load_parse_error_names_the_file(tmp_path):
    path = tmp_path / "broken.kicad_sym"
    path.write_bytes(b"(kicad_symbol_lib")
    result = load(path)
    assert isinstance(result, Issue)
    assert result.code == "sexpr.unclosed"
    assert result.text.startswith("Could not parse broken.kicad_sym")


def test_parse_bytes_mixed_eol_keeps_warning():
    loaded = _fixture("sexpr/mixed_eol.kicad_sym")
    assert [i.code for i in loaded.source.issues] == ["fs.mixed_eol"]


# -- live Custom invariants ------------------------------------------------------------


def test_live_custom_symbols():
    files = _custom_files("*.kicad_sym")
    if not files:
        pytest.skip(CUSTOM_SKIP)
    for path in files:
        loaded = load(path)
        assert isinstance(loaded, LoadedFile), f"{path}: {loaded}"
        symbols = find_symbols(loaded.root)
        assert symbols, f"{path.name} has no symbols"
        for s in symbols:
            assert not UNIT_RE.search(s.name), f"{path.name}: sub-symbol {s.name} leaked"
            assert find_property(s.node, "Footprint") is not None, f"{path.name}:{s.name}"
            assert _slice(loaded, s.name_node) == s.name_node.text


def test_live_custom_footprints():
    files = _custom_files("*.kicad_mod")
    if not files:
        pytest.skip(CUSTOM_SKIP)
    for path in files:
        loaded = load(path)
        assert isinstance(loaded, LoadedFile), f"{path}: {loaded}"
        ref = footprint_name(loaded.root)
        assert ref is not None, f"{path.name} has no footprint name"
        for m in find_models(ref.node):
            assert _slice(loaded, m.path_node) == m.path_node.text


# -- token-kind guards (WR-01) and value-less field routing (IN-04) ------------------


def test_lib_entry_with_a_list_for_a_value_leaves_the_field_unset():
    loaded = parse_bytes(b'(sym_lib_table (lib (name (x y))(uri "u")))', "t")
    (entry,) = lib_table_entries(loaded.root)
    assert entry.name is None
    assert entry.uri == "u"
    assert [x.head for x in entry.extras] == ["name"]
    assert entry.flags == ()


def test_lib_entry_valueless_known_field_goes_to_extras_never_flags():
    loaded = parse_bytes(b'(sym_lib_table (lib (name)(type "KiCad")(uri "u")(name "N")))', "t")
    (entry,) = lib_table_entries(loaded.root)
    assert entry.flags == ()
    assert entry.name == "N"
    (extra,) = entry.extras
    assert extra.head == "name" and len(extra.children) == 1


def test_lib_table_exposes_version_among_the_other_children():
    table = lib_table(_fixture("tables/basic.sym-lib-table").root)
    assert table.others[0].head == "version"


def test_find_symbols_skips_a_symbol_whose_name_is_not_a_token():
    text = '(kicad_symbol_lib (symbol (x y) (a)) (symbol "Real"))'
    loaded = parse_bytes(text.encode(), "s.kicad_sym")
    assert [s.name for s in find_symbols(loaded.root)] == ["Real"]


def test_find_property_skips_a_property_with_a_non_token_name_or_value():
    text = '(symbol "S" (property "Footprint" (at 0 0)) (property (x) "v") (property "Footprint" "FP"))'
    symbol = parse_bytes(text.encode(), "s").root.children[0]
    assert find_property(symbol, "Footprint").value == "FP"
    only_bad = parse_bytes(b'(symbol "S" (property "Footprint" (at 0 0)))', "s").root.children[0]
    assert find_property(only_bad, "Footprint") is None


# -- file kind and version (INTK-05, PREV-06 inputs) -----------------------------


def _kind_version(data: bytes):
    loaded = parse_bytes(data, "x")
    assert isinstance(loaded, LoadedFile), loaded
    return file_kind(loaded.root), file_version(loaded.root)


def test_file_kind_and_version():
    assert (file_kind(_zip_member(UL_SYMBOL).root), file_version(_zip_member(UL_SYMBOL).root)) == (
        "kicad_symbol_lib",
        20211014,
    )
    assert (file_kind(_zip_member(UL_FOOTPRINT).root), file_version(_zip_member(UL_FOOTPRINT).root)) == (
        "footprint",
        20211014,
    )
    lf = _fixture("sexpr/lf.kicad_sym").root
    assert (file_kind(lf), file_version(lf)) == ("kicad_symbol_lib", 20241209)
    legacy = _fixture("sexpr/legacy_module.kicad_mod").root
    assert (file_kind(legacy), file_version(legacy)) == ("module", None)


def test_file_version_rejects_non_integers_and_nested_versions():
    assert _kind_version(b'(kicad_symbol_lib (version "abc"))') == ("kicad_symbol_lib", None)
    assert _kind_version(b'(footprint "x" (version 1.5))') == ("footprint", None)
    assert _kind_version(b'(footprint "x" (version "20211014"))') == ("footprint", None)
    # Arabic-Indic digit one: str.isdigit() is True, but it is not an ASCII integer
    assert _kind_version('(footprint "x" (version ١))'.encode("utf-8")) == ("footprint", None)
    assert _kind_version(b'(footprint "x" (layer "F.Cu" (version 5)))') == ("footprint", None)


def test_file_kind_of_empty_input():
    assert _kind_version(b"") == (None, None)
