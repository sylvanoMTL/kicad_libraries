"""Self-tests that keep the Phase 4 install byte builders honest (INST-02, INST-05, INST-06, POST-04)."""

import re

import pytest

from kicad_lib_manager.kicad_files import (
    LoadedFile,
    file_version,
    find_property,
    find_symbols,
    parse_bytes,
)
from kicad_lib_manager.sexpr import Node, unquote
from installfixtures import target_lib

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
