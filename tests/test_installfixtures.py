"""Self-tests that keep the Phase 4 install byte builders honest (INST-02, INST-05, INST-06, POST-04)."""

import re

import pytest

from kicad_lib_manager.kicad_files import (
    LoadedFile,
    file_version,
    find_models,
    find_property,
    find_symbols,
    footprint_name,
    parse_bytes,
)
from kicad_lib_manager.sexpr import Node, unquote
from installfixtures import extends_pair, target_lib, vendor_footprint, vendor_symbol_lib

V6 = 20211014
V8 = 20231120
V9 = 20241209
ALL_VERSIONS = (V6, V8, V9)
MODERN = ((V8, "8.0"), (V9, "9.0"))


def _load(data: bytes) -> LoadedFile:
    loaded = parse_bytes(data, "fixture")
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def _sub_symbols(symbol: Node) -> list[Node]:
    return [child for child in symbol.children if child.head == "symbol"]


def _pin_numbers(sub_symbol: Node) -> list[str]:
    numbers = []
    for pin in sub_symbol.children:
        if pin.head != "pin":
            continue
        number = next(child for child in pin.children if child.head == "number")
        numbers.append(unquote(number.children[1].text))
    return numbers


def _property_names(symbol: Node) -> list[str]:
    return [unquote(child.children[1].text) for child in symbol.children if child.head == "property"]


def _footprint_node(data: bytes) -> Node:
    ref = footprint_name(_load(data).root)
    assert ref is not None
    return ref.node


def _pads(footprint: Node) -> list[Node]:
    return [child for child in footprint.children if child.head == "pad"]


def _pad_numbers(footprint: Node) -> list[str]:
    return [unquote(pad.children[1].text) for pad in _pads(footprint)]


def _xyz(model: Node, field: str) -> list[str]:
    block = next(child for child in model.children if child.head == field)
    xyz = next(child for child in block.children if child.head == "xyz")
    return [atom.text for atom in xyz.children[1:]]


# -- target_lib ----------------------------------------------------------------


def test_target_lib_v6_starts_with_crlf_blank_line_and_one_line_header():
    data = target_lib(V6)
    assert data.startswith(b"\r\n(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\r\n")


def test_target_lib_v6_uses_crlf_only():
    data = target_lib(V6)
    assert data.count(b"\r\n") > 20
    assert data.count(b"\n") == data.count(b"\r\n")
    assert data.count(b"\r") == data.count(b"\r\n")


def test_target_lib_v6_numbers_every_property_and_hides_with_a_bare_atom():
    text = target_lib(V6).decode("utf-8")
    assert text.count("(property ") == 8  # four properties in each of two symbols
    assert re.findall(r"\(id (\d+)\)", text) == ["0", "1", "2", "3"] * 2
    assert '\r\n  (symbol "EXISTING_A"' in text  # two-space indent
    assert text.count(" hide)") == 4  # Footprint and Datasheet of each symbol
    assert "(hide yes)" not in text
    for sym in find_symbols(_load(text.encode()).root):
        assert find_property(sym.node, "Description") is None  # added at 20230620


@pytest.mark.parametrize(("version", "generator_version"), MODERN)
def test_target_lib_modern_is_tab_indented_with_generator_version(version, generator_version):
    text = target_lib(version).decode("utf-8")
    assert text.startswith(
        "(kicad_symbol_lib\n"
        f"\t(version {version})\n"
        '\t(generator "kicad_symbol_editor")\n'
        f'\t(generator_version "{generator_version}")\n'
        '\t(symbol "EXISTING_A"\n'
    )
    assert "\r" not in text
    assert not re.search(r"^ ", text, re.MULTILINE)


@pytest.mark.parametrize(("version", "generator_version"), MODERN)
def test_target_lib_modern_has_no_ids_hides_with_yes_and_carries_a_description(version, generator_version):
    data = target_lib(version)
    text = data.decode("utf-8")
    assert "(id " not in text
    assert "(hide yes)" in text
    assert not re.search(r"\bhide\)", text)
    for sym in find_symbols(_load(data).root):
        assert find_property(sym.node, "Description") is not None


@pytest.mark.parametrize("version", ALL_VERSIONS)
def test_target_lib_names_symbols_in_order_with_core_properties_and_pins(version):
    root = _load(target_lib(version, names=("A", "B"))).root
    symbols = find_symbols(root)
    assert [s.name for s in symbols] == ["A", "B"]
    for s in symbols:
        for prop in ("Reference", "Value", "Footprint", "Datasheet"):
            assert find_property(s.node, prop) is not None
        assert find_property(s.node, "Reference").value == "U"
        assert find_property(s.node, "Value").value == s.name
        assert find_property(s.node, "Footprint").value == ""
        assert find_property(s.node, "Datasheet").value == ""
        subs = _sub_symbols(s.node)
        assert [unquote(sub.children[1].text) for sub in subs] == [f"{s.name}_1_1"]
        assert _pin_numbers(subs[0]) == ["1", "2"]


