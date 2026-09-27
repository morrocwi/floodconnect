# Hat Yai 2025 flood — real-data historical replay / red-team

**Simulation: NO.**  
**Event:** severe Hat Yai flood, Songkhla, November 2025 (B.E. 2568).  
**Replay window:** 18–25 Nov 2025, with earlier official warnings retained when they were
already public before 18 Nov.  
**Rule:** use only information timestamped at or before each replay point. No future
rainfall, peak levels, later damage reports, or hindsight-derived route state may be fed
back into earlier timestamps.

This is an evidence replay to find weaknesses in FloodConnect. It is not a reconstructed
hydraulic simulation and does not invent water depth or travel time.

## Verified source timeline

### 13–14 Nov — risk identified before T-7

ONWR announcement No. 30/2568, dated 13 Nov and published by PRD on 14 Nov, identified
Hat Yai district explicitly among areas to watch for flash floods, runoff and urban
flooding during 17–22 Nov. It told agencies to monitor locations exceeding 90 mm/24 h,
prepare drainage and equipment, and warn residents early enough to evacuate.

Source:
https://www.prd.go.th/th/content/category/detail/id/33/iid/442346

The Southern-East Coast Meteorological Center also issued warning No. 1 (59/2568) on
14 Nov for heavy to very heavy rain during 17–23 Nov.

Source:
https://songkhla.tmd.go.th/warning/2025-59

### 16–18 Nov — strong meteorological signal already present

TMD daily forecast issued 16 Nov said rain would increase in the South during 17–23 Nov,
with heavy to very heavy rain and risk of flash flood/runoff, especially low-lying areas
and areas near waterways.

Source:
https://www.tmd.go.th/forecast/daily/161120251200

Southern-East Coast Meteorological Center forecast issued 18 Nov stated that during
18–23 Nov the eastern South would have heavy rain in many places and very heavy rain in
some locations; monsoon strength would increase during 19–23 Nov.

Source:
https://songkhla.tmd.go.th/static/forecast/daily/2025-11-18_12_daily-forecast_th.pdf

### 19 Nov — official warning remains strong

TMD warning No. 10 (349/2568), issued 19 Nov 17:00, stated heavy rain in many southern
areas and very heavy rain in some areas during 19–23 Nov, due to a strong northeast
monsoon and low pressure over the Gulf/lower South, with explicit flash-flood/runoff
warning.

Source:
https://www.tmd.go.th/warning-and-events/warning-storm/%E0%B8%AD%E0%B8%B2%E0%B8%81%E0%B8%B2%E0%B8%A8%E0%B8%AB%E0%B8%99%E0%B8%B2%E0%B8%A7%E0%B9%80%E0%B8%A2%E0%B8%99%E0%B8%9A%E0%B8%A3%E0%B8%B4%E0%B9%80%E0%B8%A7%E0%B8%93%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B9%80%E0%B8%97%E0%B8%A8%E0%B9%84%E0%B8%97%E0%B8%A2%E0%B8%95%E0%B8%AD%E0%B8%99%E0%B8%9A%E0%B8%99-%E0%B8%9D%E0%B8%99%E0%B8%95%E0%B8%81%E0%B8%AB%E0%B8%99%E0%B8%B1%E0%B8%81%E0%B8%96%E0%B8%B6%E0%B8%87%E0%B8%AB%E0%B8%99%E0%B8%B1%E0%B8%81%E0%B8%A1%E0%B8%B2%E0%B8%81%E0%B8%9A%E0%B8%A3%E0%B8%B4%E0%B9%80%E0%B8%A7%E0%B8%93%E0%B8%A0%E0%B8%B2%E0%B8%84%E0%B9%83%E0%B8%95%E0%B9%89-%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B8%84%E0%B8%A5%E0%B8%B7%E0%B9%88%E0%B8%99%E0%B8%A5%E0%B8%A1%E0%B9%81%E0%B8%A3%E0%B8%87%E0%B8%9A%E0%B8%A3%E0%B8%B4%E0%B9%80%E0%B8%A7%E0%B8%93%E0%B8%AD%E0%B9%88%E0%B8%B2%E0%B8%A7%E0%B9%84%E0%B8%97%E0%B8%A2-%E0%B8%A1%E0%B8%B5%E0%B8%9C%E0%B8%A5%E0%B8%81%E0%B8%A3%E0%B8%B0%E0%B8%97%E0%B8%9A%E0%B8%88%E0%B8%99%E0%B8%96%E0%B8%B6%E0%B8%87%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%97%E0%B8%B5%E0%B9%88-23-%E0%B8%9E%E0%B8%A4%E0%B8%A8%E0%B8%88%E0%B8%B4%E0%B8%81%E0%B8%B2%E0%B8%A2%E0%B8%99-2568-%E0%B8%89%E0%B8%9A%E0%B8%B1%E0%B8%9A%E0%B8%97%E0%B8%B5%E0%B9%88-10-349-2568

