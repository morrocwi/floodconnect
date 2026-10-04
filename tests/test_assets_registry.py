"""Tests for assets_registry.py -- harvesters, merge/contradiction detection, build,
near()/stats() against small fixture snippets. No network calls."""
import json

import pytest

import assets_registry as ar
import store


@pytest.fixture()
def conn(tmp_path):
    c = store.connect(tmp_path / "test.sqlite")
    store.ensure_assets_schema(c)
    return c


# --- harvest_thaiwater_bma -----------------------------------------------------------

def test_harvest_thaiwater_bma_gauge_and_gate(tmp_path):
    data = {
        "data": [
            {
                "canal_datetime": "2026-09-27 05:00",
                "canal_value": 0.5,
                "agency": {"agency_name": {"th": "สนน.", "en": "BMA"}},
                "station": {
                    "id": 1, "canal_name": {"th": "ค.ทดสอบ"},
                    "canal_lat": 13.7, "canal_long": 100.6,
                    "canal_oldcode": "WL.TST.01", "bank": 1.0,
                    "warning_level": 0.8, "critical_level": 1.2,
                },
            },
            {
                "canal_datetime": "2026-09-27 05:00",
                "canal_value": 0.2,
                "agency": {"agency_name": {"th": "สนน.", "en": "BMA"}},
                "station": {
                    "id": 2, "canal_name": {"th": "ปตร.ทดสอบ"},
                    "canal_lat": 13.71, "canal_long": 100.61,
                    "canal_oldcode": "WL.TST.02", "bank": None,
                    "warning_level": None, "critical_level": None,
                },
            },
            {
                # no coordinate -> must be skipped, never fabricated
                "canal_datetime": "2026-09-27 05:00",
                "canal_value": 0.1,
                "agency": {"agency_name": {"th": "สนน.", "en": "BMA"}},
                "station": {"id": 3, "canal_name": {"th": "ค.ไม่มีพิกัด"},
                            "canal_lat": None, "canal_long": None,
                            "canal_oldcode": "WL.TST.03"},
            },
        ]
    }
    path = tmp_path / "bma.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_thaiwater_bma(path)
    assert len(rows) == 2
    by_id = {r["asset_id"]: r for r in rows}
    assert "gauge:thaiwater_bma:WL.TST.01" in by_id
    assert by_id["gauge:thaiwater_bma:WL.TST.01"]["class"] == "gauge"
    assert by_id["gauge:thaiwater_bma:WL.TST.01"]["tag"] == "VERIFIED"
    assert "gate:thaiwater_bma:WL.TST.02" in by_id
    assert by_id["gate:thaiwater_bma:WL.TST.02"]["class"] == "gate"


def test_harvest_rain_24h_filters_bounding_box(tmp_path):
    data = {
        "data": [
            {   # inside Bangkok bbox
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "station": {"id": 10, "tele_station_name": {"th": "ในกรุงเทพ"},
                            "tele_station_lat": 13.75, "tele_station_long": 100.6,
                            "tele_station_oldcode": "RF.IN.01"},
            },
            {   # outside Bangkok bbox (e.g. Nakhon Nayok)
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "station": {"id": 11, "tele_station_name": {"th": "นอกกรุงเทพ"},
                            "tele_station_lat": 14.36, "tele_station_long": 101.39,
                            "tele_station_oldcode": "RF.OUT.01"},
            },
        ]
    }
    path = tmp_path / "rain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_rain_24h(path)
    assert len(rows) == 1
    assert rows[0]["source_code"] == "RF.IN.01"
    assert rows[0]["tag"] == "VERIFIED"


def test_harvest_pumphistory_parses_datapump_array(tmp_path):
    html = """
    <html><script>
    var datapump = [{"pumpStation_code": "ST.TST.01",
                      "pumpStation_name": "สถานีทดสอบ",
                      "latitude": 13.72, "longitude": 100.62,
                      "pump_count": 2, "pump_capacity": null,
                      "district_name": "เขตทดสอบ"}];
    </script></html>
    """
    path = tmp_path / "pump.html"
    path.write_text(html, encoding="utf-8")
    rows = ar.harvest_pumphistory(path)
    assert len(rows) == 1
    r = rows[0]
    assert r["asset_id"] == "pump_station:pumphistory:ST.TST.01"
    assert r["class"] == "pump_station"
    assert r["lat"] == 13.72 and r["lon"] == 100.62
    assert r["pumps_total"] == 2
    assert r["tag"] == "VERIFIED"


def test_harvest_pumphistory_missing_array_returns_empty(tmp_path):
    path = tmp_path / "pump.html"
    path.write_text("<html>no datapump here</html>", encoding="utf-8")
    assert ar.harvest_pumphistory(path) == []