@pytest.mark.parametrize("version", ALL_VERSIONS)
def test_target_lib_without_names_is_header_only(version):
    data = target_lib(version, names=())
    root = _load(data).root
    assert find_symbols(root) == []
    assert file_version(root) == version
    assert b"(symbol" not in data


def test_target_lib_v6_header_only_bytes_are_exact():
    assert target_lib(V6, names=()) == (
        b"\r\n(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\r\n)\r\n"
    )


@pytest.mark.parametrize("version", ALL_VERSIONS)
def test_target_lib_parses_and_reports_its_version(version):
    data = target_lib(version)
    assert isinstance(data, bytes)
    root = _load(data).root
    assert file_version(root) == version
    assert [s.name for s in find_symbols(root)] == ["EXISTING_A", "EXISTING_B"]


@pytest.mark.parametrize("version", ALL_VERSIONS)
def test_target_lib_eol_override_switches_to_lf_only(version):
    data = target_lib(version, eol="\n")
    assert b"\r" not in data
    assert file_version(_load(data).root) == version


def test_target_lib_modern_eol_override_gives_crlf():
    data = target_lib(V8, eol="\r\n")
    assert data.count(b"\n") == data.count(b"\r\n") > 0
    assert data.count(b"\r") == data.count(b"\r\n")


def test_target_lib_rejects_an_unknown_version():
    with pytest.raises(ValueError):
        target_lib(20220914)


# -- vendor_symbol_lib ---------------------------------------------------------


def test_vendor_symbol_lib_builds_one_sub_symbol_per_unit_with_numbered_pins():
    root = _load(vendor_symbol_lib("PART", units=2, pins=(("1", "2"), ("3", "4")))).root
    [sym] = find_symbols(root)
    assert sym.name == "PART"
    subs = _sub_symbols(sym.node)
    assert [unquote(sub.children[1].text) for sub in subs] == ["PART_1_1", "PART_2_1"]
    assert [_pin_numbers(sub) for sub in subs] == [["1", "2"], ["3", "4"]]


def test_vendor_symbol_lib_numbers_default_pins_consecutively_across_units():
    root = _load(vendor_symbol_lib("PART", units=3)).root
    [sym] = find_symbols(root)
    assert [_pin_numbers(sub) for sub in _sub_symbols(sym.node)] == [["1", "2"], ["3", "4"], ["5", "6"]]


def test_vendor_symbol_lib_rejects_pins_that_do_not_match_units():
    with pytest.raises(ValueError):
        vendor_symbol_lib("PART", units=2, pins=(("1", "2"),))


def test_vendor_symbol_lib_carries_extra_properties_verbatim_after_datasheet():
    data = vendor_symbol_lib("PART", props={"MF": "Texas Instruments", "MP": "XYZ123"})
    [sym] = find_symbols(_load(data).root)
    assert _property_names(sym.node)[:6] == ["Reference", "Value", "Footprint", "Datasheet", "MF", "MP"]
    assert find_property(sym.node, "MF").value == "Texas Instruments"
    assert find_property(sym.node, "MP").value == "XYZ123"


def test_vendor_symbol_lib_sets_value_and_keywords_exactly():
    data = vendor_symbol_lib("PART_X", value="PART", keywords="PART power PARTX")
    [sym] = find_symbols(_load(data).root)
    assert sym.name == "PART_X"
    assert find_property(sym.node, "Value").value == "PART"
    assert find_property(sym.node, "ki_keywords").value == "PART power PARTX"


def test_vendor_symbol_lib_defaults_follow_the_ultra_librarian_shape():
    data = vendor_symbol_lib("PART")
    assert data.startswith(b"(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\r\n")
    assert data.count(b"\n") == data.count(b"\r\n") == data.count(b"\r")
    text = data.decode("utf-8")
    ids = [int(found) for found in re.findall(r"\(id (\d+)\)", text)]
    assert ids == list(range(len(ids))) and len(ids) >= 7
    assert "(hide yes)" not in text
    [sym] = find_symbols(_load(data).root)
    assert find_property(sym.node, "Footprint").value == "FP"
    assert find_property(sym.node, "ki_fp_filters").value == "FP"
    assert find_property(sym.node, "Datasheet").value == "https://www.ti.com/lit/gpn/part"
    assert find_property(sym.node, "ki_keywords").value == ""
    assert find_property(sym.node, "Value").value == "PART"


def test_vendor_symbol_lib_honours_version_and_eol():
    data = vendor_symbol_lib("PART", version=20220914, eol="\n")
    assert b"\r" not in data
    assert file_version(_load(data).root) == 20220914


# -- extends_pair --------------------------------------------------------------


def test_extends_pair_child_extends_parent_and_holds_no_sub_symbol():
    root = _load(extends_pair("PARENT_X", "CHILD_Y")).root
    parent, child = find_symbols(root)
    assert (parent.name, child.name) == ("PARENT_X", "CHILD_Y")
    assert [unquote(sub.children[1].text) for sub in _sub_symbols(parent.node)] == ["PARENT_X_1_1"]
    assert _pin_numbers(_sub_symbols(parent.node)[0])
    assert not any(c.head == "extends" for c in parent.node.children)
    extends = [c for c in child.node.children if c.head == "extends"]
    assert len(extends) == 1
    assert unquote(extends[0].children[1].text) == "PARENT_X"
    assert _sub_symbols(child.node) == []
    for prop in ("Reference", "Value", "Footprint", "Datasheet"):
        assert find_property(child.node, prop) is not None
    assert find_property(child.node, "Value").value == "CHILD_Y"


