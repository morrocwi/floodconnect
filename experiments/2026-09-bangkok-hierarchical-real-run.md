# Bangkok 25–26 Sep 2026 — Hierarchical real-data run

**Simulation: NO.**  
All numbers below are historical observations, official design/envelope values, or
official forecasts issued before the event. No synthetic rain, runoff coefficient,
pump output, or point water level is invented.

## 1) Urban forecast layer

### Forecast available before the event

TMD Warning No. 1 (217/2569), issued **21 Sep 2026 17:00**, warned that during
**23–27 Sep** the Central region including **Bangkok and vicinity** would have heavy rain
in many areas and very heavy rain in some areas.

TMD rainfall classes:
- heavy: 35.1–90.0 mm/24 h
- very heavy: >=90.1 mm/24 h

BMA's declared existing-system drainage envelope:
- 80 mm/day

Urban debt screening:

    D[t+1] = max(0, D[t] + P[t] - C[t])

For a dry opening balance (D0=0) used only to isolate the NEW-event load:

Heavy class:
    P in [35.1, 90.0] mm
    new debt in [0, 10.0] mm
    => POSSIBLE_DEFICIT

Very-heavy class:
    P >= 90.1 mm
    new debt >= 10.1 mm
    => ROBUST_DEFICIT at any location that actually receives very-heavy rain

Because the TMD warning did not identify the exact Bangkok point that would receive the
very-heavy core, the correct city-scale output on 21 Sep is:

    URBAN = POSSIBLE_DEFICIT
    LOCATION = UNRESOLVED

This is a warning signal, not a point-depth prediction.

## 2) Observed urban outcome

DDS observed at Saphan Sung:

    P_actual = 203.5 mm/24 h

New-event drainage debt increment:

    ΔD = 203.5 - 80
       = 123.5 mm

Load ratio:

    203.5 / 80 = 2.54375

So the observed rain load at Saphan Sung was about **2.54x** the declared 80 mm/day
drainage envelope.

This is a real observed load comparison. It does not require a guessed opening debt:
for any D0 >= 0,

    D1 >= 123.5 mm

under the coarse urban screening ledger.

## 3) Lead-time validation with real inundation observations

BMA road-flood observations relayed by Thai PBS:

- Nawamin Rd, Bueng Kum: flooding began **25 Sep 14:45**, observed depth later 14.1 cm.
- Ramkhamhaeng 43/1: flooding began **25 Sep 15:55**, observed depth later 17.5 cm.
- Ramkhamhaeng Rd, Suan Luang: flooding began **26 Sep 01:55**, observed depth later 15.5 cm.

From the TMD warning at 21 Sep 17:00:

- to Nawamin onset: **93.75 h** (3 d 21 h 45 min)
- to Ramkhamhaeng 43/1 onset: **94.92 h** (3 d 22 h 55 min)

Therefore this event is a real **urban-event hit with roughly 3.9 days of actionable
lead time**, while point location remained unresolved at warning time.

## 4) Zone / node persistence check using reported city backlog

BMA reported on 26 Sep:
- Phra Nakhon-side accumulated water: 223,000,000 m3
- pumping capacity in operation: about 1,200 m3/s
- stated drain time if no new rain: 2–3 days

Declared-pump-only arithmetic:

    pump per hour = 1,200 * 3,600
                  = 4,320,000 m3/h

If there were no new rain/inflow and the full 1,200 m3/s could be sustained continuously:

    theoretical pump-only clear time
      = 223,000,000 / 1,200
      = 185,833.33 s
      = 51.62 h
      = 2.15 d

Projected remainder under that best-case pump-only assumption:

- after 24 h: 119.32 million m3
- after 48 h: 15.64 million m3
- after 51 h: 2.68 million m3
- after 51.62 h: 0

This is consistent with the BMA's broad **2–3 day** statement, but the exact 48 h lower
edge is slightly shorter than the 51.62 h implied by the two stated numbers alone.
Possible explanations include rounding and/or additional drainage paths not represented
by the single 1,200 m3/s figure. Do not silently resolve that discrepancy.

This section is a consistency calculation, not a claim that measured Qout was exactly
1,200 m3/s every second.

## 5) Point zoom

At Ramkhamhaeng 43/1, the real observed depth was 17.5 cm.

This is useful as **ground truth**:

    point_flooded = TRUE
    observed_depth = 0.175 m

But the point-depth equation

    d = max(0, H_water - z_ground)

still cannot be run predictively for that point from the current FloodConnect archive,
because a pre-event forecast of H_water and a compatible point ground elevation z_ground
were not archived together.

Therefore:

    URBAN PREDICTION: HIT
    NODE/CITY PERSISTENCE: quantitatively consistent with 2–3 day drainage
    POINT OCCURRENCE: observed TRUE
    POINT DEPTH PREDICTION: NOT YET COMPUTABLE

## 6) What this experiment shows

The hierarchy behaves as intended:

    T-3.9 d:
      Urban = POSSIBLE_DEFICIT
      Location = unresolved

    Event:
      Saphan Sung actual load = 203.5 mm
      Urban new debt increment = 123.5 mm
      multiple real road points flooded

    After event:
      Point observations resolve where flooding actually occurred.

The model does not need point-level certainty to issue a useful urban warning. Point and
route precision can be added later as local hydraulic/state data become available.

## Sources

- TMD Warning No.1 (217/2569), issued 21 Sep 2026 17:00:
  https://www5.tmd.go.th/warning-and-events/warning-storm/
- TMD rainfall classification:
  https://www5.tmd.go.th/info/
- BMA annual plan 2026, declared 80 mm/day drainage envelope:
  https://dds.bangkok.go.th/public_content/files/001/0011062_1.pdf
- Thai PBS, BMA road-flood points on 26 Sep 2026:
  https://www.thaipbs.th/news/content/558585
- BMA event figures 223 million m3 / 1,200 m3/s, corroborated:
  https://www.thansettakij.com/general-news/669919
