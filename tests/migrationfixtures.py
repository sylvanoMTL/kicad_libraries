"""The rich synthetic v1 Custom/ the migration tests build from, never the live repo's Custom/ (Phase 13, MIG-02, MIG-03).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so pytest does not
collect it. Every byte is assembled from the ``installfixtures``, ``zipfixtures`` and
``stockfixtures`` builders; this module never locates or reads the repo's own Custom/, so it
cannot point at it by accident.
"""

from pathlib import Path

from gitfixtures import GitRepos, make_superproject
from installfixtures import V10_VERSION, _modern_pin, _modern_property, _tree, _v6_pin, _v6_property, vendor_footprint
from stockfixtures import write_stock_kicad
from zipfixtures import STEP_BYTES, _quote

from customfixtures import OFFICIAL_FOOTPRINT, OFFICIAL_LIBRARY, write_fake_kicad
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.plan import PartKey
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR

# The v1 (non-Atomic_) symbol libraries of the rich fixture, sorted; Atomic_Oscillator is excluded
USB_LIBRARY = "Connector_USB_GCT"
POWER_LIBRARY = "IC_Power_Management_LTC"
FUEL_GAUGE_LIBRARY = "IC_Battery_Fuel_Gauge_ADI"
FFC_LIBRARY = "Connector_FFC_GCT"
IMU_LIBRARY = "IC_IMU_TDK"
OSCILLATOR_LIBRARY = "Oscillator_TCXO_Abracon"
WIRELESS_LIBRARY = "IC_Wireless_BLE_uBlox"
ATOMIC_OSCILLATOR = "Atomic_Oscillator"
SHARED_FOOTPRINTS = "Atomic_Footprints"

V1_LIBRARIES = (
    FFC_LIBRARY,
    USB_LIBRARY,
    FUEL_GAUGE_LIBRARY,
    IMU_LIBRARY,
    POWER_LIBRARY,
    WIRELESS_LIBRARY,
    OSCILLATOR_LIBRARY,
)

PART_NAMES = (
    "USB4056-03-A_REVA2",
    "USB4730-GF-A_REVA",
    "LTC2954-1-DFN8",
    "LTC2954-1-TSOT-23",
    "LTC2954-2-DFN8",
    "LTC2954-2-TSOT-23",
    "MAX17048G",
    "MAX17048X",
    "FFC2A32-06-T",
    "ICM-42688-P",
    "CM315D32768DZFT",
    "ATXK-H14",
    "NORA-W106-00B",
    "NORA-W106-10B",
)

BAK_FILES = (
    "Custom/Symbols/Connector_USB_GCT.bak",
    "Custom/Symbols/IC_Power_Management_LTC.bak",
)

# The two footprints no part links before the migration (D-21): one already in the shared Atomic_
# library, one in a v1 .pretty; both are expected to default to Keep once a later plan reads them.
BOARD_FEATURES = (
    "Custom/Footprints/Atomic_Footprints.pretty/USB-A-PCB.kicad_mod",
    "Custom/Footprints/Connector_USB_GCT.pretty/TESTPOINT-1.kicad_mod",
)


def _key(library: str, name: str) -> PartKey:
    return (f"Custom/Symbols/{library}.kicad_sym", name)


# A test expectation only (D-01): the live suggestion engine decides the real target per part: the
# planner never reads this table.
EXPECTED_TARGETS: dict[PartKey, str] = {
    _key(USB_LIBRARY, "USB4056-03-A_REVA2"): "Atomic_Connector",
    _key(USB_LIBRARY, "USB4730-GF-A_REVA"): "Atomic_Connector",
    _key(POWER_LIBRARY, "LTC2954-1-DFN8"): "Atomic_Power_Management",
    _key(POWER_LIBRARY, "LTC2954-1-TSOT-23"): "Atomic_Power_Management",
    _key(POWER_LIBRARY, "LTC2954-2-DFN8"): "Atomic_Power_Management",
    _key(POWER_LIBRARY, "LTC2954-2-TSOT-23"): "Atomic_Power_Management",
    _key(FUEL_GAUGE_LIBRARY, "MAX17048G"): "Atomic_Battery_Management",
    _key(FUEL_GAUGE_LIBRARY, "MAX17048X"): "Atomic_Battery_Management",
    _key(FFC_LIBRARY, "FFC2A32-06-T"): "Atomic_Connector",
    _key(IMU_LIBRARY, "ICM-42688-P"): "Atomic_Sensor_Motion",
    _key(ATOMIC_OSCILLATOR, "CM315D32768DZFT"): ATOMIC_OSCILLATOR,
    _key(OSCILLATOR_LIBRARY, "ATXK-H14"): ATOMIC_OSCILLATOR,
    _key(WIRELESS_LIBRARY, "NORA-W106-00B"): "Atomic_RF_Module",
    _key(WIRELESS_LIBRARY, "NORA-W106-10B"): "Atomic_RF_Module",
}

