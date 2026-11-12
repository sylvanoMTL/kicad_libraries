# Phase 05 - UI Review

**Audited:** 2026-10-22
**Baseline:** 05-UI-SPEC.md (approved design contract, PySide6 Qt Widgets)
**Screenshots:** not captured (desktop app, no dev server; code-only audit)
**Interaction captures:** off (workflow.ui_interaction_capture is false)
**Human evidence cited:** 05-UAT.md, all 4 tests pass (end-to-end import, KiCad-running notice and KiCad load, visual checks at 100% and 150% scaling, Help re-check)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Core labels and placeholder/Generate hint copy match the contract; full string-by-string copy table not exhaustively diffed |
| 2. Visuals | 3/4 | Page structure, splitter, badge and glyph cues follow the spec; ↺ icon-only buttons tooltip coverage not verified |
| 3. Color | 3/4 | `theme.py` is the single source for AMBER/ERROR/etc., but `help_dialog.py` still hard-codes `#F9A825`, `#0078D4`, `#EEF1F5` and `#FFFFFF` appears in `conflict_row.py` |
| 4. Typography | 2/4 | `help_dialog.py` CSS uses `14px` and `13px` sizes, outside the 9/10/12pt contract (px, not pt, and a fourth size) |
| 5. Spacing | 3/4 | Dialog margins (16) and spacing (8/4) on the scale; help-dialog CSS uses off-scale values (2px, 3px, 5px, 10px, 14px) |
| 6. Experience Design | 3/4 | Strong state coverage and modal guards; six review warnings (WR-01..WR-06) still disposition "open", one blocks the GUI thread up to 60 s |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Blocking GUI thread and cross-thread plan read during install** (WR-04, WR-05) — the UI can freeze up to 60 s during kicad-cli calls and the install worker reads `self._plan` from its thread — user sees a hung window or a race on the plan — move the kicad-cli wait to the worker or a signal-driven flow, and pass an immutable plan snapshot to the worker.
2. **Help dialog outside the design tokens** — `help_dialog.py` uses `#F9A825`, `#0078D4`, `#EEF1F5`, `#F5F7FA`, `#FFF8E1` and `14px`/`13px` font sizes — contract says the help span uses `AMBER` and only 9/10/12pt — build the CSS string from `theme.py` constants (`AMBER`, `AMBER_TINT`, `ACCENT`, `SURFACE`, `SURFACE_HEADER`) and convert sizes to the Body/Heading pt values.
3. **Post-install result text and table location** (WR-01, WR-02) — `add_library_entries` reports "already listed" when the managed entry points at a different library, and an empty Destination sends the table write to the process working directory — the user reads a misleading result or tables land in the wrong folder — report the nickname clash as a WARNING and refuse the table write when Destination is empty. (UAT test 2, the KiCad-running notice and KiCad loading the part, passed on 2026-10-22.)

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Menu and toolbar use the contract strings: `&Import Part...` with `Ctrl+I` (`main_window.py:116-117`), toolbar `Import Part...` with tooltip `Import a vendor package (Ctrl+I)` (`main_window.py:190-191`).
- Drop refusal and busy-state strings match the UI-SPEC drag-and-drop table (`main_window.py:692-737`).
- Install-blocking placeholder reason and "Generate" hint are present and confirmed by UAT steps 2 and 7.
- Not verified: the full Copywriting Contract was not diffed string-by-string; the score is capped at 3 for that reason.

### Pillar 2: Visuals (3/4)
- Dialog uses the specified four-page `QStackedWidget`, `QSplitter` with `setChildrenCollapsible(False)` and `QScrollArea` (`widgets/import_dialog.py`).
- Status is never color-only: `+ ~ =` glyphs, "existing"/"new" badge text, "Needs a choice" text (`conflict_row.py`, `import_dialog.py:1140-1150`).
- The `↺` restore buttons are icon-only (24x24, `QToolButton`); no evidence in code that each carries a tooltip or accessible name. Requires check.

