# document-tests

## Purpose
Standardize test documentation so future readers can understand scope, scenario, and failure meaning quickly.

## Use when
- Existing tests need a documentation pass.
- New tests were added and the repo wants consistent test descriptions.

## Workflow
1. Review the target tests and classify them by scope such as unit, mock-heavy, integration, or end-to-end.
2. Add concise docstrings or comments that cover scenario, critical boundaries, and expected failure signal.
3. Avoid behavior changes unless the task explicitly includes test fixes.
4. Validate collection after edits.

## Done checklist
- Documentation is accurate and concise.
- Test logic and assertions are unchanged unless separately requested.