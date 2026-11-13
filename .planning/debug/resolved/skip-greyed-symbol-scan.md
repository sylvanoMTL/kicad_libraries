---
status: resolved
trigger: "G-13-1-b: the skip button is grayed out I guess for the symbol scanning, This should not be grayed out. user can skip that stage."
created: 2026-11-12T18:00:00Z
updated: 2026-11-13T14:45:00Z
goal: find_root_cause_only
gap_id: G-13-1-b
---

## Current Focus

hypothesis: CONFIRMED - Skip is greyed during the symbol stage by design. ScanProgressDialog enables Skip only on set_skippable(source), driven solely by checking(source) from _check_model_files (the 3D model path check); find_symbol_libs (and the saved-scan check, listing, cross-reference, atomic and change stages) never report a skippable source. Plan 12-17 (owner decision 2026-11-04) scoped Skip to the 3D check and pinned "disabled before and after that check". It is noticeable on the owner's checkout because the pre-3D stages take about 9 s there (symbol parse 6 s), and the owner wants to cut the WE work as soon as the window opens.
test: done - code reading, stage profile on the worktree and the main checkout, offscreen GUI timeline with the real ScanWorker and ScanProgressDialog
expecting: n/a
next_action: return ROOT CAUSE FOUND (goal find_root_cause_only)
bug_class: Bohrbug (deterministic; design-scope gap whose visible duration depends on the file cache)
reasoning_checkpoint:
  hypothesis: "Skip is disabled while 'Parsing symbol' shows because scan_all passes skip/checking only to _check_model_files, so no checking(source) reaches ScanProgressDialog.set_skippable before the 3D model path check starts"
  confirming_evidence:
    - "library_scanner.scan_all 670-733: find_symbol_libs(repo_root, banded(1, 10)) gets only progress; skip= and checking= go only to _check_model_files"
    - "Offscreen run of the real ScanWorker + ScanProgressDialog: 'Parsing symbol: ...' with Skip disabled at t=1 s, 'Skip WurthElektronik' enabled at t=2 s once the 3D check began; GUI backlog 0-2 events (no signal lag)"
  falsification_test: "If checking(source) were emitted during find_symbol_libs, or the GUI lagged the worker, the window would show an enabled Skip or a stale symbol label during the 3D check - neither observed"
  fix_rationale: "Enabling Skip earlier, as a pre-registered skip of that source's 3D model path check (ScanWorker's sticky set already honours it), meets the owner's intent without dropping symbol links; skipping the symbol parse itself would let Generate Tables remove entries"
  blind_spots: "Not measured on a truly cold cache or with antivirus first-read in the owner's own session; the owner's 40-100 s figure is not reproduced for the symbol stage (0.76 s warm worktree, 6.05 s main checkout) - it matches the WE 3D check (76-99 s cold-ish, 11.5 s warm)"
  candidate_causes:
    - "code/design: skip hook scoped to _check_model_files (plan 12-17, owner decision 2026-11-04)"
    - "environment: file-cache / antivirus state makes the pre-3D stages about 9 s on the main checkout versus about 2 s warm"
    - "data: the main checkout's WE submodule is newer and bigger (412 .kicad_sym incl. a 12.9 MB file, 7612 .kicad_mod) than the worktree's (403 / 5666)"
  and_gate: "yes - the greyed state alone is by design; it becomes a reported problem only when the pre-3D stages last long enough to notice and the owner wants to skip WE before its 3D check starts"

## Symptoms

expected: The owner expects to be able to skip long stages of the full scan (the symbol library scan over ~410 libraries, mostly WurthElektronik, takes 40-100 s on their machine) the way they can skip a source's 3D model path check.
actual: User reported: "the skip button is grayed out I guess for the symbol scanning, This should not be grayed out. user can skip that stage."
errors: None reported.
reproduction: Test 1 in UAT. Start the app when a full scan is required (e.g. after a Custom commit, or when the saved scan was made by another app version); during "Scanning repository..." the Skip button in the Loading Libraries window is disabled; it enables only once the 3D model path check starts.
started: Discovered during UAT on 2026-11-12.

