---
phase: 09-atomic-rule-check-and-scan-detection
verified: 2026-10-26T18:00:00Z
status: passed
score: 11/12 must-haves verified
covered_files:
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-01-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-01-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-02-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-02-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-03-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-03-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-04-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-04-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-05-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-05-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-06-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-06-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-07-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-07-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-08-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-08-SUMMARY.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-09-PLAN.md"
  - ".planning/phases/09-atomic-rule-check-and-scan-detection/09-09-SUMMARY.md"
  - "kicad_lib_manager/atomic_check.py"
  - "kicad_lib_manager/atomic_fixes.py"
  - "kicad_lib_manager/changes.py"
  - "kicad_lib_manager/library_scanner.py"
  - "kicad_lib_manager/main_window.py"
  - "kicad_lib_manager/manufacturers.py"
  - "kicad_lib_manager/models.py"
  - "kicad_lib_manager/widgets/atomic_check_dialog.py"
  - "kicad_lib_manager/widgets/help_dialog.py"
  - "kicad_lib_manager/widgets/library_table.py"
  - "tests/test_atomic_uat.py"
  - "tests/test_help_dialog.py"
  - "tests/test_library_table_atomic.py"
  - "tests/test_main_window.py"
covered_digest: "v3:sha256:1a2c9a25b6de476f8848f33ee5a5ca698e89ab300f84f9d1880c1ef75573645f"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "G-09-1: library tree has no component level; problems only in a tooltip (UAT test 1)"
    - "UAT helper crashed on a symbol without a Datasheet field (unit-level; live run still pending)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run the opt-in live build, outside the repo, once the owner has finished importing into Custom/: git -C Custom status --porcelain > \"$LOCALAPPDATA/Temp/g091_custom_before.txt\"; KICAD_ATOMIC_UAT_DIR=\"$LOCALAPPDATA/Temp/kicad_atomic_uat_g091\" env/Scripts/python.exe -m pytest tests/test_atomic_uat.py::test_uat_atomic_scratch -rs -q -s; git -C Custom status --porcelain | diff - \"$LOCALAPPDATA/Temp/g091_custom_before.txt\""
    expected: "1 passed (not skipped), scratch repo path printed, empty diff of the live Custom/ status. FFC2A32-06-T (no Datasheet field) no longer crashes the helper"
    why_human: "Deliberately not run by the verifier: the owner is importing a part into the live Custom/ right now, so nothing may read or write it. The three helper paths are proven on synthetic fixtures only"
  - test: "Re-test UAT test 1 on the scratch repo: open the GUI, look at an Atomic_ library with problems, expand a failing part, double-click a part and a problem row"
    expected: "Library, then part with its Status count (for example 'Changed - 3 rules') collapsed, then one amber row per broken rule and one plain row per note, full width and readable; double-clicking opens Check Atomic Parts on that part"
    why_human: "Whether the three-level tree reads clearly is the owner's judgment (UAT test 1 was a visual-clarity complaint). 09-UI-REVIEW scored the earlier two-level tree 17/24"
  - test: "Decide on WR-01: double-clicking a part row also expands or collapses it"
    expected: "Owner accepts the toggle, or asks for setExpandsOnDoubleClick(False) on the symbol tree (library and group rows would then also stop toggling on double-click)"
    why_human: "UX judgment on a side effect that does not break any must-have"
---

# Phase 9: Atomic Rule Check and Scan Detection Verification Report

**Phase Goal:** Every part in an `Atomic_` library is held to the atomic rule on every scan, so a broken or hand-made part is flagged, explained and, where it is safe, fixed in one click
**Verified:** 2026-10-26T18:00:00Z
**Status:** human_needed
**Re-verification:** Yes, after gap-closure plan 09-09 (UAT gap G-09-1). Previous report: human_needed, 5/5. No regression found in the five roadmap truths.

## Goal Achievement

### Observable Truths

