# 0001 - Release Automation Runs as a Saga Pipeline

> **Status:** Accepted
>
> **Date:** 2026-09-18
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

`release-saga` coordinates release actions that mutate several external systems in one
operator-triggered run: it can upload a wheel to S3, create and push a git tag,
publish a GitHub release, and upload distributions to PyPI. Those actions have
different failure modes and different rollback affordances: some can be undone
cleanly, some can fail halfway through, and PyPI publication cannot be fully reversed.

The tool also has two distinct execution styles that should not be conflated:

- Local wheel lifecycle commands (`build`, `install`, `dev`, `reinstall`,
  `uninstall`) are cheap, local, and repeatable; they do not need rollback.
- Release actions talk to remote systems and can leave the target project in a
  partially released state if a later step fails.

Without a single pipeline contract, each release action would have to invent its own
preflight checks, failure handling, and cleanup rules. That would make step ordering
harder to reason about, make custom steps inconsistent with built-in ones, and push
operator recovery into ad hoc manual judgment during an already failing release.

## Decision

Release automation in `release-saga` is implemented as an **ordered Saga pipeline**.
The CLI assembles `ReleaseStep` instances and passes them to
`run_release_pipeline()`, which applies the same contract to every step:

1. `check()` runs first and must be side-effect free. It returns `None` only when the
   step can safely run now; a string result or raised exception stops the pipeline
   before `execute()` is called for that step.
2. `execute()` performs the step's forward action.
3. If `execute()` raises, the pipeline rolls back **the failing step first**, then all
   previously completed steps in reverse order.
4. `rollback()` is best-effort. A rollback failure is logged as a warning, but the
   pipeline continues rolling back the remaining steps.

Step authors must record partial progress on the step instance whenever `execute()`
has more than one side effect. Rollback logic may only undo effects that actually
happened. `GitTagStep` is the reference pattern: it tracks whether it created the
local tag and whether it pushed the remote tag, then only deletes the effects that
occurred.

Irreversible or partially irreversible actions must be ordered last. The built-in
`PublishPyPiStep` is the canonical example: its rollback can only emit manual cleanup
instructions, so it belongs after reversible steps such as S3 upload, git tagging,
and GitHub release creation.

See [assets/0001-release-pipeline-saga-flow.mmd](assets/0001-release-pipeline-saga-flow.mmd)
for the control-flow summary.

## Alternatives Considered

| Alternative | Pros | Cons | Reason rejected |
|-------------|------|------|-----------------|
| Forward-only sequential release script | Smallest implementation surface; easy to sketch for the first happy path | A later failure leaves earlier remote side effects behind with no standard cleanup path | Rejected because the project's main value is coordinating multi-system release actions safely, not just sequencing shell commands |
| Per-step ad hoc cleanup inside `execute()` | Each step can tailor its own error handling closely to the command it runs | Cleanup order becomes inconsistent across steps; a later step cannot reliably unwind earlier ones; custom steps would all re-implement orchestration | Rejected because it hides global release semantics inside individual step bodies instead of one pipeline contract |
| Distributed-transaction style all-or-nothing coordinator | Strong conceptual guarantee if every external system supported prepare/commit/abort | Git, GitHub Releases, S3, and PyPI do not expose a shared transaction protocol, and the operational complexity would be far beyond this CLI's scope | Rejected as infeasible for the external systems `release-saga` targets |
| Ordered Saga pipeline with compensating rollback (chosen) | Gives one uniform contract for built-in and custom steps; handles preflight failures, mid-step failures, and partial success explicitly; matches what external release systems actually support | Rollback is not perfect; step authors must track partial progress carefully; some effects still require manual cleanup | **Accepted** |

## Consequences

### Positive

- Operators get a predictable failure model: failed availability checks stop the run
  early, and execution failures trigger compensating rollback in a documented order.
- Built-in and custom steps share the same extension contract (`check()`,
  `execute()`, `rollback()`), so new steps can participate in the same safety model
  without needing custom orchestration code.
- Partial side effects are handled explicitly instead of implicitly assumed away,
  which is important for multi-effect steps such as git tagging and GitHub release
  creation.
- The pipeline can include irreversible work, but the order requirement keeps that
  risk visible and contained to the tail of the release.

### Negative

- Rollback is best-effort, not a guarantee that every external system is restored to a
  pristine state.
- Step implementations are responsible for accurate progress tracking; missing state
  bookkeeping can make rollback over-delete or under-delete.
- Some failures still require manual operator action, especially after a PyPI upload
  or after a rollback command itself fails.
- Step ordering becomes part of the release design, not just an incidental CLI detail;
  contributors must think about reversibility before inserting a new step.

## Validation / Rollout

This ADR documents the architecture already implemented in the shipped pipeline.
Validation should continue to use the existing automated checks that cover the core
Saga guarantees:

- [`../../test/test_pipeline.py`](../../test/test_pipeline.py) verifies that a failed
  step is rolled back before previously completed steps and that failed `check()`
  calls stop later execution.
- [`../../test/test_steps.py`](../../test/test_steps.py) verifies step-specific
  partial-effect cleanup behavior, including `GitTagStep` rollback only undoing the
  effects that actually occurred.
- New release steps should not be merged unless they follow this contract, track
  partial progress when needed, and document any irreversible behavior before being
  added to the CLI order.

## Links

- **Roadmap task:** _(none - this ADR documents the current baseline architecture)_
- **Supporting specs:**
  - [`../../README.md#architecture`](../../README.md#architecture)
  - [`../../src/release_saga/pipeline.py`](../../src/release_saga/pipeline.py)
  - [`../../src/release_saga/steps/base.py`](../../src/release_saga/steps/base.py)
  - [`../../src/release_saga/steps/git_tag.py`](../../src/release_saga/steps/git_tag.py)
  - [`../../src/release_saga/steps/pypi_publish.py`](../../src/release_saga/steps/pypi_publish.py)
- **Diagrams:** [assets/0001-release-pipeline-saga-flow.mmd](assets/0001-release-pipeline-saga-flow.mmd)
