# DSVA v0.4 brutal adversarial red-team
## Finite counterexamples after repository-first synthesis

**Date:** 2026-10-01  
**Simulation:** YES — synthetic finite counterexamples only, except where an existing executable FloodConnect evaluator is directly exercised.  
**Production effect:** NONE. This file is an experiment/red-team artifact.  
**Baseline:** current `main` after DSVA v0.4 repository-first synthesis.  
**Rule:** a PASS means the architecture survives the constructed attack. A VULNERABLE result means the attack exposes either a formal ambiguity, an implementation gap, or a missing closure condition. It is not silently repaired inside this experiment.

## Summary

The brutal pass deliberately attacks the theory at places where robust-control/disaster architectures commonly fail: quantifier order, empty information sets, future-information timing, contradictory evidence, unit/datum compatibility, forecast support, unmodelled topology failure, shared bottlenecks, recovery dead ends, hysteresis, and externalized harm.

Result:

| # | Attack | Result | Severity |
|---|---|---|---|
| 1 | statewise viability vs one observation-based common policy | PASS | — |
| 2 | information arrives after irreversible action deadline | PASS | — |
| 3 | empty admissible-state set makes universal viability vacuously true | VULNERABLE | CRITICAL FORMAL |
| 4 | fresh timestamp but stuck/bad-quality sensor under DSVA-R07 alone | VULNERABLE | HIGH FORMAL-INTEGRATION |
| 5 | datum/unit incompatibility under DSVA-R07 alone | VULNERABLE | HIGH FORMAL-INTEGRATION |
| 6 | forecast has no declared quantitative support set | VULNERABLE | HIGH SEMANTIC |
| 7 | hazard-driven failure omitted from declared damage/disturbance support | BOUNDARY GAP | CRITICAL MODEL-CLOSURE |
| 8 | two independently FEASIBLE LCF deliveries oversubscribe one shared edge | VULNERABLE | HIGH IMPLEMENTATION |
| 9 | no path from life-critical floor back to normal viability | PASS | — |
| 10 | temporary improvement between two hazard pulses | PASS | — |
| 11 | locally viable control harms omitted downstream system | BOUNDARY GAP | CRITICAL SYSTEM-CLOSURE |
| 12 | road clear while community services remain failed | PASS | — |
| 13 | two competing topology steppers: Eq. 32 vs DSVA-R01/R02 | VULNERABLE | HIGH FORMAL |
| 14 | new damage state D_t is not explicitly inside chi_t | VULNERABLE | HIGH STATE-CLOSURE |
| 15 | evidence validity interval introduced after Eq. 9 but not added to evidence tuple | VULNERABLE | MEDIUM-HIGH SCHEMA |
| 16 | fixed freshness Eq. 15 and dynamic freshness DSVA-R06 coexist without explicit reduction | VULNERABLE | MEDIUM FORMAL |
| 17 | R13 uses NewUpstreamPulse / TopologyLoss without formal readers | VULNERABLE | MEDIUM FORMAL |
| 18 | Theorem T1 permits empty “refinement” unless nonempty consistency is stated | VULNERABLE | HIGH THEOREM PRECONDITION |

The executable pytest file is:
`tests/test_dsva_v04_brutal_adversarial.py`.

---

# 1. Quantifier trap — survives

Construct two hidden states with identical current information:

[
Safe(x_1)={A},
qquad
Safe(x_2)={B}.
]

Then:

[
(orall x)(exists u_x);Safe(x,u_x)
]

is true, but:

[
(exists u)(orall x);Safe(x,u)
]

is false.

The intersection is:

[
{A}cap{B}=arnothing.
]

DSVA survives because Eq. 37 makes policy depend on the information state, not the hidden state, and Eq. 38 requires one adaptive policy that works for every admissible world. The old open-loop Eq. 40 also returns no common action.

**Result: PASS.**

---

# 2. Information arrives too late — survives

Let the same two hidden states require opposite irreversible actions at (t_0). A sensor reveals the hidden state at (t_1), but the safety deadline is (t_0).

The future observation is valuable epistemically but cannot retroactively change the already-required first action.

Because DSVA policy is causal through:

[
mathcal I_k=(E_{le k},A_{<k},mathbb B_k)
]

and the Toledo observation loop is time ordered, the policy cannot condition the (t_0) action on evidence available only at (t_1).

**Result: PASS.**

---

# 3. Empty admissible set / vacuous viability — critical formal hole

Suppose contradictory licensed evidence makes the admissible state set empty:

[
mathbb B_t=arnothing.
]

The manuscript's Appendix A correctly refuses an empty reader state:

`REFUSED: model-evidence contradiction`.

But the central mathematical definition:

[
Pi_H^{EB}(mathbb B_t)
=
{pi:
orallchi_tinmathbb B_t,ldots}
]

has a classical-logic problem: universal statements over the empty set are true. Therefore every policy can become vacuously viable, and:

[
T_V(arnothing)
=
sup{H:Pi_H^{EB}(arnothing)
eqarnothing}
]

can become meaningless or spuriously unbounded.

