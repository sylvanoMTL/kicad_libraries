---
status: resolved
trigger: "UAT gap G-07-7: The table in preview: the columns cannot resize, and get shricked if expanding, shrinking the Import part window edges"
created: 2026-10-24T10:00:00Z
updated: 2026-10-25T00:00:00Z
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - PreviewTree's header (preview_tree.py:26-29,35) has no Interactive section (Item = Stretch, Detail = ResizeToContents) and the horizontal scrollbar is forced off. QHeaderView only lets the user drag a section in Interactive mode, so the divider is dead. ResizeToContents pins Detail at its widest single-line content width, whatever the viewport. Stretch gives Item only the leftover width (viewport - Detail), and when Detail alone is wider than the viewport, Item keeps a stale width and Detail is clipped past the right edge.
test: done - headless native-Windows (WA_DontShowOnScreen) and offscreen measurements of the real ImportDialog with the real SnapEDA/SamacSys/UL zips, plus a QTest mouse drag on the divider
expecting: n/a (diagnosed)
next_action: return ROOT CAUSE FOUND to the orchestrator (find_root_cause_only - no fix applied)
bug_class: Bohrbug (deterministic layout configuration, reproduces on every open of a part with Field changes)

reasoning_checkpoint:
  hypothesis: "The user cannot drag the preview columns because neither PreviewTree header section is QHeaderView.ResizeMode.Interactive (0 = Stretch, 1 = ResizeToContents, preview_tree.py:28-29). Columns squash on dialog resize because ResizeToContents locks Detail at its content width (734 px for the SnapEDA plan, due to monospace Field-changes drop rows) and Stretch gives Item only viewport - Detail. The h-scrollbar is AlwaysOff (line 35), so nothing can absorb an overflow."
  confirming_evidence:
    - "Header modes read back from the live dialog: [Stretch, ResizeToContents], stretchLastSection False, h-scrollbar AlwaysOff"
    - "QTest press/move(-80 px)/release on the Item|Detail divider: sizes unchanged (320,734) in the current modes; with both sections Interactive the same drag moves Item 320 -> 240"
    - "Native Windows metrics (Consolas 9, DPR 1.0), SnapEDA zip: viewport 634 / Item stale 595 / Detail 734 at 1100 px; viewport 814 / Item 80 / Detail 734 at 1400 px; back at 1100 Item 320, overflow 420 px clipped. Detail never changes width"
    - "Differential: UL zip (no Field changes) gives Detail 321 px, Item = viewport - 321 (313 at 1100, 158 at 900); SamacSys zip (Field changes drop row, 104 chars) shows the same 734 px overflow as SnapEDA"
  falsification_test: "If any section were Interactive or the drag moved the divider in the current modes, or if Detail's width followed the viewport, the hypothesis would be wrong. All three were checked and did not happen."
  fix_rationale: "Give the header at least one Interactive section and stop Detail from claiming its full content width, for example Item Interactive with an initial width and Detail as the stretched last section that elides, with the tooltip already holding the full text. That fixes both symptoms at the source, the header resize policy, instead of patching widths after each render."
  blind_spots: "Not seen on the owner's real display (DPI scaling >100% would widen Detail further). The splitter handle position also changes the viewport width, but it does not change the mechanism. word-wrap + ElideMiddle interplay inside a narrow Item column was not measured row by row."
  candidate_causes:
    - "code: PreviewTree header resize modes + ScrollBarAlwaysOff (preview_tree.py:26-35) - CONFIRMED"
    - "config/design: 05-UI-SPEC.md:315 and :511 prescribe exactly 'Item (stretch, elide in the middle) and Detail (resize to contents) ... no horizontal scrollbar' - CONFIRMED as the origin of the code"
    - "data: phase 07 Field changes rows (preview.py:267-283, commit 906cfc0) put up to ~104-char monospace strings in Detail (_shown keeps 57 chars + '...' + ' -> (removed): <reason>'); Path rewrites rows are not capped at all - CONFIRMED as the trigger of the severe (overflow) form"
    - "environment: offscreen vs native font metrics - ruled out as a cause (native metrics reproduce it; offscreen only makes it worse: Detail 1254 px)"
  and_gate: "yes, partly. The non-draggable divider needs only the header config. The severe squash/clip the user saw needs config AND Detail content wider than the viewport minus a usable Item width, which phase 07's Field-changes rows supply (734 px > 634 px viewport). UL-only plans (321 px Detail) still squash Item to 158 px at the 900 px minimum, so the config is necessary, and the phase 07 data turned a mild defect into a major one."

