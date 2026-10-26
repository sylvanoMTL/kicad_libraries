---
phase: 09-atomic-rule-check-and-scan-detection
verified: 2026-10-26T15:00:00Z
status: human_needed
score: 5/5 must-haves verified
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
  - "kicad_lib_manager/atomic_check.py"
  - "kicad_lib_manager/atomic_fixes.py"
  - "kicad_lib_manager/changes.py"
  - "kicad_lib_manager/library_scanner.py"
  - "kicad_lib_manager/main_window.py"
  - "kicad_lib_manager/manufacturers.py"
  - "kicad_lib_manager/models.py"
  - "kicad_lib_manager/widgets/atomic_check_dialog.py"
  - "kicad_lib_manager/widgets/library_table.py"
covered_digest: "v3:sha256:7f25944e229b7597e1371d1da61626b3c573c35103ca90c6f10135086f7a48a5"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open the GUI on a scratch repo (build it with KICAD_ATOMIC_UAT_DIR, tests/test_atomic_uat.py) or on the live Custom/ and look at the library tree after a scan"
    expected: "Failing symbols carry the warning icon and amber row; New/Changed symbols carry the accent colour; libraries with problems auto-expand; tooltips read clearly (rich text, plain language)"
    why_human: "Visual look of marks, colours and tooltips cannot be judged from code. 09-UI-REVIEW scored 17/24."
  - test: "Open Check Atomic Parts (Ctrl+Shift+A, or double-click a failing symbol) on real parts, tick fixes, Preview & apply, then rescan"
    expected: "Dialog lists every violation per symbol, the diff preview matches what lands on disk, a backup exists, and the fixed violations are gone on the next scan (D-25 UAT on real parts)"
    why_human: "D-25 owner UAT on the real parts; the synthetic end-to-end is automated but the owner has to judge the dialog wording and flow"
  - test: "Read the reason wording in the tooltip, log and dialog for each of the seven rules"
    expected: "Owner finds the wording plain and unambiguous"
    why_human: "Wording is a judgment call"
  - test: "Review the canonical manufacturer table (kicad_lib_manager/manufacturers.py) for the Murata and TDK spellings and the acquired-brand entries (Maxim, Linear, InvenSense)"
    expected: "Owner confirms the canonical names and aliases"
    why_human: "Which spelling is canonical is an owner decision flagged by the executors"
  - test: "Decide whether an undigited ${KICAD_3DMODEL_DIR} model path should resolve against KiCad's 3dmodels folder"
    expected: "Owner states the rule; today only ${KICADn_3DMODEL_DIR} (digited) resolves and the undigited form is reported as 'Could not check the 3D model: it uses ${...}'"
    why_human: "Product decision flagged by the executors"
---

# Phase 9: Atomic Rule Check and Scan Detection Verification Report

