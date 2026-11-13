---
status: diagnosed
trigger: "G-13-1-a: import kicad_lib_manager.main_window fails on Python 3.11 with NameError: name 'CommitPlan' is not defined (migration_dialog.py line 338, _CommitStepHost.start)"
created: 2026-11-12T17:45:06Z
updated: 2026-11-12T18:20:00Z
gap_id: G-13-1-a
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED. migration_dialog.py names CommitPlan (line 338) and CommitProbe (line 373) in def-signature annotations of _CommitStepHost without importing either. Python 3.10-3.13 evaluate parameter annotations when the class body runs, so importing the module raises NameError. 3.14 defers annotation evaluation (PEP 649/749), so the only interpreter the project uses never evaluates them.
bug_class: Bohrbug (deterministic, interpreter-version dependent)
test: done. AST scan, 3.11 stubbed import of every module, and a 3.14 annotation-evaluation sweep all agree.
expecting: n/a
next_action: none (goal find_root_cause_only). Hand the diagnosis to the caller for a gap-closure plan.

reasoning_checkpoint:
  hypothesis: "Importing kicad_lib_manager.widgets.migration_dialog on Python <3.14 raises NameError because _CommitStepHost.start (l.338) annotates `plan: CommitPlan` and _CommitStepHost._on_probe_done (l.373) annotates `probe: CommitProbe`. Neither name is bound in the module, and pre-3.14 interpreters evaluate parameter annotations at def time."
  confirming_evidence:
    - "Python 3.11.3 with a PySide6 stub reproduces the user's exact traceback (migration_dialog.py:338, NameError CommitPlan). No other module of 78 fails."
    - "Scratch copy with only the CommitPlan import added: the next failure is NameError CommitProbe at _on_probe_done. With both imports added, all 78 modules and main_window import cleanly on 3.11."
    - "AST scan of all 79 files finds exactly these 2 eager unbound annotation names and 0 elsewhere."
    - "On 3.14, reading _CommitStepHost.start.__annotations__ or inspect.get_annotations raises NameError CommitPlan (and CommitProbe for _on_probe_done)."
  falsification_test: "If adding the two imports did not make 3.11 import cleanly, or another module failed on 3.11, the hypothesis would be incomplete. It imported cleanly (0/78 failures)."
  fix_rationale: "Binding the two names at module level makes the eagerly evaluated annotations resolvable. Real imports are already used for CommitPlan in commit_panel.py and import_dialog.py. The regression gate addresses why it shipped."
  blind_spots: "No real 3.10 interpreter is available, so 3.10 syntax was checked only with ast feature_version and a 3.11+ API grep. PySide6 was replaced by a stub on 3.11, so Qt-runtime-only differences between PySide6 6.10.2 and 6.12 are not exercised. The traceback does not implicate them."
  candidate_causes:
    - "code: missing imports of CommitPlan / CommitProbe in widgets/migration_dialog.py (confirmed)"
    - "environment: interpreter version. 3.14 deferred annotations mask the defect and 3.10-3.13 evaluate eagerly (trigger, confirmed)"
    - "environment: PySide6 6.10.2 vs 6.12 (eliminated: reproduces with no PySide6 at all)"
    - "config/process: tests run only on 3.14, with no CI and no undefined-name lint (F821). This gate gap let it ship."
  and_gate: "yes. The failure needs BOTH the unbound name in an eagerly evaluated annotation (code) AND a <3.14 interpreter (environment). The code defect is the root cause, the interpreter is the trigger, and the 3.14-only test gate is why it was not caught."

## Symptoms

truth: The app starts and the migration dialog loads on every supported Python version (3.10+), not only 3.14.
expected: CLAUDE.md states Python 3.10+ is the practical minimum; the app must import and run on 3.10-3.14.
actual: With a venv on Python 3.11.3 (PySide6 6.10.2), `import kicad_lib_manager.main_window` fails:
  File "kicad_lib_manager/widgets/migration_dialog.py", line 338, in _CommitStepHost
    def start(self, plan: CommitPlan):
