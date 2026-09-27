# Bangkok 25–26 Sep 2026 — Toledo-strict real-data backtest

**Simulation: NO.**  
This replay uses only archived real forecasts/warnings and real observations. No synthetic
rainfall, no invented runoff coefficient, no guessed pump capacity, and no hindsight-fed
input is allowed.

## Event target

Community reports in FloodConnect record water entering some Sammakorn homes from about
04:00 on 26 Sep 2026. DDS observed 24 h rainfall at Saphan Sung of 203.5 mm in the
26 Sep daily report.

## Forecast evidence available before impact

- 19 Sep: TMD warned heavy/very-heavy rain for 19–20 Sep, but the later 25–26 Sep Bangkok
  event was not yet identified as the main threat window.
- 21 Sep 17:00 daily forecast / advisory: TMD stated that during 23–27 Sep the Central
  region including Bangkok and vicinity would have heavy rain in many areas and very
  heavy rain in some areas.
- The same hazard window was repeated on 22–25 Sep.

Using the 21 Sep 17:00 forecast as the first clearly useful Bangkok signal and the
04:00 26 Sep reported home-entry time gives about **107 hours (4 d 11 h)** of actionable
hazard lead time.

## Category verification

TMD's published rainfall classes:
- heavy = 35.1–90.0 mm / 24 h
- very heavy = >= 90.1 mm / 24 h

Observed Saphan Sung = 203.5 mm / 24 h, therefore the observed rainfall is firmly in the
**very heavy** class.

This is a **category hit** for the 21 Sep warning. It is NOT a numerical forecast-error
measurement because the warning did not issue a point estimate of 203.5 mm for Saphan
Sung. 90.1 mm is a class boundary, not a forecast value; do not compute MAE against it.

For scale only:
- observed / very-heavy threshold = 203.5 / 90.1 ~= 2.26
- observed / BMA declared 80 mm/day drainage envelope = 203.5 / 80 ~= 2.54

The latter is a load comparison, not a Toledo forecast.

## Toledo PROP-FLOOD-03 test

Canonical equation:

    S_b(k+1) = S_b(k)
             + P(k) A_b c_b
             + Q_in(k) tau
             - Q_out(k) tau

with

    Q_out(k) = 0                                  if gate CLOSED
             = min(Q_out_meas(k), C_pump_b)       if gate OPEN

### Sammakorn node

Current declarations:
- A: OPEN
- c: OPEN
- C_pump (private ST.SPS.01–04): OPEN
- S0: OPEN
- Q_in edges: not declared quantitatively

Therefore a strict Toledo historical forecast at Sammakorn is:

    REFUSED
    reasons include MISSING_INPUT / UNDECLARED_AREA

This is the correct outcome. Any numeric flood depth or storage prediction produced here
would require invented inputs.

### Bangkok-east node

Current declarations:
- A: declared only as a Bangkok-wide fallback
- C_pump: partial sourced floor
- c: OPEN
- S0: OPEN

Therefore strict Toledo also REFUSES an exact water-balance forecast at this scale.

## What was actually predictable

1. **At T-7:** the exact 25–26 Sep local flood was not honestly established.
2. **At ~T-4.5 days:** TMD correctly identified a heavy-to-very-heavy rainfall hazard
   window including Bangkok.
3. **Observed outcome:** 203.5 mm/24 h at Saphan Sung verified the very-heavy category and
   exceeded BMA's declared 80 mm/day drainage envelope by 123.5 mm.
4. **Toledo numerical flood prediction:** not yet computable from the currently declared
   local inputs; REFUSAL is required.

## Accuracy verdict

- Hazard-window classification: **HIT**
- Rainfall severity class at an affected east-Bangkok station: **HIT**
- Exact rainfall amount forecast error: **NOT COMPUTABLE from TMD categorical warning**
- Toledo storage/backlog forecast at Sammakorn: **REFUSED — insufficient declared inputs**
- House/road flood-depth forecast: **NOT COMPUTABLE — no declared stage-storage relation**

## What is needed for a true numerical forecast-skill backtest

To compute real MAE/bias/coverage without simulation:
1. archived point/grid precipitation forecasts from the exact historical model runs;
2. observed gauge rainfall at the same location/time resolution;
3. measured/declared c or a calibrated rainfall-runoff transform;
4. measured Q_in and Q_out on declared edges;
5. measured pump/gate state and capacity;
6. S0 or an observed stage-storage state;
7. stage-storage relation if converting storage to water level/depth.

Until these exist, FloodConnect must report categorical forecast skill and Toledo REFUSAL
rather than fabricate a numerical flood prediction.
