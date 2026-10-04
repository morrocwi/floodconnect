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
    # `support` (added 2026-09-28, extension not a fork): a zone-reachable service/
    # logistics point (kitchen, medical_post, charging, supply_depot, donation_point,
    # rescue_staging -- see SUPPORT_SERVICES). It shares layer 3 with `internal_safe`
    # rather than claiming a new layer number -- inserting a genuinely new layer would
    # require renumbering every existing declared node's `layer` field in site/inputs/
    # community/self_help_dag.yaml (a fork of the imported protocol's numbering, not an
    # extension of it). Sharing a layer number is safe here: the forward-only DAG rule
    # (destination layer strictly greater than source layer) is checked PER EDGE, not
    # per distinct-kind-per-layer, so two different kinds at the same layer number is
    # not a schema violation -- a zone(2) can reach a support(3) exactly like it reaches
    # an internal_safe(3), and a support(3) can itself route onward to egress(4)/
    # external_safe(5) the same way an internal_safe node can.
    "support": 3,
    "internal_safe": 3,
    "egress": 4,
    "external_safe": 5,
    # Imported from origin/main 17b9c3a (superset merge, 2026-10-02):
    # `supply_point` kept layer-5 for backward compatibility with any already-declared
    # node of that kind; `service_node` is capability-based (see `node_capabilities()`
    # below) rather than kind-based, so it has no single fixed layer -- its declared
    # `layer` is checked against SERVICE_NODE_LAYERS instead of a fixed KIND_LAYER value
    # (see validate_document() below).
    "supply_point": 5,  # backward-compatible legacy service node
    "service_node": None,  # capability-based service node; declared layer must be 2..5
}

SERVICE_NODE_LAYERS = {2, 3, 4, 5}

NODE_STATUS = {"SAFE", "DEGRADED", "UNSAFE", "UNKNOWN"}
EDGE_STATUS = {"OPEN", "ASSISTED", "BLOCKED", "UNKNOWN"}
EDGE_SAFETY = {"CLEAR", "CAUTION", "BLOCKED", "UNKNOWN"}

# Edge mode vocabulary (added 2026-09-28: `boat`, `high_clearance` -- the imported
# protocol only ever declared `walk`/`vehicle` in its own data, with no closed vocabulary
# enforced in code at all; this is the first time `modes` is actually validated).
# `air_drone` (added 2026-09-28, docs/knowledge/card_tool_rescue_drones_romklao_2569.md,
# เคหะร่มเกล้า case -- boats blocked by obstacles/fences, drones reached what boats could
# not) -- SUPPLIES/SURVEY MODE ONLY. A drone here means aerial delivery (sling-dropped
# supplies) or ISR survey (imagery/radar), never a mode for MOVING PEOPLE -- routing a
# person via `air_drone` is out of scope for this repo's find_safe_route() and must never
# be added; this mode exists only for the RESOURCE layer (typology `resource`/`support`
# nodes), not for a household->...->external_safe evacuation edge.
EDGE_MODES = {"walk", "vehicle", "boat", "high_clearance", "air_drone"}

# `support` node service vocabulary (added 2026-09-28) -- distinct from the general
# `services` vocabulary docs/COMMUNITY_SELF_HELP_DAG.md §4 already documents for spatial
# nodes generally (water/power/toilet/first_aid/charging/comms); these are the specific
# service TYPES a `support` node exists to provide.
SUPPORT_SERVICES = {"kitchen", "medical_post", "charging", "supply_depot",
                     "donation_point", "rescue_staging"}

# ---------------------------------------------------------------------------
# Dual-state / re-escalation / mode-degradation / safe-node-continuity vocabulary
# (added 2026-09-28, docs/knowledge/card_dual_state_reescalation_hatyai_2026-09-28.md --
# reasoning over experiments/2025-11-hat-yai-real-data-redteam.md, already in this repo).
# All OPTIONAL fields, all closed vocabularies, no new equation/formula anywhere below --
# a value not in the set is a schema error exactly like NODE_STATUS/EDGE_STATUS already
# are; a field simply absent is not an error (UNKNOWN operational state stays allowed).
# ---------------------------------------------------------------------------

