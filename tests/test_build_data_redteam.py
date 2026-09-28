"""Red-team fixes 2026-09-26 -- tests for site/build_data.py's DDS PDF path resolution
and rain source resolution. No network calls."""
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402

_KHLONGCHAN_SAMPLE = """\
# sample
| เวลาโพสต์ (≈) | แหล่ง | จุด | สภาพ |
|---|---|---|---|
| ~10:00 (6 ชม.) | Facebook (บุคคล) | แฟลตคลองจั่น | "ฝนตกไม่หยุด" |
| ~11:00 (5 ชม.) | สวพ.FM91 | แฟลตเคหะคลองจั่น | น้ำท่วมสูงถึงหลังคารถ |
| ~12:00 (4 ชม.) | PPTV HD 36 / ข่าว | แฟลตเคหะคลองจั่น | น้ำสูงถึงอก |
| ~13:00 (3 ชม.) | Facebook (เพจ) | แฟลตเคหะคลองจั่น | ยังไม่ลด |
"""


def test_dds_pdf_prefers_raw_live_over_dds_reports(tmp_path, monkeypatch):
    # HIGH-2: collect.py writes to raw/live/dds_daily_pdf/, but build_data.py used to
    # only ever look in raw/dds_reports/ (a manual/legacy drop location) -- the two paths
    # had silently diverged. raw/live/dds_daily_pdf/ must win when both exist.
    monkeypatch.setattr(bd, "RAW", tmp_path)
    legacy_dir = tmp_path / "dds_reports"
    legacy_dir.mkdir()
    legacy_pdf = legacy_dir / "dds_daily_20260101T0000Z.pdf"
    legacy_pdf.write_bytes(b"%PDF-1.4 legacy")

    live_dir = tmp_path / "live" / "dds_daily_pdf"
    live_dir.mkdir(parents=True)
    live_pdf = live_dir / "2026-09-26T043700Z.pdf"
    live_pdf.write_bytes(b"%PDF-1.4 live")

    rows, meta, pdf_path = bd.build_dds_quotes([])
    assert pdf_path == live_pdf


def test_dds_pdf_falls_back_to_dds_reports_when_no_live_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "RAW", tmp_path)
    legacy_dir = tmp_path / "dds_reports"
    legacy_dir.mkdir()
    legacy_pdf = legacy_dir / "dds_daily_20260101T0000Z.pdf"
    legacy_pdf.write_bytes(b"%PDF-1.4 legacy")

    rows, meta, pdf_path = bd.build_dds_quotes([])
    assert pdf_path == legacy_pdf


def test_dds_pdf_none_when_neither_location_has_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "RAW", tmp_path)
    rows, meta, pdf_path = bd.build_dds_quotes([])
    assert pdf_path is None
    assert rows == []
    assert meta is None


def test_load_rain_prefers_live_thaiwater_snapshot_over_gapfill(tmp_path, monkeypatch):
    # HIGH-3: raw/live/thaiwater_rain_24h/ (the new CI collector) must win over the
    # one-time manual raw/gapfill/rain_24h*.json snapshot when both exist.
    import json
    monkeypatch.setattr(bd, "RAW", tmp_path)

    gapfill_dir = tmp_path / "gapfill"
    gapfill_dir.mkdir()
    (gapfill_dir / "rain_24h_1.json").write_text(json.dumps({"data": [
        {"station": {"tele_station_lat": 13.7, "tele_station_long": 100.6,
                      "tele_station_name": {"th": "gapfill station"}},
         "rain_24h": 1.0, "rainfall_datetime": "2026-01-01 00:00",
         "agency": {"agency_name": {"th": "gapfill agency"}}}
    ]}), encoding="utf-8")

    live_dir = tmp_path / "live" / "thaiwater_rain_24h"
    live_dir.mkdir(parents=True)
    (live_dir / "2026-09-26T050000Z.json").write_text(json.dumps({"data": [
        {"station": {"tele_station_lat": 13.7, "tele_station_long": 100.6,
                      "tele_station_name": {"th": "live station"}},
         "rain_24h": 42.0, "rainfall_datetime": "2026-09-26 05:00",
         "agency": {"agency_name": {"th": "live agency"}}}
    ]}), encoding="utf-8")

    rain, path = bd.load_rain("2026-09-26T05:30:00+00:00", 13.7, 100.6)
    assert rain["station"] == "live station"
    assert rain["mm_24h"] == 42.0
    assert path == live_dir / "2026-09-26T050000Z.json"


