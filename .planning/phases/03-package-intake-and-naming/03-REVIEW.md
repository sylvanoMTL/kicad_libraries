---
phase: 03-package-intake-and-naming
reviewed: 2026-10-19T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/sexpr.py
  - tests/test_kicad_files.py
  - tests/test_locate_text_caps.py
  - tests/test_package_zip.py
  - tests/test_sexpr.py
  - tests/test_zipfixtures.py
  - tests/zipfixtures.py
findings:
  critical: 1
  warning: 5
  info: 6
  total: 12
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This is a re-review after gap closure (plans 03-08 and 03-09), scoped to `git diff bba9d0954d6ceb3ed4c1914c8921b8103efe2dff..HEAD` over the ten listed files. The full suite passes (817 passed, 4 skipped, all skips environmental).

**CR-02 is resolved.** `_READ_ERRORS` now covers `lzma.LZMAError` and `compression.zstd.ZstdError`, and temp-folder creation and resolution are guarded. Beyond the new tests, I fuzzed `open_package` plus `detect_candidate` with 12,000 byte-mutated and truncated zips (stored, deflate, bzip2, lzma, zstd, nested). No exception escaped.

**CR-01 is only partly resolved.** The 8 MiB text cap and the 1,000,000-node ceiling work for token-dense input (the original reproduction): the worst measured case is about 230 MiB and 1.4 s. They do not bound the cost of a single large quoted string. The string pattern in `sexpr.py` makes the regex engine keep a backtrack entry per character, so one 8 MiB string peaks at about 2.7 GiB. The cap passes it, the ratio rule passes it, and the node ceiling never counts it. This is reported as CR-03 because the T-03-35 claim ("bounded at about 200 MiB, under about 2 s") does not hold.

WR-01..WR-05 and IN-01..IN-06 are unchanged by this diff and are carried over below.

## Resolved since previous review

- **CR-01 (token-dense input, the reproduced case):** `kicad_lib_manager/importer/package.py:22-25` defines `MAX_KICAD_TEXT_NODES = 1_000_000` and `MAX_KICAD_TEXT_BYTES = 8 MiB`. `kicad_lib_manager/importer/adapters/base.py:81` caps the read at `min(MAX_KICAD_TEXT_BYTES, MAX_MEMBER_BYTES)` and `base.py:247` passes `max_nodes` to `parse_bytes`. `kicad_lib_manager/sexpr.py:83-90` raises `sexpr.too_many_nodes` before the crossing node is built, and `kicad_lib_manager/kicad_files.py:61-76` forwards the limit. Measured here with the project venv: 999,000 atoms took 1.4 s and 232 MiB peak; 330,000 `()` took 0.6 s and 94 MiB. An over-ceiling file becomes a WARNING `intake.unreadable_file` and the rest of the package is still read (`tests/test_locate_text_caps.py:77`, `:123`). A residual gap in the same class remains, see CR-03.
- **CR-02:** `kicad_lib_manager/importer/package.py:43-67` builds `_READ_ERRORS` from guarded `lzma` and `compression.zstd` imports, and `package.py:297` uses it in `_copy_member`. `package.py:334-356` returns `intake.staging_failed` when the temp folder cannot be created or resolved. `_open_zip` (`package.py:421-425`) refuses only after the zip handle is closed, so `_refuse` removes the staging folder before `open_package` returns. Verified by `tests/test_package_zip.py` (`test_corrupt_member_every_codec_refused_and_cleaned_up`, `test_corrupt_member_mid_staging_removes_earlier_files_and_spares_other_package`, `test_staging_failed_missing_temp_folder`, `test_open_package_never_raises_on_expected_faults`) and by my own fuzz run (12,000 mutated zips, zero escaped exceptions).

## Critical Issues

### CR-03: A single large quoted string costs about 2.7 GiB in the parser, so the 8 MiB cap and the node ceiling do not bound memory

**File:** `kicad_lib_manager/sexpr.py:9` (string pattern); reachable via `kicad_lib_manager/importer/adapters/base.py:81` and `base.py:247`; caps at `kicad_lib_manager/importer/package.py:23-25`
**Issue:** The token pattern `"(?:[^"\\]|\\.)*"` is an alternation inside a greedy repeat. Python's `re` pushes a backtrack record per repeated character, so one string token costs roughly 200 to 300 bytes per input character before the Node is built. The node ceiling counts the string as one node, and the byte cap of 8 MiB admits a string of nearly that length. Reproduced with the project venv (Python 3.14.4, Windows):
- A 5.5 MB zip holding one `.kicad_sym` whose `Description` property is an 8,388,486-byte random-text string (deflate ratio about 1.5:1, far below `MAX_RATIO` 200) was accepted (`refused False`) and `detect_candidate` took 3.65 s with a peak working set of 2,764 MiB.
- `parse_bytes(..., max_nodes=1_000_000)` on the same text alone: 3.5 s, 2,755 MiB working set, 3,092 MiB commit.
- An unterminated string of the same length fails only after the same scan (`peak=1701 MiB` under tracemalloc).
- A folder package has no ratio rule at all, so the same file is accepted there too.

