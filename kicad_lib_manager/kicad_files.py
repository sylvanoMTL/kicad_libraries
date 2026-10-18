from dataclasses import dataclass

from .sexpr import Node, unquote


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
