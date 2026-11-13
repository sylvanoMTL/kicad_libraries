---
title: Speed up the full test suite (about 30 min today)
created: 2026-11-13
source: owner, during /gsd-execute-phase 13 --gaps-only
area: tests
audit_acknowledged:
  milestone: v2.0
  at: 2026-11-13
---

The full `pytest` run (about 9700 tests) takes about 30 minutes, which the owner finds too long.

Known slow spots (earlier runs):
- `tests/test_commit_plan.py` + `tests/test_commit_step.py`: about 6.5 min for 167 tests (real git repos and submodules, 7-15 s each)
- WurthElektronik corpus parse budget test: about 1 min
- Qt window tests that build the full main or migration window per test

Agreed approach (2026-11-13):
1. Measure: one run with `--durations=50` to get the real top 50.
2. Parallelise with `pytest-xdist` (`-n auto`); check isolation of the `_live_custom_untouched` session guard and shared fixtures.
3. Add a `slow` marker (real git, Wurth corpus, kicad-cli) excluded from the quick run; the full run only at phase end.
4. Share expensive fixtures (build a template git repo once per session, copy per test).

Do after Phase 13 is verified, as a /gsd-quick task.
