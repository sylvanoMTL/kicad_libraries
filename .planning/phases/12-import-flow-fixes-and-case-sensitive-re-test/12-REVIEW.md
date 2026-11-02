---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-02T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_import_preview.py
  - tests/test_kicad_config.py
  - tests/test_main_window.py
  - tests/test_plain_names.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 12: Code Review Report (gap-closure plans 12-09, 12-10, 12-11)

**Reviewed:** 2026-11-02
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Incremental review of `git diff 55d1107..HEAD` for the Cancel button beside Install Part, the
required-field hints, the "Choose another package..." header button, and the plain-name rewrite for
the KiCad command-line tool and KiCad's settings file.

The behavioural changes are sound. `_cancel_btn` is wired to `reject`, which reaches the existing
`done()` override. That override already refuses while an install or commit runs, defers into
Finishing while a worker is busy, and otherwise closes. `_sync_cancel_button` is called after
`_install_worker` is set and cleared, and from `_set_git_worker`, so the enabled state tracks
`is_installing()` and `is_committing()`. In Finishing the whole `_stack` is disabled, so the Edit
page Cancel cannot be clicked there. The auto-default loop runs after `_build_edit_page`, so the new
button is not a default button.

The message rewrites keep the load-bearing phrases ("Could not", "not found", "timed out after").
No code classifies messages by "kicad-cli" or "kicad_common", and all old strings in tests are updated.

The remaining problems are that the plain-name rule is only partly enforced, and some drift risks.

## Warnings

### WR-01: Plain-name rule (G-12-5) still leaks `kicad_common.json` to the user through interpolated paths

**File:** `kicad_lib_manager/library_scanner.py:261` and `kicad_lib_manager/library_scanner.py:361`
**Issue:** The commit renames the messages that build the name from `config_file.name`, but two
messages still print the full path of the settings file. `config.not_found` shows
`KiCad config not found: C:\...\kicad_common.json (...)`, and `config.written` shows
`Updated C:\...\kicad_common.json (restart KiCad to apply)`. `config.backed_up` shows a path under
`...\kicad_common\9.0\kicad_common.json_backup_1`. These reach the log panel and name the raw file the
owner asked not to see. `tests/test_plain_names.py` cannot catch this, because it looks only at
string constants and the name arrives at run time through the `{config_file}` interpolation. The
guard therefore reports a pass while the rule is still broken. The `config.written` text is also
inconsistent with the sibling messages that now say "KiCad's settings file".
**Fix:** Say the plain name and show the folder, not the file:
```python
f"KiCad's settings file was not found in {config_dir} (start and close KiCad {config_dir.name} once, then Generate again)"
...
f"Updated KiCad's settings file in {config_dir} (restart KiCad to apply)"
```
If the file path is wanted, accept it deliberately and document that in the guard. Then widen the
guard to flag any f-string whose interpolated value is a variable named `config_file` (or
extend the test with a runtime check on the produced `Issue.text`). Update
`tests/test_kicad_config.py`, which asserts the `config.written` and `config.not_found` texts.

### WR-02: The three required-field hints duplicate the atomic-strip sentences instead of deriving from them

**File:** `kicad_lib_manager/widgets/import_dialog.py:90-95`, `kicad_lib_manager/importer/form.py:151-158`
**Issue:** The comment says the hints "mirror" `_ATOMIC_SENTENCES`, but they are separate literals
("Required - enter a Datasheet link" against "Enter a Datasheet link", and so on). Nothing ties
them together. `tests/test_import_dialog.py::test_required_field_hints_match_the_atomic_strip`
checks only the Description field (`endswith("type a description")`). If someone rewords a strip
sentence, for example "Enter the Manufacturer", the Datasheet and Manufacturer hints drift
silently. The guarded property, that the hint matches the reason blocking Install, is only tested
for one of the three fields.
**Fix:** Either build the hints from the shared sentences:
```python
_REQUIRED_HINTS = {name: f"Required - {sentence[0].lower()}{sentence[1:]}"
                   for name, sentence in REQUIRED_SENTENCES.items()}
```
with the sentences defined once in `form.py`, or loop the test over all three fields: empty each
field, wait for the plan, and assert that the strip text ends with the hint's text after
"Required - ".

## Info

### IN-01: Two buttons labelled "Cancel" now exist and the help text uses the word for both

**File:** `kicad_lib_manager/widgets/help_dialog.py:318-329`
**Issue:** "Install and result" now says `Cancel` (Edit page) closes the dialog, and a few lines
later says "Press `Cancel` to stay where you are" (the Finishing strip). In Finishing the Edit page
is greyed out, so the second sentence is unambiguous in practice. A reader who has not seen the
strip may think it is the first button, which closes the dialog, the opposite effect.
**Fix:** Name the strip's button where it is first introduced, for example "the Cancel button in the
Finishing strip", or rename one of them ("Keep working").

### IN-02: Cancel is missing from the hand-built tab order

**File:** `kicad_lib_manager/widgets/import_dialog.py:1902-1918`
**Issue:** `_set_tab_order` chains the header button through the last text Regenerate button and
leaves Install Part and Cancel to the default order. The new Cancel is created after Install, so it
should follow it, but this depends on the Qt focus chain after `setTabOrder` and no test pins it.
**Fix:** Append `self._install_btn, self._cancel_btn` to `chain`, or add a test that tabs from
Install and expects Cancel.

### IN-03: `test_install_progress_and_lock` assertion was weakened

**File:** `tests/test_import_dialog.py:2767-2768`
**Issue:** The assertion that no Cancel button is visible during an install became "no Cancel
button is visible and enabled". The dedicated `test_cancel_button_disabled_while_installing` covers
the disabled state, so nothing is lost today, but the old test no longer detects a stray visible
Finishing-strip Cancel next to the Edit-page one.
**Fix:** Keep the original visibility check for the strip's button (`dialog._finish_cancel.isVisible()`
is False) in addition to the new one.

---

_Reviewed: 2026-11-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
