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
}
\tag{46}
\]

Internal pumps may redistribute water among local storages:

\[
Q_{internal}>0
\]

without implying:

\[
Q_{export}>0.
\]

Thus:

\[
\boxed{
InternalRedistribution
\neq
NetExport.
}
\tag{47}
\]

## 17.4 Export window

Let:

\[
\Delta H_{out}(t)
=
H_{SMK}(t)-H_{receiver}(t).
\tag{48}
\]

Then:

\[
C_{out}^{feasible}(t)
=
\Phi
\left(
\Delta H_{out},
PumpState,
GateState,
DownstreamState
\right).
\tag{49}
\]

The same installed pump system can therefore have different effective export performance under different receiving-water states.

---

# 18. Worked example: connecting DSVA to Thai government data

This section is intentionally concrete. The objective is to show how a theory manuscript can connect to operational public evidence without pretending that every government webpage is a real-time machine API.

## 18.1 Canonical government evidence contract

Every source is normalized into:

```yaml
evidence:
  source_id: ...
  agency: ...
  product_type: OBSERVATION|FORECAST|WARNING|INSTRUCTION|ACTION|REFERENCE
  variable: ...
  value: ...
  unit: ...
  spatial_support: ...
  datum: ...
  observed_at: ...
  published_at: ...
  fetched_at: ...
  freshness: ...
  uncertainty: ...
  quality: ...
  provenance: ...
```

The adapter does not change the semantic type.

---

## 18.2 BMA / HII canal-water API

FloodConnect uses the public ThaiWater endpoint:

```text
https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel
```

for Bangkok canal stations republished through HII/ThaiWater.

Variables currently mapped by FloodConnect include:

```text
canal_water_level_m
warning_level_m
critical_level_m
bank_level_m
canal_out_m      # gate stations only
```

Adapter:

\[
H_i^{obs}(t)
\leftarrow
G[
product=OBSERVATION,\,
variable=canal\_water\_level\_m
].
\tag{50}
\]

If inside and outside levels share a compatible datum:

\[
\Delta H_i
=
H_{inside}-H_{outside}.
\tag{51}
\]

The reader may infer direction when the difference exceeds combined measurement resolution, but it may not infer discharge without a hydraulic bridge.

---

## 18.3 BMA PumpHistory

FloodConnect also reads the Bangkok Department of Drainage and Sewerage PumpHistory public page:

```text
https://weather.bangkok.go.th/Station/PumpHistory
```

The current parser extracts, where present:

```text
level_m
pumps_on
pumps_total
gate_open_m
station_status_th
```

These become control-state evidence:

\[
u_p^{obs}
\leftarrow
(pumps\_on,pumps\_total,status).
\tag{52}
\]

But:

\[
\boxed{
pumps\_on
\neq
actual\_pump\_discharge.
}
\tag{53}
\]

A pump-flow equation requires a pump curve or measured discharge:

\[
Q_p
=
u_p
\eta_p
\Gamma_p(\Delta H_p).
\tag{54}
\]

If \(\Gamma_p\) and \(\eta_p\) are missing:

```text
PumpState = KNOWN
PumpDischarge = UNRESOLVED
```

This distinction is essential in a public-data-driven disaster system.

---

## 18.4 BMA road-flood observation

FloodConnect uses:

```text
https://api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road
```

for fixed road-flood points.

A direct road-depth reading maps to:

\[
d_{road}^{obs}(x,t).
\tag{55}
\]

This observation contributes to the human/mobility state \(Z_t\), not merely to the hydraulic state.

---

## 18.5 BMA monkey-cheek / retention endpoint

The Bangkok public retention/monkey-cheek system is available at:

```text
https://monkeycheek.bangkok.go.th/listmongkeycheeks
```

The page publicly lists 37 facilities with fields including:

```text
code
facility name
owner
district
responsible unit
current water-level percentage
data timestamp
```

The page includes:

```text
027 — บึงรับน้ำหมู่บ้านสัมมากร — เขตสะพานสูง
```

and, on the public page checked for this draft, the displayed value was:

```text
current water-level percentage = 51.00
data timestamp = 16 July 2026 10:03:01
```

This source demonstrates three DSVA rules simultaneously.

First, it is a government-owned public endpoint, but a dedicated JSON/REST endpoint has not yet been independently verified. Therefore the present interface is treated as a public government data page rather than silently labelled a machine API.

