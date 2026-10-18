import random
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from kicad_lib_manager.sexpr import Node, SexprError, apply_edits, parse, unquote


def _spans(root: Node) -> list[tuple[int, int, str]]:
    """Return (start, end, kind) for every node in document order, iteratively."""
    out = []
    stack = [iter(root.children)]
    while stack:
        node = next(stack[-1], None)
        if node is None:
            stack.pop()
            continue
        out.append((node.start, node.end, node.kind))
        if node.children:
            stack.append(iter(node.children))
    return out


def _check(text: str, assert_tiles) -> Node:
    """Parse text, prove it tiles and that an empty splice reproduces it."""
    root = parse(text)
    assert_tiles(text, root)
    assert apply_edits(text, []) == text
    return root


# -- Tokenizer edge cases ---------------------------------------------------


def test_empty_input_has_empty_root(assert_tiles):
    root = _check("", assert_tiles)
    assert (root.start, root.end) == (0, 0)
    assert root.kind == "root"
    assert root.children == []


def test_whitespace_only_input_has_no_children(assert_tiles):
    root = _check("  \r\n\t ", assert_tiles)
    assert root.children == []


@pytest.mark.parametrize("text", ["(a)", "(a)\r\n", "(a)\n", "  (a)  "])
def test_single_form_with_and_without_trailing_newline(text, assert_tiles):
    root = _check(text, assert_tiles)
    assert len(root.children) == 1
    assert root.children[0].kind == "list"
    assert root.children[0].head == "a"


def test_empty_list_has_no_children_and_no_head(assert_tiles):
    root = _check("()", assert_tiles)
    (node,) = root.children
    assert node.kind == "list"
    assert node.children == []
    assert node.head is None


def test_empty_string_token(assert_tiles):
    root = _check('""', assert_tiles)
    (node,) = root.children
    assert node.kind == "str"
    assert node.text == '""'
    assert unquote(node.text) == ""


def test_adjacent_forms_touch_and_tile(assert_tiles):
    root = _check("(a)(b)", assert_tiles)
    first, second = root.children
    assert first.end == second.start
    assert (first.head, second.head) == ("a", "b")


def test_adjacent_nested_forms_are_in_document_order(assert_tiles):
    text = '(lib (name "x")(type "y"))'
    root = _check(text, assert_tiles)
    (lib,) = root.children
    _, name, typ = lib.children
    assert name.head == "name" and typ.head == "type"
    assert name.end == typ.start
    assert name.start < typ.start


@pytest.mark.parametrize(
    "text",
    [
        '"a (b) c"',
        r'"say \"hi\""',
        r'"C:\\dir\\"',
        r'"\\"',
        '"10kΩ"',
    ],
)
def test_tricky_strings_are_single_str_tokens(text, assert_tiles):
    root = _check(text, assert_tiles)
    (node,) = root.children
    assert node.kind == "str"
    assert node.text == text


@pytest.mark.parametrize(
    "text",
    ["${KICAD_LIB_GITHUB}/x.kicad_sym", "F.Cu", "*.Cu", "µ"],
)
def test_atoms_with_punctuation_stay_single_atoms(text, assert_tiles):
    root = _check(f"(x {text})", assert_tiles)
    atom = root.children[0].children[1]
    assert atom.kind == "atom"
    assert atom.text == text


def test_numeric_atoms_keep_exact_source_text(assert_tiles):
    root = _check("(at 1.0160 -0 1e-3 -12.7)", assert_tiles)
    texts = [c.text for c in root.children[0].children]
    assert texts == ["at", "1.0160", "-0", "1e-3", "-12.7"]
    assert all(c.kind == "atom" for c in root.children[0].children)


@pytest.mark.parametrize("sep", ["\u00a0", "\x0c", "\u2028"])
def test_non_ascii_and_formfeed_do_not_split_atoms(sep, assert_tiles):
    text = f"(a b{sep}c)"
    root = _check(text, assert_tiles)
    atoms = root.children[0].children
    assert [c.text for c in atoms] == ["a", f"b{sep}c"]


# -- Error positions --------------------------------------------------------


def test_unterminated_string_reports_opening_quote():
    with pytest.raises(SexprError) as exc:
        parse('(a "b)')
    assert exc.value.code == "sexpr.unterminated"
    assert (exc.value.line, exc.value.col) == (1, 4)


def test_stray_close_paren_is_unbalanced():
    with pytest.raises(SexprError) as exc:
        parse("(a))")
    assert exc.value.code == "sexpr.unbalanced"
    assert (exc.value.line, exc.value.col) == (1, 4)


