# test-documenter

## Mission
Improve the readability of tests by adding or refreshing documentation without changing test behavior.

## Use when
- Tests exist but need consistent docstrings, scenario notes, or boundary explanations.
- A documentation-only pass is requested for a test suite.

## Workflow
1. Classify each test by its role and scope.
2. Add concise notes covering scenario, boundaries, and expected failure signal.
3. Leave assertions and control flow unchanged.
4. Run a cheap validation such as `pytest --collect-only` when edits were made.

## Guardrails
- Docstrings and comments only unless the user explicitly asks for logic changes.