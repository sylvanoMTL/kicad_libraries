---
phase: 08-test-isolation-and-kicad-10
reviewed: 2026-10-25T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - pyproject.toml
  - tests/README.md
  - tests/clifixtures.py
  - tests/conftest.py
  - tests/customfixtures.py
  - tests/installfixtures.py
  - tests/test_clifixtures.py
  - tests/test_commit_plan.py
  - tests/test_customfixtures.py
  - tests/test_import_dialog.py
  - tests/test_import_preview.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
  - tests/test_installfixtures.py
  - tests/test_kicad_cli.py
  - tests/test_naming_suggest.py
  - tests/test_real_vendor_samples.py
  - tests/test_roundtrip_corpus.py
  - tests/test_vendor_install.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-10-25
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

This phase changed test code only. I read every listed file, diffed each against `c1cf1de`, and ran the changed modules. KiCad 10.0 is installed on this machine, so the real-binary tests ran for real. Results: `test_customfixtures`, `test_clifixtures`, `test_install_e2e`, `test_install_plan`, `test_kicad_cli`, `test_installfixtures`, `test_commit_plan`, `test_import_preview`, `test_naming_suggest`, `test_install_apply`, `test_vendor_install`, `test_real_vendor_samples` and `test_import_dialog` all pass (the only skip is the `KICAD_IMPORT_UAT_DIR` one).

The isolation work is sound. No remaining test reads `custom_copy`, and the synthetic tree is built only from byte builders under `tmp_path`. The `ul_package` staging folder is a temp dir, with an in-repo staging refusal. The `test_main_window*` modules already redirect `QSettings`. Moved tests keep real assertions: the `[+, +, ~]` and `[=, =, =]` preview rows, the version-mismatch text and the header-unchanged checks all still discriminate. I found no blockers.

The weaknesses are in the new guard and gate. The guard can fail or crash on files that are not test writes, and it reports late and without attribution. The gate checks only the major version while the tests pin an exact minor and format, and it can turn the whole real-binary tier into skips without any failure.

## Warnings

### WR-01: The live-Custom guard digests every file with no error handling, so a transient file can fail the run or error the whole suite

**File:** `tests/customfixtures.py:103-112` (`digest_tree`), `tests/customfixtures.py:143-147` (`guard_custom`)
**Issue:** `digest_tree` does `rglob("*")` and then `path.read_bytes()` with no `OSError` handling. The guard digests the live `Custom/` at session start and at session end.

- **Crash at start.** The start digest runs in session-scoped autouse setup. If a file listed by `rglob` vanishes before it is read, or is unreadable, `read_bytes` raises. A dangling symlink or a file that disappears mid-walk does this. Every test in the session then errors at setup. The failure message gives no hint that the cause is an unrelated file.
- **False failure at end.** The owner uses these libraries from KiCad, and the run takes about 18 minutes. KiCad and git create and delete files inside `Symbols/`, `Footprints/*.pretty/` and `3DModels/`. Examples are `~*.lck` lock files, `_autosave-*` files and `fp-info-cache`. Any such file that exists at the start or end of the run, but not at the other, makes `custom_changes` non-empty. The run then fails with "the test run changed the live Custom/ folder" even though no test wrote anything.

The README only warns about hand edits. The failure mode is a red run the owner cannot attribute to a test.

**Fix:** Tolerate unreadable and vanished entries when digesting, and ignore known editor and lock artifacts.

```python
_IGNORED = ("~", "_autosave-", "fp-info-cache")

def digest_tree(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.name.startswith(_IGNORED) or path.name.endswith((".lck", ".bak")):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            if path.is_dir():
                found[rel + "/"] = "dir"
            else:
                found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as e:
            found[rel] = f"unreadable:{type(e).__name__}"
    return found
```

If the ignore list is applied only to the guard, keep `digest_tree` strict for the `snapshot` fixture. That fixture compares trees under `tmp_path` that the tests own.

### WR-02: Write detection moved from per-test assertions to one end-of-session check, so the offending test is never named and the damage has already happened

**File:** `tests/conftest.py:128-136`, `tests/customfixtures.py:137-153`; removed from `tests/test_install_e2e.py` (the module-scoped `_real_custom_untouched`, and the `real_before`/`real_after` asserts in `test_ul_symbol_added_others_identical`) and from `tests/test_install_plan.py` (`test_library_pair_completed_pretty_missing`)
**Issue:** The old checks failed in the module or test that wrote. The new guard fails once, in session teardown, up to about 18 minutes later. The message lists changed paths but not the test. The guard is documented as a "write-protect guard", but it only detects. By the time it reports, the live `Custom/` has already been modified. It also cannot see a write that is later undone.

**Fix:** Keep the session guard, and add a cheap per-test check. Either make the guard function-scoped for the writing tiers (install, e2e, dialog), or add an autouse function fixture that compares a cached digest only when `request.node.get_closest_marker(...)` or the module name matches. A real write-protect is also possible: set the read-only attribute on the live `Custom/` files for the session and restore it in teardown. That makes the offending test fail at its own write. At minimum, reword the docstrings from "write-protect" to "change detector", and record the current test's node id so the failure can say who ran last.

### WR-03: The gate checks only the KiCad major version, but the tests assert an exact format number and generator version