def test_harvest_water_station_csv(tmp_path):
    csv_text = (
        "gp_id,gp_name,gp_type,district,gp_lat,gp_long,gp_gate,gp_pump,"
        "gp_total_capacity,gp_water_control,gp_critical,gp_warning\n"
        '1,สถานีทดสอบสูบ,บ่อสูบน้ำ,เขตทดสอบ,13.70,100.60,,45,45,-0.8,0.2,0\n'
        '2,ปตร.ทดสอบ,ประตูระบายน้ำ,เขตทดสอบ,13.71,100.61,,,,,,\n'
        '3,ไม่รู้จักประเภท,ท่อลอด,เขตทดสอบ,13.72,100.62,,,,,,\n'
    )
    path = tmp_path / "water_station.csv"
    path.write_text(csv_text, encoding="utf-8")
    rows = ar.harvest_water_station_csv(path)
    # row 3's gp_type ("ท่อลอด") is not in _GP_TYPE_TO_CLASS -> skipped, not fabricated
    assert len(rows) == 2
    pump = next(r for r in rows if r["class"] == "pump_station")
    assert pump["asset_id"] == "pump_station:water_station:1"
    assert pump["capacity_m3s"] == 45.0
    gate = next(r for r in rows if r["class"] == "gate")
    assert gate["asset_id"] == "gate:water_station:2"


def test_parse_capacity_number_handles_multiline_and_none():
    assert ar._parse_capacity_number("45\n 35(3)+10(5)") == 45.0
    assert ar._parse_capacity_number("") is None
    assert ar._parse_capacity_number(None) is None


# --- merge / contradiction detection --------------------------------------------------

def test_merge_pumphistory_and_water_station_matches_by_exact_name():
    pump_rows = [{
        "asset_id": "pump_station:pumphistory:ST.AAA.01", "class": "pump_station",
        "name_th": "สถานีร่วม", "source_code": "ST.AAA.01",
        "lat": 13.70, "lon": 100.60, "coord_source": "x", "coord_source_type": "official_page",
        "owner": "o", "owner_source": "os", "pumps_total": 2, "capacity_m3s": None,
        "tag": "VERIFIED", "notes": None,
    }]
    ws_rows = [{
        "asset_id": "pump_station:water_station:5", "class": "pump_station",
        "name_th": "สถานีร่วม", "source_code": "5",
        "lat": 13.7001, "lon": 100.6001, "coord_source": "y",
        "coord_source_type": "official_dataset", "owner": "o2", "owner_source": "os2",
        "capacity_m3s": 30.0, "tag": "VERIFIED", "notes": None,
    }]
    contradictions = []
    merged, unmatched = ar._merge_pumphistory_and_water_station(pump_rows, ws_rows, contradictions)
    assert len(merged) == 1
    assert merged[0]["asset_id"] == "pump_station:pumphistory:ST.AAA.01"
    assert "water_station.csv" in merged[0]["notes"]
    assert merged[0]["capacity_m3s"] == 30.0  # filled in from water_station since pump had None
    assert unmatched == []
    assert contradictions == []  # ~11m apart, well under the 200m threshold


def test_merge_detects_coordinate_contradiction_over_200m():
    pump_rows = [{
        "asset_id": "pump_station:pumphistory:ST.BBB.01", "class": "pump_station",
        "name_th": "สถานีขัดแย้ง", "source_code": "ST.BBB.01",
        "lat": 13.70, "lon": 100.60, "coord_source": "x", "coord_source_type": "official_page",
        "owner": "o", "owner_source": "os", "pumps_total": 1, "capacity_m3s": None,
        "tag": "VERIFIED", "notes": None,
    }]
    ws_rows = [{
        "asset_id": "pump_station:water_station:9", "class": "pump_station",
        "name_th": "สถานีขัดแย้ง", "source_code": "9",
        "lat": 13.80, "lon": 100.70, "coord_source": "y",  # far away
        "coord_source_type": "official_dataset", "owner": "o2", "owner_source": "os2",
        "capacity_m3s": None, "tag": "VERIFIED", "notes": None,
    }]
    contradictions = []
    merged, unmatched = ar._merge_pumphistory_and_water_station(pump_rows, ws_rows, contradictions)
    assert len(contradictions) == 1
    assert "coordinates differ" in contradictions[0]["note"]


def test_unmatched_gate_rows_pass_through():
    gate = {"asset_id": "gate:water_station:1", "class": "gate", "name_th": "x",
            "lat": 13.7, "lon": 100.6}
    merged, unmatched = ar._merge_pumphistory_and_water_station([], [gate], [])
    assert merged == []
    assert unmatched == [gate]


# --- haversine -------------------------------------------------------------------------

def test_haversine_zero_distance():
    assert ar.haversine_km(13.7, 100.6, 13.7, 100.6) == pytest.approx(0.0, abs=1e-9)


def test_haversine_known_distance_roughly_right():
    # ~1 degree latitude is ~111 km
    d = ar.haversine_km(13.0, 100.0, 14.0, 100.0)
    assert 108 < d < 112


# --- control_structures cross-check ----------------------------------------------------

def test_harvest_control_structures_resolves_against_bma(tmp_path):
    yaml_text = """
structures:
  test1:
    label_th: "ปตร.ทดสอบ"
    canal_oldcode: "WL.TST.02"
    source: "test source"
  test2:
    label_th: "ปตร.ไม่พบ"
    canal_oldcode: "WL.NOTFOUND.99"
"""
    path = tmp_path / "control_structures.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    bma_by_code = {
        "WL.TST.02": {
            "asset_id": "gate:thaiwater_bma:WL.TST.02", "class": "gate",
            "name_th": "ปตร.ทดสอบ", "lat": 13.7, "lon": 100.6,
            "coord_source": "src", "coord_source_type": "official_api",
            "owner": "BMA", "owner_source": "field",
        }
    }
    rows = ar.harvest_control_structures(path, bma_by_code)
    by_id = {r["asset_id"]: r for r in rows}
    assert by_id["gate:thaiwater_bma:WL.TST.02"]["tag"] == "VERIFIED"
    assert by_id["gate:control_structures:test2"]["tag"] == "OPEN"
    assert by_id["gate:control_structures:test2"]["lat"] is None


