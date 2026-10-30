---
phase: 11-commit-gate-and-commit-panel-fixes
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - kicad_lib_manager/changes.py
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_gate.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/README.md
  - tests/gitfixtures.py
  - tests/test_commit_gate.py
  - tests/test_commit_panel.py
  - tests/test_commit_plan.py
  - tests/test_commit_step.py
  - tests/test_gitops.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_importer_layering.py
  - tests/test_main_window_import.py
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed the Phase 11 changes since `0c5cbd2` (commit gate, Check again / rebaseline / added-file flow, the
non-locking probe, the parent-message builder fixes, identity-variable passthrough in `gitops`). No structural
(fallow) findings were supplied and no external reviewer evidence was given.

The gate logic is sound where I traced it: work-view versus HEAD-view comparison (`_introduced`), the extends-chain
expansion (`_with_changed_parents`, loop-guarded), the dedupe of old/blocking entries in `_check_linked_symbols`,
the path-safety of `linked_custom_files` / `with_added_files` (model names only come from exact directory listings,
and every added path is re-checked with `resolve()` against Custom), and the preview/commit parity of
`parent_message` / `parent_only_preview` / `_parent_text`. No security defects found: git remains the only
subprocess user, the GIT_* strip still holds apart from the six identity variables, all git-derived and
package-derived strings are rendered through plain-text labels.

Three behavioural defects remain, all in the panel/dialog interplay, plus six minor quality items. One defect
(WR-01) was reproduced by running the panel offscreen.

## Warnings

### WR-01: A refused or failed commit loses its git output and the "finish it by hand" command immediately

**File:** `kicad_lib_manager/widgets/import_dialog.py:3070-3073`, `kicad_lib_manager/widgets/commit_panel.py:326-339, 498-509, 447-462`
**Issue:** `_on_commit_done` now calls `show_outcome(outcome)` and, when nothing was committed, immediately calls
`_start_probe(reprobe=True)`. `begin_reprobe()` runs `_clear_outcome()`, which hides the git output box
(`_set_output([])`) and the manual-command label, and then re-renders `_pending_refusal` through `_render_issues`
whose return value (the detail lines of ERROR issues) is discarded. For an ERROR issue only the first line is
kept. Consequences:

- A pre-commit hook rejection: `commit.custom_failed` carries the hook's reason on lines 2..n. They are shown for
  one event-loop turn and then vanish from the panel; only "Commit in Custom failed (git exit 1); nothing was committed" stays.
- A failed parent-only bump (`commit.parent_failed`, `parent_only=True`, nothing committed): the selectable manual
  command (D-16/D-17) is shown and then hidden at once, and its text is not in the surviving first line.

Reproduced offscreen: after `show_outcome(...)` the output box is visible with the hook text; after
`begin_reprobe()` it is hidden and empty, and `_manual_label` is hidden with empty text. The full text is still
in the log (the dialog emits `issues_logged`), but the panel is the place the user is told to act. The existing
tests (`test_panel_parent_only_failure_reprobes`, `test_parent_only_failure_reprobes_in_dialog`) assert the state
before the re-probe or use a single-line failure text, so they do not catch it.
**Fix:** Let `begin_reprobe` keep the detail of the pending refusal. For example, store the rendered detail with
the refusal and restore it:

```python
def begin_reprobe(self, cplan: CommitPlan | None = None):
    ...
    self._probe = None
    ...
    self._clear_outcome()
    extra = self._render_issues(self._pending_refusal)
    self._set_output([*extra, *self._pending_output])   # keep git's output
    if self._pending_manual:
        self._manual_label.setText(self._pending_manual)
        self._manual_label.show()
```

with `_pending_output` / `_pending_manual` set in `show_outcome` on the not-committed branch and cleared wherever
`_pending_refusal` is cleared. Add a dialog-level test whose failing outcome has a multi-line `output` and a
`manual_command`, and assert both are still visible once the second probe has been applied.

### WR-02: A file that is both "changed since install" (or "added by a fix") and dirty before the import loses the pre-import warning

**File:** `kicad_lib_manager/widgets/commit_panel.py:560-585`, `kicad_lib_manager/widgets/import_dialog.py:3033`
**Issue:** `_mark_files` uses an `if changed / elif added / elif rel in probe.dirty_before` chain. When a planned
file also differs from HEAD for reasons that predate the import (`dirty_before`), the dirty branch is skipped
whenever the file is marked changed or added. The row, its tooltip and the hints then say nothing about
"also contains uncommitted changes made before this import. It is committed too", `any_dirty` is not set for that
row, and `_on_commit_file_activated` routes the double-click to `changed_diff` (any non-empty `note`), so the
pre-import diff (D-09) cannot be reached either. Edits made in KiCad after the install are the usual cause of
"changed", so this combination is realistic: the one file whose history the user most needs to review before
committing is the one where the warning is dropped. The commit still includes those pre-import changes.
**Fix:** Evaluate the dirty state independently and combine the marks and tooltips, and offer both views (for
example `changed_diff` on double-click and `pre_import_diff` on a second action, or one combined text):

```python
dirty = rel in probe.dirty_before
if changed or added:
    ...
    if dirty:
        any_dirty = True
        item.setToolTip(item.toolTip() + " It also contains uncommitted changes made before this import.")
```

and add a panel test for a row that is in `dirty_before` and has `note == NOTE_CHANGED`.

