# 01 - Coverage & regression backfill

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- Add tests until `uv run pytest -q --cov=release_saga --cov-report=term-missing` meets
  `.coveragerc`'s `fail_under = 90`, with **no source changes** - this is a test-only
  subtask. At the time of writing, total coverage is 71.73%, with these files well under
  bar: `package_ops.py` (59.65%), `steps/github_release.py` (57.33%), `steps/git_tag.py`
  (72.92%), `steps/pypi_publish.py` (69.70%), and `cli.py` (69.66%, mainly its
  `--mode build|install|dev|reinstall|uninstall` branches at `cli.py:108-122`).
- If a genuinely dead/unreachable line surfaces while writing tests, note it in the PR
  description for follow-up rather than deleting code as part of a "just write tests"
  subtask.
- Mirror the existing mocking style already used in `test/test_steps.py` /
  `test/test_pipeline.py` (subprocess calls mocked, no real `git`/`gh`/`aws`/`twine`
  invocations) - real end-to-end exercise of the local wheel lifecycle is subtask 05, not
  this one.

## Result

Total coverage went from 71.73% to **99.79%** (`uv run pytest -q --cov=release_saga
--cov-report=term-missing`), with no source changes. `test/test_public_api.py`,
`test/test_pipeline.py`, `test/test_cli.py`, `test/test_steps.py`, and
`test/test_package_ops.py` were extended (`test/test_config.py` too, to close a couple of
`config.py` branches noticed along the way).

One genuinely unreachable branch surfaced and is **not** worth chasing: `cli.py`'s
`elif args.mode == "uninstall":` fall-through (reported as `121->124`) can never be taken,
because `build_arg_parser()`'s `--mode` argument is constrained to exactly the five handled
values via `choices=[...]` - argparse itself rejects anything else before `main()`'s body
ever runs. Left as the sole line under 100% per-file coverage; still well within the 90%
total-coverage gate.

## Files

- `test/test_package_ops.py` - extend with cases covering `build_wheel`, `install_wheel`,
  `install_wheel_devmode`, `uninstall_wheel`, `cleanup_old_wheels` branches not yet hit.
- `test/test_steps.py` - extend `GitTagStep`, `GitHubReleaseStep`, `PublishPyPiStep`
  coverage for their currently-uncovered `check()`/`execute()`/`rollback()` branches.
- `test/test_cli.py` - extend to cover each `--mode` branch in `cli.py:main()`.
