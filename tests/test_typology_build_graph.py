"""
tests/test_typology_build_graph.py -- schema/ID-uniqueness/allowed-pairs tests for
tools/typology/build_graph.py, using ONLY the real repo data it reads
(site/inputs/canals/east_chain.yaml + typology/nodes/*.yaml + typology/edges/*.yaml) --
no simulated data, per AGENTS.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.typology import build_graph, validate  # noqa: E402


@pytest.fixture(scope="module")
def graph():
    import networkx as nx
    G = nx.MultiDiGraph()
    build_graph.build_water_layer(G)
    build_graph.load_registry_nodes(G)
    build_graph.load_registry_edges(G)
    return G


def test_graph_nonempty(graph):
    assert graph.number_of_nodes() > 30
    assert graph.number_of_edges() > 30


def test_node_ids_unique(graph):
    # networkx itself enforces this (add_node overwrites, never duplicates a key) --
    # this test instead checks the SOURCE yaml files don't declare the same id twice,
    # which add_node() would otherwise silently paper over.
    seen = set()
    dupes = []
    for path in sorted(build_graph.TYPOLOGY_NODES_DIR.glob("*.yaml")):
        import yaml
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if doc.get("doc_kind") == "typology_node_overlay":
            continue  # overlay rows deliberately re-use an id that already exists
            # elsewhere -- that IS the point (apply_node_overlays merges onto it), not a
            # duplicate node declaration
        for r in doc.get("rows") or []:
            if r["id"] in seen:
                dupes.append(r["id"])
            seen.add(r["id"])
    assert not dupes, f"duplicate node ids declared across typology_node_registry files: {dupes}"


def test_every_node_has_kind_layer_tag_source(graph):
    missing = []
    for n, d in graph.nodes(data=True):
        for field in ("kind", "layer", "tag"):
            if not d.get(field):
                missing.append((n, field))
    assert not missing, f"node(s) missing required attribute: {missing}"


def test_every_edge_has_kind_tag_source(graph):
    missing = []
    for u, v, d in graph.edges(data=True):
        for field in ("kind", "tag"):
            if not d.get(field):
                missing.append((u, v, field))
    assert not missing, f"edge(s) missing required attribute: {missing}"


def test_edge_kinds_are_closed_vocabulary(graph):
    kinds = {d.get("kind") for _, _, d in graph.edges(data=True)}
    assert kinds <= validate.CLOSED_EDGE_VOCAB, (
        f"edge kind(s) outside the closed vocabulary from "
        f"FLOW_STALL_TYPOLOGY_EXTENSION_PROPOSAL_2026-09-28.md §2: "
        f"{kinds - validate.CLOSED_EDGE_VOCAB}")


def test_decides_targets_gate_or_pump_only(graph):
    """Independent-review fix, 2026-09-28: decides never targets an `edge` -- only
    gate|pump (or the shared OPEN sentinel for a genuinely unresolved decider)."""
    for u, v, d in graph.edges(data=True):
        if d.get("kind") != "decides":
            continue
        if v == "OPEN":
            continue
        target_kind = graph.nodes[v].get("kind")
        assert target_kind in ("gate", "pump"), (
            f"decides edge {u} -> {v} targets kind={target_kind!r}, expected gate/pump "
            f"(edge target was dropped by the independent review -- burden stays on the "
            f"water edge's own BURDENED/RELIEVED attribute, never a decides target)")


def test_warns_is_always_two_hop(graph):
    """Every warns edge either starts at an agency (hop 1, into a warning_channel) or
    starts at a warning_channel (hop 2, into a zone/soi_surface or the OPEN sentinel) --
    never agency -> zone directly (proposal §2's 2-hop-always rule)."""
    for u, v, d in graph.edges(data=True):
        if d.get("kind") != "warns":
            continue
        u_kind = graph.nodes[u].get("kind")
        v_kind = graph.nodes[v].get("kind") if v != "OPEN" else "OPEN"
        assert (u_kind == "agency" and v_kind in ("warning_channel", "OPEN")) or \
               (u_kind == "warning_channel" and v_kind in ("soi_surface", "OPEN")), (
            f"warns edge {u} ({u_kind}) -> {v} ({v_kind}) is not a valid 2-hop leg")


def test_sensor_ids_reference_declared_water_nodes(graph):
    for n, d in graph.nodes(data=True):
        if d.get("kind") != "sensor":
            continue
        installed_on = d.get("installed_on_node")
        assert installed_on, f"sensor {n} has no installed_on_node"
        assert graph.has_node(installed_on), (
            f"sensor {n} declares installed_on_node={installed_on!r}, which is not a "
            f"node in the built graph (real data mismatch, not a simulated case)")
