# dep-audit

## Purpose
Review dependency changes for security, staleness, and licensing risk.

## Use when
- `pyproject.toml`, `uv.lock`, or dependency pins changed.
- The user asks for a routine package audit.

## Workflow
1. Identify the changed manifests and the packages affected.
2. Check for known vulnerabilities with an available auditor such as `pip-audit`.
3. Review stale or major-outdated packages with `uv tree --outdated` or equivalent.
4. Flag license or redistribution risks when dependency metadata makes them visible.
5. Summarize immediate fixes, acceptable deferments, and blockers.

## Done checklist
- High/Critical security issues are called out first.
- Tooling gaps are reported instead of silently skipped.
- Recommendations distinguish urgent fixes from maintenance work.