# --- store.py assets helpers -----------------------------------------------------------

def test_upsert_asset_new_then_update(conn):
    is_new = store.upsert_asset(
        conn, asset_id="gate:test:1", klass="gate", tag="VERIFIED",
        name_th="test gate", lat=13.7, lon=100.6, verified_at_utc="2026-01-01T00:00:00+00:00")
    assert is_new is True
    is_new2 = store.upsert_asset(
        conn, asset_id="gate:test:1", klass="gate", tag="VERIFIED",
        name_th="test gate updated", lat=13.71, lon=100.61,
        verified_at_utc="2026-01-02T00:00:00+00:00")
    assert is_new2 is False
    rows = store.query_assets(conn)
    assert len(rows) == 1
    assert rows[0]["name_th"] == "test gate updated"
    assert rows[0]["first_seen"] == "2026-01-01T00:00:00+00:00"
    assert rows[0]["last_verified"] == "2026-01-02T00:00:00+00:00"
    log_rows = store.query_assets_log(conn, asset_id="gate:test:1")
    assert len(log_rows) == 2  # append-only history, never overwritten


def test_upsert_asset_never_deletes_existing_rows(conn):
    store.upsert_asset(conn, asset_id="gate:a", klass="gate", tag="VERIFIED", lat=1, lon=1)
    store.upsert_asset(conn, asset_id="gate:b", klass="gate", tag="OPEN")
    assert len(store.query_assets(conn)) == 2
    # re-running a build that only touches gate:a must not remove gate:b
    store.upsert_asset(conn, asset_id="gate:a", klass="gate", tag="VERIFIED", lat=1, lon=1)
    assert len(store.query_assets(conn)) == 2


def test_query_assets_filters_by_class_and_tag(conn):
    store.upsert_asset(conn, asset_id="gate:1", klass="gate", tag="VERIFIED", lat=1, lon=1)
    store.upsert_asset(conn, asset_id="pump_station:1", klass="pump_station", tag="OPEN")
    assert len(store.query_assets(conn, klass="gate")) == 1
    assert len(store.query_assets(conn, tag="OPEN")) == 1
    assert len(store.query_assets(conn, klass="gate", tag="OPEN")) == 0


# --- harvest_thaiwater_waterlevel (nationwide HII telemetry, added 2026-09-27) ----------

def test_harvest_thaiwater_waterlevel_nationwide(tmp_path):
    data = {
        "data": [
            {
                "waterlevel_datetime": "2026-09-27 12:50",
                "agency": {"agency_name": {"th": "สสน.", "en": "HII"}},
                "basin": {"basin_name": {"th": "ลุ่มน้ำบางปะกง", "en": "Bang Pakong"}},
                "station": {
                    "id": 175, "tele_station_name": {"th": "สะพานเขานางบวช", "en": "x"},
                    "tele_station_lat": 14.245718, "tele_station_long": 101.27481,
                    "tele_station_oldcode": "NYK008",
                    "warning_level_m": None, "critical_level_m": None, "left_bank": 11.309,
                },
            },
            {
                # no coordinate -> must be skipped, never fabricated
                "waterlevel_datetime": "2026-09-27 12:50",
                "agency": {"agency_name": {"th": "สสน.", "en": "HII"}},
                "station": {"id": 999, "tele_station_name": {"th": "ไม่มีพิกัด"},
                            "tele_station_lat": None, "tele_station_long": None,
                            "tele_station_oldcode": "XXX001"},
            },
        ]
    }
    path = tmp_path / "waterlevel.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_thaiwater_waterlevel(path)
    assert len(rows) == 1
    r = rows[0]
    assert r["asset_id"] == "gauge:thaiwater_waterlevel:NYK008"
    assert r["class"] == "gauge"
    assert r["lat"] == 14.245718 and r["lon"] == 101.27481
    assert r["tag"] == "VERIFIED"
    assert r["coord_source_type"] == "official_api"
    assert "basin" in r["notes"]


def test_harvest_thaiwater_waterlevel_bbox_filter(tmp_path):
    """Same station shape as above, but a bbox that excludes it -- confirms the optional
    `bbox` kwarg behaves like harvest_rain_24h's (default None = nationwide, no filter)."""
    data = {"data": [{
        "waterlevel_datetime": "2026-09-27 12:50",
        "agency": {"agency_name": {"th": "สสน."}},
        "station": {"id": 1, "tele_station_name": {"th": "ทดสอบ"},
                    "tele_station_lat": 14.245718, "tele_station_long": 101.27481,
                    "tele_station_oldcode": "T01"},
    }]}
    path = tmp_path / "waterlevel.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert len(ar.harvest_thaiwater_waterlevel(path)) == 1
    assert len(ar.harvest_thaiwater_waterlevel(path, bbox=ar.BANGKOK_BBOX)) == 0


# --- harvest_rid_res_table (national large-dam names, no coordinates, added 2026-09-27) -