**File:** `tests/clifixtures.py:22-25`, `tests/clifixtures.py:42-44`
**Issue:** `check_kicad_cli` accepts any `10.x`. It does this with `_VERSION_RE.match` and `int(match.group(1)) == KICAD_MAJOR`, and the minor group is captured but never used. The consuming tests then pin `KICAD_SYMBOL_FORMAT = 20251024` and `KICAD_GENERATOR_VERSION = "10.0"` exactly. Examples are `(version 20251024)`, `(generator_version "10.0")` and `plan.target_version == KICAD_SYMBOL_FORMAT`. Two cases now produce hard assertion failures instead of a skip with a reason:

- A `10.99.x` development build, whose version string starts `10.`, passes the gate.
- A future `10.1.x` that writes `"10.1"` as the generator version passes the gate.

The module docstring says a real-binary test "only runs against the major version in KICAD_MAJOR", so the gate and the asserted constants disagree on what "KiCad 10" means.

**Fix:** Gate on the same granularity the constants assume, or derive the expected generator version from the probed binary.

```python
KICAD_MINOR = 0
...
if match and (int(match.group(1)), int(match.group(2))) == (KICAD_MAJOR, KICAD_MINOR):
    return exe, ""
```

Alternatively, keep the major-only gate and have the tests compare against what the probed binary reports. Also add a unit test in `tests/test_clifixtures.py` for `"10.99.0"` and `"10.1.0"`.

### WR-04: The gate can silently turn the entire real-binary tier into skips, and a failed probe is cached for the whole session

**File:** `tests/clifixtures.py:50-54`, `tests/conftest.py:98-106`, `tests/README.md:35`
**Issue:** The only protection against a green run that exercised no KiCad is the owner reading `-ra` output and the README's "exactly three skips" rule. Two situations produce that outcome:

- A newer KiCad (for example 11) is installed. "Newest install first" then selects it, the gate refuses it, and every `kicad_cli`-marked test skips. There is no fallback to the installed 10, by design. There is also no way to point the gate at one, such as a `KICAD_CLI_10` override.
- The one-time probe has a 30 s timeout (`VERSION_TIMEOUT`). `@functools.cache` stores the failure, for example a cold-start timeout caused by antivirus on first launch. All real-binary tests then skip for the whole session even though the next call would have succeeded.

**Fix:** Add an explicit strict mode so a missing or wrong binary can be made a failure when it should not be silent. For example, if `KICAD_CLI_REQUIRED=1`, call `pytest.fail(reason)` instead of `pytest.skip(reason)` in `kicad_cli_path`. Optionally accept an explicit executable override in `located_kicad_cli`. Do not cache a probe result that failed from `Issue`, timeout or non-zero exit. Cache only a definite "wrong major" or a success.

## Info

### IN-01: `test_every_synthetic_library_loads_in_kicad_cli` passes file names that already include `.kicad_mod`

**File:** `tests/test_customfixtures.py:134-137`
**Issue:** The footprint list is built with `(path.name, path.read_bytes())`. `load_gate` stages each entry as `f"{fp_name}.kicad_mod"`, so the staged files are named `X.kicad_mod.kicad_mod`. Every other caller passes the stem (`op.path.stem`, `"DQK0006B"`). I checked this: the real binary still loads the doubled name and still rejects garbage, so the test is not vacuous. But it exercises a naming shape the app never produces, and the footprint name KiCad sees in that staging folder is `X.kicad_mod`.
**Fix:** Use `path.stem`.

```python
footprints = [
    (path.stem, path.read_bytes())
    for path in sorted((layout.footprints_dir / f"{lib.name}.pretty").glob("*.kicad_mod"))
]
```

### IN-02: The Wurth parse budget now scales with the corpus and is about 4.3 times looser than the measurement

**File:** `tests/test_roundtrip_corpus.py:206-208`, `tests/test_roundtrip_corpus.py:255-258`
**Issue:** The measured time is 69.5 s for 6034 files, and the budget is `max(60, 0.05 * 6034)`, about 302 s. The 60 s floor can never apply to this corpus. The test now only fails on a roughly 4x regression, or on a slower machine by luck. It also guards a quantity, wall-clock time, that varies with the machine. The change itself was correct, because the old fixed 60 s was already exceeded.
**Fix:** If this is meant to catch parser regressions, size it from the measurement with a stated margin (for example 2x, about 0.025 s per file). Otherwise mark it as a smoke bound and say so in the comment.

### IN-03: The README's list of read-only live-Custom tests is incomplete

**File:** `tests/README.md:63-73`
**Issue:** The list names five consumers of the live `Custom/`. At least `tests/test_locate_text_caps.py::test_real_files_are_below_both_caps` (`REPO_ROOT / "Custom"`, `rglob`) also reads it, and it skips when `Custom/` is absent. The "no test result may depend on which parts it holds" rule at the top of the README therefore has undocumented exceptions. Part counts and sizes do change `test_real_files_are_below_both_caps`.
**Fix:** Add it to the list, or run a grep over `tests/` for `REPO_ROOT / "Custom"` and list every hit.

### IN-04: The UAT test removes a folder named `Custom` under a user-supplied path

**File:** `tests/test_install_e2e.py:586-592` (pre-existing logic, kept by this phase)
**Issue:** The guard conditions only ensure `KICAD_IMPORT_UAT_DIR` lies outside the repository and that `uat/Custom` is not a symlink. If the owner points the variable at a folder that holds an unrelated `Custom` directory, the test `shutil.rmtree`s it. Previously the same code only ever rebuilt a copy it had made itself; now it is a scratch tree that `write_synthetic_custom` recreates, so the risk is unchanged but easier to miss.
**Fix:** Refuse to run when `scratch` exists and does not contain a marker file the test wrote, or write the scratch under `uat / "kicad-import-uat" / "Custom"` and remove only that.

---

_Reviewed: 2026-10-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
