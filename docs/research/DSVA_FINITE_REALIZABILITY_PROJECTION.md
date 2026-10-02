# DSVA v0.11 — Finite Realizability Projection

**Date:** 2026-10-02  
**Status:** proposal / executable projection of DSVA SOL-20..28  
**Parent:** DSVA v0.10 executable theory-contract projection  
**Canonical theory:** \`DSVA_SECOND_ORDER_LICENSE.md\`, §6; \`DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md\`, §10D.3–10D.4  
**Rule:** no new root ontology. This file makes the existing Realizability closure \(M_Z\) more fully executable over finite declared objects.

---

## 1. Failure evidence

The v0.10 executable already enforced finite applicability, dependency, execution, requirement and verification contracts, but its observation-policy test only required a total string map. It did not prove that the response strings denoted executable future policy nodes; it also did not execute load-bearing assume-guarantee realizability or persistent recovery.

The test-only red-team in draft PR #46 produced:

\`\`\`text
GitHub Actions run 36905308893

7 failed
507 passed
1 skipped
13.77 s
\`\`\`

The seven failures were:

1. total future-response strings could point to nonexistent policy nodes;
2. a future response could command an action outside the actuation envelope;
3. a future actor could use an observation that was delivered to a different actor;
4. a policy could act on an observation before its declared arrival time;
5. a load-bearing assume-guarantee contract could have an unrealizable assumption on one admitted branch;
6. recovery could touch the return condition for one retained instant and then lose it;
7. the declared future-policy graph could be cyclic/non-forward-time.

These are finite theory-to-model projection failures, not new theory.

---

## 2. Finite adaptive policy witness

The theory requires:

\[
\pi_k:
\mathcal I_k^{admitted}
\rightarrow
\mathcal U_k^{feasible}.
\]

v0.11 represents a finite witness as a directed policy graph:

\[
P=(N,E,n_0).
\]

Each node \(n\in N\) carries:

\[
n=
(t_n,\ actor_n,\ action_n,\ ReqInfo_n,\ Obs_n).
\]

For a strong finite witness:

\[
\boxed{
action_n\in\mathcal U^{feasible}
}
\]

and:

\[
\boxed{
ReqInfo_n
\subseteq
InfoAvailable(actor_n,t_n,path_n).
}
\]

If node \(n\) observes channel \(o\) at time \(t_o\), then:

\[
\boxed{
t_o>t_n
}
\]

and every child node \(n'\) reached through that observation must satisfy:

\[
\boxed{
t_{n'}\ge t_o.
}
\]

This is the finite anti-hindsight condition.

Observation delivery is actor indexed. If channel \(o\) is delivered only to actor \(A\), the path does not make \(o\) available to actor \(B\).

---

## 3. Totality now binds to executable nodes

For every observed policy node:

\[
Outcomes(n)=\{\eta_1,\ldots,\eta_m\}.
\]

The transition map:

\[
Next_n:
Outcomes(n)\rightarrow N
\]

must be total:

\[
\boxed{
dom(Next_n)=Outcomes(n).
}
\]

For the root action, if a \`future_observation_contract\` is present, its response map must equal the policy-node transition map:

\[
\boxed{
Response_{future}=Next_{root}.
}
\]

Thus:

\[
\boxed{
TotalStringMap
\neq
ExecutableAdaptivePolicy.
}
\]

A response such as \`"MAGIC_NODE"\` cannot support a strong license unless that node exists and its action, actor-local information and timing are executable.

---

## 4. Finite policy graph discipline

The current finite witness requires:

- a declared root node;
- root action equal to the candidate action being witnessed;
- every reachable action inside the actuation envelope;
- every actor present in the actor-information ledger;
- future observations inside the observation envelope;
- explicit admitted outcomes at each observed node;
- exact total outcome-to-child mapping;
- forward-time observation and child execution;
- no cycle on a reachable policy path;
- no unreachable dead specification nodes.

The graph checker is a finite witness checker. It is not a solver over an unbounded POMDP policy space.

\[
\boxed{
FinitePolicyWitnessValid
\neq
OptimalPolicy
\neq
UniversalPolicyExistence.
}
\]

---

## 5. Load-bearing assume-guarantee realizability

Theory SOL-20/21 requires a common policy such that every load-bearing contract has both its assumption and guarantee satisfied when invoked.

For finite contract \(c\) used by action \(a\), v0.11 requires a witness over every admitted finite world × disturbance branch:

\[
W_c:
\mathcal W_Q^f
\times
D_Q^f
\rightarrow
\{A_c,G_c\}.
\]

Strong finite realizability requires:

\[
\boxed{
A_c(w,d)=true
\land
G_c(w,d)=true
\quad
\forall(w,d)
}
\]

for every contract whose \`used_by\` contains the candidate action.

Hence the executable rejects:

\[
Power\Rightarrow Pump,
\qquad
Pump\Rightarrow Power
\]

when the declared reachable branch witness cannot actually establish the assumptions.

This remains a finite witness supplied by an upstream adapter; the kernel does not infer physical contract reachability from raw infrastructure telemetry.

---

## 6. Persistent recovery

Theory defines:

\[
\mathcal K_{H_R}^{return}
=
\left\{
\chi\in\mathcal K:
\exists\pi\;
\forall w\in\mathcal W_{H_R},
\chi_s^\pi\in\mathcal K
\quad
\forall s\in[t,t+H_R]
\right\}.
\]

v0.11 adds a finite retained recovery contract:

\[
R=
(field,\ value,\ t_{return},H_R).
\]

On the declared retained grid \(T_Q^\lambda\), every admitted candidate-action trace must satisfy:

\[
\boxed{
read_R(\chi_t)=value
\quad
\forall
t\in
[t_{return},t_{return}+H_R]
\cap
T_Q^\lambda.
}
\]

Both \(t_{return}\) and \(H_R\) must lie on the declared \(\lambda\)-grid, \(H_R>0\), and:

\[
t_{return}+H_R\le H_Q.
\]

Therefore:

\[
\boxed{
Touch(\mathcal K^{return})
\neq
PersistentRecovery.
}
\]

The finite retained test does not establish continuous inter-sample persistence unless a separate continuous adapter certifies it.

---

## 7. v0.11 finite realizability closure

For candidate action \(a\), define the additional realizability obstruction set:

\[
\Omega_Z^{0.11}(a)
=
\Omega_{policy}
\cup
\Omega_{actor-local}
\cup
\Omega_{anti-hindsight}
\cup
\Omega_{contract}
\cup
\Omega_{recovery}.
\]

Then:

\[
\boxed{
M_{Z,f}^{Q}(a)=1
\iff
\Omega_Z^{0.11}(a)=\varnothing.
}
\]

The overall executable license becomes:

\[
\boxed{
License_Q^{0.11}(a)
\iff
License_Q^{0.10}(a)
\land
M_{Z,f}^{Q}(a).
}
\]

The strongest status remains:

\`\`\`text
LICENSED_WITHIN_ENVELOPE
\`\`\`

and never means universal safety.

---

## 8. Relationship to Toledo / IDM acceleration

No declared world or disturbance branch is skipped.

The speed discipline remains:

\[
\boxed{
DoNotSkipDeclaredBranches;
\quad
ReuseOnlyReaderEquivalentWork.
}
\]

The v0.8 retained-state and retained-trace quotients remain active. v0.11 adds structural policy/contract/recovery checks, but these are finite and ledgered; it does not expand repeated state predicates unnecessarily.

This preserves the intended chain:

\[
Toledo\ finite\ state
\rightarrow
IDM\ retained\ distinctions
\rightarrow
DSVA\ finite\ policy/contract\ witness
\rightarrow
verified\ scoped\ license.
\]

---

## 9. What is now materially closer to theory

With v0.11, the six v0.6 second-order meta-contracts have finite executable projections:

| Meta-contract | Finite executable projection |
|---|---|
| \(M_A\) Applicability | retained model/observation behavior overlap |
| \(M_D\) Dependency | lineage, resource reservation, factorization license |
| \(M_Z\) Realizability | finite adaptive policy DAG + assume-guarantee branch witnesses + persistent recovery |
| \(M_X\) Execution | lease, realized actuation, runtime revalidation |
| \(M_K\) Requirement | subject binding + full requirement ledger |
| \(M_V\) Verification | closure audit + exact spec/input digest binding + declared checker independence |

This does **not** collapse:

\[
FiniteProjection
\]

into:

\[
FullOpenWorldTheory.
\]

The largest remaining gaps move upstream/downstream:

1. raw heterogeneous evidence \(\rightarrow\) correct admissible-world constructor;
2. externally proving checker independence rather than verifying declared lineage;
3. domain-certified continuous inter-sample reach tubes;
4. domain-certified aggregate/group requirement semantics;
5. synthesis/optimality over policy spaces larger than the supplied finite witness.

---

## 10. Next falsification target

The next red-team should no longer focus on missing \(M_Z\) fields. It should attack the *soundness of the supplied finite witnesses*:

- two policy witnesses that are structurally valid but semantically alias different observation meanings;
- false/incomplete world construction while remaining inside the declared applicability envelope;
- circular verifier/checker lineage hidden behind apparently disjoint metadata;
- a continuous adapter whose reach-tube certificate is invalid between retained samples;
- an aggregate human-requirement adapter that preserves field coverage but changes the normative quantifier.

Failure must be recorded before repair.
