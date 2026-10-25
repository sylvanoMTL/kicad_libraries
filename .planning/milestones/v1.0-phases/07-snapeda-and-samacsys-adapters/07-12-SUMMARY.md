---
phase: 07-snapeda-and-samacsys-adapters
plan: 12
subsystem: ui
tags: [pyside6, qtooltip, qlabel, stylesheet, import-dialog, gap-closure]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: Blocked status strip with clickable reasons (05-09) and the "model" reason (07-10) that shows in the same strip
provides:
  - STRIP_LINK_HINT public constant and a strip-wide tooltip (reason list plus click hint), always rich text
  - Strip objectName installStrip with every strip stylesheet scoped to one QLabel#installStrip rule
  - Amended Phase 5 UI contract (05-UI-SPEC.md :353 and :517)
affects: [phase-07 UAT test 8, import dialog status strip]

actuals:
  tokens: 6000
  tasks: 2
  commits: 2
plan_head_before: 474e945dfdc7666aebd7be9872777f9579d0f452
plan_head_after: 63323a648468a01ec900ec9624eae8e6452270a6

tech-stack:
  added: []
  patterns:
    - "Scope a widget stylesheet with an objectName selector so Qt does not apply it to that widget's QToolTip"
    - "Leading <p> forces rich text on a tooltip regardless of reason count; every interpolated string html.escape'd"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py
    - .planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md

key-decisions:
  - "No per-link tooltip through linkHovered: one strip-wide tooltip, as the 2026-10-24 user decision chose"
  - "Tooltip colour is verified manually only (UAT test 8); automated tests check the stylesheet text, not tooltip pixels"

patterns-established:
  - "Tests decode a tooltip with QTextDocument.setHtml(...).toPlainText() and check QtGui Qt.mightBeRichText"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "Blocked strip tooltip lists every reason and ends with STRIP_LINK_HINT, as rich text"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_tooltip_says_reasons_are_links"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_caps_three_lines_with_tooltip"
        status: pass
    human_judgment: false
  - id: D2
    description: "A single reason's &, ' and < render as themselves in the tooltip; every reason stays escaped (T-07-39)"
    requirement: FMT2-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_tooltip_single_reason_decodes_entities"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_escapes_markup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Strip stylesheet is exactly one QLabel#installStrip rule in the blocked and ready states; blocked, ready, no-op and updating looks unchanged"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_tooltip_style_scoped_to_strip"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_strip_look"
        status: pass
    human_judgment: false
  - id: D4
    description: "G-07-8 tooltip is drawn in the normal tooltip colours and not on the strip's amber, on the real display (owner UAT test 8)"
    verification: []
    human_judgment: true
    rationale: "Showing a QToolTip and sampling it is display and DPI dependent; the plan makes the colour manual-only. G-07-8 stays open until UAT test 8 passes in the live GUI."
  - id: D5
    description: "05-UI-SPEC.md :353 and :517 describe the click hint, rich text and normal colours; 07-11's G-07-7 amendment intact"
    verification:
      - kind: other
        ref: "grep -c 'amended 2026-10-24, UAT gap G-07-8' / 'amended 2026-10-24, G-07-8' / 'amended 2026-10-24, UAT gap G-07-7' each return 1"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-24
status: complete
---

# Phase 7 Plan 12: Strip Tooltip Click Hint (G-07-8) Summary

**The blocked status strip's tooltip now lists every reason plus the hint "Click a reason to jump to the control that fixes it...", always as rich text, and the strip's stylesheet is scoped to QLabel#installStrip so the tooltip no longer inherits the amber tint. G-07-8 is awaiting UAT test 8 on the live GUI and is not marked resolved.**

## Performance

