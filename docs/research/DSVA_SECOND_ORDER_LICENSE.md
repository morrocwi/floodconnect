# DSVA Second-Order License Envelope
## Closing the gap between internally closed models and decision-licensed action

**Date:** 2026-10-01  
**Status:** DSVA theory synthesis / proposal  
**Version:** v0.6  
**Root rule:** this document extends the existing DSVA Information-Contract Bridge. It does not create a second ontology.

# 1. Trigger

The v0.5 second-order red-team forced every first-order closure to PASS and still produced wrong or misleading actions.

The surviving defect class was:

\[
\boxed{
InternalClosure
\not\Rightarrow
WorldAdequacy.
}
\tag{SOL-01}
\]

The first-order bridge remains necessary:

\[
\mathfrak C_t^Q
=
(C_E^Q,C_S^Q,C_T^Q,C_B^Q,C_N^Q,C_R^Q),
\]

but it is not sufficient for a strong decision claim.

The repair is a second-order license envelope over the same bridge.

# 2. Declared applicability envelope

Every decision claim is relative to a declared applicability envelope:

\[
\boxed{
\mathcal E_t^Q
=
(
D_Q,\,
P_Q,\,
H_Q,\,
\mathcal M_Q,\,
\mathcal W_Q,\,
\mathcal O_Q,\,
\mathcal U_Q,\,
\mathcal B_Q,\,
\mathcal R_Q
).
}
\tag{SOL-02}
\]

where:

- \(D_Q\): spatial/system domain;
- \(P_Q\): declared population / protected entities;
- \(H_Q\): decision horizon;
- \(\mathcal M_Q\): admitted model family;
- \(\mathcal W_Q\): disturbance / hazard envelope;
- \(\mathcal O_Q\): observation-channel envelope;
- \(\mathcal U_Q\): actuation/resource envelope;
- \(\mathcal B_Q\): subsystem/boundary contracts;
- \(\mathcal R_Q\): protected requirements.

Therefore:

\[
\boxed{
LicensedWithin(\mathcal E_t^Q)
\neq
TrueForAllPossibleWorlds.
}
\tag{SOL-03}
\]

No DSVA theorem removes the open-world problem. A strong claim is always scoped to its declared envelope.

# 3. First-order closure and second-order license

Define:

\[
\boxed{
FOC_t^Q
=
\bigwedge
\{
InformationClosure,\,
EvidenceClosure,\,
StateClosure,\,
TransitionClosure,\,
BoundaryClosure,\,
CapacityClosure,\,
RecoveryClosure
\}.
}
\tag{SOL-04}
\]

Define the second-order meta-contract:

\[
\boxed{
\mathfrak M_t^Q
=
(
M_A^Q,\,
M_D^Q,\,
M_Z^Q,\,
M_X^Q,\,
M_K^Q,\,
M_V^Q
).
}
\tag{SOL-05}
\]

where:

- \(M_A^Q\): applicability / model-support closure;
- \(M_D^Q\): dependency closure;
- \(M_Z^Q\): realizability closure;
- \(M_X^Q\): execution-time closure;
- \(M_K^Q\): requirement / protected-population closure;
- \(M_V^Q\): verification / scope-preservation closure.

The strong envelope-relative license is:

\[
\boxed{
License_t^Q(a)
=
FOC_t^Q
\land
\bigwedge\mathfrak M_t^Q
\land
a\in\mathcal A_H^{EB}(\mathbb B_t).
}
\tag{SOL-06}
\]

If a required meta-contract is missing:

\[
\boxed{
License_t^Q(a)\neq TRUE.
}
\tag{SOL-07}
\]

The result becomes CONDITIONAL, LOCAL/PARTIAL, UNRESOLVED, or HOLD depending on which obligation failed.

# 4. Applicability closure: model invalidation, not model worship

## 4.1 Dialogue absorbed

Model invalidation and set-membership fault detection ask whether observed input-output behavior is compatible with a declared model family. A model that is inconsistent with observed behavior should be rejected rather than used to produce a precise decision.

DSVA absorbs model invalidation as an applicability operator.

## 4.2 Behavior envelope

For model family \(\mathcal M_Q\) and uncertainty envelope \(\mathcal E_t^Q\), let:

\[
\boxed{
\mathcal Y_{Q,L}^{model}
=
Beh_L(
\mathcal M_Q,
\mathcal W_Q,
\mathcal O_Q,
\mathcal U_Q
).
}
\tag{SOL-08}
\]

