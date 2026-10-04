"""P0 regression tests, 2026-09-27 (orchestrator-verified real incident): an
`official_threshold` row in sources/canal_normal_levels.yaml was keyed to WL.BMA.02 but
its own lat/lon and datum actually belonged to a different station (ST.SPS.01) ~630 m
away, on an unconfirmed datum -- the mismatch made the page show "สูงกว่าปกติ" for a
station that should have been NO_NORMAL_BASIS. Fixed by (1) re-keying that specific row
to ST.SPS.01 and (2) a general admissibility guard in both loaders
(`site/build_data.py.load_canal_normal_levels()` /
`tools/heromap/sammakorn_map.load_normal_levels()`) that refuses ANY
`basis: official_threshold` row whose declared `station_distance_m` is missing/over
100 m, or whose `datum` is missing/OPEN/unknown -- "unknown = refuse", never a silent
apply. These tests cover the general guard with small synthetic fixtures (never the
real observations.sqlite/network) and confirm the real repo file's WL.BMA.02 row no
longer resolves.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "site"))
sys.path.insert(0, str(REPO_ROOT))

import build_data as bd  # noqa: E402
from tools.heromap.sammakorn_map import load_normal_levels as heromap_load_normal_levels  # noqa: E402

REAL_CANAL_NORMAL_LEVELS = REPO_ROOT / "sources" / "canal_normal_levels.yaml"


def _write_fixture(tmp_path, rows_yaml_text):
    p = tmp_path / "canal_normal_levels.yaml"
    p.write_text(rows_yaml_text, encoding="utf-8")
    return p


def test_official_threshold_row_over_100m_refused(tmp_path, monkeypatch):
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.FAR.01"
    normal_level_m: 0.40
    basis: official_threshold
    station_distance_m: 630
    datum: "m MSL"
""")
    monkeypatch.setattr(bd, "CANAL_NORMAL_LEVELS_PATH", p)
    rows = bd.load_canal_normal_levels()
    assert "WL.FAR.01" not in rows


def test_official_threshold_row_unknown_datum_refused(tmp_path, monkeypatch):
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.OPEN.01"
    normal_level_m: 0.40
    basis: official_threshold
    station_distance_m: 5
    datum: "OPEN"
""")
    monkeypatch.setattr(bd, "CANAL_NORMAL_LEVELS_PATH", p)
    rows = bd.load_canal_normal_levels()
    assert "WL.OPEN.01" not in rows


def test_official_threshold_row_missing_distance_refused(tmp_path, monkeypatch):
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.NODIST.01"
    normal_level_m: 0.40
    basis: official_threshold
    datum: "m MSL"
""")
    monkeypatch.setattr(bd, "CANAL_NORMAL_LEVELS_PATH", p)
    rows = bd.load_canal_normal_levels()
    assert "WL.NODIST.01" not in rows


def test_official_threshold_row_admissible_when_close_and_confirmed(tmp_path, monkeypatch):
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.OK.01"
    normal_level_m: 0.40
    basis: official_threshold
    station_distance_m: 5
    datum: "m MSL (confirmed)"
""")
    monkeypatch.setattr(bd, "CANAL_NORMAL_LEVELS_PATH", p)
    rows = bd.load_canal_normal_levels()
    assert "WL.OK.01" in rows
    assert rows["WL.OK.01"]["normal_level_m"] == 0.40


def test_dry_season_median_row_untouched_by_the_guard(tmp_path, monkeypatch):
    """The guard only gates `basis: official_threshold` -- a plain dry-season-median row
    (no station_distance_m/datum fields at all) must load exactly as before."""
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.MEDIAN.01"
    normal_level_m: -0.36
    basis: dry_season_median
""")
    monkeypatch.setattr(bd, "CANAL_NORMAL_LEVELS_PATH", p)
    rows = bd.load_canal_normal_levels()
    assert "WL.MEDIAN.01" in rows


def test_heromap_load_normal_levels_refuses_mislocated_official_threshold(tmp_path):
    p = _write_fixture(tmp_path, """
canals:
  - station_code: "WL.FAR.02"
    normal_level_m: 0.40
    basis: official_threshold
    station_distance_m: 630
    datum: "m MSL"
""")
    levels = heromap_load_normal_levels(str(p))
    assert "WL.FAR.02" not in levels


def test_real_repo_file_wl_bma_02_has_no_normal_level_after_rekey():
    """Regression guard for the actual P0 incident: the real
    sources/canal_normal_levels.yaml must NOT resolve a normal_level_m for WL.BMA.02
    (the row that used to be mis-keyed to it was re-keyed to ST.SPS.01, the station it
    actually describes)."""
    # load_canal_normal_levels() always reads bd.CANAL_NORMAL_LEVELS_PATH (module-level
    # constant) -- call directly against the real repo file (no monkeypatch) since this
    # test is specifically about the real, committed data.
    assert bd.CANAL_NORMAL_LEVELS_PATH == REAL_CANAL_NORMAL_LEVELS
    rows = bd.load_canal_normal_levels()
    assert "WL.BMA.02" not in rows
    assert "ST.SPS.01" in rows
    assert rows["ST.SPS.01"]["normal_level_m"] == 0.40