### WR-03: An unreadable Atomic_ library that links a committed file passes the gate with only an unseen INFO note

**File:** `kicad_lib_manager/importer/commit_gate.py:223-230, 321-323`; `kicad_lib_manager/widgets/commit_panel.py:545`
**Issue:** The module contract says "A committed library that cannot be read refuses the commit rather than passing
it". `_check_linked_symbols` does not apply that rule to the other Atomic_ libraries: when one cannot be read or
parsed it appends a note (`gate_issues` logs it as INFO `commit.atomic_note`) and `continue`s, so
`GateResult.refused` stays False and the panel goes to `ready`. The panel only renders `old_notes(gate)`; `gate.notes`
is never shown, so the user sees no sign that the check was incomplete. If the commit changes a footprint or model
that parts in that library link, those parts are not judged at all and the commit proceeds. This fails open in the
safety gate, contrary to the stated design for the committed libraries. (`test_gate_unreadable_outside_library_is_a_note`
pins the behaviour, so it is deliberate, but the notice is invisible where it matters.)
**Fix:** Either refuse (add the library to `problems` whenever it cannot be read while `footprints` or `models`
is non-empty, accepting a possible false refusal), or at minimum show `gate.notes` in the panel as an amber line
next to the old-failure notes and say in the text that those parts were not checked.

## Info

### IN-01: Dead code left in the new and touched modules

**File:** `kicad_lib_manager/widgets/commit_panel.py:33-35, 617, 32`; `kicad_lib_manager/importer/commit_gate.py:60-65`; `kicad_lib_manager/importer/commit_step.py:35`
**Issue:** `_STATES` is never read. `ready = state == "ready"` in `_set_state` (line 617) is assigned and never used.
`GateResult.first_failure` is used only by a test (the panel uses `gate.blocking[0]` directly, so the property and
the panel can disagree on which failure is first when only old failures exist). `CANCELLED_REASON` is an alias of
`CANCELLED` kept for one module. `_WARNING_NOISE ="..."` is missing a space.
**Fix:** Delete `_STATES` and the unused local; have `_on_open_check_clicked` use `first_failure` or remove the property;
use one name for the cancel text.

### IN-02: `_check_linked_symbols` takes 12 parameters, four of them output lists

**File:** `kicad_lib_manager/importer/commit_gate.py:195-263`
**Issue:** The function mutates `blocking`, `old`, `notes` and `entries` in place and rewrites `old` and `entries`
with slice assignment to "move" a failure. This makes the dedupe rule (lines 254-262) hard to follow and to test in
isolation.
**Fix:** Return a small result object (or a tuple of the four lists) and let `run_gate` merge it, keeping the
"listed as old, now introduced" move in one named helper.

### IN-03: Probe supersede logic is duplicated and the two entry points disagree on a running probe

**File:** `kicad_lib_manager/widgets/import_dialog.py:2866-2886, 2916-2937`
**Issue:** `_start_probe` and `_on_check_again` repeat the cancel-older / new-Event / reset block. `_start_probe`
supersedes a running probe, while `_on_check_again` silently returns when `_probe_worker` is not None. That also
swallows the re-check requested by `_on_atomic_fixes_applied`, leaving the panel on a probe that predates the fix.
It is not reachable today (the check dialog is window-modal over a gated panel), but it will drop a request if that changes.
**Fix:** Extract `_begin_probe_generation()` returning the new Event, and let `_on_check_again` supersede instead
of returning when only a probe is running (still refuse while `_git_worker` is set).

### IN-04: `_EARLIER_SHOWN` is reused as the cap for gate failure lines

**File:** `kicad_lib_manager/widgets/commit_panel.py:28, 538-539`
**Issue:** The constant is documented as "earlier Custom commits listed before '...and k more'" but also caps the
refusal lines. Changing one silently changes the other.
**Fix:** Add `_GATE_LINES_SHOWN = 10`.

### IN-05: "(added by a fix)" is wrong for linked files the user created themselves

**File:** `kicad_lib_manager/widgets/commit_panel.py:41, 567-571`; `kicad_lib_manager/importer/commit_step.py:376-410`
**Issue:** `_with_linked_files` also adds an untracked footprint or model that a committed part links, whether or not
a fix created it (for example a model the user copied into `Custom/3DModels` by hand). It is labelled "added by a
fix" and the help text repeats that. The tooltip is accurate ("committed because a committed part links it"); the row text is not.
**Fix:** Word the mark as "(added: linked by a committed part)", or keep "added by a fix" only when the Check Atomic Parts dialog applied one.

### IN-06: `gitops._env` promotes lower-case identity variables on every platform

**File:** `kicad_lib_manager/gitops.py:87`
**Issue:** `env.update({k.upper(): v for ... if k.upper() in _IDENTITY_VARS})` is meant for Windows, where a shell can
spell the name in lower case. On POSIX, `git_author_name` is not a variable git reads, yet it is promoted to
`GIT_AUTHOR_NAME`, and if both spellings exist the one iterated last wins. This also forwards `GIT_AUTHOR_DATE` and
`GIT_COMMITTER_DATE`, so a stale exported date is stamped on every commit made by the app (git itself would do the
same in that shell, but the app is a GUI launched from elsewhere and the dates are not identity).
**Fix:** Only fold case on `win32`, prefer an exact upper-case key when present, and consider leaving the two
`*_DATE` variables out of `_IDENTITY_VARS`.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
