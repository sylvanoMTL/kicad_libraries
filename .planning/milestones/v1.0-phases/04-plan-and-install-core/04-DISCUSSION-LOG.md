# Phase 4: Plan and Install Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-19
**Phase:** 04-plan-and-install-core
**Areas discussed:** Format version policy, Conflicts & idempotence, Fields written on install, Failure, rollback & verify

---

## Format version policy

**Q: Incoming symbol version differs from the target library's**

| Option | Description | Selected |
|--------|-------------|----------|
| Match target | Equal → as-is; older → kicad-cli upgrade; newer → refuse ("open and save in KiCad first") | ✓ |
| Always normalise | Upgrade to installed KiCad and splice even into older-header libraries | |
| Let the spike decide | Spike first, then pick | |

**Q: Footprint normalisation (kicad-cli fp upgrade assigns random UUIDs)**

| Option | Description | Selected |
|--------|-------------|----------|
| Copy as-is | Only name, value text, model node edited; deterministic | ✓ |
| Normalise, compare without UUIDs | Ignore uuid/tstamp for idempotence | |
| Normalise, deterministic UUIDs | Replace UUIDs with content-hash ones | |

**Q: kicad-cli as a load gate before writing**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, block on failure | Refuse install on non-zero exit; skip with info when absent | ✓ |
| Yes, warn only | | |
| No gate | | |

**Q: New library header version**

| Option | Description | Selected |
|--------|-------------|----------|
| Installed KiCad's format | 20241209 via kicad-cli; vendor version without it | ✓ |
| Vendor file's version | | |
| You decide | | |

**Q: kicad-cli would upgrade past an older target header (e.g. into IC_IMU_TDK at 20231120)**

| Option | Description | Selected |
|--------|-------------|----------|
| Merge vendor text as-is | Normalise only when output == target version; else as-is + warning | ✓ |
| Refuse | | |

**Notes:** Footprint decision amends INST-06 / ROADMAP Phase 4 SC3 (symbol-only normalisation).

---

## Conflicts & idempotence

| Question | Options | Selected |
|----------|---------|----------|
| Unresolved conflict default | Block until chosen / Default to skip / Default to rename | Block until chosen |
| Rename name source | Suggest free name, editable / Caller must supply it | Suggest free name, editable |
| "Identical" definition | Byte-equal to planned output / Semantically equal | Byte-equal to planned output |
| Symbol overwrite placement | Replace in place / Remove and append | Replace in place |
| Skip on footprint/model | Link to existing item / Leave unlinked | Link to existing item |
| Case-only file clash | Treat as a conflict / Warn only | Treat as a conflict |

---

## Fields written on install

| Question | Options | Selected |
|----------|---------|----------|
| Manufacturer/MPN defaults | Always fill both / MPN only, Manufacturer if known / Only what the caller passes | Always fill both |
| Vendor equivalent fields (MF, MP, …) | Rename to Manufacturer/MPN / Keep them, add ours / Remove them, add ours | Rename to Manufacturer/MPN |
| `extends` | Import parent too / Refuse | Import parent too |
| Items per install | 1 symbol, 1+ footprints, 0-1 model / Exactly one of each / Anything chosen | 1 symbol, 1+ footprints, 0-1 model |
| Fields following a rename | Follow only exact matches / Only the names themselves | Follow only exact matches |
| Manufacturer/MPN visibility | Hidden / Visible | Hidden |
| ki_fp_filters | Exact installed FP names / Keep vendor value / You decide | Exact installed FP names |

---

## Failure, rollback & verify

| Question | Options | Selected |
|----------|---------|----------|
| Verification fails after writes | Roll back everything / Keep and report error | Roll back everything |
| Crash safety | App-data backups, no journal / Journal + recovery on startup / In-memory only | App-data backups, no journal |
| Pin/pad mismatch rule | Both directions, listed / Pins without pads only | Both directions, listed |
| Duplicate-name search scope | All repo sources + KiCad stock / Custom only / Repo sources only | All repo sources + KiCad stock |
| How the phase proves KiCad loads the part | kicad-cli test + manual UAT / Automated only / Real install into Custom/ | kicad-cli test + manual UAT |

---

## Claude's Discretion

- Module layout, plan/conflict/result dataclass shapes, Issue codes
- WR-04 (staged-file lifetime) and WR-05 (package issues reaching the candidate) resolution mechanism
- Description property per target version (`ki_description` vs `Description`), new property layout
- kicad-cli timeout, backup retention N, stock symbol dir location, empty-library template

## Deferred Ideas

None.
