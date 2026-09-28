# Shelter Operation Capability Ladder (SOCL)

> **Status:** FloodConnect repo-specific synthesis; implemented fail-closed.
>
> **Not a claimed external standard.** The levels below are a FloodConnect operational
> decomposition built from Thai DDPM shelter guidance, Sphere, UNHCR/CCCM, WHO/CDC
> environmental-health guidance, and peer-reviewed shelter-location research.

## 1. Why a ladder

A flood-response point can begin as a very small safe/dry interface and accumulate capabilities over time.
FloodConnect therefore does not force a binary `not a shelter / full shelter` distinction.

## 2. Rule zero — verified dry operating footprint

The non-negotiable FloodConnect invariant is:

\[
\boxed{\neg DryGate(v,t) \Rightarrow NoShelterOperation(v,t)}
\]

where:

\[
DryGate(v,t)=DrySurface\land Verified\land Fresh\land ImmediateSiteSafety\land DrainageOperational
\]

`DrySurface` refers to the **actual operating footprint** used for people, supplies, vehicles, transfer or sleeping.
It does not mean that the whole surrounding district must be dry.

Operational meaning:
- floodwater/standing water on the operating footprint -> fail;
- `probably dry` without current verification -> `UNKNOWN`;
- stale dry observation -> `UNKNOWN`;
- dry but exposed to an immediate site hazard -> fail;
- dry surface with drainage failure that prevents safe operation -> fail.

This is a FloodConnect hard rule synthesized from multiple evidence anchors. Thai DDPM requires a strong
structure in a safe location, convenient access, utilities, and planned areas for residence, health,
storage/distribution, kitchen and coordination. Sphere requires safe and accessible settlement locations,
avoiding floodplains and keeping dwelling/service areas free of standing water with drainage planned.
UNHCR requires safety, accessibility, infrastructure/basic-service and environmental-hazard assessment.
WHO flood guidance warns against walking/driving through floodwater and highlights contamination and standing-water risks.

Evidence anchors:
- Thai DDPM, `คู่มือการจัดตั้งและการบริหารจัดการศูนย์พักพิงชั่วคราว` (2022): https://cnt.disaster.go.th/
- Sphere Handbook 2018, Shelter & Settlement Standard 2: https://handbook.spherestandards.org/
- UNHCR Emergency Handbook, Collective centres: https://emergency.unhcr.org/emergency-assistance/settlement-and-shelter/settlement-shelter-interventions/collective-centres
- CCCM Site Lifecycle: https://www.cccmcluster.org/resources/coordination-toolkit/site-lifecycle
- WHO, Floods: How to protect your health: https://www.who.int/news-room/questions-and-answers/item/how-do-i-protect-my-health-in-a-flood
- CDC Disaster Shelter Assessment: https://www.cdc.gov/environmental-health-response-and-recovery/php/disaster-shelter-assessment/

## 3. Cumulative capability levels

The external sources do not define this exact L0-L4 ladder. FloodConnect uses the following **repo-specific synthesis**
so field teams can promote a real site in small, testable steps.

### SO-L0 — DRY INTERFACE

Required after the Dry Gate:
- verified provider-side access;
- verified community/last-mile distribution access;
- communication;
- basic first-aid access.

Typical function: shared Kanban, check-in/information exchange, and transfer between dry-road logistics and last-mile teams.
**No overnight occupancy is implied.**

### SO-L1 — RELIEF TRANSFER

Adds:
- safe loading/unloading;
- goods staging/storage;
- separation of people and vehicle flow;
- adequate light/daylight;
- drinking water for workers/responders;
- waste handling.

Typical function: receive bulk aid, sort and transfer, and prevent vehicle pile-up at the flood edge.

### SO-L2 — DAY SUPPORT

Adds:
- declared capacity;
- potable water;
- toilets + hand hygiene;
- weather protection/shade;
- accessible waiting/rest area;
- safe food distribution;
- health referral access;
- functional/vulnerable support.

Typical function: people can safely wait, rest, receive food/water, health referral and assistance during the day.
This level is not yet an overnight shelter.

### SO-L3 — OVERNIGHT SHELTER

Adds:
- sleeping space and bedding/sleeping surfaces;
- privacy and dignity;
- washing/bathing;
- safe food preparation or reliable food provision;
- night lighting;
- structural + fire safety;
- medicine/health support;
- critical power when required;
- resident accountability;
- protection arrangements.

