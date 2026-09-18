# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ReleaseSaga` is a standalone Python CLI (`release-saga`) for release automation. It implements a
Saga-style pipeline: release steps run in order, and if any step fails or is unavailable, every
previously completed step is rolled back in reverse order.

Critically, this tool does not release *itself* — it is installed into and run from a **target
project's** directory (or pointed at one via `--project-dir`; defaults to `cwd`). It reads the
target project's `pyproject.toml` for `[project].name`/`.version` and for its own
`[tool.release-saga]` config table, then builds/installs/publishes *that* project's wheel. When
reading source in this repo, keep the distinction between "this repo's own `pyproject.toml`" and
"the target project's `pyproject.toml` that `config.py` parses at runtime" clear.

## Commands

```bash
uv sync                 # install (including dev deps: pytest, pytest-cov, ruff)
uv run pytest           # run the full test suite (test/ directory, not tests/)
uv run pytest test/test_pipeline.py::test_run_release_pipeline_rolls_back_failed_step_and_completed_steps
uv run ruff check .     # lint
uv run release-saga --mode build --project-dir /path/to/target/project
```

`pyproject.toml` sets `pythonpath = ["src"]` for pytest, so tests import `release_saga` without
requiring an editable install.

Note: two Ruff configs exist — `ruff.toml` (repo root) and `[tool.ruff]` in `pyproject.toml`. Ruff
gives the standalone `ruff.toml` precedence, so it's the one actually in effect (confirm with
`uv run ruff check --show-settings .` if the two ever appear to disagree). `ruff.toml`'s
`extend-exclude` comments reference `tests/lint/lint_rules.py` and `tests/flake8_lint/`, which do
not exist in this repository — that block was carried over from elsewhere and is inert here.
`ruff.toml` also deliberately excludes `UP007` (the rule that rewrites `Optional[X]` to `X | None`),
because the `.claude/hooks/style_fixes.py` PostToolUse hook does the opposite conversion on every
file it edits (`X | None` → `Optional[X]`, per `docs/dev/python_coding_standard.md`) — the two
configs agree on purpose. New code in a file the hook will touch should use `Optional[X]` directly
rather than relying on the hook to convert it: its auto-insertion of `from typing import Optional`
is a plain line scan that doesn't track multi-line parenthesized imports, so it can (and has)
inserted that line in the middle of one, producing a syntax error.

## Architecture

**Config resolution** (`config.py`): `load_config(project_dir, cli_overrides)` reads the target
project's `pyproject.toml`, requiring `[project].name` and `.version`, then merges config values
in precedence order: built-in default → `[tool.release-saga]` table in the target's
`pyproject.toml` → CLI flag. `cli.py` builds `cli_overrides` by filtering out unset (`None`) CLI
args before merging, so an explicit CLI flag always wins but an *unset* one never masks a value
from the config table. The result is a frozen `ReleaseConfig` dataclass passed to every step.

**Local package ops vs. release pipeline vs. version setting** (`cli.py`): `main()` does three
independent things based on `--mode`:
1. Local wheel lifecycle (`package_ops.py`): `build`/`install`/`dev`/`reinstall`/`uninstall` —
   direct `pip`/`build` subprocess calls against the target project, no rollback semantics.
2. The release pipeline (only when `--mode` isn't `uninstall` or `set-version`): an opt-in list of
   `ReleaseStep`s is assembled from `--upload-s3`, `--create-release` (adds both `GitTagStep` and
   `GitHubReleaseStep`), and `--publish-pypi` by the public `build_release_steps()` function, then
   handed to `run_release_pipeline`.
3. `--mode set-version --new-version X.Y.Z` (`version_ops.py`): sets the version deliberately
   *outside* the release pipeline/steps machinery — direct, one-shot, no rollback, same tradeoff
   as `package_ops.py`. Order matters: it checks `RELEASE_NOTES.json` doesn't already have an
   entry for the target version and that `uv` is on `PATH` *before* writing anything, then writes
   `pyproject.toml`'s `[project].version` (via a targeted line replace that preserves comments/
   formatting — it does not round-trip through `tomllib`, which is read-only anyway), adds an
   empty `{"release_notes": []}` entry to `RELEASE_NOTES.json` for the new version, and finally
   runs `uv lock` so `uv.lock` matches. `main()` returns immediately after this — it does not fall
   through to the wheel lifecycle or the release pipeline. `--version` (no value) is unrelated: a
   read-only flag that prints the target project's *current* version from its `pyproject.toml` and
   exits, independent of `--mode`.

**Public library facade** (`release_saga/__init__.py`): re-exports `ReleaseStep`, `ReleaseConfig`,
`load_config`, `resolve_project_dir`, `run_release_pipeline`, `build_arg_parser`, and
`build_release_steps` — the CLI's own argument parser and built-in step assembly are public,
reusable functions, not private to `cli.py`. `steps/__init__.py` similarly re-exports the four
concrete step classes (`GitTagStep`, `GitHubReleaseStep`, `PublishPyPiStep`, `UploadS3Step`)
alongside `ReleaseStep`. Together these let a library consumer add one custom `ReleaseStep`
subclass and still reuse the CLI's own flags and built-in step wiring rather than reimplementing
them — the worked pattern is in `docs/tutorials/custom-release-step.md`. There is deliberately no
`run(extra_steps=...)`-style wrapper; that was considered and rejected as unneeded abstraction over
~15 lines of glue.

Gotcha: `steps/__init__.py` eagerly importing all four step modules creates a real cycle risk.
`pipeline.py` imports `steps.base`, which runs `steps/__init__.py` in full, which imports
`pypi_publish.py` — so a *module-level* `from ..pipeline import _log` there would execute while
`pipeline` is still mid-import (it hasn't reached the `_log` definition yet) and raise an
`ImportError`. That import is deferred inside `PublishPyPiStep.rollback()` for exactly this reason
— keep it deferred if you touch that file.

**The Saga pipeline** (`pipeline.py`): for each step, in order:
- `step.check()` is called first — returns `None` if runnable, or a reason string if not. An
  exception or a non-`None` reason aborts the pipeline *before* `execute()` runs.
- `step.execute()` runs. On any exception (subprocess failures surface as
  `CalledProcessError`), rollback is triggered for `[failed_step, *reversed(completed_steps)]` —
  note the failing step's own `rollback()` is called too, since a step may partially complete
  before raising.
- Rollback is best-effort: `_rollback()` catches exceptions per-step and logs a warning rather
  than propagating, so one failed rollback doesn't prevent attempting the rest.
- Any abort path raises `SystemExit(1)`.

**Step contract** (`steps/base.py`): `ReleaseStep` is an ABC with `check()` (default: always
available), and abstract `execute()`/`rollback()`. Steps that can only partially succeed track
their own progress in instance state so `rollback()` only undoes what actually happened — see
`GitTagStep` (`_created_local_tag`, `_pushed_remote_tag`) and `GitHubReleaseStep`
(`_created_release`). `UploadS3Step` and `PublishPyPiStep` are single-action steps with no such
state; notably `PublishPyPiStep.rollback()` cannot undo a PyPI upload and only prints a manual-yank
warning — PyPI publish should generally be the last step in a pipeline for this reason.

Each step's `check()` verifies both tool availability (e.g. `gh`, `aws`, `twine`, `git` on `PATH`
and authenticated) and idempotency (e.g. tag/release/S3 key doesn't already exist) before anything
runs, so a re-run after a partial failure fails fast instead of double-publishing.
