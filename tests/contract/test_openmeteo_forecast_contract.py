"""Contract test for sources/registry.yaml's `openmeteo_forecast` entry.

Replays a real response captured 2026-10-02T07:20:27Z (single GET, lat/lon=13.7563/
100.5018, see fixtures/openmeteo_forecast_captured.sidecar.json) through the real
parser -- never a hand-built payload."""
import parsers
from tests.contract.conftest import load_captured


def test_captured_response_parses_into_hourly_rows():
    data, sidecar = load_captured("openmeteo_forecast")
    assert sidecar["url"].startswith("https://api.open-meteo.com/v1/forecast")
    rows = parsers.parse_openmeteo_forecast(data)
    assert isinstance(rows, list)
    assert len(rows) > 0
    for row in rows:
        assert "time_local" in row
        assert "mm" in row
        assert isinstance(row["mm"], float)
