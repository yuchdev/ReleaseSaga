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

## Architecture

`release-saga` is a tool you run *from* a target project's directory (or point at one with
`--project-dir`); it is not released by itself. `cli.py:main()` does two independent things:

1. **Local wheel lifecycle** (`--mode build|install|dev|reinstall|uninstall`) — builds, installs,
   or removes the target project's wheel via direct `pip`/`build` calls. This has no rollback: it's
   a straight sequence of local, cheap-to-repeat operations.
2. **Release pipeline** (opt-in via `--upload-s3`, `--create-release`, `--publish-pypi`) — a list of
   `ReleaseStep` objects handed to `run_release_pipeline()`, which runs them as a **Saga**: steps
   execute in order, and if one fails or can't run, every step that already completed is undone in
   reverse order.

For each step, the pipeline:

1. Calls `step.check()`. This must return `None` if the step can run, or a string reason if it
   can't (missing credentials, tool not installed, target already exists, etc.). A check failure —
   or a check that raises — stops the pipeline *before* `execute()` runs.
2. Calls `step.execute()`. If this raises, the pipeline rolls back **that step first, then every
   previously completed step**, in reverse order — the failing step may have partially succeeded
   before raising, so it gets a chance to undo whatever it already did.
3. Rollback is best-effort: if a step's `rollback()` itself raises, the pipeline logs a warning and
   keeps rolling back the rest rather than aborting the rollback.

Configuration flows from `config.py:load_config()`, which reads the target project's
`pyproject.toml` (`[project].name`/`.version` are required, `[tool.release-saga]` is optional) and
merges values in precedence order: built-in default → `[tool.release-saga]` → CLI flag.

**Library facade**: `cli.py`'s argument parser and step-assembly logic aren't private to the CLI —
they're the public functions `build_arg_parser()` and `build_release_steps()`. `release_saga/__init__.py`
re-exports both, alongside `ReleaseStep`, `ReleaseConfig`, `load_config`, `resolve_project_dir`, and
`run_release_pipeline`, so `from release_saga import ...` gives a library consumer the whole public
API without reaching into submodules. `release_saga.steps` likewise re-exports the four concrete
step classes alongside `ReleaseStep`. This is what lets a custom step reuse the CLI's own flags and
built-in step wiring instead of reimplementing them — see "Extending with custom steps" below.

## Release steps

The pipeline ships four built-in steps. `build_release_steps()` — used by `cli.py:main()`, and
importable directly from `release_saga` — wires them up in this order when their flag is passed:

| Order | Flag               | Step                | `check()` verifies                                                                                                                     | `execute()`                                                                                  | `rollback()`                                                                      |
|-------|--------------------|---------------------|----------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| 1     | `--upload-s3`      | `UploadS3Step`      | `s3_bucket` configured, `aws` installed and credentials valid, object doesn't already exist at the target key                          | `aws s3 cp` the wheel to `s3://{bucket}/{prefix}{wheel}`                                     | `aws s3 rm` the uploaded object                                                   |
| 2     | `--create-release` | `GitTagStep`        | `git` installed, `git_remote` configured, tag doesn't already exist locally or on the remote                                           | creates an annotated tag, pushes it to `git_remote`                                          | deletes the remote tag (if pushed), then the local tag (if created)               |
| 3     | `--create-release` | `GitHubReleaseStep` | `gh` installed and authenticated, release doesn't already exist for the tag, `release_notes_path` has an entry for the current version | builds release notes from `release_notes_path`, runs `gh release create` attaching the wheel | `gh release delete` (only if the release was actually created)                    |
| 4     | `--publish-pypi`   | `PublishPyPiStep`   | `twine` installed, `~/.pypirc` exists                                                                                                  | `twine check` then `twine upload` on files matched by `publish_glob`                         | **cannot roll back** — logs instructions to yank the release manually on pypi.org |

Because a PyPI upload can't be undone, keep `--publish-pypi` as the last step you enable for a
given release, after steps you're confident will succeed.

Steps that can only *partially* succeed track their own progress on `self` so `rollback()` only
undoes what actually happened — e.g. `GitTagStep` only pushes a tag-delete if it already pushed the
tag, and only deletes the local tag if it created one. Keep this in mind when writing your own step
(below): if `execute()` has more than one side effect, record which ones completed.

## Extending with custom steps

There's no plugin/entry-point loading yet — `release-saga`'s CLI only wires up the four steps
above. To run your own steps (in the same pipeline, with the same rollback guarantees), subclass
`ReleaseStep` and call `run_release_pipeline()` yourself. The contract is exactly three methods:

- `check() -> str | None` — return `None` if the step can run now, otherwise a short reason it
  can't. Called before `execute()`; also called again on every step *after* this one before that
  step runs, so keep it cheap and side-effect-free.
- `execute() -> None` — do the work. Raise on failure (a normal exception is fine; subprocess
  calls should use `check=True` so `CalledProcessError` propagates).
- `rollback() -> None` — best-effort undo. Only called for steps that actually executed (or that
  raised mid-`execute()`), never for steps that were skipped by a failed `check()`.

```python
from pathlib import Path

from release_saga.config import load_config, resolve_project_dir
from release_saga.pipeline import run_release_pipeline
from release_saga.steps.base import ReleaseStep
from release_saga.steps.git_tag import GitTagStep


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


class SlackNotifyStep(ReleaseStep):
    """Post to Slack; rollback deletes the message if one was posted."""

    name = "notify Slack"

    def __init__(self, config, webhook_url: str):
        self.config = config
        self.webhook_url = webhook_url
        self._posted = False

    def check(self) -> str | None:
        if not self.webhook_url:
            return "no Slack webhook configured"
        return None

    def execute(self):
        # post_to_slack(self.webhook_url, f"Released {self.config.version}")
        self._posted = True

    def rollback(self):
        if self._posted:
            # post_to_slack(self.webhook_url, f"Release {self.config.version} rolled back")
            pass


project_dir = resolve_project_dir(Path.cwd())
config = load_config(project_dir, cli_overrides={})

run_release_pipeline(
    [
        ChangelogStep(config),
        GitTagStep(config),          # mix in a built-in step wherever it belongs in the order
        SlackNotifyStep(config, webhook_url="https://hooks.slack.example/..."),
    ]
)
```

`ChangelogStep` shows the common pattern for a step whose rollback needs a prior state (it snapshots
the file before mutating it). `SlackNotifyStep` shows the common pattern for a step whose
`execute()` may or may not have "really" happened by the time something later fails (it tracks
`_posted` so `rollback()` only fires if `execute()` got far enough to matter) — the same technique
`GitTagStep` and `GitHubReleaseStep` use for their own partial-success tracking.

The example above hand-builds its step list from scratch. If you also want the CLI's own
`--upload-s3`/`--create-release`/`--publish-pypi` flags and built-in steps alongside your custom
one — without reimplementing that wiring yourself — see
[Writing a custom release step](docs/tutorials/custom-release-step.md), which reuses
`build_arg_parser()` and `build_release_steps()` from the library.