# Dual-state rule (Hat Yai finding B, 20 พ.ย. 2568: municipal statement No.2 said
# GREEN/normal locally while ONWR/TMD regional warnings were already active) -- two
# INDEPENDENT fields a node may declare. Neither is derived from the other anywhere in
# this module -- a GREEN `current_local_state` must never silently clear an ACTIVE
# `forward_hazard` (see validate_document() below, which only checks vocabulary
# membership, never cross-derives one from the other).
CURRENT_LOCAL_STATE = {"GREEN", "YELLOW", "RED", "UNKNOWN"}
FORWARD_HAZARD_STATE = {"NONE", "ACTIVE", "UNKNOWN"}

# Edge mode-degradation ladder (Hat Yai finding G: by 25 พ.ย. authorities were using
# high-clearance trucks and boats as normal vehicle access failed). Distinct from
# `modes` (which travel modes an edge accepts at all) -- `mode_degradation` is a single
# CURRENT-STATE label along a fixed, ordered ladder. find_safe_route() does not read
# this field (routing still gates on status/safety/modes, unchanged) -- this is a
# readout/display ladder, wiring it into routing is a separate, later step.
MODE_DEGRADATION_LADDER = ("normal", "high_clearance_only", "boat_only", "blocked")
MODE_DEGRADATION_STATES = set(MODE_DEGRADATION_LADDER) | {"UNKNOWN"}

# Safe-node continuity fields (Hat Yai finding F: Hospital Hat Yai had an urgent
# electricity problem despite being a hospital -- a node's KIND never proves it is a
# safe node). `internal_safe`/`external_safe`/`support` nodes SHOULD declare all 7 as
# keys; the value "UNKNOWN" is a valid, honest declaration (presence check, not a
# readiness check) -- report_safe_node_continuity_gaps() below reports which nodes are
# missing which keys entirely, a non-error report matching this repo's existing OPEN-gap
# discipline (tools/typology/validate.py's capability_gaps/warning_quality_gaps).
SAFE_NODE_CONTINUITY_FIELDS = ("access_state", "power_state", "backup_power_state",
                                "water_state", "comms_state", "medical_capacity_state",
                                "occupancy_state")
SAFE_NODE_KINDS_REQUIRING_CONTINUITY = {"internal_safe", "external_safe", "support"}

# Community-role vocabulary (added 2026-09-28, docs/knowledge/
# card_community_selforg_pattern_2569.md -- แฟลตคลองจั่น/ร่มเกล้า self-organisation, RELAYED
# FB post by a university academic). docs/COMMUNITY_SELF_HELP_DAG.md §3.3 already
# documents coordinator/welfare/route_checker/resource_keeper/comms in prose; this is
# that same list as a closed, testable vocabulary, plus the one role that case adds:
# `procurement_runner` -- goes out for supplies only when a route is ASSISTED/OPEN
# (never UNKNOWN), a specialisation of route_checker's access discipline applied to
# outbound errands. `roles_active` is an OPTIONAL node attribute (a zone/support node
# may declare which roles are currently staffed); genders are never recorded, roles only.
COMMUNITY_ROLES = {"coordinator", "welfare", "route_checker", "resource_keeper", "comms",
                    "procurement_runner"}


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
        # service_node is capability-based (origin/main 17b9c3a, superset merge):
        # its layer is declared per-node, not fixed by kind -- only checked against the
        # SERVICE_NODE_LAYERS range. Every other kind keeps the original fixed-layer
        # check unchanged.
        if kind == "service_node":
            if layer not in SERVICE_NODE_LAYERS:
                errors.append(
                    f"{node_id}: service_node layer {layer!r} must be one of "
                    f"{sorted(SERVICE_NODE_LAYERS)}"
                )
        elif layer != KIND_LAYER[kind]:
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

        # Dual-state fields (OPTIONAL, closed vocabulary when present -- see
        # CURRENT_LOCAL_STATE/FORWARD_HAZARD_STATE above). Checked independently of each
        # other by construction -- neither field's presence/value affects the other.
        cls = node.get("current_local_state")
        if cls is not None and cls not in CURRENT_LOCAL_STATE:
            errors.append(f"{node_id}: invalid current_local_state {cls!r}")
        fh = node.get("forward_hazard")
        if fh is not None and fh not in FORWARD_HAZARD_STATE:
            errors.append(f"{node_id}: invalid forward_hazard {fh!r}")

        roles_active = node.get("roles_active")
        if roles_active is not None:
            bad_roles = set(roles_active) - COMMUNITY_ROLES
            if bad_roles:
                errors.append(f"{node_id}: role(s) outside the closed vocabulary "
                               f"{sorted(COMMUNITY_ROLES)}: {sorted(bad_roles)}")

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
        bad_modes = set(edge.get("modes") or []) - EDGE_MODES
        if bad_modes:
            errors.append(f"{edge_id}: mode(s) outside the closed vocabulary "
                           f"{sorted(EDGE_MODES)}: {sorted(bad_modes)}")
        if edge.get("fresh") is not True:
            warnings.append(f"{edge_id}: not fresh; it will not be routed")
        if edge.get("field_verified") is not True:
            warnings.append(f"{edge_id}: not field-verified; it will not be routed")

        # Mode-degradation ladder (OPTIONAL, closed vocabulary when present -- see
        # MODE_DEGRADATION_LADDER above). UNKNOWN is accepted here but never treated as
        # passable by find_safe_route() (which does not read this field at all yet).
        deg = edge.get("mode_degradation")
        if deg is not None and deg not in MODE_DEGRADATION_STATES:
            errors.append(f"{edge_id}: invalid mode_degradation {deg!r} "
                           f"(closed ladder: {MODE_DEGRADATION_LADDER})")

    topo, cycle_error = topological_order(nodes, edges)
    if cycle_error:
        errors.append(cycle_error)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "topological_order": topo,
    }


