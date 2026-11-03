---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-03T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
covered_files:
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-12-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-12-SUMMARY.md
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/backup_dialog.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/theme.py
  - tests/casefixtures.py
  - tests/test_case_sensitive_install.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_plain_names.py
covered_digest: "v3:sha256:cf1a572967df91cec73fe257690eb918b0f9d45648ba131f01f98fd6cc48991c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "G-12-9 the User Guide is reachable from the import window: toolbar Help and F1 on the start, edit and result pages (plan 12-12)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "UAT 9(d) re-check, the item that failed: start the app, press Ctrl+I, and look at the import window before opening a package, then open downloaded_examples\\ul_CSD85301Q2.zip and pick an Atomic_ target library"
    expected: "A toolbar row at the very top of the import window (start page, edit page and result page) shows the standard help icon with the word 'Help' beside it. Clicking it, or pressing F1, opens the User Guide on 'Importing Parts' in a second window. The import window stays open. You can click and type in both windows. Closing or cancelling the import window also closes the guide. The row fits the window: icon and text not clipped, spacing not odd, no stray gap or line"
    why_human: "Real-window appearance and feel. The offscreen test render had no fonts, so nobody has seen the toolbar drawn. The tests assert the widget tree, the action text, the tooltip and the click behaviour through the window system, not how it looks"
  - test: "UAT 3 (blocked earlier by the worktree guard): from the main checkout, change CUSTOM_3DMODEL_DIR in KiCad, leave KiCad open, press Generate Tables"
    expected: "Dialog 'KiCad is open' with Retry (default), Change anyway, Not now. Retry after closing KiCad leads to the Yes/No question. Not now writes nothing"
    why_human: "Needs a live KiCad process and a modal dialog; the tests replace kicad_running"
  - test: "UAT 4 (skipped by owner): Finishing strip during a real kicad-cli rebuild"
    expected: "Dialog greys out with 'Finishing the preview...', window stays live, slow note after 10 s, no hang"
    why_human: "Real timing; covered only by gated stand-in workers. The owner chose to skip the manual check"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-03
**Status:** human_needed
**Re-verification:** Yes, after gap-closure plan 12-12 (G-12-9, toolbar Help in the import window), merged at 0c038a1. The previous report (2026-11-02) is replaced. Plans 12-01..12-11 were verified there; their code is unchanged since (`git diff 0c038a1 -- kicad_lib_manager tests` is empty, so the code under test is exactly the merged tree).

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | "Already listed" only when the managed entry points at that library; empty Destination writes no table, never in the working directory | VERIFIED | `table_generator._add_entry` / `_same_rel`; `main_window._dest_path()` returns None for blank text and each caller stops. Not touched by 12-12 (diff is limited to import_dialog.py, help_dialog.py and two test files). Covered by the orchestrator's full suite (9290 passed) |
| 2 | One-off conflict build never runs during Install; window responsive while the command-line tool works | VERIFIED (live timing is a human item) | Finishing state and `_pump_builds` unchanged. 12-12 adds Help that stays live in Finishing: `test_help_works_while_finishing_and_closes_with_the_dialog` passes, re-run here |
| 3 | KiCad-running confirm says so before writing; confirmed write starts from current content | VERIFIED (real dialog is a human item) | `library_scanner.sync_kicad_path_vars` re-reads after confirm; `main_window._kicad_open_box`. Unchanged by 12-12; full suite green |
| 4 | Help dialog and conflict rows use theme tokens only | VERIFIED | No colour literal or px font in help_dialog.py or conflict_row.py. 12-12 adds `topic`/`show_topic` and two text paragraphs only; the new toolbar has no stylesheet (own read of `_build_toolbar`, lines 528-545). tests/test_help_dialog.py passes (inside the 28-test targeted run) |
| 5 | Case-twin rollback proven on a case-sensitive folder | VERIFIED | tests/test_case_sensitive_install.py re-run here with `-rs`: no skip lines, passes (28 passed across the three files run) |

### Gap-closure truths

