"""Tests for tools/kg/build_kg.py's build-5 addition (2026-09-27): per-canal
normal/control level attribute (`normal_level_m` + `normal_level_basis`) on
`gauge:thaiwater_bma:*` / `gate:thaiwater_bma:*` asset nodes. Rule under test:
BMA-declared water_control (VERIFIED-BMA-control, from data/observations.sqlite) wins
over the dry-season median (MEASURED-history, sources/canal_normal_levels.yaml), which
wins over OPEN (no basis found). Never touches the real sqlite store or network -- an
in-memory sqlite connection + a tiny synthetic graph + a small fixture yaml.
"""
from pathlib import Path

import networkx as nx

import store
from tools.kg import build_kg

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "canal_normal_levels_sample.yaml"


def _base_graph() -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    # WL.TEST.01: will have BOTH a live BMA water_control row AND a dry-season median --
    # BMA control must win.
    G.add_node("gauge:thaiwater_bma:WL.TEST.01", kind="asset", **{"class": "gauge"},
               name_th="เดิม 1", lat=13.7, lon=100.6, owner=None,
               source="assets_registry.py", tag="VERIFIED")
    # WL.TEST.02: only a dry-season median, no live BMA control -- median must be used.
    G.add_node("gate:thaiwater_bma:WL.TEST.02", kind="asset", **{"class": "gate"},
               name_th="เดิม 2", lat=13.8, lon=100.7, owner=None,
               source="assets_registry.py", tag="VERIFIED")
    # WL.TEST.03: neither -- must resolve to OPEN, never fabricated.
    G.add_node("gauge:thaiwater_bma:WL.TEST.03", kind="asset", **{"class": "gauge"},
               name_th="เดิม 3", lat=13.9, lon=100.8, owner=None,
               source="assets_registry.py", tag="VERIFIED")
    # A non-BMA asset node must never be touched by this attribute.
    G.add_node("pump_station:other:1", kind="asset", **{"class": "pump_station"},
               name_th="ปั๊มอื่น", lat=None, lon=None, owner=None,
               source="assets_registry.py", tag="VERIFIED")
    return G


def _conn_with_water_control(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    store.insert_observation(
        conn, source_id="bma_station_detail", station_code="WL.TEST.01",
        variable="water_control_m", value=0.70, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00", fetched_at_utc="2026-09-27T10:05:00+00:00",
        trust_tier="official_telemetry")
    return conn


def test_bma_control_wins_over_dry_season_median(tmp_path):
    G = _base_graph()
    dry_season = build_kg.load_canal_normal_levels(FIXTURE)
    conn = _conn_with_water_control(tmp_path)
    bma_control = build_kg.load_bma_control_levels(conn)
    report = build_kg.apply_canal_normal_levels(G, dry_season, bma_control)

    node = G.nodes["gauge:thaiwater_bma:WL.TEST.01"]
    assert node["normal_level_m"] == 0.70
    assert node["normal_level_basis"] == "VERIFIED-BMA-control"
    assert report["bma_control_stations"] == 1


def test_dry_season_median_used_when_no_live_control(tmp_path):
    G = _base_graph()
    dry_season = build_kg.load_canal_normal_levels(FIXTURE)
    conn = _conn_with_water_control(tmp_path)  # only carries WL.TEST.01
    bma_control = build_kg.load_bma_control_levels(conn)
    report = build_kg.apply_canal_normal_levels(G, dry_season, bma_control)

    node = G.nodes["gate:thaiwater_bma:WL.TEST.02"]
    assert node["normal_level_m"] == -0.10
    assert node["normal_level_basis"] == "MEASURED-history"
    assert report["dry_season_median_stations"] == 1


def test_open_when_no_basis_found_never_fabricated(tmp_path):
    G = _base_graph()
    dry_season = build_kg.load_canal_normal_levels(FIXTURE)
    conn = _conn_with_water_control(tmp_path)
    bma_control = build_kg.load_bma_control_levels(conn)
    report = build_kg.apply_canal_normal_levels(G, dry_season, bma_control)

    node = G.nodes["gauge:thaiwater_bma:WL.TEST.03"]
    assert node["normal_level_m"] is None
    assert node["normal_level_basis"] == "OPEN"
    assert report["open_stations"] == 1


def test_non_bma_asset_node_untouched(tmp_path):
    G = _base_graph()
    dry_season = build_kg.load_canal_normal_levels(FIXTURE)
    conn = _conn_with_water_control(tmp_path)
    bma_control = build_kg.load_bma_control_levels(conn)
    build_kg.apply_canal_normal_levels(G, dry_season, bma_control)

    node = G.nodes["pump_station:other:1"]
    assert "normal_level_m" not in node


def test_load_canal_normal_levels_keys_by_station_code():
    dry_season = build_kg.load_canal_normal_levels(FIXTURE)
    assert set(dry_season) == {"WL.TEST.01", "WL.TEST.02"}
    assert dry_season["WL.TEST.01"]["normal_level_m"] == -0.30
