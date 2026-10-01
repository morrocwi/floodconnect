# DSVA v0.9 — Higher-Order Red-Team and Audited Meaning Repair

**Date:** 2026-10-02  
**Status:** experiment / executable meaning-preservation audit  
**v0.8 failure evidence:** draft PR #38, Actions run 36899519561  
**v0.9 implementation:** PR #40  
**Theory anchor:** DSVA / Toledo / FloodConnect; v0.8 finite retained obstruction kernel remains load-bearing

## 1. Higher-order failure evidence

After the v0.8 kernel passed the original 12 conformance failures, a new red-team attacked cases where the finite obstruction machinery itself passed but the meaning carried through the implementation could still be wrong.

GitHub Actions on the test-only v0.8 higher-order PR reported:

\`\`\`text
5 failed, 482 passed, 1 skipped
\`\`\`

The five counterexamples were:

### HO-01 — typed retained-state alias

Python treats \`True == 1\`. The v0.8 cache key inherited enough Python equality behavior that a Boolean retained state could alias a numeric state in a numeric requirement reader.

Failure class: implementation/formalization bridge.

### HO-02 — effect before decision origin

A lease could begin in the past and the selected action effect could also occur in the past while satisfying:

\[
issue\le effect\le expire.
\]

Failure class: temporal scope.

### HO-03 — conflicting proposal channels

When both \`proposed_action\` and \`typed_reader.selected\` were present and disagreed, v0.8 used precedence rather than treating the conflict as an epistemic/provenance obstruction.

Failure class: scope/provenance preservation.

### HO-04 — population-label semantic spoof

A requirement could declare:

\`\`\`text
population = [A, B]
field = A_safe
\`\`\`

and thereby satisfy executable population coverage even though the predicate observed no B-specific retained field.

Failure class: requirement semantic compilation.

### HO-05 — unaudited closure flags

All first- and second-order closure values could be supplied as bare \`true\` values without a locked spec/input/witness/checker record.

Failure class: closure auditability.

## 2. v0.9 mathematical repairs

### 2.1 Type-stable retained value

Define:

\[
\tau(v)
=
(typeclass(v),exactvalue(v)).
\]

The important distinction is:

\[
\tau(True)\neq\tau(1),
\]

while exact finite numeric representations may share a rational class:

\[
\tau(1)=\tau(1.0)=\tau(1/1).
\]

The reader-equivalence quotient now uses \(\tau\).

### 2.2 Subject-bound requirement compilation

For protected requirement \(r\):

\[
b_r:Population(r)\to Fields.
\]

The strong per-subject path requires:

\[
dom(b_r)=Population(r)
\]

and:

\[
p\ne q\Rightarrow b_r(p)\ne b_r(q).
\]

The executable requirement becomes:

\[
K_r
=
\bigcap_{p\in Population(r)}
\{x:\phi_r(read_{b_r(p)}(x))\}.
\]

A legacy single-subject field is still unambiguous. A multi-subject requirement without explicit bindings is held.

### 2.3 Closure audit witness

For every asserted closure \(c\):

\[
C_c
=
\langle spec,input,witness,checker\rangle.
\]

Strong executable licensing requires all asserted closures to have complete records.

The audit object is serialized canonically and assigned a SHA-256 digest returned with post-preflight decision outputs.

Boundary:

\[
AuditComplete\neq CheckerCorrect.
\]

### 2.4 Decision-time origin

v0.9 adds:

\[
t_{effect}\ge0.
\]

The existing lease/horizon/valid-until constraints remain.

### 2.5 Proposal consistency

If both proposal channels are present:

\[
Proposal_{explicit}
=
Proposal_{reader}.
\]

Otherwise the result is \`HOLD\`.

## 3. v0.9 executable strong condition

Let \(\Omega_Q(a)\) be the v0.8 finite obstruction set. v0.9 refines the executable condition to:

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

inside the declared DSVA envelope.

## 4. Regression battery

The v0.9 implementation includes the complete v0.8 battery plus:

- direct regressions for all five HO failures;
- correct two-subject binding witness;
- duplicate-field binding rejection;
- each missing closure-audit field;
- deterministic closure-audit digest;
- strict Boolean vs numeric equality;
- **10,000 typed-alias / audit / temporal / proposal / binding mutations**.

The prior v0.8 battery remains:

- original 12 fail-closed regressions;
- 10,000 v0.8 single-fault mutations;
- 5,000 differential cases against a separate direct finite oracle;
- metamorphic representation-invariance checks;
- 1,000-repeat determinism;
- retained trace/state quotient stress.

## 5. Integration result before this report-only commit

GitHub Actions run 36900595046 passed:

\`\`\`text
RKG validation                 PASS
active semantic claims        PASS
full regression               493 passed, 1 skipped in 6.91s
\`\`\`

The report-only commit must still pass the same repository gates before merge.

## 6. What is stronger now

The model no longer only asks whether all finite branches were enumerated. It also constrains whether the retained values, protected subjects, proposal provenance, and closure records preserve the meaning required by the decision reader.

The executable chain is now better described as:

\[
Snapshot
\to
AuditedClosures
\to
TypedRetainedQuotient
\to
SubjectBoundRequirements
\to
FiniteObstructionCheck
\to
ScopedLicense.
\]

## 7. What remains open

The following remain intentionally unresolved rather than hidden:

1. an audit record does not prove that an external checker is semantically correct;
2. the kernel does not independently derive the admissible-world set from raw disaster evidence;
3. the kernel does not prove that the supplied transition model is physically true;
4. \`discrete_retained\` semantics does not prove continuous inter-sample safety;
5. aggregate/group protected requirements need a domain-specific certified adapter;
6. independent checker/tool diversity is not yet machine-enforced.

Therefore:

\[
\boxed{
AuditedExecutableConformance
\neq
WorldTruth
}
\]

and:

\[
\boxed{
ClosureWitnessPresent
\neq
ClosureWitnessValid
}
\]

## 8. Next falsification target

The next attack should supply apparently complete closure witnesses and then try to demonstrate that:

- the checker is circular, correlated, or checks the wrong specification;
- the requirement adapter preserves syntax but not domain meaning;
- the finite world set is internally closed but misses a material world still inside the declared envelope;
- the retained discrete trace is safe while the certified continuous adapter is wrong.

Failure must be recorded before repair.

If none is found within a declared tested space, the allowed conclusion is only:

> No higher-order counterexample was found within the tested adversarial space.
