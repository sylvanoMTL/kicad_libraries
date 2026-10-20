import hashlib
import os
import re
import shutil
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


@pytest.fixture
def custom_copy(tmp_path):
    """A RepoLayout over a tmp_path copy of the real Custom/ libraries; the checkout is never written."""
    source = REPO_ROOT / "Custom"
    if not (source / "Symbols").is_dir():
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    from kicad_lib_manager.importer.layout import RepoLayout

    repo = tmp_path / "repo"
    for name in ("Symbols", "Footprints", "3DModels"):
        shutil.copytree(source / name, repo / "Custom" / name)
    return RepoLayout.for_repo(repo)


@pytest.fixture
def ul_package():
    """Yield (package, candidate) for the Ultra Librarian sample; the package is closed afterwards."""
    from kicad_lib_manager.importer.detect import detect_candidate
    from kicad_lib_manager.importer.package import open_package

    package = open_package(REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip", REPO_ROOT)
    try:
        candidate, _ = detect_candidate(package)
        yield package, candidate
    finally:
        package.close()


@pytest.fixture
def kicad_cli_path() -> Path:
    """The kicad-cli of the installed KiCad (located as the app does); skips when there is none."""
    from kicad_lib_manager.importer import kicad_cli
    from kicad_lib_manager.library_scanner import find_kicad_footprint_dir

    exe = kicad_cli.locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())
    if exe is None:
        pytest.skip("kicad-cli not found")
    return exe


@pytest.fixture
def snapshot():
    """Return a function mapping a folder to {relative path: sha256} for files and {relative path/: "dir"} for folders."""

    def take(root: Path) -> dict[str, str]:
        found: dict[str, str] = {}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_dir():
                found[rel + "/"] = "dir"
            else:
                found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return found

    return take
