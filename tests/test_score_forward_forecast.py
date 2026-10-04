"""Fixture test for tools/backtest/score_forward_forecast.py (PROP-FLOOD-10 Δ10.3 ledger on a
forward-forecast record). Trial code — ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo.

Builds a tiny throwaway observations DB (no real data, no network) and a one-day record, then
checks every ledger cell type, the REFUSED -> UNRESOLVED rule, the not-yet-observable rule,
the A5 flag, and the FEW_EVENTS refusal. Nothing is averaged anywhere.
"""
import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "backtest"))

import store  # noqa: E402
import score_forward_forecast as sff  # noqa: E402
from forward_forecast_bkk_10day import cl, zoom_state, ladder_readout  # noqa: E402

UTC = dt.timezone.utc


def _obs(conn, **kw):
    kw.setdefault("fetched_at_utc", "2026-10-01T00:00:00+00:00")
    kw.setdefault("trust_tier", "official_telemetry")
    store.insert_observation(conn, **kw)


def _pt(theta, rung, state, lo, hi):
    return {"theta": theta, "rung": rung, "state": state, "lo": lo, "hi": hi,
            "fires_strict": state == "ROBUST", "fires_worst_first": hi >= theta}


def _record():
    # day 1 = 2026-09-28 local (window 27 Sep 17:00Z -> 28 Sep 17:00Z); day 2 in the future
    day1 = {
        "day_index": 1, "date_local": "2026-09-28",
        "window_utc": ["2026-09-27T17:00:00+00:00", "2026-09-28T17:00:00+00:00"],
        "level0": {"per_theta": [_pt(35.1, "L1", "POSSIBLE", 3.2, 52.6), _pt(80.0, "L3", "BELOW", 3.2, 52.6)]},
        "level1_1h_sammakorn_cell": {"state": "BELOW", "lo": 1.2, "hi": 5.9, "fires_strict": False,
                                      "fires_worst_first": False},
        "level1_districts": [
            {"district_th": "วังทองหลาง",
             "forecast": {"per_theta": [_pt(35.1, "L1", "POSSIBLE", 3.2, 39.7), _pt(80.0, "L3", "BELOW", 3.2, 39.7)]}},
            {"district_th": "บางรัก", "forecast": {"state": "REFUSED", "reason": "INPUT_ABSENT"}},
        ],
    }
    day2 = dict(day1, day_index=2, date_local="2026-09-29",
                window_utc=["2026-09-28T17:00:00+00:00", "2026-09-29T17:00:00+00:00"])
    return {"issued_at_utc": "2026-09-27T18:10:27+00:00", "days": [day1, day2]}


def _db(tmp_path):
    conn = store.connect(tmp_path / "obs.sqlite")
    # road stations: 3 in วังทองหลาง (all wet within 6 h -> EVENT), 1 in บางรัก (UNRESOLVED)
    for i, (code, t, v) in enumerate([("FL.WTL.01", "2026-09-28T08:00:00+00:00", 25.0),
                                      ("FL.WTL.02", "2026-09-28T09:00:00+00:00", 12.0),
                                      ("FL.WTL.03", "2026-09-28T10:30:00+00:00", 30.0)]):
        _obs(conn, source_id="thaiwater_flood_road", station_code=code, lat=13.77 + i * 0.001, lon=100.61,
             variable="floodroad_value_cm", value=v, observed_at_utc=t, provenance={"district_th": "วังทองหลาง"})
    _obs(conn, source_id="thaiwater_flood_road", station_code="FL.BRK.01", lat=13.72, lon=100.52,
         variable="floodroad_value_cm", value=0.0, observed_at_utc="2026-09-28T08:00:00+00:00",
         provenance={"district_th": "บางรัก"})
    # rain gauges at window end (28 Sep 17:00Z): one near วังทองหลาง roads (41 mm), one near บางรัก (12 mm)
    _obs(conn, source_id="thaiwater_rain_24h", station_code="G1", lat=13.771, lon=100.611,
         variable="rain_24h_mm", value=41.0, observed_at_utc="2026-09-28T17:00:00+00:00")
    _obs(conn, source_id="thaiwater_rain_24h", station_code="G2", lat=13.721, lon=100.521,
         variable="rain_24h_mm", value=12.0, observed_at_utc="2026-09-28T17:00:00+00:00")
    # C.12 stage peak 2.10 m MSL
    _obs(conn, source_id="thaiwater_waterlevel", station_code="C.12", lat=13.788, lon=100.509,
         variable="waterlevel_msl", value=2.10, observed_at_utc="2026-09-28T12:00:00+00:00")
    return conn


def _find(res, **kw):
    out = [c for c in res["cells"] if all(c.get(k) == v for k, v in kw.items())]
    assert len(out) == 1, (kw, out)
    return out[0]


def test_ledger_cell_truth_table():
    assert sff.ledger_cell("ROBUST", True, "EVENT") == "HIT"
    assert sff.ledger_cell("BELOW", False, "EVENT") == "MISS"
    assert sff.ledger_cell("POSSIBLE", True, "NO_EVENT") == "FALSE_ALARM"
    assert sff.ledger_cell("BELOW", False, "NO_EVENT") == "CORRECT_NEG"
    assert sff.ledger_cell("REFUSED", None, "NO_EVENT") == "UNRESOLVED"
    assert sff.ledger_cell("ROBUST", True, "UNRESOLVED") == "UNRESOLVED"


