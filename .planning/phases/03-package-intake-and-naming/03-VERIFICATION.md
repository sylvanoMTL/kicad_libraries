---
phase: 03-package-intake-and-naming
verified: 2026-10-19T18:00:00Z
status: gaps_found
score: 6/7 must-haves verified
covered_files:
  - ".planning/phases/03-package-intake-and-naming/03-01-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-01-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-02-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-02-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-03-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-03-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-04-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-04-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-05-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-05-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-06-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-06-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-07-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-07-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-08-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-08-SUMMARY.md"
  - ".planning/phases/03-package-intake-and-naming/03-09-PLAN.md"
  - ".planning/phases/03-package-intake-and-naming/03-09-SUMMARY.md"
  - "kicad_lib_manager/importer/adapters/base.py"
  - "kicad_lib_manager/importer/adapters/loose.py"
  - "kicad_lib_manager/importer/adapters/ultralibrarian.py"
  - "kicad_lib_manager/importer/candidate.py"
  - "kicad_lib_manager/importer/detect.py"
  - "kicad_lib_manager/importer/layout.py"
  - "kicad_lib_manager/importer/naming.py"
  - "kicad_lib_manager/importer/package.py"
  - "kicad_lib_manager/importer/suggest.py"
  - "kicad_lib_manager/kicad_files.py"
  - "kicad_lib_manager/sexpr.py"
covered_digest: "v3:sha256:72367656c4dc196c31aa808d9c1a33031fd8d2976b1ff00a69f55b368d12be72"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "CR-02: a damaged LZMA zip returns ERROR intake.corrupt and removes its staging folder; open_package never raises for expected input faults"
    - "CR-01 (token-dense input): a dense 3.8 MB symbol at 7:1 ratio is skipped with a WARNING at the 1,000,000-node ceiling"
  gaps_remaining:
    - "CR-01 (string-heavy input), tracked as CR-03: one ~8 MiB quoted string is not skipped and costs about 2.8 GiB"
  regressions: []
gaps:
  - truth: "CR-01 gap truth (03-08): a hostile low-ratio .kicad_sym inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM"
    status: partial
    reason: "Closed for token-dense input only. A .kicad_sym of 8,388,389 bytes whose Description is one random-text quoted string deflates 1.33:1, passes the 8 MiB cap, the ratio rule and the 1,000,000-node ceiling (a string counts as one node), and is parsed in full. Reproduced here: open_package refused=False, detect_candidate returned the symbol with no unreadable_file WARNING, 3.4 s, peak working set 2,772 MiB, peak commit 3,108 MiB. That is the 'gigabytes of RAM' outcome the truth says must not happen, from a file the caps were added to stop. The cause is the backtracking string pattern in sexpr.py line 9."
    artifacts:
      - path: "kicad_lib_manager/sexpr.py"
        issue: "_TOKEN str group `\"(?:[^\"\\\\]|\\\\.)*\"` keeps a backtrack entry per character, about 330x amplification of the input size"
      - path: "tests/test_locate_text_caps.py"
        issue: "_hostile_symbol builds list tokens only; no single-large-string hostile case, so the suite cannot see this class"
    missing:
      - "Replace the string alternation in sexpr._TOKEN with the unrolled linear form `\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\"` (keep re.S). I tried it in a scratch copy only: the same 8 MiB string parses in 0.06 s and 8 MiB traced, `\\\"` and `\\\\` escapes still match, an unterminated string still raises sexpr.unterminated"
      - "Add a regression test in tests/test_locate_text_caps.py: one multi-MiB random-text quoted string inside the byte and ratio caps, asserting it finishes well under a second or stays under a memory bound"
      - "Add tests/test_sexpr.py cases for escaped quote, escaped backslash and unterminated string with the new pattern; the Phase 1 round-trip corpus tests must still pass unchanged"
deferred: []
---

# Phase 3: Package Intake and Naming Verification Report

