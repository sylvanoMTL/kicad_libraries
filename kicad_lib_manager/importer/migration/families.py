"""Derived-symbol decisions for the Atomic_ migration (D-06).

find_families groups inventory parts by (target library, first family-prefix of their MPN or
name, RESEARCH F-11); within a group sorted by that key, the first member is the parent and every
other member whose non-property children stream-match the parent's (unit sub-symbol names reduced
to their unit/style suffix, P-09) becomes a derived symbol of it, one FamilyRow per match. A parent
or member that already extends another symbol in its own source stays out, since it is not a plain
drawn symbol to compare or derive from.

derived_edits turns a member's own parsed block into the short (extends "<parent>") form KiCad's
own libraries use (see Regulator_Linear.kicad_sym): just the properties and, when present, the
(embedded_fonts ...) child survive; pin settings, flags and the unit sub-symbol are dropped.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ...kicad_files import Edit, LoadedFile, SymbolRef, block_text, find_symbol, parse_bytes
from ...sexpr import quote, token_stream, unquote
from ..siblings import family_prefixes
from .inventory import Inventory, InventoryPart
from .plan import FamilyRow, MigrationChoices, PartChoice, PartKey

# A unit sub-symbol is named "<NAME>_<unit>_<style>" (RESEARCH P-09); only this trailing suffix is
# kept when comparing graphics, so two members differing only by their own name (and so by their
# sub-symbols' names) compare equal.
_UNIT_STYLE_SUFFIX = re.compile(r"_[0-9]+_[0-9]+$")


@dataclass(frozen=True)
class FamiliesOutcome:
    """find_families's result: which parts derive from which, and the rows a window would show."""

    derived: Mapping[PartKey, PartKey] = field(default_factory=dict)
    rows: tuple[FamilyRow, ...] = ()


def _family_key(target: str, mpn: str, name: str) -> tuple[str, str] | None:
    """The (target, first family prefix of mpn or name) a part groups on, or None when it never groups."""
    if not target:
        return None
    prefixes = family_prefixes(mpn) or family_prefixes(name)
    if not prefixes:
        return None
    return (target, prefixes[0])


def _graphics_stream(root, ref: SymbolRef) -> tuple:
    """Token streams of a symbol's non-property children, unit sub-symbol names reduced to their suffix (D-06).

    Properties are excluded entirely (a derived symbol is judged on its own fields, not compared
    by them). Everything else a plain symbol carries - pin_numbers/pin_names settings, in_bom,
    on_board, flags, graphics and unit sub-symbols - is included, so a difference in any pin,
    graphic line or flag breaks the match.
    """
    streams = []
    for child in ref.node.children:
        if child is ref.name_node or child.kind != "list":
            continue
        if child.head == "property":
            continue
        if child.head == "symbol" and len(child.children) >= 2 and child.children[1].kind in ("str", "atom"):
            sub_name = unquote(child.children[1].text)
            match = _UNIT_STYLE_SUFFIX.search(sub_name)
            suffix = match.group(0) if match else sub_name
            stream = token_stream(child)
            stream = (stream[0], stream[1], ("atom", suffix)) + stream[3:]
        else:
            stream = token_stream(child)
        streams.append(stream)
    return tuple(streams)


def _loaded(repo_root: Path, rel_path: str, cache: dict[str, LoadedFile]) -> LoadedFile | None:
    """The parsed source file holding rel_path, cached per call; an unreadable or unparsable file gives None."""
    cached = cache.get(rel_path)
    if cached is not None:
        return cached
    try:
        data = (repo_root / rel_path).read_bytes()
    except OSError:
        return None
    loaded = parse_bytes(data, Path(rel_path).name)
    if not isinstance(loaded, LoadedFile):
        return None
    cache[rel_path] = loaded
    return loaded


def find_families(
    inventory: Inventory,
    choices: MigrationChoices,
    *,
    targets: Mapping[PartKey, str],
    mpns: Mapping[PartKey, str],
) -> FamiliesOutcome:
    """Group parts by (target, family prefix); members identical to the group's first become derived (D-06)."""
    groups: dict[tuple[str, str], list[InventoryPart]] = {}
    for part in inventory.parts:
        key = _family_key(targets.get(part.key, ""), mpns.get(part.key, part.name), part.name)
        if key is None:
            continue
        groups.setdefault(key, []).append(part)

    repo_root = inventory.layout.repo_root
    cache: dict[str, LoadedFile] = {}
    derived: dict[PartKey, PartKey] = {}
    rows: list[FamilyRow] = []

    for group_key in sorted(groups):
        members = sorted(groups[group_key], key=lambda p: (p.rel_path, p.name))
        if len(members) < 2:
            continue
        parent = members[0]
        # InventoryPart.extends is already kicad_files.extends_name(ref.node) from read_inventory,
        # so a symbol that already extends another in its own source is recognised without
        # re-parsing; a parent in that state is not a plain drawn symbol to derive others from.
        if parent.extends is not None:
            continue
        parent_loaded = _loaded(repo_root, parent.rel_path, cache)
        if parent_loaded is None:
            continue
        parent_ref = find_symbol(parent_loaded.root, parent.name)
        if parent_ref is None:
            continue
        parent_stream = _graphics_stream(parent_loaded.root, parent_ref)

        for member in members[1:]:
            if member.extends is not None:
                continue
            member_loaded = _loaded(repo_root, member.rel_path, cache)
            if member_loaded is None:
                continue
            member_ref = find_symbol(member_loaded.root, member.name)
            if member_ref is None:
                continue
            if _graphics_stream(member_loaded.root, member_ref) != parent_stream:
                continue
            choice = choices.parts.get(member.key, PartChoice())
            rows.append(FamilyRow(parent.key, member.key, choice.derive))
            if choice.derive:
                derived[member.key] = parent.key

    return FamiliesOutcome(derived, tuple(rows))


def _indent(text: str, pos: int) -> str:
    """The blanks at the start of the line holding pos (tabs or spaces, whichever the file uses)."""
    line_start = text.rfind("\n", 0, pos) + 1
    end = line_start
    while end < len(text) and text[end] in " \t":
        end += 1
    return text[line_start:end]


def derived_edits(loaded: LoadedFile, ref: SymbolRef, parent_name: str) -> list[Edit]:
    """Turn a member's own block into (extends "<parent_name>") plus its own properties (D-06).

    Pin settings, flags and the unit sub-symbol are dropped; an (embedded_fonts ...) child, when
    the symbol carries one, is kept last - matching KiCad's own derived-symbol shape (see
    Regulator_Linear.kicad_sym). Property order and text are preserved exactly.
    """
    text = loaded.source.text
    eol = loaded.source.eol
    properties = [child for child in ref.node.children if child.head == "property"]
    embedded_fonts = next((child for child in ref.node.children if child.head == "embedded_fonts"), None)
    kept = properties + ([embedded_fonts] if embedded_fonts is not None else [])
    symbol_indent = _indent(text, ref.node.start)
    child_indent = _indent(text, kept[0].start) if kept else symbol_indent + "\t"
    body = f" (extends {quote(parent_name)})"
    for child in kept:
        body += eol + child_indent + block_text(text, child)
    body += eol + symbol_indent + ")"
    return [Edit(ref.name_node.end, ref.node.end, body)]
