# DSVA × FloodConnect Canonical Synthesis
## What already existed before the v0.4 theory upgrade

**Date:** 2026-10-01  
**Status:** canonical extraction note for DSVA; no production override  
**Rule:** existing FloodConnect constructs are absorbed before new theory equations are proposed.

This note records what the repository already contained before the Nan/Hat Yai red-team was used to strengthen DSVA. The purpose is to prevent ontology duplication.

# 1. Existing constructs that already answer parts of the red-team

## 1.1 Community movement graph already exists

Canonical artifacts:
- `docs/COMMUNITY_SELF_HELP_DAG.md`
- `community_dag.py`
- `site/inputs/community/self_help_dag.yaml`

FloodConnect already defines a resident-movement graph

\[
G_{move}=(V,E_{move})
\]

with fail-closed edge use. For group size \(g\), mode \(m\), and time \(t\), an edge is usable only when the declared hard constraints pass:

\[
\phi(e;g,m,t)=1.
\]

The resulting feasible graph is

\[
\boxed{
G_t^{*}=(V_t^{*},E_t^{*})
}
\]

rather than the full road graph.

Existing hard requirements include:
- field verification;
- freshness;
- status OPEN/ASSISTED rather than BLOCKED/UNKNOWN;
- safety CLEAR/CAUTION;
- mode feasibility;
- declared capacity;
- safe/known destination state.

The route ranking is lexicographic rather than a weighted risk score:

\[
J(P)=(A,D,C,U_c,-B,U_d,L,H).
\]

This already addresses the red-team concern that route state is dynamic and mode-specific.

## 1.2 Lifeline/support network already exists

Canonical artifacts:
- `docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md`
- `convergence_feasibility.py`
- `site/inputs/community/sustainment_policy.yaml`

FloodConnect already separates:

\[
G_{move}=(V,E_{move})
\]

from:

\[
\boxed{
G_{support}=(V,E_{support})
}
\]

where support edges may move food, medicine, water, power, information, boats, volunteers and health support inward or laterally.

For group \(g\), essential function \(e\), time \(t\), and horizon \(H\), the existing Lifeline Convergence Feasibility construct uses:

\[
G_{g,e}(t,H)
=
\max(0,D_{g,e}(H)-X_{g,e}(t))
\]

and:

\[
Q_{p,g,e}(t,H)
=
\min(S_{p,e}(t,H),B_{P(p,g),e}(t,H)).
\]

Convergence is feasible only when there exists a verified interface/path with enough capacity and arrival before failure:

\[
\boxed{
q\in Reach_{community}(t)\cap Reach_{provider}(t)
\land
VerifiedFresh(q,P)
\land
Q_{p,g,e}\ge G_{g,e}
\land
T^{arrive}_{p\to g,e}<T^{fail}_{g,e}.
}
\]

Three-valued semantics are already canonical:

\[
C_{g,e}\in\{1,0,\bot\}.
\]

Thus the red-team concern that hospitals/power/medicine/support form a dependency system was already partly solved. DSVA must absorb this layer rather than introduce a duplicate "lifeline graph."

## 1.3 Thai Lifeline Margin already exists

For candidate support node \(v\):

\[
\boxed{
M_e(v,g,t,H)
=
X_{v,e}(t)
+
\sum_p y_{p\to g,e}(t,H)
-
D_{g,e}(H).
}
\]

The margin is retained separately for each essential function.

Response slack is:

\[
\boxed{
\Lambda_{g,e}
=
T^{fail}_{g,e}
-
\min_p T^{arrive}_{p\to g,e}.
}
\]

This already formalizes a common disaster failure: supply exists somewhere, but cannot arrive before the local function fails.

## 1.4 Lowest Viable Community Node and recovery phase already exist

Canonical artifacts:
- `docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md`
- `shelter_decision.py`
- `docs/THAI_FLOOD_COMMUNITY_SUSTAINMENT_MODEL.md`

FloodConnect already evaluates support layers:

`household -> buddy -> zone -> community -> external`

without converting them into a weighted score.

The Unified Crisis State already contains operational phase:

\[
Z_i(t,T)=(O,F,M,S,E,H,A,P)
\]

with

\[
P\in\{PREPARE,RESPONSE,SHELTER,RECOVERY,UNKNOWN\}.
\]

