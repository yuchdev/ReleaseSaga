# Writing a custom release step

This guide extends [README.md's "Extending with custom steps"](/README.md#extending-with-custom-steps)
section. It shows the two ways to add a custom `ReleaseStep` to a release *without* reloading or
reimplementing `release-saga`'s own CLI:

1. **Plugin loading** (recommended) — `release-saga` discovers and runs your step automatically,
   via either a `[tool.release-saga] extra_steps` entry in the target project's `pyproject.toml`,
   or a packaging entry point. No wrapper script, no re-parsing CLI flags yourself.
2. **Manual pipeline wiring** (the older, still-supported way) — subclass `ReleaseStep` and call
   `run_release_pipeline()` yourself, optionally reusing `build_arg_parser()` and
   `build_release_steps()` to avoid reimplementing the built-in steps' flags.

Read [README.md's "Configuration"](/README.md#configuration) and
[README.md's "Release steps"](/README.md#release-steps) sections first — this guide assumes you
already know `ReleaseConfig`'s fields and the built-in steps' `check()`/`execute()`/`rollback()`
contract, and doesn't restate them.

## The step

Every example below reuses the same `ChangelogStep` — it prepends a version heading to
`CHANGELOG.md` and snapshots the file so `rollback()` can restore it:

```python
from pathlib import Path

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

The constructor's only required argument is `config` (a `ReleaseConfig`) — both plugin mechanisms
below instantiate your step class as `YourStep(config)`.

## Option 1a: `extra_steps` in `pyproject.toml` (single-project, no packaging)

This is the default way to add a step that's specific to one project: drop a `.py` file in the
project root (or anywhere else relative to it) and reference it from
`[tool.release-saga] extra_steps`. **List order is priority** — steps run in the order listed.

`release_steps.py`, at the target project's root, next to `pyproject.toml`:

```python
# release_steps.py
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

`pyproject.toml`:

```toml
[tool.release-saga]
# Each entry is "path_or_module:ClassName". A relative path is resolved against project_dir.
# List order is priority: entries run in this order, after the built-in S3/git/GitHub steps
# but before the (irreversible) PyPI publish step.
extra_steps = ["release_steps.py:ChangelogStep"]
```

Now `release-saga --create-release` runs `GitTagStep`, `GitHubReleaseStep`, then
`ChangelogStep`, with full Saga rollback across all three — no code changes to `release-saga`
itself, and no wrapper script to maintain.

A second, unrelated step in the same file (or a second file) is just another list entry:

```toml
[tool.release-saga]
extra_steps = [
    "release_steps.py:ChangelogStep",
    "release_steps.py:SlackNotifyStep",
    "scripts/docs_step.py:PublishDocsStep",
]
```

`extra_steps` entries can also point at an importable, dotted module path instead of a file
(useful once a project-specific step graduates into its own installed module, before it's worth
publishing as a standalone package with an entry point):

```toml
[tool.release-saga]
extra_steps = ["myproject.release_steps:ChangelogStep"]
```

### Failure modes

Each of these raises `release_saga.plugins.PluginLoadError`, which `release-saga`'s CLI turns into
a clean `argparse` usage error (exit code 2) instead of a traceback:

- The spec isn't `"location:ClassName"` (missing or empty `:`-separated parts).
- The referenced `.py` file doesn't exist, or raises while being executed (e.g. a bad import at
  module level).
- The referenced module can't be imported (`ModuleNotFoundError` and friends).
- The file/module doesn't define the named attribute.
- The named attribute isn't a `ReleaseStep` subclass.
- The class can't be constructed as `YourStep(config)` (wrong `__init__` signature).

Pass `--no-plugins` to skip `extra_steps` (and entry-point discovery — see below) entirely,
e.g. while debugging whether a plugin step is the cause of an unexpected pipeline failure.

## Option 1b: packaging entry points (shared across projects)

If a step is meant to be reused across multiple projects, publish it as its own pip-installable
package and register it under the `release_saga.steps` entry-point group instead of copy-pasting
`extra_steps` into every project's `pyproject.toml`. `release-saga` discovers every installed
package's entry points in that group automatically — no target-project configuration at all.

Plugin package layout:

```
release-saga-changelog/
├── pyproject.toml
└── src/
    └── release_saga_changelog/
        └── __init__.py   # defines ChangelogStep, same class as above
```

Plugin package's `pyproject.toml`:

```toml
[project]
name = "release-saga-changelog"
version = "1.0.0"
dependencies = ["release-saga"]

[project.entry-points."release_saga.steps"]
changelog = "release_saga_changelog:ChangelogStep"
```

Once `pip install release-saga-changelog` is run in the same environment as `release-saga`, every
`release-saga` invocation against *any* target project automatically includes `ChangelogStep` in
its pipeline (subject to `check()` — see below). Entry-point steps run after any configured
`extra_steps`, sorted by entry-point name (`changelog` above) for a deterministic order across
multiple installed plugin packages.

### Failure modes

Same `PluginLoadError` behavior as `extra_steps`: a broken entry point (fails to import, isn't a
`ReleaseStep` subclass, or can't be constructed with `config`) is reported as a clean usage error
rather than a traceback, and `--no-plugins` disables entry-point discovery too.

### Opting out per-step

Unlike `extra_steps`, an installed entry-point step runs for every project unconditionally unless
disabled. Give the step its own `check()` opt-out so it's harmless when not wanted, e.g. gated on
a `[tool.release-saga]` key of its own:

```python
class ChangelogStep(ReleaseStep):
    name = "update changelog"

    def __init__(self, config):
        self.config = config
        self._path = config.project_dir / "CHANGELOG.md"
        self._original: str | None = None

    def check(self) -> str | None:
        if not self._path.is_file():
            # Not every project has a CHANGELOG.md; skip quietly instead of failing the release.
            return "no CHANGELOG.md in this project"
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

Remember from [README.md's "Architecture"](/README.md#architecture): a `check()` failure just
skips *that* step (with a logged reason) rather than aborting the whole pipeline, so a
"not applicable here" entry-point step is safe to leave installed everywhere.

## Option 2: manual pipeline wiring (older, still supported)

There's no requirement to use plugin loading at all. Subclass `ReleaseStep` and call
`run_release_pipeline()` directly — this is exactly the pattern from
[README.md's "Extending with custom steps"](/README.md#extending-with-custom-steps):

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

### Reusing the CLI's built-in steps from a wrapper script

To also get the CLI's own `--upload-s3`/`--create-release`/`--publish-pypi` flags and built-in
step wiring without reimplementing them, reuse the pieces `cli.py:main()` itself is built from:

- `build_arg_parser()` — the same `argparse.ArgumentParser` the `release-saga` command uses,
  including `--upload-s3`, `--create-release`, `--publish-pypi`, `--project-dir`, `--no-plugins`,
  and the `[tool.release-saga]` override flags. Add your own flags to it with
  `parser.add_argument(...)`.
- `build_release_steps(config, *, upload_s3, create_release, publish_pypi, plugin_steps=None)` —
  assembles the built-in steps selected by those three flags, in the same S3 → git tag → GitHub
  release → (optional `plugin_steps`) → PyPI order the CLI itself runs them in.

```python
import sys

from release_saga import (
    build_arg_parser,
    build_release_steps,
    load_config,
    resolve_project_dir,
    run_release_pipeline,
)

from mymodule import ChangelogStep


def main() -> int:
    parser = build_arg_parser()
    parser.add_argument("--update-changelog", action="store_true")
    args = parser.parse_args()

    project_dir = resolve_project_dir(args.project_dir)
    config = load_config(project_dir, cli_overrides={})

    # publish_pypi=False here on purpose: PublishPyPiStep can't be rolled back (see
    # README's "Release steps" table), so it must stay the *last* step in the pipeline.
    # Build the other built-ins, insert the custom step, then append PyPI last.
    steps = build_release_steps(
        config,
        upload_s3=args.upload_s3,
        create_release=args.create_release,
        publish_pypi=False,
    )
    if args.update_changelog:
        steps.append(ChangelogStep(config))
    if args.publish_pypi:
        from release_saga.steps import PublishPyPiStep

        steps.append(PublishPyPiStep(config))

    if steps:
        run_release_pipeline(steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Running this script with `--create-release --update-changelog` gets you `GitTagStep`,
`GitHubReleaseStep`, and `ChangelogStep`, in that order, with full Saga rollback across all three
— without a single line of `release-saga`'s own CLI logic reimplemented.

### When to reach for this instead of plugin loading

Manual wiring is still the right tool when a script needs its own bespoke argument parsing, needs
to build a step list programmatically based on something plugin loading can't express (e.g.
runtime-computed steps, not just config-driven ones), or is a one-off/throwaway release script
that isn't worth adding an `extra_steps` entry for. For anything that should "just run" every time
`release-saga` runs against a project, prefer Option 1 above.

## See also

- [README.md — Extending with custom steps](/README.md#extending-with-custom-steps) for a
  condensed version of both options.
- [README.md — Release steps](/README.md#release-steps) for the built-in steps' order and why
  `PublishPyPiStep` must run last.
