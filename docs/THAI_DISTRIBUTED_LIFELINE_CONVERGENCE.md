# Thai Distributed Lifeline Convergence Model (TDLC)

> **Status:** FloodConnect design + operational research layer.  
> **Scope:** Thailand-first flood response; intended to be testable and potentially generalisable,
> not claimed as a universal theorem.  
> **Relationship to Toledo:** consumes Toledo/FloodConnect hydrologic readouts; does not change
> PROP-FLOOD-03's water-balance equation.

## 1. Design premise from the Thai ecosystem

FloodConnect should not assume a clean top-down emergency system.

Thai flood response is often a **converging network**:
- households try to remain functional first;
- neighbours/buddy cells share checks, labour, vehicles, food, water, charging and information;
- community/religious/civic/private actors may create kitchens, supply points, boats or micro-hubs;
- local authorities/public-health/EMS/district actors enter from outside or across zones;
- provincial/BMA/DDPM/other state assets add heavier logistics and evacuation capacity.

The system therefore asks:

> **What is the lowest support layer that can keep people safely functional, and what verified
> lifeline must move inward or what people must move outward when that layer fails?**

This is deliberately different from:
- "nearest shelter";
- "send everyone to one centre";
- "assume the state reaches every household at the same time";
- "assume spontaneous mutual aid reaches every household evenly".

Thailand-specific evidence supports both sides of this design. Thai CBDRM studies report organic
community disaster organisations and local coping that do not wait wholly for government, but also
report slow/uneven institutionalisation and collaboration problems between government and
communities. Studies of dependent older adults in Thailand explicitly connect family preparedness
with community, local administration and health-sector management.

Academic anchors:
- AIT DPMM: Community-Based DRR, Risk-Knowledge Networking, Disaster Risk Governance, Early Warning,
  Floods/Droughts, GIS/remote sensing:
  https://ait.ac.th/program/disaster-preparedness-mitigation-and-management/
- Systematizing CBDRM in Thai flood-prone communities:
  https://doi.org/10.1016/j.ijdrr.2018.02.010
- Thai dependent older-adult flood preparedness:
  https://doi.org/10.1016/j.ijdrr.2021.102460
- Community-based flood disaster management for older adults in Southern Thailand:
  https://doi.org/10.1016/j.ijnss.2021.08.008
- Government-community collaboration in Thai flood policy:
  https://doi.org/10.1016/j.sbspro.2014.07.486
- Household flood preparedness in Songkhla Old Town:
  https://doi.org/10.1016/j.pdisas.2025.100441
- Thai local-disaster-knowledge integration:
  https://doi.org/10.1016/j.pdisas.2023.100294
- Thailand flood-risk paradigm review:
  https://doi.org/10.1016/j.ijdrr.2017.08.003

## 2. Global guidance is an input, not the architecture

Global shelter / evacuation work is reused as constraints:
- planned sheltering must maintain water, food, sanitation, health and multi-agency services;
- movement itself can be hazardous, so evacuation is not automatically safer than sheltering in
  place;
- shelter capacity and demand vary over time;
- resource sharing while sheltering in place is a separate problem from evacuee routing.

FloodConnect keeps its own Thailand-first architecture:

```text
Hydrology / control
      |
      v
Household self-sustainment
      |
      +---- support inward ---- Buddy / Zone / Civic / State
      |
      +---- people outward ---> Internal shelter / transfer / external shelter
```

The important operation is **convergence**, not centralisation.

## 3. Two networks, not one

### 3.1 Resident-movement network

[
G_{move}=(V,E_{move})
]

This remains fail-closed and acyclic for declared escalation:
`household -> buddy -> zone -> internal_safe -> egress -> external_safe`.

A movement edge is usable only when current, field-verified, mode-feasible and not blocked.

### 3.2 Lifeline/support network

[
G_{support}=(V,E_{support})
]

This graph may contain lateral and backward edges because food, medicine, water, power, information,
boats, volunteers and health support may travel **toward** people who remain in place.

