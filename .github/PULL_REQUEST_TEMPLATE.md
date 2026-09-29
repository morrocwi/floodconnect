## Intent

Describe the change and why it is needed.

## Multi-agent ownership

- Claim id(s): 
- Canonical RKG node(s) changed:
- Branch started from current main after claim merge: [ ] yes [ ] n/a

## Semantic impact

- [ ] No new canonical concept
- [ ] Existing concept extended (describe below)
- [ ] New RKG node/edge required and included in this PR
- [ ] Canonical source-of-truth changed
- [ ] Schema changed
- [ ] Epistemic class changed
- [ ] Hard invariant changed

Details:

## Dependency impact

Downstream models/files that depend on this change:

## Epistemic check

- [ ] UNKNOWN is preserved where evidence is unresolved
- [ ] No topology/observation/forecast/warning/action laundering
- [ ] Proposal/experiment is not presented as production truth
- [ ] Tool/facility labels do not override route/site safety
- [ ] Governance roles reuse canonical actor IDs

## Validation

- [ ] `python3 repo_knowledge_graph.py --validate`
- [ ] `python3 agent_claims.py --validate`
- [ ] `python3 -m pytest -q`

## Reviewer questions

1. Does this duplicate an existing RKG node/construct under another name?
2. Does a downstream consumer still assume the old schema?
3. Did any hard constraint become weaker?
4. Is the evidence class represented accurately?
5. Is the claim ownership consistent with this diff?