**Phase Goal:** Every part in an `Atomic_` library is held to the atomic rule on every scan, so a broken or hand-made part is flagged, explained and, where it is safe, fixed in one click
**Verified:** 2026-10-26T15:00:00Z
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|-----------------------------------|--------|----------|
| 1 | After a scan each `Atomic_` symbol that breaks a rule is marked in the tree; the tooltip names each broken rule in plain language; the log has one line per failure; the seven rules are enforced | VERIFIED | `atomic_check.check_libraries` (called from `library_scanner.scan_all` line 544) builds one `Violation` per broken rule for all seven `ATOMIC_RULES` (mpn, manufacturer, footprint, value, datasheet, description, model_3d) and emits one `Issue(WARNING, "atomic.<rule>")` per violation plus a summary line. `widgets/library_table._symbol_row` marks failing rows (warn icon, AMBER) and sets the tooltip from `v.text`. My own probe scan on a synthetic repo reproduced all seven rules and one log line per violation (12 problems, 12 warning lines plus summary). |
| 2 | A derived (`extends`) symbol is judged on its own fields and flagged without its own MPN even if the parent has one; non-`Atomic_` libraries (Wurth etc.) are never flagged | VERIFIED | `effective_mpn` and `_value_violation` read only the symbol's own properties; `_mpn_absent` yields "no MPN of its own (the parent's MPN does not count)". `is_atomic` is the exact case-sensitive `Atomic_` prefix test and `check_libraries` skips every other library. Probe: `CHILD extends ABC1` flagged with that reason while inheriting Datasheet/Description/Footprint cleanly; `Wurth_X` in another source got `atomic=False` and no entries. |
| 3 | A symbol added or changed in KiCad since the last `Custom` commit is highlighted on the next scan | VERIFIED | `changes.mark_changes` (called from `scan_all`) diffs git status paths against HEAD blobs by sexpr token stream (formatting-only edits are not flagged); sets `SymbolEntry.status` new/changed, `FootprintLibrary.changed`, and logs `scan.symbol_new/changed`. Probe: a symbol hand-appended after a commit came back `status=new` with the log line "new since the last Custom commit". `test_scan_changes.py` passes. |
| 4 | The check dialog lists every violation, offers one-click fixes only for Value := MPN, `MF`/`MP` to `Manufacturer`/`MPN`, canonical manufacturer spelling and price/stock leftover removal; each fix is previewed, written with backup, and gone on the next scan; missing Datasheet/Description/3D model can be filled in the dialog or stays an error | VERIFIED | `SAFE_FIX_KINDS` is exactly value_to_mpn, rename_alias, canonical_manufacturer, merge_alias, remove_leftover; `FILL_KINDS` is fill_datasheet, fill_description, attach_model. `atomic_fixes.build_preview` (read-only, SHA-256 staleness) then `apply_preview` (backup dir, atomic write, rollback, `_inside` containment to Custom/). `AtomicCheckDialog` + `MainWindow._open_atomic_check` wire the dialog to menu, Ctrl+Shift+A and tree double-click. Probe: 4 safe specs previewed to one file change, applied with `ok=True`, a backup folder created, and on rescan the MPN, Manufacturer and Value violations were gone while Datasheet/Description/3D model remained as reported errors (fill-ins, not auto-fixes). |
| 5 | A Manufacturer written as an alias is reported with its canonical name from the one manufacturer table, and the fix writes that canonical name | VERIFIED | `manufacturers.MANUFACTURERS` is the single Qt-free table (name, aliases, token, owner); `lookup` folds names and rejects two companies on one key at import. `atomic_check._group_violation` reports `"TI" is not written as "Texas Instruments"` and builds a `canonical_manufacturer` FixSpec carrying `found.entry.name`; `importer/suggest.py` derives its alias map from `manufacturers.token_map()`. Probe: `MF=TI` reported with canonical name and, after the fix, no longer flagged. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/manufacturers.py` (95 lines) | Canonical table, lookup, fold | VERIFIED | Substantive, imported by `atomic_check` and `importer/suggest` |
| `kicad_lib_manager/atomic_check.py` (648 lines) | Seven-rule check, derived symbols, fix specs, `check_libraries` | VERIFIED | Wired from `scan_all`; data flows from real parsed `.kicad_sym` and real directory listings |
| `kicad_lib_manager/atomic_fixes.py` (708 lines) | Preview, backup, atomic apply, model intake | VERIFIED | Wired from `AtomicCheckDialog`; exercised in my probe |
| `kicad_lib_manager/changes.py` (192 lines) | Changed-since-last-commit detection | VERIFIED | Wired from `scan_all` |
| `kicad_lib_manager/models.py` | `Violation`, `FixSpec`, `Finding`, `SymbolEntry`, status constants | VERIFIED | Used by scanner, tree, dialog |
| `kicad_lib_manager/widgets/library_table.py` | Child rows, marks, tooltips, `symbol_activated` | VERIFIED | Connected in `main_window` line 248 |
| `kicad_lib_manager/widgets/atomic_check_dialog.py` | Check dialog | VERIFIED | Opened by menu action, shortcut and double-click; closed with the main window |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `scan_all` | `check_libraries` | direct call, after cross-reference, with KiCad footprint dir | WIRED |
| `scan_all` | `mark_changes` | direct call after the atomic check, so entries exist | WIRED |
| `ScanResult` | `LibraryTableWidget.populate` | `SymbolLibrary.symbols` rendered as child rows | WIRED |
| `LibraryTableWidget.symbol_activated` | `MainWindow._open_atomic_check` | `_on_symbol_activated` | WIRED |
| `AtomicCheckDialog.applied` | `MainWindow._on_atomic_fixes_applied` (log, rescan) | signal | WIRED |
| `check_libraries` violations | log panel | `Issue` list through `_log_issues` | WIRED |
| `manufacturers` | `suggest` and `atomic_check` | import | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 9 test files | `pytest -m "not wurth" tests/test_atomic_check.py test_atomic_dialog.py test_atomic_fixes.py test_atomic_scan.py test_atomic_uat.py test_library_table_atomic.py test_manufacturers.py test_scan_changes.py test_naming_suggest.py` | 344 passed, 1 skipped (the opt-in `KICAD_ATOMIC_UAT_DIR` builder) | PASS |
| End-to-end scan, fix, rescan on a synthetic repo | own script in the scratchpad (scan_all, build_preview, apply_preview, scan_all) | Violations, derived MPN, new-symbol highlight, Wurth skip, fix removal and backup all as described above | PASS |
| Whole suite (orchestrator evidence, not re-run) | `pytest -m "not wurth"` | 2350 passed, 4 documented skips; prior-phase regression gate 6392 passed, 1 skip | PASS (reported) |

### Probe Execution

SKIPPED: no probe scripts are declared by the phase and none exist under `scripts/`.

### Requirements Coverage

All seven phase requirement IDs appear in plan frontmatter and in REQUIREMENTS.md; none is orphaned. REQUIREMENTS.md still shows them as Pending and unchecked; that is a tracking update for the orchestrator, not a code gap.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ATOM-01 | 09-03, 09-04 | Seven rules reported in plain language | SATISFIED | `ATOMIC_RULES`, `_check_ref`, footprint/model resolution through `repo_context` including KiCad's official footprints |
| ATOM-02 | 09-03 | Derived symbols judged on own fields, own MPN | SATISFIED | `effective_mpn`, `_mpn_absent`; probe `CHILD` |
| ATOM-03 | 09-03, 09-04 | Every rule blocking, only `Atomic_` libraries checked | SATISFIED | Every rule is a `Violation` (counts in `SymbolEntry.failing`); leftovers and unknown manufacturers are non-blocking `Finding`s; `is_atomic` gate |
| FLD-02 | 09-01, 09-03, 09-06 | One canonical manufacturer table; alias reported and fixable | SATISFIED for Phase 9 scope | Table used by `suggest` and the check, fix writes canonical name. The migration consumer belongs to Phase 13 and is not claimed here. |
| SCAN-01 | 09-02, 09-03, 09-07, 09-08 | Atomic check every scan; tree mark, tooltip, one log line per failure | SATISFIED | Truth 1 |
| SCAN-02 | 09-02, 09-05, 09-08 | Added or changed symbols highlighted | SATISFIED | Truth 3 |
| SCAN-03 | 09-06, 09-07, 09-08 | Check dialog with safe previewed, backed-up fixes and fill-ins | SATISFIED | Truth 4 |

### Anti-Patterns Found

No `TBD`, `FIXME`, `XXX`, `TODO` or `HACK` marker in any file the phase touched (grep returned nothing). No stub returns on the rendered path.

The 4 warnings and 8 info items in 09-REVIEW.md are all still `open` in 09-REVIEW-DISPOSITION.md. None is a critical finding and none breaks a roadmap truth, so they are advisory warnings, not gaps:

| Item | Severity | Impact |
|------|----------|--------|
| WR-01 `"Preview & apply"` button text loses the `&` and gets `Alt+Space` (`atomic_check_dialog.py:286`) | Warning | Cosmetic and a stolen Windows shortcut; fix is `&&` |
| WR-02 NUL character in a footprint 3D model path aborts the scan | Warning | Robustness edge. I tried the Custom-variable form and it did not crash, so the failing path is a different model form than the one I tried; not re-reproduced |
| WR-03 Two symbols sharing a footprint can attach different models to it | Warning | Edge in the model-attach fill-in |
| WR-04 A refused group leaves model copies registered so a later footprint may link a file never copied | Warning | Edge in the model-attach fill-in; can leave a dangling model link |
| IN-01 to IN-08 | Info | Duplication, dead-ish code, out-of-date User Guide Status text, inconsistent backslash handling |

### Human Verification Required

See the `human_verification` list in the frontmatter. In short:

1. **Visual look of the tree marks and tooltips.** Test: run the GUI on the scratch repo or the live `Custom/`. Expected: amber failing rows, accent New/Changed rows, auto-expand, readable tooltips. Why human: appearance.
2. **D-25 UAT on real parts.** Test: open Check Atomic Parts, tick fixes, preview, apply, rescan. Expected: preview equals disk, backup exists, fixed items gone on the next scan. Why human: owner UAT on real data.
3. **Reason wording for all seven rules.** Why human: judgment of plainness.
4. **Murata and TDK canonical spellings** (and the acquired-brand entries). Why human: owner decision on which spelling is canonical.
5. **Undigited `${KICAD_3DMODEL_DIR}`** should it resolve? Why human: product decision.

### Gaps Summary

No gaps. All five roadmap success criteria hold in the code and were exercised end to end by my own scan, fix and rescan script, in addition to the phase test files (344 passed). All seven requirement IDs are accounted for in plans and in REQUIREMENTS.md. The status is `human_needed` only because the owner has visual, wording, canonical-spelling and real-parts UAT decisions the executors explicitly deferred. Housekeeping for the orchestrator: ATOM-01..03, FLD-02 and SCAN-01..03 are still unchecked and "Pending" in REQUIREMENTS.md, and the ROADMAP Phase 9 checkbox is still `[ ]`.

---

_Verified: 2026-10-26T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
