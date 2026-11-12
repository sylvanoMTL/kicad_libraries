# Phase 9 — UI Review

**Audited:** 2026-10-26
**Baseline:** Abstract 6-pillar standards plus the phase's own contract (09-CONTEXT.md D-01..D-06, D-12..D-16; 09-02 and 09-07 must_haves). No UI-SPEC.md exists for this phase.
**Screenshots:** not captured (PySide6 desktop app; no dev server or web target). Code-only audit of the Qt widget code. Visual judgement of layout and feel is therefore not verified and remains open (09-02 D6, 09-07 D6).
**Interaction captures:** off (`interaction_capture: false`)

Scope audited:
- `kicad_lib_manager/widgets/library_table.py` (symbol and footprint child rows, markers, tooltips, auto-expand, double-click)
- `kicad_lib_manager/widgets/atomic_check_dialog.py` (Check Atomic Parts dialog)
- `kicad_lib_manager/widgets/help_dialog.py` (Atomic parts section, Ctrl+Shift+A row)
- `kicad_lib_manager/main_window.py` (File menu action, scan-time disabling)
- User-facing strings in `kicad_lib_manager/atomic_check.py` and `kicad_lib_manager/atomic_fixes.py` (reasons, fix labels, issue texts)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Plain-language strings throughout; no `ki_` names in any reachable UI text. Some reasons still quote raw alias field names (`"MF"`). |
| 2. Visuals | 2/4 | The dialog marks failing symbols with amber text only (no warning icon), so the warning signal is colour-only where the tree and Help promise icon plus colour. |
| 3. Color | 3/4 | Theme tokens only (AMBER, ACCENT, no new hex literal in the audited widgets). Amber is applied to every violation row in the dialog, which weakens its meaning as a failure marker. |
| 4. Typography | 3/4 | Two monospace/bold usages, MONO tokens for the preview; weights limited to bold. No title or heading hierarchy on the dialog pages. |
| 5. Spacing | 3/4 | Theme spacing tokens (SP_SM, SP_MD) used on the preview page; the problems page button row has no explicit spacing or margins. |
| 6. Experience Design | 3/4 | Good state coverage (empty, no scan, scan running, KiCad running, stale file refusal, invalid input). Gaps: findings with no fix show a blank Fix column, the preview page has no Cancel, and "nothing would change" gives no reason. |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Dialog failing symbols and violations are amber text only, with no warning icon** — a colour-only signal fails the contract (09-CONTEXT D-03 "Failing: warning icon plus amber", and the Help text says the same). A user with colour vision deficiency or a monochrome display cannot tell a failing row from an ordinary one in the dialog. Fix: in `atomic_check_dialog.py` `_symbol_row` (line ~164) and the violation loop (line ~167), set `row.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxWarning))` for failing symbols and violations, matching `library_table.py`. Reserve amber for failing symbols and violations only; findings stay unstyled.

2. **Cleanup findings with no fix leave the Fix column blank, and the preview page cannot explain itself** — `_symbol_row` (lines 175-180) only writes the fix row when `finding.fix` is set and never writes "No one-click fix" for a finding, so a finding without a fix reads as unfinished. Likewise `_on_preview` (line 338) shows "Nothing would change." with a disabled Apply and no reason. Fix: write `NO_ONE_CLICK_FIX` into column 1 of findings without a fix; on the preview page, add a reason line when `preview.changes` is empty (for example "The ticked fixes leave every file as it is."); and add a Cancel/Close button next to Back (lines 319-329), since the preview page currently has only Back and Apply.

