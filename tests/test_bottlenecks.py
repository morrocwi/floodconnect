"""Tests for tools/dag/bottlenecks.py (FOUNDER_TASKS item 7).

This file is new and self-contained: it writes its own tiny synthetic mermaid DAG to a
pytest tmp_path (never touching tests/fixtures/) and only exercises
tools/dag/bottlenecks.py -- it does not import or depend on tools/kg/build_kg.py's own
test coverage. Run in isolation with:
    python3 -m pytest tests/test_bottlenecks.py -q
"""
from pathlib import Path

from tools.dag.bottlenecks import (
    conflicting_commanders,
    ownership_gaps,
    parse_dag,
    shares_without_arbitration,
    single_points_of_failure,
)

# Synthetic 7-node DAG covering rules 1-4:
#   AG_TOP  -- commands both AG_A and AG_C (common commander => arbitration exists)
#   AG_A    -- SHARES with AG_B, but AG_B has no commander => no arbitration path
#   AG_B, AG_C -- both COMMAND and OWN AS_PUMP1 => conflicting commanders + contested owner
#   DT_D1   -- has no OWNS edge at all => unowned resource
#   DT_D1 -> AS_PUMP1 -> PP_P1 is the ONLY path from any DT_ node to any PP_ node, so
#   AS_PUMP1 must be the single point of failure cutting DT->PP connectivity.
FIXTURE_MMD = """
flowchart TD
  AG_TOP["Top authority"]
  AG_A["Agency A"]
  AG_B["Agency B"]
  AG_C["Agency C"]
  AS_PUMP1["Pump station 1 (pump)"]
  DT_D1["Data feed D1"]
  PP_P1["Citizens P1"]
  AG_TOP -->|"CMD:R"| AG_A
  AG_TOP -->|"CMD:R"| AG_C
  AG_C -->|"SHARES:R"| AG_A
  AG_A -.->|"SHARES:O"| AG_B
  AG_B -->|"CMD:R"| AS_PUMP1
  AG_C -->|"CMD:R"| AS_PUMP1
  AG_B -->|"OWNS:R"| AS_PUMP1
  AG_C -->|"OWNS:R"| AS_PUMP1
  DT_D1 -->|"DATA:R"| AS_PUMP1
  AS_PUMP1 -->|"WATER:R"| PP_P1
"""


def _fixture_graph(tmp_path: Path):
    mmd_path = tmp_path / "synthetic_dag.mmd"
    mmd_path.write_text(FIXTURE_MMD, encoding="utf-8")
    return parse_dag(mmd_path)


def test_parses_expected_nodes_and_edges(tmp_path):
    G = _fixture_graph(tmp_path)
    assert G.number_of_nodes() == 7
    # 10 edge lines in the fixture
    assert G.number_of_edges() == 10


def test_rule1_conflicting_commanders(tmp_path):
    G = _fixture_graph(tmp_path)
    rows = conflicting_commanders(G)
    nodes = {r["node"] for r in rows}
    assert "AS_PUMP1" in nodes
    row = next(r for r in rows if r["node"] == "AS_PUMP1")
    assert set(row["commanders"]) == {"AG_B", "AG_C"}


def test_rule2_ownership_gaps(tmp_path):
    G = _fixture_graph(tmp_path)
    gaps = ownership_gaps(G)
    unowned_nodes = {r["node"] for r in gaps["unowned"]}
    contested_nodes = {r["node"]: r for r in gaps["contested"]}
    assert "DT_D1" in unowned_nodes
    assert "AS_PUMP1" in contested_nodes
    assert set(contested_nodes["AS_PUMP1"]["owners"]) == {"AG_B", "AG_C"}


def test_rule3_shares_without_arbitration(tmp_path):
    G = _fixture_graph(tmp_path)
    flagged = shares_without_arbitration(G)
    pairs = {(r["u"], r["v"]) for r in flagged}
    # AG_A <-> AG_B has no common commander => flagged
    assert ("AG_A", "AG_B") in pairs
    # AG_C -> AG_A both commanded by AG_TOP => NOT flagged (arbitration exists)
    assert ("AG_C", "AG_A") not in pairs


def test_rule4_single_point_of_failure(tmp_path):
    G = _fixture_graph(tmp_path)
    spofs = single_points_of_failure(G)
    nodes_cut = {r["node"]: r["cuts"] for r in spofs}
    assert "AS_PUMP1" in nodes_cut
    assert any("DT_to_PP" in c for c in nodes_cut["AS_PUMP1"])
