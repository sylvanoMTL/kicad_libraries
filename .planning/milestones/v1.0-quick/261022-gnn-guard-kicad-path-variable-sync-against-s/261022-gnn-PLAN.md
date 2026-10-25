---
phase: quick-261022-gnn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/help_dialog.py
  - tests/test_kicad_config.py
  - tests/test_main_window.py
  - tests/test_main_window_import.py
  - .planning/PROJECT.md
  - .planning/STATE.md
autonomous: true
requirements: [HARD-03]

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "If KICAD_LIB_GITHUB or CUSTOM_3DMODEL_DIR would change (different value, unset or empty), Generate first shows a Yes/No question that lists each change as 'VAR: old -> new'. An old value of None or empty shows as '(not set)', and the default button is No."
    - "Answering No leaves kicad_common.json byte-identical and creates no backup, and the library tables are still written. The log shows the INFO 'KiCad path variables left unchanged'."
    - "When both variables already hold the desired values, no question is shown, nothing is backed up and nothing is written (INFO config.var_ok only)."
    - "When the app runs from a git worktree (repo_root/.git is a file), it never asks and never writes. A WARNING config.worktree_refused names the worktree path and the configured KICAD_LIB_GITHUB."
    - "When the app runs from a checkout other than a non-empty configured KICAD_LIB_GITHUB, it never asks and never writes. Paths are compared after slash, trailing-slash, normpath and normcase normalisation. A WARNING config.other_checkout_refused names both paths and points to KiCad Preferences > Configure Paths."
    - "Calling sync_kicad_path_vars without a confirm callback writes nothing (WARNING config.confirm_required), so the safe default never writes."
    - "The post-install new-library branch and Generate use the same MainWindow helper, so both ask the same question."
    - "On Yes, the existing verify, backup, atomic write, KiCad-running warning and backup pruning run unchanged, and every existing test in tests/test_kicad_config.py still passes."
    - "PROJECT.md Key Decisions and STATE.md Decisions record that KiCad path variables are never written silently."
  artifacts:
    - path: "kicad_lib_manager/library_scanner.py"
      provides: "sync_kicad_path_vars with the confirm kwarg, worktree and other-checkout refusals, and path normalisation helpers"
      contains: "config.worktree_refused"
    - path: "kicad_lib_manager/main_window.py"
      provides: "_sync_path_vars helper and _confirm_path_var_changes QMessageBox.question callback, used by both callers"
      contains: "_sync_path_vars"
    - path: "tests/test_kicad_config.py"
      provides: "unchanged/declined/no-confirm/worktree/other-checkout/normalisation tests"
      contains: "config.other_checkout_refused"
    - path: "tests/test_main_window.py"
      provides: "Generate Yes/No/worktree GUI tests with patched QMessageBox.question"
      contains: "StandardButton.No"
    - path: "tests/test_main_window_import.py"
      provides: "post-install new-library confirm (Yes) and decline (No) tests"
      contains: "left unchanged"
    - path: ".planning/PROJECT.md"
      provides: "Key Decisions row"
      contains: "never written silently"
    - path: ".planning/STATE.md"
      provides: "Decisions bullet"
      contains: "[Quick 261022-gnn]"
  key_links:
    - from: "kicad_lib_manager/main_window.py MainWindow._on_generate"
      to: "kicad_lib_manager/library_scanner.py sync_kicad_path_vars"
      via: "self._sync_path_vars() passing confirm=self._confirm_path_var_changes"
      pattern: "self\\._sync_path_vars\\(\\)"
    - from: "kicad_lib_manager/main_window.py MainWindow._finish_post_install (new_library branch)"
      to: "kicad_lib_manager/library_scanner.py sync_kicad_path_vars"
      via: "the same self._sync_path_vars() helper"
      pattern: "self\\._sync_path_vars\\(\\)"
    - from: "sync_kicad_path_vars refusal/decline branches"
      to: "fsutil.backup_file / fsutil.atomic_write_text"
      via: "every refusal or decline returns before the backup and the write"
      pattern: "confirm\\(changes\\)"
---

