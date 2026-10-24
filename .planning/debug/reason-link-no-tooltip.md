---
status: diagnosed
trigger: "UAT gap G-07-8: Clickable reason links in the status strip carry a tooltip saying they jump to the control that fixes the reason. User: 'There is no tooltip on that message, what if I clickon it?'"
created: 2026-10-24T10:00:00Z
updated: 2026-10-24T10:50:00Z
goal: find_root_cause_only
---

## Current Focus

bug_class: Bohrbug (deterministic UI copy and spec gap; SBFL skipped because no failing test exists for a tooltip hint and the gap is unspecified behaviour)
known_pattern_candidate: none (no .planning/debug/knowledge-base.md; MemPalace not available)
hypothesis: CONFIRMED H1 (primary) plus contributing C2. _render_strip's tooltip only repeats the reason texts, so nothing says a reason is clickable or where a click goes. The strip's unselected stylesheet also paints that tooltip on the same AMBER_TINT, so the identical-text tooltip blends into the strip.
test: done (scratchpad probe on the real dialog in the clash_dialog conflict state, plus a fresh-label stylesheet differential)
expecting: n/a
next_action: none (diagnose-only). Return ROOT CAUSE FOUND to the caller (plan-phase --gaps).
reasoning_checkpoint:
  hypothesis: "The UAT truth fails because the strip's only tooltip is the reason list (05-UI-SPEC E11/overflow): import_dialog.py:2222 builds tooltip = '<br>'.join(escaped reason texts) and no copy anywhere names the click behaviour. The user perceived 'no tooltip' because, with one reason, that tooltip is a verbatim copy of the link text and is drawn on the strip's own AMBER_TINT (#FFF8E1). The unselected 'background-color' rule set by _set_strip (2167) cascades to the QToolTip through Qt's stylesheet parent."
  confirming_evidence:
    - "Probe on the real dialog: strip.toolTip() == 'Choose Overwrite, Rename or Skip for footprint DQK0006B', the same as the only link text. QToolTip shows exactly that at every x across the strip."
    - "Fresh-label differential: tooltip background is #ffffdc with no stylesheet and #fff8e1 with the strip's 'background-color: #FFF8E1;'. In the dialog the tip's _q_stylesheet_parent is the strip."
    - "05-UI-SPEC.md:353/:517 and 05-09-PLAN.md:42 specify the tooltip only as the full reason list. linkHovered has 0 receivers. Reason has no hint field."
  falsification_test: "If strip.toolTip() contained click/jump copy, or QToolTip rendered on the default #ffffdc, or QToolTip.text() were empty while toolTip() is set, the hypothesis would be wrong. None of these was observed."
  fix_rationale: "Adding click-hint copy to the tooltip addresses the failed truth directly. Scoping the strip stylesheet with an object-name selector stops the tooltip inheriting the amber, so the tooltip is visibly distinct from the strip."
  blind_spots: "Probe ran on the offscreen QPA, not the Windows plugin. QTipLabel and QStyleSheetStyle are platform-independent, so the same result is expected, but the user's exact screen was not captured. The user may also have hovered for less than the ~700 ms tooltip wake-up delay; this does not change the fix."
  candidate_causes:
    - "code/spec (CONFIRMED): tooltip content is the reason list only, with no click hint; matches 05-UI-SPEC, which never asked for one"
    - "code/style (CONFIRMED, contributing): the unselected strip stylesheet cascades to its QToolTip, so the tooltip is amber like the strip"
    - "environment/Qt (REFUTED): QLabel rich text or links swallow ToolTip events"
    - "data/state (REFUTED): tooltip cleared by a later _set_strip call before hover"
  and_gate: "Yes, for the perception 'there is no tooltip': identical text AND identical background together make the tip indistinguishable. No, for the failed UAT truth (no click-hint copy): the content gap alone fails it."

## Symptoms

expected: A blocking reason in the status strip (e.g. "Choose Overwrite, Rename or Skip for <kind> <name>") shows a tooltip saying that clicking it jumps to the control that fixes it.
actual: "There is no tooltip on that message, what if I clickon it?" - no tooltip appears when hovering the status-strip message shown for an unresolved install conflict.
errors: none
reproduction: UAT test 8 (.planning/phases/07-snapeda-and-samacsys-adapters/07-UAT.md) - open Import dialog with a part already in Custom/ so a conflict appears; hover the strip message at the bottom of the dialog.
started: Discovered during UAT re-test 2026-10-24. The strip predates phase 07 (Phase 5, D-09 blocked-field highlight).