Typical function: people may remain overnight for the declared horizon.

### SO-L4 — FULL SHELTER OPERATION

Adds:
- service water and functioning sanitation/wastewater;
- solid-waste management;
- resupply continuity;
- maintenance/staffing mechanism;
- feedback/complaints;
- child safeguarding and GBV protection;
- family unity and psychosocial referral;
- animal plan when animals are present;
- contingency relocation;
- return/closure plan;
- recurrent reassessment.

Typical function: a sustained collective shelter operation rather than a temporary refuge point.

## 4. Promotion equation

Let `R_k` be the hard requirement set introduced at level `k`. Then:

\[
\boxed{SOLevel(v,t)=\max L\ \text{s.t.}\ DryGate(v,t)=1\land\forall k\le L,\forall r\in R_k:r(v,t)=1}
\]

Three-valued discipline:
- hard requirement `FALSE` -> promotion stops;
- hard requirement `UNKNOWN` -> promotion cannot be claimed;
- many TRUE fields never compensate for one failed hard field;
- current lower level may remain valid while the next level is blocked.

## 5. Relationship to LVCN and Local Convergence Board

- `LVCN`: lowest support layer that keeps a household/community viable.
- `SOCL`: what a physical dry node is currently capable of doing.

A physical node can progress:

`SO-L0 dry interface -> SO-L1 relief transfer -> SO-L2 day support -> SO-L3 overnight shelter -> SO-L4 full shelter operation`

The Local Convergence Board should live at an `SO-L0` or higher node:

\[
\boxed{LCB(q,t)\Rightarrow SOLevel(q,t)\ge SO\text{-}L0}
\]

No verified dry node -> no operational LCB at that location.

## 6. Evidence crosswalk

| Evidence | Contribution |
|---|---|
| Thai DDPM temporary-shelter manual (2022) | safe site, access, utilities, sleeping, health, storage/distribution, kitchen, coordination, lifecycle |
| Sphere Handbook Shelter & Settlement Standard 2 | safe/accessibile location, avoid floodplain, drainage, no standing water, services |
| UNHCR Collective Centres | site/structure assessment, safety/fire/accessibility, water/electricity/wastewater/waste, management/maintenance/exit |
| CCCM Site Lifecycle | site selection/planning through operation, relocation and closure |
| WHO flood health guidance | avoid floodwater exposure; safe water and standing-water risk |
| CDC Disaster Shelter Assessment | repeated environmental-health assessment of operating shelters |
| Trivedi & Singh, IJDRR 2018, DOI 10.1016/j.ijdrr.2018.07.019 | terrain, infrastructure and transport determinants |
| Yoon et al., IJDRR 2021, DOI 10.1016/j.ijdrr.2020.102016 | environmental, structural, emergency-service and transportation screening |
| Sustainability 2022, 14, 12482 review | travel distance/time, capacity and accessibility |
| Journal of International Humanitarian Action 2019 temporary-shelter model | safe distance, sewage/waste, energy, water, heavy-vehicle access, physical adequacy |

## 6A. Tool/resource capability integration

Shelter Operation is linked to the Operational Resource Capability Graph (ORCG).
A deployed tool/resource may contribute evidence toward a non-Dry-Gate requirement only when
its concrete deployment is verified, fresh, operable, adequately sized/capacitated and valid
for the declared planning horizon. Operator qualification is also required where the resource type declares it.

The executable input is `verified_tool_capabilities` on a physical node. For example, a verified
drinking-water truck with adequate capacity/horizon may provide evidence for `potable_water`.

The Dry Gate is intentionally excluded from tool substitution:

`pump present != dry_operating_surface`

After dewatering, the footprint must be field-reassessed and explicitly verified dry.

Cross-typology propagation is documented in `docs/OPERATIONAL_RESOURCE_CAPABILITY_GRAPH.md`:

`tool deployment -> capability gain -> movement/support/shelter change -> possible LVCN change`

The reverse cascade is also tracked conceptually:

`tool loss -> capability loss -> edge loss/node downgrade -> possible LVCN escalation`

## 7. Implementation

- Executable: `shelter_operation_ladder.py`
- Tests: `tests/test_shelter_operation_ladder.py`
- Policy: `site/inputs/community/sustainment_policy.yaml`

The ladder must remain fail-closed and must not certify a real site without current field evidence.