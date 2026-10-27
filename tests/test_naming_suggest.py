"""Fresh Custom/ listing and the datasheet-to-manufacturer helpers (D-03, D-23, LIB-01).

The Atomic_ library suggestion itself is tested in test_suggest_atomic.py.
"""

from pathlib import Path

import pytest
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer.candidate import ExistingLibrary
from kicad_lib_manager.importer.layout import (
    RepoLayout,
    list_existing_libraries,
    list_footprint_libs,
    list_model_files,
    list_symbol_libs,
)
from kicad_lib_manager.importer.suggest import (
    datasheet_host,
    is_aggregator_host,
    manufacturer_from_datasheet,
    registered_domain,
)


def _current_layout(tmp_path: Path) -> RepoLayout:
    root = write_custom_layout(tmp_path, CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(root)


def _snapshot(root: Path) -> list[tuple[str, bool]]:
    return sorted((p.relative_to(root).as_posix(), p.is_dir()) for p in root.rglob("*"))


# -- Task 1: fresh Custom/ listing (D-03) ------------------------------------------------


def test_layout_lists_fresh(tmp_path):
    layout = _current_layout(tmp_path)
    libs = list_existing_libraries(layout)
    expected = sorted(CURRENT_CUSTOM_SYMBOL_LIBS, key=lambda n: (n.casefold(), n))
    assert [lib.name for lib in libs] == expected
    assert len(libs) == 10
    by_name = {lib.name: lib for lib in libs}
    assert by_name["IC_IMU_TDK"] == ExistingLibrary("IC_IMU_TDK", True, False)
    assert all(
        lib.has_symbols and lib.has_footprints for name, lib in by_name.items() if name != "IC_IMU_TDK"
    )
    # Stray files are not libraries
    (layout.symbols_dir / "readme.txt").write_text("x", encoding="utf-8")
    (layout.footprints_dir / "x.kicad_mod").write_text("x", encoding="utf-8")
    assert len(list_existing_libraries(layout)) == 10
    # A library added between two calls shows up on the second (never cached)
    (layout.symbols_dir / "IC_LDO_TI.kicad_sym").write_bytes(symbol_lib(("IC_LDO_TI",)))
    after = list_existing_libraries(layout)
    assert len(after) == 11
    assert ExistingLibrary("IC_LDO_TI", True, False) in after


def test_layout_missing_custom_and_read_only(tmp_path):
    missing = RepoLayout.for_repo(tmp_path / "none")
    assert list_symbol_libs(missing) == []
    assert list_footprint_libs(missing) == []
    assert list_model_files(missing) == []
    assert list_existing_libraries(missing) == []
    assert not (tmp_path / "none").exists()
    layout = _current_layout(tmp_path / "repo")
    before = _snapshot(tmp_path)
    list_symbol_libs(layout)
    list_footprint_libs(layout)
    list_model_files(layout)
    list_existing_libraries(layout)
    assert _snapshot(tmp_path) == before


def test_layout_folders_follow_the_custom_convention(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    assert layout.repo_root == tmp_path
    assert layout.custom_dir == tmp_path / "Custom"
    assert layout.symbols_dir == tmp_path / "Custom" / "Symbols"
    assert layout.footprints_dir == tmp_path / "Custom" / "Footprints"
    assert layout.models_dir == tmp_path / "Custom" / "3DModels"


def test_layout_model_files(tmp_path):
    layout = _current_layout(tmp_path)
    (layout.models_dir / "a.step").write_bytes(b"x")
    (layout.models_dir / "sub").mkdir()
    (layout.models_dir / "sub" / "x.step").write_bytes(b"x")
    assert list_model_files(layout) == ["a.step", "sub/x.step"]


# -- datasheet host helpers (D-23) -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "host"),
    [
        ("https://www.ti.com/lit/ds/x.pdf", "www.ti.com"),
        ("https://E2E.TI.COM:443/a", "e2e.ti.com"),
        ("www.ti.com/lit/x", "www.ti.com"),
        ("//www.ti.com/x", "www.ti.com"),
        ("https://www.ti.com./x", "www.ti.com"),
        ("", None),
        ("   ", None),
        ("~", None),
        ("file:///C:/x.pdf", None),
        ("http://[bad", None),
        ("localhost", None),
    ],
)
def test_datasheet_host(value, host):
    assert datasheet_host(value) == host


@pytest.mark.parametrize(
    ("host", "domain"),
    [
        ("www.ti.com", "ti.com"),
        ("e2e.ti.com", "ti.com"),
        ("invensense.tdk.com", "tdk.com"),
        ("ti.com", "ti.com"),
        ("www.murata.co.jp", "murata.co.jp"),
        ("www.gct.co", "gct.co"),
        ("www.example.co.uk", "example.co.uk"),
    ],
)
def test_registered_domain(host, domain):
    assert registered_domain(host) == domain


def test_is_aggregator_host():
    assert is_aggregator_host("www.snapeda.com")
    assert is_aggregator_host("www.mouser.co.uk")
    assert is_aggregator_host("WWW.DIGIKEY.COM")
    assert not is_aggregator_host("www.ti.com")
    assert not is_aggregator_host("www.murata.co.jp")


# -- the one datasheet-to-manufacturer path (D-23) -----------------------------------------------


@pytest.mark.parametrize(
    ("datasheet", "expected"),
    [
        ("https://www.ti.com/lit/ds/symlink/csd85301q2.pdf", ("Texas Instruments", None)),
        ("https://e2e.ti.com/x", ("Texas Instruments", None)),
        ("https://E2E.TI.COM:443/a", ("Texas Instruments", None)),
        ("www.ti.com/lit/x", ("Texas Instruments", None)),
        ("https://www.maximintegrated.com/en/products/x.pdf", ("Maxim Integrated", None)),
        ("https://www.linear.com/docs/1234", ("Linear Technology", None)),
        ("https://invensense.tdk.com/x.pdf", ("TDK", None)),
        ("http://www.gct.co/x", ("Global Connector Technology", None)),
        ("https://www.example-parts.com/ds.pdf", ("", None)),
        ("https://www.digikey.com/en/products/x", ("", "www.digikey.com")),
        ("https://www.snapeda.com/parts/x/datasheet", ("", "www.snapeda.com")),
        ("~", ("", None)),
        ("", ("", None)),
        ("file:///C:/x.pdf", ("", None)),
        ("http://[bad", ("", None)),
    ],
)
def test_manufacturer_from_datasheet(datasheet, expected):
    assert manufacturer_from_datasheet(datasheet) == expected


def test_manufacturer_from_datasheet_keeps_an_acquired_brand_own_name():
    # Maxim Integrated stays Maxim Integrated, never Analog Devices (D-08)
    assert manufacturer_from_datasheet("https://www.maximintegrated.com/x.pdf")[0] == "Maxim Integrated"
    assert manufacturer_from_datasheet("https://www.analog.com/x.pdf")[0] == "Analog Devices"


def test_manufacturer_from_datasheet_never_names_a_distributor_as_the_company():
    # The aggregator host comes back so the caller can say why no manufacturer was filled in
    for host in ("www.mouser.co.uk", "www.octopart.com", "componentsearchengine.com", "ultralibrarian.com"):
        name, aggregator = manufacturer_from_datasheet(f"https://{host}/datasheet/x.pdf")
        assert name == ""
        assert aggregator == host


def test_manufacturer_from_datasheet_is_the_only_datasheet_to_manufacturer_path():
    from kicad_lib_manager.importer import suggest

    # No v1.0 library-token helper is left beside it (D-23)
    left = [n for n in dir(suggest) if "token" in n.casefold() or "choice" in n.casefold()]
    assert left == []
    assert callable(suggest.manufacturer_from_datasheet)


