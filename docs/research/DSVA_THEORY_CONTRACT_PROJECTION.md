# DSVA v0.10 — Executable Theory-Contract Projection

**Date:** 2026-10-02  
**Status:** proposal / executable projection of existing DSVA theory  
**Parent theory:** `DSVA_SECOND_ORDER_LICENSE.md` + `DSVA_INFORMATION_CONTRACT_BRIDGE.md`  
**Executable parent:** v0.9 audited meaning closure  
**Rule:** this file adds no parallel ontology. It makes already-declared DSVA second-order obligations load-bearing in the finite executable model.

## 1. Trigger

The v0.9 executable passed its own audited-meaning regression but still allowed scenarios that the v0.6 theory says must not receive a strong license.

A test-only theory-gap red-team in PR #42 forced those cases into the executable path. The first run established:

```text
6 failed, 493 passed, 1 skipped
```

The failures were not new theory. They were theory-to-model projection gaps.

The load-bearing theoretical anchors are:

[
InternalClosure
otRightarrow WorldAdequacy,
]

[
SourceCount
eq IndependentEvidenceCount,
]

[
FutureMeasurementExpected
eq FutureMeasurementGuaranteed,
]

[
u_{cmd}
eq u_{real},
]

and:

[
Verify_Q(Spec_Q,InputSnapshot,r,certificate).
]

v0.10 makes finite versions of those obligations executable.

---

## 2. Applicability projection

Theory defines model invalidation through behavior-set incompatibility:

[
Invalidated_Q=1
iff
mathcal Y^{model}_{Q,L}
cap
mathcal Y^{obs}_{Q,L}
=
arnothing.
]

The finite executable projection accepts two non-empty retained signature sets:

[
Y_M^f,qquad Y_O^f.
]

Then:

[
oxed{
M_A^{f}=PASS
iff
Y_M^fcap Y_O^f
eqarnothing.
}
]

If:

[
Y_M^fcap Y_O^f=arnothing,
]

the executable status is:

```text
INVALIDATED
```

rather than a precise action license.

Boundary:

[
NotInvalidated
otRightarrow TrueModel.
]

The finite signatures inherit the declared model and observation envelope supplied by the caller.

---

## 3. Dependency projection

### 3.1 Evidence lineage

For evidence nodes (i,j), let:

[
Anc(i),Anc(j)
]

be their declared failure/calibration/feed ancestors.

A pair explicitly claimed independent is accepted only if:

[
oxed{
Anc(i)cap Anc(j)=arnothing.
}
]

Therefore two sources with a shared calibration ancestor cannot be counted as independent confirmations.

This is a finite executable projection of the DSVA evidence-dependency graph, not proof that the supplied lineage graph is complete.

### 3.2 Global resource reservation

For candidate action (a) and resource (r):

[
Use(a,r)le Avail(r).
]

The executable uses exact rational comparison where values are finite rational/decimal representations:

[
oxed{
Use(a,r)>Avail(r)
Rightarrow
HOLD(a).
}
]

The current projection checks the aggregate resource use declared for the candidate action. Cross-time scheduling remains an upstream allocation/trajectory obligation.

### 3.3 Compound hazards

If multiple hazard components are represented as factorized:

[
mathcal W_H=prod_mmathcal W_{H,m},
]

the input must explicitly declare the factorization licensed.

[
oxed{
Factorized
land

eg FactorizationLicensed
Rightarrow
HOLD.
}
]

This does not infer separability from data; it prevents silent separability.

---

## 4. Observation-policy realizability projection

Theory requires an adaptive policy to be total over all admitted observation outcomes.

For a declared future channel (o), let:

[
Outcomes(o)={eta_1,ldots,eta_k}.
]

The executable future-observation contract supplies:

[
Response_o: Outcomes(o)ightarrow PolicyToken.
]

Strong finite realizability requires:

[
oxed{
dom(Response_o)=Outcomes(o).
}
]

Thus admitted branches such as:

```text
VALUE
MISSING
CHANNEL_DOWN
STALE
CONTRADICTION
```

cannot be silently omitted if they are inside the declared observation envelope.

The current v0.10 object verifies **totality of the declared response map**. It is not yet the full DSVA adaptive policy tree (pi(I_t)); semantic validity of a response token remains a later realizability obligation.

---

## 5. Execution projection

The theory distinguishes command from realized actuation:

[
u_{cmd}
eq u_{real}
]

unless realization is verified or bounded.

Every candidate action therefore carries an execution contract.

Strong execution requires:

[
RealizedStatusin{VERIFIED,BOUNDED}.
]

If bounded, a retained bound must be declared.

For runtime revalidation:

[
RuntimeRequired=1
Rightarrow
RuntimeStatus=PASS.
]