## Eliminated

- hypothesis: The GUI thread lags behind the worker (GIL contention / queued-signal backlog), so the window keeps showing the symbol label with Skip greyed long after the worker reached the 3D check
  evidence: offscreen timeline with the real ScanWorker/ScanProgressDialog - backlog 0-2 events; the window switched to an enabled 'Skip WurthElektronik' within about 1 s of the worker starting the 3D check
  timestamp: 2026-11-12T18:03:00Z

- hypothesis: The symbol stage itself is the 40-100 s part, so making the symbol parse faster is the main remedy
  evidence: symbol parse measured 0.76 s (worktree, warm) and 6.05 s (main checkout); the WE 3D model path check is 76-99 s cold-ish and 11.5 s warm - the long stage is the already-skippable one; the parse is already one regex pass over the file text
  timestamp: 2026-11-12T18:05:00Z

## Evidence

- timestamp: 2026-11-12T17:50:00Z
  checked: kicad_lib_manager/widgets/scan_progress.py (ScanProgressDialog)
  found: Skip button starts disabled via _show_idle() (tooltip "Skip is offered while the 3D model paths of a library source are checked."); only set_skippable(source) with a non-None source enables it, labelled "Skip <source>"; skip_requested(str) emits the source name
  implication: the dialog itself has no notion of a symbol stage; enabling is entirely driven by the caller

- timestamp: 2026-11-12T17:51:00Z
  checked: kicad_lib_manager/main_window.py ScanWorker (lines 94-173) and _start_scan/_on_scan_checking/_on_skip_requested (583-645)
  found: ScanWorker.checking Signal is connected to _on_scan_checking -> ScanProgressDialog.set_skippable; ScanWorker passes skip=self._skip_requested and checking=self.checking.emit to scan_all. request_skip adds the source to a lock-protected set
  implication: the skip plumbing is per-source and generic (a set of source names), but its meaning is fixed by where scan_all calls checking()/skip()

- timestamp: 2026-11-12T17:52:00Z
  checked: kicad_lib_manager/library_scanner.py scan_all (670-733), find_symbol_libs (429-444), _check_model_files (554-615)
  found: scan_all stages = find_footprint_libs (bar 0-1) -> find_symbol_libs (bar 1-10, label "Parsing symbol: <stem>") -> find_nickname_collisions + cross_reference ("Cross-referencing...", 10) -> _collect_files(*.kicad_mod) + _custom_model_names -> _check_model_files (bar 10-92, "Checking 3D paths: <stem>") -> check_libraries ("Checking atomic parts...", 92) -> mark_changes ("Looking for changed parts...", 96). checking/skip are passed ONLY to _check_model_files; find_symbol_libs takes only progress. checking(None) is emitted at the end of the 3D check, so Skip is also disabled during atomic check and change marking. Docstring: "A skip never drops a library or a footprint link." Comment: "Measured on the full repo (about 70 s): listing 0.25 s, symbol links 6 s, the 3D model path check 63 s"
  implication: CONFIRMS mechanism - Skip is greyed during the symbol stage because that stage never calls checking(source) and never asks skip(source); this is the designed G-12-21 scope (3D model path check only), not a regression

- timestamp: 2026-11-12T17:53:00Z
  checked: scan_cache.py load_fresh/fingerprint/_walk; ScanWorker.run before scan_all
  found: before scan_all the worker runs scan_cache.load_fresh (reuse_cache) or scan_cache.fingerprint: an os.scandir stat walk of the whole repo (minus SKIP_DIRS) over .kicad_sym/.kicad_mod/Custom/3DModels files, label "Checking for library changes..." at 0%; also not skippable
  implication: another pre-symbol stage the owner may perceive as part of "Scanning repository..."