Let the compatible observed trace set be:

\[
\mathcal Y_{Q,L}^{obs}.
\]

Then:

\[
\boxed{
Invalidated_Q
=
1
\iff
\mathcal Y_{Q,L}^{model}
\cap
\mathcal Y_{Q,L}^{obs}
=
\varnothing.
}
\tag{SOL-09}
\]

If invalidated:

\[
\boxed{
Invalidated_Q
\Rightarrow
HOLD(ModelFamily)
}
\tag{SOL-10}
\]

for readers that depend on that family.

But:

\[
\boxed{
NotInvalidated
\not\Rightarrow
TrueModel.
}
\tag{SOL-11}
\]

This preserves the distinction between “not yet falsified by retained evidence” and “complete description of reality.”

## 4.3 Applicability status

\[
\boxed{
M_A^Q
=
1
}
\]

only when:
1. the current context lies inside the declared domain/horizon;
2. the model family has not been invalidated by retained compatible evidence;
3. known material hazard modes required by \(Q\) are included or explicitly marked unresolved;
4. the claim is rendered as conditional on \(\mathcal E_t^Q\).

Thus DSVA may say:

\[
ROBUST\_WITHIN\_DECLARED\_ENVELOPE
\]

but never silently promote this to:

\[
ROBUST\_TO\_REALITY.
\]

# 5. Dependency closure: common causes, shared resources, and compound hazards

Second-order red-team failures shared one structure: apparently separate objects had a hidden common dependency.

## 5.1 Evidence dependency graph

Define:

\[
\boxed{
G_E=(V_E,E_E)
}
\tag{SOL-12}
\]

where evidence nodes point to calibration, transformation, sensor, agency feed, or upstream data ancestors.

For measurement \(j\):

\[
\boxed{
Y_j
=
h_j(X,\beta_{\rho(j)})
+
\nu_j
}
\tag{SOL-13}
\]

where \(\beta_{\rho(j)}\) is a shared systematic uncertainty inherited from lineage ancestor \(\rho(j)\).

Two sensors with one calibration ancestor are not automatically two independent confirmations.

\[
\boxed{
SourceCount
\neq
IndependentEvidenceCount.
}
\tag{SOL-14}
\]

If probabilistic estimates must be fused while cross-correlation is unknown, a conservative fusion method such as covariance intersection may be used as an optional solver. DSVA does not require Gaussian fusion.

## 5.2 Global resource reservation

Let physical resource \(r\) be usable in movement, support, shelter, health or infrastructure operations.

Define allocation across all graphs:

\[
\boxed{
\sum_{k\in Uses(r)}
z_{r,k}(t)
\le
Avail_r(t).
}
\tag{SOL-15}
\]

Therefore:

\[
\boxed{
MovementFeasible
\land
SupportFeasible
\not\Rightarrow
JointResourceFeasible.
}
\tag{SOL-16}
\]

The ORCG resource identity is global even when movement and support graphs remain semantically distinct.

## 5.3 Compound-hazard dependence

A joint disturbance representation may not be factorized unless the relevant separability is licensed.

\[
\boxed{
\mathcal W_H
=
\prod_m\mathcal W_{H,m}
\quad
\text{only if factorization is licensed for }Q.
}
\tag{SOL-17}
\]

Likewise dynamics may not be assumed additive/separable:

\[
\boxed{
F_{joint}
=
\sum_m F_m
\quad
\text{only if interaction terms are negligible or modeled.}
}
\tag{SOL-18}
\]

Flood plus power loss, flood plus communications loss, or rain plus tide plus upstream discharge are therefore joint mechanisms, not automatically independent layers.

## 5.4 Dependency closure

\[
\boxed{
M_D^Q=1
}
\tag{SOL-19}
\]

only when material shared causes, shared resources and joint hazard interactions required by \(Q\) are represented, bounded, or explicitly unresolved.

# 6. Realizability closure: contracts and future observations must actually be executable

## 6.1 Contract realizability

An assume-guarantee pair may be syntactically compatible and still be unrealizable.

For every boundary contract used to support reader \(Q\):

\[
C_i=(A_i,G_i).
\]

Define the set of contracts actually used by the claim:

\[
Used_Q=\{i:C_i\text{ is load-bearing for }Q\}.
\]

