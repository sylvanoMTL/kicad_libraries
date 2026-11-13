---
status: testing
phase: 13-atomic-migration-and-kicad-setup
source: [13-VERIFICATION.md]
started: 2026-11-13T11:14:42Z
updated: 2026-11-13T11:14:42Z
---

Re-test round after gap closure 13-23..13-28. The previous round (live migration UAT, gaps G-13-1-a..h, status diagnosed) is in git at commit b7c5c05.

Where to run: merge `feature/part-importer` into the main checkout `C:/Git_Repo_Clones/Kicad_Libraries` first (the folder KiCad reads, D-26), then run every test there with its own venv: `.\env\Scripts\python.exe kicad_lib_manager.py` (Python 3.11).

## Current Test

number: 1
name: The app starts on the main checkout's Python 3.11 venv (G-13-1-a)
expected: |
  `.\env\Scripts\python.exe kicad_lib_manager.py` from C:/Git_Repo_Clones/Kicad_Libraries opens the main window with no NameError.
awaiting: user response

## Tests

### 1. The app starts on the main checkout's Python 3.11 venv (G-13-1-a)
expected: `.\env\Scripts\python.exe kicad_lib_manager.py` from C:/Git_Repo_Clones/Kicad_Libraries opens the main window with no NameError.
result: [pending]

### 2. Skip is offered while the symbols are read (G-13-1-b)
expected: Press Rescan. While the Loading Libraries window reads "Parsing symbol: ...", the button already reads "Skip WurthElektronik" and is enabled. Press it: it shows "Skipping WurthElektronik...", the scan finishes, the log has one line saying the 3D model paths of WurthElektronik were skipped, and the library tree still lists the WurthElektronik libraries.
result: [pending]

### 3. The pin action is named "Pin Atomic Libraries in KiCad..." (G-13-1-c)
expected: The File menu shows "Pin Atomic Libraries in KiCad..." with Ctrl+Shift+K and the new tooltip; Help > User Guide > Generating has the "Pin Atomic libraries in KiCad" section.
result: [pending]

### 4. A deleted Destination folder is no longer offered (G-13-1-g)
expected: Browse... to a new empty throwaway folder as Destination, close the app, delete that folder, start the app again: the Destination box no longer offers it. (The Result view's Destination row, Browse... and the Generate outcome line are covered by automated tests, since there is nothing left to migrate on the real Custom/.)
result: [pending]

### 5. ICM-42688-P is in the right library after the earlier live migration (G-13-1-f follow-up)
expected: The 2026-11-12 live migration filed ICM-42688-P into `Atomic_Timer`, before the 13-25 fix; no gap plan moves already-migrated data. In the main checkout's `Custom/`, the part is in `Atomic_Sensor_Motion` (move it with the KiCad Symbol Editor and commit in `Custom` if it is still in `Atomic_Timer`).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
