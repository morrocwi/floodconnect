"""
tests/test_dwr_subbasin.py -- unit tests for tools/kg/unit_resolver.py using a tiny
synthetic fixture polygon (a tests/fixtures/dwr_subbasin/ geojson, NOT the real 359-feature
archive -- fast, deterministic, no dependency on the live archive being present).

Also exercises the real archive (raw/gis/dwr_subbasin/page_0.geojson) for the six named
points from this check's brief, SKIPPED if that archive is not present (e.g. a fresh clone
that has not run tools/harvest/dwr_subbasin.py yet -- raw/ is gitignored).
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
FIXTURE_DIR = HERE / "tests" / "fixtures" / "dwr_subbasin"
REAL_ARCHIVE = HERE / "raw" / "gis" / "dwr_subbasin"

sys.path.insert(0, str(HERE))


def _write_fixture():
    """A single square sub-basin (a 'unit square' around lon 100-101, lat 13-14) plus one
    feature with a hole, so both the shapely path and the documented pure-Python
    exterior-only limitation are exercised."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "SB_CODE": "TEST01",
                    "SB_NAME_T": "ทดสอบ",
                    "MB_CODE": "TT",
                    "MBASIN_T": "ลุ่มน้ำทดสอบ",
                    "MBASIN_E": "Test Basin",
                    "AREA_SQKM": 12345.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[100.0, 13.0], [101.0, 13.0], [101.0, 14.0], [100.0, 14.0], [100.0, 13.0]]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "SB_CODE": "TEST02",
                    "SB_NAME_T": "ทดสอบมีรู",
                    "MB_CODE": "TT",
                    "MBASIN_T": "ลุ่มน้ำทดสอบ",
                    "MBASIN_E": "Test Basin",
                    "AREA_SQKM": 999.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[110.0, 20.0], [112.0, 20.0], [112.0, 22.0], [110.0, 22.0], [110.0, 20.0]],
                        [[110.8, 20.8], [111.2, 20.8], [111.2, 21.2], [110.8, 21.2], [110.8, 20.8]],
                    ],
                },
            },
        ],
    }
    (FIXTURE_DIR / "page_0.geojson").write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture()
def resolver(monkeypatch):
    _write_fixture()
    from tools.kg import unit_resolver as mod
    monkeypatch.setattr(mod, "GEOJSON_DIR", FIXTURE_DIR)
    mod._load_pages.cache_clear()
    mod._load_shapely_index.cache_clear()
    yield mod
    mod._load_pages.cache_clear()
    mod._load_shapely_index.cache_clear()


def test_point_inside_fixture_square(resolver):
    r = resolver.resolve_unit(13.5, 100.5)
    assert r["sb_code"] == "TEST01"
    assert r["tag"] == "VERIFIED-from-DWR-service"
    assert r["basin_name_en"] == "Test Basin"


def test_point_outside_fixture_returns_open(resolver):
    r = resolver.resolve_unit(0.0, 0.0)
    assert r["sb_code"] is None
    assert r["tag"] == "OPEN"
    assert "reason" in r


def test_non_numeric_input_refuses(resolver):
    r = resolver.resolve_unit("not-a-number", 100.0)
    assert r["sb_code"] is None
    assert r["tag"] == "OPEN"


def test_out_of_world_range_refuses(resolver):
    r = resolver.resolve_unit(999.0, 100.0)
    assert r["sb_code"] is None
    assert r["tag"] == "OPEN"


def test_hole_polygon_shapely_excludes_hole(resolver):
    if not resolver._HAVE_SHAPELY:
        pytest.skip("shapely not installed -- pure-Python fallback does not subtract holes "
                    "(documented limitation), so this assertion only holds with shapely")
    inside_hole = resolver.resolve_unit(21.0, 111.0)
    assert inside_hole["sb_code"] is None
    outside_hole_inside_poly = resolver.resolve_unit(20.2, 110.2)
    assert outside_hole_inside_poly["sb_code"] == "TEST02"


@pytest.mark.skipif(not REAL_ARCHIVE.exists() or not any(REAL_ARCHIVE.glob("page_*.geojson")),
                     reason="real DWR archive not present -- run tools/harvest/dwr_subbasin.py")
class TestRealArchiveSixPoints:
    """The six MEASURED resolutions this check's brief asked for, against the real archive."""

    @pytest.fixture(autouse=True)
    def _reload(self, monkeypatch):
        from tools.kg import unit_resolver as mod
        monkeypatch.setattr(mod, "GEOJSON_DIR", REAL_ARCHIVE)
        mod._load_pages.cache_clear()
        mod._load_shapely_index.cache_clear()
        self.mod = mod
        yield
        mod._load_pages.cache_clear()
        mod._load_shapely_index.cache_clear()

    def test_sammakorn(self):
        r = self.mod.resolve_unit(13.758235, 100.676084)
        assert r["sb_code"] is not None
        assert r["basin_name_en"] == "Chao Phraya"

    def test_hatyai(self):
        r = self.mod.resolve_unit(7.008765, 100.474455)
        assert r["sb_code"] is not None

    def test_nan_town(self):
        r = self.mod.resolve_unit(18.783958, 100.773636)
        assert r["sb_code"] is not None
        assert r["basin_name_en"] == "Nan"

    def test_chiang_mai_town(self):
        r = self.mod.resolve_unit(18.787747, 98.993128)
        assert r["sb_code"] is not None
        assert r["basin_name_en"] == "Ping"

    def test_bang_ban(self):
        r = self.mod.resolve_unit(14.573611, 100.548333)
        assert r["sb_code"] is not None

    def test_sea_point_returns_open(self):
        r = self.mod.resolve_unit(10.5, 101.0)
        assert r["sb_code"] is None
        assert r["tag"] == "OPEN"
