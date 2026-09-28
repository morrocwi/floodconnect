#!/usr/bin/env python3
"""
community_dag.py -- Community self-help DAG for flood response.

This module is an OPERATIONAL ROUTING READOUT, not a flood forecast and not a flood-risk
score. It models how a person/household can escalate through a community mutual-aid
network toward a field-verified external safe node.

Design rule:
    household -> buddy_cell -> zone -> internal_safe -> egress -> external_safe

Edges may skip layers, but MUST always move to a strictly higher layer. Therefore every
declared graph is a DAG by construction.

Routing discipline:
1) hard constraints first (unknown/blocked/stale/unverified routes are not routable);
2) among feasible paths use a lexicographic ordering -- no weighted risk score.

The module intentionally refuses to invent safe routes. A target is eligible only when
it is explicitly field-verified, fresh, SAFE, has declared capacity, and satisfies the
requested service needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


KIND_LAYER = {
    "household": 0,
    "buddy_cell": 1,
    "zone": 2,
    "internal_safe": 3,
    "egress": 4,
    "external_safe": 5,
    "supply_point": 5,
}

NODE_STATUS = {"SAFE", "DEGRADED", "UNSAFE", "UNKNOWN"}
EDGE_STATUS = {"OPEN", "ASSISTED", "BLOCKED", "UNKNOWN"}
EDGE_SAFETY = {"CLEAR", "CAUTION", "BLOCKED", "UNKNOWN"}


@dataclass(frozen=True)
class RouteResult:
    found: bool
    path: tuple[str, ...] = ()
    target: str | None = None
    score: tuple[Any, ...] | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "path": list(self.path),
            "target": self.target,
            "score": list(self.score) if self.score is not None else None,
            "reason": self.reason,
        }


def load_document(path: str | Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load a YAML DAG document")
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _nodes(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = doc.get("nodes") or {}
    if not isinstance(raw, dict):
        raise ValueError("nodes must be a mapping of node_id -> definition")
    return raw


def _edges(doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = doc.get("edges") or []
    if not isinstance(raw, list):
        raise ValueError("edges must be a list")
    return raw


def validate_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Validate schema-level DAG rules.

    Returns {valid, errors, warnings, topological_order}. UNKNOWN operational state is
    allowed in the declaration (useful for an unverified template) but such nodes/edges
    are not routable by find_safe_route().
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        nodes = _nodes(doc)
        edges = _edges(doc)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": [],
                "topological_order": []}

    for node_id, node in nodes.items():
        kind = node.get("kind")
        layer = node.get("layer")
        if kind not in KIND_LAYER:
            errors.append(f"{node_id}: unknown kind {kind!r}")
            continue
        if layer != KIND_LAYER[kind]:
            errors.append(
                f"{node_id}: layer {layer!r} does not match kind {kind!r} "
                f"(expected {KIND_LAYER[kind]})"
            )
        status = node.get("status", "UNKNOWN")
        if status not in NODE_STATUS:
            errors.append(f"{node_id}: invalid node status {status!r}")
        if node.get("fresh") is not True:
            warnings.append(f"{node_id}: not fresh; it will not be used as a route target/transit")
        if kind == "external_safe" and not node.get("verified_safe", False):
            warnings.append(f"{node_id}: external safe node is not field-verified")

    seen_edge_ids: set[str] = set()
    for i, edge in enumerate(edges):
        edge_id = edge.get("id") or f"edge[{i}]"
        if edge_id in seen_edge_ids:
            errors.append(f"duplicate edge id: {edge_id}")
        seen_edge_ids.add(edge_id)

        u, v = edge.get("from"), edge.get("to")
        if u not in nodes or v not in nodes:
            errors.append(f"{edge_id}: unknown endpoint {u!r}->{v!r}")
            continue
        if u == v:
            errors.append(f"{edge_id}: self-loop is not allowed")
            continue

        lu, lv = nodes[u].get("layer"), nodes[v].get("layer")
        if isinstance(lu, int) and isinstance(lv, int) and not (lv > lu):
            errors.append(
                f"{edge_id}: DAG layer rule violated ({u}:{lu} -> {v}:{lv}); "
                "destination layer must be strictly higher"
            )

        if edge.get("status", "UNKNOWN") not in EDGE_STATUS:
            errors.append(f"{edge_id}: invalid edge status {edge.get('status')!r}")
        if edge.get("safety", "UNKNOWN") not in EDGE_SAFETY:
            errors.append(f"{edge_id}: invalid edge safety {edge.get('safety')!r}")
        if edge.get("fresh") is not True:
            warnings.append(f"{edge_id}: not fresh; it will not be routed")
        if edge.get("field_verified") is not True:
            warnings.append(f"{edge_id}: not field-verified; it will not be routed")

    topo, cycle_error = topological_order(nodes, edges)
    if cycle_error:
        errors.append(cycle_error)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "topological_order": topo,
    }


def topological_order(
    nodes: dict[str, dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> tuple[list[str], str | None]:
    """Kahn topological sort; returns (order, error)."""
    indegree = {node_id: 0 for node_id in nodes}
    outgoing = {node_id: [] for node_id in nodes}
    for edge in edges:
        u, v = edge.get("from"), edge.get("to")
        if u not in nodes or v not in nodes:
            continue
        outgoing[u].append(v)
        indegree[v] += 1

    queue = sorted([n for n, d in indegree.items() if d == 0])
    out: list[str] = []
    while queue:
        u = queue.pop(0)
        out.append(u)
        for v in outgoing[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
                queue.sort()

    if len(out) != len(nodes):
        return out, "graph contains a cycle"
    return out, None


def _free_capacity(node: dict[str, Any]) -> int | None:
    cap = node.get("capacity_persons")
    occ = node.get("occupied_persons")
    if cap is None:
        return None
    if occ is None:
        occ = 0
    try:
        return int(cap) - int(occ)
    except (TypeError, ValueError):
        return None


def _node_services_ok(node: dict[str, Any], needs: set[str]) -> bool:
    have = set(node.get("services") or [])
    return needs.issubset(have)


def _target_ok(node: dict[str, Any], group_size: int, needs: set[str]) -> bool:
    if node.get("kind") != "external_safe":
        return False
    if node.get("verified_safe") is not True:
        return False
    if node.get("fresh") is not True:
        return False
    if node.get("status") != "SAFE":
        return False
    free = _free_capacity(node)
    if free is None or free < group_size:
        return False
    return _node_services_ok(node, needs)


def _transit_node_ok(node: dict[str, Any], group_size: int) -> bool:
    if node.get("fresh") is not True:
        return False
    if node.get("status") not in {"SAFE", "DEGRADED"}:
        return False
    free = _free_capacity(node)
    return free is None or free >= group_size


def _edge_ok(edge: dict[str, Any], group_size: int, mode: str) -> bool:
    if edge.get("field_verified") is not True:
        return False
    if edge.get("fresh") is not True:
        return False
    if edge.get("status") not in {"OPEN", "ASSISTED"}:
        return False
    if edge.get("safety") not in {"CLEAR", "CAUTION"}:
        return False
    modes = set(edge.get("modes") or [])
    if mode not in modes:
        return False
    max_group = edge.get("max_group")
    if max_group is not None:
        try:
            if int(max_group) < group_size:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _rank_key(state: dict[str, Any]) -> tuple[Any, ...]:
    """Lexicographic route ordering.

    Lower is better:
      1 assisted edges
      2 degraded transit nodes
      3 caution edges
      4 unknown capacity constraints
      5 negative bottleneck spare capacity (so larger spare capacity is better)
      6 unknown distance segments
      7 total declared distance
      8 hop count

    This is deliberately NOT a weighted risk score.
    """
    bottleneck = state["bottleneck_slack"]
    bottleneck_term = 0 if bottleneck is None else -bottleneck
    return (
        state["assisted_edges"],
        state["degraded_nodes"],
        state["caution_edges"],
        state["unknown_capacity"],
        bottleneck_term,
        state["unknown_distance"],
        state["distance_m"],
        state["hops"],
    )


def _extend_state(
    state: dict[str, Any],
    edge: dict[str, Any],
    dest: dict[str, Any],
    group_size: int,
) -> dict[str, Any]:
    out = dict(state)
    out["assisted_edges"] += int(edge.get("status") == "ASSISTED")
    out["degraded_nodes"] += int(dest.get("status") == "DEGRADED")
    out["caution_edges"] += int(edge.get("safety") == "CAUTION")
    out["hops"] += 1

    slacks: list[int] = []
    max_group = edge.get("max_group")
    if max_group is None:
        out["unknown_capacity"] += 1
    else:
        try:
            slacks.append(int(max_group) - group_size)
        except (TypeError, ValueError):
            out["unknown_capacity"] += 1

    free = _free_capacity(dest)
    if free is None:
        out["unknown_capacity"] += 1
    else:
        slacks.append(free - group_size)

    if slacks:
        step_bottleneck = min(slacks)
        if out["bottleneck_slack"] is None:
            out["bottleneck_slack"] = step_bottleneck
        else:
            out["bottleneck_slack"] = min(out["bottleneck_slack"], step_bottleneck)

    distance = edge.get("distance_m")
    if distance is None:
        out["unknown_distance"] += 1
    else:
        try:
            out["distance_m"] += float(distance)
        except (TypeError, ValueError):
            out["unknown_distance"] += 1
    return out


def validate_declared_edge_path(
    doc: dict[str, Any],
    start_node: str,
    target_node: str,
    edge_ids: Iterable[str],
    *,
    group_size: int = 1,
    mode: str = "walk",
) -> RouteResult:
    """Validate one explicitly declared movement path with the same hard constraints.

    This is used by resupply/service journeys where the destination is not necessarily
    an external shelter. It does not search or optimize; it validates exactly the edge
    sequence supplied by the caller.
    """
    if group_size < 1:
        return RouteResult(False, reason="group_size must be >= 1")

    check = validate_document(doc)
    if not check["valid"]:
        return RouteResult(False, reason="invalid DAG: " + "; ".join(check["errors"]))

    nodes = _nodes(doc)
    edges = _edges(doc)
    if start_node not in nodes or target_node not in nodes:
        return RouteResult(False, reason="unknown start or target node")

    by_id = {edge.get("id"): edge for edge in edges if edge.get("id")}
    current = start_node
    path = [start_node]
    state = {
        "assisted_edges": 0,
        "degraded_nodes": 0,
        "caution_edges": 0,
        "unknown_capacity": 0,
        "bottleneck_slack": None,
        "unknown_distance": 0,
        "distance_m": 0.0,
        "hops": 0,
    }

    edge_ids = list(edge_ids)
    if not edge_ids:
        return RouteResult(False, reason="empty declared edge path")

    for edge_id in edge_ids:
        edge = by_id.get(edge_id)
        if edge is None:
            return RouteResult(False, reason=f"unknown edge id: {edge_id}")
        if edge.get("from") != current:
            return RouteResult(False, reason=f"non-contiguous edge path at {edge_id}")
        if not _edge_ok(edge, group_size, mode):
            return RouteResult(False, reason=f"edge not feasible: {edge_id}")
        dest_id = edge.get("to")
        dest = nodes.get(dest_id)
        if dest is None or not _transit_node_ok(dest, group_size):
            return RouteResult(False, reason=f"destination/transit node not feasible: {dest_id}")
        state = _extend_state(state, edge, dest, group_size)
        current = dest_id
        path.append(current)

    if current != target_node:
        return RouteResult(False, reason="declared path does not end at target")

    return RouteResult(
        True,
        path=tuple(path),
        target=target_node,
        score=_rank_key(state),
        reason="declared path satisfies movement hard constraints",
    )


def find_feasible_route_to_target(
    doc: dict[str, Any],
    start_node: str,
    target_node: str,
    *,
    group_size: int = 1,
    mode: str = "walk",
) -> RouteResult:
    """Find a constraint-feasible movement path to one declared target node.

    Unlike find_safe_route(), this helper does not require target kind=external_safe;
    the target must still be fresh and operationally usable as a transit/destination.
    """
    if group_size < 1:
        return RouteResult(False, reason="group_size must be >= 1")

    check = validate_document(doc)
    if not check["valid"]:
        return RouteResult(False, reason="invalid DAG: " + "; ".join(check["errors"]))

    nodes = _nodes(doc)
    edges = _edges(doc)
    if start_node not in nodes or target_node not in nodes:
        return RouteResult(False, reason="unknown start or target node")

    outgoing: dict[str, list[dict[str, Any]]] = {n: [] for n in nodes}
    for edge in edges:
        if edge.get("from") in outgoing:
            outgoing[edge["from"]].append(edge)

    initial = {
        "assisted_edges": 0,
        "degraded_nodes": 0,
        "caution_edges": 0,
        "unknown_capacity": 0,
        "bottleneck_slack": None,
        "unknown_distance": 0,
        "distance_m": 0.0,
        "hops": 0,
    }
    best_state: dict[str, dict[str, Any]] = {start_node: initial}
    best_path: dict[str, tuple[str, ...]] = {start_node: (start_node,)}

    for u in check["topological_order"]:
        if u not in best_state:
            continue
        for edge in outgoing[u]:
            v = edge["to"]
            dest = nodes[v]
            if not _edge_ok(edge, group_size, mode):
                continue
            if not _transit_node_ok(dest, group_size):
                continue
            cand_state = _extend_state(best_state[u], edge, dest, group_size)
            cand_path = best_path[u] + (v,)
            if v not in best_state or _rank_key(cand_state) < _rank_key(best_state[v]):
                best_state[v] = cand_state
                best_path[v] = cand_path

    if target_node not in best_state:
        return RouteResult(False, reason="no feasible route to declared target")

    return RouteResult(
        True,
        path=best_path[target_node],
        target=target_node,
        score=_rank_key(best_state[target_node]),
        reason="constraint-feasible route to declared target",
    )


def find_safe_route(
    doc: dict[str, Any],
    start_node: str,
    *,
    group_size: int = 1,
    mode: str = "walk",
    needs: Iterable[str] = (),
) -> RouteResult:
    """Find the best feasible path from start_node to any verified external safe node.

    Unknown, stale, blocked, unverified or capacity-infeasible segments are excluded.
    The start node is allowed to be UNKNOWN because it represents where the person is
    already located; every destination/transit node after it must pass operational checks.
    """
    if group_size < 1:
        return RouteResult(False, reason="group_size must be >= 1")

    check = validate_document(doc)
    if not check["valid"]:
        return RouteResult(False, reason="invalid DAG: " + "; ".join(check["errors"]))

    nodes = _nodes(doc)
    edges = _edges(doc)
    if start_node not in nodes:
        return RouteResult(False, reason=f"unknown start node: {start_node}")

    needs_set = set(needs)
    outgoing: dict[str, list[dict[str, Any]]] = {n: [] for n in nodes}
    for edge in edges:
        if edge.get("from") in outgoing:
            outgoing[edge["from"]].append(edge)

    initial = {
        "assisted_edges": 0,
        "degraded_nodes": 0,
        "caution_edges": 0,
        "unknown_capacity": 0,
        "bottleneck_slack": None,
        "unknown_distance": 0,
        "distance_m": 0.0,
        "hops": 0,
    }

    best_state: dict[str, dict[str, Any]] = {start_node: initial}
    best_path: dict[str, tuple[str, ...]] = {start_node: (start_node,)}

    for u in check["topological_order"]:
        if u not in best_state:
            continue
        for edge in outgoing[u]:
            v = edge["to"]
            dest = nodes[v]
            if not _edge_ok(edge, group_size, mode):
                continue
            if not _transit_node_ok(dest, group_size):
                continue
            cand_state = _extend_state(best_state[u], edge, dest, group_size)
            cand_path = best_path[u] + (v,)
            if v not in best_state or _rank_key(cand_state) < _rank_key(best_state[v]):
                best_state[v] = cand_state
                best_path[v] = cand_path

    candidates: list[tuple[tuple[Any, ...], str]] = []
    for node_id, node in nodes.items():
        if node_id not in best_state:
            continue
        if _target_ok(node, group_size, needs_set):
            candidates.append((_rank_key(best_state[node_id]), node_id))

    if not candidates:
        return RouteResult(
            False,
            reason=(
                "no feasible field-verified route to a fresh SAFE external node "
                "with sufficient capacity/services"
            ),
        )

    score, target = min(candidates, key=lambda x: (x[0], x[1]))
    return RouteResult(
        True,
        path=best_path[target],
        target=target,
        score=score,
        reason="constraint-feasible route; ordered lexicographically, not by risk score",
    )


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("yaml_path")
    p.add_argument("--start")
    p.add_argument("--group-size", type=int, default=1)
    p.add_argument("--mode", default="walk")
    p.add_argument("--need", action="append", default=[])
    args = p.parse_args()

    document = load_document(args.yaml_path)
    if args.start:
        print(json.dumps(
            find_safe_route(
                document,
                args.start,
                group_size=args.group_size,
                mode=args.mode,
                needs=args.need,
            ).as_dict(),
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(json.dumps(validate_document(document), ensure_ascii=False, indent=2))
