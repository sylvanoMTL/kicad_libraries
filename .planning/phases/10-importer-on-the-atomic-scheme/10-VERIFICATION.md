---
phase: 10-importer-on-the-atomic-scheme
verified: 2026-10-28T00:00:00Z
status: gaps_found
score: 6/7 must-haves verified
covered_files:
  - .planning/phases/10-importer-on-the-atomic-scheme/10-01-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-01-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-02-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-02-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-03-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-03-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-04-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-04-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-05-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-05-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-06-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-06-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-07-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-07-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-08-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-08-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-09-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-09-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-10-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-10-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-11-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-11-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-12-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-12-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-13-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-13-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-14-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-14-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-15-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-15-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-16-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-16-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-17-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-17-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-18-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-18-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-19-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-19-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-20-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-20-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-21-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-21-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-22-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-22-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-23-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-23-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-24-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-24-SUMMARY.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-25-PLAN.md
  - .planning/phases/10-importer-on-the-atomic-scheme/10-25-SUMMARY.md
  - kicad_lib_manager/atomic_check.py
  - kicad_lib_manager/importer/categories.py
  - kicad_lib_manager/importer/footprint_index.py
  - kicad_lib_manager/importer/footprint_text.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/incoming.py
  - kicad_lib_manager/importer/keywords.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/siblings.py
  - kicad_lib_manager/importer/stems.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/manufacturers.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
covered_digest: "v3:sha256:bee4ec0b0ff57c6d63fe23dcbd9f4bd1d8df735d6943d651534b9a46f85ad995"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Nothing is guessed (D-28): a package fact that cannot be computed or read is left out of the footprint description, tags and keywords (plan 10-05 prohibition; plan 10-23 truth 'the family is taken from the official KiCad footprint whose name matches the vendor package code')"
    status: failed
    reason: "When the vendor footprint's own descr and tags name no package family, planner.py takes the family from the top-ranked official KiCad footprint if its score is >= 30. A score of 30 is only 'the vendor code's leading letters are a whole word of the name', so many footprints tie and the alphabetical tie-break picks an arbitrary one. The wrong family (and the pin count from that text) is then written into the footprint description, the generated tags, the IPC-style name and the symbol keywords, and the preview shows it as an ordinary generated change. Reproduced against the installed KiCad 10 footprints (see Behavioral Spot-Checks). No test covers the ambiguous case."
    artifacts:
      - path: "kicad_lib_manager/importer/planner.py"
        issue: "line 81-83 `_MIN_FAMILY_SCORE = 30` equals the leading-letters score; line 1066-1072 accepts `best[0]` without checking that it is the only top-scored match"
      - path: "kicad_lib_manager/importer/footprint_index.py"
        issue: "rank() sorts ties alphabetically (line 156), so the family source among equal scores is effectively random"
    missing:
      - "Accept an official footprint as the family source only when the match is specific: score >= 50 (full code in the name), or a leading-letters-only match where exactly one footprint holds the top score (review CR-01 fix: request limit=2 and require best[0].score > best[1].score)"
      - "A test in tests/test_generated_text.py with a SOIC127P600X175-8N-style code against a stock fixture with two SOIC footprints, asserting that no family is taken (and the description falls back to the known parts)"
