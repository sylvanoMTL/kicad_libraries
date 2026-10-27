"""What a footprint is and the description and tags made from it (FLD-03, D-28, D-29).

The tracer test runs the Ultra Librarian DQK0006B footprint from the committed zip through the
facts, the sentence, the tags and the write back into the file. The rest pins the geometry and text
rules on built footprints, the real vendor samples and KiCad's stock footprints.
"""

import zipfile

import pytest
from zipfixtures import REPO_ROOT, UL_FOOTPRINT_MEMBER, UL_ZIP

from kicad_lib_manager.importer import footprint_text as ft
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.kicad_files import LoadedFile, footprint_name, footprint_text_edit, load, parse_bytes
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from kicad_lib_manager.sexpr import apply_edits

UL_CODE = "DQK0006B"
UL_TEXTS = ["Texas WSON-6 DQK, 2x2mm, 0.65mm pitch"]
UL_DESCRIBE = "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B"
UL_TAGS = ["WSON-6", "WSON-6_2.1x2.1mm_P0.65mm", "DQK0006B", "P0.65mm"]


def _load(data: bytes) -> LoadedFile:
    loaded = parse_bytes(data, "fixture")
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def ul_footprint_bytes() -> bytes:
    with zipfile.ZipFile(UL_ZIP) as zf:
        return zf.read(UL_FOOTPRINT_MEMBER)


def test_ul_footprint_facts():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    assert facts.pads == 8
    assert facts.pitch == 0.65
    assert facts.body == (2.1, 2.1)
    assert facts.family == "WSON-6"
    assert (facts.code, facts.maker) == (UL_CODE, "TI")


def test_ul_footprint_sentence_and_tags():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    assert ft.describe(facts) == UL_DESCRIBE
    assert ft.ipc_name(facts) == "WSON-6_2.1x2.1mm_P0.65mm"
    assert ft.generated_tags(facts) == UL_TAGS


def test_ul_footprint_text_is_written_back():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    text, eol = loaded.source.text, loaded.source.eol
    edits = [
        footprint_text_edit(text, node, "descr", ft.describe(facts), eol),
        footprint_text_edit(text, node, "tags", " ".join(ft.generated_tags(facts)), eol),
    ]
    out = apply_edits(text, edits)
    after = footprint_name(_load(out.encode("utf-8")).root).node
    assert ft.vendor_texts(after) == (UL_DESCRIBE, " ".join(UL_TAGS))


# -- builders ------------------------------------------------------------------


def _fp(*items: str, head: str = "footprint", name: str = "FP") -> bytes:
    """A footprint with the given child lines after (layer "F.Cu")."""
    body = "".join(f"  {item}\n" for item in items)
    return f'({head} "{name}"\n  (layer "F.Cu")\n{body})\n'.encode("utf-8")


def _node(data: bytes):
    return footprint_name(_load(data).root).node


def _pad(number: str, x: float, y: float = 0.0, kind: str = "smd") -> str:
    return f'(pad "{number}" {kind} rect (at {x:g} {y:g}) (size 0.5 0.5) (layers "F.Cu"))'


def _line(layer: str, x1: float, y1: float, x2: float, y2: float, quoted: bool = True) -> str:
    layer_text = f'"{layer}"' if quoted else layer
    return f"(fp_line (start {x1:g} {y1:g}) (end {x2:g} {y2:g}) (layer {layer_text}) (width 0.1))"


def _box(layer: str, w: float, h: float, quoted: bool = True) -> list[str]:
    return [
        _line(layer, 0, 0, w, 0, quoted),
        _line(layer, w, 0, w, h, quoted),
        _line(layer, w, h, 0, h, quoted),
        _line(layer, 0, h, 0, 0, quoted),
    ]


# -- pitch ---------------------------------------------------------------------


def test_pitch_needs_two_pads():
    assert ft.pitch_mm([]) is None
    assert ft.pitch_mm([(0.0, 0.0)]) is None


def test_pitch_of_two_pads():
    assert ft.pitch_mm([(0.0, 0.0), (1.27, 0.0)]) == 1.27


def test_pitch_is_the_distance_that_repeats():
    # Nearest neighbours are 1, 1 and 2: only 1 occurs twice
    assert ft.pitch_mm([(0.0, 0.0), (1.0, 0.0), (3.0, 0.0)]) == 1


def test_pitch_takes_the_smallest_repeated_distance():
    # Nearest neighbours are 1, 1, 3, 3 on a spread-out second pair: 1 is the smaller repeat
    assert ft.pitch_mm([(0.0, 0.0), (1.0, 0.0), (10.0, 0.0), (13.0, 0.0)]) == 1


def test_pitch_rounds_to_hundredths():
    assert ft.pitch_mm([(0.0, 0.0), (0.649999, 0.0)]) == 0.65


def test_pitch_ignores_pads_on_the_same_centre():
    assert ft.pitch_mm([(0.0, 0.0), (0.0, 0.0)]) is None
    assert ft.pitch_mm([(0.0, 0.0), (0.0, 0.0), (0.5, 0.0), (1.0, 0.0)]) == 0.5


