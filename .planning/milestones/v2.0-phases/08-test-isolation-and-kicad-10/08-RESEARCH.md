# Phase 8: Test Isolation and KiCad 10 - Research

**Researched:** 2026-10-25
**Domain:** pytest test-suite isolation (synthetic `Custom/` fixture), KiCad 10 (format 20251024) kicad-cli gating, one D-01 re-test
**Confidence:** HIGH (every behavioural claim below was reproduced against the installed kicad-cli 10.0.7 in a scratch directory outside the repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Synthetic Custom/ fixture (TEST-01)**
- **D-01:** Replace the `custom_copy` fixture (`tests/conftest.py`, copies the live `Custom/Symbols|Footprints|3DModels`) with an isolated `Custom/` **built in code**. It is a *format mirror*: one symbol library per format version the real `Custom/` holds today, 20211014, 20231120, 20241209 and 20251024. Each has a few footprints in a matching `.pretty/` and stub 3D model files. The Ultra Librarian sample part (CSD85301Q2 / DQK0006B / its model) is **absent by construction**, so tests never depend on what the owner has installed. Follow the existing builder rule in `tests/installfixtures.py`: builders return bytes, write nothing and take no paths. A fixture function writes them under `tmp_path`.
- **D-02:** Fixture libraries use **today's v1 names**, mirroring the real ones (e.g. `IC_Battery_Charger_TI` at 20211014, `IC_IMU_TDK` at 20231120, `IC_PowerManagementMosfet_TI` at 20241209, a 20251024 library such as `IC_Wireless_BLE_uBlox`). The library names the 14 tests already reference (`IC_Battery_Charger_TI`, `IC_Test_TI`, `IC_MOSFET_Dual_TI` as a new library, etc.) keep working without rewriting assertions. Phase 10 will add `Atomic_` libraries to this same fixture. — **Reversibility:** reversible — test-only names.
- **D-03:** The KiCad 10 (20251024) house style for the new builder is taken from **real kicad-cli 10 output** (header layout, `(generator_version "10.0")`, `(embedded_fonts no)`, CRLF/LF as written). It is checked once against a real `sym upgrade` run and documented in the builder's docstring, as the 20211014 and 20231120/20241209 styles were. Don't just bump the version number on the 20241209 builder.
- **D-04:** Tests that only **read** the live `Custom/` stay as they are and pass whatever it holds. These include the round-trip corpus (`test_roundtrip_corpus.py`), `test_edits.py` reading `Connector_USB_GCT.kicad_sym`, and scanner checks. They keep skipping when the submodule isn't checked out. Only tests that write to a copy or assume which parts exist move to the synthetic fixture.

**KiCad version targeting (TEST-02)**
- **D-05:** Real kicad-cli tests **pin KiCad 10 exactly**: expected symbol format `20251024` and `(generator_version "10.0")` as named constants. A test that runs the real binary **skips with a stated reason unless the located kicad-cli is major version 10**. That covers both "only KiCad 9 installed" and a future KiCad 11, so newer output gets reviewed rather than silently accepted. Discovery stays as the app does it (`locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())`, picks the newest; 10.0 on this workstation, where 9.0 is also installed).
- **D-06:** KiCad 9 real-CLI tests are **retargeted to their KiCad 10 equivalents**, keeping each test's intent:
  - "normalised into a 20241209 library" -> normalised into a **20251024** library;
  - the 20241209 target becomes the **as-is-with-warning** row (this is VER-01);
  - a new library gets the **KiCad 10 header**;
  - the deterministic-upgrade and second-install-is-noop tests expect 20251024.

  No KiCad 9 expectation remains in any test that runs the real binary.
- **D-07:** Fake-runner unit tests that use 20241209 constants (e.g. `SYM_UP` in `test_kicad_cli.py`, `V9` in `test_install_plan.py`, `FakeCli(output_version=20241209)`) are **left unchanged**. They don't start a process, they pass, and D-01 is version-generic logic.

**D-01 re-test on KiCad 10 (VER-01)**
- **D-08:** Close backlog 999.1 with **an automated test plus one manual KiCad check**:
  - Automated (real kicad-cli 10, marked `kicad_cli`): install the UL sample into the fixture's **20241209** library. Assert the D-01 as-is WARNING naming both versions, the library header still `(version 20241209)`, the vendor symbol spliced unchanged, and `kicad_cli.load_gate` with kicad-cli 10 returning no issues.
  - Manual: the owner opens the installed library in KiCad 10's Symbol Editor and places the part.
- **D-09:** The manual check uses a **scratch copy** through the existing `KICAD_IMPORT_UAT_DIR` hook (`tests/test_install_e2e.py::test_uat_scratch_install`). The real `Custom/` is never touched. Today that hook copies the live `Custom/` and installs into `IC_Battery_Charger_TI` (20211014). For VER-01 it must target a **20241209** library that doesn't already hold the part. The live `IC_PowerManagementMosfet_TI` now contains CSD85301Q2, so build the scratch tree from the synthetic fixture or otherwise guarantee the part is absent. Update its docstring from "KiCad 9 UAT" to KiCad 10.
- **D-10:** Record the outcome in the **Phase 8 UAT file**:
  - add a closing note to the archived `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md` Test 2 pointing to it;
  - update the PROJECT.md Key Decisions row for the kicad-cli normalisation policy from "re-test still open (backlog 999.1)" to verified on KiCad 10;
  - update the "KiCad 10 is the reference version" row, which is pending on the 7 kicad-cli tests.

**Skips and regression guard (TEST-03)**
- **D-11:** **Check out the WurthElektronik submodule in this worktree** (`git submodule update --init WurthElektronik/KiCad-Library`), so the 3 Wurth stress/round-trip tests run on the workstation. This is a one-off setup step; the skip stays in code for machines without it. After that, the expected workstation skips are the 2 symlink-privilege skips and the `KICAD_IMPORT_UAT_DIR` one.
- **D-12:** Document the expected skips in a new **`tests/README.md`** table with one row per skip condition. The conditions are: no kicad-cli 10, symlinks not permitted, no WurthElektronik submodule, `KICAD_IMPORT_UAT_DIR` unset, and any `local_kicad` opt-in. Each row says why and how to enable it. The existing `pytest.skip(...)` messages stay. Also note there that the suite must not write to or depend on the contents of the live `Custom/`.
- **D-13:** Add a **write-protect guard**: a session-scoped check (e.g. in `tests/conftest.py`) hashes the live `Custom/` (Symbols, Footprints, 3DModels) before the run and fails the session if anything changed afterwards. The `custom_copy` fixture is removed, so nothing copies the live tree any more. Read-only corpus tests still pass under the guard. The guard must be cheap: about 19 MB of models plus about 430 KB of KiCad text. Hash once per session, or compare size and mtime with a hash fallback, at Claude's discretion.

### Claude's Discretion
- Fixture shape and API: one session- or function-scoped fixture vs a builder function, its name, and how many symbols, footprints and models each library holds, as long as D-01/D-02 hold and every D-01 version row is reachable.
- How the "kicad-cli is major 10" check is implemented. It could parse `kicad-cli version`, or use the install path's version folder. Add a shared fixture, e.g. replace `kicad_cli_path` / `real_exe` / `_real_tools` with one helper that applies the KiCad 10 skip.
- Guard implementation details under D-13.
- Whether to refresh the stale `.planning/codebase/TESTING.md` (it still says "no tests exist"). Optional; `tests/README.md` is the required doc.

### Deferred Ideas (OUT OF SCOPE)
None. Discussion stayed within phase scope. (Run time of 5+ minutes was noted but not raised as a goal.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | The test suite passes whatever parts the owner's `Custom/` holds. Tests that need a target library build an isolated synthetic `Custom/` instead of copying the live one. | Fixture design (section "Synthetic Custom/ fixture"), exact library inventory the 14 tests need, 20251024 builder prototype that is a fixed point of `kicad-cli sym upgrade --force`, list of read-only live tests that still assert part-dependent state |
| TEST-02 | The real kicad-cli tests expect KiCad 10 output (symbol format 20251024), and skip with a stated reason when kicad-cli 10 is absent. | Full inventory of every real-binary test and which helper locates the CLI, `kicad-cli version` parse (verified output `10.0.7`), per-test retarget table |
| TEST-03 | Developer runs `pytest` on the workstation and gets 0 failures, with only documented skips. | Skip inventory, write-protect guard design, **Wurth checkout risk (parse budget)**, README skip table content |
| VER-01 | The D-01 "install as-is with warning" case is re-tested on KiCad 10 (backlog 999.1). | Reproduced the scenario against real kicad-cli 10.0.7: planner already behaves as specified, no product change needed; exact asserted strings, manual-check hook retarget |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Both `./CLAUDE.md` and `./.claude/CLAUDE.md` were read. Directives that bind this phase:

- Python 3.10+ (venv on 3.14), PySide6 6.12, **stdlib only** otherwise unless a dependency is clearly justified. This phase needs no new dependency.
- Windows 11 primary, standard CPython (not MSYS2). Run tests with `env/Scripts/python.exe -m pytest` from the repo root.
- **Safety:** no write without a preview; writes atomic or backed up; git commits need explicit confirmation. The suite must never write the live `Custom/` (D-13 makes this enforceable).
- Do not change app behaviour in this phase (CONTEXT domain). Report product findings instead of fixing them.
- Conventions: snake_case, narrow exception handling, early returns, `pathlib.Path` for all file work, keep surrounding file style, no formatter config (4-space indent, double quotes, f-strings).
- GSD workflow: file edits happen inside a GSD command (this research is the only write, and it is the planning artifact).
- Memory: plain-language UI text (no raw field names in user-facing importer text). Not touched by this phase.
- `human_verify_mode: end-of-phase` in `.planning/config.json`: the manual KiCad 10 Symbol Editor check (D-08) is a human checkpoint at the end of the phase.

## Summary

The phase is test-infrastructure only, and everything it needs already exists in the app. I reproduced the whole picture against the installed kicad-cli 10.0.7 in a scratch directory: (a) a hand-built 20251024 symbol library is a byte-for-byte fixed point of `kicad-cli sym upgrade --force` (so D-03 has a precise, automatable acceptance check); (b) a normalised install of the UL sample into a synthetic 20251024 library, the second-install no-op and the new-library header all behave as the KiCad 9 tests expected, just with 20251024 / `"10.0"`; (c) installing the UL sample into a synthetic 20241209 library already produces exactly the D-01 as-is row with the WARNING `CSD85301Q2 is format 20211014 but IC_PowerManagementMosfet_TI is 20241209; kicad-cli would write format 20251024, so CSD85301Q2 is merged unchanged`, the header stays `(version 20241209)` and `load_gate` returns `[]`. VER-01 therefore needs a test and a UAT retarget, not a product fix.

Three findings the CONTEXT did not have. (1) **The WurthElektronik checkout (D-11) is the biggest risk to "0 failures".** The Wurth tests have never run on this workstation (Phase 2 recorded "could not be measured"). I parsed the 8016 Wurth files of the main clone's current tip read-only: 77 s warm, 195 s cold, against the 60 s assert in `test_wurth_corpus_parse_budget`. The worktree's pinned commit `2e6e51b` has about 6030 such files (extrapolated parse time about 58 s), so the budget test is borderline to failing and the extra ~6000 round-trip params will lengthen the suite. The plan needs a measure-then-decide task for it. (2) The CONTEXT's failure split is slightly off: `test_noop_second_plan_after_normalised_apply` builds its own synthetic layout and is a KiCad 9 expectation, not a live-tree one (corrected split: 14 live-dependent + 7 KiCad 9 = the 21 baseline failures, see Pitfall 5), and `test_suggest_live_custom` asserts exact library names from the live tree although D-04 would leave it alone. (3) KiCad 10 moved `(hide yes)` from inside `(effects` to the property level and added `show_name` / `do_not_autoplace` per property, `in_pos_files`, `duplicate_pin_numbers_are_jumpers` and a trailing `(embedded_fonts no)`, so the 20251024 builder cannot be a version bump of the 20241209 one.

The removal of `custom_copy` also removes about 19 MB of file copying from each of roughly 125 tests, which should shorten the 5 min 21 s run noticeably (estimate, not measured).

**Primary recommendation:** Build the format-mirror `Custom/` in a new plain helper `tests/customfixtures.py` (writer function + byte builders from `installfixtures.py`, including a new 20251024 style that is verified once as a fixed point of real `sym upgrade --force`), expose it through one conftest fixture, rename `custom_copy` mechanically in six files, centralise the "kicad-cli major == 10" skip in conftest with `functools.cache`, retarget the seven real-CLI tests per the table below, add the VER-01 scenario to `_SCENARIOS`, add the session guard as an autouse session fixture, and treat the Wurth checkout plus its 60 s budget as its own measured task.

## Architectural Responsibility Map

This is a test-infrastructure phase; "tiers" are the layers of the test setup, not the application.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Byte builders for KiCad file styles (incl. 20251024) | `tests/installfixtures.py` | `tests/test_installfixtures.py` | Existing rule: builders return bytes, no paths. House styles documented in the module docstring. |
| Writing the synthetic `Custom/` to disk | new `tests/customfixtures.py` (plain helper) | `tests/conftest.py` fixture wrapper | Needs a root path, so it cannot live in `installfixtures.py` (rule). Precedent: `zipfixtures.write_custom_layout(root, ...)`. |
| pytest fixture exposing it | `tests/conftest.py` | `tests/test_import_dialog.py` / others for local wrappers | Single name, same return type (`RepoLayout`) as `custom_copy` so the tests change only the name. |
| "kicad-cli is major 10" skip | `tests/conftest.py` | per-module wrappers deleted | Three modules and conftest currently locate the CLI four different ways; one cached helper replaces them. |
| Live-`Custom/` write protection | `tests/conftest.py` (session fixture) | `tests/README.md` (documents it) | A property of the whole run, not of one test. |
| Skip documentation | `tests/README.md` | `pytest -ra` output | `-ra` already prints each skip reason; README explains how to enable each. |
| VER-01 automated check | `tests/test_install_e2e.py::_SCENARIOS` | real kicad-cli 10 | Natural home for the five D-01 rows (CONTEXT canonical reference). |
| VER-01 manual check | `test_uat_scratch_install` hook | owner in KiCad 10 Symbol Editor | Human checkpoint at end of phase. |
| Planning records (UAT note, PROJECT.md rows) | `.planning/` | none | Written only after the manual check passes. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.1.1 | Runner, fixtures, markers | Already pinned in `requirements-dev.txt` [VERIFIED: `env/Scripts/python.exe -m pip list` and requirements-dev.txt this session] |
| pytest-qt | 4.5.0 | Qt dialog tests (`qtbot`) | Already pinned; the `make_dialog` tests that use `custom_copy` run through it [VERIFIED: pip list] |
| Python stdlib (`hashlib`, `functools`, `re`, `shutil`, `pathlib`) | 3.14.4 | Guard hashing, cached CLI probe | Project rule: stdlib only [VERIFIED: `env/Scripts/python.exe --version`] |
| kicad-cli | 10.0.7 (also 9.0.9 installed) | Real-binary tests | Located by the app's own `locate_kicad_cli`; picks 10.0 [VERIFIED: ran `kicad-cli version` -> `10.0.7`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `kicad_lib_manager.importer.kicad_cli.run_cli` | in repo | Run `kicad-cli version` for the major-10 probe | Reuse the app's no-shell runner instead of a second `subprocess` call [VERIFIED: kicad_cli.py:62-84] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Parse `kicad-cli version` | Read the `10.0` folder name from `…\KiCad\10.0\bin\kicad-cli.exe` | Path layout differs per OS (Linux/macOS have no version folder); `version` costs about 0.55 s once per session [VERIFIED: timed run]. Use `version`. |
| Autouse session fixture for the guard | `pytest_sessionstart` / `pytest_sessionfinish` hooks | `pytest_sessionstart` "is only called for initial conftests" [VERIFIED: `_pytest/hookspec.py:897` in the venv]; a session fixture works however pytest is invoked. Failure surfaces as a teardown ERROR of the last test, which still makes the exit code non-zero. |
| Full hash of the live tree | size + mtime with hash fallback | Hashing 44 files / 19.75 MB took 1.6 s cold [VERIFIED: timed run]; do twice per session. No need for the mtime shortcut. |

**Installation:** none. No package is added.

**Version verification:** `pytest 9.1.1`, `pytest-qt 4.5.0` confirmed by `pip list` in the project venv on 2026-10-25.

## Package Legitimacy Audit

This phase installs no external packages. `requirements.txt` / `requirements-dev.txt` are unchanged.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                    pytest session (bare `pytest` from repo root)
                                   |
        +--------------------------+---------------------------+
        |                          |                           |
  session guard (autouse)    synthetic Custom/ fixture    KiCad 10 gate (cached)
  hash live Custom/ at       tmp_path/repo/Custom/...     locate_kicad_cli(newest)
  start and at teardown      built by customfixtures      -> `kicad-cli version`
        |                          |                       -> major==10 ? run : skip(reason)
        |                          v                           |
        |             installfixtures byte builders            |
        |   (20211014 / 20231120 / 20241209 / 20251024 styles) |
        |                          |                           |
        |                          v                           v
        |               RepoLayout.for_repo(tmp repo)  real_tools / kicad_cli_path
        |                          |                           |
        |                          +-----------+---------------+
        |                                      v
        |                  build_plan -> apply_plan -> verify  (existing app code, unchanged)
        |                                      |
        |                          kicad_cli.load_gate (real binary, KiCad 10 only)
        v                                      v
  live Custom/ unchanged?              assertions on 20251024 / D-01 rows
  else pytest.fail(changed files)

  Read-only live tests (D-04) read live Custom/ directly and stay outside this flow.
```

### Recommended Project Structure
```
tests/
├── conftest.py            # synthetic_custom fixture, kicad_cli_path (major 10), real_tools, session guard
├── customfixtures.py      # NEW plain helper: write_synthetic_custom(root) -> RepoLayout, name/version constants
├── installfixtures.py     # + V10_VERSION 20251024 style in target_lib (bytes only)
├── test_customfixtures.py # NEW: the fixture's own contract (versions, absent UL part, parses)
├── test_installfixtures.py# + 20251024 rows, + real-CLI fixed-point test (kicad_cli marker)
└── README.md              # NEW: skip table + live-Custom rule
```

### Pattern 1: Format-mirror `Custom/` built from bytes
**What:** One writer function takes a root `Path` and writes `Custom/Symbols`, `Custom/Footprints`, `Custom/3DModels`; the conftest fixture calls it with `tmp_path / "repo"` and returns `RepoLayout.for_repo(repo)` (the exact type `custom_copy` returned, [VERIFIED: conftest.py:78-89]).
**When to use:** every test that previously took `custom_copy`; `test_uat_scratch_install` (D-09) calls the same function with the UAT directory, so the manual check can never copy the live tree.
**Inventory the existing tests need** (from reading the tests this session):

| Library | Format | `.pretty` | Why it must exist |
|---------|--------|-----------|-------------------|
| `IC_Battery_Charger_TI` | 20211014 (CRLF, leading blank line) | yes | `UL_LIBRARY` / `LIBRARY` in `test_install_e2e.py:40`, `test_install_apply.py`, `test_commit_plan.py`, `test_import_preview.py`, `test_import_dialog.py` (19 mentions) |
| `IC_IMU_TDK` | 20231120 | **no `.pretty`** | `test_library_pair_completed_pretty_missing` asserts `not (custom_copy.footprints_dir / "IC_IMU_TDK.pretty").exists()` and `(new_symbol_lib, new_footprint_lib) == (False, True)`; `test_sc3_existing_headers_unchanged[IC_IMU_TDK]` expects `pair_completed` True; `set_library(dialog, "IC_IMU_TDK")` in `test_import_dialog.py:1152` |
| `IC_Magnetometer_Memsic` | 20241209 | yes | `test_sc3_existing_headers_unchanged` param (pair not completed), `_scenario_newer_target`, `test_cli_second_install_is_noop`, and the incoming-newer scenario reads its bytes and the symbol name `MMC5983MA` (`test_install_e2e.py:518-529`) |
| `IC_PowerManagementMosfet_TI` | 20241209, **no CSD85301Q2** | yes | D-02 / VER-01 target |
| `IC_Wireless_BLE_uBlox` | 20251024 | yes | D-02; target of the retargeted "older incoming is normalised" and "second install is noop" rows |
| `IC_MOSFET_Dual_TI` | absent | absent | `NEW_LIBRARY` in `test_install_e2e.py:121` must stay a library that does not exist |

Not needed in the fixture: `IC_Test_TI`, `IC_Old_TI`, `IC_New_TI` etc. are created by the tests themselves, and `test_import_dialog.py` uses its separate `item_layout` (built from `zipfixtures.CURRENT_CUSTOM_SYMBOL_LIBS`) for `Connector_USB_GCT` and `IC_Battery_Fuel_Gauge_ADI`. Never put `CSD85301Q2.stp`, a `DQK0006B*.kicad_mod` or a `CSD85301Q2` symbol anywhere in the fixture; model stubs use `zipfixtures.STEP_BYTES`.

Keep the fixture function-scoped and write fresh per test: the bytes are small, and the tests mutate the tree.

### Pattern 2: One cached KiCad 10 gate
**What:** A single helper in conftest probes once per session and every real-binary fixture reuses it.
**Example:**
```python
# Source: derived from conftest.py:106-115 and kicad_cli.py:31-84 (read this session)
import functools
import re

KICAD_MAJOR = 10
KICAD_SYMBOL_FORMAT = 20251024
KICAD_GENERATOR_VERSION = "10.0"


@functools.cache
def _located_kicad_cli() -> tuple[Path | None, str]:
    """(kicad-cli path or None, reason it is unusable or "") for the newest KiCad, probed once per session."""
    from kicad_lib_manager.importer import kicad_cli
    from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
    from kicad_lib_manager.models import Issue

    exe = kicad_cli.locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())
    if exe is None:
        return None, "kicad-cli not found (these tests need KiCad 10)"
    run = kicad_cli.run_cli(exe, ["version"], timeout=30)
    if isinstance(run, Issue) or run.returncode != 0:
        return None, f"could not run `kicad-cli version` at {exe}"
    found = re.match(r"\s*(\d+)\.(\d+)", run.stdout)
    if found is None or int(found.group(1)) != KICAD_MAJOR:
        return None, f"needs kicad-cli {KICAD_MAJOR}, found {run.stdout.strip() or 'unknown'} at {exe}"
    return exe, ""


@pytest.fixture
def kicad_cli_path() -> Path:
    exe, reason = _located_kicad_cli()
    if exe is None:
        pytest.skip(reason)
    return exe
```
`kicad-cli version` printed `10.0.7` on 10.0 and `9.0.9` on 9.0 [VERIFIED: ran both binaries]. Do not `import` anything from `kicad_lib_manager` at conftest module top (the file imports lazily today; keep it so the Qt `offscreen` env var is set first, conftest.py:10).

### Pattern 3: Session write-protect guard
**What:** An autouse session-scoped fixture digests the live `Custom/` once at the start and once at teardown.
**Example:**
```python
# Source: reuses the digest shape of conftest.py:118-132 (`snapshot`)
def _digest_live_custom() -> dict[str, str] | None:
    custom = REPO_ROOT / "Custom"
    if not (custom / "Symbols").is_dir():
        return None
    found: dict[str, str] = {}
    for sub in ("Symbols", "Footprints", "3DModels"):
        for path in sorted((custom / sub).rglob("*")):
            if path.is_file():
                found[path.relative_to(custom).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


@pytest.fixture(scope="session", autouse=True)
def _live_custom_untouched():
    before = _digest_live_custom()
    yield
    if before is None:
        return
    after = _digest_live_custom()
    if after != before:
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        pytest.fail("the test run changed the live Custom/ folder: " + ", ".join(changed[:10]))
```
Remove the module-level `_real_custom_untouched` autouse fixture and the `real_before/real_after` snapshots in `test_install_e2e.py:68,115,135-144` and `test_install_plan.py:735,747`; the guard supersedes them. Hashing 44 files / 19.75 MB took 1.6 s cold [VERIFIED].

### Pattern 4: 20251024 byte builder (D-03)
**What:** A separate branch of `target_lib` for `version >= 20251024`, with the shape KiCad 10 itself writes. Observed from `kicad-cli sym upgrade --force` output and the live `IC_Button_Controller_ADI.kicad_sym` (both 20251024) [VERIFIED: ran kicad-cli 10.0.7, read live file]:

- header: `(kicad_symbol_lib` / `(version 20251024)` / `(generator "kicad_symbol_editor")` / `(generator_version "10.0")`, tab-indented, every list child on its own line;
- per symbol: `(exclude_from_sim no)`, `(in_bom yes)`, `(on_board yes)`, **`(in_pos_files yes)`, `(duplicate_pin_numbers_are_jumpers no)`**, properties, sub-symbols, then **`(embedded_fonts no)`** as the last child;
- per property: `(at …)`, **`(show_name no)`, `(do_not_autoplace no)`**, then `(hide yes)` **at property level before `(effects`** (KiCad 8/9 put `(hide yes)` inside `(effects`, which the existing `_modern_effects` does), then `(effects (font (size …)))`;
- pins: `(name "" …)` (KiCad 10 turned the builder's `"~"` into `""`).

Line endings: kicad-cli 10 on Windows writes CRLF; the repo index stores LF (`git ls-files --eol` shows `i/lf w/crlf` under `core.autocrlf=true` [VERIFIED]). Default the new style to LF like the other modern styles, and compare with line endings normalised so the check is platform neutral.

**Acceptance check (automatable, marked `kicad_cli`):**
```python
# Source: prototype run this session, scratchpad proto10.py -> "identical: True"
def test_target_lib_20251024_is_what_kicad_10_writes(tmp_path, kicad_cli_path):
    data = target_lib(V10, ("EXISTING_A", "EXISTING_B"))
    src, out = tmp_path / "in.kicad_sym", tmp_path / "out.kicad_sym"
    src.write_bytes(data)
    run = kicad_cli.run_cli(kicad_cli_path, ["sym", "upgrade", "--force", "-o", str(out), str(src)])
    assert run.returncode == 0
    assert out.read_bytes().replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n")
```
My prototype (same tuple structure fed through the existing `_tree` renderer, with `\r\n`) produced byte-identical output on kicad-cli 10.0.7. `kicad-cli sym upgrade` without `--force` prints "Symbol library was not updated" for an already-current file, which is why the app passes `--force` (kicad_cli.py:164). Update the `installfixtures.py` docstring to list the new style and update `_MODERN_GENERATOR_VERSIONS` (currently `{20231120: "8.0", 20241209: "9.0"}`, installfixtures.py:21) to include `20251024: "10.0"`; add `(V10, "10.0")` to `MODERN` and `V10` to `ALL_VERSIONS` in `test_installfixtures.py:19-23` (tests at lines 96-145 are parametrised over them and the Description-property and "no ids / hide yes" assertions hold for the new style).

### Anti-Patterns to Avoid
- **Bumping the 20241209 builder's version number:** the shapes differ (see Pattern 4); the fixed-point test would fail.
- **A second place that locates kicad-cli:** the three current copies (`real_exe`, `_real_tools`, `real_tools`/`kicad_cli_path`) differ slightly; keep exactly one.
- **Writing under the repo to test the guard:** do not "prove" the guard by touching the live `Custom/`. Use a unit test that points the digest function at a `tmp_path` tree (make `_digest_live_custom` take the root as a parameter).
- **Asserting the CLI's `\r\n`:** the line endings kicad-cli writes depend on the OS; assert on normalised text.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locating kicad-cli | a new PATH/registry search | `kicad_cli.locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())` | D-05: the tests must pick the same binary the app picks (newest) |
| Running kicad-cli | raw `subprocess.run` in tests | `kicad_cli.run_cli(exe, [...])` | No shell, `CREATE_NO_WINDOW`, timeout and OSError handling already there |
| Tree digest | a second hashing helper | the `snapshot` logic in conftest (factor into a module function used by both) | Same shape, already trusted by many tests |
| Synthetic library bytes | string templates in the new helper | `installfixtures.target_lib` / `vendor_footprint`, `zipfixtures.STEP_BYTES`, `zipfixtures.write_custom_layout` | The builder rule and house-style docs live there |
| Skip documentation | custom plugin that rewrites skip reasons | `-ra` (already in `addopts`) plus `tests/README.md` | Reasons are already printed [VERIFIED: pyproject.toml:4] |

**Key insight:** every behaviour this phase tests is already in the app and verified; the work is making the test inputs independent of the owner's live data and of KiCad 9.

## Runtime State Inventory

Not a rename/refactor/migration phase. Omitted per instructions. (One related fact: the live `Custom/` and `Custom/.git` are never written by this phase; `git -C Custom status --short` is empty in this worktree.)

## Common Pitfalls

### Pitfall 1: The Wurth parse budget will likely fail once the submodule is checked out (D-11)
**What goes wrong:** `test_wurth_corpus_parse_budget` (`tests/test_roundtrip_corpus.py:240-251`) asserts `elapsed < 60` for decode plus parse of every Wurth `.kicad_sym` / `.kicad_mod` / table file. I timed decode plus parse (no tile check) of the main clone's current tip (8016 files) read-only from this worktree's package: **195.5 s cold, 77.1 s warm**, and no decode failures. The worktree pins `2e6e51b`, which has 5641 `.kicad_mod` + 389 `.kicad_sym` + 2 tables ≈ 6030 files [VERIFIED: `git ls-tree -r` on the pinned commit], so about 58 s extrapolated warm, 150 s cold. The Phase 2 notes say the Wurth timing "could not be measured" because the submodule was never checked out [VERIFIED: 02-05-SUMMARY.md line 157], and the Phase 1 review already called the 60 s budget flaky [VERIFIED: 01-REVIEW.md line 186].
**Why it happens:** 9.6 ms per file on Python 3.14 here; the budget was set without data.
**How to avoid:** after the checkout, run `env/Scripts/python.exe -m pytest -m wurth --durations=10` first. If the budget test fails or is within 20 percent of the limit, change it to a rate (for example `max(60, 0.05 * len(files))`) or raise it, and document the number in `tests/README.md`. This is a test change, in scope for TEST-03.
**Warning signs:** `parsing N Wurth files took X s (budget 60s)`.

### Pitfall 2: ~6000 extra parametrised round-trip tests change the suite's runtime
**What goes wrong:** `test_roundtrip_wurth_file` becomes about 6000 test items (each reads, tile-checks and atomically rewrites a file). Today the whole suite takes 5 min 21 s.
**How to avoid:** plan a measured full run; keep `-m "not wurth"` as the per-task quick command and run the full suite only at the phase gate. Removing the 19 MB per-test `custom_copy` copies should offset some of it [ASSUMED: not measured].

### Pitfall 3: Submodule init in a worktree
**What goes wrong:** `git submodule update --init WurthElektronik/KiCad-Library` clones from GitHub into this worktree's own module dir (`.git/worktrees/Kicad_Libraries-importer/modules/…`), like `Custom` was [VERIFIED: `Custom/.git` content]. Both submodules are `active=true` in the shared config [VERIFIED]. The main clone has the pinned commit locally [VERIFIED: `git cat-file -t 2e6e51b…` -> `commit` in the main clone's Wurth repo], so `git submodule update --init --reference C:/Git_Repo_Clones/Kicad_Libraries/WurthElektronik/KiCad-Library WurthElektronik/KiCad-Library` could avoid a download [ASSUMED: option not executed, research is read-only]. Do not run any command inside the main clone.
**Warning signs:** `git submodule status` still shows a leading `-` for the Wurth path.

### Pitfall 4: Tests that read the live `Custom/` but assert part-dependent state
**What goes wrong:** D-04 keeps read-only tests as they are, but several assert specifics, so adding or removing a part (or, after Phase 13, a library) changes their result:
- `test_naming_suggest.py::test_suggest_live_custom` (lines 454-458) asserts `suggestion.name == "IC_SubCategory_TI"` and `suggestion.alternatives[0].name == "IC_Battery_Charger_TI"` from the live library list. This is not a corpus/health check; it is a ranking test that `list_existing_libraries(RepoLayout.for_repo(REPO_ROOT))` happens to satisfy. **Recommend moving it to the synthetic fixture** (its names are a subset of the fixture's, so the assertions should hold unchanged; confirm by running it).
- `test_kicad_files.py::test_live_custom_symbols` requires every live symbol to have a `Footprint` property; `test_naming_sanitize.py::test_sanitize_live_custom_names_unchanged` requires every live name to sanitize unchanged; `test_scanner_issues.py::test_live_custom_model_findings_are_zero` requires zero model-path findings. These are repo-health invariants; keep them (D-04) but list them in `tests/README.md` as "fails if a live part breaks the naming or model rules", so a red result is read correctly.
- `test_edits.py` uses `Connector_USB_GCT.kicad_sym` by name (line 28): it will silently skip after Phase 13 renames libraries; note for that phase.
**How to avoid:** the planner decides explicitly per test; the first is in Claude's discretion under D-04 ("assume which parts exist move to the fixture").

### Pitfall 5: The CONTEXT's failure split mislabels one test
**What goes wrong:** `test_install_plan::test_noop_second_plan_after_normalised_apply` is listed under the 14 live-dependent tests, but it builds `_target_layout(tmp_path, V9, ("EXISTING_A",))` and uses `_real_tools()` (test_install_plan.py ~1238-1250); it has no `custom_copy`. It fails for the KiCad 9 reason. [VERIFIED: read the test]. The CONTEXT's "live-dependent (14)" bullet actually lists 15 items; dropping the noop test leaves the true 14. Corrected split of the 21 baseline failures: **14 live-dependent** (1 `test_commit_plan`, 2 `test_import_dialog`, 1 `test_import_preview`, 7 `test_install_apply`, 2 `test_install_e2e`, 1 `test_install_plan::test_model_changed_after_plan_is_refused_by_apply` = 14) and **7 KiCad 9** (`test_kicad_cli` 1, `test_install_plan` 3 including the noop test, `test_install_e2e` 3). I re-ran `test_commit_plan::test_build_from_real_ul_plan` to confirm the live cause: the first expected row `Custom/3DModels/CSD85301Q2.stp` is missing because the live `Custom/3DModels/CSD85301Q2.stp` already exists with the same hash, so the plan omits the model write. Everything else in the baseline passes.

### Pitfall 6: Hard-coded 20241209 / `"9.0"` in real-binary assertions
**What goes wrong:** the retargets must change every literal, not just the library: `test_install_e2e.py:492` (`plan.target_version == 20241209`), `:512` (`"(version 20241209)"`, `'(generator_version "9.0")'`), `test_install_plan.py:649,658,823,825`, `test_kicad_cli.py:587,589`. Use the named constants from conftest/`customfixtures`, not new literals.

### Pitfall 7: Scenario 4 reuses the live library's bytes
**What goes wrong:** `_scenario_incoming_newer` (test_install_e2e.py:516-537) packages the *Magnetometer* library bytes plus symbol `MMC5983MA` as the "newer incoming" file. If the fixture's `IC_Magnetometer_Memsic` has a different symbol name the test breaks. Either name the fixture's single symbol `MMC5983MA` or switch the scenario to `vendor_symbol_lib(version=20241209)`. The latter is more robust and also removes the last coupling to a real part name.

### Pitfall 8: Mixed line endings when a CRLF UL symbol is spliced into an LF library
**What goes wrong:** not a failure today; the VER-01 run showed the written library starts `(kicad_symbol_lib\n\t(version 20241209)…` (LF header from the builder) while the UL block is CRLF. Assertions about bytes of the header must slice the header (the helper `_header` exists in test_install_e2e.py:158-160) rather than compare whole files.

## Code Examples

### VER-01 automated row (goes into `_SCENARIOS`)
Verified end to end in a scratch directory with the real planner and kicad-cli 10.0.7 (script `ver01.py`, output: `blocked False normalised False 20211014 20241209`, WARNING text below, `ok True`, `gate []`).

```python
# Source: derived from test_install_e2e.py:151-160,499-505 and the scratch run; strings from planner.py:378-382
V10 = 20251024
POWER_MOSFET = "IC_PowerManagementMosfet_TI"   # 20241209 in the synthetic fixture, no CSD85301Q2


def _scenario_target_20241209_as_is(candidate, layout, tmp_path, tools):
    """VER-01 (backlog 999.1): a 20241209 target on KiCad 10 takes the as-is-with-warning row (D-01)."""
    path = layout.symbols_dir / f"{POWER_MOSFET}.kicad_sym"
    original = path.read_bytes()
    plan, result = _install(candidate, layout, tmp_path, library=POWER_MOSFET, tools=tools)
    assert plan.normalised is False and plan.target_version == 20241209
    mismatch = [i for i in plan.issues if i.code == "install.version_mismatch"]
    assert [i.severity for i in mismatch] == [Severity.WARNING]
    for number in ("20211014", "20241209", str(V10)):      # incoming, target, what kicad-cli 10 would write
        assert number in mismatch[0].text
    written = path.read_bytes()
    assert _header(written) == _header(original)             # "(version 20241209)" and the 9.0 generator unchanged
    assert b"(version 20241209)" in _header(written)
    block = written[written.index(b'(symbol "CSD85301Q2"'):]
    assert b"(id " in block                                   # vendor text merged unchanged, not run through kicad-cli
    return result, POWER_MOSFET
```
The runner `test_cli_version_scenarios` then performs `load_gate` through `_written_gate_issues`, which is the "load_gate returns no issues" part of D-08. Observed WARNING text [VERIFIED: scratch run]: `CSD85301Q2 is format 20211014 but IC_PowerManagementMosfet_TI is 20241209; kicad-cli would write format 20251024, so CSD85301Q2 is merged unchanged`.

### Retargets of the real-CLI tests that carry KiCad 9 expectations (D-06)

The 7 failing ones plus `test_unit_real_cli_loads_in_kicad`, which passes today but builds a `V9` target for a real-binary test (D-06: no KiCad 9 expectation may remain; that its V10 variant passes is [ASSUMED], not run). Real-binary tests with **no** version literal only need the shared KiCad 10 gate and no other edit: `test_kicad_cli.py::test_real_cli_gate_accepts_ul_symbol_and_footprint` and `::test_real_cli_gate_rejects_sub_symbols_left_with_the_old_name` (via `real_exe`), `test_install_e2e.py::test_cli_load_check_after_install` (via `real_tools`), `test_vendor_install.py::test_vendor_installs_load_in_kicad` and `test_real_vendor_samples.py` (the `@pytest.mark.kicad_cli` test at line 304; both via their own `real_tools` copies, which move to conftest).

| Test | Current expectation | KiCad 10 retarget |
|------|--------------------|-------------------|
| `test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically` (582-592) | `first.version == 20241209`, `"(version 20241209)" in first.text` | `KICAD_SYMBOL_FORMAT` in both places |
| `test_install_plan.py::test_version_real_cli_into_20241209` (638-654) | `_target_layout(tmp_path, V9, …)`, `plan.target_version == V9` | rename `…_into_20251024`; target built with `V10`; `plan.target_version == V10`; keep `"(hide yes)" in block` and `"(id " not in block` (both hold in KiCad 10 output) |
| `test_install_plan.py::test_library_real_cli_new_header` (814-826) | `"(version 20241209)"`, `'(generator_version "9.0")'` | `f"(version {KICAD_SYMBOL_FORMAT})"`, `f'(generator_version "{KICAD_GENERATOR_VERSION}")'` (observed header: `(kicad_symbol_lib\r\n\t(version 20251024)\r\n\t(generator "kicad_symbol_editor")\r\n\t(generator_version "10.0")`) |
| `test_install_plan.py::test_noop_second_plan_after_normalised_apply` (1238-1250) | `_target_layout(tmp_path, V9, …)` | `V10` (observed: normalised True, then `is_noop` True) |
| `test_install_plan.py::test_unit_real_cli_loads_in_kicad` (1316-) | `V9` target (passes today, but is a KiCad 9 expectation in a real-binary test) | `V10` (D-06: no KiCad 9 expectation may remain) |
| `test_install_e2e.py::_scenario_newer_target` ("older_incoming_is_normalised") | `IC_Magnetometer_Memsic`, `target_version == 20241209` | `IC_Wireless_BLE_uBlox`, `target_version == V10` (observed: normalised True, 20211014 -> 20251024) |
| `test_install_e2e.py::_scenario_new_library` | `"(version 20241209)"`, `"9.0"` | the two constants |
| `test_install_e2e.py::test_cli_second_install_is_noop` | library `IC_Magnetometer_Memsic` | `IC_Wireless_BLE_uBlox` |

Remove the "older" meaning of the Magnetometer library from the real-CLI rows; it stays 20241209 only for the fake-CLI/no-CLI tests (`test_sc3_existing_headers_unchanged`, D-07). The `_SCENARIOS` dict gains one key (`"target_20241209_as_is_with_warning"`); the existing `"target_in_another_format_warns"` (IC_IMU_TDK, 20231120) passes unchanged on KiCad 10 [VERIFIED by reading the assertions against the planner's mismatch branch].

### Manual hook retarget (D-09)
`test_uat_scratch_install` (test_install_e2e.py:581-607) currently does `shutil.copytree(repo / "Custom" / name, scratch / name)` and installs into `LIBRARY`. Replace the copy loop with `layout = write_synthetic_custom(uat)` (same function the fixture uses), install into `POWER_MOSFET`, keep the T-04-28 outside-the-repo asserts (lines 586-587), update the docstring to KiCad 10, and print the same four paths using `POWER_MOSFET`. The skip stays `KICAD_IMPORT_UAT_DIR` unset. The owner then adds the scratch `IC_PowerManagementMosfet_TI` symbol/footprint library to KiCad 10, opens it in the Symbol Editor and places `CSD85301Q2` (checklist wording from `04-10-SUMMARY.md`, referenced by 04-UAT.md Test 1).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tests copy the live `Custom/` (19 MB each) | Synthetic format-mirror built from bytes | this phase | Tests independent of owner's parts; faster |
| kicad-cli tests accept whatever is installed (KiCad 9 era) | Pin KiCad major 10, skip with a reason otherwise | this phase | Newer output (KiCad 11) gets reviewed |
| Symbol format 20241209 / generator `"9.0"` | 20251024 / `"10.0"` | KiCad 10 | `(hide yes)` moves to property level; new `show_name`, `do_not_autoplace`, `in_pos_files`, `duplicate_pin_numbers_are_jumpers`, `embedded_fonts` |

**Deprecated/outdated:**
- `custom_copy` fixture: removed (D-13 relies on that).
- `.planning/codebase/TESTING.md` still says no tests exist (stale; refresh optional).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `git submodule update --init --reference <main clone Wurth path> WurthElektronik/KiCad-Library` works in this worktree without network | Pitfall 3 | Executor falls back to a plain `--init` (network, clone size unknown) |
| A2 | Removing the `custom_copy` copies shortens the suite materially, and the ~6000 Wurth round-trip items add several minutes | Summary, Pitfall 2 | Run-time budget for the phase gate is mis-planned; no correctness impact |
| A3 | Wurth parse time at the pinned commit is about 58 s warm (extrapolated from the tip's 77 s by file count) | Pitfall 1 | Budget test might pass or fail by a wider margin; the measure-first task handles both |
| A4 | `test_suggest_live_custom` assertions hold unchanged on the synthetic fixture (names are a subset of the fixture's) | Pitfall 4 | One test needs its expected values adjusted |
| A5 | Teardown failure of a session autouse fixture yields a non-zero pytest exit code | Pattern 3 | If not, the guard would only print; the planner must verify with a unit test of the failure path |
| A6 | `test_unit_real_cli_loads_in_kicad` passes when its target is a 20251024 library | Retarget table | One more test needs investigation during execution |

## Open Questions

1. **What to do when the Wurth parse-budget test fails or is borderline (Pitfall 1)?**
   - What we know: 77 s warm on the tip, about 58 s expected at the pinned commit, budget 60 s, never run here before.
   - What's unclear: the pinned-commit number, and whether any of the ~6000 round-trip items fail.
   - Recommendation: a dedicated measure-then-decide task (run `-m wurth --durations=10`, then scale the budget to the file count). If any Wurth round-trip file fails, that is a product/parse finding: report it, do not change app code (CONTEXT domain).

2. **Move `test_suggest_live_custom` to the synthetic fixture?**
   - What we know: it asserts exact live library names; D-04 leaves read-only tests alone but SC1 says adding/removing a part must change no result.
   - Recommendation: move it (it is cheap, and Phase 10/13 will change the live library names anyway). Planner's call.

3. **Is the KiCad 10 property style in plans a Phase 10 concern?** (Observation, not a bug fix for this phase.)
   - What we know: in the scratch run, the app inserted `Manufacturer` and `MPN` into a 20251024 library as one-line KiCad 8/9-style properties: `(property "Manufacturer" "TI" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))` [VERIFIED: scratch output, `vn_run`], while the rest of the file uses the 20251024 shape. The write passed the kicad-cli load gate (`apply` returned ok), so KiCad 10 accepts it.
   - Recommendation: report it in the Phase 8 summary and carry it into Phase 10 (field writing). Do not change app code here.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | everything | yes | 3.14.4 | - |
| pytest / pytest-qt | everything | yes | 9.1.1 / 4.5.0 | - |
| kicad-cli 10 | TEST-02, VER-01 automated | yes | 10.0.7 at `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | tests skip with a stated reason |
| kicad-cli 9 | none after this phase | yes | 9.0.9 (also installed; the app picks 10.0) | - |
| git | Wurth checkout, git tests | yes | in PATH | - |
| WurthElektronik submodule | D-11 | no (`git submodule status` shows `-2e6e51b…`) | pinned `2e6e51b` | main clone has the commit locally (see A1) |
| Symlink privilege (Windows) | 2 tests | no (baseline: 2 skips) | - | documented skip |
| KiCad 10 GUI (Symbol Editor) | manual VER-01 check | yes (installed) | 10.0 | owner action |
| `KICAD_IMPORT_UAT_DIR` | manual hook | unset by default | - | owner sets it for the manual check |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Wurth checkout (setup step in the plan), symlink privilege (documented skip).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| Quick run command | `env/Scripts/python.exe -m pytest -q -m "not wurth" tests/test_customfixtures.py tests/test_installfixtures.py tests/test_install_e2e.py tests/test_install_plan.py tests/test_install_apply.py tests/test_import_preview.py tests/test_commit_plan.py tests/test_kicad_cli.py` |
| Full suite command | `env/Scripts/python.exe -m pytest` (baseline 5 min 21 s; expect longer with Wurth) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | Fixture has the four format versions, mirrors the names, lacks CSD85301Q2 / DQK0006B / its model, parses, `IC_IMU_TDK` has no `.pretty`, `IC_MOSFET_Dual_TI` absent | unit | `pytest tests/test_customfixtures.py -x` | no, Wave 0 |
| TEST-01 | The 14 formerly live-dependent tests pass on the fixture | integration | `pytest tests/test_commit_plan.py tests/test_import_preview.py tests/test_install_apply.py tests/test_install_e2e.py tests/test_install_plan.py tests/test_import_dialog.py -x` | yes (rename) |
| TEST-01 | No test file references `custom_copy`, or copies the live tree | static | `grep -rn "custom_copy" tests --include=*.py` returns nothing | n/a |
| TEST-01 | Suite result independent of live parts | proof run | copy the repo (without `env/`, `.git`, `Custom/`) to a scratch dir outside the repo, run the six files above; expect pass with 0 skips | manual command |
| TEST-01 | 20251024 builder = what KiCad 10 writes | real-binary | `pytest tests/test_installfixtures.py -k 20251024 -m kicad_cli` | no, Wave 0 |
| TEST-02 | Real-binary tests expect 20251024 / `"10.0"` | real-binary | `pytest -m kicad_cli -v` (all pass on 10.0.7) | yes (edit) |
| TEST-02 | Skip with reason when CLI is not 10 | unit | a test that monkeypatches `locate_kicad_cli`/`run_cli` results through the cached helper (clear the cache in the test) and asserts the skip reason text for: none, 9.0.9, 11.0.0, unparsable | no, Wave 0 |
| TEST-03 | Bare `pytest` 0 failures; only documented skips | full run | `env/Scripts/python.exe -m pytest -rs` and compare skip list to README table | n/a |
| TEST-03 | Guard fails when live `Custom/` changes | unit | digest function parameterised on a `tmp_path` tree; assert a changed file is reported | no, Wave 0 |
| VER-01 | As-is row on KiCad 10, header unchanged, gate clean | real-binary | `pytest "tests/test_install_e2e.py::test_cli_version_scenarios[target_20241209_as_is_with_warning]"` | no, Wave 0 |
| VER-01 | Owner places the part in KiCad 10 Symbol Editor | manual | set `KICAD_IMPORT_UAT_DIR`, run `test_uat_scratch_install`, open the library in KiCad 10 | hook exists; edit |

### Sampling Rate
- **Per task commit:** the quick run command above (no Wurth, no full suite).
- **Per wave merge:** `pytest -m "not wurth"`.
- **Phase gate:** full `pytest` green (Wurth included) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/customfixtures.py` and `tests/test_customfixtures.py` (TEST-01)
- [ ] 20251024 rows in `tests/test_installfixtures.py` plus the real-CLI fixed-point test
- [ ] conftest: `synthetic_custom` fixture, cached KiCad 10 gate with tests, `real_tools` fixture, session guard with a unit test of its failure path
- [ ] `tests/README.md`
- [ ] Framework install: none

## Security Domain

`security_enforcement` is enabled (absent = enabled; config shows `true`, ASVS level 1). The phase touches only tests, docs and one git setup step.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | - |
| V3 Session Management | no | - |
| V4 Access Control | no | - |
| V5 Input Validation | limited | `kicad-cli version` output is parsed with an anchored regex; failure means skip, never a guess |
| V6 Cryptography | no | SHA-256 from `hashlib` for the guard, not a security control |
| V12 Files/Resources | yes | Scratch hook keeps the T-04-28 check that the UAT folder is outside the repo and not a link; the guard proves the live `Custom/` is never written |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A test or the UAT hook writing into the live `Custom/` (tampering with owner data) | Tampering | Session hash guard (D-13); hook builds the synthetic tree instead of copying the live one; keep the existing outside-repo asserts |
| Running an untrusted `kicad-cli` found on PATH | Elevation of Privilege | `locate_kicad_cli` prefers the install next to the footprints folder, then PATH, as the app does; call with a list (no shell) through `run_cli` |
| Cloning the Wurth submodule from the network | Tampering / supply chain | Pinned commit `2e6e51b…` recorded in the parent; do not update to the tip; verify `git submodule status` shows that hash after init |

## Sources

### Primary (HIGH confidence)
- Repo files read this session: `tests/conftest.py`, `tests/installfixtures.py`, `tests/zipfixtures.py`, `tests/test_install_e2e.py` (full), `tests/test_install_plan.py` (version, real-CLI and noop sections), `tests/test_kicad_cli.py` (header and real section), `tests/test_installfixtures.py` (builder tests), `tests/test_roundtrip_corpus.py`, `tests/test_scanner_issues.py`, `tests/test_naming_suggest.py`, `tests/test_naming_sanitize.py`, `tests/test_kicad_files.py`, `tests/test_edits.py`, `tests/test_import_dialog.py` (fixtures), `tests/test_commit_plan.py`, `tests/test_import_preview.py`, `kicad_lib_manager/importer/planner.py` (295-419), `kicad_lib_manager/importer/kicad_cli.py` (full), `kicad_lib_manager/importer/layout.py`, `pyproject.toml`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md` rows 161 and 166, archived `04-UAT.md`.
- Runs this session (all in the scratchpad, outside the repo): `kicad-cli version` on 10.0 and 9.0; `sym upgrade --force` on builder output (v6 / 20231120 / 20241209 inputs all give the same 20251024 output); fixed-point check of a hand-built 20251024 library; VER-01 scenario with the real planner and applier; normalised install, noop and new-library header on a 20251024 target; read-only parse timing of the Wurth corpus (main clone tip); read-only `check_3d_model_paths` over the main clone (0 Wurth findings in 20.0 s).
- `env/Lib/site-packages/_pytest/hookspec.py` (hook docs for `pytest_sessionstart` / `pytest_sessionfinish`).
- `git ls-tree -r 2e6e51b` in the main clone's Wurth repo (file counts at the pinned commit).

### Secondary (MEDIUM confidence)
- `.planning/milestones/v1.0-phases/02-hardening-existing-code/02-05-SUMMARY.md` line 157 and `01-REVIEW.md` line 186 (history of the Wurth timing).

### Tertiary (LOW confidence)
- Run-time estimates (A2, A3) and the `--reference` submodule option (A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new packages, versions read from the venv.
- Architecture: HIGH - every pattern was exercised against the real binary or read from the current code.
- Pitfalls: HIGH for Pitfalls 4-8 (read from source or reproduced); MEDIUM for 1-3 (timing measured on the tip, extrapolated to the pinned commit).

**Research date:** 2026-10-25
**Valid until:** 2026-11-24 for the KiCad 10.0.7 output shapes (a new KiCad 10.x point release could change the written format; the fixed-point test catches that), 7 days for the Wurth timing numbers.
