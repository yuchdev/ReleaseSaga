# Milestone 0001 - Generic, Cross-Platform Core

**Working codename:** `release-saga` (provisional - name and PyPI availability are
finalized as part of Task 02.0, not assumed here).

Turns [release_package.py](/release_package.py) from an ExtractVersion-specific
script into the installable core of a standalone release-automation tool: every
value that is currently hardcoded to this project (the S3 bucket, the git tag
format, the `master` branch, the exact wheel filename) becomes configuration, the
script becomes a real package with its own entry point, and it is verified to
actually run on Windows and macOS, not just the Linux/macOS boxes it happened to
be written on. The `ReleaseStep` Saga pipeline - the one capability none of
`poetry`, `hatch`, or `pypa/gh-action-pypi-publish` have - is promoted from an
internal implementation detail to a documented public API, since it is this
tool's actual point of differentiation.

This milestone does not add the plugin system (→ [0002](/docs/roadmap/0002-plugin-api/plan.md)),
OIDC/attestations parity with `gh-action-pypi-publish` (→ [0003](/docs/roadmap/0003-secure-ci-native-publishing/plan.md)),
or version-bumping/changelog automation (→ [0004](/docs/roadmap/0004-release-intelligence-and-launch/plan.md)).
It only has to produce a correct, cross-platform, generically-configurable core.

## Tasks

| Task | Name                                    | Category | Output                                                                                                          |
|------|------------------------------------------|----------|------------------------------------------------------------------------------------------------------------------|
| 01.0 | Config & Convention Generalization       | refactor | No ExtractVersion-specific literal remains in step code; all of it reads from a `[tool.release-saga]` table + CLI flags |
| 02.0 | Standalone Package Scaffold             | infra    | An installable `release-saga` distribution (src/ layout, entry point, own version) built from today's script    |
| 03.0 | Cross-Platform Compatibility Pass       | infra    | Verified correct behavior on Windows, macOS, and Linux, enforced by a CI matrix                                  |
| 04.0 | Saga Pipeline as Public API             | feature  | `ReleaseStep` / `run_release_pipeline` documented as stable public API, plus `--dry-run` and structured logging  |
