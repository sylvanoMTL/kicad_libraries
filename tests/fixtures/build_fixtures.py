"""Regenerate the frozen S-expression and lib-table fixtures, byte-exactly.

Run from the repo root:  python tests/fixtures/build_fixtures.py

The fixtures carry EOL, BOM and whitespace traits that editors and git can
silently normalise, so they are never hand-edited: this script is the single
source of truth. Every fixture is original synthetic text (nothing is copied
from the Custom/ libraries). tests/test_fixtures.py compares the committed
bytes on disk to FIXTURES and checks the trait each name claims.

The source of this file holds no literal CR or TAB character; both are
produced through escapes or chr(9) so the file itself survives normalisation.
"""

from pathlib import Path

LF = "\n"
CRLF = "\r\n"
TAB = chr(9)
BOM = b"\xef\xbb\xbf"

FIXTURES_DIR = Path(__file__).resolve().parent


def _tabs(block: str) -> list[str]:
    """Turn a block indented with two spaces per level into TAB-indented lines."""
    lines = []
    for line in block.strip("\n").split("\n"):
        stripped = line.lstrip(" ")
        depth = (len(line) - len(stripped)) // 2
        lines.append(TAB * depth + stripped)
    return lines


def _join(lines: list[str], eol: str, final_eol: bool = True) -> bytes:
    text = eol.join(lines) + (eol if final_eol else "")
    return text.encode("utf-8")


def _mixed(lines: list[str]) -> bytes:
    """CRLF on the first two thirds of the lines, LF on the rest (CRLF majority)."""
    cut = (2 * len(lines)) // 3
    text = "".join(
        line + (CRLF if i < cut else LF) for i, line in enumerate(lines)
    )
    return text.encode("utf-8")


def _prop(depth: int, name: str, value_text: str, y: str = "0", hide: bool = False) -> str:
    """One symbol property block; value_text is the exact file text between the quotes."""
    pad = "  " * depth
    out = [
        f'{pad}(property "{name}" "{value_text}"',
        f"{pad}  (at 0 {y} 0)",
        f"{pad}  (effects",
        f"{pad}    (font",
        f"{pad}      (size 1.27 1.27)",
        f"{pad}    )",
    ]
    if hide:
        out.append(f"{pad}    (hide yes)")
    out.append(f"{pad}  )")
    out.append(f"{pad})")
    return "\n".join(out)


def _sym_lines() -> list[str]:
    block = "\n".join([
        "(kicad_symbol_lib",
        "  (version 20241209)",
        '  (generator "kicad_symbol_editor")',
        '  (generator_version "9.0")',
        '  (symbol "FIX_R"',
        "    (exclude_from_sim no)",
        "    (in_bom yes)",
        "    (on_board yes)",
        _prop(2, "Reference", "R", "2.54"),
        _prop(2, "Value", "FIX_R", "-2.54"),
        _prop(2, "Footprint", "Fixture_Lib:FIX_FP", "5.08", hide=True),
        _prop(2, "Datasheet", "", "7.62", hide=True),
        '    (symbol "FIX_R_0_1"',
        "      (rectangle",
        "        (start -1.016 -2.54)",
        "        (end 1.016 2.54)",
        "        (stroke",
        "          (width 0.254)",
        "          (type default)",
        "        )",
        "        (fill",
        "          (type none)",
        "        )",
        "      )",
        "    )",
        '    (symbol "FIX_R_1_1"',
        "      (pin passive line",
        "        (at 0 3.81 270)",
        "        (length 1.27)",
        '        (name "~"',
        "          (effects",
        "            (font",
        "              (size 1.27 1.27)",
        "            )",
        "          )",
        "        )",
        '        (number "1"',
        "          (effects",
        "            (font",
        "              (size 1.27 1.27)",
        "            )",
        "          )",
        "        )",
        "      )",
        "    )",
        "  )",
        '  (symbol "FIX_U"',
        "    (exclude_from_sim no)",
        "    (in_bom yes)",
        "    (on_board yes)",
        _prop(2, "Reference", "U", "2.54"),
        _prop(2, "Value", "FIX_U", "-2.54"),
        _prop(2, "Footprint", "Fixture_Lib:FIX_FP2", "5.08", hide=True),
        "  )",
        ")",
    ])
    return _tabs(block)


