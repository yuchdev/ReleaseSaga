# 02 - CI-pipeline-friendly release execution

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started

## Requirements

Small, additive changes only - no new abstractions, no new dependencies:

- `PublishPyPiStep.check()` / `execute()`: accept twine's own `TWINE_USERNAME` /
  `TWINE_PASSWORD` env vars as an alternative to requiring `~/.pypirc` to exist. Twine
  already reads these natively, so this is a `check()` condition change
  (`~/.pypirc` exists **or** both env vars are set), not new credential-handling code.
- `GitHubReleaseStep.check()`: accept `GH_TOKEN` / `GITHUB_TOKEN` as an alternative to
  requiring a prior interactive `gh auth login` (i.e. `gh auth status` succeeding). `gh`
  itself already honors these env vars natively - this is again a `check()` condition
  change, not new auth code.
- One new CLI flag, `--dry-run`: runs every selected step's existing `check()` method (no
  new step-contract method), prints which steps would run and in what order, and exits 0
  if every check passed or 1 if any failed - without calling any step's `execute()`. This
  serves a CI "plan and gate" use case with minimal new surface.

## Explicitly out of scope

State this in the PR description so it isn't relitigated: `--json`/structured output,
OIDC trusted-publishing, a generic `--yes`/`--verbose` flag family, and AWS credential
handling changes (the `aws` CLI already natively supports `AWS_ACCESS_KEY_ID` and OIDC -
`UploadS3Step` needs no code change for that).

## Files

- `src/release_saga/steps/pypi_publish.py`
- `src/release_saga/steps/github_release.py`
- `src/release_saga/cli.py` (new `--dry-run` flag in `build_arg_parser()` and a branch in
  `main()`)
- `test/test_steps.py`, `test/test_cli.py` - corresponding test additions