Existing response patterns include:
- STAY/SUSTAIN;
- STAY/PREPARE;
- RESUPPLY;
- DELIVER INWARD;
- ESCALATE SUPPORT;
- MOVE;
- ASSISTED EVACUATION;
- SHELTER INTERVENTION / RELOCATION;
- RECOVERY / RETURN;
- VERIFY / REFUSE.

Therefore "recovery exists" was already true at the operational layer. The residual gap was not the existence of recovery, but a **general DSVA equation for recoverability after the joint viability set has already been breached**.

## 1.5 Operational resource capability graph already exists

Canonical artifacts:
- `docs/OPERATIONAL_RESOURCE_CAPABILITY_GRAPH.md`
- `operational_resources.py`
- `site/inputs/community/operational_tools.yaml`

A verified tool deployment can modify node/edge capability:

\[
\boxed{
K_v^{eff}(t)
=
K_v^{base}(t)
\cup
\bigcup_{r\in R_v(t)}
\kappa_{node}(r)
}
\]

\[
\boxed{
M_e^{eff}(t)
=
M_e^{base}(t)
\cup
\bigcup_{r\in R_e(t)}
\kappa_{edge}(r).
}
\]

The repository also already records the reverse cascade:

\[
ToolLoss
\rightarrow
CapabilityLoss
\rightarrow
NodeDowngrade/EdgeLoss
\rightarrow
LVCN\ Escalation.
\]

This covers much of the Hat Yai observation that high-clearance vehicles, boats, generators and other response resources change feasible movement/support without automatically making a route safe.

## 1.6 Environmental degradation clocks already exist

Canonical artifacts:
- `docs/ENVIRONMENTAL_DEGRADATION_CLOCKS.md`
- `environmental_degradation.py`
- `finite_temporal_ledger.py`

FloodConnect already uses multiple clocks instead of one generic "age of floodwater."

The effective occupancy/shelter horizon is:

\[
\boxed{
T_{effective,i}
=
\min(
T_{resource,i},
T_{environment,i},
T_{access,i},
T_{forward\ hazard,i}
).
}
\]

Unknown clocks are not treated as infinity.

The Toledo-aligned temporal ledger already requires:
- bounded declared observation windows;
- finite event lists;
- explicit left-boundary state;
- no infinity sentinel;
- LEFT_CENSORED rather than silent zero;
- verified RESOLVED events before a clock is closed.

Thus DSVA v0.4 should reuse this finite-time discipline when formalizing warning validity and recovery.

## 1.7 The Hat Yai red-team already existed

Canonical experiment:
- `experiments/2025-11-hat-yai-real-data-redteam.md`

The repository had already extracted the following weaknesses before the current DSVA red-team:

1. current local water state and forward hazard must remain separate;
2. re-escalation/hysteresis is required for repeated flood pulses;
3. freshness must become time/rate aware in fast-rise conditions;
4. catchment-scale upstream propagation is needed outside Bangkok;
5. route mode must be time-varying;
6. safe nodes require infrastructure-state verification;
7. extreme observations need OUTSIDE_CALIBRATED_RANGE semantics;
8. throughput and evacuation/resource capacity are first-class;
9. source coverage remains Bangkok-centric;
10. anti-leakage replay must prohibit future evidence.

Therefore those findings are **not new gaps discovered in v0.4**. They are prior FloodConnect requirements that DSVA must absorb.

# 2. What was still genuinely missing at the DSVA theory level

After reading the existing repository, the residual formal gaps are narrower:

1. no general equation for **hazard-induced topology transition** of the physical/functional graph;
2. no general DSVA evidence operator for **validity interval / expiry** across warnings, routes and observations;
3. OUTSIDE_CALIBRATED_RANGE existed as a red-team requirement but not yet as a general **forecast support-breach equation**;
4. recovery existed operationally, but no general **recoverability policy set after \(\mathcal K\) has been breached**;
5. re-escalation existed as a red-team requirement and forward-hazard axis, but no general **hysteretic phase-transition equation**;
6. the RKG did not list the Hat Yai red-team under `PROSPECTIVE_EXPERIMENTS`, despite the file already existing.

# 3. v0.4 residual equations

