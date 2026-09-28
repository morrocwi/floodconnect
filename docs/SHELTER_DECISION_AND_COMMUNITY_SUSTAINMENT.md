# Shelter Decision & Community Sustainment

> **Status:** implemented fail-closed decision layer / not an evacuation order.
>
> This document extends the existing Community Self-Help DAG. It does **not** declare any
> current place safe, does not create a flood-risk score, and does not replace official
> emergency instructions.

## 1. Problem

Flood response is not only a binary choice between "stay home" and "evacuate".

A community may remain physically safe while mobility is degraded for hours or days. During
that interval the important operational questions are:

1. Can the household safely remain where it is?
2. If one household cannot sustain itself, can a buddy cell or zone support it without moving
   everyone?
3. Is there a safe resupply window while verified mobility still exists?
4. When is an internal/community shelter actually needed?
5. If a shelter is needed, is the site itself viable **and** reachable by a fresh verified
   route?
6. When must the community escalate to external/state assistance?

FloodConnect should therefore connect:

```text
water / hazard state
        |
        v
household sustainment
        |
        v
buddy / zone mutual aid
        |
        v
resupply window
        |
        v
internal/community shelter
        |
        v
egress + external shelter
        |
        v
return / relocate / close
```

## 2. Repository term: Lowest Viable Community Node (LVCN)

**LVCN is a FloodConnect design term, not a claimed international standard.**

For a household or community request, let the escalation chain be ordered from the smallest
support unit upward:

```text
household
  -> buddy_cell
  -> zone
  -> internal_safe / community shelter
  -> verified external_safe

`egress` is deliberately excluded from LVCN candidates. It is a movement connector, not a
unit that can sustain people.
```

For a declared planning horizon `T` and evaluation time `t`, FloodConnect separates
two axes that must not be collapsed:

- sustainment: `SUSTAINABLE / NOT_SUSTAINABLE / UNKNOWN`;
- escalation capability: `ESCALATABLE / ISOLATED / UNKNOWN`.

A safe and supplied household can therefore be `(SUSTAINABLE, ISOLATED)`. Unknown escape
mobility must not turn safe occupancy into "not viable", and must not trigger risky self-evacuation.

The **Lowest Viable Community Node** is the lowest support layer that is known to sustain the
affected people for the declared horizon **and is actually connected to them by the appropriate
graph**: identity at household level, verified support delivery for buddy/zone, and verified
resident movement for shelter nodes.

If any lower layer remains `UNKNOWN`, a higher known viable node is returned only as
`KNOWN_VIABLE_UPPER_BOUND`, never falsely reported as the exact LVCN.

The full Thailand-first equation/crosswalk is in
`docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md`.

This is **not** "the smallest shelter". A buddy cell or zone may be the LVCN if households can
remain in place while resources, communication, checks, and assistance are pooled at that
social node.

## 3. Viability is constraint-first, not a weighted score

A node must never become viable because several weak indicators average into a high score.

For planning horizon `T`, evaluate the following as hard/declared states:

### A. Immediate physical safety
- flood / current / electrical / fire / structural hazards are not known to make occupancy
  unsafe;
- if the state is `UNKNOWN`, do not silently treat it as safe.

### B. Essential sustainment
For the declared horizon, the node has either enough declared resources or a feasible
resupply mechanism for:
- potable/drinking water;
- **service water** for toilets, washing and cleaning (separate from drinking water);
- food appropriate to the group, including declared special/infant needs;
- essential medicines / medical consumables and time-critical health access;
- critical power needs where required;
- minimum hygiene / sanitation needs;
- communication/reassessment and functional support needs.

Do not invent a universal 24/48/72-hour number in code. `T` must be supplied by the
planning context, official guidance, or a clearly declared operator decision.

### C. People, household composition and support needs
Do not store one undifferentiated "vulnerable count". Separate:
- children by broad life stage;
- older adults;
- pregnant/postpartum persons;
- chronic/acute illness, disability/functional limitation, bed/home-bound status;
- functional dependencies (supervision, mobility, medicine, time-critical care, powered medical
  devices, communication, special diet, infant feeding);
- living arrangement (alone / pair / family group / multigenerational / group care);
- declared caregiver/helper/buddy/medical/logistics links.

Rules:
- demographic category triggers assessment but does not itself prove incapacity;
- persons who cannot self-move are demand, not counted as helpers;
- co-residence is not evidence of caregiver capability;
- a vulnerable person living alone requires a buddy/reassessment link to be checked;
- a single caregiver supporting dependents requires a backup link to be checked;
- every declared hard functional need must have a current support link, otherwise
  `vulnerable_support` fails or remains UNKNOWN.

See the need-support matching formalization in
`docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md`.

### D. Communication and reassessment
- at least one working communication/reassessment mechanism exists;
- offline fallback may satisfy this requirement if the digital system is unavailable.

