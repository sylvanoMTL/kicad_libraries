"""Synthetic vendor packages for the Phase 7 adapter tests (D-01).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so pytest
does not collect it. Test modules import it with ``from vendorfixtures import ...``,
like ``zipfixtures``. It imports the standard library and ``zipfixtures`` only.

Everything here is written from scratch. The builders copy each vendor's layout, file
names, property names and markers, never its geometry, models or licence text, because
the vendor downloads are licence-restricted and both GitHub repos are public. Every
builder returns bytes (or a list of name/bytes members), and ``snapeda_zip`` writes only
under the path the test passes (``tmp_path``).
"""

from pathlib import Path

from zipfixtures import BS, STEP_BYTES, _quote, make_zip

# -- SnapEDA ---------------------------------------------------------------------

SNAPEDA_SYMBOL = "USBC4242-01-0099-A_REVB1"
SNAPEDA_MPN = "USBC4242-01-0099-A"
SNAPEDA_FOOTPRINT = "GCT_USBC4242-01-0099-A_REVB1"
SNAPEDA_MANUFACTURER = "Global Connector Technology"
SNAPEDA_DESCRIPTION_RAW = "\n   \n      USB Type-C receptacle, 16 pins\n   \n"
SNAPEDA_DESCRIPTION = "USB Type-C receptacle, 16 pins"

_SNAPEDA_PAGE = "https://www.snapeda.com/parts/USBC4242-01-0099-A"
_HIDDEN = "(effects (font (size 1.27 1.27)) (justify bottom) hide)"
_SHOWN = "(effects (font (size 1.27 1.27)) (justify left bottom))"
_PIN_EFFECTS = "(effects (font (size 1.016 1.016)))"


def _escaped(text: str) -> str:
    """Return text as a quoted S-expression string whose line breaks are written as backslash-n escapes."""
    return _quote(text).replace("\r", BS + "r").replace("\n", BS + "n")


def snapeda_symbol(
    *,
    name: str = SNAPEDA_SYMBOL,
    footprint: str = SNAPEDA_FOOTPRINT,
    omit: tuple[str, ...] = (),
    extra: tuple[tuple[str, str], ...] = (),
) -> bytes:
    """Build a SnapEDA-style 20211014 .kicad_sym: LF text, a leading blank line, ids on every property.

    Property names and order copy the vendor's; the values are invented. Names in omit are left
    out, and extra (name, value) pairs are appended last (hidden). There is no Datasheet property.
    """
    properties = [
        ("Reference", "J"),
        ("Value", name),
        ("Footprint", f"{name}:{footprint}"),
        ("MF", SNAPEDA_MANUFACTURER),
        ("MAXIMUM_PACKAGE_HEIGHT", "3.2mm"),
        ("Package", "None"),
        ("Price", "None"),
        ("Check_prices", f"{_SNAPEDA_PAGE}/prices/"),
        ("STANDARD", "Manufacturer Recommendations"),
        ("PARTREV", "B1"),
        ("SnapEDA_Link", f"{_SNAPEDA_PAGE}/example/"),
        ("MP", SNAPEDA_MPN),
        ("Description", SNAPEDA_DESCRIPTION_RAW),
        ("MANUFACTURER", "GCT"),
        ("Availability", "In Stock"),
        ("SNAPEDA_PN", SNAPEDA_MPN),
        *extra,
    ]
    lines = [
        "",
        "(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)",
        f"  (symbol {_quote(name)} (in_bom yes) (on_board yes)",
    ]
    index = 0
    for prop_name, value in properties:
        if prop_name in omit:
            continue
        effects = _SHOWN if prop_name in ("Reference", "Value") else _HIDDEN
        lines.append(f"    (property {_quote(prop_name)} {_escaped(value)} (id {index}) (at 0 0 0)")
        lines.append(f"      {effects}")
        lines.append("    )")
        index += 1
    lines.append(f"    (symbol {_quote(name + '_0_1')}")
    lines.append("      (rectangle (start -5.08 5.08) (end 5.08 -5.08)")
    lines.append("        (stroke (width 0.254) (type default) (color 0 0 0 0))")
    lines.append("        (fill (type background))")
    lines.append("      )")
    lines.append("    )")
    lines.append(f"    (symbol {_quote(name + '_1_1')}")
    pins = (
        ("power_in", "VBUS", "1", "3.81"),
        ("bidirectional", "DN", "2", "1.27"),
        ("bidirectional", "DP", "3", "-1.27"),
        ("power_in", "GND", "4", "-3.81"),
    )
    for electrical, pin_name, number, y in pins:
        lines.append(f"      (pin {electrical} line (at -10.16 {y} 0) (length 5.08)")
        lines.append(f"        (name {_quote(pin_name)} {_PIN_EFFECTS})")
        lines.append(f"        (number {_quote(number)} {_PIN_EFFECTS})")
        lines.append("      )")
    lines.append("    )")
    lines.append("  )")
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def snapeda_footprint(name: str = SNAPEDA_FOOTPRINT, *, model: str | None = None) -> bytes:
    """Build a SnapEDA-style .kicad_mod: LF text, an unquoted name, a tedit stamp and no model unless asked.

    Pads 1 to 4 are smd; the two mounting holes are pads literally named None, as in the vendor's files.
    """
    lines = [
        f"(footprint {name} (layer F.Cu) (tedit 6ADB0C96)",
        "  (fp_text reference REF** (at 0 -4) (layer F.SilkS)",
        "    (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
        f"  (fp_text value {name} (at 0 4) (layer F.Fab)",
        "    (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
    ]
    for number, x in (("1", "-2.25"), ("2", "-0.75"), ("3", "0.75"), ("4", "2.25")):
        lines.append(f"  (pad {number} smd rect (at {x} 0) (size 0.6 1.6) (layers F.Cu F.Paste F.Mask))")
    for x in ("-4", "4"):
        lines.append(f"  (pad None np_thru_hole circle (at {x} 0) (size 0.8 0.8) (drill 0.8) (layers *.Cu *.Mask))")
    if model is not None:
        lines.append(f"  (model {_quote(model)}")
        lines.append("    (offset (xyz 0 0 0))")
        lines.append("    (scale (xyz 1 1 1))")
        lines.append("    (rotate (xyz 0 0 0))")
        lines.append("  )")
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


HOW_TO_IMPORT_HTM = (
    b"<html>\n<head>\n"
    b'<meta http-equiv="refresh" content="0; url=https://www.snapeda.com/about/import/">\n'
    b"</head>\n<body>\n"
    b'<a href="https://www.snapeda.com/about/import/">How to import this part</a>\n'
    b"</body>\n</html>\n"
)


def snapeda_members(*, how_to: bool = True, with_model: bool = False) -> list[tuple[str, bytes]]:
    """Return the members of a SnapEDA download, all at the zip root.

    The model layout (a .step beside the other files) is assumed; the vendor sample has no model.
    """
    members: list[tuple[str, bytes]] = [
        (f"{SNAPEDA_SYMBOL}.kicad_sym", snapeda_symbol()),
        (f"{SNAPEDA_FOOTPRINT}.kicad_mod", snapeda_footprint()),
    ]
    if how_to:
        members.append(("how-to-import.htm", HOW_TO_IMPORT_HTM))
    if with_model:
        members.append((f"{SNAPEDA_MPN}.step", STEP_BYTES))
    return members


def snapeda_zip(path: Path, **kwargs) -> Path:
    """Write a synthetic SnapEDA zip to path (creating its folder) and return path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return make_zip(path, snapeda_members(**kwargs))
