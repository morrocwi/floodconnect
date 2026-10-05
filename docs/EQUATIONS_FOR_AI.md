# Equations for AI — compute FloodConnect's model by hand

This page is for any AI that can read numbers out of an official source (a
water-level page, a rain-gauge table, the user's own reading) but **cannot**
run this repository's code — a sandboxed code interpreter with no internet,
or a session with no shell at all that is talking the user through doing the
arithmetic themselves. If you *can* run real Python, prefer `floodconnect
answer` (see `AI.md`, `README.md`) over doing this by hand — the shipped CLI
already includes the freshness gate, the station-level classification rules,
and the dual-state/UNKNOWN discipline that this page only summarizes.

**Toledo-first, stated honestly per object below — never invent an
equation, and never present a proposal as a registered theorem.** Every
object here comes from the `toledo` repository's own registry
(`registry/proposals/flood_readout_trend.json`,
`registry/proposals/flood_water_balance.json`,
`registry/proposals/flood_outlet_coping.json`); re-check their current
status there before citing a number from this page, since a proposal can be
revised or merged after this file was written.

## 1. PROP-FLOOD-01 — Δk, the rise/fall trend (Toledo proposal, placeholder code `weld/M.??.v1`)

**Status:** registered as an **unverified Toledo proposal** (tier `Dr`), not
yet promoted to `CANONICAL.json`. Usable as a proposal-tier readout, never
cited as a settled Toledo theorem.

**Formula:**

```
Δk(t) := h(t) - h(t-k)
```

**Variables:**

| Symbol | Meaning | Unit | Where it comes from |
|---|---|---|---|
| `h(t)` | the water-level reading at tick `t` | metres (m) | an official gauge page (e.g. `thaiwater.net`, a BMA canal-level page) or your own reading at the same station |
| `h(t-k)` | the reading `k` ticks earlier, at the **same station** | m | the same source, an earlier timestamp |
| `k` | a predeclared lag (how far back you look) | ticks (you must state what one tick is, e.g. "1 reading" or "1 hour") | you declare this before computing — do not pick it after seeing the result |
| `ε` (epsilon) | the station's own declared sensor resolution | m | the source's own stated resolution; if the source states none, `ε` is **INSTINCT** (a judgment call), never presented as MEASURED |

**Classification:**

```
Δk(t) >  ε   ->  RISING
Δk(t) < -ε   ->  FALLING
otherwise    ->  FLAT
h(t-k) not sampled, or t<k  ->  NO_READOUT  (a real, distinct outcome — never silently FLAT)
```

**Worked EXAMPLE (real station, illustrative readings — not current):**

Station WL.SSB.08 "ค.แสนแสบ-เสรีไทย 24" has real declared thresholds
`warning=0.35 m`, `critical=0.45 m`, `bank=1.91 m` (source: the station's own
`thaiwater_canal_waterlevel` record). Suppose you read `h(t) = 0.38 m` just
now, and the same station's page shows `h(t-1h) = 0.30 m` one hour ago, with
the source stating a resolution `ε = 0.01 m`.

```
Δ1(t) = 0.38 - 0.30 = 0.08 m
0.08 > 0.01  ->  RISING
```

This is a readout of the difference between two already-observed readings —
**not** a prediction that the water will keep rising at this rate.

## 2. PROP-FLOOD-02 — Tk, time to an official threshold (same PR, same placeholder code, "Toledo proposal, placeholder code")

**Status:** same unverified-proposal status as PROP-FLOOD-01 (shares its
Toledo PR).

**Formula:**

```
Tk := (θ - h(t)) * k / Δk(t)      [ticks]
```

defined **only when** `Δk(t) > ε` (genuinely rising) **and** `h(t) < θ`
(threshold not yet reached). Otherwise:

```
REFUSED, reason UNRESOLVED       if |Δk(t)| <= ε   (can't tell if it's really moving)
REFUSED, reason NOT_APPLICABLE   if Δk(t) < -ε, or h(t) >= θ, or Δk(t) was NO_READOUT
```

**Variables (new ones beyond §1):**

| Symbol | Meaning | Unit | Where it comes from |
|---|---|---|---|
| `θ` (theta) | an official agency threshold (e.g. BMA's `critical` level for that station) | m | the station's own declared `warning`/`critical`/`bank` value — never a number you pick yourself |

**Worked EXAMPLE (continuing §1, same illustrative readings):**

Using `θ = critical = 0.45 m`, `h(t) = 0.38 m`, `k = 1 hour`, `Δ1(t) = 0.08 m`:

```
T1 = (0.45 - 0.38) * 1 / 0.08 = 0.875 hours  (~53 minutes)
```

**Report this as an interval across at least two lags (e.g. k=1h and
k=3h), never as one single point number** — different lags will generally
disagree, and collapsing them hides that disagreement. `REFUSED` is a
non-value, not a number — if you ever reach a `REFUSED` state, say "cannot
estimate time-to-threshold right now" rather than printing `0`, `∞`, or a
blank.

## 3. PROP-FLOOD-03 / 06 / 07 — proposal under review, do not treat as registered

These three objects are **open Toledo pull requests, not merged** as of this
writing — a strictly earlier stage than PROP-FLOOD-01/02's "registered
proposal". Do not compute with them as if they were usable; this section
only orients you to what they will eventually do, so you recognise the
vocabulary ("water debt", "L0–L5", "F1–F6") elsewhere in this repo's docs as
**planned**, not shipped:

- **PROP-FLOOD-03 (water balance / water debt):** `S(k+1) = S(k) + rain_in - outflow`
  for a declared basin, with an explicit `REFUSED` outcome (never a silent
  zero or clamp) whenever a required input is missing, stale, or the result
  would be a bookkeeping-impossible negative storage.
- **PROP-FLOOD-06 (outlet-coping tier L0–L5):** a ratio of forecast inflow to
  the smaller of outlet headroom or pump drainage capacity, banded into a
  5-level tier, with its own `REFUSED` outcome when the unit/tuple isn't
  fully declared.
- **PROP-FLOOD-07 (flow-state classifier F1–F6):** a companion classification
  of flow direction/state built on the same inputs as PROP-FLOOD-03.

**Do not compute a number from these three and present it as a FloodConnect
reading.** If asked about water debt or coping tiers today, say plainly:
"planned; the equation objects live in open Toledo pull requests, not on
Toledo main, and are not in this release's compute path"
(see `system_capabilities.json`'s `water_debt_jev_decision` block and
`ARCHITECTURE.md` §1 for the exact PR numbers).

## 4. Honesty rules that apply to every computation above

- **BOT ≠ ZERO.** `NO_READOUT`, `REFUSED`/`UNRESOLVED`, and `REFUSED`/`NOT_APPLICABLE`
  are distinct, first-class "unresolved" outcomes — never collapse one into
  the number `0`, and never read an unresolved result as "nothing is
  happening". A genuinely flat reading (`FLAT`, `Δk` within `±ε`) is a real
  measured zero-like state; a *missing* input is not the same thing, and
  must be reported as missing, not as flat.
- **Missing input → interval or `UNKNOWN`, never a guess.** If you don't have
  `h(t-k)`, `ε`, or `θ` for a station, say so explicitly rather than
  estimating a plausible-looking value. If you have a *range* for an input
  (e.g. you're not sure of the exact resolution but know it's between two
  values), compute both ends and report the resulting interval.
- **A retained difference, not a forecast.** `Δk` and `Tk` describe what has
  already happened between two real readings, extended linearly under the
  assumption that the same rate holds — they are not a model of future
  rainfall, drainage, or dynamics, and they carry no claim that the rate will
  continue.
- **Never claim "safe".** None of these equations ever produce a safety
  verdict. The strongest honest statement is a classification (`RISING`,
  `FALLING`, `FLAT`, etc.) plus how much time is left under the current
  rate — always paired with the official emergency numbers for anything
  real (see `README.md`'s emergency-numbers table).

## 5. The one-decision procedure, by hand, at coarse zoom

This is a simplified, by-hand version of the repository's own D1–D8 decision
protocol (see `ARCHITECTURE.md` §6), for a single point at coarse
(basin/province) zoom, using only what's registered above:

1. **Locate — KG first.** Get your `kg_anchor` (`llms.txt` STEP 1: `floodconnect
   locate`, or `output/kg_index/index.json` → `province_<code>.json`); pick the
   gauge(s) from that slice's stations/assets sharing its sub-basin/reach; state
   the `kg_anchor` in the answer.
2. **Freshness.** Note each reading's timestamp. If a reading is older than
   the source's own stated update interval, call it **stale**, not fresh —
   a stale reading must never decide the colour/state on its own.
3. **Trend (§1).** Compute `Δk` for at least one lag using two fresh
   readings at the same station. If you don't have two fresh readings,
   stop here and report `NO_READOUT` — do not invent a second reading.
4. **Time-to-threshold (§2), only if §3 gave `RISING`.** Compute `Tk` for
   two lags and report the interval, or `REFUSED` with its reason.
5. **Official context.** Check whether an official agency has already
   declared this station/area WATCH/CRITICAL/OVERBANK, or issued a
   disaster declaration. An official declaration always outranks your own
   §3/§4 computation — report it first and defer to it.
6. **One decision, with confidence.** State one plain classification (e.g.
   "rising, ~53 minutes to the official critical level at the current rate,
   per station WL.SSB.08") plus your confidence (high only if the inputs
   were fresh and single-station; lower if you had to use a neighbouring
   station or a wider basin-level reading). Never collapse this into more
   than one decision, and never upgrade it to an instruction to evacuate —
   that is the official channels' job (see the emergency-numbers table).

See `docs/AI_TIERS.md` for which of the above you're expected to do given
your own capability tier, and `ARCHITECTURE.md` for the full protocol this
section simplifies.

## 6. The indicators dictionary — name every output exactly

Step 6 above says "state one plain classification" — **always name it using one of
the indicators in `docs/INDICATORS.md`**, never an ad-hoc label of your own. The closed
set: `current_local_state`, `forward_hazard`, `rise_rate_dk` (§1 above),
`time_to_threshold_tk` (§2 above), `rain_24h_mm`, `rain_7day_per_model_mm`,
`distance_to_bank_m`, `bank_fill_percent`, `one_decision` (+ `confidence`), `water_debt`
(planned v0.2+, no value).

**The RED/YELLOW/GREEN/UNKNOWN colour vocabulary applies ONLY to
`current_local_state` and `one_decision.level`** (fix, 2026-10-04, review finding #3 —
an earlier draft of this section wrongly claimed every indicator shared it). Every
other indicator has its own closed vocabulary — `forward_hazard` is
`ACTIVE`/`NONE`/`UNKNOWN`, `rise_rate_dk` is `RISING`/`FALLING`/`FLAT`/`NO_READOUT`,
and so on — see that indicator's own entry in `docs/INDICATORS.md` for its real
`levels` and exact JSON path, and `model_spec.json`'s per-indicator `levels`/`json_path`
fields for the same as data. `UNKNOWN` (wherever it is one of the possible values) is
**never treated as safe**.

## 7. FloodConnect is the method — finding the station yourself

Every computation above (`Δk`, `Tk`, `one_decision`) needs a real reading, `h_t`, first.
**FloodConnect never geocodes and holds no place/POI database** — if you only have a
place name, resolving it to lat,lon is your own job (founder ruling 2026-10-04: "ให้การ
หาพิกัด ... เป็นหน้าที่ของเอไอของใครของมันแทน"). Once you have lat,lon, either call the
CLI/MCP tool (it runs this exact method deterministically), or, with no tool access,
follow `docs/NEAREST_STATION_RECIPE.md` to find the nearest real station yourself and
read `h_t`/`θ` off the same official sources this repository's own collector reads.
