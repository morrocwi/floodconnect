"""Tests for the M7a GOV API MANUAL deliverable (docs/API_MANUAL.md, schemas/*.json,
sources/live_call_index.yaml). These are tests of the DOCUMENTATION, not a new library:
they check that (1) the field paths this manual claims exist really resolve in a real
recorded fixture, (2) a normalised reading built from a real fixture validates against
schemas/reading.schema.json, and (3) a normalised reading, fed through
floodconnect_model's existing classify(), gives the same colour the live code path
already gives for the same raw status word. No network call is made by this test file.

Note: this manual's prose also describes a richer per-ring object
(worst_status/freshness/trend/acceleration/eta_to_bank/end_state/not_joined/
kg_traversal) as fetch/traversal documentation only -- schemas/ring_readout.schema.json
and schemas/sandwich_readout.schema.json were never shipped in this repo, and the
runtime schemas (schemas/layer_readout.schema.json, schemas/sandwich_trace.schema.json)
do not carry that richer shape. This file validates only what is actually shipped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

import floodconnect_model as fm

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SCHEMAS = REPO_ROOT / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def _validator(schema_name: str) -> jsonschema.Validator:
    # reading.schema.json's/series.schema.json's $ref to a sibling schema uses the
    # $id's absolute https://floodconnect.local/... base -- that host does not exist
    # and must never be fetched over the network. referencing.Registry
    # (jsonschema.validators.RefResolver is deprecated) resolves every $ref fully
    # offline by registering each schema's own $id (and bare filename) as a Resource.
    from referencing import Registry, Resource

    schema = _load_schema(schema_name)
    resources = []
    for fname in (
        "reading.schema.json",
        "series.schema.json",
    ):
        doc = _load_schema(fname)
        resources.append((doc["$id"], Resource.from_contents(doc)))
        resources.append((fname, Resource.from_contents(doc)))
    registry = Registry().with_resources(resources)
    cls = jsonschema.validators.validator_for(schema)
    return cls(schema, registry=registry)


def test_reading_schema_is_valid_json_schema():
    schema = _load_schema("reading.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)


def test_series_schema_is_valid_json_schema():
    schema = _load_schema("series.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)


# ---------------------------------------------------------------------------
# 1. field paths claimed in the manual resolve in a real fixture
# ---------------------------------------------------------------------------

def test_bma_watermap_smk01_fixture_has_claimed_fields():
    """docs/API_MANUAL.md section 3 claims these exact field paths for WL.SMK.01."""
    data = json.loads((FIXTURES / "bma_watermap_smk01_live_sample.json").read_text())
    rec = next(r for r in data if r["water_code"] == "WL.SMK.01")
    assert rec["critical"] == 0.44
    assert rec["right_bank"] == 0.44
    assert rec["warning"] == 0.35
    assert rec["wl_in"] == -0.45
    assert rec["txtStatus"] == "ปกติ"
    assert rec["water_name"].startswith("จุดวัดบึงรับน้ำหมู่บ้านสัมมากร")
    assert rec["site_timestampTH"] == "05/10/2569 11:15"
    assert rec["water_control"] is None


def test_thaiwater_waterlevel_fixture_has_claimed_fields():
    data = json.loads((FIXTURES / "thaiwater_waterlevel_sample.json").read_text())
    rows = data["data"] if isinstance(data, dict) else data
    rec = rows[0]
    for path in ("waterlevel_msl", "waterlevel_datetime", "situation_level"):
        assert path in rec
    assert "min_bank" in rec["station"] or "critical_level_msl" in rec["station"]


# ---------------------------------------------------------------------------
# 2. normalised reading validates against reading.schema.json
# ---------------------------------------------------------------------------

def _normalize_bma_watermap(rec: dict) -> dict:
    """Mirrors docs/API_MANUAL.md section 11.1's mapping table for bma_watermap."""
    return {
        "source_id": "bma_watermap",
        "station_code": rec["water_code"],
        "station_name": rec["water_name"],
        "lat": rec["latitude"],
        "lon": rec["longitude"],
        "variable": "canal_water_level_m",
        "value": rec["wl_in"],
        "unit": "m",
        "observed_at_utc": "2026-10-05T04:15:00+00:00",
        "fetched_at_utc": "2026-10-05T04:20:19+00:00",
        "warning": rec["warning"],
        "critical": rec["critical"],
        "bank": rec["right_bank"],
        "status": rec["txtStatus"],
        "trust_tier": "official_telemetry",
    }


def test_normalized_bma_watermap_reading_validates_against_schema():
    data = json.loads((FIXTURES / "bma_watermap_smk01_live_sample.json").read_text())
    rec = next(r for r in data if r["water_code"] == "WL.SMK.01")
    reading = _normalize_bma_watermap(rec)
    _validator("reading.schema.json").validate(reading)


def test_normalized_thaiwater_waterlevel_reading_validates_against_schema():
    data = json.loads((FIXTURES / "thaiwater_waterlevel_sample.json").read_text())
    rows = data["data"] if isinstance(data, dict) else data
    rec = rows[0]
    status_word = (
        "OVERBANK"
        if (rec.get("diff_wl_bank_text") or "").startswith("ล้นตลิ่ง")
        else (f"thaiwater_situation_{rec['situation_level']}" if rec.get("situation_level") else "NO_THRESHOLD")
    )
    reading = {
        "source_id": "thaiwater_waterlevel",
        "station_code": rec["station"].get("tele_station_oldcode") or str(rec["station"]["id"]),
        "station_name": rec["station"].get("tele_station_name", {}).get("th"),
        "lat": rec["station"].get("tele_station_lat"),
        "lon": rec["station"].get("tele_station_long"),
        "variable": "waterlevel_msl",
        "value": float(rec["waterlevel_msl"]) if rec.get("waterlevel_msl") else None,
        "unit": "m",
        "observed_at_utc": rec["waterlevel_datetime"].replace(" ", "T") + ":00+07:00",
        "fetched_at_utc": "2026-10-05T04:20:00+00:00",
        "warning": None,
        "critical": rec["station"].get("critical_level_msl"),
        "bank": rec["station"].get("min_bank"),
        "status": status_word,
        "trust_tier": "official_telemetry",
    }
    _validator("reading.schema.json").validate(reading)


