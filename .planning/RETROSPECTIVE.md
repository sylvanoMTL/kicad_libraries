# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Part Importer

**Shipped:** 2026-10-25
**Phases:** 7 | **Plans:** 70 | **Sessions:** not tracked

### What Was Built
- A lossless span-splicing S-expression layer with atomic writes and backups. Every repo KiCad file round-trips byte-identically.
- The existing Library Manager hardened against data loss: managed-only lib-table splicing, collision handling, and a confirmed `kicad_common.json` sync.
- Safe intake of Ultra Librarian, SnapEDA, SamacSys/CSE and loose-file packages, with convention-following library name suggestions.
- A transactional install core (kicad-cli format matching, conflict resolution, rollback, verification, no-op re-import) proven on the real UL sample.
- The Import Part dialog: an editable preview that is exactly what gets installed, per-item conflicts, drag and drop, a separate 3D model attach, and add-only table refresh.
- A confirmed, path-limited commit step in `Custom` plus the parent gitlink, from an allow-listed git runner that never pushes.

### What Worked
- Building bottom-up with a headless core: phases 1–4 have no GUI, so correctness was proven in pytest before the dialog existed. Phases 5–7 only wrapped it.
- One shared plan for preview and install (PREV-07) removed a whole class of "preview said X, install did Y" bugs.
- Real vendor downloads as fixtures surfaced layout surprises early: a root-level STEP with an unrelated name, a timestamp-named symbol file, SnapEDA's separate model download.
- Diagnose-only debug sessions followed by small gap-closure plans worked well for UAT findings. Phase 7's four UAT issues were closed and re-tested in one day.

### What Was Inefficient
- Gap closure took 13 of 70 plans (03-08..03-10, 04-11..04-13, 07-07..07-13). Most came from security review (hostile text, exceptions during install) or UAT, not from the original plans.
- Tests coupled to the live environment. The `custom_copy` fixture copies the owner's real `Custom/`, and the kicad-cli tests hard-code KiCad 9 output. Installing the UL part for real and upgrading to KiCad 10 left 21 tests red at close.
- Bookkeeping drifted. Four debug sessions stayed "diagnosed" after their fixes shipped, and Phase 03 UAT stayed "testing" after its decisions were executed. All were only reconciled at milestone close.
- Phase 1–6 verification reports went stale as later phases touched shared files, and nothing re-ran them.

### Patterns Established
- Side-effecting services return `Issue` objects with a `Severity`, never substring-classified strings.
- Untrusted input is bounded before and while parsing (byte caps, node ceilings, linear scans), and an over-cap file is a WARNING, not a whole-package refusal.
- Every write to KiCad files or the repo follows a preview and an explicit click. KiCad path variables and git commits each get their own confirmation.
- Vendor differences live in scored adapters behind one intake contract.

### Key Lessons
1. Test fixtures must not depend on the owner's live libraries or installed tool versions. Build synthetic `Custom/` trees and pin or parametrise the kicad-cli version.
2. Close a debug session or UAT file in the same commit as the plan that fixes it, so the milestone audit does not have to reconcile them later.
3. Budget for gap closure. Security review and real-hardware UAT found issues on about one plan in five.
4. Use real vendor samples from the start. Each format phase was blocked until real downloads existed, and they changed the design (G-07-2).

### Cost Observations
- Model mix: not tracked (adaptive profile)
- Sessions: not tracked
- Notable: 70 plans and 619 commits in 7 days. The headless core let most plans verify in pytest without manual GUI checks.

---

## Milestone: v2.0 — Atomic Libraries

**Shipped:** 2026-11-13
**Phases:** 6 | **Plans:** 111 (plus quick 261027-gg7) | **Sessions:** not tracked

### What Was Built
- Test isolation: code-built synthetic `Custom/` fixtures, a session guard that fails any run touching the live `Custom/`, and one kicad-cli 10 gate. Bare `pytest` is green with no `Custom/` at all.
- One Qt-free atomic rule check and one canonical manufacturer table, consumed by the scan (tree marks, New/Changed detection against the `Custom` HEAD), the Check Atomic Parts fix dialog, the importer's install gate, the commit gate and the migration.
- The importer on the `Atomic_<stem>` scheme: sibling-vote and category-map suggestion, the shared `Atomic_Footprints` or an official KiCad footprint, generated keywords, footprint descriptions and tags, Install blocked with clickable reasons.
- A commit gate that fails closed, and a commit panel that reports what git really did, with PowerShell quoting for the manual command.
- The remaining v1.0 review findings closed, the KiCad-open question, theme tokens, the case-sensitive re-test, and a shared User Guide window that reopens on the chosen section.
- One previewed, transactional migration with a `pre-atomic` tag, rollback and an old -> new map, table descriptions, Pin Atomic Libraries in KiCad, and the D-26 wrong-checkout guard. The live run moved 21 parts into 10 libraries.

