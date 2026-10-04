"""Tests for the 2026-09-27 "free government + free global" collector wave (founder ask:
"ต่อให้เสร็จเฉพาะของฟรี แน่นอน ก่อน"). No test here makes a live network call -- every
collector's single `_one_get` is monkeypatched to return a real (trimmed) cached payload
from `tests/fixtures/`, same discipline as the rest of this file's siblings."""
import json
from pathlib import Path

import pytest

import collect
import parsers
import store

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_one_get(body: bytes, status: int = 200):
    def _fn(url, headers, timeout=None):
        return status, body
    return _fn


def test_openmeteo_flood_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_flood_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_flood(conn)
    assert res.ok is True
    assert res.counts["inserted"] == 7 * len(collect.OPENMETEO_FLOOD_POINTS)
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='openmeteo_flood'").fetchall()
    assert {r["station_code"] for r in rows} == set(collect.OPENMETEO_FLOOD_POINTS)



def test_openmeteo_ensemble_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_ensemble_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_ensemble(conn)
    assert res.ok is True
    assert res.counts["inserted"] == 6 * len(collect.OPENMETEO_ENSEMBLE_POINTS)



def test_openmeteo_marine_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_marine_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_marine(conn)
    assert res.ok is True
    assert res.counts["inserted"] == 72



def test_nasa_power_collector_skips_fill_value(monkeypatch, tmp_path):
    body = (FIXTURES / "nasa_power_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_nasa_power(conn)
    assert res.ok is True
    assert res.counts["inserted"] == 5  # 3 of 8 sample days are the -999 fill value



def test_openmeteo_multimodel_collector_writes_forecast_dir(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_multimodel_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    fake_forecast_dir = tmp_path / "raw" / "forecast"
    monkeypatch.setattr(collect, "FORECAST_DIR", fake_forecast_dir)
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_multimodel(conn)
    assert res.ok is True
    for model in collect.OPENMETEO_MULTIMODEL_MODELS:
        assert (fake_forecast_dir / f"openmeteo_{model}.json").exists()
    assert res.counts["inserted"] == 6 * len(collect.OPENMETEO_MULTIMODEL_MODELS)




def test_openmeteo_forecast16d_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_forecast16d_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_forecast16d(conn)
    assert res.ok is True
    n_points = len(collect.FORECAST7D_POINTS)
    assert res.counts["inserted"] > 0
    # every point gets its own archived raw file
    for point_id in collect.FORECAST7D_POINTS:
        assert list((fake_raw_live / "openmeteo_forecast16d").glob(f"*_{point_id}.json"))
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='openmeteo_forecast16d'").fetchall()
    station_codes = {r["station_code"] for r in rows}
    assert len(station_codes) == n_points * len(collect.FORECAST16D_MODELS)
    for point_id in collect.FORECAST7D_POINTS:
        assert f"{point_id}:ecmwf_ifs025" in station_codes


def test_openmeteo_ensemble_daily_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_ensemble_daily_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_ensemble_daily(conn)
    assert res.ok is True
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='openmeteo_ensemble_daily'").fetchall()
    station_codes = {r["station_code"] for r in rows}
    # derived median/p10/p90 summary rows must be present alongside member rows
    assert any(":gfs_ensemble_median" in c for c in station_codes)
    assert any(":gfs_ensemble_p10" in c for c in station_codes)
    assert any(":gfs_ensemble_p90" in c for c in station_codes)


def test_metno_locationforecast_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "metno_locationforecast_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_metno_locationforecast(conn)
    assert res.ok is True
    assert res.counts["inserted"] > 0
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='metno_locationforecast'").fetchall()
    station_codes = {r["station_code"] for r in rows}
    for point_id in collect.FORECAST7D_POINTS:
        assert f"{point_id}:metno" in station_codes


def test_metno_locationforecast_points_filter_excludes_other_areas(monkeypatch, tmp_path):
    """`points=` restricts this collector to one named point
    instead of all 8 FORECAST7D_POINTS -- this is what `kb.py`'s `--refresh --at
    sammakorn` now passes so a sammakorn refresh stops also requesting MET Norway data
    for hatyai/nan/chiangmai (a real MEASURED finding). Real captured fixture
    body (same one `test_metno_locationforecast_collector` above uses), one real `_one_get`
    call recorded via the monkeypatch, asserted to be exactly one call -- the point-count
    reduction is MEASURED here, not just read off the code."""
    body = (FIXTURES / "metno_locationforecast_sample.json").read_bytes()
    calls = []

    def _recording_one_get(url, headers, timeout=30):
        calls.append(url)
        return 200, body

    monkeypatch.setattr(collect, "_one_get", _recording_one_get)
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    sammakorn_only = {"sammakorn": collect.FORECAST7D_POINTS["sammakorn"]}
    res = collect.collect_metno_locationforecast(conn, points=sammakorn_only)
    assert res.ok is True
    assert len(calls) == 1, "one point requested in, one GET out -- not all 8"
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='metno_locationforecast'").fetchall()
    station_codes = {r["station_code"] for r in rows}
    assert station_codes == {"sammakorn:metno"}
    for excluded in ("hatyai:metno", "nan:metno", "chiangmai:metno"):
        assert excluded not in station_codes


def test_refresh_relevant_sources_points_by_source_excludes_other_areas(monkeypatch, tmp_path):
    """Same MEASURED finding, exercised through `collect.run()`'s own
    `points_by_source` wiring (what `kb._refresh_relevant_sources` actually calls) --
    not just the collector function called directly above."""
    body = (FIXTURES / "metno_locationforecast_sample.json").read_bytes()
    calls = []

    def _recording_one_get(url, headers, timeout=30):
        calls.append(url)
        return 200, body

    monkeypatch.setattr(collect, "_one_get", _recording_one_get)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    sammakorn_only = {"sammakorn": collect.FORECAST7D_POINTS["sammakorn"]}
    results = collect.run(
        ["metno_locationforecast"], dry_run=False, db_path=tmp_path / "t.sqlite",
        points_by_source={"metno_locationforecast": sammakorn_only},
    )
    assert len(results) == 1 and results[0].ok is True
    assert len(calls) == 1, "points_by_source must reach the collector, not fetch all 8"


def test_openmeteo_previous_runs_collector_sammakorn_only(monkeypatch, tmp_path):
    body = (FIXTURES / "openmeteo_previous_runs_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    fake_raw_live = tmp_path / "raw" / "live"
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", fake_raw_live)
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_openmeteo_previous_runs(conn)
    assert res.ok is True
    assert res.counts["inserted"] > 0
    rows = conn.execute(
        "SELECT DISTINCT station_code FROM observations "
        "WHERE source_id='openmeteo_previous_runs'").fetchall()
    station_codes = {r["station_code"] for r in rows}
    assert all(c.startswith("sammakorn:") for c in station_codes)
    assert any("currentbest" in c for c in station_codes)


def test_forecast7d_collectors_dry_run_make_no_network_call(monkeypatch, tmp_path):
    def _boom(*a, **kw):
        raise AssertionError("dry-run must not call _one_get")
    monkeypatch.setattr(collect, "_one_get", _boom)
    conn = store.connect(tmp_path / "t.sqlite")
    for fn in (collect.collect_openmeteo_forecast16d, collect.collect_openmeteo_ensemble_daily,
               collect.collect_metno_locationforecast, collect.collect_openmeteo_previous_runs):
        res = fn(conn, dry_run=True)
        assert res.ok is True
