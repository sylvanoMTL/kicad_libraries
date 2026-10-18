---
phase: 01-foundation
reviewed: 2026-10-18T12:00:00Z
depth: standard
files_reviewed: 37
files_reviewed_list:
  - .gitattributes
  - downloaded_examples/ul_CSD85301Q2.zip
  - kicad_lib_manager/fsutil.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/sexpr.py
  - pyproject.toml
  - requirements-dev.txt
  - requirements.txt
  - tests/conftest.py
  - tests/fixtures/build_fixtures.py
  - tests/fixtures/sexpr/bare_atoms.kicad_mod
  - tests/fixtures/sexpr/bom.kicad_sym
  - tests/fixtures/sexpr/crlf.kicad_sym
  - tests/fixtures/sexpr/escapes.kicad_sym
  - tests/fixtures/sexpr/legacy_module.kicad_mod
  - tests/fixtures/sexpr/lf.kicad_sym
  - tests/fixtures/sexpr/mixed_eol.kicad_sym
  - tests/fixtures/sexpr/no_trailing_newline.kicad_mod
  - tests/fixtures/sexpr/two_models.kicad_mod
  - tests/fixtures/tables/basic.sym-lib-table
  - tests/fixtures/tables/empty.sym-lib-table
  - tests/fixtures/tables/escaped.sym-lib-table
  - tests/fixtures/tables/flags.fp-lib-table
  - tests/fixtures/tables/reordered.fp-lib-table
  - tests/test_edits.py
  - tests/test_fixtures.py
  - tests/test_fsutil.py
  - tests/test_kicad_files.py
  - tests/test_layering.py
  - tests/test_library_table_widget.py
  - tests/test_manifests.py
  - tests/test_models.py
  - tests/test_roundtrip_corpus.py
  - tests/test_scanner_skip_dirs.py
  - tests/test_sexpr.py
findings:
  critical: 0
  warning: 7
  info: 7
  total: 14
status: issues_found
---

# Phase 01-foundation: Code Review Report

**Reviewed:** 2026-10-18T12:00:00Z
**Depth:** standard
**Files Reviewed:** 37
**Status:** issues_found

## Summary

Reviewed the new foundation modules (`sexpr.py`, `fsutil.py`, `kicad_files.py`), the `models.py` additions, the one-line `SKIP_DIRS` change in `library_scanner.py`, the test suite, the fixture builder and the fixtures, and the packaging files. The vendor zip was not extracted or executed. I read it only through the tests that open it, and those tests read members into memory. They check the declared size first, never write to disk, and never use member names as paths. I found no path-traversal or zip-bomb exposure there.

`./env/Scripts/python.exe -m pytest` gives 353 passed and 2 skipped (the Wurth corpus, submodule absent).

The tokenizer, span tree, `apply_edits` and the atomic-write core are sound. I traced overlap and ordering semantics, the explicit-stack parse, regex backtracking (the alternatives are disjoint, so no catastrophic cases) and the temp-file cleanup paths. I found no data-loss or security defect.

The defects are contract gaps that will bite in later phases, when real vendor files are rewritten:
- The locators do not validate token kinds.
- `unquote` is narrower than KiCad's escape set.
- The error mapping in `atomic_write_bytes` is imprecise.
- Some tests depend on the machine they run on.

## Warnings

### WR-01: `find_symbols`, `find_property` and `lib_table_entries` do not validate the kind of the name and value token

