# Thai Flood Community Sustainment Model (TFCSM)

**Status:** FloodConnect proposal / executable-design target / not a safety order.  
**Scope:** Thai flood crises where households, neighbours, civil society/private service nodes,
local authorities and state agencies may all act concurrently.

This model composes with Toledo-style physical water bookkeeping. It does **not** replace
hydrology, official incident command, or verified evacuation routing.

## 1. Why Thailand needs a coupled model

FloodConnect evidence from Bangkok, Hat Yai and Thai community-based disaster research shows
that flood survival is not determined by water level alone.

The physical system may be represented as a water network, while the social response behaves
as a second network:

```text
WATER / CONTROL GRAPH
rain -> river/canal/storage -> gate/pump -> local water state

HUMAN / SUPPORT GRAPH
household <-> buddy <-> zone <-> civil-society/private service nodes <-> local/state services
                              \-> shelter / transfer / logistics nodes
```

Thailand's practical response therefore cannot be reduced to a single top-down shelter
network. Households frequently remain in place; neighbours, religious institutions,
foundations, volunteer kitchens and private businesses can become temporary service nodes;
local/state resources may enter later or through different access paths.

FloodConnect's design objective is:

> preserve safe household/community function at the lowest feasible support layer, while
> making escalation toward public response explicit and verifiable.

## 2. Global anchors, Thai adaptation

Global literature contributes reusable components:
- evacuation vs shelter-in-place;
- planned shelter lifecycle;
- WASH/food/health/protection constraints;
- multi-agency coordination;
- community-based DRR;
- early warning and risk-knowledge networking.

AIT's DPMM program itself groups disaster work around DRR/resilience, Community-Based DRR,
Risk-Knowledge Networking, multi-hazard assessment, flood/drought, governance, early warning,
GIS and remote sensing. FloodConnect treats these as interacting layers rather than separate
course topics.

Thai research adds a locally important observation: effective flood management can span
family/caregiver, community leaders, local administration, public-sector staff and civil
groups, with success depending on human, work/process, data and resource factors.

Field evidence added to FloodConnect (28 Sep 2026) additionally shows:
- a community/religious building may itself be exposed to receiving-canal flooding;
- an occupied building may retain electricity but lose service water;
- food shortage can induce unsafe travel through floodwater;
- shops can be reachable but depleted;
- a dry private kitchen can become a supply node serving flooded areas;
- NGOs/religious charities can form parallel last-mile food/survival-bag networks.

These are treated as observed mechanisms/failure modes, not as universal Thai cultural traits.

## 3. Five-layer FloodConnect model

### Layer P — Physical water state (Toledo-compatible)

For water/storage node b:

[
S_b(k+1)=S_b(k)+P(k)A_bc_b+Q_{in}(k)	au-Q_{out}(k)	au
]

This remains the physical bookkeeping layer. Missing declared physical inputs => REFUSED.

### Layer H — Household sustainment state

For household/support node i, resource/function r and declared planning horizon T:

- (R_{ir}(t)): currently declared available resource/function state;
- (D_{ir}(t,T)): declared requirement for horizon T;
- (Y_{ir}(t,T)): support that is actually deliverable through verified support paths.

When quantitative units exist:

[
B_{ir}(t,T)=R_{ir}(t)+Y_{ir}(t,T)-D_{ir}(t,T)
]

For essential functions E:

[
V_i(t,T)=
egin{cases}
SAFE_SUSTAINABLE,& 	ext{if physical safety is verified and }B_{ir}ge0 orall rin E\
NOT_SUSTAINABLE,& 	ext{if any verified hard constraint fails}\
UNKNOWN,& 	ext{if any safety-critical term cannot be justified}
end{cases}
]

FloodConnect initially implements the categorical equivalent
SUFFICIENT / INSUFFICIENT / UNKNOWN instead of inventing quantities.

Essential functions are not a weighted score:
- physical safety;
- potable water;
- service water / sanitation;
- essential medicines / time-critical care;
- critical power when required;
- food;
- communications;
- functional support for vulnerable members.

A failure in any hard constraint cannot be averaged away by abundance in another.

### Layer N — Lowest Viable Community Node (LVCN)

Let the support-layer order be:

[
household < buddy < zone < internal/community shelter < external shelter
]

Egress is excluded: it is a connector, not a sustainment unit.

[
LVCN(h,t,T)
=
min_{ell(v)}
{v : v	ext{ can sustain }h	ext{ for }T
	ext{ through verified support relations}}
]

If lower layers are UNKNOWN but a higher layer is known viable, return only a
**KNOWN_VIABLE_UPPER_BOUND**, never falsely claim an exact LVCN.

### Layer F — Function diffusion / service placement