| Gap | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| G-12-9 | A toolbar above the page stack, shared by every page, whose only action is Help (F1) | VERIFIED | `_build_toolbar(outer)` is called at import_dialog.py:506, before `outer.addWidget(self._stack)` at 507, so the toolbar is item 0 of the outer layout and outside the stack (Finishing disables only the stack). `QToolBar` has one action `_help_action` with `HELP_ACTION_TEXT = "Help"` (line 88), tooltip `_HELP_TIP` (89), `QKeySequence("F1")`, WindowShortcut context. No separate F1 `QShortcut` exists: the only `QShortcut(` in the module is Ctrl+Return (line 519) |
| G-12-9 | Help or F1 opens the User Guide on Importing Parts; the import window stays open and both take input | VERIFIED | `_on_help` (547-561): function-level import of `HelpDialog` (avoids the circular import with help_dialog.py's module-level import of import_dialog texts), `HelpDialog(topic="importing", parent=self)`, then `show()`, never `exec()`. `grep -v '^\s*#' import_dialog.py \| grep -c setModal` prints 0. `test_import_window_takes_input_while_help_is_open` clicks through the window system on `windowHandle()` and passes |
| G-12-9 | One reused Help window; it closes with the import window on every exit path | VERIFIED | `_help_dialog` initialised line 392, reused via `show_topic` on a second press (line 558), swapped to None and closed in `_shutdown` (3409-3411). `_shutdown` is called from `_finish_close` (Cancel, Escape, result Close, Finishing close) and `closeEvent` (X). Lifecycle tests pass |
| G-12-9 | Help works while rebuilding, Finishing, installing and committing, and changes no import state | VERIFIED | `_on_help` reads and writes no import state; no enable/disable logic for the action. `test_help_works_while_installing`, `_while_committing`, `_while_finishing_and_closes_with_the_dialog` pass |
| G-12-9 | `HelpDialog(topic=...)` opens on that topic, unknown or None opens Overview; main window Help unchanged | VERIFIED | help_dialog.py:486 `__init__(self, parent=None, *, topic=None)`, `show_topic` (520-530) walks both TOC levels, falls back to `topLevelItem(0)` at 517-518. main_window.py:1308 still `HelpDialog(parent=self).exec()`. `test_help_dialog_opens_on_a_given_topic` passes |
| G-12-9 | Help pages name the toolbar Help and F1 | VERIFIED | help_dialog.py:225-227 (Start section, via `+ HELP_ACTION_TEXT +`) and 438-439 (Keyboard Shortcuts F1 row). `test_help_names_the_toolbar_help` passes. Both paragraphs use plain words |
| G-12-5..8 | Plain names, Cancel, required hints, "Choose another package..." (plans 12-09..11) | VERIFIED (previous report; no change) | Not changed since; `tests/test_plain_names.py` re-run and passes |

**Score:** 6/6 truths verified (5 roadmap success criteria plus the G-12-9 gap-closure contract; 0 present-but-behavior-unverified).

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `widgets/import_dialog.py` `HELP_ACTION_TEXT`, `_build_toolbar`, `_on_help`, `_shutdown` closes guide | VERIFIED | present, substantive, wired (exact line numbers above) |
| `widgets/help_dialog.py` `topic`, `show_topic`, two text paragraphs | VERIFIED | lines 486-530, 225-227, 438-439 |
| `tests/test_import_dialog.py` 7 named tests (toolbar, F1, every page, installing, committing, finishing, real clicks) | VERIFIED | all 7 names exist (lines 5830-6007) and pass |
| `tests/test_help_dialog.py` `test_help_dialog_opens_on_a_given_topic`, `test_help_names_the_toolbar_help` | VERIFIED | lines 397, 424; pass |
| 12-01..12-11 artifacts | VERIFIED | previous report; unchanged |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| `ImportDialog.__init__` -> `_build_toolbar(outer)` before `outer.addWidget(self._stack)` | WIRED (506 < 507) |
| `_help_action.triggered` -> `_on_help` (F1 is the action's own shortcut) | WIRED (line 541) |
| `_on_help` -> `HelpDialog(topic=_HELP_TOPIC, parent=self)` | WIRED (556; one indented import in the method) |
| `help_dialog` HELP_PAGES -> `HELP_ACTION_TEXT` | WIRED (import at line 8, used at 225 and 439) |
| `_shutdown` -> closes `_help_dialog` | WIRED (3409-3411) |
| `main_window._on_help` -> `HelpDialog(parent=self).exec()` | UNCHANGED (1308) |

### Data-Flow Trace (Level 4)

Not applicable to 12-12: static strings and a read-only window. No dynamic data rendered by the new code.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Help topic, Help text, plain-name guard, case-twin rollback | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_plain_names.py tests/test_case_sensitive_install.py -q -rs` | 28 passed, no skips | PASS |
| Toolbar, F1, every page, every state, real clicks, Cancel, Ctrl+Return | `pytest tests/test_import_dialog.py -q -k "toolbar_help or f1_opens or help_reachable or help_works or takes_input_while_help or cancel_button or ctrl_return"` | 13 passed, 219 deselected | PASS |
| Full suite at 0c038a1 (orchestrator evidence, not re-run: about 20 min) | `pytest -q` | 9290 passed, 4 expected skips (2 UAT-dir, 2 symlink privilege), 0 failed, 19 min 37 s. No source change since | PASS (reported) |

### Probe Execution

No `probe-*.sh` declared or found. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5, tests re-run |
| UI-01 | 12-02, 12-12 | SATISFIED | SC4; the 12-12 toolbar adds no colour or px font (no stylesheet) |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08, 12-09, 12-11 | SATISFIED | SC2 (live timing pending, human item 3) |
| REV-05 | 12-06, 12-08, 12-10 | SATISFIED | SC3 (live dialog pending, human item 2) |

All seven IDs from the task appear in PLAN frontmatter (`requirements:` of 12-01..12-12) and in REQUIREMENTS.md; no orphaned requirements.

**Bookkeeping, not a goal gap:** REQUIREMENTS.md still shows all seven as `[ ]` and "Pending" (lines 88-96, 106, 169-181). ROADMAP.md line 33 shows Phase 12 unchecked, and line 258 still says "1 gap-closure plan pending: 12-12" although the 12-12 box is checked. The orchestrator should flip these on phase completion. 12-UAT.md still records G-12-9 as `status: failed`; it should be set to resolved only after human item 1 passes.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK in import_dialog.py or help_dialog.py. No stubs or hollow props in the new code. 12-REVIEW.md (3bd328b): 0 critical, 1 warning, 4 info. The warning WR-02 (the three required-field hints in `_REQUIRED_HINTS` duplicate the atomic-strip sentences instead of deriving from them, so they could drift) is carried from plan 12-09 and is guarded by `test_required_field_hints_match_the_atomic_strip`; advisory, no success criterion depends on it. 12-SECURITY.md: status verified, 31 threats closed, `threats_open: 0`.

### Prohibitions

- Test-tier, 12-12: Help never closes, blocks or resets the import window (real-click and state tests pass); exactly one F1 binding (no F1 `QShortcut` in the module, the action carries the only F1); toolbar has no colour literal or px font (no stylesheet). All wired to named, passing tests.
- Judgment-tier (12-08), "User-facing text must not use raw KiCad field names or code identifiers": the new toolbar tooltip and Help paragraphs read "Help", "toolbar", "User Guide", "Importing Parts" with no identifier or tool name. Mechanical verdict: satisfied. Plain-language judgment of the wording stays with the owner (human item 1).

### Human Verification Required

1. **Toolbar and Help in the real window (UAT 9(d) re-check, the gap that failed).** Test: run `.\env\Scripts\python.exe kicad_lib_manager.py`, press Ctrl+I, look at the import window on the start page, then open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ library, press Help, press F1 on the edit page, and cancel the import window. Expected: the toolbar row with the help icon and "Help" sits at the top of every page and looks right; Help or F1 opens the User Guide on Importing Parts; the import window stays open and both windows take input; cancelling the import window closes the guide. Why human: nobody has seen the toolbar drawn with real fonts; tests assert structure and behaviour, not appearance.
2. **UAT 3 live KiCad-open dialog** from the main checkout. Why human: live KiCad process and modal dialog.
3. **UAT 4 (owner skipped)**: Finishing strip with a real kicad-cli rebuild. Why human: real timing; covered only by stand-in workers.

### Gaps Summary

No gaps. G-12-9 is closed in code and by 13 targeted import-window tests, 28 help/plain-name/case-twin tests re-run here, and the orchestrator's full suite (9290 passed, 0 failed, no source change since). Status is `human_needed` solely because the toolbar's appearance and the live-window Help flow (the item that failed UAT), the live KiCad-open dialog and the live rebuild cannot be confirmed programmatically.

---

_Verified: 2026-11-03_
_Verifier: Claude (gsd-verifier)_
