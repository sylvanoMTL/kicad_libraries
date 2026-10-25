---
phase: "01"
slug: "foundation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-18"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| disk file -> fsutil.decode_source | KiCad files (owner's now, vendor-supplied from Phase 3) enter as bytes and must not be silently changed | KiCad library text (owner data) |
| file text -> sexpr.parse | Hostile nesting or size must not crash or hang the parser | Untrusted S-expression text |
| user/vendor value -> sexpr.quote -> library file | A value must never break out of its string and inject structure | Property values |
| edited text -> atomic write / fsutil.atomic_write_bytes -> filesystem | The only write path; a partial or wrong write would damage a library file | Library and config file bytes |
| fsutil.backup_file -> backup directory | Backups must not land in a tracked tree | Copies of library files |
| KiCad file text -> kicad_files locators | Later phases act on what locators return; a wrong node means a wrong edit | Node spans |
| tests/fixtures -> GUI library scan -> user's real lib tables | Fixture libraries must never be offered to Select All + Generate | Library nicknames |
| working tree -> git (core.autocrlf=true) | Git must not rewrite fixture bytes on add/checkout | Fixture bytes |
| downloaded_examples/ -> git; vendor zip -> test process | Untrusted vendor archive becomes tracked content; members enter memory | Third-party archive |
| owner's %APPDATA%/kicad tables -> test process -> test output | Personal configuration must not leave the config dir via ids, messages or copies | Personal config (sensitive) |
| test suite -> owner's machine | Tests must not touch real KiCad config, app-data or Custom/ | Local files |
| PyPI -> env/ | Three pinned packages installed into the project venv | Third-party code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | fsutil.atomic_write_bytes | high | mitigate | `open(tmp, "xb")` + `os.fsync` + single `os.replace` (fsutil.py:95-99); tracer asserts no temp and untouched bytes identical | closed |
| T-01-02 | Tampering | fsutil.decode_source / encode_source | high | mitigate | Bytes-only I/O, `SourceText.bom`, strict UTF-8 `fs.bad_encoding`, `fs.mixed_eol` flagged never normalised (fsutil.py:21-51) | closed |
| T-01-03 | Denial of Service | sexpr.parse | medium | mitigate | Explicit stack, no recursion (sexpr.py:64-65); stress tests in tests/test_sexpr.py | closed |
| T-01-04 | Tampering | downloaded_examples/ul_CSD85301Q2.zip | medium | mitigate | Tracked by explicit path; SHA-256 pinned `ZIP_SHA256` (tests/test_roundtrip_corpus.py:23) | closed |
| T-01-05 | Repudiation | git staging | medium | mitigate | Explicit-path staging; `git ls-files -- reports research_notes` empty (verified post-merge) | closed |
| T-01-06 | Tampering | atomic_write_bytes on locked/read-only target | high | mitigate | `os.access` read-only pre-check returns `fs.read_only` (fsutil.py:85-88); retry then `fs.locked`; tests/test_fsutil.py:59 | closed |
| T-01-07 | Information Disclosure | backup_file destination | medium | mitigate | Caller-chosen dir; `default_backup_dir` under LOCALAPPDATA (fsutil.py:182-191) | closed |
| T-01-08 | Denial of Service | retry loop | low | accept | ~1 s worst case per locked file; `_RETRY_DELAYS` injectable (fsutil.py:15,80) — see Accepted Risks | closed |
| T-01-09 | Tampering | temp files beside libraries | low | mitigate | Unique `.name.pid.hex.tmp` names, exclusive create (fsutil.py:91) | closed |
| T-01-10 | Tampering | concurrent writers to one target | medium | mitigate | Distinct temp per call + single replace; `test_concurrent_writers_leave_one_complete_payload` (tests/test_fsutil.py:154) | closed |
| T-01-11 | Denial of Service | sexpr.parse on deep or huge input | medium | mitigate | Iterative parse; 100k-deep test (tests/test_sexpr.py:178) and large-input test | closed |
| T-01-12 | Tampering | sexpr.quote | high | mitigate | Single-pass `translate` escape table (sexpr.py:121-123); `unquote(quote(s)) == s` tests (tests/test_sexpr.py:374) | closed |
| T-01-13 | Tampering | apply_edits | medium | mitigate | Out-of-range / overlapping edits raise `ValueError` (sexpr.py:107) | closed |
| T-01-14 | Tampering | library_scanner SKIP_DIRS | high | mitigate | `"tests"` in SKIP_DIRS (library_scanner.py:13), commit 901e3be precedes fixture commit 6ddcbb1; tests/test_scanner_skip_dirs.py | closed |
| T-01-15 | Tampering | fixture bytes under core.autocrlf=true | medium | mitigate | `.gitattributes` `tests/fixtures/** -text`; `git check-attr` self-test (tests/test_fixtures.py:113) | closed |
| T-01-16 | Information Disclosure | fixture content | low | mitigate | Fixtures are synthetic, generated by tests/fixtures/build_fixtures.py (01-04-SUMMARY) | closed |
| T-01-17 | Tampering | find_symbol / find_property name matching | medium | mitigate | Exact `unquote` equality, direct/top-level children only (kicad_files.py:99); sub-symbol rejection tests | closed |
| T-01-18 | Tampering | edits on mixed-EOL or BOM files | high | mitigate | `normalize_eol` on inserted text, BOM/mixed-EOL fixtures in tests/test_edits.py:160 | closed |
| T-01-19 | Tampering | interrupted write of an edited file | high | mitigate | Injected permanent `PermissionError` returns `fs.locked`, original intact (tests/test_edits.py:390-396) | closed |
| T-01-20 | Elevation of Privilege | layering | low | mitigate | Subprocess + AST checks reject Qt and upward imports (tests/test_layering.py) | closed |
| T-01-21 | Information Disclosure | local_kicad round-trip tests | high | mitigate | Read in place, ids `local/<ver>/<file>` (tests/test_roundtrip_corpus.py:177), no write leg | closed |
| T-01-22 | Denial of Service | zip member reads | medium | mitigate | `info.file_size > cap` check before read, 5 MB cap; boundary test at cap and cap-1 (tests/test_roundtrip_corpus.py:36,127-138) | closed |
| T-01-23 | Tampering | UL sample integrity | medium | mitigate | SHA-256 pinned; no `extract`/`extractall` anywhere in tests or package | closed |
| T-01-24 | Denial of Service | multi-MB Wurth corpus | low | accept | `wurth` marker gate + 60 s budget test — see Accepted Risks | closed |
| T-01-SC | Tampering | pip install of PySide6 / pytest / pytest-qt | high | mitigate | Exact `==` pins in requirements*.txt (D-14, owner-approved D-17); `test_requirements_are_exact_pins` and installed-version checks (tests/test_manifests.py) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01-01 | T-01-08 | Worst case is a ~1 s wait per locked file; read-only targets skip the loop; injectable sleep keeps tests fast | Plan 01-02 threat model (owner-approved plan) | 2026-10-18 |
| AR-01-02 | T-01-24 | Wurth corpus is opt-in behind the `wurth` marker; a 60 s parse-budget test reports regressions when the submodule is present | Plan 01-06 threat model (owner-approved plan) | 2026-10-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-18 | 25 | 25 | 0 | /gsd-secure-phase (orchestrator, ASVS L1 grep-depth short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-18
