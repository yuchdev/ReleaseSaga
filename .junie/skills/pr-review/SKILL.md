# pr-review

## Purpose
Produce a single merge recommendation from correctness, testing, and security review.

## Use when
- A branch, diff, or PR needs a structured review before merge.

## Workflow
1. Resolve the exact diff under review.
2. Review for correctness, regression risk, and test sufficiency.
3. Review the same diff for security concerns.
4. De-duplicate findings and assign a single verdict.

## Verdicts
- `APPROVE`, `REQUEST_CHANGES`, or `BLOCK`.

## Done checklist
- Blocking issues are separated from nice-to-have feedback.
- The final verdict matches the highest-severity finding.