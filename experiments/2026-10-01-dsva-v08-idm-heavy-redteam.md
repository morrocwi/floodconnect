# DSVA v0.8 — IDM-Informed Heavy Red-Team and Repair Audit

**Date:** 2026-10-01  
**Status:** experiment / executable conformance audit  
**Anchor:** DSVA v0.7 executable model on FloodConnect main before this upgrade  
**v0.7 failure evidence:** PR #34, GitHub Actions run 36894785288  
**v0.8 implementation:** PR #36  
**IDM source:** `morrocwi/information-discrete-math` (operator-level reuse only)

## 1. Baseline failure

The v0.7 adversarial PR deliberately added fail-closed obligations that the executable did not yet implement. GitHub Actions reported:

```text
12 failed, 453 passed, 1 skipped
```

The repository architecture and semantic-claim validators passed; the failures were in the new executable red-team cases.

The established v0.7 failures were:

1. empty disturbance set could vacuously license;
2. action outside the declared actuation envelope could license;
3. checked disturbances could be smaller than the declared disturbance envelope;
4. a short trace could be licensed for a longer decision horizon;
5. action effect could occur after the question horizon;
6. action effect could occur after `validUntil`;
7. an unknown information status could be treated as supported;
8. duplicate action identifiers could produce an ambiguous decision state rather than fail closed;
9. protected-population coverage could be incomplete while the action licensed;
10. an unsupported requirement operator could escape as an exception;
11. a requirement type mismatch could escape as an exception;
12. a malformed outcome branch could escape as an exception.

These are implementation/formalization-bridge failures. They do not by themselves refute the higher DSVA theory.

## 2. IDM-informed repair principle

The sibling Information Discrete Mathematics repository was read using its own review/discovery order. The DSVA upgrade reuses only the following operator-level ideas:

- finite retained readout first;
- declare the finite resolution before computing;
- exact rational arithmetic where the decision domain permits it;
- fail-closed verdict discipline;
- reader-equivalence quotienting;
- explicit finite cost ledger.

No IDM runtime dependency or parallel ontology is introduced.

## 3. v0.8 finite obstruction kernel

For action `a` define:

\[
\Omega_Q(a)
=
\Omega_{scope}
\cup
\Omega_{closure}
\cup
\Omega_{lease}
\cup
\Omega_{actor-info}
\cup
\Omega_{coverage}
\cup
\Omega_{trace}
\cup
\Omega_{requirement}.
\]

The finite executable license rule is:

\[
\boxed{
License_Q(a)
\iff
\Omega_Q(a)=\varnothing
}
\]

after the existing DSVA information/envelope gates pass.

Every load-bearing universal axis must first be explicitly non-empty. Therefore the mathematical fact

\[
\forall x\in\varnothing:P(x)
\]

cannot silently become a safety license.

## 4. Retained decision time

v0.8 declares a retained decision resolution:

\[
\lambda_Q>0
\]

and finite grid

\[
T_Q^\lambda
=
\{0,\lambda,2\lambda,\ldots,H_Q\},
\qquad
H_Q/\lambda_Q\in\mathbb N.
\]

Horizon, resolution, lease issue/expiry/effect, and `validUntil` are read as exact rational values. A discrete-retained trace must cover the complete declared grid.

This is an exact finite trace contract. It is not a proof of continuous inter-sample safety.

## 5. Retained-reader quotient

Let the compiled protected-requirement reader observe only the fields actually used by the requirements:

\[
\sigma_{\mathcal R}(x)
=
(read_{r_1}(x),\ldots,read_{r_m}(x)).
\]

Define:

