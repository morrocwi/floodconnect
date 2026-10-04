#!/usr/bin/env python3
"""
Edge-level "typical problems" layer over the governance DAG (FOUNDER_TASKS item 10).

Founder's task, verbatim: "ทำ DAG ecosystem หน่วยงานรัฐต่างๆ ถึงประชาชน ให้ครบเป็นองค์รวมระบบเดียว ด้วย
DAG พร้อมระบุปัญหาที่มักพบระหว่าง node" (+ "จัดเรื่องนี้เข้า todolist ด้วย")

This module joins docs/knowledge/edge_problems.yaml (curated rows: an (src_id, dst_id) pair,
its academic problem name, and evidence) onto the SAME parsed graph tools/dag/bottlenecks.py
uses (imported, never copied), then emits an annotated copy of the full state->citizen DAG:
docs/knowledge/water_system_dag_problems.mmd -- identical to water_system_dag.mmd except
edges that match a row in edge_problems.yaml are additionally styled dashed red
(mermaid `linkStyle`) and their label gets a short "⚠ <problem name>" suffix.

Two kinds of "problem" rows are supported:
  - matched-edge rows: src_id and dst_id are BOTH endpoints of a real edge already in the
    DAG (any edge kind) -- these get the dashed-red linkStyle treatment above.
  - no-edge rows: src_id and dst_id both exist as NODES in the DAG, but no edge connects
    them -- this documents a *missing* coordination/data channel, which is itself one of
    the "typical problems between nodes" the founder asked for (see THAI_SOCIETY_PROBLEMS_
    ACADEMIC.md problem 2/5). These cannot be dash-styled (there is no line to dash) so they
    are reported separately, never silently dropped.

FAIL LOUDLY (non-zero exit, no .mmd written) if any row's src_id or dst_id is not even a
NODE in the parsed DAG -- that is a real data error in edge_problems.yaml, not a documented
gap.

Usage:
    python3 -m tools.dag.edge_problems [--dag PATH] [--rows PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
import networkx as nx

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(HERE))

from tools.dag.bottlenecks import parse_dag  # noqa: E402
from tools.kg.build_kg import MERMAID_EDGE_RE, KIND_RENAME  # noqa: E402

DEFAULT_DAG_PATH = HERE / "docs" / "knowledge" / "water_system_dag.mmd"
DEFAULT_ROWS_PATH = HERE / "docs" / "knowledge" / "edge_problems.yaml"
DEFAULT_OUT_PATH = HERE / "docs" / "knowledge" / "water_system_dag_problems.mmd"

PROBLEM_STYLE = "stroke:#c0392b,stroke-width:3px,stroke-dasharray:4 3"


def load_rows(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("rows", [])


class MissingNodeError(Exception):
    """Raised when an edge_problems.yaml row references a node id absent from the DAG."""


def validate_rows(rows: list[dict], G: nx.MultiDiGraph) -> None:
    """Fail loudly (raise) if any row's src_id/dst_id is not a node in G at all. A row
    whose two nodes exist but share no edge is NOT an error -- see module docstring."""
    missing = []
    for row in rows:
        for key in ("src_id", "dst_id"):
            node_id = row.get(key)
            if node_id and node_id not in G:
                missing.append((row.get("src_id"), row.get("dst_id"), key, node_id))
    if missing:
        lines = [f"  row (src={s!r}, dst={d!r}): {key}={val!r} is not a node in the DAG"
                 for s, d, key, val in missing]
        raise MissingNodeError(
            f"{len(missing)} edge_problems.yaml row(s) reference node ids absent from "
            f"the parsed DAG:\n" + "\n".join(lines)
        )


def index_edge_lines(dag_path: Path) -> list[tuple[int, str, str, str]]:
    """Walk water_system_dag.mmd's lines in order and return, for every edge line
    (in the exact order mermaid itself will number them for `linkStyle`), a tuple of
    (linkStyle_index, u, v, kind). Non-edge lines are skipped. This mirrors exactly how
    mermaid assigns link indices -- 0-based, in source order, across the WHOLE diagram
    (subgraphs do not reset the counter)."""
    out = []
    idx = 0
    for line in dag_path.read_text(encoding="utf-8").splitlines():
        m = MERMAID_EDGE_RE.match(line)
        if not m:
            continue
        u, v = m.group("u"), m.group("v")
        kind_raw = m.group("kind")
        kind = KIND_RENAME.get(kind_raw, kind_raw)
        out.append((idx, u, v, kind))
        idx += 1
    return out


def match_rows_to_edges(rows: list[dict], edge_index: list[tuple[int, str, str, str]]) -> tuple[dict, list[dict]]:
    """Returns (linkstyle_idx -> list of problem names, unmatched_rows). A row matches an
    edge line if its (src_id, dst_id) equals that edge's (u, v) -- edge_kind in the row is
    NOT required to match (a row documents the (u,v) relationship, whichever kind(s) the
    graph actually draws between them)."""
    by_pair: dict[tuple[str, str], list[int]] = {}
    for idx, u, v, _kind in edge_index:
        by_pair.setdefault((u, v), []).append(idx)

    style_targets: dict[int, list[str]] = {}
    unmatched: list[dict] = []
    for row in rows:
        pair = (row.get("src_id"), row.get("dst_id"))
        idxs = by_pair.get(pair)
        if not idxs:
            unmatched.append(row)
            continue
        for i in idxs:
            style_targets.setdefault(i, []).append(row["problem_name_academic"])
    return style_targets, unmatched


def annotate_labels(dag_path: Path, style_targets: dict[int, list[str]]) -> list[str]:
    """Return the full .mmd file as a list of output lines: edge lines that matched a
    problem get a short "⚠ <name>" suffix appended to their label (first problem name
    only, to keep the diagram legible -- the full list stays in edge_problems.yaml)."""
    out_lines = []
    idx = 0
    for line in dag_path.read_text(encoding="utf-8").splitlines():
        m = MERMAID_EDGE_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        if idx in style_targets:
            names = style_targets[idx]
            short = names[0]
            label_start = line.index('|"') + 2
            label_end = line.index('"|', label_start)
            old_label = line[label_start:label_end]
            new_label = f"{old_label} / ⚠ {short}"
            line = line[:label_start] + new_label + line[label_end:]
        out_lines.append(line)
        idx += 1
    return out_lines


def build_problems_mmd(dag_path: Path, rows: list[dict]) -> tuple[str, list[dict]]:
    G = parse_dag(dag_path)
    validate_rows(rows, G)
    edge_index = index_edge_lines(dag_path)
    style_targets, unmatched = match_rows_to_edges(rows, edge_index)
    lines = annotate_labels(dag_path, style_targets)

    header = [
        "%% AUTO-GENERATED by tools/dag/edge_problems.py -- do not hand-edit.",
        "%% Source graph: docs/knowledge/water_system_dag.mmd + docs/knowledge/edge_problems.yaml",
        "%% Edges with a documented typical problem are styled dashed red (linkStyle) and",
        "%% carry a short ⚠ <problem name> suffix in their label. Full evidence per edge",
        "%% lives in edge_problems.yaml (and, for unmatched/no-edge rows, in the report this",
        "%% script prints -- see docs/knowledge/WATER_SYSTEM_DAG.md 'ปัญหาที่มักพบระหว่าง node'.",
        "",
    ]
    style_lines = [f"linkStyle {i} {PROBLEM_STYLE}" for i in sorted(style_targets)]
    out_text = "\n".join(header + lines + [""] + style_lines) + "\n"
    return out_text, unmatched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dag", default=str(DEFAULT_DAG_PATH))
    ap.add_argument("--rows", default=str(DEFAULT_ROWS_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    args = ap.parse_args()

    dag_path = Path(args.dag)
    rows_path = Path(args.rows)
    out_path = Path(args.out)

    rows = load_rows(rows_path)
    try:
        out_text, unmatched = build_problems_mmd(dag_path, rows)
    except MissingNodeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")

    print(f"Parsed {len(rows)} edge_problems.yaml rows against {dag_path}")
    print(f"Wrote {out_path}")
    if unmatched:
        print(f"\n{len(unmatched)} row(s) have both endpoints as real nodes but NO edge "
              f"between them in the DAG (documented gap, not an error -- see module docstring):")
        for row in unmatched:
            # a "dst_prefix" row (e.g. src_id="AG_DDPM", dst_prefix="PP_") documents a
            # whole CLASS of missing edges rather than one (src_id, dst_id) pair -- it
            # has no dst_id key at all, by design (see AGENTS.md ss8, "PP_ prefix row").
            dst_label = row.get("dst_id") or f"{row.get('dst_prefix', '?')}* (class, no single node)"
            print(f"  {row['src_id']} -> {dst_label}: {row['problem_name_academic']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
