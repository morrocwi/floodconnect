# Thai Flood Warning Actor Typology (TFWAT)

> Status: FloodConnect role typology / evidence-informed / not an exclusive legal chain of command.

## 1. Why this exists

Thai flood warnings are produced by several agencies that observe different physical systems and issue different
kinds of products. FloodConnect must therefore distinguish **who measures what**, **who interprets what**,
**who integrates**, **who warns the public**, and **who acts locally**.

The typology is a role graph, not a single chain of command.

## 2. Canonical role graph

`OBSERVE -> INTERPRET_SECTOR -> INTEGRATE -> PUBLIC_WARN -> LOCAL_WARN_AND_ACT`

Stages may run in parallel, skip stages, or be performed by the same actor for a specific hazard.

## 3. Core Thai roles

### Meteorological observer / forecaster — กรมอุตุนิยมวิทยา (TMD)

Primary domain: rainfall, storms, severe weather, radar/satellite weather, weather forecasts and meteorological warnings.

Do not convert a weather warning directly into an exact street-flood-depth claim or evacuation order.

### Irrigation water-system operator — กรมชลประทาน (RID)

Primary domain: irrigation reservoirs/canals/structures, water allocation, releases/drainage and water-system management.

Do not treat one RID status as proof of every basin/local drainage condition.

### Flash-flood / watershed EWS — กรมทรัพยากรน้ำ (DWR)

Primary domain: upstream rainfall, flash-flood/landslide early-warning networks and watershed risk monitoring.

DWR's EWS does not stand in for all urban-drainage flooding.

### National water integrator — สำนักงานทรัพยากรน้ำแห่งชาติ (ONWR)

Primary domain: cross-agency water information, integration, coordination and national/basin decision context.

Integration does not mean ONWR owns every underlying sensor or delivers every last-mile warning.

### National public-warning disseminator — ปภ./ศูนย์เตือนภัยพิบัติแห่งชาติ

Primary domain: public disaster warning, warning levels and channels such as Cell Broadcast.

DDPM warning products may depend on hazard information supplied by sector agencies.

### Local last-mile warning and response — จังหวัด / อำเภอ / อปท.

Primary domain: local warning channels, route closures, pump/sandbag operations, shelter opening, rescue and relief.

Local operational evidence can be more specific than national products, but must retain provenance and timestamp.

## 4. FloodConnect extensions

### BMA Department of Drainage and Sewerage

For Bangkok, BMA DDS occupies a combined local role: urban-drainage telemetry/operator plus local operational response.
FloodConnect already consumes canal levels, pump history, road-flood reports and DDS bulletins.

### HII / ThaiWater

HII/สสน. is represented as a hydro-data broker/aggregator where it republishes or integrates telemetry from agencies.
The data publisher/broker must not be confused with the original measurement owner.

## 5. Product semantics

FloodConnect keeps these product classes separate:

- `observation` — physical measurement/readout;
- `forecast` — estimate of future hazard;
- `warning` — official hazard message for a population/area;
- `operational_instruction` — closure/evacuation/shelter/opening or equivalent competent-authority instruction;
- `response_action` — deployment or action taken to reduce harm.

This prevents source laundering such as:

`rain forecast -> exact road flood claim`

`canal gauge -> evacuation order`

`national integration bulletin -> local route safe`

## 6. Contradiction rule

Two products should be compared as contradictory only when they address sufficiently similar:

`hazard + variable + geography + valid time + product semantic`

A TMD severe-weather warning and a BMA canal gauge are normally complementary, not contradictory.

## 7. Mapping to FloodConnect

- source registry: add/retain `actor_role` and `product_semantic` metadata where available;
- contradiction engine: compare like-with-like before raising a contradiction;
- unified crisis state: observations/forecasts update hazard evidence; warnings update official-warning context;
- movement/shelter graph: local operational instructions may close/open edges or change site status;
- Local Convergence Board: warning/route cards should retain issuer, semantic, issue time and valid geography.

## 8. Machine-readable schema

`site/inputs/governance/flood_warning_actor_typology.yaml`

## 9. Evidence anchors

- TMD mission: https://tmd.go.th/department/core-mission
- TMD forecast/warning division: https://www.tmd.go.th/department/weather-forecast-division
- RID duties: https://www.rid.go.th/th/duty_responsibility
- RID water management: https://water.rid.go.th/hwm/wmoc/mwater/
- DWR duties: https://www.dwr.go.th/about_us.php?about_us_id=5
- DWR flash-flood EWS: https://dwr.go.th/uploads/file/infor/2025/Article-250227104243-qMfF.pdf
- DDPM warning datasets: https://catalog.disaster.go.th/group/warning_information
- DDPM Cell Broadcast: https://catalog.disaster.go.th/th/dataset/cell-broadcast
- Local-warning practice: https://www.disaster.go.th/

ONWR is represented as the national water-integration/co-ordination layer based on its statutory/data-integration role;
the typology does not claim it is the sole public-warning issuer.