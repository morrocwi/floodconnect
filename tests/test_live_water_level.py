"""
Tests for live_water_level.py. No network calls -- parsing/join logic only, against a
recorded fixture (tests/fixtures/klongmap_sample.json, 5 stations trimmed from a real
cached KlongMap dump, raw/bangkok/klongmap_data.json, stripped to public station-level
fields only: name, coordinate, current level, timestamp).
"""
import json
import sys
from pathlib import Path

import networkx as nx
import pytest

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(REPO_ROOT))

import live_water_level as lwl  # noqa: E402

FIXTURE = HERE / "fixtures" / "klongmap_sample.json"
THAIWATER_FIXTURE = HERE / "fixtures" / "thaiwater_canal_sample.json"
PUMPHISTORY_FIXTURE = HERE / "fixtures" / "pumphistory_sample.html"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_thaiwater_fixture():
    return json.loads(THAIWATER_FIXTURE.read_text(encoding="utf-8"))


def test_parse_klongmap_stations_extracts_expected_fields():
    stations = lwl.parse_klongmap_stations(load_fixture())
    assert len(stations) == 5
    s = stations[0]
    assert s["station_id"] == "10"
    assert s["name_th"] == "จุดวัดคลองบางพรม ตอนถนนกาญจนาภิเษก"
    assert s["lat"] == pytest.approx(13.76264)
    assert s["lon"] == pytest.approx(100.39624)
    assert s["level_m"] == pytest.approx(0.34)
    assert s["observed_at"] == "2026-09-22T17:40:00+00:00"
    assert s["source_url"] == lwl.KLONGMAP_URL
    assert s["fetched_at"] is None  # only fetch_klongmap() fills this in


def test_parse_klongmap_stations_skips_missing_coordinate():
    data = {"waterStation": [{"water_id": "1", "water_station_info": {"latitude": None, "longitude": None},
                               "water_level_last": {"wl_in": 1.0}}]}
    assert lwl.parse_klongmap_stations(data) == []


def test_parse_klongmap_stations_skips_no_reading_sentinel():
    data = {"waterStation": [{"water_id": "1",
                               "water_station_info": {"latitude": 13.7, "longitude": 100.5},
                               "water_level_last": {"wl_in": -99}}]}
    assert lwl.parse_klongmap_stations(data) == []


def test_dotnet_date_to_iso():
    assert lwl._dotnet_date_to_iso("/Date(1790098800000)/") == "2026-09-22T17:40:00+00:00"
    assert lwl._dotnet_date_to_iso(None) is None
    assert lwl._dotnet_date_to_iso("not a date") is None


def _tiny_graph():
    G = nx.DiGraph()
    # one node right on top of station "10" (13.76264, 100.39624), one far away
    G.add_node("100.39624,13.76264", lat=13.76264, lon=100.39624)
    G.add_node("100.90000,14.00000", lat=14.0, lon=100.9)
    return G


def test_attach_live_water_level_matches_nearest_node_within_radius():
    stations = lwl.parse_klongmap_stations(load_fixture())
    G = _tiny_graph()
    summary = lwl.attach_live_water_level(G, stations)
    assert summary["nodes_matched"] == 1  # only the co-located node is within 300 m of any station
    near = G.nodes["100.39624,13.76264"]
    assert near["live_water_level_m"] == pytest.approx(0.34)
    assert near["live_water_level_station"] == "จุดวัดคลองบางพรม ตอนถนนกาญจนาภิเษก"
    assert near["live_water_level_source"] == lwl.KLONGMAP_URL
    far = G.nodes["100.90000,14.00000"]
    assert "live_water_level_m" not in far


def test_attach_live_water_level_never_overwrites_existing_reading():
    stations = lwl.parse_klongmap_stations(load_fixture())
    G = _tiny_graph()
    G.nodes["100.39624,13.76264"]["live_water_level_m"] = 9.99  # pretend already set
    summary = lwl.attach_live_water_level(G, stations)
    assert summary["stations_matched"] == 0
    assert G.nodes["100.39624,13.76264"]["live_water_level_m"] == 9.99


def test_attach_live_water_level_never_overwrites_other_source_attributes():
    stations = lwl.parse_klongmap_stations(load_fixture())
    G = _tiny_graph()
    G.nodes["100.39624,13.76264"]["nearby_floodgates_km_0.3"] = "some other gate"
    lwl.attach_live_water_level(G, stations)
    assert G.nodes["100.39624,13.76264"]["nearby_floodgates_km_0.3"] == "some other gate"


