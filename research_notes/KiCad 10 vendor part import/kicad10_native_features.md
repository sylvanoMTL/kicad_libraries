# KiCad 10 native features for importing and managing library parts

Research date: 2026-10-18. Latest KiCad 10 point release found: 10.0.7 (2026-10-07). The assignment said "up to ~10.0.6 by Aug 2026"; 10.0.6 was released 2026-08-29 and 10.0.7 now exists.

## Does KiCad 10 have a built-in import of vendor part packages (Ultra Librarian, SnapEDA, SamacSys/CSE, zip, loose files)?

### Takeaway
No. I found no built-in feature in KiCad 10 that takes a vendor zip or a folder of loose files and installs symbol, footprint and 3D model into a user library. KiCad 10 does add a "remote symbol provider" protocol (a panel in the Schematic Editor that downloads symbol/footprint/3D assets from a provider you configure) and nested library tables, but neither is a vendor-zip importer, and no default provider ships. Vendor zips still require manual library-table additions or third-party tools.

### Cited Findings
- The official 10.0.0 announcement lists new importers for Allegro, PADS and gEDA/Lepton PCB, with no mention of a vendor part or zip importer. Library items in the post: STEP-only official 3D models, Symbol Editor Pin Table CSV export/import, alternate body styles, inner-layer footprint objects, design blocks in the PCB editor. — [Version 10.0.0 Released](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- The three new importers are project-level importers, not part importers. Allegro is .brd v16-23, board only ("no schematic support - yet"). PADS covers ASCII .asc schematics and boards. gEDA/Lepton covers .sch, .pcb and .fp, and is the only one of the three with library browsing (it can load individual .fp footprint files from directory libraries). — [Three New Importers in KiCad 10](https://www.kicad.org/blog/2026/02/Three-New-Importers-in-KiCad-10-Allegro-PADS-and-gEDA/)
- Symbol Editor "File > Import > Symbol..." only imports symbols from an external **KiCad** library into a loaded destination library. The source library need not be in the library tables; derived symbols bring their base symbol along. Other File menu items listed: New Library, Save As, Save Copy As, Export > Symbol. — [KiCad 10.0 Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Foreign formats are handled by adding the file as a library in Manage Symbol Libraries, not via a Symbol Editor import wizard. Supported symbol library types in the 10.0 manual: KiCad .kicad_sym (file or folder), KiCad legacy .lib, Altium .SchLib/.IntLib, CADSTAR .lib, Eagle .xml, EasyEDA (JLCEDA) Standard .json, EasyEDA Professional .elibz/.epro/.zip, plus .kicad_dbl (database) and .kicad_httplib (HTTP) config files. LTspice is not listed in that section. Only KiCad-format libraries can be saved (footprints; see below). — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Footprint library manual text: supported/writable format is KiCad .pretty folders of .kicad_mod; "Only KiCad format libraries ... can be saved." The excerpt I retrieved did not list non-KiCad footprint formats or the Footprint Editor File > Import menu. — [KiCad 10.0 PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
- No new "vendor import" items appear in the 10.0.1-10.0.7 changelogs. Import fixes are for Altium, Eagle, PADS, Allegro, CADSTAR, LTspice, EasyEDA Pro and DXF. Examples: "Remove illegal library name characters when importing EasyEDA Pro projects" (10.0.1), "Fix crash when importing an Altium footprint library" (#24278, 10.0.3), "Fix missing rectangle fill mode when importing Eagle symbol library" (#24581, 10.0.5). — [10.0.1](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/), [10.0.3](https://www.kicad.org/blog/2026/05/KiCad-10.0.3-Release/), [10.0.5](https://www.kicad.org/blog/2026/07/KiCad-10.0.5-Release/)
- **Remote symbol providers (new in the 10.x line, closest native analogue to a part importer).** The Schematic Editor actions table lists "Remote Symbols: Show/hide the remote symbol panel." The developer docs show a REMOTE_PROVIDER_METADATA class, a PANEL_REMOTE_SYMBOL wxPanel on the schematic frame, and a remote symbol import job/download manager. — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html), [PANEL_REMOTE_SYMBOL doxygen](https://docs.kicad.org/doxygen/classPANEL__REMOTE__SYMBOL.html)
  - Provider metadata (JSON, validated against `kicad-remote-provider-metadata-v1.schema.json`): required `provider_name`, `provider_version`, `api_base_url`, `max_download_bytes`, `supported_asset_types`, `auth` (none or oauth2), `capabilities`; optional `panel_url`, `session_bootstrap_url`, `documentation_url`, `terms_url`, `privacy_url`, `parts.endpoint_template`. Capability flags: `web_ui_v1` (must be true), `parts_v1`, `direct_downloads_v1`, `inline_payloads_v1` (at least one of the two download flags required). URLs must be HTTPS (HTTP only on loopback with `allow_insecure_localhost`). — [metadata source](https://docs.kicad.org/doxygen/remote__provider__metadata_8cpp_source.html)
  - User settings (REMOTE_PROVIDER_SETTINGS): list of providers (id, metadata URL, display name override, last account/auth status), `destination_dir`, `library_prefix`, `add_to_global_table`. — [settings source](https://docs.kicad.org/doxygen/remote__provider__settings_8h_source.html)
  - Import helpers write the payload to a configured destination root, ensure a library-table entry (global or project) exists, save the symbol into a nickname-keyed library, place it in the schematic, and apply footprint links (`ApplyFootprintLinks`). — [remote_symbol_import_utils.h](https://docs.kicad.org/doxygen/remote__symbol__import__utils_8h_source.html)
  - 10.0.2 changelog (section "Remote symbols and providers"): "Link downloaded symbols to their bundled footprints" and "Fix memory leak in remote symbol download on save failure"; 10.0.1 and 10.0.7 also have remote symbol library fixes (#23698 "Force library to loaded state after remote symbol import", #25530 "Create the remote symbol library before the first save"). — [10.0.2](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/), [10.0.1](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/), [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)
  - Third-party description: the ZiroEDA issue states KiCad 10.0.6 ships this as an open protocol "not a hosted KiCad service", the provider list is empty by default, and the user adds a metadata URL. It also raises the open question of whether SnapMagic/SamacSys/Ultra Librarian can serve parts given redistribution limits. — [ZiroEDA issue #656](https://github.com/ZiroEDA/ziro-designer/issues/656) (secondary source)
- Vendor side: SnapMagic (SnapEDA) documentation for KiCad v6+ describes importing the downloaded .kicad_sym via Manage Symbol Libraries, i.e. manual. — [SnapMagic support](https://support.snapmagic.com/en/articles/5612390-how-to-add-libraries-on-kicad-using-the-snapmagic-desktop-app) (from search snippet, not fetched in full)
- Third-party tools that fill the gap (not KiCad features): Steffen-W Import-LIB-KiCad-Plugin (Ultra Librarian and SnapEDA zips, supports drag and drop of zip files into its own text area), a KiCad forum thread on SnapEDA/UltraLibrarian automated import (a commenter raised licence concerns), robertxdx component-importer-for-kicad. — [Import-LIB-KiCad-Plugin](https://github.com/Steffen-W/Import-LIB-KiCad-Plugin), [forum thread](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000), [component-importer](https://github.com/robertxdx/component-importer-for-kicad)

### Inferences
- A part importer in this repo does not duplicate a KiCad 10 feature. The remote-provider mechanism is the only native "download symbol + footprint + 3D" flow, and it is provider-pull over HTTPS, not a local zip/loose-file ingest.
- Because remote-provider imports write into a configured destination dir with a configurable library prefix (and can add to global table), they could in principle point at `Custom/`, but the prefix/naming scheme is KiCad's, not the repo's `<Type>_<SubCategory>_<Manufacturer>` convention. This is an inference from the settings struct, not tested.
- Vendor zips (Ultra Librarian, SnapEDA, SamacSys) are plain KiCad-format files (.kicad_sym, .kicad_mod, .step); KiCad 10 will open them as libraries but will not rename, merge or relink them.

### Gaps
- No user-facing documentation page for the Remote Symbols panel found (manual only lists the action). Which `supported_asset_types` values exist (symbol/footprint/3D) and the default destination dir and prefix could not be confirmed.
- Whether the remote symbol feature was in 10.0.0 or added in a point release is not confirmed; the 10.0.0 announcement fetch did not mention it, and 10.0.1 changelog already contains fixes for it.
- The Footprint Editor File > Import menu contents in 10 were not found in the manual excerpts retrieved (searched pcbnew manual offsets 0-100k, 400-700k). Older forum evidence indicates Eagle .lbr footprint libraries can be added via Manage Footprint Libraries, but that is not KiCad 10-specific.
- No GitLab issue or roadmap item for "part importer / library from zip / drag and drop import" was found; GitLab search was not directly reachable, only via web search. Absence is not proof none exists.

## Library table handling in KiCad 10 (global vs project, adding libraries, UI changes, bugs in 10.0.x)

### Takeaway
Two-tier tables (global in the user config dir, project in the project dir, project wins on nickname conflicts) continue. Notable 10 additions: nested library tables (add a table file as a single entry via the Table type), "unpacked" folder-based symbol libraries (.kicad_symdir), design block library tables, and a start-up wizard that can upgrade existing library settings. The 10.0.x point releases fix many library-table bugs.

### Cited Findings
- Global table: `sym-lib-table` / `fp-lib-table` in the KiCad config folder; project table in the project folder; "Project tables take precedence when nicknames conflict" (symbol manual wording). — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html), [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)
- Access via Preferences > Manage Symbol Libraries / Manage Footprint Libraries; add with the folder button (file browser) or plus button (type path); for nested tables use the arrow next to the folder button, choose type **Table**, browse to the table file. — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html), [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
- "Library tables can also include other library tables, which are called nested library tables." Forum report: a user adding the official GitLab symbol repo was told that adding a table file is "a new feature in v10" (single-user claim, not official release-note text). — [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html), [forum thread](https://forum.kicad.info/t/kicad-v10-with-libraries-from-gitlab/70612)
- Unpacked symbol libraries (folders of .kicad_sym, conventionally .kicad_symdir) begin with KiCad 10.0. The library-utils project merged "Update symbol tooling to KiCad10 unpacked format". — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html), [kicad-library-utils MR !736](https://gitlab.com/kicad/libraries/kicad-library-utils/-/merge_requests/736) (title seen in search results only)
- Design block libraries have their own table (`design-block-lib-table`) and a Manage Design Block Libraries dialog that "behaves the same" as the symbol/footprint dialogs; design blocks extended to the PCB editor in 10. — [10.0.0 post](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/), [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Start-up wizard: choose built-in libraries, import tables from a previous version, or start empty; "Migrate built-in libraries to the latest version" recommended on upgrade. Preference "Automatically add installed libraries to global library table" controls PCM auto-add. — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)
- 10.0.1 fixes: library-table warning icon paths (#23359), reload child tables after editing, load hidden tables but hide children (#23634), upgrade user library settings in start-up wizard (#21263), reload libraries when environment variables change, speed up opening large tables, resolve env vars in nested tables (#23787), missing project-local footprint libs in standalone mode (#23872). — [10.0.1 release](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/)
- 10.0.2: improve handling of empty tables, visible dirty indicator on modified tables, pinned footprint libs disappearing after adding a library (#23717). — [10.0.2 release](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/)
- 10.0.5: persist design-block library visibility (#24588), crash migrating a nested table row (#23291), do not add stock libraries on migration if user had none (#24594), "Do not limit available substitution paths in library managers" (#23476). — [10.0.5 release](https://www.kicad.org/blog/2026/07/KiCad-10.0.5-Release/)
- 10.0.6: "Show a new project library without restarting" (#24872), "Show a warning for a library that could not be loaded" (#25166), "Reload footprint libraries that changed on disk", don't report unloaded rows as load errors (#22764). — [10.0.6 release](https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/)
- 10.0.7: guard multiple libraries referencing others during load (#25420), crash opening symbols on network drive (#25559), "Highlight library save failures" (#23850), "Keep the footprint when a rename only changes its case" (#25586), "Allow overwriting an existing file when creating a library" (10.0.5, #24617). — [10.0.7 release](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/), [10.0.5 release](https://www.kicad.org/blog/2026/07/KiCad-10.0.5-Release/)
- Database (.kicad_dbl, ODBC) and HTTP (.kicad_httplib, read-only REST, access-token auth) libraries exist as non-file-based symbol sources; recent fixes concern HTTP libs (background refresh, no contact with disabled rows). — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html), [10.0.6](https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/), [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)
- 10.0.1 bug relevant to a tool that writes library tables: "Fix false-positive library table warning", "Fix crash when creating symbol library on export" (#23756). — [10.0.1 release](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/)

### Inferences
- The repo's generated `sym-lib-table`/`fp-lib-table` approach is still valid in 10 (same file names/locations). KiCad 10 also lets a user add one table file as a nested entry, which is an alternative to writing every entry into the global table. That is an option, not verified against this repo's `${KICAD_LIB_GITHUB}` flow.
- The fix "Reload footprint libraries that changed on disk" (10.0.6) and "Show a new project library without restarting" suggest KiCad 10 now picks up externally written libraries better, but GUI restart is still advised by the manual after path changes.

### Gaps
- No official release-note line describing nested tables as new in 10 (only the manual text and one forum post). A single combined "Manage Libraries" dialog replacing the symbol/footprint dialogs was not found; web search found no evidence of it.
- "Add existing" phrase from the forum post does not appear in the 10.0 manual excerpts.

## 3D model path handling in KiCad 10

### Takeaway
Official libraries ship STEP only from 10; footprints reference models through path variables (`${KICAD10_3DMODEL_DIR}`, `${KIPRJMOD}`, user-defined variables like `CUSTOM_3DMODEL_DIR`). Old versioned variables auto-resolve to the 10 value. There is no native "relink/fix model path on import" feature for external vendor parts that I found; the 10.0.x notes include a 3D model migration dialog only for legacy WRL boards.

### Cited Findings
- "Starting with KiCad version 10 we are shipping STEP files only for 3D models" in the official libraries. — [10.0.0 post](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- Footprint model formats allowed: STEP, VRML, IDF. Models are specified as paths that "can contain path variables" (e.g. `${KIPRJMOD}`); Configure Paths button in the 3D Models tab; a warning icon shows when a model fails to load. — [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
- Built-in path variables in 10: `KICAD10_3DMODEL_DIR`, `KICAD10_FOOTPRINT_DIR`, `KICAD10_SYMBOL_DIR`, `KICAD10_TEMPLATE_DIR`, `KICAD10_3RD_PARTY` (PCM content), `KIPRJMOD` (always set, read-only). Environment variables set outside KiCad override Configure Paths and show read-only. — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)
- "KiCad will automatically resolve versioned path variables from older versions" to the KiCad 10 equivalents unless the old one is explicitly defined (e.g. `${KICAD9_FOOTPRINT_DIR}`). 10.0.6 adds "Resolve old version environment variables in configuration paths" (#23120). The PCB manual still uses `${KICAD9_3DMODEL_DIR}` in an example (stale text). — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html), [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html), [10.0.6](https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/)
- Embedding: 3D models can be embedded in a footprint via the "Embed File" option; embedded references start `kicad-embed://`, deduplicated when added to a board. (Manual statement; the version where embedding arrived was not verified here, it is believed to predate 10.) — [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
- 10.0.1 path fixes: "Fix resolution of ${ALIAS} variable for user aliases", "Prevent environment variable expander from corrupting unresolved paths", "Resolve environment variables in nested library tables" (#23787). 10.0.2: "Add 3D model migration dialog for legacy WRL boards" (#23804), crash typing an incomplete env var in 3D model path (#24002). 10.0.7: crash applying footprint properties after changing the 3D model path (#25239). — [10.0.1](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/), [10.0.2](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/), [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)
- Custom user path variables can be added via Preferences > Configure Paths (stored in KiCad user config), which matches the repo's `CUSTOM_3DMODEL_DIR` approach. — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)

### Inferences
- Setting `${CUSTOM_3DMODEL_DIR}/<file>.step` in a footprint's model entry is fully supported in 10. The importer must still rewrite the vendor's model path itself; KiCad provides no relink.
- Since 10 official libs are STEP-only, writing STEP (not WRL) references for custom parts is consistent with upstream direction.

### Gaps
- Behaviour of relative model paths (not variable-based) is not documented in the excerpts retrieved.
- Whether the Footprint Editor offers a bulk "fix 3D paths" tool in 10 was not found.

## Symbol-footprint linking, footprint assignment, name validation

### Takeaway
Linking is by the symbol's Footprint field (`Library:Footprint`), assigned via the footprint chooser or the Assign Footprints tool, and constrained by optional symbol footprint filters. 10 adds jumpers and pin/gate swap but no new link-validation feature; nickname/footprint-name rules are minimal (no colon).

### Cited Findings
- "The Footprint field defines which footprint will correspond to the symbol in the board design"; the chooser opens from the field; default footprint is previewed and alternates matching footprint filters can be chosen. — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Footprint filters: footprints matching any filter are shown, none defined shows all; wildcards `*` and `?`. — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Tools menu: "Assign Footprints..." (assignment tool) and "Import Footprint Assignments..." (from a .cmp file). — [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Identifier rules: a footprint is identified by library nickname plus footprint name; "The colon character (:) cannot be used in library nicknames or footprint names"; "Library nicknames do not have to be related to the library filename or path." — [PCB Editor manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
- New in 10: jumpers (group pins/pads as internally connected) and unconstrained pin/pad and gate/unit swap with forward/back annotation. — [10.0.0 post](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- Remote symbol downloads link bundled footprints to the symbol (10.0.2). ERC reports missing library tables entries ("The symbol library for a symbol is not included and enabled in the library table"). — [10.0.2](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/), [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- Assignment-tool fixes: "Correctly report missing footprints when updating from schematic" (#23924, 10.0.2), "Fix laggy and frozen input in the Assign Footprints tool" (#23991), "Don't duplicate footprints on update when replace is off" (#24960), "Prevent intermittent assignment of an unrelated/previous symbol footprint to symbols with no default footprint" (#25538, 10.0.7). — [10.0.2](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/), [10.0.5](https://www.kicad.org/blog/2026/07/KiCad-10.0.5-Release/), [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)
- 10.0.7: "Keep the footprint when a rename only changes its case" (#25586) - relevant to case-only renames on Windows file systems. — [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)

### Inferences
- KiCad does not enforce the repo's `<Type>_<SubCategory>_<Manufacturer>` pairing between .kicad_sym and .pretty; the importer must do that itself.
- Case-only renames of footprints were buggy until 10.0.7, so an importer should avoid relying on case-only rename operations through KiCad.

### Gaps
- No documented length/character restrictions on footprint names beyond the colon (KiCad also sanitizes illegal filename characters in some importers, per EasyEDA Pro fix in 10.0.1).

## Plugin and Content Manager (PCM) in KiCad 10

### Takeaway
PCM installs four package types: plugins, fabrication plugins, libraries (symbols/footprints/3D, nickname prefix `PCM_`), and color themes. "Install from file..." accepts a downloaded package zip but requires a PCM metadata file, so it is not a vendor-zip importer. No new library-specific PCM capability was found for 10, only bug fixes.

### Cited Findings
- Package categories and behaviour (Pending tab, Apply Pending Changes, default official repo, Manage... to add repositories, `KICAD10_3RD_PARTY` as install location, security warning, "Install from file..."). — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)
- Preference "Automatically add installed libraries to global library table" controls auto-registration of PCM libraries. — [Project Manager manual](https://docs.kicad.org/10.0/en/kicad/kicad.html)
- Forum evidence: zipping a personal library and using Install from file fails with "archive lacked a valid metadata file". — [forum thread](https://forum.kicad.info/t/how-to-make-a-personal-user-library-install-under-pcm/55589) (search snippet only)
- 10.0.x PCM changes are fixes: preserve execute bits when extracting (10.0.1), false-positive PCM cleanup with overlapping env vars (10.0.1), best-effort revoke policy by default on restricted networks (10.0.2), dialog selection issue and crash (10.0.6), validate archive file names before extraction (#25227, #25175) and keep install-from-file dialog open if plugin extraction fails (10.0.7), recreate Python virtualenvs when needed (#25528). — [10.0.1](https://www.kicad.org/blog/2026/04/KiCad-10.0.1-Release/), [10.0.2](https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/), [10.0.6](https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/), [10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)

### Inferences
- Packaging a vendor part as a PCM package would need a `metadata.json` and the PCM layout; that is heavier than writing straight into `Custom/` and not aligned with the repo's git-submodule model.
- The 10.0.7 archive-name validation shows KiCad treats zips as untrusted; an importer extracting vendor zips should validate member names (zip-slip) too.

### Gaps
- No 10.0.0 PCM "new feature" announcements found. The PCM schema/doc page on dev-docs.kicad.org was not fetched.

## Official roadmap, developer docs, GitLab/forum discussion on part importers

### Takeaway
I found no official roadmap item, GitLab issue or mailing list thread about a native vendor "part importer", "library from zip", or drag-and-drop part import in KiCad. The community answer is third-party plugins; the upstream answer is the remote symbol provider protocol.

### Cited Findings
- Remote provider developer docs exist for the protocol (metadata, panel, settings, import job). — [REMOTE_PROVIDER_METADATA doxygen](https://docs.kicad.org/doxygen/structREMOTE__PROVIDER__METADATA.html), [PANEL_REMOTE_SYMBOL](https://docs.kicad.org/doxygen/classPANEL__REMOTE__SYMBOL.html)
- Forum thread on SnapEDA/UltraLibrarian automated import: an individual forked an old GitHub project; a commenter noted the vendor files have a restrictive licence. — [forum thread](https://forum.kicad.info/t/snapeda-ultralibrarian-automated-import/36000)
- Ultra Librarian's own KiCad help describes manual steps (add .kicad_sym and .pretty folder to library tables). — [Ultra Librarian KiCad help](https://app.ultralibrarian.com/content/help/kicad.htm) (search result only)
- The only drag-and-drop mentioned in the 10.0.0 post is "image support" (unspecified). — [10.0.0 post](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- Secondary reviews: [Elektor](https://www.elektormagazine.com/news/kicad-10-release), [electwork](https://electwork.net/en/posts/kicad-10-new-features/) (not fetched in full; only appeared in results).

### Inferences
- The upstream project is unlikely to add a local vendor-zip importer soon given licence/redistribution issues around SnapEDA, SamacSys and Ultra Librarian files and the protocol-based direction.

### Gaps
- GitLab (gitlab.com/kicad/code/kicad) issue search and the devel mailing list could not be queried directly with the tools available; only web search was used. A direct GitLab search for "import zip", "SnapEDA" and "remote symbol" is recommended before relying on "no upstream plan".
- The roadmap page (kicad.org/discover/roadmap or dev-docs) was not fetched.
