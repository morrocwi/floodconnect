"""v0.1.2 nationwide one-path acceptance tests (founder ruling 2026-10-04, "ทำเลย
v0.1.2 ทั้งประเทศ"). Uses a real, trimmed excerpt (verbatim, not edited) of one live
GET of api-v3.thaiwater.net's nationwide waterlevel feed --
tests/fixtures/thaiwater_waterlevel_v012_sample.json, see its own .sidecar.json for
provenance. No simulated/fabricated data; the real-data-only-in-tests rule (AGENTS.md)
is honoured by capturing real records, never inventing one.
"""
import json
from pathlib import Path

import collect
import floodconnect_model as fm
import readout
import store

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = "2026-10-04"


def _fake_one_get(body: bytes):
    def _fn(url, headers, timeout=None):
        return 200, body
    return _fn


def _collected_conn(monkeypatch, tmp_path):
    body = (FIXTURES / "thaiwater_waterlevel_v012_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_thaiwater_waterlevel(conn)
    assert res.ok is True
    return conn


def test_overbank_row_stores_overbank_status_and_classifies_red(monkeypatch, tmp_path):
    """C.67: a real `diff_wl_bank_text` == "ล้นตลิ่ง (ม.)" row -- the agency's own,
    directly-observed overflow word. Must store status="OVERBANK" and classify RED."""
    conn = _collected_conn(monkeypatch, tmp_path)
    row = conn.execute(
        "SELECT * FROM observations WHERE station_code='C.67'").fetchone()
    assert row["status"] == "OVERBANK"
    assert fm.classify(row["status"]) == "RED"


def test_no_threshold_only_station_is_unknown_never_green(monkeypatch, tmp_path):
    """M.104: no `situation_level` published at all for this record -- regate finding
    #2's acceptance test. Must store NO_THRESHOLD and classify UNKNOWN, never GREEN."""
    conn = _collected_conn(monkeypatch, tmp_path)
    row = conn.execute(
        "SELECT * FROM observations WHERE station_code='M.104'").fetchone()
    assert row["status"] == "NO_THRESHOLD"
    assert fm.classify(row["status"]) == "UNKNOWN"
    assert fm.classify(row["status"]) != "GREEN"


def test_normal_situation_level_classifies_green(monkeypatch, tmp_path):
    """CHI011: a real situation_level=3 row (below bank) -- the verbatim agency code
    stores as thaiwater_situation_3 and classifies GREEN."""
    conn = _collected_conn(monkeypatch, tmp_path)
    row = conn.execute(
        "SELECT * FROM observations WHERE station_code='CHI011'").fetchone()
    assert row["status"] == "thaiwater_situation_3"
    assert fm.classify(row["status"]) == "GREEN"


def test_build_readout_nationwide_station_resolution_decides_red(monkeypatch, tmp_path):
    """A point at C.67's own coordinate (14.36851, 100.414391) -- within the 10 km
    station radius of a fresh OVERBANK row -- must decide at "station" resolution."""
    conn = _collected_conn(monkeypatch, tmp_path)
    full = readout.build_readout(conn, 14.36851, 100.414391, 3.0, as_of_date=AS_OF)
    f4 = full["factors"]["4_การระบาย"]
    wl_rows = [r for r in f4["measured"] if r.get("source") == "thaiwater_waterlevel"]
    assert wl_rows, "expected at least one thaiwater_waterlevel row in factor 4"
    decided = [r for r in wl_rows if r.get("used_for_decision")]
    assert decided, f"expected a deciding row, got {wl_rows}"
    assert decided[0]["resolution"] == "station"
    assert decided[0]["status"] == "OVERBANK"
    assert fm.classify(decided[0]["status"]) == "RED"


def test_build_readout_no_station_nearby_is_unknown(monkeypatch, tmp_path):
    """A point far (Phuket, ~7.88,98.39) from every fixture station (all in the
    central/northeast basins) within even the 50 km basin radius -- no nationwide row
    decides, current_local_state stays UNKNOWN (never GREEN by default)."""
    conn = _collected_conn(monkeypatch, tmp_path)
    full = readout.build_readout(conn, 7.88, 98.39, 3.0, as_of_date=AS_OF)
    f4 = full["factors"]["4_การระบาย"]
    wl_rows = [r for r in f4["measured"] if r.get("source") == "thaiwater_waterlevel"]
    assert not any(r.get("used_for_decision") for r in wl_rows)