<objective>
Stop the KiCad Library Manager from changing KiCad's global path variables (KICAD_LIB_GITHUB, CUSTOM_3DMODEL_DIR in the newest kicad_common.json) without asking. Also refuse the change outright when the app runs from a git worktree or from a checkout other than the configured KICAD_LIB_GITHUB.

Purpose: on 2026-10-21 the owner pressed Generate from the dev worktree C:/Git_Repo_Clones/Kicad_Libraries-importer. `sync_kicad_path_vars` silently repointed KiCad 10 at that worktree, so 89 WurthElektronik footprint libraries went missing and an ERC error appeared (IC_Battery_Management_TI absent from that Custom commit). Generate and the post-install new-library branch both call the sync without asking. This plan adds a confirm step, a worktree guard and a configured-checkout guard. The library tables are still written either way.

Output: guarded `sync_kicad_path_vars` (still Qt-free), one MainWindow helper used by both callers, scanner and GUI tests, a help-page bullet, and the decision recorded in PROJECT.md and STATE.md.

Extends HARD-03 (kicad_common.json backed up and written atomically, only environment.vars changed). That guarantee is kept unchanged; this plan adds "never silently, never from the wrong checkout".
</objective>

<execution_context>
@C:/Git_Repo_Clones/Kicad_Libraries-importer/.claude/gsd-core/workflows/execute-plan.md
@C:/Git_Repo_Clones/Kicad_Libraries-importer/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@kicad_lib_manager/library_scanner.py
@tests/test_kicad_config.py

HARD SAFETY RULES (apply to every task, executor and tests alike):
- Never write to the real library checkout C:/Git_Repo_Clones/Kicad_Libraries or to KiCad's real config under %APPDATA%/kicad. Do not open, back up, or edit the real kicad_common.json. The owner is restoring it by hand.
- Every sync call in tests goes through tmp_path with config_base, backup_root and running overrides. Never call sync_kicad_path_vars, MainWindow._on_generate or MainWindow._finish_post_install without the make_window fake or those overrides. Never launch the GUI (kicad_lib_manager.py) to check this change, because a real run would talk to the real config.
- Do not edit kicad_lib_manager/widgets/import_dialog.py, kicad_lib_manager/importer/form.py, tests/test_import_form.py or tests/test_import_dialog.py. A phase 5 executor (plan 05-09) is changing them in a separate worktree.
- Known baseline failures to ignore (KiCad 10 kicad-cli writes 20251024): tests/test_install_plan.py::test_version_real_cli_into_20241209, ::test_library_real_cli_new_header, ::test_noop_second_plan_after_normalised_apply; tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically; tests/test_install_e2e.py::test_cli_version_scenarios (both params), ::test_cli_second_install_is_noop. Planning-time baseline with those deselected: 1526 passed, 5 skipped.

<interfaces>
Current signature (kicad_lib_manager/library_scanner.py, line 113):

    def sync_kicad_path_vars(
        repo_root: Path,
        *,
        config_base: Path | None = None,
        backup_root: Path | None = None,
        running: Callable[[], list[str]] | None = None,
    ) -> list[Issue]:

Target signature (adds one keyword, everything else unchanged):

    def sync_kicad_path_vars(
        repo_root: Path,
        *,
        config_base: Path | None = None,
        backup_root: Path | None = None,
        running: Callable[[], list[str]] | None = None,
        confirm: Callable[[list[tuple[str, str | None, str]]], bool] | None = None,
    ) -> list[Issue]:

Current function flow (lines 125-238): find config dir -> config.dir_not_found WARNING | config file exists -> config.not_found WARNING | fsutil.read_source -> Issue | json.loads -> config.bad_json ERROR | shape check -> config.bad_shape ERROR | build `desired` from repo_str (forward slashes) | loop desired: equal -> INFO config.var_ok into `issues`, else SUCCESS config.var_set into `set_issues` | `if not set_issues: return issues` | build new_text and _only_vars_changed verify -> config.verify_failed ERROR | normalize_eol | running() -> WARNING config.kicad_running | fsutil.backup_file -> INFO config.backed_up | fsutil.atomic_write_text | extend set_issues + SUCCESS config.written | _prune_backups.

