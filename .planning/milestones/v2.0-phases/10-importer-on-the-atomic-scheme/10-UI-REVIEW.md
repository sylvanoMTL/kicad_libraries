# Phase 10 — UI Review

**Audited:** 2026-10-27
**Baseline:** Abstract 6-pillar standards, plus the owner's plain-language rule (no raw field names such as `ki_keywords` / `ki_fp_filters`, no internal issue codes such as `install.atomic.*`) and the phase's own decisions in 10-CONTEXT.md (D-06, D-22, D-25, D-30). No UI-SPEC.md exists for this phase.
**Screenshots:** not captured (PySide6 desktop app; no dev server or web target). Code-only audit of the Qt widget code and the planner/form/preview strings. Layout, real column widths, icon appearance and clipping are not verified visually.
**Interaction captures:** off (`interaction_capture: false`)
**Known context, not re-scored:** the help dialog's hard-coded colours and px sizes outside theme.py (pre-existing item UI-01, deferred to Phase 12); the 24 px glyph Regenerate button (10-23 choice, flagged for owner judgement).

Scope audited:
- `kicad_lib_manager/widgets/import_dialog.py` (library picker and tooltip, destination radios and official picker, Fields section with read-only Value, generated text rows, reason strip, model row, install banner)
- `kicad_lib_manager/importer/preview.py` (Path rewrites, Field changes, Not used rows)
- `kicad_lib_manager/importer/form.py` (reason sentences, `atomic_reason`, `blocking_reasons`, labels)
- `kicad_lib_manager/widgets/preview_tree.py` (tone colours, fonts)
- `kicad_lib_manager/widgets/help_dialog.py` (Importing Parts page)
- `kicad_lib_manager/importer/planner.py` (issue texts and alias rename rows)
- `kicad_lib_manager/widgets/theme.py` (tokens)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | Reachable preview row reads "Rename MF", a raw KiCad alias field name, which breaks the owner's explicit rule. "extends parent" and "duplicate Manufacturer/MPN alias" are KiCad or internal wording. The Help page misdescribes the reason strip. |
| 2. Visuals | 2/4 | The dialog's only primary action (Install Part) has no primary styling. Read-only Value and Footprint look like editable fields. Section headings are bold body text with no size step. |
| 3. Color | 3/4 | No literal hex in import_dialog.py; all colour comes from theme tokens. Amber strip, frames and labels are used with consistent meaning. Install Part, the dialog's main action, carries no accent. |
| 4. Typography | 3/4 | Mono is used for paths and field values; bold is limited to a few labels. `HEADING_PT` exists in theme but section headings do not use it, so the hierarchy is flat. |
| 5. Spacing | 3/4 | Values stay on the 4/8/16 scale, but about 50 margin and spacing calls are literals instead of `SP_*` tokens. The reason strip is capped at three lines with no scroll, so reasons can be cut off. |
| 6. Experience Design | 3/4 | Good state coverage: reading, unavailable KiCad, refusal, live clearing of reasons, updating state, install-failure banner, Ctrl+Return. Gaps: the reason strip clips extra reasons, the library suggestion reason is reachable only by hover, and the read-only Value gives no visual cue. |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Raw KiCad alias field name shown to the owner ("Rename MF")** — the owner's rule forbids raw field names in user-facing text, and this row appears whenever a vendor package uses an alias such as `MF` for Manufacturer. The owner sees a KiCad field name they cannot act on. Fix: in `importer/preview.py` `_field_changes_section`, map known alias names through `_FIELD_LABELS` (for example `MF` and `MANUFACTURER` → "Manufacturer") and label alias renames as "Manufacturer kept under a second name", with the old name only in the detail column. Reword `_DROP_REASON["duplicate"]` from "duplicate Manufacturer/MPN alias" to "same value already kept under another name". Reword `_SET`/`extends` text in `import_dialog.py` line ~2228 ("extends parent X is included automatically") to plain words such as "Also writes parent X, which this symbol builds on".

