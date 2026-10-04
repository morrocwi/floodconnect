"""Contract tests for the connector-contract remediation batch (2026-10-02): real single-GET
captures for sources that already have a dedicated pure parser in `parsers.py` or
`tools/harvest/forecast7d_draft.py`, replayed through that real parser -- never a
hand-built payload, same discipline as `test_openmeteo_forecast.py` /
`test_thaiwater_canal_waterlevel.py` / `test_gdacs_events.py`.

Captured 2026-10-02 (see each fixture's own `*_captured.sidecar.json` for the exact
URL/timestamp/sha256). One test function per source so a future re-capture that breaks
one parser doesn't hide a regression in another. Several of these legitimately return a
small or zero-length result for THIS capture (e.g. a model with no data at this specific
point, or an index/table with few rows) -- that is a real, honestly-observed result, not
a test bug; each such case is called out in its own test's comment, and the assertion is
written to still prove the parser ran correctly (no crash, right shape) rather than
asserting a nonzero count it cannot honestly claim.

These tests widen `contract_test` coverage from 3/33 to 23/33 wired sources (defect-1
remediation) -- see CONVERGE_LEDGER.yaml (internal, local-only team ledger, not
shipped in this public tree) for the remaining 10 (BMA/DDS HTML+PDF+GIF
sources, 2 dormant/403 hosts, 2 legacy http:// gov pages, multi-request collectors not
reduced to a single fixture), each with its own deferral reason, not silently dropped."""
import datetime

import parsers
from tools.harvest.forecast7d_draft import (
    parse_openmeteo_multimodel_daily,
    parse_openmeteo_ensemble_members,
    parse_metno_locationforecast_daily,
    parse_openmeteo_previous_runs_skillcheck,
)
from tests.contract.conftest import load_captured


