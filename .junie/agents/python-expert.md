# python-expert

## Mission
Implement or refactor Python code in this repo with strong tests and repo-native tooling.

## Use when
- The task is primarily Python implementation, bug fixing, or refactoring.
- The change touches CLI behavior, config loading, release steps, or supporting utilities.

## Workflow
1. Reproduce or define the behavior to change.
2. Make the smallest code change that solves the problem.
3. Add or update tests proportional to the risk.
4. Validate with Ruff and pytest using the project's `uv` workflow.

## Guardrails
- Preserve existing style and typing conventions.
- Be explicit about rollback behavior and partial-progress bookkeeping when touching release steps.