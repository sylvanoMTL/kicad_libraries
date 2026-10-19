"""Byte builders for the Phase 4 install tests (INST-02, INST-05, INST-06, POST-04).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so
pytest does not collect it. Test modules import it with ``from installfixtures
import ...``, like ``zipfixtures``. The rule: builders return bytes, write nothing,
take no paths, and import only the standard library and ``zipfixtures._quote``.

Two house styles are reproduced from the real Custom/ headers:

* 20211014 (KiCad 6): optional leading blank line, a one-line header, two-space
  indent, ``(id N)`` on every property and a bare ``hide`` atom inside ``(effects``.
* 20231120 / 20241209 (KiCad 8 / 9): one header child per tab-indented line, no ids,
  ``(hide yes)`` inside ``(effects`` and a Description property.
"""

from zipfixtures import _quote

V6_VERSION = 20211014
_MODERN_GENERATOR_VERSIONS = {20231120: "8.0", 20241209: "9.0"}
_EFFECTS = "(effects (font (size 1.27 1.27))"


# -- KiCad 6 style (two-space indent, ids, bare hide) --------------------------


def _v6_property(indent: str, index: int, name: str, value: str, *, hide: bool, at: str = "0 0 0") -> list[str]:
    """Return the lines of one 20211014-style property, id numbered index."""
    flag = " hide" if hide else ""
    return [
        f"{indent}(property {_quote(name)} {_quote(value)} (id {index}) (at {at})",
        f"{indent}  {_EFFECTS}{flag})",
        f"{indent})",
    ]


def _v6_pin(indent: str, number: str, *, x: str, y: str, angle: str, name: str = "~") -> list[str]:
    """Return the lines of one passive pin in the form KiCad 6 writes."""
    return [
        f"{indent}(pin passive line (at {x} {y} {angle}) (length 2.54)",
        f"{indent}  (name {_quote(name)} (effects (font (size 1.27 1.27))))",
        f"{indent}  (number {_quote(number)} (effects (font (size 1.27 1.27))))",
        f"{indent})",
    ]


def _v6_pin_pair(indent: str, first: str, second: str) -> list[str]:
    """Return a left and a right pin carrying the given numbers."""
    return (
        _v6_pin(indent, first, x="-5.08", y="0", angle="0")
        + _v6_pin(indent, second, x="5.08", y="0", angle="180")
    )


# -- KiCad 8 / 9 style (tab indent, no ids, hide yes) --------------------------


def _tree(node: tuple, level: int = 0) -> list[str]:
    """Render a (head, atom..., (child)...) tuple the way KiCad 8 and later write it.

    Atoms (already quoted strings) stay on the head line; list children each get
    their own line one tab deeper, and a list with children closes on its own line.
    """
    head, *rest = node
    atoms = [item for item in rest if isinstance(item, str)]
    children = [item for item in rest if not isinstance(item, str)]
    pad = "\t" * level
    line = pad + "(" + " ".join([head, *atoms])
    if not children:
        return [line + ")"]
    lines = [line]
    for child in children:
        lines.extend(_tree(child, level + 1))
    lines.append(pad + ")")
    return lines


def _modern_effects(*, hide: bool) -> tuple:
    effects = ("effects", ("font", ("size", "1.27 1.27")))
    return effects + (("hide", "yes"),) if hide else effects


def _modern_property(name: str, value: str, *, hide: bool) -> tuple:
    return ("property", _quote(name), _quote(value), ("at", "0 0 0"), _modern_effects(hide=hide))


def _modern_pin(number: str, *, x: str, angle: str) -> tuple:
    return (
        "pin", "passive", "line",
        ("at", f"{x} 0 {angle}"),
        ("length", "2.54"),
        ("name", _quote("~"), _modern_effects(hide=False)),
        ("number", _quote(number), _modern_effects(hide=False)),
    )