Required closure is explicit, not implicit:

[
oxed{
mathbb B_t=arnothing
Rightarrow
PolicyReadout=REFUSED(CONTRADICTION)
}
]

and all viability/recovery/VOI operators must be undefined/refused on the empty information state.

**Result: VULNERABLE — CRITICAL.**

---

# 4. Fresh-but-stuck sensor vs DSVA-R07 — integration hole

The older DSVA core already states:

[
FRESH
otRightarrow VALID
]

and defines `StuckSuspect`.

However v0.4's new residual admission equation is:

[
Admit_j
=
SemanticOK_j
land ProvenanceOK_j
land Active_j
land Fresh_j.
]

A sensor can satisfy all four while failing quality/QC.

Thus the theory text contains the right rule, but DSVA-R07 is weaker than the pre-existing evidence architecture.

Required repair should either add the quality/compatibility gate or state formally that R07 is downstream of an already-passed QC operator.

**Result: VULNERABLE — HIGH.**

---

# 5. Datum/unit incompatibility — integration hole

Two water-level observations can each be official, fresh, active and semantically an observation, while using incompatible vertical datums. If admitted directly into a head-gradient calculation, a false hydraulic direction can result.

Eq. 9 stores `unit` and `datum`, but DSVA-R07 does not require compatibility.

A robust admission relation needs a reader-specific compatibility condition, for example:

[
Compatible_j(Q)
=
UnitOKland DatumOKland SpatialSupportOKland TemporalSupportOK.
]

Then:

[
Admit_j(Q)
=
SemanticOKland ProvenanceOKland QualityOK
land Activeland Freshland Compatible_j(Q).
]

**Result: VULNERABLE — HIGH.**

---

# 6. Forecast with undefined support — Boolean support breach is insufficient

DSVA-R08 uses:

[
SupportBreach
=
mathbf 1[
Y^{obs}
otinmathcal S^{fcst}
].
]

But some real forecast products are categorical or provide no licensed numeric predictive support interval. When:

[
mathcal S^{fcst}=UNKNOWN,
]

the system must not evaluate breach as FALSE.

The required semantics are three-valued:

[
SupportBreachin{TRUE,FALSE,UNKNOWN}.
]

**Result: VULNERABLE — HIGH.**

---

# 7. Unmodelled topology damage — robustness is only as complete as the support

DSVA-R01/R02 can represent hazard-driven topology failure only if the relevant failure lies inside the declared damage/disturbance support.

A finite counterexample is trivial:

- modelled worlds: bridge remains usable;
- true world: bridge fails before the planned crossing;
- bridge failure was omitted from (mathcal D/mathcal W).

Then the robust policy can be “robust” only to the declared set and still fail physically.

This is not solved by adding ever more hazards. The theory needs a **model-closure/readout obligation**: a guarantee may be stated only relative to a declared uncertainty envelope, and missing topology-affecting mechanisms must downgrade the claim.

**Result: BOUNDARY GAP — CRITICAL.**

---

# 8. Shared-edge oversubscription — executable LCF counterexample

Current `convergence_feasibility.evaluate_candidate()` evaluates one provider/interface/path tuple at a time.

Finite witness:

- shared edge capacity = 10 units/h;
- provider P1 needs to deliver 8;
- provider P2 needs to deliver 8;
- both paths independently declare path capacity 10;
- each candidate evaluates `FEASIBLE`.

But simultaneous flow is:

[
8+8=16>10.
]

Therefore pairwise feasibility does not imply network-feasible simultaneous allocation.

This is already consistent with the old Hat Yai red-team's statement that throughput is unfinished. What is still missing is a shared-edge allocation constraint such as:

[
oxed{
sum_{r:P_r
i e} y_r(t)
le
B_e(t)
quadorall e.
}
]

**Result: VULNERABLE — HIGH IMPLEMENTATION GAP.**

---

# 9. Recovery dead end — survives

Construct an emergency state in (mathcal K^{life}setminusmathcal K) with only a self-loop and no transition back to (mathcal K).

Then:

[
Pi_H^{REC}=arnothing.
]

DSVA-R11 correctly does not confuse “can remain alive temporarily” with “recoverable.”

**Result: PASS.**

---

# 10. Two-pulse chatter — survives conceptually

Sequence:

[
DANGER, CALM, DANGER.
]

A naive phase machine produces:

[
ESCALATE, DEESCALATE, ESCALATE.
]

With a two-observation hold requirement, the middle de-escalation is blocked.

This is exactly the role of DSVA-R13/R14.

**Result: PASS at theory level.**  
**Engineering status:** guard readers and hold logic are not yet executable DSVA objects.

---

# 11. Local viability with downstream harm — critical system-boundary gap

Consider a local drainage action that keeps Sammakorn inside its local (mathcal K) by exporting water, but harms a downstream community omitted from the modeled state.

The policy can then be mathematically viable locally and socially harmful globally.

Therefore the system boundary for an action claim must be **closed under material action consequences**.

A candidate closure rule is:

