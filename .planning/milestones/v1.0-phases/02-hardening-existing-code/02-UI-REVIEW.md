---
phase: 02-hardening-existing-code
type: ui-review
baseline: abstract 6-pillar standards (no UI-SPEC.md)
method: code-only (PySide6 desktop app, no URL to capture)
overall_score: 17
max_score: 24
reviewed: 2026-10-19
---

# Phase 02: UI Review

**Overall: 17/24.** This is a code-only audit. No screenshots were taken because the app is a PySide6 desktop GUI with no dev server. Interaction capture was off. The scores come from reading the code, not from rendering the window.

## Pillar Summary

| Pillar | Score | Key finding |
|---|---|---|
| 1. Copywriting | 3/4 | The help dialog doesn't cover the new "Collision" status or Ctrl+Shift+R. Raw exception text is shown on a scan error. |
| 2. Visuals | 3/4 | In the Symbols tree, the Status column sits past 710 px of fixed columns, so it is off-screen in the default window. Status cells have no tooltip. |
| 3. Color | 3/4 | The warning orange `#CC7700` on white is about 3.4:1, below WCAG AA (4.5:1). The literal appears in three files. |
| 4. Typography | 3/4 | Three sizes and one weight. Consistent. px and pt are mixed. |
| 5. Spacing | 3/4 | No spacing scale. Qt defaults plus arbitrary fixed pixel widths. |
| 6. Experience Design | 2/4 | `populate()` can leave `_updating` stuck at True. No empty state. Select All and Deselect All stay enabled during a scan. |

## Top 3 Priority Fixes

1. **`populate()` can leave the tree ignoring checkbox changes.** `_updating` is set True at `kicad_lib_manager/widgets/library_table.py:66` and cleared at `:158` with no try/finally. If anything raises in between, every later check change is ignored until restart, and nothing is logged. Fix: wrap the body in try/finally, as `_uncheck_peers` (`:216-231`) and the footprint sync (`:247-262`) already do.
2. **The Symbols Status column is off-screen at the default size.** `library_table.py:24-27` sets fixed widths of 280+130+300+60 px. The tree is about 530 px wide in the default 1100 px window (`main_window.py:62`), so you have to scroll sideways to see "Collision" or "Missing FP". Fix: narrow the fixed widths, or let the Status column resize to its contents, or move Status next to the name. Also put the row tooltip on the Status cell (column 3), not only on column 0.
3. **The in-app help is out of date.** `widgets/help_dialog.py:160` lists only "OK" or "Missing FP" as statuses. It doesn't mention "Collision", the mutual-exclusion rule, or that pre-selection happens only at startup. The shortcut table also leaves out Ctrl+Shift+R. Fix: add these to the help text.

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- WARNING: The help text is stale (Fix 3).
- WARNING: The message "No libraries selected." (`main_window.py:526`) doesn't say what to do next. Suggest "Select at least one library, then Generate Tables."
- WARNING: `main_window.py:497` logs `Scan error: {raw exception text}` with no plain-language explanation.
- INFO: The labels "Missing FP" and "Collision" (`library_table.py:103-105`) are terse. That's acceptable for a personal tool, but "Missing footprint" would read better.
- Strengths: Button labels are specific (Generate Tables, Deselect All, Rescan). Warnings are full sentences that name the library involved.

### Pillar 2: Visuals (3/4)
- WARNING: The Status column sits off-screen and has no tooltip (Fix 2).
- INFO: In the footprint tree the fixed columns total about 470 px, so its last column fits. Its tooltip is also only on column 0.
- INFO: Problem rows are coloured across every column (`library_table.py:115-117`). That is heavy; consider colouring only the status cell.
- Strengths: The hierarchy is clear: bold group headers, a single accent-coloured primary button, and a warning icon on problem rows. No button relies on an icon alone.

### Pillar 3: Color (3/4)
- WARNING: `#CC7700` on white is about 3.4:1. It colours the warning rows (`library_table.py:115`, `:148`) and the log (`log_panel.py:12`). A darker amber such as `#8A5200` gives about 6:1.
- WARNING: That colour value is repeated in three files with no shared constant.
- INFO: White text on the accent `#0078D4` is about 4.5:1, which passes. It is used only on the Generate button.
- INFO: Colour is never the only cue. An icon and status text back it up.

### Pillar 4: Typography (3/4)
- Sizes: 13px bold for tree headers, Consolas 9pt in the log, and 13/14px in the help CSS. Bold is the only weight.
- INFO: px and pt units are mixed.

### Pillar 5: Spacing (3/4)
- Layouts use Qt's default spacing throughout. Margins are zeroed only in `library_table.py:15` and `log_panel.py:22`.
- Fixed sizes: the column widths (`library_table.py:24-27`, `:44-46`), the log's `setMaximumHeight(180)`, and the backup dialog's `setMinimumWidth(500)`. Of these, only the column widths cause a real problem (Fix 2).

### Pillar 6: Experience Design (2/4)
- WARNING: `_updating` can get stuck (Fix 1).
- WARNING: There is no empty state. A repo with no libraries gives empty trees and only a count in the log.
- WARNING: `_set_scan_running` (`main_window.py:274-280`) disables Rescan, Set KiCad Path and Generate. It leaves Select All and Deselect All enabled. Changes made with them during a rescan are thrown away silently when the tree is rebuilt.
- WARNING (pre-existing): `_detect_kicad()` can open a modal folder dialog from `__init__` before the window is shown.
- INFO: Restore Backup overwrites the live tables without asking first. A safety copy is taken first (02-03), which limits the damage.
- Strengths: Every scan goes through a single guarded `_start_scan`, cleanup runs in `finally` blocks, pre-selection happens only at startup, and issue severity is routed without substring matching. Offscreen tests cover the busy-state guard.
- The 02-06 human check (pressing Ctrl+Shift+R repeatedly during the startup scan) passed in UAT on 2026-10-19 (`02-UAT.md`, test 1).

## Files Audited
- `kicad_lib_manager/main_window.py`
- `kicad_lib_manager/widgets/library_table.py`
- `kicad_lib_manager/widgets/log_panel.py`
- `kicad_lib_manager/widgets/backup_dialog.py`
- `kicad_lib_manager/widgets/help_dialog.py`
- 02-01 to 02-09 SUMMARY and PLAN files, and 02-CONTEXT.md