## Eliminated

- hypothesis: H2 - the tooltip is set but never shown at runtime (QLabel rich-text control or the stylesheet suppresses QToolTip)
  evidence: QHelpEvent(ToolTip) sent at every x across the real strip shows QToolTip (visible=True) with the strip's toolTip(). A standalone QLabel with the same flags, rich text, links and stylesheet behaves the same.
  timestamp: 2026-10-24T10:30:00Z

- hypothesis: H3 - the tooltip is cleared by a later _set_strip call (Updating... cycle) before hover
  evidence: In the settled conflict state (wait_current), strip.toolTip() == 'Choose Overwrite, Rename or Skip for footprint DQK0006B' (non-empty). _set_strip always sets the tooltip together with the text, so they cannot disagree.
  timestamp: 2026-10-24T10:30:00Z

## Evidence

- timestamp: 2026-10-24T10:05:00Z
  checked: kicad_lib_manager/widgets/import_dialog.py lines 596-612 (strip construction), 2163-2169 (_set_strip), 2210-2230 (_render_strip), 2232-2247 (_on_reason_link)
  found: self._strip is a QLabel, PlainText at construction, no setToolTip there. _set_strip(text, rich, style, tooltip) sets format, stylesheet, text, then strip.setToolTip(tooltip) on EVERY call (default tooltip=""). Only the blocked branch of _render_strip passes a tooltip, and it is tooltip = "<br>".join(html.escape(reason.text) for reason in reasons) - the reason texts themselves. Strip text is f"⚠ Install is blocked: {links}" with links = '<a href="reason:{i}" style="color:{LINK}">{escaped text}</a>' joined by " · ". linkActivated -> _on_reason_link focuses _reason_targets[target] (or _preview for "plan") and ensureWidgetVisible in the left scroll.
  implication: A strip-wide tooltip IS set while blocked, but its content only repeats the visible reason text; nothing anywhere says the reasons are links or that clicking jumps to the fixing control. No linkHovered handler exists.

- timestamp: 2026-10-24T10:05:00Z
  checked: kicad_lib_manager/importer/form.py lines 65-199 (Reason, blocking_reasons)
  found: Reason(text, target) - no hint field. Conflict reason text "Choose Overwrite, Rename or Skip for {kind_label(kind)} {name}" target "conflict:{key}"; rename reason "Enter a new name for ..." target "rename:{key}"; plan-level reasons target "plan".
  implication: The model carries the target needed for a per-link hint (e.g. "plan" reasons jump to the preview, others to a left-pane control) but no hint copy.

- timestamp: 2026-10-24T10:15:00Z
  checked: .planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md:353 and :517, 05-09-PLAN.md:42, 05-DISCUSSION-LOG.md:86-88
  found: The spec defines the strip tooltip only as "full list in the tooltip" for the 3-line overflow case (E11/overflow). "Tooltip on Install - reasons on hover" was a rejected option; "Status line + jump links" was chosen. No copy anywhere says the reasons are clickable or what a click does.
  implication: The implementation matches the spec. The missing hint is a spec gap carried into code, not a regression.

- timestamp: 2026-10-24T10:20:00Z
  checked: Existing strip tests (pytest tests/test_import_dialog.py -k "strip or conflict_rename_field_and_empty_reason or placeholder_blocks", offscreen, importer venv PySide6 6.12.0)
  found: 10 passed. The only tooltip assertion is test_strip_caps_three_lines_with_tooltip (tests/test_import_dialog.py:1763-1775), which checks that each of 10 reason texts is CONTAINED in strip.toolTip().
  implication: Nothing tests a click hint, the tooltip styling or linkHovered. Appending a hint line keeps the existing test green.