behavior_unverified_items: []
human_verification:
  - test: "Setup S1: build the scratch repo. PowerShell, from the repo root: `$env:KICAD_ATOMIC_UAT_DIR = \"$env:TEMP\\kicad_atomic_uat\"` then `env\\Scripts\\python.exe -m pytest tests/test_atomic_uat.py -k uat_atomic_scratch -s`. The output holds a line \"Run the app on it: <command>\"; the \"Check in the app:\" lines after it belong to the Phase 9 check, so skip them."
    expected: "The test passes and prints \"Run the app on it: <command>\"."
    why_human: "Builds the scratch environment the manual checks run in; it must never be run against the live Custom/ or the real KiCad tables."
  - test: "Setup S2 and S3: `mkdir \"$env:TEMP\\kicad_atomic_uat\\tables\"`. Run the command printed in S1. In the main window's toolbar set \"Destination:\" to that tables folder. If the app offers to change KiCad's path variables at any point, click No."
    expected: "The scratch app opens with Destination pointing at the scratch tables folder."
    why_human: "Interactive GUI session on a scratch copy; the scratch Destination keeps every table write away from the owner's real KiCad tables."
  - test: "Check 1 [criterion 1]: Ctrl+I (Import Part...), pick downloaded_examples\\ul_CSD85301Q2.zip. Read the library field, hover it, and look under it."
    expected: "The library field reads Atomic_Transistor_FET. Tooltip: \"Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2).\" The badge next to it reads \"new - creates .kicad_sym\". There is no amber token line under the field."
    why_human: "Tooltip, badge and amber-line presence are visual, and the sibling count depends on the installed KiCad 10 libraries."
  - test: "Check 2 [criterion 4]: In the same dialog read the amber strip, click \"Type a Description\", then type \"Dual N-channel MOSFET 30 V\" in the Description field."
    expected: "The strip reads \"⚠ Install is blocked: Type a Description\". Clicking the reason puts the cursor in the Description field and its frame turns amber. After typing, the reason and the amber frame go at once, and Install Part enables after the preview updates."
    why_human: "Focus jump, frame colour and live clearing are GUI behaviour."
  - test: "Check 3 [criteria 3, 4, 5]: Look at Value, Manufacturer, Footprint, the Files list, Footprint description, Footprint tags and Keywords."
    expected: "Value is greyed out and reads CSD85301Q2. Manufacturer reads Texas Instruments. The Footprint field reads Atomic_Footprints:DQK0006B. Files lists Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod and nothing named Atomic_Transistor_FET.pretty. Footprint description reads \"WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B\". Footprint tags contain WSON-6, DQK0006B and P0.65mm. Keywords contain Transistor, FET, TI and Texas."
    why_human: "Exact preview text on a real vendor sample against the installed KiCad 10 footprint library."
  - test: "Check 4 [criterion 2]: Type each name into the library field and read the strip: \"Transistor_FET\"; \"Atomic_TI\"; \"atomic_transistor_fet\" then Tab; \"fet\". Then open the dropdown."
    expected: "\"Transistor_FET\" gives \"Transistor_FET is the name of a KiCad library; use Atomic_Transistor_FET\". \"Atomic_TI\" gives \"Atomic_TI is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET\". \"atomic_transistor_fet\" then Tab turns the text into Atomic_Transistor_FET with the grey note \"Spelling corrected to Atomic_Transistor_FET\" under the field. \"fet\" makes the list show only names containing fet. The dropdown shows your Atomic_ libraries first, a divider, then the rest; no IC_... or Connector_..._GCT name."
    why_human: "Typing, filtering and dropdown ordering in the live widget."
  - test: "Check 5 [criterion 3]: Click \"Use an official KiCad footprint\". Read the list, pick Package_SON:Texas_DQK, read the Footprint field, the Not used section and the footprint name and text fields. Then click \"Install the vendor footprint into Atomic_Footprints\" to switch back."
    expected: "Package_SON:Texas_DQK is first in the list. The Footprint field reads Package_SON:Texas_DQK. Not used lists DQK0006B (\"footprint, not installed: an official KiCad footprint is used\") and DLV0006A.stp (\"3D model, not installed: KiCad's own 3D model is used\"). The footprint name and the two footprint text fields are greyed with \"KiCad's own footprints are never changed\". No pad warning appears."
    why_human: "Ranked list order, greyed fields and the Not used wording are visual and depend on the installed KiCad footprints."
  - test: "Check 6 [criterion 3]: Click Install Part. Then look at the result banner, the Library tables row and the scratch tables folder."
    expected: "The result banner reads \"✓ Installed CSD85301Q2 into Atomic_Transistor_FET\". The Library tables row reads \"Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table\" (the scratch repo has Atomic_Footprints.pretty, and the empty tables folder of S2 does not list it, so it is added). The tables folder of S2 now holds sym-lib-table and fp-lib-table."
    why_human: "End-to-end install into the scratch repo and table step; the table-file check is on the filesystem outside the repo."
  - test: "Check 7 [criteria 1, 4]: Click Change..., pick downloaded_examples\\LIB_RS3-1212S_H3.zip. Read the library field, hover it, read Field changes."
    expected: "The library field reads Atomic_Converter_DCDC_Isolated; tooltip \"Suggested from the vendor category Power Supply and the description.\" Field changes shows \"Set Manufacturer\" with \"RECOM Power → RECOM: canonical spelling\". Install Part enables without typing anything."
    why_human: "Category-map suggestion text and the Field changes row on a real SamacSys/LIB sample."
  - test: "Check 8 [criteria 1, 4]: Click Change..., pick downloaded_examples\\ul_ATXK-H14-D-32-768KHZ-E50-T3.zip. Read the library field and the strip, then click the 3D model reason."
    expected: "The library field is empty with the grey hint \"Pick a library, or type Atomic_ and a KiCad library name\". The strip lists \"Pick or type a library name\", \"Enter the Manufacturer\", \"The Datasheet must be a link or a file path\" and a reason starting \"3D model:\". Clicking the 3D model reason moves the focus to the Add 3D model... button."
    why_human: "The importer asking instead of guessing, and the focus jump, are GUI behaviour."
  - test: "Check 9 [criterion 4]: Click Change..., pick downloaded_examples\\USB4145-03-0170-C_REVA2.zip. Read the library field and the strip. Click Add 3D model..., pick downloaded_examples\\194150990-659-usb4145-03-0170-c.zip."
    expected: "The library field reads Atomic_Connector. The strip lists \"Enter a Datasheet link\" and a reason starting \"3D model:\". After adding the model, the 3D model reason goes away."
    why_human: "Filling in the 3D model in the preview clearing its reason is a live GUI interaction."
  - test: "Check 10 [criterion 5]: In KiCad 10, Symbol Editor, File > Add Library..., pick <scratch>\\Custom\\Symbols\\Atomic_Transistor_FET.kicad_sym and add it to the PROJECT library table only, never Global (Global edits the owner's real library tables). Open CSD85301Q2's Symbol Properties. Then Footprint Editor, add <scratch>\\Custom\\Footprints\\Atomic_Footprints.pretty, again to the PROJECT table only, and open DQK0006B's Footprint Properties. Afterwards remove both libraries from the Project library table."
    expected: "The symbol's Keywords equal the Keywords of check 3. The footprint's Description and Keywords equal the footprint description and tags of check 3. Both libraries are removed from the Project table afterwards."
    why_human: "Needs the real KiCad 10 GUI to confirm the installed files carry exactly what the preview showed. Use a scratch project and the Project table so the owner's Global tables are not edited."
  - test: "Check 11 (owner decision): Say whether to keep or change: strict majority for sibling votes, ATXK-H14 asking instead of suggesting Atomic_Oscillator, the measured \"2.1x2.1 mm\" instead of KiCad's nominal \"2x2 mm\", and the IPC-style tag WSON-6_2.1x2.1mm_P0.65mm."
    expected: "A keep or change decision for each of the four behaviours."
    why_human: "Design preference of the owner, not verifiable by code."