Flooded Thailand often requires services to move toward people before people move toward
shelters.

For service r supplied from node j to demand node i:

[
Y_{ir}(t,T)
=
sum_j x_{jir}(t,T)
]

subject to:

[
0le x_{jir}le
min{Supply_{jr},,EdgeCapacity_{ji,r}}
]

and only when every edge on the declared support path is:
- fresh;
- field verified;
- operational for the relevant delivery mode;
- not in conflict with official restrictions.

If edge capacity is unknown, FloodConnect may still record a categorical deliverability
state but must REFUSE quantitative throughput.

Service-node typology (not automatically shelters):
- `supply_point` — shop/warehouse/stock point;
- `community_kitchen` — converts ingredients/capacity into prepared meals;
- `mobile_service` — boat/truck/team carrying water/food/medicine/comms;
- `micro_hub` — small in-zone service node;
- `transfer_hub` — mode change / triage / logistics boundary;
- `full_service_hub` — dry-area shelter/clinic/warehouse/command combination.

The desirable flood-depth/accessibility gradient is:

[
deep/isolated
ightarrow mobile critical service
ightarrow micro hub
ightarrow transfer hub
ightarrow dry full service hub
]

This is a topology rule, not a claim that every Thai flood must use all node types.

### Layer A — Action state

Given physical state P, sustainment V, LVCN N and verified mobility/support state M:

[
Action(i,t,T)=
egin{cases}
STAY_AND_SUSTAIN, & V_i=SAFE_SUSTAINABLE\
RESUPPLY_WINDOW, & V_i	ext{ has declared resource gap and verified safe resupply exists}\
REQUEST_DELIVERY, & resource gap exists, resident movement is unsafe/unverified, support delivery exists\
PREPARE_TO_MOVE, & occupancy is becoming non-viable and verified movement remains available\
REQUEST_ASSISTED_EVACUATION, & occupancy non-viable and self-movement not verified\
EVACUATE_ROUTE, & applicable official instruction + verified feasible route/destination\
VERIFY_BEFORE_ACTION, & critical state remains UNKNOWN
end{cases}
]

Official evacuation instructions are surfaced and never overridden by LVCN logic.

## 4. Thai social-response topology

FloodConnect models Thai response as **converging networks**, not a single command tree:

[
Self
leftrightarrow Buddy
leftrightarrow Zone
leftrightarrow CivilSociety/Private
leftrightarrow LocalGovernment
leftrightarrow State
]

Different actors may start independently and later connect.

### Strengths observable in Thai cases
- strong household/family persistence and preference to remain near home;
- rapid neighbour mutual aid;
- religious/community institutions can mobilize trusted communication/resources;
- volunteer foundations and private kitchens can activate quickly;
- relatives' homes can be real alternative destinations;
- local knowledge identifies vulnerable residents and blocked access that central datasets miss.

### Failure modes observable in Thai cases
These are system/process failure modes, **not essential traits of Thai people**:
1. **coverage asymmetry** — some buildings/zones receive aid while nearby ones are missed;
2. **inventory blindness** — a mapped shop exists but shelves may be empty;
3. **last-mile severance** — supplies exist outside the flooded zone but cannot reach households;
4. **self-exposure pressure** — hunger/medicine gaps push people into unsafe water;
5. **service-water neglect** — drinking water/food may arrive while toilet/washing water fails;
6. **vulnerability invisibility** — aggregate population counts miss mobility, medication,
   infant feeding and older-adult-alone needs;
7. **volunteer coordination load** — many independent helpers can create duplicated and missed
   coverage without a shared demand/supply map;
8. **site-label fallacy** — mosque/school/hospital/community building is assumed safe from its
   identity rather than current hazard/access/service state;
9. **state/community timing mismatch** — public, private and community actors may activate at
   different times and with different information;
10. **recovery discontinuity** — food rescue is visible during inundation, while cleaning,
   sanitation restoration, health follow-up and return support can become the next bottleneck.

## 5. Household composition and dependency pairing

FloodConnect must not represent vulnerability as one scalar or one undifferentiated
`vulnerable_people` count.

Use two independent dimensions:

1. **who is present** — age/life stage and functional needs;
2. **who/what supports whom** — caregiver, buddy, medical, power, mobility and logistics links.

Examples:

```text
child_0_5
  -> caregiver
  -> feeding / hygiene
  -> assisted evacuation

older_adult + mobility dependency
  -> caregiver or buddy
  -> essential medicine
  -> mobility/transport support

pregnant/postpartum person
  -> companion/buddy
  -> maternal-health access
  -> transport/referral if needed

time-critical patient
  -> caregiver/buddy
  -> verified medical referral
  -> verified transport

medical-device power dependency
  -> critical power
  -> backup power
  -> medical escalation

single-person household
  -> buddy/check-in relation

single-caregiver household + dependents
  -> backup caregiver/buddy relation
```