_RID_RES_TABLE_FIXTURE_HTML = """
<html><body>
<p style="margin:5px 0 10px 20px; color:#800;">ภาคเหนือ</p>
<ul style="margin-top:-10px; list-style-type:none;">
<li><a href="http://water.rid.go.th/x/p1.JPG" class="highslide">ภูมิพล</a></li>
<li><a href="http://water.rid.go.th/x/p2.JPG" class="highslide">สิริกิติ์</a></li>
</ul>
<p style="margin:-10px 0 10px 20px;color:#800;">ภาคใต้</p>
<ul style="margin-top:-10px; list-style-type:none">
<li><a href="http://water.rid.go.th/x/p3.JPG" class="highslide">รัชชประภา</a></li>
</ul>
</body></html>
"""


def test_harvest_rid_res_table_names_only_no_coordinate(tmp_path):
    path = tmp_path / "res_table.htm"
    path.write_bytes(_RID_RES_TABLE_FIXTURE_HTML.encode("cp874"))
    rows = ar.harvest_rid_res_table(path)
    assert len(rows) == 3
    names = {r["name_th"] for r in rows}
    assert names == {"ภูมิพล", "สิริกิติ์", "รัชชประภา"}
    for r in rows:
        assert r["class"] == "dam"
        assert r["tag"] == "OPEN"
        assert r["lat"] is None and r["lon"] is None
        assert r["owner"] == "กรมชลประทาน (RID)"
    by_name = {r["name_th"]: r for r in rows}
    assert "ภาคเหนือ" in by_name["ภูมิพล"]["notes"]
    assert "ภาคใต้" in by_name["รัชชประภา"]["notes"]


def test_harvest_rid_res_table_missing_file_returns_empty(tmp_path):
    assert ar.harvest_rid_res_table(tmp_path / "nope.htm") == []


# --- harvest_hii_dam (HII dam/reservoir census, added 2026-09-27) -----------------------

def _hii_dam_fixture():
    return {
        "data": {
            "dam_hourly": [{
                "station_type": "dam_hourly",
                "dam": {"id": 1, "dam_oldcode": "1", "dam_name": {"th": "ทดสอบใหญ่"},
                        "dam_lat": 17.24, "dam_long": 98.97},
                "agency": {"agency_name": {"th": "กรมชลประทาน", "en": "RID"}},
                "geocode": {"province_name": {"th": "ตาก"}},
                "basin": {"basin_name": {"th": "ลุ่มน้ำปิง"}},
            }],
            "dam_medium": [
                {
                    "dam": {"id": 700, "dam_name": {"th": "อ่างกลางทดสอบ"},
                            "dam_lat": 17.4, "dam_long": 104.4},
                    "agency": {"agency_name": {"th": "กรมชลประทาน"}},
                    "geocode": {"province_name": {"th": "สกลนคร"}},
                },
                {
                    # no coordinate -> must be OPEN, never geocoded
                    "dam": {"id": 701, "dam_name": {"th": "อ่างไม่มีพิกัด"},
                            "dam_lat": None, "dam_long": None},
                    "agency": {"agency_name": {"th": "กรมชลประทาน"}},
                },
            ],
            "dam_daily": [],
            "dam_small_tele": [{
                "dam": {"id": 900, "smalldam_name": {"th": "อ่างเล็กทดสอบ"},
                        "tele_station_lat": 17.77, "tele_station_long": 99.41},
                "agency": {"agency_name": {"th": "สสน."}},
                "geocode": {"province_name": {"th": "แพร่"}},
            }],
        }
    }


def test_harvest_hii_dam_classes_and_counts(tmp_path):
    path = tmp_path / "dam.json"
    path.write_text(json.dumps(_hii_dam_fixture()), encoding="utf-8")
    rows = ar.harvest_hii_dam(path)
    assert len(rows) == 4
    by_id = {r["asset_id"]: r for r in rows}
    assert by_id["dam:hii_dam:1"]["class"] == "dam"
    assert by_id["dam:hii_dam:1"]["tag"] == "VERIFIED"
    assert by_id["reservoir_medium:hii_dam:700"]["class"] == "reservoir_medium"
    assert by_id["reservoir_medium:hii_dam:700"]["tag"] == "VERIFIED"
    assert by_id["reservoir_small:hii_dam:900"]["class"] == "reservoir_small"
    assert by_id["reservoir_small:hii_dam:900"]["tag"] == "VERIFIED"
    # no-coordinate row stays OPEN -- never upgraded/geocoded
    open_row = by_id["reservoir_medium:hii_dam:701"]
    assert open_row["tag"] == "OPEN"
    assert open_row["lat"] is None and open_row["lon"] is None
    for r in rows:
        if r["lat"] is not None:
            assert ar.THAILAND_BBOX["lat_min"] <= r["lat"] <= ar.THAILAND_BBOX["lat_max"]
            assert ar.THAILAND_BBOX["lon_min"] <= r["lon"] <= ar.THAILAND_BBOX["lon_max"]