Second, the percentage is not automatically a storage fraction:

\[
\boxed{
51\%
\not\Rightarrow
S=0.51S^{max}
}
\tag{56}
\]

until the denominator and transformation are documented.

Third, the timestamp matters. Relative to an October 2026 operational decision, a July value is stale:

\[
Fresh=0.
\tag{57}
\]

Therefore DSVA may retain it as historical/reference evidence while refusing to use it as current storage state.

This is precisely why provenance and freshness are part of the theory rather than implementation metadata.

---

## 18.6 Thai Meteorological Department nowcasting

The TMD SATDA public service states that Bangkok and metropolitan rainfall nowcasting is provided up to 180 minutes ahead and updated every 15 minutes.

This is mapped as:

\[
P^{fcst}_{0:180}(x,t)
\tag{58}
\]

with:

```text
product_type = FORECAST
```

not `OBSERVATION`.

The forecast contracts the forcing set:

\[
\mathcal W_t
\rightarrow
\mathcal W_t^{TMD}
\tag{59}
\]

but does not become realized rainfall until observed.

---

## 18.7 Royal Irrigation Department reservoir API

RID publishes a documented public API:

```text
https://app.rid.go.th/reservoir/api/dam/public
```

and dated historical access such as:

```text
https://app.rid.go.th/reservoir/api/dam/public/YYYY-MM-DD
```

Documented fields include:

```text
capacity
storage
active_storage
dead_storage
volume
percent_storage
inflow
outflow
```

These can map to an upstream/boundary state:

\[
R_d(t)
=
\left(
V_d,I_d,O_d,S_d
\right).
\tag{60}
\]

For Bangkok flood management, reservoir information is an upstream forcing/boundary input. It does not directly determine local Sammakorn flooding without routing and downstream-system relations.

---

## 18.8 Royal Thai Navy Hydrographic Department tide products

The Hydrographic Department publishes 2026 predicted water-level tables for multiple stations, including Bangkok Bar, Phra Chulachomklao Fort, Bangkok Port, Royal Thai Navy Headquarters, and Pak Nam Bang Pakong.

These map to:

\[
H_{tide}^{pred}(t)
\tag{61}
\]

with:

```text
product_type = FORECAST
```

Predicted tide must remain distinct from observed receiving-water level:

\[
\boxed{
H_{tide}^{pred}
\neq
H_{receiver}^{obs}.
}
\tag{62}
\]

The difference matters because local export depends on the realized downstream head, not solely on astronomical prediction.

---

# 19. End-to-end Thai government evidence stack

For the Sammakorn demonstrator:

\[
\boxed{
\begin{aligned}
E_t
=
\{&
H^{BMA/ThaiWater},
d_{road}^{BMA},
U_{pump}^{BMA},
S_{monkeycheek}^{BMA?},
P^{TMD}_{fcst},
R^{RID},
H^{Navy}_{tide,pred}
\}.
\end{aligned}
}
\tag{63}
\]

The question mark on \(S_{monkeycheek}^{BMA?}\) is deliberate: the public percentage cannot become storage volume until its measurement semantics are closed.

The operational pipeline is:

```text
Government/public source
        ↓
typed evidence atom
        ↓
freshness / datum / sensor / contradiction QC
        ↓
admissible-world set B_t
        ↓
physical + human viability constraints
        ↓
evidence-bounded safe action set
        ↓
DETERMINATE / INTERVAL / UNRESOLVED / REFUSED
        ↓
protective or operational action
```

This is the executable bridge between theory and FloodConnect.

---

# 20. Advice before precise prediction

A major implication is that useful disaster advice can become available before a quantitative local-depth forecast.

Suppose:

\[
H>H^{crit},
\qquad
Trend=RISING,
\qquad
Route=UNKNOWN.
\tag{64}
\]

The architecture cannot infer:

```text
EVACUATE
```

because route feasibility is unresolved.

It can support:

```text
PREPARE + VERIFY_ROUTE
```

or, for a vulnerable household with unsafe occupancy and no safe independent route:

```text
REQUEST_ASSISTED_EVACUATION
```

Likewise, if:

\[
Trend=FALLING
\]

but:

\[
H>H^{crit},
\]

the system must not issue an all-clear.

The disaster-management objective is not to maximize apparent certainty. It is to select the strongest action licensed by the current viable-action intersection.

