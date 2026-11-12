---
status: inconclusive
trigger: "UAT gap G-12-27 (Phase 12, test 27): User Guide reopens on the page 4.4 Importing Parts instead of the section 4.4.7 Conflicts last chosen"
created: 2026-11-10T17:38:00Z
updated: 2026-11-10T18:15:00Z
goal: find_root_cause_only
---

## Current Focus

bug_class: Bohrbug in code paths (deterministic), but the reported page-row result is NOT reproducible from the reported steps; two input-dependent defects confirmed (D1, D3)
hypothesis: |
  The reported picture (page row 4.4 current + page top shown, settings still importing#conflicts) can only come from a QUIET
  move to the page row, i.e. show_topic('importing') via (a) show_remembered's page fallback (needs show_topic(saved) False,
  eliminated) or (b) MainWindow.show_guide('importing') from the import window's Help/F1; or from a non-quiet click on 4.4
  whose save was later overwritten; or the owner read a hovered/scrolled guide as "4.4" (windows11 style: selection and
  hover look alike; D1 leaves the page top in view on a reused guide the owner scrolled).
test: run scratchpad/probe/guide_trace.py (real app + real settings, run by the owner) through test 27 steps 1, 2 and 4; read guide_trace.log
expecting: the log shows which call made 'importing' current (show_topic('importing') from show_guide/show_remembered with a stack, or a TOC MouseButtonPress on row=importing), and the BROWSER scroll value at each show
next_action: owner runs C:\Users\sylvain\AppData\Local\Temp\claude\258e6a257498df82\1c63b19d-e7f0-4611-9982-ec8610123914\scratchpad\probe\guide_trace.py from the repo root with env\Scripts\python.exe, repeats test 27 steps 1-2 and the restart + F1, takes a screenshot of the guide at each check, and returns guide_trace.log (beside the script)

reasoning_checkpoint:
  hypothesis: "not confirmed - see INCONCLUSIVE"
  confirming_evidence:
    - "D1 confirmed on real platform: reused hidden guide, owner scrolls page after choosing Conflicts, Close + F1 -> Conflicts still selected but page stays at its top (heading '4.4 Importing Parts')"
    - "D3 confirmed on real platform: held click on 4.4 while a page above with sections is open selects and saves 4.4.1/4.4.2/4.4.3 instead"
  falsification_test: "guide_trace.log from the owner's real run showing show_topic('importing#conflicts') -> True with current_after=importing#conflicts and a SNAPSHOT 400 ms after show with current=importing#conflicts would prove the code restored the section and the report is a perception/rendering issue"
  blind_spots: "Real OS mouse input not driven (QTest window-system events used; real SendInput would hit the owner's other windows); the owner's exact unreported actions between steps; whether the owner's 'restart' really started a single fresh process"
  candidate_causes:
    - "code: show_remembered/show_topic never re-scroll an already-current section (D1); _sync_expansion runs under a held mouse button (D3)"
    - "environment/input: windows11 style draws hover and selection alike, accent bar at the tree's far-left edge"
    - "data/sequence: an unreported import-window Help (show_guide('importing')) or a second app instance"
  and_gate: "yes - the page-top half needs D1 plus an owner scroll (or a quiet show_topic('importing')); the page-row half needs a quiet move or a misread highlight"

## Symptoms

expected: (UAT test 27, plan 12-19) F1, click "4.4 Importing Parts", then its section "4.4.7 Conflicts"; close the guide with Close; F1 again -> guide opens on Conflicts: 4.4.7 Conflicts selected in the left menu, Importing Parts opened out, other pages folded, Conflicts heading in view. Also after closing the app and starting it again.
actual: owner verbatim "No by default it is selecting 4.4 Importing Parts". After an app restart + F1: "No it still open at 4.4". Left menu highlighted row = "4.4" (Importing Parts, the page row), right side top heading = "4.4" (top of the Importing Parts page).
errors: none reported.
reproduction: Test 27 in .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-UAT.md. Windows 11, 100% display scale, real desktop, app started with env\Scripts\python.exe kicad_lib_manager.py from repo root (branch feature/part-importer).
started: discovered during UAT 2026-11-10, re-check of G-12-23 after plan 12-19 (and 12-18 shared guide).

## Eliminated

- hypothesis: "The section is not saved, or a different key is saved"
  evidence: "Real settings.ini holds importing#conflicts; probes save it on the Conflicts click (trace: SAVE help/last_topic <- 'importing#conflicts')"
  timestamp: 2026-11-10T17:45Z

- hypothesis: "show_topic('importing#conflicts') fails, so show_remembered falls back to the page"
  evidence: "Fresh and reused guide, real platform, scratch copy of the owner's settings.ini: show_topic -> True, current_after=importing#conflicts (tracer self-test and app_probe)"
  timestamp: 2026-11-10T17:58Z

- hypothesis: "Reopen of the reused hidden guide lands on the page (orchestrator's UAT note)"
  evidence: "Full MainWindow probe, real platform, human-like clicks, 7 different starting places: every Close + F1 ends on importing#conflicts with the Conflicts heading on top"
  timestamp: 2026-11-10T17:55Z

