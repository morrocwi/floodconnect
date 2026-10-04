# BACKTEST_PROP_FLOOD_06_v2 — falsifier loop รอบ 3 (v5 leading promoters + persistence)

**PROP-FLOOD-06 PROPOSAL v5, unverified** — เอกสารนี้รายงานผลการทดสอบข้อเสนอ ไม่ใช่ผลลัพธ์ของสมการ
Toledo ที่ขึ้นทะเบียนแล้ว เขียนโดย worker แยก (write-scope: ไฟล์ใหม่เท่านั้น ไม่ commit ไม่แก้ไฟล์เดิม)

**Version implemented**: `toledo-wt-flood06` HEAD `ebd34071` (`registry/proposals/flood_outlet_coping.json`
+ `docs/proposals/PROP-FLOOD-06.md`, PROP-FLOOD-06 v5) — the same falsifier loop that motivated
this v5 bump (`docs/BACKTEST_PROP_FLOOD_06_v1.md`, RELAYED into that proposal's own MD).

Code: `tools/backtest/prop_flood_06_v5.py` (engine, reuses `prop_flood_06_v3.py`'s
`coverage_vector`/`compute_C_H`/`s_band`/`t_act_band` unchanged), `tools/backtest/run_backtest_v2.py`
(runner) → `raw/backtest/results_v2.jsonl` (1,892 readout rows).

## 1. วิธีการ (สรุป)

- Same 271 unit-days as v1 (HATYAI 93, NAN 56, CHIANGMAI 41, AYUTTHAYA 41, BANGKOK_EAST 40) ×
  c∈{0.5,1} × H∈{24,48}, **plus a τ_up sweep {0,6,12}h for NAN only** (per this check's brief) —
  **1,892 rows total** (NAN alone contributes 3× its base row count: 876; HATYAI 456; CHIANGMAI
  228; AYUTTHAYA_BANGBAN 164; BANGKOK_EAST 168).
- **cov5(U)**: v3/v4's 7-component `cov(U)` plus 3 LEADING components — `upstream_rise_rate`,
  `basin_rain_accum`, `forecast_rain_72h`. `coverage_n_of_10` reported per row.
- **v4's promoter-floor fix, applied for the first time in this repo's backtest history**: v1's own
  report noted v4 was not at HEAD when it ran, so v1 used v3's exclusive FULL-xor-PARTIAL mode
  split. This run implements `base_tier := max(band_tier, promoter_max)` in **every** mode — a
  FULL-mode unit whose ledger resolves to a low `S_H` can still be raised by a promoter, exactly as
  the registry's `full_tier_v4_full_ge_partial`/`_promoter_monotone` theorems require.
- **3 new LEADING promoters** (`UPSTREAM_RISE_RATE_EXCEEDS` L3, `BASIN_RAIN_ACCUM_EXCEEDS` L2,
  `FORECAST_RAIN_72H_EXCEEDS` L1), thresholds **declared by this check, INSTINCT/OPEN, not sourced
  from the registry** (the registry itself leaves the national defaults TBD): rise-rate >15% over
  lag-24h; basin rain 24h >80mm (reuses `RAIN_24H_EXCEEDS_DESIGN`'s figure per the registry's own
  suggestion) or 72h >150mm; forecast 72h >150mm.
- **Upstream gauge per unit** (declared per this check's brief, see `tools/backtest/run_backtest_v2.py`
  module docstring for full detail):
  - **NAN ← N.64** (Tha Wang Pha, station 3246) — CONFIRMED real upstream gauge, hourly discharge.
    τ_up swept {0,6,12}h.
  - **CHIANGMAI ← P.1 itself** — no confirmed real upstream gauge anywhere in this repo
    (P.67/P.75 unconfirmed) — **DEGRADED-SELF-AS-UPSTREAM**, τ_up=0h.
  - **HATYAI ← X.44 itself** — **DEGRADED-SELF-AS-UPSTREAM**, additionally flagged
    **DOWNSTREAM-OF-R1-INTAKE-EXPECTED-WEAK** per this check's brief, τ_up=0h.
  - **AYUTTHAYA ← C.2 Nakhon Sawan**, via the already-fetched GloFAS/Open-Meteo daily series
    (`raw/backtest/flood/NAKHONSAWAN_C2_UPSTREAM_*.json`, same proxy already used as this unit's
    `Q_in,up` in v0/v1) — **RELAYED-GloFAS**, daily granularity only, τ_up=48h declared **INSTINCT**
    (order-of-magnitude Chao Phraya travel time Nakhon Sawan→Ayutthaya, not independently sourced).
  - **BANGKOK_EAST** — no upstream gauge declared anywhere in the proposal for this unit (its own
    worked-instantiation table states "no material upstream-mainstem inflow term declared") —
    `upstream_rise_rate` structurally absent (`UPSTREAM_GAUGE_UNDECLARED`), every row.
- **`basin_rain_accum`/`forecast_rain_72h`**: every ERA5 archive under `raw/backtest/rain/` is a
  **single unit-CENTRE point request** (per `fetch_historical.py`), never a true upstream-sub-basin
  polygon aggregate — flagged **AGGREGATE-PROXY-CENTRE-POINT** on every row. `sb_code` per unit is
  resolved via `tools/kg/unit_resolver_draft.py` against the real DWR sub-basin polygons (reported
  below, §8) but this run does **not** re-fetch/spatially-aggregate ERA5 over that polygon (reuse-only
  brief; would need a new pull).
- **`forecast_rain_72h` uses the ERA5 "future" window as a PERFECT-PROGNOSIS PROXY** — the
  identical archived reanalysis, read forward from the evaluation day — explicitly an **UPPER
  BOUND** on what a genuine forecast-driven promoter could achieve, never a forecast-skill claim.
- **`lead_time_h` is a SIMPLIFIED proxy**, not PROP-FLOOD-02's full `T_k` threshold-crossing search
  applied to the shifted series (that would need a declared upstream threshold `theta` this check
  does not source) — reported as `tau_up` when `UPSTREAM_RISE_RATE_EXCEEDS` fires, else `None`.
  **INSTINCT approximation**, same discipline as v1's flagged `T_act` daily-granularity shortcut.
- **Persistence (p=2 raise / q=3 step-down)** applied as a post-processing layer over each
  (unit, c, H, τ) scenario's **chronological per-DAY** raw-tier sequence — the registry declares
  this over an **hourly** stream; this backtest has no hourly readout series, so this is a
  **granularity downgrade from the registered spec**, flagged, not a literal implementation.
- Persistence proof-preserving property (`persisted_is_some_historical_raw`) holds by
  construction: every persisted-day tier is copied from some earlier-or-equal raw-day tier, never
  invented.

## 2. Counts / REFUSED (LR) share / mode split

**1,892 rows total. LR: 28/1,892 (1.5%)** — all in NAN (up slightly from v1's 0.9%/12 rows because
NAN's row count itself tripled via the τ sweep; the underlying LR *dates* are the same 3 days v1
already found — 2024-09-04/07/08, entirely outside the fetched ERA5 window with null N.1 discharge
— reused verbatim, not a new finding).

| หน่วย | FULL | PARTIAL | LR | รวม |
|---|---|---|---|---|
| HATYAI | 84 | 372 | 0 | 456 |
| NAN | 204 | 644 | 28 | 876 |
| CHIANGMAI | 64 | 164 | 0 | 228 |
| AYUTTHAYA_BANGBAN | 164 | 0 | 0 | 164 |
| BANGKOK_EAST | 168 | 0 | 0 | 168 |
| **รวม** | **684** | **1,180** | **28** | **1,892** |

The **v4 floor fix means FULL-mode rows can still carry a promoter** — e.g. AYUTTHAYA_BANGBAN's
164 rows are all FULL by ledger resolution (unchanged from v1), but now also checked against the
promoter floor (`UPSTREAM_RISE_RATE_EXCEEDS` fired once there, on a non-flooded day — see §5).

## 3. Confusion matrix (act-now L3-L5 vs. flooded), scenario c=1.0,H=24, default τ_up per unit,
non-LR rows only — MEASURED-on-backtest

Raw (un-persisted) tier:

| หน่วย | hit (act&flooded) | FA (act&not) | miss (time&flooded) | tn (time&not) |
|---|---|---|---|---|
| HATYAI | 6 | 28 | 4 | 76 |
| NAN | 8 | 20 | 6 | 36 |
| CHIANGMAI | 11 | 11 | 9 | 26 |
| AYUTTHAYA_BANGBAN | 15 | 17 | 0 | 9 |
| BANGKOK_EAST | 10 | 11 | 8 | 13 |

Persisted (p=2/q=3) tier:

| หน่วย | hit | FA | miss | tn |
|---|---|---|---|---|
| HATYAI | 8 | 37 | 2 | 67 |
| NAN | 14 | 24 | 0 | 32 |
| CHIANGMAI | 16 | 12 | 4 | 25 |
| AYUTTHAYA_BANGBAN | 15 | 18 | 0 | 8 |
| BANGKOK_EAST | 15 | 13 | 3 | 11 |

## 4. Lead time ที่ทำได้จริง — v1 vs v2, per event, scenario c=1.0,H=24 — MEASURED-on-backtest

| เหตุการณ์ | v1 first L3+ (lead) | v2 first L3+ (raw, lead) | promoter ที่ carry เป็นตัวแรก | v2 first L3+ (persisted, lead) |
|---|---|---|---|---|
| HATYAI 2553 | 2010-11-01, **−24h** | 2010-11-01, **−24h** (unchanged) | `RAIN_24H_EXCEEDS_DESIGN` + `BASIN_RAIN_ACCUM_EXCEEDS` (both same-day, in-unit) | 2010-11-02, −48h |
| HATYAI 2565 (X.44) | never L3+ | 2022-11-12, **+432h (18 days)** | `UPSTREAM_RISE_RATE_EXCEEDS` (X.44-on-itself, degraded) | 2022-11-13, +408h |
| NAN 2567 (N.1/N.64) | 2024-08-21, **−48h** | 2024-08-02, **+408h (17 days)** | `UPSTREAM_RISE_RATE_EXCEEDS` (N.64, real upstream gauge) | 2024-08-03, +384h |
| CHIANGMAI 2567 (P.1) | 2024-09-24, **0h** | 2024-09-20, **+360h (15 days)** | `UPSTREAM_RISE_RATE_EXCEEDS` (P.1-on-itself, degraded) | 2024-09-21, +336h |
| AYUTTHAYA 2011 | 2011-09-20, +264h | 2011-09-20, **+264h (unchanged)** | none (band tier alone, `FULL`, same as v1) | 2011-09-20, +264h |
| BANGKOK_EAST 2011 | 2011-10-20, +120h | 2011-10-20, **+120h (unchanged)** | none (band tier alone) | 2011-10-20, +120h |
| BANGKOK_EAST 2569 | real data starts after onset | 2026-09-20, **+96h** — but this date is OUTSIDE the real `pumps_2569.csv` window (26–27 ก.ย. only); the row scoring L4/L5 there is `FULL`-mode from `BASIN_RAIN_ACCUM_EXCEEDS`/ERA5 rain, **not** the real pump/canal telemetry — same data-window limitation v1 already flagged | 2026-09-21, +72h (same caveat) |

**พูดตรงๆ — headline number is misleading without the FA context (§3/§5):** on the surface, 3 of the
4 "no real lead time" falsifiers from v1 (Hat Yai 2565, Nan, Chiang Mai) now show **triple-digit-hour
positive lead** with `UPSTREAM_RISE_RATE_EXCEEDS` firing first. But this promoter is also the single
biggest false-alarm source in the whole run (77/97 total promoter firings at c=1,H=24; §5) — the
"first L3+" date being early does **not** mean the signal reliably discriminates; it means the
declared 15% rise-rate threshold is *loose enough* to fire early and often, including on
non-flooded stretches. Ayutthaya and Bangkok East (the two units that already had real lead time in
v1) are **unchanged** by v5 — neither has a working leading promoter feed (Ayutthaya's C.2 rise-rate
fired once, on a FALSE-ALARM day, see §5; Bangkok East has no declared upstream gauge at all).

## 5. Promoter ที่ carry hit — MEASURED-on-backtest, scenario c=1.0,H=24, per-unit default τ

Fire counts split by ground truth (flooded / not_flooded):

| หน่วย | promoter | flooded | not_flooded | อ่านว่าอย่างไร |
|---|---|---|---|---|
| HATYAI | `UPSTREAM_RISE_RATE_EXCEEDS` | 4 | **28** | X.44-on-itself (degraded, expected weak per brief) — **confirmed weak**: 7:1 FA:hit |
| HATYAI | `BASIN_RAIN_ACCUM_EXCEEDS` | 3 | 0 | in-unit rain proxy, no FA in this sample but n too small to trust |
| HATYAI | `RAIN_24H_EXCEEDS_DESIGN` | 2 | 0 | same, in-unit, not leading |
| HATYAI | `FORECAST_RAIN_72H_EXCEEDS` | 1 | 2 | perfect-prognosis proxy, still 2:1 FA:hit here |
| NAN | `UPSTREAM_RISE_RATE_EXCEEDS` | 6 | **20** | N.64 real upstream gauge — still 3.3:1 FA:hit at the declared 15% threshold |
| CHIANGMAI | `UPSTREAM_RISE_RATE_EXCEEDS` | 8 | 10 | best FA:hit ratio of the three (P.1-on-itself, degraded, but closer to even) |
| CHIANGMAI | `BASIN_RAIN_ACCUM_EXCEEDS` | 4 | 0 | in-unit rain |
| CHIANGMAI | `FORECAST_RAIN_72H_EXCEEDS` | 0 | 4 | **fires only on non-flooded days here** — a pure false-alarm source in this sample |
| AYUTTHAYA_BANGBAN | `UPSTREAM_RISE_RATE_EXCEEDS` | 0 | 1 | C.2/GloFAS daily proxy — the one row it fired on was **not flooded**; too sparse (n=1) to conclude anything beyond "no confirmed hit yet" |
| BANGKOK_EAST | `RAIN_24H_EXCEEDS_DESIGN` | 3 | 0 | in-unit, real (pumps_2569.csv rain field) |
| BANGKOK_EAST | `BASIN_RAIN_ACCUM_EXCEEDS` | 5 | 0 | AGGREGATE-PROXY-CENTRE-POINT, in-unit |
| BANGKOK_EAST | `FORECAST_RAIN_72H_EXCEEDS` | 1 | 1 | perfect-prognosis proxy |
| BANGKOK_EAST | `PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD` | 1 | 0 | real pump telemetry |

`DAM_RELEASE_ABOVE_SPILL_THRESHOLD`/`VULNERABLE_UNIT_PROMOTION` — **still not evaluated**, no feed,
unchanged from v1 (OPEN).

## 6. Effect of persistence (p=2/q=3) on FA and lead — reported together per registry's own
demand, MEASURED-on-backtest

**Counterintuitive, honestly reported finding: at DAY granularity, this check's p=2/q=3 defaults
RAISED both hit rate and false-alarm rate simultaneously — they did not trade lead time for FA
reduction the way the registry's hourly-granularity design intends.**

| หน่วย | hit rate raw→persisted | FA rate raw→persisted | lead-time cost (first-L3+ date shift) |
|---|---|---|---|
| HATYAI | 60.0%→80.0% | 26.9%→35.6% | −1 day (2022-11-12→13) |
| NAN | 57.1%→100%* | 35.7%→42.9% | −1 day (2024-08-02→03) |
| CHIANGMAI | 55.0%→80.0% | 29.7%→32.4% | −1 day (2024-09-20→21) |
| AYUTTHAYA_BANGBAN | 62.5%→62.5% | 65.4%→69.2% | 0 (unchanged, no promoter carries a raise here) |
| BANGKOK_EAST | 55.6%→83.3% | 45.8%→54.2% | −1 day (2026-09-20→21) |

\* NAN's 100% persisted hit rate is on a small non-LR flooded-day count (n=14) — not a claim of a
reliable detector, see §5's FA numbers on the same promoter.

**Why**: `p=2` (fast raise) / `q=3` (slow step-down) is asymmetric by design — a tier, once raised,
is held for at least 3 consecutive lower-raw-readouts before it steps back down. In this dataset,
promoter firings are short, sparse spikes (a day or two) surrounded by longer non-firing stretches.
The asymmetric hold **extends** the elevated-tier window past the original spike, sweeping in
*more* subsequent days on both sides of the ground-truth label — both more flooded days (raising
hit rate) and more non-flooded days (raising FA rate). This is the opposite of the registry's
stated intent ("trades lead time for FA rate... explicitly, not silently") **at this backtest's
downgraded daily granularity** — it is not evidence against the hysteresis *construction* itself
(the registry's own Coq proof only claims persistence never fabricates an absent raw tier, which
still holds here; it makes no claim about the net FA effect at any particular granularity/parameter
choice). **Falsifies**: p=2/q=3 as declared defaults, applied at day-granularity with this dataset's
sparse promoter-firing pattern, is not obviously the safer choice over the raw rule — this is a
finding for the founder to weigh, not a silent adoption.

## 7. Sensitivity — S_H unchanged from v1 (arithmetic untouched by v5); promoter-threshold
separability, MEASURED-on-backtest

`S_H`/`T_act` band arithmetic is byte-identical to v1's (`compute_C_H`/`s_band`/`t_act_band` reused
unchanged) — v1 §6's finding stands verbatim: no single `S_H` threshold in (0.3/0.6/0.9/1.2)
separates flooded from non-flooded for HATYAI/NAN/CHIANGMAI; AYUTTHAYA still overlaps heavily.

New for v5 — `upstream_rise_rate` (%) separability at the declared 15% threshold, same three units:

| หน่วย | % rise, flooded days (min–max, n) | % rise, non-flooded days (min–max, n) | แยกได้ไหม |
|---|---|---|---|
| NAN (N.64) | overlaps into the >15% band on 6/14 flooded days | overlaps into the >15% band on 20/56 non-flooded days | **ทับซ้อน** — 15% is not a clean separator |
| CHIANGMAI (P.1 self) | fires on 8/20 flooded days | fires on 10/37 non-flooded days | closest to separable of the three, still overlapping |
| HATYAI (X.44 self) | fires on 4/10 flooded days | fires on 28/104 non-flooded days | **แยกไม่ได้เลย** — confirms the brief's "expected weak" flag |

## 8. Per-unit calibration DRY RUN — "what calibration WOULD choose", NOT adopted

Per the registry's `calibration_procedure`: finite predeclared grid, MAXIMISE hits s.t. a declared
FA ceiling (chosen here: **FA ≤ 20%**), on the `upstream_rise_rate` % threshold, grid
`{0.05,0.10,...,0.50}` (declared here, INSTINCT, this check's own choice):

- **NAN (N.64, real upstream gauge)**: **no grid value tested reaches FA ≤ 20%** — the closest,
  `thr=0.50`, still gives FA=25.6% (hit=2/7=28.6%). Reported honestly: this unit's rise-rate signal
  does not calibrate cleanly against this ceiling with this candidate grid.
- **CHIANGMAI (P.1 self, degraded)**: `thr=0.40` gives the max hits (3/10=30%) subject to
  FA≤20% (FA=9.5%, 2/21) — this WOULD be the chosen threshold if this unit were calibrated today.
- **HATYAI (X.44 self, degraded)**: not run in full (§5/§7 already show HATYAI's rise-rate signal
  is the weakest of the three; a grid dry run here would not change the "expected weak" verdict).

**`calibrated: no ("ยังไม่สอบเทียบที่นี่")` on every row of this run** — no unit is calibrated by this
backtest. Per the registry's falsifier discipline, calibrating NAN/CHIANGMAI now, on data already
seen and already fitted against by this same grid search, would be a **prohibited** re-run against
the same event set — this dry run is reported as a "what-if", never adopted, and requires a
genuinely NEW observed event before any unit here may be actually calibrated.

## 9. sb_code per unit (DWR sub-basin resolution, `tools/kg/unit_resolver_draft.py`)

Resolved read-only against `raw/gis/dwr_subbasin/page_0.geojson`; every unit here still uses its own
`raw/backtest/units.yaml` radius-INSTINCT `A_U` for the S_H/T_act ledger (unchanged from v1) —
`sb_code` is reported for reference/future wiring, **not yet substituted into `A_U`/basin_rain_accum
aggregation** this check (reuse-only brief, see §1).

| หน่วย | centre (lat,lon) | sb_code resolved |
|---|---|---|
| HATYAI | 7.0084, 100.4747 | see `raw/backtest/results_v2.jsonl` `sb_code` field, every HATYAI row |
| NAN | 18.7756, 100.7730 | see `sb_code` field, every NAN row |
| CHIANGMAI | 18.7883, 98.9853 | see `sb_code` field, every CHIANGMAI row |
| AYUTTHAYA_BANGBAN | 14.4744, 100.5013 | see `sb_code` field, every AYUTTHAYA_BANGBAN row |
| BANGKOK_EAST | 13.7734, 100.6813 | see `sb_code` field, every BANGKOK_EAST row |

(`sb_code` is recorded per-row rather than restated here to avoid a second, potentially
stale copy of a resolver result this doc doesn't re-verify at write time — read the JSONL for the
live value; a `null` there means the resolver reported the point outside every archived polygon or
the resolver itself failed, see `tools/kg/unit_resolver_draft.py`'s own `reason` field, not
reproduced in this JSONL row.)

## 10. ข้อจำกัดที่ต้องพูดตรงๆ

1. **All v1 limitations still apply unchanged** (ERA5 rain below real rain, X.44 not reflecting Hat
   Yai's real crisis, qmax as RELAYED-HII-metadata not verified bankfull capacity, T_act daily-
   granularity approximation, BANGKOK_EAST 2569's 2-real-days window, no Chao Phraya 2569 discharge,
   DAM_RELEASE/VULNERABLE_UNIT never tested, canal/pump promoters never tested in PARTIAL mode,
   HATYAI 2553 still GloFAS-only, ground truth mostly RELAYED) — not re-litigated here.
2. **`upstream_rise_rate`'s declared 15% threshold is this check's own INSTINCT choice, not sourced
   from the registry or any hydrological reference** — the large apparent lead-time gains in §4 are
   partly an artifact of a loose threshold, not solely a genuine leading-signal discovery; §5/§7's
   FA numbers are the honest counterweight to §4's headline lead-time table.
3. **τ_up ∈ {0,6,12}h made no visible difference to which day first crossed L3+ for NAN** — at this
   backtest's DAY-granularity engine, an intra-day shift of ≤12h is invisible to a day-level ground
   truth window; the sweep is reported (per the brief) but does not itself validate any particular
   τ_up value. A real hourly-resolution ground truth series would be needed to actually
   discriminate between τ=0/6/12h.
4. **Persistence ran on daily readouts, not hourly** — a real granularity downgrade from the
   registry's own declared spec (§1/§6); the FA-increase finding in §6 is scoped to this
   granularity and these p/q defaults, not a general claim about hysteresis.
5. **`basin_rain_accum`/`forecast_rain_72h` are unit-CENTRE-point proxies, not real
   upstream-sub-basin polygon aggregates** — flagged AGGREGATE-PROXY-CENTRE-POINT on every row;
   the DWR sub-basin polygons exist and are resolved (§9) but not yet used to re-fetch/aggregate
   ERA5 grid points this check.
6. **`forecast_rain_72h` is a perfect-prognosis proxy (the same archived reanalysis, read forward)
   — an explicit UPPER BOUND on real forecast skill**, not a forecast-skill measurement; a real
   ensemble forecast product would very likely perform worse than this proxy, not better.
7. **`lead_time_h` does not implement PROP-FLOOD-02's full `T_k` construction** — it reports the
   declared `tau_up` when the rise-rate promoter fires, nothing more sophisticated; a genuine
   projected time-to-threshold crossing (with the upstream gauge's own declared warning line as
   `theta`) is not implemented this check (no declared upstream `theta` sourced for any of the four
   units).
8. **AYUTTHAYA's C.2 upstream series is the SAME GloFAS proxy already used as its `Q_in,up` term**
   — `upstream_rise_rate` and the existing `F_H(U)` upstream-inflow term are therefore NOT
   independent signals for this unit; a promoter firing there is largely redundant with what the
   FULL-mode ledger already captures, unlike Nan/Chiang Mai/Hat Yai where the leading term is a
   genuinely separate reading from the in-unit ledger.
9. **Calibration grid (§8) is this check's own declared choice (FA≤20%, step 0.05), not the
   registry's** — a different declared ceiling or grid step could produce a different "what
   calibration would choose" answer; this is reported as one honest example, not the only possible
   dry run.

## 11. คำตัดสิน (verdict) ต่อหน่วยและภาพรวม — **does v5 give lead time ≥6h on any real event?**

- **NAN**: **Yes, on paper** — `UPSTREAM_RISE_RATE_EXCEEDS` (real N.64 upstream gauge) gives
  +408h raw / +384h persisted lead on the 2024-08 event, a genuine reversal from v1's −48h. **But**
  the same promoter fires on 20/56 non-flooded days at this threshold (3.3:1 FA:hit) and no grid
  value in the declared candidate set reaches FA≤20% (§8) — the lead time is real in this one
  event's date arithmetic, but the signal is not yet a trustworthy discriminator. **Verdict:
  falsifier partially answered (lead time achieved), new falsifier opened (FA at this threshold).**
- **CHIANGMAI**: **Yes, weakly** — same promoter (degraded self-gauge) gives +360h/+336h lead, best
  FA:hit ratio of the three (10:8), and the only unit where a calibration dry run reaches FA≤20%
  with hits retained (§8, thr=0.40). Still self-referential (no real upstream gauge exists per this
  repo's own knowledge base) — a real P.67/P.75 confirmation would be needed before trusting this
  as genuinely leading rather than "same-unit signal arriving slightly earlier than rain/canal."
- **HATYAI**: **Technically yes (+432h), practically no** — confirms the founder's own instructions'
  prediction ("expected weak"): 28 false alarms to 4 hits at the declared threshold, the weakest
  separability of any unit tested (§7). The lead-time number in §4 is real but not usable as a
  warning signal without a much higher, and probably unit-specific, threshold.
- **AYUTTHAYA_BANGBAN**: **No change from v1** — still +264h lead, but that lead comes entirely
  from the SAME upstream-inflow ledger term as before (§10.8), not a new independent signal;
  `upstream_rise_rate` fired once, on a false alarm. The unresolved v1 falsifier (51.6% FA, `S_H`
  overlap) is **unchanged and still open**.
- **BANGKOK_EAST**: **No leading signal available** — no upstream gauge declared for this unit in
  the proposal itself; v5 adds nothing here beyond the existing in-unit promoters (rain/canal/pump,
  all confirmed real telemetry, unchanged from v1). The 2569 real-data-window limitation (starts
  after the 24 Sep onset) is unchanged.
- **ภาพรวม**: v5's leading promoters **do** produce positive lead-time numbers on 3 of 4 units that
  previously had none or negative lead (Hat Yai, Nan, Chiang Mai) — this is the mechanism the v5
  bump was built for, and it works in the narrow sense of moving the first-L3+ date earlier than
  onset. **It does not yet produce a trustworthy warning** at the thresholds declared by this check:
  every leading promoter's false-alarm rate is high enough (§5/§7) that none of the three units
  would be safe to present as "early warning working" without genuine per-unit calibration against
  NEW ground truth (§8), which this run explicitly does not perform. Persistence (§6), rather than
  fixing the FA problem, made it slightly worse at this backtest's daily granularity — a real,
  reportable falsifier of the p=2/q=3 defaults at this granularity, not of the hysteresis
  construction itself. **Next falsifier**: (a) confirm or rule out P.67/P.75 (Chiang Mai) and
  X.90/X.173-as-upstream (Hat Yai) as real gauges rather than continuing to use degraded self-
  reference; (b) source a declared, non-arbitrary rise-rate threshold per unit (hydrological, not
  this check's flat 15%); (c) run persistence at real hourly granularity once an hourly ground-truth
  series exists; (d) a genuinely new NAN/CHIANGMAI event before any calibration in §8 may be
  adopted.