---

# Phase 10: Importer on the Atomic Scheme Verification Report

**Phase Goal:** A part imported from any supported vendor package lands in the right `Atomic_<stem>` library, with its footprint in the shared `Atomic_Footprints`, and only once it passes the atomic rule, so new imports never bring back the old names
**Verified:** 2026-10-28
**Status:** gaps_found (one narrow must-have gap; the human UAT of ROADMAP criteria 1-5 is still pending and listed under Human Verification Required)
**Re-verification:** No, initial verification

## Goal Achievement

The goal itself is achieved in the code: suggestion, name rule, shared-footprint install, official-footprint option, install gate and generated text are present, wired end to end (planner -> preview -> install, dialog -> gate) and exercised by tests. One plan-level must-have (D-28, "nothing is guessed") is violated by the package-family fallback, see CR-01 below.

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | ROADMAP 1: `ul_CSD85301Q2.zip` suggests `Atomic_Transistor_FET` from the `CSD` family in KiCad's libraries; RS3-1212S/H3 gets `Atomic_Converter_DCDC_Isolated` from the category map; unplaceable parts ask; no suggestion holds a manufacturer name | VERIFIED | `importer/suggest.py::suggest_library` runs own siblings, then KiCad siblings (`siblings.py`), then `classify()` (`categories.py`), else returns `kind="ask"` with an empty name. Stems come only from `allowed_stems()` (KiCad library stems minus excluded), so a manufacturer token cannot be produced. `tests/test_suggest_atomic.py`, `test_siblings.py`, `test_categories.py` pass (341 passed in the targeted run). The exact CSD and RS3 outcomes against the installed KiCad 10 libraries are in the human check (checks 1, 7, 8). |
| 2 | ROADMAP 2: user can pick an existing `Atomic_` library or type a new name; a name equal to an official KiCad library (`Transistor_FET`) or using a manufacturer token (`Atomic_TI`) is refused with the reason shown | VERIFIED | `importer/stems.py::name_verdict` returns the refusals "`Transistor_FET` is the name of a KiCad library; use Atomic_Transistor_FET" and "`Atomic_TI` is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET", plus case correction. Enforced in `build_plan` and the form (plan 10-10); picker in `import_dialog.py` (line ~1350). `tests/test_stems.py` passes. |
| 3 | ROADMAP 3: footprint installs into the shared `Atomic_Footprints.pretty`, or into an official KiCad footprint the user picks; Footprint field reads `Atomic_Footprints:<FP>` or `<Lib>:<FP>`; a new symbol library creates no matching `.pretty` | VERIFIED | `stems.SHARED_FOOTPRINT_LIBRARY = "Atomic_Footprints"`; planner supports `is_official` (official link, no vendor footprint or model written, KiCad's own model used) and the shared-library clash rules (reuse, rename `<FP>_<MPN>`, overwrite). `tests/test_shared_footprints.py`, `test_official_footprint.py`, `test_single_footprint.py` pass. |
| 4 | ROADMAP 4: Install stays disabled while the incoming part fails the atomic check; each failure is a clickable reason that jumps to its field; Value defaults to the MPN; filling in Datasheet, Description or the 3D model clears the matching reason | VERIFIED | `planner.py` (line ~1457-1480) runs `incoming_issues` on the planned bytes and emits `install.atomic.<rule>` errors; `import_dialog.py` (line ~2630-2653) sets `Install Part` enabled only with `not reasons and not plan.blocked`; strip text "⚠ Install is blocked: ..." with clickable reasons (`form.py::blocking_reasons`). `tests/test_install_gate.py`, `test_gate_reasons.py`, `test_incoming_check.py` pass. Live click-to-focus and clearing are in the human check (checks 2, 8, 9). |
| 5 | ROADMAP 5: preview shows generated `ki_keywords` (function words, interfaces, package codes, manufacturer aliases, MPN variants) and a footprint description and tags (package, IPC name, vendor package code, pitch); all editable; installed files carry exactly what the preview showed | VERIFIED (see gap on the family source) | `keywords.py::generate_keywords`, `footprint_text.py` (`pitch_mm`, `body_mm`, `ipc_name`, `describe`, `generated_tags`), `kicad_files.footprint_text_edit` write the nodes; `PartText` in the plan; dialog edits with Regenerate; written text = options override else generated. `tests/test_keywords.py`, `test_footprint_text.py`, `test_generated_text.py` pass, including written-equals-previewed. The family input has the CR-01 defect below. |
| 6 | Plan 10-05 prohibition + 10-23 truth: "nothing is guessed" (D-28): the package family is read only from the vendor's own text or from the official footprint whose name matches the vendor package code | FAILED | Code accepts a leading-letters-only match (score 30) among many ties as the family source. Reproduced, see Behavioral Spot-Checks. Gap 1. |
| 7 | Plan 10-25: help page describes the Atomic_ import with no jargon (no `ki_keywords`, `SubCategory`, `Make linked`); tests/README documents the fixtures and skips; end-of-phase human gate exists | VERIFIED | `help_dialog.py` contains `Atomic_Footprints` (3 hits) and no `ki_keywords`; no `SubCategory` in code; `tests/test_help_dialog.py` is in the review's file list and covered by the orchestrator's green run. The human-check block is collected below. |

**Score:** 6/7 truths verified (0 present, behavior-unverified)

### CR-01 weighed against the must-haves

CR-01 is a gap in must-have achievement, not only an advisory defect. Reasons:

- Plan 10-05 carries the prohibition "MUST NOT guess a package fact that cannot be computed or read" (status resolved, verification test). The code does guess one on realistic input, and the only enforcing tests cover the unambiguous cases, so the "resolved" status holds for the tested paths only.
- Plan 10-23's truth says the family comes from the official footprint "whose name matches the vendor package code". A leading-letters-only match among tens of tied footprints does not meet that wording.
- The wrong value is not transient: it is written to the permanent `Atomic_Footprints` footprint (description and tags) and to the symbol keywords, and the preview shows it as an ordinary generated change.
- The ROADMAP criteria themselves still hold, and the owner can edit the three texts in the preview, so this does not defeat the phase goal (right library, shared footprint library, atomic gate). It does defeat the "nothing is guessed" must-have, so status is gaps_found. The fix is small and local (about five lines in `planner.py` plus one test).

I did not find CR-01 triggered by the three real samples named in the UAT: the CSD sample's own text and `Package_SON:Texas_DQK` give `WSON-6`, which matches the UAT expectation.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `kicad_lib_manager/importer/stems.py` | allow-list, `name_verdict`, shared library constant | VERIFIED | substantive, imported by suggest, siblings, dialog |
| `kicad_lib_manager/importer/suggest.py`, `siblings.py`, `categories.py` | three-step suggestion | VERIFIED | `suggest_library` wires own, stock, category, ask |
| `kicad_lib_manager/importer/footprint_index.py` | official footprint index and ranking | VERIFIED (defect CR-01 in tie-handling use; WR-01 thread safety) | used by planner and dialog picker |
| `kicad_lib_manager/importer/footprint_text.py` | pitch, body, family, describe, tags | VERIFIED | wired through `footprint_facts` in planner |
| `kicad_lib_manager/importer/keywords.py` | keyword generation | VERIFIED (WR-02 "CAN" false positive) | wired as `generate_keywords` in planner |
| `kicad_lib_manager/importer/incoming.py` | incoming atomic check on planned bytes | VERIFIED | `incoming_context`/`incoming_issues` called from planner |
| `kicad_lib_manager/kicad_files.py` | `footprint_text_edit` | VERIFIED | used by planner for descr/tags |
| `kicad_lib_manager/widgets/import_dialog.py` | picker, strip, gate, three text edits with Regenerate, official choice | VERIFIED | install button gated at line ~2653 |
| `kicad_lib_manager/widgets/help_dialog.py` | rewritten importing page | VERIFIED | contains Atomic_Footprints |
| `tests/README.md` | fixtures and skips documented | VERIFIED (per plan 10-25 acceptance; not re-grepped) | |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| planner.build_plan | incoming.incoming_issues | planned footprint/model bytes into gate context | WIRED | planner.py ~1457-1480 |
| import_dialog install button | plan.blocked + blocking_reasons | `_refresh` ready flag | WIRED | import_dialog.py ~2630-2653 |
| planner | footprint_index.rank / footprint_text.footprint_facts | official family fallback | WIRED (but unsafe, CR-01) | planner.py ~1062-1073 |
| dialog text edits | InstallOptions.keywords/fp_description/fp_tags | form.build_options | WIRED | plan 10-23 key link, covered by `test_generated_text.py` |
| suggest_library | allowed stems | `allowed_stems()` | WIRED | no manufacturer token can be suggested |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Footprint description / tags | `facts.family` | vendor descr/tags, else official footprint text | Yes for vendor text; unsafe when the official fallback is ambiguous | FLOWING (CR-01) |
| Library suggestion | `SiblingIndex` | KiCad `.kicad_sym` files and own `Custom/` | Yes | FLOWING |
| Gate reasons | `incoming_issues` | planned file bytes | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 10 core tests (suggest, siblings, categories, stems, shared/official/single footprint, gate, incoming check, keywords, footprint text, generated text) | `env/Scripts/python.exe -m pytest tests/test_suggest_atomic.py tests/test_siblings.py tests/test_categories.py tests/test_stems.py tests/test_shared_footprints.py tests/test_official_footprint.py tests/test_single_footprint.py tests/test_install_gate.py tests/test_gate_reasons.py tests/test_incoming_check.py tests/test_keywords.py tests/test_footprint_text.py tests/test_generated_text.py -q -m "not wurth"` | 341 passed | PASS |
| CR-01 reproduction against installed KiCad 10 footprints | `rank(idx, package_code="SOIC127P600X175-8N", limit=3)` then `package_family` over the winner's texts | winner `Package_SO:Infineon_SOIC-20W_7.6x12.8mm_P1.27mm` (score 30, tied with JEITA_SOIC-16 and JEITA_SOIC-8); family `SOIC-20` for an 8-pin code | FAIL |
| CR-01 second case | same with `LQFP48` | winner `Package_QFP:LQFP-100-1EP_14x14mm_P0.5mm_EP6.9x6.9mm` (score 30); family `LQFP-100` | FAIL |
| Unambiguous case still right | same with `DQK0006B` | single hit `Package_SON:Texas_DQK` (30); family `WSON-6` | PASS |

I did not re-run the full `-m "not wurth"` suite; the orchestrator's figures (2920 passed, 4 documented skips; Phase 9 regression 101 passed, 1 skipped) are taken as reported. The `-m wurth` run is outside this verification.

### Probe Execution

Step 7c: SKIPPED. No probe is declared by the Phase 10 plans and no `scripts/*/tests/probe-*.sh` exists.

### Requirements Coverage

All six requirement IDs from the phase are declared in plan frontmatter and map to Phase 10 in REQUIREMENTS.md; no orphaned Phase 10 requirement exists. REQUIREMENTS.md still shows them as `[ ]` / Pending; that checkbox update belongs to phase completion.

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| LIB-04 | 10-03, 10-04, 10-15, 10-18, 10-25 | Suggest `Atomic_<KiCad stem>`: siblings, then category map, then ask; never a manufacturer | SATISFIED (human check 1, 7, 8 pending) | `suggest.py`, `siblings.py`, `categories.py`, tests green |
| LIB-05 | 10-01, 10-02, 10-07, 10-08, 10-09, 10-10, 10-15, 10-25 | Pick or type an `Atomic_` library; official names and manufacturer tokens refused | SATISFIED (human check 4 pending) | `stems.name_verdict`, `test_stems.py` |
| LIB-06 | 10-02, 10-03, 10-07, 10-08, 10-09, 10-11, 10-12, 10-13, 10-14, 10-24, 10-25 | Footprints into `Atomic_Footprints.pretty` or an official footprint; no `.pretty` pairing | SATISFIED (human checks 3, 5, 6 pending; WR-05 edge case below) | planner, shared/official tests |
| LIB-07 | 10-06, 10-16, 10-17, 10-19 to 10-22, 10-25 | Install blocked until atomic; clickable reasons; Value = MPN; fields editable | SATISFIED (human checks 2, 8, 9 pending) | `incoming.py`, dialog gate, gate tests |
| FLD-01 | 10-04, 10-23, 10-25 | Generate `ki_keywords`, editable in the preview | SATISFIED (the migration half belongs to Phase 13) | `keywords.py`, `test_generated_text.py` |
| FLD-03 | 10-05, 10-23, 10-25 | Footprint description and tags: package, IPC name, vendor code, pitch | PARTIAL: implemented, but the family part is affected by Gap 1 | `footprint_text.py`, planner |

Note: FLD-01 and FLD-03 also say "and the migration"; the migration is Phase 13 (MIG-*) and is out of scope for this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `importer/planner.py` | 81-83, 1066-1072 | Guessed family from an ambiguous leading-letters match (CR-01) | BLOCKER (Gap 1) | Wrong text in permanent files |
| `importer/footprint_index.py`, `siblings.py` | 68-72, 108-111, 175-188 | Shared module-level caches mutated from several threads without a lock (WR-01) | WARNING | Rare "Preview could not be built" |
| `importer/keywords.py` | 76-88, 118-120 | English word "can" produces keyword `CAN` (WR-02) | WARNING | Wrong searchable keyword written |
| `manufacturers.py`, `keywords.py` | 57-80, 94-107 | `owner` chain unvalidated; cycle would loop forever (WR-03); needs a bad table edit | WARNING | Hang only after a bad source edit |
| `widgets/import_dialog.py` | 1559, 1574, 1772, 2261, 2312 | Vendor text set as an unescaped tooltip (WR-04, same class as T-10-17) | WARNING | Spoofed tooltip text only |
| `main_window.py` | 828-870 | After a new symbol library, an existing but unlisted `Atomic_Footprints` gets no fp-lib-table entry or hint (WR-05) | WARNING | Edge case; KiCad shows an unresolved footprint library |
| info | - | IN-01 to IN-03 (shared mutable defaults, 4-space sibling indent, stale picker ranking) | INFO | Cosmetic or robustness |

No `TBD`, `FIXME`, `XXX`, `TODO` or `HACK` markers in `kicad_lib_manager/`. The review warnings and info items are all still `open` in `10-REVIEW-DISPOSITION.md`; they are advisory for this verdict and should be triaged in the gap-closure round. The security audit reports `threats_open: 0` (T-10-17 low, accepted).

### Human Verification Required

`workflow.human_verify_mode` is `end-of-phase`: the `<human-check>` of plan 10-25 Task 2 is the phase's human gate for ROADMAP criteria 1-5. It is collected below with its setup and exact expected text. Run it on the scratch copy only, never on the live `Custom/` or the real KiCad library tables. Change from the plan text: in check 10 add the scratch libraries to the Project library table only, never Global (security audit note: Global edits the owner's real tables).