## Symptoms

expected: In the Import dialog preview, the table's columns can be resized by dragging the header dividers, and resizing the Import part window keeps the columns readable instead of squashing them.
actual: "The table in preview: the columns cannot resize, and get shricked if expanding, shrinking the Import part window edges"
errors: none
reproduction: UAT test 7 (07-UAT.md) - run .\env\Scripts\python.exe kicad_lib_manager.py, open Import part, load downloaded_examples/USB4145-03-0170-C_REVA2.zip, look at the table(s) in the preview area; drag header dividers; resize dialog edges.
started: Discovered 2026-10-24 during UAT re-test (observed during test 3). Preview may predate phase 07 (Phase 5 import UI).

## Eliminated

- hypothesis: Preview rebuilds (render() / _request_rebuild) reset column widths and undo user drags
  evidence: PreviewTree never calls setColumnWidth/resizeColumnToContents; QTreeWidget.clear() keeps header section sizes. Measured with both sections Interactive - dragged Item 240 stays 240 after tree.render(sections) and after a full dialog._request_rebuild(). Under the current modes there is no user width to lose; Qt recomputes widths from the modes on every layout.
  timestamp: 2026-10-24T10:30:00Z

- hypothesis: The tree is inside a QScrollArea(setWidgetResizable) that squeezes it
  evidence: import_dialog.py:572-590 - PreviewTree sits directly in self._preview_stack (QStackedWidget) in the right pane of a horizontal QSplitter; only the LEFT pane is a QScrollArea (517-543).
  timestamp: 2026-10-24T10:10:00Z

- hypothesis: A phase 07 code change to PreviewTree broke previously working resizable columns
  evidence: git log of preview_tree.py has only b5c5bca (05-01) and 65d1c3a (05-06), both 2026-10-22; the header config is unchanged since Phase 5 and matches 05-UI-SPEC.md:315. Columns were never user-resizable. Phase 07 only added the longer Detail content (Field changes, 906cfc0).
  timestamp: 2026-10-24T10:35:00Z

- hypothesis: There is a second table (e.g. a separate "Field changes" QTableWidget) in the preview
  evidence: no QTableWidget/QTableView in kicad_lib_manager/; Files, Renames, Path rewrites, Field changes, Format, Conflicts, Issues are all top-level sections of the one PreviewTree (preview_tree.py:63-72).
  timestamp: 2026-10-24T10:05:00Z

## Evidence

- timestamp: 2026-10-24T10:00:00Z
  checked: .planning/debug/knowledge-base.md
  found: file does not exist; no prior resolved sessions
  implication: no known-pattern candidate; proceed with open investigation

- timestamp: 2026-10-24T10:05:00Z
  checked: grep of kicad_lib_manager/ for QTreeWidget/QTableWidget/header resize calls
  found: the only table in the Import dialog preview is PreviewTree (kicad_lib_manager/widgets/preview_tree.py), a 2-column QTreeWidget ("Item", "Detail"). Lines 26-29 - header.setStretchLastSection(False); section 0 = QHeaderView.ResizeMode.Stretch; section 1 = QHeaderView.ResizeMode.ResizeToContents. Line 35 - setHorizontalScrollBarPolicy(ScrollBarAlwaysOff). Line 34 - ElideMiddle; line 32 - setWordWrap(True). No QTableWidget/QTableView anywhere in import_dialog.py; "Field changes" etc. are sections (top-level items) of this same tree, not separate tables.
  implication: neither section is Interactive, so Qt gives the user no draggable divider (QHeaderView only lets the user drag a section whose resize mode is Interactive). Column widths are fully computed by Qt.