A load-bearing contract cannot rely only on the implication \(A_i\Rightarrow G_i\). Its assumption must be supplied on a reachable trace.

Define:

\[
\boxed{
Realizable_H^Q
=
1
}
\tag{SOL-20}
\]

iff there exists an admissible common policy such that, for every currently admitted world and disturbance sequence, the induced trace can satisfy:

\[
\boxed{
A_i
\land
G_i
\quad
\forall i\in Used_Q
}
\tag{SOL-21}
\]

at the times those contracts are invoked.

This rejects unsupported circular compositions such as:

\[
Power\Rightarrow Pump,
\qquad
Pump\Rightarrow Power
\]

when neither service is reachable from the current state.

## 6.2 Observation-policy realizability

An adaptive policy may rely on future evidence. Therefore the observation channel itself is part of the uncertainty model.

Let:

\[
\eta_k^O
\in
\mathcal W_k^O
\]

represent sensor loss, communications failure, access denial, delay, or missing data.

Future information is:

\[
\boxed{
\mathcal I_k
=
(E_{\le k},A_{<k},\mathbb B_k,\eta_{\le k}^O).
}
\tag{SOL-22}
\]

The policy must be total over all admitted observation outcomes:

\[
\boxed{
\pi_k:
\mathcal I_k^{admitted}
\rightarrow
\mathcal U_k^{feasible}.
}
\tag{SOL-23}
\]

In particular, MISSING, CHANNEL_DOWN, STALE and CONTRADICTION branches must have a defined safe response when they lie inside the declared observation envelope.

Hence:

\[
\boxed{
FutureMeasurementExpected
\neq
FutureMeasurementGuaranteed.
}
\tag{SOL-24}
\]

## 6.3 Persistent recovery

Reaching \(\mathcal K\) at one instant is not sufficient for recovery.

Define a return set for persistence horizon \(H_R\):

\[
\boxed{
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
}
\tag{SOL-25}
\]

Recovery is complete only when the admissible post-recovery information state is contained in the return set:

\[
\boxed{
\mathbb B_{\tau}
\subseteq
\mathcal K_{H_R}^{return}.
}
\tag{SOL-26}
\]

Thus:

\[
\boxed{
Touch(\mathcal K)
\neq
Recovered.
}
\tag{SOL-27}
\]

\(H_R\) is context/hazard specific; no universal dwell time is asserted.

## 6.4 Realizability closure

\[
\boxed{
M_Z^Q
=
ContractRealizable_Q
\land
ObservationPolicyRealizable_Q
\land
RecoveryPersistence_Q
}
\tag{SOL-28}
\]

for readers that depend on those elements.

# 7. Execution-time closure: an action needs a lease, not only an issue time

A correct readout can become wrong before it takes effect.

## 7.1 Action lease

For action \(a\) issued by reader \(Q\), define:

\[
\boxed{
I_{Q,a}^{license}
=
[t_{issue},t_{expire}].
}
\tag{SOL-29}
\]

\(t_{expire}\) is bounded by the earliest load-bearing expiry among:
- evidence validity/freshness;
- route/site validity;
- boundary contract validity;
- resource reservation validity;
- forecast/forward-hazard horizon;
- declared reader horizon.

Let:

\[
t_{effect}
=
t_{issue}+L(a).
\]

The action is execution-licensed only if:

\[
\boxed{
t_{effect}
\in
I_{Q,a}^{license}.
}
\tag{SOL-30}
\]

Otherwise:

\[
\boxed{
REVALIDATE
\quad\text{or}\quad
HOLD.
}
\tag{SOL-31}
\]

## 7.2 Command is not realized actuation

\[
\boxed{
u_t^{cmd}
\neq
u_t^{real}
}
\tag{SOL-32}
\]

unless realization is verified or bounded by the transition model.

Actuator acknowledgement, pump-on state, dispatched vehicle, public warning transmission and actual household receipt are different evidence classes.

## 7.3 Runtime assurance operator

A runtime monitor may be inserted immediately before/through execution:

\[
\boxed{
RA_Q(a,t)
=
Check(
Invariant_Q,
CurrentEvidence,
Lease,
Resources,
Boundary
).
}
\tag{SOL-33}
\]

If the monitor detects that the licensed envelope no longer holds, it cancels, revalidates, or switches to a declared safe fallback.

Runtime-assurance / Simplex-style ideas enter DSVA only as an EXECUTION OPERATOR, not as a new control ontology.