def _escapes_lines() -> list[str]:
    # Raw strings keep the KiCad backslash escapes literal in the file text
    props = [
        _prop(2, "Reference", "U", "2.54"),
        _prop(2, "Value", "R (0.1%)", "-2.54"),
        _prop(2, "Description", r"say \"hi\" (twice)", "5.08"),
        _prop(2, "Datasheet", r"C:\\docs\\a.pdf", "7.62"),
        _prop(2, "Note", r"line1\nline2", "10.16"),
        _prop(2, "Tabbed", "tab" + TAB + "here", "12.7"),
        _prop(2, "Unit", "10k\u03a9", "15.24"),
        _prop(2, "Footprint", "Fixture_Lib:FIX_ESC_FP", "17.78", hide=True),
    ]
    block = "\n".join([
        "(kicad_symbol_lib",
        "  (version 20241209)",
        '  (generator "kicad_symbol_editor")',
        '  (generator_version "9.0")',
        '  (symbol "FIX_ESC"',
        "    (exclude_from_sim no)",
        "    (in_bom yes)",
        "    (on_board yes)",
        *props,
        "  )",
        ")",
    ])
    return _tabs(block)


_EFFECTS = "(effects (font (size 1 1) (thickness 0.15)))"

BARE_ATOMS_LINES = [
    "(footprint \"FIX_BARE\" (version 20211014) (generator pcbnew)",
    '  (layer "F.Cu")',
    "  (attr smd)",
    "  (fp_text reference \"REF**\" (at 0 0 unlocked) (layer F.SilkS)",
    f"    {_EFFECTS}",
    "  )",
    "  (fp_text value FIX_BARE (at 0 1 unlocked) (layer F.Fab)",
    f"    {_EFFECTS}",
    "  )",
    '  (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu" "F.Paste" "F.Mask"))',
    ")",
]

TWO_MODELS_LINES = [
    '(footprint "FIX_TWO_MODELS" (version 20240108) (generator "pcbnew")',
    '  (layer "F.Cu")',
    '  (property "Reference" "REF**" (at 0 -2 0) (layer "F.SilkS")',
    f"    {_EFFECTS}",
    "  )",
    '  (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu" "F.Paste" "F.Mask"))',
    '  (model "${CUSTOM_3DMODEL_DIR}/FIX_A.step"',
    "    (offset (xyz 0 0 0))",
    "    (scale (xyz 1 1 1))",
    "    (rotate (xyz 0 0 0))",
    "  )",
    '  (model "${CUSTOM_3DMODEL_DIR}/FIX_B.stp"',
    "    (offset (xyz 0 0 0.5))",
    "    (scale (xyz 1 1 1))",
    "    (rotate (xyz 0 0 90))",
    "  )",
    ")",
]

LEGACY_MODULE_LINES = [
    "(module FIX_LEGACY (layer F.Cu) (tedit 5A0B1C2D)",
    "  (fp_text reference REF** (at 0 0) (layer F.SilkS)",
    f"    {_EFFECTS}",
    "  )",
    "  (fp_text value FIX_LEGACY (at 0 1) (layer F.Fab)",
    f"    {_EFFECTS}",
    "  )",
    "  (pad 1 smd rect (at 0 0) (size 1 1) (layers F.Cu F.Paste F.Mask))",
    "  (model ${KIPRJMOD}/3d/FIX_LEGACY.wrl",
    "    (at (xyz 0 0 0))",
    "    (scale (xyz 1 1 1))",
    "    (rotate (xyz 0 0 0))",
    "  )",
    ")",
]

NO_TRAILING_NEWLINE_LINES = [
    '(footprint "FIX_NO_EOL"',
    '  (layer "F.Cu")',
    '  (model "${CUSTOM_3DMODEL_DIR}/FIX_NO_EOL.step")',
    ")",
]


