---
phase: 13-atomic-migration-and-kicad-setup
reviewed: 2026-11-13T00:00:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - CLAUDE.md
  - kicad_lib_manager/importer/categories.py
  - kicad_lib_manager/importer/migration/gate.py
  - kicad_lib_manager/importer/migration/plan.py
  - kicad_lib_manager/importer/migration/symbols.py
  - kicad_lib_manager/importer/siblings.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/kicad_setup.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/migration_dialog.py
  - kicad_lib_manager/widgets/scan_progress.py
  - tests/migrationfixtures.py
  - tests/test_annotations_resolve.py
  - tests/test_categories.py
  - tests/test_help_dialog.py
  - tests/test_kicad_setup.py
  - tests/test_main_window.py
  - tests/test_main_window_chooser.py
  - tests/test_main_window_migration.py
  - tests/test_migration_dialog.py
  - tests/test_migration_dialog_run.py
  - tests/test_migration_full.py
  - tests/test_migration_gate.py
  - tests/test_migration_symbols.py
  - tests/test_scan_skip.py
  - tests/test_siblings.py
  - tests/test_suggest_atomic.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 13: Code Review Report (incremental, diff_base 39406d5)

**Reviewed:** 2026-11-13
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

Incremental review of the gap-closure work since 39406d5 (plans 13-23..13-28: dropdown pick, early Skip, separator-aware family vote and weak votes, guessed-library gate, Pin Atomic Libraries rename, Result-view Destination). I read each source diff in full, traced the new `library_basis` / `weak` data flow from `siblings.pick` through `suggest.suggest_library`, `symbols.plan_symbols`, `gate.check_plan` and `migration_dialog`, and ran the affected test files (siblings, suggest_atomic, categories, migration_gate, scan_skip, kicad_setup: 152 passed; migration_dialog, migration_dialog_run, main_window_migration, help_dialog, annotations_resolve, main_window_chooser: 122 passed).

No crash, data-loss or security defect found. The write paths touched (destination history, Generate outcome, chooser wording) are display-only or constant renames. There are three behavioural defects in the new weak-vote logic and the Result view, all in code that decides what the owner sees or whether Run is blocked.

## Warnings

### WR-01: A weak vote from the owner's own libraries shadows a strong vote from KiCad's libraries

**File:** `kicad_lib_manager/importer/suggest.py:171-186` (and `from_vote`, 152-170)
**Issue:** `suggest_library` returns as soon as the own-library vote is `decided`, before the stock index is consulted. With plan 13-25 a decided own vote can now be weak (found on the bare letters, or under 75%), and `from_vote` only lets the description rescue it. When the description names nothing, the weak own suggestion is returned and the stock step never runs, even when KiCad has a strong vote at a finer prefix. Reproduced:

```
own   = Atomic_Regulator_Switching: TPS62130
stock = Regulator_Linear: TPS7A4700, TPS7A4701, TPS7A8300
suggest_library(PartMeta("TPS7A4702"), own=own, stock=stock)
-> Atomic_Regulator_Switching, source=own, weak=True      (matched only on "TPS")
suggest_library(PartMeta("TPS7A4702"), stock=stock)
-> Atomic_Regulator_Linear,   source=stock, weak=False    (matched on "TPS7")
```

