# Retrospective backtest — Sammakorn flood, 26 Sep 2026

**Purpose:** test how FloodConnect + Community Self-Help DAG should have behaved from
**T-7** through flood onset, using only information that had been published or could have
been observed by each historical time.

**Target event:** water entering homes in Sammakorn from about 04:00 on 26 Sep 2026,
with community reports later recording up to about 30 cm in Soi 48/3. This target is used
only to score the backtest; the future observation MUST NOT be fed into earlier decisions.

**Anti-leakage rule:** no post-event community flood pattern (which sois flooded first,
later measured depth, later BMA backlog figures, etc.) may be used as if it had been known
before its timestamp. Static terrain/canal/road topology that genuinely existed before
the event is allowed as prior structure, but any unverified route remains UNKNOWN.

## Historical evidence used

1. TMD 7-day forecast issued 19 Sep 2026 12:00 for 19–25 Sep:
   - Bangkok/metropolitan area: 60–80% thunderstorms with heavy rain on 19–20 Sep.
   - 21–25 Sep: 40–60% thunderstorms, with heavy rain highlighted only on 21–22 Sep.
   - General outlook said rainfall would decrease during 21–25 Sep.
   Source relayed at:
   https://www.naewna.com/n/top-stories/69986/

2. TMD warning series first appearing 21–22 Sep for impacts 23–27 Sep:
   heavy to very heavy rain in multiple regions including Bangkok/metropolitan area.
   Official warning archive:
   https://www.tmd.go.th/warning-and-events/warning-storm/

3. TMD daily forecast 22 Sep:
   heavy rain remained possible in Bangkok/metropolitan area; the bulletin explicitly
   described a strong low-pressure area moving toward lower Northeast/East/Central,
   including Bangkok, during 23–27 Sep.
   https://www.tmd.go.th/forecast/daily/220920261200

4. TMD 23 Sep daily forecast:
   Bangkok/metropolitan area could see heavy to very heavy rain in some areas.
   https://www.tmd.go.th/forecast/daily/230920261200

5. TMD 24–25 Sep:
   forecasts strengthened further; on 25 Sep Bangkok/metropolitan area was forecast to
   have thunderstorms over about 80% of the area, with heavy to very heavy rain in some
   places.
   https://www.tmd.go.th/forecast/daily/250920260600

6. BMA preparedness reporting on 23 Sep:
   Bangkok ordered districts to prepare for the 23–27 Sep heavy-rain period, including
   monitoring and drainage readiness. This is supporting institutional evidence, not a
   local Sammakorn measurement.

7. FloodConnect historical community timeline:
   - Ramkhamhaeng 53: public/community reports indicate flooding from about 16:00 on
     25 Sep, with severe flooding continuing overnight.
   - Sammakorn: community reports record water entering some homes from about 04:00 on
     26 Sep.
   These observations are used only at/after their own timestamps.

## Operational state machine

The backtest separates **forecast confidence** from **action cost**. Cheap/reversible
actions can happen early; disruptive movement needs stronger/local evidence.

- S0 NORMAL — routine awareness.
- S1 PREPARE — credible wet-period signal, but no event-specific local prediction.
- S2 READY — multi-day official warning overlaps the area; activate human network and
  verify resources/routes/safe-node candidates.
- S3 ACTIVATE — 24–72 h evidence strengthens; zone coordinators active, vulnerable
  households checked, vehicles/critical items repositioned, safe targets re-verified.
- S4 EARLY MOVE — local leading nodes/telemetry show deterioration or route closure is
  becoming plausible; move vulnerable people/assets only through VERIFIED feasible DAG
  routes.
- S5 RESPONSE — flooding/route failure is occurring; do not invent routes. Use the
  last verified feasible DAG, shelter in place when movement is less safe, and escalate
  life-safety cases to emergency services.

This is not a probability scale.

## Backtest timeline