def test_harvest_hii_dam_rejects_implausible_coordinate(tmp_path):
    """A coordinate outside Thailand (or the (0,0) sentinel) must never be stored as
    VERIFIED -- downgraded to OPEN instead of being silently accepted or corrected."""
    data = {"data": {"dam_hourly": [{
        "dam": {"id": 2, "dam_oldcode": "2", "dam_name": {"th": "ทดสอบพิกัดเพี้ยน"},
                "dam_lat": 118.5, "dam_long": 100.8},
        "agency": {"agency_name": {"th": "กรมชลประทาน"}},
    }], "dam_medium": [], "dam_daily": [], "dam_small_tele": []}}
    path = tmp_path / "dam.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_hii_dam(path)
    assert len(rows) == 1
    assert rows[0]["tag"] == "OPEN"
    assert rows[0]["lat"] is None and rows[0]["lon"] is None


def test_merge_hii_dam_into_rid_res_table_fills_coords():
    rid_dam_rows = [{
        "asset_id": "dam:rid_res_table:สียัด", "class": "dam", "name_th": "สียัด",
        "lat": None, "lon": None, "tag": "OPEN", "notes": "RID region: ภาคตะวันออก",
        "coord_source": None, "coord_source_type": "none",
        "owner": "กรมชลประทาน (RID)",
    }, {
        "asset_id": "dam:rid_res_table:ไม่มีคู่", "class": "dam", "name_th": "ไม่มีคู่",
        "lat": None, "lon": None, "tag": "OPEN", "notes": "RID region: ภาคใต้",
        "coord_source": None, "coord_source_type": "none",
        "owner": "กรมชลประทาน (RID)",
    }]
    hii_dam_rows = [{
        "asset_id": "dam:hii_dam:30", "class": "dam", "name_th": "คลองสียัด",
        "lat": 13.43, "lon": 101.65, "tag": "VERIFIED",
        "coord_source": "raw/live/hii_dam", "coord_source_type": "official_api",
        "owner": "กรมชลประทาน",
    }]
    still_open = []
    merged = ar._merge_hii_dam_into_rid_res_table(hii_dam_rows, rid_dam_rows, still_open)
    by_id = {r["asset_id"]: r for r in merged}
    filled = by_id["dam:rid_res_table:สียัด"]
    assert filled["tag"] == "VERIFIED"
    assert filled["lat"] == 13.43 and filled["lon"] == 101.65
    assert "coords from hii_dam" in filled["notes"]
    still_open_row = by_id["dam:rid_res_table:ไม่มีคู่"]
    assert still_open_row["tag"] == "OPEN"
    assert still_open_row["lat"] is None
    assert still_open == ["ไม่มีคู่"]


# --- harvest_hii_watergate (HII watergate_data census, added 2026-09-27) ----------------

def _hii_watergate_fixture():
    return {"watergate_data": {"data": [
        {
            "watergate_in": 17.4, "watergate_out": 16.3,
            "agency": {"agency_name": {"th": "สสน."}},
            "basin": {"basin_name": {"th": "ลุ่มน้ำเจ้าพระยา"}},
            "geocode": {"province_name": {"th": "ชัยนาท"}},
            "station": {"id": 1, "tele_station_name": {"th": "ปตร.ทดสอบ"},
                        "tele_station_lat": 15.2, "tele_station_long": 100.07,
                        "tele_station_oldcode": "ATG011"},
        },
        {
            "agency": {"agency_name": {"th": "สสน."}},
            "geocode": {"province_name": {"th": "พะเยา"}},
            "station": {"id": 2, "tele_station_name": {"th": "ฝายทดสอบ"},
                        "tele_station_lat": 19.35, "tele_station_long": 99.82,
                        "tele_station_oldcode": "PYO002"},
        },
        {
            "agency": {"agency_name": {"th": "สสน."}},
            "station": {"id": 3, "tele_station_name": {"th": "สถานีสูบน้ำทดสอบ"},
                        "tele_station_lat": 13.7, "tele_station_long": 100.5,
                        "tele_station_oldcode": "PMP001"},
        },
        {
            # no coordinate -> must be OPEN, never geocoded
            "agency": {"agency_name": {"th": "สสน."}},
            "station": {"id": 4, "tele_station_name": {"th": "ไม่มีพิกัด"},
                        "tele_station_lat": None, "tele_station_long": None,
                        "tele_station_oldcode": "NOCOORD"},
        },
        {
            # sentinel (0, 0) -> must be OPEN, never a real coordinate
            "agency": {"agency_name": {"th": "สสน."}},
            "station": {"id": 5, "tele_station_name": {"th": "พิกัดศูนย์"},
                        "tele_station_lat": 0, "tele_station_long": 0,
                        "tele_station_oldcode": "ZERO001"},
        },
    ]}}


def test_harvest_hii_watergate_classifies_and_tags(tmp_path):
    path = tmp_path / "watergate.json"
    path.write_text(json.dumps(_hii_watergate_fixture()), encoding="utf-8")
    rows = ar.harvest_hii_watergate(path)
    assert len(rows) == 5
    # source_code is keyed on station.id (unique across the whole feed), not the
    # oldcode -- oldcode was found reused across two different stations/agencies in
    # the real 2026-09-27 payload (see harvest_hii_watergate docstring)
    by_code = {r["source_code"]: r for r in rows}
    assert by_code["1"]["class"] == "gate" and by_code["1"]["tag"] == "VERIFIED"
    assert "ATG011" in by_code["1"]["notes"]
    assert by_code["2"]["class"] == "weir" and by_code["2"]["tag"] == "VERIFIED"
    assert by_code["3"]["class"] == "pump_station" and by_code["3"]["tag"] == "VERIFIED"
    # no-coordinate and sentinel-(0,0) rows both stay OPEN -- never upgraded/geocoded
    assert by_code["4"]["tag"] == "OPEN"
    assert by_code["4"]["lat"] is None
    assert by_code["5"]["tag"] == "OPEN"
    assert by_code["5"]["lat"] is None
    for r in rows:
        if r["lat"] is not None:
            assert ar.THAILAND_BBOX["lat_min"] <= r["lat"] <= ar.THAILAND_BBOX["lat_max"]
            assert ar.THAILAND_BBOX["lon_min"] <= r["lon"] <= ar.THAILAND_BBOX["lon_max"]