_GENERATOR_VERSIONS = {20231120: "8.0", 20241209: "9.0", V10_VERSION: "10.0"}


def _tab_symbol(
    name: str, props: list[tuple[str, str, bool]], *, extends: str | None = None, pins: tuple[str, ...] = ("1", "2")
) -> tuple:
    """One tab-indented (20231120 / 20241209 / 20251024-style) symbol; props is ordered (name, value, hide)."""
    body = tuple(_modern_property(key, value, hide=hide) for key, value, hide in props)
    if extends is not None:
        return ("symbol", _quote(name), ("extends", _quote(extends)), *body)
    pin_nodes = tuple(
        _modern_pin(number, x=f"{-5.08 + 10.16 * index:g}", angle=str(180 * index))
        for index, number in enumerate(pins)
    )
    return (
        "symbol", _quote(name),
        ("exclude_from_sim", "no"), ("in_bom", "yes"), ("on_board", "yes"),
        *body,
        ("symbol", _quote(f"{name}_1_1"), *pin_nodes),
    )


def _tab_lib(version: int, symbols: list[tuple], *, eol: str = "\r\n") -> bytes:
    """A tab-indented .kicad_sym at version, forced CRLF to match the live Custom/ (RESEARCH F-12)."""
    library = (
        "kicad_symbol_lib",
        ("version", str(version)),
        ("generator", _quote("kicad_symbol_editor")),
        ("generator_version", _quote(_GENERATOR_VERSIONS[version])),
        *symbols,
    )
    return (eol.join(_tree(library)) + eol).encode("utf-8")


def _id_symbol(name: str, props: list[tuple[str, str, bool]], *, pins: tuple[str, ...] = ("1", "2")) -> list[str]:
    """One two-space, id-numbered (20211014-style) symbol; props is ordered (name, value, hide)."""
    lines = [f"  (symbol {_quote(name)} (in_bom yes) (on_board yes)"]
    for index, (key, value, hide) in enumerate(props):
        lines.extend(_v6_property("    ", index, key, value, hide=hide))
    lines.append(f"    (symbol {_quote(f'{name}_1_1')}")
    for row, number in enumerate(pins):
        x = f"{-5.08 + 5.08 * row:g}"
        lines.extend(_v6_pin("      ", number, x=x, y="0", angle="0" if row == 0 else "180"))
    lines.append("    )")
    lines.append("  )")
    return lines


def _id_lib(symbols: list[list[str]], *, eol: str = "\r\n", version: int = 20211014) -> bytes:
    """A 20211014-style .kicad_sym holding every symbol block in order, forced CRLF."""
    lines = ["", f"(kicad_symbol_lib (version {version}) (generator kicad_symbol_editor)"]
    for block in symbols:
        lines.extend(block)
    lines.append(")")
    return (eol.join(lines) + eol).encode("utf-8")


