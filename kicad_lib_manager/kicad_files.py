import re
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path

from .fsutil import SourceText, decode_source, normalize_eol, read_source
from .models import Issue, Severity
from .sexpr import Edit, Node, SexprError, apply_edits, parse, quote, unquote

_LIB_FIELDS = ("name", "type", "uri", "options", "descr")


@dataclass(frozen=True)
class LoadedFile:
    source: SourceText
    root: Node


@dataclass(frozen=True)
class SymbolRef:
    name: str
    node: Node
    name_node: Node


@dataclass(frozen=True)
class PropertyRef:
    name: str
    value: str
    node: Node
    name_node: Node
    value_node: Node


@dataclass(frozen=True)
class NameRef:
    name: str
    node: Node
    name_node: Node


@dataclass(frozen=True)
class ModelRef:
    path: str
    node: Node
    path_node: Node


@dataclass(frozen=True, eq=False)
class LibEntry:
    node: Node
    name: str | None
    type: str | None
    uri: str | None
    options: str | None
    descr: str | None
    flags: tuple[str, ...]
    extras: tuple[Node, ...]
    value_nodes: dict[str, Node]


def _parse(source: SourceText | Issue, name: str, max_nodes: int | None = None) -> LoadedFile | Issue:
    if isinstance(source, Issue):
        return source
    try:
        root = parse(source.text, max_nodes=max_nodes)
    except SexprError as e:
        return Issue(Severity.ERROR, e.code, f"Could not parse {name}: {e}")
    return LoadedFile(source, root)


def parse_bytes(data: bytes, name: str, *, max_nodes: int | None = None) -> LoadedFile | Issue:
    """Decode and parse in-memory KiCad file bytes; failures come back as an Issue.

    max_nodes is the parser's node ceiling (None = unlimited); crossing it is an Issue too.
    """
    return _parse(decode_source(data, name), name, max_nodes=max_nodes)


def load(path: Path) -> LoadedFile | Issue:
    """Read, decode and parse a KiCad file; failures come back as an Issue."""
    return _parse(read_source(path), path.name)


def _top_level(root: Node, match: Callable[[str], bool]) -> Node | None:
    """Return the first top-level list whose head satisfies match."""
    for child in root.children:
        head = child.head
        if head is not None and match(head):
            return child
    return None


def file_kind(root: Node) -> str | None:
    """Return the head of the first top-level list, such as kicad_symbol_lib or footprint."""
    node = _top_level(root, lambda head: True)
    return node.head if node is not None else None


def file_version(root: Node) -> int | None:
    """Return the integer (version N) of the first top-level list, or None."""
    node = _top_level(root, lambda head: True)
    if node is None:
        return None
    for child in node.children:
        if child.head == "version" and len(child.children) >= 2:
            value = child.children[1]
            if value.kind == "atom" and value.text.isascii() and value.text.isdigit():
                return int(value.text)
            return None
    return None


def _is_token(node: Node) -> bool:
    """True for a string or atom; a list has no text value to unquote."""
    return node.kind in ("str", "atom")


def find_symbols(root: Node) -> list[SymbolRef]:
    """Return the top-level symbols of a kicad_symbol_lib, in document order."""
    found = []
    for lib in root.children:
        if lib.head != "kicad_symbol_lib":
            continue
        for child in lib.children:
            if child.head == "symbol" and len(child.children) >= 2:
                name_node = child.children[1]
                if _is_token(name_node):
                    found.append(SymbolRef(unquote(name_node.text), child, name_node))
    return found


def find_symbol(root: Node, name: str) -> SymbolRef | None:
    """Return the top-level symbol whose name equals name exactly."""
    for ref in find_symbols(root):
        if ref.name == name:
            return ref
    return None