- hypothesis: "Fresh guide's pre-show anchor scroll lands short at 100% (orchestrator's offscreen finding)"
  evidence: "QTextEdit defers scrollToAnchor to its own showEvent; on the real platform the guide keeps 860 px width (Full HD 100% and 200%) so scroll 2297 == heading top 2297. Lands short only when HelpDialog.showEvent's fit_window narrows the width AFTER the browser's showEvent (offscreen 800 px screen: 3720 vs 4132, heading still in view)"
  timestamp: 2026-11-10T18:08Z

- hypothesis: "Owner ran stale or other code / other interpreter"
  evidence: "On-disk files == HEAD blobs; pyc headers match sources; .venv has no PySide6; the terminal uses env"
  timestamp: 2026-11-10T17:45Z

- hypothesis: "Real main-window content, geometry or saved scan changes the guide"
  evidence: "Restart probe with the real repo, the real saved scan and the owner's settings copy shows importing#conflicts with the heading on top"
  timestamp: 2026-11-10T18:00Z

## Evidence

- timestamp: 2026-11-10 (from orchestrator)
  checked: "%APPDATA%/KiCadExtLibManager/settings.ini and settings.load_help_topic()"
  found: "[help] last_topic=importing#conflicts before and after the failing restart; load_help_topic() returns 'importing#conflicts'"
  implication: "Saving works; the failing open did not overwrite the key. Fault is on the restore/display side."

- timestamp: 2026-11-10 (from orchestrator)
  checked: "offscreen probe, load_help_topic patched to 'importing#conflicts'"
  found: "HelpDialog() currentItem key 'importing#conflicts' before and after show(); browser scroll 3720 of 6665 vs scrollToAnchor('conflicts') after layout = 4132"
  implication: "Anchor scroll in __init__ before show uses pre-show layout and lands short of the heading"

- timestamp: 2026-11-10 (from orchestrator)
  checked: "offscreen probe: reused guide, scroll set to 0, close(), show_remembered(), show()"
  found: "scroll stays 0; show_topic on already-current item emits no currentItemChanged so _on_topic_selected (scrollToAnchor) never runs"
  implication: "Reused guide shows the page top, not the section heading"

- timestamp: 2026-11-10 (from orchestrator)
  checked: "real windows-platform probe, same patch"
  found: "currentItem and selectedItems both 'importing#conflicts' after show + 1.5 s events; scroll 2297"
  implication: "Left-menu highlight on the page row not reproduced in isolation; full app path / click sequence not yet covered"

- timestamp: 2026-11-10T17:40Z
  checked: "scratchpad/probe/app_probe.py: full MainWindow (scan/sync/kicad_running patched, QSettings redirected to scratch), real 'windows' platform, saved='generating', human-like clicks (press, 120 ms event loop, 1 px move, release) on 4.4 then 4.4.7, Close button click, help action trigger"
  found: "first F1: generating. After click on 4.4 Importing Parts: current=importing#start (NOT importing) - the singleShot _sync_expansion fired under the held button, folded 4.3's one section, rows moved up one, and the 1 px move selected the row now under the cursor. After click on Conflicts: current=importing#conflicts, scroll 2297 = conflicts_top 2296.8. After Close + F1: current=importing#conflicts, selected=[importing#conflicts], expanded=[importing], scroll 2297 (Conflicts heading at top). Focus on the Close button after reopen."
  implication: "Reuse path (show_remembered on a hidden guide) works with these inputs on the real platform. Separate finding: a held click on a page row below an open page lands on another row (row shift under the pressed mouse)."

- timestamp: 2026-11-10T17:42Z
  checked: "Same probe, restart scenario, (a) saved='importing#conflicts', (b) a scratch COPY of the owner's real settings.ini (window geometry, [help] last_topic=importing#conflicts); real file mtime unchanged (17:32:27)"
  found: "Both: first F1 -> current=importing#conflicts, selected=[importing#conflicts], expanded=[importing], scroll 2297 = conflicts_top; screenshot shows 4.4.7 Conflicts selected and its heading at the top. On the real platform the conflicts heading top is 2296.8, so the orchestrator's real-platform scroll 2297 WAS the heading (only offscreen lands short)."
  implication: "Restart path with the owner's exact settings and the on-disk code does not reproduce on this machine. The pre-show anchor scroll fault is offscreen-only (QTextBrowser.scrollToAnchor defers to a pending anchor while hidden on the real platform)."

- timestamp: 2026-11-10T17:45Z
  checked: "git hash-object vs HEAD for help_dialog.py, main_window.py, settings.py, import_dialog.py; pyc headers"
  found: "On-disk files equal HEAD 7da9a1f; pyc headers record the current source mtime/size (Nov 4 18:11:26), so the owner's runs used this code."
  implication: "Not a stale-code problem."

