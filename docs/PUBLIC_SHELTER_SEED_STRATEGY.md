# Public Shelter Seed Strategy

> Status: FloodConnect repo-specific search strategy / fail-closed.
> Facility archetype is a discovery shortcut, never a safety or shelter-level claim.

## 1. Goal

Find a government/public facility that can become a useful shelter-operation node quickly by reusing
existing infrastructure instead of building a new field site from zero.

## 2. Rule zero

Every real candidate passes the same Dry Gate:

`verified dry operating footprint + fresh evidence + immediate site safety + workable drainage`

No school, sports hall, district office or hospital receives shelter credit from its label.

## 3. Default discovery order

Use this order to **look first**, not to declare a winner:

1. public school, especially a site with gym/hall + cafeteria/kitchen + toilets + yard/loading;
2. public sports/youth/community centre with large hall and sanitation;
3. district/municipal/local-government office as logistics-information hub;
4. primary health centre as linked health-support node;
5. hospital as critical referral node, not default general shelter.

Once actual field evidence exists, archetype priority disappears. The candidate with the smallest
hard capability gap to the requested Shelter Operation level is preferred.

## 4. Why public schools are searched first

A suitable school may already contain several expensive-to-create functions in one public site:

- roofed/large indoor area;
- toilets and service water;
- electricity;
- cafeteria/kitchen or food-service area;
- classrooms/hall/gym that can be zoned;
- yard/vehicle access and potential loading area;
- storage and administrative space.

These are inspection targets, not assumed capabilities.

A school may therefore move rapidly through:

`Dry Gate -> SO-L0 -> SO-L1 -> SO-L2 -> possible SO-L3`

provided every hard requirement is verified.

## 5. Sports/youth centres

Often strong candidates for large day-support or overnight capacity because of open floor area,
parking/loading, toilets and sometimes showers. Common upgrade gaps may include food preparation,
privacy partitions, sleeping equipment and dedicated health/protection functions.

## 6. District/municipal offices

Best treated initially as:

`SO-L0/L1 + Local Convergence Board + route/resource information + staging`

rather than assumed overnight accommodation. They may contribute communications, official local
information, vehicle access and resource coordination while a nearby school/sports centre handles occupancy.

## 7. Health facilities

Primary health centres and hospitals should normally support the shelter cluster without being consumed by
general shelter demand. WHO emergency guidance emphasizes continuity of essential health services and
maintaining health-facility functionality during emergencies.

Default roles:

- primary health centre -> health referral / vulnerable-support node;
- hospital -> critical medical referral / ambulance handoff / inpatient continuity.

A hospital enters general-shelter selection only when explicitly designated for that role and when shelter
operations can be separated from clinical flows without compromising health-service continuity.

## 8. Public Shelter Support Cluster

FloodConnect should prefer a **cluster of complementary public nodes** over forcing one building to provide
every function:

```text
district/municipal office  -> logistics + information + LCB
public school              -> main shelter seed
sports/youth centre        -> overflow / large hall
primary health centre      -> health support
hospital                   -> critical referral
```

This lets capabilities remain distributed but connected.

## 9. Selection rule

For requested target level L:

`Gap_L(site) = RequiredCapabilities(L) - VerifiedCapabilities(site)`

Selection is lexicographic, not weighted:

1. Dry Gate / SO-L0 must already be confirmed;
2. site must be permitted for the requested role;
3. fewer failed hard requirements to target level;
4. fewer UNKNOWN hard requirements;
5. verified dry-side + community-side access;
6. shorter declared distance to affected area.

Facility type is not part of this final evidence ordering.

Executable: `public_shelter_seed.py`

Machine-readable strategy: `site/inputs/community/public_shelter_seeds.yaml`

Tests: `tests/test_public_shelter_seed.py`

## 10. Evidence anchors

- Thai DDPM temporary-shelter manual: https://cnt.disaster.go.th/
- Sphere Handbook shelter/settlement standards: https://handbook.spherestandards.org/
- UNHCR Collective Centres: https://emergency.unhcr.org/emergency-assistance/settlement-and-shelter/settlement-shelter-interventions/collective-centres
- WHO safe health facilities / continuity: https://www.who.int/activities/making-health-facilities-safe-in-emergencies-and-disasters

These sources support safe-site, service, accessibility, lifecycle and health-service-continuity constraints.
They do not define FloodConnect's exact discovery order or L0-L4 ladder.