# Active Semantic Claims

This directory is the persistent coordination layer for multi-agent writers.

## Why claims live on main

A claim hidden only inside an agent's feature branch is invisible to other agents. Therefore a claim is merged to `main` **before** substantive implementation starts.

## One writer per canonical node

An ACTIVE claim owns one or more canonical RKG node IDs. Two ACTIVE claims may not own the same node.

The validator:

`python3 agent_claims.py --validate`

checks:
- schema;
- claim id uniqueness;
- canonical RKG node existence;
- one ACTIVE writer per node;
- branch naming;
- SHA shape;
- status.

## Lifecycle

```text
ACTIVE -> RELEASED
```

Do not delete released claims. They are provenance.

## File naming

Use:

`YYYYMMDD-<agent-id>-<task-slug>.yaml`

Files beginning with `_` are templates and ignored by the validator.

## Minimal claim

```yaml
claim_id: "20260929-agent-a-shelter"
status: ACTIVE
writer: "agent-a"
branch: "agent/agent-a/shelter"
base_sha: "0123456789abcdef0123456789abcdef01234567"
nodes: [SOCL]
artifacts:
  - shelter_operation_ladder.py
intent: "Tighten shelter promotion invariant."
created_at: "2026-09-29T15:40:00+07:00"
reviewers: []
note: null
```

## Handoff / takeover

Never create a competing ACTIVE claim. Release or explicitly supersede the old claim first, then create/update ownership with review.
