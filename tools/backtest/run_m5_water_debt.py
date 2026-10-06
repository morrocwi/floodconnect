#!/usr/bin/env python3
"""run_m5_water_debt.py -- M5 water-debt backtest, run as an EXPERIMENT.

    ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo (PROP-FLOOD-03, PR #60 pending;
    PROP-FLOOD-10 Delta10.3 cells, unregistered). Every result below is tagged
    PROPOSAL -- not yet in Toledo and is evidence toward registration, never a
    user-facing answer (founder ruling 2026-10-05).

Reuses, AS-IS, with no new equation and no invented threshold:
  - water_balance.py's `step()` (Toledo PROP-FLOOD-03) for the per-tick water-debt
    ledger (S_b storage increment), including its own REFUSED reason codes.
  - tools/backtest/score_forward_forecast.py's `ledger_cell()` (the PROP-FLOOD-10
    Delta10.3 5-cell scoring: HIT / MISS / FALSE_ALARM / CORRECT_NEG / UNRESOLVED)
    and its `N_MIN` FEW_EVENTS floor (10, per forward_forecast_bkk_10day.py).

Inputs (all real, recorded; nothing simulated):
  - docs/experiments/M5_event_set.yaml -- 6 independent flood events + 8 control
    (quiet) periods, real GloFAS/ERA5-derived daily readings ported from this repo's
    own (gitignored) raw/backtest/events.yaml, plus ledger merge notes. (NASA-POWER was
    named here in an earlier draft; corrected -- it was a cross-check only in prior
    work, no NASA-POWER value is in this file.)
  - docs/experiments/M5_national_units.yaml -- declared A/c/C_pump/S0/tau for the 5
    national PROP-FLOOD-06 backtest units, copied from sources/backtest_units.yaml.
  - site/inputs/areas/{sammakorn,ram53}.balance.yaml -- already-tracked declared
    PROP-FLOOD-03 inputs for the 2 Bangkok-area village nodes (unchanged, read-only).

c_U is the ONE exception to "OPEN means refuse" in this run: it is a declared BOUND
[0.5, 1.0], so it is propagated as an enclosure (step() run at both ends, keep
[min(S_next), max(S_next)]) rather than refused -- per the experiment's frozen scope
(founder ruling 2026-10-05). Every other OPEN/missing field causes a REFUSED outcome,
via water_balance.py's own reason codes, never a silent default.

**Headline**: EVERY row REFUSES MISSING_INPUT because `gate_flag` is ALWAYS passed as
None below (never declared for any unit in this run) -- this is just as universal a
blocker as S0 (both 219/219 rows), not a secondary one. Q_out_meas is additionally
missing on 138/219 rows. The 2 village rows also lack A/c/C_pump/P. See
docs/experiments/M5_WATER_DEBT_BACKTEST.md section 1 for the full finding.

This runner does NOT chain days: every unit-day is scored independently with
S_prev=None (tick 0 of its own, isolated chain) -- it never threads S_next from day k
into S_prev for day k+1, even within the same multi-day event window. A real
water-debt ledger needs that chaining; this experiment does not attempt it (see the
report's section 2 and 5).

Output: docs/experiments/M5_results.jsonl, one row per (unit_or_node, event_or_control,
date) -- deterministic, append-free (regenerated fresh each run, sorted key order,
so a re-run reproduces it byte-for-byte). Every row carries "toledo_status":
"PROPOSAL -- not yet in Toledo".

Usage:
    python3 tools/backtest/run_m5_water_debt.py [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKTEST_DIR = REPO_ROOT / "tools" / "backtest"
if str(BACKTEST_DIR) not in sys.path:
    sys.path.insert(0, str(BACKTEST_DIR))

import water_balance as wb  # noqa: E402 -- Toledo PROP-FLOOD-03, reused as-is
from score_forward_forecast import ledger_cell, N_MIN  # noqa: E402 -- PROP-FLOOD-10 Delta10.3, reused as-is

EVENT_SET_PATH = REPO_ROOT / "docs" / "experiments" / "M5_event_set.yaml"
NATIONAL_UNITS_PATH = REPO_ROOT / "docs" / "experiments" / "M5_national_units.yaml"
BALANCE_DIR = REPO_ROOT / "site" / "inputs" / "areas"
DEFAULT_OUT_PATH = REPO_ROOT / "docs" / "experiments" / "M5_results.jsonl"

TOLEDO_STATUS = "PROPOSAL -- not yet in Toledo"

NATIONAL_NODE_IDS = {"HATYAI", "NAN", "CHIANGMAI", "AYUTTHAYA_BANGBAN", "BANGKOK_EAST"}
BALANCE_NODE_IDS = {"sammakorn", "ram53"}  # site/inputs/areas/bangkok_east.balance.yaml
# also exists but is a DIFFERENT purpose/granularity than the national BANGKOK_EAST unit
# (see M5_national_units.yaml header) -- not reused here, to avoid conflating the two.


def _cfg_value(cfg: dict, key: str):
    field_cfg = cfg.get(key)
    if not isinstance(field_cfg, dict):
        return None
    return field_cfg.get("value")


def load_balance_yaml(node_id: str) -> dict:
    """Same read-only convention as site/build_data.py's own `load_balance_yaml` --
    duplicated here (not imported) so this experiment never imports site/build_data.py
    (which touches the live answer path / DB on import) and never risks mutating it."""
    path = BALANCE_DIR / f"{node_id}.balance.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_national_units() -> dict:
    doc = yaml.safe_load(NATIONAL_UNITS_PATH.read_text(encoding="utf-8"))
    tau_s = doc["tau_s"]
    out = {}
    for u in doc["units"]:
        out[u["node_id"]] = {
            "A_km2": u["A_km2"]["value"],
            "c_low": u["c"]["low"],
            "c_high": u["c"]["high"],
            "C_pump_m3s": u["C_pump_m3s"]["value"],
            "S0_m3": u["S0_m3"]["value"],
            "tau_s": tau_s,
        }
    return out


def step_once(node_id: str, tick_time: str, A, c, tau, C_pump, S0, P, Q_out_meas,
              Q_in_edges=None) -> wb.StepResult:
    inp = wb.WaterBalanceInputs(
        node_id=node_id, tick_index=0, tick_time=tick_time,
        S0=S0, A=A, c=c, tau=tau, C_pump=C_pump,
        P=P, P_observed_at=(tick_time if P is not None else None),
        gate_flag=None, gate_flag_observed_at=None,
        Q_out_meas=Q_out_meas, Q_out_observed_at=(tick_time if Q_out_meas is not None else None),
        inflow_edges=Q_in_edges or [], declared_edges=set(e.edge_id for e in (Q_in_edges or [])),
    )
    return wb.step(inp)


def score_day(node_id: str, day: dict, A_m2, c_low, c_high, C_pump, S0, tau_s,
              A_basis: str = "") -> dict:
    """Run PROP-FLOOD-03 for one unit-day, c propagated as an enclosure over
    [c_low, c_high], then map the result through PROP-FLOOD-10's Delta10.3 ledger_cell.
    `rain_mm_24h` -> P in metres (depth over the tick) when present; `Q_o_now_m3s` is
    used as Q_out_meas ONLY when the source itself flags it credible
    (`Q_o_now_credible: true`) -- an incredible GloFAS-cell reading is treated the same
    as this repo's own existing convention (units.yaml's own caveats): not used at
    face value, left absent rather than silently trusted."""
    date = day["date"]
    tick_time = f"{date}T00:00:00+00:00"
    P = None
    if day.get("rain_mm_24h") is not None:
        P = Fraction(str(day["rain_mm_24h"])) / Fraction(1000)  # mm -> m
    Q_out_meas = None
    if day.get("Q_o_now_credible") and day.get("Q_o_now_m3s") is not None:
        Q_out_meas = Fraction(str(day["Q_o_now_m3s"]))

    c_vals = sorted({c_low, c_high}) if (c_low is not None and c_high is not None) else [None]
    results = []
    for c in c_vals:
        res = step_once(
            node_id=node_id, tick_time=tick_time,
            A=(Fraction(str(A_m2)) if A_m2 is not None else None),
            c=(Fraction(str(c)) if c is not None else None),
            tau=Fraction(str(tau_s)) if tau_s is not None else None,
            C_pump=(Fraction(str(C_pump)) if C_pump is not None else None),
            S0=(Fraction(str(S0)) if S0 is not None else None),
            P=P, Q_out_meas=Q_out_meas,
        )
        results.append(res)

    refused = any(r.refused for r in results)
    reason_codes = sorted({code for r in results for code in r.reason_codes})
    missing = sorted({m for r in results for m in r.inputs_missing})
    present = sorted({m for r in results for m in r.inputs_present})

    if refused:
        f_state, s_next_enclosure, increment_enclosure = "REFUSED", None, None
    else:
        s_vals = [r.S_next for r in results]
        inc_vals = [r.increment for r in results]
        f_state = "OK"
        s_next_enclosure = [str(min(s_vals)), str(max(s_vals))]
        increment_enclosure = [str(min(inc_vals)), str(max(inc_vals))]

    # "fires" (an act-now signal) would require a declared capacity threshold on
    # S_next this experiment does not invent (no new equation/threshold) -- since
    # every row in this dataset is REFUSED before reaching that question (S0 is
    # universally undeclared), `fires` is structurally None whenever f_state !=
    # "OK", which is every row. If f_state were ever "OK" in a future run with S0
    # declared, `fires` would still need a registered threshold before this
    # runner could respond True/False -- left None (UNRESOLVED) rather than guessed.
    fires = None
    obs = "EVENT" if day.get("flooded_significantly") else "NO_EVENT"
    cell = ledger_cell(f_state, fires, obs)

    return {
        "node_id": node_id,
        "date": date,
        "obs": obs,
        "f_state": f_state,
        "fires": fires,
        "cell": cell,
        "reason_codes": reason_codes,
        "inputs_missing": missing,
        "inputs_present": present,
        "S_next_enclosure_m3": s_next_enclosure,
        "increment_enclosure_m3": increment_enclosure,
        "c_enclosure": c_vals,
        "toledo_status": TOLEDO_STATUS,
        "inputs_provenance": {
            "A_m2": A_m2,
            "A_basis": A_basis or None,
            "C_pump_m3s": C_pump,
            "S0_m3": S0,
            "gate_flag": None,
            "gate_flag_basis": "never declared/wired for any node in this run -- universal MISSING_INPUT",
            "tau_s": tau_s,
            "rain_mm_24h": day.get("rain_mm_24h"),
            "Q_o_now_m3s": day.get("Q_o_now_m3s"),
            "Q_o_now_credible": day.get("Q_o_now_credible"),
            "ground_truth_source": day.get("ground_truth_source"),
            "ground_truth_tag": day.get("ground_truth_tag"),
        },
    }


def score_balance_node(node_id: str, day: dict) -> dict:
    """Score a sammakorn/ram53-style node using ONLY its already-tracked
    site/inputs/areas/<node_id>.balance.yaml declared inputs -- A/c/C_pump/S0 all OPEN
    for both nodes today, so this always REFUSES, same posture as the live site's own
    build_village_water_balance(). tau is OVERRIDDEN to this experiment's own 86400s
    (see M5_national_units.yaml header) -- the .balance.yaml's own 3600s is for the
    live hourly page, a different purpose, not reused here."""
    cfg = load_balance_yaml(node_id)
    A = _cfg_value(cfg, "A")
    c = _cfg_value(cfg, "c")
    C_pump = _cfg_value(cfg, "C_pump")
    S0 = _cfg_value(cfg, "S0")
    return score_day(node_id, day, A_m2=A, c_low=c, c_high=c, C_pump=C_pump, S0=S0, tau_s=86400,
                      A_basis=f"declared directly in site/inputs/areas/{node_id}.balance.yaml (m^2)")


def _score_unit_day(unit: str, day: dict, national: dict) -> dict:
    """Dispatch one unit-day to the national-unit path or the village-balance-yaml
    path, per NATIONAL_NODE_IDS/BALANCE_NODE_IDS. Shared by the event loop and the
    control-period loop so the two never silently diverge."""
    if unit in NATIONAL_NODE_IDS:
        cfg = national[unit]
        A_m2 = cfg["A_km2"] * 1_000_000 if cfg["A_km2"] is not None else None
        return score_day(unit, day, A_m2=A_m2, c_low=cfg["c_low"], c_high=cfg["c_high"],
                          C_pump=cfg["C_pump_m3s"], S0=cfg["S0_m3"], tau_s=cfg["tau_s"],
                          A_basis="A_km2*1e6 from M5_national_units.yaml")
    return score_balance_node(unit, day)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH,
                         help="Output path for the results JSONL (default: "
                              "docs/experiments/M5_results.jsonl). Tests pass a tmp_path "
                              "here so they never write to the tracked file.")
    args = parser.parse_args(argv)
    out_path = args.out

    event_set = yaml.safe_load(EVENT_SET_PATH.read_text(encoding="utf-8"))
    national = load_national_units()

    n_independent = event_set["n_independent_events"]
    few_events = n_independent < N_MIN

    rows = []
    for ev in event_set["independent_events"]:
        for u in ev["units"]:
            unit = u["unit"]
            for day in u["days"]:
                row = _score_unit_day(unit, day, national)
                row["event_id"] = ev["event_id"]
                row["sub_event_label"] = u["sub_event_label"]
                row["kind"] = "event"
                rows.append(row)

    for cp in event_set["control_periods"]:
        unit = cp["unit"]
        for day in cp["days"]:
            row = _score_unit_day(unit, day, national)
            row["event_id"] = cp["control_id"]
            row["sub_event_label"] = cp["control_id"]
            row["kind"] = "control"
            rows.append(row)

    # Also score the two Bangkok-area declared-OPEN nodes against the bangkok_2569
    # event window directly (sammakorn/ram53 have no per-day real rain/Q series of
    # their own in M5_event_set.yaml -- they are scored once, at the event's onset
    # day, using only their own balance.yaml declared inputs, which REFUSE regardless
    # of any day's rain value since A/c/C_pump/S0 are OPEN; this documents their
    # REFUSED status explicitly inside M5's own results rather than only inheriting it
    # by omission).
    onset_day = {"date": "2026-09-25", "flooded_significantly": True,
                 "rain_mm_24h": None, "Q_o_now_m3s": None, "Q_o_now_credible": False,
                 "Q_in_up_m3s": None, "ground_truth_source": "sources/urban_flood_event_ledger.yaml",
                 "ground_truth_tag": "MEASURED"}
    for node_id in sorted(BALANCE_NODE_IDS):
        row = score_balance_node(node_id, onset_day)
        row["event_id"] = "bangkok_2569"
        row["sub_event_label"] = f"{node_id}_own_balance_yaml"
        row["kind"] = "event"
        rows.append(row)

    rows.sort(key=lambda r: (r["event_id"], r["node_id"], r["date"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")

    counts = {}
    for r in rows:
        counts.setdefault(r["node_id"], {}).setdefault(r["cell"], 0)
        counts[r["node_id"]][r["cell"]] += 1

    summary = {
        "toledo_status": TOLEDO_STATUS,
        "n_independent_events": n_independent,
        "n_min": N_MIN,
        "skill_claim": ({"state": "REFUSED", "reason": f"FEW_EVENTS (n_ind={n_independent} < N_min={N_MIN})"}
                        if few_events else {"state": "OPEN"}),
        "rows_written": len(rows),
        "counts_per_unit": counts,
    }
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