Examples observed in Bangkok field reports:
- a dry-area kitchen cooking and sending meals inward;
- foundations/volunteer groups carrying relief bags to hard-to-reach locations;
- one residential block supplying service water to another;
- community/religious sites acting as a temporary resource node.

A support node is not automatically a shelter.

## 4. Essential-function vector

Let the declared essential-function set for group g over planning horizon H be:

[
E_g(H) =
{water_{drink}, water_{service}, food, medicine, power^*, WASH,
communications, mobility/support, ...}
]

where `power*` is required only when the group/site has a declared critical power dependency.

No universal fixed list is forced on every person; functional needs are declared.

For each essential e:

- `D_{g,e}(H)`: declared demand over H;
- `X_{v,e}(t)`: usable stock/service already available at node v;
- `y_{p->g,e}(t,H)`: quantity/service that provider p can actually deliver to g through a
  verified support path within H.

The deliverable quantity is constrained by provider supply and path capacity:

[
0 le y_{p	o g,e} le S_{p,e}
]

[
sum_g y_{p	o g,e} le S_{p,e}
]

[
y_{p	o g,e} le B_{P(p,g),e}
]

and

[
y_{p	o g,e}=0
quad	ext{when } P(p,g) 	ext{ is blocked/stale/unverified.}
]

This avoids the common error "a donor exists, therefore the household is supplied".

## 4A. Person/group composition — needs are matched to support, not scored

FloodConnect separates three things that are often wrongly collapsed:

1. **life-stage / vulnerability group** — child, older adult, pregnant/postpartum, illness/disability;
2. **functional dependency** — supervision, mobility, medicine, medical follow-up, powered device,
   communication, special diet, infant feeding;
3. **living arrangement** — alone, pair, family group, multigenerational, group-care setting.

Thai public-health guidance explicitly prioritises children, older adults, pregnant people,
bed/home-bound people, people with disabilities and chronic illness during floods. Thai research on
dependent older adults also shows that preparedness is produced by the relationship among family
caregivers, community, local administration and health services rather than age alone.

### Composition tags are descriptive, never a risk score

Examples:
- `LIVES_ALONE`
- `CHILD_WITH_OLDER_ONLY`
- `OLDER_ONLY_HOUSEHOLD`
- `PREGNANT_ALONE`
- `SINGLE_CAREGIVER_WITH_DEPENDENTS`
- `MULTIGENERATIONAL`
- `NO_CO_RESIDENT_CAPABLE_ADULT`

A tag triggers the correct assessment question. It does **not** by itself make a household
non-viable.

### Need–support matching

Let (N_g(t)) be the finite declared set of functional need tokens in household/group (g).
A token is a pair ((p,f)): person/member category (p) has declared need function (f).

Let (S_g(t)) be the finite set of available support tokens, from:
- co-resident helpers/caregivers;
- buddy/neighbor links;
- community/zone services;
- health/public/emergency providers.

A support token (s) may cover need token (n) only when capability, availability and connection
are declared:

[
E_{NS}(n,s,t)=1
iff
Capability(s,f)=1
land Available(s,t)=1
land Connected(s,p,t)=1
]

where `Connected` may mean co-resident availability, a fresh support edge, or a verified
health/logistics link depending on the function.

With declared support capacities (cap_s), find a feasible bipartite b-matching (mu). Then:

[
oxed{
Uncovered_g(t)
=
N_g(t)setminus Covered_{mu}(N_g(t))
}
]

and the hard dependency condition is:

[
oxed{
DepOK_g(t)=1
iff
Uncovered_g(t)=arnothing
}
]

If a required need, capability, link or capacity is unknown, `DepOK = bottom/UNKNOWN`, not TRUE.

The current categorical implementation does not invent helper capacity. It records explicit
`*_link_uncovered` fields and fails closed when a required link is unknown.

### Pairing rules used operationally