def _write_v1_tree(custom_dir: Path) -> None:
    """Write every Symbols/Footprints/3DModels file of the rich v1 Custom/ under custom_dir; no .bak files.

    Shared between write_v1_custom (plain tmp_path) and make_v1_superproject's populate callback
    (a git work tree), so both fixtures hold exactly the same part, footprint and model content.
    """
    symbols_dir = custom_dir / "Symbols"
    footprints_dir = custom_dir / "Footprints"
    models_dir = custom_dir / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    # (a) USB connector: revision-suffixed names, an MPN field, no datasheet, a Description_1 leftover
    (symbols_dir / f"{USB_LIBRARY}.kicad_sym").write_bytes(
        _id_lib(
            [
                _id_symbol(
                    "USB4056-03-A_REVA2",
                    [
                        ("Reference", "U", False),
                        ("Value", "USB4056-03-A_REVA2", False),
                        ("Footprint", f"{USB_LIBRARY}:USB4056-03-A", True),
                        ("MPN", "USB4056-03-A", True),
                        ("Description_1", "USB Type-C receptacle", True),
                    ],
                ),
                _id_symbol(
                    "USB4730-GF-A_REVA",
                    [
                        ("Reference", "U", False),
                        ("Value", "USB4730-GF-A_REVA", False),
                        ("Footprint", f"{USB_LIBRARY}:USB4730-GF-A", True),
                        ("MPN", "USB4730-GF-A", True),
                    ],
                ),
            ]
        )
    )

    # (d) SnapEDA-style FFC part: MF/MP aliases, price/vendor-URL leftovers, a description with a raw newline
    (symbols_dir / f"{FFC_LIBRARY}.kicad_sym").write_bytes(
        _id_lib(
            [
                _id_symbol(
                    "FFC2A32-06-T",
                    [
                        ("Reference", "U", False),
                        ("Value", "FFC2A32-06-T", False),
                        ("Footprint", f"{FFC_LIBRARY}:FFC2A32-06-T", True),
                        ("MF", "Global Connector Technology", True),
                        ("MP", "FFC2A32-06-T", True),
                        ("Price", "0.50", True),
                        ("Check_prices", "https://www.snapeda.com/parts/FFC2A32-06-T/GCT/view-part/", True),
                        ("purchase-url", "https://www.snapeda.com/parts/FFC2A32-06-T/GCT/view-part/?ref=eda", True),
                        ("Description", "FFC/FPC connector\nvertical, 32-pin, 0.5mm pitch", True),
                    ],
                ),
            ]
        )
    )

    # (g) oscillator part in a v1 library whose footprint has no model
    (symbols_dir / f"{OSCILLATOR_LIBRARY}.kicad_sym").write_bytes(
        _id_lib(
            [
                _id_symbol(
                    "ATXK-H14",
                    [
                        ("Reference", "U", False),
                        ("Value", "ATXK-H14", False),
                        ("Footprint", f"{OSCILLATOR_LIBRARY}:ATXK-H14", True),
                        ("Datasheet", "https://abracon.com/Oscillators/ATXK-H14.pdf", True),
                    ],
                ),
            ]
        )
    )

    # (b) LTC2954-style: Values repeat in pairs, two linked footprints each shared by two parts,
    # two members with identical graphics/pins (2-pin) and two with a third pin ("differs by one pin")
    (symbols_dir / f"{POWER_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20231120,
            [
                _tab_symbol(
                    "LTC2954-1-DFN8",
                    [
                        ("Reference", "U", False),
                        ("Value", "ltc2954-1", False),
                        ("Footprint", f"{POWER_LIBRARY}:DFN-8_DDB", True),
                    ],
                    pins=("1", "2"),
                ),
                _tab_symbol(
                    "LTC2954-1-TSOT-23",
                    [
                        ("Reference", "U", False),
                        ("Value", "ltc2954-1", False),
                        ("Footprint", f"{POWER_LIBRARY}:TSOT-23_TS8", True),
                    ],
                    pins=("1", "2", "3"),
                ),
                _tab_symbol(
                    "LTC2954-2-DFN8",
                    [
                        ("Reference", "U", False),
                        ("Value", "ltc2954-2", False),
                        ("Footprint", f"{POWER_LIBRARY}:DFN-8_DDB", True),
                    ],
                    pins=("1", "2"),
                ),
                _tab_symbol(
                    "LTC2954-2-TSOT-23",
                    [
                        ("Reference", "U", False),
                        ("Value", "ltc2954-2", False),
                        ("Footprint", f"{POWER_LIBRARY}:TSOT-23_TS8", True),
                    ],
                    pins=("1", "2", "3"),
                ),
            ],
        )
    )

    # (c) fuel-gauge: two parts that carry only a Value
    (symbols_dir / f"{FUEL_GAUGE_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol("MAX17048G", [("Reference", "U", False), ("Value", "MAX17048G", False)]),
                _tab_symbol("MAX17048X", [("Reference", "U", False), ("Value", "MAX17048X", False)]),
            ],
        )
    )

    # (e) IMU part already linking the fake official footprint
    (symbols_dir / f"{IMU_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "ICM-42688-P",
                    [
                        ("Reference", "U", False),
                        ("Value", "ICM-42688-P", False),
                        ("Footprint", f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}", True),
                    ],
                ),
            ],
        )
    )

    # (f) Atomic_Oscillator: one complete part linking Atomic_Footprints:CM315
    (symbols_dir / f"{ATOMIC_OSCILLATOR}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "CM315D32768DZFT",
                    [
                        ("Reference", "U", False),
                        ("Value", "CM315D32768DZFT", False),
                        ("Footprint", f"{SHARED_FOOTPRINTS}:CM315", True),
                        ("Datasheet", "https://www.citizen.co.jp/cfd/pdf/CM315.pdf", True),
                        ("Description", "32.768kHz crystal", True),
                        ("MPN", "CM315D32768DZFT", True),
                        ("Manufacturer", "Citizen Finedevice", True),
                    ],
                ),
            ],
        )
    )

    # (h) radio-module: two parts linking one footprint with two byte-identical model blocks
    (symbols_dir / f"{WIRELESS_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            V10_VERSION,
            [
                _tab_symbol(
                    "NORA-W106-00B",
                    [
                        ("Reference", "U", False),
                        ("Value", "NORA-W106-00B", False),
                        ("Footprint", f"{WIRELESS_LIBRARY}:XCVR_NORA-W106-00B", True),
                        ("Manufacturer", "u-blox", True),
                    ],
                ),
                _tab_symbol(
                    "NORA-W106-10B",
                    [
                        ("Reference", "U", False),
                        ("Value", "NORA-W106-10B", False),
                        ("Footprint", f"{WIRELESS_LIBRARY}:XCVR_NORA-W106-00B", True),
                        ("Manufacturer", "u-blox", True),
                    ],
                ),
            ],
        )
    )

    usb_pretty = footprints_dir / f"{USB_LIBRARY}.pretty"
    usb_pretty.mkdir(parents=True, exist_ok=True)
    (usb_pretty / "USB4056-03-A.kicad_mod").write_bytes(vendor_footprint("USB4056-03-A", eol="\r\n"))
    (usb_pretty / "USB4730-GF-A.kicad_mod").write_bytes(vendor_footprint("USB4730-GF-A", eol="\r\n"))
    # Board feature (D-21): a v1 .pretty footprint no symbol links
    (usb_pretty / "TESTPOINT-1.kicad_mod").write_bytes(vendor_footprint("TESTPOINT-1", eol="\r\n"))

    power_pretty = footprints_dir / f"{POWER_LIBRARY}.pretty"
    power_pretty.mkdir(parents=True, exist_ok=True)
    (power_pretty / "DFN-8_DDB.kicad_mod").write_bytes(vendor_footprint("DFN-8_DDB", eol="\r\n"))
    (power_pretty / "TSOT-23_TS8.kicad_mod").write_bytes(vendor_footprint("TSOT-23_TS8", eol="\r\n"))

    ffc_pretty = footprints_dir / f"{FFC_LIBRARY}.pretty"
    ffc_pretty.mkdir(parents=True, exist_ok=True)
    (ffc_pretty / "FFC2A32-06-T.kicad_mod").write_bytes(vendor_footprint("FFC2A32-06-T", eol="\r\n"))

    osc_pretty = footprints_dir / f"{OSCILLATOR_LIBRARY}.pretty"
    osc_pretty.mkdir(parents=True, exist_ok=True)
    (osc_pretty / "ATXK-H14.kicad_mod").write_bytes(vendor_footprint("ATXK-H14", eol="\r\n"))  # no model block

    shared_pretty = footprints_dir / f"{SHARED_FOOTPRINTS}.pretty"
    shared_pretty.mkdir(parents=True, exist_ok=True)
    (shared_pretty / "CM315.kicad_mod").write_bytes(
        vendor_footprint("CM315", model=f"{MODEL_DIR_VAR}/CM315D32768DZFT.step", eol="\r\n")
    )
    # Board feature (D-21): already in the shared library, no symbol links it
    (shared_pretty / "USB-A-PCB.kicad_mod").write_bytes(vendor_footprint("USB-A-PCB", eol="\r\n"))

    wireless_pretty = footprints_dir / f"{WIRELESS_LIBRARY}.pretty"
    wireless_pretty.mkdir(parents=True, exist_ok=True)
    (wireless_pretty / "XCVR_NORA-W106-00B.kicad_mod").write_bytes(
        vendor_footprint(
            "XCVR_NORA-W106-00B",
            models=(f"{MODEL_DIR_VAR}/NORA-W106-00B.step", f"{MODEL_DIR_VAR}/NORA-W106-10B.step"),
            eol="\r\n",
        )
    )

    (models_dir / "CM315D32768DZFT.step").write_bytes(STEP_BYTES)
    (models_dir / "NORA-W106-00B.step").write_bytes(STEP_BYTES)
    (models_dir / "NORA-W106-10B.step").write_bytes(STEP_BYTES)