def test_extends_pair_child_first_puts_the_child_before_its_parent():
    root = _load(extends_pair("PARENT_X", "CHILD_Y", child_first=True)).root
    assert [s.name for s in find_symbols(root)] == ["CHILD_Y", "PARENT_X"]


def test_extends_pair_uses_the_version_and_eol_it_is_given():
    data = extends_pair(version=20220914, eol="\n")
    assert b"\r" not in data
    assert file_version(_load(data).root) == 20220914


# -- vendor_footprint ----------------------------------------------------------


def test_vendor_footprint_default_has_value_atom_and_numbered_pads():
    data = vendor_footprint("FP", pads=("1", "2"))
    assert data.startswith(b'(footprint "FP" (version 20211014) (generator pcbnew)\r\n')
    footprint = _footprint_node(data)
    values = [c for c in footprint.children if c.head == "fp_text" and c.children[1].text == "value"]
    assert len(values) == 1
    assert values[0].children[2].kind == "atom"
    assert values[0].children[2].text == "FP"
    assert _pad_numbers(footprint) == ["1", "2"]
    assert find_models(footprint) == []
    assert not any(c.head in ("property", "embedded_files") for c in footprint.children)


def test_vendor_footprint_property_form_replaces_the_fp_text_value():
    footprint = _footprint_node(vendor_footprint("FP", value_form="property"))
    assert not any(c.head == "fp_text" and c.children[1].text == "value" for c in footprint.children)
    [prop] = [c for c in footprint.children if c.head == "property"]
    assert unquote(prop.children[1].text) == "Value"
    assert prop.children[2].kind == "str"
    assert unquote(prop.children[2].text) == "FP"
    assert any(c.head == "fp_text" and c.children[1].text == "reference" for c in footprint.children)


def test_vendor_footprint_rejects_an_unknown_value_form():
    with pytest.raises(ValueError):
        vendor_footprint("FP", value_form="label")


def test_vendor_footprint_model_carries_a_non_zero_offset():
    footprint = _footprint_node(vendor_footprint("FP", model="${KIPRJMOD}/x.step"))
    [ref] = find_models(footprint)
    assert ref.path == "${KIPRJMOD}/x.step"
    assert _xyz(ref.node, "offset") == ["0", "0", "1"]
    assert _xyz(ref.node, "scale") == ["1", "1", "1"]
    assert _xyz(ref.node, "rotate") == ["0", "0", "0"]


def test_vendor_footprint_models_carries_one_block_per_path():
    footprint = _footprint_node(vendor_footprint("FP", models=("a.step", "b.step")))
    refs = find_models(footprint)
    assert [ref.path for ref in refs] == ["a.step", "b.step"]
    assert all(_xyz(ref.node, "offset") == ["0", "0", "1"] for ref in refs)


def test_vendor_footprint_npth_adds_a_pad_with_an_empty_number():
    footprint = _footprint_node(vendor_footprint("FP", pads=("1", "2", "3"), npth=True))
    assert _pad_numbers(footprint) == ["1", "2", "3", ""]
    assert _pads(footprint)[-1].children[2].text == "np_thru_hole"


def test_vendor_footprint_embedded_adds_an_embedded_files_child():
    assert any(c.head == "embedded_files" for c in _footprint_node(vendor_footprint("FP", embedded=True)).children)
    assert not any(c.head == "embedded_files" for c in _footprint_node(vendor_footprint("FP")).children)


def test_vendor_footprint_uses_crlf_by_default_and_honours_eol():
    data = vendor_footprint("FP")
    assert data.count(b"\r\n") > 5
    assert data.count(b"\n") == data.count(b"\r\n") == data.count(b"\r")
    assert b"\r" not in vendor_footprint("FP", eol="\n")
    assert file_version(_load(vendor_footprint("FP", version=20240108)).root) == 20240108


def test_vendor_footprint_quotes_a_name_that_is_not_a_bare_atom():
    footprint = _footprint_node(vendor_footprint("QFN 16"))
    [value] = [c for c in footprint.children if c.head == "fp_text" and c.children[1].text == "value"]
    assert unquote(value.children[2].text) == "QFN 16"


# -- all builders --------------------------------------------------------------


def test_every_builder_returns_bytes_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outputs = [
        target_lib(V6),
        target_lib(V8),
        target_lib(V9),
        vendor_symbol_lib(),
        extends_pair(),
        vendor_footprint(),
        vendor_footprint(model="x.step", npth=True, embedded=True, value_form="property"),
    ]
    assert all(isinstance(data, bytes) and data for data in outputs)
    assert list(tmp_path.iterdir()) == []