def test_harvest_hii_watergate_missing_file_returns_empty(tmp_path):
    assert ar.harvest_hii_watergate(tmp_path / "nope.json") == []


def test_harvest_hii_watergate_oldcode_reuse_does_not_collapse_stations(tmp_path):
    """Real finding in the 2026-09-27 payload: oldcode "E21" is reused by two entirely
    different stations from two different agencies (~370 km apart). Keying the asset
    code on the oldcode would upsert one on top of the other -- this asserts both
    survive as distinct rows, keyed on the unique station.id instead."""
    data = {"watergate_data": {"data": [
        {"agency": {"agency_name": {"th": "กรมชลประทาน"}},
         "station": {"id": 417156, "tele_station_name": {"th": "แม่น้ำชี"},
                     "tele_station_lat": 15.75296, "tele_station_long": 102.252889,
                     "tele_station_oldcode": "E21"}},
        {"agency": {"agency_name": {"th": "สนน."}},
         "station": {"id": 960, "tele_station_name": {"th": "ประตูระบายน้ำทดสอบ"},
                     "tele_station_lat": 13.723837, "tele_station_long": 100.749754,
                     "tele_station_oldcode": "E21"}},
    ]}}
    path = tmp_path / "watergate.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_hii_watergate(path)
    assert len(rows) == 2
    assert len({r["asset_id"] for r in rows}) == 2


def test_harvest_hii_watergate_skips_placeholder_rows_with_zero_id(tmp_path):
    """station.id == 0, with no name/oldcode/coordinate, is a placeholder census
    entry (139 of 2,315 rows in the real 2026-09-27 payload) -- never stored as a
    fake asset."""
    data = {"watergate_data": {"data": [
        {"agency": {}, "station": {"id": 0}},
        {"agency": {"agency_name": {"th": "สสน."}},
         "station": {"id": 1, "tele_station_name": {"th": "ทดสอบ"},
                     "tele_station_lat": 13.7, "tele_station_long": 100.6}},
    ]}}
    path = tmp_path / "watergate.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_hii_watergate(path)
    assert len(rows) == 1
    assert rows[0]["source_code"] == "1"


def test_merge_hii_watergate_gates_keeps_existing_row_on_close_match():
    existing = [{
        "asset_id": "gate:thaiwater_bma:WL.TST.01", "class": "gate", "name_th": "ปตร.ทดสอบ",
        "lat": 15.2001, "lon": 100.0701, "tag": "VERIFIED", "notes": None,
    }]
    hii_gate_rows = [{
        "asset_id": "gate:hii_watergate:ATG011", "class": "gate", "name_th": "ปตร.ทดสอบ",
        "source_code": "ATG011", "lat": 15.2, "lon": 100.07, "tag": "VERIFIED", "notes": None,
    }]
    new_rows = ar._merge_hii_watergate_gates(hii_gate_rows, existing)
    assert new_rows == []  # merged into the existing row, not duplicated
    assert "HII watergate_data" in existing[0]["notes"]
    assert "ATG011" in existing[0]["notes"]


def test_merge_hii_watergate_gates_inserts_new_row_when_no_match():
    existing = [{
        "asset_id": "gate:thaiwater_bma:WL.TST.01", "class": "gate", "name_th": "ปตร.อื่น",
        "lat": 15.2001, "lon": 100.0701, "tag": "VERIFIED", "notes": None,
    }]
    hii_gate_rows = [{
        "asset_id": "gate:hii_watergate:ATG011", "class": "gate", "name_th": "ปตร.ทดสอบ",
        "source_code": "ATG011", "lat": 15.2, "lon": 100.07, "tag": "VERIFIED", "notes": None,
    }]
    new_rows = ar._merge_hii_watergate_gates(hii_gate_rows, existing)
    assert len(new_rows) == 1
    assert new_rows[0]["asset_id"] == "gate:hii_watergate:ATG011"


def test_normalize_dam_name_strips_common_prefixes_and_thanthakhat():
    assert ar._normalize_dam_name("คลองสียัด") == ar._normalize_dam_name("สียัด")
    assert ar._normalize_dam_name("วชิราลงกรณ์") == ar._normalize_dam_name("วชิราลงกรณ")


# --- full build() against real repo caches ----------------------------------------------

