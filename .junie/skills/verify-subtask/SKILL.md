# verify-subtask

## Purpose
Check whether implementation actually satisfies a named subtask or acceptance spec.

## Use when
- The task has an explicit checklist, milestone item, or spec file.

## Workflow
1. Read the subtask or acceptance criteria.
2. Compare each requirement against code, tests, and observable behavior.
3. Build a compliance matrix with evidence.
4. Return `PASS`, `PARTIAL`, or `FAIL` plus exact follow-ups.

## Done checklist
- Every requirement has a status.
- Deviations and omissions are explicit.