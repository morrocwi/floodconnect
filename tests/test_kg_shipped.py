"""Regression tests over the SHIPPED committed graph, output/thailand_water_kg.graphml --
never a fresh build. Guards the actual artifact that ships, not just the builder code
(a committed KG once silently shipped with ZERO
IN_SUBBASIN edges even though the builder code itself was fine -- the DWR polygon
archive was simply missing from that build environment). Skips cleanly (never fails)
when the shipped file is absent from a given checkout, matching every other
real-artifact test in this suite (see tests/test_kg_build.py's own module-level skip)."""
import sys
from pathlib import Path

import networkx as nx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from tools.kg import build_kg  # noqa: E402

SHIPPED_GRAPHML = REPO_ROOT / "output" / "thailand_water_kg.graphml"
RIVER_FLOW_GRAPHML = REPO_ROOT / "output" / "thailand_river_flow.graphml"


@pytest.fixture(scope="module")
def shipped_graph():
    if not SHIPPED_GRAPHML.is_file():
        pytest.skip("output/thailand_water_kg.graphml not present in this checkout")
    return nx.read_graphml(SHIPPED_GRAPHML)


def test_mekong_reach_near_nong_khai_is_main_stem_on_the_real_graph():
    """Regression for a fixed restart-on-break bug: the Mekong reach near
    17.88N,102.74E (riverreach:41246335, the Nong Khai area, main_river_id 41392598,
    discharge 4504.2 cms) sits in a weakly-connected component of its own
    main_river_id group that the pre-fix single walk never reached at all (the walk
    started from a Cambodia-side member and ran out of upstream candidates at the
    clip-severed border gap) -- MUST be main_stem=True once the restart-on-break fix
    (compute_main_stem's weakly-connected-component walk) is applied. Lives here, not
    in tests/test_kg_build.py, because that whole module skips without the gitignored
    data/observations.sqlite -- output/thailand_river_flow.graphml IS committed, so
    this regression must still run on a fresh clone."""
    if not RIVER_FLOW_GRAPHML.is_file():
        pytest.skip("output/thailand_river_flow.graphml not present in this checkout")
    nodes, _edges = build_kg.load_river_reaches(RIVER_FLOW_GRAPHML)
    by_id = dict(nodes)
    assert "riverreach:41246335" in by_id, "fixture reach missing from the real graph"
    assert by_id["riverreach:41246335"]["main_stem"] is True


def test_shipped_graph_has_in_subbasin_edges(shipped_graph):
    """The shipped graph must never ship with zero
    IN_SUBBASIN edges -- that silently drops the asset -> sub-basin -> basin link the
    upstream/accountability walk depends on. Not an exact count (the real DWR polygon
    coverage can shift a little build to build), just > 0, which the pre-fix regression
    violated outright (0 edges shipped)."""
    n = sum(1 for _u, _v, d in shipped_graph.edges(data=True) if d.get("kind") == "IN_SUBBASIN")
    assert n > 0, (
        "shipped output/thailand_water_kg.graphml has ZERO IN_SUBBASIN edges -- rebuild "
        "with raw/gis/dwr_subbasin/ present (never ship a build made with "
        "--allow-missing-subbasin)"
    )
