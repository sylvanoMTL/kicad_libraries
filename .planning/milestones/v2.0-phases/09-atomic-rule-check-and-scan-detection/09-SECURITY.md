---
phase: "9"
slug: "atomic-rule-check-and-scan-detection"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-26"
---

# Phase 9 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| library files -> scan and check | `.kicad_sym` / `.kicad_mod` text from `Custom/`, WurthElektronik and the KiCad install is parsed on every scan | untrusted S-expression text, size and node capped |
| scan text -> Qt widgets | Symbol names, field values and reasons are shown in tree rows, tooltips and dialog labels | untrusted text, escaped or shown as plain text |
| scanner -> git | Change detection asks the `Custom` checkout what changed since HEAD | read-only git output (status paths, HEAD blobs) |
| fix engine -> `Custom/` files | One-click fixes rewrite owner library files and copy 3D models | owner library files, backed up and written atomically |
| user input -> fix engine | Typed Datasheet, Description and a picked 3D model file become fixes | untrusted strings and a user-chosen file |
| UAT helper -> filesystem and git | The opt-in UAT builder copies the live `Custom/` into a scratch repo and commits there | owner library files (read only), scratch repo writes |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-09-01 | Tampering | `manufacturers._index` | medium | mitigate | `raise ValueError` at import when two entries fold to one key (`kicad_lib_manager/manufacturers.py`); pinned by `tests/test_manufacturers.py` | closed |
| T-09-02 | Tampering | `suggest.MANUFACTURER_ALIASES` | low | mitigate | `MANUFACTURER_ALIASES = token_map()` in `importer/suggest.py`; all 20 v1.0 keys pinned by a test | closed |
| T-09-03 | Tampering | `_on_sym_item_changed` | medium | mitigate | Child rows return early (`widgets/library_table.py:299`); selection-safety tests in `tests/test_library_table_atomic.py` | closed |
| T-09-04 | Spoofing | tooltips built from scan text | low | mitigate | `_rich_tip` escapes every line with `html.escape` | closed |
| T-09-05 | Denial of service | `check_libraries` parse | medium | mitigate | `MAX_KICAD_TEXT_BYTES` before reading and `max_nodes` on parse in `atomic_check.py`; a broken library becomes `check_problem` | closed |
| T-09-06 | Information disclosure | `datasheet_problem` | low | mitigate | Datasheet string-matched only; ast test forbids `urllib`, `http`, `socket`, `webbrowser`, `subprocess` in `atomic_check` (`tests/test_atomic_scan.py:250`) | closed |
| T-09-07 | Tampering | fix specs for non-Custom libraries | medium | mitigate | Fixes and fills only for source Custom; tested on `Atomic_Elsewhere`; re-checked by the fix engine (T-09-13) | closed |
| T-09-08 | Tampering | `repo_context` resolver | medium | mitigate | Exact `os.listdir` matches before any path is built; segment walk refuses empty, `.` and `..`; wrong-case and dotted inputs tested | closed |
| T-09-09 | Denial of service | footprint parse in the model rule | low | mitigate | Size and node caps; listings and verdicts cached per scan, each footprint parsed once | closed |
| T-09-10 | Elevation of privilege | git invocation in `mark_changes` | high | mitigate | `changes.py` uses only `gitops` (`find_git`, `show_toplevel`, `status_entries`, `head_blob`); no `subprocess` import; pinned by an ast test | closed |
| T-09-11 | Denial of service | HEAD and work-tree parse | medium | mitigate | Size and node caps on both versions in `changes.py`; oversized file skipped with one INFO line (tested) | closed |
| T-09-12 | Tampering | status paths -> file reads | low | mitigate | A status path is read only when it equals the `rel_path` of a library the scan already found under `Custom/` | closed |
| T-09-13 | Tampering | `build_preview` containment | high | mitigate | Every target must resolve strictly inside `Custom/` (`atomic_fixes.py`); Wurth, absolute, dotted, backslash, drive-less and sibling paths refused (tested) | closed |
| T-09-14 | Tampering | lost update (D-16) | high | mitigate | SHA-256 of full bytes at preview, compared immediately before writing; mismatch refuses the whole batch (one-byte change tested) | closed |
| T-09-15 | Tampering | partial multi-file write | high | mitigate | `backup_file` first, `atomic_write_text`, restore of earlier files on failure; injected write failures tested | closed |
| T-09-16 | Tampering | hostile model source | high | mitigate | `open_model_source` intake checks, `close()` in `finally`, SHA-256 verified before copying | closed |
| T-09-17 | Tampering | model name clash | medium | mitigate | Casefolded exact listing; same bytes reused, different bytes refused, never overwritten | closed |
| T-09-18 | Tampering | apply without preview | high | mitigate | `apply_preview` has exactly one caller, the preview page's Apply (`widgets/atomic_check_dialog.py:366`); tested by recording calls | closed |
| T-09-19 | Tampering | KiCad overwriting fixes (D-16) | medium | mitigate | Running warning on the preview page; stale refusal via T-09-14 (tested) | closed |
| T-09-20 | Spoofing | rich text in rows and labels | low | mitigate | Labels use `Qt.TextFormat.PlainText`; rows are plain `QTreeWidgetItem` text | closed |
| T-09-21 | Tampering | typed Datasheet value | low | mitigate | Goes through `complete_fill` and `datasheet_problem` before becoming a fix; never fetched | closed |
| T-09-22 | Tampering | `build_atomic_uat` | high | mitigate | Source only read; dest inside or containing the repo refused; source/scratch containment refused; old scratch removed only with the helper's marker (`tests/test_atomic_uat.py`) | closed |
| T-09-23 | Elevation of privilege | scratch git commit | low | mitigate | git run with `GIT_*` stripped, an empty global config, no system config, identity/signing/autocrlf by `-c` | closed |
| T-09-SC | Tampering | npm/pip/cargo installs | low | accept | No packages installed in this phase (RESEARCH Package Legitimacy Audit: none) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-01 | T-09-SC | Phase 9 adds no third-party package; nothing to vet | plan-time register (all eight plans) | 2026-10-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-26 | 24 | 24 | 0 | /gsd-secure-phase 9 (L1 grep evidence, auditor skipped by the short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-26
