# link-check

## Purpose
Validate that documentation links and heading anchors still resolve after edits.

## Use when
- Editing Markdown, renaming headings, or moving documentation files.

## Workflow
1. Review changed documentation paths and anchors.
2. Run a project link checker if one exists; otherwise inspect relative links and anchor slugs manually.
3. Fix dangling paths, stale anchors, and misnamed targets.
4. If the problem came from a rename, use `doc-xref` to propagate the change.

## Done checklist
- Changed docs have no known dangling links.
- Anchor names match the final headings.