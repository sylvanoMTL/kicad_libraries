---
phase: "7"
slug: "snapeda-and-samacsys-adapters"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-23"
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor zip -> staged symbol text | The staged .kicad_sym is untrusted text read by the adapter head sniff and the planner | untrusted vendor text |
| zip / folder member -> intake memory | Non-staged marker members (how-to-import.htm, part_info.txt, license.txt, version.bin) are read, bounded, for detection | untrusted vendor bytes, held in memory only |
| part_info.txt / license.txt text -> metadata and scores | Vendor text becomes PartMeta values, a category token and detection points | untrusted vendor text |
| vendor symbol properties -> installed library | Untrusted property names and values decide which fields are dropped, cleaned or renamed | untrusted vendor text written to the owner's library |
| plan -> preview | The owner approves the install from the preview rows, including "Field changes" | install plan |
| detected vendor -> commit message | The adapter label becomes the `Import-Vendor:` trailer | fixed adapter label |
| local vendor zips / synthetic fixtures -> public GitHub repo | Licence-restricted downloads must never be committed; synthetic fixtures are published | licence-restricted files |
| install -> Custom/ | A failed install must leave the library as it was | owner's library files |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-07-01 | Denial of Service | `SnapEDAAdapter.detect` on hostile or missing staged files | medium | mitigate | `read_head` bounded to `SNIFF_BYTES` (64 KiB) x `SNIFF_FILES` (8), returns b"" on OSError (`adapters/base.py`); test_snapeda_detect_survives_unreadable_symbol | closed |
| T-07-02 | Information Disclosure | real vendor zips in the public repo (D-01) | high | mitigate | `.gitignore` `downloaded_examples/*` + `!downloaded_examples/ul_CSD85301Q2.zip`; `git ls-files downloaded_examples` lists only the UL sample; test_vendor_zips_stay_local | closed |
| T-07-03 | Tampering | planner `remove_property_edit` spans | medium | mitigate | one edit per property, overlap check in `apply_edits`, edited unit re-parsed; test_snapeda_volatile_fields_dropped, test_remove_property_edit_basic (LF and CRLF) | closed |
| T-07-04 | Tampering | lookalike package labelled SnapEDA to trigger drops | low | mitigate | drops touch only the incoming symbol and each is a preview row before any write; test_field_changes_section | closed |
| T-07-05 | Tampering | placeholder rule stripping KiCad-reserved fields | medium | mitigate | `fieldrules.is_protected` keeps standard fields and every `ki_*` name; test_protected_fields_never_dropped, test_ul_property_list_unchanged_by_cleanup | closed |
| T-07-06 | Repudiation | a field changed without the owner seeing it | medium | mitigate | every drop, clean and rename is a FieldChange and a preview row; test_snapeda_symbol_cleaned, test_field_change_rows | closed |
| T-07-07 | Tampering | placeholder alias ("N/A") becoming the Manufacturer token | low | mitigate | placeholders count as absent in part_meta and role(); test_placeholder_alias_is_absent | closed |
| T-07-08 | Tampering | cleanup reaching symbols already in Custom/ | medium | mitigate | edits run on the cut incoming unit only; test_cleanup_never_touches_existing_symbols | closed |
| T-07-09 | Denial of Service | oversized or decompression-bomb marker member | medium | mitigate | read after unchanged `_prescan` and Phase 3 caps; `MAX_MARKER_BYTES` (64 KiB), `MAX_MARKERS` (16), INFO skip beyond cap; test_marker_over_cap_skipped, test_marker_limits | closed |
| T-07-10 | Tampering | a marker written to disk or used as a path | high | mitigate | markers are in-memory bytes keyed by name, STAGE_KINDS unchanged; test_markers_held_in_memory_only | closed |
| T-07-11 | Denial of Service | corrupt marker member turning into a refusal or exception | medium | mitigate | reads wrapped, become INFO `intake.marker_skipped`, decode with errors="replace"; test_marker_corrupt_member_skipped, test_marker_text_shallowest | closed |
| T-07-12 | Information Disclosure | real vendor zips committed while tests read them | high | mitigate | real-sample tests read zips via open_package staging outside the repo; test_vendor_zips_stay_local | closed |
| T-07-13 | Tampering | part_info values with quotes/newlines/control characters reaching symbol, preview or commit | medium | mitigate | parse_part_info strips control characters, caps keys at 40 and values at 200 characters; values reach symbol text only through planner quoting; test_part_info_parse_caps | closed |
| T-07-14 | Tampering | PartCategory used verbatim as a library Type token | medium | mitigate | only `PART_CATEGORY_TYPE` keys produce a token; test_unmapped_category_falls_back | closed |
| T-07-15 | Denial of Service | huge or hostile part_info.txt | low | mitigate | 64 KiB marker cap, 100-line parse cap, detect never raises; test_part_info_oversized_is_skipped, test_samacsys_detect_survives_hand_built_package | closed |
| T-07-16 | Repudiation | D-16 summary hiding which files were not imported | low | mitigate | summary names folders and total; `candidate.ignored` keeps every member; test_folder_summary_replaces_list | closed |
| T-07-17 | Information Disclosure | synthetic fixtures copying vendor bytes into the public repo | high | mitigate | test_fixture_originality (SHA-256 against every real member plus real-part-name guard, ran against both real zips), test_fixture_members_small (4096-byte cap) | closed |
| T-07-18 | Tampering | failed vendor install leaving Custom/ half-written | medium | mitigate | INST-07 rollback; test_vendor_install_rolls_back_on_failed_write asserts byte-identical snapshot and no temp file | closed |
| T-07-19 | Information Disclosure | real zips read by tests ending up in the repo | high | mitigate | real members read in memory, staged outside the repo; test_vendor_zips_stay_local | closed |
| T-07-20 | Tampering / Elevation | `package.open_model_source` zip branch (G-07-2) | high | mitigate | reuses `_open_zip` / `_stage_zip` / `_prescan` unchanged with `kinds=MODEL_SOURCE_KINDS`, staging outside the repo; test_model_zip_hostile_refused, test_model_zip_nested_one_level. Residual (zip opened by path with no handle re-check) logged as AR-07-03 | closed |
| T-07-21 | Information Disclosure / Tampering | `package._open_model_file` bare model read in place | medium | mitigate | no-follow `_lstat`; `S_ISLNK` and `FILE_ATTRIBUTE_REPARSE_POINT` refused (`intake.link_refused`); `S_ISREG` required; opened handle `(st_dev, st_ino)` must match; "rb" only; test_bare_model_symlink_refused (skips without the symlink privilege), test_bare_model_reparse*, test_bare_model_handle* | closed |
| T-07-22 | Denial of Service | `open_model_source` size handling | medium | mitigate | `MAX_MEMBER_BYTES` on the lstat size and on real counted bytes; zip caps unchanged; test_bare_model_oversize_refused | closed |
| T-07-23 | Spoofing / Tampering | `adapters.base.attach_models` | medium | mitigate | every second-source model passes `_check_model` (ISO-10303-21; / #VRML magic) before attach; test_attach_rejects_wrong_magic, test_attach_keeps_good_drops_bad | closed |
| T-07-24 | Tampering | bare model edited between preview and install | medium | mitigate | applier source SHA-256 re-check reused unchanged (six contract modules unchanged since c2b75c8); test_attach_source_edited_after_preview, test_attach_zip_closed_before_install | closed |
| T-07-25 | Information Disclosure | attach Issue texts naming local folders | low | mitigate | `intake.model_attached` / `no_model_in_source` texts use `source.name` only; test_attach_zip_model | closed |
| T-07-26 | Denial of Service | per-model-source byte budget | low | accept | AR-07-02 | closed |
| T-07-27 | Denial of Service / Tampering | model package lifetime in the dialog | medium | mitigate | packages close only in `_discard_package` (Change..., open, close) and `_shutdown`, never during install; test_add_model_package_open_until_install_ends, test_add_model_close_while_reading_closes_package | closed |
| T-07-28 | Tampering | late attach result after Change... or during close | medium | mitigate | session counter plus closing / installing / page guards close and drop the result; test_add_model_result_after_change_is_dropped | closed |
| T-07-29 | Tampering | Install from a preview that does not show the model yet | medium | mitigate | `_updating()` counts `_model_worker`, so Install shows Updating until the plan is current; test_add_model_blocks_install_while_reading | closed |
| T-07-30 | Tampering / Spoofing | `_model_note` rendering untrusted names | low | mitigate | `Qt.TextFormat.PlainText`; test_add_model_note_is_plain_text | closed |
| T-07-31 | Information Disclosure (licence) | real SnapEDA model zip `194150990-659-usb4145-03-0170-c.zip` | high | mitigate | `downloaded_examples/*` ignore rule; test_vendor_zips_stay_local asserts check-ignore for it and that `git ls-files downloaded_examples` lists only the UL sample; no commit of 07-07..07-09 touches `downloaded_examples/` | closed |
| T-07-32 | Information Disclosure (licence) | synthetic SnapEDA model fixture | medium | mitigate | test_fixture_originality[snapeda_model] hashes every real model-zip member against the synthetic members and rejects the real part name in both cases; members < 4096 bytes | closed |
| T-07-33 | Tampering | install while a model source was rejected (`_form_status`, `blocking_reasons`) (G-07-5) | medium | mitigate | rejection held as `RejectedModel`, routed into `FormStatus.model_error`, a blocking `Error:` Reason until Remove or a usable attach; test_add_model_rejection_blocks_install, test_blocking_reasons_model_error | closed |
| T-07-34 | Spoofing / Tampering | red note, strip reason, Remove tooltip | low | mitigate | note stays `Qt.TextFormat.PlainText`, strip escapes every reason (T-05-27), Remove tooltip is static text; test_add_model_note_is_plain_text | closed |
| T-07-35 | Tampering | partly bad model zip (`attach_models`) | medium | mitigate | a source with any file failing the magic check is rejected whole (`intake.unusable_model_in_source` / `intake.no_model_in_source`), texts name member files only; tests in test_model_attach.py | closed |
| T-07-36 | Denial of Service | stale model failure or rejection across Change... / open | low | mitigate | `_on_model_failed` checks the bound session; `_clear_items` resets the rejection; test_add_model_stale_failure_does_not_block, test_add_model_rejection_reset_by_change | closed |
| T-07-37 | Denial of Service | staging folder of a rejected zip | low | mitigate | rejected package closed at once, dialog keeps only the name and Issue; test_add_model_refusal_shows_note asserts the staging folder is gone | closed |
| T-07-38 | Tampering | `PreviewTree` column layout hiding text past the edge (G-07-7) | low | mitigate | Item clamped so Detail keeps `MIN_COLUMN_WIDTH` (120 px), Detail stretches and elides with the full text in the cell tooltip; test_preview_columns_fit_at_900_and_1400, test_item_clamped_when_tree_narrows | closed |
| T-07-39 | Spoofing / Tampering | rich-text strip tooltip (G-07-8) | low | mitigate | every reason and the hint `html.escape`d, only fixed p/br/i tags added, strip still accepts only `reason:<digits>` hrefs; test_strip_tooltip_single_reason_decodes_entities | closed |
| T-07-40 | Tampering | install after a failed model read (`_on_model_failed`) | medium | mitigate | a current-session read failure is held as a `RejectedModel` and routed into `model_error`; test_add_model_worker_failure_logged | closed |
| T-07-SC | Tampering | npm/pip/cargo installs | high | accept | no package is installed by any Phase 7 plan (RESEARCH Package Legitimacy Audit: nothing to audit) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-SC | No third-party package was added in this phase; the dependency set (PySide6, pytest, pytest-qt) is unchanged, so there is no supply-chain surface to mitigate | plan-time threat model (07-01..07-06 PLAN.md) | 2026-10-23 |
| AR-07-02 | T-07-26 | Each model source gets its own budget and temp staging folder outside the repo, removed on Change... or close; every source is an explicit user pick and bare files are never staged | plan-time threat model (07-07 PLAN.md) | 2026-10-24 |
| AR-07-03 | T-07-20 (residual) | The model zip is lstat'ed (link or reparse point refused) and then opened by path with no handle-identity re-check, unlike the bare-file branch. Acceptable because `_stage_zip` fully checks every member of whatever file is actually read, and the path is the user's own pick | plan-time threat model (07-07 PLAN.md) | 2026-10-24 |
| AR-07-04 | T-07-SC (07-07..07-09) | Gap closure added no third-party package (stdlib and PySide6 only) | plan-time threat model (07-07..07-09 PLAN.md) | 2026-10-24 |
| AR-07-05 | T-07-SC (07-10..07-13) | Gap closure added no third-party package (stdlib and PySide6 only) | plan-time threat model (07-10..07-13 PLAN.md) | 2026-10-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-23 | 20 | 20 | 0 | secure-phase (L1 short-circuit: register authored at plan time, every named mitigation test present and green in the main checkout with both real zips and kicad-cli present) |
| 2026-10-24 | 41 | 41 | 0 | secure-phase after gap closure 07-10..07-13 (L1 short-circuit: T-07-33..T-07-40 registered at plan time, medium/low only, every mitigation grep-found and its named tests green in the main checkout) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-23; re-verified 2026-10-24 after gap closure 07-10..07-13

## Security Audit 2026-10-23

| Metric | Count |
|---|---|
| Threats found | 33 |
| Closed | 33 |
| Open | 0 |

## Security Audit 2026-10-24

| Metric | Count |
|---|---|
| Threats found | 41 |
| Closed | 41 |
| Open | 0 |
