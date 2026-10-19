from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .fsutil import SourceText, decode_source, read_source
from .models import Issue, Severity
from .sexpr import Node, SexprError, parse, unquote

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


def _parse(source: SourceText | Issue, name: str) -> LoadedFile | Issue:
    if isinstance(source, Issue):
        return source
    try:
        root = parse(source.text)
    except SexprError as e:
        return Issue(Severity.ERROR, e.code, f"Could not parse {name}: {e}")
    return LoadedFile(source, root)


def parse_bytes(data: bytes, name: str) -> LoadedFile | Issue:
    """Decode and parse in-memory KiCad file bytes; failures come back as an Issue."""
    return _parse(decode_source(data, name), name)


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


def find_symbols(root: Node) -> list[SymbolRef]:
    """Return the top-level symbols of a kicad_symbol_lib, in document order."""
    found = []
    for lib in root.children:
        if lib.head != "kicad_symbol_lib":
            continue
        for child in lib.children:
            if child.head == "symbol" and len(child.children) >= 2:
                name_node = child.children[1]
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
        name_node = child.children[1]
        if unquote(name_node.text) == name:
            value_node = child.children[2]
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
        if head in _LIB_FIELDS and len(field.children) >= 2 and head not in value_nodes:
            value_nodes[head] = field.children[1]
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
