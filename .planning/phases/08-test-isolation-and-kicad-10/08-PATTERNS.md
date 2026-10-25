# Phase 8: Test Isolation and KiCad 10 - Pattern Map

**Mapped:** 2026-10-25
**Files analyzed:** 14 (new or modified)
**Analogs found:** 14 / 14 (all tracked in git; `tests/conftest.py`, `installfixtures.py`, `zipfixtures.py` confirmed via `git ls-files`)

Test-only phase. No application file changes. Line numbers are from files read this session.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|-------------------|------|-----------|----------------|-------|
| `tests/customfixtures.py` (new) | test helper (writer) | file-I/O | `tests/zipfixtures.py::write_custom_layout` (313-325) | exact |
| `tests/installfixtures.py` (mod: 20251024 style) | test helper (byte builder) | transform | itself: modern branch of `target_lib` (120-167) | exact |
| `tests/conftest.py` (mod: `synthetic_custom`, KiCad 10 gate, `real_tools`, session guard; remove `custom_copy`) | fixture | file-I/O, request-response | itself: `custom_copy` (78-89), `kicad_cli_path` (106-115), `snapshot` (118-132) | exact |
| `tests/test_customfixtures.py` (new) | test | transform | `tests/test_installfixtures.py` | role-match |
| `tests/test_installfixtures.py` (mod: V10 rows, fixed-point real-CLI test) | test | transform | itself (lines 19-23, 96-145 parametrised over versions) | exact |
| `tests/test_install_e2e.py` (mod: scenarios, VER-01 row, UAT hook, drop `real_tools` + live snapshots) | test | request-response | itself: `_SCENARIOS`, `_scenario_*`, `test_uat_scratch_install` (581-607) | exact |
| `tests/test_install_plan.py` (mod: V9 -> V10 in real-CLI tests, drop `_real_tools`) | test | request-response | itself (631-654, 814-827, 1238-1250, 1316-) | exact |
| `tests/test_kicad_cli.py` (mod: drop `real_exe`, 20251024 constants) | test | request-response | itself (569-592) | exact |
| `tests/test_install_apply.py`, `test_import_dialog.py`, `test_import_preview.py`, `test_commit_plan.py` (mod: fixture rename) | test | CRUD | themselves | exact (mechanical) |
| `tests/test_vendor_install.py`, `test_real_vendor_samples.py` (mod: drop local `real_tools`) | test | request-response | `tests/test_install_e2e.py:458-462` (identical copy) | exact |
| `tests/test_naming_suggest.py` (mod, optional: `test_suggest_live_custom` to fixture) | test | read-only | itself (454-458) | exact |
| `tests/test_roundtrip_corpus.py` (maybe mod: Wurth 60 s budget, 240-251) | test | batch | itself | exact |
| `tests/README.md` (new) | doc | n/a | none in tests/; content from skip reasons in `test_roundtrip_corpus.py` (67, 186, 221, 244) and `test_install_e2e.py:581` | partial |
| `.planning/PROJECT.md`, archived `04-UAT.md`, new `08-UAT.md` (mod/new) | planning record | n/a | existing rows quoted in RESEARCH | n/a |

## Pattern Assignments

### `tests/customfixtures.py` (writer, file-I/O)

**Analog:** `tests/zipfixtures.py::write_custom_layout` (313-325). Writer takes a root, writes only under it, returns root.
```python
def write_custom_layout(
    root: Path, symbol_libs: Iterable[str], footprint_libs: Iterable[str]
) -> Path:
    """Create Custom/Symbols, Custom/Footprints and Custom/3DModels under root only."""
    custom = root / "Custom"
    (custom / "3DModels").mkdir(parents=True, exist_ok=True)
    (custom / "Symbols").mkdir(parents=True, exist_ok=True)
    (custom / "Footprints").mkdir(parents=True, exist_ok=True)
    for name in symbol_libs:
        (custom / "Symbols" / f"{name}.kicad_sym").write_bytes(symbol_lib((name,)))
    for name in footprint_libs:
        (custom / "Footprints" / f"{name}.pretty").mkdir(parents=True, exist_ok=True)
    return root
```
Use: `target_lib(version, names)` for symbol bytes (installfixtures), `vendor_footprint(name, ...)` for `.kicad_mod`, `zipfixtures.STEP_BYTES` for model stubs, `RepoLayout.for_repo(repo)` as return value. Imports use the flat style `from installfixtures import ...` / `from zipfixtures import ...`. Public API suggestion: `write_synthetic_custom(root: Path) -> RepoLayout` plus constants (`POWER_MOSFET = "IC_PowerManagementMosfet_TI"`, etc.) so the UAT hook and fixture share one writer.

Inventory (RESEARCH Pattern 1): `IC_Battery_Charger_TI` 20211014 + pretty; `IC_IMU_TDK` 20231120 and NO `.pretty`; `IC_Magnetometer_Memsic` 20241209 + pretty; `IC_PowerManagementMosfet_TI` 20241209 + pretty, no CSD85301Q2; `IC_Wireless_BLE_uBlox` 20251024 + pretty; `IC_MOSFET_Dual_TI` absent. Never add CSD85301Q2 / DQK0006B / its model.

