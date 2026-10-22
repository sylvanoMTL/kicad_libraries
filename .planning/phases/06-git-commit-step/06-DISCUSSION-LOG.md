# Phase 6: Git Commit Step - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-22
**Phase:** 06-git-commit-step
**Areas discussed:** Commit step flow, Pre-existing changes, Parent ref bump & branches, Commit message format

---

## Commit step flow

| Question | Options | Selected |
|----------|---------|----------|
| Where does the confirmation live? | Inline in Result view commit_slot / Separate modal dialog / Auto-prompt dialog | Inline in Result view |
| Close without committing? | Leave uncommitted, log it / Ask before closing / Offer it again later | Leave uncommitted, log it |
| Custom commit OK, parent commit fails? | Keep Custom commit, report / Undo the Custom commit (reset --soft) / Offer a Retry button | Keep Custom commit, report |
| After a successful commit? | Hashes + "not pushed, N ahead" note / Just a success line / Hashes + copyable push commands | Hashes + "not pushed" note |
| git missing or Custom not a repo? | Disabled slot with reason / Hide slot entirely | Disabled slot with reason |
| Hooks? | Always run, show output on fail / Run, offer --no-verify skip on fail | Always run, show output on fail |
| Threading? | Worker thread, lock inputs / GUI thread is fine | Worker thread, lock inputs |
| Entry points? | Only after a successful install / Also from a menu | Only after a successful install |

**Notes:** The user asked for a second round of questions in this area (git missing, hooks, threading, entry point).

---

## Pre-existing changes

| Question | Options | Selected |
|----------|---------|----------|
| Touched file already had uncommitted edits? | Warn, show diff, allow commit / Refuse the commit / Commit only the import's hunks | Warn, show diff, allow commit |
| Other unrelated changes in Custom? | Leave alone, mention count / Leave alone, say nothing / List them by name | Leave alone, mention count |
| File changed after install, before Commit? | Refuse, ask to re-check / Warn and commit anyway | Refuse |
| Editable file list? | Fixed, read-only / Checkable list | Fixed, read-only |

---

## Parent ref bump & branches

| Question | Options | Selected |
|----------|---------|----------|
| Parent ref already behind Custom HEAD (extra commits ride along)? | Allow, list them in slot + message / Skip parent bump / Refuse whole commit | Allow, list them |
| Parent bump optional? | Checkbox, on by default / Always both | Checkbox, on by default |
| Custom on a non-main named branch? | Commit there, branch shown amber / Treat like detached / Refuse | Commit there, amber |
| Parent detached or mid-merge/rebase? | Pre-check, disable parent bump with reason / Refuse everything | Pre-check, disable parent bump |
| Detached HEAD on main's history, main ahead? | Plain `git switch main`, refuse if git does / Offer only if HEAD == main tip | Plain `git switch main` |
| Parent commit scope? | Only the Custom gitlink / Same, plus a warning about other staged files | Only the Custom gitlink |
| Running from a worktree? | Whatever repo the app runs from / Refuse in worktree / Warn in worktree | Whatever repo the app runs from |

---

## Commit message format

| Question | Options | Selected |
|----------|---------|----------|
| Custom message style? | Sentence subject + Import-* trailers / Conventional `feat(lib):` + trailers / Sentence subject + prose provenance | Sentence subject + trailers |
| Parent message? | Mirror subject, list included commits / Conventional `chore(custom): bump` | Mirror subject, list commits |
| Which messages are editable? | Custom editable, parent auto / Both editable | Custom editable, parent auto |
| Provenance removed by the user? | Allow it, user's message wins / Always re-append trailers | User's message wins |

---

## Claude's Discretion

- Module layout (gitops service, commit panel widget), exact git invocations, mapping `touched` (which includes mkdir dirs) to committable file paths, the pre-install diff source, the date format, the vendor display name, folding in Phase 5 WR-04, and the test strategy.

## Deferred Ideas

- Copyable `git push` commands in the slot (never run).
- A "commit last import" menu entry or reminder (needs persisted state).
- Hunk-level partial staging for files that were already dirty.
