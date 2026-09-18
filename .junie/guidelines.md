# ReleaseSaga Junie Guidelines

## Purpose
- These guidelines preserve the intent of the Claude hook set using Junie-native instructions and manual checkpoints.
- This repository does not define Junie repo-level lifecycle hooks here; anything listed below is guidance unless Junie already enforces it internally.

## Project invariants
- Preserve Saga behavior: `check()` gates execution, execution failures trigger rollback of the failing step first and then prior completed steps in reverse order, and rollback remains best-effort.
- For multi-effect steps, track partial progress explicitly so rollback only undoes what actually happened.
- Keep irreversible or partially irreversible release actions clearly documented and ordered last.

## Validation checkpoints
- After Python code changes, run proportional validation with the real project tooling: `uv run ruff check .` and targeted `uv run pytest`.
- Use `uv run ruff format` when formatting is needed; do not rely on an automatic post-edit formatter.
- After documentation changes, verify changed links, anchors, and renamed targets; use the `link-check` and `doc-xref` skills when helpful.
- After dependency manifest changes, review outdated packages and known vulnerabilities with available tools such as `uv tree --outdated` and `pip-audit` when installed.

## Documentation rules
- Treat `README.md`, `RELEASE_NOTES.json`, CLI help text, and any future docs tree as the primary documentation surface for this repo.
- When renaming headings, files, or public symbols, update inbound references instead of fixing only the edited file.

## Safety and security
- Avoid destructive shell, database, Git, or release commands unless the user explicitly requires them.
- Never print full secret values in reports; show only minimal excerpts and recommend removal, rotation, and history cleanup where relevant.
- Treat Junie's built-in command and content safety as a baseline, not as a substitute for deliberate caution.

## Style notes
- Follow existing local style, including the repo's current use of `T | None`; do not rewrite annotations to `Optional[T]` just for consistency with the Claude kit.
- Prefer minimal, reviewable changes over broad mechanical rewrites.

## Hook parity notes
- Intent ported as guidelines/manual checkpoints: `dep_audit`, `doc_link_check`, `guard_bash`, `post_edit_format`, `run_tests`, and `secret_scan`.
- Not ported as repo-defined Junie hooks: `github_audit`, `session_start`, and the helper module `_common`.
- `style_fixes` was intentionally not ported because its `Optional[T]` rewrite conflicts with the existing codebase style.