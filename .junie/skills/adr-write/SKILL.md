# adr-write

## Purpose
Create or update an architecture decision record before implementation drifts beyond an undocumented design choice.

## Use when
- A change affects architecture, extension points, rollout strategy, or core invariants.

## Inputs
- A decision title.
- The motivating problem, constraints, and any candidate options.

## Workflow
1. Find the repo's ADR location; if none exists, propose one before creating a new convention.
2. Determine the next ADR identifier using the repo's existing numbering style, or start a clear sequence if the user wants ADRs introduced.
3. Summarize context, decision, consequences, and rejected alternatives.
4. Highlight impacts on rollback behavior, release safety, testing, and migration.
5. Link the ADR from the nearest index or README if that documentation surface exists.

## Done checklist
- The decision, alternatives, and consequences are explicit.
- Status is clear.
- Follow-up implementation or migration tasks are named.