- timestamp: 2026-11-12T17:56:00Z
  checked: stage-by-stage profile of scan_all on the worktree repo (scratchpad prof_scan.py; 403 .kicad_sym = 14 Custom + 389 WurthElektronik, 15.5 MB; 5666 .kicad_mod), Python 3.14, warm file cache, no GUI
  found: scan_cache.fingerprint 0.09 s; find_footprint_libs 0.29 s; collect *.kicad_sym 0.32 s; symbol footprint-link parse 0.76 s total (Custom 0.01 s, WurthElektronik 0.67 s; slowest file 0.033 s for a 5.1 MB WE library); collisions 0.00 s; cross_reference 0.03 s; collect *.kicad_mod 0.43 s; _check_model_files Custom (17 files) 0.19 s; _check_model_files WurthElektronik (5645 files) 75.96 s; check_libraries 0.01 s; mark_changes 0.12 s. Wall 79 s
  implication: the symbol stage is ~1-2 s of a ~79 s scan (the 12-16 plan measured 6 s); ~96% of the time is the WE 3D model path check, which IS skippable. The symbol parse itself is a regex over the file text - already the cheap path; making it faster has little to gain

- timestamp: 2026-11-12T17:58:00Z
  checked: main checkout C:/Git_Repo_Clones/Kicad_Libraries (read-only): env/pyvenv.cfg and diff of library_scanner.py, main_window.py, scan_cache.py, widgets/scan_progress.py against the worktree
  found: owner's checkout runs Python 3.11.3; the four scan files are identical to the worktree's (main at c6920f5 on top of merge 610df43 + 3dc3081); Custom/Symbols there holds 10 Atomic_ libraries
  implication: the owner ran the same scan code; any difference in what they saw is timing/environment (Python 3.11, file cache, Defender), not code

- timestamp: 2026-11-12T18:00:00Z
  checked: table_generator._merge_table (lines 207-230) and LibraryTableWidget._sync_footprint_selection (library_table.py 432-460), MainWindow._select_linked_footprints
  found: Generate Tables treats every managed entry whose rel_path is not in the scanned libs as stale and REMOVES it ("removed stale entry ... that library no longer exists in the repo"); footprint selection per source is computed only from the selected symbols' footprint_refs, and any symbol check change in a source recomputes (and unchecks) all of that source's footprint libraries
  implication: a symbol-stage skip that drops a source's SymbolLibrary entries would make Generate Tables delete that source's sym-lib-table entries; one that lists them with empty footprint_refs would make the next symbol click in that source uncheck all its footprint libraries, and Generate Tables would then remove them as deselected. Either breaks the CLAUDE.md contract "its libraries are still listed and Generate Tables keeps them" and the scan_all docstring "A skip never drops a library or a footprint link"

- timestamp: 2026-11-12T18:03:00Z
  checked: offscreen run of the real main_window.ScanWorker + ScanProgressDialog on the worktree (scratchpad gui_lag2.py; cache_file=None so nothing written; scan_all wrapped in plain Python to time worker-side reports; a 1 s QTimer sampling the window)
  found: t=1.0 s window 'Parsing symbol: Inductor_Wurth_WE-LPCC', button 'Skip' disabled (worker at the same file, backlog 1); t=2.0 s 'Checking 3D paths: ...', button 'Skip WurthElektronik' enabled; enabled through t=13 s; 'Done' and finished at 13.56 s with 'Skip' disabled. GUI backlog stayed 0-2 events. Warm 3D check this run took about 11.5 s against 76 s in the first profile, so file-cache / antivirus state dominates that stage. Harness-only artefact: app.quit() is refused because ScanProgressDialog.reject ignores close until finish()
  implication: no GUI/GIL signal lag; the greyed window is exactly the pre-3D stages; once the 3D check starts Skip works as designed