def find_property(symbol_node: Node, name: str) -> PropertyRef | None:
    """Return the direct (property "name" "value" ...) child with an exactly matching name."""
    for child in symbol_node.children:
        if child.head != "property" or len(child.children) < 3:
            continue
        name_node, value_node = child.children[1], child.children[2]
        if not (_is_token(name_node) and _is_token(value_node)):
            continue
        if unquote(name_node.text) == name:
            return PropertyRef(name, unquote(value_node.text), child, name_node, value_node)
    return None


def footprint_name(root: Node) -> NameRef | None:
    """Return the name of the top-level footprint (or legacy module) with its token node."""
    node = _top_level(root, lambda head: head in ("footprint", "module"))
    if node is None or len(node.children) < 2:
        return None
    name_node = node.children[1]
    if name_node.kind not in ("str", "atom"):
        return None
    return NameRef(unquote(name_node.text), node, name_node)


def find_models(footprint_node: Node) -> list[ModelRef]:
    """Return the direct (model ...) children of a footprint, in document order."""
    found = []
    for child in footprint_node.children:
        if child.head != "model" or len(child.children) < 2:
            continue
        path_node = child.children[1]
        if path_node.kind in ("str", "atom"):
            found.append(ModelRef(unquote(path_node.text), child, path_node))
    return found


def retarget_model(ref: ModelRef, new_path: str) -> Edit:
    """Return the edit that replaces only the model path token."""
    return Edit(ref.path_node.start, ref.path_node.end, quote(new_path))


def footprint_name_edit(ref: NameRef, new_name: str) -> Edit:
    """Return the edit that replaces only the footprint name token."""
    return Edit(ref.name_node.start, ref.name_node.end, quote(new_name))


def footprint_value_edits(footprint_node: Node, value: str) -> list[Edit]:
    """Return edits that set the footprint's Value text: (fp_text value ...) and (property "Value" ...).

    Both spellings are direct children of the footprint; the token may be an unquoted atom.
    The list is empty when neither exists.
    """
    edits = []
    for child in footprint_node.children:
        if child.head == "fp_text" and len(child.children) >= 3:
            kind, token = child.children[1], child.children[2]
            if kind.kind == "atom" and kind.text == "value" and _is_token(token):
                edits.append(Edit(token.start, token.end, quote(value)))
        elif child.head == "property" and len(child.children) >= 3:
            name_node, token = child.children[1], child.children[2]
            if _is_token(name_node) and unquote(name_node.text) == "Value" and _is_token(token):
                edits.append(Edit(token.start, token.end, quote(value)))
    return edits


def _line_indent(text: str, pos: int) -> str:
    """Return the blanks at the start of the line that holds pos."""
    line_start = text.rfind("\n", 0, pos) + 1
    return re.match(r"[ \t]*", text[line_start:pos]).group()


def model_insert_edit(text: str, footprint_node: Node, model_path: str, eol: str) -> Edit:
    """Return the zero-width insert of a default (model ...) block after the footprint's last direct child."""
    anchor = footprint_node.children[-1]
    indent = _line_indent(text, anchor.start)
    inner = indent + ("\t" if "\t" in indent else "  ")
    lines = [
        f"(model {quote(model_path)}",
        inner + "(offset (xyz 0 0 0))",
        inner + "(scale (xyz 1 1 1))",
        inner + "(rotate (xyz 0 0 0))",
        indent + ")",
    ]
    return Edit(anchor.end, anchor.end, eol + indent + eol.join(lines))


def set_property_edit(prop: PropertyRef, value: str) -> Edit:
    """Return the edit that replaces only the property's value token."""
    return Edit(prop.value_node.start, prop.value_node.end, quote(value))


def next_property_id(symbol_node: Node) -> int | None:
    """Return the highest (id N) among direct property children plus one, or None when none carries an id."""
    found = []
    for child in symbol_node.children:
        if child.head != "property":
            continue
        for part in child.children:
            if part.head == "id" and len(part.children) >= 2:
                value = part.children[1]
                if value.kind == "atom" and value.text.isascii() and value.text.isdigit():
                    found.append(int(value.text))
    return max(found) + 1 if found else None


