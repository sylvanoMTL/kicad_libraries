---
phase: 11-commit-gate-and-commit-panel-fixes
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_gate.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/test_commit_gate.py
  - tests/test_commit_gate_panel.py
  - tests/test_commit_panel.py
  - tests/test_commit_step.py
  - tests/test_gitops.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 11: Code Review Report (incremental, plans 11-14..11-17)

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Incremental review of the changes since `e8360ef`. The nine earlier findings are fixed correctly as far as the code
shows: the gate's linked check now returns an immutable `_LinkedFindings` and fails closed on unreadable outside
Atomic_ libraries and on an unlistable Symbols folder; `_env` no longer passes the DATE variables; Check again
supersedes a running probe through `_begin_probe_generation` and the stale-worker guards (`worker is not
self._probe_worker`) drop the older results; a refusal's output box and manual command are kept in
`_pending_output` / `_pending_manual` and replayed by `_show_pending`; a changed or added row that was also dirty
before the import gets one combined row and one combined view. No security issue, no crash path and no data-loss
path was found. One new warning: the kept refusal is not forgotten on the Check-again route that starts from the
atomic-fix dialog.

## Warnings

### WR-01: A kept refusal survives the Check again that follows an atomic fix

**File:** `kicad_lib_manager/widgets/import_dialog.py:2976-2982` (with `kicad_lib_manager/widgets/commit_panel.py:739-742, 463-469`)
**Issue:** The panel forgets its kept refusal (`_drop_pending`) only in its own click handlers
(`_on_commit_clicked`, `_on_check_again_clicked`, `_on_switch_clicked`). `ImportDialog._on_atomic_fixes_applied`
calls `self._on_check_again()` directly, so that route never reaches the panel handler. Scenario: Commit is refused
(the commit-time gate or a hook), `show_outcome` stores the refusal text, git output and manual command, the dialog
re-probes and the state is `gated`. The user clicks Open Check Atomic Parts, applies the fixes, and the dialog runs
the re-check. `apply_probe` then calls `_show_pending()` for any state except `refused` / `unavailable`, so the old
red refusal line and its output box stay on top of a `ready` probe with Commit enabled. The new class docstring
says the text stays "until the next Commit, Check again or Switch click", which is not true for this Check again.
The probe's own result and the stale refusal then contradict each other. The new tests exercise only the panel's
own Check again button, so this path is uncovered.
**Fix:** Give the panel a public way to forget the refusal and call it from the dialog before the re-check, for
example:
```python
# commit_panel.py
def forget_refusal(self):
    """Drop the kept refusal, its output and its manual command (the user asked for a fresh check)."""
    self._drop_pending()

# import_dialog.py
def _on_atomic_fixes_applied(self, issues):
    self.atomic_fixes_applied.emit(list(issues))
    if self._commit_panel is not None:
        self._commit_panel.forget_refusal()
    self._on_check_again()
```
Add a dialog test: refuse a commit, reach `gated`, call `_on_atomic_fixes_applied`, and assert
`panel.outcome_lines() == []` and the output box is hidden once the probe is `ready`.

## Info

### IN-01: `refusal_summary` finds the "folder could not be listed" problem by searching its text

**File:** `kicad_lib_manager/importer/commit_gate.py:479-485`
**Issue:** `unlisted = sum(1 for problem in gate.problems if _UNLISTED in problem)` classifies a problem line by a
substring of free text. The other problem lines embed library names and OS or parser error text (`why`), so any line
that happened to contain the phrase would be miscounted and the "N libraries could not be checked" count would be
wrong. It cannot happen with the current messages, but `GateResult.problems` is documented as "the one channel", so
the kind of a problem is not carried in the data.
**Fix:** Keep the kind in the data, for example a separate `unlisted: bool` field on `GateResult` set by
`_check_linked_symbols`, or a small `Problem` tuple of `(kind, text)`. `refusal_summary` then counts by kind.

### IN-02: `combined_view` reports "diff" when one half is an error

**File:** `kicad_lib_manager/importer/commit_step.py:793-805`
**Issue:** When one half is `kind == "diff"` and the other is `"error"` (for example the pre-import copy was not
found in the backup folder), the result is `"diff"`, so the error sentence is run through `DiffHighlighter` as if it
were diff text and the failure looks like part of the diff. When the halves are `error` and `unchanged` the result
is `"text"`, which also hides that one half failed. The body still contains both texts, so no information is lost.
**Fix:** Return `"error"` when either half is an error and keep `"diff"` only when no half is an error, or keep the
kind of the half that failed in the title line of its section.

### IN-03: The case-folding branch of `_env` cannot run in production

**File:** `kicad_lib_manager/gitops.py:84-100`
**Issue:** The `fold_case` branch promotes a differently cased identity key on Windows. Python already upper-cases
every key of `os.environ` on Windows, and `_env()` is only called without an argument in production, so the branch
is reachable only through the injected `environ` / `windows` test parameters. It is harmless and tested, but it adds
a code path and two keyword parameters that real runs never use.
**Fix:** Either keep it as defensive code and say so in the docstring ("`os.environ` already folds on Windows;
this covers an injected mapping"), or drop the fold and the `windows` parameter and test the plain exact-name rule.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
