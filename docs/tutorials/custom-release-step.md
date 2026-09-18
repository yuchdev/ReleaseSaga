# Writing a custom release step

This guide extends [README.md's "Extending with custom steps"](/README.md#extending-with-custom-steps)
section: it shows how to reuse `release-saga`'s own CLI wiring for its four built-in steps —
`UploadS3Step`, `GitTagStep`, `GitHubReleaseStep`, `PublishPyPiStep` — instead of hand-building
the whole step list, so a custom step is the *only* new code you have to write.

## Prerequisites

Read [README.md's "Configuration"](/README.md#configuration) and
[README.md's "Release steps"](/README.md#release-steps) sections first — this guide assumes you
already know `ReleaseConfig`'s fields and the built-in steps' `check()`/`execute()`/`rollback()`
contract, and doesn't restate them.

## The step

Reuse the `ChangelogStep` example from README verbatim — it prepends a version heading to
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

## Reusing the CLI's built-in steps

`release_saga` exposes the pieces `cli.py:main()` itself is built from:

- `build_arg_parser()` — the same `argparse.ArgumentParser` the `release-saga` command uses,
  including `--upload-s3`, `--create-release`, `--publish-pypi`, `--project-dir`, and the
  `[tool.release-saga]` override flags. Add your own flags to it with `parser.add_argument(...)`.
- `build_release_steps(config, *, upload_s3, create_release, publish_pypi)` — assembles the
  built-in steps selected by those three flags, in the same S3 → git tag → GitHub release → PyPI
  order the CLI itself runs them in.

Wiring your own entry point around these means the *only* new class you write is `ChangelogStep`
above:

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

## What this isn't

There's no `run(extra_steps=...)`-style entry point that owns this wiring for you. That was
considered and deliberately left out: the wiring above is ~15 lines, and a wrapper whose only job
is hiding those 15 lines isn't worth the extra abstraction. `build_arg_parser()` and
`build_release_steps()` are the whole extension surface.

## See also

- [README.md — Extending with custom steps](/README.md#extending-with-custom-steps) for the
  minimal pattern (no CLI reuse) using `run_release_pipeline()` directly.
- [README.md — Release steps](/README.md#release-steps) for the built-in steps' order and why
  `PublishPyPiStep` must run last.