# Format versions where the property writer changed: ids stop at 20220914, (hide yes) starts at 20231120
_NO_ID_FROM = 20220914
_HIDE_YES_FROM = 20231120
_DESCRIPTION_FROM = 20230620
_HIDDEN_TEMPLATE_ORDER = ("Datasheet", "Footprint", "ki_fp_filters", "ki_keywords")


def _effects_node(property_node: Node) -> Node | None:
    return next((c for c in property_node.children if c.head == "effects"), None)


def _hide_part(effects: Node) -> Node | None:
    """Return the bare hide atom or (hide ...) list inside an effects list, or None."""
    for part in effects.children[1:]:
        if (part.kind == "atom" and part.text == "hide") or part.head == "hide":
            return part
    return None


def _hide_is_on(part: Node) -> bool:
    if part.kind == "atom" or len(part.children) < 2:
        return True
    value = part.children[1]
    return _is_token(value) and unquote(value.text) == "yes"


def property_is_hidden(prop: PropertyRef) -> bool:
    """True when the property's effects carry a bare hide or (hide yes)."""
    effects = _effects_node(prop.node)
    if effects is None:
        return False
    part = _hide_part(effects)
    return part is not None and _hide_is_on(part)


def hidden_template(symbol_node: Node) -> PropertyRef | None:
    """Return a hidden property to clone: Datasheet, Footprint, ki_fp_filters, ki_keywords, then any hidden one."""
    for name in _HIDDEN_TEMPLATE_ORDER:
        prop = find_property(symbol_node, name)
        if prop is not None and property_is_hidden(prop):
            return prop
    for child in symbol_node.children:
        if child.head != "property" or len(child.children) < 3:
            continue
        name_node, value_node = child.children[1], child.children[2]
        if not (_is_token(name_node) and _is_token(value_node)):
            continue
        prop = PropertyRef(unquote(name_node.text), unquote(value_node.text), child, name_node, value_node)
        if property_is_hidden(prop):
            return prop
    return None


def rename_property_edit(prop: PropertyRef, new_name: str) -> Edit:
    """Return the edit that replaces only the property's name token."""
    return Edit(prop.name_node.start, prop.name_node.end, quote(new_name))


def synth_property_text(name: str, value: str, *, version: int | None, next_id: int | None) -> str:
    """Return a hidden property block for a symbol that has no hidden property to clone.

    The id appears only before format 20220914, bare hide before 20231120, (hide yes) from then on.
    An unknown version is written in the current style.
    """
    parts = [f"(property {quote(name)} {quote(value)}"]
    if next_id is not None and version is not None and version < _NO_ID_FROM:
        parts.append(f" (id {next_id})")
    parts.append(" (at 0 0 0) (effects (font (size 1.27 1.27))")
    parts.append(" hide)" if version is not None and version < _HIDE_YES_FROM else " (hide yes))")
    parts.append(")")
    return "".join(parts)


def description_field_name(symbol_node: Node, version: int | None) -> str:
    """Return the name to use for the description field of a symbol.

    An existing Description or ki_description wins; otherwise the target's own format decides.
    """
    for name in ("Description", "ki_description"):
        if find_property(symbol_node, name) is not None:
            return name
    if version is None or version >= _DESCRIPTION_FROM:
        return "Description"
    return "ki_description"