#### Setup

**S1. Build the scratch repo.**
PowerShell, from the repo root:
`$env:KICAD_ATOMIC_UAT_DIR = "$env:TEMP\kicad_atomic_uat"`
`env\Scripts\python.exe -m pytest tests/test_atomic_uat.py -k uat_atomic_scratch -s`
The output holds a line "Run the app on it: <command>". The "Check in the app:" lines after it belong to the Phase 9 check, so skip them.

**S2.** `mkdir "$env:TEMP\kicad_atomic_uat\tables"`

**S3.** Run the printed command. In the main window's toolbar set "Destination:" to the tables folder of S2. If the app offers to change KiCad's path variables at any point, click No.

#### Checks (the number in brackets is the ROADMAP criterion)

1. **[1] CSD sample suggestion.** Ctrl+I (Import Part...), pick `downloaded_examples\ul_CSD85301Q2.zip`.
   Expected: the library field reads `Atomic_Transistor_FET`. Hover the field: tooltip "Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2)." The badge next to it reads "new - creates .kicad_sym". There is no amber token line under the field.

2. **[4] Gate reason jumps and clears.** Read the amber strip.
   Expected: it reads "⚠ Install is blocked: Type a Description". Click "Type a Description": the cursor is in the Description field and its frame is amber. Type "Dual N-channel MOSFET 30 V": the reason and the frame go at once, and Install Part enables after the preview updates.