- child/adolescent -> caregiver link is checked;
- single caregiver + dependents -> backup caregiver/buddy link is checked;
- older adult -> support link becomes mandatory only when a functional need is declared;
- pregnancy/postpartum -> maternal-health/transport support link is checked;
- illness/bedbound/essential medication/time-critical care -> medical support link is required;
- mobility dependency -> mobility support link is required;
- powered medical device -> critical-power support link is required;
- communication dependency -> communication support link is required;
- living alone + vulnerability/dependency -> buddy/reassessment link is required.

Important non-inferences:
- two older adults together are not assumed to be mutual caregivers;
- a working-age co-resident is not automatically a capable caregiver;
- pregnancy does not imply immobility;
- older age does not imply dependency;
- co-residence does not imply the needed support function exists.

This representation handles the user's practical question "who is living with whom?" without
creating an explosive list of every demographic combination.

---

## 5. Thai Lifeline Margin

For group g sustained at candidate support node v:

[
oxed{
M_e(v,g,t,H)
=
X_{v,e}(t)
+
sum_p y_{p	o g,e}(t,H)
-
D_{g,e}(H)
}
]

The margin is retained **per essential**; it is never collapsed into one weighted resilience score.

Define hard safety/service predicates `B_j in {1,0,bottom}`, e.g.:
- physical occupancy safety;
- sanitation operability;
- communication/reassessment;
- support for declared mobility/medical needs.

Then:

[
oxed{
Sus(v,g,t,H)=
egin{cases}
1,& orall e:M_ege0 land orall j:B_j=1\
0,& exists e:M_e<0 	ext{ or } exists j:B_j=0\
ot,& 	ext{otherwise}
end{cases}
}
]

Operational implementation may use categorical
`SUFFICIENT / INSUFFICIENT / UNKNOWN / NOT_REQUIRED` until measured units exist.

## 6. Time matters: support must arrive before a function fails

When stock/use rates and travel/service time are genuinely declared, define:

[
T^{fail}_{g,e}
=
	ext{time until essential e becomes insufficient}
]

and

[
T^{arrive}_{p	o g,e}
=
	ext{verified/declared time for support from p to reach g}.
]

Then the response slack is:

[
oxed{
Lambda_{g,e}
=
T^{fail}_{g,e}
-
min_p T^{arrive}_{p	o g,e}
}
]

Interpretation:
- (Lambda>0): at least one declared support path can arrive before depletion;
- (Lambdale0): support does not close the time gap under current declarations;
- missing duration/travel data: `REFUSED/UNKNOWN`, never guessed.

This captures a common Thai-flood failure mode: supplies exist somewhere, but last-mile arrival is
later than the household's usable stock.

## 7. Coverage matters: visible demand is not total demand

Thai field reports show that a building or household may be near a main road yet still be missed.

For declared household set (mathcal H_Z) in zone Z:

[
A_Z(t)={hinmathcal H_Z : h 	ext{ has a current needs/self-sufficiency assessment}}
]

[
U_Z(t)=mathcal H_Z setminus A_Z(t)
]

If counts are declared:

[
Coverage_Z(t)=rac{|A_Z(t)|}{|mathcal H_Z|}
]

This is a **coverage readout**, not a safety/resilience score.

Crucial rule:

[
hin U_Z 
otRightarrow h 	ext{ is fine}
]

Unknown households remain unknown. Aid distribution must not infer "served" from proximity to a
road, shelter, kitchen or previous delivery point.

## 8. Allocation mismatch: detect duplication and invisible gaps

For essential e in zone Z:

[
Need_{Z,e}(t,H)=sum_{gin Z}max(0,D_{g,e}-X_{g,e})
]

[
Delivered_{Z,e}(t,H)=sum_p y_{p	o Z,e}
]

[
oxed{
Mismatch_{Z,e}
=
Delivered_{Z,e}-Need_{Z,e}
}
]

- negative: confirmed unmet demand;
- positive: delivery exceeds currently confirmed demand;
- zero: ledger balance only, **not** proof that every household is covered because `U_Z` may be
  non-empty.