---

# 21. Dialogue with existing theories

This section is intentionally downstream of the architecture.

The rule is:

\[
\boxed{
\phi_j:
\mathcal T_j
\rightarrow
\mathcal T^\star
}
\tag{65}
\]

where \(\mathcal T^\star\) is DSVA and external theory \(j\) must enter with a declared role:

\[
\boxed{
Role(\mathcal T_j)
\in
\{
SPECIAL\ CASE,\,
SOLVER,\,
OPERATOR,\,
PARAMETERIZATION,\,
BOUNDARY,\,
RIVAL
\}.
}
\tag{66}
\]

The literature does not automatically redefine the root ontology.

## 21.1 Viability theory

Classical viability theory studies whether trajectories can remain within viability constraints under admissible controls. In DSVA, it enters as a special case when the physical state is known exactly and human/institutional extensions are removed.

If:

\[
B_t=\{x_t\},
\qquad
Z=\varnothing,
\qquad
\Gamma=\top,
\tag{67}
\]

then the evidence-bounded safe action set collapses toward a classical state-based viability problem.

Thus:

\[
ClassicalViability
=
SpecialCase(DSVA).
\tag{68}
\]

DSVA does not claim ownership of viability theory. It uses viability as an internal mathematical conversation partner.

## 21.2 Real-time control and model predictive control

RTC and MPC contribute solvers and operating policies for \(u^H\). Urban drainage research has treated drainage networks as large-scale dynamic systems and developed multiple control strategies. Reviews of MPC in urban drainage and water-resource systems show mature literatures involving receding horizons, internal models, forecasts, optimization, uncertainty, and multiobjective operation.

In DSVA:

\[
\phi_{MPC}
:
MPC
\mapsto
Solver
\left(
\mathcal U_H^{safe}
\right).
\tag{69}
\]

MPC can optimize a DSVA action problem, but DSVA separately specifies whether the evidence and action semantics license the optimization inputs.

## 21.3 Robust decision making

Robust adaptive decision approaches address deep uncertainty by seeking strategies that perform acceptably across multiple plausible futures.

In DSVA they map naturally to the handling of:

\[
B_t\times\mathcal W_t
\]

and to policy selection across uncertain trajectories.

They therefore function as solver/decision traditions inside the viable-futures problem.

## 21.4 Digital twins

Digital-twin research in disaster risk management emphasizes real-time representation, monitoring, scenario testing, decision support, and interconnected physical/social systems.

In DSVA:

\[
\phi_{DT}
:
DigitalTwin
\mapsto
Implementation
\left(
E
\rightarrow
B
\rightarrow
F
\rightarrow
Reader
\right).
\tag{70}
\]

A digital twin is therefore an implementation architecture capable of supporting DSVA, not the definition of disaster viability itself.

## 21.5 Disaster resilience

Resilience research contributes concepts of resistance, functional loss, recovery, and cross-system dependencies.

In DSVA, resilience enters through:

\[
\mathcal K,\quad
T_V,\quad
T_R,\quad
Z_t.
\tag{71}
\]

DSVA's additional discipline is that recovery of a physical variable cannot silently stand for recovery of human function.

## 21.6 Sendai Framework

The Sendai Framework identifies understanding disaster risk, strengthening disaster-risk governance, investing in resilience, and enhancing preparedness for effective response and recovery as its four priorities.

DSVA maps these priorities into formal objects:

```text
Understanding risk        → E_t, B_t
Governance                → Γ_t
Investment/resilience     → u^S, K
Preparedness/response     → u^P, Z_t, U_H^EB
```

The Sendai Framework therefore provides a global policy boundary and evaluative dialogue rather than a competing state-transition model.

## 21.7 Integrated water resources management

IWRM emphasizes coordinated management of water, land, related resources, social welfare, equity, and ecosystem sustainability.

In DSVA, IWRM contributes to the construction of:

\[
\mathcal K
\]

and:

\[
\Gamma.
\]

The architecture allows ecological, social, and economic constraints to coexist with hazard constraints without reducing them to one risk score.

---

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

First, DSVA is an architecture, not a claim that all components are individually new.

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
X_t
\rightarrow
E_t
\rightarrow
B_t
\rightarrow
\mathcal U_H^{EB}
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

The manuscript should be treated as `PROPOSAL / THEORY_SYNTHESIS`, not production truth.

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