3. **[3, 4, 5] Fields, footprint link and generated text.**
   Expected: Value is greyed out and reads CSD85301Q2. Manufacturer reads Texas Instruments. The Footprint field reads `Atomic_Footprints:DQK0006B`. Files lists `Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod` and nothing named `Atomic_Transistor_FET.pretty`. Footprint description reads "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B". Footprint tags contain WSON-6, DQK0006B and P0.65mm. Keywords contain Transistor, FET, TI and Texas.

4. **[2] Name refusals and picker.** Type each name into the library field and read the strip.
   Expected: "Transistor_FET" gives "Transistor_FET is the name of a KiCad library; use Atomic_Transistor_FET". "Atomic_TI" gives "Atomic_TI is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET". "atomic_transistor_fet" then Tab turns the text into Atomic_Transistor_FET with the grey note "Spelling corrected to Atomic_Transistor_FET" under the field. Type "fet": the list shows only names containing fet. Open the dropdown: your Atomic_ libraries first, a divider, then the rest; no IC_... or Connector_..._GCT name.

5. **[3] Official KiCad footprint.** Click "Use an official KiCad footprint".
   Expected: `Package_SON:Texas_DQK` is first in the list; pick it. The Footprint field reads `Package_SON:Texas_DQK`. Not used lists DQK0006B ("footprint, not installed: an official KiCad footprint is used") and DLV0006A.stp ("3D model, not installed: KiCad's own 3D model is used"). The footprint name and the two footprint text fields are greyed with "KiCad's own footprints are never changed". No pad warning appears. Click "Install the vendor footprint into Atomic_Footprints" to switch back.