- timestamp: 2026-11-10T17:46Z
  checked: "All callers of show_topic/show_remembered/HelpDialog()"
  found: "Quiet moves (not saved): HelpDialog.__init__ (show_remembered or topic), show_remembered fallback to the page (show_topic(saved.partition('#')[0])), MainWindow.show_guide(topic) used only by ImportDialog._on_help with 'importing'. Any non-quiet move to the page row would have saved 'importing'."
  implication: "Because settings.ini kept importing#conflicts, the move to the page row 4.4 was a QUIET move: either show_topic(saved) failed and the page fallback ran, or show_guide('importing') ran (import window Help/F1). Both give exactly the reported picture: page row 4.4 selected + setHtml -> page top."

- timestamp: 2026-11-10T17:55Z
  checked: "Reuse probe on the real platform with human-like clicks for initial saved places none, importing, importing#conflicts, library_tree, kicad_detection, restoring, filter"
  found: "Every run ends with current=importing#conflicts, selected=[importing#conflicts], expanded=[importing], scroll=2297 (Conflicts heading on top) after Close + F1. Row-shift side effect seen whenever the open page sits above 4.4 and has sections: library_tree -> click on 4.4 lands on 4.4.2 Items, kicad_detection -> 4.4.3 Target library, generating -> 4.4.1 Start (saved too). None of them ends on the page row 4.4."
  implication: "With the reported click sequence the final Conflicts click always wins, and show_remembered re-applies it on reopen. No realistic Qt-level input reproduces the page row."

- timestamp: 2026-11-10T18:00Z
  checked: "Restart probe with the owner's real repo and real saved scan (scan_cache/50a91c459fbab034.json copied into scratch), real settings copy, sync/kicad_running patched; real files' mtimes unchanged afterwards"
  found: "first F1 -> current=importing#conflicts, scroll 2297 (Conflicts heading on top)."
  implication: "Main-window content, geometry and saved settings are not the hidden variable."

- timestamp: 2026-11-10T18:02Z
  checked: "hover_probe.py: guide with saved=importing#conflicts, mouse resting on the 4.4 row, windows11 style"
  found: "Style is 'windows11'. The selected row 4.4.7 gets a faint grey fill plus a 3 px accent bar at the far-left edge of the tree; a hovered row (4.4) gets the same faint grey fill. Selection and hover are nearly indistinguishable."
  implication: "A hovered page row can read as 'selected'; weak, does not explain the right pane showing the page top."

- timestamp: 2026-11-10T18:03Z
  checked: ".venv (uv) and env interpreters"
  found: ".venv has no PySide6 (empty, Python 3.13); owner's terminal uses env (PySide6 6.12.0)."
  implication: "Not an interpreter mix-up."

- timestamp: 2026-11-10T18:05Z
  checked: "app_probe.py reuse with SCROLL_TOP_BEFORE_CLOSE=1 (owner scrolls the page to the top after choosing Conflicts), real platform"
  found: "After Close + F1: current=importing#conflicts, selected=[importing#conflicts], scroll=0, top heading '4.4 Importing Parts'. show_remembered -> show_topic on the already-current item emits no currentItemChanged, so _on_topic_selected (scrollToAnchor) never runs; _on_item_clicked only covers a click."
  implication: "D1 confirmed: the remembered section's heading is not brought back into view on a reused guide; the page shows wherever it was left. Gives the 'top of 4.4' half of the report if the page was scrolled up before Close."

- timestamp: 2026-11-10T18:06Z
  checked: "guide_trace.py self-test (trace_selftest.py, scratch settings): event-level trace of a held click on 4.4 with 'generating' open"
  found: "Press at +2.624 s on row=importing -> _on_topic_selected('importing') -> SAVE 'importing'; at +2.683 s, button still held, 'TOC collapsed generating' / 'TOC expanded importing' (the QTimer.singleShot(0) _sync_expansion); held 1 px move at +2.823 s row=importing#start -> selection and current move -> SAVE 'importing#start'."
  implication: "D3 confirmed: the singleShot does not wait for the release; a real press spans event-loop turns, so folding rows under the held button moves the selection to another row and saves it. tests use QTest.mouseClick (press+release with no event loop between), so they never see it."

- timestamp: 2026-11-10T18:10Z
  checked: "tests/test_help_dialog.py persistence/scroll subset (13 tests, offscreen)"
  found: "13 passed; real settings.ini mtime unchanged (17:32:27)"
  implication: "Suite green; it does not model held presses (D3) or a reused guide scrolled away from its section (D1)."

## Resolution

root_cause: "INCONCLUSIVE for the page-row half. Confirmed defects: D1 show_remembered/show_topic do not re-scroll an already-current section on a reused guide (help_dialog.py:640-658, main_window.py:1367-1368); D3 _sync_expansion (singleShot 0, help_dialog.py:697-698) runs while the mouse button is still held, so a click on a page row selects and saves a different row. D2 (narrowing fit_window after QTextEdit's deferred anchor scroll) only matters on narrow screens."
fix:
verification:
files_changed: []