3. **Raw alias field names appear in reason texts** — `atomic_check.py:144` builds `f'{label} is stored as "{prop.name}", not as "{canonical}"'`, and `atomic_fixes.py` lines 215, 218, 228 and 265 build `there is no "{old}" field any more`, `it already has a "{new}" field`. These show KiCad field names such as `MF` and `MANUFACTURER` to the owner. The CONTEXT mock-up already uses `MF` in fix labels, so this is a low-severity wording issue, not a blocker. Fix: say "the Manufacturer value is kept under a second field name" and drop the quoted field name where the user does not act on it. Keep the names only in the fix label that renames them.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Passing:**
- Tree status words are plain and match the contract: "New", "Changed", "OK", "No symbols", "Could not check", "N of M fail", "Missing FP" (`library_table.py` lines ~146-157, ~235-245).
- Help text is plain language and names the shortcut and the marks (`help_dialog.py` lines 168-180).
- Dialog text is plain: "No atomic rule problems in the last scan.", "Preview & apply N fixes", "Apply N file changes", "Pick the value to keep", "Choose 3D model...", "Paste the datasheet link or file path" (`atomic_check_dialog.py` lines 24-27, 196-208).
- Owner rule (no `ki_` names): grep for `ki_` in `atomic_check.py`, `atomic_fixes.py`, `atomic_check_dialog.py`, `library_table.py`, `help_dialog.py`, and `main_window.py` returns no user-facing text. The only hits are code comments in `atomic_fixes.py:289` and the importer modules, which are not in this phase's UI.

**Findings:**
- `atomic_check.py:144`: "`<Label>` is stored as "MF", not as "Manufacturer"" exposes an alias field name the owner does not act on (see Top Fix 3).
- `atomic_fixes.py:215, 218, 228, 265`: skip notes quote field names ("there is no "MF" field any more"). Same wording issue.
- `atomic_check.py:444`: "Could not check the 3D model: it uses ${KICAD10_3DMODEL_DIR}" shows a KiCad path variable. Acceptable because it is a variable the owner sets in KiCad, but a plain phrase ("KiCad's 3D model folder is not set up") would read better. Minor.
- `atomic_check_dialog.py:86`: `_empty_label` text is accurate, but the summary label has no wording for the "scan found nothing to check" case (summary is hidden, so the user only sees the empty message). Acceptable.
- The Preview & apply button uses a bare `&` in its label. Qt treats `&` as a mnemonic marker; `& ` followed by a space is normally shown literally, but the rendering should be confirmed on Windows. Use `&&` only if the ampersand disappears.

### Pillar 2: Visuals (2/4)

**Findings:**
- `atomic_check_dialog.py:164` and `:167`: a failing symbol and each violation get `setForeground` amber only. No `setIcon` is applied, so there is no non-colour marker. The library tree does add `warn_icon` (`library_table.py`, `_make_symbol_row` lines ~250-252), and the Help page tells the user "amber with a warning icon". The dialog breaks that promise. This is the main visual gap.
- `atomic_check_dialog.py:76-90`: the dialog has no page heading. The summary line ("N problems in N symbols, from the last scan") is the only header on page 0, and it is plain body text, so the page has no visual entry point above the tree.
- Focal point on page 0: the primary "Preview & apply N fixes" button is the only styled control (PRIMARY_BUTTON_QSS, line 104). This is a sound focal point.
- Library tree: failing symbol child rows, New/Changed rows and the library "N of M fail" status are clearly differentiated by icon, colour and text. Changed and New rows carry the word in the Status column, so they are not colour-only (`library_table.py` `_make_symbol_row` and `_make_footprint_row`). Passing.

### Pillar 3: Color (3/4)

**Passing:**
- No new hex literal in the audited widgets. Colour comes from `theme.AMBER` and `theme.ACCENT` (`library_table.py:14`, `atomic_check_dialog.py:20`, `help_dialog.py` uses the same tokens). The only literal found is `AMBER_TINT` in theme, not used here.
- ACCENT is applied only to New and Changed child rows, not to the whole library, matching D-03.
- Contrast: AMBER `#8A5200` on white is well above 4.5:1, and ACCENT `#0078D4` on white is about 4.6:1; both pass for text.

**Findings:**
- `atomic_check_dialog.py:164` and `:167`: amber is applied to each failing symbol row and each violation row. A symbol with three violations shows four amber lines. The accent is used on too many elements in the dialog, so it no longer separates "failing" from "listed". Keep amber for the failing symbol row and the violation text only, and drop it from findings (already plain) and from notes.
- `atomic_check_dialog.py:309`: the running warning is bold amber text in a stylesheet string. It is the correct colour for a warning, but it has no icon either (see Pillar 2).
- Distribution (60/30/10): the tree is mostly neutral with amber and accent as small accents, which is acceptable. The dialog is the exception (see above).