### What Worked
- Building the rule once as a Qt-free module (Phase 9) and reusing it unchanged in four consumers. The importer, commit gate and migration each took the check as given; no consumer grew its own variant.
- Synthetic fixtures before features (Phase 8). Every later phase's tests ran whatever the owner's `Custom/` held, and the suite never went red for environment reasons again.
- Seams planned ahead of the change: `footprint_library_for` and the `name_verdict` module let plans 10-10 and 10-12 switch the name rule and the shared footprint library without editing the test files that had already moved.
- Diagnose-only debug sessions followed by small gap plans, again. The live migration UAT on 2026-11-12 found seven problems in one afternoon; six gap plans (13-23..13-28) closed them and the re-test passed 5/5 the next day.
- Owner decisions written down as they were made (D-26 run from the checkout KiCad reads, the skip unit, the fail-closed gate, Pin wording) and turned into tests and guide text in the same plan.

### What Was Inefficient
- Gap closure took 22 of 111 plans (10-29, 10-30, 12-09..12-21, 13-22..13-28), about one in five, the same ratio as v1.0. Most came from UAT, not from review.
- Phase 10 ran to 30 plans. About a third were mechanical moves of existing test files onto the `Atomic_` names, which could have been one scripted sweep.
- The suite grew from 1993 to 9693 tests and a full run now takes about 30 minutes. The real-git commit tests (7-15 s each) and the Würth corpus dominate; nothing was parallelised.
- Bookkeeping drifted again: eight debug sessions stayed "diagnosed" after their fixes shipped and five verification reports went stale after their gap plans. Both were reconciled only at milestone close, exactly as in v1.0.
- A Python 3.11 NameError (unresolved annotation names in `migration_dialog.py`) hid behind 3.14's deferred annotations until the live UAT ran from the main checkout's venv. There is still no lint step.
- The first live migration attempt ran from the dev worktree, which KiCad does not read. It cost a restart and produced D-26.

### Patterns Established
- One rule, many consumers: a Qt-free check module with injected context (`AtomicContext`, `repo_context(planned_footprints, planned_models)`) so every writer judges the same bytes the same way.
- Gates fail closed. Anything the app cannot prove (an unreadable library, an unlistable folder, a guessed library) blocks with a plain-language strip line until the owner decides.
- Plain-language UI text with no KiCad jargon or raw field names, pinned by tests on the literal strings.
- The app checks which checkout it runs from against KiCad's `KICAD_LIB_GITHUB` before any write KiCad depends on (D-26): warn for tables and installs, refuse for the migration and the chooser.
- Every write is a span-exact edit through `apply_preview` with a per-file backup, an atomic replace and a SHA-256 stale refusal, confined to `Custom/`.

### Key Lessons
1. Run the live UAT from the environment the tool will really run in, with the interpreter the owner uses. Two of the seven migration problems (the 3.11 NameError and the worktree run) were environment, not logic.
2. Close a debug session or a verification report in the same commit as the plan that fixes it. Second milestone in a row that this was left to the close.
3. Budget one plan in five for gap closure and keep phases under about 20 plans; split mechanical sweeps (test-file moves) into one scripted plan.
4. Watch suite duration as a metric from the first phase. A 30-minute suite changes how often the full gate runs.
5. An undefined-name check (lint or an import-on-oldest-supported-Python test) belongs in the harness before code is written for more than one interpreter.

### Cost Observations
- Model mix: not tracked (adaptive profile)
- Sessions: not tracked
- Notable: 111 plans and 918 commits in 20 days (v1.0: 70 plans and 619 commits in 7 days). Phases 10-13 each ran two to four executor waves in worktrees; the full-suite gate at phase end cost about 30 minutes per wave.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | — | 7 | Headless core first, then UI; gap-closure plans for review and UAT findings |
| v2.0 | — | 6 | Synthetic fixtures and a KiCad 10 gate first; one shared Qt-free rule check reused by four consumers; a live migration UAT from the main checkout drove the final gap plans |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 1993 (1966 pass, 21 env-dependent fail, 6 skip) | not measured | 0 runtime deps added (PySide6 only; pytest, pytest-qt dev) |
| v2.0 | 9693 (9689 pass, 0 fail, 4 documented skip; about 30 min) | not measured | 0 runtime deps added |

### Top Lessons (Verified Across Milestones)

1. Close debug sessions and verification reports in the fixing plan's commit. Both milestones left them (4 and then 8 sessions, 6 and then 5 stale reports) to be reconciled at the close.
2. Gap closure costs about one plan in five (13/70 in v1.0, 22/111 in v2.0). Budget it; most of it comes from real-hardware UAT, which no amount of planning replaces.
3. Run from the real environment. v1.0's Generate from the worktree repointed KiCad at the wrong folder (quick 261022-gnn); v2.0's migration UAT first ran from the worktree too (D-26). Guards now exist, but the lesson is to test from where the owner runs.
4. Build the headless core first and wrap it last. Both milestones proved their logic in pytest before any dialog existed, and the UI phases found copy and layout issues, not logic bugs.
