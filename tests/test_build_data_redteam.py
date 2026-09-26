"""Red-team fixes 2026-09-26 -- tests for site/build_data.py's DDS PDF path resolution
and rain source resolution. No network calls."""
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402


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