def new_property_text(
    text: str,
    template: PropertyRef,
    name: str,
    value: str,
    next_id: int | None,
    *,
    version: int | None = None,
) -> str:
    """Return a hidden copy of the template property with a new name and value.

    The id is renewed when the template carries one. A template that is not hidden gets the hide
    flag in the style of version; without a version the template's own style decides (ids mean bare hide).
    """
    block = text[template.node.start:template.node.end]
    node = parse(block).children[0]
    edits = [
        Edit(node.children[1].start, node.children[1].end, quote(name)),
        Edit(node.children[2].start, node.children[2].end, quote(value)),
    ]
    has_id = False
    for part in node.children:
        if part.head == "id" and len(part.children) >= 2:
            has_id = True
            if next_id is not None:
                edits.append(Edit(part.children[1].start, part.children[1].end, str(next_id)))
    bare = has_id if version is None else version < _HIDE_YES_FROM
    effects = _effects_node(node)
    if effects is None:
        last = node.children[-1].end
        flag = " hide" if bare else " (hide yes)"
        edits.append(Edit(last, last, f" (effects (font (size 1.27 1.27)){flag})"))
    else:
        part = _hide_part(effects)
        if part is None:
            end = effects.children[-1].end
            edits.append(Edit(end, end, " hide" if bare else " (hide yes)"))
        elif not _hide_is_on(part):
            if bare:
                edits.append(Edit(part.start, part.end, "hide"))
            else:
                edits.append(Edit(part.children[1].start, part.children[1].end, "yes"))
    return apply_edits(block, edits)


def property_insert_edit(text: str, symbol_node: Node, block: str, eol: str) -> Edit:
    """Return the zero-width insert of a property block after the symbol's last direct property."""
    props = [c for c in symbol_node.children if c.head == "property"]
    anchor = props[-1] if props else symbol_node.children[-1]
    indent = _line_indent(text, anchor.start)
    return Edit(anchor.end, anchor.end, eol + indent + normalize_eol(block, eol))


def symbol_insert_edit(target: LoadedFile, block: str) -> Edit:
    """Return the zero-width insert of a symbol block after the library's last top-level symbol."""
    lib = next((c for c in target.root.children if c.head == "kicad_symbol_lib"), None)
    if lib is None:
        raise ValueError("target is not a kicad_symbol_lib")
    text, eol = target.source.text, target.source.eol
    symbols = find_symbols(target.root)
    if symbols:
        anchor = symbols[-1].node
        indent = _line_indent(text, anchor.start)
    else:
        anchor = lib.children[-1]
        indent = "  "
    return Edit(anchor.end, anchor.end, eol + indent + normalize_eol(block, eol))


def _extends_token(symbol_node: Node) -> Node | None:
    """Return the name token of a direct (extends ...) child, or None."""
    for child in symbol_node.children:
        if child.head == "extends" and len(child.children) >= 2 and _is_token(child.children[1]):
            return child.children[1]
    return None


def extends_name(symbol_node: Node) -> str | None:
    """Return the unquoted parent name of a symbol that extends another, or None."""
    token = _extends_token(symbol_node)
    return unquote(token.text) if token is not None else None


def symbol_unit(root: Node, name: str) -> list[SymbolRef] | None:
    """Return the named symbol with its extends ancestors, parent first.

    None when the symbol or a parent is missing from the file, or the extends chain loops.
    """
    chain: list[SymbolRef] = []
    seen: set[str] = set()
    current: str | None = name
    while current is not None:
        if current in seen:
            return None
        seen.add(current)
        ref = find_symbol(root, current)
        if ref is None:
            return None
        chain.append(ref)
        current = extends_name(ref.node)
    chain.reverse()
    return chain


def unit_library_text(loaded: LoadedFile, keep: Collection[str]) -> str:
    """Return the file text with every top-level symbol not named in keep deleted.

    Each deleted symbol takes the whitespace between it and the previous sibling with it,
    so no blank line is left behind.
    """
    edits = []
    for lib in loaded.root.children:
        if lib.head != "kicad_symbol_lib":
            continue
        for index, child in enumerate(lib.children):
            if child.head != "symbol" or len(child.children) < 2 or not _is_token(child.children[1]):
                continue
            if unquote(child.children[1].text) in keep:
                continue
            previous = lib.children[index - 1]
            edits.append(Edit(previous.end, child.end, ""))
    return apply_edits(loaded.source.text, edits)


_SUB_SYMBOL_SUFFIX = "_([0-9]+)_([0-9]+)"


