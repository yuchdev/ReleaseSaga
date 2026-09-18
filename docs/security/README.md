# Security

Threat models, security review outputs, and posture documentation for RegeaseSaga.

The `security-auditor` agent owns this directory. Every change touching auth,
secrets, external integrations, or untrusted-input ingestion triggers a security
review whose output is stored here.

## Naming convention

`threat-model-<scope>.md` for threat models, `review-<scope>-<YYYY-MM-DD>.md`
for point-in-time reviews.

## What a threat model must contain

1. **Scope** - which components and trust boundaries are in scope.
2. **Assets** - what secrets, PII, and data are handled.
3. **Threat actors** - attacker profiles considered.
4. **STRIDE analysis** - Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation.
5. **Mitigations** - existing controls and open gaps.
6. **Verdict** - CRITICAL (merge blocked) / HIGH / MEDIUM / LOW / INFO.

## Security rules (non-negotiable)

- Never log secrets; rely on this project's log-redaction mechanism (if any)
  and verify it covers new sinks.
- Never hard-code credentials. Read from settings/env.
- Treat all untrusted external input as sensitive - no unredacted raw input
  in logs, exceptions, stored reports, or API error bodies.
- Untrusted input must never reach a shell, SQL string, `eval`, or an AI
  prompt without sanitization/parameterization.

## Starting point for the first threat model

> **SME REVIEW NEEDED (AI-drafted - verify before relying on this):**
>
> Drafted from a read of `src/release_saga/` at version `0.1.0`. Nothing below has been
> validated by a security engineer, and no control listed as "existing" has been tested.
> File it as `threat-model-release-pipeline.md` once reviewed.
>
> **1. Scope.** The `release-saga` CLI (`cli.py:main()`) and everything it invokes: config
> loading (`config.py`), the local wheel lifecycle (`package_ops.py`), the Saga pipeline
> (`pipeline.py`), and the four steps in `steps/`. Three trust boundaries: (a) the **target
> project directory** - its `pyproject.toml`, `RELEASE_NOTES.json`, and `dist/` are inputs the
> tool does not control; (b) the **operator's ambient credentials** - AWS, `gh`, `git`, and
> `~/.pypirc`, which the tool consumes but never manages; (c) the **external services** it
> mutates - S3, the git remote, GitHub Releases, PyPI.
>
> **2. Assets.** AWS credentials and the identity behind them; the PyPI API token in
> `~/.pypirc`; the GitHub token behind `gh`; push access to the git remote; the published wheel
> and its S3 object; the target project's unreleased version numbers and internal bucket names.
>
> **3. Threat actors.** (i) A malicious or compromised **target repository** - the most
> important one, because `--project-dir` accepts any path and the tool runs against whatever it
> is pointed at. (ii) A co-tenant with write access to the shared S3 bucket or the git remote.
> (iii) A compromised build dependency reachable from the target's build backend. Remote
> unauthenticated attackers are **not** in scope: this is an operator-run local CLI with no
> listening surface.
>
> **4. STRIDE.**
> - *Spoofing* - the tool verifies that credentials are **valid**, never that they are the
>   **intended** ones. `steps/s3.py:check()` accepts any identity `aws sts get-caller-identity`
>   returns; `steps/github_release.py:check()` accepts any authenticated `gh` account. Running
>   from the wrong shell publishes under the wrong account and the pipeline will not notice.
> - *Tampering* - `s3_prefix` and `git_tag_template` are `str.format()` templates read from the
>   target's `pyproject.toml` and rendered into an S3 key (`steps/s3.py:_key()`) and a git ref
>   (`steps/git_tag.py:_tag()`); `release.download_link` in the release-notes JSON is a third
>   template. `_key()` applies `lstrip("/")` and normalizes a trailing slash, but performs **no
>   path-traversal check**, so a crafted prefix can place an object outside the intended prefix
>   in a shared bucket. `publish_glob` determines exactly which files reach `twine upload`.
> - *Repudiation* - there is no audit trail. `pipeline._log()` writes to stderr only; nothing is
>   persisted, so a partially failed rollback leaves only a scrollback warning.
> - *Information disclosure* - `steps/s3.py:execute()` hard-codes `--acl public-read`, making
>   every uploaded wheel world-readable regardless of bucket policy. `cli.py:main()` and
>   `steps/github_release.py:tmp_release_notes()` `print()` package name, version, bucket-derived
>   URLs, and release-notes text. `~/.pypirc` is existence-checked but never read - preserve that.
> - *Denial of service* - not a meaningful category for an operator-triggered local CLI.
> - *Elevation of privilege* - **the highest-impact finding to adjudicate**:
>   `package_ops.build_wheel()` runs `python -m build` with `cwd=config.project_dir`, which
>   executes the target project's build backend (and any `setup.py`) as arbitrary code under the
>   operator's full AWS, GitHub, and PyPI credentials. Pointing `--project-dir` at an untrusted
>   repository is therefore equivalent to running that repository's code with publish rights.
>
> **5. Mitigations - existing.** All subprocess calls pass argument lists and none use
> `shell=True`. Every `check()` is an idempotency gate as well as an availability gate (S3
> `head-object`, local and remote tag existence, `gh release view`, a release-notes entry for the
> version), so a re-run after partial failure fails fast rather than double-publishing.
> Partial-success flags (`GitTagStep._created_local_tag` / `_pushed_remote_tag`,
> `GitHubReleaseStep._created_release`) keep rollback within what the run created.
> `package_ops.command_ok()` captures subprocess output and returns a bool, so credential probe
> output is not echoed. `GitHubReleaseStep.execute()` unlinks its temp notes file in a `finally`.
>
> **6. Mitigations - open gaps.** No validation of `[tool.release-saga]` values beyond "is a
> table". No traversal check on the rendered S3 key. No schema validation on the release-notes
> JSON (missing keys surface as `KeyError`). `--acl public-read` is not configurable. No identity
> confirmation before an irreversible step. `PublishPyPiStep.rollback()` cannot undo an upload and
> only prints a manual-yank URL. No audit record of what a run published or rolled back.
>
> **7. Verdict.** Not assigned - a reviewer must rate it. Suggested focus, highest first: the
> untrusted-target code-execution path, then the hard-coded `public-read` ACL, then S3 key
> traversal via a target-controlled `s3_prefix`.