2. **Reason strip hides reasons beyond three lines, and the Help page promises a list** — `import_dialog.py` `_build_*` strip (`self._strip.setMaximumHeight(3 * lineSpacing + 2 * SP_SM)`, around line 715) clips the text with no scroll, and `_render_strip` (around lines 2675-2688) joins reasons with " · ". A fresh import with MPN, Manufacturer, Datasheet, Description and 3D model missing shows only the first few. The rest are reachable only through a hover tooltip, which keyboard and touch users cannot use. `help_dialog.py` (importing page, "Atomic check", around line 313) says "The amber strip lists each problem on its own line", which is false. Fix: reuse the failure banner pattern (`_build_failure_banner`, a read-only `QPlainTextEdit` capped at six lines that scrolls), or make the strip scroll, and separate reasons with `<br>` so the Help text is true.

3. **Install Part and read-only fields do not look like what they are** — `import_dialog.py` never applies `PRIMARY_BUTTON_QSS` to `self._install_btn` (around line 735), though `main_window.py` and `atomic_check_dialog.py` do, so the dialog's main action is a plain default button. The read-only Value (around line 1062) and the read-only Footprint field (around line 1038) use the same white field as editable rows, with only a tooltip to show they are locked. Fix: apply `PRIMARY_BUTTON_QSS` to the install button; add a read-only rule for line edits (for example `QLineEdit[readOnly="true"] { background: SURFACE; color: MUTED; }` in theme.py, or set a palette on those two widgets) so Value and Footprint read as locked.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**Passing:**
- Most reason sentences are plain and actionable: "Enter the MPN", "Enter a Datasheet link", "Type a Description", "Pick or type a library name", "Choose Overwrite, Rename or Skip for ...". The `ki_*` names are mapped to words in the reasons (`form._plain`, `_ATOMIC_SENTENCES`).
- The `Keywords`, `Footprint description` and `Footprint tags` row labels, the "Set Keywords" preview rows, and the `_FIELD_LABELS` map in `preview.py` keep the raw `ki_keywords`, `ki_description` and `ki_fp_filters` names out of the preview.
- The "Not used" wording is plain: "footprint, not installed: one footprint per part", "3D model, not installed: KiCad's own 3D model is used".
- The official footprint sentences are plain: "Pick an official KiCad footprint", "KiCad's own footprints are never changed".

**Findings:**
- **Raw alias field name shown (WARNING, breaks owner rule).** `importer/planner.py` (around line 227) emits `FieldChange(new_name, "rename", target.name, "", name, "alias")`. The preview builds its row text from `change.field` (`preview.py` `_field_changes_section`), so a `MF` alias renders as "Rename MF" with detail "→ Manufacturer". The owner's rule forbids raw field names in user-facing text.
- **Jargon in preview reasons (WARNING).** `preview.py` `_DROP_REASON["duplicate"]` reads "duplicate Manufacturer/MPN alias". `_SET_REASON` is plain, but the field label map is not consistent: the Path rewrites row says "Footprint Filter" (`preview.py` line ~245), while the Field changes map says "Footprint filters" (line ~267). Pick one label.
- **KiCad term in dialog text (WARNING).** `import_dialog.py` (around line 2228) reads "extends parent X is included automatically". "extends" is KiCad's inheritance term. The owner would not use it.
- **Unexplained acronym and tooltip (INFO).** The MPN field is never spelled out as "manufacturer part number". Its tooltip, "MPN names the 3D model file" (`import_dialog.py` around line 1059), is a technical claim the owner may not recognise.
- **Raw error text in a status line (WARNING).** `import_dialog.py` around line 1908 shows `"KiCad's footprints could not be listed: {text}"` with `text` taken from the worker's error. The text is not filtered for plain words.
- **Inconsistent error prefix (INFO).** `form.blocking_reasons` gives "Error: ..." to every plan ERROR except `install.official_missing`, which gets a plain sentence. The "KiCad's footprints were not found, so an official footprint cannot be used" and "is not one of KiCad's installed footprints" reasons therefore read "Error: ...".
- **Help misdescribes the UI (WARNING).** `help_dialog.py`, importing page, "Atomic check": "The amber strip lists each problem on its own line." The strip joins them with " · " into one wrapped line (see Top Fix 2). The "Target library" section says "The strip under the field gives the reason", but the strip sits at the bottom of the window, not under the library field.

### Pillar 2: Visuals (2/4)

