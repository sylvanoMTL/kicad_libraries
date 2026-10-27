"""Generate the single-word keywords of a part and merge them after the vendor's own words (FLD-01, D-26, D-27).

KiCad 10's symbol chooser searches the keywords, so a part gets words for what it is: the library
stem, its function and interface, its package codes, the manufacturer and its parent brand, the MPN
and the runner-up category words. Pure and Qt-free. Generation only reads the manufacturer; it never
changes the Manufacturer field (D-26).
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence

from ..manufacturers import lookup

ATOMIC_PREFIX = "Atomic_"

# Words that carry no meaning about the part: prices, stock and the shops and sites that supply it
JUNK_WORDS = frozenset(
    {
        "price",
        "prices",
        "stock",
        "instock",
        "availability",
        "qty",
        "usd",
        "eur",
        "buy",
        "digikey",
        "mouser",
        "lcsc",
        "octopart",
        "farnell",
        "arrow",
        "snapeda",
        "snapmagic",
        "ultralibrarian",
        "samacsys",
        "componentsearchengine",
    }
)

# (whole phrase of the folded description or category, keyword) in output order
FUNCTION_WORDS: tuple[tuple[str, str], ...] = (
    ("mosfet", "MOSFET"),
    ("n channel", "N-channel"),
    ("p channel", "P-channel"),
    ("half bridge", "half-bridge"),
    ("load switch", "load-switch"),
    ("isolated", "isolated"),
    ("dc dc", "DC-DC"),
    ("ac dc", "AC-DC"),
    ("converter", "converter"),
    ("regulator", "regulator"),
    ("ldo", "LDO"),
    ("buck", "buck"),
    ("boost", "boost"),
    ("charger", "charger"),
    ("fuel gauge", "fuel-gauge"),
    ("magnetometer", "magnetometer"),
    ("accelerometer", "accelerometer"),
    ("gyroscope", "gyroscope"),
    ("imu", "IMU"),
    ("oscillator", "oscillator"),
    ("tcxo", "TCXO"),
    ("crystal", "crystal"),
    ("connector", "connector"),
    ("receptacle", "receptacle"),
    ("usb c", "USB-C"),
    ("type c", "USB-C"),
)

INTERFACE_WORDS: tuple[tuple[str, str], ...] = (
    ("i2c", "I2C"),
    ("spi", "SPI"),
    ("uart", "UART"),
    ("usb", "USB"),
    ("can", "CAN"),
    ("i2s", "I2S"),
    ("sdio", "SDIO"),
    ("ethernet", "Ethernet"),
    ("ble", "BLE"),
    ("bluetooth", "Bluetooth"),
    ("wifi", "WiFi"),
)

_WORD_SPLIT_RE = re.compile(r"[\s,;]+")
_WRAPPERS = "()[]{}<>\"'"


def _phrase_text(text: str) -> str:
    """Fold text to blank-separated whole words with a blank at both ends, for whole-phrase matching."""
    folded = unicodedata.normalize("NFKD", text.replace("\\n", " "))
    folded = "".join(c for c in folded if not unicodedata.combining(c)).casefold()
    return " " + " ".join(re.findall(r"[a-z0-9]+", folded)) + " "


def split_words(text: str) -> list[str]:
    """Split on blanks, commas and semicolons and strip surrounding brackets and quotes."""
    words = (word.strip(_WRAPPERS) for word in _WORD_SPLIT_RE.split(text))
    return [word for word in words if word]


def _dedupe(words: Iterable[str]) -> list[str]:
    """Drop repeats ignoring case; the first spelling stays."""
    seen: set[str] = set()
    kept: list[str] = []
    for word in words:
        key = word.casefold()
        if key not in seen:
            seen.add(key)
            kept.append(word)
    return kept


def manufacturer_words(name: str) -> list[str]:
    """The words a user may type for a manufacturer: its one-word aliases, first word, then its owner's."""
    match = lookup(name)
    if match is None:
        found = split_words(name)
        return found[:1]
    words: list[str] = []
    entry = match.entry
    while entry is not None:
        words.extend(alias for alias in entry.aliases if len(split_words(alias)) == 1)
        words.extend(split_words(entry.name)[:1])
        owner = lookup(entry.owner) if entry.owner else None
        entry = owner.entry if owner is not None else None
    return _dedupe(words)


def _stem_words(stem: str) -> list[str]:
    return [part for part in stem.removeprefix(ATOMIC_PREFIX).split("_") if part]


def _matched(pairs: tuple[tuple[str, str], ...], text: str) -> list[str]:
    return [word for phrase, word in pairs if f" {phrase} " in text]


def generate_keywords(
    *,
    library: str,
    description: str,
    category: str,
    package_words: Sequence[str],
    manufacturer: str,
    mpn: str,
    symbol_name: str,
    related: Sequence[str] = (),
) -> list[str]:
    """Build the keyword list of a part in order of how much each source says about it (FLD-01, D-26).

    Every item is one word without blanks or "=", free of junk words and unique ignoring case.
    """
    text = _phrase_text(f"{description} {category}")
    words: list[str] = _stem_words(library)
    words += _matched(FUNCTION_WORDS, text)
    words += _matched(INTERFACE_WORDS, text)
    words += package_words
    words += manufacturer_words(manufacturer)
    if mpn and mpn.casefold() not in symbol_name.casefold():
        words.append(mpn)
    for stem in related:
        words += _stem_words(stem)
    words += split_words(category)
    clean = (
        word
        for word in words
        if word and not any(c.isspace() or c == "=" for c in word) and word.casefold() not in JUNK_WORDS
    )
    return _dedupe(clean)


def merge_words(vendor: str, generated: Sequence[str]) -> str:
    """Join the vendor's words without junk, then generated words not already present ignoring case (D-27)."""
    kept = [word for word in split_words(vendor) if word.casefold() not in JUNK_WORDS]
    present = {word.casefold() for word in kept}
    for word in generated:
        key = word.casefold()
        if key not in present:
            present.add(key)
            kept.append(word)
    return " ".join(kept)