ROADMAP success criteria (the contract), then the plan 09-09 must-haves.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a scan each `Atomic_` symbol that breaks a rule is marked in the tree; tooltip names each broken rule in plain language; the log has one line per failure; the seven rules are enforced | VERIFIED | Unchanged since the prior report: `atomic_check.check_libraries` called from `scan_all`, `_make_symbol_row` marks failing rows and builds the tooltip from `v.text`. Regression run: `test_atomic_check/dialog/fixes/scan`, `test_manufacturers`, `test_scan_changes`, `test_naming_suggest` 317 passed |
| 2 | Derived (`extends`) symbols judged on their own fields; non-`Atomic_` libraries never flagged | VERIFIED | Unchanged (`effective_mpn`, `is_atomic`); covered by the 317 passing regression tests |
| 3 | A symbol added or changed since the last `Custom` commit is highlighted | VERIFIED | Unchanged (`changes.mark_changes`); `test_scan_changes.py` passes |
| 4 | Check dialog lists every violation and offers one-click, previewed, backed-up fixes for the safe kinds; fill-ins for Datasheet/Description/3D model | VERIFIED | Unchanged (`atomic_fixes`, `AtomicCheckDialog`); `test_atomic_fixes.py`, `test_atomic_dialog.py` pass. Owner UAT test 2 (D-25 on real parts) passed |
| 5 | Alias Manufacturer reported with canonical name from the one table; fix writes it | VERIFIED | Unchanged (`manufacturers.py`, `_group_violation`); `test_manufacturers.py` passes. Owner UAT test 4 passed |
| 6 | G-09-1: each symbol with problems or notes has one row per broken rule then one row per note under it; problem rows first in `violations` order, then notes in `findings` order; text is `Violation.text` / `Finding.text` unchanged | VERIFIED | `library_table._make_symbol_row` (lines 264-271) adds `_make_problem_row(violation.text, ...)` per violation then per finding, text unchanged. My probe: three child rows in order footprint, description, leftover note, text including raw `<b>x</b>`. Tests `test_note_rows_follow_problem_rows_in_order` and siblings pass (37 tests in `test_library_table_atomic.py`) |
| 7 | Problem row: amber text and warning icon; note row: plain text, information icon; both span full width; theme tokens only | VERIFIED | `_make_problem_row` calls `_colour_row(row, AMBER)` for violations, no brush for findings; icons `SP_MessageBoxWarning` / `SP_MessageBoxInformation`; `_span_problem_rows` runs after `group.addChild(item)`. Probe: `isFirstColumnSpanned()` True on all three rows, icons not null. `grep` for a quoted `#RRGGBB` literal outside comments: 0 |
| 8 | After a scan symbol rows start collapsed (library still shows its component list and Status count); libraries holding a failing, new or changed symbol still expand; Expand All / Collapse All reach problem rows | VERIFIED | No `setExpanded` on symbol rows; library auto-expand condition unchanged (line 195). Probe: library expanded True, symbol row expanded False. `test_symbol_rows_start_collapsed_and_libraries_still_expand` and `test_expand_all_and_collapse_all_reach_child_rows` pass |
| 9 | Problem and note rows are display only: no checkbox, no check state; changing them, or Select All / Deselect All, never changes library selection or footprint check states | VERIFIED | `ItemIsUserCheckable` cleared; `_on_sym_item_changed` early-return guard (parent present, data not a `SymbolLibrary`); `_set_all_check_state` walks library rows only. Probe: after `select_all()` problem-row check state is `None` for all rows. Tests `test_problem_row_change_leaves_selection_unchanged`, `test_select_all_gives_problem_rows_no_check_state` pass; `test_library_table_widget.py` unchanged and passing |
| 10 | Double-clicking a problem or note row opens Check Atomic Parts with its parent symbol current, exactly as double-clicking the symbol row does | VERIFIED (WR-01 side effect noted) | `_on_sym_item_double_clicked` steps from a `Violation`/`Finding` row to `item.parent()` and emits `(lib.rel_path, entry.name)`. My probe with real `QTest` mouse clicks on the real widget: double-click on the symbol row emitted `(ATOMIC, "TWO_BAD")`; double-click on a problem row emitted the identical `(ATOMIC, "TWO_BAD")`. End-to-end `test_atomic_problem_row_double_click_opens_dialog_on_its_symbol` (real `MainWindow`, dialog current item "Atomic_Connector / FFC-0.5-20") passes. WR-01 is real (see Anti-Patterns): the symbol row now also toggles its expansion. The must-have is about which symbol the dialog opens on and the emitted arguments, and both are identical for the two rows, so the truth holds. The toggle is a side effect |
| 11 | Problem and note tooltips are escaped rich text; no tree text or tooltip contains an internal field name | VERIFIED | `row.setToolTip(0, _rich_tip([text]))` (html.escape inside `<qt>`); `test_problem_and_note_tooltips_are_escaped` and the `_all_tip_text` "ki_" check pass |
| 12 | UAT helper edits a property the first symbol has (Description, then Datasheet), adds a Datasheet only when it has neither, so the live `test_uat_atomic_scratch` passes on the owner's live Custom/ (FFC2A32-06-T has no Datasheet) and leaves the live Custom/ byte-identical | UNCERTAIN (human) | `_edit_first_symbol` exists and implements Description, ki_description, Datasheet, then insert via `property_insert_edit`, keeping EOL and BOM. Four helper tests pass (no-Datasheet edits Description; no-Description edits Datasheet; neither adds Datasheet; CRLF kept). The live run was deliberately not executed (owner is importing into the live Custom/; verifier instruction). The claim on the live data is therefore unproven, not failed |