Callers in kicad_lib_manager/main_window.py (the only two):
- line 619, inside `_finish_post_install`, `if pending.new_library:` branch after add_library_entries: `self._log_issues(sync_kicad_path_vars(REPO_ROOT))` with the comment "Same rule as Generate: the path variables follow every table write"
- line 766, inside `_on_generate`, after write_tables: `self._log_issues(sync_kicad_path_vars(REPO_ROOT))` with the comment "Sync KiCad path variables, independent of how the table writes went"
- `REPO_ROOT = Path(__file__).parent.parent.resolve()` (line 31); tests monkeypatch it to tmp_path / "repo".
- QMessageBox is already imported (line 6); today it is used only by `_on_about` (line 834).
- `_log_issues(issues)` routes each Issue by Severity through `self._log.log_issue`.

Test fixtures to update (identical shape in both GUI test modules):
- tests/test_main_window.py `make_window` fixture, lines 35-81: `def fake_sync(repo_root):` (line 58) calls library_scanner.sync_kicad_path_vars(repo_root, config_base=config_base, backup_root=tmp_path / "backups", running=lambda: []) and is monkeypatched onto main_window.sync_kicad_path_vars. make.config_file is tmp_path/kicad_cfg/10.0/kicad_common.json holding {"environment": {"vars": null}}. Fixture-level attributes: make.calls, make.repo.
- tests/test_main_window_import.py `make_window` fixture, lines 48-92: same fake_sync at line 69.
- Existing tests that need the default Yes answer: tests/test_main_window.py::test_generate_with_read_only_sym_table_logs_one_error_and_finishes (asserts the config is written and "Updated" is logged) and tests/test_main_window_import.py::test_tables_new_library_add_only (line 318, asserts the config text changed).
- tests/test_main_window_import.py helpers available: stub_plan(repo, NEW_LIB, new_library=True), install_result(), scan_with(...), usb_tables(repo), _managed(...), log_text(w), NEW_LIB = "IC_New_TI".
- tests/test_kicad_config.py helpers: fixtures repo (tmp_path/"my repo"), cfg, backups; _desired(repo), _dump, _write_config(base, version, obj), _sync(repo, cfg, backups, running=...), _codes, _by_code, _null_vars_config(), _backup_dir, _assert_untouched(path, before, backups).
</interfaces>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer - confirm before any path-variable write, end to end from Generate to kicad_common.json</name>
  <files>kicad_lib_manager/library_scanner.py, kicad_lib_manager/main_window.py, tests/test_kicad_config.py, tests/test_main_window.py, tests/test_main_window_import.py</files>
  <read_first>
    - kicad_lib_manager/library_scanner.py lines 72-238 (sync_kicad_path_vars and helpers)
    - kicad_lib_manager/main_window.py lines 594-640 (_finish_post_install) and 734-775 (_log_issues, _on_generate)
    - tests/test_kicad_config.py lines 93-216 (fixtures, _sync helper, already-correct test)
    - tests/test_main_window.py lines 1-81 and 205-243
    - tests/test_main_window_import.py lines 1-92 and 318-361
  </read_first>
  <behavior>
    - Scanner, confirm returns False: kicad_common.json bytes unchanged, no backups/kicad_common folder, an INFO config.declined whose text starts "KiCad path variables left unchanged", and no config.var_set or config.written.
    - Scanner, values already correct: a confirm callback that records calls is never called, codes are exactly ["config.var_ok", "config.var_ok"], and there is no backup and no write.
    - Scanner, null vars: confirm receives [("KICAD_LIB_GITHUB", None, repo_str), ("CUSTOM_3DMODEL_DIR", None, repo_str + "/Custom/3DModels")]. With KICAD_LIB_GITHUB already equal to repo_str and CUSTOM_3DMODEL_DIR missing, it receives only the CUSTOM_3DMODEL_DIR tuple.
    - Scanner, confirm=None passed explicitly with a changing value: a WARNING config.confirm_required, and the file and backups are untouched.
    - All existing tests in tests/test_kicad_config.py pass unchanged once _sync defaults to a confirm that returns True. This covers the existing backup and atomic-write path.
    - GUI, Generate with the patched QMessageBox.question answering No: the tables are written, config bytes are unchanged, tmp_path/"backups" does not exist, and the log contains "KiCad path variables left unchanged".
    - GUI, Generate answering Yes: question is called exactly once. args[0] is the window, args[2] contains "KICAD_LIB_GITHUB: (not set) -> {repo_str}" and "CUSTOM_3DMODEL_DIR: (not set) -> {repo_str}/Custom/3DModels", and args[4] is QMessageBox.StandardButton.No (the default button). The config is written.
  </behavior>
  <action>