### 20 Nov — key contradiction: local current status still green

Hat Yai municipality statement No. 2 on 20 Nov classified the city as normal / green
flag, while broader official forecasts and warnings already indicated a serious
multi-day rainfall hazard.

Source:
https://www.hatyaicity.go.th/news/detail/388300/data.html

### 21 Nov — local state deteriorates sharply

Hat Yai municipality statement No. 3 raised yellow flag for 12 areas. The municipality
later issued statement No. 4 raising red flag for 65 communities on the same date.

Sources:
https://www.hatyaicity.go.th/news/detail/388506/data.html
https://www.hatyaicity.go.th/news/cate/2?limit=36

### 22 Nov 08:00 — red flag expands citywide

Municipality statement No. 5 raised red flag for 103 communities and instructed residents
to move belongings and prepare to enter safe areas.

Source:
https://hatyaicity.go.th/news/detail/393367/data.html

RID reported on 22 Nov:
- U-Taphao canal catchment rain: up to 351.3 mm/24 h
- Khlong Wa: 360 mm/24 h; overflow had affected communities since night of 21 Nov
- Khlong Tam: 346 mm
- Khlong Wat: 366 mm
- drainage canal R.1 being operated at 1,200 m3/s

Source:
https://www.rid.go.th/th/rid_news/26534

### 24 Nov — upstream-to-city crest forecast becomes explicit

ONWR reported that rising water at upstream station X.173A in Sadao would propagate
downstream. It forecast for 25 Nov:
- X.90 Khlong Hoi Khong around 00:00–01:00: 2.26–2.46 m above bank
- X.44 Hat Yai around 06:00–07:00: 2.00–2.20 m above bank

Source:
https://radioprachuapkhirikhan.prd.go.th/th/content/category/detail/id/9/iid/446842

### 25 Nov — catastrophic peak / response phase

Government and emergency reports described Hat Yai as critical, with high-clearance
vehicles, boats and military resources used for evacuation. ONWR stated that 2025 water
levels in the U-Taphao basin exceeded the 2010 major-flood record.

Source:
https://www.prd.go.th/th/content/category/detail/id/39/iid/447043

### 27 Nov — observed peak can be reconstructed from official level report

ONWR reported at 06:00 on 27 Nov:
- X.44 Hat Yai = 7.59 m, already 2.38 m below its maximum, but still 0.19 m above bank
- X.174 Khlong Wa = 9.15 m, 2.67 m below maximum, still 0.27 m above bank

This confirms that the maximum had occurred on 25 Nov and allows a check against the
24 Nov forecast without feeding the peak backward into the replay.

Source:
https://www.prd.go.th/th/content/category/detail/id/33/iid/448211

## What the real replay says

### A. Seven-day preparedness signal existed

For a replay starting 18 Nov, FloodConnect did NOT face the same long-range ambiguity as
the Sammakorn Sep-2026 case. By 18 Nov, several official sources already supported a
material flood-preparedness posture for Songkhla/Hat Yai. ONWR had explicitly named
Hat Yai before T-7, and TMD/local meteorological warnings described heavy to very heavy
rain for the relevant window.

Therefore, for low-cost actions such as:
- household supplies,
- medicines,
- charging/power backup,
- vehicle relocation planning,
- buddy-network activation,
- identifying candidate safe nodes,
- checking drainage/electrical vulnerabilities,

the evidence was already sufficient before city flooding began.

This is an evidence sufficiency finding, not a claim that exact flood depth or exact
street inundation was predictable seven days ahead.

### B. The most dangerous information pattern is not “no warning” but conflicting layers

On 20 Nov the municipality said current water status was GREEN/NORMAL while meteorological
and water-risk agencies were already warning of a multi-day severe-rain window.

FloodConnect must therefore represent at least two independent state axes:

1. **current local water state**
2. **forward hazard state**

A green current-water flag must never zero out a severe forward hazard warning.

### C. Hat Yai exposes a two-pulse / re-escalation problem

RID's post-event technical account describes an initial overflow around 21 Nov from
western/eastern tributary inflows, followed by another major inflow during 23–25 Nov from
the Sadao/Sankalakhiri upstream area.