**Score:** 11/12 truths verified (0 present, behavior-unverified; 1 uncertain, awaiting the owner)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/widgets/library_table.py` | `_make_problem_row`, `_span_problem_rows`, double-click from a problem row | VERIFIED | Present, substantive, wired from `_make_symbol_row` and `_populate_trees`; double-click handler connected at line 91 |
| `tests/test_library_table_atomic.py` | Three-level tree tests | VERIFIED | 37 tests, contains `isFirstColumnSpanned` |
| `tests/test_main_window.py` | End-to-end problem-row double-click test | VERIFIED | `test_atomic_problem_row_double_click_opens_dialog_on_its_symbol` present and passing |
| `kicad_lib_manager/widgets/help_dialog.py` | Help text for problem and note rows | VERIFIED | "one row for each problem" appears once (line 174); "one row for each note" at line 176 |
| `tests/test_atomic_uat.py` | `_edit_first_symbol` with tests for three paths | VERIFIED (unit level) | `def _edit_first_symbol` line 127, `EDITED_DESCRIPTION` line 41, `property_insert_edit` line 158 |
| Phase 9 artifacts from the prior report (`manufacturers.py`, `atomic_check.py`, `atomic_fixes.py`, `changes.py`, `models.py`, `atomic_check_dialog.py`) | as before | VERIFIED | Files unchanged by 09-09 (diff since `ede4f72` touches only the six 09-09 files); regression tests pass |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `library_table.py` problem rows | `models.py` | `Violation` / `Finding` stored in `UserRole`, imported at line 10-13 | WIRED |
| `library_table.py` | `main_window.py` | `symbol_activated.emit(lib.rel_path, entry.name)` for a problem row's parent, connected to `MainWindow._on_symbol_activated` | WIRED (probe plus end-to-end test) |
| `tests/test_atomic_uat.py` | `kicad_files.py` | `find_property`, `set_property_edit`, `property_insert_edit` etc. | WIRED |
| All earlier phase links (scan -> check, scan -> changes, dialog -> apply -> rescan, manufacturers -> suggest and check) | | | WIRED (unchanged; regression tests pass) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Problem and note rows | `entry.violations`, `entry.findings` | `atomic_check.check_libraries` from parsed `.kicad_sym`, copied onto `SymbolEntry` by `scan_all` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 09-09 test files | `pytest tests/test_library_table_atomic.py test_library_table_widget.py test_main_window.py test_help_dialog.py test_atomic_uat.py test_layering.py` | 135 passed, 1 skipped (opt-in live build) | PASS |
| Phase 9 regression files | `pytest -m "not wurth"` on atomic_check, atomic_dialog, atomic_fixes, atomic_scan, manufacturers, scan_changes, naming_suggest | 317 passed | PASS |
| Real widget, real mouse double-click (own probe, offscreen Qt, scratchpad) | `probe09.py`: populate a 3-row symbol, `QTest.mouseDClick` on the symbol row, then on a problem row, then `select_all()` | Both double-clicks emit the same `(rel_path, "TWO_BAD")`; symbol row expanded True afterwards (WR-01); problem rows span the full width, have icons, no check state, unchanged by `select_all()` | PASS (WR-01 noted) |
| Whole suite (orchestrator evidence, not re-run) | `pytest -m "not wurth"` on merged HEAD | 2371 passed, 4 skipped, 0 failed | PASS (reported) |

### Probe Execution

SKIPPED: no probe scripts are declared by the phase and none exist under `scripts/`.

### Requirements Coverage

All seven phase IDs appear in plan frontmatter (09-09 declares SCAN-01 and SCAN-03; the others are claimed by 09-01 to 09-08) and in REQUIREMENTS.md; none is orphaned.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ATOM-01 | 09-03, 09-04 | Seven rules, plain language | SATISFIED | Truth 1; regression tests |
| ATOM-02 | 09-03 | Derived symbols on own fields | SATISFIED | Truth 2 |
| ATOM-03 | 09-03, 09-04 | Every rule blocking; only `Atomic_` checked | SATISFIED | Truths 1 and 2 |
| FLD-02 | 09-01, 09-03, 09-06 | One canonical manufacturer table; alias reported and fixable | SATISFIED for Phase 9 scope | Truth 5; migration consumer belongs to Phase 13 |
| SCAN-01 | 09-02, 09-03, 09-07, 09-08, 09-09 | Check every scan; tree mark, tooltip, one log line per failure | SATISFIED | Truths 1, 6 to 9, 11. Component-level problem rows now make the marks readable |
| SCAN-02 | 09-02, 09-05, 09-08 | Added or changed symbols highlighted | SATISFIED | Truth 3 |
| SCAN-03 | 09-06, 09-07, 09-08, 09-09 | Check dialog with safe previewed, backed-up fixes and fill-ins; path from marked part to dialog | SATISFIED in code; live UAT scratch build pending | Truths 4 and 10; truth 12 awaits the owner |

REQUIREMENTS.md still shows all seven as Pending / unchecked and ROADMAP Phase 9 is still `[ ]`. That is a tracking update for the orchestrator, not a code gap.

### Anti-Patterns Found

No `TBD`, `FIXME`, `XXX`, `TODO` or `HACK` in the 09-09 source or test files. No stub on the rendered path. No hardcoded colour literal in `library_table.py`.

Open review items (09-REVIEW-DISPOSITION.md lists all as `open`); none is critical and none breaks a must-have, so all are warnings or info, not gaps:

| Item | Severity | Impact |
|------|----------|--------|
| WR-01 (09-09 review): symbol rows now have children, `expandsOnDoubleClick` is still true, so double-clicking a part opens the dialog and also toggles the part's expansion. Reproduced with real mouse events | Warning | Weighed against truth 10: the dialog opens on the right symbol with identical arguments for both gestures, so the truth holds. Side effect is cosmetic: cancelling the dialog leaves the row toggled. Fix, if wanted: `self._sym_tree.setExpandsOnDoubleClick(False)` (this also stops library and group rows toggling on double-click), plus a `QTest.mouseDClick` test. The existing tests emit `itemDoubleClicked` directly, so they cannot see it. Routed to the owner as a decision |
| IN-01 expansion state lost on rescan | Info | Parts the user had expanded collapse after a fix is applied |
| IN-02 libraries holding only notes stay collapsed | Info | Pre-existing condition (`e.failing or e.status`); matches truth 8 as written; notes are still in the tooltip, log and dialog |
| IN-03 UAT helper copies `atomic_fixes._insert_property` | Info | Test-fixture drift risk only |
| Phase-level WR-01 (`&` in "Preview & apply"), WR-02, WR-03, WR-04, IN-04 to IN-08 from the earlier review | Warning / Info | Unchanged from the prior report; edge cases and cosmetics, still open |

### Human Verification Required

1. **Live scratch build on the owner's real Custom/ (deferred on purpose).** Run only after the owner has finished importing. Command in the frontmatter. Expected: `1 passed` (not skipped), scratch repo path printed, empty diff of `git -C Custom status --porcelain`. Why human: the verifier must not read or write the live `Custom/` while the owner is importing; truth 12 is unit-proven only.
2. **Re-test UAT test 1 (G-09-1) on the scratch repo.** Open the GUI; check Library, part (collapsed, with its count), amber problem rows, plain note rows, double-click opens Check Atomic Parts. Why human: it was a clarity complaint; only the owner can judge the new shape.
3. **WR-01 decision.** Accept the double-click expand toggle or switch it off.

### Gaps Summary

No gaps. G-09-1 is closed in code: the Symbols tree now has Library, then Component (with Status count, collapsed), then one display-only row per broken rule (amber, warning icon) and per note (plain, information icon), with unchanged texts, full-width spanning, escaped tooltips, no selection side effects, and double-click on a problem row opens Check Atomic Parts on its parent symbol. I confirmed this with the test files (135 passed plus 317 passed on the regression set) and with my own real-widget, real-mouse probe. The five roadmap truths show no regression and all seven requirement IDs are accounted for in plans and REQUIREMENTS.md.

The status is `human_needed` rather than `passed` for one reason that is not a failure: the opt-in live build against the owner's real `Custom/` (must-have 12, the claim that the helper now survives FFC2A32-06-T) was deliberately not run, and the owner still has to re-test the visual tree (UAT test 1) and decide on WR-01. Housekeeping for the orchestrator: tick ATOM-01..03, FLD-02, SCAN-01..03 in REQUIREMENTS.md and the Phase 9 box in ROADMAP.md once the owner checks are done.

---

_Verified: 2026-10-26T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
