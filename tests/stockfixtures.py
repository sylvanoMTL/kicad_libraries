"""A small synthetic stand-in for KiCad's installed symbols and footprints folders (no unit test needs the real install).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so pytest does not
collect it. ``write_stock_kicad`` writes only under the root it is given. Symbols come from the
``customfixtures`` builders (KiCad 10 tab style, each with a NAME_1_1 unit sub-symbol, so a naive
count of ``(symbol "`` text would overcount exactly as it does on the real stock libraries).
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from customfixtures import atomic_lib, atomic_part

# One footprint row: (name, pad numbers, descr, tags); descr and tags are written only when non-empty
FootprintRow = tuple[str, tuple[str, ...], str, str]
_PAD_PITCH_MM = 0.65


def _pad_line(number: str, index: int) -> str:
    x = f"{index * _PAD_PITCH_MM:.2f}"
    return (
        f'\t(pad "{number}" smd rect (at {x} 0) (size 0.4 0.8) (layers "F.Cu" "F.Mask" "F.Paste"))'
    )


def stock_footprint(name: str, pads: Sequence[str], descr: str = "", tags: str = "") -> bytes:
    """Build a minimal KiCad 10 footprint with one smd pad per number, spaced 0.65 mm apart."""
    lines = [f'(footprint "{name}"', "\t(version 20260206)", '\t(generator "pcbnew")', '\t(layer "F.Cu")']
    if descr:
        lines.append(f'\t(descr "{descr}")')
    if tags:
        lines.append(f'\t(tags "{tags}")')
    lines.extend(_pad_line(number, index) for index, number in enumerate(pads))
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_stock_kicad(
    root: Path,
    symbols: Mapping[str, Sequence[tuple[str, str]]],
    footprints: Mapping[str, Sequence[FootprintRow]] | None = None,
) -> tuple[Path, Path]:
    """Write root/kicad/symbols and root/kicad/footprints; return (symbols dir, footprints dir).

    symbols maps a library stem to (symbol name, Footprint field) pairs. footprints maps a
    library name to (footprint name, pad numbers, descr, tags) rows.
    """
    symbols_dir = root / "kicad" / "symbols"
    footprints_dir = root / "kicad" / "footprints"
    symbols_dir.mkdir(parents=True, exist_ok=True)
    footprints_dir.mkdir(parents=True, exist_ok=True)
    for stem, entries in symbols.items():
        parts = tuple(atomic_part(name, replace={"Footprint": link}) for name, link in entries)
        (symbols_dir / f"{stem}.kicad_sym").write_bytes(atomic_lib(parts))
    for library, rows in (footprints or {}).items():
        pretty = footprints_dir / f"{library}.pretty"
        pretty.mkdir(parents=True, exist_ok=True)
        for name, pads, descr, tags in rows:
            (pretty / f"{name}.kicad_mod").write_bytes(stock_footprint(name, pads, descr, tags))
    return symbols_dir, footprints_dir


# The standard sample: the CSD family is split across Transistor_FET (3), Diode (1) and power (1,
# which never votes); USB parts span Connector, Interface_USB and Power_Protection.
STOCK_SAMPLE_SYMBOLS: dict[str, tuple[tuple[str, str], ...]] = {
    "Transistor_FET": (
        ("CSD16301Q2", "Package_SON:Texas_DQK"),
        ("CSD17313Q2", "Package_SON:Texas_DQK"),
        ("CSD18531Q5A", "Package_TO_SOT_SMD:TDSON-8-1"),
    ),
    "Diode": (("CSD01060A", ""),),
    "power": (("CSDPWR", ""),),
    "Connector": (("USB4105-GF-A", ""), ("USB4110-GF-A", ""), ("USB4085-GF-A", "")),
    "Interface_USB": (("USB2514B", ""),),
    "Power_Protection": (("USBLC6-2SC6", ""),),
    "Amplifier_Operational": (("MAX4238", ""),),
    "Analog_Switch": (("MAX4544", ""),),
    "Interface_UART": (("MAX4800", ""),),
    "Converter_DCDC": (("R-78E5.0-0.5", ""),),
}
STOCK_SAMPLE_FOOTPRINTS: dict[str, tuple[FootprintRow, ...]] = {
    "Package_SON": (
        (
            "Texas_DQK",
            tuple(str(n) for n in range(1, 9)),
            "Texas WSON-6 DQK, 2x2mm, 0.65mm pitch",
            "Texas WSON6 2x2mm",
        ),
    ),
    "Package_SO": (("SOIC-8_3.9x4.9mm_P1.27mm", tuple(str(n) for n in range(1, 9)), "", ""),),
    "Package_TO_SOT_SMD": (("SOT-23-5", tuple(str(n) for n in range(1, 6)), "", ""),),
}


def write_stock_sample(root: Path) -> tuple[Path, Path]:
    """Write the standard stock tree under root/kicad and return (symbols dir, footprints dir)."""
    return write_stock_kicad(root, STOCK_SAMPLE_SYMBOLS, STOCK_SAMPLE_FOOTPRINTS)