### `tests/installfixtures.py` (20251024 builder)

**Analog:** the modern branch of `target_lib` (120-167) and `_modern_*` helpers (79-117). Current branch:
```python
    if version in _MODERN_GENERATOR_VERSIONS:
        newline = "\n" if eol is None else eol
        library = (
            "kicad_symbol_lib",
            ("version", str(version)),
            ("generator", _quote("kicad_symbol_editor")),
            ("generator_version", _quote(_MODERN_GENERATOR_VERSIONS[version])),
            *(_modern_symbol(name) for name in names),
        )
        return (newline.join(_tree(library)) + newline).encode("utf-8")
    raise ValueError(f"no target library style for format version {version}")
```
Add `20251024: "10.0"` to `_MODERN_GENERATOR_VERSIONS` (line 21) only if the branch dispatches to a separate `_v10_symbol` builder. KiCad 10 differences (RESEARCH Pattern 4): per symbol add `("in_pos_files","yes")`, `("duplicate_pin_numbers_are_jumpers","no")` after `on_board`, trailing `("embedded_fonts","no")`; per property add `("show_name","no")`, `("do_not_autoplace","no")`, and put `("hide","yes")` at property level BEFORE `(effects` (not inside, unlike `_modern_effects` at 79-81); pin names `""` not `"~"`. Reuse `_tree` unchanged. Update module docstring house-style list (lines 8-14). Fixed-point check against real `sym upgrade --force`, comparing with CRLF normalised.

### `tests/conftest.py`

**Fixture replacing `custom_copy`** (analog is `custom_copy`, 78-89; same return type):
```python
@pytest.fixture
def custom_copy(tmp_path):
    ...
    from kicad_lib_manager.importer.layout import RepoLayout
    repo = tmp_path / "repo"
    ...
    return RepoLayout.for_repo(repo)
```
New fixture: lazy-import inside the function (conftest sets `QT_QPA_PLATFORM` at line 10 before any app import; keep all `kicad_lib_manager` imports lazy), write via `customfixtures.write_synthetic_custom(tmp_path / "repo")`. Function-scoped. Remove the `shutil` import if unused.

**KiCad 10 gate** (analog `kicad_cli_path`, 106-115):
```python
    exe = kicad_cli.locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())
    if exe is None:
        pytest.skip("kicad-cli not found")
    return exe
```
Extend per RESEARCH Pattern 2: `@functools.cache _located_kicad_cli()` using `kicad_cli.run_cli(exe, ["version"], timeout=30)` and `re.match(r"\s*(\d+)\.(\d+)")`; constants `KICAD_MAJOR = 10`, `KICAD_SYMBOL_FORMAT = 20251024`, `KICAD_GENERATOR_VERSION = "10.0"`. Move one `real_tools` fixture here (identical copy at test_install_e2e.py:458-462, test_vendor_install.py:475-479, test_real_vendor_samples.py:297-301):
```python
@pytest.fixture
def real_tools(kicad_cli_path):
    tools = detect_tools(find_kicad_footprint_dir())
    assert tools.kicad_cli == kicad_cli_path
    return tools
```
Replace `real_exe` (test_kicad_cli.py:569-574, module-scoped, no major check) and `_real_tools()` (test_install_plan.py:631-635) with these. Test modules cannot import constants from conftest cleanly, so put the constants in `customfixtures.py` (or a small plain module) and import from there.

**Session guard** (analog `snapshot`, 118-132, same sha256 shape): RESEARCH Pattern 3. Make `_digest_live_custom(root: Path)` take the root so a unit test can point it at `tmp_path`. Autouse, `scope="session"`, yield, `pytest.fail(...)` with changed names at teardown. Delete the per-test live snapshots in `test_install_e2e.py` (module `_real_custom_untouched`, ~68/115/135-144) and `test_install_plan.py` (~735/747).

### `tests/test_install_e2e.py`

**Scenario shape to copy** (`_scenario_new_library`, 508-513):
```python
def _scenario_new_library(candidate, layout, tmp_path, tools):
    plan, result = _install(candidate, layout, tmp_path, library=NEW_LIBRARY, tools=tools)
    text = (layout.symbols_dir / f"{NEW_LIBRARY}.kicad_sym").read_text(encoding="utf-8")
    header = text[: text.index("(symbol ")]
    assert "(version 20241209)" in header and '(generator_version "9.0")' in header
    return result, NEW_LIBRARY
```
Replace literals with `f"(version {KICAD_SYMBOL_FORMAT})"` / `KICAD_GENERATOR_VERSION`. Add the VER-01 row `_scenario_target_20241209_as_is` as written in RESEARCH "Code Examples" and register key `"target_20241209_as_is_with_warning"` in `_SCENARIOS`; reuse existing helper `_header` (158-160) and `_written_gate_issues` (465). Retarget `_scenario_newer_target` and `test_cli_second_install_is_noop` to `IC_Wireless_BLE_uBlox`/V10 (RESEARCH retarget table). `_scenario_incoming_newer` (516-537): switch to `vendor_symbol_lib(version=20241209)` instead of reading `IC_Magnetometer_Memsic` bytes + symbol `MMC5983MA` (Pitfall 7).

