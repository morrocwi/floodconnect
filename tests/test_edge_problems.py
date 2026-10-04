"""Tests for tools/dag/edge_problems.py (FOUNDER_TASKS item 10).

Self-contained: writes its own tiny synthetic mermaid DAG + a tiny edge_problems.yaml to a
pytest tmp_path (never touching tests/fixtures/, which another worker owns this check) and
only exercises tools/dag/edge_problems.py.
    python3 -m pytest tests/test_edge_problems.py -q
"""
import pytest

from tools.dag.edge_problems import (
    MissingNodeError,
    build_problems_mmd,
    load_rows,
    match_rows_to_edges,
    index_edge_lines,
)

FIXTURE_MMD = """
flowchart TD
  AG_TOP["Top authority"]
  AG_A["Agency A"]
  AG_B["Agency B"]
  AG_LONE["Unconnected agency"]
  DC_X["Decision X"]
  AG_TOP -->|"CMD:R"| AG_A
  AG_A -->|"CMD:R"| DC_X
  AG_B -->|"CMD:R"| DC_X
""".strip()

ROWS_MATCHED = [
    {
        "src_id": "AG_A",
        "dst_id": "DC_X",
        "problem_name_academic": "Institutional fragmentation / jurisdictional overlap",
        "problem_th": "test",
        "typical_failure": "test",
        "evidence": [],
        "severity_tag": "MEASURED-on-graph",
        "open_questions": "none",
    },
    {
        "src_id": "AG_B",
        "dst_id": "DC_X",
        "problem_name_academic": "Institutional fragmentation / jurisdictional overlap",
        "problem_th": "test",
        "typical_failure": "test",
        "evidence": [],
        "severity_tag": "MEASURED-on-graph",
        "open_questions": "none",
    },
]

ROW_NO_EDGE = {
    "src_id": "AG_TOP",
    "dst_id": "AG_LONE",
    "problem_name_academic": "Risk-communication deficit model",
    "problem_th": "test",
    "typical_failure": "test",
    "evidence": [],
    "severity_tag": "RELAYED-OPINION",
    "open_questions": "none",
}

ROW_MISSING_NODE = {
    "src_id": "AG_TOP",
    "dst_id": "AG_DOES_NOT_EXIST",
    "problem_name_academic": "should never render",
    "problem_th": "test",
    "typical_failure": "test",
    "evidence": [],
    "severity_tag": "OPEN",
    "open_questions": "none",
}


def _write_dag(tmp_path):
    p = tmp_path / "dag.mmd"
    p.write_text(FIXTURE_MMD, encoding="utf-8")
    return p


def test_matched_edges_get_dashed_red_linkstyle(tmp_path):
    dag_path = _write_dag(tmp_path)
    out_text, unmatched = build_problems_mmd(dag_path, ROWS_MATCHED)
    assert unmatched == []
    # both AG_A->DC_X and AG_B->DC_X should be dashed-red styled
    style_lines = [ln for ln in out_text.splitlines() if ln.startswith("linkStyle ")]
    assert len(style_lines) == 2
    assert "⚠ Institutional fragmentation" in out_text
    # the third edge (AG_TOP->AG_A) must be untouched
    assert 'AG_TOP -->|"CMD:R"| AG_A' in out_text


def test_no_edge_row_is_reported_not_dropped_and_not_an_error(tmp_path):
    dag_path = _write_dag(tmp_path)
    out_text, unmatched = build_problems_mmd(dag_path, [ROW_NO_EDGE])
    assert len(unmatched) == 1
    assert unmatched[0]["src_id"] == "AG_TOP"
    # no edge exists AG_TOP->AG_LONE, so no linkStyle line should be emitted for it
    style_lines = [ln for ln in out_text.splitlines() if ln.startswith("linkStyle ")]
    assert style_lines == []


def test_missing_node_fails_loudly(tmp_path):
    dag_path = _write_dag(tmp_path)
    with pytest.raises(MissingNodeError):
        build_problems_mmd(dag_path, [ROW_MISSING_NODE])


def test_index_edge_lines_matches_mermaid_link_order(tmp_path):
    dag_path = _write_dag(tmp_path)
    edges = index_edge_lines(dag_path)
    assert edges == [
        (0, "AG_TOP", "AG_A", "COMMANDS"),
        (1, "AG_A", "DC_X", "COMMANDS"),
        (2, "AG_B", "DC_X", "COMMANDS"),
    ]


def test_load_rows_reads_yaml(tmp_path):
    yaml_path = tmp_path / "edge_problems.yaml"
    yaml_path.write_text(
        "rows:\n"
        "  - src_id: \"A\"\n"
        "    dst_id: \"B\"\n"
        "    problem_name_academic: \"x\"\n",
        encoding="utf-8",
    )
    rows = load_rows(yaml_path)
    assert len(rows) == 1
    assert rows[0]["src_id"] == "A"
