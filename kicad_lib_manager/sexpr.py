import re
import sys
from dataclasses import dataclass

# Separators are ASCII space/tab/CR/LF only, like KiCad's lexer (never the regex \s class)
_TOKEN = re.compile(
    r'(?P<open>\()'
    r'|(?P<close>\))'
    r'|(?P<str>"(?:[^"\\]|\\.)*")'
    r'|(?P<atom>[^ \t\r\n()"]+)'
    r'|(?P<ws>[ \t\r\n]+)'
    r'|(?P<bad>.)',
    re.S,
)

# KiCad's writer escapes exactly these four; TAB stays raw
_QUOTE_TABLE = str.maketrans({
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
})

_UNESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
_ESCAPE_RE = re.compile(r"\\(.)", re.S)


class SexprError(ValueError):
    def __init__(self, code: str, message: str, line: int, col: int):
        super().__init__(f"{message} at line {line}, col {col}")
        self.code = code
        self.line = line
        self.col = col


def _line_col(text: str, pos: int) -> tuple[int, int]:
    """Return the 1-based (line, col) of a character offset."""
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col


@dataclass(slots=True, eq=False, repr=False)
class Node:
    start: int
    end: int
    kind: str  # "root" | "list" | "str" | "atom"
    children: list["Node"]
    text: str = ""

    @property
    def head(self) -> str | None:
        """Return the first child's text when this is a list led by an atom."""
        if self.kind == "list" and self.children and self.children[0].kind == "atom":
            return self.children[0].text
        return None

    def __repr__(self) -> str:
        return f"Node({self.kind} {self.start}:{self.end}, {len(self.children)} children)"


def parse(text: str, *, max_nodes: int | None = None) -> Node:
    """Parse text into a span-carrying tree, raising SexprError at the first bad token.

    max_nodes caps the lists, atoms and strings built (the root is not counted); the token
    that would cross it raises sexpr.too_many_nodes. None means no limit.
    """
    root = Node(0, len(text), "root", [])
    # Explicit stack: no recursion limit on deeply nested input
    stack = [root]
    limit = sys.maxsize if max_nodes is None else max_nodes
    count = 0
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "bad":
            raise SexprError(
                "sexpr.unterminated",
                "unterminated string or stray character",
                *_line_col(text, m.start()),
            )
        if kind != "close":
            count += 1
            if count > limit:
                raise SexprError(
                    "sexpr.too_many_nodes",
                    f"more than {max_nodes} nodes",
                    *_line_col(text, m.start()),
                )
        if kind == "open":
            node = Node(m.start(), -1, "list", [])
            stack[-1].children.append(node)
            stack.append(node)
        elif kind == "close":
            if len(stack) == 1:
                raise SexprError(
                    "sexpr.unbalanced",
                    "unbalanced ')'",
                    *_line_col(text, m.start()),
                )
            stack.pop().end = m.end()
        else:
            stack[-1].children.append(Node(m.start(), m.end(), kind, [], m.group()))
    if len(stack) != 1:
        raise SexprError(
            "sexpr.unclosed",
            "unclosed '('",
            *_line_col(text, stack[-1].start),
        )
    return root


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str


def apply_edits(src: str, edits: list[Edit]) -> str:
    """Splice edits into src; overlapping or out-of-range edits are a programmer error and raise ValueError."""
    out = []
    pos = 0
    # Stable sort: a zero-width insert at p precedes a replace starting at p
    for e in sorted(edits, key=lambda e: (e.start, e.end)):
        if e.start < pos or not 0 <= e.start <= e.end <= len(src):
            raise ValueError("overlapping or out-of-range edits")
        out.append(src[pos:e.start])
        out.append(e.text)
        pos = e.end
    out.append(src[pos:])
    return "".join(out)


def quote(value: str) -> str:
    """Return value as a KiCad quoted string."""
    return '"' + value.translate(_QUOTE_TABLE) + '"'


def _unescape(m: re.Match) -> str:
    return _UNESCAPES.get(m.group(1), m.group(0))


def unquote(token: str) -> str:
    """Return the decoded value of a quoted token, or an atom unchanged."""
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return _ESCAPE_RE.sub(_unescape, token[1:-1])
    return token
