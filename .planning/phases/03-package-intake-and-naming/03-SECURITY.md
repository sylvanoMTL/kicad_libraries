---
phase: "3"
slug: "package-intake-and-naming"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
register_authored_at_plan_time: true
created: "2026-10-19"
---

# Phase 3 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Vendor package → importer | Zip or loose folder downloaded from a third-party site (Ultra Librarian, SnapEDA, SamacSys, unknown) | Untrusted member names, header sizes, flags, file contents, embedded names and URLs |
| Importer → system temp staging | Zip members copied to a `TemporaryDirectory` outside the repo | Untrusted bytes under generated names (`sym_000.kicad_sym`, ...) |
| Importer → user-picked folder | Folder read in place, read-only | Untrusted file tree, possibly with symlinks/junctions or huge depth |
| Importer → `Custom/` listing | Read-only listing of existing library names | Repo file names only |
| Candidate → Phase 4 install | Names proposed for files Phase 4 will write | Sanitised name beside verbatim original (`name_check`) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | staging folder placement | high | mitigate | `is_relative_to(repo_root.resolve())` check, `intake.staging_in_repo` refusal after cleanup (`package.py`, `tests/test_package_zip.py`) | closed |
| T-03-02 | Tampering | staged paths from member names (zip slip) | high | mitigate | generated staged names, `open(target, "xb")`, members opened by `ZipInfo`; no `extract`/`extractall` in `importer/` (layering guard) | closed |
| T-03-03 | Information disclosure | temp files left behind | medium | mitigate | `TemporaryDirectory(ignore_cleanup_errors=True)`, idempotent `close()` on exit and every refusal; cleanup tests | closed |
| T-03-04 | Elevation of privilege | bundled HTML guides | medium | mitigate | HTML never written or opened; listed in `intake.ignored_members` only | closed |
| T-03-05 | Denial of service | oversize member during copy | medium | mitigate | `_copy_member` counts real bytes against `MAX_MEMBER_BYTES` and remaining budget | closed |
| T-03-06 | Tampering | zip slip via `..`, absolute, drive, UNC, backslash names | high | mitigate | `_hostile_reason` on normalised name, whole-package refusal in `_prescan` before any read | closed |
| T-03-07 | Tampering | symlink or reparse-point members | high | mitigate | `S_ISLNK(external_attr >> 16)` and 0x400 bit refuse the package; staged files written from bytes | closed |
| T-03-08 | Denial of service | zip bomb (count, size, total, ratio) | high | mitigate | `MAX_MEMBERS`, `MAX_MEMBER_BYTES`, `MAX_TOTAL_BYTES`, `_ratio_exceeded` on declared sizes; boundary tests | closed |
| T-03-09 | Denial of service | headers lying about sizes | medium | mitigate | real-byte counting against `_Budget`; CRC / `BadZipFile` mapped to `intake.corrupt`. Gap (code review CR-02): corrupt LZMA payload raises `LZMAError` out of `open_package` | open — below high threshold (non-blocking) |
| T-03-10 | Spoofing | duplicate / case-colliding members | medium | mitigate | casefolded duplicate refusal; members opened by `ZipInfo` | closed |
| T-03-11 | Tampering | `name:stream` ADS and control characters | medium | mitigate | `:` (D-19) and control characters refuse the package | closed |
| T-03-12 | Denial of service | recursive nested zips | medium | mitigate | one level only, `intake.nested_too_deep`, shared `_Budget` | closed |
| T-03-13 | Information disclosure | encrypted members | low | mitigate | `intake.encrypted` refusal from the flag bit | closed |
| T-03-14 | Tampering | hostile names inside KiCad files | medium | transfer | Phase 3 never turns a name into a path; `name_check` (03-05) exposes the sanitised form; Phase 4 write-time containment check owns paths | closed |
| T-03-15 | Denial of service | huge in-place file read in `locate` | medium | mitigate | `_read_limited` reads at most `MAX_MEMBER_BYTES + 1` and skips with a WARNING. Gap (code review CR-01): the 100 MB model cap also applies to parsed `.kicad_sym`/`.kicad_mod` text, so the pure-Python parser can take minutes and GBs; needs a smaller text cap | open — below high threshold (non-blocking) |
| T-03-16 | Denial of service | malformed / deep S-expressions | low | mitigate | iterative Phase 1 parser; errors mapped to `intake.unreadable_file` | closed |
| T-03-17 | Spoofing | package imitating Ultra Librarian markers | low | accept | see Accepted Risks Log AR-03-01 | closed |
| T-03-18 | Tampering | KiCad 5 `(module` footprint passed as v6+ | low | mitigate | root head recorded; WARNING `intake.legacy_footprint_syntax` (D-18) | closed |
| T-03-19 | Tampering | traversal through names | high | mitigate | `sanitize_name` maps everything outside `A-Za-z0-9_.-` to `_`, strips leading dots; single path component | closed |
| T-03-20 | Denial of service | Windows reserved device names | medium | mitigate | `_` appended to reserved stem, WARNING `naming.reserved` | closed |
| T-03-21 | Spoofing | non-ASCII look-alikes | low | mitigate | NFKD, combining marks dropped, ASCII-only output | closed |
| T-03-22 | Denial of service | overlong names | low | mitigate | 64-character cap, WARNING `naming.truncated` | closed |
| T-03-23 | Spoofing | distributor host posing as manufacturer | medium | mitigate | `AGGREGATOR_DOMAINS` deny-list, INFO `naming.aggregator_host` | closed |
| T-03-24 | Denial of service | malformed datasheet URLs | low | mitigate | `datasheet_host` catches `ValueError`, safe handling of empty / `~` / scheme-less values | closed |
| T-03-25 | Tampering | listing code changing `Custom/` | medium | mitigate | `layout.py` uses only `iterdir` / `rglob` / `is_file` / `is_dir` (no write calls); snapshot test | closed |
| T-03-26 | Information disclosure | listing outside `Custom/` | low | mitigate | `RepoLayout` fixes the three `Custom/` folders; names only | closed |
| T-03-27 | Information disclosure | symlinks / junctions out of picked folder | high | mitigate | `is_symlink()` plus `st_file_attributes` reparse bit, `follow_symlinks=False`, INFO `intake.link_skipped`; junction test runs, symlink test skips without privilege (fake-entry unit test covers the branch) | closed |
| T-03-28 | Denial of service | intake pointed at a huge tree | medium | mitigate | `MAX_MEMBERS` counts every entry, `MAX_FOLDER_DEPTH = 8`, size caps | closed |
| T-03-29 | Tampering | writing into the user's folder | high | mitigate | folder files opened `"rb"` only, nothing staged; snapshot test | closed |
| T-03-30 | Denial of service | file growing between listing and reading | low | mitigate | `_hash_file` counts real bytes against the remaining budget | closed |
| T-03-31 | Tampering | `unpack_sample` turning member names into paths | low | mitigate | `..` / absolute / `:` rejected, resolved target inside dest, `"xb"`, sample sha256 unchanged | closed |
| T-03-32 | Tampering | hostile or unpacked fixtures committed | low | mitigate | hostile zips built in memory / `tmp_path`; `downloaded_examples/** -text` | closed |
| T-03-33 | Tampering | hostile item names reaching Phase 4 as file names | high | mitigate | `name_check` on every symbol, footprint and model; hostile-name test in `tests/test_candidate_names.py` | closed |
| T-03-34 | Tampering | layering guard passing vacuously | medium | mitigate | `test_guard_*` self-tests on synthetic trees; real-module tests ran after merge; unregistered module is an error | closed |
| T-03-SC | Tampering | package installs | high | mitigate | stdlib only; no dependency files changed in Phase 3 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-17 | The vendor label only selects parsing quirks and is shown to the user; it grants no privilege, and every package goes through the same hostile-member checks and caps regardless of label. Accepted in the 03-04 plan threat model. | plan 03-04 threat model | 2026-10-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-19 | 35 | 35 | 0 | secure-phase (L1 grep-depth, orchestrator; auditor skipped per ASVS L1 short-circuit) |
| 2026-10-19 | 35 | 33 | 2 (both medium, below `high` block threshold; threats_open stays 0) | orchestrator, from code review 03-REVIEW.md CR-01 / CR-02 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-19
