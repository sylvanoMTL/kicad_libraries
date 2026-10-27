"""Official footprint index (LIB-06, D-16): KiCad's installed footprints listed, ranked by name and checked by exact link."""

import os

import pytest

from kicad_lib_manager.importer import footprint_index
from kicad_lib_manager.importer.footprint_index import (
    EMPTY_FOOTPRINT_INDEX,
    RankedFootprint,
    build_index,
    footprint_texts,
    pad_numbers,
    rank,
    rank_with_pads,
)
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from stockfixtures import write_stock_kicad, write_stock_sample

DQK = "Package_SON:Texas_DQK"
SOT = "Package_TO_SOT_SMD:SOT-23-5"
SOIC = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
EIGHT_PADS = {str(n) for n in range(1, 9)}


@pytest.fixture
def sample_index(tmp_path):
    return build_index(write_stock_sample(tmp_path)[1])


def test_no_footprints_folder_gives_the_empty_index():
    assert build_index(None) is EMPTY_FOOTPRINT_INDEX
    assert not EMPTY_FOOTPRINT_INDEX.contains(DQK)


def test_the_index_lists_every_library_and_footprint(sample_index):
    assert sorted(sample_index.libraries) == ["Package_SO", "Package_SON", "Package_TO_SOT_SMD"]
    assert sorted(sample_index.links()) == sorted([DQK, SOT, SOIC])


def test_contains_answers_exact_case_membership(sample_index):
    assert sample_index.contains(DQK)
    assert not sample_index.contains("package_son:texas_dqk")
    assert not sample_index.contains("Package_SON:Texas_dqk")
    assert not sample_index.contains("Package_SON")
    assert not sample_index.contains("Package_SON:Nope")
    assert not sample_index.contains("Nope:Texas_DQK")


def test_the_index_never_lists_the_repo_or_wurth_elektronik(tmp_path):
    _, footprints_dir = write_stock_sample(tmp_path)
    wurth = tmp_path / "WurthElektronik" / "KiCad-Library" / "footprints" / "WE_Fake.pretty"
    wurth.mkdir(parents=True)
    (wurth / "WE-FAKE.kicad_mod").write_bytes(b'(footprint "WE-FAKE")')

    index = build_index(footprints_dir)

    assert "WE_Fake" not in index.libraries
    assert not index.contains("WE_Fake:WE-FAKE")


def test_build_index_is_cached_until_the_folder_changes(tmp_path):
    _, footprints_dir = write_stock_sample(tmp_path)
    first = build_index(footprints_dir)
    assert build_index(footprints_dir) is first

    (footprints_dir / "Package_SO.pretty" / "SOIC-14.kicad_mod").write_bytes(b'(footprint "SOIC-14")')

    second = build_index(footprints_dir)
    assert second is not first
    assert second.contains("Package_SO:SOIC-14")


def test_build_index_reports_progress(tmp_path):
    _, footprints_dir = write_stock_sample(tmp_path)
    calls = []

    build_index(footprints_dir, lambda message, current, total: calls.append((current, total)))

    assert calls
    assert calls[-1][0] == calls[-1][1]


# -- ranking by name ----------------------------------------------------------


def test_the_package_code_leading_letters_find_the_official_footprint(sample_index):
    ranked = rank(sample_index, package_code="DQK0006B")

    assert ranked[0].link == DQK


def test_a_name_holding_the_full_code_beats_one_holding_only_its_leading_letters(tmp_path):
    _, footprints_dir = write_stock_kicad(
        tmp_path,
        {},
        {"Lib_A": (("Foo_DQK", ("1",), "", ""), ("DQK0006B_Custom", ("1",), "", ""))},
    )
    index = build_index(footprints_dir)

    ranked = rank(index, package_code="DQK0006B")

    assert [r.link for r in ranked] == ["Lib_A:DQK0006B_Custom", "Lib_A:Foo_DQK"]
    assert ranked[0].score > ranked[1].score


def test_a_footprint_linked_by_sibling_symbols_beats_every_name_only_match(sample_index):
    ranked = rank(sample_index, package_code="DQK0006B", linked={SOIC: 2})

    assert ranked[0].link == SOIC
    assert ranked[0].score >= 200


def test_family_words_count_as_whole_tokens(sample_index):
    assert rank(sample_index, package_code="", words=("SOT",)) == [RankedFootprint(SOT, 5)]
    assert rank(sample_index, package_code="", words=("sot", "23")) == [RankedFootprint(SOT, 10)]
    # SO is only the start of the token SOIC, never a whole token
    assert rank(sample_index, package_code="", words=("SO",)) == []