This is the same defect class as CR-01 (a size-capped, ratio-passing hostile file amplified roughly 330:1 in the pure-Python parser), and it contradicts the plan-03-08 claim that a file is bounded at about 200 MiB. `locate` only catches `MemoryError`, which does not fire on a machine with a large pagefile; the process just commits 3 GiB and slows down. The test suite has no string-heavy hostile case: `_hostile_symbol` builds only list tokens, so it could not detect this.
**Fix:** Replace the string alternation with the standard unrolled loop, which is linear and does not grow the backtrack stack. Measured on the same 8 MiB string: 0.06 s and 136 MiB instead of 1.88 s and 1,770 MiB, with identical matching:
```python
r'|(?P<str>"[^"\\]*(?:\\.[^"\\]*)*")'
```
Keep the `re.S` flag. Add a regression test in `tests/test_locate_text_caps.py` with a single multi-MiB random-text string (inside the ratio and byte caps) that asserts peak memory or, more portably, that parsing it finishes well under a second. Add a `tests/test_sexpr.py` case that the unrolled pattern still accepts `\"` and `\\` escapes and rejects an unterminated string with `sexpr.unterminated`. Optionally also lower `MAX_KICAD_TEXT_BYTES` (real files are below 50 KiB, the largest known real footprint is 6 MiB only because of an embedded model).

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

_Current location (lines shifted by plans 03-08 and 03-09): `package.py:446-450` (`_is_link`) and `package.py:151-152` (`_hostile_reason`). Unchanged and still open._

### WR-03: A write failure while staging is reported as a corrupt archive

**File:** `kicad_lib_manager/importer/package.py:264-268`
**Issue:** The `with zf.open(info) as src, open(target, "xb") as dst:` block shares one `except OSError`. A full disk, antivirus lock or permission problem on the temp folder is reported as `intake.corrupt` with text "Could not read member ... of <zip>". The user is told the vendor zip is bad when the problem is local, and the wrong remediation (re-download) is suggested.
**Fix:** Separate the read and write failures, for example by opening `dst` in its own `try` and returning `Issue(Severity.ERROR, "intake.stage_failed", f"Could not write a staged copy of {name}: ...")`, or by catching `OSError` around `open(target, ...)` only.

_Current location: `package.py:293-298` (`_copy_member`); the new `_READ_ERRORS` tuple at line 297 still contains `OSError`. Plan 03-09 deliberately left this open. Unchanged and still open._

### WR-04: `ImportCandidate` outlives the staged files it points at, and nothing says so

**File:** `kicad_lib_manager/importer/candidate.py:11-78`, `kicad_lib_manager/importer/package.py:72-77`, `kicad_lib_manager/importer/detect.py:15-38`
**Issue:** For zips every `PackageFile.path` lives in a temp folder deleted by `Package.close()`. `detect_candidate` returns a frozen candidate that does not reference the package. The tests already use this pattern: `with open_package(...) as package: candidate, _ = detect_candidate(package)` and then use the candidate after the block (`_ul_zip_candidate`, `test_ultra_suggestion`). A Phase 4 or GUI caller following the same idiom will install from paths that no longer exist, while `PackageFile.staged` and `size/sha256` still look valid. `Package`'s docstring documents the lifetime, but `ImportCandidate` does not.
**Fix:** At minimum document on `ImportCandidate` (and `PackageFile`) that staged paths are valid only while the originating `Package` is open. Better, add `package: Package | None = field(default=None, compare=False)` to the candidate, or have Phase 4 re-verify `sha256` and existence before copying, and add a test that pins the contract.

_Current location: `package.py:70-77` (`PackageFile`) and `package.py:80-86` (`Package` docstring). Unchanged and still open._

### WR-05: Package-level warnings never reach the candidate, so a skipped deep or unreadable part looks like "nothing found"

**File:** `kicad_lib_manager/importer/detect.py:15-38`, `kicad_lib_manager/importer/adapters/base.py:221-263`
**Issue:** `intake.depth_limit`, `intake.unreadable_folder`, `intake.unreadable_file` (folder walk) and `intake.link_skipped` are appended to `package.issues` only. `detect_candidate` returns `locate`'s issues and `candidate.issues`, which exclude them. When the real part sits nine folders deep, in an unreadable subfolder or behind a link, the user sees only `intake.nothing_found: holds no KiCad v6+ symbol or footprint`, and the cause is invisible unless the caller also remembers to print `package.issues`.
**Fix:** In `detect_candidate`, prepend the non-ERROR `package.issues` to the returned issue list (and to `candidate.issues`), or append a pointer to the nothing-found message ("N folders were not read, see ...").

