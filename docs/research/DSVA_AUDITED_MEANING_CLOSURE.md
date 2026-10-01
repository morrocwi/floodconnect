# DSVA v0.9 — Audited Meaning Closure

**Status:** proposal / executable meaning-preservation upgrade  
**Parent:** DSVA v0.8 finite retained obstruction kernel  
**Purpose:** close higher-order executable gaps exposed only after the v0.8 finite envelope, horizon, and malformed-input gates passed.

## 1. Failure evidence

The v0.8 higher-order red-team (PR #38, Actions run 36899519561) produced:

\`\`\`text
5 failed, 482 passed, 1 skipped
\`\`\`

The five failures were:

1. Python Boolean/numeric equality could alias retained-state cache keys;
2. an action whose effect time was before the decision origin could still license;
3. conflicting explicit and typed-reader proposals could be silently resolved by precedence;
4. population labels could claim multiple protected subjects while the predicate read only one subject field;
5. bare caller-supplied closure flags could support a strong license with no locked audit witness.

These failures are about executable meaning preservation and auditability. They do not by themselves establish a failure of the higher DSVA theory.

## 2. Type-stable retained distinctions

Python has:

\[
True = 1
\]

under ordinary equality. DSVA cannot inherit that coercion for a retained-information quotient.

Define a typed retained value:

\[
\tau(v)
=
(\operatorname{typeclass}(v),\operatorname{exactvalue}(v)).
\]

Finite numeric encodings such as integer, finite decimal, and rational may share the same exact rational class:

\[
\tau(1)=\tau(1.0)=\tau(1/1)=("num",1,1),
\]

while Boolean values remain distinct:

\[
\tau(True)=("bool",True)
\neq
("num",1,1).
\]

The requirement-reader quotient becomes:

\[
x\sim_{\mathcal R}x'
\iff
\sigma_{\mathcal R}^{typed}(x)
=
\sigma_{\mathcal R}^{typed}(x').
\]

This preserves the speed benefit of quotient caching without collapsing semantically distinct primitive types.

## 3. Subject-bound protected requirements

A population label is not itself a proof that a predicate protects every listed subject.

For requirement \(r\), let:

\[
P_r=Population(r).
\]

v0.9 introduces an executable subject binding:

\[
b_r:P_r\rightarrow Fields.
\]

For the strong per-subject path the binding must be total:

\[
dom(b_r)=P_r,
\]

and distinct subjects must have distinct retained fields:

\[
p\neq q
\Rightarrow
b_r(p)\neq b_r(q).
\]

The compiled requirement is then:

\[
K_r
=
\bigcap_{p\in P_r}
\left\{
x:
\phi_r\big(read_{b_r(p)}(x)\big)=true
\right\}.
\]

A legacy one-subject requirement may use one explicit field because the binding is unambiguous. A multi-subject requirement without explicit bindings is not strongly executable.

Aggregate/group semantics are not guessed. They require a separate certified adapter.

## 4. Closure audit witness

A Boolean closure value is not itself an audit trail.

For each asserted load-bearing closure \(c\), v0.9 requires:

\[
C_c
=
\langle
spec_c,
input_c,
witness_c,
checker_c
\rangle.
\]

Audit completeness is:

\[
AuditComplete_Q
=
\bigwedge_{c\in Closures_Q}
Complete(C_c).
\]

A strong executable license requires:

\[
AuditComplete_Q=1.
\]

The kernel computes a deterministic digest of the closure-audit object and returns it with post-preflight decision outputs.

Important boundary:

\[
AuditComplete
\neq
CheckerSemanticallyCorrect.
\]

v0.9 proves only that the asserted closure is tied to a locked spec/input/witness/checker record. Independent semantic validation of an external checker remains a separate obligation.

## 5. Decision-time origin

For a new action selected at decision origin \(t=0\):

\[
0
\le
t_{effect}
\le
H_Q,
\]

in addition to the existing lease and valid-until constraints:

\[
t_{issue}
\le
t_{effect}
\le
t_{expire},
\]

\[
t_{effect}
\le
validUntil_Q.
\]

A lease may have begun before the decision snapshot; the selected effect may not occur in the past.

## 6. Proposal-channel consistency

If two decision channels are both declared:

- explicit \`proposed_action\`;
- \`typed_reader.selected\`;

then v0.9 requires:

\[
Proposal_{explicit}
=
Proposal_{reader}.
\]

Otherwise:

\[
HOLD.
\]

The kernel no longer resolves a provenance contradiction by silent precedence.

## 7. v0.9 strong executable condition

Let \(\Omega_Q(a)\) be the v0.8 finite obstruction set. Then the v0.9 executable strong-license condition is:

\[
\boxed{
License_Q^{v0.9}(a)
\iff
\Omega_Q(a)=\varnothing
\land
AuditComplete_Q
\land
SubjectBindingComplete_Q
\land
ProposalConsistent_Q
\land
t_{effect}\ge0
}
\]

inside the already declared DSVA applicability envelope.

The strongest status remains:

\`\`\`text
LICENSED_WITHIN_ENVELOPE
\`\`\`

and still does not mean universal real-world safety.

## 8. What remains open

This upgrade intentionally does not solve:

- whether raw evidence generated the correct admissible-world set;
- whether an external closure checker is semantically correct;
- whether a domain transition model is true;
- whether a continuous physical trajectory is safe between retained samples;
- whether an aggregate/group requirement has been faithfully compiled without a domain-specific adapter.

Therefore:

\[
AuditedExecutableClosure
\neq
UniversalTruth.
\]

The next falsification target should attack independently verified closure checkers and requirement adapters rather than merely malformed JSON.
