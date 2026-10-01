# Disaster-System Viability Architecture (DSVA)
## A General Theory of Viable Futures under Partial Observability and Constrained Actuation

**Standalone theory manuscript — Formal Upgrade v0.2**  
**Date:** 1 October 2026  
**Field:** Disaster Risk Science / Disaster Management  
**Empirical demonstrator:** Sammakorn retention-and-drainage system, eastern Bangkok, Thailand  
**Software/reproducibility anchor:** FloodConnect (`morrocwi/floodconnect`)  
**Theory claim:** DSVA is presented as a general disaster-management theory of viable futures. The claim rests on the synthesized equation system, its reductions, its intervention calculus, and its empirical falsifiability; no claim is withdrawn merely because a constituent operator has an established precedent.

---

## Abstract

Disaster management is commonly partitioned into hazard modelling, observation, forecasting, infrastructure control, early warning, emergency decision making, governance, response, and recovery. DSVA treats that partition not as a list of separate frameworks to be assembled, but as projections of one disaster-system equation universe. The theory begins from the phenomenon itself and asks a single general question: **which future trajectories remain viable, which actions can still preserve them, and what information or institutional change is required when the true state is only partially knowable?**

At time \(t\), DSVA distinguishes the latent world state, typed evidence, a joint information state \(\mathbb B_t\) containing every system state still admissible under evidence and physical constraints, human-and-service viability \(Z_t\), institutional actuation constraints \(\Gamma_t\), future disturbance sets \(\mathcal W\), and an adaptive policy space. The central object is the **evidence-bounded viable policy set**

\[
\Pi_H^{EB}(\mathbb B_t)
=
\left\{
\pi:
\forall \chi_t\in\mathbb B_t,\;
\forall w_{t:t+H}\in\mathcal W_H,\;
\chi_\tau^\pi\in\mathcal K
\;\forall\tau\le t+H
\right\},
\]

where \(\pi\) may condition future actions on future evidence. The associated **current evidence-bounded action set**

\[
\mathcal A_H^{EB}(\mathbb B_t)
=
\left\{
\pi_t(\mathcal I_t):\pi\in\Pi_H^{EB}(\mathbb B_t)
\right\}
\]

contains actions that are justified now while preserving future adaptation. The **viability horizon**

\[
T_V(\mathbb B_t)
=
\sup\left\{
H:\Pi_H^{EB}(\mathbb B_t)\neq\varnothing
\right\}
\]

measures how far into the future the disaster system can still be kept inside declared physical, human, service, and institutional viability constraints.

DSVA also introduces one intervention calculus for four classes of limiting resources: physical capacity, information, protective capability, and institutional actuation. Information is operationally valuable when it expands the viable policy/action set or extends \(T_V\); infrastructure is valuable when it changes dynamics or expands controllable capacity; governance is operationally represented through the actions that can actually be authorized and executed in time. This makes physical, epistemic, human, and institutional bottlenecks commensurable without collapsing them into a single risk score.

Thailand is used as a demanding empirical stress environment rather than a decorative case. The Bangkok 2026 flood exposed exactly the separations DSVA requires: extreme rainfall and limited retention, rising upstream discharge, tidal and receiving-water constraints, added pumps whose installed/support capacity could not be equated with realized net export, official warnings and action reports that were not observations, stale and contradictory public measurements, and uneven recovery in which roads improved before some communities recovered. The Sammakorn retention-and-drainage system is then used as a compact empirical instantiation. Thai government data interfaces are mapped explicitly into the theory: BMA/ThaiWater canal observations, BMA PumpHistory, road-flood observations, Bangkok monkey-cheek retention data, TMD nowcasts, RID reservoir data, and Royal Thai Navy tide products. Each source is typed so that observation, forecast, warning, instruction, action report, infrastructure capacity, and realized hydraulic performance cannot silently substitute for one another.

Existing traditions—including viability theory, controlled invariance, POMDP/belief-state decision making, set-membership estimation, real-time and model-predictive control, robust decision making, value-of-information analysis, formal warning decision theory, digital twins, disaster resilience, IWRM, and the Sendai Framework—enter only after DSVA is constructed. They are mapped as special cases, solvers, operators, parameterizations, boundaries, or rivals inside the DSVA equation system. The resulting theory is designed to be executable in FloodConnect, reducible to established theories under declared limiting conditions, and falsifiable across independent hazards and events.

**Keywords:** disaster management; disaster risk; viability; partial observability; evidence; emergency decision making; flood management; real-time control; governance; resilience; digital twin; FloodConnect; Bangkok

---

# 1. Introduction

A disaster manager rarely observes the disaster itself in full. What is available is a changing collection of measurements, forecasts, institutional reports, field observations, operating states, warnings, and incomplete descriptions of infrastructure. At the same time, action cannot wait for complete knowledge. Pumps may need to be operated before all inflows are measured; vulnerable households may need support before a local depth forecast is precise; roads may become unusable while city-scale indicators improve; and a warning may be technically correct yet operationally too late.

This creates a fundamental problem:

\[
\boxed{
\text{How should a disaster system act when the true state is only partially knowable?}
}
\]

The answer cannot be reduced to better prediction alone. A high-resolution model is useful only if its inputs, boundaries, control states, and human consequences are sufficiently represented for the decision being made. Conversely, many useful actions do not require a complete state estimate. A community can prepare medical supplies before the exact peak flood depth is known. A drainage operator can verify a terminal outlet before computing every internal flow. An emergency manager can refuse an evacuation recommendation when route safety remains unknown.

This paper therefore starts from the disaster-management problem itself. It does not begin by selecting an existing theoretical school and extending it. Instead, it constructs a closed equation universe from the phenomenon and then asks how established theories enter that universe.

The method is:

\[
\boxed{
\text{Phenomenon}
\rightarrow
\text{Primitives}
\rightarrow
\text{Equations}
\rightarrow
\text{Propositions}
\rightarrow
\text{Dialogue with existing theories}
}
\]

The unit of contribution is the architecture. The paper does not depend on the assertion that every mathematical component is individually new. A viability kernel may have precedent; model predictive control may have precedent; evidence filtering may have precedent; disaster resilience may have precedent. The question is whether these components can be placed in one formal disaster-management system without collapsing distinctions that matter operationally.

The architecture is called the **Disaster-System Viability Architecture (DSVA)**.

---

# 2. Phenomenon-first theory construction

## 2.1 The object of management is not a single hazard variable

Flood management is often summarized through variables such as rainfall, water depth, discharge, or storage. Fire management may use heat, spread rate, fuel condition, or wind. Epidemic management may use incidence, prevalence, hospital load, or reproduction metrics. These variables are necessary but insufficient because disaster management also involves:

- what is observed;
- what is forecast;
- what is uncertain;
- what infrastructure can do;
- what institutions are authorized and able to do;
- what people can still safely do;
- what services remain functioning;
- what future states remain preventable.

