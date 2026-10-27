"""The one name rule of the Atomic_ scheme: a library is Atomic_ plus an official KiCad symbol-library stem (D-08).

A leaf module of the importer: no Qt, and it reads only file names. The form calls name_verdict live
and build_plan calls it again as the authority, so both give the same answer for the same text. The
allowed stems are the built-in KiCad 10 snapshot unioned with the stems of an installed KiCad symbols
folder (D-07); an installed folder never removes a snapshot stem, and a newer KiCad adds its new stems.
"""

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..atomic_check import ATOMIC_PREFIX

# The 223 stems of the symbol libraries shipped with KiCad 10.0.7
_SNAPSHOT = (
    "4xxx", "4xxx_IEEE", "74xGxx", "74xx", "74xx_IEEE", "Amplifier_Audio", "Amplifier_Buffer",
    "Amplifier_Current", "Amplifier_Difference", "Amplifier_Instrumentation",
    "Amplifier_Operational", "Amplifier_Video", "Analog", "Analog_ADC", "Analog_DAC",
    "Analog_Switch", "Audio", "Auxiliary_Items", "Battery_Management", "Buffer", "Comparator",
    "Connector", "Connector_Audio", "Connector_Generic", "Connector_Generic_MountingPin",
    "Connector_Generic_Shielded", "Converter_ACDC", "Converter_DCDC", "Converter_DCDC_Isolated",
    "CPLD_Altera", "CPLD_Microchip", "CPLD_Renesas", "CPLD_Xilinx", "CPU", "CPU_NXP_6800",
    "CPU_NXP_68000", "CPU_NXP_IMX", "CPU_PowerPC", "Device", "Diode", "Diode_Bridge", "Diode_Laser",
    "Display_Character", "Display_Graphic", "Driver", "Driver_Display", "Driver_FET", "Driver_LED",
    "Driver_Motor", "DSP_AnalogDevices", "DSP_Freescale", "DSP_Microchip_DSPIC33", "DSP_Motorola",
    "DSP_Texas", "Fiber_Optic", "Filter", "FPGA_Altera_MAX10", "FPGA_CologneChip_GateMate",
    "FPGA_Efinix_Trion", "FPGA_Lattice", "FPGA_Microsemi", "FPGA_Xilinx", "FPGA_Xilinx_Artix7",
    "FPGA_Xilinx_Kintex7", "FPGA_Xilinx_Spartan6", "FPGA_Xilinx_Virtex5", "FPGA_Xilinx_Virtex6",
    "FPGA_Xilinx_Virtex7", "GPU", "Graphic", "Interface", "Interface_CAN_LIN",
    "Interface_CurrentLoop", "Interface_Ethernet", "Interface_Expansion", "Interface_HDMI",
    "Interface_HID", "Interface_LineDriver", "Interface_Optical", "Interface_Telecom",
    "Interface_UART", "Interface_USB", "Isolator", "Isolator_Analog", "Jumper", "LED",
    "Logic_LevelTranslator", "Logic_Programmable", "MCU_AnalogDevices", "MCU_Cypress", "MCU_Dialog",
    "MCU_Espressif", "MCU_Intel", "MCU_Microchip_8051", "MCU_Microchip_ATmega",
    "MCU_Microchip_ATtiny", "MCU_Microchip_AVR", "MCU_Microchip_AVR_Dx", "MCU_Microchip_PIC10",
    "MCU_Microchip_PIC12", "MCU_Microchip_PIC16", "MCU_Microchip_PIC18", "MCU_Microchip_PIC24",
    "MCU_Microchip_PIC32", "MCU_Microchip_SAMA", "MCU_Microchip_SAMD", "MCU_Microchip_SAME",
    "MCU_Microchip_SAML", "MCU_Microchip_SAMV", "MCU_Module", "MCU_Nordic", "MCU_NXP_ColdFire",
    "MCU_NXP_HC11", "MCU_NXP_HC12", "MCU_NXP_HCS12", "MCU_NXP_Kinetis", "MCU_NXP_LPC",
    "MCU_NXP_MAC7100", "MCU_NXP_MCore", "MCU_NXP_NTAG", "MCU_NXP_S08", "MCU_Parallax", "MCU_Puya",
    "MCU_RaspberryPi", "MCU_Renesas_Synergy_S1", "MCU_SiFive", "MCU_SiliconLabs", "MCU_ST_STM32C0",
    "MCU_ST_STM32F0", "MCU_ST_STM32F1", "MCU_ST_STM32F2", "MCU_ST_STM32F3", "MCU_ST_STM32F4",
    "MCU_ST_STM32F7", "MCU_ST_STM32G0", "MCU_ST_STM32G4", "MCU_ST_STM32H5", "MCU_ST_STM32H7",
    "MCU_ST_STM32L0", "MCU_ST_STM32L1", "MCU_ST_STM32L4", "MCU_ST_STM32L5", "MCU_ST_STM32MP1",
    "MCU_ST_STM32U0", "MCU_ST_STM32U5", "MCU_ST_STM32WB", "MCU_ST_STM32WL", "MCU_ST_STM8",
    "MCU_STC", "MCU_Texas", "MCU_Texas_MSP430", "MCU_Texas_SimpleLink", "MCU_Trident",
    "MCU_WCH_RiscV", "Mechanical", "Memory_EEPROM", "Memory_EPROM", "Memory_Flash", "Memory_NVRAM",
    "Memory_RAM", "Memory_ROM", "Memory_UniqueID", "Motor", "Oscillator", "Potentiometer_Digital",
    "power", "Power_Management", "Power_Protection", "Power_Supervisor", "Reference_Current",
    "Reference_Voltage", "Regulator_Controller", "Regulator_Current", "Regulator_Linear",
    "Regulator_SwitchedCapacitor", "Regulator_Switching", "Relay", "Relay_SolidState", "RF",
    "RF_AM_FM", "RF_Amplifier", "RF_Bluetooth", "RF_Filter", "RF_GPS", "RF_GSM", "RF_Mixer",
    "RF_Module", "RF_NFC", "RF_RFID", "RF_Switch", "RF_WiFi", "RF_ZigBee", "Security", "Sensor",
    "Sensor_Audio", "Sensor_Current", "Sensor_Distance", "Sensor_Energy", "Sensor_Gas",
    "Sensor_Humidity", "Sensor_Magnetic", "Sensor_Motion", "Sensor_Optical", "Sensor_Pressure",
    "Sensor_Proximity", "Sensor_Temperature", "Sensor_Touch", "Sensor_Voltage", "Simulation_SPICE",
    "Switch", "Timer", "Timer_PLL", "Timer_RTC", "Transformer", "Transistor_Array",
    "Transistor_BJT", "Transistor_FET", "Transistor_FET_Other", "Transistor_IGBT",
    "Transistor_Power_Module", "Triac_Thyristor", "Valve", "Video",
)
KICAD10_STEMS: frozenset[str] = frozenset(_SNAPSHOT)

