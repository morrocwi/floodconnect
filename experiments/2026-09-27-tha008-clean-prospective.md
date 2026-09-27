# Clean prospective test — THA008 Nakhon Chai Si, 28 Sep 2026

**Prediction locked:** 2026-09-27 22:50 ICT  
**Simulation:** NO  
**Derived FloodWatch alert/24h forecast fields used as input:** NO  
**TMD province warning used as input:** NO

## Target

THA008 สะพานนครชัยศรี, Nakhon Pathom, Tha Chin River.

## Raw inputs available before lock

Bank level:
- 1.95 m

Raw hourly stage observations (selected evening phase):

26 Sep 2026:
- 18:50 = 1.85 m
- 19:50 = 1.92 m
- 20:50 = 1.99 m
- 21:50 = 2.02 m
- 22:00 = 2.02 m

27 Sep 2026:
- 18:50 = 1.95 m
- 19:50 = 2.01 m
- 20:50 = 2.09 m
- 21:50 = 2.08 m

Thus both of the two latest observed evening cycles crossed the independently declared
bank threshold (1.95 m).

## Tide timing, used only as an external phase clock

Pak Nam Tha Chin predicted high tide:
- 26 Sep = 17:40
- 27 Sep = 17:57
- 28 Sep = 18:12

Observed THA008 evening peaks:
- 26 Sep peak in available hourly series = 21:50 (2.02 m)
- 27 Sep peak in available hourly series = 20:50 (2.09 m)

Observed mouth-high-tide -> THA008-peak lags:
- 26 Sep: 4 h 10 min
- 27 Sep: 2 h 53 min

Midpoint/median-of-two lag:
- about 3 h 31 min

Phase-time projection for 28 Sep:
- 18:12 + ~3 h 31 min = ~21:43 ICT

This timing projection does NOT subtract tide height from river stage and does not assume
a shared vertical datum. Tide is used only as a clock/phase signal.

## Independent forecast rule

Use the two-cycle phase-window persistence rule from `raw_stage_forecast.py`:

A threshold recurrence is SUPPORTED only when the same phase window crossed bank in BOTH
of the latest two observed daily cycles.

No linear stage extrapolation is used.

## Locked prospective prediction

**THA008 will be at or above the 1.95 m bank threshold at least once during
2026-09-28 20:30–22:30 ICT.**

Expected peak-phase center:
- approximately 21:40 ICT

This predicts a NODE threshold event only.

## Scoring

HIT:
- at least one raw THA008 observation in 20:30–22:30 is >= 1.95 m.

MISS:
- every raw THA008 observation in that window is < 1.95 m.

UNRESOLVED:
- no raw observation is available in the scoring window.

## What is deliberately NOT predicted

- road flooding in Nakhon Chai Si;
- flood depth at a street/house;
- THA009/Mahachai flooding;
- a numerical THA008 stage such as 2.10 m.

Those require a separate zoom relation / local hydraulic evidence.

## Toledo relation

This is not a replacement for Toledo PROP-FLOOD-03. It is a raw-stage boundary readout.

Toledo remains:

    ΔS = P*A*c + Qin*tau - Qout*tau

The raw-stage persistence result is used only as an observed boundary-state forecast at
a node when the volumetric inputs needed for exact Toledo accounting are not all declared.

## Sources

Raw THA008 hourly series and bank level:
https://floodwatch.vizdata.io/poi/gauge/HII_151

Pak Nam Tha Chin tide timetable:
https://www.thailandtidetables.com/tide-tables-pak-nam-tha-chin-samut-sakhon-year-2026-09-475.php
