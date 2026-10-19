---
phase: 03-package-intake-and-naming
verified: 2026-10-19T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
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
covered_digest: "v3:sha256:245008331a34ecdc37ad49d92e0d3097e889d73245697a3def1ced9a108b876f"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Decide whether CR-01 (parsed KiCad text capped at 100 MB) must be closed before Phase 4 starts. Recommendation: close it, with a small gap-closure plan that adds a separate MAX_KICAD_TEXT_BYTES cap (about 8 MB) for symbol and footprint files."
    expected: "A hostile low-ratio .kicad_sym inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM."
    why_human: "This is a severity and scheduling call, not a code question. The defect is reproduced (see Behavioral Spot-Checks) and no roadmap success criterion is literally falsified, so it is a WARNING, not a BLOCKER."
  - test: "Decide whether CR-02 (corrupt LZMA member raises out of open_package; TemporaryDirectory creation outside any try) must be closed before Phase 4 starts. Recommendation: close it, since a one-line addition of lzma.LZMAError to the caught tuple plus a guarded TemporaryDirectory covers it."
    expected: "A damaged LZMA zip returns an ERROR Issue intake.corrupt and deterministically removes its staging folder; open_package never raises for expected input faults."
    why_human: "The module's own docstring promises 'never raised'. The Phase 5 GUI worker will call open_package on user-downloaded files, so the owner should choose between fixing it now and catching it in the caller."
---

# Phase 3: Package Intake and Naming Verification Report

**Phase Goal:** Given a vendor zip or a folder of loose files, the importer safely finds the KiCad symbol, footprint and 3D model and proposes a sanitised, convention-following target library name, without writing anything into the repo
**Verified:** 2026-10-19
**Status:** human_needed
**Re-verification:** No, initial verification

## Verdict in one paragraph

The phase goal is achieved functionally. All five ROADMAP success criteria were confirmed by running the code myself, not by reading SUMMARY.md, and the full suite passes (773 passed, 4 skipped, run again by me). Two reproduced hardening defects from the code review (CR-01, CR-02) weaken the word "safely" at the edges. I classify both as WARNING, not BLOCKER: neither lets anything be written into the repo, neither defeats a literal ROADMAP success criterion, and the declared size, count and ratio limits do exist and fire. They are real, though, and I recommend closing both before Phase 4 builds on this API. The status is `human_needed` so the owner makes that call explicitly.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | UL zip is identified as Ultra Librarian; timestamp-named symbol under `KiCADv6/`, `DQK0006B.kicad_mod` under `KiCADv6/footprints.pretty/`, `DLV0006A.stp` at root; a folder of loose files is read the same way | VERIFIED | My run of `open_package` + `detect_candidate` on `downloaded_examples/ul_CSD85301Q2.zip`: vendor `UltraLibrarian`, confidence 1.0, symbols `['CSD85301Q2']` (member `KiCADv6/2026-10-18_09-12-49.kicad_sym`), footprints `['DQK0006B']`, models `['DLV0006A.stp']`, no issues. Name comes from inside the file, not the timestamp filename. Loose folder of the three real UL files: vendor `Loose`, 0.3, same symbol, footprint and model; folder mtimes unchanged afterwards. |
| 2 | KiCad 5-only package rejected with "re-download as KiCad v6+" | VERIFIED | Zip of `a.lib`, `a.dcm`, `a.mod`: no candidate, `intake.legacy_only` text "only holds KiCad 5 files (a.lib, a.dcm, a.mod); re-download as KiCad v6+". Same result for a folder holding `a.lib` and `a.mod`. Half-legacy and mixed matrix covered by `tests/test_legacy_rules.py` (passing). |
| 3 | Zip refused for `..`, absolute, drive-letter names, symlinks, over size/count/ratio limits; content only staged in a temp folder outside the repo | VERIFIED (with caveats, see CR-01 and CR-02) | I built zips with `../evil.step`, `/abs.step`, `C:/x.step`, `a/../../b.step`, `a:b.step`, a symlink entry (mode 0o120777) and a 50 MB all-zero deflate member: every one gave `refused=True` with `intake.hostile_member` (or `intake.high_ratio` for the bomb) and no files. UL sample staged to `%TEMP%\kicad_import_*` (outside the repo), files under generated names (`model_000.stp`, `sym_001.kicad_sym`, `fp_002.kicad_mod`), staging dir gone after the `with` block. `git status --short` is identical before and after all my runs. No `extract`/`extractall`/PySide6 in `kicad_lib_manager/importer` (grep clean; AST layering guard test passes). |
| 4 | UL sample suggests `<Type>_<SubCategory>_<Manufacturer>` ending `_TI`, as an overridable default | VERIFIED | `suggest_library` against the live `Custom/` returns `IC_SubCategory_TI`, confidence `low`, placeholders `('SubCategory',)`, Type `IC` (reference), Manufacturer `TI` (host_table, from `ti.com`). Alternatives start `IC_Battery_Charger_TI` (score 5), then four score-2 entries, exactly as the plan states. `placeholder_tokens` returns `['SubCategory']` for it and `[]` for `Transistor_MOSFET_TI`, so the name is a default the user edits, and the D-04 install-refusal contract is exposed for Phases 4 and 5. |
| 5 | Names with `/`, `:`, Windows-reserved names or traversal are sanitised; `.` and `-` kept; original and sanitised both reported | VERIFIED | `sanitize_name`: `CON`->`CON_`, `a/b:c`->`a_b_c`, `../../x`->`x`, `S3G-E3/57T`->`S3G-E3_57T`, `NUL.foo`->`NUL_.foo`, `COM1`->`COM1_`; each `NameResult` carries `original`, `sanitized`, `changed`. `SymbolItem`/`FootprintItem`/`ModelItem.name_check` exist (candidate.py) and are covered by `tests/test_candidate_names.py` and `tests/test_naming_sanitize.py` (passing, including all current `Custom/` names unchanged). |