The important variable is therefore not simply whether a person belongs to a demographic
group. It is whether a **declared functional dependency is covered**.

Let (D_h) be the set of declared dependencies in household (h), and let (L_d(t)) be
the state of the required support link for dependency (d):

[
C_h(t)=
egin{cases}
COVERED,& L_d(t)=VERIFIED orall din D_h\
UNCOVERED,& exists din D_h: L_d(t)=FAILED\
UNKNOWN,& 	ext{otherwise}
end{cases}
]

This avoids two errors:
- treating every older adult/pregnant person/child as incapable;
- treating a household with multiple adults as automatically self-sufficient.

Living arrangement is therefore first-class:
- single-person household;
- older adult living alone;
- single-caregiver household;
- dependents with no co-resident capable adult;
- multiple capable adults;
- co-resident caregiver(s).

A demographic category alone never changes LVCN status. An uncovered **functional support
dependency** can.

---

## 6. Minimum-function bottleneck

For a community c, define categorical minimum-function state:

[
MF_c(t,T)=igwedge_{rin E}F_{cr}(t,T)
]

where logical AND is fail-closed:
- all essential functions known sufficient => SUSTAINABLE;
- any known essential failure => NOT_SUSTAINABLE;
- otherwise => UNKNOWN.

This is intentionally **not**:

[
Score=sum_r w_rF_r
]

because a high food score cannot compensate for unsafe electricity, absent water, or an
unmet dialysis/medical-transfer dependency.

## 7. Human-Work-Data-Resource decomposition

Thai community research identifies four contributing domains. FloodConnect maps them as:

[
CommunityCapacity_c(t)=
H_c cap W_c cap D_c cap R_c
]

where:
- (H) Human = helpers/caregivers/skills/available people;
- (W) Work = roles, procedures, rehearsal, coordination;
- (D) Data = current household needs, hazard, access, source provenance/freshness;
- (R) Resource = food, water, medicine, power, boats, vehicles, funds, facilities.

The intersection symbol is deliberate: FloodConnect does not average these into a resilience
score. A missing critical domain can block an action.

## 8. Demand-supply gap for Thai volunteer/civil-society response

For zone z and resource r:

[
Gap_{zr}(t,T)=
Demand_{zr}(t,T)-VerifiedAvailable_{zr}(t,T)
]

[
VerifiedAvailable=
LocalStock+DeliverableExternalSupply
]

not:

[
LocalStock+AllDonationsPromised
]

A central kitchen therefore becomes useful only when:
- demand is identified;
- ingredients/cooking capacity are available;
- output can be delivered over verified paths;
- coverage is tracked to destination zones/households.

Likewise, "1,000 meals produced" is an output measure, not proof that the highest-need
households were reached.

## 9. Crisis typology

### Type 1 — Water hazard high, household functions intact
Action: stay/sustain + watch + maintain escalation information.

### Type 2 — House safe, one/more lifelines failing, route still verified
Action: resupply window or support delivery depending on who can move safely.

### Type 3 — House safe, routes degraded/unknown, external supplies exist
Action: buddy/zone aggregation + last-mile delivery; no unsafe self-resupply.

### Type 4 — Local community service capacity failing
Action: connect zone to civil-society/private/local-government nodes; deploy mobile/micro hubs.

### Type 5 — Occupancy unsafe but movement available
Action: prepare/move to verified shelter/relative/private destination.

### Type 6 — Occupancy unsafe and movement unavailable
Action: assisted evacuation/rescue request; household cannot be treated as self-sustaining.

### Type 7 — Shelter itself degrades
Action: resupply/intervention/relocation based on failed function; shelter identity does not
override current constraints.

### Type 8 — Water recedes but recovery lifelines fail
Action: cleaning/WASH/electrical/health/return support; do not close incident merely because
water level falls.

## 10. Relationship to Toledo

Toledo remains the physical conservation/refusal layer:

[
Delta S = PA c + Q_{in}	au-Q_{out}	au
]

FloodConnect adds the socio-operational conservation/refusal layer:

[
Delta R_{ir}
=
SupplyIn_{ir}
-
Consumption_{ir}
-
Loss_{ir}
+
MutualAid_{ir}
]

when quantitative observations exist.

The coupled state is:

[
X(t)=
ig(S_{water}(t),,R_{essential}(t),,G_{movement}(t),,G_{support}(t)ig)
]

and the decision operator is:

[
pi(X,T)
ightarrow
{stay,resupply,deliver,prepare_move,evacuate,assist,recover,verify}
]

subject to the same epistemic law:

[
Missing critical input Rightarrow REFUSE/UNKNOWN,
quad not guessed substitution.
]

This is the core FloodConnect extension: **conservation of water is coupled to conservation
of essential community function.**

## 11. Research/falsification agenda

The model should be rejected or revised if real event replay shows that:
- lower-node sustainment cannot be represented without forced centralization;
- categorical fail-closed logic systematically causes harmful delay despite good inputs;
- service diffusion does not improve coverage relative to simple nearest-shelter logistics;
- LVCN classification is unstable under small, credible changes in verified inputs;
- Thai field cases require important actor/node types not representable by the support graph.

Real validation must use timestamped evidence with anti-leakage. Do not claim lives saved,
losses avoided or optimized evacuation time without deployed comparison data.

## Evidence anchors

- Yodsuban & Nuntaboot (2021), *Community-based flood disaster management for older adults
  in southern of Thailand*, International Journal of Nursing Sciences 8:409-417,
  DOI 10.1016/j.ijnss.2021.08.008.
- Krongthaeo et al. (2021), *Community-based flood preparedness for Thai dependent older
  adults*, International Journal of Disaster Risk Reduction 63:102460,
  DOI 10.1016/j.ijdrr.2021.102460.
- Zhong et al. (2019), *Planned sheltering as an adaptation strategy to climate change*,
  Science of the Total Environment 694:133586,
  DOI 10.1016/j.scitotenv.2019.133586.
- AIT Disaster Preparedness, Mitigation and Management program: Community-Based DRR,
  Risk-Knowledge Networking, disaster governance, early warning, flood/drought, GIS/RS.
- FEMA, *Planning Considerations: Evacuation and Shelter-in-Place*.
- Existing FloodConnect field evidence:
  `site/inputs/community/shelter_field_evidence_2026-09-28.md`.


## Water lifeline separation

FloodConnect treats three household water-related functions as independent hard constraints:

1. **Drinking water — น้ำดื่ม**
   Internal field: `potable_water_for_horizon`.

   This is water verified suitable for ingestion and oral-consumption uses where potable
   water is required. It is not inferred from clear appearance, lack of odor, or the
   availability of other household water.

2. **Clean service water — น้ำสะอาดสำหรับใช้**
   Internal field: `service_water_for_horizon`.

   This supports declared hygiene/service functions such as washing, bathing and cleaning.
   It is not automatically drinkable.

3. **Sanitation function — ระบบส้วม/ระบายน้ำเสีย**
   Internal field: `sanitation_hygiene`.

   This represents whether toilets, drains and wastewater can function safely. A household
   may have both bottled drinking water and clean service water while sanitation still fails
   because of sewer surcharge/backflow.

For a declared planning horizon T:

[
T_{drink}=rac{Stock_{drink}+VerifiedInflow_{drink}}{DemandRate_{drink}}
]

[
T_{clean}=rac{Stock_{clean}+VerifiedInflow_{clean}}{DemandRate_{clean}}
]

where quantitative division is used only when stock, inflow and demand-rate units are
measured/declared.

The effective household WASH horizon is:

[
T_{WASH}
=
min(
T_{drink},
T_{clean},
T_{sanitation}
)
]

This means:

[
DrinkingWater=SUFFICIENT

otRightarrow
CleanWater=SUFFICIENT
]

and:

[
CleanWater=SUFFICIENT

otRightarrow
Sanitation=FUNCTIONAL
]

The separation is important in Thai flood cases where bottled drinking water can still be
available while tap/service water, toilets or drainage fail.


## Human–Animal Household Unit

Thai flood response repeatedly shows that household continuity may include companion animals
and, in some settings, livestock/working animals. FloodConnect therefore models:

U_h = H_h union A_h

while keeping human and animal resource ledgers separate.

For a co-resident/co-evacuating animal unit:

B_a_r(T) = Stock_a_r + VerifiedInflow_a_r(T) - Demand_a_r(T)

and the household-unit effective horizon is:

T_HAHU = min(T_human_effective, T_animal_effective)

Animal hard constraints may include:
- animal drinking water;
- species-appropriate feed;
- required medication;
- litter/waste hygiene;
- containment/transport;
- animal-compatible destination;
- veterinary support when declared necessary.

Evacuation feasibility becomes:

Move_HAHU =
HumanRoute
AND AnimalContainment
AND AnimalTransportCapacity
AND DestinationAnimalCompatibility

A failed animal constraint never authorizes remaining in a physically unsafe location.
The action becomes assisted evacuation with animals or a separate verified animal plan.

See:
- docs/HUMAN_ANIMAL_HOUSEHOLD_UNIT.md
- human_animal_household.py
- site/inputs/community/human_animal_field_evidence.md
