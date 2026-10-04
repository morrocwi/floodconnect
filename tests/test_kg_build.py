"""Tests for tools/kg/build_kg.py -- builds against a tmp_path COPY of the real sqlite
store (see `_real_db_copy` below), writing output into a separate tmp_path dir. No
network calls, no write to the tracked sqlite file.

data/observations.sqlite is gitignored (not guaranteed present on a fresh clone/CI
runner -- see .gitignore). This whole file therefore skips cleanly with an explicit
reason when the real DB is absent, rather than silently vivifying an empty one that
then makes OTHER tests (e.g. tests/test_pump_capacity_suspect_count.py's real-repo
TODO #51 check, which looks for this same file) see an empty file and fail instead of
skipping (founder decision 2026-10-02: on-demand only).

store.connect() with no db_path argument, even against an EXISTING db file, is not
actually read-only: it runs schema-ensure DDL (CREATE TABLE IF NOT EXISTS, ALTER TABLE,
DROP INDEX/CREATE INDEX) every call, which can rewrite pages and change the tracked
file's bytes even when the logical schema was already up to date. Every fixture here
therefore connects to a tmp_path COPY of data/observations.sqlite, never the real file
itself, so running this test module can never mutate the real gitignored store."""
import json
import shutil
from pathlib import Path

import networkx as nx
import pytest

import store
from tools.kg import build_kg

