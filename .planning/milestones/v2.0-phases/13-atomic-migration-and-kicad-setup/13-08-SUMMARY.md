---
phase: 13-atomic-migration-and-kicad-setup
plan: 08
subsystem: migration
tags: [migration, atomic-libraries, draft, qsettings, app-data, sha256]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "importer/migration/plan.py (MigrationChoices, PartChoice, Resolution) and inventory.py (read_inventory, Inventory, InventoryPart, InventoryFootprint) from plan 13-05"
provides:
  - "importer/migration/draft.py: DRAFT_FORMAT, MAX_DRAFT_BYTES, LoadedDraft, fingerprints, save_draft, load_draft, changed_parts, clear_draft - the complete D-14 draft service"
  - "settings.migration_draft_file(repo_root): migration_draft/<hash>.json beside settings.ini, never in the repo, mirroring scan_cache_file"
affects: ["13-14..13-16 (the migration window plans wire these functions to Save/Open/Run and the 'changed since the draft' re-check UI)"]

actuals:
  tokens: 5900
  tasks: 2
  commits: 2
  plan_head_before: c1bdc2de6aba85e620725251b75efe58417cc86f
  plan_head_after: cea4b15aa9cefafc67f4db90d4e0125c9d50d8a9

tech-stack:
  added: []
  patterns:
    - "Draft fingerprint is one sha256 per part over its own block hash plus its linked footprint's hash plus that footprint's linked model file hashes (read in 1 MiB chunks); an unreadable model contributes the literal text 'unreadable' instead of raising, so a part's print always exists"
    - "load_draft validates every field with isinstance before building any dataclass, so a hostile or foreign draft never produces a partial MigrationChoices - mirrors scan_cache._read_payload's one-catch-tuple-of-(OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) pattern"
    - "migration_draft_file(repo_root) copies scan_cache_file's hash-named-file-beside-settings.ini shape with its own 'migration_draft' folder"

key-files:
  created:
    - kicad_lib_manager/importer/migration/draft.py
    - tests/test_migration_draft.py
  modified:
    - kicad_lib_manager/settings.py

key-decisions:
  - "The draft.restored INFO code named in the plan's artifact table is not emitted by draft.py: load_draft's success path returns a LoadedDraft (not an Issue), and the saved_at it carries is what a later window plan uses to construct that note itself when it shows the restored draft to the owner"
  - "fingerprints() looks up each part's linked footprint via InventoryFootprint.linked_by rather than re-deriving the link from the part's own Footprint field text, so the digest always agrees with what read_inventory already resolved"
  - "A part's choice is omitted from the saved JSON entirely when the owner never touched it (only footprint_target and derive are always written for a choice that exists); a part with only a fingerprint and no choice round-trips with no entry in MigrationChoices.parts"

patterns-established:
  - "importer/migration/draft.py imports strictly within its plan-13-03-registered ALLOWED set (models, fsutil, importer.plan, importer.migration.plan, importer.migration.inventory) - verified by tests/test_importer_layering.py before any test of its own behaviour ran"

requirements-completed: [MIG-02]

coverage:
  - id: D1
    description: "The owner's migration choices (library, MPNs, manufacturers, datasheets, descriptions, renames, footprint target, derive, leftovers and resolutions) survive closing the window and the app, saved and restored from app data"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_draft.py#test_draft_round_trip_keeps_every_choice"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_draft_round_trip_with_no_choices"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_draft_file_is_beside_settings"
        status: pass
    human_judgment: false
  - id: D2
    description: "A part whose symbol block, linked footprint or linked model changed on disk since the draft was saved is detected and flagged for re-checking, without discarding its saved choices"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_draft.py#test_changed_part_is_flagged"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_saved_keys_missing_now_are_flagged"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_unreadable_model_contributes_unreadable_text_not_a_crash"
        status: pass
    human_judgment: false
  - id: D3
    description: "A missing, oversized, malformed, wrong-format or other-repository draft means starting without one, with a plain INFO note, never an exception and never a partial MigrationChoices; a save or clear failure is one WARNING and never raises"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_draft.py#test_missing_draft_is_none"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_bad_drafts_start_clean"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_bad_draft_contents_start_clean"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_deeply_nested_draft_is_unreadable"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_oversized_draft_is_unreadable"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_other_repo_draft_is_ignored"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_save_failure_is_one_warning"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_clear_draft"
        status: pass
      - kind: unit
        ref: "tests/test_migration_draft.py#test_clear_draft_failure_is_one_warning"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 08: Migration draft save/restore and changed-since-draft detection Summary

**`importer/migration/draft.py` saves and restores every owner migration choice to a hash-named file beside `settings.ini` (never in the repo), and flags any part whose symbol, footprint or model changed on disk since the draft was saved, by comparing per-part sha256 fingerprints.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-11-11T16:32:00Z (approximate)
- **Completed:** 2026-11-11T17:17:00Z
- **Tasks:** 2 completed
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `importer/migration/draft.py`: `fingerprints(inventory)` computes one sha256 per part over its block hash, its linked footprint's hash and that footprint's linked model file hashes (1 MiB chunks; an unreadable model contributes the text "unreadable" instead of raising); `save_draft`/`load_draft` round-trip a `MigrationChoices` and its fingerprints through one JSON file, validating every field with `isinstance` before building any dataclass so a hostile or foreign draft never produces a partial result; `changed_parts` flags any saved key whose print differs from the current one or that no longer exists; `clear_draft` removes the file after a successful Run
- `settings.migration_draft_file(repo_root)`: `migration_draft/<16-hex>.json` beside `settings.ini`, mirroring `scan_cache_file`'s shape exactly
- `tests/test_migration_draft.py`: 27 tests covering the full round trip (every `PartChoice` field, leftovers, resolutions), changed-since-draft detection against a rich synthetic v1 `Custom/` (`write_v1_custom`), the draft's app-data location, and every hostile/foreign/failing-draft path (bad JSON, wrong format, wrong types, deep nesting, oversized files, another repository, a save target whose parent is a file, a locked clear)

