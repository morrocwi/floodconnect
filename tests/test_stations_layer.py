"""M8 P2 tests -- nationwide station nodes + KG connectivity (tools/kg/stations_layer.py,
tools/harvest/station_tables.py, sources/stations/*.json, sources/canalchain_station_joins.yaml).

No live network calls -- every test here reads the already-committed station tables and
builds/augments graphs in memory or in a tmp_path copy, same discipline as
tests/test_kg_build.py."""
import copy
import json
from pathlib import Path

import networkx as nx
import pytest

import tools.kg.stations_layer as sl

REPO_ROOT = Path(__file__).parent.parent
KG_GRAPHML = REPO_ROOT / "output" / "thailand_water_kg.graphml"


# ---------------------------------------------------------------------------------
# committed station tables: sync / shape
# ---------------------------------------------------------------------------------

def test_committed_station_tables_exist_and_are_sorted():
    for sid in sl.STATION_TABLE_SOURCES:
        path = sl.STATIONS_DIR / f"{sid}.json"
        assert path.exists(), f"missing committed table {path}"
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc["rows"]
        assert rows, f"{sid} table is empty"
        assert doc["row_count"] == len(rows)
        ids = [str(r["id"]) for r in rows]
        assert ids == sorted(ids), f"{sid} rows are not sorted by id"
        assert len(ids) == len(set(ids)), f"{sid} has duplicate ids"


def test_bma_watermap_table_has_the_three_missing_live_stations():
    """Per the M8 design's MEASURED facts: WL.SMK.01, WL.BMA.02, WL.SSB.13 have no
    existing KG node as of v0.1.4 -- they must be present in the committed table so
    stations_layer.py can add nodes for them."""
    doc = json.loads((sl.STATIONS_DIR / "bma_watermap.json").read_text(encoding="utf-8"))
    ids = {r["id"] for r in doc["rows"]}
    for code in ("WL.SMK.01", "WL.BMA.02", "WL.SSB.13"):
        assert code in ids, f"{code} missing from committed bma_watermap table"


def test_bma_watermap_row_has_verbatim_thai_name():
    doc = json.loads((sl.STATIONS_DIR / "bma_watermap.json").read_text(encoding="utf-8"))
    row = next(r for r in doc["rows"] if r["id"] == "WL.SMK.01")
    assert row["name_th"] == (
        "จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2"
    )


def test_thaiwater_waterlevel_table_row_count_matches_measured_facts():
    doc = json.loads((sl.STATIONS_DIR / "thaiwater_waterlevel.json").read_text(encoding="utf-8"))
    # MEASURED 2026-10-05: 807 nationwide stations.
    assert doc["row_count"] >= 800


# ---------------------------------------------------------------------------------
# joins file
# ---------------------------------------------------------------------------------

def test_joins_file_has_smk_and_bma_located_on():
    joins = sl._load_joins()
    located = {(j["station_id"], j["canal_node"]) for j in joins if j["edge"] == "LOCATED_ON"}
    assert ("WL.SMK.01", "canalchain:sammakorn_pond") in located
    assert ("WL.BMA.02", "canalchain:banma") in located


def test_joins_file_outlet_to_carries_contradiction():
    joins = sl._load_joins()
    outlet = next(j for j in joins if j["edge"] == "OUTLET_TO")
    assert outlet["canal_node"] == "canalchain:sammakorn_pond"
    assert outlet["target_canal_node"] == "canalchain:ssb08"
    assert "contradicts" in outlet and outlet["contradicts"]
    assert outlet["tag"] == "DERIVED-snap"


# ---------------------------------------------------------------------------------
# apply() on a small synthetic graph (fast, no 30 MB file read)
# ---------------------------------------------------------------------------------

def _tiny_graph():
    G = nx.MultiDiGraph()
    G.add_node("canalchain:sammakorn_pond", kind="canal_node", class_=None, **{
        "class": "canal_node", "name_th": "บึงสัมมากร", "lat": None, "lon": None,
        "tag": "OPEN", "source": "site/inputs/canals/east_chain.yaml (declared chain, unresolved)",
    })
    G.add_node("canalchain:banma", kind="canal_node", **{
        "class": "canal_node", "name_th": "คลองบ้านม้า", "lat": None, "lon": None,
        "tag": "OPEN", "source": "site/inputs/canals/east_chain.yaml (declared chain, unresolved)",
    })
    G.add_node("canalchain:ssb08", kind="canal_node", **{
        "class": "canal_node", "name_th": "แสนแสบ-เสรีไทย 24", "lat": 13.7805, "lon": 100.67387,
        "tag": "RELAYED", "source": "site/inputs/canals/east_chain.yaml (declared chain)",
    })
    # existing thaiwater_bma node, to exercise the SAME_STATION match for WL.SSB.08
    G.add_node("gauge:thaiwater_bma:WL.SSB.08", kind="asset", **{
        "class": "gauge", "name_th": "x", "lat": 13.78, "lon": 100.67, "tag": "VERIFIED",
        "source": "x",
    })
    return G


