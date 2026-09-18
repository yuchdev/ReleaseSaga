# Architecture Decision Records

ADRs for ReleaseSaga use the [MADR](https://adr.github.io/madr/) (Markdown Any
Decision Records) template. Each record lives in this directory as
`000N-slug.md`. Mermaid diagrams referenced by ADRs are stored in `assets/`.

## Inventory

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-release-automation-runs-as-a-saga-pipeline.md) | Release Automation Runs as a Saga Pipeline | Accepted | 2026-09-18 |

## Template

Use `template.md` when creating a new ADR:

```bash
cp docs/adr/template.md docs/adr/0002-short-title.md
```

Replace the template placeholders with the record's number, title, date, and status.

## Naming conventions

- Filename: `000N-kebab-slug.md` - sequential, zero-padded to four digits.
- Status values: `Proposed` | `Accepted` | `Implemented` | `Superseded` | `Deprecated`.
- Superseded ADRs keep their file; add a `Superseded by: [000N](...)` line to their header.