Obey the HARD SAFETY RULES in the context block: tmp_path only, never the real kicad_common.json, never launch the GUI, and do not touch the four phase-5 files.

library_scanner.py (stays Qt-free; Issue codes are stable strings; issues stay list[Issue] routed by Severity):
1. Add the keyword `confirm: Callable[[list[tuple[str, str | None, str]]], bool] | None = None` after `running`, as shown in the interfaces block (owner requirement 1). Update the docstring. It should say that nothing is written unless the values would change and confirm(changes) returns True, that changes lists only the variables that would change as (variable, old value or None, new value), and that a missing confirm writes nothing.
2. In the existing desired loop, also build `changes`. For every key whose old value differs from the desired value (including unset or empty), append (key, old_vars.get(key), value), keeping today's config.var_set SUCCESS issues in set_issues for the post-write log. The early return `if not set_issues: return issues` stays first, so unchanged values never prompt and never back up.
3. After that early return, add two decision branches in this order. Each returns `issues` (the config.var_ok INFOs gathered so far) plus exactly one new Issue. None of them reaches fsutil.backup_file or fsutil.atomic_write_text. (Task 2 inserts the worktree and other-checkout refusals in front of these two branches.)
   a. confirm is None -> Issue(Severity.WARNING, "config.confirm_required", "Not changing KiCad path variables: no confirmation step was provided"). This is the safe default.
   b. not confirm(changes) -> Issue(Severity.INFO, "config.declined", "KiCad path variables left unchanged"). Optionally append " (change declined)", but the text must start with "KiCad path variables left unchanged".
   Otherwise fall through to the existing new_config / _only_vars_changed verify / normalize_eol / running() warning / backup / atomic write / set_issues / config.written / prune path, byte-for-byte unchanged. The KiCad-running warning only fires when a write follows, which is already true because it sits after the branches.

main_window.py (per owner requirement 1; one helper used by BOTH callers):
4. Add `_confirm_path_var_changes(self, changes) -> bool`. It builds one line per change as "VAR: old -> new", using an ASCII arrow, and shows "(not set)" when old is None or an empty string. It calls QMessageBox.question with positional arguments in exactly this order: self as parent, the title "Change KiCad path variables?", the text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, and QMessageBox.StandardButton.No as the default button. It returns True only when the answer equals QMessageBox.StandardButton.Yes. The text starts with "These KiCad path variables in kicad_common.json would change:", then a blank line and the change lines, then a blank line and "KiCad loads its libraries from these paths after a restart. Change them?". Add a one-line comment above the helper noting that this is an intentional exception to the convention that QMessageBox is used only for About, because the owner requires an explicit confirmation before KiCad's global settings change (PROJECT.md Safety constraint: no write without a preview first).
5. Add `_sync_path_vars(self)` with a one-line docstring. It calls `self._log_issues(sync_kicad_path_vars(REPO_ROOT, confirm=self._confirm_path_var_changes))` and reads the module-level REPO_ROOT at call time so the test monkeypatch keeps working. Replace BOTH existing direct calls (in _on_generate after write_tables, and in the _finish_post_install new_library branch after add_library_entries) with `self._sync_path_vars()`. Update their comments: Generate's comment says the path variables are offered for change, never written silently, independent of how the table writes went; the post-install comment says "Same rule as Generate". Table writes stay independent of the sync outcome: write_tables and add_library_entries keep running before the sync, whatever the answer.

