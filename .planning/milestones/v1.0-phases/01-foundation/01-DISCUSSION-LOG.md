# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-18
**Phase:** 01-foundation
**Areas discussed:** Round-trip test corpus, Write failure & backups, Line endings & .gitattributes, Phase 1 module scope

---

## Round-trip test corpus

**Corpus source**

| Option | Description | Selected |
|--------|-------------|----------|
| Live repo + frozen set | Glob Custom/ (+Wurth) at test time, plus a small committed edge-case fixture set | ✓ |
| Live repo files only | Glob Custom/ only. Nothing to test if the submodule isn't initialised | |
| Frozen fixtures only | Deterministic, but new library content goes untested | |

**Lib-table source**

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic + local opt-in | Committed tricky-case tables, plus round-trip of %APPDATA%/kicad/*/ tables when present | ✓ |
| Synthetic fixtures only | Never read the KiCad config from tests | |
| Copy my real tables in | Sanitised copies committed, with machine-specific paths | |

**WurthElektronik handling**

| Option | Description | Selected |
|--------|-------------|----------|
| Skip when absent | Marked tests skip with a reason; used as a stress corpus when present | ✓ |
| Check it out now | Init the submodule in this worktree during Phase 1 | |
| Ignore Wurth entirely | Custom/ only | |

**UL sample zip**

| Option | Description | Selected |
|--------|-------------|----------|
| Commit to parent repo | Track downloaded_examples/ in the parent repo (private) | ✓ |
| Keep untracked, skip if missing | Use when present locally | |
| Extract trimmed copies | Commit only the .kicad_sym/.kicad_mod text | |

**Notes:** I checked the parent repo after the discussion: `sylvanoMTL/kicad_libraries` is PRIVATE.

---

## Write failure & backups

| Question | Options | Selected |
|----------|---------|----------|
| Locked file | Short retry then fail / Fail immediately / Retry then ask user | Short retry (~1 s), then fail |
| Backup location | Caller chooses with outside-repo default / Always next to file / Always app data | Caller chooses; tables side-by-side, Custom/ + kicad_common.json in app data |
| Outcome reporting | Structured Issue now / Keep list[str] / Raise exceptions | Structured Issue now |
| Durability | flush+fsync then replace / No fsync / You decide | flush + fsync, then replace |

---

## Line endings & .gitattributes

| Question | Options | Selected |
|----------|---------|----------|
| .gitattributes | Fixtures only (parent) / Repo-wide policy now / None | Fixtures only: `tests/fixtures/** -text` |
| Inserted text EOL | File's dominant EOL / Always LF / You decide | File's dominant EOL |
| Mixed-EOL files | Preserve + warn / Refuse to edit / Preserve silently | Preserve + warn |
| Encoding | Strict UTF-8 keep BOM / Lenient surrogateescape / Operate on bytes | Strict UTF-8, keep BOM |

---

## Phase 1 module scope

| Question | Options | Selected |
|----------|---------|----------|
| kicad_files.py | Minimal read side now / sexpr + fsutil only / Full kicad_files now | Minimal read side now |
| pyproject.toml | Tool config only / Tool config + metadata / pytest.ini instead | Tool config only |
| Pinning | Exact everywhere / Exact PySide6 + ranged dev / Lower bounds | Exact pins everywhere |
| Qt widget test | LibraryTableWidget sync / LogPanel smoke / Both | LibraryTableWidget sync |

---

## Claude's Discretion

- Retry count and backoff, the app-data backup path, the Issue code naming, tokenizer internals and edit API shape, and fixture naming.

## Deferred Ideas

- A repo-wide EOL policy with a renormalisation commit (declined for Phase 1).