def report_safe_node_continuity_gaps(doc: dict[str, Any]) -> dict[str, list[str]]:
    """Non-error report (Hat Yai finding F, docs/knowledge/card_dual_state_reescalation_
    hatyai_2026-09-28.md): for every internal_safe/external_safe/support node, which of
    the 7 SAFE_NODE_CONTINUITY_FIELDS are entirely ABSENT (never mind their value --
    "UNKNOWN" is an honest present value, not a gap). Mirrors tools/typology/validate.py's
    report_capability_gaps/report_warning_quality_gaps pattern -- surfaces the gap, never
    fails the build over it."""
    gaps: dict[str, list[str]] = {}
    nodes = _nodes(doc)
    for node_id, node in nodes.items():
        if node.get("kind") not in SAFE_NODE_KINDS_REQUIRING_CONTINUITY:
            continue
        missing = [f for f in SAFE_NODE_CONTINUITY_FIELDS if f not in node]
        if missing:
            gaps[node_id] = missing
    return gaps


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


def node_capabilities(node: dict[str, Any]) -> set[str]:
    """Return declared functional capabilities independent of topology kind.

    Imported from origin/main 17b9c3a (superset merge, 2026-10-02).
    `services` remains supported for backward compatibility; new nodes should prefer
    `capabilities`. A node may expose several capabilities at once.
    """
    return set(node.get("services") or []) | set(node.get("capabilities") or [])


def _node_services_ok(node: dict[str, Any], needs: set[str]) -> bool:
    return needs.issubset(node_capabilities(node))


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


