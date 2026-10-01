# DSVA v0.8 — Finite Retained Obstruction Kernel

**Status:** proposal / executable reference kernel  
**Parent:** DSVA theory + DSVA_DECISION_MODEL  
**IDM reuse:** operator-level reuse only from `morrocwi/information-discrete-math`; no runtime dependency and no new root ontology.

## 1. Why v0.8 exists

The v0.7 heavy red-team found 12 executable conformance failures even though the higher DSVA theory already contained most of the missing distinctions. The failures included vacuous licensing on an empty disturbance set, action licensing outside the actuation envelope, horizon truncation, action effect after the decision horizon / `validUntil`, unknown information status treated as supported, protected-population coverage gaps, and malformed input crashing rather than failing closed.

The repair is not another hazard model. It is a tighter finite decision kernel.

## 2. IDM-informed mathematical reduction

Information Discrete Mathematics starts from a finite retained readout, declares a resolution, computes at finite resolution, carries a fail-closed verdict, and exposes a cost ledger. DSVA v0.8 reuses those operators inside the existing DSVA decision model.

For decision question `Q`, declare:

\[
\lambda_Q > 0
\]

and a finite retained time grid

\[
T_Q^\lambda = \{0,\lambda,2\lambda,\ldots,H_Q\},
\qquad H_Q/\lambda_Q\in\mathbb N.
\]

The finite obligation universe for an action is generated from:

\[
W_Q^f \times D_Q^f \times T_Q^\lambda \times \mathcal R_Q^f.
\]

Before the universal check is allowed, every load-bearing axis must be explicitly non-empty. This prevents vacuous safety:

\[
\forall x\in\varnothing:P(x)
\]

from ever becoming a decision license.

For an action `a`, define a finite obstruction set:

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

The executable rule is:

\[
\boxed{
License_Q(a)
\iff
\Omega_Q(a)=\varnothing
}
\]

subject to the existing DSVA envelope, verification, and epistemic-status rules. The strongest returned status remains:

```text
LICENSED_WITHIN_ENVELOPE
```

—not universal safety.

## 3. Exact finite time / envelope checks

Decision time, horizon, trace resolution, lease issue/expiry/effect, and `validUntil` are read as exact rational values using `fractions.Fraction`.

A strong action therefore requires, at minimum:

\[
issue(a)\le effect(a)\le expire(a),
\]

\[
effect(a)\le H_Q,
\]

\[
effect(a)\le validUntil_Q,
\]

and every retained trace must start at zero, lie on the declared \(\lambda_Q\) grid, be strictly increasing, and end exactly at \(H_Q\).

This closes the v0.7 endpoint-only / horizon-stripping gap for the finite retained semantics. It still does **not** prove continuous inter-sample safety. A continuous-domain adapter must provide its own certified reach-tube / interval contract before it can be represented as a retained trace.

## 4. Protected requirement coverage

Each executable protected requirement now carries an explicit `population` field. Let:

\[
P_Q^{decl}
\]

be the declared protected population and

\[
P_Q^{req}
=
\bigcup_{r\in\mathcal R_Q} Population(r).
\]

Then:

\[
P_Q^{decl}\setminus P_Q^{req}\neq\varnothing
\Rightarrow
LOCAL/PARTIAL.
\]

This is still a **syntactic / executable coverage certificate**, not a proof that a natural-language human requirement was semantically compiled correctly. That upstream semantic obligation remains part of DSVA theory.

## 5. Retained-state quotient for speed

The requirement reader only observes the fields named by the compiled requirements. Define:

\[
\sigma_{\mathcal R}(x)
=
\big(
read_{r_1}(x),\ldots,read_{r_m}(x)
\big).
\]

Then:

\[
x\sim_{\mathcal R}x'
\iff
\sigma_{\mathcal R}(x)=\sigma_{\mathcal R}(x').
\]

Because every compiled requirement predicate is a function only of this signature:

\[
x\sim_{\mathcal R}x'
\Rightarrow
ReqOK(x)=ReqOK(x').
\]

Therefore the kernel evaluates the requirement predicate set once per retained state class and caches the result. This is a DSVA/Toledo-compatible reader quotient, not an approximation.

## 6. Retained trace classes

A scenario may supply:

```json
"trace_library": {
  "safe_profile": [...]
}
```

and a branch may use:

```json
{"trace_ref": "safe_profile"}
```

instead of copying the same trace into every world × disturbance branch.

If `L` unique retained trace classes cover `W×D` branches, branch coverage is still checked for every branch but trace semantics need be evaluated only once per class.

The useful cost decomposition becomes:

\[
O(AWD) + O(LNT) + O(KR),
\]

where:

- `A` = candidate actions,
- `W` = admitted worlds,
- `D` = admitted disturbances,
- `L` = unique retained trace classes,
- `N` = retained time points per trace,
- `K` = unique protected-readout state signatures,
- `R` = protected requirements.

The kernel reports the actual finite work in `cost_ledger`; performance claims should use that ledger and a reproduced wall-clock benchmark separately.

## 7. Fail-closed boundary

Malformed caller data must not become either an exception escaping the decision service or a silent license.

The kernel therefore maps malformed/unreadable conditions to `HOLD`, `UNRESOLVED`, `LOCAL/PARTIAL`, `CONTRADICTION`, or `INVALIDATED` as appropriate.

Examples:

```text
empty disturbance set        -> HOLD
unknown information status   -> HOLD
unsupported requirement op   -> HOLD
malformed branch             -> HOLD
population coverage gap      -> LOCAL/PARTIAL
model invalidated            -> INVALIDATED
information contradiction    -> CONTRADICTION
```

## 8. Scope boundary

v0.8 is still a finite action-license checker:

\[
\boxed{
CallerSuppliedSnapshot
\rightarrow
FiniteRetainedObstructionCheck
\rightarrow
ScopedDecisionStatus
}
\]

It does not yet infer the full admissible-world set from raw evidence, prove the transition model, or prove natural-language requirement compilation. Those remain separate DSVA obligations and are intentionally not hidden inside this kernel.
