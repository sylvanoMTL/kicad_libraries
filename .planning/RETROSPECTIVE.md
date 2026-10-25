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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | — | 7 | Headless core first, then UI; gap-closure plans for review and UAT findings |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 1993 (1966 pass, 21 env-dependent fail, 6 skip) | not measured | 0 runtime deps added (PySide6 only; pytest, pytest-qt dev) |

### Top Lessons (Verified Across Milestones)

1. (Needs a second milestone to cross-check.)
