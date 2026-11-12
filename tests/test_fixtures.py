"""Self-checks for the frozen fixtures: byte-exact, trait-true, tracked as -text, not ignored."""

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from kicad_lib_manager import fsutil, sexpr

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
FIXTURE_SUBDIRS = ("sexpr", "tables")

BOM = b"\xef\xbb\xbf"
TAB = b"\t"


def _load_builder():
    path = FIXTURES_DIR / "build_fixtures.py"
    spec = importlib.util.spec_from_file_location("build_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURES: dict[str, bytes] = _load_builder().FIXTURES

# Every fixture claims one trait through its name; this table is the explicit claim
TRAITS = {
    "sexpr/lf.kicad_sym": "lf",
    "sexpr/crlf.kicad_sym": "crlf",
    "sexpr/bom.kicad_sym": "lf+bom",
    "sexpr/mixed_eol.kicad_sym": "mixed",
    "sexpr/escapes.kicad_sym": "lf",
    "sexpr/bare_atoms.kicad_mod": "lf",
    "sexpr/two_models.kicad_mod": "crlf",
    "sexpr/legacy_module.kicad_mod": "lf",
    "sexpr/no_trailing_newline.kicad_mod": "lf+noeol",
    "tables/basic.sym-lib-table": "lf",
    "tables/escaped.sym-lib-table": "crlf",
    "tables/empty.sym-lib-table": "lf",
    "tables/reordered.fp-lib-table": "lf",
    "tables/flags.fp-lib-table": "crlf",
}

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")


def _disk_files() -> set[str]:
    found = set()
    for sub in FIXTURE_SUBDIRS:
        for p in (FIXTURES_DIR / sub).rglob("*"):
            if p.is_file():
                found.add(p.relative_to(FIXTURES_DIR).as_posix())
    return found


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )


def test_builder_keys_are_safe_and_traits_cover_all():
    assert set(TRAITS) == set(FIXTURES)
    for key in FIXTURES:
        rel = Path(key)
        assert not rel.is_absolute() and ".." not in rel.parts, key
        assert key.split("/")[0] in FIXTURE_SUBDIRS, key


def test_disk_set_equals_builder_set():
    assert _disk_files() == set(FIXTURES)


@pytest.mark.parametrize("key", sorted(FIXTURES))
def test_disk_bytes_equal_builder_bytes(key):
    assert (FIXTURES_DIR / key).read_bytes() == FIXTURES[key], key


def _count(data: bytes) -> tuple[int, int, int]:
    """Return (crlf, bare_lf, bare_cr) counts."""
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


@pytest.mark.parametrize("key", sorted(TRAITS))
def test_fixture_has_claimed_trait(key):
    data = (FIXTURES_DIR / key).read_bytes()
    trait = TRAITS[key]
    crlf, lf, cr = _count(data)
    if trait == "crlf":
        assert crlf > 0 and lf == 0 and cr == 0, f"{key}: expected pure CRLF"
    elif trait == "lf":
        assert crlf == 0 and cr == 0, f"{key}: expected no CR"
    elif trait == "lf+bom":
        assert data.startswith(BOM) and crlf == 0 and cr == 0, f"{key}: expected BOM + LF"
    elif trait == "mixed":
        assert crlf > lf > 0 and cr == 0, f"{key}: expected CRLF majority with some LF"
    elif trait == "lf+noeol":
        assert crlf == 0 and cr == 0 and data.endswith(b")"), f"{key}: expected no trailing EOL"
    else:  # pragma: no cover
        pytest.fail(f"unknown trait {trait!r} for {key}")


@needs_git
@pytest.mark.parametrize("key", sorted(FIXTURES))
def test_fixture_is_text_unset(key):
    result = _git("check-attr", "text", "--", f"tests/fixtures/{key}")
    assert result.returncode == 0, key
    assert result.stdout.strip().endswith("text: unset"), f"{key}: {result.stdout.strip()}"


@needs_git
@pytest.mark.parametrize("key", sorted(FIXTURES))
def test_fixture_is_not_git_ignored(key):
    result = _git("check-ignore", "-q", f"tests/fixtures/{key}")
    assert result.returncode == 1, f"{key}: git ignores this path"


def test_no_pretty_directory_under_tests():
    assert [p for p in TESTS_DIR.rglob("*.pretty") if p.is_dir()] == []


@pytest.mark.parametrize("key", sorted(FIXTURES))
def test_fixture_decodes_and_parses(key):
    data = (FIXTURES_DIR / key).read_bytes()
    source = fsutil.decode_source(data, Path(key).name)
    assert isinstance(source, fsutil.SourceText), key
    sexpr.parse(source.text)


# D-02 lib-table edge cases: (case id, fixture key, check over the committed bytes)
def _last_lib_tail(data: bytes) -> bytes:
    return data[data.rindex(b"(lib"):]


D02_CASES = [
    (
        "escaped_quote",
        "tables/escaped.sym-lib-table",
        lambda d: b'\\"quotes\\"' in d,
    ),
    (
        "escaped_backslash",
        "tables/escaped.sym-lib-table",
        lambda d: b"C:\\\\KiCad\\\\libs" in d,
    ),
    (
        "reordered_fields",
        "tables/reordered.fp-lib-table",
        lambda d: 0 <= d.find(b"(uri") < d.find(b"(name"),
    ),
    (
        "odd_whitespace_spaces",
        "tables/reordered.fp-lib-table",
        lambda d: re.search(rb"\) {3}\(", d) is not None,
    ),
    (
        "odd_whitespace_tab",
        "tables/reordered.fp-lib-table",
        lambda d: re.search(rb"\)" + TAB + rb"\(", d) is not None,
    ),
    (
        "odd_whitespace_linebreak",
        "tables/reordered.fp-lib-table",
        lambda d: re.search(rb"\)\n +\(descr", d) is not None,
    ),
    (
        "missing_options_descr",
        "tables/reordered.fp-lib-table",
        lambda d: (
            b'"Minimal"' in _last_lib_tail(d)
            and b"(options" not in _last_lib_tail(d)
            and b"(descr" not in _last_lib_tail(d)
        ),
    ),
    (
        "disabled_flag",
        "tables/flags.fp-lib-table",
        lambda d: b"(disabled)" in d,
    ),
    (
        "hidden_flag",
        "tables/flags.fp-lib-table",
        lambda d: b"(hidden)" in d,
    ),
    (
        "unknown_child",
        "tables/flags.fp-lib-table",
        lambda d: b'(future_field "x")' in d,
    ),
    (
        "empty_table",
        "tables/empty.sym-lib-table",
        lambda d: b"(version 7)" in d and b"(lib" not in d,
    ),
]


@pytest.mark.parametrize(
    ("case", "key", "check"),
    D02_CASES,
    ids=[case for case, _, _ in D02_CASES],
)
def test_table_fixtures_cover_d02_edge_cases(case, key, check):
    data = (FIXTURES_DIR / key).read_bytes()
    assert check(data), f"D-02 case {case} missing from {key}"
