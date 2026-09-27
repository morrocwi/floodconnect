# Prospective test — Mueang Kanchanaburi urban flooding

**Prediction locked:** 2026-09-27 22:33 ICT  
**Simulation:** NO  
**Hindsight:** PROHIBITED after this commit

## Target

Urban area of **Mueang Kanchanaburi**, Kanchanaburi Province.

## Horizon

From lock time through **2026-09-28 22:33 ICT** (24 h).

## Prediction

**URBAN_FLOOD_EVENT = WATCH / EXPECTED-POSSIBLE**

Operational reading:
- A new urban flooding episode affecting roads/communities in Mueang Kanchanaburi is
  plausible within the next 24 h.
- This is NOT a point-depth forecast.
- Confidence is intentionally not converted to a probability because the local urban
  drainage capacity is not declared.

## Pre-committed success criterion

Count this prospective test as a **HIT** if, before 2026-09-28 22:33 ICT, at least one
of the following is documented inside Mueang Kanchanaburi urban area:

1. an official/local-government/DDPM report of urban road or community inundation; OR
2. at least two named urban road/community locations independently report standing water
   affecting access/traffic.

River-stage rise alone is NOT sufficient to call this an urban-flood HIT.

Count as a **MISS** if no qualifying urban inundation is documented in the target area
during the horizon.

## Evidence available BEFORE lock time

### Weather
TMD daily forecast issued 27 Sep 2026 17:00:
- western Central Thailand: heavy rain in many areas, very heavy in some;
- Kanchanaburi explicitly listed among provinces with possible very-heavy rain.

### Antecedent wetness
Thai PBS Active reported accumulated rainfall in Kanchanaburi districts including the
Mueang area approaching ~200 mm before lock time.

### Hydrologic node
FloodWatch TH telemetry aggregation at 27 Sep 2026 19:25:
- KRN001 Mueang Kanchanaburi: 24.26 m
- flagged "แนวโน้มถึงตลิ่งใน 24 ชม."

Other Kanchanaburi gauges were simultaneously flagged as rising, near-bank, or already
over-bank in other parts of the province.

### Synoptic movement
A government briefing reported the low-pressure area had shifted west from Bangkok
toward Kanchanaburi and explicitly named Mueang Kanchanaburi among watch areas.

## Hierarchical FloodConnect interpretation

### Urban layer
Local drainage capacity C for Mueang Kanchanaburi is NOT declared, so a numerical
drainage-debt value is not fabricated.

Rain-pressure evidence:
- forecast class includes VERY HEAVY (>=90.1 mm/24 h category in TMD terminology);
- antecedent rainfall is already high.

Result:
    URBAN_PRESSURE = HIGH / WATCH
    NUMERIC_DEBT = OPEN

### Node layer
A real water-level node in Mueang Kanchanaburi is already flagged as trending toward
bank level within 24 h.

Result:
    NODE_PRESSURE = RISING / NEAR-BANK-WATCH

This is not equivalent to saying the city is already flooded.

### Point layer
No exact street point is predicted.

Result:
    POINT = UNRESOLVED

## Falsifiability

This file must not be edited after the event to change:
- target geography,
- 24 h horizon,
- success criterion,
- prediction state.

Post-event evaluation must be appended in a NEW file or commit.

## Sources

- TMD daily forecast, 27 Sep 2026 17:00:
  https://www.tmd.go.th/forecast/daily/270920261800
- FloodWatch TH alerts (telemetry aggregation):
  https://floodwatch.vizdata.io/alerts
- Thai PBS Active Kanchanaburi rainfall/flood report:
  https://theactive.thaipbs.or.th/news/disaster-20260926-6
- Government briefing reported by Naewna, 27 Sep 2026:
  https://www.naewna.com/n/top-stories/83803