# Explicit "no route" reason string (added 2026-09-28, docs/knowledge/
# card_dual_state_reescalation_hatyai_2026-09-28.md item 6 -- founder ask: confirm
# find_safe_route() returns an explicit no-route result rather than inventing a path).
# The behavior already existed (see the return below, unchanged); this constant just
# names it so callers/tests can check `result.reason == REASON_NO_FEASIBLE_SAFE_ROUTE`
# instead of matching the string by hand.
REASON_NO_FEASIBLE_SAFE_ROUTE = (
    "no feasible field-verified route to a fresh verified external refuge "
    "with sufficient capacity/services"
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
        return RouteResult(False, reason=REASON_NO_FEASIBLE_SAFE_ROUTE)

    score, target = min(candidates, key=lambda x: (x[0], x[1]))
    return RouteResult(
        True,
        path=best_path[target],
        target=target,
        score=score,
        reason="constraint-feasible route; ordered lexicographically, not by risk score",
    )


# --------------------------------------------------------------------------------------
# Imported from origin/main 17b9c3a (superset merge, 2026-10-02): two
# movement-validation helpers distinct from find_safe_route(). Neither overrides or
# duplicates find_safe_route() -- find_safe_route() stays the single canonical "is there
# a safe route to an external_safe node" search (per the 2026-10-02 merge design's H6 fix: the
# MCP server's route tool must call this one function, never re-implement its own
# walk). These two are for different, narrower questions:
#   validate_declared_edge_path -- check one SPECIFIC caller-supplied edge sequence
#   find_feasible_route_to_target -- search for a feasible route to a named node that
#       need not be kind=external_safe (e.g. a resupply/service journey)
# --------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------
# Access-first priority rule (added 2026-09-28, founder: "เอ อาจต้องเริ่มจากการทำให้ระบบ
# การเดินทางเชื่อมถึงก่อน เช่นเรือ หรือรถยกสูง" -- for a mobility-limited zone, a boat/
# high-clearance-truck link toward the outside world is prerequisite, not one option among
# equals). Structural rule, NO equation, NO weighted score -- a pure ordering function over
# the same hard-constraint checks find_safe_route() already uses (field_verified, fresh,
# status, safety, mode) -- UNKNOWN is never treated as passable, matching the module's
# existing routing discipline verbatim (see module docstring "Routing discipline").
# --------------------------------------------------------------------------------------

PRIORITY_RESTORE_ACCESS = "RESTORE_ACCESS"
PRIORITY_SUPPORT = "SUPPORT"
PRIORITY_EVACUATE = "EVACUATE"


def zone_has_verified_access(
    doc: dict[str, Any],
    zone_id: str,
    required_modes: Iterable[str],
) -> bool:
    """True iff `zone_id` can reach some node at layer >= egress (4) through a chain of
    edges that are ALL field_verified, fresh, status in {OPEN, ASSISTED}, safety in
    {CLEAR, CAUTION}, and whose declared `modes` intersects `required_modes` -- through
    transit nodes whose own status is in {SAFE, DEGRADED} and fresh=True. UNKNOWN status
    (node or edge) is never treated as passable -- same discipline as `_edge_ok`/
    `_transit_node_ok` above, deliberately re-checked here rather than reused as-is
    because this function asks a different question (can we reach EGRESS at all, for ANY
    of several modes) than `find_safe_route` (best single-mode path to a capacity-
    sufficient external_safe target)."""
    nodes = _nodes(doc)
    edges = _edges(doc)
    if zone_id not in nodes:
        return False
    required = set(required_modes) or {"walk"}

    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        outgoing.setdefault(edge.get("from"), []).append(edge)

    seen: set[str] = set()
    stack = [zone_id]
    while stack:
        u = stack.pop()
        if u in seen:
            continue
        seen.add(u)
        node_u = nodes.get(u) or {}
        if u != zone_id and isinstance(node_u.get("layer"), int) \
                and node_u["layer"] >= KIND_LAYER["egress"]:
            return True
        for edge in outgoing.get(u, []):
            if edge.get("field_verified") is not True:
                continue
            if edge.get("fresh") is not True:
                continue
            if edge.get("status") not in {"OPEN", "ASSISTED"}:
                continue
            if edge.get("safety") not in {"CLEAR", "CAUTION"}:
                continue
            if not (set(edge.get("modes") or []) & required):
                continue
            v = edge.get("to")
            dest = nodes.get(v)
            if dest is None:
                continue
            if dest.get("status") not in {"SAFE", "DEGRADED"}:  # excludes UNKNOWN/UNSAFE
                continue
            if dest.get("fresh") is not True:
                continue
            if v not in seen:
                stack.append(v)
    return False


def zone_priority_order(
    doc: dict[str, Any],
    zone_id: str,
    required_modes: Iterable[str] = ("walk",),
) -> list[str]:
    """Ordered list of what a zone should do first. If NO verified edge chain reaches
    egress/external_safe using a mode the zone's own demand requires (e.g. the zone
    declares it needs `boat`/`high_clearance` because water is too deep for `walk`, and
    no such-moded verified edge exists), the first priority is RESTORE_ACCESS (request
    the missing mode via a named channel) -- BEFORE using/requesting SUPPORT nodes, which
    comes before EVACUATE. When access already exists, RESTORE_ACCESS is not returned at
    all (nothing to restore)."""
    if zone_has_verified_access(doc, zone_id, required_modes):
        return [PRIORITY_SUPPORT, PRIORITY_EVACUATE]
    return [PRIORITY_RESTORE_ACCESS, PRIORITY_SUPPORT, PRIORITY_EVACUATE]


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
