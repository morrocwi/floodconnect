"""Contract tests for the two Bangkok Open Data CSV sources wired this check:
bangkok_floodgate_locations and bangkok_pump_station_and_floodgate_physical_data.
Real single-GET captures, replayed through their real parsers -- never a hand-built
payload, same discipline as test_hii_bma_gistda_sources.py.

Both files have quoted multi-line Thai-text cells, so the real row count only shows up
correctly through the stdlib `csv` module (the full captures confirmed this: 237 of
230-valid-coord / 438 of 429-valid-coord, vs an earlier wrong naive-line-count figure of
332 / 1,157). The real capture bodies are TRIMMED here (publish-safety finding,
2026-10-03: a 300KB total budget for this public tree's fixtures) to a 5-row real excerpt
each -- see each `*.sidecar.json`'s `trimmed_note` -- so these tests assert structurally
(a positive, small row count) rather than pinning the full-capture count, which this
excerpt deliberately no longer carries."""
import parsers
from tests.contract.conftest import load_captured


def test_bangkok_floodgate_locations_parses_real_row_count_and_coords():
    body, sidecar = load_captured("bangkok_floodgate_locations", binary=True)
    assert sidecar["url"].endswith("floodgate.csv")
    rows = parsers.parse_bangkok_floodgate_locations(body.decode("utf-8-sig"))
    assert isinstance(rows, list)
    # Trimmed excerpt (see module docstring) -- structural floor only, not the full
    # capture's 230-of-237 count.
    assert len(rows) >= 3
    for r in rows:
        assert 5.0 < r["lat"] < 20.0
        assert 95.0 < r["lon"] < 105.0
        assert r["id"]


def test_bangkok_pump_stations_parses_real_row_count_and_coords():
    body, sidecar = load_captured(
        "bangkok_pump_station_and_floodgate_physical_data", binary=True)
    assert sidecar["url"].endswith("-.csv")
    rows = parsers.parse_bangkok_pump_stations(body.decode("utf-8-sig"))
    assert isinstance(rows, list)
    # Trimmed excerpt (see module docstring) -- structural floor only, not the full
    # capture's 429-of-438 count.
    assert len(rows) >= 3
    for r in rows:
        assert 5.0 < r["lat"] < 20.0
        assert 95.0 < r["lon"] < 105.0
        assert r["id"]


def test_bangkok_pump_stations_keeps_composite_capacity_as_string():
    """A composite capacity cell (e.g. "35(3)+10(5)") must never be summed/guessed
    into a single number -- it stays the original string for provenance."""
    body, _sidecar = load_captured(
        "bangkok_pump_station_and_floodgate_physical_data", binary=True)
    rows = parsers.parse_bangkok_pump_stations(body.decode("utf-8-sig"))
    composite = [r for r in rows if isinstance(r["total_capacity"], str)]
    assert composite, "expected at least one composite (non-numeric) capacity cell"