## 7.4 Execution closure

\[
\boxed{
M_X^Q=1
}
\tag{SOL-34}
\]

only when action lease, latency, realized-actuation uncertainty, resource reservation and required runtime revalidation are closed for the reader/action pair.

# 8. Requirement closure: the safe set must represent what we claim to protect

State completeness does not imply requirement completeness.

Define the protected requirement ledger:

\[
\boxed{
\mathcal R_Q
=
\{
r_\ell
\}
}
\tag{SOL-35}
\]

with:

\[
r_\ell
=
(
id,\,
population/entity,\,
function,\,
constraint,\,
threshold,\,
horizon,\,
provenance,\,
coverageStatus
).
\]

The viability set is constructed from requirements:

\[
\boxed{
\mathcal K_Q
=
\bigcap_{r\in\mathcal R_Q}
\mathcal K_r.
}
\tag{SOL-36}
\]

Define declared protected population \(P_Q^{decl}\) and represented population:

\[
P_Q^{repr}
=
\bigcup_{r\in\mathcal R_Q}Population(r).
\]

Then:

\[
\boxed{
CoverageGap_Q
=
P_Q^{decl}\setminus P_Q^{repr}.
}
\tag{SOL-37}
\]

If:

\[
CoverageGap_Q\neq\varnothing
\]

or its status is UNKNOWN, a complete human-safety claim is not licensed.

\[
\boxed{
M_K^Q=1
}
\tag{SOL-38}
\]

only when the protected requirements and declared population/entities relevant to \(Q\) are traceable, represented and testable at the claimed scope.

Requirements-traceability theory enters as a DISCOVERY / TRACEABILITY OPERATOR; it does not define DSVA values.

# 9. Verification and scope-preservation closure

The formal specification can be correct while implementation or rendering is wrong.

## 9.1 Proof/certificate checking

For an optimization/readout result \(r\), define:

\[
\boxed{
Verify_Q(
Spec_Q,
InputSnapshot,
r,
certificate
)
\in
\{PASS,FAIL,UNRESOLVED\}.
}
\tag{SOL-39}
\]

Operational use requires PASS when the reader depends on a solver whose output can be independently checked.

The exact certificate depends on the solver. Examples include:
- recomputing all hard constraints;
- checking flow conservation and capacity;
- validating a route against current edge gates;
- verifying an interval encloses all admitted states;
- checking an optimization certificate when available.

Proof-carrying-code ideas enter only as a VERIFICATION pattern: producer supplies a result plus evidence that a small independent checker can validate.

## 9.2 Decision resolution

A categorical reader is determined only if all admissible worlds agree:

\[
\boxed{
Resolved_Q(c)
=
1
\iff
\{O_Q(\chi):\chi\in\mathbb B_t\}
=
\{c\}.
}
\tag{SOL-40}
\]

For threshold decisions, measurement uncertainty must not straddle the category boundary unless the result is represented as an interval/UNRESOLVED.

This is a direct operationalization of Toledo finite reader equivalence.

## 9.3 Scope-preserving rendering

A rendered decision object must retain:

\[
\boxed{
R_Q^{out}
=
(
value,\,
Q,\,
H,\,
\mathcal E_t^Q,\,
assumptions,\,
validUntil,\,
status,\,
provenance
).
}
\tag{SOL-41}
\]

Therefore:

\[
\boxed{
SafeFor6Hours
\not\Rightarrow
SAFE.
}
\tag{SOL-42}
\]

A presentation layer may simplify wording but may not erase a load-bearing horizon, scope or assumption.

## 9.4 Verification closure

\[
\boxed{
M_V^Q
=
SolverChecked_Q
\land
ReaderResolved_Q
\land
ScopePreserved_Q.
}
\tag{SOL-43}
\]

# 10. The second-order license theorem schema

The v0.6 claim is not that every action can be proven correct in an open world.

The theorem schema is conditional:

\[
\boxed{
\begin{aligned}
&FOC_t^Q=1,\\
&\bigwedge\mathfrak M_t^Q=1,\\
&a\in\mathcal A_H^{EB}(\mathbb B_t),\\
&Context_t\in\mathcal E_t^Q
\end{aligned}
}
\]

implies:

\[
\boxed{
a
\text{ is licensed for reader }Q
\text{ within declared envelope }\mathcal E_t^Q
\text{ through its action lease.}
}
\tag{SOL-44}
\]