Tests:
6. tests/test_kicad_config.py: change `_sync` to accept `confirm=lambda changes: True` as a keyword default and forward it. Add test_declined_change_writes_nothing_and_makes_no_backup, test_unchanged_values_never_ask (the recording confirm must stay uncalled), test_confirm_gets_only_the_changing_variables (both cases from the behavior block) and test_missing_confirm_writes_nothing (call library_scanner.sync_kicad_path_vars directly with config_base=cfg, backup_root=backups, running=lambda: [] and confirm=None). Use _assert_untouched for the no-write and no-backup checks.
7. tests/test_main_window.py and tests/test_main_window_import.py `make_window` fixtures:
   - Change fake_sync to `fake_sync(repo_root, **kwargs)`. It forwards **kwargs and keeps the explicit config_base=config_base, backup_root=tmp_path / "backups" and running=lambda: [] overrides. If a future caller passes one of those overrides itself, the duplicate keyword raises TypeError and the test fails loudly instead of reaching the real config.
   - Import QMessageBox from the Qt widgets module. At fixture level, outside make() so a test can override it before or after creating the window, set make.answer = QMessageBox.StandardButton.Yes and make.questions = []. Monkeypatch main_window.QMessageBox's "question" attribute with a fake that appends its positional args tuple to make.questions and returns make.answer, read at call time. Patching at fixture level guarantees no test can block on a real modal dialog offscreen.
8. tests/test_main_window.py: add test_generate_declined_leaves_kicad_config_untouched (set make_window.answer to No, generate with _new_lib_scan(), capture config bytes before, and assert the behavior-block expectations) and test_generate_confirmed_shows_old_and_new_values (Yes, with the args assertions from the behavior block, using repo_str = str(make_window.repo).replace("\\", "/")). In tests/test_main_window_import.py::test_tables_new_library_add_only, add `assert len(make_window.questions) == 1` to prove the post-install path asks through the same helper.
  </action>
  <verify>
    <automated>./env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py tests/test_main_window_import.py -q</automated>
    <automated>grep -c "self._sync_path_vars()" kicad_lib_manager/main_window.py   # prints 2</automated>
    <automated>grep -c "sync_kicad_path_vars(" kicad_lib_manager/main_window.py   # prints 1 (only inside _sync_path_vars)</automated>
    <automated>grep -v '^\s*#' kicad_lib_manager/library_scanner.py | grep -c "PySide6"   # prints 0</automated>
  </verify>
  <done>Generate and the post-install new-library branch both ask through _confirm_path_var_changes before any kicad_common.json change. Answering No (or passing no confirm) leaves the file byte-identical with no backup. Unchanged values never ask. The three test modules pass, including every pre-existing test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Refuse from a git worktree or from a checkout other than the configured KICAD_LIB_GITHUB</name>
  <files>kicad_lib_manager/library_scanner.py, tests/test_kicad_config.py, tests/test_main_window.py, tests/test_main_window_import.py</files>
  <read_first>
    - kicad_lib_manager/library_scanner.py sync_kicad_path_vars as left by Task 1
    - tests/test_kicad_config.py tests added in Task 1
  </read_first>
  <behavior>
    - Scanner, repo/.git written as a file ("gitdir: elsewhere\n") and KICAD_LIB_GITHUB set to another tmp path: a single WARNING config.worktree_refused whose text contains repo_str and the configured value. The recording confirm is never called, and _assert_untouched holds.
    - Same, with vars null (KICAD_LIB_GITHUB unset): still config.worktree_refused, with "(not set)" in the text, no prompt and no write.
    - Scanner, no .git and KICAD_LIB_GITHUB set to a different tmp path: a single WARNING config.other_checkout_refused whose text contains both paths and "Configure Paths". Confirm is never called, and the file and backups are untouched.
    - Scanner, KICAD_LIB_GITHUB set to the same checkout spelled differently, with CUSTOM_3DMODEL_DIR unset: no refusal, confirm called once, file written. Parametrize the spellings as str(repo) with all separators as backslashes, repo_str + "/", and str(repo) + "\\". Add one Windows-only case (pytest.mark.skipif(sys.platform != "win32")) with repo_str.upper().
    - Scanner, KICAD_LIB_GITHUB is "" (empty): not "configured", so confirm is called with old "", and the file is written on True.
    - Scanner, repo/.git as a directory (normal checkout) with vars null: confirm is called and the file is written.
    - GUI, Generate after writing make_window.repo/".git" as a file: make_window.questions stays empty, config bytes are unchanged, tmp_path/"backups" does not exist, both tables are still written, and the log contains "git worktree" in the warning colour (COLORS["warning"]).
    - GUI, post-install new library with make_window.answer = No: the sym and fp table lines for IC_New_TI are still added, config bytes are unchanged, there is exactly one question, and the log contains "KiCad path variables left unchanged".
  </behavior>
  <action>
