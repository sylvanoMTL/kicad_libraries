---
phase: 02-hardening-existing-code
plan: 08
subsystem: infra
tags: [fsutil, atomic-write, backups, line-endings, python, pytest]

requires:
  - phase: 01-foundation
    provides: fsutil.atomic_write_bytes, backup_file, decode_source and the Issue/Severity model
provides:
  - backup_file keyword-only number= so two tables can share one backup number
  - best-effort copystat and writable backups (IN-01)
  - atomic_write_text returns fs.bad_encoding instead of raising (WR-04)
  - fs.not_a_file for folder targets and post-retry fs.read_only (WR-03)
  - fs.mixed_eol text built from the endings actually present (WR-05)
  - legacy generate_lib_tables.py CLI deleted with its docs (D-11)
affects: [02-01, 02-03, 02-04]

actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 17aa9b845d1ce5eee2f720b478d038b077daa927
plan_head_after: 22d432cbe6b29d586a0db5c7de9a326dd1058ce2

tech-stack:
  added: []
  patterns:
    - "Side-effecting fs helpers return an Issue instead of raising"
    - "Metadata steps after a complete write/copy are best-effort (try/except OSError)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/fsutil.py
    - tests/test_fsutil.py
    - CLAUDE.md
    - README.md
    - .planning/REQUIREMENTS.md
  deleted:
    - generate_lib_tables.py

key-decisions:
  - "The two fs.read_only Issues are written out in full rather than through a helper, so the plan's acceptance grep (at least 2 occurrences) holds"
  - "Mixed-EOL text for the common CRLF+LF case keeps the old wording (CRLF and LF); other combinations are built from the counts"
  - ".planning/codebase/ map documents still mention the deleted CLI and were left alone (generated documents, out of this plan's file list)"

patterns-established:
  - "backup_file(number=) skips the directory scan and uses the exclusive-create loop, so a taken name moves to the next number"

requirements-completed: [HARD-01, HARD-02]

coverage:
  - id: D1
    description: "backup_file number= starts at N and skips taken names; default max+1 numbering unchanged; best-effort copystat; backups writable"
    requirement: HARD-02
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_backup_file_number_starts_at_given_n, test_backup_file_number_skips_existing, test_backup_file_gaps_continue_after_highest, test_backup_file_copystat_failure_still_returns_backup, test_backup_file_of_read_only_source_is_writable"
        status: pass
    human_judgment: false
  - id: D2
    description: "atomic_write_text returns fs.bad_encoding for unencodable text; folder target is fs.not_a_file; target made read-only during retries is fs.read_only"
    requirement: HARD-02
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_atomic_write_text_unencodable_returns_bad_encoding, test_atomic_write_bytes_folder_target_is_not_a_file, test_atomic_write_bytes_read_only_after_retries_is_read_only"
        status: pass
    human_judgment: false
  - id: D3
    description: "fs.mixed_eol warning names only the line endings present"
    requirement: HARD-02
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_mixed_eol_text_names_present_endings"
        status: pass
    human_judgment: false
  - id: D4
    description: "generate_lib_tables.py deleted; CLAUDE.md and README.md point to the GUI; REQUIREMENTS.md Out of Scope row updated"
    requirement: HARD-01
    verification:
      - kind: other
        ref: "git ls-files -- generate_lib_tables.py prints nothing; grep -c generate_lib_tables CLAUDE.md README.md prints 0; full pytest run passes"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 08: fsutil review fixes and legacy CLI removal Summary

**fsutil now numbers backups on request, never calls a complete backup failed, reports unencodable text, folders and newly read-only targets truthfully, names the real line endings in the mixed-EOL warning, and the legacy CLI is gone so the GUI is the single table-generation path**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-19T08:28:00Z
- **Completed:** 2026-10-19T08:40:39Z
- **Tasks:** 2
- **Files modified:** 5 (plus 1 deleted)

## Accomplishments