**File:** `kicad_lib_manager/kicad_files.py:97-99, 114-119, 162-168`
**Issue:** `footprint_name` and `find_models` check `kind in ("str", "atom")`. `find_symbols`, `find_property` and `lib_table_entries` take `children[1]`, `children[2]` and so on without that check. A malformed or unexpected form such as `(symbol (x y) ...)` or `(property "Footprint" (at 0 0))` produces a `SymbolRef` with `name == ""` and a *list* node as `name_node`. A `PropertyRef` has a list `value_node` and `value == ""` (`unquote` of a list node's empty `.text`).

Reproduced:
- `find_symbols` returned name `''` with a `list` name node.
- `find_property` returned `value=''` with a `list` value node.

Callers will use these spans for `Edit(node.start, node.end, quote(...))`. Replacing the "value" would then silently overwrite a whole sub-list such as `(at 0 0)`. `find_symbol(root, "")` can also match a garbage symbol.
**Fix:** Apply the same guard everywhere, and skip or reject entries that fail it:
```python
def _is_token(node: Node) -> bool:
    return node.kind in ("str", "atom")

# find_symbols
if child.head == "symbol" and len(child.children) >= 2 and _is_token(child.children[1]):
# find_property
if len(child.children) < 3 or not _is_token(child.children[1]) or not _is_token(child.children[2]):
    continue
# lib_table_entries
if head in _LIB_FIELDS and len(field.children) >= 2 and _is_token(field.children[1]) and head not in value_nodes:
```

### WR-02: `unquote` decodes only five escapes, so `quote(unquote(x))` can change a foreign value

**File:** `kicad_lib_manager/sexpr.py:23, 126-134`
**Issue:** `_UNESCAPES` covers `\\ \" \n \r \t`. KiCad's lexer also accepts `\a \b \f \v`, `\xHH` and octal escapes. Any other escape is kept verbatim with its backslash, so the decoded value differs from what KiCad reads.

Reproduced:
- `unquote('"a\\x41"')` gives `a\x41`. KiCad reads `aA`.
- `quote()` of that gives `"a\\x41"`, which KiCad reads as a literal backslash.

Any code path that decodes a vendor value and re-quotes it (rather than splicing the original token) silently changes the value. The test `test_unquote_unknown_escape_survives_verbatim` locks in the current behaviour instead of flagging the gap.
**Fix:** Either decode the full KiCad escape set (`\a \b \f \v \xHH`, octal), or document and enforce that values are only ever replaced and never round-tripped. If you keep the narrow decode, add an `is_lossless(token)` helper that callers can use to refuse editing tokens containing unknown escapes.

### WR-03: Any `PermissionError` from `os.replace` is reported as "file is in use", after about 1 s of pointless retries

**File:** `kicad_lib_manager/fsutil.py:100-115`
**Issue:** The read-only check runs once, before the temp write. Other non-lock causes of `PermissionError` are retried for the full window and reported as `fs.locked` / "file is in use".

Reproduced: `atomic_write_bytes(<directory path>, ...)` returns `fs.locked` "Could not write d: file is in use". The same applies when the read-only attribute is set between the check and the replace, or when an ACL denies the write. The log message misleads the user, and the delay is wasted.
**Fix:** Reject `path.is_dir()` up front with a dedicated code (for example `fs.not_a_file`). After the retries are exhausted, re-run the `os.access(path, os.W_OK)` test and return `fs.read_only` if it now fails.

### WR-04: `atomic_write_text` and `encode_source` can raise, which breaks the "return an Issue" contract

**File:** `kicad_lib_manager/fsutil.py:70-73, 138-141`
**Issue:** `encode_source` calls `text.encode("utf-8")` strictly, outside the `try` in `atomic_write_bytes`. A str containing a lone surrogate raises `UnicodeEncodeError` out of `atomic_write_text`. Such strings can arrive from Windows filenames, because Python surfaces undecodable names as lone surrogates, and a future importer derives symbol and footprint names from file names. The rest of the module returns `Issue` for every failure mode.
**Fix:** Catch the error and return an Issue:
```python
try:
    data = encode_source(text, bom)
except UnicodeEncodeError as e:
    return Issue(Severity.ERROR, "fs.bad_encoding", f"Could not write {path.name}: text is not encodable as UTF-8 ({e.reason})")
return atomic_write_bytes(path, data, retry_delays=retry_delays, sleep=sleep)
```

### WR-05: The mixed-EOL warning text is wrong for lone-CR files

**File:** `kicad_lib_manager/fsutil.py:46-53`
**Issue:** `mixed` is true when `cr > 0`, but the message always says "mixed line endings (CRLF and LF)". Reproduced: `decode_source(b"a\rb\rc\n", "x")` yields that exact text, although the file has bare CR and LF and no CRLF at all. The user is told something false about the file.
**Fix:** Build the description from the counts, for example "mixed line endings (CRLF/LF/CR)", or name the endings actually present.

### WR-06: `test_ul_zip_is_pinned_and_tracked` calls `git` without the `needs_git` guard

**File:** `tests/test_roundtrip_corpus.py:117-124`
**Issue:** `tests/test_fixtures.py` skips its git-dependent tests with `shutil.which("git") is None`. This test calls `subprocess.run(["git", ...])` unguarded, so with no git on PATH it errors with `FileNotFoundError` instead of skipping. Run from a source export without `.git`, it fails with a misleading "not tracked" message.
**Fix:** Reuse the guard:
```python
@pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")
def test_ul_zip_is_pinned_and_tracked(): ...
```
Split the SHA assertion into its own test so it still runs without git.

### WR-07: `local_kicad` tests are documented as opt-in but run on every default invocation

**File:** `pyproject.toml:3-8`, `tests/test_roundtrip_corpus.py:149-195`
**Issue:** The marker text says "opt-in", but `addopts` has no `-m "not local_kicad"` (or a similar deselect). They run whenever `%APPDATA%\kicad\<ver>\sym-lib-table` exists, so test outcomes depend on the developer's personal KiCad install. They also read personal data on every run. The `wurth` marker has the same shape, but there it is only a missing-submodule skip.
**Fix:** Make it truly opt-in with `addopts = "-ra --strict-markers -m 'not local_kicad'"`, so that `-m local_kicad` enables it. Or reword the marker text to say it runs automatically when a config exists.

## Info

### IN-01: `backup_file` reports failure after a complete backup exists, and copies the read-only attribute

**File:** `kicad_lib_manager/fsutil.py:172`
**Issue:** `shutil.copystat` runs outside the cleanup `try`. If it raises, the function returns `fs.backup_failed` but leaves a complete `_backup_N` file that the Restore dialog will list. `copystat` also carries the read-only attribute over: I reproduced that a backup of a read-only file has `os.access(W_OK) == False`. That makes later cleanup of the backup by `Path.unlink` raise `PermissionError` on Windows.
**Fix:** Treat `copystat` as best-effort (`try/except OSError: pass`) and return the backup path regardless. Or chmod the backup writable afterwards.

### IN-02: `Severity(str, Enum)` formats as `Severity.INFO` on Python 3.12+

**File:** `kicad_lib_manager/models.py:36-41`
**Issue:** The comment says "Values equal the LogPanel.COLORS keys". With a `(str, Enum)` mixin, `f"{sev}"` and `str(sev)` give `'Severity.INFO'` on 3.12+, not `'info'`. Dict lookups work because hash and equality are str-based, but a caller that formats the severity or passes it to `QSettings` or a CSS class gets the wrong text. The project targets 3.10+ and runs on 3.14.
**Fix:** Use `enum.StrEnum` (3.11+). On 3.10 define `__str__` returning `self.value`.

### IN-03: Scanner skips `tests/` but not `downloaded_examples/`, which will hold vendor KiCad files

**File:** `kicad_lib_manager/library_scanner.py:13, 138-140`
**Issue:** The zip contains `KiCADv6/footprints.pretty/` and a `.kicad_sym`. The project's constraints say more real vendor downloads will be added to `downloaded_examples/`. If any is extracted in place (to inspect it, for example), `find_symbol_libs` and `find_footprint_libs` will present it as a new "downloaded_examples" source, and Generate Tables would write `fp-lib-table` entries for it. `_in_skip_dir` also matches only the first path segment, case-sensitively.
**Fix:** Add `"downloaded_examples"` to `SKIP_DIRS` together with a regression test, as was done for `tests`.

### IN-04: A bare `(name)` / `(uri)` in a lib entry is classified as a flag

**File:** `kicad_lib_manager/kicad_files.py:162-167`
**Issue:** The `elif len(field.children) == 1` branch catches every one-child form, including a value-less `(name)`. Reproduced: `(lib (name)(type "KiCad")(uri "u")(name "N"))` gives `flags == ('name',)`. The effect is harmless today, but `flags` is meant for presence flags such as `disabled` and `hidden`.
**Fix:** Route `head in _LIB_FIELDS` with fewer than two children to `extras`, or ignore it.

### IN-05: Environment-coupled and wall-clock tests are brittle

**File:** `tests/test_manifests.py:26-29`, `tests/test_sexpr.py:218`, `tests/test_roundtrip_corpus.py:251`, `tests/test_fsutil.py:59-72`
**Issue:**
- `test_installed_versions_match_pins` fails on any legitimate `pip install -U`. It checks the environment, not the code.
- The 3 s and 60 s parse budgets are wall-clock asserts, so they are flaky on a loaded machine.
- `test_read_only_target_returns_issue_without_retry` fails when run as root on POSIX, where `os.access(W_OK)` is true.

**Fix:** Keep the version check under a dedicated marker, or drop it. Scale the budgets or mark them with a `perf` marker. Skip the read-only test when `os.geteuid() == 0`.

### IN-06: Fixtures are protected from EOL conversion, but the zip and temp leftovers are not

**File:** `.gitattributes:1`, `.gitignore`
**Issue:** `.gitattributes` has `tests/fixtures/** -text` but nothing for the zip. Git's binary auto-detection will cover it, and the SHA test would catch a corruption. An explicit `*.zip binary` is safer. If the process is killed hard, `atomic_write_bytes` can leave `.<name>.<pid>.<hex>.tmp` beside the target, for example in `Custom/Symbols/`. Nothing ignores `*.tmp`, so a later `git add -A` in the Custom submodule could commit it.
**Fix:** Add `*.zip binary` to `.gitattributes`. Add `.*.tmp` to the `.gitignore` of the repo and of the Custom submodule.

### IN-07: Live-data tests encode content assumptions about the Custom submodule

**File:** `tests/test_kicad_files.py:343-355`
**Issue:** `test_live_custom_symbols` asserts that every top-level symbol has a `Footprint` property and that no name matches `_\d+_\d+$`. A legitimate derived symbol (`extends`) without its own Footprint property, or a part named `…_1_2`, fails the Phase 1 suite for reasons unrelated to the code under test.
**Fix:** Report these as warnings (`warnings.warn`) or move them to a separate marked test for the live corpus.

---

_Reviewed: 2026-10-18T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