- timestamp: 2026-11-12T18:05:00Z
  checked: stage profile on the owner's main checkout data (C:/Git_Repo_Clones/Kicad_Libraries, read-only, worktree code run with -B; scratchpad prof_scan2.py)
  found: fingerprint 0.74 s; find_footprint_libs 0.84 s; collect *.kicad_sym 0.48 s (412 files); symbol parse 6.05 s (Custom 0.10 s, WurthElektronik 5.86 s; slowest 0.082 s for the 12.88 MB WR-TBL file); cross_reference 0.02 s; collect *.kicad_mod 0.95 s; 3D check Custom (18 files) 0.23 s; 3D check WurthElektronik (7612 files) 99.26 s; check_libraries 0.17 s; mark_changes 0.18 s
  implication: on the owner's checkout Skip stays greyed about 9 s (saved-scan check + listing + 6 s symbol parse + footprint-file listing) while 'Parsing symbol: ...' runs; the expensive ~100 s WE 3D check is already skippable once reached. The owner's 40-100 s matches the 3D check, not the symbol stage

- timestamp: 2026-11-12T18:05:30Z
  checked: %APPDATA%/KiCadExtLibManager/scan_cache metadata (read-only peek)
  found: worktree saved scan 2026-11-12T15:36 has skipped_sources ['WurthElektronik']; main checkout saved scan 2026-11-12T17:32 has skipped_sources []
  implication: the owner does use Skip WurthElektronik once it is offered; the last main-checkout scan ran without a skip

- timestamp: 2026-11-12T18:06:00Z
  checked: 12-UAT.md G-12-21, 12-17-PLAN.md, tests/test_main_window.py 1454-1660, help_dialog.py 154-158, scan_progress.py _show_idle tooltip
  found: owner decision 2026-11-04 - "the skip unit is the source ... skipping only its 3D model path check"; 12-17 truth - "before and after that check it reads 'Skip' and is disabled"; G-12-21 required symbol footprint links "still read (never dropped or emptied, so Generate Tables removes nothing and pre-select / footprint auto-select keep working)"; threat T-12-44 (high) - a skip dropping libraries makes Generate Tables remove WE entries. Pinned by test_scan_progress_dialog_skip_button_follows_the_source (a new dialog shows a disabled 'Skip'), test_loading_dialog_skips_the_source_being_checked, test_a_skip_click_after_the_check_ended_logs_no_skip and test_generate_after_a_skip_removes_no_entry, which already runs the real scan_all with skip=lambda s: s == 'WurthElektronik' true from the very start (an early request is honoured by the 3D check). Help 'Repository Scan' and CLAUDE.md say Skip appears during the 3D model path check
  implication: the greyed symbol stage is specified behaviour, not a regression; the backend (ScanWorker._skip_sources, a sticky per-source set asked per file by _check_model_files) already honours a request made before the 3D check starts - only the dialog's enabled state gates it

## Resolution

root_cause: "Design-scope gap, not a code regression. ScanProgressDialog enables Skip only when set_skippable(source) receives a non-None source, and its only producer is checking(source), which scan_all passes solely to _check_model_files (the 3D model path check). find_symbol_libs and every other stage (saved-scan check, listing, cross-reference, atomic check, change marking) take only a progress callback, so the button stays 'Skip' and disabled until the 3D check starts. This follows plan 12-17 (owner decision 2026-11-04: the skip unit is the source, skipping only its 3D model path check) and is pinned by tests. It shows on the owner's checkout because the pre-3D stages take about 9 s there (symbol parse 6 s over 412 files incl. a 12.9 MB WE library), and the owner wants to cut WurthElektronik's work then; the long stage (about 100 s WE 3D check) is already skippable once reached. A request made earlier would already be honoured by the backend (ScanWorker keeps a sticky per-source set that _check_model_files asks before each source's files)."
fix: "Plan 13-24 (G-13-1-b): Skip is offered while the symbols are read; an early click skips only that source's 3D model path check once it starts."
verification: "Phase 13 re-test UAT 5/5 passed 2026-11-13."
files_changed: []

Resolved at the v2.0 milestone close (2026-11-13) against the plan that fixed it.
