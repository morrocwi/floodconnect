# EVIDENCE.md — what has actually been measured, including where it fails

This page exists so any AI or human can check our honesty claim rather than take our
word for it. **Negatives are listed first, on purpose.** Nothing here is validated,
accurate, or proven in any universal sense — each row names its own proxies, sample
size, and limits, and the right way to read every row is "this backtest, run once,
on this data, found this" — never "FloodConnect is good at X". This project checks a
claim against the concrete data in front of it, never a person's or institution's
say-so — so this page never asks a reader to "trust us" or to seek outside
validation; it points at the exact files a reader can open and recompute from.

**Headline, stated plainly: forecast skill for flood depth or water level at
Sammakorn is NOT yet demonstrated.** Only one real flood event has been studied, and
neither Sammakorn station (`WL.SMK.01`, `WL.BMA.02`) had any archived reading before
roughly 61 hours after that event's onset — so there is no pre-event 24-hour window to
even attempt a hindcast against, for Sammakorn specifically. The numbers below are
real backtests on the data that *is* available (other stations, other provinces,
rain-forecast skill) — they are evidence about the method, not a report card on
Sammakorn.

Every number below is tagged `MEASURED` (computed directly from the source file named
in its row, re-checked against that file during this write) unless stated otherwise.
None of it was re-run for this page — these are the existing backtests' own already-
computed results, read and re-verified line-by-line against their source files before
being copied here.

## 1. Rain-forecast skill, one real Sammakorn event (26–27 Sep 2026)