def test_cl_and_single_source_guard():
    assert cl(36, 40, "35.1") == "ROBUST"
    assert cl(3.2, 52.6, "35.1") == "POSSIBLE"
    assert cl(1, 5, "35.1") == "BELOW"
    assert cl("35.1", "35.1", "35.1") == "AT_THRESHOLD"
    one = zoom_state([("m@p", 90)], "80")
    assert one["state"] == "POSSIBLE" and one["raw_ge_theta"] is True and one["spread"] == "UNKNOWN_SINGLE_SOURCE"
    assert zoom_state([("m@p", 1), ("m@p", 2)], "35.1")["state"] == "REFUSED"


def test_a6_zoom_focus_is_inclusive_but_rung_stays_strict():
    lr = ladder_readout([("a@p", "35.1"), ("b@p", "35.1")])
    first = lr["per_theta"][0]
    assert first["state"] == "AT_THRESHOLD" and first["zoom_focus_descend"] is True
    assert lr["rung_strict"] == "L0" and lr["agency_class_hi"].startswith("TMD เหลือง")


def test_score_fixture_all_cells(tmp_path):
    conn = _db(tmp_path)
    now = dt.datetime(2026, 9, 29, 0, 0, tzinfo=UTC)  # day 1 scorable, day 2 not yet
    res = sff.score(_record(), conn, now)
    # L0 city rain axis at 35.1: max gauge 41 -> EVENT; strict (POSSIBLE) -> MISS; worst-first -> HIT
    c = _find(res, date_local="2026-09-28", unit="L0:DWR1002-Bangkok", axis="rain_24h", theta=35.1)
    assert (c["O"], c["cell_strict"], c["cell_worst_first"]) == ("EVENT", "MISS", "HIT")
    # at 80: NO_EVENT, BELOW both ways -> CORRECT_NEG
    c = _find(res, date_local="2026-09-28", unit="L0:DWR1002-Bangkok", axis="rain_24h", theta=80.0)
    assert (c["O"], c["cell_strict"], c["cell_worst_first"]) == ("NO_EVENT", "CORRECT_NEG", "CORRECT_NEG")
    # district with forecast: flood_road cluster of 3 roads -> EVENT
    c = _find(res, date_local="2026-09-28", unit="L1:วังทองหลาง", axis="flood_road", theta=35.1)
    assert (c["O"], c["cell_strict"], c["cell_worst_first"]) == ("EVENT", "MISS", "HIT")
    # district without forecast: REFUSED -> UNRESOLVED, observation still recorded
    c = _find(res, date_local="2026-09-28", unit="L1:บางรัก", axis="rain_24h")
    assert c["F_state"] == "REFUSED" and c["cell_strict"] == "UNRESOLVED" and c["O"] == "NO_EVENT"
    c = _find(res, date_local="2026-09-28", unit="L1:บางรัก", axis="flood_road")
    assert c["O"] == "UNRESOLVED"
    # stage: forecast refused, observation kept (2.10 >= 2.00 -> EVENT)
    c = _find(res, date_local="2026-09-28", unit="boundary:C.12", theta=2.0)
    assert c["O"] == "EVENT" and c["cell_strict"] == "UNRESOLVED" and c["obs_detail"]["value_m"] == 2.10
    # day 2 not yet observable
    c = _find(res, date_local="2026-09-29")
    assert c["reason"] == "NOT_YET_OBSERVABLE" and c["cell_worst_first"] == "UNRESOLVED"
    # skill claim refused, counts are counts
    assert res["skill_claim"]["state"] == "REFUSED" and "FEW_EVENTS" in res["skill_claim"]["reason"]
    assert all(isinstance(v, int) for v in res["counts_not_averages"].values())


def test_a5_flag_on_possible_correct_negative(tmp_path):
    conn = _db(tmp_path)
    rec = _record()
    rec["days"][0]["level1_districts"][0]["forecast"]["per_theta"][0] = _pt(35.1, "L1", "POSSIBLE", 3.2, 60.0)
    res = sff.score(rec, conn, dt.datetime(2026, 9, 29, 0, 0, tzinfo=UTC))
    # วังทองหลาง gauge 41 >= 35.1 -> EVENT, so use theta 80 row of L0 for the A5 flag check instead
    c = _find(res, date_local="2026-09-28", unit="L1:วังทองหลาง", axis="rain_24h", theta=35.1)
    assert c["O"] == "EVENT" and c["undecided_forecast"] is False
    rec["days"][0]["level0"]["per_theta"][1] = _pt(80.0, "L3", "POSSIBLE", 3.2, 85.0)
    res = sff.score(rec, conn, dt.datetime(2026, 9, 29, 0, 0, tzinfo=UTC))
    c = _find(res, date_local="2026-09-28", unit="L0:DWR1002-Bangkok", axis="rain_24h", theta=80.0)
    assert c["cell_strict"] == "CORRECT_NEG" and c["undecided_forecast"] is True
    assert c["cell_worst_first"] == "FALSE_ALARM"