def test_parse_thaiwater_canal_stations_extracts_expected_fields():
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    assert len(stations) == 5
    s = stations[0]
    assert s["station_id"] == "153"
    assert s["name_th"] == "ค.ภาษีเจริญ-ค.มหาศร"
    assert s["lat"] == pytest.approx(13.68138)
    assert s["lon"] == pytest.approx(100.35047)
    assert s["level_m"] == pytest.approx(0.12)
    assert s["observed_at"] == "2021-01-22T05:05:00+00:00"  # local 12:05 UTC+7 -> 05:05 UTC
    assert s["source_url"] == lwl.THAIWATER_CANAL_URL
    assert s["agency"] == "Department of Bangkok"
    assert s["fetched_at"] is None


def test_parse_thaiwater_canal_stations_skips_missing_coordinate():
    data = {"data": [{"station": {"id": 1, "canal_lat": None, "canal_long": None}, "canal_value": 1.0}]}
    assert lwl.parse_thaiwater_canal_stations(data) == []


def test_parse_thaiwater_canal_stations_skips_missing_level():
    data = {"data": [{"station": {"id": 1, "canal_lat": 13.7, "canal_long": 100.5}, "canal_value": None}]}
    assert lwl.parse_thaiwater_canal_stations(data) == []


def test_load_thaiwater_stations_from_file():
    stations = lwl.load_thaiwater_stations_from_file(THAIWATER_FIXTURE)
    assert len(stations) == 5
    assert all(s["fetched_at"] is not None for s in stations)