def test_build_runs_against_real_repo_caches_and_produces_assets(tmp_path, monkeypatch):
    """Integration-style smoke test: build() reads THIS repo's real raw/ caches (no
    network -- cache-first). raw/live/ is gitignored (not guaranteed present on a fresh
    clone/CI runner -- see .gitignore), so this test skips cleanly with an explicit
    reason rather than failing or fabricating data when those caches are absent or too
    thin to produce the expected asset count."""
    if not ar.RAW_LIVE_DIR.is_dir() or not any(ar.RAW_LIVE_DIR.iterdir()):
        pytest.skip("raw/live/ caches absent (gitignored, not present on a fresh clone)")
    # Skip on MISSING INPUT only, never on thin output -- the three sources that drive
    # the bulk of build()'s row count (bma gates, nationwide rain gauges, waterlevel
    # stations). If these are present, the >100 assertion below is a hard failure, not
    # a skip, so a real regression in build() can't hide behind "cache too thin".
    required_sources = {
        "thaiwater_bma": ar._freshest_cache_file(ar.RAW_LIVE_DIR / "thaiwater_bma", "*.json"),
        "thaiwater_rain_24h": ar._freshest_cache_file(ar.RAW_LIVE_DIR / "thaiwater_rain_24h", "*.json"),
        "thaiwater_waterlevel": ar._freshest_cache_file(ar.RAW_LIVE_DIR / "thaiwater_waterlevel", "*.json"),
    }
    missing = [name for name, path in required_sources.items() if path is None]
    if missing:
        pytest.skip(
            f"required raw/live source(s) missing: {missing} -- gitignored, not "
            "guaranteed present on a fresh clone/CI runner"
        )
    db_path = tmp_path / "assets.sqlite"
    monkeypatch.setattr(ar, "YAML_DUMP_PATH", tmp_path / "assets_registry.dump.yaml")
    stats = ar.build(db_path=db_path)
    assert stats["total_assets_in_db"] > 100, (
        f"total_assets_in_db={stats['total_assets_in_db']} with all required inputs "
        "present -- this is a build() regression, not a thin-cache skip"
    )
    assert ar.YAML_DUMP_PATH.exists()
    conn = store.connect(db_path)
    gates = store.query_assets(conn, klass="gate")
    assert any(g["tag"] == "VERIFIED" for g in gates)


def test_stats_cmd_and_near_cmd_smoke(tmp_path, capsys):
    db_path = tmp_path / "assets.sqlite"
    conn = store.connect(db_path)
    store.ensure_assets_schema(conn)
    store.upsert_asset(conn, asset_id="gate:1", klass="gate", tag="VERIFIED",
                        lat=13.758235, lon=100.676084, name_th="near point")
    store.upsert_asset(conn, asset_id="gate:2", klass="gate", tag="OPEN")

    class Args:
        klass = None
        tag = None
        owner = None
    ar.cmd_stats(Args(), conn)
    out = capsys.readouterr().out
    assert "total assets: 2" in out

    class NearArgs:
        lat = 13.758235
        lon = 100.676084
        km = 3.0
    ar.cmd_near(NearArgs(), conn)
    out2 = capsys.readouterr().out
    assert "gate:1" in out2
    assert "gate:2" not in out2  # no coordinate -> excluded from near()


# --- new classes added 2026-09-27 (founder ask: retention basins, tunnels, levees,
# tide gates, nationwide rain gauges, 22 basins) -------------------------------------

def test_harvest_rain_gauge_nationwide_no_bbox_filter(tmp_path):
    data = {
        "data": [
            {   # inside Bangkok bbox
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "geocode": {"province_name": {"th": "กรุงเทพมหานคร"}},
                "station": {"id": 100, "tele_station_name": {"th": "ในกรุงเทพ"},
                            "tele_station_lat": 13.75, "tele_station_long": 100.6,
                            "tele_station_oldcode": "RF.IN.01"},
            },
            {   # far outside Bangkok bbox -- must still be included (nationwide)
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "geocode": {"province_name": {"th": "เชียงใหม่"}},
                "station": {"id": 101, "tele_station_name": {"th": "เชียงใหม่"},
                            "tele_station_lat": 18.79, "tele_station_long": 98.98,
                            "tele_station_oldcode": "RF.CM.01"},
            },
            {   # no coordinate -> skipped, never fabricated
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "station": {"id": 102, "tele_station_name": {"th": "ไม่มีพิกัด"},
                            "tele_station_lat": None, "tele_station_long": None},
            },
            {   # implausible sentinel coordinate -> rejected by _valid_th_coord
                "agency": {"agency_name": {"th": "อต.", "en": "TMD"}},
                "station": {"id": 103, "tele_station_name": {"th": "พิกัดผิด"},
                            "tele_station_lat": 0, "tele_station_long": 0},
            },
        ]
    }
    path = tmp_path / "rain_nationwide.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = ar.harvest_rain_gauge_nationwide(path)
    ids = {r["asset_id"] for r in rows}
    assert ids == {"rain_gauge:thaiwater_rain_24h:100", "rain_gauge:thaiwater_rain_24h:101"}
    for r in rows:
        assert r["class"] == "rain_gauge"
        assert r["tag"] == "VERIFIED"