**UAT hook** (581-607): replace the `copytree` loop with `layout = write_synthetic_custom(uat)`; install into `POWER_MOSFET`; keep T-04-28 asserts and the `skipif(not os.environ.get("KICAD_IMPORT_UAT_DIR"))` decorator; docstring "KiCad 9" -> "KiCad 10"; print paths with `POWER_MOSFET` instead of `LIBRARY`.

### `tests/test_install_plan.py` / `tests/test_kicad_cli.py` (real-CLI retargets)

**Pattern to copy:** existing real-CLI test body (638-654), swapping `V9` for `V10` and `plan.target_version == V10`; keep `"(hide yes)" in block and "(id " not in block`. Header assertions (822-825) become `f"(version {KICAD_SYMBOL_FORMAT})"` and `f'(generator_version "{KICAD_GENERATOR_VERSION}")'`. `test_kicad_cli.py:587,589` use `KICAD_SYMBOL_FORMAT`. Fake-runner tests with `V9`/`SYM_UP`/`FakeCli(output_version=20241209)` stay unchanged (D-07). Define `V10 = 20251024` next to the existing `V9` in each module (or import from the constants module).

### Mechanical renames
`custom_copy` -> new fixture name in `test_install_plan.py` (35 uses), `test_install_e2e.py` (39), `test_install_apply.py` (32), `test_import_dialog.py` (13), `test_import_preview.py` (3), `test_commit_plan.py` (2). Verify with `grep -rn custom_copy tests` returning nothing. `test_import_dialog.py` keeps its separate `item_layout`.

### `tests/test_customfixtures.py` and new unit tests
**Analog:** `tests/test_installfixtures.py` (parametrised over `ALL_VERSIONS`; add `(V10, "10.0")` to `MODERN` and `V10` to `ALL_VERSIONS` at lines 19-23). Contract asserts: four versions present via header parse, `IC_IMU_TDK.pretty` absent, `IC_MOSFET_Dual_TI` absent, no `CSD85301Q2`/`DQK0006B` file or text anywhere under the tree, guard digest reports a changed file on a `tmp_path` tree, gate reasons for none / 9.0.9 / 11.0.0 / unparsable (clear `functools.cache` in the test; monkeypatch `locate_kicad_cli` and `run_cli`).

### `tests/test_roundtrip_corpus.py` (Wurth budget)
Skip pattern already exists (`_WURTH_SKIP_REASON`, lines 67, 221, 244); keep. After `git submodule update --init WurthElektronik/KiCad-Library`, measure with `pytest -m wurth --durations=10`; if `test_wurth_corpus_parse_budget` (240-251, `elapsed < 60`) fails or is within 20 percent, scale with file count. Report, do not fix, any real round-trip failure.

### `tests/README.md`
No analog. Table rows (D-12): no kicad-cli 10 (message from gate), symlinks not permitted (2 tests, Windows privilege), no WurthElektronik submodule, `KICAD_IMPORT_UAT_DIR` unset, `local_kicad` opt-in (`test_roundtrip_corpus.py:186` "no KiCad user config tables found"). Also: suite must not write or depend on live `Custom/`; list read-only live health tests that fail on bad live parts (`test_live_custom_symbols`, `test_sanitize_live_custom_names_unchanged`, `test_live_custom_model_findings_are_zero`).

## Shared Patterns

### Builder rule (all fixture bytes)
**Source:** `tests/installfixtures.py` docstring lines 1-8. Builders return bytes, write nothing, take no paths, stdlib + `zipfixtures._quote` only. Writing lives in `customfixtures.py`/conftest.

### Lazy app imports in conftest
**Source:** `tests/conftest.py:10,78-89`. Set `QT_QPA_PLATFORM` first; import `kicad_lib_manager.*` inside functions.

### Real-binary tests
**Source:** `test_install_plan.py:638` and `test_install_e2e.py`. Decorate with `@pytest.mark.kicad_cli` (marker registered in `pyproject.toml`, `--strict-markers`), obtain the binary only through the shared gate fixture, run through `kicad_cli.run_cli` / `load_gate`. Assert on CRLF-normalised text; slice headers with `_header`.

### Digest/snapshot
**Source:** `tests/conftest.py:118-132`. `{relative path: sha256}` map; factor into a module function shared by `snapshot` and the guard.

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `tests/README.md` | doc | No existing tests documentation; compose from skip messages |
| Session-scoped autouse guard | fixture | No existing session fixture; closest is `snapshot`, plus pytest docs (hooks `pytest_sessionstart` only fire for initial conftests, so use a session fixture) |

## Metadata

**Analog search scope:** `tests/` (conftest, fixtures, e2e, plan, kicad_cli, installfixtures, zipfixtures)
**Files scanned:** about 12 read or grepped, plus RESEARCH/CONTEXT
**Pattern extraction date:** 2026-10-25
