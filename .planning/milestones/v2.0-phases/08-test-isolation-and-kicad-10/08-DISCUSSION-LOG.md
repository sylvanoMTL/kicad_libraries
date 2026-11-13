# Phase 8: Test Isolation and KiCad 10 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-25
**Phase:** 08-test-isolation-and-kicad-10
**Areas discussed:** Synthetic Custom/ fixture, KiCad version targeting, D-01 re-test on KiCad 10, Skips and regression guard

---

## Synthetic Custom/ fixture

**What should the isolated Custom/ that replaces the live copy contain?**

| Option | Description | Selected |
|--------|-------------|----------|
| Format mirror | Small tree built in code: one library per format (20211014, 20231120, 20241209, 20251024), a few footprints, stub models, UL part absent by design | ✓ |
| Per-test minimal tree | Each test builds only the libraries it needs | |
| Frozen snapshot of Custom/ | Commit a pre-eecac22 copy under tests/fixtures | |

**Should tests that only read the live Custom/ keep reading it?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep live read-only | Round-trip corpus etc. keep checking the real files; only writers and part-assuming tests move | ✓ |
| Move everything to fixture | No test touches the live Custom/ | |
| Live reads opt-in marker | Live reads behind a new marker | |

**Library names in the fixture?**

| Option | Description | Selected |
|--------|-------------|----------|
| Today's v1 names | Mirror the real names; Phase 10 adds Atomic_ libraries later | ✓ |
| Neutral test names | Lib_V6 / Lib_V8 / Lib_V9 / Lib_V10 | |
| Atomic_ names already | Build Atomic_ libraries now | |

**Where does the KiCad 10 (20251024) house style come from?**

| Option | Description | Selected |
|--------|-------------|----------|
| Copy real KiCad 10 output | Builder based on real kicad-cli 10 output, checked once and documented | ✓ |
| Reuse the 20241209 builder | Bump the version number only | |
| You decide | Leave it to the planner | |

---

## KiCad version targeting

**How do real kicad-cli tests know which output to expect?**

| Option | Description | Selected |
|--------|-------------|----------|
| Pin KiCad 10 exactly | Constants 20251024 / "10.0"; skip unless kicad-cli is major 10 | ✓ |
| Read it from the CLI, min 10 | Compare against whatever the CLI reports, ≥10 | |
| Both: constant + CLI check | Constant, and fail with "retarget" on a newer CLI | |

**What happens to KiCad 9 "normalised into 20241209" tests?**

| Option | Description | Selected |
|--------|-------------|----------|
| Retarget to KiCad 10 rows | Normalise into 20251024; 20241209 target becomes as-is-with-warning (VER-01) | ✓ |
| Retarget + keep 9 fakes | Also keep fake-runner variants of the KiCad 9 rows | |
| You decide | Leave it to the planner | |

**Bump fake-runner unit tests that use 20241209?**

| Option | Description | Selected |
|--------|-------------|----------|
| Leave them as they are | Version-generic logic, no process started | ✓ |
| Bump to 20251024 everywhere | Consistency | |

---

## D-01 re-test on KiCad 10

**How should backlog 999.1 be closed?**

| Option | Description | Selected |
|--------|-------------|----------|
| Automated + one KiCad check | Real-CLI test plus a manual Symbol Editor check in KiCad 10 | ✓ |
| Automated test only | Load gate stands in for KiCad | |
| Manual UAT only | Repeat Phase 4 UAT Test 2 by hand | |

**Where should the manual check install the part?**

| Option | Description | Selected |
|--------|-------------|----------|
| Scratch copy | Existing KICAD_IMPORT_UAT_DIR hook; real Custom/ untouched | ✓ |
| Real Custom/ via the app | Import through the GUI, discard with git | |

**Where should the outcome be recorded?**

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 8 UAT + close 999.1 | Phase 8 UAT, closing note on 04-UAT.md Test 2, PROJECT.md D-01 row updated | ✓ |
| Phase 8 UAT only | Leave the v1.0 archive untouched | |

---

## Skips and regression guard

**What should a green run mean for the 3 WurthElektronik skips?**

| Option | Description | Selected |
|--------|-------------|----------|
| Check it out in the worktree | `git submodule update --init` so the Würth tests run | ✓ |
| Accept as a documented skip | Keep the 3 skips as expected | |

**Where should the list of expected skips live?**

| Option | Description | Selected |
|--------|-------------|----------|
| tests/README.md table | Condition, why, how to enable | ✓ |
| Skip messages only | Rely on `-ra` output | |
| Update codebase/TESTING.md | Fold into the GSD codebase map | |

**What should stop a future test from depending on the live Custom/?**

| Option | Description | Selected |
|--------|-------------|----------|
| Write-protect guard | Session hash snapshot of live Custom/, fail if changed; remove custom_copy | ✓ |
| Convention only | Remove custom_copy, note the rule | |
| Snapshot + lint test | Guard plus a grep test with an allow-list | |

---

## Claude's Discretion

- Fixture shape, scope and name; how many symbols, footprints and models per library
- How the "kicad-cli is major 10" check is implemented, and centralising the three CLI-locating helpers
- Write-protect guard implementation (hash vs size+mtime with hash fallback)
- Whether to refresh the stale `.planning/codebase/TESTING.md`

## Deferred Ideas

None.