def test_harvest_basins_excludes_unspecified_and_foreign_codes(tmp_path):
    rain = {
        "data": [
            {"basin": {"basin_code": 10, "basin_name": {"th": "ลุ่มน้ำเจ้าพระยา"}},
             "station": {"id": 1, "tele_station_lat": 13.7, "tele_station_long": 100.6},
             "agency": {"agency_name": {"th": "อต."}}},
            {"basin": {"basin_code": 99, "basin_name": {"th": "ไม่ระบุ"}},
             "station": {"id": 2, "tele_station_lat": 13.7, "tele_station_long": 100.6},
             "agency": {"agency_name": {"th": "อต."}}},
        ]
    }
    watergate = {
        "watergate_data": {
            "data": [
                {"basin": {"basin_code": 15, "basin_name": {"th": "ลุ่มน้ำบางปะกง"}},
                 "station": {"id": 5}, "agency": {"agency_name": {"th": "x"}}},
                {"basin": {"basin_code": 88, "basin_name": {"th": "นอกประเทศไทย"}},
                 "station": {"id": 6}, "agency": {"agency_name": {"th": "x"}}},
            ]
        }
    }
    rain_path = tmp_path / "rain.json"
    rain_path.write_text(json.dumps(rain), encoding="utf-8")
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(json.dumps(watergate), encoding="utf-8")

    rows = ar.harvest_basins([rain_path, gate_path])
    codes = {r["source_code"] for r in rows}
    assert codes == {"10", "15"}
    for r in rows:
        assert r["class"] == "basin"
        assert r["lat"] is None and r["lon"] is None
        assert r["tag"] == "VERIFIED"


def test_hand_declared_retention_basins_all_open_coords():
    rows = ar.hand_declared_retention_basins()
    assert len(rows) == 14  # 12 named ทุ่ง + 2 aggregate east/west schemes
    names = {r["name_th"] for r in rows}
    assert "ทุ่งเชียงราก" in names
    assert "ทุ่งรังสิตใต้" in names
    for r in rows:
        assert r["class"] == "retention_basin"
        assert r["lat"] is None and r["lon"] is None
        assert r["tag"] == "RELAYED"


def test_hand_declared_tunnels_bma_dds_thirteen_new_rows():
    rows = ar.hand_declared_tunnels_bma_dds()
    assert len(rows) == 12  # 6 operating (excluding the pre-existing rama9 duplicate) + 6 planned
    for r in rows:
        assert r["class"] == "tunnel"
        assert r["tag"] == "OPEN"
        assert r["lat"] is None and r["lon"] is None
    ids = {r["asset_id"] for r in rows}
    assert "tunnel:bma_dds:bangsue" in ids
    assert "tunnel:bma_dds:sukhumvit26" in ids
    # the Bung Makkasan / Rama9-Ramkhamhaeng tunnel is NOT duplicated here
    assert not any("makkasan" in i or "rama9" in i for i in ids)


def test_hand_declared_levees_diversion_tide_gates():
    levees = ar.hand_declared_levees()
    assert len(levees) == 2
    assert all(r["class"] == "levee" and r["tag"] == "OPEN" for r in levees)

    diversions = ar.hand_declared_diversion_channels()
    assert len(diversions) == 3
    assert all(r["class"] == "diversion_channel" and r["tag"] == "OPEN" for r in diversions)
    assert any("DIV002" in (r["notes"] or "") for r in diversions)

    tide_gates = ar.hand_declared_tide_gates()
    assert len(tide_gates) == 1
    assert tide_gates[0]["class"] == "tide_gate"
    assert tide_gates[0]["tag"] == "RELAYED"


def test_build_wires_new_classes_end_to_end(tmp_path, monkeypatch):
    """build() should include all 6 new classes without crashing, even when only a
    minimal rain_24h fixture is present (the other hand-declared sources need no
    file)."""
    live_dir = tmp_path / "raw" / "live"
    (live_dir / "thaiwater_rain_24h").mkdir(parents=True)
    rain_data = {
        "data": [
            {"agency": {"agency_name": {"th": "อต."}},
             "basin": {"basin_code": 10, "basin_name": {"th": "ลุ่มน้ำเจ้าพระยา"}},
             "station": {"id": 1, "tele_station_name": {"th": "ทดสอบ"},
                         "tele_station_lat": 13.7, "tele_station_long": 100.6,
                         "tele_station_oldcode": "RF.T.01"}},
        ]
    }
    (live_dir / "thaiwater_rain_24h" / "2026-09-27T000000Z.json").write_text(
        json.dumps(rain_data), encoding="utf-8")

    monkeypatch.setattr(ar, "RAW_LIVE_DIR", live_dir)
    monkeypatch.setattr(ar, "RAW_GAPFILL_DIR", tmp_path / "raw" / "gapfill")
    monkeypatch.setattr(ar, "CONTROL_STRUCTURES_YAML", tmp_path / "no_such_file.yaml")
    monkeypatch.setattr(ar, "YAML_DUMP_PATH", tmp_path / "dump.yaml")

    db_path = tmp_path / "assets.sqlite"
    stats = ar.build(db_path=db_path, quiet=True)
    assert stats["rain_gauge_rows_nationwide"] == 1
    assert stats["basin_rows"] == 1
    assert stats["retention_basin_rows"] == 14
    assert stats["bma_tunnel_rows_new"] == 12
    assert stats["levee_rows"] == 2
    assert stats["diversion_channel_rows"] == 3
    assert stats["tide_gate_rows"] == 1

    conn = store.connect(db_path)
    assert len(store.query_assets(conn, klass="retention_basin")) == 14
    assert len(store.query_assets(conn, klass="tunnel")) == 12 + 1  # + pre-existing rama9 row
    assert len(store.query_assets(conn, klass="rain_gauge")) == 1
    assert len(store.query_assets(conn, klass="basin")) == 1