### Pillar 3: Color (3/4)
- `theme.py` defines the contract palette and `PRIMARY_BUTTON_QSS` with the `:disabled` rule; `main_window.py:226` applies it to Generate.
- `log_panel.py:13` maps `warning` to `AMBER`; `library_table.py:138,174` uses `AMBER`. No `#CC7700` literal remains.
- `help_dialog.py:18-55` hard-codes `#0057A0`, `#0078D4`, `#EEF1F5`, `#F5F7FA`, `#FFF8E1`, `#F9A825`. The contract (Shared theme module, Color section) requires the help span to use `AMBER` and all colors to come from `theme.py`. The `#F9A825` border is a new, unlisted amber.
- `conflict_row.py:35-37` uses `#FFFFFF` literals for button fill and checked text rather than a theme constant.
- Accent reserved-for list is respected in the import dialog (checked Rename/Skip, Install, progress chunk).

### Pillar 4: Typography (2/4)
- `help_dialog.py:12` sets `body { font-size: 14px }` and `help_dialog.py:31,37` sets `13px` for code and pre blocks. The contract allows exactly 9, 10 and 12pt, with Mono at 9pt, and requires pt-only new code. These px sizes are a fourth and fifth size and break the scale.
- `import_dialog.py:363,621`, `import_result.py:93,127` and `content_view.py:60` use `HEADING_PT`, `DISPLAY_PT` and `MONO_PT` correctly.
- Weights: only 400 and 700 are used (`conflict_row.py:38`, `import_dialog.py:1144,1148`, `theme.py:29`). This part conforms.

### Pillar 5: Spacing (3/4)
- Dialog margins `setContentsMargins(16, 16, 16, 16)` and spacing 8 match the contract. Minimum control heights of 28 are applied (4 occurrences).
- Off-scale values are limited to the help stylesheet (`padding: 2px 5px`, `padding: 10px 14px`, `padding: 8px 12px`, `border-left: 3px`, `border-radius: 3px`) and `conflict_row.py` `padding: 4px {_BUTTON_PAD}px`. Contract exceptions cover borders (1px, 2px, 3px accent bars), but padding values such as 5px, 10px and 14px fall outside the 4-multiple rule.
- `setContentsMargins(SP_XL, ...)` on the start step matches the reserved 32px inset.

### Pillar 6: Experience Design (3/4)
- Strengths: window-modal import dialog (D-19), Install disabled with a visible reason, `Ctrl+Return` shortcut gated on enablement, drag-and-drop refusals with status and log messages, KiCad-running check on a worker with a logged WARNING, rescan and post-install selection, and the add-only table write.
- Open review warnings from 05-REVIEW-DISPOSITION.md, all still "open":
  - WR-01: `add_library_entries` reports "already listed" when the managed entry points at a different library — misleading result text.
  - WR-02: post-install table write goes to the process working directory when Destination is empty — wrong-location write risk.
  - WR-03: a one-off conflict build can overlap Install, although the code says it cannot — violates the contract's busy-state guard.
  - WR-04: install worker reads `self._plan` from the worker thread; `open_path` has no install guard.
  - WR-05: GUI thread blocks on worker `wait()` for up to 60 s of kicad-cli time — frozen window.
  - WR-06: `kicad_common.json` write can use stale content after the confirm dialog, and the KiCad-running check does not gate the write.
- UAT test 2 (KiCad-running notice, KiCad loads the part with an empty Datasheet) passed, so the amber notice and the external load are human-verified.

---

## Files Audited
- `kicad_lib_manager/widgets/theme.py`
- `kicad_lib_manager/widgets/import_dialog.py`
- `kicad_lib_manager/widgets/import_result.py`
- `kicad_lib_manager/widgets/conflict_row.py`
- `kicad_lib_manager/widgets/preview_tree.py`
- `kicad_lib_manager/widgets/content_view.py`
- `kicad_lib_manager/widgets/library_table.py`
- `kicad_lib_manager/widgets/log_panel.py`
- `kicad_lib_manager/widgets/help_dialog.py`
- `kicad_lib_manager/main_window.py`
- `.planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md`, `05-UAT.md`, `05-REVIEW-DISPOSITION.md`, `05-VERIFICATION.md`
- Plans and summaries 05-01 through 05-11 were located but only the UI-spec and disposition-level facts were cross-checked in this pass.