### E. Escalation state — reported separately
Escalation capability is important but is **not part of the sustainment truth value**. Report:
- `ESCALATABLE` when a current verified fallback mechanism exists;
- `ISOLATED` when a declared fallback is unavailable/blocked;
- `UNKNOWN` when not verified.

This preserves the distinction between "safe to remain for the declared horizon" and "can leave
safely if conditions change".

## 4. Decision states

FloodConnect should expose a small state machine instead of jumping directly to evacuation.

### 4.1 STAY_AND_SUSTAIN
Use when the current lowest node satisfies the declared sustainment horizon and no hard
constraint requires movement.

This can be:
- one household;
- several households supported by a buddy cell;
- a zone coordinating shared resources while people remain in their homes.

### 4.2 RESUPPLY_WINDOW
A temporary opportunity, **not an automatic instruction to travel**.

It can be declared only when:
- current occupancy remains physically safe;
- essential supplies are insufficient for the declared planning horizon or need replenishing;
- destination/supplier is known and available;
- the route is fresh, field-verified, and feasible for the declared travel mode;
- no current official restriction/order conflicts with the movement;
- the journey itself does not require entering an unverified flood/electrical hazard.

If any route or destination state is stale/unknown, the resupply route is not recommended.

### 4.3 PREPARE_TO_MOVE
Use when continued occupancy may soon cease to satisfy hard constraints, especially when
people need lead time to move, but verified mobility still exists.

### 4.4 SHELTER_SITE_SCREENING
A candidate building/place is **not** a shelter merely because it is a school, temple,
mosque, hospital, community hall, hotel, or high building.

Candidate sites must be screened for at least:
- hazard/flood exposure and drainage;
- structural and fire safety;
- safe access and accessibility;
- potable water and sanitation/WASH;
- electricity / backup where required;
- communications;
- capacity and occupancy;
- medical/accessibility needs;
- ability to receive supplies;
- management/maintenance and an exit/closure plan.

### 4.4A DRY GATE + Shelter Operation Capability Ladder

Every physical shelter/service node now passes the repo-level **Dry Gate** before any shelter-operation
capability can be claimed. The actual operating footprint must be dry, currently verified/fresh, free of
an immediate site hazard, and have drainage that does not prevent safe operation.

`FALSE -> NO_SHELTER_OPERATION`; missing/stale dry evidence -> `UNKNOWN`.

After the Dry Gate, physical-node capability is cumulative:

`SO-L0 dry interface -> SO-L1 relief transfer -> SO-L2 day support -> SO-L3 overnight shelter -> SO-L4 full shelter operation`

These levels are a FloodConnect synthesis, not a claimed external standard. Promotion requires every
hard requirement through that level; no weighted score or abundance of other services can override a
failed requirement. See `docs/SHELTER_OPERATION_CAPABILITY_LADDER.md` and
`shelter_operation_ladder.py`.

This is orthogonal to LVCN: SOCL describes **what a physical node can do**; LVCN describes **the lowest
support layer people actually need**.
### 4.5 EVACUATE_ROUTE
Only after the destination is currently viable and the path satisfies the existing
Community DAG fail-closed route constraints.

A safe node without a safe route is not a usable shelter.

### 4.6 SHELTER_OPERATION
Once opened, shelter operation includes capacity, water, food, sanitation, protection,
accessibility, health support, power, communications, maintenance, supply and governance.

### 4.7 RETURN_RELOCATE_CLOSE
Shelter lifecycle must include exit/return/relocation/closure rather than assuming an opened
site remains appropriate indefinitely.

## 5. Movement and support are different networks

Resident movement remains in `community_dag.py` as the fail-closed movement DAG.

Resource/help delivery is represented separately as `support_edges`. It is **not a DAG**:
food, water, medicine, charging, health support or helpers may move laterally or back toward a
household while residents remain in place.

Therefore:

[
G_{move} \neq G_{support}
]

A resource gap can be closed by buddy/zone only when a current field-verified support path
explicitly carries the required resource category. Geographic proximity is never enough.

## 6. Resource pooling changes the required node level

The LVCN concept intentionally separates **where people sleep** from **where support is
organized**.

Example without invented quantities:

```text
Household A: medicine shortfall
Household B: helper + verified ability to deliver
Buddy cell: communication working
Route A<->B: field-verified and fresh
-------------------------------------
=> Household A alone may be NOT_VIABLE
=> Buddy cell may be VIABLE_AND_ESCALATABLE
=> no community shelter is required yet
```

Similarly, if multiple buddy cells need pooled supplies or transport coordination, the
`zone` may become the LVCN while residents still remain in their own homes.

The design objective is therefore:

[
	ext{use the lowest safe support layer that preserves community function}
]

not:

[
	ext{move people to the largest available shelter as early as possible}
]

## 7. Minimum data model

Do not implement numeric defaults. Every field may remain `UNKNOWN`.