NameError: name 'CommitPlan' is not defined. Did you mean: 'CommitPanel'?
The repo venv (Python 3.14, deferred annotation evaluation per PEP 649/749) hides it; a 3.11 venv trips on it.
errors: NameError as above.
reproduction: Test 1 in UAT (found during UAT setup). Reproduce with any Python <3.14 interpreter that has PySide6: `python -c "import kicad_lib_manager.widgets.migration_dialog"`.
started: Discovered during UAT on 2026-11-12.

## Eliminated

- hypothesis: The PySide6 version difference (6.10.2 in the 3.11 venv vs 6.12 in the repo venv) causes the failure.
  evidence: Python 3.11.3 with PySide6 replaced by a stub (no PySide6 at all) reproduces the identical NameError at migration_dialog.py:338.
  timestamp: 2026-11-12T18:05:00Z

## Evidence

- timestamp: 2026-11-12T17:48:00Z
  checked: migration_dialog.py imports (lines 10-72) and _CommitStepHost (lines 316-375)
  found: There is no import of CommitPlan (it lives in importer/commit_plan.py) or CommitProbe (importer/commit_step.py:40). The `from ..importer.commit_step import (...)` at line 26 imports only functions. The annotations that use them are line 322 `self._plan: CommitPlan | None` and line 323 `self._probe: CommitProbe | None` (function-local attribute annotations, never evaluated), and line 338 `def start(self, plan: CommitPlan)` and line 373 `def _on_probe_done(self, worker: TaskWorker, probe: CommitProbe)` (parameter annotations, evaluated at def time before 3.14). The module has no `from __future__ import annotations`.
  implication: Line 338 is the first NameError on <3.14. Line 373 (CommitProbe) is a second, latent one that would surface right after 338 is fixed.
- timestamp: 2026-11-12T17:49:00Z
  checked: git log -S on the failing signature
  found: Introduced by 02cc644 feat(13-16), "the Result view, map buttons, Generate/chooser emits and the commit panel".
  implication: This is a recent regression from phase 13 plan 16. No gate caught it because the only interpreter used is 3.14.
- timestamp: 2026-11-12T17:55:00Z
  checked: AST scan (scratchpad annscan/scan.py) of all 79 files in kicad_lib_manager/ plus kicad_lib_manager.py and generate_lib_tables.py. It looks for annotation Names that are evaluated eagerly before 3.14 (def params/returns at module/class scope, defs inside functions, module/class AnnAssign) and are not bound before use (TYPE_CHECKING-only, bound later, or never bound).
  found: Exactly 2: migration_dialog.py:338 _CommitStepHost.start CommitPlan, and migration_dialog.py:373 _CommitStepHost._on_probe_done CommitProbe (neither is bound in the module). There are 0 forward-reference or TYPE_CHECKING-only cases. One informational case: importer/migration/symbols.py:235 plan_symbols `footprints: FootprintsOutcome` is unbound, but the module deliberately uses `from __future__ import annotations` (layering comment at lines 60-62). It never fails at import and only fails typing.get_type_hints / eval_str=True.
  implication: The defect is confined to migration_dialog.py, at two sites rather than one.
- timestamp: 2026-11-12T18:00:00Z
  checked: 3.14 repo venv: `_CommitStepHost.start.__annotations__`, inspect.get_annotations, annotationlib FORWARDREF
  found: NameError CommitPlan and NameError CommitProbe on access. FORWARDREF returns ForwardRef('CommitPlan').
  implication: On 3.14 the bug is latent, not absent. Anything that reads these annotations fails, so a 3.14 test can detect it.
- timestamp: 2026-11-12T18:05:00Z
  checked: C:/Python/Python311/python.exe (3.11.3) importing all 78 package modules with a PySide6/shiboken6 stub (scratchpad annscan/import_all_stubbed.py, run with -B so no pyc lands in the repo)
  found: 3 failures with one root: migration_dialog, help_dialog (which imports it) and main_window all fail with NameError CommitPlan at migration_dialog.py:338. This matches the UAT traceback exactly. The other 75 modules import fine on 3.11.
  implication: Reproduced deterministically without PySide6. Nothing else in the package breaks on 3.11.
