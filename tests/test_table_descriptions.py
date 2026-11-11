"""Library description rules (TBL-01, D-20) and the stock-table reader."""

from kicad_lib_manager import kicad_files
from kicad_lib_manager import table_generator as tg
from kicad_lib_manager.models import Issue, Severity, SymbolLibrary


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


# -- Task 2: kept descriptions, the add-only entry and the table templates (D-20) ------------


def test_existing_description_is_kept(tmp_path):
    path = tmp_path / "sym-lib-table"
    path.write_bytes(
        b"(sym_lib_table\n"
        b"  (version 7)\n"
        b'  (lib (name "Atomic_Connector")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Atomic_Connector.kicad_sym")'
        b'(options "")(descr "My connectors"))\n'
        b'  (lib (name "Other")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Other.kicad_sym")'
        b'(options "")(descr ""))\n'
        b")\n"
    )
    libs = [
        SymbolLibrary(
            "Atomic_Connector", "Custom/Symbols/Atomic_Connector.kicad_sym", "Custom",
            selected=True,
        ),
        SymbolLibrary("Other", "Custom/Symbols/Other.kicad_sym", "Custom", selected=True),
    ]

    tg.write_tables(tmp_path, libs, [])

    text = path.read_text(encoding="utf-8")
    assert '(descr "My connectors")' in text
    assert '(name "Other")' in text
    assert '(descr "Custom: Other")' in text


def test_external_entries_untouched(tmp_path):
    external_table = (
        '(lib (name "KiCad")(type "Table")'
        '(uri "C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table")'
        '(options "")(descr "KiCad Default Libraries"))'
    )
    external_hand = '(lib (name "Hand")(type "KiCad")(uri "C:/ext/Hand.kicad_sym")(options "")(descr ""))'
    path = tmp_path / "sym-lib-table"
    path.write_text(
        "(sym_lib_table\n"
        "  (version 7)\n"
        f"  {external_table}\n"
        f"  {external_hand}\n"
        ")\n",
        encoding="utf-8",
    )
    libs = [SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom", selected=True)]

    tg.write_tables(tmp_path, libs, [])

    text = path.read_text(encoding="utf-8")
    assert external_table in text
    assert external_hand in text


def test_add_only_entry_is_described(tmp_path):
    issues = tg.add_library_entries(
        tmp_path,
        symbol=("Atomic_Transistor_FET", "Custom/Symbols/Atomic_Transistor_FET.kicad_sym"),
        footprint=("Atomic_Footprints", "Custom/Footprints/Atomic_Footprints.pretty"),
        repo_root=tmp_path,
        stock={"Transistor_FET": "FET transistor symbols"},
    )

    sym_text = (tmp_path / "sym-lib-table").read_text(encoding="utf-8")
    fp_text = (tmp_path / "fp-lib-table").read_text(encoding="utf-8")
    assert '(descr "Atomic parts: FET transistor symbols")' in sym_text
    assert '(descr "Atomic part footprints (own and vendor)")' in fp_text
    assert not [i for i in issues if i.severity is Severity.ERROR]


def test_repoint_keeps_description(tmp_path):
    original = (
        b"(sym_lib_table\n"
        b"  (version 7)\n"
        b'  (lib (name "Atomic_Transistor_FET")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Gone.kicad_sym")(options "")(descr "Old text"))\n'
        b")\n"
    )
    (tmp_path / "sym-lib-table").write_bytes(original)

    tg.add_library_entries(
        tmp_path,
        symbol=("Atomic_Transistor_FET", "Custom/Symbols/Atomic_Transistor_FET.kicad_sym"),
        repo_root=tmp_path,
    )

    text = (tmp_path / "sym-lib-table").read_bytes()
    assert text == original.replace(b"Gone.kicad_sym", b"Atomic_Transistor_FET.kicad_sym")
    assert b'(descr "Old text")' in text


def test_descriptions_are_quoted(tmp_path):
    stock = {"Transistor_FET": 'Weird "quoted" text \\ backslash'}
    libs = [
        SymbolLibrary(
            "Atomic_Transistor_FET", "Custom/Symbols/Atomic_Transistor_FET.kicad_sym", "Custom",
            selected=True,
        ),
    ]

    tg.write_tables(tmp_path, libs, [], stock=stock)

    loaded = kicad_files.load(tmp_path / "sym-lib-table")
    assert not isinstance(loaded, Issue)
    table = kicad_files.lib_table(loaded.root)
    (entry,) = table.entries
    assert entry.descr == 'Atomic parts: Weird "quoted" text \\ backslash'