This does **not** entail:

\[
\boxed{
a\text{ is safe in every physically possible world.}
}
\tag{SOL-45}
\]

The distinction is constitutional.

# 11. Claim-status lattice

A DSVA action/readout should end in one of the following statuses:

\[
\boxed{
\{
LICENSED\_WITHIN\_ENVELOPE,\,
CONDITIONAL,\,
LOCAL/PARTIAL,\,
UNRESOLVED,\,
CONTRADICTION,\,
INVALIDATED,\,
HOLD
\}.
}
\tag{SOL-46}
\]

Suggested interpretation:

- LICENSED_WITHIN_ENVELOPE: all required first- and second-order contracts pass;
- CONDITIONAL: valid only under an unresolved or externally supplied assumption;
- LOCAL/PARTIAL: scope/population/boundary is incomplete;
- UNRESOLVED: evidence/readout does not separate required outcomes;
- CONTRADICTION: admitted evidence/model constraints have empty intersection;
- INVALIDATED: retained behavior is incompatible with the model/envelope;
- HOLD: no action claim may be promoted because a load-bearing obligation failed.

# 12. External theory placement

| External family | DSVA v0.6 absorption | Role |
|---|---|---|
| model invalidation / set-membership fault detection | current behavior vs model behavior envelope | APPLICABILITY OPERATOR |
| covariance intersection / unknown-correlation fusion | conservative treatment of unknown evidence dependence when probabilistic fusion is used | OPTIONAL SOLVER |
| assume-guarantee realizability checking | reject syntactically compatible but unrealizable contracts | REALIZABILITY OPERATOR |
| POMDP / observation-kernel decision theory | include future observation availability/failure branches | POLICY REALIZABILITY |
| runtime assurance / Simplex | revalidate before/effect execution, fallback on envelope violation | EXECUTION OPERATOR |
| requirements traceability | population/requirement-to-constraint coverage | REQUIREMENT TRACEABILITY |
| controlled invariance / terminal invariant sets | persistent post-recovery return set | RECOVERY SPECIAL CASE |
| proof-carrying / certifying computation | independently check result against hard specification | VERIFICATION PATTERN |

No external family replaces Toledo, DSVA, TDLC/LCF, ORCG, Unified Crisis State, or the FloodConnect evidence system.

# 13. Source anchors

- Harirchi, F., & Ozay, N. (2018). Guaranteed model-based fault detection in cyber–physical systems: A model invalidation approach. Automatica, 93, 476–488. https://doi.org/10.1016/j.automatica.2018.03.040
- Julier, S., & Uhlmann, J. (1997). A non-divergent estimation algorithm in the presence of unknown correlations. American Control Conference. https://doi.org/10.1109/ACC.1997.609105
- Gacek, A., Katis, A., Whalen, M. W., Backes, J., & Cofer, D. (2015). Towards realizability checking of contracts using theories. NASA Formal Methods.
- Mehmood, U., Sheikhi, S., Bak, S., Smolka, S. A., & Stoller, S. D. (2021). The Black-Box Simplex Architecture for Runtime Assurance of Autonomous CPS.
- Ramesh, B., & Jarke, M. (2001). Toward reference models for requirements traceability. IEEE Transactions on Software Engineering, 27(1), 58–93. https://doi.org/10.1109/32.895989
- Necula, G. C. (1997). Proof-carrying code. POPL 1997, 106–119. https://doi.org/10.1145/263699.263712
- Aubin, J.-P., Bayen, A. M., & Saint-Pierre, P. (2011). Viability Theory: New Directions. Springer.

# 14. Resulting single bridge

DSVA v0.6 remains one chain:

\[
\boxed{
Occurrence
\rightarrow
Evidence
\rightarrow
FirstOrderContracts
\rightarrow
InformationState
\rightarrow
PossibleFutures
\rightarrow
MetaLicense
\rightarrow
Viable/RecoverablePolicy
\rightarrow
VerifiedReadout
\rightarrow
LeasedAction
\rightarrow
RuntimeFeedback.
}
\tag{SOL-47}
\]

The central methodological rule becomes:

\[
\boxed{
Computable
\neq
InternallyClosed
\neq
DecisionLicensed
\neq
TrueInAllPossibleWorlds.
}
\tag{SOL-48}
\]

This is the second-order continuation of the same DSVA/Toledo information bridge.
