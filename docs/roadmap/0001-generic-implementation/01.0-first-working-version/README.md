# Task 01.0 - First Working Version

**Parent milestone:** [plan.md](../plan.md)
**Status:** 🔶 In progress / partial

## Scope

Close the gaps between ReleaseSaga's shipped core and a "complete working version": the
test-coverage gate the repo already enforces locally but not in CI, the ambient-credential
assumptions that make the release pipeline awkward to run from a CI runner, and one
doc/claim inconsistency around extensibility. Deliberately excludes new release-target
integrations, a plugin/entry-point loader, and structured (JSON) output - those are either
future-milestone scope (see [/README.md](/README.md)'s "Competitive comparison" /
"Migration" stubs, tagged Milestone 0004) or would overcomplicate a tool whose value is a
small, auditable Saga pipeline.

## Subtasks

| #  | Document                                                                                      | Status         | Blocks |
|----|------------------------------------------------------------------------------------------------|----------------|--------|
| 01 | [Coverage & regression backfill](01-coverage-and-regression-backfill.md)                       | ✅ Complete    | 02, 05 |
| 02 | [CI-pipeline-friendly release execution](02-ci-pipeline-friendly-execution.md)                 | ⬜ Not started | -      |
| 03 | [Enforce the coverage + lint gate in GitHub Actions](03-ci-coverage-lint-gate.md)               | ⬜ Not started | -      |
| 04 | [Reconcile the "plugin-extensible" claim with the real extension story](04-extensibility-claim-reconciliation.md) | ⬜ Not started | -      |
| 05 | [End-to-end smoke test for the local wheel-lifecycle modes](05-package-lifecycle-smoke-test.md) | ⬜ Not started | -      |

## Key constraints

- No new third-party runtime dependencies.
- No new CLI output format (no `--json`); no plugin/entry-point loader.
- The existing pipeline contract (`check()` / `execute()` / `rollback()`) does not change -
  new CI-friendliness is additive (optional env-var fallbacks, one new flag), never a
  breaking change to `ReleaseConfig` or `ReleaseStep`.