**Phase Goal:** Given a vendor zip or a folder of loose files, the importer safely finds the KiCad symbol, footprint and 3D model and proposes a sanitised, convention-following target library name, without writing anything into the repo
**Verified:** 2026-10-19
**Status:** gaps_found
**Re-verification:** Yes, after gap closure (plans 03-08 and 03-09)

## Verdict in one paragraph

The functional goal holds and CR-02 is closed. One safety gap remains: CR-03, which is the part of CR-01 that plan 03-08 did not reach. The 8 MiB byte cap and the 1,000,000-node ceiling stop token-dense hostile text, but a single large quoted string passes both and costs about 2.8 GiB in the parser. Plan 03-08's own gap truth names "gigabytes of RAM" as the outcome to prevent, and this input still produces it. I weighed it against the INTK-06 safety intent and the word "safely" in the phase goal and call it a gap, not a warning, for three reasons. It is the same defect class as CR-01, so closing CR-01 did not actually remove the amplification. The fix is one line in a regex that I confirmed in a scratch copy. And no later phase covers it (the Phase 4 and 5 roadmap entries mention nothing about parser limits), so deferral is not available. Nothing is written to the repo and the user chose the file, which is why this is a small gap-closure plan and not a redesign.

## Goal Achievement

### Observable Truths

ROADMAP success criteria (the contract) plus the two gap-closure truths from plans 03-08 and 03-09.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | UL zip identified as Ultra Librarian; timestamp-named symbol under `KiCADv6/`, `DQK0006B.kicad_mod`, `DLV0006A.stp` found; a folder of loose files read the same way | VERIFIED | My run on `downloaded_examples/ul_CSD85301Q2.zip`: vendor `UltraLibrarian`, confidence 1.0, symbol `CSD85301Q2` from member `KiCADv6/2026-10-18_09-12-49.kicad_sym` (name read from inside the file), footprint `DQK0006B`, model `DLV0006A.stp`, no issues. Staging dir not under the repo and the `kicad_import_*` temp count unchanged after close. Loose-folder parity is covered by passing `tests/test_package_folder.py` (full suite green). |
| 2 | KiCad 5-only package rejected with "re-download as KiCad v6+" | VERIFIED | Zip of `a.lib`, `a.dcm`, `a.mod`: no candidate, `intake.legacy_only` "leg.zip only holds KiCad 5 files (a.lib, a.dcm, a.mod); re-download as KiCad v6+". |
| 3 | Zip refused for `..`, absolute, drive-letter names, symlinks, over size/count/ratio limits; content staged only in a temp folder outside the repo | VERIFIED | `../evil.step`, `/abs.step`, `C:/x.step`, `a/../../b.step`: each `refused=True`, `intake.hostile_member`, no files. Symlink, ratio and count cases are covered by passing `tests/test_package_zip.py`. No `extract`/`extractall`/PySide6 in `kicad_lib_manager/importer`, enforced by the passing AST layering test. `git status --short` is unchanged by my runs. |
| 4 | UL sample suggests `<Type>_<SubCategory>_<Manufacturer>` ending `_TI`, as an overridable default | VERIFIED | `suggest_library(candidate.symbols[0].meta, list_existing_libraries(RepoLayout.for_repo(repo)))` returned `IC_SubCategory_TI`, confidence `low`, placeholders `('SubCategory',)`. Ends in `_TI`, and the placeholder contract for Phases 4 and 5 is exposed. |
| 5 | Names with `/`, `:`, reserved names, traversal sanitised; `.` and `-` kept; original and sanitised both reported | VERIFIED | `sanitize_name`: `CON`->`CON_`, `a/b:c`->`a_b_c`, `../../x`->`x`, `S3G-E3/57T`->`S3G-E3_57T`, `NUL.foo`->`NUL_.foo`. `NameResult` and `name_check` carry both forms; tests pass. |
| 6 | CR-02 gap truth (03-09): a damaged LZMA zip returns ERROR `intake.corrupt`, staging folder removed before return, `open_package` never raises for expected input faults | VERIFIED | Corrupted LZMA member: `refused=True`, one ERROR `intake.corrupt`, `files == []`, `staging_dir is None`, leaked temp folders 0, no exception (the previous run raised `_lzma.LZMAError`). `_READ_ERRORS` at `package.py:~56-67` includes `lzma.LZMAError` and `compression.zstd.ZstdError`; staging creation is guarded (`intake.staging_failed`). Codec, nested, mid-staging, tripwire and never-raises tests are in the green suite. The reviewer's 12,000-zip fuzz found no escaped exception; I did not repeat the fuzz. |
| 7 | CR-01 gap truth (03-08): a hostile low-ratio `.kicad_sym` inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM | PARTIAL, FAILED as stated (BLOCKER) | Token-dense case closes: 3.8 MB at 7:1 gave `refused False`, WARNING `intake.unreadable_file` "more than 1000000 nodes", 2.0 s. String-heavy case does not: see Gaps Summary and the spot-check table. The truth is stated as a general property of such files, and a member of that class still costs about 2.8 GiB. |