These checks operate in addition to the existing exact lease constraints:

[
t_{issue}le t_{effect}le t_{expire},
]

[
0le t_{effect}le H_Q,
]

[
t_{effect}le validUntil_Q.
]

---

## 6. Protected-requirement ledger projection

The theory defines:

[
r_ell=
(
id,,
population/entity,,
function,,
constraint,,
threshold,,
horizon,,
provenance,,
coverageStatus
).
]

v0.9 already added per-subject field binding. v0.10 requires the remaining ledger fields for a strong executable requirement.

For each (r):

[
CoverageStatus(r)=COVERED,
]

[
H_rge H_Q,
]

and function, constraint, provenance and threshold must be present.

The existing v0.9 binding rule remains:

[
dom(b_r)=Population(r),
]

and on the strong per-subject path:

[
p
eq qRightarrow b_r(p)
eq b_r(q).
]

Thus:

[
oxed{
PopulationLabel

eq
ProtectedRequirementLedger

eq
VerifiedHumanOutcome.
}
]

---

## 7. Verification binding and declared independence

v0.9 required closure audit witnesses but did not bind the verification certificate to the actual executable snapshot.

v0.10 defines two canonical projections:

[
Spec_Q^f
]

from the decision question, envelope, protected requirements, horizon/expiry and assumptions, and:

[
Input_Q^f
]

from retained information status, closures, worlds, disturbances, actors, traces, actions and second-order audit inputs.

The kernel computes:

[
d_S=SHA256(Canon(Spec_Q^f)),
]

[
d_I=SHA256(Canon(Input_Q^f)).
]

The supplied verification contract must carry the same digests:

[
oxed{
d_S^{decl}=d_S
land
d_I^{decl}=d_I.
}
]

A checker must also be declared distinct from the producer in:

```text
identity
implementation digest
failure lineage
```

For declared lineages (L_P,L_C):

[
oxed{
L_Pcap L_C=arnothing.
}
]

This operationalizes the theory's “small independent checker” requirement as far as the finite metadata permits.

Critical boundary:

[
oxed{
DeclaredIndependentChecker

eq
ProvenIndependentChecker.
}
]

The repository can verify the declared relationship and snapshot binding. It cannot prove that two external implementations secretly share no defect.

---

## 8. v0.10 finite strong condition

Let (Omega_Q^{0.9}(a)) be the v0.9 finite obstruction set.

Define additional finite theory obstructions:

[
Omega_Q^{T}(a)
=
Omega_A
cup
Omega_D
cup
Omega_Z
cup
Omega_X
cup
Omega_K
cup
Omega_V.
]

Then the v0.10 executable condition is:

[
oxed{
License_Q^{0.10}(a)
iff
Omega_Q^{0.9}(a)=arnothing
land
Omega_Q^{T}(a)=arnothing.
}
]

The returned strongest status remains:

```text
LICENSED_WITHIN_ENVELOPE
```

not:

```text
TRUE_IN_ALL_POSSIBLE_WORLDS
```

and not:

```text
ROBUST_TO_REALITY
```

---

## 9. IDM acceleration is preserved

The new contracts do not remove the v0.8 retained quotient.

The kernel still:

- uses exact rational decision-time/resource comparisons;
- evaluates repeated protected-state classes once;
- evaluates repeated retained trace classes once;
- checks every declared world × disturbance branch for coverage;
- returns an explicit finite `cost_ledger`.

v0.10 adds:

```text
contract_checks
digest_checks
lineage_checks
```

to the cost ledger.

The rule remains:

[
oxed{
DoNotSkipDeclaredWorlds;
quad
QuotientOnlyReaderEquivalentWork.
}
]

---

## 10. Scope still not closed by v0.10

v0.10 materially reduces the theory/model gap, but it is still a **finite projection**, not the whole DSVA theory.

The following remain explicitly open:

1. the finite model-behavior set is caller supplied;
2. the evidence-lineage graph may itself be incomplete;
3. declared checker independence is not externally proven;
4. future-observation response tokens are checked for totality, not yet as a full actor-local adaptive policy tree;
5. persistent recovery / controlled-invariant return sets are not yet executed as a dedicated finite return-set solver;
6. continuous inter-sample physical safety is not proven by `discrete_retained`;
7. aggregate/group requirement adapters need domain-specific semantic certificates;
8. the admissible-world constructor from raw heterogeneous evidence remains upstream.

Therefore:

[
oxed{
ExecutableTheoryContractClosure

eq
FullTheoryExecution

eq
WorldTruth.
}
]

The next adversarial target should attack the two largest remaining theory gaps:

[
oxed{
AdaptivePolicyExecution
}
]

and:

[
oxed{
PersistentRecoveryExecution.
}
]
