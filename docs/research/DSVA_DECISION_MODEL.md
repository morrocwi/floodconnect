# DSVA v0.7 Executable Disaster Decision Model

**Status:** proposal / executable reference model  
**Anchor:** DSVA v0.7 standalone, with the FloodConnect v0.6 repository state at `affd07ead02df0fc5d9b8bd8ab6f72ce57b6978c` as constitutional baseline.  
**Purpose:** turn finite, declared disaster evidence/state scenarios into auditable action-license outputs without replacing hazard models or DSVA theory.

## 1. Research-facing object

For question `Q` and only the information available at decision time:

\[
D_Q(E_{\\le t},Q)
\\rightarrow
(A^*,status,H,\\mathcal E_t^Q,validUntil,provenance).
\]

The reference implementation does not claim to infer the whole physical world. It enumerates a finite set of admitted worlds/disturbances supplied by the caller, checks protected requirements over each declared trace, enforces actor-local information and action leases, and returns a DSVA status.

The implementation therefore exposes one operational reduction of the theory:

\[
\\boxed{
DecisionModel_Q
=
Gate(
ReaderProposal,
FOC_t^Q,
\\mathfrak M_t^Q,
TraceSafety,
ActorLocalRealizability,
Verify,
Lease
)
}
\]

## 2. What it is not

It is not:

- a rainfall, flood-depth, earthquake, wildfire, epidemic, or infrastructure forecast model;
- a replacement for FloodConnect live-source ingestion;
- a claim that a finite enumerated scenario covers all physically possible worlds;
- a rule that confidence can override hard safety constraints.

A Jev-style `Choice`/`Score`/`Noul`, an LLM, a rule engine, or a human can act as a typed reader. The reader proposes or ranks an action. DSVA decides whether that action is licensed inside the declared envelope.

\[
P_{reader}(safe)=0.99
\\not\\Rightarrow
LicensedAction.
\]

## 3. Executable input

A scenario JSON contains:

- `question`: reader/task and horizon;
- `envelope`: declared domain, population, model/disturbance/observation/actuation scope;
- first-order and second-order closure flags;
- `worlds`: finite admissible worlds for this test;
- `disturbances`: finite admitted disturbance branches;
- `requirements`: protected-state predicates;
- `actor_information`: information actually available to each executing actor;
- `actions`: candidate actions, leases, and finite outcome traces;
- optional `typed_reader` / `proposed_action`.

## 4. Decision rule

An action is admitted into the finite viable action set only if all of the following are true:

1. all required DSVA closures pass;
2. its effect occurs within its action lease;
3. every declared actor has the information the action branch actually requires;
4. an outcome trace exists for every admitted world × disturbance branch;
5. every state on every declared trace satisfies every protected requirement.

If a typed reader proposes an action, the model licenses it only when the action is in this verified set. Reader confidence is retained as provenance but does not relax a failed gate.

## 5. Status semantics

The executable returns only the DSVA strong-status family:

```text
LICENSED_WITHIN_ENVELOPE
CONDITIONAL
LOCAL/PARTIAL
UNRESOLVED
CONTRADICTION
INVALIDATED
HOLD
```

The finite reference implementation currently emits `LICENSED_WITHIN_ENVELOPE`, `LOCAL/PARTIAL`, `UNRESOLVED`, `CONTRADICTION`, `INVALIDATED`, and `HOLD`. `CONDITIONAL` remains reserved for adapters that explicitly retain an unresolved external assumption.

## 6. Run

```bash
python3 dsva_decision.py examples/dsva_decision_minimal.json
python3 -m pytest -q tests/test_dsva_decision.py
```

The example is synthetic. It is not an operational flood instruction.

## 7. Academic evaluation path

A paper can compare the same anti-hindsight input snapshots under:

- fixed threshold/rule baseline;
- direct LLM recommendation;
- typed decision reader such as Jev;
- DSVA decision licensing around the same reader.

Candidate outcome measures include unsafe-action rate, unsupported-action rate, appropriate abstention, scope violation, decision traceability, actor-local realizability failures, and sensitivity to evidence removal/addition.

The key research question is:

> Given only the information available at decision time, which disaster-response actions are actually justified within the declared envelope?