Suggested node block:

```yaml
sustainment:
  checked_at: null
  planning_horizon_h: null

  physical_safety: UNKNOWN
  potable_water_for_horizon: UNKNOWN
  food_for_horizon: UNKNOWN
  essential_medicine_for_horizon: UNKNOWN
  critical_power: UNKNOWN
  wash: UNKNOWN
  communications: UNKNOWN
  vulnerable_support: UNKNOWN

  resupply:
    status: UNKNOWN          # OPEN / ASSISTED / BLOCKED / UNKNOWN
    supplier_node: null
    route_edge: null
    fresh: false
    field_verified: false

  escalation:
    status: UNKNOWN
    target_node: null
    route_edge: null
    assisted_by: null

  classification: UNKNOWN   # computed, never hand-promoted without evidence
```

The initial implementation should prefer categorical evidence over guessed resource
quantities. Quantitative stock-duration models may be added later only when the inputs and
units are measured/declared.

## 8. Interaction with hydrology

The sustainment layer does not replace hydrologic reasoning.

Hydrologic/control nodes answer:
- is the hazard increasing or decreasing?
- is local storage accumulating/draining?
- are receiving canals constrained?
- are pumps/gates available?
- is another upstream pulse possible?

The LVCN layer answers:
- given the best current hazard state, what is the smallest support unit that can still
  safely sustain the people for `T`?
- if that node stops being viable, what is the next feasible escalation?

Therefore:

[
WaterNetwork
ightarrow HazardState
ightarrow LVCN
ightarrow Resupply/Shelter/Route
]

A coarse hydrologic warning must never be laundered into a claim that a particular shelter
or route is safe.

## 9. Evidence and global anchors

FloodConnect should reuse established guidance rather than invent shelter criteria.

### Official / humanitarian guidance
- FEMA, *Planning Considerations: Evacuation and Shelter-in-Place*:
  https://www.fema.gov/sites/default/files/2020-07/fema_DRRA-1209-planning-considerations-evacuation-shelter-in-place_guide.pdf
- UNHCR Emergency Handbook, *Collective centres*:
  https://emergency.unhcr.org/emergency-assistance/settlement-and-shelter/settlement-shelter-interventions/collective-centres
- UNHCR Emergency Handbook, *Principles & Standards for Settlement Planning*:
  https://emergency.unhcr.org/emergency-assistance/shelter-camp-and-settlement/camps/site-planning-camps
- CCCM Cluster, *Site Lifecycle — Setup to Closure*:
  https://www.cccmcluster.org/resources/coordination-toolkit/site-lifecycle
- Sphere Handbook:
  https://spherestandards.org/handbook/

### Peer-reviewed location/allocation anchors
- Kongsomsaksakul, Yang & Chen (2005), *Shelter location-allocation model for flood
  evacuation planning*, DOI: 10.11175/easts.6.4237.
- Tun et al. (2024), *Emergency shelter location-allocation analysis with time-varying
  demand*, DOI: 10.1016/j.eastsj.2024.100152.
- *Assessment of shelter location-allocation for multi-hazard emergency evacuation*
  (2023), International Journal of Disaster Risk Reduction 84:103435,
  DOI: 10.1016/j.ijdrr.2022.103435.

These sources support evacuation/shelter decision, site suitability, access, lifecycle,
capacity and time-varying demand. **They do not establish FloodConnect's LVCN construct.**
LVCN remains a repo proposal that must be tested against real events.

## 10. Safety invariants

1. `UNKNOWN != SAFE`.
2. No weighted safety score may override a failed hard constraint.
3. No route becomes usable from map proximity alone.
4. No named building becomes a shelter without current verification.
5. Resupply is never recommended through stale/unverified routes.
6. A household that cannot self-sustain becomes demand before becoming volunteer supply.
7. Community autonomy is not interpreted as abandonment by public emergency services.
8. If official evacuation/emergency instructions apply, FloodConnect must surface them and
   must not use LVCN to argue against them.
9. No fabricated duration, stock quantity, flood depth, route state or shelter capacity.
10. Historical tests must be anti-leakage: only information available at replay time may be
    used.

## 11. Thailand-specific integration and implementation

The operational implementation is:
- `shelter_decision.py` — sustainment, LVCN, resupply, shelter lifecycle and action state;
- `community_dag.py` — movement constraints/routes;
- `site/inputs/community/self_help_dag.yaml` — fail-closed topology/schema;
- `site/inputs/community/sustainment_policy.yaml` — policy/schema;
- `docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md` — Thailand-first mathematical/ecosystem model;
- `site/inputs/community/shelter_field_evidence_2026-09-28.md` — relayed field failure modes;
- `tests/test_shelter_decision.py` — deterministic fail-closed tests.

See `docs/HANDOFF_SHELTER_DECISION_AND_SUSTAINMENT.md` for continuation rules.
