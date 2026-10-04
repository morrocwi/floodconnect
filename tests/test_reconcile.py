"""Tests for tools/reconcile.py (build 4, 2026-09-27 -- founder rule, verbatim:
"ระวังข้อมูลขัดแย้งด้วย"). Cross-source station reconciliation between `bma_watermap` and
`thaiwater_canal_waterlevel`, both `canal_water_level_m`, joined by the identical
'WL.xxx.NN' station_code scheme. Never touches the real sqlite store, never the network.
"""
from pathlib import Path

import store
from tools import reconcile


def _conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def _insert(conn, source_id, station_code, value, observed_at):
    store.insert_observation(
        conn, source_id=source_id, station_code=station_code, station_name=None,
        lat=None, lon=None, variable="canal_water_level_m", value=value, unit="m",
        observed_at_utc=observed_at, fetched_at_utc=observed_at,
        trust_tier="official_telemetry")


def test_agree_station_writes_no_contradiction(tmp_path):
    conn = _conn(tmp_path)
    _insert(conn, "bma_watermap", "WL.SSB.07", 0.40, "2026-09-27T10:00:00+00:00")
    _insert(conn, "thaiwater_canal_waterlevel", "WL.SSB.07", 0.41, "2026-09-27T10:00:00+00:00")
    result = reconcile.reconcile_canal_water_level(conn, ["WL.SSB.07"])
    assert result["stations"]["WL.SSB.07"]["status"] == reconcile.STATUS_AGREE
    assert result["summary"] == {"agree": 1, "disagree": 0, "one_sided": 0, "no_data": 0}
    contradictions = conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
    assert contradictions == 0


def test_disagree_station_by_value_writes_contradiction(tmp_path):
    """The fixture disagreement: same timestamp, values 0.40 vs 0.60 (delta 0.20m, well
    over the 0.05m threshold) -- must be flagged DISAGREE and write exactly one
    contradiction row, with BOTH readings kept intact in observations (never merged)."""
    conn = _conn(tmp_path)
    _insert(conn, "bma_watermap", "WL.PWT.04", 0.40, "2026-09-27T10:00:00+00:00")
    _insert(conn, "thaiwater_canal_waterlevel", "WL.PWT.04", 0.60, "2026-09-27T10:00:00+00:00")
    result = reconcile.reconcile_canal_water_level(conn, ["WL.PWT.04"])
    row = result["stations"]["WL.PWT.04"]
    assert row["status"] == reconcile.STATUS_DISAGREE
    assert abs(row["delta_m"] - 0.20) < 1e-9
    assert result["summary"]["disagree"] == 1
    contradictions = conn.execute(
        "SELECT topic, source_a, value_a, source_b, value_b FROM contradictions").fetchall()
    assert len(contradictions) == 1
    topic, source_a, value_a, source_b, value_b = contradictions[0]
    assert topic == "canal_water_level_m:WL.PWT.04"
    assert source_a == "bma_watermap" and source_b == "thaiwater_canal_waterlevel"
    # both readings preserved verbatim in observations, neither overwritten/merged
    stored = conn.execute(
        "SELECT source_id, value FROM observations WHERE station_code='WL.PWT.04' "
        "ORDER BY source_id").fetchall()
    assert dict(tuple(r) for r in stored) == {
        "bma_watermap": 0.40, "thaiwater_canal_waterlevel": 0.60}


def test_disagree_station_by_time_gap_writes_contradiction(tmp_path):
    """Same value, but timestamps > 60 minutes apart -- still DISAGREE (a stale-vs-fresh
    mismatch is itself a disagreement worth flagging, per the founder's own rule)."""
    conn = _conn(tmp_path)
    _insert(conn, "bma_watermap", "WL.SSB.09", 0.94, "2026-09-27T10:00:00+00:00")
    _insert(conn, "thaiwater_canal_waterlevel", "WL.SSB.09", 0.94, "2026-09-27T08:30:00+00:00")
    result = reconcile.reconcile_canal_water_level(conn, ["WL.SSB.09"])
    assert result["stations"]["WL.SSB.09"]["status"] == reconcile.STATUS_DISAGREE
    assert result["stations"]["WL.SSB.09"]["minutes_apart"] == 90.0


def test_one_sided_and_no_data_stations_never_write_a_contradiction(tmp_path):
    conn = _conn(tmp_path)
    _insert(conn, "bma_watermap", "WL.ONLY.A", 0.5, "2026-09-27T10:00:00+00:00")
    result = reconcile.reconcile_canal_water_level(conn, ["WL.ONLY.A", "WL.NEITHER"])
    assert result["stations"]["WL.ONLY.A"]["status"] == reconcile.STATUS_ONE_SIDED
    assert result["stations"]["WL.NEITHER"]["status"] == reconcile.STATUS_NO_DATA
    assert result["summary"] == {"agree": 0, "disagree": 0, "one_sided": 1, "no_data": 1}
    assert conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0] == 0


def test_mixed_fixture_agree_and_disagree_counts(tmp_path):
    """One station agrees, one disagrees -- exercises the exact 'fixture where one
    station disagrees' the founder asked for, in a batch with an agreeing neighbour."""
    conn = _conn(tmp_path)
    _insert(conn, "bma_watermap", "WL.SSB.07", 0.40, "2026-09-27T10:00:00+00:00")
    _insert(conn, "thaiwater_canal_waterlevel", "WL.SSB.07", 0.40, "2026-09-27T10:00:00+00:00")
    _insert(conn, "bma_watermap", "WL.PWT.04", 0.40, "2026-09-27T10:00:00+00:00")
    _insert(conn, "thaiwater_canal_waterlevel", "WL.PWT.04", 0.60, "2026-09-27T10:00:00+00:00")
    result = reconcile.reconcile_canal_water_level(conn, ["WL.SSB.07", "WL.PWT.04"])
    assert result["summary"]["agree"] == 1
    assert result["summary"]["disagree"] == 1
    assert conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0] == 1
