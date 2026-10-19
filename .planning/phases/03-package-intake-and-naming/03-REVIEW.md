---
phase: 03-package-intake-and-naming
reviewed: 2026-10-19T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - .gitattributes
  - kicad_lib_manager/importer/__init__.py
  - kicad_lib_manager/importer/adapters/__init__.py
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/adapters/loose.py
  - kicad_lib_manager/importer/adapters/ultralibrarian.py
  - kicad_lib_manager/importer/candidate.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/layout.py
  - kicad_lib_manager/importer/naming.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/kicad_files.py
  - tests/test_adapters.py
  - tests/test_candidate_names.py
  - tests/test_importer_layering.py
  - tests/test_kicad_files.py
  - tests/test_legacy_rules.py
  - tests/test_naming_sanitize.py
  - tests/test_naming_suggest.py
  - tests/test_package_folder.py
  - tests/test_package_zip.py
  - tests/test_zipfixtures.py
  - tests/zipfixtures.py
findings:
  critical: 2
  warning: 5
  info: 6
  total: 13
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

The zip and folder hardening in `package.py` is solid. Zip slip, drive letters, ADS, symlinks, duplicate and case-colliding members, encrypted members, header-declared caps, the ratio rule and the staging-in-repo check all hold, and staged file names are generated. Naming and layout code is clean. No `extract` or `extractall` is used anywhere.

Two defects contradict claims in `03-SECURITY.md` and the module contract, and both were reproduced with scripts (scratchpad scripts, not committed):

1. T-03-15 is marked closed, but the 100 MB read cap is far too high for the pure-Python S-expression parser. A 3.6 MB hostile `.kicad_sym` that compresses about 8:1 (so it passes the ratio rule) takes 3.7 s to parse, and a 6 MB one peaked at 855 MB. Scaled to the allowed 100 MB this means minutes and gigabytes.
2. `open_package` is documented to never raise on expected failures, yet a corrupt LZMA-compressed member raises `lzma.LZMAError` out of the function.

The remaining findings are robustness and quality issues around vendor-name guessing, Windows reparse-point handling, error attribution and the candidate lifetime contract.

## Critical Issues

### CR-01: Untrusted KiCad files are parsed in memory with a 100 MB cap, a practical DoS (T-03-15 is not really closed)

**File:** `kicad_lib_manager/importer/adapters/base.py:76-86` (cap), `base.py:239` (parse call); cap constant at `kicad_lib_manager/importer/package.py:18`
**Issue:** `_read_limited` reuses `MAX_MEMBER_BYTES` (100 MB, sized for STEP models) as the limit for `.kicad_sym` and `.kicad_mod` text, then hands the whole buffer to `parse_bytes`. The Phase 1 parser builds a slotted `Node` plus a `list` per token. Measured with the project venv:
- A 6 MB file of `(a)` repeated peaked at 855 MB of Python heap.
- A 3.6 MB random mix of `(a)`, `(b 1)`, `()` and similar, from a 461 KB zip (about 8:1, well under `MAX_RATIO` 200), took 3.7 s inside `detect_candidate` (`detect 3.70 s`).

Extrapolated to the allowed 100 MB, one hostile member costs minutes of CPU and several GB of RAM, so a `MemoryError` or an unresponsive GUI worker is reachable from a single downloaded zip. The ratio rule does not help because the payload is not highly compressible. Real KiCad symbol and footprint files are well under a few MB.
**Fix:** Use a separate, much smaller cap for text that is parsed, and skip with the existing WARNING:
```python
MAX_KICAD_TEXT_BYTES = 8 * 1024 * 1024  # in package.py

def _read_limited(pf: PackageFile) -> bytes | Issue:
    cap = _package.MAX_KICAD_TEXT_BYTES if pf.kind in ("symbol", "footprint") else _package.MAX_MEMBER_BYTES
    ...
```
Optionally also give `sexpr.parse` a node-count ceiling and catch `MemoryError` around `parse_bytes` in `locate`. Add a test with a multi-MB, low-ratio hostile file.

### CR-02: `open_package` raises on corrupt LZMA members and on temp-folder failures, breaking its "never raised" contract

**File:** `kicad_lib_manager/importer/package.py:267` (`_copy_member` except tuple), `package.py:304` (`TemporaryDirectory`), `package.py:324`, `package.py:373`
**Issue:** The docstring says expected failures "come back as ERROR Issues, never raised". The caught set (`BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError, OSError`) omits `lzma.LZMAError`, which does not derive from `OSError`. Reproduced: flipping two bytes in the compressed payload of an LZMA zip member raised `_lzma.LZMAError: Corrupt input data` out of `open_package` (bzip2 and deflate corruption were handled). A truncated or damaged LZMA zip, for example from 7-Zip, therefore crashes the caller instead of producing `intake.corrupt`. The staging folder is then only removed by the `TemporaryDirectory` finalizer, not by the deterministic `_refuse` path.