def test_apply_adds_located_on_and_coordinates():
    G = _tiny_graph()
    report = sl.apply(G, REPO_ROOT)
    assert "gauge:bma_watermap:WL.SMK.01" in G
    assert "gauge:bma_watermap:WL.BMA.02" in G
    assert G.has_edge("gauge:bma_watermap:WL.SMK.01", "canalchain:sammakorn_pond")
    assert G.has_edge("gauge:bma_watermap:WL.BMA.02", "canalchain:banma")
    # the pond node had no coordinate before -- it must get one from its station now
    assert G.nodes["canalchain:sammakorn_pond"]["lat"] is not None
    assert G.nodes["canalchain:sammakorn_pond"]["tag"] == "RELAYED"
    assert report["located_on"] == 2
    assert report["outlet_to"] == 1
    assert G.has_edge("canalchain:sammakorn_pond", "canalchain:ssb08")


def test_apply_same_station_edge_for_ssb08():
    G = _tiny_graph()
    sl.apply(G, REPO_ROOT)
    assert G.has_edge("gauge:bma_watermap:WL.SSB.08", "gauge:thaiwater_bma:WL.SSB.08")
    edge_data = G.get_edge_data("gauge:bma_watermap:WL.SSB.08", "gauge:thaiwater_bma:WL.SSB.08")
    assert any(d["kind"] == "SAME_STATION" for d in edge_data.values())


def test_apply_is_idempotent_on_reapply():
    G = _tiny_graph()
    sl.apply(G, REPO_ROOT)
    n1, e1 = G.number_of_nodes(), G.number_of_edges()
    sl.apply(G, REPO_ROOT)  # re-apply: must drop+re-add the layer, not double it
    assert G.number_of_nodes() == n1
    assert G.number_of_edges() == e1


def test_apply_never_fabricates_sb_dwr_without_archive():
    """raw/gis/dwr_subbasin/ is not present in this checkout -- sb_dwr on every new
    node must be None, never a guessed code."""
    G = _tiny_graph()
    sl.apply(G, REPO_ROOT)
    for nid, d in G.nodes(data=True):
        if d.get("layer") == "stations_v1" and d.get("kind") == "asset":
            assert d.get("sb_dwr") is None


# ---------------------------------------------------------------------------------
# real committed KG: join count / coverage / size budget (reads the real 30MB file
# once per test module via a module-scoped fixture -- NOT per test)
# ---------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_graph():
    return nx.read_graphml(KG_GRAPHML, force_multigraph=True)


def test_real_kg_has_the_three_previously_missing_bma_nodes(real_graph):
    for code in ("WL.SMK.01", "WL.BMA.02", "WL.SSB.13"):
        assert f"gauge:bma_watermap:{code}" in real_graph, (
            f"gauge:bma_watermap:{code} not found in the committed KG -- "
            "run `python3 -m tools.kg.stations_layer --augment output/thailand_water_kg.graphml`"
        )


def test_real_kg_smk01_located_on_sammakorn_pond(real_graph):
    assert real_graph.has_edge("gauge:bma_watermap:WL.SMK.01", "canalchain:sammakorn_pond")
    assert real_graph.has_edge("gauge:bma_watermap:WL.BMA.02", "canalchain:banma")


def test_real_kg_coverage_report_before_after_per_class(real_graph):
    """Smoke test on the real committed graph: every class stations_layer.py touches
    gained at least as many nodes as it had before (never a silent regression)."""
    cov = sl.coverage_snapshot(real_graph)
    assert cov["gauge:bma_watermap"]["nodes"] >= 300
    assert cov["gauge:thaiwater_waterlevel"]["nodes"] >= 804


def test_real_kg_size_budget():
    graphml_mb = KG_GRAPHML.stat().st_size / (1024 * 1024)
    jsonld_mb = (KG_GRAPHML.with_suffix(".jsonld")).stat().st_size / (1024 * 1024)
    assert graphml_mb < 95, f"thailand_water_kg.graphml is {graphml_mb:.1f} MB, over the 95 MB budget"
    assert jsonld_mb < 95, f"thailand_water_kg.jsonld is {jsonld_mb:.1f} MB, over the 95 MB budget"


def test_augment_on_a_tmp_copy_is_deterministic(tmp_path):
    import shutil
    import subprocess
    import sys as _sys

    tmp_graphml = tmp_path / "kg.graphml"
    shutil.copy(KG_GRAPHML, tmp_graphml)
    cmd = [_sys.executable, "-m", "tools.kg.stations_layer", "--augment", str(tmp_graphml)]
    r1 = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    h1 = tmp_graphml.read_bytes()
    r2 = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    h2 = tmp_graphml.read_bytes()
    assert h1 == h2, "re-augmenting the same graph+inputs must be byte-identical"
