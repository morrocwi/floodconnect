"""Tests for site/build_data.py's build-5 (2026-09-27) per-canal normal/control level
readout: resolve_normal_level() (BMA water_control > dry-season median > OPEN),
prop_flood_02_time_to_threshold() (PROPOSAL, unverified linear extrapolation, REFUSED
paths), and canal_normal_level_readout()'s rendered Thai text. Uses an in-memory-style
tmp sqlite (via store.connect/insert_observation) and a small in-repo dry-season dict --
never the real observations.sqlite or network.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "site"))
sys.path.insert(0, str(REPO_ROOT))

import store  # noqa: E402
import build_data as bd  # noqa: E402


def _conn(tmp_path, control_value=None, station_code="WL.TEST.01"):
    conn = store.connect(tmp_path / "test.sqlite")
    if control_value is not None:
        store.insert_observation(
            conn, source_id="bma_station_detail", station_code=station_code,
            variable="water_control_m", value=control_value, unit="m",
            observed_at_utc="2026-09-27T09:00:00+00:00",
            fetched_at_utc="2026-09-27T09:05:00+00:00", trust_tier="official_telemetry")
    return conn


DRY_SEASON = {"WL.TEST.01": {"normal_level_m": -0.30, "period": "2026-02-01..2026-03-15"}}


def test_resolve_normal_level_prefers_bma_control(tmp_path):
    conn = _conn(tmp_path, control_value=0.70)
    r = bd.resolve_normal_level(conn, "WL.TEST.01", DRY_SEASON)
    assert r == {"value": 0.70, "basis": "VERIFIED-BMA-control"}


def test_resolve_normal_level_falls_back_to_dry_season_median(tmp_path):
    conn = _conn(tmp_path, control_value=None)
    r = bd.resolve_normal_level(conn, "WL.TEST.01", DRY_SEASON)
    assert r == {"value": -0.30, "basis": "MEASURED-history"}


def test_resolve_normal_level_open_when_neither(tmp_path):
    conn = _conn(tmp_path, control_value=None)
    r = bd.resolve_normal_level(conn, "WL.UNKNOWN", DRY_SEASON)
    assert r == {"value": None, "basis": "OPEN"}


def test_prop_flood_02_refuses_with_no_prior_reading():
    r = bd.prop_flood_02_time_to_threshold(0.50, "2026-09-27T10:00:00+00:00", None, -0.30)
    assert r["status"] == "refused"
    assert r["reason"] == "no_qualifying_prior_reading"


def test_prop_flood_02_refuses_when_trend_flat():
    prev = {"value": 0.50, "observed_at": "2026-09-27T08:00:00+00:00", "delta": 0.0}
    r = bd.prop_flood_02_time_to_threshold(0.50, "2026-09-27T10:00:00+00:00", prev, -0.30)
    assert r["status"] == "refused"
    assert r["reason"] == "trend_flat_or_rising"


def test_prop_flood_02_refuses_when_rising():
    prev = {"value": 0.30, "observed_at": "2026-09-27T08:00:00+00:00", "delta": 0.20}
    r = bd.prop_flood_02_time_to_threshold(0.50, "2026-09-27T10:00:00+00:00", prev, -0.30)
    assert r["status"] == "refused"
    assert r["reason"] == "trend_flat_or_rising"


def test_prop_flood_02_already_at_or_below():
    r = bd.prop_flood_02_time_to_threshold(-0.40, "2026-09-27T10:00:00+00:00", None, -0.30)
    assert r["status"] == "already_at_or_below"


def test_prop_flood_02_computes_hours_when_falling():
    # falling 0.20 m over 2 h -> rate -0.10 m/h; current 0.50, threshold -0.30 ->
    # (0.50 - (-0.30)) / 0.10 = 8.0 h
    prev = {"value": 0.70, "observed_at": "2026-09-27T08:00:00+00:00", "delta": -0.20}
    r = bd.prop_flood_02_time_to_threshold(0.50, "2026-09-27T10:00:00+00:00", prev, -0.30)
    assert r["status"] == "ok"
    assert r["hours"] == pytest.approx(8.0)


def test_canal_normal_level_readout_open_when_no_basis(tmp_path):
    conn = _conn(tmp_path, control_value=None)
    out = bd.canal_normal_level_readout(conn, "WL.UNKNOWN", 0.5, "2026-09-27T10:00:00+00:00", DRY_SEASON)
    assert out["status"] == "open"
    assert out["readout_th"] is None


def test_canal_normal_level_readout_refused_rendered_text(tmp_path):
    conn = _conn(tmp_path, control_value=None)
    out = bd.canal_normal_level_readout(conn, "WL.TEST.01", 0.10, "2026-09-27T10:00:00+00:00", DRY_SEASON)
    # no prior reading in this fixture DB -> REFUSED, exact Thai wording used by the page
    assert out["status"] == "refused"
    assert out["readout_th"] == "ยังบอกไม่ได้"


def test_canal_normal_level_readout_trending_text(tmp_path):
    conn = _conn(tmp_path, control_value=None)
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.TEST.01",
        variable="canal_water_level_m", value=0.70, unit="m",
        observed_at_utc="2026-09-27T08:00:00+00:00",
        fetched_at_utc="2026-09-27T08:05:00+00:00", trust_tier="official_telemetry")
    out = bd.canal_normal_level_readout(conn, "WL.TEST.01", 0.50, "2026-09-27T10:00:00+00:00", DRY_SEASON)
    assert out["status"] == "trending_to_normal"
    assert "กลับสู่ปกติ" in out["readout_th"]
    assert out["basis_label"] == "ค่ากลางฤดูแล้ง"


def test_hero_summary_counts_only_known_stations():
    readouts = [
        {"status": "at_normal"}, {"status": "trending_to_normal"},
        {"status": "refused"}, None, {"status": "open"},
    ]
    summary = bd.canal_normal_level_hero_summary(readouts)
    assert summary["known"] == 3
    assert summary["at_normal"] == 1