def test_fetch_thaiwater_stations_raises_on_http_error(monkeypatch):
    import urllib.error

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(lwl.THAIWATER_CANAL_URL, 500, "Server Error", {}, None)

    monkeypatch.setattr(lwl.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(lwl.LiveSourceUnavailable):
        lwl.fetch_thaiwater_stations()


def test_fetch_klongmap_raises_on_http_error(monkeypatch):
    import urllib.error

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(lwl.KLONGMAP_URL, 403, "Forbidden", {}, None)

    monkeypatch.setattr(lwl.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(lwl.LiveSourceUnavailable):
        lwl.fetch_klongmap()


def test_resolve_station_coordinate_passthrough_when_coordinate_present():
    st = {"lat": 1.0, "lon": 2.0, "name_th": "x"}
    assert lwl.resolve_station_coordinate(st) is st


def test_parse_thaiwater_canal_stations_carries_thresholds_gate_and_amphoe():
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    by_id = {s["station_id"]: s for s in stations}

    no_threshold = by_id["153"]
    assert no_threshold["warning_level"] is None
    assert no_threshold["critical_level"] is None
    assert no_threshold["bank"] is None
    assert no_threshold["is_gate"] is False
    assert no_threshold["amphoe_th"] == "หนองแขม"

    gate = by_id["96"]
    assert gate["is_gate"] is True
    assert gate["canal_oldcode"]
    assert gate["canal_out"] is not None

    thresholded = by_id["87"]
    assert thresholded["warning_level"] == pytest.approx(2.6)
    assert thresholded["critical_level"] == pytest.approx(2.8)
    assert thresholded["bank"] == pytest.approx(2.8)


# ---- classify_level ----

def test_classify_level_no_threshold_when_all_none():
    assert lwl.classify_level(1.5, None, None, None) == "NO_THRESHOLD"


def test_classify_level_normal_below_all_bands():
    assert lwl.classify_level(1.0, warning=2.0, critical=2.5, bank=3.0) == "NORMAL"


def test_classify_level_watch_at_warning_boundary():
    assert lwl.classify_level(2.0, warning=2.0, critical=2.5, bank=3.0) == "WATCH"


def test_classify_level_critical_at_critical_boundary():
    assert lwl.classify_level(2.5, warning=2.0, critical=2.5, bank=3.0) == "CRITICAL"


def test_classify_level_overbank_at_bank_boundary():
    assert lwl.classify_level(3.0, warning=2.0, critical=2.5, bank=3.0) == "OVERBANK"


def test_classify_level_overbank_above_all():
    assert lwl.classify_level(10.0, warning=2.0, critical=2.5, bank=3.0) == "OVERBANK"


def test_classify_level_missing_bank_still_classifies_critical():
    assert lwl.classify_level(2.5, warning=2.0, critical=2.5, bank=None) == "CRITICAL"


def test_classify_level_non_numeric_threshold_never_raises():
    # Fix MEDIUM-4 (2026-09-26): a station publishing "N/A"/"" instead of a
    # number used to raise deep inside the >= comparison; it must now degrade to
    # NO_THRESHOLD, never crash the whole classification pass.
    assert lwl.classify_level(2.5, warning="N/A", critical="", bank=None) == "NO_THRESHOLD"
    assert lwl.classify_level("N/A", warning=2.0, critical=2.5, bank=3.0) == "NO_THRESHOLD"
    # numeric strings still classify correctly (safe_float coerces, doesn't just reject)
    assert lwl.classify_level("2.5", warning="2.0", critical="2.5", bank="3.0") == "CRITICAL"


# ---- classify_level normal-level ladder (founder rule, verbatim, 2026-09-27:
# "ไม่ปกติ ต้องต่ำกว่าเกณฑ์ปกติหรือเปล่า แค่นี้ยังไม่เรียกปกติ") ----

def test_classify_level_without_normal_level_unchanged():
    # the old 4-arg call (normal_level omitted) must classify EXACTLY as before --
    # backward compatibility for every call site not yet upgraded to the ladder.
    assert lwl.classify_level(1.0, warning=2.0, critical=2.5, bank=3.0) == "NORMAL"
    assert lwl.classify_level(1.5, None, None, None) == "NO_THRESHOLD"


def test_classify_level_normal_at_or_below_normal_level():
    assert lwl.classify_level(1.0, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "NORMAL"
    assert lwl.classify_level(0.5, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "NORMAL"


def test_classify_level_above_normal_between_normal_and_warning():
    # 1.5 is below warning (2.0) but ABOVE normal_level (1.0) -- must NOT be "NORMAL".
    assert lwl.classify_level(1.5, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "ABOVE_NORMAL"


def test_classify_level_watch_critical_overbank_unaffected_by_normal_level():
    assert lwl.classify_level(2.0, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "WATCH"
    assert lwl.classify_level(2.5, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "CRITICAL"
    assert lwl.classify_level(3.0, warning=2.0, critical=2.5, bank=3.0, normal_level=1.0) == "OVERBANK"


def test_classify_level_no_normal_basis_sentinel_never_normal():
    # opted into the ladder (sentinel), but no normal_level resolved for this station --
    # grey "ยังไม่มีเกณฑ์ปกติ", never green "ปกติ", even though 1.0 is below every
    # published danger threshold.
    assert lwl.classify_level(1.0, warning=2.0, critical=2.5, bank=3.0,
                               normal_level=lwl.NO_NORMAL_LEVEL) == "NO_NORMAL_BASIS"
    # danger thresholds still take priority over the missing-normal-basis state.
    assert lwl.classify_level(2.5, warning=2.0, critical=2.5, bank=3.0,
                               normal_level=lwl.NO_NORMAL_LEVEL) == "CRITICAL"


def test_classify_level_no_normal_basis_even_with_no_danger_thresholds():
    # opted in, no normal_level, AND no warning/critical/bank either -- still the grey
    # "no normal basis" state (never silently falls back to the old NO_THRESHOLD/NORMAL
    # split once the caller has opted into the ladder).
    assert lwl.classify_level(1.0, None, None, None,
                               normal_level=lwl.NO_NORMAL_LEVEL) == "NO_NORMAL_BASIS"


def test_safe_float_coerces_or_returns_none():
    assert lwl.safe_float("2.5") == 2.5
    assert lwl.safe_float(None) is None
    assert lwl.safe_float("N/A") is None
    assert lwl.safe_float("") is None
    assert lwl.safe_float(3) == 3.0


# ---- age_hours / staleness ----

def test_age_hours_basic():
    assert lwl.age_hours("2026-09-25T00:00:00+00:00", "2026-09-26T00:00:00+00:00") == pytest.approx(24.0)


def test_age_hours_none_when_missing():
    assert lwl.age_hours(None, "2026-09-26T00:00:00+00:00") is None
    assert lwl.age_hours("2026-09-25T00:00:00+00:00", None) is None


def test_is_fresh_within_bound():
    fresh, age_h = lwl.is_fresh("2026-09-26T00:00:00+00:00", "2026-09-26T12:00:00+00:00", 24.0)
    assert fresh is True
    assert age_h == pytest.approx(12.0)


def test_is_fresh_past_max_age():
    fresh, age_h = lwl.is_fresh("2026-09-20T00:00:00+00:00", "2026-09-26T00:00:00+00:00", 24.0)
    assert fresh is False
    assert age_h == pytest.approx(144.0)


def test_is_fresh_missing_timestamp_never_fresh():
    fresh, age_h = lwl.is_fresh(None, "2026-09-26T00:00:00+00:00", 24.0)
    assert fresh is False
    assert age_h is None


def test_is_fresh_small_negative_age_still_fresh_for_day_truncated_reference():
    """Fix (2026-10-04): `is_fresh` no longer accepts an UNBOUNDED
    negative age -- a day-pinned caller (`readout.py`'s `as_of_date` path) must now pass
    its own wider `future_tolerance_h` explicitly (readout.py passes -24.0) to keep this
    legitimate same-day case fresh; the function's own default (-1.0, for a REAL
    wall-clock reference) would reject it."""
    fresh, age_h = lwl.is_fresh("2026-09-28T06:20:00+00:00", "2026-09-28T00:00:00+00:00", 24.0,
                                future_tolerance_h=-24.0)
    assert age_h == pytest.approx(-6.333333, rel=1e-3)
    assert fresh is True
    # The function's own default (no `future_tolerance_h` override) is for a real
    # wall-clock reference and must reject this same row.
    fresh_default, _ = lwl.is_fresh("2026-09-28T06:20:00+00:00", "2026-09-28T00:00:00+00:00", 24.0)
    assert fresh_default is False


def test_is_fresh_large_negative_age_now_rejected_by_default():
    """Fix (2026-10-04): this used to be the DOCUMENTED known limit
    (any negative age passed, unbounded) -- a real incident (a Buddhist-year PDF date
    misparsed into the far future, MEASURED `age_h = -4,759,715.5`) showed that limit
    reached production. `is_fresh`'s default `future_tolerance_h` (-1.0) now rejects any
    row more than 1h "in the future" of a REAL wall-clock reference, closing it."""
    fresh, age_h = lwl.is_fresh("2026-09-27T00:00:00+00:00", "2026-09-26T00:00:00+00:00", 24.0)
    assert age_h == pytest.approx(-24.0)
    assert fresh is False
    # A day-pinned caller that explicitly widens the tolerance still gets this row as
    # fresh (unchanged legitimate behaviour for that one caller).
    fresh_pinned, _ = lwl.is_fresh("2026-09-27T00:00:00+00:00", "2026-09-26T00:00:00+00:00", 24.0,
                                   future_tolerance_h=-24.0)
    assert fresh_pinned is True


def test_max_age_hours_for_reads_registry_field():
    registry = {"some_source": {"max_age_hours": 6}}
    assert lwl.max_age_hours_for("some_source", registry) == 6.0


def test_max_age_hours_for_falls_back_when_field_absent():
    registry = {"some_source": {}}
    assert lwl.max_age_hours_for("some_source", registry) == lwl.STALE_HOURS
    assert lwl.max_age_hours_for("unknown_source", registry) == lwl.STALE_HOURS


def test_attach_live_water_level_skips_stale_stations():
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    # newest observed_at in this fixture is 2026-09-25; station 153 is from 2021 -> stale
    G = nx.DiGraph()
    stale_id = next(s for s in stations if s["station_id"] == "153")
    G.add_node("stale-node", lat=stale_id["lat"], lon=stale_id["lon"])
    summary = lwl.attach_live_water_level(G, stations)
    assert summary["stations_stale"] >= 1
    assert "live_water_level_m" not in G.nodes["stale-node"]


def test_attach_live_water_level_writes_threshold_and_status_attributes():
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    fresh = next(s for s in stations if s["station_id"] == "87")
    G = nx.DiGraph()
    G.add_node("n1", lat=fresh["lat"], lon=fresh["lon"])
    summary = lwl.attach_live_water_level(G, stations)
    assert summary["stations_matched"] >= 1
    node = G.nodes["n1"]
    assert node["live_water_level_bma_code"] == fresh["canal_oldcode"]
    assert node["live_water_level_warning_m"] == pytest.approx(2.6)
    assert node["live_water_level_critical_m"] == pytest.approx(2.8)
    assert node["live_water_level_bank_m"] == pytest.approx(2.8)
    assert node["live_water_level_status"] in ("NORMAL", "WATCH", "CRITICAL", "OVERBANK", "NO_THRESHOLD")


# ---- --watch table ----

def test_run_watch_prints_expected_status_strings_and_summary(capsys):
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    center_lat, center_lon = stations[0]["lat"], stations[0]["lon"]
    lwl.run_watch(center_lat, center_lon, radius_km=50.0, from_file=THAIWATER_FIXTURE)
    out = capsys.readouterr().out
    assert "dist_km" in out
    assert "stale skipped" in out
    assert any(status in out for status in ("NORMAL", "WATCH", "CRITICAL", "OVERBANK", "NO_THRESHOLD"))


# ---- BMA PumpHistory (ST.SPS Sammakorn pumps) ----

def load_pumphistory_fixture_text():
    return PUMPHISTORY_FIXTURE.read_text(encoding="utf-8")


def test_parse_pumphistory_html_extracts_all_four_sps_stations():
    rows = lwl.parse_pumphistory_html(load_pumphistory_fixture_text())
    codes = sorted(r["station_code"] for r in rows)
    assert codes == ["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"]


def test_parse_pumphistory_html_fields():
    rows = lwl.parse_pumphistory_html(load_pumphistory_fixture_text())
    by_code = {r["station_code"]: r for r in rows}

    s1 = by_code["ST.SPS.01"]
    assert s1["name_th"] == "สถานีสูบน้ำคลองบ้านม้า 2"
    assert s1["district"] == "สะพานสูง"
    # ST.SPS.01's own status_th is ขัดข้อง (fault) in this fixture -- its level_m must be
    # None (untrusted sensor), never the raw 0.0 the page happens to show (see
    # test_parse_pumphistory_html_fault_status_nulls_level below for the direct check).
    assert s1["level_m"] is None
    assert s1["status_th"] == "ขัดข้อง"
    assert s1["sensor_status"] == "fault"
    assert s1["pumps_total"] == 4
    assert s1["pumps_on"] == 0  # all 4 pump cells say "รอทำงาน" (standby)
    assert s1["gate_open"] == pytest.approx(0.0)
    assert s1["observed_at"] == "2026-09-26T04:00:00+00:00"  # local 11:00 UTC+7 -> 04:00 UTC
    assert s1["source_url"] == lwl.PUMPHISTORY_URL
    assert s1["fetched_at"] is None

    s3 = by_code["ST.SPS.03"]
    assert s3["pumps_total"] == 3
    assert s3["pumps_on"] == 1  # exactly one cell says "ทำงาน" (running)
    assert s3["gate_open"] is None  # all gate cells blank for this station
    assert s3["status_th"] == "ปกติ"
    assert s3["sensor_status"] == "ok"
    assert s3["level_m"] is not None  # normal-status station keeps its real reading


def test_parse_pumphistory_html_fault_status_nulls_level():
    # Direct, isolated check of the fault guard (2026-09-27 data-hygiene fix): a station
    # whose status_th is ขัดข้อง must never carry a numeric level_m, regardless of what
    # the page's raw ระดับน้ำ cell shows.
    rows = lwl.parse_pumphistory_html(load_pumphistory_fixture_text())
    faulted = [r for r in rows if r["status_th"] == "ขัดข้อง"]
    assert faulted, "fixture must contain at least one faulted station to exercise this"
    for r in faulted:
        assert r["level_m"] is None
        assert r["sensor_status"] == "fault"


def test_parse_pumphistory_html_pump_running_vs_standby_distinct():
    # "รอทำงาน" (standby) contains "ทำงาน" as a substring -- must not be miscounted as running.
    rows = lwl.parse_pumphistory_html(load_pumphistory_fixture_text())
    s2 = next(r for r in rows if r["station_code"] == "ST.SPS.02")
    assert s2["pumps_total"] == 2
    assert s2["pumps_on"] == 0


def test_parse_pumphistory_html_skips_short_rows():
    assert lwl.parse_pumphistory_html("<tr role=\"row\" class=\"odd\"><td>x</td></tr>") == []


def test_load_pumphistory_from_file_fills_fetched_at_and_filters_to_default_codes():
    rows = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE)
    assert len(rows) == 4
    assert all(r["fetched_at"] is not None for r in rows)
    assert all(r["station_code"] in lwl.DEFAULT_PUMP_STATION_CODES for r in rows)


def test_load_pumphistory_from_file_no_filter_when_empty_list():
    rows = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE, station_codes=[])
    assert len(rows) == 4  # fixture only has the 4 SPS rows anyway


def test_fetch_pumphistory_raises_on_http_error(monkeypatch):
    import urllib.error

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(lwl.PUMPHISTORY_URL, 403, "Forbidden", {}, None)

    monkeypatch.setattr(lwl.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(lwl.LiveSourceUnavailable):
        lwl.fetch_pumphistory()


def test_parse_pumphistory_html_carries_real_coordinates():
    rows = lwl.parse_pumphistory_html(load_pumphistory_fixture_text())
    by_code = {r["station_code"]: r for r in rows}
    s3 = by_code["ST.SPS.03"]
    assert s3["lat"] == pytest.approx(13.767)
    assert s3["lon"] == pytest.approx(100.6771)
    assert s3["coord_source"] == lwl.DATAPUMP_COORD_SOURCE


def test_watch_pump_block_prints_sorted_by_distance(capsys):
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    center_lat, center_lon = stations[0]["lat"], stations[0]["lon"]
    lwl.run_watch(center_lat, center_lon, radius_km=50.0, from_file=THAIWATER_FIXTURE,
                  pump_from_file=PUMPHISTORY_FIXTURE)
    out = capsys.readouterr().out
    assert "pump stations (sorted by distance" in out
    assert "dist_km" in out
    assert "ST.SPS.01" in out
    assert "ST.SPS.04" in out

    # verify actual distance ordering matches what the printed table implies
    pump_rows = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE)
    dists = {r["station_code"]: lwl.haversine_km(center_lat, center_lon, r["lat"], r["lon"])
             for r in pump_rows}
    block = out[out.index("pump stations"):]
    lines = [ln for ln in block.splitlines() if "ST.SPS" in ln]
    printed_order = [next(tok for tok in ln.split() if tok.startswith("ST.SPS")) for ln in lines]
    assert printed_order == sorted(dists, key=dists.get)


# ---- attach_live_pump_status ----

def test_attach_live_pump_status_matches_nearest_node_and_reports_canal_name():
    pumps = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE)
    p3 = next(p for p in pumps if p["station_code"] == "ST.SPS.03")
    G = nx.DiGraph()
    G.add_node("canal-node-1", lat=p3["lat"], lon=p3["lon"], canal_name="ค.บ้านม้า 2")
    G.add_node("far-node", lat=p3["lat"] + 1.0, lon=p3["lon"] + 1.0)
    summary = lwl.attach_live_pump_status(G, pumps)
    assert summary["pumps_matched"] >= 1
    node = G.nodes["canal-node-1"]
    assert node["live_pump_code"] == "ST.SPS.03"
    assert node["live_pump_pumps_on"] == 1
    assert node["live_pump_pumps_total"] == 3
    match = next(m for m in summary["matches"] if m["station_code"] == "ST.SPS.03")
    assert match["node"] == "canal-node-1"
    assert match["canal_name"] == "ค.บ้านม้า 2"


def test_attach_live_pump_status_reports_no_node_when_out_of_radius():
    pumps = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE)
    G = nx.DiGraph()
    G.add_node("far-node", lat=0.0, lon=0.0)  # nowhere near Bangkok
    summary = lwl.attach_live_pump_status(G, pumps)
    assert summary["pumps_matched"] == 0
    for m in summary["matches"]:
        assert m["node"] is None


def test_attach_live_pump_status_never_overwrites():
    pumps = lwl.load_pumphistory_from_file(PUMPHISTORY_FIXTURE)
    p3 = next(p for p in pumps if p["station_code"] == "ST.SPS.03")
    G = nx.DiGraph()
    G.add_node("canal-node-1", lat=p3["lat"], lon=p3["lon"], live_pump_code="ALREADY-SET")
    lwl.attach_live_pump_status(G, pumps)
    assert G.nodes["canal-node-1"]["live_pump_code"] == "ALREADY-SET"


def test_watch_no_pump_block_when_pump_from_file_omitted(capsys):
    stations = lwl.parse_thaiwater_canal_stations(load_thaiwater_fixture())
    center_lat, center_lon = stations[0]["lat"], stations[0]["lon"]
    lwl.run_watch(center_lat, center_lon, radius_km=50.0, from_file=THAIWATER_FIXTURE)
    out = capsys.readouterr().out
    assert "pump stations" not in out