**Score:** 6/7 truths verified. `behavior_unverified`: 0.

Plan prohibitions: the test-tier ones (no D-06 re-sizing, no `parse` behaviour change without `max_nodes`, no catch-all `Exception` in `package.py`, skip not refuse) have passing tests in the 817-test suite. The judgment-tier ones (do not stage `.planning/config.json`, `state.json`, `milestone.lock`, `reports/`, `research_notes/`; do not fix other review findings) are consistent with `git status`, which still shows those paths uncommitted, and with `03-REVIEW-DISPOSITION.md`, which keeps WR-01..05 and IN-01..06 open. Non-authoritative, no human item raised.

### Deferred Items

None. ROADMAP Phases 4 to 6 have no goal or success criterion about parser limits or hostile input handling, so CR-03 is not deferred.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/package.py` | intake, D-06 caps, `MAX_KICAD_TEXT_BYTES`, `MAX_KICAD_TEXT_NODES`, `_READ_ERRORS`, guarded staging | VERIFIED | Constants at lines 22-25 (1,000,000 nodes, 8 MiB). `_READ_ERRORS` present. D-06 caps unchanged (1000, 100 MiB, 250 MiB, 200, 1 MiB). |
| `kicad_lib_manager/sexpr.py` | `parse(text, *, max_nodes=None)` raising `sexpr.too_many_nodes` | VERIFIED for the node ceiling, STUB-LEVEL for DoS bounding | Ceiling present and wired. The string token pattern at line 9 is the CR-03 defect. |
| `kicad_lib_manager/kicad_files.py` | `parse_bytes(..., max_nodes=None)` forwarding | VERIFIED | Wired from `base.locate`. |
| `kicad_lib_manager/importer/adapters/base.py` | byte cap in `_read_limited`, ceiling and `MemoryError` guard in `locate` | VERIFIED | `cap = min(MAX_KICAD_TEXT_BYTES, MAX_MEMBER_BYTES)`, `handle.read(cap + 1)`, `parse_bytes(..., max_nodes=_package.MAX_KICAD_TEXT_NODES)`, `except MemoryError` -> WARNING. |
| `tests/test_locate_text_caps.py` | CR-01 regression tests | PARTIAL | Exists with boundary, folder, model-exempt and real-file tests; passing. Only list-token hostile input, so it cannot detect CR-03. |
| `tests/zipfixtures.py` `corrupt_member`, `tests/test_package_zip.py` | CR-02 tests | VERIFIED | Present, passing. |
| UL adapters, `detect.py`, `naming.py`, `layout.py`, `suggest.py`, `candidate.py` | Plans 03-01 to 03-07 | VERIFIED | Exercised end to end above. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `adapters/base.py` | `package.py` | `_package.MAX_KICAD_TEXT_BYTES` read at call time | WIRED | `base.py:81`. |
| `adapters/base.py` | `kicad_files.py` | `max_nodes=_package.MAX_KICAD_TEXT_NODES` | WIRED | `base.py:247`. |
| `kicad_files.py` | `sexpr.py` | `_parse` forwards `max_nodes` | WIRED | Node-ceiling test passes. |
| `package.py` `_copy_member` | decompressors | `except _READ_ERRORS` -> `intake.corrupt` | WIRED | LZMA run above. |
| `package.py` `_stage_zip` | `tempfile.TemporaryDirectory` | guarded, `intake.staging_failed` | WIRED | Test passes. |
| `detect.py` -> adapters; `suggest.py` -> `naming.py`; `layout.py` -> `candidate.py` | n/a | registry and calls | WIRED | Used in the runs above. |

### Data-Flow Trace (Level 4)

No UI. Candidate chain traced: zip member bytes -> staged file -> `_read_limited` -> `parse_bytes` -> `find_symbols` / `PartMeta` (real property values, datasheet host `ti.com`) -> `suggest_library`. FLOWING, no static returns.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `./env/Scripts/python.exe -m pytest -q` | 817 passed, 4 skipped (3 Wurth submodule, 1 symlink privilege) | PASS |
| UL zip intake and suggestion | scratch script run with `python -I` | SC1 and SC4 outputs above | PASS |
| Legacy-only and hostile names | scratch script | SC2 and SC3 outputs above | PASS |
| CR-02: corrupt LZMA member | scratch script | refused, one ERROR `intake.corrupt`, no raise, 0 leaked temp dirs | PASS |
| CR-01 token-dense 3.8 MB, 7:1 | scratch script | WARNING `intake.unreadable_file` "more than 1000000 nodes", 2.0 s, no raise | PASS |
| CR-01 / CR-03 single 8,388,389-byte quoted string, 1.33:1 | scratch script (zip with one `.kicad_sym`, `open_package` + `detect_candidate`) | not skipped, no WARNING, symbol returned, 3.4 s, **peak working set 2,772 MiB, peak commit 3,108 MiB** | **FAIL** |
| Proposed fix (scratch only, repo untouched) | unrolled string regex monkeypatched into `sexpr._TOKEN`, same string | 0.06 s, 8 MiB traced; escapes parse; unterminated -> `sexpr.unterminated` | PASS (evidence the fix is sufficient) |

### Probe Execution

SKIPPED: the phase declares no probe scripts and `scripts/*/tests/probe-*.sh` do not exist.

### Requirements Coverage

PLAN frontmatter IDs: 03-01 `INTK-01, INTK-02, LIB-01`; 03-02 `INTK-01`; 03-03 `INTK-06`; 03-04 `INTK-01, INTK-02, INTK-05`; 03-05 `LIB-03`; 03-06 `LIB-01`; 03-07 `INTK-01, INTK-02`; 03-08 and 03-09 `INTK-06, INTK-01`. The union is exactly the six ROADMAP IDs for Phase 3. No orphans: INTK-03 and INTK-04 map to Phase 7 in REQUIREMENTS.md.

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| INTK-01 | 03-01, 03-02, 03-04, 03-07, 03-08, 03-09 | Open a zip or folder of loose files | SATISFIED | Zip and folder intake verified; open never raises for expected faults after 03-09. |
| INTK-02 | 03-01, 03-04, 03-07 | UL zip recognised, files found wherever they sit | SATISFIED | SC1 run. |
| INTK-05 | 03-04 | KiCad 5-only rejected with re-download message | SATISFIED | SC2 run. |
| INTK-06 | 03-03, 03-08, 03-09 | Zips read safely; traversal, absolute, symlinks rejected; size and count limits stop zip bombs | PARTIALLY SATISFIED | Every listed class is refused and the zip caps fire. The "limits stop zip bombs" intent is not met for parsed text: a ratio-passing 8 MiB string costs about 2.8 GiB (CR-03). |
| LIB-01 | 03-01, 03-06 | Suggested `<Type>_<SubCategory>_<Manufacturer>`, editable | SATISFIED | SC4 run; the edit UI is Phase 5, the placeholder contract is in place. |
| LIB-03 | 03-05 | Names sanitised; original vs sanitised reported | SATISFIED | SC5 run; the preview is Phase 5. |

Bookkeeping, not a code defect: REQUIREMENTS.md already ticks INTK-06 as Complete but leaves INTK-01, INTK-02, INTK-05, LIB-01 and LIB-03 unticked and Pending, and the ROADMAP Phase 3 line is unticked. INTK-06 should be reset to Pending until CR-03 closes; update the rest when the phase closes.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `kicad_lib_manager/sexpr.py` | 9 | Backtracking string regex (CR-03) | BLOCKER | About 330x memory amplification; 8 MiB input costs 2.8 GiB. |
| `kicad_lib_manager/importer/suggest.py` | 137-151 | WR-01 bare `Foo.pdf` datasheet becomes a manufacturer guess | WARNING (open) | Low-confidence flagged, still pollutes the primary suggestion. |
| `kicad_lib_manager/importer/package.py` | 151-152, 446-450 | WR-02 reparse-point bit matches cloud placeholders | WARNING (open, unreproduced) | Possible silent skip under OneDrive; check on the owner's machine. |
| `kicad_lib_manager/importer/package.py` | 293-298 | WR-03 write failure reported as corrupt archive | WARNING (open, deliberately left by 03-09) | Wrong remediation text. |
| `candidate.py`, `package.py`, `detect.py`, `adapters/base.py` | n/a | WR-04, WR-05 candidate outlives staged files; package-level warnings not carried to candidate | WARNING (open) | Phase 4 must re-check paths and surface `package.issues`. |
| phase source files | n/a | TBD/FIXME/XXX/TODO/HACK scan | none | No debt markers found in the importer, `sexpr.py` or `kicad_files.py` sources. |

IN-01 to IN-06 are info and stay open in `03-REVIEW-DISPOSITION.md`.

### Human Verification Required

None for this report. The two items raised last time are resolved: the owner chose to close CR-01 and CR-02 by plans 03-08 and 03-09, and I verified CR-02 closed. WR-02 needs a check on the owner's OneDrive setup at some point, but it is unreproduced and a WARNING, so it does not gate this phase.

### Gaps Summary

One gap, one root cause, a small fix.

**CR-03 leaves the CR-01 gap truth partly open.** Plan 03-08's truth reads "a hostile low-ratio .kicad_sym inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM". Its "Concretely" clause lists two token-dense examples, and both pass. But the truth is a statement about the class of file, the plan objective says the same, and the plan and T-03-35 in `03-SECURITY.md` claim the cost is bounded at about 200 MiB and 2 s. I measured a counter-example that the caps admit: 8,388,389 bytes, one quoted string, 1.33:1 deflate, no WARNING, 2,772 MiB peak working set. CPU is seconds, not minutes, but the memory half of the truth is falsified, and on a machine with less free RAM or pagefile than this one it ends in a hang or `MemoryError` from a single downloaded zip. That is the INTK-06 safety intent ("size and count limits stop zip bombs") not being met for the one input the added caps were meant to bound. Folder intake is exposed too, since it has no ratio rule.

I did not accept "the user chose the file, nothing is written" as a reason to downgrade, because that same argument applied to CR-01 and the owner decided to close it. The security register entries T-03-15 and T-03-35 are marked closed and should be reopened until this lands.

**Suggested closure plan (one task):**
1. In `kicad_lib_manager/sexpr.py`, replace the `str` group with the unrolled linear form. In source it is `"[^"\\]*(?:\\.[^"\\]*)*"` inside the existing raw string, with `re.S` kept. Behaviour is identical (checked on escaped quote, escaped backslash, unterminated).
2. Add a string-heavy hostile fixture next to `_hostile_symbol` in `tests/test_locate_text_caps.py`, with a time or memory bound.
3. Add escape and unterminated-string cases to `tests/test_sexpr.py`; rerun `tests/test_roundtrip_corpus.py` to confirm the Phase 1 byte-identical guarantee.
4. Reopen then re-close T-03-15 and T-03-35 in `03-SECURITY.md`; update the CR-03 disposition.

WR-01 to WR-05 and IN-01 to IN-06 remain open by decision and do not gate this phase; Phase 4 should note WR-04 and WR-05 when it consumes `ImportCandidate`.

---

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