def rename_symbol_edits(root: Node, old: str, new: str) -> list[Edit]:
    """Return the edits that rename a symbol, its unit sub-symbols and every extends reference.

    Names are compared unquoted, case-sensitively and exactly; a name that merely contains
    old is never touched. Property values are not edited here.
    """
    if old == new:
        return []
    sub_pattern = re.compile(re.escape(old) + _SUB_SYMBOL_SUFFIX)
    edits = []
    for ref in find_symbols(root):
        if ref.name == old:
            edits.append(Edit(ref.name_node.start, ref.name_node.end, quote(new)))
            for child in ref.node.children:
                if child.head != "symbol" or len(child.children) < 2 or not _is_token(child.children[1]):
                    continue
                match = sub_pattern.fullmatch(unquote(child.children[1].text))
                if match:
                    token = child.children[1]
                    edits.append(Edit(token.start, token.end, quote(f"{new}_{match[1]}_{match[2]}")))
        parent = _extends_token(ref.node)
        if parent is not None and unquote(parent.text) == old:
            edits.append(Edit(parent.start, parent.end, quote(new)))
    return edits


def replace_exact_tokens(value: str, old: str, new: str) -> str:
    """Replace the space-separated tokens of value that equal old, keeping the original spacing."""
    return " ".join(new if token == old else token for token in value.split(" "))


def block_text(text: str, node: Node) -> str:
    """Return the source text of a node."""
    return text[node.start:node.end]


def symbol_replace_edit(target: LoadedFile, ref: SymbolRef, block: str) -> Edit:
    """Return the edit that replaces exactly the symbol's span with block, in the target's EOL."""
    return Edit(ref.node.start, ref.node.end, normalize_eol(block, target.source.eol))


def symbol_insert_before_edit(target: LoadedFile, before: SymbolRef, block: str) -> Edit:
    """Return the zero-width insert of a symbol block just before another symbol."""
    eol = target.source.eol
    indent = _line_indent(target.source.text, before.node.start)
    return Edit(before.node.start, before.node.start, normalize_eol(block, eol) + eol + indent)


@dataclass(frozen=True, eq=False)
class LibTable:
    node: Node
    tag: str
    entries: tuple[LibEntry, ...]
    others: tuple[Node, ...]


def _lib_entry(lib: Node) -> LibEntry:
    value_nodes: dict[str, Node] = {}
    flags: list[str] = []
    extras: list[Node] = []
    for field in lib.children[1:]:
        head = field.head
        if head is None:
            continue
        if head in _LIB_FIELDS:
            # A known field without a usable token value is never a flag
            if head not in value_nodes and len(field.children) >= 2 and _is_token(field.children[1]):
                value_nodes[head] = field.children[1]
            else:
                extras.append(field)
        elif len(field.children) == 1:
            flags.append(head)
        else:
            extras.append(field)
    values = {k: unquote(v.text) for k, v in value_nodes.items()}
    return LibEntry(
        node=lib,
        name=values.get("name"),
        type=values.get("type"),
        uri=values.get("uri"),
        options=values.get("options"),
        descr=values.get("descr"),
        flags=tuple(flags),
        extras=tuple(extras),
        value_nodes=value_nodes,
    )


def lib_table(root: Node) -> LibTable | None:
    """Return the table node of a sym/fp/design-block lib table with its entries and other children."""
    table = _top_level(root, lambda head: head.endswith("_lib_table"))
    if table is None:
        return None
    entries = []
    others = []
    # children[0] is the head atom
    for child in table.children[1:]:
        if child.head == "lib":
            entries.append(_lib_entry(child))
        else:
            others.append(child)
    return LibTable(table, table.head, tuple(entries), tuple(others))


def lib_table_entries(root: Node) -> list[LibEntry]:
    """Return the (lib ...) entries of a sym/fp/design-block lib table, fields in any order."""
    table = lib_table(root)
    return list(table.entries) if table is not None else []
