# Disaster-System Viability Architecture
## A Synthesis-First Theory of Evidence-Bounded Action under Partial Observability

**Standalone theory manuscript — Draft v0.1**  
**Date:** 1 October 2026  
**Field:** Disaster Risk Science / Disaster Management  
**Empirical demonstrator:** Sammakorn retention-and-drainage system, eastern Bangkok, Thailand  
**Software/reproducibility anchor:** FloodConnect (`morrocwi/floodconnect`)  
**Priority claim:** None required. The article treats architecture and synthesis as the unit of contribution; individual components are allowed to have established precedents.

---

## Abstract

Disaster management is commonly partitioned into hazard modelling, observation, forecasting, infrastructure control, warning, emergency decision making, governance, response, and recovery. The resulting analytical landscape is rich but fragmented: physical models often assume a sufficiently known state; control models commonly optimize within a declared system; warning systems focus on information products; disaster-management frameworks emphasize institutions and human outcomes; and resilience approaches examine loss and recovery at different scales. This article presents the **Disaster-System Viability Architecture (DSVA)** as a synthesis-first formal theory in which these activities become operators inside one equation system rather than separate frameworks that must later be combined.

DSVA begins from the disaster phenomenon rather than from a literature taxonomy. At time \(t\), the architecture distinguishes the latent physical state \(X_t\), retained evidence \(E_{\le t}\), the set \(B_t\) of physical states still admissible under evidence and physical constraints, a human-and-service state \(Z_t\), institutional and actuation constraints \(\Gamma_t\), and the set of feasible actions. Disaster management is defined as the preservation and recovery of **viable futures** rather than as the optimization of a single hazard variable. The central operational construct is the **evidence-bounded safe action set**,

\[
\mathcal U_H^{EB}(B_t,Z_t,\Gamma_t)
=
\bigcap_{x\in B_t}
\mathcal U_H^{safe}(x,Z_t,\Gamma_t),
\]

which contains actions that remain admissible across all currently possible states for a planning horizon \(H\). The corresponding **viability horizon**

\[
T_V
=
\sup\left\{
H:
\mathcal U_H^{EB}\neq\varnothing
\right\}
\]

measures how far into the future the system can still be managed within declared safety and continuity constraints under present evidence. This produces a common language for physical, epistemic, institutional, and human bottlenecks.

The theory is demonstrated with the Sammakorn urban flood system in Bangkok. The example maps Thai government data products into the architecture, including Bangkok Metropolitan Administration canal levels, pump states, road-flood reports and monkey-cheek retention data; Thai Meteorological Department rainfall nowcasting; Royal Irrigation Department reservoir APIs; and Royal Thai Navy tide predictions. The demonstration shows why observation, forecast, warning, action report, infrastructure capacity, and realized hydraulic performance cannot be collapsed into one state. It also shows how useful disaster advice can be licensed before a point-accurate hydraulic forecast is possible.

Existing traditions—including viability theory, real-time and model-predictive control, robust decision making, digital twins, disaster resilience, integrated water resources management, and the Sendai Framework—are introduced only after the architecture is constructed. They are treated as special cases, solvers, operators, parameterizations, boundaries, or rivals inside the DSVA equation system. The resulting paper offers a falsifiable research program for multi-hazard disaster management and an executable path through FloodConnect.

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

# 6. The admissible-world set

The central epistemic object is not a point estimate but the set of physical states that remain possible.

\[
\boxed{
B_t
=
\left\{
x:
x\models\mathcal C_{physical}
\land
x\models E_{\le t}^{licensed}
\land
x\models\mathcal C_{epistemic}
\right\}
}
\tag{21}
\]

Here:

- \(\mathcal C_{physical}\) contains conservation, topology, geometry, boundary, and control constraints;
- \(E_{\le t}^{licensed}\) contains evidence that passes the declared reader requirements;
- \(\mathcal C_{epistemic}\) contains freshness, datum, provenance, uncertainty, and contradiction rules.