## 3.1 Hazard-induced topology transition

Let \(D_t\) be damage/failure state and \(w_t^G\) hazard loading on topology.

\[
\boxed{
D_{t+1}
\in
\mathcal D(
D_t,G_t,X_t,w_t^G,u_t^S
)
}
\tag{DSVA-R01}
\]

\[
\boxed{
G_{t+1}
=
\mathcal T_G(
G_t,D_{t+1},u_t^S
)
}
\tag{DSVA-R02}
\]

This permits bridges, roads, pumps, power nodes or service links to fail because of the hazard itself, not only because of a structural management action.

Existing FloodConnect movement/support logic then computes current feasible subgraphs from the changed topology and evidence:

\[
\boxed{
G_{move,t}^{*}
=
\Phi_{move}
(
G_t,E_t,M_t^{eff}
)
}
\tag{DSVA-R03}
\]

and analogously for support feasibility through the existing TDLC/LCF machinery.

## 3.2 Evidence validity and expiry

For every evidence product \(E_j\), define a declared validity interval:

\[
\boxed{
I_j^{valid}
=
[t_j^{from},t_j^{to}]
}
\tag{DSVA-R04}
\]

and:

\[
\boxed{
Active_j(t)
=
\mathbf 1[
t\in I_j^{valid}
].
}
\tag{DSVA-R05}
\]

Freshness remains separate:

\[
\boxed{
Fresh_j(t)
=
\mathbf 1[
t-t_j^{obs}\le\tau_j(t)
].
}
\tag{DSVA-R06}
\]

\(\tau_j(t)\) may depend on rate of change, hazard state, edge type or travel mode **only when such a rule is declared/calibrated**. Otherwise the source's fixed freshness rule remains authoritative or freshness stays unresolved.

Operational evidence is admissible only when its semantic, provenance, validity and freshness requirements all pass:

\[
\boxed{
Admit_j(t)
=
SemanticOK_j
\land
ProvenanceOK_j
\land
Active_j(t)
\land
Fresh_j(t).
}
\tag{DSVA-R07}
\]

This distinguishes "warning existed historically" from "warning remains active now."

## 3.3 Forecast support breach

Let a forecast product define a declared support/set \(\mathcal S^{fcst}_{j,t}\) for variable \(Y\).

When the later observation becomes available:

\[
\boxed{
SupportBreach_{j,t}
=
\mathbf 1[
Y_t^{obs}
\notin
\mathcal S^{fcst}_{j,t}
].
}
\tag{DSVA-R08}
\]

If support is breached:

\[
\boxed{
ForecastStatus
=
OUTSIDE\_CALIBRATED\_RANGE
}
\tag{DSVA-R09}
\]

for readers that depended on that support.

CAN-009 applies: the original forecast is retained exactly as issued; the later observation does not rewrite it.

A model-dependent quantitative reader must then either:
- re-estimate a licensed uncertainty set; or
- return HOLD/UNRESOLVED.

No automatic extrapolation is permitted.

## 3.4 Recoverability after viability loss

Existing FloodConnect `RECOVERY_RETURN` is lifted into DSVA by defining an emergency floor:

\[
\boxed{
\mathcal K^{life}
\supseteq
\mathcal K.
}
\tag{DSVA-R10}
\]

\(\mathcal K\) is the normal joint viability set. \(\mathcal K^{life}\) retains only declared life-critical and irreversibility constraints required during rescue/response.

When the current admissible state no longer lies inside normal viability, define:

\[
\boxed{
\Pi_H^{REC}(\mathbb B_t)
=
\left\{
\pi:
\forall \chi_t\in\mathbb B_t,
\forall w\in\mathcal W_H,
\exists \tau\le H:
\begin{array}{l}
\chi_s^\pi\in\mathcal K^{life}
\quad\forall s\in[t,t+\tau],\\
\chi_{t+\tau}^\pi\in\mathcal K
\end{array}
\right\}.
}
\tag{DSVA-R11}
\]

The worst-case re-entry time is:

\[
\boxed{
T_R^{*}
=
\inf_{\pi\in\Pi^{REC}}
\sup_{\chi,w}
\inf\{
\tau:
\chi_{t+\tau}^{\pi}\in\mathcal K
\}.
}
\tag{DSVA-R12}
\]