- timestamp: 2026-10-24T10:06:00Z
  checked: kicad_lib_manager/widgets/import_dialog.py _build_edit_page (478-637)
  found: PreviewTree is created at line 584, placed in self._preview_stack (QStackedWidget) on the right side of a horizontal QSplitter (513-592); right pane minimumWidth 400 (589), left QScrollArea minimumWidth 380 (543), splitter sizes [440, 660] (591); dialog resize(1100,720), setMinimumSize(900,600) (353-354). The tree is NOT inside a QScrollArea (only the left pane is).
  implication: when the dialog or splitter shrinks, the tree viewport shrinks; with h-scrollbar forced off there is no overflow escape, so the column widths must fit the viewport.

- timestamp: 2026-10-24T10:07:00Z
  checked: git log of preview_tree.py and .planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md
  found: header modes introduced in b5c5bca (05-01) / 65d1c3a (05-06), 2026-10-22. 05-UI-SPEC.md:315 specifies verbatim "two columns Item (stretch, elide in the middle) and Detail (resize to contents) ... no horizontal scrollbar"; 05-UI-SPEC.md:511 marks E9 Preview tree overflow as covered by eliding the Item column. Contrast 05-UI-SPEC.md:192 for the main-window library trees, which use Interactive for the first columns.
  implication: the behaviour predates phase 07 and is a faithful implementation of the Phase 5 design contract; the contract itself does not provide user-resizable columns. Not a phase 07 regression.

- timestamp: 2026-10-24T10:20:00Z
  checked: headless run (QT_QPA_PLATFORM=offscreen) of scratchpad measure_preview.py - real ImportDialog over a temp copy of Custom/, real USB4145-03-0170-C_REVA2.zip, real build_plan
  found: |
    modes = [Stretch, ResizeToContents], stretchLastSection False, minimumSectionSize 16, h-scrollbar AlwaysOff.
    Sections: Files, Path rewrites, Field changes, Format, Conflicts, Issues. Widest Detail = Field changes drop row
    "https://www.snapeda.com/parts/USB4145-03-0170-C/Global+Co... -> (removed): price or stock data goes stale" (104 chars, monospace because kind == "rewrite").
    dialog 1100: viewport 636, Item 562, Detail 1254 (= sizeHintForColumn(1)), overflow 1180 px
    dialog  900: viewport 482, Item 562, Detail 1254, overflow 1334
    dialog 1400: viewport 816, Item 562, Detail 1254
    dialog 1800: viewport 1056, Item 562, Detail 1254
    Mouse drag on the Item|Detail divider (QTest press/move -80/release): cursor ArrowCursor, sizes unchanged (562,1254) -> not draggable.
    Counterfactual with both sections Interactive: same drag moves Item 562 -> 482; tree.render(sections) keeps (482,1254); a full dialog._request_rebuild() keeps (482,1254).
  implication: (1) no Interactive section => user cannot drag (confirmed). (2) ResizeToContents pins Detail at its widest single-line content width regardless of viewport; with the h-scrollbar off the overflow is simply clipped. (3) Qt's QHeaderViewPrivate::resizeSections only re-stretches a Stretch section when lengthToStretch > 0 (viewport minus non-stretch widths); when Detail alone exceeds the viewport, Item keeps a stale width. (4) Rebuilds do NOT reset widths themselves - PreviewTree never calls setColumnWidth/resizeColumnToContents; clear() keeps header section sizes - so an Interactive fix will survive rebuilds. Offscreen font metrics may exaggerate widths; re-measure with the native Windows platform.

- timestamp: 2026-10-24T10:28:00Z
  checked: same script on the native "windows" QPA platform with WA_DontShowOnScreen (real font metrics: Consolas 9 pt, DPR 1.0), SnapEDA zip
  found: |
    minimumSectionSize 32.
    dialog 1100: viewport 634, Item 595 (stale), Detail 734, overflow 695 px
    dialog  900: viewport 479, Item 595 (stale), Detail 734, overflow 850 px
    dialog 1400: viewport 814, Item 80 (= 814 - 734), Detail 734, overflow 0
    dialog 1800: viewport 1054, Item 320, Detail 734
    back 1100: viewport 634, Item 320 (stale), Detail 734, overflow 420 px
    Drag in current modes: unchanged (320,734). Interactive counterfactual: 320 -> 240, kept by render() and _request_rebuild().
  implication: reproduces the user's report with real metrics. Detail is fixed at 734 px, wider than the default 634 px viewport. Item is squashed (80 px) or frozen at a stale width, and the right part of Detail is clipped with no scrollbar, depending on the window size.

