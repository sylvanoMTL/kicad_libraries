# Tests

This folder holds the pytest suite for the KiCad Library Manager and its part importer.

## How to run

Run these from the repository root with the project's virtual environment.

- Full suite: `.\env\Scripts\python.exe -m pytest`
- Quick run, without the WurthElektronik stress corpus: `.\env\Scripts\python.exe -m pytest -m "not wurth"`
- Only the tests that run the real kicad-cli 10 binary: `.\env\Scripts\python.exe -m pytest -m kicad_cli`
- Only the WurthElektronik corpus: `.\env\Scripts\python.exe -m pytest -m wurth`

The full suite takes about 18 minutes on the workstation. The quick run takes about 8 minutes.
Bare `pytest` already prints the reason for every skip (`-ra` is set in `pyproject.toml`).

## The rule: never touch the live Custom/

The suite must never write to the live `Custom/` folder, and no test result may depend on which parts it holds.
Adding or removing a real part in `Custom/` must not change a test result.

- Tests that need a target library use the `synthetic_custom` fixture from `tests/conftest.py`, built by `tests/customfixtures.py`.
- It writes one library per format version (20211014, 20231120, 20241209, 20251024) with today's naming, in a temporary folder.
  It never contains the Ultra Librarian sample part.
- Do not copy real libraries into fixtures.
- A session guard in `tests/conftest.py` fails the run if the live `Custom/` changes while the suite runs, and names the paths.
  If you edit `Custom/` by hand during a run, run the suite again.

## Expected skips

Each row is one condition that makes tests skip. `pytest -rs` prints the message in the second column.

| Condition | Message printed by `pytest -rs` | Why | How to enable |
| --- | --- | --- | --- |
| No kicad-cli 10 | `kicad-cli not found (these tests need KiCad 10)`, `could not run kicad-cli version at <exe>: <detail>`, or `needs kicad-cli 10, found <version> at <exe>` | The real-binary tests pin KiCad 10 (format 20251024, generator 10.0) and skip on any other major version. | Install KiCad 10. The newest install is used. |
| Symlinks not permitted | `symlinks not permitted here: [WinError 1314] A required privilege is not held by the client: ...` | Creating a symbolic link needs a privilege that a normal Windows account does not have. | Turn on Windows Developer Mode, or run the tests from an elevated shell. |
| No WurthElektronik submodule | `WurthElektronik submodule not checked out (git submodule update --init WurthElektronik/KiCad-Library)` | The stress and round-trip corpus reads the Wurth library. | `git submodule update --init WurthElektronik/KiCad-Library` |
| `KICAD_IMPORT_UAT_DIR` unset | `set KICAD_IMPORT_UAT_DIR to build the manual UAT scratch install` | This test builds a scratch install for the owner to open in KiCad 10. It is not an automated check. | Set `KICAD_IMPORT_UAT_DIR` to a folder outside the repository, then run `tests/test_install_e2e.py::test_uat_scratch_install -s` and open the result in KiCad 10. |
| `local_kicad` | `no KiCad user config tables found` | These tests read the user's real KiCad library tables, read-only, and have nothing to read on a machine without them. | They run when the tables exist. Deselect them with `-m "not local_kicad"`. |

On the workstation the expected skips are exactly three: the two symlink skips (`tests/test_model_source.py` and `tests/test_package_folder.py`) and the `KICAD_IMPORT_UAT_DIR` skip.
Anything else that is skipped there is a finding.

## Other conditional skips

These skip only on a machine that lacks something. None of them skip on the workstation.

- Custom submodule not checked out: `Custom submodule not checked out (git submodule update --init Custom)`.
  Used by the read-only live health checks below.
- Case-sensitive volume: `case-sensitive volume` (`tests/test_commit_plan.py`).
- Directory links unavailable: `directory links are not available here` (`tests/test_install_apply.py`).
- Junctions unavailable: `junctions are a Windows feature` and `could not create a junction here` (`tests/test_package_folder.py`).
- Git not on PATH: `git is not on PATH` (`tests/gitfixtures.py`, `tests/test_fixtures.py`, `tests/test_package_zip.py`).
- A zipfile feature missing: `this Python's zipfile has no <name>` (`tests/test_package_zip.py`).
- Licence-restricted vendor samples absent: `downloaded_examples/<file> not present (licence-restricted <vendor> sample, kept local)` (`tests/test_real_vendor_samples.py`, `tests/test_vendorfixtures.py`).
- No KiCad stock symbols folder: `no KiCad install with a stock symbols folder` (`tests/test_install_verify.py`).
- `tomllib` missing on Python 3.10: `tests/test_manifests.py` skips through `importorskip`.
- Windows-only behaviour on another platform:
  `held-open handles block os.replace only on win32`, `case is only ignored on Windows`,
  `replacing a case twin leaves one entry only on NTFS (research spike S7)`.
- Importer package not present: `kicad_lib_manager/importer not present yet ...` (`tests/test_importer_layering.py`).

## Read-only live health checks

A few tests read the live `Custom/` on purpose (decision D-04). They never write to it.
They fail when a live part breaks a rule, so a red result there is a finding about the live data, not a test bug.

- `test_kicad_files.py::test_live_custom_symbols`
- `test_naming_sanitize.py::test_sanitize_live_custom_names_unchanged`
- `test_scanner_issues.py::test_live_custom_model_findings_are_zero`
- the `custom/...` cases of the round-trip corpus in `test_roundtrip_corpus.py`
- `test_edits.py`, which reads `Connector_USB_GCT.kicad_sym`.
  It skips if that library is renamed (Phase 13 note).

## WurthElektronik corpus timing

The `wurth` tests read the pinned submodule commit `2e6e51b1bd78f89b31c358214642ba7e795872e0`.
Measured on 2026-10-25 on the workstation (Windows 11, CPython 3.14):

- Files in the corpus: 6034.
- Parsing every file once (`test_wurth_corpus_parse_budget`): 69.5 s, about 0.012 s per file.
- Whole `-m wurth` run: about 8 min 45 s.

The parse budget is `max(60 s, 0.05 s x number of files)` (`_WURTH_PARSE_BUDGET_PER_FILE` in `tests/test_roundtrip_corpus.py`).
For this corpus the budget is about 302 s.
The earlier fixed 60 s limit was too tight for 6034 files.