\[
x\sim_{\mathcal R}x'
\iff
\sigma_{\mathcal R}(x)
=
\sigma_{\mathcal R}(x').
\]

For the compiled executable reader, equal signatures imply equal requirement readouts. Therefore requirement predicates are evaluated once per retained state class.

Repeated trajectories may similarly be represented as named retained trace classes through `trace_library` and `trace_ref`. Every world × disturbance branch is still checked for coverage; a shared trace class is semantically evaluated once.

## 6. Test battery added to v0.8

The implementation PR contains four layers of executable tests:

### A. direct regression

The original 12 v0.7 failures are retained as regression obligations.

Additional direct attacks include:

- non-Boolean model-invalidated flag;
- missing trace semantics;
- missing/zero trace resolution;
- horizon off the declared resolution grid;
- mixed explicit/implicit trace time;
- non-monotone trace time;
- invalid typed-reader confidence.

### B. deterministic mutation stress

`tests/test_dsva_decision_v08_redteam.py` executes **10,000 single-fault scenario mutations** in CI. Every mutated case must return a non-licensed status and no selected action.

### C. metamorphic tests

`tests/test_dsva_decision_v08_metamorphic.py` checks properties that should be invariant under representational changes:

- inline trace vs `trace_ref`;
- permutation of worlds / requirements / actions;
- adding state fields invisible to the protected reader;
- reader-confidence changes cannot override a hard gate;
- decimal and exact-rational encodings of the same decision time agree;
- 1,000 repeated evaluations of the same snapshot are deterministic.

### D. independent finite oracle

`tests/test_dsva_decision_v08_differential.py` generates **5,000 deterministic random finite scenarios** and compares the optimized kernel with a separate direct enumeration oracle.

The optimization is accepted only when the action-license readout agrees with the direct finite check.

## 7. Finite-work stress witness

The v0.8 red-team includes a retained-trace stress case with:

```text
W = 128 worlds
D = 8 disturbances
H = 32 retained steps
R = 8 protected requirements
```

A naive repeated predicate evaluation would contain:

\[
128\times8\times33\times8
=
270{,}336
\]

predicate obligations.

All 1,024 world × disturbance branches still undergo branch-coverage checks. When they point to the same certified retained trace class, the kernel test requires:

```text
branches_checked = 1024
traces_checked   = 1
trace_cache_hits = 1023
predicates_checked = 8
```

This is a finite work ledger for this constructed case, not a universal wall-clock speed claim.

An additional out-of-CI development stress used:

```text
W=256, D=8, H=64, R=16
```

for a naive count of:

\[
256\times8\times65\times16
=
2{,}129{,}920
\]

predicate obligations versus 16 protected predicates for one repeated retained-state class. The corresponding compression factor for that deliberately repeated case is:

\[
\frac{2{,}129{,}920}{16}
=
133{,}120.
\]

This is an exact ledger-derived work reduction for that synthetic equivalence-class case. It must not be presented as a universal runtime speedup.

## 8. Development fuzz result

Before integration, an executable prototype was stress-tested with **100,000 single-fault adversarial evaluations** covering the repaired failure families. No mutated case reached `LICENSED_WITHIN_ENVELOPE`.

This is evidence over the tested finite mutation space, not proof of correctness.

## 9. What remains deliberately open

v0.8 closes executable conformance holes but does not collapse higher theory obligations into booleans.

Still open / external to this kernel:

1. **raw evidence -> admissible worlds:** the executable does not independently construct the correct \(\mathbb B_t\) from raw heterogeneous evidence;
2. **transition truth:** caller-supplied finite trajectories are not proof that the physical transition model is true;
3. **requirement semantic compilation:** explicit population metadata proves executable coverage, not that a natural-language human requirement was translated without semantic loss;
4. **closure certificates:** first- and second-order closure values are checked strictly but are still supplied by an upstream verifier;
5. **continuous inter-sample safety:** `discrete_retained` covers retained states; a continuous-domain adapter needs a certified reach-tube/interval contract;
6. **independent verifier independence:** the executable does not yet establish process/tool independence of every supplied certificate.

Therefore:

\[
\boxed{
ExecutableConformance
\neq
WorldTruth
}
\]

and:

\[
\boxed{
NoFiniteObstructionFound
\neq
NoPossibleRealWorldFailure
}
\]

## 10. Current falsification target

After the original 12 failures are closed, the next valuable attack is not merely malformed input. It is to construct a case where:

- the finite obstruction kernel passes;
- every supplied closure certificate is independently valid;
- the retained trace coverage is complete for the declared finite semantics;
- the requirement compiler is semantically certified;
- the actor-local policy is realizable;
- the action is inside lease/horizon/envelope;

yet the licensed action is still wrong **inside the declared envelope**.

Failure should be reported before repair.

If none is found:

> No higher-order counterexample was found within the tested adversarial space.

Never promote that statement to universal correctness.
