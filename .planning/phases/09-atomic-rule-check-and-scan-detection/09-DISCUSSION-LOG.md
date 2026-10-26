# Phase 9: Atomic Rule Check and Scan Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-26
**Phase:** 09-atomic-rule-check-and-scan-detection
**Areas discussed:** Tree marks & highlights, Manufacturer table, Check dialog & fixes, Rule edge cases

---

## Tree marks & highlights

| Option | Description | Selected |
|--------|-------------|----------|
| Symbol rows | Atomic_ libraries get one child row per symbol (no checkbox); failing = icon + amber; library shows "N of M fail" | ✓ |
| Library row only | Library row amber, tooltip lists symbol: rule | |
| Symbol rows for all | Child rows for every library incl. Würth | |

| Option | Description | Selected |
|--------|-------------|----------|
| All Custom libraries | Changed highlight on any Custom/ library; rows only where something to show | ✓ |
| Atomic_ libraries only | Highlight only where the check runs | |

| Option | Description | Selected |
|--------|-------------|----------|
| Separate markers | Failing = icon + amber; changed = accent + New/Changed; both combined | ✓ |
| Status text only | Word only, no colour | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Symbols only | Footprint tree unchanged | |
| Also highlight changed footprints | Footprint child rows for changed .kicad_mod files | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Every line, plus a summary | One line per (symbol, rule) + summary | ✓ |
| One line per symbol | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Expand only with problems | Auto-expand libraries with failing/changed items | ✓ |
| Always collapsed | | |
| Always expanded | | |

**Notes:** The tree has library rows only today, and no Atomic_ library exists yet, which is why the highlight covers all Custom libraries.

---

## Manufacturer table

| Option | Description | Selected |
|--------|-------------|----------|
| Full company name | Texas Instruments, Global Connector Technology, … ; short forms are aliases | ✓ |
| Short common name | TI, GCT, ADI | |
| Brand as marketed | Per company | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep the original brand | Maxim Integrated / Linear Technology stay as on datasheet | ✓ |
| Map to the current owner | Fold into Analog Devices / TDK | |

| Option | Description | Selected |
|--------|-------------|----------|
| Python module | Qt-free module, canonical → aliases; suggest.py map folded in | ✓ |
| Data file in the repo | JSON/TOML | |
| Editable in the app | From the check dialog | |

| Option | Description | Selected |
|--------|-------------|----------|
| Pass, with an info note | Unknown name passes, INFO note | ✓ |
| Fail until added | | |
| Silent pass | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Folded match | Ignore case, spaces, punctuation, corporate suffixes | ✓ |
| Exact alias list | | |

---

## Check dialog & fixes

| Option | Description | Selected |
|--------|-------------|----------|
| Menu + double-click | Menu item with shortcut + double-click marked row | ✓ |
| Menu only | | |
| Auto after scan | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tick, preview, apply | Ticked rows, one preview, one write + backup per file, rescan | ✓ |
| One button per fix | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Merge, show the conflict | Merge agreeing aliases into one canonical property; conflict = user picks | ✓ |
| Rename only | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Pick a file, it gets linked | Copy into Custom/3DModels with intake checks, link in footprint | ✓ |
| Report only | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Warn in the preview, allow | kicad_running() warning + re-read before write | ✓ |
| Refuse while KiCad runs | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Must look like a URL or file | http(s), ${VAR}/path or absolute path; not fetched | ✓ |
| Any non-empty text | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same test | Rule uses the same URL-or-file definition | ✓ |
| No, rule stays 'not empty or ~' | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Listed as cleanup, not a failure | Leftovers shown, fix ticked by default, not blocking | ✓ |
| Treat as a failure | | |

---

## Rule edge cases

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve in KiCad's install | Expand KICADn_3DMODEL_DIR to the installed 3dmodels folder; fail if not found | ✓ |
| Trust official footprints | | |
| Fail → warn when KiCad absent | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Content, not formatting | Token compare against Custom HEAD | ✓ |
| Any byte in the block | | |
| Whole file | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Repo or KiCad stock | Any repo or installed footprint library; fails on empty/missing/ambiguous | ✓ |
| Only Atomic_Footprints or KiCad stock | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Scratch copy of the repo | UAT helper builds throwaway repo with Atomic_ libraries from real parts | ✓ |
| Temporary rename in a Custom branch | | |
| Synthetic fixture only | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Own MPN + Value; rest inherited ok | Child needs its own MPN and Value = MPN; other fields may be inherited | ✓ |
| Every field its own | | |

---

## Claude's Discretion

- Module and class names, the check result data shape, how it attaches to ScanResult
- Running inside ScanWorker; batching git reads
- Git missing or Custom not a checkout: skip the highlight with an INFO line
- Shortcut key, dialog layout, rule reason wording
- Handling of .bak files

## Deferred Ideas

- Editing the manufacturer table in the app
- Restricting Footprint targets to Atomic_Footprints (Phase 10 / 13)