| Historical time | What was knowable then | FloodConnect state | Correct community action |
|---|---|---|---|
| **19 Sep (T-7)** | TMD 7-day outlook actually suggested rain would ease during 21–25 Sep; Bangkok heavy rain highlighted mainly 19–20 and 21–22 | **S1 PREPARE**, not “flood predicted” | household self-check; buddy contacts; charge/meds/documents; inventory pumps/vehicles; do NOT evacuate or claim 25–26 flood |
| **20 Sep (T-6)** | Heavy-rain risk still exists but exact 25–26 Bangkok event not established | **S1 PREPARE** | keep low-cost preparations; no route declaration without field check |
| **21 Sep (T-5)** | New TMD warning begins to identify 23–27 Sep as heavy/very-heavy-rain period including Bangkok/metropolitan area | **S2 READY** | activate zone contacts; verify which households may need mobility help; survey candidate internal/external safe nodes |
| **22 Sep (T-4)** | Warning repeated; meteorological mechanism now explicitly points toward Central/Bangkok during 23–27 Sep | **S2 READY → S3 candidate** | physically check egresses, drains, electrical hazards, vehicles, radios/power banks; timestamp node/edge status |
| **23 Sep (T-3)** | TMD says Bangkok may have heavy to very heavy rain; BMA orders preparedness | **S3 ACTIVATE** | zone coordinators on duty; buddy acknowledgements; re-verify external-safe-node capacity/services; position resources before roads deteriorate |
| **24 Sep (T-2)** | Repeated official heavy-rain warning, broad government/BMA preparedness | **S3 ACTIVATE** | move low-cost assets/vehicles; vulnerable households ready for early movement; increase verification cadence |
| **25 Sep morning (T-~20 h)** | Bangkok forecast ~80% thunderstorms, heavy to very heavy in some areas | **S3 high / S4 trigger armed** | no mass evacuation from forecast alone; keep verified routes and safe targets live, shorten freshness windows |
| **25 Sep ~16:00 (T-~12 h)** | Ramkhamhaeng 53 community node begins reporting flooding | **S4 EARLY MOVE** for connected vulnerable zones if route/safe target verified | treat nearby-node deterioration as local leading evidence; move vulnerable persons/critical assets before route closure where the DAG proves a feasible path |
| **26 Sep ~04:00 (T0)** | Water begins entering homes in Sammakorn | **S5 RESPONSE** | stop speculative movement; use only fresh verified edges; buddy accountability, rescue/medical escalation, resource delivery, electrical-hazard exclusion |

## Main result

### What a 7-day system could NOT honestly predict

At T-7, the archived 7-day forecast did **not** support a high-confidence statement that
Sammakorn would flood severely on 25–26 Sep. A system that now claims it “predicted the
event seven days ahead” from that information would be using hindsight.

### What the system COULD have done well

The useful lead time appears in layers:

1. **T-7:** preparedness without alarm.
2. **T-5/T-4:** new official multi-day warning -> organize the social network.
3. **T-3/T-2:** stronger Bangkok-specific rain evidence -> activate and verify the DAG.
4. **T-~12 h:** nearby Ramkhamhaeng 53 flooding -> a strong local leading signal for
   early action in connected vulnerable zones.
5. **T0:** switch from forecasting to safe-response routing.

This is the intended FloodConnect behavior:

```
long-range uncertain forecast
        ↓
cheap reversible preparation
        ↓
repeated official warning
        ↓
community network activation
        ↓
local/nearby leading evidence
        ↓
verified early movement
        ↓
event response
```

## Evaluation criteria for future backtests

For each future historical event, score separately:

- **forecast honesty:** did the system avoid claiming what data did not support?
- **activation lead time:** when did S2/S3 occur before impact?
- **local-action lead time:** when did S4 become justified before local impact?
- **false-action burden:** how many costly actions would have been triggered unnecessarily?
- **coverage:** fraction of households acknowledged by buddy/zone network.
- **route validity:** fraction of used edges that were field-verified and fresh.
- **safe-node validity:** no person routed to UNKNOWN/unverified targets.
- **human outcome metrics:** time to contact vulnerable households, requests matched,
  failed contacts, and emergency escalations.

Do not collapse these into one magic score until there is enough event data to justify a
validated aggregation model.

## Immediate engineering implication

FloodConnect should keep **two clocks**:

1. `forecast_horizon` — how far ahead environmental evidence reaches.
2. `action_horizon` — when a particular reversible/irreversible community action is
   justified.

The system's goal is not “be certain seven days early.” It is to **spend uncertainty
wisely**: cheap preparations early, expensive/disruptive actions only when evidence
crosses the corresponding operational constraint.
