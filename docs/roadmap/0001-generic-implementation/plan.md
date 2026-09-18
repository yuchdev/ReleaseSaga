# Milestone 0001 - Generic Implementation

**Package:** `release_saga` | **Module root:** `src/release_saga/`

ReleaseSaga's core is already shipped: config resolution, the Saga pipeline, the four
built-in release steps, and a CLI/library split that lets a consumer reuse the CLI's own
argument parser and step assembly (`build_arg_parser()` / `build_release_steps()`, see
[/README.md#architecture](/README.md#architecture)). This milestone closes the gap between
that shipped core and a genuinely **complete working version**: a test-coverage gate the
repo already enforces locally but not in CI, ambient-credential assumptions that make the
release pipeline awkward to run from a CI runner, and a doc/claim inconsistency around
extensibility. It deliberately does not add new release-target integrations, a plugin/
entry-point loader, or a new output format - see this milestone's one task for what's
explicitly out of scope and why.

## Tasks

| Task | Name                  | Category  | Output                                                                                            |
|------|-----------------------|-----------|-----------------------------------------------------------------------------------------------------|
| 01.0 | First Working Version | hardening | Coverage gate closed, CI enforces it, credentials work non-interactively, extension docs match reality |