Prediction propagates a set:

\[
\boxed{
B_{t+\Delta t}^{-}
=
\mathcal F
\left(
B_t,\,
\mathcal U_t,\,
\mathcal W_t,\,
\Theta
\right)
}
\tag{22}
\]

and new evidence updates it:

\[
\boxed{
B_{t+\Delta t}
=
B_{t+\Delta t}^{-}
\cap
C(E_{t+\Delta t}).
}
\tag{23}
\]

If the intersection becomes empty, DSVA emits a model-evidence contradiction. It does not fabricate a reconciled physical state.

---

# 7. Viability

## 7.1 Joint physical-human viability set

Let:

\[
\boxed{
\mathcal K
=
\left\{
(x,z):
g_j(x,z)\le0
\quad
\forall j
\right\}
}
\tag{24}
\]

denote the declared viability set.

Constraints may include:

- flood-depth limits;
- minimum reservoir storage;
- maximum contaminant concentration;
- minimum environmental flow;
- safe occupancy;
- accessible medical support;
- functioning electricity or water supply;
- feasible evacuation or logistics routes.

The same mathematical object can therefore describe flood, drought, heat, wildfire, water-quality, infrastructure, and multi-hazard constraints.

## 7.2 Safe actions under a known state

For a known state \(x\), human/service state \(z\), and horizon \(H\), define:

\[
\mathcal U_H^{safe}(x,z,\Gamma_t)
=
\left\{
u_{t:t+H}:
(X_\tau,Z_\tau)\in\mathcal K
\quad
\forall \tau\in[t,t+H]
\right\}.
\tag{25}
\]

This is the action set that keeps the system viable under that state and the actions permitted by \(\Gamma_t\).

---

# 8. Evidence-bounded safe action

The true state is usually not known exactly. Therefore DSVA defines:

\[
\boxed{
\mathcal U_H^{EB}(B_t,Z_t,\Gamma_t)
=
\bigcap_{x\in B_t}
\mathcal U_H^{safe}(x,Z_t,\Gamma_t)
}
\tag{26}
\]

This is the **Evidence-Bounded Safe Action Set**.

Its interpretation is direct:

> Which actions remain viable across every physical state that current evidence still permits?

If:

\[
\mathcal U_H^{EB}\neq\varnothing,
\tag{27}
\]

at least one common action remains supportable without resolving the exact state.

If:

\[
\mathcal U_H^{EB}=\varnothing,
\tag{28}
\]

either the physical system has no common safe control, or uncertainty is so large that no action can be guaranteed across all admissible states.

This gives a formal reason why **information itself can become an operational resource**.

---

# 9. Viability horizon

Define:

\[
\boxed{
T_V(B_t,Z_t,\Gamma_t)
=
\sup
\left\{
H:
\mathcal U_H^{EB}(B_t,Z_t,\Gamma_t)
\neq\varnothing
\right\}.
}
\tag{29}
\]

\(T_V\) is the **viability horizon**: the farthest horizon over which at least one evidence-bounded viable action remains.

This is different from a forecast horizon.

- A forecast horizon asks: how far into the future do environmental predictions extend?
- A viability horizon asks: how far into the future can the system still be managed within declared constraints?
- An action horizon asks: when does a specific action become justified?

The three clocks need not coincide.

---

# 10. Action universe

Actions are divided into four families:

\[
\boxed{
u_t
=
\left(
u_t^{H},
u_t^{I},
u_t^{P},
u_t^{S}
\right)
}
\tag{30}
\]

where:

- \(u^H\): physical/hydraulic action—pump, gate, valve, diversion, release;
- \(u^I\): information action—measure, inspect, verify, request, survey;
- \(u^P\): protective action—warn, close route, shelter, evacuate, deliver support;
- \(u^S\): structural action—construct, retrofit, add storage, alter land or network structure.

The architecture therefore permits a measurement to compete with a pump as a legitimate disaster-management action if the measurement materially expands safe decision space.