- timestamp: 2026-10-24T10:30:00Z
  checked: Scratchpad probe (scratchpad/g078/test_probe_strip_tooltip.py) using the real ImportDialog via the clash_dialog(model=False) fixture, i.e. the UAT conflict state; QHelpEvent(ToolTip) sent at x = 4..900 step 25 across the strip
  found: strip.text() = '⚠ Install is blocked: <a href="reason:0" style="color:#0057A0">Choose Overwrite, Rename or Skip for footprint DQK0006B</a>'; textFormat RichText; strip.toolTip() = 'Choose Overwrite, Rename or Skip for footprint DQK0006B'; stylesheet 'background-color: #FFF8E1;'; QToolTip shows at every x position with exactly that text (visible=True); linkHovered exists but has 0 receivers.
  implication: H3 refuted (the tooltip is not cleared). H2 refuted (Qt does show it; QLabel does not swallow ToolTip events over rich text or links). H1 confirmed: with one reason the tooltip is a verbatim copy of the visible message and says nothing about clicking.

- timestamp: 2026-10-24T10:40:00Z
  checked: Fresh-QLabel tooltip background differential (one tip per label, 1.2 s wait between so QTipLabel is destroyed): no stylesheet vs the strip's 'background-color: #FFF8E1;' vs 'color: #6B6B6B;'
  found: Tooltip background is #ffffdc with no stylesheet, #fff8e1 with the strip's amber stylesheet, and #ffffdc with the colour-only one. In the real dialog the tooltip label is also drawn #fff8e1, and its _q_stylesheet_parent is the strip. (The first in-dialog differential was confounded: hideText() keeps the tip alive about 300 ms, so the reused tip was not re-polished. It was discarded.)
  implication: The strip's unselected stylesheet rule applies to its QToolTip, because Qt styles a tooltip with the stylesheet of the widget it is shown for. So the tooltip pops up with the same text on the same amber as the strip under the cursor, and visually blends in. This is the likely reason the user reported "no tooltip" rather than "an unhelpful tooltip".

- timestamp: 2026-10-24T10:40:00Z
  checked: Qt.mightBeRichText on the tooltip strings _render_strip builds
  found: One reason gives 'Choose ... A&amp;B', where mightBeRichText is False, so the tip renders as plain text with the entity shown literally. Two reasons give 'one A&amp;B<br>two', where mightBeRichText is True, so it renders as rich text and the entity is decoded.
  implication: Latent secondary defect. A single-reason tooltip shows html entities (&amp;, &#x27;, &lt;) literally. A fix that rewrites the tooltip should force rich text (e.g. wrap in <p>...</p> or <qt>) so a single reason decodes too.

## Resolution

root_cause: "Spec gap carried into code. The blocked strip's only tooltip is the reason list, built in kicad_lib_manager/widgets/import_dialog.py:2222 as tooltip = '<br>'.join(html.escape(reason.text) ...) per 05-UI-SPEC E11/overflow ('full list in the tooltip'). No copy anywhere (tooltip, strip text, Reason model) says a reason is a link or that clicking jumps to the control that fixes it. linkHovered is unused. With the single conflict reason the tooltip is a verbatim copy of the visible link text; Contributing: _set_strip (import_dialog.py:2167) applies an unselected 'background-color: AMBER_TINT;' stylesheet to the strip, which Qt also applies to the strip's QToolTip (via _q_stylesheet_parent). So the duplicate-text tooltip is drawn on the same #FFF8E1 as the strip (default tooltip #ffffdc), blends in, and reads as 'no tooltip'."
fix: (not applied - goal find_root_cause_only)
verification: (n/a)
files_changed: []
secondary_finding: "A single-reason tooltip is html.escape()d but contains no tag, so Qt.mightBeRichText is False. It renders as plain text and shows entities literally (&amp;, &#x27;, &lt;). With 2+ reasons the '<br>' makes it rich and the entities decode. Any rewrite of the tooltip should force rich text (e.g. wrap in <p>...</p>)."
fix_direction: "Recommended: strip-wide hint. In _render_strip append a hint line to the existing reason list (keeps the E11/overflow contract and test_strip_caps_three_lines_with_tooltip), force rich text, and scope the strip stylesheet with an object name (e.g. setObjectName('installStrip'); 'QLabel#installStrip { background-color: ... }') so the QToolTip ('qtooltip_label') keeps the normal tooltip look. Optional: a per-link hint via linkHovered(href) -> remembered href plus an eventFilter on QEvent.ToolTip that shows a target-specific hint (conflict -> Overwrite/Rename/Skip buttons, rename -> name field, plan -> preview) and falls back to the full list. QLabel has no public anchorAt, the widget-level ToolTip event would otherwise override a linkHovered-shown tip, and this means more state and tests for little gain on a strip of at most 3 lines. Update 05-UI-SPEC E11 copy accordingly."
