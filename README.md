# release-saga

`release-saga` is a standalone Python CLI for release automation with a Saga-style rollback pipeline: when one release step fails, every previously completed step is rolled back in reverse order.

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

| Config key | CLI flag | Built-in default | Notes |
| --- | --- | --- | --- |
| `wheel_glob` | `--wheel-glob` | `dist/*.whl` | Relative to the target project root |
| `s3_bucket` | `--s3-bucket` | `None` | Makes the S3 upload step available |
| `s3_prefix` | `--s3-prefix` | `{package_name_dash}/` | `str.format()` template with `package_name` and `package_name_dash` |
| `git_tag_template` | `--git-tag-template` | `v{version}` | `str.format()` template with `version` |
| `git_remote` | `--git-remote` | `origin` | Git remote used for tag pushes |
| `git_branch` | `--git-branch` | `None` | Defaults to the currently checked out branch |
| `release_notes_path` | `--release-notes-path` | `RELEASE_NOTES.json` | Relative to the target project root |

Example target-project configuration:

```toml
[tool.release-saga]
s3_bucket = "my-bucket"
git_tag_template = "v{version}"
```

Projects migrating from `extract_version` should explicitly set the legacy values below so existing release conventions do not change implicitly:

```toml
[tool.release-saga]
s3_bucket = "packages-s3-useast1-any"
s3_prefix = "{package_name_dash}/"
git_tag_template = "release.{version}"
git_remote = "origin"
git_branch = "master"
release_notes_path = "RELEASE_NOTES.json"
```

## Competitive comparison

<!-- Milestone 0004, Task 04.0 -->

## Migration from `release_package.py`

<!-- Milestone 0004, Task 04.0 -->