def _modern_symbol(name: str) -> tuple:
    return (
        "symbol", _quote(name),
        ("exclude_from_sim", "no"),
        ("in_bom", "yes"),
        ("on_board", "yes"),
        _modern_property("Reference", "U", hide=False),
        _modern_property("Value", name, hide=False),
        _modern_property("Footprint", "", hide=True),
        _modern_property("Datasheet", "", hide=True),
        _modern_property("Description", "", hide=True),
        (
            "symbol", _quote(f"{name}_1_1"),
            _modern_pin("1", x="-5.08", angle="0"),
            _modern_pin("2", x="5.08", angle="180"),
        ),
    )


# -- target library builder ----------------------------------------------------


def target_lib(
    version: int,
    names: tuple[str, ...] = ("EXISTING_A", "EXISTING_B"),
    *,
    eol: str | None = None,
) -> bytes:
    """Build a Custom/ target .kicad_sym in the house style of the given format version.

    Every symbol has Reference "U", Value = its name, empty Footprint and Datasheet, and one
    sub-symbol <name>_1_1 with pins "1" and "2". eol defaults to CRLF for 20211014 and LF
    for the tab-indented versions; any other version raises ValueError.
    """
    if version == V6_VERSION:
        newline = "\r\n" if eol is None else eol
        lines = [
            "",
            f"(kicad_symbol_lib (version {version}) (generator kicad_symbol_editor)",
        ]
        for name in names:
            lines.append(f"  (symbol {_quote(name)} (in_bom yes) (on_board yes)")
            lines.extend(_v6_property("    ", 0, "Reference", "U", hide=False))
            lines.extend(_v6_property("    ", 1, "Value", name, hide=False))
            lines.extend(_v6_property("    ", 2, "Footprint", "", hide=True))
            lines.extend(_v6_property("    ", 3, "Datasheet", "", hide=True))
            lines.append(f"    (symbol {_quote(f'{name}_1_1')}")
            lines.extend(_v6_pin_pair("      ", "1", "2"))
            lines.append("    )")
            lines.append("  )")
        lines.append(")")
        return (newline.join(lines) + newline).encode("utf-8")
    if version in _MODERN_GENERATOR_VERSIONS:
        newline = "\n" if eol is None else eol
        library = (
            "kicad_symbol_lib",
            ("version", str(version)),
            ("generator", _quote("kicad_symbol_editor")),
            ("generator_version", _quote(_MODERN_GENERATOR_VERSIONS[version])),
            *(_modern_symbol(name) for name in names),
        )
        return (newline.join(_tree(library)) + newline).encode("utf-8")
    raise ValueError(f"no target library style for format version {version}")


# -- vendor builders -----------------------------------------------------------


def vendor_symbol_lib(
    name: str = "PART",
    *,
    version: int = V6_VERSION,
    units: int = 1,
    pins: tuple[tuple[str, ...], ...] | None = None,
    value: str | None = None,
    keywords: str = "",
    footprint_field: str = "FP",
    fp_filters: str = "FP",
    datasheet: str = "https://www.ti.com/lit/gpn/part",
    props: dict[str, str] | None = None,
    eol: str = "\r\n",
) -> bytes:
    """Build a vendor .kicad_sym holding one symbol in the Ultra Librarian shape."""
    return b""


def extends_pair(
    parent: str = "PARENT_X",
    child: str = "CHILD_Y",
    *,
    version: int = V6_VERSION,
    child_first: bool = False,
    eol: str = "\r\n",
) -> bytes:
    """Build a .kicad_sym holding a parent symbol and a child that (extends "<parent>")."""
    return b""


def vendor_footprint(
    name: str = "FP",
    *,
    version: int = V6_VERSION,
    pads: tuple[str, ...] = ("1", "2"),
    value_form: str = "fp_text",
    model: str | None = None,
    models: tuple[str, ...] = (),
    npth: bool = False,
    embedded: bool = False,
    eol: str = "\r\n",
) -> bytes:
    """Build a vendor .kicad_mod in the Ultra Librarian shape."""
    return b""