So the part is blocked in the migration as "only a guess" and the better answer was thrown away; the owner has to find it by hand (it is not even in the alternatives, which come only from the own pick's counts).
**Fix:** when the own vote is weak and the description does not decide, keep it as a fallback and continue to the stock step; take the stock vote if it is not weak, else fall back to the own weak vote. For example:

```python
fallback: LibrarySuggestion | None = None
if decided(found):
    voted = from_vote(found, "own", reason)
    if not voted.weak:
        return voted
    fallback = voted          # weak: let KiCad's libraries try
...
# in the stock step
if decided(found):
    voted = from_vote(found, "stock", reason)
    if not voted.weak or fallback is None:
        return voted
...
if fallback is not None:      # before the category/ask tail
    return fallback
```

### WR-02: `SiblingPick.weak` flags overwhelming letter-only majorities, and misses the equally coarse `ICM-` step

**File:** `kicad_lib_manager/importer/siblings.py:66-72`
**Issue:** `weak` is `self.prefix.isalpha() or top*4 < total*3`. Two inconsistencies:
1. Any vote found on the bare letters is weak regardless of margin. The existing test `test_a_weak_vote_nothing_contradicts_is_kept_and_marked_weak` pins `CSD85301Q2` (3 of 4 on `CSD`) as weak, and the live KiCad 10 data is 75 of 77 on `CSD`. A 97% majority is reported to the owner as "only a guess from similar part numbers" and blocks Run until each such part is confirmed by hand whenever the description does not name the kind of part. That contradicts the gate text and the Help page wording ("spread over several KiCad libraries, or matching only on the first letters").
2. The separator-aware step `ICM-` (added in 13-25) is exactly as coarse as `ICM` (an entire manufacturer family), yet `"ICM-".isalpha()` is False, so a 3-letter-plus-hyphen vote is never weak from the prefix rule (only from the 75% rule). `ABC-1234` parts vote strongly on `ABC-` with no description check, while `ABC1234` voting on `ABC` is weak.
**Fix:** decide coarseness by what the prefix contains, and let a lopsided letters-only vote count as strong, e.g.

```python
coarse = not any(c.isdigit() for c in self.prefix)   # letters, optionally a trailing - or _
return (coarse and top * 10 < total * 9) or top * 4 < total * 3
```

(choose the letters-only threshold the owner wants; the point is that the prefix test should use "no digit" rather than `isalpha()`, and should not be unconditional). Update `test_a_vote_on_the_letters_alone_or_a_close_vote_is_weak` and the `csd` assertion accordingly.

### WR-03: Pin Atomic Libraries outcome is never shown in the Result view; only Generate Tables got the new status line

**File:** `kicad_lib_manager/main_window.py:1554-1583` (`_on_setup_chooser`, `_on_chooser_check`)
**Issue:** Plan 13-28 made the migration window window-modal and added a status line under its buttons so the owner sees what Generate Tables did, because the main-window log is not reachable while the dialog is open. The Pin Atomic Libraries button on the same Result page (`setup_chooser_requested` -> `_on_setup_chooser`) gets that treatment only for the blank-Destination case. Every other outcome (refused from a worktree, wrong checkout, KiCad config not found, `chooser.ok` "already pinned", declined, verify failed, kicad_running warning) goes only to `self._log_issues(issues)`, i.e. the log panel of the window that is blocked behind the dialog. Since the owner develops from a git worktree, the very first click on this button after a migration is a refusal that the Result view does not show: the button appears to do nothing.
**Fix:** after `sync_kicad_chooser` returns, derive a one-line outcome from `issues` (reuse the `_generate_outcome` pattern: first ERROR, else first WARNING refusal, else INFO/"pinned") and call `self._set_migration_status(text, severity)` next to the `_log_issues` call. Skip it when `chooser.retry` is returned (the check restarts).

## Info

### IN-01: A Skip pressed for a source that has no 3D model files is accepted and silently does nothing

**File:** `kicad_lib_manager/library_scanner.py:578-590`, `kicad_lib_manager/widgets/scan_progress.py:60-74, 94-98`
**Issue:** Skip is now offered for every source reported while the symbols are read, but `_check_model_files` consults `skip(source)` only per `.kicad_mod` file. A source with symbol libraries and no footprint files is never reported to `checking`/`skip` in the 3D phase, so it never enters `skipped`. The button reads "Skipping X..." (disabled) and the scan result, log line and saved scan record no skip. Harmless, but the label claims an action that did not happen.
**Fix:** in `scan_all`, after `_check_model_files`, add any source requested via `skip(source)` that was never reached (call `skip(s)` for each symbol-library source not already in `skipped` and not seen in the 3D phase) so the result and log are truthful; or have `set_skippable` only offer Skip for sources that own footprint files.

### IN-02: Garbled module docstring in gate.py

**File:** `kicad_lib_manager/importer/migration/gate.py:6-11`
**Issue:** The 13-26 edit spliced a new sentence into the middle of an existing one: "(owner plain-language rule). A part whose library is only a weak guess ... (plan 13-26) — part.issues ERRORs are already plain text by the time they reach here (13-09/13-10/13-11), and atomic-rule violations go through form.atomic_reason ...". The em-dash clause now attaches to the wrong subject and the paragraph is hard to read.
**Fix:** put the guessed-library sentence in its own sentence after the "...strips ki_* names itself." clause.

### IN-03: Test hygiene nits in the new tests

**File:** `tests/test_main_window_migration.py:13-31`, `tests/test_migration_dialog_run.py:563`
**Issue:** `from dataclasses import replace` sits between third-party imports (pytest / PySide6) instead of with the stdlib block. `_result_dialog` waits a fixed `qtbot.wait(200)` and then asserts the result page is current, which can flake on a loaded machine; the same file already has `qtbot.waitUntil` for this transition elsewhere in the plan (`test_real_result_view_changes_the_destination_end_to_end` uses it).
**Fix:** move the import to the stdlib group; replace the sleep with `qtbot.waitUntil(lambda: dialog._stack.currentWidget() is dialog._result_page, timeout=5000)`.

---

_Reviewed: 2026-11-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
