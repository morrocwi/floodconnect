# FloodConnect Multi-Agent Protocol

> Mandatory for every AI/agent that reads or writes this repository.
>
> Goal: keep FloodConnect multi-agent **write-safe**, not merely easy to understand.

## 1. Boot order

Before changing anything, read in this order:

1. `AGENTS.md` (this file)
2. `docs/AI_ENTRYPOINT.md`
3. `site/inputs/meta/floodconnect_repo_kg.yaml`
4. the `question_routes` / canonical artifacts for your task
5. `.ai/claims/README.md`

Do not scan-and-invent a parallel ontology.

## 2. Main is integration state

Agents MUST NOT treat `main` as a personal working branch.

Normal work happens on:

`agent/<agent-id>/<task-slug>`

A branch must start from the current `main` head for the task.

## 3. Claim before substantive writing

If a task can change the meaning, schema, invariant, implementation, or source-of-truth of one or more canonical RKG nodes, create a **claim-only PR first**.

Claim file:

`.ai/claims/<claim-id>.yaml`

The claim must be merged to `main` before substantive implementation begins. This makes ownership visible to every other agent.

A claim declares:
- one writer identity;
- branch;
- base SHA;
- canonical RKG nodes owned for the task;
- intended artifacts;
- intent;
- optional reviewers / expiry.

### One active writer per canonical node

For every canonical RKG node `n`:

[
\left|\{c: c.status=ACTIVE \land n\in c.nodes\}\right| \le 1
]

Many reviewers are allowed. Multiple active writers are not.

If another ACTIVE claim already owns a node, do not redefine or mutate that node. Review, coordinate, or wait for claim release.

## 4. File ownership is not enough

Semantic ownership is by **canonical node**, not file path.

Example: a task touching `SOCL` may modify:
- `shelter_operation_ladder.py`
- `site/inputs/community/sustainment_policy.yaml`
- `docs/SHELTER_OPERATION_CAPABILITY_LADDER.md`

A second agent must not redefine SOCL merely because it edits a different file.

## 5. Read-only and low-risk work

A claim is not required for:
- read-only analysis;
- typo-only documentation fixes with no semantic change;
- adding evidence that does not alter a canonical node/schema;
- tests that only increase coverage without changing semantics.

When uncertain, claim.

## 6. Canonical extension rule

Before adding any node, construct, registry, role, or source-of-truth:

1. check the RKG;
2. check the canonical artifact for the closest node;
3. prefer an attribute / role overlay / capability edge on an existing node;
4. only create a new construct if extension is not semantically correct;
5. update the RKG in the same implementation PR when architecture changes.

## 7. Epistemic invariants

Never violate:
- UNKNOWN != SAFE
- topology != forecast
- observation != forecast != warning != instruction != action
- movement graph != support/lifeline graph
- tool/facility type != route/site safety
- tool capability never overrides Dry Gate
- proposal/experiment != production truth
- role overlay != duplicate actor identity

## 8. Implementation PR requirements

Every substantive PR must state:
- active claim id(s), if required;
- canonical RKG nodes changed;
- source-of-truth artifacts changed;
- dependency edges added/removed;
- epistemic class changes, if any;
- hard invariants affected;
- tests run;
- whether RKG changed.

Use `.github/PULL_REQUEST_TEMPLATE.md`.

## 9. Integration gates

Before merge:

`python3 repo_knowledge_graph.py --validate`

`python3 agent_claims.py --validate`

`python3 -m pytest -q`

All must pass.

A task-specific test passing is insufficient if full regression fails.

## 10. Claim lifecycle

Typical sequence:

```text
current main
   ↓
claim-only branch / PR
   ↓
claim merged ACTIVE
   ↓
fresh implementation branch from updated main
   ↓
implementation PR + full gates
   ↓
merge
   ↓
release-claim PR (status: RELEASED)
```

Do not delete the claim file. Mark it `RELEASED` so provenance remains visible.

## 11. Stale claims

An ACTIVE claim may include `expires_at`. Expiry does not silently transfer ownership.

A new writer may take over only after:
- the old claim is explicitly RELEASED or superseded through a reviewed claim update;
- the new branch is rebased/restarted from current main;
- the handoff is recorded in the claim note.

## 12. Conflict classes

Treat these separately:

- **text conflict** — Git detects overlapping lines;
- **schema conflict** — two changes disagree about fields/shape;
- **semantic conflict** — different files redefine the same concept;
- **epistemic conflict** — one change silently promotes evidence class;
- **dependency conflict** — downstream code still assumes old schema.

No textual conflict does **not** imply safe merge.

## 13. Handoff

When handing work to another agent, provide:
- claim id;
- current branch and head SHA;
- RKG nodes touched;
- files changed;
- tests/status;
- unresolved assumptions;
- explicit next step.

The receiving agent rereads the current canonical files; it must not rely only on the handoff summary.
