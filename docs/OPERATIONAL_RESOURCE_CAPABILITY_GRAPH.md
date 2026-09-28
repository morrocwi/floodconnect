# Operational Resource Capability Graph (ORCG)

> Status: FloodConnect repo-specific synthesis / operational architecture.
> Not a claimed FEMA, DDPM, Sphere, UNHCR or IFRC standard.

## 1. Why tools are nodes

Flood response resources are often stored as a flat inventory: car, boat, pump, generator, tent.
That loses the operational fact that one resource can change what a **route**, **support link**, or
**shelter node** can actually do.

FloodConnect therefore introduces a separate operational-resource graph with a generic:

`tool_node`

A tool node is not a household, shelter, egress or road node. It is a deployable resource whose
verified capability can attach to a physical node or edge.

Canonical definitions live in:

`site/inputs/community/operational_tools.yaml`

## 2. Capability transform

For tool/resource r, let kappa(r) be its declared capability set.
For a concrete deployment at time t, capability credit is allowed only when the resource is
verified, fresh, operable and has a qualified operator where required.

Then the effective node capability set can be represented as:

\[
K_v^{eff}(t)=K_v^{base}(t)\cup\bigcup_{r\in R_v(t)}\kappa_{node}(r)
\]

and an edge may gain declared movement/support modes:

\[
M_e^{eff}(t)=M_e^{base}(t)\cup\bigcup_{r\in R_e(t)}\kappa_{edge}(r)
\]

but:

\[
ToolCapability(r) \not\Rightarrow RouteSafe(e)
\]

and:

\[
ToolCapability(r) \not\Rightarrow DryGate(v)
\]

Route safety, site safety and Dry Gate remain independent hard constraints.

## 3. Vehicle/watercraft roles

### Passenger car / sedan
- dry-road personnel and light cargo;
- never gains flood-route credit from vehicle type alone.

### Van / minibus
- multi-person dry-road transport;
- useful for secondary evacuation after transfer from the flood edge to a dry interface.

### Pickup / 4x4
- cargo, personnel and rough-surface access;
- 4x4 capability does not prove flooded-road passability.

### High-clearance response vehicle
- specialized last-mile personnel/cargo/assisted movement;
- useful where a trained response team has a verified route;
- not a generic public instruction to drive into floodwater.

### Heavy cargo truck
- bulk dry-side logistics into an SO-L0/SO-L1 node;
- can increase throughput before last-mile transfer.

### ATV / UTV
- narrow/rough last-mile mobility and light cargo;
- patient transport only when appropriately fitted;
- route/terrain/operator constraints remain hard gates.

### Motorcycle
- rapid courier / very light cargo on verified dry routes;
- not floodwater transport.

### Powered / inflatable rescue boat
- waterborne evacuation, patient/animal movement and relief delivery;
- mission-appropriate craft and trained operators are required.

### Hand-launch raft / skiff
- small-group short transfer where conditions are appropriate;
- not interchangeable with technical swiftwater rescue craft.

## 4. Mobile service vehicles

Thai DDPM operations show that vehicles can be **mobile service nodes**, not merely transport:

- evacuation/disaster transport vehicle;
- drinking-water production/supply truck;
- cooking/meal-production truck;
- mobile power/lighting truck.

These can attach capabilities directly to a dry node, e.g. potable water, meal production, power
or lighting, and may therefore make the next Shelter Operation level attainable when all other
hard requirements are also satisfied.

Thai anchors:
- DDPM rescue-equipment GIS/catalog classifies cars, boats and machinery as disaster resources.
- DDPM flood-response records include evacuation vehicles, flat-bottom boats and pumps.
- DDPM reporting documents mobile drinking-water, cooking and lighting/power vehicles in relief missions.

Sources:
- https://catalog.disaster.go.th/en/dataset/dpm-gd003
- https://gis-portal.disaster.go.th/arcgis/rest/services/Map116/DPM_rescue_equipment_DSS/MapServer/0
- https://elearning.disaster.go.th/subjects/SJ66-00067

Global anchors:
- FEMA Resource Typing Library: resources are categorized by capability, not name alone.
- FEMA Swiftwater/Flood SAR typing includes boat operations and high-clearance vehicle operations
  as distinct response capabilities.
