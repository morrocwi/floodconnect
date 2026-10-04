"""Tests for tools/harvest/bma_drain_pipes.py (CSV parser) and tools/kg/build_kg.py's
BMA drain-pipe DRAINS_TO topology loader (build 3, 2026-09-27 -- founder ask "เอาเลย
สร้าง floodconnect topology จากสิ่งที่เรามี"). Uses a small local fixture, never the
real 2,903-row archive, and never hits the network.

Regression coverage for a real bug found and fixed while building this: build_kg's
generic `slug()` helper strips every character outside [a-z0-9] after lowercasing, so a
Thai-only junction name (almost all of them) collapsed to the literal node id
"drainjunction:unknown" for EVERY distinct name -- silently merging hundreds of
different real-world junctions into one node. Fixed by keying junction ids off an
insertion-order sequence number instead of slug(name); the fixture below has two
distinct all-Thai junction names specifically to catch a regression of that bug.
"""
from pathlib import Path

import pytest

from tools.harvest import bma_drain_pipes
from tools.kg import build_kg

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DRAIN = REPO_ROOT / "tests" / "fixtures" / "bma_drain_pipe_sample.csv"
FIXTURE_PIPE_JACKING = REPO_ROOT / "tests" / "fixtures" / "bma_pipe_jacking_sample.csv"


def test_parse_drain_pipe_csv_splits_by_side_and_skips_blank_rows():
    rows = bma_drain_pipes.parse_drain_pipe_csv(FIXTURE_DRAIN)
    # fixture row 2 has every side blank -- must produce ZERO rows, not a fabricated one
    ids = {r["segment_id"] for r in rows}
    assert not any(sid.startswith("seg2_") for sid in ids)
    # fixture row 1 has R+L data -> two rows
    row1_sides = {r["side"] for r in rows if r["segment_id"].startswith("seg1_")}
    assert row1_sides == {"R", "L"}
    r1r = next(r for r in rows if r["segment_id"] == "seg1_R")
    assert r1r["district"] == "ดุสิต"
    assert r1r["pipe_from"] == "ถนนเอ"
    assert r1r["pipe_to"] == "คลองทดสอบ"
    assert r1r["dimension"] == "1"
    assert r1r["length_m"] == 100.0
    assert r1r["type"] == "ท่อกลม"
    assert r1r["tag"] == "VERIFIED-from-official-csv"
    assert r1r["coords"] is None  # never geocoded


def test_parse_drain_pipe_csv_never_fabricates_coords():
    rows = bma_drain_pipes.parse_drain_pipe_csv(FIXTURE_DRAIN)
    assert all(r["coords"] is None for r in rows)


def test_parse_pipe_jacking_csv_converts_utm_to_wgs84():
    # `pyproj` is an optional "geo" extra (pyproject.toml), not installed by the
    # `dev`/`mcp` extras a fresh `pip install -e .[dev,mcp]` pulls in -- skip rather
    # than fail on an environment that never installed it.
    pytest.importorskip("pyproj")
    rows = bma_drain_pipes.parse_pipe_jacking_csv(FIXTURE_PIPE_JACKING)
    assert len(rows) == 1
    r = rows[0]
    assert r["district"] == "Ratchathewi"
    assert r["place"] == "บ่อสูบน้ำทดสอบ"
    # Bangkok bbox sanity, not an exact-value assertion (pyproj version/datum grid
    # could shift the last decimal places) -- this is a CRS conversion of the source's
    # own coordinate, not an independent geocode.
    assert 13.0 < r["lat"] < 14.0
    assert 100.0 < r["lon"] < 101.0
    assert r["power_kw"] == 8.9
    assert r["tag"] == "VERIFIED-from-official-csv"


def _write_bma_drain_pipes_yaml(tmp_path, drain_rows):
    import yaml
    p = tmp_path / "bma_drain_pipes.yaml"
    p.write_text(yaml.safe_dump({"drain_pipe_rows": drain_rows, "sump_wells": []},
                                 allow_unicode=True), encoding="utf-8")
    return p