- **Duration:** about 15 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `STRIP_LINK_HINT` (public constant) is appended to the blocked-strip tooltip as `<p><i>escaped hint</i></p>`; the reasons sit in a leading `<p>` joined by `<br>`, which makes the tooltip rich text for any reason count, so a single `Tom & Jerry's <part>` decodes instead of showing `&amp;`.
- The strip has objectName `installStrip`; `_set_strip` wraps the caller's bare declarations in `QLabel#installStrip { ... }` (empty style stays empty), so the rule cannot reach the tooltip label.
- 05-UI-SPEC.md :353 and :517 amended; 07-11's G-07-7 amendments untouched.

## Task Commits

1. **Task 1: Tracer, strip tooltip with click hint, forced rich text, scoped stylesheet** - `a8c47b6` (feat)
2. **Task 2: UI-SPEC amendment** - `63323a6` (docs)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified
- `kicad_lib_manager/widgets/import_dialog.py` - `STRIP_LINK_HINT`, `setObjectName("installStrip")`, scoped `_set_strip`, new tooltip in `_render_strip`
- `tests/test_import_dialog.py` - `test_strip_tooltip_says_reasons_are_links`, `test_strip_tooltip_single_reason_decodes_entities`, `test_strip_tooltip_style_scoped_to_strip`; hint assertion added to `test_strip_caps_three_lines_with_tooltip`
- `.planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md` - the two amended lines

## Decisions Made
- Followed the plan's design choices exactly (no `linkHovered` tooltip, constant in the module, `<p>` forcing rich text).
- Tooltip colour has no automated check by design; see G-07-8 status below.

## G-07-8 Status

**Awaiting UAT test 8.** The automated tests prove the tooltip text, the entity decoding and that the stylesheet is one `QLabel#installStrip` rule. They do not show a tooltip or sample its colour. G-07-8 must not be marked resolved until the owner confirms in the live GUI (hover a blocking reason, for example an emptied Value) that the tooltip is in normal tooltip colours, lists the reasons, ends with the hint, and that clicking the reason focuses the fixing control.

## Deviations from Plan

None - plan executed exactly as written.

Notes on process (not code deviations):
- Task 1 is `type="tracer"` and its `<verify>` carries a `<human-check>`. The plan explicitly defers that check to end-of-phase UAT test 8 (config `human_verify_mode: end-of-phase`, parallel worktree executor with no interactive user), so the tracer's automated verify was re-run and passed and expansion (Task 2, a docs-only edit independent of the tracer) continued rather than raising a mid-flight checkpoint.
- The plan's `./env/Scripts/python.exe` commands were run with the orchestrator checkout's interpreter from the worktree root, as the environment notes direct.
- The first attempt of the test-file edit script wrote with the default cp1252 encoding and truncated `tests/test_import_dialog.py` on a `UnicodeEncodeError`; the file was restored with `git checkout -- tests/test_import_dialog.py` (nothing had been committed from it) and the edit was re-applied with explicit UTF-8 and CRLF preserved. The committed diffs contain only the intended lines.

## Issues Encountered
None. The full-suite phase gate (about 6 minutes) was not run here; the orchestrator runs it after merge.

Verification run:
- 9 targeted tests (plan's first automated command): 9 passed
- `-k "strip or updating_reason"`: 12 passed
- `-k "add_model or placeholder or empty_library or conflict_rename"`: 26 passed
- `tests/test_import_dialog.py tests/test_help_dialog.py tests/test_preview_tree.py` minus the two real-Custom ids: 184 passed, 9 skipped (Custom submodule absent in the worktree), 2 deselected

## Known Stubs
None.

## Threat Flags
None. T-07-39 (escaped reasons in a rich-text tooltip) is mitigated: every reason and the hint are `html.escape`d, only fixed p, br and i tags are added, and `test_strip_tooltip_single_reason_decodes_entities` asserts the raw tooltip carries `&lt;part&gt;` and no raw `<part>`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for owner UAT test 8 on the real display (see the plan's human-check).

## Self-Check: PASSED

- Files exist: import_dialog.py, test_import_dialog.py, 05-UI-SPEC.md (modified, all present).
- Commits `a8c47b6` and `63323a6` are ancestors of HEAD.
- Task 2 grep acceptance counts all return 1.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-24*