def test_pitch_gives_up_on_a_huge_pad_count():
    centres = [(float(i), 0.0) for i in range(ft._MAX_PITCH_PADS + 1)]
    assert ft.pitch_mm(centres) is None


# -- pad centres ---------------------------------------------------------------


def test_pad_centres_skip_holes_and_unnumbered_pads():
    from installfixtures import vendor_footprint

    node = _node(vendor_footprint(pads=("1", "2", "3"), npth=True))
    assert ft.pad_centres(node) == [(0.0, 0.0), (1.5, 0.0), (3.0, 0.0)]


def test_pad_centres_skip_a_numbered_hole_and_an_empty_number():
    node = _node(_fp(_pad("1", 0), _pad("", 1), _pad("5", 2, kind="np_thru_hole"), _pad("2", 3)))
    assert ft.pad_centres(node) == [(0.0, 0.0), (3.0, 0.0)]


def test_pad_centres_skip_unreadable_positions():
    bad = '(pad "3" smd rect (at x y) (size 1 1))'
    nan = '(pad "4" smd rect (at nan 1) (size 1 1))'
    none = '(pad "5" smd rect (size 1 1))'
    assert ft.pad_centres(_node(_fp(_pad("1", 0), bad, nan, none))) == [(0.0, 0.0)]


# -- body ----------------------------------------------------------------------


def test_body_prefers_the_fab_outline_over_the_courtyard():
    node = _node(_fp(*_box("F.CrtYd", 7.4, 5.4), *_box("F.Fab", 3.9, 4.9)))
    assert ft.body_mm(node) == (3.9, 4.9)


def test_body_falls_back_to_the_courtyard():
    assert ft.body_mm(_node(_fp(*_box("F.CrtYd", 7.4, 5.4)))) == (7.4, 5.4)


def test_body_is_unknown_without_an_outline():
    assert ft.body_mm(_node(_fp(_pad("1", 0), _line("F.SilkS", 0, 0, 3, 3)))) is None


def test_body_reads_a_bare_layer_token():
    assert ft.body_mm(_node(_fp(*_box("F.Fab", 2.1, 2.1, quoted=False)))) == (2.1, 2.1)


def test_body_covers_rect_poly_circle_and_arc():
    rect = "(fp_rect (start -1 -1) (end 1 1) (layer F.Fab) (width 0.1))"
    poly = '(fp_poly (pts (xy 0 0) (xy 4 0) (xy 4 2)) (layer "F.Fab") (width 0.1))'
    circle = '(fp_circle (center 0 0) (end 3 0) (layer "F.Fab") (width 0.1))'
    arc = '(fp_arc (start 0 0) (mid 1 1.5) (end 2 0) (layer "F.Fab") (width 0.1))'
    assert ft.body_mm(_node(_fp(rect))) == (2.0, 2.0)
    assert ft.body_mm(_node(_fp(poly))) == (4.0, 2.0)
    assert ft.body_mm(_node(_fp(circle))) == (6.0, 6.0)
    assert ft.body_mm(_node(_fp(arc))) == (2.0, 1.5)


def test_body_skips_an_outline_with_no_area():
    node = _node(_fp(_line("F.Fab", 0, 0, 3, 0), *_box("F.CrtYd", 4, 3)))
    assert ft.body_mm(node) == (4.0, 3.0)


# -- family --------------------------------------------------------------------


def test_family_from_compact_text():
    assert ft.package_family(["Texas WSON6 2x2mm"]) == "WSON-6"


def test_family_sot_keeps_its_pin_count():
    assert ft.package_family(["SOT-23-5"]) == "SOT-23-5"
    assert ft.package_family(["Package SOT23"]) == "SOT-23"
    assert ft.package_family(["SOT-223-3_TabPin2"]) == "SOT-223-3"


def test_family_from_an_ipc_style_name():
    assert ft.package_family(["SOIC-8_3.9x4.9mm_P1.27mm"]) == "SOIC-8"


def test_family_unknown():
    assert ft.package_family(["CSD85301Q2 "]) is None
    assert ft.package_family([]) is None
    assert ft.package_family(["DIPLEXER 0402", "persona 12"]) is None


def test_family_first_text_wins():
    assert ft.package_family(["nothing here", "QFN-32 5x5", "SOIC-8"]) == "QFN-32"


def test_family_read_from_the_footprints_own_text_before_the_extra_texts():
    node = _node(_fp('(descr "Texas WSON-6 DQK")', '(tags "WSON6")'))
    assert ft.footprint_facts(node, code="DQK", maker="TI", texts=["SOIC-8"]).family == "WSON-6"


# -- sentence and tags ---------------------------------------------------------


def _facts(**kw) -> ft.FootprintFacts:
    base = dict(pads=0, pitch=None, body=None, family=None, code="DQK0006B", maker="TI")
    base.update(kw)
    return ft.FootprintFacts(**base)


def test_describe_with_only_maker_and_code():
    assert ft.describe(_facts()) == "TI DQK0006B"