def test_unclosed_reports_innermost_open_paren_with_crlf():
    with pytest.raises(SexprError) as exc:
        parse("(a\r\n  (b")
    err = exc.value
    assert err.code == "sexpr.unclosed"
    assert (err.line, err.col) == (2, 3)
    assert "line 2, col 3" in str(err)


def test_crlf_and_lf_report_the_same_line_numbers():
    lf = "(a\n(b)\n  \"oops"
    crlf = lf.replace("\n", "\r\n")
    with pytest.raises(SexprError) as e_lf:
        parse(lf)
    with pytest.raises(SexprError) as e_crlf:
        parse(crlf)
    assert e_lf.value.line == e_crlf.value.line == 3
    assert e_lf.value.col == e_crlf.value.col == 3


def test_sexpr_error_is_a_value_error_with_attributes():
    err = SexprError("sexpr.unclosed", "msg", 4, 5)
    assert isinstance(err, ValueError)
    assert (err.code, err.line, err.col) == ("sexpr.unclosed", 4, 5)


# -- Hostile input ----------------------------------------------------------


def test_deep_nesting_parses_without_recursion_and_repr_is_short(assert_tiles):
    depth = 100_000
    text = "(" * depth + ")" * depth
    root = parse(text)
    node = root
    while node.children:
        node = node.children[0]
    assert len(repr(root)) < 100
    assert len(repr(node)) < 100
    assert_tiles(text, root)
    assert apply_edits(text, []) == text


def _symbol_library(count: int) -> str:
    parts = ['(kicad_symbol_lib (version 20211014) (generator "test")\n']
    filler = "capacitor ceramic " * 30
    for i in range(count):
        parts.append(
            f'  (symbol "PART_{i}" (in_bom yes) (on_board yes)\n'
            f'    (property "Reference" "U" (id 0) (at 0 0 0))\n'
            f'    (property "Value" "PART_{i}" (id 1) (at 0 0 0))\n'
            f'    (property "Footprint" "Lib:FP_{i}" (id 2) (at 0 0 0))\n'
            f'    (property "Description" "Part \\"{i}\\" (rev {i})" (id 3) (at 0 0 0))\n'
            f'    (property "ki_keywords" "{filler}" (id 4) (at 0 0 0))\n'
            f'    (symbol "PART_{i}_0_1"\n'
            f'      (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254)))\n'
            f'      (pin input line (at -7.62 2.54 0) (length 2.54) (name "IN{i}") (number "1"))\n'
            f'    )\n'
            f'  )\n'
        )
    parts.append(")\n")
    return "".join(parts)


def test_large_library_parses_within_budget():
    text = _symbol_library(2_000)
    assert len(text) > 1_800_000  # ~2 MB
    t0 = time.perf_counter()
    root = parse(text)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0, f"parse took {elapsed:.2f}s"
    assert len(root.children[0].children) > 2_000


def _random_form(rng: random.Random, depth: int = 0) -> str:
    ws = [" ", "  ", "\t", "\n", "\r\n", " \r\n  "]
    atoms = ["a", "F.Cu", "-12.7", "1e-3", "${VAR}/x", "µ", "*.Cu"]
    strs = [r'"plain"', r'"(paren)"', r'"q\"uote"', r'"back\\"', r'""', '"10kΩ"']
    items = []
    for _ in range(rng.randint(0, 5)):
        pick = rng.random()
        if pick < 0.35 and depth < 6:
            items.append(_random_form(rng, depth + 1))
        elif pick < 0.7:
            items.append(rng.choice(atoms))
        else:
            items.append(rng.choice(strs))
    # Adjacent items may touch only when a bracket separates them
    out = "("
    for i, item in enumerate(items):
        if i:
            out += rng.choice(ws)
        out += item
    return out + rng.choice(["", " ", "\n"]) + ")"


def test_seeded_fuzz_tiles_and_round_trips(assert_tiles):
    rng = random.Random(1234)
    for _ in range(500):
        text = "".join(_random_form(rng) + rng.choice(["", " ", "\n", "\r\n"]) for _ in range(rng.randint(1, 3)))
        root = parse(text)
        assert_tiles(text, root)
        assert apply_edits(text, []) == text


def test_assert_tiles_rejects_shifted_span(assert_tiles):
    text = "(a b)"
    root = parse(text)
    atom = root.children[0].children[1]
    shifted = Node(atom.start + 1, atom.end + 1, atom.kind, [], atom.text)
    root.children[0].children[1] = shifted
    with pytest.raises(AssertionError):
        assert_tiles(text, root)


def test_parse_is_thread_safe_and_deterministic():
    text = _symbol_library(200)
    assert 150_000 < len(text) < 260_000
    expected = _spans(parse(text))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _spans(parse(text)), range(8)))
    assert all(r == expected for r in results)
