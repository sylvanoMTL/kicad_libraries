"""User-facing text never names the KiCad command-line tool or KiCad's settings file by its raw name.

Owner rule G-12-5 (plain language): say "the KiCad command-line tool" and "KiCad's settings file".
This test parses every module under kicad_lib_manager and fails when a string constant outside a
docstring contains one of the two search tokens, "kicad-cli" or "kicad_common.json".
"""

import ast
from pathlib import Path

# The tokens include the ".json" extension on purpose, so the on-disk backup folder segment
# "kicad_common" in sync_kicad_path_vars is not matched. That folder name is data the code reads
# and writes; it must never be renamed to satisfy this test.
SEARCH_TOKENS = ("kicad-cli", "kicad_common.json")

# The program and file names the code uses to find and open them. They are not text a user reads.
ALLOWED_BARE_NAMES = frozenset({"kicad-cli", "kicad-cli.exe", "kicad_common.json"})

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "kicad_lib_manager"
_SCAN_AT_LEAST = 20


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """The ids of the string nodes that are docstrings: first statement of a module, class or function."""
    found: set[int] = set()
    scopes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, scopes) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def test_no_user_text_names_kicad_cli_or_its_settings_file():
    files = sorted(PACKAGE_DIR.rglob("*.py"))
    assert len(files) > _SCAN_AT_LEAST, f"only {len(files)} files found under {PACKAGE_DIR}"

    offenders: list[str] = []
    allowed_seen: set[str] = set()
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if id(node) in docstrings:
                continue
            text = node.value
            if not any(token in text for token in SEARCH_TOKENS):
                continue
            if text in ALLOWED_BARE_NAMES:
                allowed_seen.add(text)
                continue
            offenders.append(f"{path.relative_to(PACKAGE_DIR.parent).as_posix()}:{node.lineno}:{text!r}")

    assert allowed_seen, "no allowed bare name was seen, so the scan looks at the wrong place"
    assert not offenders, (
        "User-facing text must say 'the KiCad command-line tool' and \"KiCad's settings file\", "
        "not the raw names:\n" + "\n".join(offenders)
    )
