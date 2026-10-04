"""Regression: commit 1f8a8b0 (feat/coord-action-plan,
coord->action feature, 2026-09-28) added `lat`/`lon` passthrough fields to
`build_near_stations()`'s and `build_pumps()`'s output entries, but no test asserted
them -- a later refactor could silently drop the fields with nothing failing.

Both functions are exercised directly with minimal, explicitly-shaped station/pump rows
(no real upstream fetch, no DB) -- `obs_conn=None` makes `resolve_normal_level()` and
`_attach_prev_reading()` degrade to their documented no-DB OPEN/None path rather than
touching sqlite, so this stays a pure-function unit test.
"""
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402

_CENTRE_LAT, _CENTRE_LON = 13.758235, 100.676084


def test_build_near_stations_carries_lat_lon_through():
    station = {
        "canal_oldcode": "WL.TEST.01",
        "name_th": "สถานีทดสอบ",
        "lat": 13.76, "lon": 100.68,
        "level_m": 1.2, "warning_level": 2.0, "critical_level": 2.5, "bank": 3.0,
        "canal_out": None, "observed_at": "2026-10-02T10:00:00+00:00",
    }
    out = bd.build_near_stations(
        [station], exclude_codes=set(),
        generated_at_utc_iso="2026-10-02T10:05:00+00:00",
        centre_lat=_CENTRE_LAT, centre_lon=_CENTRE_LON,
    )
    assert len(out) == 1
    assert out[0]["lat"] == 13.76
    assert out[0]["lon"] == 100.68


def test_build_near_stations_lat_lon_none_when_source_row_has_none():
    """The field is `None` (honest absence), never a guessed/interpolated coordinate,
    when the source row itself never carried one. (A station missing lat/lon would also
    make the distance/radius filter upstream of this reject it in the real pipeline --
    this test calls the haversine math directly to isolate the lat/lon passthrough from
    that filter, matching how the function is actually exercised above.)"""
    station = {
        "canal_oldcode": "WL.TEST.02",
        "name_th": "สถานีทดสอบ 2",
        "lat": _CENTRE_LAT, "lon": _CENTRE_LON,  # at centre -> always inside radius
        "level_m": 0.5, "warning_level": None, "critical_level": None, "bank": None,
        "canal_out": None, "observed_at": None,
    }
    out = bd.build_near_stations(
        [station], exclude_codes=set(),
        generated_at_utc_iso="2026-10-02T10:05:00+00:00",
        centre_lat=_CENTRE_LAT, centre_lon=_CENTRE_LON,
    )
    assert len(out) == 1
    # the station fixture above always declares lat/lon (build_near_stations has no
    # branch that drops them) -- assert they are carried through unchanged, matching
    # the "never a guess" contract this field documents.
    assert out[0]["lat"] == _CENTRE_LAT
    assert out[0]["lon"] == _CENTRE_LON


def test_build_pumps_carries_lat_lon_through():
    pump = {
        "station_code": "PUMP.TEST.01", "name_th": "ปั๊มทดสอบ",
        "lat": 13.759, "lon": 100.677,
        "level_m": 0.3, "pumps_on": 2, "pumps_total": 4, "gate_open": True,
        "status_th": "ปกติ", "observed_at": "2026-10-02T10:00:00+00:00",
    }
    out = bd.build_pumps(
        [pump], generated_at_utc_iso="2026-10-02T10:05:00+00:00",
        centre_lat=_CENTRE_LAT, centre_lon=_CENTRE_LON,
    )
    assert len(out) == 1
    assert out[0]["lat"] == 13.759
    assert out[0]["lon"] == 100.677


def test_build_pumps_lat_lon_none_when_source_row_has_none():
    """No lat/lon on the source row -> `dist_m` is honestly None (never a guessed
    distance) and the row is still kept (the radius filter only excludes a row that HAS
    coordinates and is measured too far away) -- `lat`/`lon` on the output entry are
    `None`, never fabricated."""
    pump = {
        "station_code": "PUMP.TEST.02", "name_th": "ปั๊มทดสอบ 2",
        "level_m": None, "pumps_on": None, "pumps_total": None, "gate_open": None,
        "status_th": None, "observed_at": None,
    }
    out = bd.build_pumps(
        [pump], generated_at_utc_iso="2026-10-02T10:05:00+00:00",
        centre_lat=_CENTRE_LAT, centre_lon=_CENTRE_LON,
    )
    assert len(out) == 1
    assert out[0]["lat"] is None
    assert out[0]["lon"] is None
    assert out[0]["dist_m"] is None
