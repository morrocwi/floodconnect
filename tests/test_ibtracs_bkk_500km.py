"""Tests for tools/harvest/ibtracs_bkk_500km.py's pure functions. No network -- uses a
tiny synthetic fixture CSV (tests/fixtures/ibtracs_wp_sample.csv) with the real IBTrACS
column shape (including its own units row as line 2, which must be skipped, and blank-
string WMO_WIND falling back to USA_WIND)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
from tools.harvest import ibtracs_bkk_500km as ib  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_haversine_km_zero_distance_for_same_point():
    assert ib.haversine_km(13.75, 100.5, 13.75, 100.5) == 0.0


def test_haversine_km_matches_known_rough_distance():
    # Bangkok to a point ~200km away (checked independently) -- allow a few km tolerance
    d = ib.haversine_km(13.7563, 100.5018, 15.5, 101.0)
    assert 195 < d < 210


def test_extract_bkk_500km_skips_units_row_and_out_of_range_rows():
    rows = ib.extract_bkk_500km(FIXTURES / "ibtracs_wp_sample.csv",
                                 season_min=2005, season_max=2025, radius_km=500.0)
    # row 1 (2015, 15.5/101.0) is within 500km and in-season -> kept
    # row 2 (2015, 7.0/134.0) is >500km -> dropped
    # row 3 (1998, ...) is out of season range -> dropped
    # the units row itself is skipped (SEASON="Year" doesn't parse as int)
    assert len(rows) == 1
    assert rows[0]["storm_id"] == "2015123N15150"
    assert rows[0]["season"] == 2015


def test_extract_bkk_500km_falls_back_to_usa_wind_when_wmo_blank():
    rows = ib.extract_bkk_500km(FIXTURES / "ibtracs_wp_sample.csv")
    assert rows[0]["wind_kt"] == 60.0  # WMO_WIND was blank, USA_WIND=60 used instead


def test_build_output_states_data_only_and_reference_point():
    out = ib.build_output([{"storm_id": "X"}])
    meta = out["_meta"]
    assert meta["reference_point"]["label"] == "Bangkok"
    assert "DATA ONLY" in meta["kind"]
    assert meta["row_count"] == 1
