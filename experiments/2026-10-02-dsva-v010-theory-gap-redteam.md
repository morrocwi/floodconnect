# DSVA v0.10 — Theory-Gap Red-Team and Executable Projection Audit

**Date:** 2026-10-02  
**Status:** experiment / executable conformance audit  
**Failure evidence:** draft PR #42  
**Implementation:** PR #44  
**Theory anchor:** DSVA_SECOND_ORDER_LICENSE.md and DSVA_INFORMATION_CONTRACT_BRIDGE.md

## 1. Failure before repair

The test-only v0.9 theory-gap red-team deliberately exercised obligations already present in DSVA theory but not yet load-bearing in the executable model.

Final pre-repair run:

~~~text
GitHub Actions run 36902928503

9 failed
493 passed
1 skipped
8.98 s
~~~

The nine failures were:

1. verification certificate not bound to the actual spec/input snapshot;
2. checker could share producer implementation/failure lineage;
3. disjoint finite model/observed behavior sets could still license;
4. two evidence sources with one calibration ancestor could still be claimed independent;
5. protected-requirement horizon/coverage ledger could be shorter than the decision claim;
6. future observation policy could omit an admitted CHANNEL_DOWN branch;
7. candidate action could overbook a globally declared resource;
8. compound hazard components could be factorized without a factorization license;
9. commanded action could be treated as realized without verification/bounds/runtime revalidation.

The red-team PR remains unmerged so the failure evidence is preserved.

## 2. Repair mapping to existing theory

No new root ontology was created.

The repair maps directly to existing second-order DSVA clauses:

| Theory obligation | v0.10 executable projection |
|---|---|
| SOL-09 model invalidation | finite retained model/observed behavior-set intersection |
| SOL-12–14 evidence dependency | declared lineage intersection for explicit independence claims |
| SOL-15 global resource reservation | exact rational candidate-action resource bound |
| SOL-17 compound-hazard factorization | explicit factorization license |
| SOL-20ff observation-policy realizability | total response map over admitted future observation outcomes |
| execution closure | VERIFIED/BOUNDED realized actuation + runtime revalidation |
| SOL-35 requirement ledger | function/constraint/threshold/horizon/provenance/coverageStatus |
| SOL-39 verification | SHA-256 binding to canonical finite spec/input + declared independent checker |

## 3. Finite verification binding

The kernel defines finite canonical projections:

\[
Spec_Q^f
\]

and:

\[
Input_Q^f.
\]

It computes:

\[
d_S=SHA256(Canon(Spec_Q^f)),
\qquad
d_I=SHA256(Canon(Input_Q^f)).
\]

A strong finite verification contract must carry exactly those digests.

This prevents a certificate for one task/input from being silently reused for another.

The checker must also be declared distinct from the producer by identity, implementation digest and failure lineage, with disjoint declared lineages.

Boundary:

\[
DeclaredIndependentChecker
\neq
ProvenIndependentChecker.
\]

## 4. Preserved IDM acceleration

The repair keeps the v0.8 retained quotient and adds only finite contract work.

The cost ledger now includes:

~~~text
contract_checks
digest_checks
lineage_checks
~~~

in addition to branch, trace, state, predicate and exact-time counts.

No declared world/disturbance branch is skipped.

## 5. Regression battery

The implementation keeps:

- 10,000 v0.8 single-fault mutations;
- 5,000 differential scenarios against a separate direct finite oracle;
- metamorphic representation-invariance tests;
- 1,000-repeat determinism;
- 10,000 v0.9 typed-alias/audit/binding/proposal mutations;
- retained trace/state quotient stress;

and adds:

- direct regressions for all nine v0.9 theory-gap failures;
- positive applicability/dependency/resource/factorization/verification cases;
- **10,000 v0.10 theory-contract mutations**.

A pre-documentation implementation run already passed:

~~~text
GitHub Actions run 36904278582
507 passed, 1 skipped in 14.13 s
~~~

The final documentation/RKG head must pass the same repository gates before merge.

## 6. What v0.10 still does not execute

The model is much closer to the theory but two large theory objects remain only partially projected.

### A. Full adaptive policy execution

The theory's central policy object is:

\[
\pi_k:I_k^{admitted}\to U_k^{feasible}.
\]

v0.10 verifies totality of a declared future observation response map, but it does not yet execute a full actor-local multi-step policy tree over every admitted observation history.

### B. Persistent recovery execution

The theory requires a persistent return set, not one instantaneous safe state.

v0.10 still relies on the existing closure/audit plus finite trace requirements rather than a dedicated finite controlled-invariant return-set solver.

These are the next red-team targets.

Therefore:

\[
\boxed{
ExecutableTheoryContractClosure
\neq
FullTheoryExecution
\neq
WorldTruth.
}
\]