**Passing:**
- The reason strip is the one amber-tinted bar at the bottom, and the amber frames sit on the fields it names. The focal point of the form is clear.
- Icon-only controls (↺ restore, ↻ Regenerate, ✕ dismiss) each carry an accessible name and a tooltip. The Regenerate glyph choice is the known owner-judgement item and is not scored here.
- The Footprint destination is a two-radio choice with a muted hint and a disabled state when KiCad is missing, so the state is visible.

**Findings:**
- **Primary action has no primary treatment (WARNING).** `import_dialog.py` creates `self._install_btn = QPushButton("Install Part")` (around line 735) and never applies `PRIMARY_BUTTON_QSS`. `main_window.py` (`_generate_btn`) and `atomic_check_dialog.py` (`_preview_btn`, `_apply_btn`) do apply it. The dialog's only commit action is therefore the same visual weight as "Browse zip...".
- **Read-only fields look editable (WARNING).** The Value field (`import_dialog.py` around lines 1060-1063) and the Footprint field (around lines 1037-1040) call `setReadOnly(True)` and rely on a tooltip. No stylesheet or palette tells the eye they are locked, and the `FIELD_FRAME_QSS` rule only sets the blocked border. The Value restore button is disabled but still drawn, which adds to the confusion.
- **Section headings are not distinguished (WARNING).** `_heading()` (around line 836) only sets bold on the default font. "Footprint", "Fields" and "Conflicts" are the same size as the labels beneath them. `HEADING_PT` is defined in theme.py and used only for the start page heading.
- **Radio labels may clip (NEEDS VISUAL CHECK).** The two destination radios use `QSizePolicy.Ignored` horizontally (`_build_destination_choice`, around lines 972-973). "Install the vendor footprint into Atomic_Footprints" is long for a 364 px pane. A radio cannot wrap, so the end of the text may be cut. The geometry test (`test_the_destination_choice_and_picker_fit_the_left_pane`) checks that widgets fit the viewport, not that their text is complete, so it would pass with clipped text.

### Pillar 3: Color (3/4)

**Passing:**
- No literal hex colour in `import_dialog.py`. Colours come from `theme.AMBER`, `AMBER_TINT`, `ERROR`, `ERROR_TINT`, `SUCCESS`, `MUTED`, `LINK`, `BORDER`. The check is by grep; no hex literal matched.
- Contrast of the main text pairs is adequate: AMBER `#8A5200` on AMBER_TINT `#FFF8E1` and LINK `#0057A0` on AMBER_TINT are both well above 4.5:1 by calculation.
- Amber carries one meaning in the form (a blocked field or a blocking reason). The "existing" library badge is green, and the "new" badge is bold with no colour, so the two states are not colour-only.
- The preview tree maps tones to theme colours (`preview_tree.py` `_TONE_COLORS`). "Not used" rows are muted, so they read as inert, not as a problem.

**Findings:**
- **Dialog's main action has no accent (WARNING).** Only the dialog's primary control lacks the accent treatment that the other importer dialogs use (see Visuals). In 60/30/10 terms the accent is absent from the one place the owner's eye needs to go.
- **Clarification for the amber frames (INFO).** Up to five fields can be framed amber at once (model, MPN, Manufacturer, Datasheet, Description), and the strip is amber-tinted too. This is consistent, but the frame and the strip share one signal, so the strip gives no separate cue for a non-field reason such as a conflict.

### Pillar 4: Typography (3/4)

**Passing:**
- Mono (`theme.MONO_FAMILY`, `MONO_PT`) is used for the Footprint link and for "rewrite" preview rows, which suits paths and values.
- Weights are limited to bold, used in about five places. No italic or third weight is in use.
- Font sizes come from theme tokens: `HEADING_PT` for the start heading, `DISPLAY_PT` for the failure banner title.

**Findings:**
- **Flat hierarchy in the form (WARNING).** Section headings use the default size in bold (`_heading()`), the same as the labels they introduce. `HEADING_PT` exists for this purpose but is not used. The result is a page of equal-size labels with no entry point per section.
- **Mono value font in fields only partly applied (INFO).** The read-only Footprint field is mono, while the editable Value, Datasheet and MPN fields are not. A reader comparing a Footprint link with an MPN sees two families.

