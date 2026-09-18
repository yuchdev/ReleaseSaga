# implement-subtasks

## Goal
Advance a larger task by completing exactly one well-scoped subtask per iteration.

## Inputs
- A task description plus any existing checklist or plan.

## Loop
1. Build a cursor of done, in-progress, and not-started subtasks.
2. Pick the next smallest subtask that unblocks the plan.
3. Implement the minimum change needed for that subtask.
4. Run targeted validation immediately.
5. Record the outcome, remaining gaps, and the next candidate subtask.

## Expectations
- Do not silently expand scope to multiple subtasks.
- If the next subtask is underspecified, clarify or verify it before coding.