This does not replace LVCN, TDLC, shelter recovery or environmental clocks. Those existing constructs provide the human/service constraints and recovery operators inside \(\mathcal K^{life}\) and \(\mathcal K\).

## 3.5 Hysteresis and re-escalation

Let the existing Unified Crisis State provide current occupancy/function/movement/support/environment/forward-hazard state and phase \(P_t\).

Define a re-escalation guard:

\[
\boxed{
R_t^{+}
=
1
\quad\text{if}
\quad
H_t\in\{HIGH,CRITICAL,ACTIVE\}
\lor
NewUpstreamPulse_t
\lor
TopologyLoss_t.
}
\tag{DSVA-R13}
\]

Define a de-escalation guard only when current and forward conditions remain closed for a declared hold interval \(\Delta_h\):

\[
\boxed{
R_t^{-}
=
1
}
\]

iff all required current-state readers are acceptable, forward hazard is NONE/LOW, required evidence remains valid/fresh, and closure conditions persist through the declared hold interval.

Phase update:

\[
\boxed{
P_{t+1}
=
\begin{cases}
Escalate(P_t),&R_t^{+}=1,\\
DeEscalate(P_t),&R_t^{-}=1,\\
P_t,&\text{otherwise}.
\end{cases}
}
\tag{DSVA-R14}
\]

No numerical hold interval is universal. It must be hazard/context specific.

# 4. Resulting DSVA synthesis

After repository extraction, DSVA should be read as:

\[
\boxed{
\text{Toledo root}
\rightarrow
\text{typed evidence}
\rightarrow
\mathbb B_t
\rightarrow
\text{dynamic topology}
\rightarrow
\text{movement + lifeline/support graphs}
\rightarrow
\text{viable / recoverable policies}
\rightarrow
\text{Unified Crisis State}
\rightarrow
\text{action / recovery}
}
\]

Existing FloodConnect constructs remain canonical at their own layer.

New DSVA v0.4 theory is therefore **residual synthesis**, not ontology duplication.


# 5. v0.5 external-theory absorption after the brutal red-team

The v0.4 repository audit established what FloodConnect already owned. The subsequent brutal red-team identified closure defects. v0.5 therefore performs a second, narrower synthesis step: external theories are admitted only where they close one of those defects.

The canonical bridge is:

\[
\boxed{
\mathfrak C_t^Q
=
(C_E^Q,C_S^Q,C_T^Q,C_B^Q,C_N^Q,C_R^Q)
}
\]

with the full derivation in:

docs/research/DSVA_INFORMATION_CONTRACT_BRIDGE.md

Mapping:

| Leak | External dialogue absorbed | DSVA role |
|---|---|---|
| empty-set vacuity / contradiction | Belnap-bilattice information status | readout-status operator |
| fresh but invalid evidence / datum incompatibility | JCGM/VIM metrology + set-membership consistency | evidence contract / estimator |
| hidden damage breaks state closure | sufficient-state principle + hybrid systems | state/transition closure |
| undefined forecast support | set-valued prediction + optional conformal support builder | forecast-support operator |
| local safety exports harm downstream | assume-guarantee contracts | boundary composition |
| individually feasible deliveries overload shared edge | multicommodity/time-expanded flow | TDLC/LCF allocation solver |
| emergency state survives but may never return to normal | viability capture basin / reach-avoid | recovery special case / solver |

The ordering remains inside-out:

\[
FloodConnect/DSVA
\rightarrow
RedTeamLeak
\rightarrow
ExternalOperator
\rightarrow
DSVATranslation
\rightarrow
ToledoWeld
\]

not:

\[
ExternalTheory
\rightarrow
NewRootOntology.
\]

## 5.1 Closure rule

A strong DSVA claim now requires the closures relevant to its task reader:

\[
\boxed{
InformationClosure
\land
EvidenceClosure
\land
StateClosure
\land
TransitionClosure
\land
BoundaryClosure
\land
CapacityClosure
\land
RecoveryClosure
}
\]

where a closure that is irrelevant to the reader may be marked NOT_REQUIRED, but a required closure that is missing remains UNKNOWN/HOLD.

This is the single-bridge answer to the v0.4 red-team. It does not replace the canonical FloodConnect subsystems.
