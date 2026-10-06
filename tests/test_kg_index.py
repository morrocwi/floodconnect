"""Tests for tools/kg/build_index.py -- the M4 "KG-first that AIs cannot
skip" per-province KG index. Every test here reads the REAL shipped graph
(output/thailand_water_kg.graphml, committed in git) -- never a synthetic
fixture -- per this workspace's "real data only in tests" rule. Tests that
need the graphml are skipped (not failed) when it is absent, same convention
tools/kg/README.md's own regeneration docs use.

Run only this file while iterating:
    python3 -m pytest tests/test_kg_index.py -q
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools.kg import build_index  # noqa: E402

GRAPH_PATH = HERE / "output" / "thailand_water_kg.graphml"
COMMITTED_INDEX_DIR = HERE / "output" / "kg_index"

pytestmark = pytest.mark.skipif(
    not GRAPH_PATH.exists(), reason="output/thailand_water_kg.graphml absent in this checkout"
)


@pytest.fixture(scope="module")
def built():
    with tempfile.TemporaryDirectory() as tmp:
        result = build_index.build(graph_path=str(GRAPH_PATH), out_dir=tmp)
        files = {}
        for name in os.listdir(tmp):
            with open(os.path.join(tmp, name), encoding="utf-8") as f:
                files[name] = f.read()
        yield result, files


def test_regenerating_equals_committed_files_byte_for_byte(built):
    _result, files = built
    committed = sorted(p.name for p in COMMITTED_INDEX_DIR.glob("*.json"))
    rebuilt = sorted(files.keys())
    assert committed == rebuilt, "rebuild index -- file set differs from the committed output/kg_index/"
    for name in committed:
        committed_text = (COMMITTED_INDEX_DIR / name).read_text(encoding="utf-8")
        assert committed_text == files[name], f"rebuild index -- {name} differs from the committed build"


def test_index_kg_sha256_matches_committed_graph(built):
    result, files = built
    index = json.loads(files["index.json"])
    with open(GRAPH_PATH, "rb") as f:
        import hashlib

        actual = hashlib.sha256(f.read()).hexdigest()
    assert index["kg"]["sha256"] == actual, "rebuild index -- committed sha256 no longer matches the graph"
    assert index["kg"]["sha256"] == result["kg_sha256"]


def test_every_province_node_has_a_slice(built):
    import networkx as nx

    g = nx.read_graphml(str(GRAPH_PATH))
    province_codes = {
        d.get("province_code") or n.split(":")[-1]
        for n, d in g.nodes(data=True)
        if d.get("kind") == "province"
    }
    _result, files = built
    index = json.loads(files["index.json"])
    assert set(index["prov"]) == province_codes
    for code in province_codes:
        assert f"province_{code}.json" in files


def test_index_counts_match_slice_counts(built):
    """`meta["n"]` counts the province's FULL `a` row set, including any rows
    `build_index.py` split out to an `extra_files` sibling (fix) --
    merge those back in before comparing, the same way `tools/kg/locate.py`'s
    `_load_slice_full` does at read time."""
    _result, files = built
    index = json.loads(files["index.json"])
    for code, meta in index["prov"].items():
        slice_obj = json.loads(files[meta["file"]])
        a_rows = list(slice_obj["a"])
        for ext_filename in meta.get("extra_files") or []:
            a_rows.extend(json.loads(files[ext_filename])["a"])
        assert meta["n"]["a"] == len(a_rows)
        assert meta["n"]["a_e"] == sum(1 for r in a_rows if r[9] == "e")
        assert meta["n"]["a_b"] == sum(1 for r in a_rows if r[9] == "b")
        assert meta["n"]["a_n"] == sum(1 for r in a_rows if r[9] == "n")


def test_box_members_lie_inside_the_box(built):
    """Catches the F3 rounding bug: a plain round(.,3) box excluded a Pathum
    member sitting exactly on its own rounded boundary."""
    _result, files = built
    index = json.loads(files["index.json"])
    for code, meta in index["prov"].items():
        slice_obj = json.loads(files[meta["file"]])
        bbox = slice_obj["bbox"]
        if bbox[0] is None:
            continue
        s, w, n, e = bbox
        for row in slice_obj["a"]:
            if row[9] != "e":
                continue
            lat, lon = row[3], row[4]
            assert s <= lat <= n and w <= lon <= e, (
                f"province {code}: edge-linked member {row[0]} at ({lat},{lon}) "
                f"lies outside its own province's bbox {bbox}"
            )


def test_size_report_median_and_max_within_budget(built):
    _result, files = built
    sizes = sorted(len(v.encode("utf-8")) for k, v in files.items() if k != "index.json")
    median = sizes[len(sizes) // 2]
    print(f"\nkg_index size report: median={median}B max={max(sizes)}B total={sum(sizes)}B n={len(sizes)}")
    assert median <= 30_000, f"median slice {median}B exceeds the 30 KB target"
    # fix: the cap stays at 200KB -- it is never loosened. Bangkok's
    # own province:10 slice would have grown to ~242KB after M8 P2 added the 311
    # nationwide bma_watermap station nodes; `build_index.py` now splits those rows
    # into a sibling `province_10_ext.json` file instead (see CHANGELOG
    # "Unreleased" and `tools/kg/locate.py`'s `_load_slice_full`, which merges it
    # back in at read time -- a caller never sees a behaviour difference).
    assert max(sizes) <= 200_000, f"max slice {max(sizes)}B exceeds the 200 KB cap"


def test_asset_ag_prefers_owned_by_agency_edge_over_name_match(built):
    """MED fix: gate:hii_watergate:27 has an OWNED_BY_AGENCY edge to AG_HII in
    the shipped graph but no owner-name match, so it must no longer come out
    as ag=null."""
    import networkx as nx

    g = nx.read_graphml(str(GRAPH_PATH))
    if "gate:hii_watergate:27" not in g.nodes:
        pytest.skip("gate:hii_watergate:27 not present in this checkout's graph")
    _result, files = built
    found = False
    for name, text in files.items():
        if not name.startswith("province_"):
            continue
        slice_obj = json.loads(text)
        for row in slice_obj["a"]:
            if row[0] == "gate:hii_watergate:27":
                found = True
                assert row[5] == "AG_HII", f"expected ag=AG_HII via OWNED_BY_AGENCY, got {row[5]!r}"
    assert found, "gate:hii_watergate:27 not present in any committed slice"


def test_global_gaps_mentions_rain_gauge_class_mislabel(built):
    result, files = built
    index = json.loads(files["index.json"])
    assert any("thaiwater_rain" in g for g in index["gaps"])


def test_province_en_names_populated_from_committed_snapshot(built):
    """MED fix: sources/province_names_en.yaml (committed) must give every one
    of the 77 Thai provinces a non-null `en`, the two non-Thailand codes stay
    null by design."""
    _result, files = built
    index = json.loads(files["index.json"])
    assert index["prov"]["13"]["en"] == "Pathum Thani"
    assert index["prov"]["10"]["en"] == "Bangkok"
    assert index["prov"]["50"]["en"] == "Chiang Mai"
    missing = [c for c, m in index["prov"].items() if not m.get("en") and c not in ("99", "10499")]
    assert not missing, f"provinces missing an en name: {missing}"


def test_pathum_gate_known_gap_is_recorded():
    """F3/gap tie-back: Pathum's hii_watergate gates have no IN_PROVINCE edge
    and the committed slice must say so, not silently drop them."""
    path = COMMITTED_INDEX_DIR / "province_13.json"
    if not path.exists():
        pytest.skip("output/kg_index/province_13.json not committed in this checkout")
    slice_obj = json.loads(path.read_text(encoding="utf-8"))
    gate_rows = [r for r in slice_obj["a"] if r[2] == "gate"]
    assert gate_rows, "province_13.json has no gate rows at all"
    assert any(r[9] == "b" for r in gate_rows), (
        "no box-placed (pv=b) gate in province_13.json -- expected per F3/F1 finding"
    )
    assert any("IN_PROVINCE" in g for g in slice_obj["gaps"])