def test_describe_leaves_out_the_missing_body():
    assert ft.describe(_facts(family="WSON-6", pitch=0.65)) == "WSON-6, 0.65 mm pitch, TI DQK0006B"


def test_describe_with_nothing_known_is_empty():
    assert ft.describe(_facts(code="", maker="")) == ""


def test_describe_prints_numbers_without_trailing_zeros():
    assert ft.describe(_facts(body=(2.0, 2.0), pitch=1.0)) == "2x2 mm, 1 mm pitch, TI DQK0006B"
    assert ft.describe(_facts(body=(21.8, 9.2), pitch=2.54)) == "21.8x9.2 mm, 2.54 mm pitch, TI DQK0006B"
    assert ft.describe(_facts(pitch=0.5)).startswith("0.5 mm pitch")


def test_describe_stays_on_one_line():
    assert ft.describe(_facts(code="A\nB  C", maker="T\tI")) == "T I A B C"


def test_ipc_name_needs_family_body_and_pitch():
    full = _facts(family="SOIC-8", body=(3.9, 4.9), pitch=1.27)
    assert ft.ipc_name(full) == "SOIC-8_3.9x4.9mm_P1.27mm"
    assert ft.ipc_name(_facts(family=None, body=(3.9, 4.9), pitch=1.27)) is None
    assert ft.ipc_name(_facts(family="SOIC-8", body=None, pitch=1.27)) is None
    assert ft.ipc_name(_facts(family="SOIC-8", body=(3.9, 4.9), pitch=None)) is None


def test_generated_tags_leave_out_the_unknown():
    assert ft.generated_tags(_facts()) == ["DQK0006B"]
    assert ft.generated_tags(_facts(code="", pitch=2.54)) == ["P2.54mm"]
    assert ft.generated_tags(_facts(code="", maker="")) == []


def test_a_footprint_with_one_pad_and_no_outline_falls_back_to_maker_and_code():
    node = _node(_fp(_pad("1", 0)))
    facts = ft.footprint_facts(node, code="DQK0006B", maker="TI")
    assert (facts.pads, facts.pitch, facts.body, facts.family) == (1, None, None, None)
    assert ft.describe(facts) == "TI DQK0006B"


# -- real samples and stock footprints -----------------------------------------

_SAMPLES = REPO_ROOT / "downloaded_examples"


def _sample_footprint(zip_name: str) -> tuple[bytes, str]:
    path = _SAMPLES / zip_name
    if not path.exists():
        pytest.skip(f"downloaded_examples/{zip_name} not present (licence-restricted vendor sample, kept local)")
    with open_package(path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        item = candidate.footprints[0]
        return item.file.path.read_bytes(), item.root_head


def test_real_ul_atxk_pitch_prints_without_a_decimal():
    data, head = _sample_footprint("ul_ATXK-H14-D-32-768KHZ-E50-T3.zip")
    facts = ft.footprint_facts(_node(data), code="ATXK-H14", maker="Abracon")
    assert head == "footprint"
    assert facts.pitch == 1.0
    assert "1 mm pitch" in ft.describe(facts)


def test_real_samacsys_legacy_module_footprint():
    data, head = _sample_footprint("LIB_RS3-1212S_H3.zip")
    assert head == "module"
    facts = ft.footprint_facts(_node(data), code="RS3", maker="RECOM")
    assert facts.pads == 7
    assert facts.pitch == 2.54
    assert facts.body == (21.8, 9.2)


def test_real_snapeda_footprint_pitch():
    data, _ = _sample_footprint("USB4145-03-0170-C_REVA2.zip")
    facts = ft.footprint_facts(_node(data), code="USB4145", maker="GCT")
    # 22 pad blocks, two of them mounting holes (np_thru_hole)
    assert facts.pads == 20
    assert facts.pitch == 0.5


def _stock(library: str, name: str) -> LoadedFile:
    fp_dir = find_kicad_footprint_dir()
    path = fp_dir / f"{library}.pretty" / f"{name}.kicad_mod" if fp_dir is not None else None
    if path is None or not path.is_file():
        pytest.skip("no KiCad install with a stock symbols folder")
    loaded = load(path)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def test_stock_texas_dqk():
    node = footprint_name(_stock("Package_SON", "Texas_DQK").root).node
    facts = ft.footprint_facts(node, code="DQK", maker="TI")
    assert facts.pitch == 0.65
    assert facts.body == (2.0, 2.0)
    assert facts.family == "WSON-6"


def test_stock_soic8():
    node = footprint_name(_stock("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm").root).node
    # Its own text says "SOIC, 8 Pin", so the family comes from the name the planner passes in
    facts = ft.footprint_facts(node, code="", maker="", texts=["SOIC-8_3.9x4.9mm_P1.27mm"])
    assert facts.pitch == 1.27
    assert facts.body == (3.9, 4.9)
    assert facts.family == "SOIC-8"
    assert ft.ipc_name(facts) == "SOIC-8_3.9x4.9mm_P1.27mm"
