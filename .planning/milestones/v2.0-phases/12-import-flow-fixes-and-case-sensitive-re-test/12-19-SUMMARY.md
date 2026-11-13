---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 19
subsystem: ui
tags: [user-guide, help, settings, persistence, G-12-23]
requires:
  - phase: 12-18
    provides: "one shared, parentless User Guide owned by the main window (show_guide)"
provides:
  - "settings.load_help_topic / save_help_topic under help/last_topic"
  - "HelpDialog saves the owner's own menu moves and reopens there (show_remembered)"
  - "MainWindow.show_guide restores the remembered place on a hidden guide when no topic is asked"
affects: [12-20]
tech-stack:
  added: []
  patterns:
    - "A quiet counter around programmatic selections so only the owner's moves are persisted"
key-files:
  created: []
  modified:
    - kicad_lib_manager/settings.py
    - kicad_lib_manager/widgets/help_dialog.py
    - kicad_lib_manager/main_window.py
    - CLAUDE.md
    - tests/test_help_dialog.py
    - tests/test_main_window.py
    - tests/test_import_dialog.py
key-decisions:
  - "Saved from _on_topic_selected on every owner move, not in a close event: Escape and a deleted parent fire no close event"
  - "A counter (self._quiet) rather than a flag, so the group-to-first-page step nested inside show_topic stays quiet"
  - "Fallbacks always go through show_topic (saved key, then its page part, then the first item)"
requirements-completed: [UI-01]
duration: 15 min
completed: 2026-11-04
status: complete
commits: 5
plan_head_before: e7bea4c6d149865b3c2924285a66982f48bb079e
plan_head_after: d0da3123b85d6d9a15453782a28cc18576dce9cc
actuals:
  tokens: 9000
  tasks: 3
  commits: 5
coverage:
  - id: D1
    description: "The guide saves each page or section the owner chooses and reopens there with the node selected and expanded, after Close, Escape, a deleted parent or a restart"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_help_dialog.py#test_owner_choice_is_remembered_after_close_escape_and_parent_deleted", status: pass}
      - {kind: unit, ref: "tests/test_help_dialog.py#test_saved_place_survives_a_restart", status: pass}
      - {kind: unit, ref: "tests/test_help_dialog.py#test_help_topic_settings_round_trip", status: pass}
    human_judgment: false
  - id: D2
    description: "An explicit topic (the import window's Importing Parts) wins and is never remembered; stale or odd saved values fall back"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_help_dialog.py#test_an_explicit_topic_wins_and_is_not_remembered", status: pass}
      - {kind: unit, ref: "tests/test_help_dialog.py#test_stale_saved_places_fall_back", status: pass}
      - {kind: integration, ref: "tests/test_import_dialog.py#test_import_help_keeps_opening_importing_parts_with_a_saved_place", status: pass}
    human_judgment: false
  - id: D3
    description: "Main-window Help and F1 reopen the owner's last place, only raise a visible guide, and open the saved place after a restart"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_main_window_help_reopens_the_owner_choice", status: pass}
      - {kind: integration, ref: "tests/test_main_window.py#test_main_window_help_on_a_visible_guide_only_raises", status: pass}
      - {kind: integration, ref: "tests/test_main_window.py#test_main_window_help_after_restart_opens_the_saved_place", status: pass}
    human_judgment: false
  - id: D4
    description: "The remembered place looks right on a real desktop at 100% and 200% display scale (selected row and heading visible)"
    verification: []
    human_judgment: true
    rationale: "Offscreen Qt has no real scaling or window manager; the plan's human-check covers it (UAT test 23)"
---

# Phase 12 Plan 19: The User Guide remembers the owner's place Summary

The User Guide saves each page or section the owner picks in its left menu under `help/last_topic` (through new `settings.py` helpers) and reopens there, also after Close, Escape, a deleted parent or an app restart, while explicit topics such as the import window's Importing Parts never read or change the saved place.

Start commit: e7bea4c6d149865b3c2924285a66982f48bb079e

## Performance