6. **[3] Install.** Click Install Part.
   Expected: the result banner reads "✓ Installed CSD85301Q2 into Atomic_Transistor_FET". The Library tables row reads "Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table" (the scratch repo has Atomic_Footprints.pretty, and the empty tables folder of S2 does not list it, so it is added). The tables folder of S2 now holds `sym-lib-table` and `fp-lib-table`.

7. **[1, 4] RECOM sample from the category map.** Click Change..., pick `downloaded_examples\LIB_RS3-1212S_H3.zip`.
   Expected: the library field reads `Atomic_Converter_DCDC_Isolated`; hover it: "Suggested from the vendor category Power Supply and the description." Field changes shows "Set Manufacturer" with "RECOM Power → RECOM: canonical spelling". Install Part enables without typing anything.

8. **[1, 4] Importer asks when it cannot place a part.** Click Change..., pick `downloaded_examples\ul_ATXK-H14-D-32-768KHZ-E50-T3.zip`.
   Expected: the library field is empty with the grey hint "Pick a library, or type Atomic_ and a KiCad library name". The strip lists "Pick or type a library name", "Enter the Manufacturer", "The Datasheet must be a link or a file path" and a reason starting "3D model:". Click the 3D model reason: the focus goes to the Add 3D model... button.

9. **[4] 3D model clears its reason.** Click Change..., pick `downloaded_examples\USB4145-03-0170-C_REVA2.zip`.
   Expected: the library field reads `Atomic_Connector`. The strip lists "Enter a Datasheet link" and a reason starting "3D model:". Click Add 3D model..., pick `downloaded_examples\194150990-659-usb4145-03-0170-c.zip`: the 3D model reason goes away.

