# 04 - Reconcile the "plugin-extensible" claim with the real extension story

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started

## Requirements

- `pyproject.toml`'s `[project].description` currently says "plugin-extensible", but no
  plugin/entry-point discovery mechanism exists anywhere in `cli.py` / `pipeline.py` /
  `steps/`. The real extension story is: subclass `ReleaseStep`, reuse
  `build_arg_parser()` / `build_release_steps()`, and call `run_release_pipeline()`
  yourself - documented in
  [/docs/tutorials/custom-release-step.md](/docs/tutorials/custom-release-step.md). Reword the
  description to match reality (e.g. "Cross-platform release automation with Saga-style
  rollback, extensible via a `ReleaseStep` subclass") rather than building a plugin/
  entry-point loader to match the current claim - that loader would be new discovery
  machinery this milestone deliberately excludes.
- Update the three internal doc references still pointing at this milestone's old
  pre-rename example path (`0001-working-implementation/01.0-hello-world-endpoint/...`) so
  no doc is left pointing at a folder that no longer exists:
  - `.claude/agents/subtask-verifier.md` (its "Subtask spec path" example)
  - `.claude/loops/implement-subtasks.md` (its `milestone_path` / `task_folder` example
    values)
  - `.claude/skills/verify-subtask/SKILL.md` (its subtask-id example)

  These are illustrative example paths only, not functional references - update them to
  `0001-generic-implementation/01.0-first-working-version/...` for consistency.

## Files

- `pyproject.toml`
- `.claude/agents/subtask-verifier.md`
- `.claude/loops/implement-subtasks.md`
- `.claude/skills/verify-subtask/SKILL.md`