This is designed for the Thai reality of many independent donors/volunteer groups: it helps expose
both duplicate concentration and uncovered pockets without requiring one actor to command everyone.

## 9. Lowest Viable Community Node in the Thai topology

Candidate layers:

```text
L0 household / private shelter
L1 buddy cell / immediate neighbour support
L2 zone / community micro-hub
L3 internal/community shelter
L4 external verified shelter
```

`egress`, kitchens, warehouses, boats and supply points are **service/connective nodes**, not
LVCN candidates.

Let `Conn(v,g,t)` mean:
- identity if v is the household;
- verified support connectivity if v is buddy/zone;
- verified movement connectivity if v is a shelter.

Then:

[
oxed{
LVCN(g,t,H)
=
argmin_{vin C_g}ell(v)
quad
s.t. Sus(v,g,t,H)=1 land Conn(v,g,t)=1
}
]

If a lower layer is UNKNOWN and a higher layer is known viable, report:

[
KNOWN_VIABLE_UPPER_BOUND
]

not an exact LVCN.

## 10. Operational response patterns from the unified state

This document previously used T0-T5 as a protective-action typology. Those labels are now treated as examples of **where a missing function is resolved**, not as mutually exclusive crisis types.

The canonical executable state is now:

`Z_i(t,T) = (O, F, M, S, E, H, A, P)`

and response patterns are derived from that state:

- `STAY_SUSTAIN` — occupancy viable, functions intact;
- `STAY_PREPARE` — viable now, forward hazard elevated;
- `RESUPPLY` — safe self-resupply window exists;
- `DELIVER_INWARD` — move the missing function toward residents;
- `ESCALATE_SUPPORT` — household/buddy/zone cannot yet close the gap;
- `MOVE` — occupancy non-viable and verified independent movement exists;
- `ASSISTED_EVACUATION` — occupancy non-viable but self-movement/animal movement/destination is not verified;
- `SHELTER_OPERATION` — occupied shelter passes current hard constraints;
- `SHELTER_INTERVENTION_RELOCATION` — shelter itself loses a hard constraint;
- `RECOVERY_RETURN` — recovery-phase constraints are verified;
- `VERIFY` / `VERIFY_PREPARE` — critical evidence remains unknown.

Old T0-T5 descriptions can still be read as support-depth examples:

`self -> buddy -> zone -> civic/private bridge -> public transfer -> external shelter`

but they are no longer the primary typology.

This prevents new dimensions such as environmental degradation, assistance animals or livestock from requiring new numbered crisis types. They modify the state vector and therefore the derived response pattern.
## 11. Convergence: community and state move toward each other

Let (r_g) be the lowest functional layer currently reachable from inside the community and
(r_p) the deepest layer current external providers can reliably reach.

A service exchange becomes feasible when a verified interface node q exists such that:

[
qin Reach_{community}(t)cap Reach_{provider}(t)
]

The interface may be:
- a house;
- buddy/zone node;
- micro-hub;
- boat/vehicle transfer point;
- external shelter.

FloodConnect's design objective is:

[
oxed{
	ext{push essential functions inward as far as safely feasible;
move people outward only as far as required for viability.}
}
]

This is a design objective, not a claim that self-reliance replaces public duty.

### 11A. Lifeline Convergence Feasibility — canonical constraint

The field failure this construct targets is **not simply supply shortage**. It is the case where
supplies, responders or vehicles exist, but the required essential function still cannot reach the
right group through a usable interface/path with enough capacity before the function fails.

FloodConnect names this **Lifeline Convergence Feasibility (LCF)**. It is a hard feasibility
predicate, not a weighted coordination/risk score.

For group \(g\), essential \(e\), time \(t\), and planning horizon \(H\), define the declared gap:

\[
G_{g,e}(t,H)
=
\max\left(0,D_{g,e}(H)-X_{g,e}(t)\right)
\]