### Pillar 5: Spacing (3/4)

**Passing:**
- Spacing values stay on the scale: 4, 8, 16, 24, 32 (`SP_XS`..`SP_XL`). No off-scale value was found in the importer dialog.
- The restore, Regenerate and Dismiss buttons are a fixed 24 px, and fields have a 28 px minimum height, so the field column lines up (`_restore_button`, `_aligned_row`).
- The `_aligned_row` helper keeps the read-only rows on the same right edge as the editable rows, which is a deliberate and good alignment choice.

**Findings:**
- **Token drift (INFO).** About 50 `setSpacing(...)` and `setContentsMargins(...)` calls use literal 4, 8 or 16 (for example `form.setSpacing(8)`, `outer.setContentsMargins(16, 16, 16, 16)`) where `SP_SM` and `SP_MD` exist. The values match today; a future change to the scale will miss these.
- **Reason strip clips its own content (WARNING).** The strip's maximum height is three lines (`setMaximumHeight(3 * lineSpacing + 2 * SP_SM)`), and it has no scroll. Reasons that do not fit are cut off without a "more" cue (see Top Fix 2).
- **Hard-coded popup width (INFO).** `_OFFICIAL_POPUP_WIDTH = 420` is a fixed pixel width for the official footprint popup. It is wider than the 364 px left pane the geometry tests use, and it does not scale.

### Pillar 6: Experience Design (3/4)

**Passing (state coverage):**
- Reading state: "Reading KiCad's footprints..." while the official list builds on a worker, and "Updating..." while a rebuild runs. Install is off during both.
- No KiCad installed: the official radio is disabled with "KiCad's footprints were not found" and an explanatory note. The stock sibling lookup is skipped with one INFO line.
- Empty and refused states: "No KiCad symbol or footprint was found in this package.", "Pick another file.", and the library field starts empty with a hint when nothing places the part.
- Live clearing: a reason drops as soon as the field it names is typed into (`_atomic_fixed_live`), and the amber frame follows the live text.
- Clickable reasons focus the field that fixes them (`_on_reason_link`), and links are reachable by keyboard as well as mouse (`LinksAccessibleByKeyboard`).
- Install failure: a red banner lists the reasons, says whether every file was restored, and asks for a retry.
- Ctrl+Return installs only when the button is enabled.
- Preview before write: nothing is written until Install Part is clicked, and the "Not used" rows show what will not be written.

**Findings:**
- **Reasons beyond three lines are not reachable on screen (WARNING).** See Pillar 5 and Top Fix 2. A keyboard user can tab to the links only if they are visible; links past the clip are not reachable at all.
- **Library suggestion reason is hover-only (INFO, owner decision D-06).** The "Suggested from 75 similar parts..." reason sits only in the combo tooltip, as decided. Keyboard and touch users cannot see why a library was chosen. This is the owner's call; note it, do not change it.
- **Read-only Value gives no cue (WARNING).** See Visuals. The owner clicks Value, nothing happens, and the only explanation is a tooltip.
- **Help promises a behaviour the strip does not have (WARNING).** See Copywriting. The Help text says each problem is on its own line; the strip does not do that.
- **Official picker popup width is fixed (INFO).** `combo.view().setMinimumWidth(_OFFICIAL_POPUP_WIDTH)` may extend past the window edge on a small screen.

---

## Registry Safety

Not applicable: no `components.json` and no third-party UI registry in this phase.

---

## Files Audited

- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/import_dialog.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/importer/preview.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/importer/form.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/importer/planner.py (issue texts, alias rename rows)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/preview_tree.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/help_dialog.py (importing page)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/theme.py
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/main_window.py (primary-button reference only)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/kicad_lib_manager/widgets/atomic_check_dialog.py (primary-button reference only)
- C:/Git_Repo_Clones/Kicad_Libraries-importer/tests/test_official_footprint.py (geometry test scope)
- Phase inputs: 10-CONTEXT.md, 09-UI-REVIEW.md, 10-12 to 10-17 and 10-22 to 10-25 SUMMARY.md

Not audited: rendered layout, real text widths, clipping of the radio labels, icon appearance, popup placement, and keyboard flow in a running window. Those findings are code-derived and need a look in the real app.