### Pillar 4: Typography (3/4)

**Passing:**
- Preview text uses MONO_FAMILY and MONO_PT (`atomic_check_dialog.py:300-303`), which suits before/after text.
- Bold is used only for the amber warnings (`help_dialog.py`) and the running label (line 309). No more than two weights are in use across the audited files.
- Help headings use `HEADING_PT` from theme (`library_table.py:14`).

**Findings:**
- The dialog pages use the default font size for all text, including the summary and the running warning. There is no title or heading level (see Pillar 2), so the hierarchy between summary, rows and buttons is flat.
- The problems tree sets only `setColumnWidth(0, 520)` and never sets a font for the rows, so Violation text, fix rows and symbol rows share one size. Indentation is the only level cue.

### Pillar 5: Spacing (3/4)

**Passing:**
- Spacing tokens are used on the preview page: `layout.setSpacing(SP_SM)` (line 294) and `buttons.setContentsMargins(0, SP_MD, 0, 0)` (line 320).
- The dialog has a fixed size of 900 by 620 (line 55), which gives the tree room.

**Findings:**
- The problems page button row (lines 92-107) has no spacing or margin set, so the buttons sit on the layout default while the preview page uses theme tokens. Inconsistent with the rest of the dialog.
- `atomic_check_dialog.py:242-243`: the reason row for invalid input is a plain tree row. Its text is long (for example "Datasheet is not a link or file path") and will be clipped in column 1 (which has no width set; only column 0 is set to 520). Set column 1 width or let the tree resize to contents.

### Pillar 6: Experience Design (3/4)

**Passing (state coverage):**
- Empty state: "No atomic rule problems in the last scan." with the preview button disabled (lines 137-143, 284-287).
- No scan yet: log message "No scan result yet; rescan first." (`main_window.py` `_open_atomic_check`).
- Scan running: the action is disabled through `_set_scan_running` (`main_window.py:332`), and a request during a scan logs "A scan is already running; request ignored."
- KiCad running: amber warning shown on the preview page only while KiCad runs (lines 339-347).
- Stale file: refusal shown in the dialog and logged (`_on_apply`, lines 362-373); nothing is written.
- Invalid typed input: plain reason shown beside the input (`_on_input`, lines 240-245).
- Only Apply writes: the preview page's Apply is the only caller of `apply_preview` (line 366).
- Double-click on a marked symbol opens the dialog with that row current (`_scroll_to_focus`).

**Findings:**
- Findings with no fix show a blank Fix column and no explanation (`atomic_check_dialog.py:175-180`). Users cannot tell "nothing to do" from "not yet loaded".
- The preview page has no Cancel. The only exits are Back (returns to page 0) and the window close button, which is not discoverable for a modal dialog. Add Close or Cancel next to Back.
- Empty preview: "Nothing would change." (line 338) with a disabled Apply and no reason. Add the reason (see Top Fix 2).
- After a refused Apply the Apply button is disabled and stays so until Back (line 372). The user has no in-place retry; this is by design (the preview must be rebuilt), but the dialog should say so ("Go back and preview again"). The current issue text ("preview again") is in the refusal message, which mitigates this.
- Symbol rows in the tree (`library_table.py`) and the dialog rows are not keyboard-navigable to a fix in one step. Focus follows `setCurrentItem`, which is adequate.
- No registry or third-party block is involved in this phase (no `components.json`), so no registry safety section is needed.

---

## Files Audited

- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/atomic_check_dialog.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/library_table.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/help_dialog.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/theme.py (token lookup only)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/main_window.py (action wiring lines 142-157, 332, 777-800)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/atomic_check.py (user-facing reason strings)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/atomic_fixes.py (user-facing skip, fix-label and issue strings)
- Phase inputs: 09-02-SUMMARY.md, 09-07-SUMMARY.md, 09-02-PLAN.md, 09-07-PLAN.md, 09-CONTEXT.md

Not audited: rendered layout, real column widths, icon appearance, and keyboard flow in a running window. The visual findings are code-derived and need a look in the real app (09-02 D6, 09-07 D6).
