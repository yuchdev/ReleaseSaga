# 05 - End-to-end smoke test for the local wheel-lifecycle modes

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-coverage-and-regression-backfill.md](01-coverage-and-regression-backfill.md)

## Requirements

- Add one integration-style test that actually exercises `--mode build` (and ideally
  `install` / `uninstall`) against a minimal real fixture package - a throwaway
  `pyproject.toml` plus a trivial module under a pytest `tmp_path` - using the real
  `pip` / `build` subprocesses rather than mocks. This is the one path noted as entirely
  untested end-to-end today; everything else in the suite mocks subprocess calls.
- Skip or xfail gracefully if `build` / `pip` aren't available or usable in the test
  environment, rather than making CI depend on network access it doesn't already need.
- Depends on subtask 01 landing first, so the coverage-owner test files stay stable
  before this slower integration test is added alongside them.

## Files

- `test/test_package_lifecycle_integration.py` (new)