def test_khlongchan_community_names_media_agency_not_person(tmp_path):
    p = tmp_path / "social_timeline_khlongchan_sample.md"
    p.write_text(_KHLONGCHAN_SAMPLE, encoding="utf-8")
    rows = bd.build_khlongchan_community(p)
    assert len(rows) == 4
    # a personal Facebook post/page is never named in the output
    assert "Facebook" not in rows[0]["state"]
    assert "Facebook" not in rows[3]["state"]
    # a named media outlet IS disclosed as the source
    assert "(สวพ.FM91)" in rows[1]["state"]
    assert "(PPTV HD 36)" in rows[2]["state"]  # " / ข่าว" suffix stripped


def test_khlongchan_community_missing_file_returns_empty():
    from pathlib import Path
    assert bd.build_khlongchan_community(Path("/nonexistent/path.md")) == []


# --- previous_reading (review MUST-FIX #1: trend arrows on every station/pump row) --------

def _make_obs_db(tmp_path, rows):
    import sqlite3
    db_path = tmp_path / "observations.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
        station_code TEXT, station_name TEXT, variable TEXT NOT NULL, value REAL,
        observed_at_utc TEXT NOT NULL, fetched_at_utc TEXT NOT NULL, trust_tier TEXT NOT NULL)""")
    for source_id, code, value, observed_at in rows:
        conn.execute(
            "INSERT INTO observations (source_id, station_code, variable, value, "
            "observed_at_utc, fetched_at_utc, trust_tier) VALUES (?, ?, 'x', ?, ?, ?, 'official')",
            (source_id, code, value, observed_at, observed_at))
    conn.commit()
    conn.close()
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def test_previous_reading_finds_reading_at_least_60min_older(tmp_path):
    conn = _make_obs_db(tmp_path, [
        ("thaiwater_canal_waterlevel", "WL.TEST.01", 1.00, "2026-09-27T00:00:00+00:00"),
        ("thaiwater_canal_waterlevel", "WL.TEST.01", 1.10, "2026-09-27T00:50:00+00:00"),
        ("thaiwater_canal_waterlevel", "WL.TEST.01", 1.30, "2026-09-27T02:00:00+00:00"),
    ])
    prev = bd.previous_reading(conn, "thaiwater_canal_waterlevel", "WL.TEST.01",
                                1.30, "2026-09-27T02:00:00+00:00")
    # the 00:50 reading is only 70 min older but the 00:00 one qualifies too -- the
    # MOST RECENT one at least 60 min older must win, i.e. 00:50 (70 min gap).
    assert prev["observed_at"] == "2026-09-27T00:50:00+00:00"
    assert prev["value"] == 1.10
    assert abs(prev["delta"] - 0.20) < 1e-9


def test_previous_reading_none_when_no_qualifying_row(tmp_path):
    conn = _make_obs_db(tmp_path, [
        ("thaiwater_canal_waterlevel", "WL.TEST.01", 1.30, "2026-09-27T01:50:00+00:00"),
    ])
    prev = bd.previous_reading(conn, "thaiwater_canal_waterlevel", "WL.TEST.01",
                                1.30, "2026-09-27T02:00:00+00:00")
    assert prev is None  # only candidate is 10 min old, below the 60-min gap


def test_previous_reading_none_when_db_missing():
    assert bd.previous_reading(None, "thaiwater_canal_waterlevel", "WL.TEST.01",
                                1.30, "2026-09-27T02:00:00+00:00") is None