_Current location: `base.py:228-276` (`locate`). Unchanged and still open._

## Info

### IN-01: Dead parameter, oversized function and misleading `kind` on error packages

**File:** `kicad_lib_manager/importer/package.py:409`, `package.py:224-238`
**Issue:** `_open_folder(path, repo_root, progress)` never uses `repo_root`. The function is about 120 lines with several nesting levels, with the same "first N, and K more" formatting repeated three times (lines 211-218, 516-518, 525-527). `open_package` builds not-found and unsupported results with `kind="zip"` even when the path is a missing folder or a text file, so the `Package.kind` annotation lies.
**Fix:** Drop the unused argument (or use it for an in-repo guard), extract a `_capped_list(items)` helper, split the walk and the hash pass into two functions, and use a neutral `kind` such as `"unknown"`.

_Current location: `_open_folder` is at `package.py:453-576`; the repeated list formatting is at `package.py:239-248`, `560-562` and `569-571`; the `kind="zip"` results are at `package.py:255` and `264`. Unchanged and still open._

### IN-02: Look-alike non-ASCII literals in source, and a stale "stays ASCII" comment

**File:** `kicad_lib_manager/importer/naming.py:21-30`, `tests/test_naming_sanitize.py:20-36`
**Issue:** `_TRANSLIT` keys use literal `µ`/`μ` (U+00B5/U+03BC) and `Ω`/`Ω` (U+2126/U+03A9), which are visually identical, so a future edit or normalising editor can silently merge them. `tests/test_naming_sanitize.py:20` says "Non-ASCII inputs are built with escapes so this file stays ASCII", but the file contains literal `µ`, `Ω`, `°`, `é`, `¹`, katakana and `ß`, and two `("10Ω", "10Ohm")` rows look like duplicates on screen.
**Fix:** Write the keys as `"µ"`, `"μ"`, `"Ω"`, `"Ω"` and use escapes in the tests too; fix or drop the comment.

_Unchanged and still open._

### IN-03: Sanitised-name and model-basename collisions inside one candidate are not reported

**File:** `kicad_lib_manager/importer/candidate.py:26-61`, `kicad_lib_manager/importer/adapters/base.py:231`
**Issue:** `ModelItem.filename` is only the basename, so `a/x.step` and `b/x.step` both become `x.step`. Symbols `"A/B"` and `"A_B"`, or two footprints that differ only by characters `sanitize_name` maps to `_`, sanitise to the same target. Phase 3 reports neither, so Phase 4 could overwrite one with the other.
**Fix:** Add a post-pass in `locate` that emits a WARNING (for example `intake.name_collision`) when two items of one kind share a casefolded sanitised name.

_Current location of the model basename: `base.py:238`. Unchanged and still open._

### IN-04: `test_ul_sample_leaves_repo_unchanged` is fragile

**File:** `tests/test_package_zip.py:409-432`
**Issue:** `_git_status` runs `git status` with `check=True`, so a checkout that is not a git work tree (tarball, some CI) raises `CalledProcessError` instead of skipping. It also compares whole-repo status before and after, so any concurrent change (editor, parallel pytest workers) makes it flaky.
**Fix:** Catch `CalledProcessError` and `pytest.skip`, or assert on a snapshot of the repo paths the importer could plausibly touch.

_Current location: `tests/test_package_zip.py:415-438`. A missing `git` binary now skips, but `check=True` is still there. Unchanged and still open._

### IN-05: Directory listings are fully materialised before the member cap is applied

**File:** `kicad_lib_manager/importer/package.py:426-427`
**Issue:** `entries = sorted(it, key=...)` reads and sorts every entry of a directory before `budget.members` is checked, so a folder with millions of entries is fully loaded despite `MAX_MEMBERS`. This undercuts the T-03-28 claim, although it needs a hostile local folder the user chose.
**Fix:** Iterate with `itertools.islice(it, MAX_MEMBERS + 1)` per directory (or check the count while iterating) and sort the bounded list.

_Current location: `package.py:470-471`. Unchanged and still open._

### IN-06: The layering guard only matches the attribute names `extract` and `extractall`

**File:** `tests/test_importer_layering.py:78`, `test_importer_layering.py:166`
**Issue:** The zip-slip regression guard is an AST attribute-name match. `shutil.unpack_archive`, `zipfile.Path`-based extraction or `getattr(zf, "extr" + "act")` are not caught, and `ZipFile.extract` on a non-zip object would be a false positive. The guard is useful but is documented as covering D-07 more broadly than it does.
**Fix:** Add `unpack_archive` and `_extract_member` to `BULK_EXTRACT_ATTRS`, and note the limits of the guard in the module docstring.

_Unchanged and still open._

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
