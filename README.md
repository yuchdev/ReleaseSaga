# ReleaseSaga

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](./pyproject.toml)
[![Pytest status](https://github.com/yuchdev/ReleaseSaga/actions/workflows/ci.yml/badge.svg)](https://github.com/yuchdev/ReleaseSaga/actions/workflows/ci.yml)
[![Pytest coverage](https://img.shields.io/badge/pytest%20coverage-%E2%89%A590%25-brightgreen)](./.coveragerc)
[![License](https://img.shields.io/github/license/yuchdev/ReleaseSaga)](./LICENSE)

`ReleaseSaga` is a standalone Python CLI for release automation with a Saga-style rollback pipeline: when one release step fails, every previously completed step is rolled back in reverse order.

## Install

```bash
pip install release-saga
```

## Quickstart

From the root of the project you want to release:

```bash
release-saga --mode build
```

Use `--project-dir` to point at a different target project directory when needed.

## Configuration

`release-saga` reads configuration from the target project's `pyproject.toml` under `[tool.release-saga]`.
Precedence is: CLI flag > `[tool.release-saga]` > built-in default.

| Config key           | CLI flag               | Built-in default       | Notes                                                               |
|----------------------|------------------------|------------------------|---------------------------------------------------------------------|
| `wheel_glob`         | `--wheel-glob`         | `dist/*.whl`           | Relative to the target project root                                 |
| `publish_glob`       | `--publish-glob`       | `dist/*`               | Relative to the target project root; used for Twine upload inputs   |
| `s3_bucket`          | `--s3-bucket`          | `None`                 | Makes the S3 upload step available                                  |
| `s3_prefix`          | `--s3-prefix`          | `{package_name_dash}/` | `str.format()` template with `package_name` and `package_name_dash` |
| `git_tag_template`   | `--git-tag-template`   | `v{version}`           | `str.format()` template with `version`                              |
| `git_remote`         | `--git-remote`         | `origin`               | Git remote used for tag pushes                                      |
| `release_notes_path` | `--release-notes-path` | `RELEASE_NOTES.json`   | Relative to the target project root                                 |
| `extra_steps`        | *(none)*               | `[]`                   | Plugin steps to load, as `"path_or_module:ClassName"`; list order is priority - see [Extending with custom steps](#extending-with-custom-steps) |

Example target-project configuration:

```toml
[tool.release-saga]
s3_bucket = "my-bucket"
git_tag_template = "v{version}"
publish_glob = "dist/*"
```

Projects migrating from `extract_version` should explicitly set the legacy values below so existing release conventions do not change implicitly:

```toml
[tool.release-saga]
s3_bucket = "packages-s3-useast1-any"
s3_prefix = "{package_name_dash}/"
git_tag_template = "release.{version}"
git_remote = "origin"
release_notes_path = "RELEASE_NOTES.json"
publish_glob = "dist/*"
```

## How it compares

Several mature release tools exist. ReleaseSaga is not trying to replace all of them. It focuses
on one problem they mostly leave to you: **what happens when a multi-target release fails halfway**.

| | ReleaseSaga | [semantic-release](https://github.com/semantic-release/semantic-release) | [python-semantic-release](https://github.com/python-semantic-release/python-semantic-release) | [zest.releaser](https://github.com/zestsoftware/zest.releaser) |
|---|---|---|---|---|
| Ecosystem / runtime | Python CLI, any Python project | Node.js, npm-first (other ecosystems via plugins) | Python | Python |
| Main focus | Transactional publish across several targets | Fully automated CI releases from commit messages | Commit-driven version bump, changelog, tag, and publish | Interactive, human-driven release checklist |
| Failure mid-release | Completed steps are **rolled back in reverse order** (Saga) | Stops. Tags, published packages, and releases created so far stay in place | Stops. Earlier side effects stay in place | Stops. You clean up by hand |
| Re-run after a partial failure | Every step's `check()` detects existing tags, releases, and S3 objects **before** anything runs; `--mode clean` resumes an interrupted rollback | Depends on each plugin | Manual | Manual |
| Setup | `pip install`, optional `[tool.release-saga]` table; every key has a default | `package.json`/`.releaserc` plus a plugin list, Node toolchain on the build machine | `[tool.semantic_release]` config plus a Conventional Commits discipline | `pip install`; answer prompts |
| How it talks to services | Runs the standard CLIs you already have and authenticate: `git`, `gh`, `aws`, `twine` | Built-in plugin code calling service APIs | Built-in code calling service APIs | `twine` for uploads, `git`/`hg` for VCS |
| Version / changelog automation | No. You set the version explicitly (`--mode set-version`) | Yes, from Conventional Commits | Yes, from Conventional Commits | Bumps version, edits changelog |

### Why ReleaseSaga

- **Designed for transactional releases.** A real release often touches multiple systems: an artifact
  store (S3), a git remote, a GitHub release, and PyPI. Other tools run those steps as a script
  that halts on the first error, so a failed GitHub release can leave a pushed tag and an
  uploaded wheel behind. ReleaseSaga models each target as a `ReleaseStep` with `check()`,
  `execute()`, and `rollback()`. If a step fails, the steps already done are undone, so the
  release either happens completely or leaves no trace. The one exception is a PyPI upload,
  which can't be undone, so it always runs last.
- **Simple to set up and use.** No Node toolchain, no plugin list to assemble, and no commit
  message convention to adopt. Install it, run `release-saga --create-release --publish-pypi`
  from the project root, and opt into targets with flags. Configuration is a small, optional
  table in the `pyproject.toml` you already have, and every key has a sensible default.
- **Built on the external tools you already trust.** ReleaseSaga doesn't reimplement service
  clients. It calls `twine`, `aws`, `gh`, and `git` as subprocesses, so it uses the credentials,
  profiles, and `~/.pypirc` already on your machine or CI runner. There are no extra tokens or
  auth formats to learn. When a step fails, the error is the familiar output of the underlying
  tool, and you can rerun the same command by hand to debug it.
- **Extensible without forking.** A custom target, such as a Docker push, a docs deploy, or a
  Slack notice, is one small class listed in `extra_steps` or shipped as an entry-point plugin,
  and it gets the same rollback guarantees as the built-in steps.

**Pick something else if** you want fully automatic version numbers and changelogs generated from
commit history (semantic-release, python-semantic-release) or a guided interactive checklist
(zest.releaser). These tools can work together: for example, let a commit-driven tool pick the
version, then pass it to `release-saga --mode set-version` and use ReleaseSaga's pipeline to
publish.

## Architecture

`release-saga` is a tool you run *from* a target project's directory (or point at one with
`--project-dir`); it is not released by itself. `cli.py:main()` does two independent things:

1. **Local wheel lifecycle** (`--mode build|install|dev|reinstall|uninstall`) - builds, installs,
   or removes the target project's wheel via direct `pip`/`build` calls. This has no rollback: it's
   a straight sequence of local, cheap-to-repeat operations.
2. **Release pipeline** (opt-in via `--upload-s3`, `--create-release`, `--publish-pypi`) - a list of
   `ReleaseStep` objects handed to `run_release_pipeline()`, which runs them as a **Saga**: steps
   execute in order, and if one fails or can't run, every step that already completed is undone in
   reverse order.

For each step, the pipeline:

1. Calls `step.check()`. This must return `None` if the step can run, or a string reason if it
   can't (missing credentials, tool not installed, target already exists, etc.). A check failure -
   or a check that raises - stops the pipeline *before* `execute()` runs.
2. Calls `step.execute()`. If this raises, the pipeline rolls back **that step first, then every
   previously completed step**, in reverse order - the failing step may have partially succeeded
   before raising, so it gets a chance to undo whatever it already did.
3. Rollback is best-effort: if a step's `rollback()` itself raises, the pipeline logs a warning and
   keeps rolling back the rest rather than aborting the rollback.

Each CLI-driven pipeline run is also recorded under
`$XDG_DATA_HOME/release-saga/<package>/<version>/` (or
`~/.local/share/release-saga/<package>/<version>/`). If the process is interrupted after one or
more steps complete, rerun from the same target project with:

```bash
release-saga --mode clean
```

This finds the newest incomplete run for the target project's current version and retries rollback
for its completed steps in reverse order. Plugin steps that keep in-memory rollback state can
implement `recovery_data()` and `prepare_rollback()` to persist and restore that state; stateless
plugin rollback needs no additional methods.

Configuration flows from `config.py:load_config()`, which reads the target project's
`pyproject.toml` (`[project].name`/`.version` are required, `[tool.release-saga]` is optional) and
merges values in precedence order: built-in default → `[tool.release-saga]` → CLI flag.

**Library facade**: `cli.py`'s argument parser and step-assembly logic aren't private to the CLI -
they're the public functions `build_arg_parser()` and `build_release_steps()`. `release_saga/__init__.py`
re-exports both, alongside `ReleaseStep`, `ReleaseConfig`, `load_config`, `resolve_project_dir`, and
`run_release_pipeline`, so `from release_saga import ...` gives a library consumer the whole public
API without reaching into submodules. `release_saga.steps` likewise re-exports the four concrete
step classes alongside `ReleaseStep`. This is what lets a custom step reuse the CLI's own flags and
built-in step wiring instead of reimplementing them - see "Extending with custom steps" below.

## Release steps

The pipeline ships four built-in steps. `build_release_steps()` - used by `cli.py:main()`, and
importable directly from `release_saga` - wires them up in this order when their flag is passed:

| Order | Flag               | Step                | `check()` verifies                                                                                                                     | `execute()`                                                                                  | `rollback()`                                                                      |
|-------|--------------------|---------------------|----------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| 1     | `--upload-s3`      | `UploadS3Step`      | `s3_bucket` configured, `aws` installed and credentials valid, object doesn't already exist at the target key                          | `aws s3 cp` the wheel to `s3://{bucket}/{prefix}{wheel}`                                     | `aws s3 rm` the uploaded object                                                   |
| 2     | `--create-release` | `GitTagStep`        | `git` installed, `git_remote` configured, tag doesn't already exist locally or on the remote                                           | creates an annotated tag, pushes it to `git_remote`                                          | deletes the remote tag (if pushed), then the local tag (if created)               |
| 3     | `--create-release` | `GitHubReleaseStep` | `gh` installed and authenticated, release doesn't already exist for the tag, `release_notes_path` has an entry for the current version | builds release notes from `release_notes_path`, runs `gh release create` attaching the wheel | `gh release delete` (only if the release was actually created)                    |
| 4     | `--publish-pypi`   | `PublishPyPiStep`   | `twine` installed, `~/.pypirc` exists                                                                                                  | `twine check` then `twine upload` on files matched by `publish_glob`                         | **cannot roll back** - logs instructions to yank the release manually on pypi.org |

Because a PyPI upload can't be undone, keep `--publish-pypi` as the last step you enable for a
given release, after steps you're confident will succeed.

Steps that can only *partially* succeed track their own progress on `self` so `rollback()` only
undoes what actually happened - e.g. `GitTagStep` only pushes a tag-delete if it already pushed the
tag, and only deletes the local tag if it created one. Keep this in mind when writing your own step
(below): if `execute()` has more than one side effect, record which ones completed.

## Extending with custom steps

A custom step is a `ReleaseStep` subclass with exactly three methods:

- `check() -> str | None` - return `None` if the step can run now, otherwise a short reason it
  can't. Called before `execute()`; also called again on every step *after* this one before that
  step runs, so keep it cheap and side-effect-free.
- `execute() -> None` - do the work. Raise on failure (a normal exception is fine; subprocess
  calls should use `check=True` so `CalledProcessError` propagates).
- `rollback() -> None` - best-effort undo. Only called for steps that actually executed (or that
  raised mid-`execute()`), never for steps that were skipped by a failed `check()`.

**The recommended way to add one is plugin loading** - `release-saga` discovers and runs it
automatically, with no CLI reimplementation and no reload of the CLI tool required:

```toml
# pyproject.toml, in the target project
[tool.release-saga]
# "path_or_module:ClassName"; a relative path resolves against project_dir.
# List order is priority - steps run in this order, after the built-in S3/git/GitHub
# steps but before the (irreversible) PyPI publish step.
extra_steps = ["release_steps.py:ChangelogStep"]
```

```python
# release_steps.py, next to pyproject.toml
from release_saga.steps.base import ReleaseStep


class ChangelogStep(ReleaseStep):
    """Prepend a version heading to CHANGELOG.md."""

    name = "update changelog"

    def __init__(self, config):
        self.config = config
        self._path = config.project_dir / "CHANGELOG.md"
        self._original: str | None = None

    def check(self) -> str | None:
        if not self._path.is_file():
            return f"{self._path} does not exist"
        if f"## {self.config.version}" in self._path.read_text(encoding="utf-8"):
            return f"CHANGELOG.md already has an entry for {self.config.version}"
        return None

    def execute(self):
        self._original = self._path.read_text(encoding="utf-8")
        heading = f"## {self.config.version}\n\n"
        self._path.write_text(heading + self._original, encoding="utf-8")

    def rollback(self):
        if self._original is not None:
            self._path.write_text(self._original, encoding="utf-8")
```

That's it - no reload of `release-saga`, no wrapper script. `release-saga --create-release` now
also runs `ChangelogStep`, with full Saga rollback across all three steps. A step meant to be
shared across projects instead of copy-pasted into each one's `pyproject.toml` can be published as
its own pip-installable package registering a `release_saga.steps` entry point; `release-saga`
discovers every installed package's entry points in that group automatically. Pass `--no-plugins`
to disable both mechanisms at once. See
[Writing a custom release step](docs/tutorials/custom-release-step.md) for the full walkthrough
of both plugin mechanisms, their failure modes, and more examples.

**There's also an older way**, predating plugin loading: subclass `ReleaseStep` and call
`run_release_pipeline()` yourself. It's still supported, and still the right tool for a bespoke,
one-off release script that isn't worth an `extra_steps` entry - see
["Manual pipeline wiring" in the tutorial](docs/tutorials/custom-release-step.md#option-2-manual-pipeline-wiring-older-still-supported)
for the full version, including how to reuse `build_arg_parser()` and `build_release_steps()` to
avoid reimplementing the CLI's own flags:

```python
from pathlib import Path

from release_saga.config import load_config, resolve_project_dir
from release_saga.pipeline import run_release_pipeline
from release_saga.steps.git_tag import GitTagStep

from mymodule import ChangelogStep

project_dir = resolve_project_dir(Path.cwd())
config = load_config(project_dir, cli_overrides={})

run_release_pipeline(
    [
        ChangelogStep(config),
        GitTagStep(config),  # mix in a built-in step wherever it belongs in the order
    ]
)
```