**Score:** 5/5 ROADMAP truths verified. PLAN-level must_have truths for plans 03-01 to 03-07 were also checked against code and tests; no PLAN truth failed. The plan prohibitions (no repo write during intake, no write to the picked folder, no name derived from a filename, no silent rename, no aggregator host as manufacturer, no placeholder name presented as finished) are test-tier and all have passing tests; the "do not stage `.planning/config.json` etc." prohibitions are judgment-tier and `git status` shows those files still uncommitted/untracked, consistent with compliance (non-authoritative).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/package.py` (532 lines) | zip/folder intake, caps, staging | VERIFIED | Substantive: `_hostile_reason`, `_prescan`, `_copy_capped`, nested zip one level, `_open_folder` read-only walk. Wired: used by `detect`, tests. |
| `kicad_lib_manager/importer/candidate.py` | intake data model with `name_check` | VERIFIED | Present, imports `naming`. |
| `kicad_lib_manager/importer/adapters/base.py` | `locate`, legacy matrix, `part_meta` | VERIFIED | Present, wired from `detect.py`. Caveat: `_read_limited` cap (CR-01). |
| `kicad_lib_manager/importer/adapters/ultralibrarian.py`, `loose.py` | vendor adapters | VERIFIED | Registered in `detect.ADAPTERS`; both exercised above. |
| `kicad_lib_manager/importer/detect.py` | registry + `detect_candidate` | VERIFIED | Run end to end. |
| `kicad_lib_manager/importer/naming.py` | sanitiser | VERIFIED | Run directly. |
| `kicad_lib_manager/importer/layout.py`, `suggest.py` | fresh `Custom/` listing, suggestion | VERIFIED | `list_existing_libraries` read live `Custom/`; suggestion matches plan. |
| `kicad_lib_manager/kicad_files.py` (`file_kind`, `file_version`) | read helpers | VERIFIED | Used by `base.py`. |
| `tests/zipfixtures.py`, `tests/test_*` (zip, folder, legacy, naming, suggest, candidate names, layering) | test infrastructure | VERIFIED | All present and passing. |
| `.gitattributes` `downloaded_examples/** -text` | no line-ending conversion of vendor files | VERIFIED | Covered by a passing fixture test. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `detect.py` | `ultralibrarian.py`, `loose.py` | `ADAPTERS` registry | WIRED | UL and Loose both chosen correctly in my runs. |
| `adapters/base.py` | `kicad_files.py` | `parse_bytes`, `find_symbols`, `footprint_name`, `file_version` | WIRED | Names and versions read from file content. |
| `package.py` | `tempfile` | `TemporaryDirectory(` staging | WIRED | Staging outside repo, removed on close. |
| `suggest.py` | `naming.py` | `sanitize_name(` + `case_clash` | WIRED | Suggestion issues carry sanitiser output. |
| `layout.py` | `candidate.py` | `ExistingLibrary(` | WIRED | Live listing returned. |
| `candidate.py` | `naming.py` | `sanitize_filename(` | WIRED | `name_check` properties. |

### Data-Flow Trace (Level 4)

Not applicable in the UI sense (no rendering in this phase). Data chain for the candidate was traced: zip member bytes, then staged file, then `parse_bytes`, then `find_symbols`/`footprint_name`, then `PartMeta` (reads real properties, e.g. datasheet `ti.com`), then `suggest_library`. No static or hardcoded return in the chain. FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `./env/Scripts/python.exe -m pytest -q` | 773 passed, 4 skipped (3 Wurth submodule, 1 symlink privilege) | PASS |
| UL zip intake and suggestion | scratch script (open_package, detect_candidate, suggest_library) | as in truths 1 and 4 | PASS |
| Hostile zip names, symlink, ratio bomb | scratch script | all refused whole | PASS |
| Legacy-only zip and folder | scratch script | `intake.legacy_only`, "re-download as KiCad v6+" | PASS |
| Loose folder read-only | scratch script, mtime snapshot | identical before/after | PASS |
| Repo untouched | `git status --short` before/after | identical | PASS |
| CR-02 reproduction | LZMA zip, bytes 60-90 flipped, `open_package` | **raises `_lzma.LZMAError`** | FAIL (hardening defect) |
| CR-01 reproduction | 3.8 MB random-token `.kicad_sym`, deflated to 0.38 MB (ratio 10:1, passes the 200:1 rule) | `open_package` accepts it; `detect_candidate` takes 5.8 s (35 s under tracemalloc) and peaks about 476 MB heap, ending `content_mismatch` + `nothing_found` | FAIL (hardening defect) |

### Probe Execution

SKIPPED: the phase declares no probe scripts, and `scripts/*/tests/probe-*.sh` do not exist for this project.

### Requirements Coverage

Requirement IDs declared across PLAN frontmatter: 03-01 `INTK-01, INTK-02, LIB-01`; 03-02 `INTK-01`; 03-03 `INTK-06`; 03-04 `INTK-01, INTK-02, INTK-05`; 03-05 `LIB-03`; 03-06 `LIB-01`; 03-07 `INTK-01, INTK-02`. The union is exactly the six IDs assigned to Phase 3 in ROADMAP.md. No orphaned requirements: the other REQUIREMENTS.md IDs mapped to Phase 3 do not exist (INTK-03 and INTK-04 map to Phase 7).

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INTK-01 | 03-01, 03-02, 03-04, 03-07 | Open a zip or a folder of loose files | SATISFIED | Zip and folder runs above; loose-folder parity with zip tested. |
| INTK-02 | 03-01, 03-04, 03-07 | UL zip recognised, files found wherever they sit, STEP at root with a different name | SATISFIED | UL run above. |
| INTK-05 | 03-04 | Legacy KiCad 5-only rejected with re-download message | SATISFIED | Legacy runs above. |
| INTK-06 | 03-03 | Zips read safely: no repo extraction, traversal, absolute names, symlinks rejected, size/count limits | SATISFIED with WARNING | All listed hostile classes refused; ratio, count and size caps fire. Hardening gaps CR-01 and CR-02 noted; they do not break any item in the requirement text. |
| LIB-01 | 03-01, 03-06 | Suggested `<Type>_<SubCategory>_<Manufacturer>`, editable | SATISFIED | Suggestion run above. Editing UI is Phase 5; the `placeholder_tokens` contract is in place. |
| LIB-03 | 03-05 | Names sanitised; preview shows original vs sanitised | SATISFIED | `NameResult` + `name_check` carry both. The preview itself is Phase 5. |

Bookkeeping note for the orchestrator (not a code defect): `.planning/REQUIREMENTS.md` still shows INTK-01, INTK-02, INTK-05, LIB-01 and LIB-03 as `Pending` and unticked, and the ROADMAP Phase 3 line is unticked. They should be updated when the phase closes.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `kicad_lib_manager/importer/adapters/base.py` | 76-86, 239 | CR-01: parsed `.kicad_sym`/`.kicad_mod` read with the 100 MB model cap, then handed to the pure-Python S-expression parser | WARNING | Reproduced: a hostile low-ratio text file inside every declared limit costs seconds now and, scaled to 100 MB, minutes and GBs. Unresponsive worker or `MemoryError` from a single downloaded zip. Not a repo-write or traversal issue. |
| `kicad_lib_manager/importer/package.py` | 267, 304-306 | CR-02: `lzma.LZMAError` not in the caught tuple; `TemporaryDirectory(...)` and `staging.resolve()` outside any `try` | WARNING | Reproduced for LZMA. Breaks the documented "never raised" contract on a corrupt archive; staging folder then removed only by the `TemporaryDirectory` finalizer. No data loss, no repo write. |
| `kicad_lib_manager/importer/suggest.py` | 137-151 | WR-01: bare `Foo.pdf` datasheet becomes a manufacturer guess | WARNING (open, review) | Low-confidence flagged, still pollutes primary suggestion. |
| `kicad_lib_manager/importer/package.py` | 402-406, 121 | WR-02: reparse-point bit also matches cloud placeholders | WARNING (open, review; unreproduced) | Possible silent skip of real files under OneDrive; needs a check on the owner's machine. |
| `kicad_lib_manager/importer/package.py` | 264-268 | WR-03: write failure reported as corrupt archive | WARNING (open, review) | Wrong remediation text. |
| `kicad_lib_manager/importer/candidate.py`, `detect.py` | n/a | WR-04, WR-05: candidate outlives staged files undocumented; package-level warnings not carried to the candidate | WARNING (open, review) | Phase 4 must re-check paths and surface `package.issues`. |
| importer modules | n/a | TBD/FIXME/XXX/TODO/HACK scan | none found | No debt markers in the phase's source files. |

Review items IN-01 to IN-06 are info-level and are not repeated here. All 13 review findings remain `open` in `03-REVIEW-DISPOSITION.md`.

### Human Verification Required

#### 1. Close or defer CR-01 (text-parse cap)

**Test:** Decide whether to add a gap-closure plan before Phase 4. Recommended fix: a separate `MAX_KICAD_TEXT_BYTES` (about 8 MB) used by `_read_limited` for `symbol`/`footprint` kinds, skipping with the existing WARNING, plus a test with a multi-MB low-ratio hostile file.
**Expected:** The hostile file reproduced above is skipped quickly with a WARNING.
**Why human:** Severity and scheduling decision. I weighed it against the "safely" wording and INTK-06 ("size and count limits stop zip bombs"): the limits exist and fire on every case the ROADMAP names, but the one that guards parsed text is sized for STEP models and is ineffective as a DoS guard. That is a real gap in the spirit of INTK-06 and a measured defect, but nothing is written, extracted or traversed, and the user chose the file, so I rate it WARNING.

#### 2. Close or defer CR-02 (open_package may raise)

**Test:** Decide whether to fix now. Recommended fix: add `lzma.LZMAError` to the caught tuple at `package.py:267`, wrap `TemporaryDirectory(...)` in a `try` that returns `intake.staging_failed`, and add a corrupt-LZMA fixture test.
**Expected:** A corrupt LZMA zip returns an ERROR Issue and cleans up deterministically.
**Why human:** The ROADMAP does not mention it, but `open_package`'s docstring and plan 03-03 promise it never raises on expected failures. Phase 5's GUI worker will call it on user downloads. Cheap to fix now; otherwise Phase 5 must catch broadly.

### Gaps Summary

No ROADMAP success criterion fails, and no PLAN must_have truth fails. Both critical review findings are real (I reproduced each from a clean script), and both are hardening defects in the "safely" dimension rather than functional failures. They are the reason the security register carries T-03-09 and T-03-15 as open-non-blocking. The review's other eleven findings are open and non-blocking. I recommend a single small gap-closure plan covering CR-01, CR-02, and (cheaply) WR-01 and WR-05 before Phase 4, since Phase 4 will consume `ImportCandidate` and `Package` directly. If the owner prefers to proceed, record the decision in `03-REVIEW-DISPOSITION.md` (accepted/deferred, with the Phase 5 catch-all as the compensating control) so the gap is not forgotten.

---

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