def test_openmeteo_flood_parses_daily_discharge():
    data, sidecar = load_captured("openmeteo_flood")
    assert sidecar["url"].startswith("https://flood-api.open-meteo.com/v1/flood")
    rows = parsers.parse_openmeteo_flood(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert isinstance(r["discharge_m3s"], float)


def test_openmeteo_ensemble_parses_member_spread():
    data, sidecar = load_captured("openmeteo_ensemble")
    assert sidecar["url"].startswith("https://ensemble-api.open-meteo.com/v1/ensemble")
    rows = parsers.parse_openmeteo_ensemble(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["n_members"] > 0
        assert r["min_mm"] <= r["median_mm"] <= r["max_mm"]


def test_openmeteo_marine_handles_an_all_null_capture_without_fabricating():
    """This particular capture's `sea_level_height_msl` series is entirely null (MEASURED
    -- re-checked when this test was written: the model has no data for this point/run).
    The parser's own documented rule is to skip a null row, never fabricate a value --
    this test proves that rule holds even when EVERY row is null, not just some."""
    data, sidecar = load_captured("openmeteo_marine")
    assert sidecar["url"].startswith("https://marine-api.open-meteo.com/v1/marine")
    assert data["hourly"]["sea_level_height_msl"]  # the raw series exists and is non-empty
    assert all(v is None for v in data["hourly"]["sea_level_height_msl"]), (
        "fixture is no longer all-null -- update this test to also assert on real rows")
    rows = parsers.parse_openmeteo_marine(data)
    assert rows == []


def test_openmeteo_soil_moisture_parses_three_depth_layers():
    data, sidecar = load_captured("openmeteo_soil_moisture")
    rows = parsers.parse_openmeteo_soil_moisture(data)
    assert isinstance(rows, list) and len(rows) > 0
    assert any(r["soil_moisture_0_to_1cm"] is not None for r in rows)


def test_openmeteo_archive_precip_parses_daily_sums():
    data, sidecar = load_captured("openmeteo_archive_precip")
    rows = parsers.parse_openmeteo_archive_precip(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert isinstance(r["precipitation_sum_mm"], float)


def test_openmeteo_pressure_parses_multimodel_hourly():
    data, sidecar = load_captured("openmeteo_pressure")
    rows = parsers.parse_openmeteo_pressure_multimodel(data)
    assert isinstance(rows, list) and len(rows) > 0
    models = {r["model"] for r in rows}
    assert len(models) > 1, "expected more than one model column in a multimodel capture"


def test_openmeteo_sst_parses_three_sea_points():
    data, sidecar = load_captured("openmeteo_sst")
    point_ids = list(parsers.OPENMETEO_SST_POINTS.keys())
    by_point = parsers.parse_openmeteo_sst_multipoint(data, point_ids)
    assert set(by_point.keys()) == set(point_ids)
    assert any(len(rows) > 0 for rows in by_point.values())


def test_nasa_power_skips_the_minus999_fill_value():
    """NASA POWER's own fill value for a not-yet-processed day is -999.0 (see the
    parser's docstring) -- this capture's trailing 1-3 days are expected to carry it.
    The real assertion here is that -999 never survives into the parsed output."""
    data, sidecar = load_captured("nasa_power")
    rows = parsers.parse_nasa_power_daily_rain(data)
    assert isinstance(rows, list) and len(rows) > 0
    assert all(r["rain_mm"] != parsers.NASA_POWER_FILL_VALUE for r in rows)


def test_hii_waterlevel_load_parses_station_timesteps():
    data, sidecar = load_captured("hii_waterlevel_load")
    rows = parsers.parse_hii_waterlevel_load(data)
    assert isinstance(rows, list) and len(rows) > 0
    assert any(r.get("discharge_cms") is not None for r in rows)
    assert any(r.get("waterlevel_msl") is not None for r in rows)


def test_thaiwater_flood_road_parses_road_stations():
    data, sidecar = load_captured("thaiwater_flood_road")
    assert sidecar["url"].endswith("flood_road")
    rows = parsers.parse_thaiwater_flood_road(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert isinstance(r["value_cm"], float)


def test_thaiwater_rain_24h_parses_rain_stations():
    data, sidecar = load_captured("thaiwater_rain_24h")
    assert sidecar["url"].endswith("rain_24h")
    rows = parsers.parse_thaiwater_rain_24h(data)
    assert isinstance(rows, list) and len(rows) > 0
    assert any(r["mm_24h"] is not None for r in rows)


def test_thaiwater_waterlevel_parses_stations():
    data, sidecar = load_captured("thaiwater_waterlevel")
    assert sidecar["url"].endswith("/waterlevel")
    rows = parsers.parse_thaiwater_waterlevel(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert isinstance(r["lat"], float) and isinstance(r["lon"], float)


def test_hii_dam_parses_nationwide_census():
    data, sidecar = load_captured("hii_dam")
    rows = parsers.parse_hii_dam(data)
    # Trimmed excerpt (publish-safety finding, 2026-10-03: 300KB fixture budget) --
    # the full capture is a nationwide census (hundreds of rows); this fixture keeps a
    # small real excerpt per station_type, so this is a structural sanity floor only.
    assert isinstance(rows, list) and len(rows) >= 3
    for r in rows:
        assert r["dam_id"] is not None


def test_hii_watergate_parses_gate_stations():
    data, sidecar = load_captured("hii_watergate")
    rows = parsers.parse_hii_watergate(data)
    assert isinstance(rows, list) and len(rows) > 0


def test_openmeteo_forecast16d_parses_nine_deterministic_models():
    data, sidecar = load_captured("openmeteo_forecast16d")
    run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = parse_openmeteo_multimodel_daily(data, run_time=run_time)
    assert isinstance(rows, list) and len(rows) > 0
    models = {r["model"] for r in rows}
    assert len(models) > 1


def test_openmeteo_ensemble_daily_parses_member_rows():
    data, sidecar = load_captured("openmeteo_ensemble_daily")
    run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = parse_openmeteo_ensemble_members(data, run_time=run_time)
    assert isinstance(rows, list) and len(rows) > 0


def test_metno_locationforecast_parses_daily_rollup():
    data, sidecar = load_captured("metno_locationforecast")
    run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = parse_metno_locationforecast_daily(data, run_time=run_time)
    assert isinstance(rows, list) and len(rows) > 0


def test_openmeteo_previous_runs_parses_skillcheck_columns():
    data, sidecar = load_captured("openmeteo_previous_runs")
    run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = parse_openmeteo_previous_runs_skillcheck(data, run_time=run_time)
    assert isinstance(rows, list) and len(rows) > 0
    models = {r["model"] for r in rows}
    assert "gfs_seamless_currentbest" in models


def test_openmeteo_multimodel_parses_one_model_hourly_precip():
    """This capture used a single model (icon_seamless) rather than the 6-model fan-out
    collect_openmeteo_multimodel makes in production (6 GETs) -- a contract fixture only
    needs to prove the shared hourly-precip parsing path, not replicate every model."""
    data, sidecar = load_captured("openmeteo_multimodel")
    rows = parsers.parse_openmeteo_forecast(data)
    assert isinstance(rows, list) and len(rows) > 0
    for row in rows:
        assert isinstance(row["mm"], float)