def test_load_bma_drain_pipes_never_collapses_distinct_thai_junction_names(tmp_path):
    """Regression test for the slug()-collision bug described in this file's module
    docstring: two rows with two DIFFERENT all-Thai PIPE_TO names must produce TWO
    distinct junction nodes, not one merged 'unknown' node."""
    rows = [
        {"segment_id": "segA_R", "district": "ดุสิต", "road": "ถนนเอ",
         "pipe_from": None, "pipe_to": "คลองทดสอบหนึ่ง", "side": "R",
         "dimension": "1", "length_m": 100.0, "type": "ท่อกลม",
         "tag": "VERIFIED-from-official-csv", "coords": None, "source": "test"},
        {"segment_id": "segB_R", "district": "ดุสิต", "road": "ถนนบี",
         "pipe_from": None, "pipe_to": "คลองทดสอบสอง", "side": "R",
         "dimension": "1", "length_m": 50.0, "type": "ท่อกลม",
         "tag": "VERIFIED-from-official-csv", "coords": None, "source": "test"},
    ]
    path = _write_bma_drain_pipes_yaml(tmp_path, rows)
    seg_nodes, junction_nodes, edges, report = build_kg.load_bma_drain_pipes(path, {})

    junction_ids = {nid for nid, _ in junction_nodes}
    assert len(junction_ids) == len(junction_nodes), "junction ids must be unique"
    names_by_id = {nid: attrs["name_th"] for nid, attrs in junction_nodes}
    assert set(names_by_id.values()) == {"คลองทดสอบหนึ่ง", "คลองทดสอบสอง"}
    # the two names must map to TWO DIFFERENT node ids (this is exactly what the
    # slug()-collision bug broke -- both used to become "drainjunction:unknown")
    assert len(set(names_by_id.keys())) == 2
    assert report["junctions"] == 2


def test_load_bma_drain_pipes_wires_drains_to_only_where_field_present():
    rows = [
        {"segment_id": "segC_R", "district": "ดุสิต", "road": None,
         "pipe_from": None, "pipe_to": "คลองซี", "side": "R",
         "dimension": "1", "length_m": 10.0, "type": "ท่อกลม",
         "tag": "VERIFIED-from-official-csv", "coords": None, "source": "test"},
        {"segment_id": "segD_R", "district": "ดุสิต", "road": None,
         "pipe_from": None, "pipe_to": None, "side": "R",
         "dimension": "1", "length_m": 10.0, "type": "ท่อกลม",
         "tag": "VERIFIED-from-official-csv", "coords": None, "source": "test"},
    ]
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = _write_bma_drain_pipes_yaml(Path(td), rows)
        seg_nodes, junction_nodes, edges, report = build_kg.load_bma_drain_pipes(path, {})
    # segD has no pipe_from/pipe_to at all -- must produce zero DRAINS_TO edges for it
    seg_d_edges = [e for e in edges if e[0] == "drainseg:segD_R" or e[1] == "drainseg:segD_R"]
    assert seg_d_edges == []
    # segC has a pipe_to only -- exactly one DRAINS_TO edge (segment -> junction)
    seg_c_edges = [e for e in edges if e[0] == "drainseg:segC_R"]
    assert len(seg_c_edges) == 1
    assert seg_c_edges[0][2]["kind"] == "DRAINS_TO"


def test_load_bma_drain_pipes_matches_canal_name_index():
    """A junction whose normalised name is in the canal_name_index gets an EXTRA
    DRAINS_TO edge into that canal node -- never fabricated for names not in the
    index."""
    rows = [
        {"segment_id": "segE_R", "district": "ดุสิต", "road": None,
         "pipe_from": None, "pipe_to": "คลองรู้จัก", "side": "R",
         "dimension": "1", "length_m": 10.0, "type": "ท่อกลม",
         "tag": "VERIFIED-from-official-csv", "coords": None, "source": "test"},
    ]
    canal_index = {build_kg.normalize_canal_name("คลองรู้จัก"): "canal:known_canal"}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = _write_bma_drain_pipes_yaml(Path(td), rows)
        seg_nodes, junction_nodes, edges, report = build_kg.load_bma_drain_pipes(path, canal_index)
    canal_edges = [e for e in edges if e[1] == "canal:known_canal"]
    assert len(canal_edges) == 1
    assert report["canal_matches"] == 1


def test_normalize_canal_name_strips_leading_khlong_and_whitespace():
    assert build_kg.normalize_canal_name("คลองบ้านม้า") == "บ้านม้า"
    assert build_kg.normalize_canal_name("  คลอง วังใหญ่บน  ") == "วังใหญ่บน"
    assert build_kg.normalize_canal_name(None) == ""
    assert build_kg.normalize_canal_name("") == ""
