# 03 - Enforce the coverage + lint gate in GitHub Actions

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-coverage-and-regression-backfill.md](01-coverage-and-regression-backfill.md)

## Requirements

- Extend `.github/workflows/ci.yml`'s single `build` job to run `pytest` with
  `--cov=release_saga --cov-report=term-missing`, mirroring the local
  `.claude/hooks/run_tests.py` Stop hook, so CI and local development enforce the
  identical bar defined once in `.coveragerc` (`fail_under = 90`). Keep the existing
  `ruff check .` step as-is.
- No new job, no Python-version matrix expansion, no coverage-upload service - this
  subtask only makes CI actually run the check the repo already defines locally; it does
  not add new CI infrastructure.
- Depends on subtask 01: land the coverage backfill first, otherwise this subtask's own
  PR fails CI the moment the gate is turned on.

## Files

- `.github/workflows/ci.yml`
