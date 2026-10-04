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