For a provider \(p\) and verified support path \(P(p,g)\), the maximum declared deliverable
quantity is:

\[
Q_{p,g,e}(t,H)
=
\min\left(S_{p,e}(t,H),B_{P(p,g),e}(t,H)\right)
\]

A candidate interface \(q\) is admissible only when it is a current, verified meeting point of the
community-side and provider-side reachable sets:

\[
q \in Reach_{community}(t)\cap Reach_{provider}(t)
\]

The canonical convergence predicate is:

\[
\boxed{
C_{g,e}(t,H)=1
}
\]

iff there exists at least one declared tuple \((p,q,P)\) such that:

\[
\boxed{
q\in Reach_{community}(t)\cap Reach_{provider}(t)
\;\land\;
VerifiedFresh(q,P)
\;\land\;
Q_{p,g,e}(t,H)\ge G_{g,e}(t,H)
\;\land\;
T^{arrive}_{p\to g,e}<T^{fail}_{g,e}
}
\]

Interpretation:

- **supply present is insufficient evidence** — provider stock must cover the declared gap;
- **a route drawn on a map is insufficient evidence** — the path/interface must be fresh,
  field-verified and mode-feasible;
- **large upstream supply does not override a small bottleneck** — deliverable quantity is bounded by
  the path/interface capacity;
- **eventual delivery is insufficient** — delivery must arrive before the relevant lifeline fails.

Three-valued semantics are mandatory:

\[
C_{g,e}(t,H)
=
\begin{cases}
1,& \text{at least one candidate tuple closes all hard constraints}\\
0,& \text{declared evidence proves every candidate fails at least one hard constraint}\\
\bot,& \text{otherwise / required evidence is missing, stale or unverified}
\end{cases}
\]

