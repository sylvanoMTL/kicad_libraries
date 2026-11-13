# Phase 12: Import Flow Fixes and Case-Sensitive Re-test - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-01
**Phase:** 12-import-flow-fixes-and-case-sensitive-re-test
**Areas discussed:** Library name already taken, Waiting on kicad-cli, KiCad running / file changed, Case-sensitive re-test

---

## Library name already taken

**Q: A tool-owned entry with the installed library's name points at a missing file. What should the table step do?**

| Option | Description | Selected |
|--------|-------------|----------|
| Repoint it | The entry is ours and dead; give it the new path (backed up) | ✓ |
| Warn only | Leave the table; amber row suggests pressing Generate | |

**Q: The tool-owned entry points at another library that still exists (e.g. Würth IC_X). What should happen?**

| Option | Description | Selected |
|--------|-------------|----------|
| Warn, keep the old one | Table unchanged; amber row says KiCad still loads the other library | ✓ |
| Ask which one wins | Yes/No dialog to repoint the name | |

**Q: Install into an existing library whose tool-owned entry is stale?**

| Option | Description | Selected |
|--------|-------------|----------|
| Same repoint rule | One rule for both kinds of install; a fully missing library keeps the Generate hint | ✓ |
| Hint only, as today | Existing-library installs never write tables | |

**Q: The name is taken by a hand-added (external) entry?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep the warning | Never edit external entries; plainer wording | ✓ |
| Treat stale ones like ours | Repoint a dead external entry too | |

**User's choice:** Repoint stale tool-owned entries for both new and existing libraries. Live clashes and hand-added entries only warn.

---

## Waiting on kicad-cli

**Q: Change..., open another package or close while a preview build runs?**

| Option | Description | Selected |
|--------|-------------|----------|
| Finishing..., then it happens | Dialog greys out, window stays responsive, action runs by itself | ✓ |
| Refuse and say why | Status line; user clicks again later | |
| Stop kicad-cli at once | Kill kicad-cli; action happens immediately | |

**Q: A way out of a hung kicad-cli?**

| Option | Description | Selected |
|--------|-------------|----------|
| Cancel button + countdown | Cancel drops the pending action; slow note after 10 s; nothing killed | ✓ |
| Just wait | 60 s timeout is the bound | |
| Cancel also stops kicad-cli | Kill on cancel; needs a stoppable launch | |

**Q: Install while a one-off conflict build runs?**

| Option | Description | Selected |
|--------|-------------|----------|
| Disabled with "Updating..." | Same as a normal rebuild; one-off jobs held during install | ✓ |
| Accept the click, install after | Click waits for the one-off, then installs | |

**User's choice:** Finishing state with Cancel and a 10 s slow-response note; Install disabled during one-off builds.

---

## KiCad running / file changed

**Q: What should the path-variable dialog offer when KiCad is open?**

| Option | Description | Selected |
|--------|-------------|----------|
| Retry / Change anyway / Not now | Names the open programs; default Retry | ✓ |
| Yes/No with a warning line | Today's dialog plus one line | |
| Refuse while KiCad runs | No write; log says close KiCad and Generate | |

**Q: The file changed while the dialog was open?**

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into the fresh file | Set only the two vars on the fresh content; re-ask if the needed changes differ | ✓ |
| Stop and ask again every time | Any change means no write; dialog returns | |
| Stop, write nothing | Abort with a log line (v1.0 review fix) | |

**Q: After "Change anyway", KiCad may undo the paths on exit?**

| Option | Description | Selected |
|--------|-------------|----------|
| Clear log line only | Warning says how to redo; Generate re-offers the change | ✓ |
| Also note a startup check for later | Deferred feature idea | |

**User's choice:** Three-button dialog when KiCad is open; merge into the fresh file; log line only.

---

## Case-sensitive re-test

**Q: How to prove case-twin rollback and overwrite?**

| Option | Description | Selected |
|--------|-------------|----------|
| Automated test + you run it once | Real case-sensitive temp folder (fsutil / Linux); UAT = pass, not skip | ✓ |
| Automated test only | Green suite closes VER-02 | |
| Hands-on import by you | GUI imports on a case-sensitive scratch repo | |

**Q: A successful overwrite of foo.STEP by incoming Foo.step on a case-sensitive folder?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep the existing spelling | New bytes into foo.STEP; footprint links foo.STEP; one file | ✓ |
| Take the incoming spelling | Write Foo.step, remove foo.STEP; other links may break | |
| Researcher decides | Match today's NTFS end state | |

**User's choice:** Automated tests plus one owner run; overwrite keeps the spelling already on disk.
**Notes:** Per-folder case sensitivity (`fsutil file setCaseSensitiveInfo`) was verified to work on the owner's machine without admin rights before the question was asked.

---

## Claude's Discretion

- Empty Destination handling (REV-02): one blank-rejecting helper used everywhere the Destination text becomes a path.
- Help dialog and conflict-row theming (UI-01): CSS from `theme.py` tokens, pt sizes, `SP_*` padding; owner checks via screenshots.
- Same-spelling rule extends to footprint files; wording of the new strips, dialog and rows; path compare ignores case on Windows; how the KiCad-open check moves off the GUI thread.

## Deferred Ideas

None.