- **Duration:** about 15 min
- **Started:** 2026-11-04T17:34:24Z
- **Completed:** 2026-11-04T17:46Z
- **Tasks:** 3
- **Files modified:** 7 (none created)

## Accomplishments

- `load_help_topic() -> str | None` and `save_help_topic(key)` in a new "User Guide" section of `settings.py`; a non-str or empty stored value reads as None.
- `HelpDialog`: `_quiet` counter, public `show_remembered()` (saved key, then its page part, then the first menu item), constructor restores when no topic is given, `show_topic` is quiet, and `_on_topic_selected` saves each owner move after the group early return. No close or hide handler.
- `MainWindow.show_guide`: with no topic and a hidden existing guide, `show_remembered()` runs before showing; a visible guide is only raised.
- CLAUDE.md "User Guide" bullet under GUI Behavior.

## Task Commits

1. **Task 1 (tracer):** RED `f360c4b` test(12-19), GREEN `2fa504b` feat(12-19)
2. **Task 2:** `a6c515a` test(12-19) (tests only; they passed on Task 1's implementation, see below)
3. **Task 3:** RED `695d83a` test(12-19), GREEN `d0da312` feat(12-19)

**Plan metadata:** the docs commit that adds this SUMMARY.

## Files Created/Modified

- `kicad_lib_manager/settings.py` - help topic helpers.
- `kicad_lib_manager/widgets/help_dialog.py` - quiet selection, `show_remembered`, save on owner move.
- `kicad_lib_manager/main_window.py` - `show_guide` restores a hidden guide.
- `CLAUDE.md` - User Guide bullet.
- `tests/test_help_dialog.py` - autouse `_isolated_settings`, round-trip, remember, restart, explicit-topic and stale-key tests.
- `tests/test_main_window.py` - three main-window Help tests.
- `tests/test_import_dialog.py` - import Help keeps Importing Parts with a saved place.

## Decisions Made

- Save on every owner move rather than on close (Escape and a deleted parent fire no close event); the only `save_help_topic(` call is in `_on_topic_selected`.
- A counter instead of a boolean for quiet, so nested selections (group to its first page inside `show_topic`) stay quiet.

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- Task 1: RED `f360c4b` precedes GREEN `2fa504b`. RED evidence (semantic assessment, `gsd_run check tdd-red-evidence` not run since plain pytest output is not a supported report): `test_help_topic_settings_round_trip` failed with `AttributeError: module 'kicad_lib_manager.settings' has no attribute 'load_help_topic'`, the planned missing feature; the dependent tests need the same helpers.
- Task 2: no separate GREEN commit. The three new tests passed right after Task 1 (the plan allowed this). To prove they bite, a temporary mutation (save on every selection, quiet ignored) made six of them fail; it was reverted before committing.
- Task 3: RED `695d83a`: `test_main_window_help_reopens_the_owner_choice` failed (`'importing' == 'generating'`); the other two passed already by design (visible guide untouched, restart restores in the constructor). GREEN `d0da312`.

## Verification

- Task 1 verify: `pytest tests/test_help_dialog.py tests/test_settings_import.py` - 48 passed.
- Task 2 verify: `-k "help or topic or guide or saved or stale"` on help and import dialog tests - 64 passed.
- Plan-level: `pytest tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_settings_import.py tests/test_plain_names.py -m "not wurth"` - 438 passed in 191 s (3:11), run in the background.
- Acceptance greps: two settings helpers found, one `def show_remembered`, no `QSettings`/`get_settings` in help_dialog.py, one non-comment `save_help_topic(` call in help_dialog.py, one `show_remembered()` in main_window.py, the User Guide bullet in CLAUDE.md.
- The plan's human-check (F1 flow, restart, 200% scale) is not run here; it belongs to UAT.

## Issues Encountered

None. No known stubs. No new network, auth or file-access surface (threat flags: none); T-12-49 and T-12-50 mitigated as planned.

## Next Phase Readiness

Plan 12-20 can build on the guide as is; the saved place is independent of its work.

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*

## Self-Check: PASSED

- Modified files exist; commits f360c4b, 2fa504b, a6c515a, 695d83a and d0da312 are ancestors of HEAD.