def test_links_with_no_match_are_not_returned(sample_index):
    ranked = rank(sample_index, package_code="DQK0006B")

    assert [r.link for r in ranked] == [DQK]
    assert all(r.score > 0 for r in ranked)


def test_a_code_with_fewer_than_three_leading_letters_matches_only_the_full_text(sample_index):
    assert rank(sample_index, package_code="SO") == []


def test_at_most_limit_links_come_back(tmp_path):
    rows = tuple((f"DQK_{n}", ("1",), "", "") for n in range(10))
    _, footprints_dir = write_stock_kicad(tmp_path, {}, {"Lib_A": rows})

    ranked = rank(build_index(footprints_dir), package_code="DQK0006B", limit=4)

    assert len(ranked) == 4


# -- pad numbers, read lazily ---------------------------------------------------


def test_pad_numbers_come_from_the_file_and_are_read_once(tmp_path):
    _, footprints_dir = write_stock_sample(tmp_path)
    index = build_index(footprints_dir)

    assert pad_numbers(index, DQK) == EIGHT_PADS

    (footprints_dir / "Package_SON.pretty" / "Texas_DQK.kicad_mod").unlink()
    assert pad_numbers(index, DQK) == EIGHT_PADS


def test_pad_numbers_of_an_unknown_link_are_none_and_no_path_is_formed(sample_index):
    assert pad_numbers(sample_index, "Package_SON:../../Texas_DQK") is None
    assert pad_numbers(sample_index, "package_son:texas_dqk") is None
    assert pad_numbers(sample_index, "Package_SON:Nope") is None


def test_an_oversized_footprint_file_is_refused(sample_index, monkeypatch):
    monkeypatch.setattr(footprint_index, "MAX_KICAD_TEXT_BYTES", 10)

    assert pad_numbers(sample_index, DQK) is None


def test_rank_with_pads_moves_the_link_with_equal_pad_numbers_ahead(sample_index):
    ranked = [RankedFootprint(SOT, 30), RankedFootprint(DQK, 30)]

    result = rank_with_pads(sample_index, ranked, EIGHT_PADS)

    assert [r.link for r in result] == [DQK, SOT]
    assert result[0].score == 30 + 20 + 20


def test_rank_with_pads_adds_less_when_only_the_count_matches(sample_index):
    ranked = [RankedFootprint(SOIC, 30), RankedFootprint(DQK, 30)]

    result = rank_with_pads(sample_index, ranked, {"A", "B", "C", "D", "E", "F", "G", "H"})

    assert {r.link: r.score for r in result} == {SOIC: 50, DQK: 50}


def test_rank_with_pads_reads_pads_only_for_the_first_top_entries(sample_index):
    ranked = [RankedFootprint(SOT, 30), RankedFootprint(DQK, 30)]

    result = rank_with_pads(sample_index, ranked, EIGHT_PADS, top=1)

    assert [r.link for r in result] == [SOT, DQK]


def test_footprint_texts_return_the_description_and_tags(sample_index):
    assert footprint_texts(sample_index, DQK) == ("Texas WSON-6 DQK, 2x2mm, 0.65mm pitch", "Texas WSON6 2x2mm")


def test_footprint_texts_are_empty_when_absent_or_unreadable(sample_index):
    assert footprint_texts(sample_index, SOT) == ("", "")
    assert footprint_texts(sample_index, "Package_SON:Nope") == ("", "")


# -- the live KiCad 10 footprints ------------------------------------------------

_LIVE_FP_DIR = find_kicad_footprint_dir()


@pytest.mark.skipif(_LIVE_FP_DIR is None, reason="no KiCad install with a footprints folder")
def test_live_kicad_footprints_rank_the_dqk_package_first():
    index = build_index(_LIVE_FP_DIR)

    assert len(index.libraries) > 100
    assert rank(index, package_code="DQK0006B")[0].link == DQK


def test_a_listing_without_the_pretty_suffix_is_not_a_library(tmp_path):
    footprints_dir = tmp_path / "kicad" / "footprints"
    (footprints_dir / "NotALibrary").mkdir(parents=True)
    (footprints_dir / "NotALibrary" / "X.kicad_mod").write_bytes(b'(footprint "X")')
    os.makedirs(footprints_dir / "Real.pretty")
    (footprints_dir / "Real.pretty" / "Y.kicad_mod").write_bytes(b'(footprint "Y")')

    index = build_index(footprints_dir)

    assert sorted(index.libraries) == ["Real"]