Also, `tempfile.TemporaryDirectory(...)` at line 304 and `staging.resolve()` are outside any `try`. A missing or unwritable temp dir (the test fixture comment itself notes "tempfile never creates a missing one") raises `FileNotFoundError` or `PermissionError` from `open_package`.
**Fix:**
```python
import lzma
_READ_ERRORS = (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, lzma.LZMAError, EOFError, OSError)
# use _READ_ERRORS at line 267
try:
    tmp = tempfile.TemporaryDirectory(prefix=STAGING_PREFIX, ignore_cleanup_errors=True)
except OSError as e:
    return Issue(Severity.ERROR, "intake.staging_failed", f"Could not create a temp folder to stage {path.name}: {e.strerror or e}")
```
Consider a last-resort `except Exception` in `_open_zip` around `_stage_zip` that maps to `intake.corrupt` and calls `_refuse`, so no future decompressor error escapes. Add a test using a corrupted LZMA fixture.

## Warnings

### WR-01: A bare filename or IP address in the Datasheet field becomes a bogus manufacturer guess

**File:** `kicad_lib_manager/importer/suggest.py:137-151` (`datasheet_host`), `suggest.py:205-209`
**Issue:** `datasheet_host` prefixes `//` to any scheme-less value, so a local-file datasheet value is treated as a hostname if it contains a dot. Verified:
- `"LM317.pdf"` gives host `lm317.pdf`, so `manufacturer_choice` returns `TokenChoice("Lm317", "host_guess", False)`.
- `"datasheet.pdf"` gives manufacturer `Datasheet`.
- `"192.168.1.1"` gives manufacturer token `1`.

Vendor symbols commonly carry a plain `<part>.pdf` Datasheet, so the suggested library name becomes e.g. `IC_SubCategory_Lm317`. It is flagged low confidence, but it still pollutes the primary suggestion and could be installed after a hurried edit.
**Fix:** In `datasheet_host`, require either an explicit scheme or a `www.`-style prefix before treating a scheme-less value as a host, and reject numeric-only or file-extension TLDs.
```python
_FILE_TLDS = {"pdf", "htm", "html", "txt", "zip", "doc", "docx"}
...
tld = host.rsplit(".", 1)[-1]
if not tld.isalpha() or tld in _FILE_TLDS:
    return None
```

### WR-02: The Windows reparse-point bit also matches OneDrive and cloud placeholders, so real files may be skipped silently

**File:** `kicad_lib_manager/importer/package.py:402-406` (`_is_link`), `package.py:121`
**Issue:** `_is_link` treats any file or folder with `FILE_ATTRIBUTE_REPARSE_POINT` (0x400) as a link to skip. On Windows 11 files managed by OneDrive Files On-Demand or other cloud filters (for example a Downloads folder under OneDrive Known Folder Move) are, as far as I know, reparse points with a cloud tag, not symlinks or junctions. I could not reproduce this here, so treat it as a risk to verify on the owner's machine. If it holds, such files are skipped with only an INFO `intake.link_skipped` and the user sees "nothing found". The same bit test in `_hostile_reason` (line 121) would refuse a whole zip if an archiver copied that attribute from OneDrive-sourced files.
**Fix:** Test the reparse tag instead of the generic bit: `st.st_reparse_tag in (stat.IO_REPARSE_TAG_SYMLINK, stat.IO_REPARSE_TAG_MOUNT_POINT)` (available on Windows in `os.stat_result` and `stat`; define the two constants locally if needed). For the zip case, refuse on symlink mode only, or downgrade the 0x400 attribute to a skipped, ignored member.

### WR-03: A write failure while staging is reported as a corrupt archive

**File:** `kicad_lib_manager/importer/package.py:264-268`
**Issue:** The `with zf.open(info) as src, open(target, "xb") as dst:` block shares one `except OSError`. A full disk, antivirus lock or permission problem on the temp folder is reported as `intake.corrupt` with text "Could not read member ... of <zip>". The user is told the vendor zip is bad when the problem is local, and the wrong remediation (re-download) is suggested.
**Fix:** Separate the read and write failures, for example by opening `dst` in its own `try` and returning `Issue(Severity.ERROR, "intake.stage_failed", f"Could not write a staged copy of {name}: ...")`, or by catching `OSError` around `open(target, ...)` only.

### WR-04: `ImportCandidate` outlives the staged files it points at, and nothing says so

**File:** `kicad_lib_manager/importer/candidate.py:11-78`, `kicad_lib_manager/importer/package.py:72-77`, `kicad_lib_manager/importer/detect.py:15-38`
**Issue:** For zips every `PackageFile.path` lives in a temp folder deleted by `Package.close()`. `detect_candidate` returns a frozen candidate that does not reference the package. The tests already use this pattern: `with open_package(...) as package: candidate, _ = detect_candidate(package)` and then use the candidate after the block (`_ul_zip_candidate`, `test_ultra_suggestion`). A Phase 4 or GUI caller following the same idiom will install from paths that no longer exist, while `PackageFile.staged` and `size/sha256` still look valid. `Package`'s docstring documents the lifetime, but `ImportCandidate` does not.
**Fix:** At minimum document on `ImportCandidate` (and `PackageFile`) that staged paths are valid only while the originating `Package` is open. Better, add `package: Package | None = field(default=None, compare=False)` to the candidate, or have Phase 4 re-verify `sha256` and existence before copying, and add a test that pins the contract.

