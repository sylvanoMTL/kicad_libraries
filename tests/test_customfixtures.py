"""Self-tests for the synthetic Custom/ the writing tests install into (TEST-01, D-01, D-02).

Each test writes a fresh tree under tmp_path and checks it at its source. None of them reads
the repo's own Custom/.
"""

import pytest

from customfixtures import (
    ABSENT_LIBRARY,
    FORMAT_VERSIONS,
    IMU,
    SYNTHETIC_LIBRARIES,
    UL_PART_TOKENS,
    write_synthetic_custom,
)
from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.layout import list_existing_libraries
from kicad_lib_manager.kicad_files import LoadedFile, file_version, footprint_name, parse_bytes
from zipfixtures import STEP_BYTES


@pytest.fixture
def layout(tmp_path):
    return write_synthetic_custom(tmp_path / "repo")


def _load(path):
    loaded = parse_bytes(path.read_bytes(), path.name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def test_symbol_files_match_the_inventory(layout):
    written = sorted(p.name for p in layout.symbols_dir.iterdir())

    assert written == sorted(f"{lib.name}.kicad_sym" for lib in SYNTHETIC_LIBRARIES)
    assert len(SYNTHETIC_LIBRARIES) == 5


def test_each_symbol_file_has_its_declared_version(layout):
    for lib in SYNTHETIC_LIBRARIES:
        loaded = _load(layout.symbols_dir / f"{lib.name}.kicad_sym")
        assert file_version(loaded.root) == lib.version, lib.name


def test_all_four_format_versions_are_present(layout):
    versions = {file_version(_load(p).root) for p in layout.symbols_dir.glob("*.kicad_sym")}

    assert versions == set(FORMAT_VERSIONS)


def test_libraries_hold_exactly_their_declared_footprints(layout):
    for lib in SYNTHETIC_LIBRARIES:
        pretty = layout.footprints_dir / f"{lib.name}.pretty"
        if lib.footprints:
            assert sorted(p.stem for p in pretty.glob("*.kicad_mod")) == sorted(lib.footprints), lib.name
        else:
            assert not pretty.exists(), lib.name


def test_imu_library_has_symbols_but_no_pretty_folder(layout):
    assert (layout.symbols_dir / f"{IMU}.kicad_sym").is_file()
    assert not (layout.footprints_dir / f"{IMU}.pretty").exists()


def test_new_library_name_does_not_exist(layout):
    assert not (layout.symbols_dir / f"{ABSENT_LIBRARY}.kicad_sym").exists()
    assert not (layout.footprints_dir / f"{ABSENT_LIBRARY}.pretty").exists()


def test_ul_sample_part_is_absent_by_construction(layout):
    tokens = [t.casefold() for t in UL_PART_TOKENS]
    for path in layout.custom_dir.rglob("*"):
        shown = path.relative_to(layout.custom_dir).as_posix().casefold()
        for token in tokens:
            assert token not in shown, f"{token} in path {shown}"
        if path.is_file():
            text = path.read_bytes().decode("utf-8", errors="replace").casefold()
            for token in tokens:
                assert token not in text, f"{token} in content of {shown}"


def test_every_symbol_and_footprint_file_parses(layout):
    for path in layout.symbols_dir.glob("*.kicad_sym"):
        _load(path)
    for path in layout.footprints_dir.glob("*.pretty/*.kicad_mod"):
        loaded = _load(path)
        assert footprint_name(loaded.root).name == path.stem


def test_model_files_are_the_stub_step_bytes(layout):
    expected = sorted(m for lib in SYNTHETIC_LIBRARIES for m in lib.models)
    found = sorted(p.name for p in layout.models_dir.iterdir())

    assert found == expected
    for path in layout.models_dir.iterdir():
        assert path.read_bytes() == STEP_BYTES


def test_footprints_link_the_custom_model_dir(layout):
    for lib in SYNTHETIC_LIBRARIES:
        for index, footprint in enumerate(lib.footprints):
            text = (layout.footprints_dir / f"{lib.name}.pretty" / f"{footprint}.kicad_mod").read_text("utf-8")
            if index < len(lib.models):
                assert f"${{CUSTOM_3DMODEL_DIR}}/{lib.models[index]}" in text
            else:
                assert "(model" not in text


def test_existing_libraries_list_the_five_with_imu_symbols_only(layout):
    listed = {lib.name: lib for lib in list_existing_libraries(layout)}

    assert sorted(listed) == sorted(lib.name for lib in SYNTHETIC_LIBRARIES)
    assert listed[IMU].has_symbols and not listed[IMU].has_footprints
    assert all(lib.has_symbols and lib.has_footprints for name, lib in listed.items() if name != IMU)


def test_writes_nothing_outside_its_root(tmp_path):
    root = tmp_path / "repo"
    sibling = tmp_path / "sibling"
    sibling.mkdir()

    write_synthetic_custom(root)

    assert list(sibling.iterdir()) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["repo", "sibling"]
    assert [p.name for p in root.iterdir()] == ["Custom"]


@pytest.mark.kicad_cli
def test_every_synthetic_library_loads_in_kicad_cli(layout, kicad_cli_path):
    for lib in SYNTHETIC_LIBRARIES:
        footprints = [
            (path.name, path.read_bytes())
            for path in sorted((layout.footprints_dir / f"{lib.name}.pretty").glob("*.kicad_mod"))
        ]
        issues = kicad_cli.load_gate(
            kicad_cli_path,
            library=lib.name,
            symbol_lib=(layout.symbols_dir / f"{lib.name}.kicad_sym").read_bytes(),
            footprints=footprints,
        )
        assert issues == [], (lib.name, issues)
