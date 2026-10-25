# Phase 5: Import UI and Post-Install - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-20
**Phase:** 05-import-ui-and-post-install
**Areas discussed:** Dialog flow & entry, Live preview behaviour, Editing & conflicts, After install

---

## Dialog flow & entry

**Shape of the import UI**

| Option | Description | Selected |
|--------|-------------|----------|
| One dialog, split view | Choices left, live preview right, Install at bottom | ✓ |
| Wizard (QWizard pages) | Package → Items → Library & fields → Preview → Install | |
| Panel in main window | Tab or dock inside the Library Manager | |

**Newest Downloads zip (UX-02)**

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-fill + Open | Start step shows newest Downloads zip with Open, beside Browse zip / Browse folder | ✓ |
| File dialog only | QFileDialog in last folder, newest zip pre-selected | |
| Auto-open newest | Open a recent Downloads zip immediately, with Change... | |

**Item picker (INTK-07)**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in the left pane | Symbol combo, footprint checklist (first = linked), model combo with No model | ✓ |
| Separate picker step first | Modal picker before the main dialog | |
| You decide | Leave to planning / UI-SPEC | |

**Refused or empty package**

| Option | Description | Selected |
|--------|-------------|----------|
| Dialog stays open, reasons shown | Start step lists reasons; also logged | ✓ |
| Log only, no dialog | Reasons only in the log panel | |
| Message box | QMessageBox with reasons | |

---

## Live preview behaviour

**When the plan rebuilds**

| Option | Description | Selected |
|--------|-------------|----------|
| Debounced auto, on a worker | ~300 ms after typing, immediate on combos; cached kicad-cli; stale rebuild superseded | ✓ |
| On field commit | Rebuild on focus-out / Enter | |
| Refresh button | Manual "Update preview" | |

**Preview presentation**

| Option | Description | Selected |
|--------|-------------|----------|
| Sectioned tree | Files, Renames, Path rewrites, Format, Conflicts, Issues | ✓ |
| Formatted text report | Read-only HTML report | |
| You decide | Leave to UI-SPEC | |

**Content view**

| Option | Description | Selected |
|--------|-------------|----------|
| Double-click a file → diff | Planned text / unified diff / size + SHA-256 | ✓ |
| List only | No contents shown | |
| Inline diff pane | Third pane under the tree | |

**During install**

| Option | Description | Selected |
|--------|-------------|----------|
| Progress, no cancel | Worker, progress bar, inputs locked, close blocked | ✓ |
| Progress with Cancel | Cooperative cancel with rollback | |
| Busy cursor only | Synchronous with wait cursor | |

**Why Install is disabled**

| Option | Description | Selected |
|--------|-------------|----------|
| Status line + jump links | Clickable reasons, amber border on field | ✓ |
| Status line only | Reasons listed, no click-through | |
| Tooltip on Install | Reasons on hover | |

**Highlight changes between rebuilds**

| Option | Description | Selected |
|--------|-------------|----------|
| No highlight | Re-render keeping expand state and scroll | ✓ |
| Brief flash on changed rows | Highlight rows that differ | |

---

## Editing & conflicts

**Target library picker**

| Option | Description | Selected |
|--------|-------------|----------|
| Editable combo + badge | Suggestion pre-filled, ranked alternatives then all libraries, existing/new badge, amber for low confidence | ✓ |
| Token fields | Type / SubCategory / Manufacturer fields | |
| Existing / New radio | Explicit mode switch | |

**Conflict resolution control**

| Option | Description | Selected |
|--------|-------------|----------|
| Row with 3 buttons + rename field | Overwrite / Rename / Skip, none preselected, suggested rename name, diff on double-click | ✓ |
| Combo box per row | Compact combo | |
| You decide | Leave to UI-SPEC | |

**Fields and explicit clear (WR-05)**

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-filled, empty = clear | WYSIWYG; ↺ resets; Value and MPN can't be empty; small Phase 4 change | ✓ |
| Placeholder = vendor, blank keeps it | Current Phase 4 rule, no clearing | |
| Placeholder + explicit Clear toggle | Per-field clear checkbox | |

**Symbol name editable?**

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only, shown vendor → sanitised | Renamed only via conflict Rename | ✓ |
| Editable | New InstallOptions field | |

**Conflict choices across rebuilds**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep by conflict key | Kind + library + name; vanished conflicts drop choice | ✓ |
| Reset all on any rebuild | Clear every choice | |
| Keep by item name only | Follows vendor name across libraries | |

**Field edits when the symbol pick changes**

| Option | Description | Selected |
|--------|-------------|----------|
| Reset to new symbol's values | Library change keeps edits | ✓ |
| Keep edited fields | Edits survive any pick | |

---

## After install

**Dialog after Install**

| Option | Description | Selected |
|--------|-------------|----------|
| Result view in the dialog | Summary, warnings, KiCad notice, backup dir; Phase 6 commit lands here; failure returns to preview | ✓ |
| Close + log summary | Everything to the log | |
| Close on success, stay on failure | Middle ground | |

**Table regeneration for a new library (POST-02)**

| Option | Description | Selected |
|--------|-------------|----------|
| Add-only, automatic | Only the new library's entries added; nothing else changes | ✓ |
| Full Generate, automatic | Current tree selection + new library | |
| Ask first | Pre-checked button in the result view | |

**Meaning of "selected" (POST-01)**

| Option | Description | Selected |
|--------|-------------|----------|
| Checked + scrolled + highlighted | Rows checked, expanded, current; rest of selection kept | ✓ |
| Highlighted only | Check state unchanged | |

**Modality**

| Option | Description | Selected |
|--------|-------------|----------|
| Modal; Import disabled during scan | Window-modal; Import and drops join the busy guard | ✓ |
| Non-modal | Main window usable during import | |

---

## Claude's Discretion

- Module layout, worker placement, shortcut and menu placement for "Import Part..."
- Locating the Downloads folder and the age threshold for offering a zip
- Debounce interval and the supersession mechanism
- How the add-only table merge is implemented
- Diff view widget and size cap
- Folding in the Phase 2 UI-review fixes and the Phase 4 WR-02 early refusal
- Test strategy (pytest-qt offscreen plus manual UAT)

## Deferred Ideas

None. The git commit from the result view is Phase 6.