### WR-05: Package-level warnings never reach the candidate, so a skipped deep or unreadable part looks like "nothing found"

**File:** `kicad_lib_manager/importer/detect.py:15-38`, `kicad_lib_manager/importer/adapters/base.py:221-263`
**Issue:** `intake.depth_limit`, `intake.unreadable_folder`, `intake.unreadable_file` (folder walk) and `intake.link_skipped` are appended to `package.issues` only. `detect_candidate` returns `locate`'s issues and `candidate.issues`, which exclude them. When the real part sits nine folders deep, in an unreadable subfolder or behind a link, the user sees only `intake.nothing_found: holds no KiCad v6+ symbol or footprint`, and the cause is invisible unless the caller also remembers to print `package.issues`.
**Fix:** In `detect_candidate`, prepend the non-ERROR `package.issues` to the returned issue list (and to `candidate.issues`), or append a pointer to the nothing-found message ("N folders were not read, see ...").

## Info

### IN-01: Dead parameter, oversized function and misleading `kind` on error packages

**File:** `kicad_lib_manager/importer/package.py:409`, `package.py:224-238`
**Issue:** `_open_folder(path, repo_root, progress)` never uses `repo_root`. The function is about 120 lines with several nesting levels, with the same "first N, and K more" formatting repeated three times (lines 211-218, 516-518, 525-527). `open_package` builds not-found and unsupported results with `kind="zip"` even when the path is a missing folder or a text file, so the `Package.kind` annotation lies.
**Fix:** Drop the unused argument (or use it for an in-repo guard), extract a `_capped_list(items)` helper, split the walk and the hash pass into two functions, and use a neutral `kind` such as `"unknown"`.

### IN-02: Look-alike non-ASCII literals in source, and a stale "stays ASCII" comment

**File:** `kicad_lib_manager/importer/naming.py:21-30`, `tests/test_naming_sanitize.py:20-36`
**Issue:** `_TRANSLIT` keys use literal `µ`/`μ` (U+00B5/U+03BC) and `Ω`/`Ω` (U+2126/U+03A9), which are visually identical, so a future edit or normalising editor can silently merge them. `tests/test_naming_sanitize.py:20` says "Non-ASCII inputs are built with escapes so this file stays ASCII", but the file contains literal `µ`, `Ω`, `°`, `é`, `¹`, katakana and `ß`, and two `("10Ω", "10Ohm")` rows look like duplicates on screen.
**Fix:** Write the keys as `"µ"`, `"μ"`, `"Ω"`, `"Ω"` and use escapes in the tests too; fix or drop the comment.

### IN-03: Sanitised-name and model-basename collisions inside one candidate are not reported

**File:** `kicad_lib_manager/importer/candidate.py:26-61`, `kicad_lib_manager/importer/adapters/base.py:231`
**Issue:** `ModelItem.filename` is only the basename, so `a/x.step` and `b/x.step` both become `x.step`. Symbols `"A/B"` and `"A_B"`, or two footprints that differ only by characters `sanitize_name` maps to `_`, sanitise to the same target. Phase 3 reports neither, so Phase 4 could overwrite one with the other.
**Fix:** Add a post-pass in `locate` that emits a WARNING (for example `intake.name_collision`) when two items of one kind share a casefolded sanitised name.

### IN-04: `test_ul_sample_leaves_repo_unchanged` is fragile

**File:** `tests/test_package_zip.py:409-432`
**Issue:** `_git_status` runs `git status` with `check=True`, so a checkout that is not a git work tree (tarball, some CI) raises `CalledProcessError` instead of skipping. It also compares whole-repo status before and after, so any concurrent change (editor, parallel pytest workers) makes it flaky.
**Fix:** Catch `CalledProcessError` and `pytest.skip`, or assert on a snapshot of the repo paths the importer could plausibly touch.

### IN-05: Directory listings are fully materialised before the member cap is applied

**File:** `kicad_lib_manager/importer/package.py:426-427`
**Issue:** `entries = sorted(it, key=...)` reads and sorts every entry of a directory before `budget.members` is checked, so a folder with millions of entries is fully loaded despite `MAX_MEMBERS`. This undercuts the T-03-28 claim, although it needs a hostile local folder the user chose.
**Fix:** Iterate with `itertools.islice(it, MAX_MEMBERS + 1)` per directory (or check the count while iterating) and sort the bounded list.

### IN-06: The layering guard only matches the attribute names `extract` and `extractall`

**File:** `tests/test_importer_layering.py:78`, `test_importer_layering.py:166`
**Issue:** The zip-slip regression guard is an AST attribute-name match. `shutil.unpack_archive`, `zipfile.Path`-based extraction or `getattr(zf, "extr" + "act")` are not caught, and `ZipFile.extract` on a non-zip object would be a false positive. The guard is useful but is documented as covering D-07 more broadly than it does.
**Fix:** Add `unpack_archive` and `_extract_member` to `BULK_EXTRACT_ATTRS`, and note the limits of the guard in the module docstring.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
