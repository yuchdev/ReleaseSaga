# test-gap

## Purpose
Identify the most valuable missing tests instead of chasing raw coverage numbers blindly.

## Use when
- A feature area feels under-tested.
- The user wants a prioritized testing backlog.

## Workflow
1. Inspect existing tests and, when useful, gather coverage evidence.
2. Map uncovered or weakly covered lines to behaviors and failure modes.
3. Rank gaps by user impact and rollback/release risk.
4. Propose concrete test cases with suggested scope and assertions.

## Priority rubric
- `P0`: data loss, bad release state, missing rollback, or security impact.
- `P1`: common user flows or important edge cases.
- `P2`: low-impact or highly localized gaps.