If \(G_{g,e}=0\), convergence for that essential is \`NOT_REQUIRED\`, not a proof that the whole
household/zone is safe.

The executable implementation is \`convergence_feasibility.py\` with states
\`FEASIBLE / INFEASIBLE / NOT_REQUIRED / UNKNOWN\`.

#### Coordination is infrastructure, not a person

A chief-of-staff / incident-command role may improve operations, but TDLC must not make one person a
single point of failure. The minimum shared operational layer is:

\[
SharedState(t)
=
\{DemandLedger,\ ResourceLedger,\ RouteInterfaceLedger\}
\]

The ledgers answer three different questions:

1. **Demand ledger** — who/which zone needs what, how much, and by when;
2. **Resource ledger** — which provider has what usable quantity/capability;
3. **Route/interface ledger** — where transfer is actually possible, by which mode, with what
   freshness and bottleneck capacity.

People may rotate; the shared state must persist. A coordinator allocates against this state rather
than relying on memory or first-arrival visibility.

This construct exposes a common last-mile pattern without assuming that centralisation is the only
solution: multiple independent providers can remain independent while sharing the minimum state
needed to prevent duplicate concentration, invisible demand and bottleneck pile-ups.

## 12. Thailand-specific strengths represented explicitly

These are capacities to measure, not stereotypes:
- dense family/neighbor support where present;
- community leaders and local organisations;
- temples, mosques, schools, businesses or other civic facilities when actually suitable;
- volunteer/foundation logistics;
- local food-production/cooking networks;
- village/public-health volunteers and local health actors where active;
- digital social coordination and local disaster knowledge;
- local administrative/public rescue assets.

A node gets no credit merely for having one of these labels. Capacity must be declared/current.

## 13. Thailand-specific failure modes represented explicitly

The model must be able to expose:
1. **visibility bias** — households not on the obvious aid route remain unassessed;
2. **donation concentration** — many providers deliver to the same visible node;
3. **last-mile failure** — supply exists but cannot safely reach demand;
4. **stockout propagation** — nearby shops exist but shelves/replenishment fail;
5. **volunteer fragmentation** — multiple groups have capacity but no shared demand ledger;
6. **role ambiguity / coordination friction** — government/community/private actors hold
   different information, expectations or willingness;
7. **vulnerable-person invisibility** — older adults alone, dependent persons, infants and
   time-critical medical needs remain hidden if only headcount is recorded;
8. **service-function confusion** — "has electricity" can coexist with "no service water";
9. **shelter-label fallacy** — a mosque/school/temple/community hall may itself be flood-exposed;
10. **unsafe self-rescue** — food/resource depletion can push people to enter floodwater when
    delivery/assisted movement should be considered first.

These are represented as missing/failed constraints and coverage gaps, not cultural scores.

## 14. Link to AIT disaster-management frame

AIT's DPMM focus areas map cleanly without replacing FloodConnect's architecture:

| AIT field | FloodConnect use |
|---|---|
| Community-Based DRR | L0-L3 support network / LVCN |
| Risk-Knowledge Networking | provenance + local/community reports + official feeds |
| Disaster Risk Governance | provider/owner/responsibility metadata |
| Early Warning | forward hazard separate from current state |
| Floods and Droughts | Toledo/FloodConnect hydrologic readouts |
| GIS/Remote Sensing | node/edge/hazard localisation |
| Multi-hazard assessment | shelter/site hard constraints |
| Humanitarian management | lifeline, shelter lifecycle, allocation/coverage |

AIT confirms the interdisciplinarity needed; it is not used as evidence for any specific equation.

## 15. What should be tested

Real-data/real-report tests should ask:
- Does UNKNOWN remain UNKNOWN?
- Does a verified buddy/zone delivery close a household resource gap without forcing evacuation?
- Does a dry kitchen/support node remain a support node rather than being mislabeled a shelter?
- Does an unsafe community building fail shelter screening even if it has volunteers/capacity?
- Does a service-water failure make an occupied shelter non-viable?
- Does an unassessed household remain uncovered rather than "probably served"?
- When a safe route disappears, does the system switch from self-resupply to delivery/assisted
  response instead of recommending risky travel?
- Can hydrologic recovery lower the required support layer over time?

No claim about saved lives, response efficiency or superiority to current Thai practice is licensed
until prospective deployment data exist.


## 16. Environmental degradation clocks — safe now can become unsafe later

Water depth alone does not determine occupancy duration. FloodConnect now adds environmental
degradation clocks for flood-affected household/shelter nodes.

The key distinction is:

[
Depth(t) 	ext{ unchanged}

otRightarrow
OccupancySafety(t) 	ext{ unchanged}
]

Use:

[
T^{effective}_i
=
min
left(
T^{resource}_i,
T^{environment}_i,
T^{access}_i,
T^{forward-hazard}_i
ight)
]

where the environmental horizon is the earliest **known** deadline among mechanisms such as
wet-material/mold progression and standing-water control cycles. Unknown clocks are not infinity.

Immediate contamination mechanisms do not receive a time grace period:
suspected/confirmed sewage intrusion or sewer backflow can fail WASH/sanitation immediately.

Time-dependent mechanisms are kept separate:
- wet indoor materials: 24–48 h mold-prevention clock from CDC guidance;
- standing water: vector-control starts immediately; weekly source-reduction cycle is tracked;
- stagnant/organic/sewage-loaded water: anaerobic odor/H2S formation is plausible, but no ppm
  is inferred without measurement;
- sewer gas: odor is a trigger to investigate, never a clearance test;
- dry drain traps and sewer surcharge/backflow are different pathways and use different controls.

The intervention operator is:

[
M_k:(T^{trigger},State)ightarrow(T'^{trigger},State')
]

but an intervention receives **no guaranteed extension** unless the effect is verified. This is
important for Thai operational practices: drainage, waste removal, EM/biological treatment,
aeration or other actions may be recommended by local/health authorities in context, but
FloodConnect does not convert them into extra "safe hours" without measurement.

See:
`docs/ENVIRONMENTAL_DEGRADATION_CLOCKS.md`
and `environmental_degradation.py`.
