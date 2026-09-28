# Field Evidence — Flood Mobility Resource Matching (2026-09-29)

> Status: user-supplied public field report; extracted as operational evidence, not independently verified incident data.
> No personal contact details are stored in this public repository.

## Observed field pattern

A humanitarian coordination call requested and matched multiple mobility resources for flood response:

- high-clearance vehicles;
- trucks;
- 4x4 vehicles;
- ATV/UTV;
- boats / flood-capable watercraft.

Demand was framed around movement of people who may not be able to leave independently, including:

- patients;
- older adults;
- young children;
- people stranded or unable to self-evacuate.

Supply-side information requested:

- area the team can cover;
- vehicle/resource type;
- number of vehicles / teams;
- coordination availability.

Demand-side information requested:

- area / location reference;
- number of people needing assistance;
- type of assistance required;
- operational details needed to match a suitable resource.

## FloodConnect extraction

This is evidence for a **resource-capability matching problem**, not merely a vehicle inventory.

Minimal public matching tuple:

`REQUEST = (zone, people_count, functional_need, movement_need, urgency/deadline)`

`RESOURCE = (tool_type, count, current_node, declared_capabilities, operator/team readiness)`

`ROUTE = (from, to, mode, verified, fresh, status, capacity if known)`

A resource is useful only when all three can meet:

`REQUEST <-> RESOURCE <-> VERIFIED ROUTE`

## Safety boundary

High-clearance / 4x4 / SUV labels do not by themselves prove a flooded road is passable.
FloodConnect therefore stores them as capability-bearing resources while route safety remains an independent hard gate.

## Architecture consequence

Vehicles and other deployable assets should be modeled as **tool/resource nodes** whose capabilities can affect:

- movement edges (who/what can traverse);
- lifeline/support edges (what can be delivered inward);
- Local Convergence Board capacity;
- Shelter Operation capability;
- Human–Animal movement and destination support.

Canonical registry: `site/inputs/community/operational_tools.yaml`.