## Task Commits

Each task was committed atomically:

1. **Task 1: Choices saved, restored, and changed parts flagged (D-14)** - `36bfacf` (feat)
2. **Task 2: Hostile, foreign and failing drafts never break the migration (D-14)** - `cea4b15` (test)

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/importer/migration/draft.py` - the complete draft service: `DRAFT_FORMAT`, `MAX_DRAFT_BYTES`, `LoadedDraft`, `fingerprints`, `save_draft`, `load_draft`, `changed_parts`, `clear_draft`
- `kicad_lib_manager/settings.py` - `migration_draft_file(repo_root)` added under a new "Migration draft" section divider
- `tests/test_migration_draft.py` - 27 behaviour and hostile-input tests

## Decisions Made

- The `draft.restored` INFO code the plan's artifact table names is not emitted inside `draft.py`: `load_draft`'s success path returns a typed `LoadedDraft`, not an `Issue`, and the `saved_at` it carries is what a later window plan (13-14..13-16) will use to build that note itself when it shows the restored draft to the owner. No behaviour test in this plan requires `draft.py` to emit it, and the plan's own "functions" list names only the five functions that exist.
- `fingerprints()` resolves each part's linked footprint via `InventoryFootprint.linked_by` (built by `read_inventory`) rather than re-parsing the part's own `Footprint` field text, so the fingerprint always agrees with what the inventory already resolved and never disagrees with it on an edge case like an official-KiCad-style link.
- A part's `choice` entry is omitted from the saved JSON when the owner never touched it; only a part that has an explicit `PartChoice` gets a `"choice"` object (always carrying `footprint_target` and `derive`, plus any non-`None` override field). A part with only a fingerprint and no choice round-trips with no entry in `MigrationChoices.parts` - confirmed by `test_draft_round_trip_with_no_choices`.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written, Rules 1-3.

### Scope note (not a Rule 1-4 deviation - documented for transparency)

Task 1 (`type="tracer"`) is explicitly production-quality, never a throwaway, so its action text already fully specified `load_draft`/`save_draft`/`clear_draft`'s complete hostile-input handling (the size cap, full `isinstance` validation before any dataclass is built, and the `RecursionError`-inclusive catch tuple) alongside the three round-trip/changed-part/settings-path behaviours it names in its own `<behavior>` block. As a result, when Task 2's hostile-input test list was written against that already-complete implementation, every one of its listed scenarios passed immediately - see "TDD Gate Compliance" below for the full accounting and the two genuinely new tests Task 2 added (an unreadable model file and malformed leftover/resolution entries) to avoid pure duplication.

---

**Total deviations:** 0 Rule 1-4 auto-fixes.
**Impact on plan:** None - every acceptance criterion and the plan's own verification command pass unchanged.

## TDD Gate Compliance

Task 2 carries `tdd="true"`. The RED/GREEN commit sequence exists (`test(13-08)` at `cea4b15`, `feat(13-08)` at `36bfacf`) but in the **reverse of the usual order**: `feat` landed first because it is Task 1's tracer commit, and Task 1's own action spec already fully implemented every hostile-input behaviour Task 2 later tests (see the Deviations scope note above). Re-running Task 2's full hostile-draft test list against that already-committed implementation found no failing test - a legitimate "feature already exists" outcome per the TDD error-handling guidance (not a mistaken test: the underlying implementation and the test list describe the exact same `draft.py` hardening, specified once in Task 1's action text and verified a second time in Task 2's dedicated test pass). No code change was needed, so there is no separate GREEN commit for Task 2; the `test(13-08)` commit adds genuinely new coverage not already present (fingerprints() on an unreadable model file, malformed leftover/resolution entries, an extra malformed parts entry) specifically so the commit is not a pure duplicate of Task 1's own test additions.

| Plan | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 13-08 | test(13-08) exists, confirms (not discovers) hardening | feat(13-08) predates it (Task 1 tracer) | none needed | Pass - see note above |

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `importer/migration/draft.py` and `settings.migration_draft_file` are ready for the migration window plans (13-14..13-16): `fingerprints`/`save_draft`/`load_draft`/`changed_parts`/`clear_draft` give the window everything it needs to save on every edit, restore on open, and re-check a part flagged as changed since the draft.
- The window plans will need to construct the `draft.restored` INFO note themselves from `LoadedDraft.saved_at` (see Decisions Made above) - this plan does not emit it.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/migration/draft.py
- FOUND: kicad_lib_manager/settings.py (migration_draft_file added)
- FOUND: tests/test_migration_draft.py
- FOUND: commit 36bfacf (Task 1)
- FOUND: commit cea4b15 (Task 2)
- `python -m pytest tests/test_migration_draft.py tests/test_importer_layering.py tests/test_settings_import.py -q` -> 46 passed