This means a system that de-escalates after the first apparent stabilization can fail
badly. FloodConnect needs hysteresis / re-escalation memory and must retain upstream
forecast state even after a local node temporarily improves.

### D. Bangkok-style local canal graph is insufficient

Hat Yai requires a catchment-scale directed graph with at least:
- upper U-Taphao / Sadao (X.173A),
- Khlong Hoi Khong (X.90),
- Hat Yai / X.44,
- Khlong Wa (X.174),
- lateral tributaries such as Khlong Tam and Khlong Wat,
- R.1 diversion/drainage structure,
- urban zones and safe nodes.

The graph needs both longitudinal propagation and lateral tributary loading. A pure
nearest-canal or city-only graph would miss the second flood pulse.

### E. Fixed freshness windows are unsafe in fast-rise conditions

Current Community DAG uses boolean `fresh`. Hat Yai shows why freshness must be dynamic.
When an upstream crest is moving and water levels are rising rapidly, a route check that
was valid hours earlier may be obsolete.

Required evolution:
```
freshness_window = function(
    rate_of_level_change,
    rainfall_intensity,
    upstream_forecast,
    edge_type,
    travel_mode
)
```

Do not assign a numeric function until calibrated with real events.

### F. Safe nodes need infrastructure-state verification, not just flood-state verification

During the crisis, Hospital Hat Yai had an urgent electricity problem while critical
patients required ventilators. A hospital cannot be assumed to be a safe node merely
because it is a hospital.

External safe node state must include at least:
- flood/access state,
- electricity,
- backup power/fuel,
- potable water,
- communications,
- medical/service capacity,
- remaining occupancy capacity,
- viable incoming route/mode.

### G. Route mode must be time-varying

By 25 Nov authorities were using high-clearance trucks and boats. An edge cannot simply be
OPEN/CLOSED; it may transition:

```
normal_vehicle -> high_clearance_only -> boat_only -> blocked
```

The Community DAG schema should support mode-specific edge state and capacity.

### H. Extreme rainfall needs an “outside historical operating envelope” state

Warnings used standard heavy/very-heavy rainfall categories, but RID measured roughly
346–366 mm/24 h across several Hat Yai tributary catchments on 22 Nov.

FloodConnect should explicitly surface when observations exceed normal warning bands or
known design/operating envelopes. It must not extrapolate a fabricated flood depth; it
should instead mark the state as **OUTSIDE_CALIBRATED_RANGE / extreme observed load**.

### I. Capacity and throughput are first-class problems

A red alert across 103 communities creates a simultaneous evacuation/resource-allocation
problem. Shortest safe path is not enough.

Future DAG routing needs:
- node occupancy,
- edge throughput,
- vehicle/boat capacity,
- queue/load,
- alternate failure domains,
- resource dispatch matching.

Again, do not create arbitrary weights; use hard constraints and auditable ordering.

## Concrete weaknesses found in current FloodConnect

1. **Source coverage is Bangkok-centric.** No Hat Yai/ONWR/TMD southern warning registry.
2. **Hazard and current state are not separate dimensions.**
3. **Community DAG freshness is boolean, not time/rate aware.**
4. **No catchment-scale upstream propagation graph for non-Bangkok deployments.**
5. **No explicit re-escalation/hysteresis logic for repeated flood pulses.**
6. **Edge mode is static; no normal-car/high-clearance/boat transition state.**
7. **Safe-node schema is too shallow for power/water/comms/service continuity.**
8. **No explicit outside-calibrated-range state for extreme observations.**
9. **No network throughput / evacuation-capacity calculation.**
10. **No anti-leakage historical backtest harness yet; this replay is manual evidence
    discipline, not an automated replay engine.**

## What survives the red-team

The core design choices still look sound:

- UNKNOWN remains UNKNOWN.
- hard constraints before route ordering.
- safe nodes must be verified.
- community network activates before movement.
- official-source disagreement is preserved rather than silently resolved.
- local social/field data complements telemetry.

Hat Yai does not refute the DAG concept. It shows that the DAG must become a
**time-dependent, multi-modal catchment + community graph**, not merely a static
community evacuation graph.

## Next engineering work

Priority order based on this real event:

1. Add `hazard_state` separately from `current_state`.
2. Add timestamped node/edge observations and adaptive freshness hooks.
3. Add mode-specific edge state/capacity.
4. Generalize hydrologic graph interface to catchment chains + tributaries.
5. Add repeated-pulse / re-escalation state memory.
6. Expand safe-node services to power/water/comms/medical continuity.
7. Add throughput-aware resource/evacuation routing.
8. Build an automated historical replay harness that refuses future-dated inputs.