Accordingly, DSVA defines a disaster-management universe:

\[
\boxed{
\Omega_t
=
\left(
G_t,\,
X_t,\,
E_{\le t},\,
B_t,\,
Z_t,\,
\Gamma_t,\,
\mathcal U_t
\right)
}
\tag{1}
\]

where:

- \(G_t\): physical and functional topology of the disaster system;
- \(X_t\): latent physical state;
- \(E_{\le t}\): retained evidence up to time \(t\);
- \(B_t\): set of latent physical states still admissible under evidence and declared constraints;
- \(Z_t\): human, service, access, and continuity state;
- \(\Gamma_t\): institutional, legal, operational, temporal, and resource constraints;
- \(\mathcal U_t\): available action universe.

The non-collapse rule is:

\[
\boxed{
X_t
\neq
E_t
\neq
B_t
\neq
Z_t
\neq
\Gamma_t
\neq
u_t
}
\tag{2}
\]

This rule is constitutional. A government warning is not the physical state. A pump operating signal is not pump discharge. A dry road is not full community recovery. A stale gauge is not current safety. A predicted tide is not an observed downstream boundary.

---

# 3. Physical dynamics

## 3.1 Latent state transition

Let the physical state evolve according to:

\[
\boxed{
X_{t+\Delta t}
\in
F_G
\left(
X_t,\,
u_t^{H},\,
w_t;\,
\theta
\right)
\oplus
\Xi_t
}
\tag{3}
\]

where:

- \(F_G\) is the system dynamics induced by topology \(G\);
- \(u_t^{H}\) is a hydraulic/physical control action;
- \(w_t\) is exogenous forcing;
- \(\theta\) is the parameter set;
- \(\Xi_t\) is unresolved disturbance/model discrepancy;
- \(\oplus\) denotes declared uncertainty composition, not necessarily ordinary addition.

A domain-specific model—hydrodynamic, hydrological, fire-spread, epidemic, structural, atmospheric, or otherwise—is therefore an implementation of \(F_G\), not the whole disaster theory.

## 3.2 Flood specialization

For an urban flood network with storage vector \(\mathbf S_t\), signed incidence matrix \(B_G\), edge-flow vector \(\mathbf Q_t\), external runoff/input \(\mathbf R_t\), and unresolved volume term \(\mathbf \Xi_t^S\):

\[
\boxed{
\mathbf S_{t+\Delta t}
=
\mathbf S_t
+
\mathbf R_t
+
\Delta t B_G \mathbf Q_t
+
\mathbf \Xi_t^S
}
\tag{4}
\]

The stage-storage bridge at node \(i\) is:

\[
\boxed{
H_i
=
\psi_i(S_i;\theta_i)
}
\tag{5}
\]

and an edge relation is:

\[
\boxed{
Q_e
\in
\Phi_e
\left(
\Delta H_e,\,
U_e,\,
\theta_e
\right)
}
\tag{6}
\]

where \(\Phi_e\) may be set-valued when the hydraulic relation is incompletely known.

Equation (6) prevents the common collapse:

\[
\boxed{
\text{water-level difference}
\neq
\text{known discharge}
}
\tag{7}
\]

---

# 4. Evidence architecture

## 4.1 Government/public information products are typed

A disaster system does not receive “data” as one undifferentiated object. Each product must retain its semantic class:

\[
\boxed{
p
\in
\{
OBSERVATION,\,
FORECAST,\,
WARNING,\,
INSTRUCTION,\,
ACTION,\,
REFERENCE,\,
FIELD\_EVIDENCE
\}
}
\tag{8}
\]

For evidence item \(j\):

\[
\boxed{
E_j
=
\left\langle
id,\,
source,\,
agency,\,
p,\,
variable,\,
value,\,
unit,\,
support,\,
datum,\,
t_{obs},\,
t_{pub},\,
uncertainty,\,
freshness,\,
quality,\,
lineage
\right\rangle
}
\tag{9}
\]

This yields:

\[
\boxed{
Observation
\neq
Forecast
\neq
Warning
\neq
Instruction
\neq
Action
}
\tag{10}
\]

## 4.2 Measurement relation

A direct observation channel \(m\) may be represented as:

\[
\boxed{
Y_{m,t}
=
h_m(X_t;\theta_m)
+
\nu_{m,t}
}
\tag{11}
\]

but a forecast is generated differently:

\[
\boxed{
Y^{fcst}_{m,t+k}
=
\mathcal M_m(E_{\le t},B_{\le t})
}
\tag{12}
\]

and a warning is a policy/institutional product:

\[
\boxed{
Y^{warn}_{m,t}
=
\mathcal W_m(E_{\le t},Policy_m)
}
\tag{13}
\]

Therefore a severe warning may coexist with a normal local gauge because the two products refer to different semantic layers.

---

# 5. Evidence quality and contradiction

## 5.1 Freshness is necessary but not sufficient

For evidence \(j\):

\[
age_j(t)=t-t_{obs,j}
\tag{14}
\]

and:

\[
Fresh_j(t)
=
\mathbf 1
\left[
age_j(t)\le\tau_j
\right].
\tag{15}
\]

However:

\[
\boxed{
FRESH
\not\Rightarrow
VALID
}
\tag{16}
\]

A sensor can emit a new timestamp while remaining physically stuck.

Define:

\[
Range_m(t,L)
=
\max_{\tau\in[t-L,t]}Y_m(\tau)
-
\min_{\tau\in[t-L,t]}Y_m(\tau)
\tag{17}
\]

and:

\[
StuckSuspect_m
=
\mathbf 1
\left[
Range_m\le\epsilon_m
\land
DynamicContext_m=1
\right].
\tag{18}
\]

`StuckSuspect` is not equivalent to `SensorFalse`; it is a quality state requiring cautious use.

## 5.2 Contradiction must be retained

If two licensed measurements impose incompatible state constraints:

\[
C(E_a)\cap C(E_b)=\varnothing,
\tag{19}
\]

the architecture produces:

\[
\boxed{
CONTRADICTION
}
\tag{20}
\]

rather than an unregistered mean.

This rule is important for multi-agency disaster systems in which independent official sources may disagree.

---

# 6. Joint information state and typed evidence assimilation

The v0.1 manuscript used \(B_t\subseteq\mathcal X\) as a set of admissible physical states. That object remains an anchor, but the general theory requires a larger information state because disasters can be uncertain not only physically but also topologically, socially, parametrically, and institutionally.

Define the latent joint disaster state:

\[
\boxed{
\chi_t=(G_t,X_t,Z_t,\Theta_t,\Gamma_t)
}
\tag{21}
\]

and the **joint admissible information state**

\[
\boxed{
\mathbb B_t
\subseteq
\mathcal G\times\mathcal X\times\mathcal Z\times\Theta\times\Gamma .
}
\tag{22}
\]