Source: `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §2.1.

| Lead time | Forecast model's own value (mm/day) | Actual rain (currentbest, mm/day) | Ratio actual/forecast |
|---|---|---|---|
| T−6 | 5.8 | 117.4 | ≈20× |
| T−2 | 52.4 | 117.4 | ≈2.2× |
| T0 (currentbest, backward-looking re-estimate) | 117.4 | 117.4 | 1× (not a forecast — this is the model's own after-the-fact re-analysis) |

**No forecast horizon in this event predicted anything close to the actual rain.**
Underforecast ranged 2.2× (two days ahead) to roughly 20× (six days ahead), with no
clean monotonic climb toward the true value as the event approached. This is one
event, one location; it is not a general verdict on any model.

## 2. Flood-warning skill at the BMA 80mm design-capacity threshold

Source: `docs/experiments/2026-09-27-zoom-forecast-real-backtest.md` §2/§3 (12 known-truth cells
for the forecast rows below; a separate 30-district nowcast table for the row that is not a
forecast — see the note under it).

**Forecast rows (Level 0 — a forecast model's own advance value, 12 known-truth cells):**

| Threshold | HIT | MISS | False alarm | Correct negative | Note |
|---|---|---|---|---|---|
| 35.1 mm (watch level, best-case/worst-first reading) | 5 | 7 | not measurable (no confirmed dry day in this sample) | not measurable | hits are scattered, not a continuous climb |
| **80 mm (BMA design capacity, strict single-source rule)** | **0** | **12** | not measurable | not measurable | no forecast horizon ever exceeded 58.1 mm while actual rain on flooded days ran 102–186 mm |

**At the threshold that matters for BMA's own design capacity, this rain-forecast
signal alone caught zero of twelve known flooded cells under a strict rule.** This
is exactly the gap the planned v0.2 water-debt model is meant to address (not yet
built — see `system_capabilities.json`'s `water_debt_jev_decision` entry).

**Level 1 district nowcast (measured rain, NOT a forecast — same source §0 item 4), 30 districts:**

| Threshold | HIT | MISS | False alarm | Correct negative | Note |
|---|---|---|---|---|---|
| 80 mm, worst-first/any-source reading, measured (not forecast) rain across 30 districts (12 flooded / 18 not) | 12 | 0 | **18** | 0 | nearly the whole city's *measured* rain reads over design capacity on this reading rule — roads did not all flood, so this rule over-warns as a nowcast; it says nothing about forecast skill |

## 3. PROP-FLOOD-06 (outlet-coping tier) backtest v2 — nationwide proposal, not Sammakorn

Source: `docs/BACKTEST_PROP_FLOOD_06_v2.md` (1,892 rows across 5 units: HATYAI, NAN,
CHIANGMAI, AYUTTHAYA_BANGBAN, BANGKOK_EAST — **Sammakorn is not in this sample**).

| Leading promoter | Unit | Hits | False alarms | False-alarm : hit ratio |
|---|---|---|---|---|
| `UPSTREAM_RISE_RATE_EXCEEDS` | HATYAI (self-as-upstream, flagged weak by design) | 4 | 28 | 7:1 |
| `UPSTREAM_RISE_RATE_EXCEEDS` | NAN (real upstream gauge N.64) | 6 | 20 | 3.3:1 |
| `FORECAST_RAIN_72H_EXCEEDS` | CHIANGMAI | 0 | 4 | fires only on non-flooded days in this sample — a pure false-alarm source here |
| `BASIN_RAIN_ACCUM_EXCEEDS` | CHIANGMAI (in-unit rain proxy) | 4 | 0 | the one promoter in this sample with zero false alarms; also 3/0 at HATYAI and 5/0 at BANGKOK_EAST, each flagged small-n / proxy-centre-point caveats in the source — not yet enough to trust as a standalone trigger either |

**Most tested leading promoters have a false-alarm rate too high to use as a
standalone warning trigger**, even on the one upstream gauge judged real (NAN);
`BASIN_RAIN_ACCUM_EXCEEDS` is the one exception in this sample (zero false alarms at
3 of 5 units) but each occurrence is flagged small-sample or proxy-centre-point in
the source, so it is not yet trusted as a standalone trigger either. This is the
proposal-stage equation `PROP-FLOOD-06` being red-teamed against real data — it is
not yet a Toledo-registered theorem, and this result is part of why.

## 4. Token budget — measured with real tiktoken, not estimated

Source: `tests/test_token_budget.py` (run as part of this project's own test suite).

| Budget name | Ceiling (cl100k tokens) | What it covers |
|---|---|---|
| `TOKEN_BUDGET` | 5,000 | repo-wide baseline ceiling |
| `FIXC_TOKEN_BUDGET` | 4,700 | a tightened margin below the 5,000 baseline |
| `MCP_TOKEN_BUDGET` | 9,500 | `AI.md` + `skills/floodconnect/SKILL.md` + one real refreshed `floodconnect_answer` call, both MVP areas — measured at 500 tokens of margin below the 10,000 ceiling this project's founder set |

The **100,000-token "L3 deep" level named elsewhere in this project's plans has no
test, no code path, and no measured number as of this release — it is `OPEN`**; do
not cite a figure for it (see `system_capabilities.json`'s `token_levels.L3_deep`).

## 5. Adversarial / red-team evidence kept deliberately open

PRs **#34** (DSVA v0.7, 12 failed/453 passed/1 skipped), **#38** (v0.8, 5
failed/482 passed/1 skipped), **#42** (v0.9, 6 failed/493 passed/1 skipped), and
**#46** (v0.10, 7 failed/507 passed/1 skipped) are test-only adversarial pull
requests against the DSVA executable decision model. **They are left open on
purpose, as a permanent audit trail of counterexamples found and then fixed in a
later version — closing or merging them would erase that trail.** Read a PR's diff
directly if you want to see the counterexample it preserves; do not read "open" as
"broken" or "unfinished work someone forgot about."

## 6. What this page does not cover

- It does not cover `kb.py answer`'s live-observation path (`state` block) at all —
  that path reports what a sensor/report said, not a prediction, so backtest metrics
  (HIT/MISS/false-alarm) don't apply to it the same way. See `AI.md`'s dual-state rule.
- It does not include a Sammakorn-specific hindcast table, because the data to build
  one honestly does not exist yet (§0 above). A later release (v0.2+) that does build
  one must keep continuous-value metrics (MAE/RMSE by lead time) and classification
  metrics (HIT/MISS/FA/CN) in **separate tables**, never combined into one number, and
  must allow the honest outcome `REFUSED FEW_EVENTS` if there still isn't enough data.
- It never asks you to seek outside/peer validation of any of this — recompute it from
  the named source file yourself if you want a second opinion.

## How to verify any number on this page yourself

```bash
git clone <this-repo-url> floodconnect && cd floodconnect
cat docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md   # §1 and §2
cat docs/experiments/2026-09-27-zoom-forecast-real-backtest.md    # §2 and §3
cat docs/BACKTEST_PROP_FLOOD_06_v2.md                              # §2 and §5/§7
python3 -m pytest tests/test_token_budget.py -q -v
gh pr view 34; gh pr view 38; gh pr view 42; gh pr view 46         # confirm still OPEN
```