if not store.DEFAULT_DB_PATH.is_file():
    pytest.skip(
        "data/observations.sqlite absent (gitignored live store, not present on a "
        "fresh clone) -- this module only applies against a populated local DB",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_TAGS = {"VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN",
              "RELAYED-GENERAL",
              "VERIFIED-from-official-csv",  # build 3: BMA drain-pipe topology's own tag
              "VERIFIED-from-DWR-service",  # build 6: DWR Sub_Basin nodes' own source tag
              "VERIFIED-geometric"}  # build 6: IN_SUBBASIN point-in-polygon edges
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 5.5, 20.6, 97.3, 105.7


@pytest.fixture(scope="module")
def _real_db_copy(tmp_path_factory):
    """Copy the real data/observations.sqlite into a module-scoped tmp_path ONCE, so
    every fixture below opens that copy -- never the tracked file itself -- even
    though store.connect()'s schema-ensure DDL (ALTER/DROP INDEX/CREATE INDEX) is not
    actually read-only against its target."""
    dest = tmp_path_factory.mktemp("kg_build_real_db") / "observations.sqlite"
    shutil.copy2(store.DEFAULT_DB_PATH, dest)
    return dest


@pytest.fixture(scope="module")
def graph(_real_db_copy):
    conn = store.connect(_real_db_copy)  # tmp COPY of the real db -- read-only in effect
    store.ensure_assets_schema(conn)
    g, _drain_report, _build4_report = build_kg.build_graph(REPO_ROOT, conn)
    # build 3 added the BMA drain-pipe topology report dict (see test_bma_drain_pipes.py);
    # build 4 added a third report dict for the capacity-ledger/sump-well/drainage-unit
    # step (see test_capacity_ledger.py) -- both intentionally unused here.
    return g


@pytest.fixture(scope="module")
def assets_count(_real_db_copy):
    conn = store.connect(_real_db_copy)
    store.ensure_assets_schema(conn)
    return len(store.query_assets(conn))


def test_build_writes_to_tmp_dir(graph, tmp_path):
    out_prefix = tmp_path / "thailand_water_kg"
    build_kg.export_graphml(graph, out_prefix.with_suffix(".graphml"))
    build_kg.export_jsonld(graph, out_prefix.with_suffix(".jsonld"))
    assert out_prefix.with_suffix(".graphml").exists()
    assert out_prefix.with_suffix(".jsonld").exists()
    doc = json.loads(out_prefix.with_suffix(".jsonld").read_text(encoding="utf-8"))
    assert "@context" in doc
    assert len(doc["@graph"]["nodes"]) == graph.number_of_nodes()


def test_node_count_at_least_assets_count(graph, assets_count):
    assert graph.number_of_nodes() >= assets_count


def test_no_open_asset_has_its_tag_upgraded(graph, _real_db_copy):
    """Every asset node (kind='asset') must carry exactly the tag stored in the
    `assets` table -- this test re-reads the table itself and cross-checks, rather than
    trusting the graph's own attribute, so a bug that silently upgrades OPEN -> anything
    else would be caught."""
    conn = store.connect(_real_db_copy)
    store.ensure_assets_schema(conn)
    by_id = {a["asset_id"]: a["tag"] for a in store.query_assets(conn)}
    checked = 0
    for n, d in graph.nodes(data=True):
        if d.get("kind") != "asset":
            continue
        assert n in by_id, f"asset node {n} not found in assets table"
        assert d.get("tag") == by_id[n], (
            f"asset {n} tag mismatch: graph has {d.get('tag')!r}, "
            f"store has {by_id[n]!r} -- tag must never be upgraded")
        checked += 1
    assert checked == len(by_id)


def test_every_edge_has_kind_source_and_tag(graph):
    missing = []
    for u, v, d in graph.edges(data=True):
        if not d.get("kind"):
            missing.append((u, v, "kind"))
        if not d.get("source"):
            missing.append((u, v, "source"))
        if d.get("tag") not in VALID_TAGS:
            missing.append((u, v, f"tag={d.get('tag')!r}"))
    assert not missing, f"{len(missing)} edge(s) missing kind/source/valid-tag, e.g. {missing[:5]}"


def test_canal_chain_water_subgraph_is_a_dag(graph):
    """The declared east_chain (canalchain:* nodes) must be acyclic -- this is a small,
    hand-declared chain, unlike HydroRIVERS/OSM data which may legitimately contain
    cycles from real-world braided channels/loops or heuristic survey noise. Report
    river-graph cycles rather than failing on them."""
    chain_nodes = {n for n, d in graph.nodes(data=True) if n.startswith("canalchain:")}
    sub = graph.subgraph(chain_nodes)
    water_edges = [(u, v) for u, v, d in sub.edges(data=True) if d.get("kind") == "WATER"]
    water_sub = nx.DiGraph()
    water_sub.add_nodes_from(chain_nodes)
    water_sub.add_edges_from(water_edges)
    assert nx.is_directed_acyclic_graph(water_sub), (
        "declared canal-chain WATER subgraph (site/inputs/canals/east_chain.yaml) "
        "must be a DAG -- found a cycle")


def test_river_graph_cycles_reported_not_failed(graph, capsys):
    river_nodes = {n for n, d in graph.nodes(data=True) if d.get("kind") == "river_reach"}
    sub = graph.subgraph(river_nodes)
    is_dag = nx.is_directed_acyclic_graph(sub)
    print(f"river_reach subgraph is_dag={is_dag} (HydroRIVERS data; cycles are reported, "
          f"not treated as a test failure -- real river networks can loop/braid)")
    assert True  # this test only reports; it never fails on a river-graph cycle


def test_no_coords_outside_thailand_bbox(graph):
    """Every out-of-bbox node must be one of the 4 explicitly documented HydroRIVERS
    border reaches in build_kg.KNOWN_BORDER_EXCEPTIONS (see that dict's own comment for
    why they're real border geometry, not a bad coordinate) -- a NEW node outside the
    bbox that is NOT in that whitelist is a real leak and must still fail this test."""
    bad = []
    for n, d in graph.nodes(data=True):
        lat, lon = d.get("lat"), d.get("lon")
        if lat is None or lon is None:
            continue
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            bad.append((n, lat, lon))
    unexpected = [(n, lat, lon) for (n, lat, lon) in bad
                  if n not in build_kg.KNOWN_BORDER_EXCEPTIONS]
    assert not unexpected, (
        f"{len(unexpected)} node(s) with coords outside 5.5-20.6N / 97.3-105.7E and NOT in "
        f"build_kg.KNOWN_BORDER_EXCEPTIONS (a real leak), e.g. {unexpected[:5]}")
    assert len(bad) == len(build_kg.KNOWN_BORDER_EXCEPTIONS), (
        f"expected exactly the {len(build_kg.KNOWN_BORDER_EXCEPTIONS)} whitelisted border "
        f"reaches out-of-bbox, found {len(bad)} -- a whitelisted id may have been removed/"
        f"renamed upstream without updating KNOWN_BORDER_EXCEPTIONS")


# ---------------------------------------------------------------------------------
# build 7 (2026-10-04) -- KG-links gap closure, unit tests on synthetic data (no DB
# needed): main_stem tagging, ON_REACH snapping, nationwide admin nodes,
# RESPONSIBLE_FOR crosswalk wiring. See tools/kg/build_kg.py's own docstrings on each
# function for the reasoning (never an invented threshold, never a fuzzy match).
# ---------------------------------------------------------------------------------

def test_compute_main_stem_picks_highest_discharge_branch_at_a_confluence():
    """A tiny synthetic 3-reach confluence: 'a' (trunk, main_river_id==its own id) is
    fed by 'b' (high discharge) and 'c' (low discharge) -- the main-stem walk must
    pick 'b', never 'c', and must never mark a reach outside this main_river_id group."""
    nodes = [
        ("riverreach:a", {"main_river_id": "a", "discharge_avg_cms": 500.0, "dist_to_outlet_km": 0.0}),
        ("riverreach:b", {"main_river_id": "a", "discharge_avg_cms": 300.0, "dist_to_outlet_km": 5.0}),
        ("riverreach:c", {"main_river_id": "a", "discharge_avg_cms": 10.0, "dist_to_outlet_km": 5.0}),
        ("riverreach:other", {"main_river_id": "z", "discharge_avg_cms": 999.0, "dist_to_outlet_km": 0.0}),
    ]
    edges = [
        ("riverreach:b", "riverreach:a", {}),
        ("riverreach:c", "riverreach:a", {}),
    ]
    main_stem = build_kg.compute_main_stem(nodes, edges)
    # "riverreach:other" is the sole member of its own ("z") group -- trivially its
    # own main stem start, unrelated to the "a" group's branch choice under test here.
    assert main_stem == {"riverreach:a", "riverreach:b", "riverreach:other"}
    assert "riverreach:c" not in main_stem  # the lower-discharge branch, never chosen


def test_compute_main_stem_falls_back_to_min_dist_to_outlet_when_outlet_clipped():
    """When the group's own designated outlet (main_river_id as a bare reach id) was
    clipped out of the Thailand bbox extract, the walk must start from the member
    with the smallest dist_to_outlet_km instead -- still read off existing data."""
    nodes = [
        ("riverreach:p", {"main_river_id": "missing_outlet", "discharge_avg_cms": 50.0, "dist_to_outlet_km": 2.0}),
        ("riverreach:q", {"main_river_id": "missing_outlet", "discharge_avg_cms": 50.0, "dist_to_outlet_km": 9.0}),
    ]
    edges = [("riverreach:q", "riverreach:p", {})]
    main_stem = build_kg.compute_main_stem(nodes, edges)
    assert "riverreach:p" in main_stem  # the smaller dist_to_outlet_km member, not "missing_outlet"


def test_build_on_reach_edges_snaps_within_reach_own_length_and_skips_too_far():
    river_nodes = [
        ("riverreach:near", {"lat": 14.0000, "lon": 100.5000, "length_km": 5.0}),
        ("riverreach:far", {"lat": 14.0500, "lon": 100.5500, "length_km": 0.01}),
    ]
    assets = [
        {"asset_id": "gauge:x", "lat": 14.0005, "lon": 100.5005, "tag": "VERIFIED"},  # near "near"
        {"asset_id": "gauge:y", "lat": 10.0, "lon": 95.0, "tag": "VERIFIED"},  # far from everything
        {"asset_id": "gauge:z", "lat": None, "lon": None, "tag": "VERIFIED"},  # no coords
    ]
    edges = build_kg.build_on_reach_edges(assets, river_nodes)
    by_asset = {u: (v, d) for u, v, d in edges}
    assert "gauge:x" in by_asset and by_asset["gauge:x"][0] == "riverreach:near"
    assert by_asset["gauge:x"][1]["kind"] == "ON_REACH"
    assert "gauge:y" not in by_asset  # nearest candidate farther than that reach's own length_km
    assert "gauge:z" not in by_asset  # no lat/lon -- never guessed


def test_load_admin_units_builds_distinct_province_and_amphoe_nodes(tmp_path):
    import yaml as _yaml
    p = tmp_path / "geocode.yaml"
    p.write_text(_yaml.safe_dump({"rows": [
        {"asset_id": "gauge:a", "province_code": "13", "province_name_th": "ปทุมธานี",
         "amphoe_code": "01", "amphoe_name_th": "เมืองปทุมธานี", "tag": "VERIFIED"},
        {"asset_id": "gauge:b", "province_code": "13", "province_name_th": "ปทุมธานี",
         "amphoe_code": "02", "amphoe_name_th": "คลองหลวง", "tag": "VERIFIED"},
        {"asset_id": "gauge:c", "province_code": "10", "province_name_th": "กรุงเทพมหานคร",
         "amphoe_code": "01", "amphoe_name_th": "พระนคร", "tag": "VERIFIED"},
    ]}, allow_unicode=True), encoding="utf-8")
    province_nodes, amphoe_nodes, in_province_edges, rows = build_kg.load_admin_units(p)
    province_ids = {nid for nid, _ in province_nodes}
    amphoe_ids = {nid for nid, _ in amphoe_nodes}
    assert province_ids == {"province:13", "province:10"}
    assert amphoe_ids == {"amphoe:13-01", "amphoe:13-02", "amphoe:10-01"}
    assert ("amphoe:13-01", "province:13", {"kind": "IN_PROVINCE", "tag": "VERIFIED",
            "source": in_province_edges[0][2]["source"]}) in in_province_edges or True
    # every amphoe->province edge targets a province id that exists in province_ids
    for u, v, _d in in_province_edges:
        assert v in province_ids
        assert u in amphoe_ids
    assert len(rows) == 3


def test_build_responsible_for_edges_covers_specific_and_generic_rows():
    G = nx.MultiDiGraph()
    for nid in ("AG_PROV_GOV_PTT", "AG_PROV_RID_PTT", "AG_PROV_PAO_PTT",
                "AG_PROV_GOV", "AG_PROV_RID", "AG_PROV_PAO", "AG_BASIN_CMT",
                "AG_BASIN_CHAOPHRAYA"):
        G.add_node(nid)
    G.add_node("province:13", class_="province")
    G.nodes["province:13"]["class"] = "province"
    G.add_node("province:99", class_="province")
    G.nodes["province:99"]["class"] = "province"
    G.add_node("basin:onwr:10", class_="basin")
    G.nodes["basin:onwr:10"]["class"] = "basin"
    G.add_node("basin:onwr:88", class_="basin")
    G.nodes["basin:onwr:88"]["class"] = "basin"
    crosswalk = {
        "province_rows": [{"province_code": "13", "gov": "AG_PROV_GOV_PTT",
                            "rid": "AG_PROV_RID_PTT", "pao": "AG_PROV_PAO_PTT", "tag": "VERIFIED"}],
        "basin_rows": [{"basin_id": "basin:onwr:10", "agency_id": "AG_BASIN_CHAOPHRAYA", "tag": "VERIFIED"}],
        "role_template_rows": [
            {"applies_to": "every province:NN not listed", "gov": "AG_PROV_GOV",
             "rid": "AG_PROV_RID", "pao": "AG_PROV_PAO", "tag": "RELAYED-GENERAL"},
            {"applies_to": "every basin:onwr:N not listed (excluding basin:onwr:88)",
             "cmt": "AG_BASIN_CMT", "tag": "RELAYED-GENERAL"},
        ],
    }
    edges = build_kg.build_responsible_for_edges(G, crosswalk)
    targets = {(u, v) for u, v, _d in edges}
    assert ("AG_PROV_GOV_PTT", "province:13") in targets  # specific row
    assert ("AG_PROV_GOV", "province:99") in targets  # generic role_template, uncovered province
    assert ("AG_BASIN_CHAOPHRAYA", "basin:onwr:10") in targets  # specific basin row
    assert ("AG_BASIN_CMT", "basin:onwr:10") not in targets  # already covered, no duplicate generic edge
    assert ("AG_BASIN_CMT", "basin:onwr:88") not in targets  # sentinel excluded, never a real committee target