- CDC/NWS flood guidance warns that ordinary vehicles and SUVs do not make floodwater crossing safe.

Sources:
- https://preptoolkit.fema.gov/web/national-resource-hub/resource-typing
- https://rtlt.preptoolkit.fema.gov/Public/Resource/View/8-508-1020
- https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- https://www.weather.gov/mlb/riverflood_rules

## 5. Cross-typology links

One tool can affect several FloodConnect layers at once.

| Tool capability | Movement | Support/LCF | LCB | Shelter Operation | HAHU |
|---|---|---|---|---|---|
| high-clearance response mobility | edge mode | last-mile delivery | transfer throughput | indirect | human/animal transport if equipped |
| rescue boat | water edge | inward/outward lifeline | interface to wet zone | indirect | people + animal evacuation |
| heavy truck | dry logistics edge | bulk supply | staging throughput | SO-L1 support | indirect |
| water truck | delivery edge | closes water gap | supply card | SO-L2/L4 input | animal water if declared/separate ledger |
| cooking truck/mobile kitchen | supply | food inflow | supply card | SO-L3 input | separate animal feed still required |
| generator/power truck | service delivery | power gap | resource card | lighting/critical-power inputs | powered care/animal services where declared |
| portable toilet/handwash | none | WASH support | resource card | SO-L2/L4 input | indirect |
| pump/dewatering | none | preserves access/site | route/site status | may help restore Dry Gate, but cannot certify it itself | indirect |
| radio/repeater | route reporting | coordination | NEED/SUPPLY/ROUTE freshness | SO-L0 communication | indirect |
| stretcher/wheelchair | assisted movement | dependency support | demand matching | accessibility/health support | indirect |

## 6. The structural insight: capability cascade

The important network effect is not the object itself but what becomes possible after it arrives.

Define a verified tool deployment event r -> x. It may change capability at a node/edge:

\[
r \rightarrow \Delta K_x
\]

which can then change several downstream decision layers:

\[
\Delta K_x
\rightarrow
\{EdgeFeasible,\ LCF,\ SOLevel,\ LVCN,\ HAHU\}
\]

This is a **capability cascade**, not a claim that one tool automatically makes the system safe.

Examples:

1. `boat -> verified water edge -> household becomes reachable -> LCF closes medicine gap`.
2. `water truck -> dry interface -> potable-water requirement becomes supportable -> SO-L2 may become attainable`.
3. `generator -> lighting + declared critical power -> overnight capability may become attainable if all other SO-L3 gates pass`.
4. `portable pump -> water removed -> field team re-verifies dry footprint -> only then Dry Gate may change from FALSE/UNKNOWN to TRUE`.
5. `animal carrier + compatible transport -> HAHU movement readiness improves without changing home sustainment`.

The reverse also matters:

\[
ToolLoss \rightarrow CapabilityLoss \rightarrow NodeDowngrade/EdgeLoss \rightarrow LVCN\ Escalation
\]

A failed generator, lost boat, exhausted fuel supply or unavailable operator can therefore propagate quickly
through the network. FloodConnect should display these dependencies instead of hiding them inside a generic
`resources available` flag.

## 7. Resource instance schema

A real deployment should minimally declare:

```yaml
tool_instance:
  tool_id: high_clearance_response_vehicle
  count: null
  at_node: null
  on_edge: null
  verified: false
  fresh: false
  operable: null
  operator_qualified: null
  capacity: null
  capacity_unit: null
  usable_until: null
```

UNKNOWN remains UNKNOWN. The registry defines what a resource *can* provide; the instance defines what is
actually usable now.

## 8. Relationship to Shelter Operation

`shelter_operation_ladder.py` remains constraint-first.

A tool can supply evidence/capability toward a level requirement, but only a verified deployment with adequate
capacity for the declared horizon should satisfy that requirement. Tool type alone never promotes a node.

Most importantly:

`portable pump present != Dry Gate passed`

`water truck present != potable water sufficient for everyone`

`generator present != critical power adequate`

`boat present != route feasible`

This separation is the safety boundary that lets FloodConnect scale without turning inventory into false certainty.
