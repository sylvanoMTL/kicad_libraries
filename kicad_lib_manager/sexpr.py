import re
import sys
from dataclasses import dataclass

# Separators are ASCII space/tab/CR/LF only, like KiCad's lexer (never the regex \s class)
# A string is only opened here; _string_end finds where it closes. bad keeps "every position
# matches" true, so _TOKEN.match never returns None.
_TOKEN = re.compile(
    r'(?P<open>\()'
    r'|(?P<close>\))'
    r'|(?P<quote>")'
    r'|(?P<atom>[^ \t\r\n()"]+)'
    r'|(?P<ws>[ \t\r\n]+)'
    r'|(?P<bad>.)',
    re.S,
)

# Escape pairs matched per regex call: bounds the backtracking state the regex engine keeps for a
# repeated group, whatever the string length.
_STRING_WINDOW = 1024
_STRING_BODY = re.compile(r'[^"\\]*(?:\\.[^"\\]*){0,%d}' % _STRING_WINDOW, re.S)

# KiCad's writer escapes exactly these four; TAB stays raw
_QUOTE_TABLE = str.maketrans({
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
})

_UNESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
_ESCAPE_RE = re.compile(r"\\(.)", re.S)
# A lone surrogate, which strict UTF-8 decoding never produces, so it never occurs in file text
_BACKSLASH_PLACEHOLDER = "\ud800"
_PAIR_ESCAPES = ((r'\"', '"'), (r"\n", "\n"), (r"\r", "\r"), (r"\t", "\t"))


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


def _string_end(text: str, start: int) -> int:
    """Return the offset just past the closing quote of the string opening at start, or -1 when it is unterminated."""
    pos = start + 1
    while True:
        pos = _STRING_BODY.match(text, pos).end()
        if pos == len(text):
            return -1
        if text[pos] == '"':
            return pos + 1
        # A backslash starts the next window; as the last character it escapes nothing
        if pos == len(text) - 1:
            return -1


def parse(text: str, *, max_nodes: int | None = None) -> Node:
    """Parse text into a span-carrying tree, raising SexprError at the first bad token.

    max_nodes caps the lists, atoms and strings built (the root is not counted); the token
    that would cross it raises sexpr.too_many_nodes. None means no limit. String ends are
    found by a linear scan, so one long string costs no more than its own text.
    """
    root = Node(0, len(text), "root", [])
    # Explicit stack: no recursion limit on deeply nested input
    stack = [root]
    limit = sys.maxsize if max_nodes is None else max_nodes
    count = 0
    pos = 0
    size = len(text)
    while pos < size:
        m = _TOKEN.match(text, pos)
        kind = m.lastgroup
        start = m.start()
        end = m.end()
        if kind == "quote":
            end = _string_end(text, start)
            if end < 0:
                raise SexprError(
                    "sexpr.unterminated",
                    "unterminated string or stray character",
                    *_line_col(text, start),
                )
            kind = "str"
        pos = end
        if kind == "ws":
            continue
        if kind == "bad":
            raise SexprError(
                "sexpr.unterminated",
                "unterminated string or stray character",
                *_line_col(text, start),
            )
        if kind != "close":
            count += 1
            if count > limit:
                raise SexprError(
                    "sexpr.too_many_nodes",
                    f"more than {max_nodes} nodes",
                    *_line_col(text, start),
                )
        if kind == "open":
            node = Node(start, -1, "list", [])
            stack[-1].children.append(node)
            stack.append(node)
        elif kind == "close":
            if len(stack) == 1:
                raise SexprError(
                    "sexpr.unbalanced",
                    "unbalanced ')'",
                    *_line_col(text, start),
                )
            stack.pop().end = end
        else:
            stack[-1].children.append(Node(start, end, kind, [], text[start:end]))
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
        body = token[1:-1]
        if "\\" not in body:
            return body
        if _BACKSLASH_PLACEHOLDER in body:
            return _ESCAPE_RE.sub(_unescape, body)
        # str.replace pairs each run of backslashes from its left end, exactly as the regex does, so
        # after the first pass every remaining backslash is the last of an odd run and escapes the
        # next character. No replacement emits a backslash, so the passes cannot interact.
        body = body.replace("\\\\", _BACKSLASH_PLACEHOLDER)
        for escape, char in _PAIR_ESCAPES:
            body = body.replace(escape, char)
        return body.replace(_BACKSLASH_PLACEHOLDER, "\\")
    return token
