"""Self-tests for the synthetic Custom/ the writing tests install into (TEST-01, D-01, D-02).

Each test writes a fresh tree under tmp_path and checks it at its source. None of them reads
the repo's own Custom/.
"""

import pytest

from customfixtures import (
    ABSENT_LIBRARY,
    BATTERY_CHARGER,
    FORMAT_VERSIONS,
    SYNTHETIC_LIBRARIES,
    UL_PART_TOKENS,
    V1_ABSENT_LIBRARY,
    V1_IMU,
    V1_LIBRARY_NAMES,
    write_synthetic_custom,
)
from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.layout import list_existing_libraries
from kicad_lib_manager.importer.plan import InstallOptions
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import (
    LoadedFile,
    file_version,
    find_property,
    find_symbol,
    footprint_name,
    parse_bytes,
)
from zipfixtures import STEP_BYTES, footprint_library_for


@pytest.fixture
def layout(tmp_path):
    return write_synthetic_custom(tmp_path / "repo")


def _load(path):
    loaded = parse_bytes(path.read_bytes(), path.name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def test_symbol_files_match_the_inventory(layout):
    written = sorted(p.name for p in layout.symbols_dir.iterdir())

    assert written == sorted(f"{name}.kicad_sym" for name in V1_LIBRARY_NAMES)
    assert len(SYNTHETIC_LIBRARIES) == 5


def test_each_symbol_file_has_its_declared_version(layout):
    for lib in SYNTHETIC_LIBRARIES:
        loaded = _load(layout.symbols_dir / f"{lib.v1_name}.kicad_sym")
        assert file_version(loaded.root) == lib.version, lib.v1_name


def test_all_four_format_versions_are_present(layout):
    versions = {file_version(_load(p).root) for p in layout.symbols_dir.glob("*.kicad_sym")}

    assert versions == set(FORMAT_VERSIONS)


def test_libraries_hold_exactly_their_declared_footprints(layout):
    for lib in SYNTHETIC_LIBRARIES:
        pretty = layout.footprints_dir / f"{lib.v1_name}.pretty"
        if lib.footprints:
            assert sorted(p.stem for p in pretty.glob("*.kicad_mod")) == sorted(lib.footprints), lib.v1_name
        else:
            assert not pretty.exists(), lib.v1_name


def test_imu_library_has_symbols_but_no_pretty_folder(layout):
    assert (layout.symbols_dir / f"{V1_IMU}.kicad_sym").is_file()
    assert not (layout.footprints_dir / f"{V1_IMU}.pretty").exists()


def test_new_library_name_does_not_exist(layout):
    assert not (layout.symbols_dir / f"{V1_ABSENT_LIBRARY}.kicad_sym").exists()
    assert not (layout.footprints_dir / f"{V1_ABSENT_LIBRARY}.pretty").exists()


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
            text = (layout.footprints_dir / f"{lib.v1_name}.pretty" / f"{footprint}.kicad_mod").read_text("utf-8")
            if index < len(lib.models):
                assert f"${{CUSTOM_3DMODEL_DIR}}/{lib.models[index]}" in text
            else:
                assert "(model" not in text


def test_existing_libraries_list_the_five_with_imu_symbols_only(layout):
    listed = {lib.name: lib for lib in list_existing_libraries(layout)}

    assert sorted(listed) == sorted(V1_LIBRARY_NAMES)
    assert listed[V1_IMU].has_symbols and not listed[V1_IMU].has_footprints
    assert all(lib.has_symbols and lib.has_footprints for name, lib in listed.items() if name != V1_IMU)


def test_writes_nothing_outside_its_root(tmp_path):
    root = tmp_path / "repo"
    sibling = tmp_path / "sibling"
    sibling.mkdir()

    write_synthetic_custom(root)

    assert list(sibling.iterdir()) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["repo", "sibling"]
    assert [p.name for p in root.iterdir()] == ["Custom"]


def test_naming_v1_writes_exactly_the_v1_names(tmp_path):
    layout = write_synthetic_custom(tmp_path / "repo", naming="v1")

    assert sorted(p.stem for p in layout.symbols_dir.glob("*.kicad_sym")) == sorted(V1_LIBRARY_NAMES)
    assert sorted(p.stem for p in layout.footprints_dir.glob("*.pretty")) == sorted(
        lib.v1_name for lib in SYNTHETIC_LIBRARIES if lib.footprints
    )


def test_naming_atomic_writes_the_atomic_names(atomic_custom):
    assert sorted(p.stem for p in atomic_custom.symbols_dir.glob("*.kicad_sym")) == sorted(
        lib.name for lib in SYNTHETIC_LIBRARIES
    )
    assert not (atomic_custom.symbols_dir / f"{ABSENT_LIBRARY}.kicad_sym").exists()
    for lib in SYNTHETIC_LIBRARIES:
        pretty = atomic_custom.footprints_dir / f"{footprint_library_for(lib.name)}.pretty"
        if lib.footprints:
            written = {p.stem for p in pretty.glob("*.kicad_mod")}
            assert set(lib.footprints) <= written, lib.name
    with_footprints = {footprint_library_for(lib.name) for lib in SYNTHETIC_LIBRARIES if lib.footprints}
    assert {p.stem for p in atomic_custom.footprints_dir.glob("*.pretty")} == with_footprints


def test_naming_other_raises(tmp_path):
    with pytest.raises(ValueError, match="v1.*atomic"):
        write_synthetic_custom(tmp_path / "repo", naming="other")


def test_atomic_custom_writes_nothing_outside_its_root(atomic_custom, tmp_path):
    assert sorted(p.name for p in tmp_path.iterdir()) == ["repo"]
    assert [p.name for p in (tmp_path / "repo").iterdir()] == ["Custom"]


def test_atomic_install_target_plans_through_footprint_library_for(atomic_custom, ul_package):
    _, candidate = ul_package
    footprint_lib = footprint_library_for(BATTERY_CHARGER)

    plan = build_plan(candidate, InstallOptions(library=BATTERY_CHARGER), atomic_custom)

    assert not plan.blocked, plan.issues
    footprint_ops = [op for op in plan.ops if op.kind == "footprint"]
    assert [op.path for op in footprint_ops] == [
        atomic_custom.footprints_dir / f"{footprint_lib}.pretty" / "DQK0006B.kicad_mod"
    ]
    symbol_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    symbol = find_symbol(_parsed(symbol_op).root, "CSD85301Q2")
    assert find_property(symbol.node, "Footprint").value == f"{footprint_lib}:DQK0006B"


def _parsed(op):
    loaded = parse_bytes(op.data, op.path.name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


@pytest.mark.kicad_cli
def test_every_synthetic_library_loads_in_kicad_cli(layout, kicad_cli_path):
    for lib in SYNTHETIC_LIBRARIES:
        footprints = [
            (path.name, path.read_bytes())
            for path in sorted((layout.footprints_dir / f"{lib.v1_name}.pretty").glob("*.kicad_mod"))
        ]
        issues = kicad_cli.load_gate(
            kicad_cli_path,
            library=lib.v1_name,
            symbol_lib=(layout.symbols_dir / f"{lib.v1_name}.kicad_sym").read_bytes(),
            footprints=footprints,
        )
        assert issues == [], (lib.v1_name, issues)


# ── The session write-protect guard over the live Custom/ (TEST-03, D-13) ────────────────────


def _tree(root):
    (root / "Symbols").mkdir(parents=True)
    (root / "Symbols" / "a.kicad_sym").write_bytes(b"one")
    (root / "Footprints" / "A.pretty").mkdir(parents=True)
    (root / "Footprints" / "A.pretty" / "x.kicad_mod").write_bytes(b"two")
    (root / "3DModels").mkdir()
    (root / "3DModels" / "m.step").write_bytes(b"three")
    return root


def test_digest_tree_maps_files_to_sha256_and_folders_to_dir(tmp_path):
    from customfixtures import digest_tree

    root = tmp_path / "t"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "f.bin").write_bytes(b"abc")

    assert digest_tree(root) == {
        "sub/": "dir",
        "sub/f.bin": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    }


def test_snapshot_fixture_returns_digest_tree(snapshot, tmp_path):
    from customfixtures import digest_tree

    root = _tree(tmp_path / "t")

    assert snapshot(root) == digest_tree(root)


def test_digest_custom_is_none_without_a_symbols_folder(tmp_path):
    from customfixtures import digest_custom

    assert digest_custom(tmp_path / "missing") is None
    empty = tmp_path / "empty"
    empty.mkdir()
    assert digest_custom(empty) is None


def test_digest_custom_keys_the_three_watched_folders(tmp_path):
    from customfixtures import digest_custom

    custom = _tree(tmp_path / "Custom")
    (custom / "README.md").write_bytes(b"not watched")

    digest = digest_custom(custom)

    assert sorted(digest) == [
        "3DModels/",
        "3DModels/m.step",
        "Footprints/",
        "Footprints/A.pretty/",
        "Footprints/A.pretty/x.kicad_mod",
        "Symbols/",
        "Symbols/a.kicad_sym",
    ]


def test_custom_changes_is_empty_for_equal_digests():
    from customfixtures import custom_changes

    assert custom_changes({"a": "1", "b/": "dir"}, {"b/": "dir", "a": "1"}) == []


def test_custom_changes_reports_changed_added_removed_and_new_folder():
    from customfixtures import custom_changes

    before = {"Symbols/": "dir", "Symbols/keep": "1", "Symbols/edit": "1", "Symbols/gone": "1"}
    after = {"Symbols/": "dir", "Symbols/keep": "1", "Symbols/edit": "2", "Symbols/new": "9", "Symbols/empty/": "dir"}

    assert custom_changes(before, after) == ["Symbols/edit", "Symbols/empty/", "Symbols/gone", "Symbols/new"]


def _run_guarded(tmp_path, *, touch: bool):
    import os
    import subprocess
    import sys
    from pathlib import Path

    tests_dir = Path(__file__).resolve().parent
    watched = tmp_path / "watched" / "Custom"
    (watched / "Symbols").mkdir(parents=True)
    (watched / "Symbols" / "a.kicad_sym").write_bytes(b"original")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "conftest.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "import pytest\n"
        "from customfixtures import guard_custom\n"
        "\n"
        "@pytest.fixture(scope='session', autouse=True)\n"
        "def _guard():\n"
        "    yield from guard_custom(Path(os.environ['GUARD_CUSTOM_DIR']))\n",
        encoding="utf-8",
    )
    body = (
        "import os\n"
        "from pathlib import Path\n"
        "def test_touch():\n"
        "    target = Path(os.environ['GUARD_CUSTOM_DIR']) / 'Symbols' / 'a.kicad_sym'\n"
        "    with target.open('ab') as handle:\n"
        "        handle.write(b'x')\n"
        if touch
        else "def test_touch():\n    assert True\n"
    )
    (run_dir / "test_touch.py").write_text(body, encoding="utf-8")
    env = dict(os.environ)
    env["GUARD_CUSTOM_DIR"] = str(watched)
    env["PYTHONPATH"] = os.pathsep.join([str(tests_dir), str(tests_dir.parent)])
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(run_dir)],
        cwd=run_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_guard_failure_fails_the_run(tmp_path):
    done = _run_guarded(tmp_path, touch=True)

    assert done.returncode != 0, done.stdout
    assert "changed the live Custom/ folder" in done.stdout
    assert "Symbols/a.kicad_sym" in done.stdout


def test_guard_quiet_run_passes(tmp_path):
    done = _run_guarded(tmp_path, touch=False)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "changed the live Custom/ folder" not in done.stdout


def test_watching_an_absent_or_empty_custom_is_a_no_op(tmp_path):
    from customfixtures import guard_custom

    absent = tmp_path / "absent"
    empty = tmp_path / "empty"
    empty.mkdir()
    for custom in (absent, empty):
        gen = guard_custom(custom)
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)
