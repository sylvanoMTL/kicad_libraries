# Phase 2: Hardening Existing Code - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log keeps the alternatives that were considered.

**Date:** 2026-10-18
**Phase:** 02-hardening-existing-code
**Areas discussed:** Library identity, Table merge output, kicad_common.json writes, Model path cleanup

---

## Library identity

**Same nickname in Custom and Wurth**

| Option | Description | Selected |
|--------|-------------|----------|
| Mutually exclusive | Both shown with a collision warning; checking one unchecks the other | ✓ |
| Block Generate | Allow both to be checked; Generate refuses with an error | |
| Custom wins | The other source's copy is shown disabled | |

**Repo library vs an external table entry with the same nickname**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep external, skip repo | External untouched, repo library not written, warning names both URIs | ✓ |
| Repo replaces external | Managed entry overwrites the external one, logged and kept in the backup | |
| Block Generate | Refuse until resolved | |

**A library appearing for the first time on Rescan**

| Option | Description | Selected |
|--------|-------------|----------|
| Unchecked | Opt-in only; Phase 5 may select the library it installed into | ✓ |
| Checked | Auto opt-in | |
| Checked only if in Custom | New Custom libraries auto-checked, third-party ones unchecked | |

**Destination switch: reload the selection from that folder's tables?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep, don't reload | Only startup reads the tables | ✓ |
| Reload from new dest | Mirror the folder, losing unsaved checks | |
| Ask each time | Prompt when the selection differs | |

---

## Table merge output

**Regenerated table layout**

| Option | Description | Selected |
|--------|-------------|----------|
| Splice in place | Non-managed bytes untouched; managed block replaced as one run | ✓ |
| Rewrite, externals verbatim | Today's layout, with spacing normalised | |
| Splice, managed in place | Update each managed entry where it sits; append new ones | |

**Stale managed entry (library gone from the repo)**

| Option | Description | Selected |
|--------|-------------|----------|
| Remove and warn | Drop it, with a warning naming it | ✓ |
| Keep and warn | Leave it in place for the user to clean up | |
| Remove silently | Same as a deselected library | |

**Unparseable existing table**

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse that file | Error with line/col, file untouched, the other table still generates | ✓ |
| Back up, then overwrite | Externals survive only in the backup | |
| Refuse both tables | Keep sym and fp in step | |

**Legacy CLI `generate_lib_tables.py`**

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | Remove the script and its CLAUDE.md mentions | ✓ |
| Thin wrapper | CLI calls scan_all + write_tables | |
| Leave as is | Keeps its bugs | |

---

## kicad_common.json writes

**Which KiCad config versions to write**

| Option | Description | Selected |
|--------|-------------|----------|
| Newest only | Numeric sort fixed; older installs untouched | ✓ |
| All installed | Write every version folder | |
| Newest + log others | Write the newest, report stale older ones | |

**How strict "only environment.vars differs" is**

| Option | Description | Selected |
|--------|-------------|----------|
| Semantic | Re-dump with indent 2, re-parse and assert only the vars changed | ✓ |
| Byte-level splice | Splice only the vars bytes | |

**KiCad running**

| Option | Description | Selected |
|--------|-------------|----------|
| Detect and warn | Process-list check; still write; warn | ✓ |
| Detect and skip | Skip the config write only | |
| Always warn, no detection | Generic advice | |

**Backup timing and retention**

| Option | Description | Selected |
|--------|-------------|----------|
| Only on change, keep 10 | No write means no backup; prune to the newest 10 | ✓ |
| Only on change, keep all | Never prune | |
| Every Generate, keep 10 | Back up even when nothing changes | |

---

## Model path cleanup

**How the five `${KIPRJMOD}` footprints are rewritten**

| Option | Description | Selected |
|--------|-------------|----------|
| One-off in this phase | Tested splice helper run once; commit; scan warning only | ✓ |
| Tool feature | GUI "Fix legacy model paths" action | |
| Manual by owner | Phase adds only the warning | |

**Scan warning scope**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-source rule | Custom strict; other sources warn only on absolute/non-variable paths | ✓ |
| Custom only | Skip other sources | |
| Everywhere strict | Noisy on Wurth | |

**Commit flow**

| Option | Description | Selected |
|--------|-------------|----------|
| Also bump parent ref | Custom commit on main, then a parent ref bump; no push | ✓ |
| Custom only | Owner bumps the parent later | |
| Pause for me first | Human checkpoint before the commits | |

**Missing model file warning**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, warn | Exact-case existence check in Custom/3DModels | ✓ |
| Yes, ignore case | Quieter on Windows | |
| No | Leave it to Phase 4 verification | |

---

## Claude's Discretion

- Busy-guard UX (disable actions vs a guarded `_start_scan`)
- How the collision mark is shown in the tree
- Names of the new `Issue.code` values
- The insert point when managed entries were scattered
- The fix for the `LogPanel.COLORS` / `Severity` KeyError
- The order of the table and config writes, and whether their failures are reported independently
- A Restore confirmation, only if it falls out naturally
- Table backup retention (unchanged unless needed)

## Deferred Ideas

- A GUI "Fix legacy model paths" action
- Writing path vars to every installed KiCad version
- Byte-level JSON splicing for `kicad_common.json`