def _entry(
    name: str,
    uri: str,
    *,
    options: str | None = "",
    descr: str | None = "",
    extra: str = "",
) -> str:
    """A KiCad-style lib entry: sub-forms packed with no whitespace between them."""
    text = f'  (lib (name "{name}")(type "KiCad")(uri "{uri}")'
    if options is not None:
        text += f'(options "{options}")'
    if descr is not None:
        text += f'(descr "{descr}")'
    return text + extra + ")"


_GH = "${KICAD_LIB_GITHUB}"

BASIC_SYM_TABLE = [
    "(sym_lib_table",
    "  (version 7)",
    _entry("Fixture_A", f"{_GH}/Custom/Symbols/Fixture_A.kicad_sym"),
    _entry("Fixture_B", f"{_GH}/Custom/Symbols/Fixture_B.kicad_sym", descr="Second fixture"),
    ")",
]

ESCAPED_SYM_TABLE = [
    "(sym_lib_table",
    "  (version 7)",
    _entry(
        "Escaped_Lib",
        r"C:\\KiCad\\libs\\Escaped.kicad_sym",
        descr=r"Has \"quotes\" and (parens)",
    ),
    ")",
]

EMPTY_SYM_TABLE = [
    "(sym_lib_table",
    "  (version 7)",
    ")",
]

# Sub-forms deliberately out of order, with odd whitespace between them (D-02):
# one space, three spaces, one TAB, a line break plus six spaces, two spaces.
_REORDERED_ENTRY = (
    "  (lib "
    f'(uri "{_GH}/Custom/Footprints/Reordered.pretty")'
    "   "
    '(type "KiCad")'
    + TAB
    + '(name "Reordered")'
    + LF
    + "      "
    '(descr "fields out of order")'
    "  "
    '(options ""))'
)

REORDERED_FP_TABLE = [
    "(fp_lib_table",
    "  (version 7)",
    _REORDERED_ENTRY,
    '  (lib (name "Minimal")(type "KiCad")(uri "/abs/path/Minimal.pretty"))',
    ")",
]

FLAGS_FP_TABLE = [
    "(fp_lib_table",
    "  (version 7)",
    _entry("Disabled_Lib", f"{_GH}/Custom/Footprints/Disabled_Lib.pretty", extra="(disabled)"),
    _entry("Hidden_Lib", f"{_GH}/Custom/Footprints/Hidden_Lib.pretty", extra="(hidden)"),
    _entry("Future_Lib", f"{_GH}/Custom/Footprints/Future_Lib.pretty", extra='(future_field "x")'),
    ")",
]


def _build() -> dict[str, bytes]:
    sym = _sym_lines()
    sym_lf = _join(sym, LF)
    return {
        "sexpr/lf.kicad_sym": sym_lf,
        "sexpr/crlf.kicad_sym": _join(sym, CRLF),
        "sexpr/bom.kicad_sym": BOM + sym_lf,
        "sexpr/mixed_eol.kicad_sym": _mixed(sym),
        "sexpr/escapes.kicad_sym": _join(_escapes_lines(), LF),
        "sexpr/bare_atoms.kicad_mod": _join(BARE_ATOMS_LINES, LF),
        "sexpr/two_models.kicad_mod": _join(TWO_MODELS_LINES, CRLF),
        "sexpr/legacy_module.kicad_mod": _join(LEGACY_MODULE_LINES, LF),
        "sexpr/no_trailing_newline.kicad_mod": _join(NO_TRAILING_NEWLINE_LINES, LF, final_eol=False),
        "tables/basic.sym-lib-table": _join(BASIC_SYM_TABLE, LF),
        "tables/escaped.sym-lib-table": _join(ESCAPED_SYM_TABLE, CRLF),
        "tables/empty.sym-lib-table": _join(EMPTY_SYM_TABLE, LF),
        "tables/reordered.fp-lib-table": _join(REORDERED_FP_TABLE, LF),
        "tables/flags.fp-lib-table": _join(FLAGS_FP_TABLE, CRLF),
    }


# Relative POSIX path (under tests/fixtures) -> exact file bytes
FIXTURES: dict[str, bytes] = _build()


def main() -> None:
    for key, data in FIXTURES.items():
        rel = Path(key)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"refusing fixture key outside tests/fixtures: {key}")
        target = FIXTURES_DIR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"wrote {key} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
