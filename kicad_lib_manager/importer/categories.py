"""Place a part in a KiCad library stem from its vendor category, its words or an unambiguous reference letter (D-04).

Used when no sibling part in KiCad decides the library. Order of evidence: a vendor category together
with words of the description, then the vendor category alone, then words alone, then a reference letter
that names one kind of part. A part that none of these places is left unplaced, never filed by a guess.
Qt-free; reads only the part's text and the allowed stems.
"""

import re
import unicodedata
from dataclasses import dataclass

from .candidate import PartMeta
from .stems import allowed_stems


@dataclass(frozen=True)
class CategoryRule:
    """One placement rule: the vendor category (when set), words that must all occur, words of which one must."""

    stem: str
    vendor: frozenset[str] = frozenset()
    all_words: tuple[str, ...] = ()
    any_words: tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryMatch:
    """The outcome of classify; source is "vendor", "words", "reference" or "" when nothing placed the part."""

    stem: str | None
    source: str
    detail: str
    runner_up: tuple[str, ...]


# Vendor category keys (letters and digits, casefolded) for a power supply or converter part
POWER_SUPPLY = frozenset({"powersupply", "powersupplies", "dcdcconverter", "dcdcconverters"})

# Ordered; the first matching rule wins. A phrase such as "dc dc" matches as whole words. No rule names
# Crystal: KiCad 10 has no such library, and a crystal is never filed by a guess (Pitfall 4).
RULES: tuple[CategoryRule, ...] = (
    CategoryRule("Converter_DCDC_Isolated", POWER_SUPPLY, any_words=("isolated", "isolation")),
    CategoryRule("Converter_ACDC", POWER_SUPPLY, any_words=("ac dc", "acdc")),
    CategoryRule("Converter_DCDC", POWER_SUPPLY, any_words=("dc dc", "dcdc", "converter")),
    CategoryRule("Converter_DCDC_Isolated", all_words=("isolated",), any_words=("dc dc", "dcdc")),
    CategoryRule("Converter_ACDC", any_words=("ac dc converter", "acdc converter")),
    CategoryRule("Converter_DCDC", any_words=("dc dc converter", "dcdc converter")),
    CategoryRule("Regulator_Linear", any_words=("ldo", "linear regulator", "low dropout")),
    CategoryRule("Regulator_Switching", any_words=("buck", "boost", "switching regulator")),
    CategoryRule("Transistor_FET", any_words=("mosfet", "n channel", "p channel")),
    CategoryRule("Transistor_BJT", any_words=("bjt", "npn", "pnp")),
    CategoryRule("Sensor_Magnetic", any_words=("magnetometer",)),
    CategoryRule("Sensor_Motion", any_words=("imu", "accelerometer", "gyroscope")),
    CategoryRule("Battery_Management", any_words=("fuel gauge", "battery charger", "charger")),
    CategoryRule("Oscillator", any_words=("tcxo", "vcxo", "ocxo", "mems oscillator", "oscillator")),
    CategoryRule(
        "Connector", all_words=("usb",), any_words=("connector", "receptacle", "plug", "header")
    ),
    CategoryRule("Diode", any_words=("diode", "schottky", "zener")),
)

# Vendor category keys that name one kind of part. Only "Power Supply" is seen in a real download; the
# rest are assumed wording and fall through when wrong. Crystal, transistor and integrated circuit stay
# unmapped: each spans several KiCad libraries.
VENDOR_STEMS: dict[str, str] = {
    "connector": "Connector",
    "connectors": "Connector",
    "diode": "Diode",
    "diodes": "Diode",
    "relay": "Relay",
    "relays": "Relay",
    "oscillator": "Oscillator",
    "oscillators": "Oscillator",
    "led": "LED",
    "leds": "LED",
    "switch": "Switch",
    "switches": "Switch",
}

# Only these reference letters name one kind of part; U, Q, D, X, Y and the rest never place a part (A3, A4)
REFERENCE_STEMS: dict[str, str] = {
    "K": "Relay",
    "SW": "Switch",
    "TR": "Transformer",
    "M": "Motor",
    "JP": "Jumper",
    "J": "Connector",
}


def _fold(text: str) -> str:
    """Fold text: literal backslash-n escapes to blanks, NFKD, no combining marks, casefold."""
    text = unicodedata.normalize("NFKD", text.replace("\\n", " "))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _category_key(category: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(category))


def part_text(meta: PartMeta) -> str:
    """The description, keywords and category as blank-separated whole words with a blank at both ends."""
    text = _fold(" ".join((meta.description, meta.keywords, meta.category)))
    return " " + " ".join(re.findall(r"[a-z0-9]+", text)) + " "


def _rule_matches(rule: CategoryRule, key: str, text: str) -> bool:
    if rule.vendor and key not in rule.vendor:
        return False
    if any(f" {phrase} " not in text for phrase in rule.all_words):
        return False
    return not rule.any_words or any(f" {phrase} " in text for phrase in rule.any_words)


def _vendor_detail(category: str, with_description: bool) -> str:
    detail = f"the vendor category {category}"
    return f"{detail} and the description" if with_description else detail


def classify(meta: PartMeta, allowed: frozenset[str] | None = None) -> CategoryMatch:
    """Place a part by its vendor category, then words, then reference letters; unplaced gives stem None."""
    stems = allowed_stems() if allowed is None else allowed
    text = part_text(meta)
    key = _category_key(meta.category)
    category = " ".join(meta.category.replace("\\n", " ").split())
    hits = [rule for rule in RULES if _rule_matches(rule, key, text) and rule.stem in stems]

    stem: str | None = None
    source = ""
    detail = ""
    for rule in hits:
        if rule.vendor:
            stem, source = rule.stem, "vendor"
            detail = _vendor_detail(category, bool(rule.all_words or rule.any_words))
            break
    if stem is None:
        mapped = VENDOR_STEMS.get(key)
        if mapped is not None and mapped in stems:
            stem, source, detail = mapped, "vendor", _vendor_detail(category, False)
    if stem is None:
        for rule in hits:
            if not rule.vendor:
                stem, source, detail = rule.stem, "words", "the description"
                break
    if stem is None:
        letters = re.match(r"[A-Za-z]+", meta.reference.strip())
        if letters is not None:
            mapped = REFERENCE_STEMS.get(letters.group(0).upper())
            if mapped is not None and mapped in stems:
                stem, source, detail = mapped, "reference", f"the reference {letters.group(0).upper()}"
    if stem is None:
        return CategoryMatch(None, "", "", ())

    runner_up: list[str] = []
    for rule in hits:
        if rule.stem != stem and rule.stem not in runner_up:
            runner_up.append(rule.stem)
    return CategoryMatch(stem, source, detail, tuple(runner_up))
