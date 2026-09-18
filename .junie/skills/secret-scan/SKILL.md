# secret-scan

## Purpose
Detect likely hardcoded credentials or sensitive tokens before they are committed or shared.

## Use when
- Reviewing changed files.
- A user asks for a focused secret sweep.

## Workflow
1. Define the file set to inspect.
2. Search for likely credential patterns and suspicious high-entropy strings.
3. Review context to reduce false positives.
4. Report only minimal excerpts.
5. Recommend removal, rotation, and history cleanup when a real secret is found.

## Done checklist
- No full secrets are reproduced.
- Findings distinguish placeholders, test fixtures, and likely real credentials.