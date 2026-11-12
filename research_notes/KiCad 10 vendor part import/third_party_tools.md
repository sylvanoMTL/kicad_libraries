# Third-party tools that import vendor parts (Ultra Librarian, SnapEDA/SnapMagic, SamacSys/CSE, loose files) into KiCad libraries

Research date: 2026-10-18. GitHub stars, issue counts and push dates come from the GitHub REST API (api.github.com) read on that date. "KiCad 10" evidence is thin for most tools, so each tool's KiCad 10 status is marked as confirmed, unconfirmed or contradicted.

## Q1. Which tools exist that take downloaded vendor packages (or loose files) and install them into a KiCad library?

### Takeaway
There are four active, maintained vendor-ZIP importers: Steffen-W's Import-LIB-KiCad-Plugin (the incumbent, PCM-installed), KiLM's `kilm import` (added 2026-10-12, so brand new), robertxdx's component-importer-for-kicad (desktop app, 2026) and Kandle (CLI, stale since 2024-04). Vendor-native tools (SnapMagic plugin and desktop app, SamacSys Library Loader, Ultra Librarian export) are either legacy, stuck at KiCad 5/6, or manual. The EasyEDA/LCSC converters (easyeda2kicad, JLC2KiCadLib) are a different source class and do not take the user's three vendor packages.

### Cited Findings

#### Catalogue table (summary)
| Tool | Type / install | Sources handled | Last push / release | Stars / open issues | KiCad 10 |
|---|---|---|---|---|---|
| Import-LIB-KiCad-Plugin (Steffen-W) | PCM plugin (IPC runtime), standalone wx GUI, CLI | Octopart, SamacSys, Ultra Librarian, SnapEDA, EasyEDA/LCSC | pushed 2026-10-12; release 2026.10.12 | 264 / 0 shown (see note) | Partly; 4 KiCad-10 issues filed and closed 2026-10-12 |
| KiLM `kilm import` (barisgit) | pip/pipx CLI | SamacSys/Mouser, Ultra Librarian, SnapMagic | pushed 2026-10-13; v0.6.0 2026-10-13 (import added in v0.5.6, 2026-10-12) | 30 / 4 | Unconfirmed ("KiCad 6.x and newer") |
| component-importer-for-kicad (robertxdx) | Desktop app (PyQt6) with Windows installer | SnapMagic/SnapEDA, CSE/SamacSys, Ultra Librarian | pushed 2026-08-26; v0.1.6 2026-08-18 | 55 / 1 | Not stated |
| Kandle (HarveyBates) | CLI | SnapEDA, Ultra Librarian, CSE | pushed 2024-04-29 | 48 / 3 | Not stated; stale |
| kicad_remote_import (topherbuckley), fork of wexi/impart | Script | Ultra Librarian, SnapEDA | pushed 2022-09-02 | 4 / 2 | Legacy; ancestor of Steffen-W's tool |
| KiCADSamacSysImporter (ulikoehler) | Script | SamacSys only | pushed 2020-05-30 | 3 / 0 | Dead |
| easyeda2kicad.py (uPesy) | pip CLI | LCSC/EasyEDA only | pushed 2026-04-08; v1.0.1 2026-04-06 | 1706 / 25 | "KiCad v6 and newer" per README; 10 not mentioned |
| JLC2KiCadLib (TousstNicolas) | pip CLI | JLCPCB/EasyEDA only | pushed 2026-09-11 | 486 / 9 | Not stated; author says project is "complete" |
| easyeda2kicad_plugin (rasmushauschild) | KiCad plugin | LCSC/EasyEDA only | pushed 2025-08-22 | 57 / 7 | Not stated |
| SnapMagic Search plugin | Manual .py install | SnapEDA | Legacy | n/a | No: "only supported by Kicad up to version 5.1.10" |
| SnapMagic Desktop App | Desktop app | SnapEDA | Article dated 2023-10-27 | n/a | No: steps cover "up to KiCad v6" |
| SamacSys / Supplyframe Library Loader | Vendor desktop app | Component Search Engine | Unknown | n/a | Unconfirmed |
| Ultra Librarian KiCad export | Manual import docs | Ultra Librarian | n/a | n/a | Manual only |

