---
phase: 03-package-intake-and-naming
reviewed: 2026-10-19T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - kicad_lib_manager/sexpr.py
  - tests/test_locate_text_caps.py
  - tests/test_sexpr.py
  - tests/test_zipfixtures.py
  - tests/zipfixtures.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

I reviewed the linear-time string scan in `sexpr.py` (`_string_end`, `_STRING_BODY`), the replace-based `unquote`, and the four test and fixture files that pin them. I traced the window logic in `_string_end` through the window-exhausted, trailing-backslash, escaped-close and unterminated cases. I also traced the `str.replace` unquote algorithm against run-of-backslashes semantics, and `apply_edits` ordering. I found no correctness or security defect in the production code. The tokenizer and `unquote` match the pre-03-10 oracle on every case I could construct. `apply_edits` ordering and range checks are right. The zip header offsets in `zipfixtures.py` (central directory sizes at +20/+24, local header sizes at +18/+22, flags at +8/+6) are correct.

The findings below are robustness and test-reliability issues. The most significant are a vacuous guard test, a wall-clock performance assertion, and an exception type that cannot be pickled.

I ran two quick checks to confirm the claims below.
- No Unicode scalar value reaches the `bad` alternative in `_TOKEN` (0 of 1,112,064 tested).
- `pickle.loads(pickle.dumps(SexprError(...)))` raises `TypeError`.

## Warnings

### WR-01: The "walker descends" sanity assertion in the 3.11-syntax guard is vacuous

**File:** `tests/test_sexpr.py:780`
**Issue:** `assert "MAX_REPEAT" in _regex_opcodes(patterns["_STRING_BODY"])` is meant to prove that `_regex_opcodes` recurses into nested groups. `_STRING_BODY` has a top-level `MAX_REPEAT` (`[^"\\]*` and the `{0,1024}` repeat), so the assertion is true even if the walker never descended. I confirmed that the top-level opcodes are `['MAX_REPEAT', 'MAX_REPEAT']`. If `visit` were broken, for example if a future `re` version changes the `av` shapes, the test would still pass. It would then also pass for a pattern that hides `POSSESSIVE_REPEAT` or `ATOMIC_GROUP` inside a group. That is exactly the 3.10 import-time `re.error` regression the test exists to catch.
**Fix:** Assert something that only a recursive walk can find, for example a group inside the repeat:
```python
opcodes = _regex_opcodes(patterns["_STRING_BODY"])
assert {"SUBPATTERN", "ANY"} <= opcodes  # ANY lives inside the (?:\\.[^"\\]*) group
```
Alternatively, add a positive control: `assert "ATOMIC_GROUP" in _regex_opcodes(re.compile(r"(?>a(b))"))` guarded by `sys.version_info >= (3, 11)`.

### WR-02: Wall-clock assertion makes the parse test flaky on slow or loaded machines

**File:** `tests/test_sexpr.py:228-235`
**Issue:** `test_large_library_parses_within_budget` asserts `elapsed < 3.0` for a roughly 2 MB pure-Python parse. Every other performance property in this phase is bounded by memory (`traced_peak`) or by a very generous 30 s ceiling (`_END_TO_END_SECONDS`). A 3 s hard limit will fail under CI contention, on a debug interpreter, or when run with coverage or `tracemalloc`. A failure there says nothing about algorithmic regressions.
**Fix:** Either widen it to the same "catastrophic regression" scale used elsewhere (for example 30 s), or replace the timing check with a scaling check. For example, assert that parsing 4x the text costs less than about 8x the time, or count regex matches instead of seconds.

### WR-03: `SexprError` cannot be pickled or copied

**File:** `kicad_lib_manager/sexpr.py:38-43`
**Issue:** `__init__` takes `(code, message, line, col)` but passes only the formatted string to `super().__init__`, so `args == (formatted_message,)`. `pickle.loads(pickle.dumps(err))` and `copy.copy(err)` call `SexprError(formatted_message)` and fail with `TypeError: __init__() missing 3 required positional arguments` (verified). The error crosses no process boundary today. The import path is single-process, with a QThread worker. Any future `ProcessPoolExecutor` or `multiprocessing` use for hostile-file parsing would turn a clean parse failure into an opaque `TypeError` or a hung pool.
**Fix:** Make the exception reconstructible:
```python
def __reduce__(self):
    return (self.__class__, (self.code, self._message, self.line, self.col))
```
(store `self._message = message` before calling `super().__init__`).

## Info

### IN-01: The `bad` alternative in `_TOKEN` and its branch in `parse` are dead code, and the comment misdescribes them

**File:** `kicad_lib_manager/sexpr.py:5-16, 117-122`
**Issue:** Every character is covered by `open`, `close`, `quote`, `atom` (anything not whitespace, parentheses or a quote) or `ws`. I tested every non-surrogate code point and none reaches `bad`. So `_TOKEN.match` can never return `None` without it, and the `if kind == "bad"` branch is unreachable. The comment "bad keeps 'every position matches' true" is therefore wrong. It was needed by the pre-03-10 tokenizer, where an unterminated quote fell through to `bad`. Keeping a never-taken error path, with a duplicated `SexprError` raise, invites someone to rely on it.
**Fix:** Remove the `bad` group and the `kind == "bad"` branch, and fix the comment. Alternatively keep the group as a defensive guard but say so and mark the branch `# pragma: no cover`. `test_tokenizer_matches_reference_parser` is unaffected, since it exercises the unterminated-quote path through `_string_end`.

### IN-02: `unpack_sample` uses `assert` for path-safety checks

**File:** `tests/zipfixtures.py:151-155`
**Issue:** The traversal guards (`..`, leading `/` or `\`, `:`, `resolve().is_relative_to`) are `assert` statements, which vanish under `python -O` or `PYTHONOPTIMIZE`. The comment says the sample is trusted, so this is low risk. But the helper is documented as the one place that turns a zip into real files, and `UL_ZIP` could be swapped for a different archive.
**Fix:** Raise `ValueError` explicitly instead of asserting.

### IN-03: The string-unit table is duplicated between the fixture module and its self-test

**File:** `tests/test_zipfixtures.py:227` and `tests/zipfixtures.py:217`
**Issue:** `_UNITS` in the test repeats `_STRING_UNITS` from `zipfixtures.py`. If a kind's unit changes in the builder, the self-test shape check changes independently and could silently check the wrong lead length.
**Fix:** Keep it independent on purpose and add a one-line comment saying so, or import `_STRING_UNITS`. The `STRING_KINDS` tuple is already shared.

### IN-04: `test_current_custom_lists` only tests its own constants

**File:** `tests/test_zipfixtures.py:217-222`
**Issue:** It asserts lengths and membership of hard-coded tuples defined in `zipfixtures.py`. It cannot fail unless someone edits the tuples, and it never compares them to the real `Custom/` submodule. It adds maintenance cost without protecting behavior.
**Fix:** Drop it, or compare against the real `Custom/` directory (skipping when the submodule is absent, as `test_real_files_are_below_both_caps` does).

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