- `backup_file(path, dir, *, number=None)`: with `number` the directory scan is skipped and the existing exclusive-create loop starts there; without it the max+1 numbering is unchanged. `copystat` and a writable chmod are best-effort, so a complete backup is never reported as `fs.backup_failed` and backups of read-only sources stay deletable (IN-01).
- `atomic_write_text` catches `UnicodeEncodeError` and returns `fs.bad_encoding` (WR-04).
- `atomic_write_bytes` returns `fs.not_a_file` at once for a folder target (no temp file, no retries) and re-checks writability after the retries so a target that turned read-only is `fs.read_only`, not "file is in use" (WR-03). The existing lock tests still return `fs.locked`.
- `decode_source` builds the `fs.mixed_eol` text from the CRLF/LF/CR counts; only-CR files say "bare CR line endings" (WR-05).
- `generate_lib_tables.py` removed; CLAUDE.md, README.md and the REQUIREMENTS.md Out of Scope row updated (D-11).

## TDD Gate Compliance

- **RED:** Commit `c352bbb` added the new tests and rewrote the gaps test without importing `table_generator`. Run before implementation: 10 failed, 43 passed. Each failure was on the planned assertion: `TypeError: unexpected keyword argument 'number'` (2), `UnicodeEncodeError` raised from `atomic_write_text`, `fs.locked` instead of `fs.not_a_file`, `fs.locked` instead of `fs.read_only`, copystat failure returned as `fs.backup_failed`, backup of a read-only source not writable, and three mixed-EOL texts that still said "(CRLF and LF)". Semantic assessment: every target test executed and failed for the intended reason (no import, collection or fixture errors). The `gsd_run check tdd-red-evidence` classifier was not run; the pytest output was inspected directly.
- **GREEN:** `3bcb371` implemented the fsutil changes; full suite 327 passed, 7 skipped (submodule-dependent tests skip in the worktree).
- **REFACTOR:** none needed.

## Task Commits

1. **Task 1 RED: failing fsutil tests** - `c352bbb` (test)
2. **Task 1 GREEN: fsutil review fixes** - `3bcb371` (feat)
3. **Task 2: delete legacy CLI and docs** - `22d432c` (chore)

**Plan metadata:** committed separately as `docs(02-08)` (SUMMARY only; STATE.md and ROADMAP.md are owned by the orchestrator).

## Files Created/Modified

- `kicad_lib_manager/fsutil.py` - number=, best-effort copystat and chmod, encode guard, folder and read-only handling, EOL text
- `tests/test_fsutil.py` - new tests for each behavior; gaps test no longer imports `table_generator`
- `CLAUDE.md` - legacy CLI bullet removed from Repository Structure
- `README.md` - tree, "Generate library tables" and "Adding a new open-source library" point to the GUI
- `.planning/REQUIREMENTS.md` - Out of Scope row records the deletion
- `generate_lib_tables.py` - deleted

## Decisions Made

- Inlined the two `fs.read_only` Issues instead of sharing a helper so the plan's acceptance grep for at least two occurrences holds.
- Left `.planning/codebase/*.md` (generated map documents) untouched; they still describe the CLI and will be refreshed by the next codebase mapping.

## Deviations from Plan

None - plan executed exactly as written. The plan's `./env/Scripts/python.exe` commands were run with the main checkout's venv interpreter by absolute path, as the dispatch instructions directed (the worktree has no `env/`), from the worktree root so the worktree's package was the one imported (verified via `kicad_lib_manager.__file__`).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None - no new network, auth or trust-boundary surface.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 02-01, 02-03 and 02-04 can rely on the extended fsutil contract (`number=`, `fs.bad_encoding`, `fs.not_a_file`, `fs.read_only`).
- No test imports `table_generator.backup_existing` any more, so plan 02-03 can delete it.

## Self-Check: PASSED

- `kicad_lib_manager/fsutil.py`, `tests/test_fsutil.py`, `README.md`: present; `generate_lib_tables.py`: absent.
- Commits `c352bbb`, `3bcb371`, `22d432c`: present in HEAD ancestry.
- Full suite: 327 passed, 7 skipped.

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