[
oxed{
Affected(u,chi)
subseteq
Domain(chi,mathcal K)
}
]

for every action used to support a safety/viability claim; otherwise the result must explicitly be local/partial rather than system-safe.

**Result: BOUNDARY GAP — CRITICAL.**

---

# 12. Road-clear recovery collapse — survives

Existing FloodConnect already has:

[
RoadClear
otRightarrow CommunityRecovered
]

and the human/service vector plus environmental clocks preserve this separation.

**Result: PASS.**

---

# 13. Competing topology steppers — internal formal inconsistency

Earlier DSVA Eq. 32 still states:

[
G_{t+1}=F_G(G_t,u_t^S).
]

v0.4 later adds:

[
D_{t+1}inmathcal D(D_t,G_t,X_t,w_t^G,u_t^S)
]

and:

[
G_{t+1}
=
mathcal T_G(G_t,D_{t+1},u_t^S).
]

Unless Eq. 32 is explicitly declared the special case of no hazard-induced damage, two different topology-transition laws coexist.

Required repair:

[
Eq32
equiv
DSVA	ext{-}R02
quad	ext{when}quad
D_{t+1}=D_t
	ext{ and hazard causes no topology change.}
]

**Result: VULNERABLE — HIGH.**

---

# 14. Damage state is not in the joint state — state-closure hole

DSVA's joint state is:

[
chi_t=(G_t,X_t,Z_t,Theta_t,Gamma_t).
]

But DSVA-R01 requires (D_t).

If two worlds have identical ((G,X,Z,Theta,Gamma)) but different latent structural damage (D_t), they can have different (G_{t+1}). Then (chi_t) is not sufficient to evolve the new v0.4 dynamics.

Repair options:
1. include (D_t) explicitly in (chi_t); or
2. formally define (D_t) as part of (G_t) or (Theta_t).

It cannot remain implicit.

**Result: VULNERABLE — HIGH.**

---

# 15. Validity interval is not present in the evidence tuple

Eq. 9 defines evidence with:

[
t_{obs},t_{pub},uncertainty,freshness,quality,lineage
]

but v0.4 introduces:

[
I_j^{valid}=[t_j^{from},t_j^{to}].
]

The new object has no explicit location in the evidence schema.

This matters because warning validity is not derivable from observation age.

**Result: VULNERABLE — MEDIUM-HIGH.**

---

# 16. Two freshness equations coexist

Earlier:

[
Fresh_j(t)=mathbf1[age_j(t)le	au_j].
]

v0.4:

[
Fresh_j(t)=mathbf1[t-t_j^{obs}le	au_j(t)].
]

These are compatible only if the older form is explicitly the constant-window special case:

[
	au_j(t)equiv	au_j.
]

Without that statement, the same symbol has two definitions.

**Result: VULNERABLE — MEDIUM.**

---

# 17. Hysteresis guards are named but not formal readouts

DSVA-R13 uses:

[
NewUpstreamPulse_t
quad	ext{and}quad
TopologyLoss_t
]

without defining their evidence readers.

The conceptual rule is sound, but an executable theory must define the source/readout contract or leave these values UNKNOWN.

**Result: VULNERABLE — MEDIUM.**

---

# 18. Theorem T1 needs nonempty consistent refinement

T1 assumes:

[
mathbb B'_tsubseteqmathbb B_t.
]

But the empty set is a subset of every set. Therefore a contradictory update could satisfy the written subset relation and make the formal monotonicity statement vacuously true while the information state is unusable.

Required precondition:

[
oxed{
arnothing
eqmathbb B'_tsubseteqmathbb B_t
}
]

plus licensed/quality-compatible evidence and no harmful hidden exclusion of the true state, as the prose already intends.

**Result: VULNERABLE — HIGH theorem-precondition gap.**

---

# Strongest findings

The red-team did **not** break the central common-policy idea. The strongest surviving part is still:

[
oxed{
existspi(	ext{information history})
;orallchiinmathbb B_t
;orall w
}
]

rather than the weaker and unsafe:

[
orallchi;existspi_chi.
]

The highest-value defects are instead **closure defects**:

1. empty/contradictory information state must never create vacuous viability;
2. the state must be closed under every variable used by the transition law;
3. evidence admission must be closed under QC + unit/datum/readout compatibility;
4. uncertainty support must cover the mechanism to which a robustness claim refers;
5. system boundaries must include material action externalities;
6. candidate-level lifeline feasibility must not be promoted to simultaneous network allocation.

These are falsifiable and patchable without abandoning the DSVA root objects.

## Next patch target

If this red-team is accepted, the minimal theory patch should add no new ontology. It should only:
- make nonempty information state a precondition of viability/recovery/VOI;
- reconcile Eq. 32 with DSVA-R01/R02;
- place (D_t) inside the declared state;
- strengthen DSVA-R07 to quality + compatibility-aware admission;
- make support-breach three-valued;
- state uncertainty-envelope and action-domain closure obligations;
- keep shared-edge allocation as an LCF/ORCG engineering extension rather than pretending pairwise LCF solves network flow.
