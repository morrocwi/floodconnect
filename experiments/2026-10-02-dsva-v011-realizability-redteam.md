# DSVA v0.11 — Finite Realizability Red-Team and Repair Audit

**Date:** 2026-10-02  
**Status:** experiment / executable realizability audit  
**Failure evidence:** draft PR #46  
**Implementation:** v0.11 implementation branch  
**Theory anchor:** DSVA SOL-20..28

## 1. Pre-repair failure

The v0.10 realizability red-team attacked the remaining gap in \(M_Z\): the executable accepted a total future-response string map but did not require that responses be real actor-local policy nodes, and it did not execute persistent recovery or load-bearing assume-guarantee realizability.

GitHub Actions run 36905308893 reported:

~~~text
7 failed
507 passed
1 skipped
13.77 s
~~~

The seven failures were:

1. future response token not bound to a real policy node;
2. future action outside the actuation envelope;
3. future actor using an observation delivered to another actor;
4. future observation used before arrival;
5. load-bearing contract assumption unrealizable on an admitted branch;
6. recovery touching the return condition at one instant only;
7. cyclic/non-forward finite policy graph.

Failure evidence remains in draft PR #46 and is not merged.

## 2. Repair

v0.11 adds a finite adaptive policy witness:

\[
P=(N,E,n_0).
\]

Each reachable node checks:

\[
action_n\in\mathcal U^{feasible},
\]

\[
ReqInfo_n\subseteq InfoAvailable(actor_n,t_n,path_n),
\]

and anti-hindsight:

\[
t_{obs}>t_n,
\qquad
t_{child}\ge t_{obs}.
\]

Future observation responses are no longer arbitrary strings. The root response map must equal the finite outcome-to-child-node map.

Load-bearing contracts used by an action require:

\[
A_c(w,d)\land G_c(w,d)
\]

for every admitted finite world × disturbance branch.

Persistent recovery requires the declared recovery readout to remain satisfied at every retained grid point in:

\[
[t_{return},t_{return}+H_R].
\]

Thus:

\[
Touch(\mathcal K)\neq Recovered.
\]

## 3. Preserved acceleration

The repair does not remove the retained-state/trace quotient. It adds finite graph/contract/recovery checks while preserving exact rational timing and the existing cost ledger.

The operational rule remains:

\[
DoNotSkipDeclaredBranches;
\quad
ReuseOnlyReaderEquivalentWork.
\]

## 4. Regression plan

The v0.11 suite keeps all v0.8-v0.10 tests and adds:

- direct regressions for all seven PR #46 failures;
- positive finite adaptive-policy witness;
- positive load-bearing boundary contract;
- positive persistent recovery;
- **10,000 realizability mutations** across policy binding, action envelope, actor-local delivery, anti-hindsight, boundary assumptions, transient recovery and cyclic policy structure.

Final integration results must be recorded from GitHub Actions before merge.

## 5. Boundary

This is a finite witness checker for DSVA realizability. It is not:

- an optimal-policy synthesizer;
- an unbounded/open-world POMDP solver;
- proof that a supplied boundary witness matches physical reality;
- proof of continuous safety between retained samples;
- proof that upstream admissible-world construction is complete.

Therefore:

\[
\boxed{
FiniteRealizabilityWitness
\neq
UniversalRealizability.
}
\]
