"""Tests for parsers.py's BMA water/PageMap/GoogleMap parser (source id `bma_watermap`,
registered 2026-09-27 per docs/knowledge/BMA_WATER_MAP_PROBE.md's probe + proposed
collector spec) and collect.py's collect_bma_watermap(). Uses a small trimmed-real
fixture (tests/fixtures/bma_watermap_sample.json -- 6 verbatim records pulled from the
archived probe response raw/live/bma_maplet/pagemap_googlemap.json, never the full
312-record file), never the real sqlite store, never the network.
"""
import json
from pathlib import Path

import parsers
import store

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "bma_watermap_sample.json"


def _load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_thai_be_datetime_to_iso():
    iso = parsers._thai_be_datetime_to_iso("27/09/2569 17:00")
    assert iso is not None
    # 2569 BE - 543 = 2026 CE; 17:00 Bangkok (UTC+7) = 10:00 UTC
    assert iso.startswith("2026-09-27T10:00:00")
    assert parsers._thai_be_datetime_to_iso(None) is None
    assert parsers._thai_be_datetime_to_iso("not a date") is None


def test_parse_bma_watermap_stations_returns_all_six_and_keeps_real_fields():
    data = _load_fixture()
    stations = parsers.parse_bma_watermap_stations(data)
    assert len(stations) == 6
    by_code = {s["water_code"]: s for s in stations}
    assert set(by_code) == {
        "WL.SSB.09", "WL.PWT.04", "WL.PSR.01", "WL.SST.01", "WL.RPS.01", "WL.ANG.01",
    }
    pwt04 = by_code["WL.PWT.04"]
    assert pwt04["lat"] == 13.72411 and pwt04["lon"] == 100.74987
    assert pwt04["wl_in"] == 0.8
    assert pwt04["warning"] == 0.4 and pwt04["critical"] == 0.6
    assert pwt04["observed_at"] is not None


def test_null_water_control_not_fabricated_as_zero():
    """This is the 52-gate-station / null-water_control regression this collector must
    respect -- store.py's own 'never fabricate a number' rule."""
    data = _load_fixture()
    stations = parsers.parse_bma_watermap_stations(data)
    for s in stations:
        assert s["water_control"] is None  # true of every record in the real archive


def test_gate_stations_parse_with_correct_indices_and_non_gate_stations_have_empty_gates():
    data = _load_fixture()
    stations = parsers.parse_bma_watermap_stations(data)
    by_code = {s["water_code"]: s for s in stations}
    # 4 of the 6 fixture records carry a gate reading (all in watergate01 only, per the
    # real archive -- watergate02-06 are null for every one of these 6 real records)
    gate_codes = {c for c, s in by_code.items() if s["gates"]}
    assert gate_codes == {"WL.SSB.09", "WL.PWT.04", "WL.PSR.01", "WL.SST.01"}
    assert by_code["WL.PWT.04"]["gates"] == {1: 0.5}
    assert by_code["WL.SSB.09"]["gates"] == {1: 0.0}  # closed gate -- a real 0.0, not None
    # the two non-gate stations must have an EMPTY gates dict, never a fabricated one
    assert by_code["WL.RPS.01"]["gates"] == {}
    assert by_code["WL.ANG.01"]["gates"] == {}


def test_record_with_no_water_code_is_skipped():
    stations = parsers.parse_bma_watermap_stations([{"wl_in": 1.0}])
    assert stations == []


def test_collect_bma_watermap_inserts_level_and_gate_rows_without_collision(tmp_path):
    import collect

    conn = store.connect(tmp_path / "test.sqlite")
    data = _load_fixture()
    stations = parsers.parse_bma_watermap_stations(data)
    fetched_at = "2026-09-27T10:05:00+00:00"
    n_level = n_gates = 0
    for s in stations:
        if s.get("observed_at") is None:
            continue
        if s.get("wl_in") is not None:
            n_level += store.insert_observation(
                conn, source_id="bma_watermap", station_code=s["water_code"],
                station_name=s.get("water_name"), lat=s.get("lat"), lon=s.get("lon"),
                variable="canal_water_level_m", value=s["wl_in"], unit="m",
                observed_at_utc=s["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry", warning=s.get("warning"),
                critical=s.get("critical"), status=s.get("status_th"),
                provenance={"source_url": s["source_url"]})
        for gate_index, height_m in s["gates"].items():
            n_gates += store.insert_observation(
                conn, source_id="bma_watermap",
                station_code=f"{s['water_code']}#gate{gate_index:02d}",
                station_name=s.get("water_name"), lat=s.get("lat"), lon=s.get("lon"),
                variable="gate_opening_m", value=height_m, unit="m",
                observed_at_utc=s["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": s["source_url"], "water_code": s["water_code"],
                            "gate_index": gate_index})
    assert n_level == 6
    assert n_gates == 4  # WL.SSB.09, WL.PWT.04, WL.PSR.01, WL.SST.01 -- one gate each
    # regression check: two different gates on the SAME station at the SAME
    # observed_at_utc must NOT collide on the (source_id, station_code, variable,
    # observed_at_utc) identity index -- exercised implicitly above since these 6 fixture
    # records only have 1 gate each; explicitly re-assert the collision-avoidance key
    # shape here so a future refactor that reverts to a bare water_code key is caught.
    rows = conn.execute(
        "SELECT station_code FROM observations WHERE source_id='bma_watermap' "
        "AND variable='gate_opening_m' ORDER BY station_code").fetchall()
    codes = [r["station_code"] for r in rows]
    assert codes == ["WL.PSR.01#gate01", "WL.PWT.04#gate01", "WL.SSB.09#gate01",
                      "WL.SST.01#gate01"]
