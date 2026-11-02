---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
audited: "2026-11-02"
baseline: "abstract 6-pillar standards (no UI-SPEC.md)"
method: "static code review; no screenshots or offscreen render"
overall_score: 17
---

# Phase 12 — UI Review

Audited at 60df383 by gsd-ui-auditor (code only, no render). Overall **17/24**; no pillar at 1, no blocker.

| Pillar | Score | Notes |
|--------|-------|-------|
| Copywriting | 2/4 | Raw file names still appear in some user-facing text (see Top Fixes 1) |
| Visuals | 3/4 | Finishing strip, Cancel button and KiCad-open box are clearly structured; not verified by render |
| Color | 3/4 | help_dialog.py and conflict_row.py use theme tokens; `PRIMARY_BUTTON_QSS` in theme.py still hardcodes `#0078D4`, white, `#E1E1E1`, `#595959` |
| Typography | 3/4 | Help px sizes moved to the pt scale; Help still hardcodes the "Segoe UI" and Consolas families |
| Spacing | 3/4 | Help uses `SP_*`; literal paddings remain in theme.py (`8px 16px`), conflict_row.py (`4px`), the import_dialog.py badge (`4px 8px`) |
| Experience Design | 3/4 | Finishing state, 10 s slow note, Cancel, Retry / Change anyway / Not now, blank-Destination warnings present; owner visual check still open |

## Top Fixes

1. **Raw names in user text.** The auditor lists:
   - help_dialog.py L48, 111, 115, 191–196, 205, 255, 372, 386
   - importer/form.py L83, the badge "new - creates .kicad_sym"
   - main_window.py L247–255 (tooltips and status tips), L436, 737, 891
   - library_scanner.py L133, 140–142
   - table_generator.py L376, 385–386, 459 (Result rows name the table file)

   The suggested fix is plain phrasing, for example "a new library creates only its symbol file", and dropping the file name from Result rows.

   *Orchestrator note:* the owner rule (memory `plain-language-ui`) keeps values the user really has to recognise, such as `${CUSTOM_3DMODEL_DIR}` and `KICAD_LIB_GITHUB`. These are path variables the owner sets in KiCad, so those mentions are not violations. The `.kicad_sym` / `.kicad_mod` / `sym-lib-table` / `fp-lib-table` mentions are candidates for the owner to judge.
2. **Wider guard test.** `tests/test_plain_names.py` checks only `kicad-cli` and `kicad_common.json`. Consider adding the file names the owner wants hidden, keeping the allowlist approach.
3. **Button stylesheet tokens.** `PRIMARY_BUTTON_QSS` in theme.py should use `ACCENT`, `SURFACE_BASE`, `MUTED` and a disabled-fill token, not literals.

## Warnings (non-blocking)

- Result-row copy names the table file ("Not added to <file>: …", "Updated: X in <file> now points at …"). The wording in 12-CONTEXT.md "Specific Ideas" omits the file name.
- Literal paddings and colours remain outside the token set (see Color and Spacing).
- There is no render evidence for the Finishing strip, the KiCad-open box or the Help pages. The owner's screenshot check (12-02, `human_judgment: true`) stays a pending UAT item.

Interaction captures: off. Screenshots: not captured.