def write_v1_custom(root: Path) -> RepoLayout:
    """Write the rich v1 Custom/ (PART_NAMES, V1_LIBRARIES, BAK_FILES, BOARD_FEATURES) under root/Custom.

    Returns the layout over root; never reads or copies anything from the repo's own Custom/.
    """
    custom = root / "Custom"
    _write_v1_tree(custom)
    (custom / "Symbols" / "Connector_USB_GCT.bak").write_bytes(b"old revision, kept for reference\r\n")
    (custom / "Symbols" / "IC_Power_Management_LTC.bak").write_bytes(b"old revision, kept for reference\r\n")
    return RepoLayout.for_repo(root)


def write_v1_stock(root: Path) -> tuple[Path, Path]:
    """Write a KiCad stand-in under root/kicad: return (symbols dir, footprints dir).

    Sibling symbols vote the USB parts into Connector and the IMU-style part into Timer, the way
    the live suggestion engine places them today (RESEARCH F-12); the fake official SOT-23-5
    footprint and its model (customfixtures.write_fake_kicad) and a template/sym-lib-table with
    stock descriptions (TBL-01) sit beside them.
    """
    symbols = {
        "Connector": (("USB4105-GF-A", ""), ("USB4110-GF-A", ""), ("USB4085-GF-A", "")),
        "Timer": (("ICM7555", ""), ("ICM7556", ""), ("ICM7232", ""), ("ICM7211", "")),
    }
    symbols_dir, footprints_dir = write_stock_kicad(root, symbols)
    template = root / "kicad" / "template"
    template.mkdir(parents=True, exist_ok=True)
    (template / "sym-lib-table").write_bytes(
        b'(sym_lib_table\n'
        b'  (lib (name "Connector")(type "KiCad")(uri "${KICAD10_SYMBOL_DIR}/Connector.kicad_sym")(options "")'
        b'(descr "Connector symbols (Examples: Terminal Block, D-SUB, DIN, USB...)"))\n'
        b'  (lib (name "Timer")(type "KiCad")(uri "${KICAD10_SYMBOL_DIR}/Timer.kicad_sym")(options "")'
        b'(descr "Timer symbols"))\n'
        b')\n'
    )
    write_fake_kicad(root)
    return symbols_dir, footprints_dir


def make_v1_superproject(root: Path, **kwargs) -> GitRepos:
    """Build the parent + Custom superproject with the rich v1 Custom committed (MIG-01 fixtures).

    The .bak files are written after the commit, so they are untracked and ignored by the
    .gitignore this populate callback writes alongside them.
    """

    def _populate(custom: Path) -> None:
        _write_v1_tree(custom)
        (custom / ".gitignore").write_bytes(b"*.bak\n")

    repos = make_superproject(root, populate=_populate, **kwargs)
    (repos.custom / "Symbols" / "Connector_USB_GCT.bak").write_bytes(b"old revision, kept for reference\r\n")
    (repos.custom / "Symbols" / "IC_Power_Management_LTC.bak").write_bytes(b"old revision, kept for reference\r\n")
    return repos