# KiCad libraries that never hold parts (D-10)
EXCLUDED_STEMS: frozenset[str] = frozenset(
    {
        "power",
        "Simulation_SPICE",
        "Graphic",
        "Connector_Generic",
        "Connector_Generic_MountingPin",
        "Connector_Generic_Shielded",
    }
)

# The one footprint library every installed part uses (D-15)
SHARED_FOOTPRINT_LIBRARY = "Atomic_Footprints"

_SYMBOL_SUFFIX = ".kicad_sym"
# A stem read from disk becomes part of a path later, so only plain library-name characters pass (T-10-01)
_SAFE_STEM_RE = re.compile(r"[A-Za-z0-9_-]+")


def _fold_index(stems: Iterable[str]) -> dict[str, str]:
    """Map the casefold of every stem to its official spelling; two stems that fold together are an error."""
    index: dict[str, str] = {}
    for stem in stems:
        key = stem.casefold()
        if key in index and index[key] != stem:
            raise ValueError(f"stems {index[key]!r} and {stem!r} differ only by letter case")
        index[key] = stem
    return index


if len(_SNAPSHOT) != len(KICAD10_STEMS):
    raise ValueError("the KiCad 10 stem snapshot holds a duplicate")
_SNAPSHOT_FOLD = _fold_index(KICAD10_STEMS)
_EXCLUDED_FOLD = _fold_index(EXCLUDED_STEMS)
if not EXCLUDED_STEMS <= KICAD10_STEMS:
    raise ValueError(f"excluded stems missing from the snapshot: {sorted(EXCLUDED_STEMS - KICAD10_STEMS)}")


def installed_stems(symbols_dir: Path | None) -> frozenset[str]:
    """The exact-case stems of the .kicad_sym files in an installed KiCad symbols folder; empty when unreadable."""
    if symbols_dir is None:
        return frozenset()
    try:
        names = os.listdir(symbols_dir)
    except OSError:
        return frozenset()
    stems = set()
    for name in names:
        if not name.lower().endswith(_SYMBOL_SUFFIX):
            continue
        stem = name[: -len(_SYMBOL_SUFFIX)]
        if _SAFE_STEM_RE.fullmatch(stem):
            stems.add(stem)
    return frozenset(stems)


def allowed_stems(installed: Iterable[str] = ()) -> frozenset[str]:
    """The snapshot unioned with installed stems, minus the excluded ones; the installed spelling wins on a case clash."""
    merged = dict(_SNAPSHOT_FOLD)
    for stem in installed:
        key = stem.casefold()
        if key in _EXCLUDED_FOLD or not _SAFE_STEM_RE.fullmatch(stem):
            continue
        merged[key] = stem
    return frozenset(stem for key, stem in merged.items() if key not in _EXCLUDED_FOLD)


_DEFAULT_ALLOWED = allowed_stems()


@dataclass(frozen=True)
class NameVerdict:
    """The answer for one typed library name; name is the text to use, note and reason are one plain line each."""

    ok: bool
    name: str
    note: str
    reason: str


def _refuse(text: str, reason: str, name: str | None = None, note: str = "") -> NameVerdict:
    return NameVerdict(False, text if name is None else name, note, reason)


def name_verdict(text: str, allowed: frozenset[str] | None = None) -> NameVerdict:
    """Judge a library name: ok only for Atomic_ plus an allowed stem; every refusal carries its own reason."""
    stems = _DEFAULT_ALLOWED if allowed is None else allowed
    if not text.strip():
        return _refuse(text, "Pick or type a library name")
    wanted = {(ATOMIC_PREFIX + stem).casefold(): ATOMIC_PREFIX + stem for stem in stems}
    official = wanted.get(text.casefold())
    if official == text:
        return NameVerdict(True, text, "", "")
    if official is not None:
        return _refuse(
            text,
            f"{text} is spelled differently from the KiCad library name; use {official}",
            name=official,
            note=f"Spelling corrected to {official}",
        )
    return _refuse(text, f"{text} is not an allowed library name")
