"""Contract test for sources/registry.yaml's `thaiwater_canal_waterlevel` entry.

Replays a real response captured 2026-10-02T07:20:27Z (single GET, no params, see
fixtures/thaiwater_canal_waterlevel_captured.sidecar.json) through the real parser --
never a hand-built payload."""
import live_water_level
from tests.contract.conftest import load_captured


def test_captured_response_parses_into_station_records():
    data, sidecar = load_captured("thaiwater_canal_waterlevel")
    assert sidecar["url"].endswith("canal_waterlevel")
    stations = live_water_level.parse_thaiwater_canal_stations(data)
    assert isinstance(stations, list)
    assert len(stations) > 0
    for s in stations:
        assert isinstance(s["lat"], float) and isinstance(s["lon"], float)
        assert isinstance(s["level_m"], float)