Obey the HARD SAFETY RULES in the context block. The worktree tests create `.git` only inside tmp_path; never inspect or modify this checkout's own `.git`.

library_scanner.py (owner requirement 2; stays Qt-free):
1. Add the private helper `_norm_path(text: str) -> str`. It strips surrounding whitespace, replaces backslashes with forward slashes, then applies os.path.normpath and then os.path.normcase. The result ignores slash direction and a trailing separator on every platform, and ignores case on Windows. It is pure string work: no resolve(), and no filesystem access to the configured path, which may not exist.
2. Add the private helper `_path_var_refusal(repo_root: Path, repo_str: str, old_vars: dict) -> Issue | None`:
   - If (repo_root / ".git").is_file(), it is a git worktree. Return Issue(Severity.WARNING, "config.worktree_refused", ...) with the text: "Not changing KiCad path variables: this app runs from a git worktree ({repo_str}). KICAD_LIB_GITHUB stays {configured or '(not set)'}. Run the app from the library checkout to update them." A `.git` directory is a normal checkout and is not refused.
   - Otherwise, let configured = old_vars.get("KICAD_LIB_GITHUB"). It counts as configured only when it is a str that is non-empty after strip; an unset or empty value falls through to the confirmation path, per the owner. When it is configured and _norm_path(configured) != _norm_path(repo_str), return Issue(Severity.WARNING, "config.other_checkout_refused", ...) with the text: "Not changing KiCad path variables: KICAD_LIB_GITHUB is set to {configured}, but this app runs from {repo_str}. Run the app from {configured}, or change KICAD_LIB_GITHUB in KiCad Preferences > Configure Paths if you meant to switch checkouts."
   - Otherwise, return None.
3. In sync_kicad_path_vars, call it immediately after the `if not set_issues: return issues` early return and before the confirm-is-None and confirm(changes) branches from Task 1. If it returns an Issue, return issues + [that issue]: no prompt, no backup, no write. The final order is: read/parse/shape checks, compute changes, nothing changes (var_ok INFOs, return), worktree refusal, other-checkout refusal, confirm_required, declined, then the unchanged verify/backup/atomic-write path. A KICAD_LIB_GITHUB that normalises equal but is spelled differently still counts as a change (the exact string differs), so it goes through confirm and is rewritten in forward-slash form on Yes.

Tests (tdd: write them first and watch the refusal ones fail, then implement):
4. tests/test_kicad_config.py: add test_worktree_refuses_without_asking_or_writing (parametrized over a configured other path and null vars), test_other_checkout_refuses_without_asking_or_writing, test_same_checkout_in_another_spelling_is_not_refused (parametrized, plus the Windows-only upper-case case; import sys for the skipif), test_empty_configured_value_asks_for_confirmation and test_git_directory_is_not_a_worktree, as specified in the behavior block. Use a recording confirm (a list plus a callable returning True) to assert the call count. For "another checkout", use str(tmp_path / "main checkout") with forward slashes. Never use the real C:/Git_Repo_Clones/Kicad_Libraries path as a test value.
5. tests/test_main_window.py: add test_generate_from_worktree_refuses_without_asking. Create the window with _new_lib_scan(), write make_window.repo / ".git" as a file, capture the config bytes, call w._on_generate(), and assert the behavior-block expectations. Find the warning line in w._log._text.toHtml() as test_generate_without_kicad_config_warns_and_still_writes_both_tables does.
6. tests/test_main_window_import.py: add test_tables_new_library_declined_keeps_kicad_config. Mirror test_tables_new_library_add_only (usb_tables, scan_with(with_installed=False, with_ffc=True) then scan_with(lib=NEW_LIB, with_ffc=True), w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_library=True)), qtbot.waitUntil(lambda: w._worker is None, timeout=5000)), set make_window.answer to No before the install, and assert the behavior-block expectations.
  </action>
  <verify>
    <automated>./env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py tests/test_main_window_import.py -q</automated>
    <automated>grep -c "config.worktree_refused\|config.other_checkout_refused" kicad_lib_manager/library_scanner.py   # prints 2 or more</automated>
    <automated>grep -c "config.worktree_refused\|config.other_checkout_refused" tests/test_kicad_config.py   # prints 2 or more</automated>
  </verify>
  <done>A worktree run and a run from a checkout other than the configured KICAD_LIB_GITHUB both log a WARNING naming both paths, and never prompt, back up or write. The same checkout spelled with other slashes, a trailing separator or (on Windows) other case is not refused. An unset or empty KICAD_LIB_GITHUB goes through confirmation. The GUI worktree test and the post-install decline test pass.</done>
