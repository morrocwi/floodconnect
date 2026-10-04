"""Tests for tools/harvest/hii_station_geocode.py -- small synthetic fixtures only
(no network, no dependency on the gitignored raw/live/ tree). Mirrors the real HII
payload shapes (checked against raw/live/ during development, not guessed)."""
import json

from tools.harvest import hii_station_geocode as geo


def _waterlevel_payload(oldcode="X.1", province_code="13", amphoe_code="01"):
    return {"data": [{
        "station": {"id": 1, "tele_station_oldcode": oldcode},
        "geocode": {
            "province_code": province_code, "province_name": {"th": "ปทุมธานี"},
            "amphoe_code": amphoe_code, "amphoe_name": {"th": "เมืองปทุมธานี"},
            "tumbon_name": {"th": "บางปรอก"},
        },
        "river_name": "แม่น้ำเจ้าพระยา",
    }]}


def test_collect_waterlevel_keys_by_oldcode(tmp_path):
    d = tmp_path / "thaiwater_waterlevel"
    d.mkdir()
    (d / "a.json").write_text(json.dumps(_waterlevel_payload()), encoding="utf-8")
    rows = geo._collect_waterlevel(tmp_path)
    assert len(rows) == 1
    assert rows[0]["asset_id"] == "gauge:thaiwater_waterlevel:X.1"
    assert rows[0]["province_code"] == "13"
    assert rows[0]["amphoe_name_th"] == "เมืองปทุมธานี"
    assert rows[0]["tag"] == "VERIFIED"


def test_collect_dam_keys_by_nested_dam_id(tmp_path):
    d = tmp_path / "hii_dam"
    d.mkdir()
    payload = {"data": {"dam_hourly": [{
        "id": 999999,  # outer per-reading id -- must NOT be used as the code
        "dam": {"id": 12, "dam_name": {"th": "สิริกิติ์"}},
        "geocode": {"province_code": "53", "province_name": {"th": "อุตรดิตถ์"}},
    }]}}
    (d / "a.json").write_text(json.dumps(payload), encoding="utf-8")
    rows = geo._collect_dam(tmp_path)
    assert len(rows) == 1
    assert rows[0]["asset_id"] == "hii_dam:dam:12"


def test_collect_watergate_keys_by_station_id_not_oldcode(tmp_path):
    d = tmp_path / "hii_watergate"
    d.mkdir()
    payload = {"watergate_data": {"data": [{
        "station": {"id": 492316, "tele_station_oldcode": "ATG011"},
        "geocode": {"province_code": "18", "province_name": {"th": "ชัยนาท"}},
    }]}}
    (d / "a.json").write_text(json.dumps(payload), encoding="utf-8")
    rows = geo._collect_watergate(tmp_path)
    assert len(rows) == 1
    assert rows[0]["asset_id"] == "hii_watergate:station:492316"


def test_merge_keeps_both_on_disagreement_never_prefers():
    rows = [
        {"asset_id": "gauge:x:1", "province_code": "10", "amphoe_code": "01",
         "river_name": None, "tag": "VERIFIED", "source": "a"},
        {"asset_id": "gauge:x:1", "province_code": "99", "amphoe_code": "01",
         "river_name": None, "tag": "VERIFIED", "source": "b"},
    ]
    by_id, contradictions = geo.merge(rows)
    assert len(by_id) == 1
    assert len(contradictions) == 1
    assert contradictions[0]["asset_id"] == "gauge:x:1"
    # the kept row is not silently rewritten to either variant's province_code in a
    # way that hides the disagreement -- the contradiction row carries both
    assert contradictions[0]["variant_a"]["province_code"] in ("10", "99")
    assert contradictions[0]["variant_b"]["province_code"] in ("10", "99")


def test_merge_backfills_missing_fields_without_conflict():
    rows = [
        {"asset_id": "gauge:x:2", "province_code": "10", "amphoe_code": None,
         "river_name": None, "tag": "VERIFIED", "source": "a"},
        {"asset_id": "gauge:x:2", "province_code": "10", "amphoe_code": "05",
         "river_name": None, "tag": "VERIFIED", "source": "b"},
    ]
    by_id, contradictions = geo.merge(rows)
    assert len(contradictions) == 0
    assert by_id["gauge:x:2"]["amphoe_code"] == "05"


def test_main_skips_cleanly_when_raw_dir_missing(tmp_path, capsys):
    geo.main.__wrapped__ if hasattr(geo.main, "__wrapped__") else None
    import argparse
    import sys
    missing = tmp_path / "does-not-exist"
    old_argv = sys.argv
    try:
        sys.argv = ["hii_station_geocode", "--raw-dir", str(missing),
                    "--out", str(tmp_path / "out.yaml")]
        geo.main()
    finally:
        sys.argv = old_argv
    assert not (tmp_path / "out.yaml").exists()