#### Import-LIB-KiCad-Plugin (Steffen-W) — closest existing tool to the user's need
- Description: "Helps to import KiCad component libraries imported from ultralibrarian and snapeda zipfiles"; GPL-3.0; created 2023-03-18; 264 stars; pushed 2026-10-12 — [GitHub API](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin)
- README: imports from Octopart, Samacsys, Ultralibrarian, Snapeda and EasyEDA; "symbols, footprints, descriptions, and if available, 3D files"; drag-and-drop ZIP import, standalone GUI (wxPython) and CLI (`python -m KiCadImport`) — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- Install: via KiCad Plugin and Content Manager (PCM) or "Install from File"; "Requires KiCad 9.0 or newer" — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- PCM metadata declares `"runtime": "ipc"`, `"kicad_version": "9.0"` (this is the older 2025.00.00 metadata on the master branch) — [metadata.json](https://raw.githubusercontent.com/Steffen-W/Import-LIB-KiCad-Plugin/master/metadata.json)
- Release cadence: 2026.01.07, 2026.02.08, 2026.02.15, 2026.03.03, 2026.03.08, 2026.10.12 — [releases](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/releases)
- Release 2026.10.12 notes: "Removes automatic writing of KiCad config files (manual setup now), requires KiCad 9.0+ for PCM installs, adds JLCPCB/EasyEDA component search with previews", plus 3D model compression and bug fixes — [releases](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/releases)
- The `open_issues_count` of 0 comes from the API, but the issue tracker clearly has issues (numbers up to #100), so 0 means all were closed. Several KiCad-10 issues were closed in a batch on 2026-10-12, the day of the release — [issue #96](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/96), [issue #100](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/100)

#### KiLM (barisgit/KiLM) — `kilm import`
- "KiCad Library Manager | Easily manage global libraries with github"; MIT; created 2025-03-09; 30 stars; 4 open issues; pushed 2026-10-13 — [GitHub API](https://api.github.com/repos/barisgit/kilm)
- Lists "Imports vendor part ZIPs from SamacSys/Mouser, UltraLibrarian, and SnapMagic into your library"; "Compatible with KiCad 6.x and newer"; Python 3.10+; Beta — [PyPI](https://pypi.org/project/kilm/)
- v0.5.6 (2026-10-12) "Added a `kilm import` command for vendor part ZIP files (PR #9)"; v0.6.0 (2026-10-13) has no import changes; v0.5.5 was 2026-06-07 and v0.5.4 2025-09-08, so the project is active but the import feature is days old — [releases](https://api.github.com/repos/barisgit/kilm/releases?per_page=4)
- Note: its Python package is named `kicad_lib_manager`, the same as the user's GUI package — [repo contents](https://api.github.com/repos/barisgit/kilm/contents). This is a naming collision only, not a functional issue.

#### component-importer-for-kicad (robertxdx)
- "open source universal component importer/library loader for kicad"; MIT; created 2026-05-18; 55 stars; 1 open issue; pushed 2026-08-26 — [GitHub API](https://api.github.com/repos/robertxdx/component-importer-for-kicad)
- Handles ZIPs from SnapMagic/SnapEDA, ComponentSearchEngine/SamacSys and Ultra Librarian; also `.kicad_sym`, `.kicad_mod`, `.step/.stp/.wrl/.stl`, `.pdf`, `.json` — [README](https://github.com/robertxdx/component-importer-for-kicad)
- Releases: v0.1.4 (2026-05-28, Symbol Style tab with live preview), v0.1.5 (2026-05-31), v0.1.6 (2026-08-18, simultaneous project and global library imports, Linux support, backups) — [releases](https://api.github.com/repos/robertxdx/component-importer-for-kicad/releases?per_page=3)

#### Kandle (HarveyBates)
- "A CLI that automatically imports external components into a KiCad project"; MIT; 48 stars; 3 open issues; last push 2024-04-29 — [GitHub API](https://api.github.com/repos/HarveyBates/kandle)
- Supports SnapEDA, Ultra Librarian and Component Search Engine files — [README](https://github.com/HarveyBates/kandle)

#### Older or narrow importers
- topherbuckley/kicad_remote_import is a fork of wexi/impart: 4 stars, pushed 2022-09-02, Apache-2.0 — [GitHub API](https://api.github.com/repos/topherbuckley/kicad_remote_import). A KiCad forum thread from June 2022 shows the author reworking it to automate SnapEDA/Ultra Librarian ZIP imports — [forum](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000)
- ulikoehler/KiCADSamacSysImporter is SamacSys-only, last pushed 2020-05-30 — [GitHub API](https://api.github.com/repos/ulikoehler/KiCADSamacSysImporter)
- adom-kicad-library-importer is a Rust CLI for KiCad 9 that patches footprint references and 3D paths and registers lib tables. It is tied to the Adom desktop relay and a search summary reports the GitHub repo is private. I could not fetch its README directly (404) — [Adom wiki page via search](https://wiki.adom.inc/kyle/adom-kicad-library-importer)

#### EasyEDA/LCSC converters (adjacent, not the three vendors)
- easyeda2kicad.py: "Convert any LCSC components (including EasyEDA) to KiCad library"; AGPL-3.0; 1706 stars; 25 open issues; pushed 2026-04-08; latest release v1.0.1 (2026-04-06) — [GitHub API](https://api.github.com/repos/uPesy/easyeda2kicad.py), [releases](https://api.github.com/repos/uPesy/easyeda2kicad.py/releases?per_page=3)
- JLC2KiCadLib: MIT; 486 stars; 9 open issues; pushed 2026-09-11 — [GitHub API](https://api.github.com/repos/TousstNicolas/JLC2KiCad_lib)
- rasmushauschild/easyeda2kicad_plugin: 57 stars; 7 open issues; pushed 2025-08-22; no license — [GitHub API](https://api.github.com/repos/rasmushauschild/easyeda2kicad_plugin)

#### Vendor-native tooling
- SnapMagic Search plugin page: "optimized for KiCad up to v5.1.10 (Beta)" and "only supported by Kicad up to version 5.1.10"; manual `snapeda_plugin.py` copy install — [SnapMagic plugins](https://www.snapeda.com/plugins)
- SnapMagic Desktop App article (dated 2023-10-27): steps apply "up to KiCad v6"; footprints go in a "SnapEDA Library"; 3D models "aren't linked to footprints yet"; opens Pcbnew because KiCad lacks schematic APIs — [SnapMagic support](https://support.snapmagic.com/en/articles/5612390-how-to-add-libraries-on-kicad-using-snapeda-desktop-app)
- A KiCad forum commenter in 2022 said SnapEDA's plugin lacked V6 support and Ultra Librarian had "no automated integration option" — [forum](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000)
- SamacSys Library Loader: needs V2.50+ for `.kicad_sym` files; user adds `SamacSys_Parts.kicad_sym` as a global symbol library and `SamacSys_Parts.pretty` as a global footprint library; default path `C:\SamacSys_PCB_Library\KiCad` — [SamacSys](https://www.samacsys.com/?p=321860) (301-redirects to supplyframe.com/samacsys; the guide text was seen via search snippet, not fetched)
- A KiCad forum reply notes the Library Loader is third-party and "isn't directly supported by anyone involved with KiCad" — [forum search result](https://forum.kicad.info/t/problem-library-loader-footprint-library/15993)
- Ultra Librarian KiCad 6.0+ help: manual steps. Add the `[date].lib` symbol file in Manage Symbol Libraries, add the `.pretty` folder in Manage Footprint Libraries, and load the STEP model by hand in Footprint Properties > 3D Models — [Ultra Librarian help](https://app.ultralibrarian.com/content/help/kicad-6_0.htm)
- Forum thread caveat: a commenter asked whether SnapEDA and Ultra Librarian licences permit automated handling; the author's answer was that manual login and download avoids the issue (forum discussion, not legal advice) — [forum](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000)

#### The user's own kipart-search (C:\Git_Repo_Clones\kipart-search)
- Local repo, origin `https://github.com/sylvanoMTL/kipart_search.git`; `pyproject.toml` description: "Parametric electronic component search with KiCad integration"; v0.2.3, MIT, authored by Sylvain Boyer (MecaFrog); depends on httpx, kicad-python, keyring, openpyxl, platformdirs, PySide6; last local commit 2026-04-01 — read from local `pyproject.toml`, `README.md` and `git log`
- The public GitHub URL returned 404 via the API (private or unpublished), so there is no public upstream description or star count to cite. It is a component search tool, not a vendor-package importer. It is unrelated to devbisme/kipart (symbol generator from spreadsheets) despite the similar name — [search result](https://github.com/devbisme/kipart)

#### Not found
- "kicad-footprint-importer": a search found no GitHub project by that name — [search](https://github.com/uPesy/easyeda2kicad.py) (closest hit was easyeda2kicad).
- Octopart: no standalone KiCad import integration found. Import-LIB lists "Octopart" as a supported ZIP source.

### Inferences
- The space moved fast in 2026: KiLM's vendor import (Oct 2026) and component-importer-for-kicad (created May 2026) are new entrants, so the user's tool is not the only candidate and it overlaps with these newcomers.
- Steffen-W's tool is the only one with large adoption (264 stars, in PCM) and sustained maintenance since 2023.
- All three active ZIP importers are young or fragile on KiCad 10; none is clearly "KiCad 10 proven".

### Gaps
- Could not verify the PCM listing page or download counts for Import-LIB; the README badge exists but no number was retrieved.
- Could not find any official SnapMagic, SamacSys or Ultra Librarian statement on KiCad 9/10 support. The SamacSys/Supplyframe page did not load usable Library Loader content.
- Could not fetch Octopart or JLCPCB-tools (Bouni) repos; they were not checked for relevance.
- The Adom importer README could not be fetched directly, so its details are second-hand.

## Q2. For each tool: how it installs, and what it does with naming, 3D model paths, library tables, duplicates and git; plus maintenance and KiCad 9/10 compatibility (including KiCad 10 Python/API changes)

### Takeaway
Behaviour varies a lot. KiLM and component-importer-for-kicad both back up before writing and skip duplicates; KiLM and Import-LIB leave library-table edits to the user or limit them. Import-LIB's KiCad 10 record is mixed: users reported failures in 10.0.3 and 10.0.4, including one data-loss incident where auto-setup wiped `kicad_common.json`, and the author responded in the 2026.10.12 release by removing automatic config writes. SWIG is deprecated but not removed in KiCad 10 (planned for 11), and IPC plugins work only in the PCB editor in 9 and 10.

### Cited Findings

#### Import-LIB-KiCad-Plugin: behaviour
- Naming: each source gets its own library by default (e.g. `Samacsys.kicad_sym`, `Snapeda.kicad_sym`, `UltraLibrarian.kicad_sym`, `EasyEDA.kicad_sym`, with matching `.pretty`). A "single lib name" option merges everything into one library; CLI: `--lib-name` ("Use a custom library name for all imports (e.g., 'Custom' instead of Samacsys/Snapeda/EasyEDA)") — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- 3D models: the user adds a `KICAD_3RD_PARTY` environment variable, and footprints reference models through it. CLI `--path-variable` sets the variable ("if only project-specific '${KIPRJMOD}' standard is '${KICAD_3RD_PARTY}'"); `--compress-models` writes `.step.gz`; `--prefer-step` for EasyEDA — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- The README warns that `KICAD9_3RD_PARTY`, `KICAD10_3RD_PARTY` etc. belong to the PCM, so users must add a separate `KICAD_3RD_PARTY` entry — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- Library tables: "The library paths must be added to KiCad manually. The plugin checks this configuration and lists missing entries, but never changes KiCad's settings itself." KiCad only accepts library entries whose file already exists, so the user imports one part first, then adds the libraries — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- Overwrite: CLI `--overwrite-if-exists`; duplicate handling is otherwise not documented in the README — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- Backups/git: none built in. The README says "please be sure to use git or some other means of backing up/reverting changes caused by this script. This script will modify existing lib, dcm, footprint or 3D model files." — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- No pre-write preview of the part was seen in the README; the 2026.10.12 release adds "component search with previews", which refers to the JLCPCB/EasyEDA search — [releases](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/releases)
- IPC API: "KiCad -> Settings -> Plugins -> Enable Plugin System" then "Enable KiCad API", restart; menu entry "impartGUI (IPC API)" in PCB and Schematic editors; falls back to a pcbnew-based solution with manual dependency setup when the API is off — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)

#### Import-LIB-KiCad-Plugin: KiCad 10 evidence
- README badge still reads "Supports KiCad v6, v7, v8, v9" (no v10), while the README text says "Requires KiCad 9.0 or newer" — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme)
- Issue #95 (2026-05-25, closed 2026-10-12): user says it is listed as compatible in the plugin browser but "only partly works in legacy run mode" on KiCad 10. The owner replied he was staying on KiCad 9 for an ongoing project and had not tested on 10. A commenter noted KiCad 10 renamed defaults (`kicad10_3rd_party`, `kicad10_xxx`) — [issue #95](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/95), [comments](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/95/comments)
- Issue #96 (KiCad 10.0.3, Linux, plugin 2026.04.07, closed 2026-10-12): IPC button works in the Schematic Editor but not the PCB Editor; KiCad won't register a new symbol library unless the file exists with a valid header; SamacSys import fails unless the target matches KiCad's third-party path; saving to the project folder fails with "no KiCad project available"; configuration features land in the Description field — [issue #96](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/96)
- Issue #100 (KiCad 10.0.4, Windows, plugin 2026.04.07, opened 2026-09-15, closed 2026-10-12): automatic library setup shrank `kicad_common.json` from 66 KB to 4 KB, deleting environment variables, so KiCad dropped every library table row using `${KICAD_3RD_PARTY}`. Reporter suspects a failed read returned an empty dict that was written back. Workaround: `auto_lib = False` in `config.ini`. Owner acknowledged the same day — [issue #100](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/100), [comments](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/100/comments)
- Issue #98 (KiCad 10.0.4, macOS): "Save local, in the project folder" always defaulted to global library mode — [issue list](https://api.github.com/search/issues?q=repo:Steffen-W/Import-LIB-KiCad-Plugin+is:issue+KiCad+10)
- Issue #94 (KiCad nightly, macOS): install triggered an "incompatible Python API" warning — [issue list](https://api.github.com/search/issues?q=repo:Steffen-W/Import-LIB-KiCad-Plugin+is:issue+KiCad+10)
- The 2026.10.12 release then "Removes automatic writing of KiCad config files (manual setup now)" — [releases](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/releases). I did not test the release, so whether it fully fixes the KiCad 10 issues is unverified.

#### KiCad 10 / Python / API platform facts
- KiCad 10.0.0 was published 2026-03-20; it ships STEP-only 3D models and added Allegro, PADS and gEDA/Lepton PCB importers; the announcement does not mention plugins, SWIG or the IPC API — [KiCad blog](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- SWIG: "deprecated since KiCad 9.0 and will be removed in a future version... The current plan is to remove the SWIG bindings in KiCad 11.0"; new plugins should use the IPC API — [KiCad dev docs](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/). So SWIG action plugins are not formally removed in KiCad 10.
- IPC API: introduced in 9.0; "KiCad 9 and 10 support IPC plugins only in the PCB Editor. KiCad 11 adds Schematic Editor plugin support." IPC plugins live under `${KICAD_DOCUMENTS_HOME}/<version>/plugins/<name>/plugin.json`; Python plugins get an auto-created virtual environment — [KiCad dev docs](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
- Search-result summary of the same docs says IPC in 9/10 "only works with a running GUI instance" and headless kicad-cli support arrived in 11 — [search result citing dev-docs](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/). Contradiction to note: Import-LIB's README says the IPC plugin is available from the Schematic Editor, while the dev docs say schematic IPC plugin support arrives in KiCad 11. I could not reconcile this; the README may refer to a pre-release or a limited entry point.
- A KiCad forum thread reported KiCad 10 changed default environment variable names and library defaults (e.g. `kicad10_3rd_party`), reported in issue #95 above — [issue #95 comments](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/95/comments)
- Third-party summary: the IPC server must be enabled under Preferences > Plugins; 10.0.0 had IPC usability problems and 10.0.1 fixed plugin-management bugs — [search summary](https://forum.pedalpcb.com/threads/kicad-version-10-released.28834/latest) (secondary source, forum post)

#### KiLM `kilm import`: behaviour (from the merged PR description)
- Command: `kilm import [OPTIONS] ZIP_FILES...` with `--library/-l`, `--symbol-lib/-s`, `--footprint-lib/-f`, `--kicad-cli`, `--dry-run` — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- Handles SnapMagic ZIPs, which have no wrapper directory, by searching the extracted tree by extension — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- Naming/linking: imported symbols get the `LIB:` footprint prefix and the Footprint field points at the footprint library; new footprints keep the original stem with a lowercase `.kicad_mod` extension. It does not rename parts to a convention — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- 3D models: references are rewritten to the copied model, incl. quoted and gzipped `.step.gz` names; models go into a 3D library registered with `kilm add-3d` and referenced by its environment variable; with none it reuses an existing `*.3dshapes` dir, else falls back to an absolute path with a warning. Absolute paths "break for anyone else using a shared library" — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- Safety: symbol library backed up once per run; writes go to a hidden sibling file then rename over the target (atomic); each ZIP fully planned before any write; `--dry-run` stops before writing; zip-slip guard; vendor files in a newer format than the library are rejected — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- Duplicates: existing symbols/footprints are skipped so re-running is safe — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- Library tables / git: the PR page does not cover `sym-lib-table`/`fp-lib-table` edits or git commits. KiLM's README shows `kilm init/setup/status` and says KiLM sets environment variables in the KiCad config and makes timestamped config backups; docs mention "Git integration" for creator/consumer workflows but give no detail — [KiLM docs](https://kilm.aristovnik.me), [PyPI](https://pypi.org/project/kilm/)
- Test suite: 182 passing tests reported by the PR author — [PR #9](https://github.com/barisgit/KiLM/pull/9)
- KiCad 10: the only compatibility statement is "KiCad 6.x and newer"; v0.5.5 (2026-06-07) "Fixed KiCad config version selection" — [PyPI](https://pypi.org/project/kilm/), [releases](https://api.github.com/repos/barisgit/kilm/releases?per_page=4). KiLM is a standalone CLI that edits KiCad config files, so it does not depend on the Python/IPC plugin APIs (inference).

#### component-importer-for-kicad: behaviour
- Windows `KiCadComponentImporter_Setup.exe` installer, AUR package, Ubuntu tarball, or source (Python 3.10+, PyQt6); not a PCM plugin — [README](https://github.com/robertxdx/component-importer-for-kicad)
- Repairs the 3D-model reference inside each imported footprint; backs up before modifying existing symbols, footprints, metadata or library tables; detects and skips duplicates; registers imports in `sym-lib-table`/`fp-lib-table` (project or global); tells the user to close KiCad before first global setup; rejects unsafe archives — [README](https://github.com/robertxdx/component-importer-for-kicad)
- Adds a Symbol Style tab with live preview that normalises outlines, fills and pin lengths (v0.1.4) — [releases](https://api.github.com/repos/robertxdx/component-importer-for-kicad/releases?per_page=3)
- Preview, git and naming rules: README mentions none of these; the supported KiCad versions are not stated — [README](https://github.com/robertxdx/component-importer-for-kicad)

#### Kandle: behaviour
- `kandle -I` creates `components/extern/{3dmodels,footprints,symbols,tmp}` plus `fp-info-table`/`sym-info-table` in the project dir; `kandle -f <zip> -l <library_name>` imports; converts KiCad v4 `.lib` symbols to v6 `.kicad_sym`; auto-links symbol to footprint; strips `ul_` and `LIB_` prefixes and replaces hyphens/spaces with underscores (e.g. `LIB_PESD 0402-140.zip` becomes `PESD_0402_140`) — [README](https://github.com/HarveyBates/kandle)
- Project-local only (must be run in the dir with the `.kicad_pro`); the user adds libraries manually; last push 2024-04-29 — [README](https://github.com/HarveyBates/kandle), [GitHub API](https://api.github.com/repos/HarveyBates/kandle)

#### easyeda2kicad.py and JLC2KiCadLib (LCSC/EasyEDA only)
- easyeda2kicad: `pip install easyeda2kicad`; `--full/--symbol/--footprint/--3d/--svg`, `--output`, `--overwrite`, `--project-relative`; default outputs `easyeda2kicad.kicad_sym`, `.pretty`, `.3dshapes`; 3D paths absolute by default, `${KIPRJMOD}/...` with `--project-relative`; user adds an `EASYEDA2KICAD` path variable and library entries manually; "supports KiCad v6 and newer" — [README](https://raw.githubusercontent.com/uPesy/easyeda2kicad.py/master/README.md)
- JLC2KiCadLib: `pip install JLC2KiCadLib`; `-dir`, `-symbol_lib`, `-footprint_lib`, `-models STEP/WRL`, `-model_base_variable`, `--skip_existing`; footprint names derived from the package (e.g. `QFN-24_L4.0-W4.0-P0.50-BL-EP2.7`); courtyard approximated with 0.25 mm clearance; no library-table handling; author considers the project complete, with bug fixes only — [README](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/README.md)

#### Vendor tools: behaviour
- SnapMagic desktop app: footprints appear under "SnapEDA Library", 3D models downloaded to `C:\Users\<user>\SnapEDA Kicad Plugin\KiCad Library\SnapEDA 3D Models` and imported manually; no library table info — [SnapMagic support](https://support.snapmagic.com/en/articles/5612390-how-to-add-libraries-on-kicad-using-snapeda-desktop-app)
- Library Loader: one fixed library `SamacSys_Parts`; parts accumulate in that library; the user adds the global library entries once — [SamacSys](https://www.samacsys.com/?p=321860) (via search snippet)
- Ultra Librarian: no installer; fully manual steps, per-part project-specific library nicknames, 3D STEP loaded by hand — [Ultra Librarian help](https://app.ultralibrarian.com/content/help/kicad-6_0.htm)

### Inferences
- For KiCad 10 specifically, the Python-plugin-versus-standalone choice matters. A PCM IPC plugin (Import-LIB) depends on the IPC runtime, which is PCB-editor-only in KiCad 10; standalone tools (KiLM, component-importer, a PySide6 app like the user's) avoid that dependency. The user's GUI is standalone, so KiCad 10 plugin API churn does not affect it.
- Import-LIB's known destructive behaviour (rewriting `kicad_common.json`) is directly relevant to the user's existing `sync_kicad_path_vars` function in `library_scanner.py`, which also writes `kicad_common.json`. The same read-failure-then-overwrite failure mode should be guarded (read failure must never write; merge rather than rewrite; temp-file-and-rename). This is an inference from issue #100 plus the project's own notes that it reads and writes `kicad_common.json`.
- KiLM's `kilm import` is the best reference design to study (plan-everything-then-write, dry run, single backup, atomic rename, zip-slip guard, case-insensitive matching, duplicate skip).

### Gaps
- No tool's behaviour was confirmed by running it; all descriptions come from READMEs, PRs and issues.
- KiLM's full docs (CLI reference) were not retrievable (docs source fetch returned 401), so the details of `kilm import` rely on the PR description.
- Whether the Import-LIB 2026.10.12 release actually fixes issues #94-#100 on KiCad 10 is unverified.
- KiCad 10 details of the library-table file format or path variable changes (`KICAD10_3DMODEL_DIR` etc.) were not found in the official release post; only the forum report in issue #95 mentions renamed defaults.
- SnapMagic/Ultra Librarian/SamacSys current ZIP layouts for KiCad 10-era downloads were not researched here (covered by sample files in `downloaded_examples/`).

## Q3. What do these tools NOT do that a naming-convention-enforcing, git-submodule-aware importer would?

### Takeaway
None of the tools found enforces a `<Type>_<SubCategory>_<Manufacturer>` library convention, rewrites 3D paths to a repo-specific variable like `${CUSTOM_3DMODEL_DIR}` by default, shows a part preview before every write plus an atomic/backup guarantee, or runs a confirmed git commit inside a submodule. Each of those four is partly covered by one tool or another, but no tool combines them.

### Cited Findings

| Capability the user wants | Closest existing behaviour | Gap |
|---|---|---|
| Rename/route into `<Type>_<SubCategory>_<Manufacturer>` libraries and pair `.kicad_sym` with `.pretty` | Import-LIB: per-source libs (`Samacsys`, `Snapeda`...) or one custom name via `--lib-name` — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme). KiLM: user picks target with `-s`/`-f` — [PR #9](https://github.com/barisgit/KiLM/pull/9). Kandle: strips `ul_`/`LIB_`, replaces hyphens/spaces — [README](https://github.com/HarveyBates/kandle) | No tool validates a naming scheme, derives a name from part metadata, or forces symbol and footprint folder stems to match. |
| Rewrite 3D path to `${CUSTOM_3DMODEL_DIR}/<file>.step` | Import-LIB: configurable `--path-variable` defaulting to `${KICAD_3RD_PARTY}`. KiLM: rewrites to the library's registered 3D env var, else absolute path with warning. component-importer: "repairs the 3D-model reference" | The variable is configurable in one tool, but none ships a "one named variable, flat `.step` file in a fixed folder" convention, and none verifies the variable resolves. |
| Preview before write | KiLM `--dry-run` (reports plan and failures, writes nothing) — [PR #9](https://github.com/barisgit/KiLM/pull/9). component-importer: live preview of symbol style — [releases](https://api.github.com/repos/robertxdx/component-importer-for-kicad/releases?per_page=3) | Dry-run is CLI text; no tool found shows a symbol/footprint/3D preview plus the exact name/path diff as a required step before install. |
| Backup / atomic writes | KiLM: single backup per run, hidden sibling file then rename. component-importer: backups before changes. Import-LIB: none, tells user to use git — [README](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/readme). Import-LIB issue #100 shows a destructive non-atomic write — [issue #100](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/100) | Atomic/backup is solved by KiLM; it is a pattern to copy, not a gap in the field. |
| Library-table refresh | component-importer: writes `sym-lib-table`/`fp-lib-table`. Import-LIB: never edits tables (as of 2026.10.12). KiLM: not covered by the import PR | Only the relative `${KICAD_LIB_GITHUB}/...` managed-marker style used in this repo is not supported by any tool. |
| Duplicate handling | KiLM skips existing; component-importer detects and skips; easyeda2kicad/Import-LIB offer overwrite flags | No tool offers a "replace / keep / rename" per-part decision UI (not documented in any README read). |
| Git commit inside a submodule, then parent update | Not mentioned in any README or PR read (Import-LIB: "use git"; component-importer, KiLM import, Kandle: nothing) | Entirely absent. No submodule awareness, no "commit in Custom first, then update the parent pointer" flow, no confirmation gate. |
| Multi-vendor in one tool plus loose files | Import-LIB, KiLM, component-importer cover all three vendors. Loose-file support: component-importer lists `.kicad_sym/.kicad_mod/.step` and lone files as supported file types | Naming/preview/commit absent as above. |

- Licensing caveat to consider when automating: a forum commenter raised whether SnapEDA/Ultra Librarian licences permit automated handling; the thread's author said manual download avoids the issue — [forum](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000)
- Quality caveat: a forum commenter reported the vendor footprints and symbols "often contain significant errors" and the importer author saw symbols split into unnecessary multiple parts — [forum](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000). Import-LIB issue #96 reports configuration data landing in the Description field instead of dedicated fields — [issue #96](https://api.github.com/repos/Steffen-W/Import-LIB-KiCad-Plugin/issues/96)

### Inferences
- The differentiators that no existing tool combines are: (1) enforced naming convention with symbol/footprint stem pairing, (2) a single fixed 3D variable written into the footprint, (3) preview-then-install gated on the exact diff, and (4) confirmed git commit in a submodule followed by parent-ref update. Items (1) and (4) are fully unaddressed; (2) and (3) are partially addressed by KiLM and component-importer.
- KiLM's import (Oct 2026) and Import-LIB are the two serious "build vs adopt" comparisons. Adopting either would still leave naming, 3D variable and git commit to be built, and Import-LIB's `.pretty`/`.kicad_sym` layout (one library per source) conflicts with the repo's per-category layout.
- Re-scoping risk: because KiLM already merges into an existing library with symbol/footprint/3D rewriting, atomic writes and dry-run, the user's importer should take ideas from it (and could even reuse its algorithms, MIT-licensed) rather than reimplementing from scratch.

### Gaps
- The absence of git features is based on READMEs/PR text; I did not read source code of any tool, so a hidden `git` call could exist.
- Whether component-importer's footprint 3D repair supports a user-chosen variable is not stated in its README.
- Whether KiLM's `kilm import` writes `fp-lib-table`/`sym-lib-table` entries was not documented in the sources I could fetch.
