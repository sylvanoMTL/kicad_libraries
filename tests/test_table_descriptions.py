"""Library description rules (TBL-01, D-20) and the stock-table reader."""

from kicad_lib_manager import table_generator as tg


def test_atomic_library_takes_kicad_description():
    assert tg.library_description(
        "Atomic_Transistor_FET",
        "Custom/Symbols/Atomic_Transistor_FET.kicad_sym",
        {"Transistor_FET": "FET transistor symbols"},
    ) == "Atomic parts: FET transistor symbols"


def test_atomic_library_without_stock_uses_stem_words():
    assert tg.library_description(
        "Atomic_Transistor_FET",
        "Custom/Symbols/Atomic_Transistor_FET.kicad_sym",
        {},
    ) == "Atomic parts: Transistor FET"


def test_atomic_footprints_description():
    assert tg.ATOMIC_FOOTPRINTS_DESCRIPTION == "Atomic part footprints (own and vendor)"
    assert tg.library_description(
        "Atomic_Footprints", "Custom/Footprints/Atomic_Footprints.pretty", {},
    ) == tg.ATOMIC_FOOTPRINTS_DESCRIPTION


def test_other_library_uses_source_and_spaced_nickname():
    assert tg.library_description(
        "IC_LDO_TI", "Custom/Symbols/IC_LDO_TI.kicad_sym", {},
    ) == "Custom: IC LDO TI"
    assert tg.library_description(
        "WE_LED", "WurthElektronik/KiCad-Library/Symbols/WE_LED.kicad_sym", {},
    ) == "WurthElektronik: WE LED"


def test_stock_descriptions_reads_template_table(tmp_path):
    table = tmp_path / "sym-lib-table"
    table.write_text(
        "(sym_lib_table\n"
        '  (lib (name "Connector")(type "KiCad")(uri "x")(options "")'
        '(descr "Connector symbols (Examples: USB)"))\n'
        '  (lib (name "Empty")(type "KiCad")(uri "y")(options "")(descr ""))\n'
        '  (lib (name "Colon")(type "KiCad")(uri "z")(options "")(descr "A: B"))\n'
        ")\n",
        encoding="utf-8",
    )

    assert tg.stock_descriptions(table) == {
        "Connector": "Connector symbols (Examples: USB)",
        "Colon": "A: B",
    }
    assert tg.stock_descriptions(None) == {}
    assert tg.stock_descriptions(tmp_path / "missing") == {}

    unreadable = tmp_path / "bad"
    unreadable.write_bytes(b"\xff\xfe not valid utf-8 \x00")
    assert tg.stock_descriptions(unreadable) == {}

    no_table = tmp_path / "no-table"
    no_table.write_text("(something_else)\n", encoding="utf-8")
    assert tg.stock_descriptions(no_table) == {}
