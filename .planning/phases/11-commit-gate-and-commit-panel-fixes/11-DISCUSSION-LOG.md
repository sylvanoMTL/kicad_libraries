# Phase 11: Commit Gate and Commit Panel Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-29
**Phase:** 11-commit-gate-and-commit-panel-fixes
**Areas discussed:** Gate scope, Refusal and recovery, Uncertain git outcomes, Manual command and outcome look

---

## Gate scope

| Option | Description | Selected |
|--------|-------------|----------|
| New/changed vs HEAD | Check symbols in committed .kicad_sym files that are new or changed against HEAD (Phase 9 D-21) | ✓ |
| Every symbol in the files | Whole file must be atomic | |
| Only the imported symbol | Check CommitPlan.symbol only | |

**User's choice:** New/changed vs HEAD

| Option | Description | Selected |
|--------|-------------|----------|
| Amber note, no block | One amber line for parts already failing at HEAD; log lists them | ✓ |
| Ignore silently | Scan tree marks already show them | |
| Block it too | Any failing part in a touched file blocks | |

**User's choice:** Amber note, no block

| Option | Description | Selected |
|--------|-------------|----------|
| Probe and click | Gate in the read-only probe and again in _precheck | ✓ |
| Only at click | _precheck only | |
| Only in the probe | Decide once when the panel opens | |

**User's choice:** Probe and click

| Option | Description | Selected |
|--------|-------------|----------|
| Linked symbols at HEAD too | Committed footprint/model also checks the Custom symbols that link it; failures block | ✓ |
| Symbols in the commit only | Footprints/models judged only via committed symbols | |
| Linked: amber note only | Check linked symbols, warn only | |

**User's choice:** Linked symbols at HEAD too
**Notes:** Recorded in CONTEXT D-04 with the reading that only failures introduced by the commit block; failures already at HEAD fall under the amber-note rule.

---

## Refusal and recovery

| Option | Description | Selected |
|--------|-------------|----------|
| Strip + per-part lines | Amber strip + one line per (part, rule), capped, also logged | ✓ |
| Strip + count only | One line, details in the log | |
| Inline on the file list | Amber file with tooltip | |

**User's choice:** Strip + per-part lines

| Option | Description | Selected |
|--------|-------------|----------|
| Fix, then re-check | "Open Check Atomic Parts…" link + "Check again", re-baseline, gate re-runs | ✓ |
| Explain only, commit by hand | Keep D-11 strict | |
| Re-check without the dialog link | Check again only | |

**User's choice:** Fix, then re-check

| Option | Description | Selected |
|--------|-------------|----------|
| Any change, shown and re-checked | Re-baseline any change, amber "changed since install", diff viewable | ✓ |
| Only the app's own fixes | Re-baseline only bytes the check dialog wrote | |
| Any change, without a separate diff | Silent re-baseline | |

**User's choice:** Any change, shown and re-checked

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same button | Check again also after a plain D-11 stale refusal | ✓ |
| Only after an atomic refusal | Stale refusal alone keeps today's behaviour | |

**User's choice:** Yes, same button

| Option | Description | Selected |
|--------|-------------|----------|
| Add files the parts need | New untracked model/footprint linked by a committed part joins the list, marked "added by a fix" | ✓ |
| Keep the list fixed, refuse | Refuse with "commit <file> first" | |

**User's choice:** Add files the parts need

---

## Uncertain git outcomes

| Option | Description | Selected |
|--------|-------------|----------|
| Report it, skip parent bump | Warning that the commit exists, no parent bump, manual parent command, no unstage | ✓ |
| Report it and continue the bump | Success with warning, continue to parent | |
| Stop, report, no manual command | Say the commit exists and stop | |

**User's choice:** Report it, skip parent bump

| Option | Description | Selected |
|--------|-------------|----------|
| Info line, carry on | INFO "Already identical to HEAD", parent bump continues; only extra files are ERROR | ✓ |
| Silent | Leave them out without saying so | |
| Mark them in the file list | Grey "unchanged" marker | |

**User's choice:** Info line, carry on

| Option | Description | Selected |
|--------|-------------|----------|
| Probe says so, Commit disabled | "Nothing to commit"; parent-only bump still offered when the gitlink is behind | ✓ |
| Probe says so, no parent offer | Whole panel disabled | |

**User's choice:** Probe says so, Commit disabled

| Option | Description | Selected |
|--------|-------------|----------|
| Keep it until the next action | Refusal stays above the fresh probe until the next click | ✓ |
| Replace with the probe result | Refusal only in the log | |

**User's choice:** Keep it until the next action

---

## Manual command and outcome look

| Option | Description | Selected |
|--------|-------------|----------|
| PowerShell quoting | Single quotes with '' doubling on Windows; shlex.quote on POSIX | ✓ |
| Message file (-F) | Save message to a file, shell-agnostic | |
| Both | PowerShell -m line plus -F alternative | |

**User's choice:** PowerShell quoting

| Option | Description | Selected |
|--------|-------------|----------|
| 'Committed in Custom only' | Disabled button with that label; ✓ Custom and ✖ parent lines | ✓ |
| 'Commit' disabled | Normal label, disabled | |
| 'Committed (parent failed)' | UI-review wording | |

**User's choice:** 'Committed in Custom only'

| Option | Description | Selected |
|--------|-------------|----------|
| Tinted strip per outcome | One strip, SUCCESS/ERROR/AMBER tint by strongest state | ✓ |
| Tint each line | Per-line backgrounds | |
| Text colour only | Only add the primary button | |

**User's choice:** Tinted strip per outcome

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, style Install too | Install Part also gets PRIMARY_BUTTON_QSS | ✓ |
| Commit only | Install's style left to Phase 12 | |

**User's choice:** Yes, style Install too

---

## Claude's Discretion

- REV-11 identity variables kept by `_env`, and the `input` → `stdin_data` rename
- IN-01 parent checkbox persistence, IN-02 probe not blocking Close
- The gate's AtomicContext/HEAD reading, feeding the check dialog from the import dialog, rescan after fixes
- Re-baseline storage, marker wording, parent-only button label, test strategy

## Deferred Ideas

None.
