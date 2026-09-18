# implement-milestone

## Goal
Drive a milestone from researched plan to completed, validated slices.

## Inputs
- A milestone description, roadmap item, or plan file.

## Loop
1. Read the milestone and restate exit criteria.
2. Inventory dependencies, blockers, and unknowns.
3. Order the remaining subtasks by dependency and risk.
4. Run `implement-subtasks` for the next unfinished slice.
5. After each slice, update milestone state, validation status, and remaining blockers.
6. Stop when the milestone meets its acceptance criteria or a blocking unknown requires escalation.

## Expectations
- Complete one meaningful slice at a time.
- Keep validation proportional after every slice, not only at the end.