The earlier physical set is retained as a projection:

\[
\boxed{
B_t=Proj_X(\mathbb B_t).
}
\tag{23}
\]

This is an upgrade, not a retraction: the original \(B_t\) remains the physical component of a richer disaster information state.

## 6.1 Semantic assimilation is typed

\[
Type(E_j)\in\{OBS,FCST,WARN,INST,ACT,REF,FIELD\}.
\tag{24}
\]

Each type has a different legal target:

\[
\boxed{
\begin{aligned}
OBS &\rightarrow C_X \text{ or } C_Z,\\
FCST &\rightarrow C_{\mathcal W},\\
WARN &\rightarrow C_{\Gamma,P}\text{ and public-information state},\\
INST &\rightarrow C_{\Gamma,\mathcal U},\\
ACT &\rightarrow C_U\text{ or }C_G,\\
REF &\rightarrow \Theta,G,\Gamma,\\
FIELD &\rightarrow C_X\text{ or }C_Z\text{ with declared provenance.}
\end{aligned}
}
\tag{25}
\]

Therefore a forecast constrains future forcing; it does not become an observation. A warning changes the decision/information environment; it does not become the measured hazard. An action report constrains what an agency reports doing; it does not prove realized hydraulic performance.

\[
\boxed{
\mathbb B_t^{+}
=
\mathsf A(\mathbb B_t^{-},E_t;Type(E_t)).
}
\tag{26}
\]

If typed evidence is mutually incompatible with the current model, the output is:

\[
\boxed{MODEL\_EVIDENCE\_CONTRADICTION}
\tag{27}
\]

rather than an invented reconciled world.

---

# 7. Coupled disaster-system dynamics

DSVA distinguishes four intervention families:

\[
\boxed{
u_t=(u_t^H,u_t^I,u_t^P,u_t^S)
}
\tag{28}
\]

where \(H\)=physical/hydraulic, \(I\)=information, \(P\)=protective, and \(S\)=structural.

\[
\boxed{
X_{t+1}
\in
F_X(X_t,G_t,u_t^H,u_t^S,w_t;\Theta_t)\oplus\Xi_t^X
}
\tag{29}
\]

\[
\boxed{
E_{t+1}
=
F_E(E_{\le t},X_{t+1},Z_{t+1},u_t^I,\nu_{t+1})
}
\tag{30}
\]

\[
\boxed{
Z_{t+1}
\in
F_Z(Z_t,X_{t+1},u_t^P,u_t^S,\omega_t)
}
\tag{31}
\]

\[
\boxed{
G_{t+1}=F_G(G_t,u_t^S)
}
\tag{32}
\]

\[
\boxed{
\Gamma_{t+1}
=
F_\Gamma(\Gamma_t,u_t,\omega_t^\Gamma).
}
\tag{33}
\]

The operators need not share a time scale:

\[
\boxed{
L(u^I),L(u^H),L(u^P),L(u^S)
\text{ are explicitly represented rather than assumed equal.}
}
\tag{34}
\]

---

# 8. Joint viability

\[
\boxed{
\mathcal K
=
\left\{
\chi:
g_j(\chi)\le0\quad\forall j
\right\}.
}
\tag{35}
\]

Constraints may encode physical hazard limits, minimum storage or water supply, contamination bounds, safe occupancy, route viability, essential-service continuity, support accessibility, environmental requirements, and institutional hard constraints. Success is therefore not minimization of one physical variable.

---

# 9. Evidence-bounded adaptive policy viability

The v0.1 common-action intersection is retained as an open-loop anchor. The general theory strengthens it to adaptive policy viability.

\[
\mathcal I_k=(E_{\le k},A_{<k},\mathbb B_k).
\tag{36}
\]

An adaptive policy is:

\[
\boxed{
\pi_k:\mathcal I_k\rightarrow\mathcal U_k^{feasible}.
}
\tag{37}
\]

The **Evidence-Bounded Viable Policy Set** is:

\[
\boxed{
\Pi_H^{EB}(\mathbb B_t)
=
\left\{
\pi:
\forall \chi_t\in\mathbb B_t,\;
\forall w_{t:t+H}\in\mathcal W_H,\;
\chi_\tau^\pi\in\mathcal K
\;\forall\tau\in[t,t+H]
\right\}.
}
\tag{38}
\]

This is the formal core of DSVA: a policy is disaster-viable only if it keeps every currently admissible world inside declared viability constraints across the declared disturbance set, while allowing later actions to respond to later evidence.

The actions justified **now** are the first-action projection:

\[
\boxed{
\mathcal A_H^{EB}(\mathbb B_t)
=
\left\{
\pi_t(\mathcal I_t):
\pi\in\Pi_H^{EB}(\mathbb B_t)
\right\}.
}
\tag{39}
\]

The original v0.1 equation remains as the open-loop special case:

\[
\boxed{
\mathcal U_H^{EB}
=
\bigcap_{x\in B_t}
\mathcal U_H^{safe}(x)
\quad
\text{when future evidence cannot change policy.}
}
\tag{40}
\]

---

# 10. Viability horizon and decision clocks

\[
\boxed{
T_V(\mathbb B_t)
=
\sup\left\{
H:\Pi_H^{EB}(\mathbb B_t)\neq\varnothing
\right\}.
}
\tag{41}
\]

DSVA distinguishes:

\[
\boxed{
T_{forecast}\neq T_V\neq T_{action}\neq T_{recovery}.
}
\tag{42}
\]

A forecast horizon, viable-management horizon, action-justification horizon, and recovery horizon are different clocks.

---

# 11. Feasible actuation and governance

\[
\boxed{
\mathcal U_t^{feasible}
=
\left\{
u:
Authority(u,\Gamma_t)=1,\;
Resource(u,t)=1,\;
Latency(u)\le H,\;
OperationalCondition(u)=1
\right\}.
}
\tag{43}
\]

Hence:

\[
\boxed{
InstalledCapability
\neq
ExecutableCapability
\neq
RealizedPerformance.
}
\tag{44}
\]

Governance enters through the action set, latency, information access, coordination structure, legal authority, and resource availability.

---

# 12. Unified intervention-value and bottleneck calculus

A bottleneck is not defined by the smallest component alone; it is the intervention whose feasible relaxation most expands viable future space.

\[
\boxed{
\mathcal V_q(\delta_q)
=
T_V(\mathcal M\oplus\delta_q)-T_V(\mathcal M).
}
\tag{45}
\]

\[
\boxed{
\mathcal V_q^{net}
=
\frac{
T_V(\mathcal M\oplus\delta_q)-T_V(\mathcal M)
}{
Cost(\delta_q)+\epsilon
}.
}
\tag{46}
\]

Parallel bottleneck classes follow:

\[
\boxed{
b_H^\ast=\arg\max_{\delta_H}\mathcal V_H^{net},
\quad
b_I^\ast=\arg\max_{\delta_I}\mathcal V_I^{net},
\quad
b_P^\ast=\arg\max_{\delta_P}\mathcal V_P^{net},
\quad
b_\Gamma^\ast=\arg\max_{\delta_\Gamma}\mathcal V_\Gamma^{net}.
}
\tag{47}
\]

The binding limitation may therefore be physical, epistemic, protective, or institutional.

## 12.1 Ex-ante value of information

Probabilistic form:

\[
\boxed{
VOI(m)
=
\mathbb E_{y\sim p(y|\mathbb B_t)}
[T_V(\mathbb B_t^y)]
-
T_V(\mathbb B_t)
-
Cost(m).
}
\tag{48}
\]

Set-based worst-case form:

\[
\boxed{
VOI^{wc}(m)
=
\inf_{y\in Y_m(\mathbb B_t)}
T_V(\mathbb B_t^y)
-
T_V(\mathbb B_t)
-
Cost(m).
}
\tag{49}
\]

Information is valuable when it changes viable policy/action space, not merely when it produces more data.

---

# 13. Human, service, and recovery state

FloodConnect's human-operational vector remains a core DSVA anchor:

\[
\boxed{
Z_i(t,T)=(O,F,M,S,E,H,A,P).
}
\tag{50}
\]

\[
\boxed{
PhysicalRecovery\neq HumanRecovery
}
\tag{51}
\]

\[
\boxed{
RoadClear\not\Rightarrow CommunityRecovered.
}
\tag{52}
\]

\[
\boxed{
T_R
=
\inf\{\tau>0:\chi_{t+\tau}\in\mathcal K\}.
}
\tag{53}
\]

---

# 14. Decision rule without a universal risk score

\[
\boxed{
a_t^\ast
\in
\arg\max_{a\in\mathcal A_H^{EB}(\mathbb B_t)}
T_V(\mathbb B_t^{+a})
}
\tag{54}
\]

subject to declared hard constraints.

Where objectives conflict:

\[
\boxed{
\operatorname{lexmin}
(
LifeSafetyLoss,
RouteFailure,
CriticalServiceLoss,
ViabilityLoss,
RecoveryTime,
OperatingCost
).
}
\tag{55}
\]

---

# 15. Axioms, reductions, and theorems

DSVA separates constitutional rules, definitions, mathematical consequences, and empirical hypotheses.

## Axiom A1 — Semantic non-collapse

\[
OBS\neq FCST\neq WARN\neq INST\neq ACT.
\tag{56}
\]

## Axiom A2 — Unknown is not safe

\[
UNKNOWN\not\Rightarrow SAFE.
\tag{57}
\]

## Axiom A3 — Missing is not zero

\[
MISSING\not\Rightarrow 0.
\tag{58}
\]

## Theorem T1 — Evidence refinement monotonicity

Assume a valid evidence update excludes no true state and has zero harmful latency/cost. If:

\[
\mathbb B'_t\subseteq\mathbb B_t,
\tag{59}
\]

then:

