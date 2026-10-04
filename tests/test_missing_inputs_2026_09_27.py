"""
Tests for the collectors wired 2026-09-27 per docs/knowledge/
EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md + founder follow-on additions
(pressure, sst, oni). No network calls anywhere in this file -- every parser is tested
against a saved fixture.

Fixture provenance:
  - hii_waterlevel_load_sample.json, openmeteo_soil_moisture_sample.json,
    openmeteo_archive_precip_sample.json, noaa_oni_sample.txt, gdacs_events_sample.json --
    trimmed from real live payloads fetched during this check's own probe (see
    docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md).
  - openmeteo_pressure_sample.json, openmeteo_sst_sample.json -- shape CONFIRMED live this
    task (a quick shape-check fetch, not saved to the census), but VALUES are synthetic
    (illustrative nulls/numbers chosen to exercise the "skip missing" parser path) --
    tagged INSTINCT-shape/synthetic-values, not a captured real payload.
"""
import json
from pathlib import Path

import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- hii_waterlevel_load ------------------------------------------------------------------

def test_parse_hii_waterlevel_load_keeps_discharge_and_msl():
    rows = parsers.parse_hii_waterlevel_load(_load("hii_waterlevel_load_sample.json"))
    assert len(rows) == 8
    assert all(r["observed_at"] for r in rows)
    # at least one row carries a numeric discharge value
    assert any(r["discharge_cms"] is not None for r in rows)


def test_hii_waterlevel_load_url_has_basin_ids_and_dates():
    url = parsers.hii_waterlevel_load_url("6,7,8", "2026-09-27 00:00", "2026-09-27 23:59")
    assert "basin_id=6,7,8" in url
    assert "start_date=" in url and "end_date=" in url


def test_parse_hii_waterlevel_load_skips_missing_datetime():
    data = {"waterlevel_data": {"data": [{"station": {}, "basin": {}, "agency": {}}]}}
    assert parsers.parse_hii_waterlevel_load(data) == []


# --- openmeteo_soil_moisture ----------------------------------------------------------------

def test_parse_openmeteo_soil_moisture_reads_three_layers():
    rows = parsers.parse_openmeteo_soil_moisture(_load("openmeteo_soil_moisture_sample.json"))
    assert len(rows) > 0
    first = rows[0]
    assert first["soil_moisture_0_to_1cm"] is not None
    assert 0.0 <= first["soil_moisture_0_to_1cm"] <= 1.0


def test_parse_openmeteo_soil_moisture_skips_all_null_hour():
    data = {"hourly": {"time": ["2026-09-27T00:00"],
                        "soil_moisture_0_to_1cm": [None],
                        "soil_moisture_1_to_3cm": [None],
                        "soil_moisture_3_to_9cm": [None]}}
    assert parsers.parse_openmeteo_soil_moisture(data) == []


def test_openmeteo_soil_moisture_url_has_no_key():
    url = parsers.openmeteo_soil_moisture_url(13.76, 100.62)
    assert "soil_moisture_0_to_1cm" in url
    assert "apikey" not in url.lower()


# --- openmeteo_archive_precip ----------------------------------------------------------------

def test_parse_openmeteo_archive_precip_sums_match_fixture():
    rows = parsers.parse_openmeteo_archive_precip(_load("openmeteo_archive_precip_sample.json"))
    assert len(rows) == 30
    assert rows[-1]["date"] == "2026-09-26"
    assert rows[-1]["precipitation_sum_mm"] == 44.7


def test_parse_openmeteo_archive_precip_skips_missing_day():
    data = {"daily": {"time": ["2026-09-01", "2026-09-02"], "precipitation_sum": [1.0, None]}}
    rows = parsers.parse_openmeteo_archive_precip(data)
    assert len(rows) == 1 and rows[0]["date"] == "2026-09-01"


# --- gdacs_events ----------------------------------------------------------------------------

def test_parse_gdacs_events_thailand_filters_client_side():
    events = parsers.parse_gdacs_events_thailand(_load("gdacs_events_sample.json"))
    assert len(events) == 1
    assert events[0]["from_date"] == "2026-08-18T01:00:00"


def test_gdacs_event_list_url_has_country_query():
    url = parsers.gdacs_event_list_url("2020-01-01", "2026-09-27")
    assert "country=Thailand" in url


# --- openmeteo_pressure (multi-model) --------------------------------------------------------

def test_parse_openmeteo_pressure_multimodel_skips_null_per_model():
    rows = parsers.parse_openmeteo_pressure_multimodel(_load("openmeteo_pressure_sample.json"))
    models = {r["model"] for r in rows}
    assert models == {"gfs_seamless", "icon_seamless"}  # ecmwf_ifs025 was all-null, dropped
    gfs_rows = [r for r in rows if r["model"] == "gfs_seamless"]
    assert len(gfs_rows) == 2  # one null hour skipped
    assert all(r["pressure_msl_hpa"] is not None for r in rows)


def test_openmeteo_pressure_url_has_past_and_forecast_days():
    url = parsers.openmeteo_pressure_url(13.76, 100.62)
    assert "past_days=7" in url and "forecast_days=16" in url
    assert "pressure_msl" in url


# --- openmeteo_sst (multi-point array response) -----------------------------------------------

def test_parse_openmeteo_sst_multipoint_keeps_request_order():
    point_ids = list(parsers.OPENMETEO_SST_POINTS.keys())
    by_point = parsers.parse_openmeteo_sst_multipoint(_load("openmeteo_sst_sample.json"), point_ids)
    assert set(by_point.keys()) == set(point_ids)
    gulf_rows = by_point["gulf_of_thailand_upper"]
    assert len(gulf_rows) == 1  # one null hour skipped
    assert gulf_rows[0]["sst_degc"] == 29.8


def test_openmeteo_sst_url_is_one_comma_separated_request():
    url = parsers.openmeteo_sst_url()
    assert url.count("latitude=") == 1
    assert "13.2,12.0,9.0" in url


# --- noaa_oni ----------------------------------------------------------------------------------

def test_parse_noaa_oni_latest_reads_last_row():
    text = (FIXTURES / "noaa_oni_sample.txt").read_text(encoding="utf-8")
    row = parsers.parse_noaa_oni_latest(text)
    assert row is not None
    assert row["season"] == "JJA"
    assert row["year"] == 2026
    assert row["anom_degc"] == 1.80


def test_parse_noaa_oni_latest_none_on_empty_text():
    assert parsers.parse_noaa_oni_latest("SEAS YR TOTAL ANOM\n") is None
