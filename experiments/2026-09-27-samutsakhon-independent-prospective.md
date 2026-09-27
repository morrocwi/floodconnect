# Prospective test — Mueang Samut Sakhon / Mahachai, 28 Sep 2026

**Prediction locked:** 2026-09-27 22:41 ICT  
**Simulation:** NO  
**TMD province-name warning:** NOT USED FOR TARGET SELECTION  
**Hindsight:** PROHIBITED after this commit

## Why this target was selected independently

The target was selected from hydrologic state + upstream pressure + tide, not from TMD's
province list.

Observed before lock time:

### Upstream Tha Chin basin pressure
- Suphan Buri provincial ThaiWater page (27 Sep):
  - 24 h max rain 177.1 mm
  - 4 rainfall stations in "very heavy" class
  - 16 stations in "heavy" class
  - 3 of 7 water-level stations over bank
- Nakhon Pathom provincial ThaiWater page (27 Sep):
  - 3-day rain 205.0 mm at Thaiyawat/Nakhon Chai Si
  - 7-day rain 235.4 mm at Nakhon Chai Si
  - 5 of 7 water-level stations over bank
- FloodWatch TH:
  - THA008 Nakhon Chai Si was at ~100% bank / near-bank alert.

### Target-city node pressure
FloodWatch TH, 27 Sep 19:25:
- THA009 Mueang Samut Sakhon: 1.40 m, ~94% of bank, "trend to bank within 24 h"
- TTC09 Wat Tha Krabue, Samut Sakhon: 1.77 m, ~94% of bank, "trend to bank within 24 h"

The DDPM national flood summary published 27 Sep did NOT include Samut Sakhon among the
25 provinces with active flood situations at that reporting time. This makes it a useful
prospective target rather than an already-declared flood province.

### Downstream boundary / tide
Published tide table for Tha Chin estuary:
- 28 Sep high tide 06:25, 3.13 m
- 28 Sep high tide 18:12, 3.10 m

A high downstream boundary can reduce discharge head and/or raise the tidal river stage.
No direct stage conversion is assumed because datums and transfer functions are not
declared.

### Local rain
Samut Sakhon provincial ThaiWater page available before lock showed only moderate recent
local rainfall (24 h max on the retrieved snapshot 21.2 mm), while all 3 water-level
stations were already in "high water" class.

Therefore the forecast is deliberately a **hydrologic propagation/backwater test**, not
a heavy-local-rain test.

## Hierarchical calculation

### Urban layer
Local rainfall alone does NOT establish an 80-mm-style urban drainage deficit.

    local-rain debt signal = NOT ROBUST

### Node layer
The local node has only ~6% bank headroom:

    headroom_ratio = 1 - 0.94 = 0.06

Two independent Samut Sakhon nodes are simultaneously at ~94% bank, while upstream
Tha Chin nodes are already at/over bank and a high-tide boundary is approaching.

Toledo criterion:

    ΔS = P*A*c + Qin*tau - Qout*tau

Exact ΔS cannot be computed because Qin/Qout/A/c are not fully declared at this node.
However the observed state places the node near its storage/stage boundary and gives a
falsifiable near-term event target.

## Locked prediction

### Primary measurable prediction
**THA009 Mueang Samut Sakhon will reach or exceed its bank threshold at least once
between lock time and 2026-09-28 09:00 ICT.**

### Secondary urban prediction
**At least one low-lying road/community in Mueang Samut Sakhon / Mahachai will report a
new inundation episode affecting access between 2026-09-28 04:00 and 10:00 ICT.**

This is expected to be associated more with high river/tidal boundary pressure than with
extreme new local rainfall.

## Pre-committed scoring

Primary:
- HIT: THA009 >= bank threshold / over-bank status before 09:00
- MISS: THA009 remains below bank through 09:00

Secondary:
- HIT: official/local-government or two independent named-location reports document
  road/community inundation affecting access in Mueang Samut Sakhon/Mahachai during
  04:00–10:00
- MISS: no qualifying new inundation report during that window
- UNRESOLVED: source outage prevents checking the target

Do not change geography, time window, threshold, or event definition after this commit.

## External check after target selection

TMD may be consulted only AFTER locking this file as an external comparator. Agreement
or disagreement must not change the locked forecast.

## Sources available before lock

- Suphan Buri ThaiWater provincial dashboard:
  https://suphanburi.thaiwater.net/
- Nakhon Pathom ThaiWater provincial dashboard:
  https://nakhonpathom.thaiwater.net/
- Samut Sakhon ThaiWater provincial dashboard:
  https://samutsakhon.thaiwater.net/
- FloodWatch TH alerts:
  https://floodwatch.vizdata.io/alerts
- DDPM/PRD national flood summary, 27 Sep 2026:
  https://www.prd.go.th/th/content/category/detail/id/33/iid/545372
- Tha Chin estuary tide table:
  https://www.thailandtidetables.com/