---

# 11. Institutional actuation

An action is not feasible merely because it is physically imaginable.

Define:

\[
\boxed{
\mathcal U_t^{feasible}
=
\left\{
u:
Authority(u,\Gamma_t)=1,\,
Resource(u,t)=1,\,
Latency(u)\le H,\,
OperationalCondition(u)=1
\right\}.
}
\tag{31}
\]

Thus fragmented authority, unavailable staff, incompatible procedures, inaccessible equipment, or delayed authorization shrink the feasible action set.

Governance becomes part of the formal state of actionability rather than a qualitative afterthought.

---

# 12. Physical, epistemic, and institutional bottlenecks

## 12.1 Physical bottleneck

For a flow/export network:

\[
\boxed{
b_P^\ast(t)
=
\arg\min_{e\in Cut}
C_e^{feasible}(t).
}
\tag{32}
\]

The installed capacities of all components do not define system throughput when the network contains serial restrictions, downstream head constraints, storage, or unavailable controls.

## 12.2 Epistemic bottleneck

For a candidate measurement or information action \(m\), define the viability value of information:

\[
\boxed{
VOI_m
=
T_V(B_t^{+m},Z_t,\Gamma_t)
-
T_V(B_t,Z_t,\Gamma_t).
}
\tag{33}
\]

Then:

\[
\boxed{
b_E^\ast
=
\arg\max_m VOI_m.
}
\tag{34}
\]

The most valuable sensor is not necessarily the one producing the most data; it is the one that most changes viable action.

## 12.3 Institutional bottleneck

For institutional constraint component \(\gamma\):

\[
\boxed{
VOA_\gamma
=
T_V(B_t,Z_t,\Gamma_t^{-\gamma})
-
T_V(B_t,Z_t,\Gamma_t),
}
\tag{35}
\]

where \(\Gamma_t^{-\gamma}\) represents removal or resolution of that constraint.

The binding bottleneck may therefore be physical, epistemic, or institutional.

---

# 13. Human and service state

A disaster is not over when one physical variable crosses a threshold.

Let the human-operational state be:

\[
\boxed{
Z_i(t,T)
=
(O,F,M,S,E,H,A,P)
}
\tag{36}
\]

with:

- \(O\): occupancy safety;
- \(F\): essential-function state;
- \(M\): movement state;
- \(S\): support/sustainment state;
- \(E\): environmental degradation;
- \(H\): forward hazard;
- \(A\): human-animal household topology where relevant;
- \(P\): operational phase.

The non-collapse principle is:

\[
\boxed{
PhysicalRecovery
\neq
HumanRecovery.
}
\tag{37}
\]

For example:

\[
RoadDry
\not\Rightarrow
CommunityRecovered.
\tag{38}
\]

## 13.1 Recovery time

For joint physical-human viability:

\[
\boxed{
T_R
=
\inf
\left\{
\tau>0:
(X_{t+\tau},Z_{t+\tau})\in\mathcal K
\right\}.
}
\tag{39}
\]

Recovery is therefore a return to the declared joint viability set, not merely a return of one sensor to normal.

---

# 14. Decision rule without a magic risk score

DSVA does not require a single weighted composite score.

A simple form is:

\[
\boxed{
u_t^\ast
\in
\arg\max_{u\in\mathcal U_t^{feasible}}
T_V
\left(
B_t^{+u},
Z_t^{+u},
\Gamma_t^{+u}
\right)
}
\tag{40}
\]

subject to hard constraints such as life safety and route validity.

Where objectives conflict, a lexicographic rule can be used:

\[
\boxed{
\operatorname{lexmin}
\left(
LifeSafetyLoss,\,
RouteFailure,\,
CriticalServiceLoss,\,
ViabilityLoss,\,
RecoveryTime,\,
OperatingCost
\right).
}
\tag{41}
\]

The point is not that every system must use this exact ordering; the ordering must be declared rather than hidden inside arbitrary weights.