10. **[5] Installed files carry what the preview showed (KiCad 10, Project table only).** In KiCad 10: Symbol Editor, File > Add Library..., pick `<scratch>\Custom\Symbols\Atomic_Transistor_FET.kicad_sym` and add it to the **Project** library table only, never Global. Open CSD85301Q2's Symbol Properties.
    Expected: Keywords equal the Keywords of check 3.
    Then Footprint Editor, add `<scratch>\Custom\Footprints\Atomic_Footprints.pretty` to the **Project** table only, open DQK0006B's Footprint Properties.
    Expected: Description and Keywords equal the footprint description and tags of check 3. Remove both libraries from the Project library table afterwards.

11. **Owner decision.** Say whether to keep or change: strict majority for sibling votes, ATXK-H14 asking instead of suggesting Atomic_Oscillator, the measured "2.1x2.1 mm" instead of KiCad's nominal "2x2 mm", and the IPC-style tag `WSON-6_2.1x2.1mm_P0.65mm`.

### Gaps Summary

One gap, from the code review's CR-01, confirmed by reproduction: the official-footprint family fallback in `planner.py` accepts a leading-letters-only match (score 30) without checking it is unique, so a vendor package code such as `SOIC127P600X175-8N` or `LQFP48` can write another package's family and pin count (`SOIC-20`, `LQFP-100`) into the footprint description, tags and symbol keywords. This breaks the D-28 prohibition of plan 10-05 and the family truth of plan 10-23. The five ROADMAP criteria are met in code and tests. After the fix (require score >= 50, or a unique top score, plus an ambiguity test) a re-verification should pass the automated checks, and the status then becomes human_needed until the owner runs the checklist above. The five open warnings and three info items are advisory; WR-02 (`CAN` keyword) and WR-05 (fp-lib-table hint) change written output or table state and are worth closing in the same gap-closure round.

---

_Verified: 2026-10-28_
_Verifier: Claude (gsd-verifier)_