# ---------------------------------------------------------------------------
# 3. normalised reading, fed to classify(), matches the live code path's colour
# ---------------------------------------------------------------------------

def test_normalized_bma_watermap_status_matches_classify():
    data = json.loads((FIXTURES / "bma_watermap_smk01_live_sample.json").read_text())
    rec = next(r for r in data if r["water_code"] == "WL.SMK.01")
    reading = _normalize_bma_watermap(rec)
    assert fm.classify(reading["status"]) == "GREEN"


def test_normalized_thaiwater_situation5_matches_classify():
    # situation_level 5 maps to RED via STATUS_TO_LEVEL -- same code path as kb.py.
    assert fm.classify("thaiwater_situation_5") == "RED"


# ---------------------------------------------------------------------------
# 4. series shape claimed by the manual for bma_station_detail / thaiwater graph
# ---------------------------------------------------------------------------

def test_bma_station_detail_series_fixture_has_claimed_shape():
    """docs/API_MANUAL.md section 10 claims [Date.UTC(Y,M0,D,h,m,s), value] pairs,
    5-minute steps, for WL.SMK.01 (StationDetail?id=284)."""
    data = json.loads((FIXTURES / "bma_station_detail_smk01_series_sample.json").read_text())
    assert data["n_points"] > 0
    first = data["sample_first_3"][0]
    assert len(first) == 7  # Y, M, D, h, m, s, value
    second = data["sample_first_3"][1]
    # 5-minute step between consecutive points (minute field, same hour)
    assert int(second[4]) - int(first[4]) == 5 or int(second[3]) != int(first[3])


def test_bma_station_detail_series_converts_and_validates_against_series_schema():
    """Converts the bma_station_detail WL.SMK.01 series fixture (literal Date.UTC
    tuples) into schemas/series.schema.json's shape, applying the M0+1 month fix
    and the +07:00 Bangkok-local offset (reading.schema.json's observed_at_utc
    note) -- then validates the result and checks the first tick lands on the
    correct calendar date (2026-10-03, not 2026-09-03)."""
    import datetime as dt

    data = json.loads((FIXTURES / "bma_station_detail_smk01_series_sample.json").read_text())
    ticks = []
    for y, m0, d, h, mi, s, value in data["sample_first_3"]:
        month = int(m0) + 1
        observed = dt.datetime(int(y), month, int(d), int(h), int(mi), int(s))
        observed_utc = (observed - dt.timedelta(hours=7)).isoformat() + "Z"
        ticks.append({"observed_at_utc": observed_utc, "value": float(value)})
    series = {
        "station_code": "WL.SMK.01",
        "source_id": "bma_station_detail",
        "ticks": ticks,
        "declared_tick_spacing_minutes": 5,
        "max_gap_minutes": 10,
    }
    _validator("series.schema.json").validate(series)
    first_observed = dt.datetime.fromisoformat(ticks[0]["observed_at_utc"].replace("Z", "+00:00"))
    assert first_observed.date() == dt.date(2026, 10, 3)


def test_thaiwater_waterlevel_graph_fixture_has_claimed_shape():
    """docs/API_MANUAL.md section 10 claims data.graph_data[].{datetime,value,discharge}."""
    data = json.loads((FIXTURES / "thaiwater_waterlevel_graph_sample.json").read_text())
    rec = data["sample"]["first_3"][0]
    for key in ("datetime", "value", "value_out", "discharge"):
        assert key in rec


def test_fault_reading_withholds_value_per_schema():
    """MEASURED 2026-10-05: WL.SSB.02 status 'ขัดข้อง' (fault), last reading 2026-03-23 --
    a FAULT record must have value=null and must never be allowed to set a ring colour."""
    reading = {
        "source_id": "bma_watermap",
        "station_code": "WL.SSB.02",
        "variable": "canal_water_level_m",
        "value": None,
        "bank": None,
        "bank_note": "not provided by source",
        "critical": None,
        "status": "ขัดข้อง",
        "freshness_flag": "FAULT",
        "observed_at_utc": "2026-03-23T00:00:00+07:00",
        "fetched_at_utc": "2026-10-05T04:31:00+00:00",
        "trust_tier": "official_telemetry",
    }
    _validator("reading.schema.json").validate(reading)
    assert reading["value"] is None
    assert reading["freshness_flag"] == "FAULT"


def test_every_registry_source_is_mentioned_in_the_manual_or_excluded():
    import yaml

    registry = yaml.safe_load((REPO_ROOT / "sources" / "registry.yaml").read_text())
    srcs = registry.get("sources") if isinstance(registry, dict) else registry
    ids = list(srcs.keys()) if isinstance(srcs, dict) else [s.get("id") for s in srcs]

    manual = (REPO_ROOT / "docs" / "API_MANUAL.md").read_text()
    missing = [sid for sid in ids if f"`{sid}`" not in manual]
    assert not missing, f"registry source(s) not mentioned anywhere in API_MANUAL.md: {missing}"