- timestamp: 2026-10-24T10:38:00Z
  checked: differential, native metrics, UL ul_CSD85301Q2.zip with library IC_Battery_Charger_TI and SamacSys LIB_RS3-1212S_H3.zip with library PowerSupply_DCDC_RECOM
  found: |
    UL (sections Files, Renames, Path rewrites, Format, Issues; widest Detail "(none) -> ${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp", 45 chars): Detail 321 px; Item = viewport - 321 -> 313 @1100, 158 @900, 493 @1400; no overflow.
    SamacSys (adds Field changes; widest Detail = mouser URL drop row, 104 chars): Detail 734 px, identical overflow pattern to SnapEDA (695/848 px clipped at 1100/900, Item 80 @1400).
  implication: the header config alone already makes the divider undraggable and squashes Item as the window narrows (UL, Phase 5 data). The phase 07 "Field changes" section (preview.py:267-283, commit 906cfc0 feat(07-02)) adds monospace Detail strings up to ~104 chars, which push Detail past the viewport and turn a mild defect into the severe clipping/squash the user reported. Both phase 07 vendors are affected.

- timestamp: 2026-10-24T10:40:00Z
  checked: tests touching the preview tree
  found: tests/test_preview_tree.py::test_tree_no_horizontal_scroll_and_elide pins ScrollBarAlwaysOff, ElideMiddle, wordWrap, header labels ["Item","Detail"] and per-cell tooltips; it does NOT assert section resize modes. test_render_restores_expand_and_scroll pins vertical scroll/expand restore across render(). tests/test_import_dialog.py uses dialog._preview only for content (files_rows, .sections, row_activated); its geometry tests (test_fields_long_text_geometry:1336, test_library_long_name_geometry:1562, test_conflicts_overflow_geometry:2209, test_result_view_scrolls_at_minimum_size:3505) all target _left_scroll / result view, not the preview header. No test covers preview column widths or user resizing.
  implication: a fix that changes resize modes breaks no existing assertion; enabling an h-scrollbar would require changing test_tree_no_horizontal_scroll_and_elide and the 05-UI-SPEC E9 contract. A new regression test is needed (no gate existed for this class).

## Resolution

root_cause: "PreviewTree (kicad_lib_manager/widgets/preview_tree.py:26-29,35), the one table in the Import dialog preview, sets header section 0 (Item) to QHeaderView.ResizeMode.Stretch and section 1 (Detail) to ResizeToContents, with stretchLastSection False and the horizontal scrollbar AlwaysOff, exactly as 05-UI-SPEC.md:315 prescribes. (a) Neither section is Interactive, so QHeaderView ignores drags on the divider and the user cannot resize. (b) ResizeToContents locks Detail at its widest single-line width, whatever the viewport. Stretch gives Item only viewport - Detail and is not recomputed when that is <= 0. So resizing the dialog moves all the change into Item (squashed to 80 px at 1400 px wide) or leaves Item at a stale width while Detail is clipped past the right edge. AND-gate trigger: the phase 07 Field changes section (preview.py:267-283, 906cfc0) puts monospace Detail strings up to ~104 chars (734 px on Windows at Consolas 9) into the SnapEDA and SamacSys previews, which is wider than the default 634 px viewport. That turned the latent Phase 5 defect (UL: Detail 321 px, Item squashed to 158 px at 900 px) into the severe squash/clip the user reported. Rebuilds do not reset widths (verified)."
fix: (not applied - goal find_root_cause_only)
verification: (diagnosis only) reproduced headless on native Windows metrics and offscreen; drag counterfactual with Interactive modes moves the divider and survives render() and _request_rebuild()
files_changed: []

## Resolution

resolved: 2026-10-25 at v1.0 milestone close
fixed_by: G-07-7, plan 07-11 (Interactive Item column, stretched eliding Detail)
verified_by: 07-VERIFICATION.md (status: passed) and 07-UAT.md (issue resolved by gap closure)