</task>

<task type="auto">
  <name>Task 3: Help text, decision records, and full-suite regression</name>
  <files>kicad_lib_manager/widgets/help_dialog.py, .planning/PROJECT.md, .planning/STATE.md</files>
  <read_first>
    - kicad_lib_manager/widgets/help_dialog.py lines 186-202 (HELP_PAGES["generating"])
    - .planning/PROJECT.md lines 105-130 (Key Decisions table)
    - .planning/STATE.md lines 72-101 (### Decisions list)
  </read_first>
  <action>
Obey the HARD SAFETY RULES in the context block.

1. kicad_lib_manager/widgets/help_dialog.py. At planning time no help text claims that Generate sets the KiCad path variables automatically, so there is nothing to correct. Instead, add one `<li>` to the "What happens" list in HELP_PAGES["generating"], after the backup-number bullet, in the same string-concatenation style. It should say, using `<code>` for the variable names: if KICAD_LIB_GITHUB or CUSTOM_3DMODEL_DIR in KiCad's settings needs to change, the app first shows the old and new values and asks; answering No leaves KiCad's settings unchanged while the tables are still written; and when the app runs from a git worktree, or from a checkout other than the one KICAD_LIB_GITHUB points at, it never changes them and the log says why. Do not touch any other help page.
2. .planning/PROJECT.md Key Decisions table (owner requirement 4). Use Edit (scoped) to append one row after the last row (the kicad-cli row):
   - Decision: "KiCad path variables are never written silently: Generate and the post-install table update show `VAR: old -> new` and ask (default No); a git worktree or a checkout other than the configured `KICAD_LIB_GITHUB` is refused with a WARNING; no confirm callback means no write"
   - Rationale: "2026-10-21: Generate from the dev worktree repointed KiCad 10 at it; 89 WurthElektronik libraries went missing and an ERC error followed"
   - Outcome: "✓ Good (Quick 261022-gnn)"
   Leave the existing "A running KiCad only warns" row as it is; it still holds after a confirmed change.
3. .planning/STATE.md, "### Decisions" list (owner requirement 4). Use Edit (scoped) to append one bullet after the last existing bullet (the "[Phase 04]: 04-11..04-13 (gap closure)" one): "- [Quick 261022-gnn]: KiCad path variables are never written silently: `sync_kicad_path_vars` writes only after `confirm(changes)` returns True (no callback = no write); a git worktree (`.git` is a file) or a checkout other than a non-empty configured `KICAD_LIB_GITHUB` (normalised compare) is refused with a WARNING and never prompts. Later phases must not add a silent caller." Do not use Write on either planning file.
4. Run the full suite with the known kicad-cli baseline failures deselected (command below) and confirm it matches the planning-time baseline (1526 passed, 5 skipped) plus the new tests, with 0 failures. Before committing, confirm the four phase-5 files are not modified (second command prints nothing).
  </action>
  <verify>
    <automated>./env/Scripts/python.exe -m pytest -q --deselect tests/test_install_plan.py::test_version_real_cli_into_20241209 --deselect tests/test_install_plan.py::test_library_real_cli_new_header --deselect tests/test_install_plan.py::test_noop_second_plan_after_normalised_apply --deselect tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically --deselect tests/test_install_e2e.py::test_cli_version_scenarios --deselect tests/test_install_e2e.py::test_cli_second_install_is_noop</automated>
    <automated>git status --porcelain -- kicad_lib_manager/widgets/import_dialog.py kicad_lib_manager/importer/form.py tests/test_import_form.py tests/test_import_dialog.py   # prints nothing</automated>
    <automated>grep -c "Quick 261022-gnn" .planning/PROJECT.md .planning/STATE.md   # each prints 1</automated>
    <automated>./env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q</automated>
  </verify>
  <done>The Generating Tables help page describes the confirmation and the worktree/other-checkout refusal. PROJECT.md has the Key Decisions row and STATE.md has the [Quick 261022-gnn] bullet. The full suite passes with only the known kicad-cli baseline deselected, and the four phase-5 files are untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| App process -> KiCad global config (%APPDATA%/kicad/<ver>/kicad_common.json) | A write here changes which libraries every KiCad project loads; it is outside the repo and shared by all checkouts |
| kicad_common.json values -> confirmation dialog text | Values read from disk are shown to the user verbatim |
| Test process -> owner's machine | Tests run on the owner's workstation where the real KiCad config and the real library checkout live |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261022-gnn-01 | Tampering | library_scanner.sync_kicad_path_vars called from Generate / _finish_post_install | high | mitigate | Writes only after confirm(changes) returns True; confirm=None returns config.confirm_required with no write; MainWindow._confirm_path_var_changes defaults to No (Task 1) |
| T-261022-gnn-02 | Tampering | sync_kicad_path_vars run from a git worktree or a different checkout | high | mitigate | _path_var_refusal returns config.worktree_refused / config.other_checkout_refused before any prompt, backup or write; normalised path compare via _norm_path (Task 2) |
| T-261022-gnn-03 | Tampering | Test suite / executor on the owner's machine | high | mitigate | Every sync call goes through tmp_path config_base/backup_root/running; fake_sync keeps explicit overrides so a duplicate keyword fails loudly; QMessageBox.question patched at fixture level so no real modal; GUI never launched (HARD SAFETY RULES) |
| T-261022-gnn-04 | Denial of Service | Refusal/decline branches | medium | mitigate | Branches return before fsutil.backup_file and fsutil.atomic_write_text; tests assert byte-identical file and no backups/kicad_common folder |
| T-261022-gnn-05 | Repudiation | User cannot tell why variables did not change | low | mitigate | WARNING texts name the running path and the configured KICAD_LIB_GITHUB and give the fix (run from the checkout or change it in Preferences > Configure Paths) |
| T-261022-gnn-06 | Spoofing | Config values rendered in QMessageBox (Qt auto-detects rich text) | low | accept | Values come from the owner's own KiCad config on a personal tool; worst case is odd formatting in a dialog that defaults to No |
| T-261022-gnn-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs in this plan (stdlib + existing PySide6 only) |
</threat_model>

<verification>
- `./env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py tests/test_main_window_import.py tests/test_help_dialog.py -q` passes.
- The full suite passes with the known kicad-cli baseline deselected (Task 3 command).
- `grep -c "self._sync_path_vars()" kicad_lib_manager/main_window.py` prints 2 and `grep -c "sync_kicad_path_vars(" kicad_lib_manager/main_window.py` prints 1.
- library_scanner.py has no Qt import (Task 1 gate).
- The four phase-5 files are unmodified.
- No test, and no executor step, touched %APPDATA%/kicad or C:/Git_Repo_Clones/Kicad_Libraries.
</verification>

<success_criteria>
- Owner requirement 1: a value that would change is shown as old -> new and needs a Yes. No leaves kicad_common.json unchanged while the tables are still generated.
- Owner requirement 2: a git worktree, or a checkout other than a non-empty configured KICAD_LIB_GITHUB (normalised compare), is refused with a WARNING naming both paths, with no prompt and no write. An unset or empty value goes through confirmation.
- Owner requirement 3: the unchanged, declined, worktree, other-checkout and confirmed backup/atomic-write cases are each covered by a passing test, at scanner level and through the GUI for both callers.
- Owner requirement 4: the decision is recorded in the PROJECT.md Key Decisions table and the STATE.md Decisions list.
</success_criteria>

<output>
Create `.planning/quick/261022-gnn-guard-kicad-path-variable-sync-against-s/261022-gnn-SUMMARY.md` when done
</output>