\[
\boxed{
\Pi_H^{EB}(\mathbb B'_t)
\supseteq
\Pi_H^{EB}(\mathbb B_t)
}
\tag{60}
\]

and:

\[
\boxed{
T_V(\mathbb B'_t)\ge T_V(\mathbb B_t).
}
\tag{61}
\]

**Proof sketch.** Every policy viable for every state in the larger admissible set is viable for every state in its subset. Any cost or latency of obtaining the information is represented separately in the coupled dynamics.

## Theorem T2 — Feasible-action expansion monotonicity

If:

\[
\mathcal U_t^{feasible}\subseteq{\mathcal U'}_t^{feasible}
\tag{62}
\]

without worsening dynamics or constraints, then:

\[
\boxed{
T'_V\ge T_V.
}
\tag{63}
\]

## Theorem T3 — Known-state reduction

If:

\[
\mathbb B_t=\{\chi_t\}
\tag{64}
\]

and future observations add no decision-relevant information, DSVA reduces to a robust controlled-viability/invariance problem:

\[
\Pi_H^{EB}
=
\left\{
\pi:
\forall w\in\mathcal W_H,\;
\chi_\tau^\pi\in\mathcal K
\right\}.
\tag{65}
\]

## Theorem T4 — Open-loop reduction

If policy cannot depend on future evidence:

\[
\pi_k(\mathcal I_k)=u_k\quad\forall k,
\tag{66}
\]

then Eq. (38) reduces to the original common safe action-sequence intersection of DSVA v0.1. The previous manuscript is therefore retained as an explicit subtheory.

---

# 16. Empirical propositions and falsifiers

### P1 — Feasible-futures proposition
Disaster management is better represented by viable future trajectories and policies than by a single point-state estimate.

### P2 — Capacity non-additivity proposition
Installed component capacities do not generally equal realized system capacity under network, storage, boundary, and control constraints.

### P3 — Adaptive common-policy proposition
Partial observability is operationally tolerable while at least one evidence-bounded viable adaptive policy remains:

\[
\Pi_H^{EB}(\mathbb B_t)\neq\varnothing.
\]

### P4 — Operational information-value proposition
Decision-relevant information increases management capability when it expands \(\Pi_H^{EB}\), expands \(\mathcal A_H^{EB}\), or increases \(T_V\) after accounting for cost and latency.

### P5 — Multi-bottleneck proposition
The intervention with greatest viability gain may be physical, epistemic, protective, or institutional.

### P6 — Human non-collapse proposition
Physical or infrastructure recovery is not sufficient to establish human/service recovery.

### P7 — Reversibility proposition
When irreversible-action losses are high, reversible preparation and information actions can become justified under a broader admissible-state set than irreversible movement or shutdown actions.

### P8 — Semantic evidence proposition
Observation, forecast, warning, instruction, action report, and realized outcome are not mutually substitutable without an explicit typed transformation.

## Falsification program

DSVA is challenged when, after measurement and model error are controlled:

1. system throughput is consistently predicted by simple installed-capacity addition despite network/boundary/control structure;
2. information refinement systematically fails to change or preserve viable policy space in cases where state-dependent actions differ;
3. institutional actuation never changes feasible policy space across independent emergencies;
4. physical recovery consistently coincides with full mobility, service, occupancy, and support recovery;
5. typed evidence separation provides no measurable reduction in false inference or action error;
6. cross-hazard instantiations cannot be represented without abandoning the root objects \((\mathbb B,\mathcal K,\Pi^{EB},T_V,Z,\Gamma)\).

---

# 17. Thailand as a full-system empirical stress environment

Thailand is not introduced merely as a local case. It provides a demanding empirical environment for a general disaster-management theory because the operational problem is distributed across physical networks, multiple public institutions, heterogeneous data products, different update cadences, and different semantic classes of public information.

For Bangkok flooding, the relevant evidence ecology includes:

- **Thai Meteorological Department (TMD):** meteorological observation, radar, forecast and nowcast;
- **Royal Irrigation Department (RID):** upstream river/reservoir conditions and operational water management;
- **Bangkok Metropolitan Administration, Department of Drainage and Sewerage (BMA DDS):** urban canals, pump stations, gates, road flooding, drainage operations and retention/monkey-cheek facilities;
- **Hydro-Informatics Institute / ThaiWater:** public water-data integration and APIs used by FloodConnect;
- **Royal Thai Navy Hydrographic Department:** astronomical tide predictions and hydrographic reference;
- **ONWR/DDPM and local authorities:** warning/governance/emergency-management context;
- **community and field evidence:** local effects, route conditions, service loss, support needs and lived recovery.

These sources do not describe the same object. DSVA therefore treats Thailand's public-data environment as a real test of typed evidence rather than as a single fused "government data" stream.

## 17.1 Bangkok 2026 event as a theory stress test

FloodConnect's audited reconstruction of the September–October 2026 Bangkok flood records a combination of factors that cannot be represented adequately by a single-variable flood narrative:

- eastern retention need was reported around **13 million m³** against about **7.64 million m³** available in the cited baseline;
- a point rainfall total reached **230.5 mm/day**;
- upstream discharge at C.2 was reported around **1,795 m³/s on 25 September** and **2,565 m³/s on 30 September**;
- high-tide conditions were warned for the late-September/early-October period;
- additional pumps were deployed, including a reported **221 support pumps / ~97 million m³/day** support-capacity snapshot, without that number being equivalent to realized Bangkok net export;
- **109 road-flood points across 30 districts** were reported at one event stage;
- road recession and community recovery were uneven: major roads could improve while low-lying communities remained flooded.

The event therefore instantiates:

\[
\boxed{
Rainfall
\neq Storage
\neq UpstreamBoundary
\neq ReceivingBoundary
\neq InstalledPumpCapacity
\neq RealizedExport
\neq RoadState
\neq CommunityRecovery.
}
\tag{67}
\]

## 17.2 Thailand's multi-agency evidence ecology

\[
\boxed{
E_t^{TH}
=
E_t^{TMD}
\cup
E_t^{RID}
\cup
E_t^{BMA}
\cup
E_t^{HII}
\cup
E_t^{NAVY}
\cup
E_t^{GOV}
\cup
E_t^{FIELD}.
}
\tag{68}
\]

The union is not an arithmetic merge. Each element enters through the typed assimilation rules of Eq. (25).

---

# 18. Sammakorn as a compact empirical instantiation

Sammakorn in eastern Bangkok is the first compact empirical world for DSVA because it contains storage, internal transfer, terminal export, receiving-water dependence, public observations, pump/control uncertainty, road/community consequences, and institutional boundaries in one tractable system.

\[
\boxed{
Rain
\rightarrow
Retention
\leftrightarrow
InternalTransfer
\rightarrow
TerminalExport
\rightarrow
ReceivingWater.
}
\tag{69}
\]

\[
\boxed{
Observation
\rightarrow
TypedEvidence
\rightarrow
\mathbb B_t
\rightarrow
\Pi_H^{EB}
\rightarrow
\mathcal A_H^{EB}
\rightarrow
Action.
}
\tag{70}
\]

FloodConnect preserves local hydraulic topology as partially verified. Four pump stations ST.SPS.01–04 are represented, while exact internal geometry, several flow directions, stage-storage functions, realized pump discharge, and some receiving-water boundaries remain open. That incompleteness is the condition DSVA is designed to manage.

## 18.1 Local water balance

\[
\boxed{
S_{t+\Delta t}
=
S_t
+
V^{rain}
+
V^{up}
+
V^{surface}
+
V^{back}
-
V^{gravity}
-
V^{pump}
-
V^{other}.
}
\tag{71}
\]

Every undeclared term remains unresolved rather than being replaced by zero.

## 18.2 Stage-storage and export

\[
H_i=\psi_i(S_i;\theta_i)
\tag{72}
\]

\[
Q_e\in\Phi_e(\Delta H_e,U_e,\theta_e).
\tag{73}
\]

\[
\boxed{
WaterLevelDifference\neq KnownDischarge.
}
\tag{74}
\]

## 18.3 Export window

\[
\boxed{
\Delta H_{out}=H_{SMK}-H_{receiver}.
}
\tag{75}
\]

\[
\boxed{
C_{out}^{feasible}
=
\Phi(
\Delta H_{out},
PumpState,
GateState,
DownstreamState
).
}
\tag{76}
\]

The same installed pump configuration can therefore have different realized effectiveness under different receiving-water conditions.

---

# 19. Worked Thailand government-data interfaces

The purpose is not merely reproducibility. It demonstrates how a national/local public-data ecology is translated into a general disaster information state.

## 19.1 BMA / ThaiWater canal observations

Public endpoint:

    https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel

Mapped variables include canal water level, warning level, critical level, bank level, and gate-side/outside level where exposed.

\[
\boxed{
E^{canal}\rightarrow OBS\rightarrow C_X.
}
\tag{77}
\]

Compatible inside/outside levels can support:

\[
\Delta H=H_{inside}-H_{outside},
\tag{78}
\]

but not an uncalibrated discharge claim.

## 19.2 BMA PumpHistory

Public interface:

    https://weather.bangkok.go.th/Station/PumpHistory

FloodConnect extracts, where present, level, pumps on/total, gate opening and station status.

\[
\boxed{
E^{pump}\rightarrow OBS/ACT\rightarrow C_U.
}
\tag{79}
\]

\[
\boxed{
pumps\_on\neq actual\_pump\_discharge.
}
\tag{80}
\]

\[
Q_p=u_p\eta_p\Gamma_p(\Delta H_p).
\tag{81}
\]

## 19.3 BMA / ThaiWater road flooding

Public endpoint:

    https://api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road

\[
\boxed{
E^{road}\rightarrow(C_X,C_Z).
}
\tag{82}
\]

A road observation is therefore simultaneously local physical evidence and a mobility consequence.

## 19.4 Bangkok monkey-cheek retention system

Public BMA interface:

    https://monkeycheek.bangkok.go.th/listmongkeycheeks

The public page lists **37 retention/monkey-cheek facilities** and includes:

    027 — บึงรับน้ำหมู่บ้านสัมมากร — เขตสะพานสูง

At the checked snapshot the page displayed:

    current water-level percentage = 51.00
    data timestamp = 16 July 2026 10:03:01

DSVA derives two refusal rules:

\[
\boxed{
51\%\not\Rightarrow S=0.51S^{max}
}
\tag{83}
\]

until the denominator/measurement transformation is documented, and:

\[
\boxed{
GovernmentSource\not\Rightarrow FreshOperationalObservation.
}
\tag{84}
\]

## 19.5 TMD nowcasting

TMD SATDA provides Bangkok/metropolitan short-range rainfall nowcasting, including a 180-minute horizon with frequent updates.

\[
\boxed{
P^{TMD}_{fcst}\rightarrow FCST\rightarrow C_{\mathcal W}.
}
\tag{85}
\]

It contracts the future forcing set; it does not become observed rain.

## 19.6 RID reservoir/public API

Example documented endpoint:

    https://app.rid.go.th/reservoir/api/dam/public

\[
\boxed{
R_d(t)=(V_d,I_d,O_d,S_d)
\rightarrow
OBS/REF
\rightarrow
C_X,C_{\mathcal W}.
}
\tag{86}
\]

For Sammakorn, reservoir data inform upstream context only through an explicit routing/propagation relation.

## 19.7 Royal Thai Navy Hydrographic tide products

\[
\boxed{
H_{tide}^{pred}
\rightarrow
FCST
\rightarrow
C_{\mathcal W}.
}
\tag{87}
\]

\[
\boxed{
H_{tide}^{pred}\neq H_{receiver}^{obs}.
}
\tag{88}
\]

## 19.8 Thailand evidence-to-action stack

    TMD forecast / nowcast
            +
    RID upstream / reservoir evidence
            +
    BMA/ThaiWater canal + road observations
            +
    BMA pump/gate state
            +
    BMA monkey-cheek retention reference/observation
            +
    Navy tide prediction
            +
    field/community evidence
                     ↓
           typed evidence contract
                     ↓
     freshness / datum / sensor / contradiction QC
                     ↓
             joint information state 𝔅_t
                     ↓
          adaptive viable policy set Π_H^EB
                     ↓
          current justified actions 𝒜_H^EB
                     ↓
     hydraulic + human + institutional response

This is the explicit Thailand-to-general-theory bridge.

---

# 20. Advice before precise prediction

DSVA makes a strong claim: a disaster system can produce justified action before it can produce a precise local hazard trajectory.

Suppose:

\[
H>H^{crit},
\quad Trend=RISING,
\quad Route=UNKNOWN.
\tag{89}
\]

A route-dependent evacuation recommendation is not licensed because route safety is unresolved. But preparation, route verification, support mobilization, or assisted-evacuation requests for households already failing occupancy constraints may be licensed.

Likewise:

\[
Trend=FALLING\land H>H^{crit}
\tag{90}
\]

does not imply all-clear.

\[
\boxed{
Advice_t
=
StrongestAction(
\mathcal A_H^{EB}(\mathbb B_t)
).
}
\tag{91}
\]

# 21. Dialogue with world theories after DSVA is constructed

External theories enter DSVA through:

\[
\boxed{
\phi_j:\mathcal T_j\rightarrow\mathcal T^{DSVA}.
}
\tag{92}
\]

\[
\boxed{
Role(\mathcal T_j)
\in
\{
SPECIAL\ CASE,
SOLVER,
OPERATOR,
PARAMETERIZATION,
BOUNDARY,
RIVAL
\}.
}
\tag{93}
\]

The dialogue is equation-to-equation rather than vocabulary-to-vocabulary.

## 21.1 Viability theory and controlled invariance

Classical viability theory (Aubin, Bayen, & Saint-Pierre, 2011) enters as a **SPECIAL CASE** through Theorem T3:

\[
\mathbb B_t=\{\chi_t\}
\Rightarrow
DSVA\rightarrow KnownStateViability.
\tag{94}
\]

DSVA keeps typed evidence, evolving information state, adaptive information actions, human/service state, and constrained institutional actuation explicit.

## 21.2 POMDP and belief-state decision making

POMDP theory formalizes decisions when the state is hidden and actions depend on observation history (Kaelbling, Littman, & Cassandra, 1998; Chadès et al., 2021).

\[
\boxed{
POMDP
\mapsto
SOLVER/PARAMETERIZATION
}
\tag{95}
\]

when the set-valued information state \(\mathbb B_t\) is represented probabilistically as a belief \(b_t(\chi)\). DSVA also permits non-probabilistic set-valued states when defensible probabilities are unavailable.

## 21.3 Set-membership estimation

\[
\boxed{
SetMembership
\mapsto
Estimator/UpdateOperator(\mathbb B_t).
}
\tag{96}
\]

This supplies a computational family for evidence-bounded state construction without determining human or institutional viability semantics.

## 21.4 Real-time control and model predictive control

Urban drainage RTC and MPC are mature traditions for controlling large dynamic drainage systems (García et al., 2015; Lund et al., 2018; Castelletti et al., 2023).

\[
\boxed{
MPC/RTC
\mapsto
Solver(
\Pi_H^{EB}\mid F_X,\mathcal K,\mathcal W
).
}
\tag{97}
\]

They solve an internal control problem after DSVA has determined what evidence, constraints, and actuation semantics are admissible.

## 21.5 Robust decision making

\[
\boxed{
RobustDecision
\mapsto
Solver(
\mathbb B_t\times\mathcal W_H
).
}
\tag{98}
\]

This directly converses with the universal quantifiers in Eq. (38).

## 21.6 Value of information

Value-of-information analysis in engineering evaluates whether monitoring/inspection changes expected decision value; sequential formulations use MDP/POMDP structures (Zhang et al., 2021).

\[
\boxed{
VOI
\mapsto
InformationInterventionValue.
}
\tag{99}
\]

DSVA values information by its effect on viable future/action space.

## 21.7 Formal natural-hazard warning decision theory

Bayesian decision theory has been applied directly to natural-hazard warnings, mapping predictive information and loss functions into warning actions (Economou et al., 2016).

\[
\boxed{
WarningDecisionTheory
\mapsto
Solver(
FCST,Loss,u^P
).
}
\tag{100}
\]

DSVA retains:

\[
WARNING\neq OBSERVATION\neq PROTECTIVE\_OUTCOME.
\]

## 21.8 Digital twins

\[
\boxed{
DigitalTwin
\mapsto
Implementation(
E\rightarrow\mathbb B\rightarrow F\rightarrow Reader
).
}
\tag{101}
\]

A twin can instantiate DSVA but does not replace its semantic and viability constraints.

## 21.9 Disaster resilience

\[
\boxed{
Resilience
\mapsto
(\mathcal K,T_V,T_R,Z).
}
\tag{102}
\]

DSVA insists that physical and human/service recovery remain typed and separately measurable.

## 21.10 Sendai Framework

The Sendai priorities map naturally:

    Understand disaster risk       → E, 𝔅
    Strengthen risk governance     → Γ
    Invest in resilience           → u^S, K
    Enhance preparedness/response  → u^P, Z, Π_H^EB

Sendai is therefore a **BOUNDARY / policy architecture** for the DSVA decision universe, not a competing state-transition equation (UNDRR, 2015; 2023).

## 21.11 Integrated water resources management

\[
\boxed{
IWRM
\mapsto
Boundary/ConstraintArchitecture(\mathcal K,\Gamma).
}
\tag{103}
\]

## 21.12 Residual synthesis

\[
\boxed{
\Delta^{DSVA}
=
\mathcal T^{DSVA}
-
\bigcup_j\phi_j(\mathcal T_j).
}
\tag{104}
\]

The DSVA research program asks whether the residual architecture—joint physical/epistemic/human/institutional viability governed by adaptive evidence-bounded policies and one intervention-value calculus—continues to explain and predict decision structure across hazards better than any single imported tradition.

# 22. Inside-out synthesis rule

DSVA adopts the following methodological rule:

\[
\boxed{
\textbf{
We do not assemble the theory from existing theories.
We construct the theory from the disaster phenomenon,
then require existing theories to declare what they become
inside the equation system.
}
}
\tag{72}
\]

External familiarity cannot become an internal premise.

An external construct enters only after one of three tests:

1. **Reduction:** Is it already a special case of DSVA?
2. **Extension:** Does it explain an observable phenomenon not representable by DSVA?
3. **Rivalry:** Does it make incompatible predictions about the same phenomenon?

This prevents vocabulary accumulation from being mistaken for theory building.

---

# 23. Research design and validation program

A theory of disaster management should be tested at multiple layers.

## 23.1 Structural validation

Ask whether the topology, state variables, evidence classes, control objects, and human states correspond to the actual system.

## 23.2 Equation validation

For flood applications, test:

- mass-balance residual;
- stage-storage relation;
- edge-direction consistency;
- pump-flow relation;
- downstream-boundary sensitivity;
- storage/export bottleneck.

## 23.3 Forecast validation

Separate:

\[
F_0=\text{current-state nowcast}
\]

\[
F_1=\text{directional forecast}
\]

\[
F_2=\text{threshold/clearance interval}
\]

\[
F_3=\text{quantitative local hydraulic forecast}.
\]

Do not claim a higher level merely because a lower level is operationally useful.

## 23.4 Advice validation

Measure:

- preparation lead time;
- local-action lead time;
- false-action burden;
- verified-route validity;
- support coverage;
- missed vulnerable households;
- emergency escalation;
- time to recovery of critical service.

## 23.5 Multi-event validation

A single flood can demonstrate coherence but cannot establish general predictive performance.

The next stage requires prospective or anti-hindsight replay across independent events, followed by cross-hazard testing.

---

# 24. Implications for disaster management

DSVA changes several practical questions.

Instead of:

> What is the water level?

ask:

> What states are still possible, and do they require different actions?

Instead of:

> How many pumps are running?

ask:

> What is the feasible system export under current receiving boundaries?

Instead of:

> Do we need more sensors?

ask:

> Which missing observation would most change viable action?

Instead of:

> Has the road dried?

ask:

> Has joint physical-human viability been restored?

Instead of:

> Which model is most accurate?

ask:

> Is the model accurate enough for the decision reader currently being asked to emit?

This is a shift from **state prediction** toward **decision-licensed viability management**.

---

# 25. Limitations

This manuscript has several explicit limits.

First, DSVA makes a general-theory claim at the level of architecture, equation ordering, reductions, and joint intervention calculus; it does not require every constituent mathematical operator to be individually unprecedented.

Second, the Sammakorn example remains partially observed. Internal hydraulic geometry, stage-storage relations, realized pump discharge, and some receiving-water boundaries remain incomplete.

Third, robust set-based formulations may become computationally expensive in large systems. Practical implementations may require interval, ensemble, probabilistic, reduced-order, or optimization approximations.

Fourth, institutional variables are difficult to quantify. Equation (31) should not create false numerical precision where authority or organizational capacity is only qualitatively known.

Fifth, the human state \(Z_t\) requires ethical and empirical validation; it must not become a covert social-risk score.

Sixth, cross-hazard generalization is a hypothesis. A theory developed from urban flooding must be tested against hazards with different temporal scales, spatial structures, and action regimes.

---

# 26. Conclusion

This paper proposes a synthesis-first architecture for disaster management.

Its root claim is not that disasters can be reduced to one model. It is the opposite: physically different, epistemically different, institutionally different, and humanly different objects must remain distinct long enough to be connected correctly.

The core architecture is:

\[
\boxed{
\chi_t
\rightarrow
E_t
\rightarrow
\mathbb B_t
\rightarrow
\Pi_H^{EB}
\rightarrow
\mathcal A_H^{EB}
\rightarrow
T_V
\rightarrow
Z_t
\rightarrow
Action.
}
\tag{73}
\]

The central operational thesis is:

\[
\boxed{
\textbf{
Disaster management is the preservation and recovery of viable futures
through coordinated physical control, information acquisition,
protective action, and structural change under partial observability
and constrained actuation.
}
}
\tag{74}
\]

And the central practical implication is:

\[
\boxed{
\textbf{
The limiting resource in disaster management is not always physical capacity;
sometimes it is the ability to know which action remains safe.
}
}
\tag{75}
\]

Sammakorn provides a compact empirical world in which this claim can be progressively closed with real public data. FloodConnect provides the executable environment in which the distinctions can be preserved, tested, falsified, and extended.

---

# 27. Reproducibility and FloodConnect integration

This manuscript is designed to live with the executable repository rather than as an isolated conceptual paper.

Relevant FloodConnect artifacts include:

```text
sources/registry.yaml
collect.py
parsers.py
store.py
readout.py
live_water_level.py
water_balance.py
canal_graph.py
burden_ledger.py
hierarchical_flood_zoom.py
raw_stage_forecast.py
unified_crisis_state.py
site/inputs/canals/sammakorn_pond_canal_dag.yaml
site/inputs/areas/sammakorn.balance.yaml
experiments/2026-09-26-sammakorn-7day-backtest.md
experiments/2026-09-bangkok-hierarchical-real-run.md
experiments/2026-09-bangkok-toledo-real-backtest.md
```

The manuscript is the canonical `PROPOSAL / THEORY_SYNTHESIS` expression of DSVA inside FloodConnect. Its general-theory claim is preserved; operational deployment remains separately gated by source freshness, model validation, and reader-specific evidence requirements.

Every equation intended for operational use must eventually map to:

```text
source → parser → normalized evidence → QC → model/readout → test
```

and every unresolved input must remain explicitly unresolved.

---

# References

1. United Nations Office for Disaster Risk Reduction (UNDRR). (2015). *Sendai Framework for Disaster Risk Reduction 2015–2030*. United Nations.

2. Aubin, J.-P., Bayen, A. M., & Saint-Pierre, P. (2011). *Viability Theory: New Directions*. Springer. https://doi.org/10.1007/978-3-642-16684-6

3. García, L., Barreiro-Gomez, J., Escobar, E., Téllez, D., Quijano, N., & Ocampo-Martínez, C. (2015). Modeling and real-time control of urban drainage systems: A review. *Advances in Water Resources, 85*, 120–132. https://doi.org/10.1016/j.advwatres.2015.08.007

4. Lund, N. S. V., Falk, A. K. V., Borup, M., Madsen, H., & Mikkelsen, P. S. (2018). Model predictive control of urban drainage systems: A review and perspective towards smart real-time water management. *Critical Reviews in Environmental Science and Technology, 48*(3), 279–339. https://doi.org/10.1080/10643389.2018.1455484

5. Castelletti, A., Ficchì, A., Cominola, A., Segovia, P., Giuliani, M., Wu, W., Lucia, S., Ocampo-Martinez, C., De Schutter, B., & Maestre, J. M. (2023). Model Predictive Control of water resources systems: A review and research agenda. *Annual Reviews in Control, 55*, 442–465. https://doi.org/10.1016/j.arcontrol.2023.03.013

6. Oh, J., & Bartos, M. (2023). Model predictive control of stormwater basins coupled with real-time data assimilation enhances flood and pollution control under uncertainty. *Water Research, 235*, 119825. https://doi.org/10.1016/j.watres.2023.119825

7. Chen, Y., Wang, C., Yang, Q., Lei, X., Wang, H., Jiang, S., & Wang, Z. (2024). Model predictive control and rainfall uncertainties: Performance and risk analysis for drainage systems. *Journal of Hydrology, 630*, 130779. https://doi.org/10.1016/j.jhydrol.2024.130779

8. Lempert, R. J., & Groves, D. G. (2010). Identifying and evaluating robust adaptive policy responses to climate change for water management agencies in the American west. *Technological Forecasting and Social Change, 77*(6), 960–974. https://doi.org/10.1016/j.techfore.2010.04.007

9. Macatulad, E., & Biljecki, F. (2024). Continuing from the Sendai Framework midterm: Opportunities for urban digital twins in disaster risk management. *International Journal of Disaster Risk Reduction, 102*, 104310. https://doi.org/10.1016/j.ijdrr.2024.104310

10. Lagap, U., & Ghaffarian, S. (2024). Digital post-disaster risk management twinning: A review and improved conceptual framework. *International Journal of Disaster Risk Reduction, 110*, 104629. https://doi.org/10.1016/j.ijdrr.2024.104629

11. Global Water Partnership. *Integrated Water Resources Management* definition and principles.

12. Food and Agriculture Organization of the United Nations (FAO). *Integrated Water Resources Management*.

13. Bangkok Metropolitan Administration, Department of Drainage and Sewerage. Public canal, pump, road-flood, flood-report, and monkey-cheek data products used by FloodConnect.

14. Hydro-Informatics Institute / ThaiWater. Public canal-water, road-flood, and rainfall data services used by FloodConnect.

15. Thai Meteorological Department. SATDA rainfall-radar and Bangkok/metropolitan 180-minute nowcasting public products.

16. Royal Irrigation Department. Public reservoir API documentation: storage, inflow, outflow, and related reservoir variables.

17. Royal Thai Navy Hydrographic Department. *Tide Tables in Thai Waters 2026*, including Bangkok and Pak Nam Bang Pakong stations.


18. Kaelbling, L. P., Littman, M. L., & Cassandra, A. R. (1998). Planning and acting in partially observable stochastic domains. *Artificial Intelligence, 101*, 99–134. https://doi.org/10.1016/S0004-3702(98)00023-X

19. Chadès, I., Chapron, G., Cros, M.-J., Garcia, F., & Sabbadin, R. (2021). A primer on partially observable Markov decision processes (POMDPs). *Methods in Ecology and Evolution*. https://doi.org/10.1111/2041-210X.13692

20. Zhang, W.-H., Lu, D.-G., Qin, J., Faber, M. H., & Thöns, S. (2021). Value of information analysis in civil and infrastructure engineering: a review. *Journal of Infrastructure Preservation and Resilience, 2*, 16. https://doi.org/10.1186/s43065-021-00027-0

21. Papakonstantinou, K. G., & Shinozuka, M. (2014). Planning structural inspection and maintenance policies via dynamic programming and Markov processes. Part II: POMDP implementation. *Reliability Engineering & System Safety, 130*, 214–224. https://doi.org/10.1016/j.ress.2014.04.006

22. Memarzadeh, M., & Pozzi, M. (2016). Value of information in sequential decision making: Component inspection, permanent monitoring and system-level scheduling. *Reliability Engineering & System Safety, 154*, 137–151.

23. Economou, T., Stephenson, D. B., Rougier, J. C., Neal, R. A., & Mylne, K. R. (2016). On the use of Bayesian decision theory for issuing natural hazard warnings. *Proceedings of the Royal Society A, 472*(2194), 20160295. https://doi.org/10.1098/rspa.2016.0295

24. UNDRR. (2023). *Midterm Review of the Implementation of the Sendai Framework for Disaster Risk Reduction 2015–2030*. United Nations Office for Disaster Risk Reduction.

25. FloodConnect. (2026). *World-Tier Event Reconstruction Matrix — Bangkok Flood 2569, audited 2026-10-01*. Project research artifact.

26. FloodConnect. (2026). *Bangkok Flood 2569 Introduction / Event Reconstruction — audited 2026-10-01*. Project research artifact.

---

## Appendix A — Minimal executable DSVA reader

```python
def reader(question, admissible_states):
    if admissible_states is None:
        return ("REFUSED", "state set cannot be licensed")
    if len(admissible_states) == 0:
        return ("REFUSED", "model-evidence contradiction")

    answers = {question(x) for x in admissible_states}

    if len(answers) == 1:
        return ("DETERMINATE", next(iter(answers)))

    bound = admissible_bound(answers)
    if bound is not None:
        return ("INTERVAL", bound)

    return ("UNRESOLVED", None)
```

---

## Appendix B — Minimal evidence-bounded action pseudocode

```python
def evidence_bounded_safe_actions(B, Z, Gamma, horizon):
    common = None

    for x in B:
        safe = safe_actions(x, Z, Gamma, horizon)
        common = safe if common is None else common.intersection(safe)

        if not common:
            return set()

    return common
```

---

## Appendix C — Theory-dialogue mapping template

For every external theory or framework:

```yaml
external_theory: "..."
root_objects: [...]
mapping_into_dsva:
  - external_object: "..."
    dsva_object: "..."
role:
  one_of:
    - SPECIAL_CASE
    - SOLVER
    - OPERATOR
    - PARAMETERIZATION
    - BOUNDARY
    - RIVAL
reduction_test: "..."
unexplained_residual: "..."
decision: FOLD|EXTEND|KEEP_AS_RIVAL
```

This prevents literature vocabulary from silently becoming new ontology.