# Contributing to FloodConnect

FloodConnect is designed for human + multi-agent collaboration. The repository uses a canonical Repo Knowledge Graph (RKG) and active semantic claims to reduce ontology drift and concurrent-write errors.

## Start here

Read:
1. `AGENTS.md`
2. `docs/AI_ENTRYPOINT.md`
3. `site/inputs/meta/floodconnect_repo_kg.yaml`

## Contribution workflow

### 1. Classify the change

**Read-only / non-semantic:** no claim normally required.

**Semantic / schema / architecture / canonical model change:** claim required.

### 2. Claim canonical nodes

Create a small claim-only PR adding:

`.ai/claims/<claim-id>.yaml`

The claim must be ACTIVE on `main` before implementation starts.

Only one ACTIVE claim may own a canonical RKG node.

### 3. Work on a fresh branch

Use:

`agent/<agent-id>/<task-slug>`

Start from the latest `main` after the claim is merged.

### 4. Preserve canonical sources

Do not create a second registry/ontology when a canonical artifact already exists.

If architecture changes, update the RKG in the same PR.

### 5. Validate locally

Run:

```bash
python3 repo_knowledge_graph.py --validate
python3 agent_claims.py --validate
python3 -m pytest -q
```

### 6. Open a PR

Use the repository PR template. Declare semantic impact explicitly.

### 7. Release ownership

After implementation is merged, change the claim status to `RELEASED` in a small follow-up PR.

## Review focus

Reviewers should look for more than code correctness:

- duplicate concepts under different names;
- schema changes not propagated downstream;
- epistemic promotion (e.g. observation -> forecast);
- RKG dependency drift;
- stale branch assumptions;
- hard constraint removal;
- proposal code presented as operational truth.

## Emergency changes

If a safety-critical operational fix cannot follow the normal workflow, keep the diff minimal, state why the claim/PR sequence was bypassed, run all available gates, and create a follow-up audit immediately. Emergency bypass is exceptional and does not redefine the normal protocol.

## Branch protection

Repository settings should protect `main` so that pull requests and required checks are mandatory. The in-repo protocol and CI can detect many violations, but repository-host branch protection is the final enforcement layer.
