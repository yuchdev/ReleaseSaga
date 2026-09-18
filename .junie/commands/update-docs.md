# update-docs

## Goal
Repair and propagate documentation changes after edits, moves, or heading renames.

## Inputs
- Either a target path or a request to scan the documentation surface.

## Modes
### Scan mode
1. Inspect `README.md` and any docs tree for stale links or references.
2. Fix obvious path and anchor issues.
3. Flag ambiguous references for review.

### Targeted mode
1. Start from the changed file or renamed heading.
2. Find inbound references with `doc-xref`.
3. Update affected links, examples, and indexes.
4. Finish with `link-check`.

## Expectations
- Treat renamed headings and moved files as cross-file changes, not isolated edits.