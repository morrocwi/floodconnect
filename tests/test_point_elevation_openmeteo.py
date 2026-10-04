"""Tests for tools/harvest/point_elevation_openmeteo.py's pure parse function. No
network -- uses the real 7-point sample this check's probe captured
(tests/fixtures/openmeteo_elevation_sample.json)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
from tools.harvest import point_elevation_openmeteo as peo  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_elevation_matches_probe_sample():
    data = json.loads((FIXTURES / "openmeteo_elevation_sample.json").read_text())
    point_ids = ["p0", "p1", "p2", "p3", "p4", "p5", "p6"]
    out = peo.parse_elevation(data, point_ids)
    assert out == {"p0": 4.0, "p1": 4.0, "p2": 1.0, "p3": 2.0, "p4": 3.0, "p5": 6.0, "p6": 4.0}


def test_parse_elevation_drops_points_beyond_array_length():
    data = {"elevation": [4.0, 5.0]}
    out = peo.parse_elevation(data, ["a", "b", "c"])
    assert out == {"a": 4.0, "b": 5.0}


def test_elevation_url_is_one_comma_separated_request():
    url = peo.elevation_url({"a": (13.0, 100.0), "b": (14.0, 101.0)})
    assert url.count("latitude=") == 1
    assert "13.0,14.0" in url and "100.0,101.0" in url