---

# 15. Formal propositions

The following propositions form the initial research program.

### P1 — Feasible-futures proposition

Disaster management acts on a set of feasible future trajectories rather than on a single estimated state.

### P2 — Capacity non-additivity proposition

System capacity is topology-, state-, boundary-, and control-dependent and generally cannot be obtained by summing installed component capacities.

### P3 — Common-action proposition

Incomplete observability is operationally harmless over horizon \(H\) if and only if a sufficiently safe common action exists across the admissible state set:

\[
\mathcal U_H^{EB}\neq\varnothing.
\]

### P4 — Operational value-of-information proposition

Information has disaster-management value to the extent that it changes viable action or viable future space.

### P5 — Multiple-bottleneck proposition

The binding limitation on disaster management may be physical, epistemic, or institutional.

### P6 — Human non-collapse proposition

Physical recovery of infrastructure or hazard variables is neither necessary nor sufficient for complete human/service recovery.

### P7 — Action-cost proposition

Low-cost reversible actions can be justified under broader uncertainty than high-cost, irreversible, or movement-disruptive actions.

### P8 — Semantic evidence proposition

Observation, forecast, warning, instruction, and action report cannot be substituted for one another without an explicit transformation.

---

# 16. Falsifiability

DSVA is intended as a theory that can fail.

Examples of empirical or formal challenges include:

1. **P2 failure:** verified system export repeatedly exceeds a verified binding cut without an undeclared path or storage explanation.
2. **P3 failure:** two indistinguishable admissible states require different actions, yet a deterministic action can be proved safe for both.
3. **P4 failure:** additional information consistently increases \(T_V\) under the formal model but worsens correctly measured operational outcomes because the information action itself was misrepresented or delayed.
4. **P5 failure:** across well-instrumented systems, physical capacity alone fully determines viable action and neither knowledge nor institutional constraints change the feasible action set.
5. **P6 failure:** across independent disaster cases, hydraulic or physical recovery always coincides with recovery of movement, occupancy, critical services, and support.
6. **Evidence-model failure:** retained licensed evidence yields an empty admissible-world set under the declared model; the system must then identify a model/evidence contradiction rather than silently repair it.

---

# 17. Sammakorn as a minimal complete demonstrator

## 17.1 Why Sammakorn

Sammakorn, in eastern Bangkok, is useful not because it represents every disaster system, but because it contains a compact form of nearly every DSVA object:

\[
Rain
\rightarrow
Retention
\leftrightarrow
Internal\ transfer
\rightarrow
Terminal\ export
\rightarrow
Receiving\ water.
\tag{42}
\]

It also contains:

\[
Observation
\rightarrow
Evidence
\rightarrow
Admissible\ states
\rightarrow
Action
\tag{43}
\]

and:

\[
Physical\ state
\rightarrow
Road/household/service\ consequence.
\tag{44}
\]

FloodConnect currently models the historical large-pond system as interconnected at system level while refusing to claim that every pair of ponds has a known direct hydraulic connection. The working topology identifies four pump stations (ST.SPS.01–04) and treats ST.SPS.01 as a strong working hypothesis for the main terminal outlet toward the Khlong Saen Saep side; exact internal geometry and several pump directions remain unverified pending BOQ/as-built material.

This makes the case suitable for a theory whose core rule is to preserve what is known, what is hypothesized, and what remains unresolved.

## 17.2 Local water balance

For the Sammakorn storage system:

\[
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
\tag{45}
\]

The equation is exact as bookkeeping only when every term is declared. It is not a quantitative forecast if catchment area, runoff coefficient, stage-storage relation, realized pump discharge, or receiving-water state are absent.

## 17.3 Terminal bottleneck

If ST.SPS.01 is confirmed as the terminal export path, net export is bounded by the feasible capacity of the terminal cut:

\[
\boxed{
Q_{export}(t)
\le
C_{terminal}^{feasible}(t).