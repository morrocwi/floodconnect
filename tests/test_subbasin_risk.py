"""tests/test_subbasin_risk.py -- synthetic-unit tests for tools/riskmap/subbasin_risk.py.

Uses a throwaway in-memory sqlite DB (never touches data/observations.sqlite) so this
test never depends on live archived rows drifting over time. Exercises the pure tier
logic, the coping-threshold lookup, and the flow-consistency guard (project decision
2026-09-27: no gauge/forecast value anchors a tier unless it passes a directional
plausibility check against known dam releases + diversion-only reach structure).
"""
from __future__ import annotations

import sqlite3

import pytest

from tools.riskmap.subbasin_risk import (
    _max_tier,
    _tier_from_ratio,
    _colour_for_tier,
    _coping_var_for_kind,
    flow_consistency_flag,
)


def test_max_tier_picks_highest():
    assert _max_tier(["L0", "L2", "L1"]) == "L2"
    assert _max_tier([]) == "L0"
    assert _max_tier(["bogus"]) == "L0"


def test_tier_from_ratio_bands():
    # below coped_max -> L0
    assert _tier_from_ratio(50, coped_max=100, flooded_min=200) == "L0"
    # between coped_max and 50% of the gap -> L1
    assert _tier_from_ratio(110, coped_max=100, flooded_min=200) == "L1"
    # >=80% of the gap -> L3
    assert _tier_from_ratio(185, coped_max=100, flooded_min=200) == "L3"
    # at/over flooded_min -> L4
    assert _tier_from_ratio(200, coped_max=100, flooded_min=200) == "L4"
    assert _tier_from_ratio(250, coped_max=100, flooded_min=200) == "L4"
    # no value -> L0, never a guess
    assert _tier_from_ratio(None, coped_max=100, flooded_min=200) == "L0"
    # no thresholds at all -> L0 (absent, not fabricated)
    assert _tier_from_ratio(999, coped_max=None, flooded_min=None) == "L0"


def test_colour_for_tier_grey_never_used_for_missing_only():
    assert _colour_for_tier("LR") == "grey"
    assert _colour_for_tier("L0") == "grey"
    assert _colour_for_tier("L4") == "red"
    assert _colour_for_tier("unknown_tier") == "grey"


def test_coping_var_for_kind_reads_derived_block():
    coping = {
        "synthetic_unit": {
            "river_flow_m3s": {
                "threshold_flooded_min": {"value": 500.0, "tag": "RELAYED"},
                "threshold_coped_max": {"value": 300.0, "tag": "RELAYED"},
            },
            "rain_24h_mm": {
                "threshold_flooded_min": {"value": 150.0, "tag": "VERIFIED"},
                "threshold_coped_max": {"value": None, "tag": "OPEN"},
            },
        }
    }
    flow = _coping_var_for_kind(coping, "synthetic_unit", "flow")
    assert flow["coped_max"] == 300.0
    assert flow["flooded_min"] == 500.0
    rain = _coping_var_for_kind(coping, "synthetic_unit", "rain")
    assert rain["flooded_min"] == 150.0
    assert rain["coped_max"] is None
    # unknown unit -> None, never a guessed row
    assert _coping_var_for_kind(coping, "no_such_unit", "flow") is None


# ---------------------------------------------------------------------------
# flow_consistency_flag -- synthetic in-memory DB, no live data
# ---------------------------------------------------------------------------

def _make_synthetic_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        """CREATE TABLE observations (
            id INTEGER PRIMARY KEY, source_id TEXT, station_code TEXT, station_name TEXT,
            lat REAL, lon REAL, variable TEXT, value REAL, unit TEXT,
            observed_at_utc TEXT, fetched_at_utc TEXT, warning REAL, critical REAL,
            bank REAL, status TEXT, trust_tier TEXT, provenance_json TEXT
        )"""
    )
    return con


def _insert_flood(con, station_code, values):
    for i, v in enumerate(values):
        con.execute(
            "INSERT INTO observations (source_id, station_code, variable, value, observed_at_utc) "
            "VALUES ('openmeteo_flood', ?, 'glofas_river_discharge_m3s', ?, ?)",
            (station_code, v, f"2026-09-{26+i:02d}T17:00:00+00:00"),
        )


def test_flow_consistency_flags_implausible_downstream_increase():
    """Synthetic case mirroring the real founder-flagged incident: downstream
    discharge higher than upstream by far more than any known dam release, on a
    reach with only outflow-type diversions -- must be SUSPECT."""
    con = _make_synthetic_db()
    _insert_flood(con, "synthetic_downstream", [3800, 3850, 4150, 4400, 4650, 4740, 4680])
    _insert_flood(con, "synthetic_upstream", [2300, 2300, 2350, 2400, 2450, 2450, 2430])
    con.execute(
        "INSERT INTO observations (source_id, station_code, station_name, variable, value, observed_at_utc) "
        "VALUES ('hii_dam', 'dam:synthetic:1', 'Synthetic Dam', 'dam_hourly_release_m3s_computed', 5.0, '2026-09-27T11:00:00+00:00')"
    )
    con.commit()
    result = flow_consistency_flag(con, "synthetic_downstream", "synthetic_upstream", ["dam:synthetic:1"])
    assert result["suspect"] is True
    assert result["combined_known_release_m3s"] == 5.0
    assert all(p["exceeds_known_release"] for p in result["per_day"])


def test_flow_consistency_passes_when_release_explains_gap():
    """Downstream slightly higher than upstream, but by LESS than the known dam
    release entering the reach -- plausible, must NOT be flagged suspect."""
    con = _make_synthetic_db()
    _insert_flood(con, "synthetic_downstream", [2320, 2330, 2340])
    _insert_flood(con, "synthetic_upstream", [2300, 2300, 2300])
    con.execute(
        "INSERT INTO observations (source_id, station_code, station_name, variable, value, observed_at_utc) "
        "VALUES ('hii_dam', 'dam:synthetic:2', 'Synthetic Dam 2', 'dam_hourly_release_m3s_computed', 100.0, '2026-09-27T11:00:00+00:00')"
    )
    con.commit()
    result = flow_consistency_flag(con, "synthetic_downstream", "synthetic_upstream", ["dam:synthetic:2"])
    assert result["suspect"] is False


def test_flow_consistency_insufficient_data_never_guesses():
    con = _make_synthetic_db()
    result = flow_consistency_flag(con, "nonexistent_downstream", "nonexistent_upstream", [])
    assert result["suspect"] is False
    assert result["checked"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
