"""Tests for the append-only readout_log write path (site/build_data.py's
write_readout_log/archive_readout) and the history printer (readout_history.py). No
network calls -- everything runs against a small hand-built `data` dict, matching the
real shape site/build_data.py's main() produces."""
import datetime
import sys
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402

import readout_history  # noqa: E402
import store  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def _fake_data():
    return {
        "generated_at_bkk": "2026-09-27T12:30:12+07:00",
        "burden_ledger": {
            "available": True,
            "structures": {
                "ssb10": {
                    "label_th": "ปตร.แสนแสบ-มีนบุรี", "state": "CLOSED", "result": "DETERMINATE",
                    "reason_codes": [], "burdened_side": "B", "value_m": 1.0, "out_m": 1.2,
                    "a_c": "-1/5", "observed_at": "2026-09-27T04:40:00+00:00", "stale": False,
                    "persistence": 29,
                },
            },
        },
        "canal_graph": {
            "available": True,
            "edges": [
                {"edge_id": "e_ssb10_ssb09", "u": "ssb10", "v": "ssb09", "status": "CONTROLLED",
                 "direction": None, "delta_m": None, "locked_node": "ssb10",
                 "design_direction": "u_to_v", "control_structures": ["WL.SSB.10 gate"]},
            ],
        },
        "bma_briefing": {"hero_line_th": "test briefing line"},
        "areas": {
            "sammakorn": {
                "pumps": [
                    {"code": "ST.SPS.02", "pumps_on": 0, "pumps_total": 2, "status_th": "ขัดข้อง"},
                    {"code": "ST.SPS.03", "pumps_on": 2, "pumps_total": 3, "status_th": "ปกติ"},
                ],
                "stations_near": [],
                "rain": {"mm_24h": 10.0, "mm_1h": 0.5, "observed_at": "2026-09-27T04:40:00+00:00",
                         "tier_word": "เบา", "stale": False},
                "tide": {"next_high": [], "datum": "MSL"},
                "forecast": {"available": True, "direction": "steady", "trend_word": "ใกล้เคียงเดิม",
                             "next6h_mm": 0, "next24h_mm": 0},
                "water_balance": {"status": "REFUSED", "reason_codes": ["MISSING_INPUT"],
                                   "S_next": None, "increment": None, "trend": None},
            },
            "ram53": {
                "pumps": [],
                "stations_near": [],
                "rain": None,
                "tide": None,
                "forecast": {"available": False},
                "water_balance": {"status": "REFUSED", "reason_codes": ["UNDECLARED_AREA"]},
            },
        },
    }


def test_write_readout_log_writes_burden_and_pump_rows_per_area(conn):
    data = _fake_data()
    inserted = bd.write_readout_log(conn, data, "2026-09-27T05:30:12+00:00")
    assert inserted > 0

    burden_rows = store.query_readout_log(conn, kind="burden")
    assert len(burden_rows) == 1
    assert burden_rows[0]["key"] == "ssb10"
    assert burden_rows[0]["state"] == "CLOSED"
    assert burden_rows[0]["burdened_side"] == "B"
    assert round(burden_rows[0]["diff_m"], 2) == 0.2

    edge_rows = store.query_readout_log(conn, kind="edge")
    assert len(edge_rows) == 1
    assert edge_rows[0]["key"] == "e_ssb10_ssb09"

    for area in ("sammakorn", "ram53"):
        pump_rows = store.query_readout_log(conn, area=area, kind="pump")
        assert len(pump_rows) == 1, f"expected exactly one pump row for {area}"

    briefing_rows = store.query_readout_log(conn, kind="briefing")
    assert len(briefing_rows) == 1


def test_write_readout_log_idempotent_same_run(conn):
    data = _fake_data()
    first = bd.write_readout_log(conn, data, "2026-09-27T05:30:12+00:00")
    second = bd.write_readout_log(conn, data, "2026-09-27T05:30:12+00:00")
    assert first > 0
    assert second == 0  # same run_at_utc -> every row already logged, nothing new


def test_archive_readout_writes_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "READOUTS_DIR", tmp_path / "readouts")
    data = _fake_data()
    dest = bd.archive_readout(data, "2026-09-27T05:30:12+00:00")
    assert dest is not None
    assert dest.exists()
    assert dest.name == "2026-09-27T053012Z.json"


def test_history_printer_shows_rows(conn):
    data = _fake_data()
    bd.write_readout_log(conn, data, "2026-09-27T05:30:12+00:00")
    now = datetime.datetime(2026, 9, 28, 0, 0, 0, tzinfo=datetime.timezone.utc)
    text = readout_history.build_history_text(conn, days=7, now_utc=now)
    assert "MEASURED" in text
    assert "burden:ssb10" in text
    assert "sammakorn_pumps" in text
    assert "no score" in text.lower() or "no ranking" in text.lower()


def test_history_printer_filters_by_area(conn):
    data = _fake_data()
    bd.write_readout_log(conn, data, "2026-09-27T05:30:12+00:00")
    now = datetime.datetime(2026, 9, 28, 0, 0, 0, tzinfo=datetime.timezone.utc)
    text = readout_history.build_history_text(conn, days=7, area="ram53", now_utc=now)
    assert "ram53" in text
    assert "sammakorn" not in text


def test_history_printer_empty_window(conn):
    text = readout_history.build_history_text(conn, days=7)
    assert "no rows in this window" in text