- timestamp: 2026-11-12T18:08:00Z
  checked: Scratch copies of the package. copyA adds only `from ..importer.commit_plan import CommitPlan`; copyB also adds `from ..importer.commit_step import CommitProbe`.
  found: copyA on 3.11 fails with NameError CommitProbe at _on_probe_done (the next site). copyB on 3.11 has 0/78 failures and main_window imports OK. The AST scan of copyB finds 0 eager cases.
  implication: The two imports are necessary and sufficient for import on 3.11.
- timestamp: 2026-11-12T18:10:00Z
  checked: The 3.10 floor without a 3.10 interpreter: ast.parse(feature_version=(3,10)) on every module under 3.11, plus a grep for 3.11+/3.12+ stdlib APIs (tomllib, typing.Self/Never/override, datetime.UTC, StrEnum, ExceptionGroup, TaskGroup, hashlib.file_digest, contextlib.chdir, itertools.batched, Path.walk, walk_up=, onexc=, atomic/possessive regex)
  found: 0 syntax failures, 0 except*, and no 3.11+ API use (models.py already avoids StrEnum for 3.10).
  implication: G-13-1-a is the only known break on the 3.10 floor. The 3.10 check is approximate because there was no real 3.10 run.
- timestamp: 2026-11-12T18:12:00Z
  checked: Gates: .github/ CI, tox/nox, pre-commit, ruff/flake8/pyflakes/mypy in env, pyproject.toml, tests/
  found: There is no CI, and no linter or type checker is installed (env has only pytest 9.1.1 and pytest-qt 4.5.0). Tests are compiled only under cpython-314. pyproject.toml holds pytest config only, with no requires-python. The existing 3.10-floor guards are narrow (tests/test_sexpr.py regex opcodes, tests/test_manifests.py tomllib importorskip). tests/test_migration_dialog*.py exercise the dialog, but on 3.14 calling start()/_on_probe_done never evaluates annotations. An untracked uv.lock declares requires-python >=3.13, which contradicts the 3.10 floor (it is not committed).
  implication: No gate existed for this class. A 3.14-only suite with no undefined-name lint cannot see unbound annotation names.
- timestamp: 2026-11-12T18:15:00Z
  checked: Prototype regression check (scratchpad annscan/annotations_resolve_proto.py) on 3.14. It imports every module and calls inspect.get_annotations(obj) on every module-level function, class and class member (2588 objects).
  found: On the current tree it fails on exactly _CommitStepHost.start (CommitPlan) and _CommitStepHost._on_probe_done (CommitProbe). On patched copyB all annotations resolve. With eval_str=True it also flags symbols.plan_symbols (FootprintsOutcome, the deliberate future-annotations case) on both trees.
  implication: A test that runs on 3.14 catches this class. eval_str=True needs an explicit exemption (or a fix) for symbols.plan_symbols.
- timestamp: 2026-11-12T18:16:00Z
  checked: tests/test_importer_layering.py ALLOWED rules
  found: The rules govern importer.* modules only. Widgets are outside them, and commit_panel.py and import_dialog.py already import CommitPlan from importer.commit_plan.
  implication: Real imports in migration_dialog.py do not conflict with the layering test.

## Resolution

root_cause: kicad_lib_manager/widgets/migration_dialog.py (added in 02cc644, feat(13-16)) annotates two _CommitStepHost method parameters with names that are never bound in the module: line 338 `def start(self, plan: CommitPlan)` and line 373 `def _on_probe_done(self, worker: TaskWorker, probe: CommitProbe)`. CommitPlan lives in importer/commit_plan.py and CommitProbe in importer/commit_step.py. The module imports neither (its commit_step import lists only functions) and has no `from __future__ import annotations`. Python 3.10-3.13 evaluate parameter annotations when the class body executes, so importing migration_dialog (and with it help_dialog and main_window) raises NameError. Python 3.14 defers evaluation (PEP 649/749), so the repo venv, the only interpreter the tests run on, never evaluates them, and no lint or CI gate checks for undefined names.
fix:
verification:
files_changed: []
