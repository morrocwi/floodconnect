# M5 water-debt backtest — PROP-FLOOD-03 / PROP-FLOOD-10, EXPERIMENT

**ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo.** Every number in this document is tagged
`PROPOSAL — not yet in Toledo` and is evidence toward a future Toledo registration, never a
user-facing answer (founder ruling 2026-10-05). `water_balance.py` implements PROP-FLOOD-03
(Toledo PR #60, pending, unverified). The Δ10.3 scoring cells are implemented in
`tools/backtest/score_forward_forecast.py` (PROP-FLOOD-10, unregistered).

**n_independent = 6, N_min = 10 → the skill claim is REFUSED FEW_EVENTS.** This holds
regardless of any cell outcome below — stated first, plainly.

## 1. Headline finding

Every single unit-window in this backtest is **REFUSED `MISSING_INPUT`**: `S0` (initial
storage, all 219/219 rows) and `gate_flag` (all 219/219 rows, never declared for any
unit — this runner always passes `gate_flag=None`) are **both universal** blockers,
present in `inputs_missing` on every row, for all 5 national units (HATYAI, NAN,
CHIANGMAI, AYUTTHAYA_BANGBAN, BANGKOK_EAST) *and* for the two already-tracked
Bangkok-area nodes (`sammakorn`, `ram53`, via their existing
`site/inputs/areas/*.balance.yaml`). `Q_out_meas` is also missing on 138/219 rows
(MEASURED recount — not the 136 first estimated — see `test_m5_water_debt_backtest.py`).
The two village rows (`sammakorn`, `ram53`) additionally lack `A`, `c`, `C_pump`, and
`P` — every field water_balance.py needs, not only `S0`. `S0` is not declared anywhere
in this repo's knowledge base for any of the 7 nodes reached; neither is a `gate_flag`
convention for any of them. This is not a Sammakorn/Ram53-specific gap — it is
universal across every node this backtest could reach, and it is **not reducible to a
single missing value**.

Because every row REFUSES, `score_forward_forecast.py`'s `ledger_cell()` maps every one
of them to `UNRESOLVED` (its own rule: `f_state == "REFUSED" → UNRESOLVED`, never
`CORRECT_NEG`). **HIT = MISS = FALSE_ALARM = CORRECT_NEG = 0 everywhere; 219/219 rows
UNRESOLVED.**

## 2. Method

1. **Event set** (`docs/experiments/M5_event_set.yaml`) — 6 independent real-world flood
   events (merging same-event rows across units/districts, per the experiment's frozen scope) + 8 real
   control/quiet periods, ported from this repo's own `raw/backtest/events.yaml`
   (gitignored, 217 unit-days, GloFAS/ERA5-derived) and
   `sources/urban_flood_event_ledger.yaml` (tracked, 32 rows). See §3 for the merge list.
   **Attribution** (corrected this round — NASA-POWER was named as a source in an earlier
   draft; it was a cross-check only during that prior work and **no NASA-POWER value is
   in this file**):
   - Rain: ERA5 reanalysis via Open-Meteo Historical Weather API (CC BY 4.0); contains
     modified Copernicus Climate Change Service information [2010–2026, per event year].
   - Discharge: GloFAS reanalysis via Open-Meteo Flood API (CC BY 4.0); Copernicus
     Emergency Management Service.
   See `docs/experiments/M5_event_set.yaml`'s own `attribution:` block, same text.
2. **Declared static inputs**:
   - `docs/experiments/M5_national_units.yaml` — `A`/`c`/`C_pump`/`S0` for the 5 national
     units, copied unchanged from `sources/backtest_units.yaml`.
   - `site/inputs/areas/sammakorn.balance.yaml` / `ram53.balance.yaml` — already-tracked,
     read unchanged (not modified).
   - `tau := 86400 s` (1 day), this experiment's own declaration (INSTINCT), matching the
     daily granularity of the real rain/flow data available — explicitly different from
     the live site's hourly `tau=3600s` in those same `.balance.yaml` files, never conflated.
3. **No day-chaining (limitation, stated plainly, not re-engineered this round)**: the
   runner scores every unit-day independently, calling `water_balance.step()` with
   `S_prev=None` on every single day — it never threads `S_next` from day *k* forward as
   `S_prev` for day *k+1*, even within the same multi-day event window. A real water-debt
   ledger must chain `S_prev` across consecutive days of the same event/control window;
   this run does not attempt that (out of scope this round, see §5 and the handoff for
   why it would not change this round's result even if implemented: `S0`/`gate_flag`
   refuse every chain's very first link anyway).
4. **Runner** (`tools/backtest/run_m5_water_debt.py`) reuses `water_balance.step()`
   (PROP-FLOOD-03) and `score_forward_forecast.ledger_cell()` (PROP-FLOOD-10 Δ10.3) as-is.
   `c_U`'s declared bound `[0.5, 1.0]` is propagated as an **enclosure** (step() run at
   both ends, keep `[min(S_next), max(S_next)]`) — the one exception to "OPEN means
   refuse" in this run, per the experiment's frozen scope (founder ruling 2026-10-05). Every other missing/OPEN field causes a REFUSED
   outcome via `water_balance.py`'s own reason codes.
5. **Scoring**: per unit-day, `obs := EVENT` if `flooded_significantly` else `NO_EVENT`;
   `cell := ledger_cell(f_state, fires, obs)`. `fires` is structurally `None` on every row
   (acting on a storage increment would need a registered action threshold this
   experiment does not invent — no new equation, no invented threshold, per the frozen
   scope), so every resolvable row would default to `UNRESOLVED` even if `f_state` were
   ever `OK` — moot here since `f_state` is `REFUSED` on all 219 rows anyway.

**C7 bracket** (`[certain, certain + unresolved]`, PROP-FLOOD-10a reuse): applied to the
one count that could ever move, HIT. Certain HIT = 0 (no row resolves OK). Upper bound =
certain + UNRESOLVED = 0 + 219 = 219. Bracket: **HIT ∈ [0, 219]** — trivial here because
nothing is resolved, stated anyway since the rule applies universally, not only when it
bites.

## 3. Independent events (n=6) and merges

| event_id | real-world event | unit(s) scored | tag |
|---|---|---|---|
| `chaophraya_2554` | Oct 2011 Chao Phraya flood | AYUTTHAYA_BANGBAN, BANGKOK_EAST | INSTINCT (per-day window placement; event itself RELAYED) |
| `hatyai_2553` | Oct–Nov 2010 Hat Yai flood | HATYAI | RELAYED |
| `hatyai_2565` | Nov 2022 Hat Yai flood (worst on record) | HATYAI | INSTINCT (per-day window placement; event itself RELAYED) |
| `nan_2567` | Aug 2024 Nan flood | NAN | RELAYED |
| `chiangmai_2567` | Sep–Oct 2024 Chiang Mai (Ping R.) flood | CHIANGMAI | RELAYED |
| `bangkok_2569` | 25–27 Sep 2026 Bangkok road flooding | BANGKOK_EAST (+ sammakorn/ram53 own nodes) | MEASURED+RELAYED |

**Merges applied** (same real event, not double-counted):
- `chaophraya_2554` merges the separately-dated `ayutthaya_2554` and `bangkok_2554`
  unit-day sequences in `raw/backtest/events.yaml` — one real flood, two reaches/units.
- `bangkok_2569` merges **27 of the 32 rows** in `sources/urban_flood_event_ledger.yaml`
  (every `*_2026-09-2[5-7]_*` district row, `bangkok_citywide_disaster_declared_2026-09-27`,
  and `sammakorn_2026-09-26`) — one real 25–27 Sep 2026 rain event, many
  district/city/node-scope ground-truth rows, per the experiment's frozen scope (founder ruling 2026-10-05).

8 real control/quiet periods (`hatyai_control_2015/2017/2019/2021`, `nan_control_2024`,
`chiangmai_control_2024`, `ayutthaya_control_2012`, `bangkok_control_2026`) are scored
too, for completeness, but do not count toward `n_independent` (they are NO_EVENT ground
truth windows, not flood events).

## 4. Counts table (per unit, and total)

| node | HIT | MISS | FALSE_ALARM | CORRECT_NEG | UNRESOLVED | rows |
|---|---|---|---|---|---|---|
| HATYAI | 0 | 0 | 0 | 0 | 83 | 83 |
| NAN | 0 | 0 | 0 | 0 | 27 | 27 |
| CHIANGMAI | 0 | 0 | 0 | 0 | 26 | 26 |
| AYUTTHAYA_BANGBAN | 0 | 0 | 0 | 0 | 41 | 41 |
| BANGKOK_EAST | 0 | 0 | 0 | 0 | 40 | 40 |
| sammakorn | 0 | 0 | 0 | 0 | 1 | 1 |
| ram53 | 0 | 0 | 0 | 0 | 1 | 1 |
| **TOTAL** | **0** | **0** | **0** | **0** | **219** | **219** |

REFUSED (= UNRESOLVED here, since every REFUSED row maps to UNRESOLVED) = 219/219 = 100%.

## 5. What this does and does not show

**Does show**: a real, reproducible, deterministic finding — this repo's knowledge base
has never declared an initial-storage value (`S0`) *or* a `gate_flag` convention for
*any* of the 7 nodes this backtest could reach, national or village-scale (plus, for the
two village nodes, `A`/`c`/`C_pump`/`P` on top of that). These two universal gaps — not
any single missing value, and not primarily a rainfall/outflow data quality issue — are
what block PROP-FLOOD-03 from producing a single resolvable water-debt figure anywhere
in Thailand within this repo's current sources — confirming, at national scope, the same
root cause already known for Sammakorn/Ram53 specifically.

**Does not show**: anything about PROP-FLOOD-03's/PROP-FLOOD-06's skill at forecasting
flood onset (every cell is UNRESOLVED, never HIT/MISS/FA/CN) — this is a REFUSAL-RATE
finding, not a performance finding. It also does not show that `c_U`'s interval-enclosure
propagation changes any outcome: the enclosure code path is **implemented, but not
exercised by any OK row or test on this real dataset** — every row is REFUSED *before*
reaching the c-dependent arithmetic (`S0`/`gate_flag` block it first), so whether
enclosure propagation would actually matter once `S0`/`gate_flag` are declared is
**OPEN**, not answered here. Even if `S0` and `gate_flag` were declared tomorrow, no
`fires`/action threshold exists yet to turn a resolved storage increment into
HIT/MISS/FA/CN — that is a second, separate registration gap.

**Day-chaining is also not exercised** (see §2 item 3): since this round scores every
day independently (`S_prev=None` always), nothing here shows what a correctly-chained
multi-day ledger would find even where S0 could be supplied for day 1 of a window.

**Next step — the observed-storage route the founder is actually asking about**:
everything above is about the *storage-increment* ledger (PROP-FLOOD-03), which needs
`S0` and a stage–storage curve neither node has. A separate route needs **neither**: the
already-real `WL.SMK.01` pond-level gauge (MEASURED, `sources/units_datum_crosswalk.yaml`,
`docs/SAMMAKORN_STANDING_WATER_2026-09-27.md`) can be read directly as PROP-FLOOD-01/02
trend readouts (RISING/FALLING/FLAT) (PROPOSAL, registered — this is now the
shipped v0.1.5 ETA, linear, two windows) and, going forward, the
acceleration-aware time-to-bank PROP-FLOOD-11 (PROPOSAL, registered in
Toledo PR #65, merged 2026-10-06, tier Dr — but NOT IMPLEMENTED in this
release; v0.2 target) — using only the declared critical level for `WL.SMK.01` (bma_watermap,
same gauge and datum), not a volume. That is the founder's actual focus: water over the
bank, judged by how fast it is rising, not a reconstructed storage volume. This M5 round
did not attempt that route; it is the recommended next step (see
`docs/handoff/NEXT_AI_HANDOFF.md`).

## 6. Missing inputs to run at Sammakorn and Ram53

| value | what it is | why needed | likely owner/agency | how to get it | status |
|---|---|---|---|---|---|
| `S0` (sammakorn) | Initial stored volume (m³) in the private retention pond at t=0 of a run | PROP-FLOOD-03's first required term; without it `step()` REFUSES before any arithmetic | N/A — see "how to get it" | Pond level `WL.SMK.01` **already exists and is MEASURED** (from 2026-09-27; see `docs/SAMMAKORN_STANDING_WATER_2026-09-27.md`, `sources/backtest_units.yaml`, `sources/units_datum_crosswalk.yaml`). What is missing is (a) the stage–storage curve for บึงสัมมากร (separate row below) and (b) the `WL.SMK.01` gauge datum (the reference elevation that turns a gauge reading into an absolute level). Until both exist, `S0` stays OPEN. | OPEN — `site/inputs/areas/sammakorn.balance.yaml` |
| **Stage–storage curve** (บึงสัมมากร) | The level↔volume relationship for the pond (m → m³) | Needed to convert a real `WL.SMK.01` level reading into the `S0` volume PROP-FLOOD-03 requires | Village juristic person (pond owner) / BMA drainage division (holds any pond design drawings, per `bma_operating_permission`) | The pond's original design drawings (cross-section/bathymetry) from whichever of the two above parties commissioned the pond, or a fresh bathymetric survey if none exist | OPEN |
| `A` (sammakorn) | Catchment area draining into the pond (m²) | Needed to turn rainfall depth into an inflow volume (`P·A·c` term) | BMA drainage-engineering division (the authority that would hold a catchment delineation) | A GIS catchment delineation of the village's actual drainage boundary (distinct from the OSM building-footprint convex hull already on file, which is explicitly flagged INSTINCT/illustrative-only, not used in the ledger) | OPEN |
| `c` (sammakorn) | Runoff fraction (dimensionless, [0,1]) | Same inflow term as above | N/A (a measured rainfall-runoff relationship, not an administrative fact) | Paired rainfall/pond-level or rainfall/pumped-outflow measurements over several real storms, fitted | OPEN — no bound declared even (unlike the national units' `[0.5,1.0]`) |
| `C_pump`/`D_H` (sammakorn) | Combined ST.SPS.01–04 pump discharge capacity (m³/s) | Caps `Q_out` when the gate/pumps are running | BMA (owns/operates the 4 stations per `bma_operating_permission`) | BMA pump-station design-spec sheet for ST.SPS.01–04 specifically (not found in `raw/gapfill/pump_stations_full.json`'s 172 BMA-registered stations or `water_station.csv` — these are private stations, not in the public registry) | OPEN — `D_H` field in `sources/backtest_units.yaml`'s `normalized_fields.sammakorn` |
| `S0`, `A`, `c`, `C_pump` (ram53) | Same four terms, for Soi Ramkhamhaeng 53 | Same as above | Same (BMA / local committee), plus BMA telemetry stations ST.WTL.01/BKP.01/06/02 whose discharge has never been assigned to this node | No catchment/pump/storage declaration exists for this soi at all today | OPEN — `site/inputs/areas/ram53.balance.yaml` |

An INSTINCT illustrative `S0_m3=249,700` exists in `sammakorn.balance.yaml`'s
`rough_estimate_instinct` block, fenced as chart-only and never a model input;
correctly not used here (this M5 run never reads that block).

### What the 5 national units still lack

| unit(s) | missing | status |
|---|---|---|
| ALL 5 (HATYAI, NAN, CHIANGMAI, AYUTTHAYA_BANGBAN, BANGKOK_EAST) | `S0` — no initial-storage declaration exists anywhere for any of them | OPEN, universal |
| NAN, CHIANGMAI | `Q_cap_o_m3s` (outlet/channel conveyance capacity) — `OUTLET_CAPACITY_UNKNOWN`, separate from `C_pump` which this run does use (declared 0, NO_PUMPS_IN_UNIT) | OPEN |
| ALL 5 | `A_U` is an INSTINCT radius-fallback (no real municipality/catchment polygon) | INSTINCT, usable but flagged |
| ALL 5 | per-tick `gate_flag` (OPEN/CLOSED) — never declared for any national unit; this run leaves it `None`, contributing its own `MISSING_INPUT` independently of, and just as universal as, `S0` | OPEN, universal (same standing as `S0`, not merely out of scope) |
| HATYAI/NAN/CHIANGMAI/AYUTTHAYA_BANGBAN | `C_pump` (=`pumps.P_U_m3s`, declared 0, NO_PUMPS_IN_UNIT) models a pump-limited outlet; for a river-mainstem unit this is a **model-fit caveat**, not a data gap — `water_balance.py` has no outlet-channel-conveyance term, see `docs/experiments/M5_national_units.yaml`'s `model_fit_caveat` | model-fit limitation, not newly invented here |
| AYUTTHAYA_BANGBAN | A real upstream inflow series exists (`raw/backtest/flood/NAKHONSAWAN_C2_UPSTREAM_*.json`, GloFAS, RELAYED) but was **not wired** into this M5 run (no declared edge in this experiment's scope) | out of scope this pass, not a true data gap |

## 7. Scope note (founder ruling: "ทำเท่าที่ทำได้ + ลิสต์ค่าที่ขาด")

Per-tick `P` (rain) is real and available for every national-unit unit-day, and
`Q_out_meas` for 81/219 rows (credible readings only — see §1), in
`docs/experiments/M5_event_set.yaml` (copied from GloFAS/ERA5 archives), and both ARE
passed into the runner — but `S0` and `gate_flag` (both universal, see §1) refuse every
row before they could matter. `gate_flag` was never declared/wired for any node this
round (a genuine architecture gap, same standing as `S0`, not merely "out of scope").
`P` and `Q_out_meas` for the control periods and for Sammakorn/Ram53's own node rows, and
day-chaining of `S_next`→`S_prev` across a window (§2 item 3), were intentionally left
out of scope for this pass since none of them can change the REFUSED outcome while
`S0`/`gate_flag` are universally absent; wiring them is listed above as remaining work,
not hidden.
