# HANDOFF — Shelter Decision, Sustainment & Lowest Viable Community Node

**Branch:** `proposal/shelter-sustainment`  
**Status:** design proposal, not operational logic  
**Primary design:** `docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md`

## Goal

Extend FloodConnect from:

```text
situation readout -> community route
```

to:

```text
situation readout
  -> lowest viable support node
  -> stay/sustain or resupply
  -> prepare to move
  -> shelter screening
  -> verified route
  -> shelter operation
  -> return/relocate/close
```

The key contribution is **not "find the nearest shelter"**. It is to find the lowest
support layer at which the community can continue safely without unnecessary movement.

## Settled design decisions

### 1. LVCN is repo-specific
Use the term **Lowest Viable Community Node (LVCN)**. Do not claim it is a FEMA, Sphere,
UNHCR, CCCM or academic standard.

### 2. Lowest layer first
Evaluate in ascending support layer:

```text
household -> buddy_cell -> zone -> internal_safe/community shelter
          -> egress -> verified external_safe
```

A social node can be the LVCN even if people remain in their homes.

### 3. Constraint-first
Do not build a weighted safety/resilience score.

Classification:
- `VIABLE_AND_ESCALATABLE`
- `VIABLE_BUT_ISOLATED`
- `NOT_VIABLE`
- `UNKNOWN`

Missing safety-critical input stays `UNKNOWN`.

### 4. No universal stock-duration default
Do not hard-code "72 hours" or any other horizon unless an authoritative context explicitly
requires it. The evaluator takes a declared `planning_horizon_h`.

### 5. Resupply is conditional
`RESUPPLY_WINDOW` is allowed only with a fresh field-verified route and destination and
without conflicting official movement restrictions. It is an opportunity state, not an
instruction to travel.

### 6. Shelter is a lifecycle
Screening -> access -> operation -> maintenance -> return/relocate/closure.

## Existing code that must remain authoritative

- `community_dag.py` — existing route fail-closed logic.
- `site/inputs/community/self_help_dag.yaml` — current declared topology, initially
  UNKNOWN.
- `water_balance.py` and Toledo proposal discipline — do not bypass/refactor merely to
  implement shelter logic.
- `hierarchical_flood_zoom.py` — hydrologic scale layers remain separate from the
  sustainment decision layer.
- `sources/registry.yaml` — provenance/trust/freshness remain source-of-truth concepts.

## Proposed implementation sequence

### Phase A — schema only
1. Add optional `sustainment` blocks to community nodes.
2. All new operational values default to `UNKNOWN` / null / false.
3. Add schema validation; do not change routing behavior yet.

### Phase B — pure evaluator
Create a small module, suggested name `shelter_decision.py`, with pure functions:

```python
evaluate_sustainment(node, planning_horizon_h) -> classification
find_lowest_viable_node(doc, household_id, planning_horizon_h) -> result
evaluate_resupply_window(doc, node_id, planning_horizon_h, mode) -> result
screen_shelter_candidate(node, needs) -> result
```

No network calls. No hidden defaults. Return reason codes for every refusal.

Suggested refusal/reason vocabulary:
- `MISSING_PLANNING_HORIZON`
- `UNKNOWN_PHYSICAL_SAFETY`
- `INSUFFICIENT_WATER`
- `INSUFFICIENT_FOOD`
- `ESSENTIAL_MEDICINE_GAP`
- `CRITICAL_POWER_GAP`
- `WASH_GAP`
- `COMMUNICATION_GAP`
- `VULNERABLE_SUPPORT_GAP`
- `RESUPPLY_ROUTE_UNVERIFIED`
- `RESUPPLY_DESTINATION_UNVERIFIED`
- `OFFICIAL_MOVEMENT_CONFLICT`
- `NO_ESCALATION_MECHANISM`
- `SHELTER_UNSAFE`
- `SHELTER_CAPACITY_UNKNOWN`
- `NO_FEASIBLE_SAFE_ROUTE`

### Phase C — integrate without coupling
Use existing `community_dag.py` only to determine whether a declared movement/resupply
edge is feasible. Do not duplicate route rules in the new module.

### Phase D — tests
Minimum test cases:

1. household fully viable -> household is LVCN;
2. household not viable, buddy can close the resource/support gap -> buddy is LVCN;
3. buddy insufficient, zone can pool resources -> zone is LVCN;
4. node has supplies but no escalation path -> `VIABLE_BUT_ISOLATED`;
5. stale route -> no resupply window;
6. unverified shop/supplier -> no resupply window;
7. candidate shelter physically unsafe -> rejected regardless of capacity;
8. candidate shelter safe but route blocked -> not usable;
9. external shelter capacity UNKNOWN -> not eligible;
10. vulnerable/medical need not met -> lower node fails;
11. every layer UNKNOWN -> return UNKNOWN/REFUSED, never choose a node;
12. official movement conflict -> do not recommend resupply movement.

### Phase E — real-event anti-leakage replay
Use only timestamp-available evidence.

Priority fixtures:
- Sammakorn / east Bangkok, 26–28 Sep 2026.
- Hat Yai, 18–25 Nov 2025.

Questions to test:
- Could a household remain the LVCN?
- When would a buddy/zone become necessary?
- Was there a verified resupply window?
- When did current-state vs forward-hazard disagreement matter?
- When did route/shelter freshness invalidate a prior decision?

Do **not** estimate saved lives, avoided losses, flood depth, or evacuation-time improvement
without a real deployed comparison.

## Suggested schema

Start categorical and auditable:

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
    status: UNKNOWN
    supplier_node: null
    route_edge: null
    fresh: false
    field_verified: false

  escalation:
    status: UNKNOWN
    target_node: null
    route_edge: null
    assisted_by: null
```

Do not infer resource sufficiency from household wealth, building type, neighborhood,
distance to shops, or other proxies.

## Research anchors

Read before implementing criteria:
- FEMA — Evacuation and Shelter-in-Place planning considerations.
- UNHCR Emergency Handbook — Collective centres.
- UNHCR — Principles & Standards for Settlement Planning.
- CCCM Cluster — Site Lifecycle.
- Sphere Handbook.
- Kongsomsaksakul, Yang & Chen (2005), DOI 10.11175/easts.6.4237.
- Tun et al. (2024), DOI 10.1016/j.eastsj.2024.100152.
- IJDRR (2023) multi-hazard shelter location-allocation, DOI 10.1016/j.ijdrr.2022.103435.

Exact URLs are maintained in
`docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md`.

## Non-goals for the next agent

- Do not invent a national evacuation algorithm.
- Do not optimize shelters before hard safety constraints exist.
- Do not add arbitrary weights.
- Do not convert uncertain community reports into measured telemetry.
- Do not auto-mark hospitals/schools/temples/mosques as safe nodes.
- Do not recommend movement from a stale route.
- Do not silently merge contradictory official sources.

## Definition of done for the next coding pass

A coding pass is acceptable when:
1. all new fields can remain UNKNOWN without breaking current behavior;
2. validator + evaluator are deterministic and reason-coded;
3. old Community DAG tests remain green;
4. new sustainment tests cover fail-closed behavior;
5. no live current-state claim is introduced by the schema;
6. the docs clearly distinguish global guidance from FloodConnect's proposed LVCN construct.
