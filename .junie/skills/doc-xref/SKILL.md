# doc-xref

## Purpose
Find and update inbound references when a document path, heading, or public symbol changes.

## Use when
- Renaming or moving docs.
- Renaming user-facing commands, config keys, or public code symbols with doc references.

## Workflow
1. Resolve the target being renamed or moved.
2. Search inbound references across `README.md`, docs if present, `src/`, and `test/`.
3. Update every confirmed reference, not just the file being edited.
4. Re-check anchors and related links after the rename.
5. Hand off to `link-check` for final validation.

## Done checklist
- All confirmed inbound references are handled.
- Ambiguous matches are listed for human review.