import os
import re
from pathlib import Path

import pytest

# Force (not setdefault): a developer shell with another platform must not open real windows
os.environ["QT_QPA_PLATFORM"] = "offscreen"

REPO_ROOT = Path(__file__).resolve().parent.parent

_GAP_RE = re.compile(r"[ \t\r\n]*")
_ATOM_BAD_RE = re.compile(r'[ \t\r\n()"]')


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def _collect_tokens(root) -> list[tuple[int, int, str, object]]:
    """Walk nodes iteratively and return (start, end, kind, node) token spans in document order."""
    tokens = []
    stack = [iter(root.children)]
    closers = [None]
    while stack:
        node = next(stack[-1], None)
        if node is None:
            stack.pop()
            closer = closers.pop()
            if closer is not None:
                tokens.append((closer.end - 1, closer.end, "close", closer))
            continue
        if node.kind == "list":
            tokens.append((node.start, node.start + 1, "open", node))
            stack.append(iter(node.children))
            closers.append(node)
        else:
            tokens.append((node.start, node.end, node.kind, node))
    return tokens


@pytest.fixture
def assert_tiles():
    """Return a checker proving node spans plus gaps cover the text exactly."""

    def check(text: str, root) -> None:
        pos = 0
        for start, end, kind, node in _collect_tokens(root):
            assert start >= pos, f"token {kind} at {start} overlaps previous token ending {pos}"
            assert _GAP_RE.fullmatch(text, pos, start), (
                f"gap {pos}:{start} before {kind} token is not pure space/tab/CR/LF"
            )
            if kind == "open":
                assert text[start] == "(", f"list at {start} does not start with '('"
            elif kind == "close":
                assert text[start] == ")", f"list ending at {end} does not end with ')'"
            elif kind == "str":
                assert text[start:end] == node.text, f"str node at {start}:{end} text mismatch"
                assert end - start >= 2 and text[start] == '"' and text[end - 1] == '"', (
                    f"str node at {start}:{end} is not double-quoted"
                )
            elif kind == "atom":
                assert text[start:end] == node.text, f"atom node at {start}:{end} text mismatch"
                assert end > start and not _ATOM_BAD_RE.search(node.text), (
                    f"atom node at {start}:{end} contains a separator or quote"
                )
            pos = end
        assert _GAP_RE.fullmatch(text, pos, len(text)), (
            f"trailing gap {pos}:{len(text)} is not pure space/tab/CR/LF"
        )

    return check
