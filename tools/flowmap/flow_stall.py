#!/usr/bin/env python3
"""
tools/flowmap/flow_stall.py -- minimal-data "terrain + flow" typology for one declared
water chain/graph, one readout instant.

Founder's task, verbatim: "ทำ typology ให้เห็นภูมิทัศน์ แล้วค่าวัดต่างๆ ทำให้เห็นการไหล และการหยุดไหล
โดยใช้ข้อมูลน้อยที่สุด" (make a typology that shows the terrain/landscape, and let the
measurements show flow and stalled-flow, using the least data possible).

**Composes, does not derive**: every number this module reports as "measured" comes from
one of two already-registered Toledo proposals --
  - PROP-FLOOD-01 (`water_balance.py`, `site/build_data.py`'s `previous_reading()`): the
    lag-k retained-difference trend construction (RISING/FLAT/FALLING style sign readout
    over >=2 retained readings). `_node_trend_from_readings()` below applies the SAME
    construction to a node's own raw level series (not a basin-storage series) -- this is
    the same reuse relationship `water_balance.py`'s own docstring describes between
    itself and PROP-FLOOD-01.
  - PROP-FLOOD-04 (`canal_graph.py`, repo root): `edge_direction()` is imported and called
    DIRECTLY (never re-derived) for every edge whose both endpoints carry a usable
    reading -- see `_compute_base_edge()` below.

**Inference layer (founder correction, 2026-09-27, verbatim)**: "อย่าลืมว่าไม่มีทางมีข้อมูลพอ แต่
ใช้การอนุมานจากข้อมูลที่แข็งแรงเป็นหลัก" (there is never enough data -- infer from the STRONGEST
available anchors instead). REFUSED is the LAST resort, not the default, for an
un-instrumented node/edge. `_infer_run()` below applies two DECLARED CONSISTENCY RULES
(order relations on levels -- "a connected, open, unpumped link cannot show its upstream
surface below its downstream surface for long without either draining or being
provably stalled" -- INSTINCT-rule, never a new arithmetic formula, never cited as a
Toledo theorem) to the runs of un-gauged nodes/edges bounded by the strongest reachable
anchors. Every inferred value carries `inferred=True`, the anchors used, the rule id, and
an ordinal confidence capped by the WEAKEST anchor/evidence item used.

**What this is NOT** (claim_boundary): not a hydraulic/routing model (same claim_boundary
as PROP-FLOOD-04 itself) and not a forecast -- an inferred STALLED/MOVING state is a
readout of what the declared consistency rules say must be true GIVEN the strongest
anchors on hand right now, not a prediction of what happens next tick. `REFUSED` still
fires whenever literally no anchor is reachable in the connected component, or a genuine
datum mismatch / staleness / undeclared edge is hit (matching `canal_graph.py`'s own
REFUSED reason-code vocabulary).

A separate candidate classifier (F1-F6 flow-state over two composed heads, folded in from
an external proposal the founder forwarded) is documented as an APPENDIX candidate
statement in `docs/FLOW_STALL_TYPOLOGY.md` only -- see that file's "ภาคผนวก" section. It
is intentionally NOT implemented as a callable here: it would compose PROP-FLOOD-01/04/05a
in a genuinely new way and must go through Toledo registration (candidate id
PROP-FLOOD-07) by a different worker before any code runs it against the public page.

All arithmetic on level readings uses `fractions.Fraction` (Q), never `float`, per this
workspace's IDM Q-computability law -- same discipline as `canal_graph.py`/`water_balance.py`.
"""
from __future__ import annotations

import datetime
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Optional, Union

Numeric = Union[Fraction, int, float, str]

_HERE = Path(__file__).resolve()
_FLOOD_KG = _HERE.parents[2]  # repo root (tools/flowmap/flow_stall.py -> tools -> root)
if str(_FLOOD_KG) not in sys.path:
    sys.path.insert(0, str(_FLOOD_KG))

try:
    import canal_graph as cg  # noqa: E402 -- Toledo PROP-FLOOD-04 (proposal), reused directly
except Exception as _cg_exc:  # pragma: no cover - defensive fallback, matches build_data.py's
    # posture for optional cross-module imports; flow_stall degrades to "no edges resolvable"
    cg = None
    _CG_IMPORT_ERROR = _cg_exc


# --------------------------------------------------------------------------------------
# Declared vocabulary (typology conventions -- labels only, never a computed formula)
# --------------------------------------------------------------------------------------

# Node roles (folded in from the external proposal extract, tag RELAYED-external-proposal
# -> adopted-as-convention, founder 2026-09-27; a label describing a node's position in
# the chain, not a measurement).
NODE_ROLES = {
    "source": "ต้นทาง/จุดกระตุ้น -- ฝนตกบนพื้นที่ หรือปริมาณน้ำต้นทางจากนอกพื้นที่",
    "local_surface": "ผิวน้ำ/ผิวดินในพื้นที่ (ซอย ถนน สนาม) -- จุดที่คนอยู่จริง",
    "storage": "ที่เก็บกักน้ำ (บึง สระ แก้มลิง)",
    "connector": "ทางเชื่อมที่ไม่มีโครงสร้างควบคุม (คลอง ท่อ ลำราง)",
    "control": "จุดที่มีโครงสร้างควบคุม (ประตูระบายน้ำ สถานีสูบ)",
    "receiver": "ปลายทางรับน้ำ (แม่น้ำ ทะเล พื้นที่รับน้ำนอกเขต)",
}

# Edge kinds (same source as NODE_ROLES).
EDGE_KINDS = {
    "open_gravity": "เชื่อมแบบเปิด ไหลตามแรงโน้มถ่วง ไม่มีโครงสร้างควบคุมกั้น",
    "constrained_gravity": "ไหลตามแรงโน้มถ่วงแต่ถูกจำกัดหน้าตัด/ความจุ (ท่อเล็ก, culvert)",
    "controlled": "มีประตู/ปั๊มควบคุมทิศทาง-ปริมาณ",
    "backflow_risk": "เสี่ยงน้ำไหลย้อน (ปลายทางสูงกว่าต้นทางได้เมื่อน้ำหนุน/ฝนตกพร้อมกัน)",
    "unknown": "ยังไม่ประกาศชนิดเส้นเชื่อม",
}

# Landscape types 1-6 with their observable signals (used only to LABEL a chain/sub-chain
# from anchors already on hand -- a topological classification over declared node
# roles/edge kinds and anchor connectivity, never a numeric formula). Sammakorn's own
# classification below is produced by `classify_landscape_type()` and is always tagged
# INFERRED with the anchors it used -- never asserted outright.
LANDSCAPE_TYPES = {
    1: {
        "name_th": "ลาดเปิดสู่คลอง (open slope to canal)",
        "signals": "ไม่มี storage node; local_surface ต่อกับ connector/receiver โดยตรง",
    },
    2: {
        "name_th": "แอ่งเดียวผ่านทางออกเดียว (basin via single passage)",
        "signals": "storage node เดียว มี connector ออกทางเดียว ไม่มี control",
    },
    3: {
        "name_th": "แอ่ง+บึง+ทางออก (basin + pond + outlet)",
        "signals": ">=1 storage node ต่อเนื่องกันก่อนถึง connector/control ที่นำออกนอกพื้นที่",
    },
    4: {
        "name_th": "พึ่งพาปั๊ม (pump-dependent)",
        "signals": "control node เป็นปั๊ม (ไม่ใช่ประตูโน้มถ่วง) อยู่บนเส้นทางออกหลัก",
    },
    5: {
        "name_th": "ปลายน้ำหนุนครอบงำ (backwater-dominated)",
        "signals": "receiver/ปลายทางมีระดับผันผวนจากน้ำขึ้นน้ำลง/น้ำหนุน กระทบทิศทางเส้นเชื่อมใกล้ปลายทาง",
    },
    6: {
        "name_th": "ผสมโน้มถ่วง+ควบคุม (mixed gravity + control)",
        "signals": "มีทั้ง open_gravity/connector และ control node ผสมกันตลอดสาย",
    },
}

# Minimal data set of 5 (founder-forwarded extract): the least a chain needs to say
# anything at all -- documented here as a checklist, not enforced as a hard gate (a chain
# with fewer than 5 still gets the best honest picture `compute_chain()` can build).
MINIMAL_DATA_SET = [
    "main_chain_declared",       # 1. the declared node/edge list itself
    "upstream_surface_level",    # 2. >=1 reading on an upstream anchor
    "downstream_surface_level",  # 3. >=1 reading on a downstream anchor
    "control_state",             # 4. gate/pump measured state (opening_m or pumps_on)
    "local_state",                # 5. soi/local-surface qualitative state (rising/steady/
                                   #    falling) or a backflow yes/no community report
]

# Inference-strength ladder (founder-forwarded extract, mapped onto this module's own
# evidence tags). Higher = stronger; used to cap confidence at the WEAKEST link used.
STRENGTH_ORDER = {
    "VERIFIED_LIVE": 4,   # measured, fresh, this repo's own data
    "VERIFIED_STALE": 3,  # measured but past the declared freshness window
    "RELAYED": 2,         # official/media relay, not independently measured
    "COMMUNITY": 1,       # resident/community report
    "INSTINCT": 0,        # judgment call, weakest rung
}
INFERENCE_RUNG_OBSERVED = "observed"
INFERENCE_RUNG_STRONG = "strong_inference"
INFERENCE_RUNG_WEAK = "weak_inference"
INFERENCE_RUNG_REFUSE = "refuse"

TREND_MOVING_UP = "MOVING_UP"
TREND_MOVING_DOWN = "MOVING_DOWN"
TREND_STALLED = "STALLED"
TREND_UNKNOWN = "UNKNOWN"

STATUS_OK = "OK"
STATUS_NO_READOUT = "NO_READOUT"

EDGE_STATUS_OK = "OK"
EDGE_STATUS_CONTROLLED = "CONTROLLED"
EDGE_STATUS_REFUSED = "REFUSED"
EDGE_STATUS_INFERRED = "INFERRED"

RULE_STALL_01 = "RULE-STALL-01"
RULE_DIR_01 = "RULE-DIR-01"

DEFAULT_EPSILON_M = Fraction("0.03")  # OPEN-convention, declared band 0.02-0.05 m
# (external-proposal extract) -- distinct from canal_graph.py's own DEFAULT_EPSILON_M
# (0.02 m, INSTINCT, PROP-FLOOD-04's own declared sensor-resolution cutoff). This
# module's epsilon governs the INFERENCE layer (STALLED-persistence checks, head-ledger
# significance), never overrides PROP-FLOOD-04's own epsilon when it calls
# `canal_graph.edge_direction()` directly (that call keeps canal_graph's own default
# unless a caller of THIS module explicitly asks otherwise).
DEFAULT_MIN_GAP_HOURS = 1.0
DEFAULT_STALE_AFTER_HOURS = 1.0  # founder rule: REFUSE on Δt > 60 min
DEFAULT_PERSISTENCE_HOURS = 24.0


def _q(x: Optional[Numeric]) -> Optional[Fraction]:
    if x is None:
        return None
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        return Fraction(x)
    return Fraction(x).limit_denominator(10**12)


def _hours_between(observed_at_iso: Optional[str], ref_iso: str) -> Optional[float]:
    if not observed_at_iso or not ref_iso:
        return None
    try:
        obs = datetime.datetime.fromisoformat(observed_at_iso.replace("Z", "+00:00"))
        ref = datetime.datetime.fromisoformat(ref_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if obs.tzinfo is None:
        obs = obs.replace(tzinfo=datetime.timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=datetime.timezone.utc)
    return (ref - obs).total_seconds() / 3600.0


# --------------------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------------------

@dataclass
class TerrainAttr:
    """One static terrain attribute (ground/bed/bank/control level). `tag="OPEN"` (the
    default) means the declaration does not exist yet -- never a guessed number."""
    value: Optional[Numeric] = None
    tag: str = "OPEN"
    source: Optional[str] = None

    def as_dict(self) -> dict:
        return {"value": str(self.value) if self.value is not None else None,
                "tag": self.tag, "source": self.source}


@dataclass
class Reading:
    """One retained observation of a node's water surface level."""
    value: Optional[Numeric]
    observed_at: Optional[str] = None
    datum: str = "MSL"
    sensor_status: str = "ok"   # ok | faulted | unknown
    tag: str = "VERIFIED_LIVE"  # STRENGTH_ORDER key
    source: Optional[str] = None


@dataclass
class Node:
    node_id: str
    name_th: str
    kind: str  # soi_surface | pond | canal_reach | culvert | gate | pump | river | sea
    role: Optional[str] = None  # NODE_ROLES key, declared or left None (OPEN)
    ground_m_msl: TerrainAttr = field(default_factory=TerrainAttr)
    bed_m_msl: TerrainAttr = field(default_factory=TerrainAttr)
    bank_m_msl: TerrainAttr = field(default_factory=TerrainAttr)
    control_m_msl: TerrainAttr = field(default_factory=TerrainAttr)
    readings: list = field(default_factory=list)  # list[Reading], any order
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_gate: bool = False
    # `profile_order` (RELAYED-via-KlongMap-schema, founder 2026-09-27, adopted-as-
    # convention from the flood69.peoplesparty.or.th third-party KlongMap-proxy probe --
    # see docs/knowledge/card_thirdparty_flood69_peoplesparty_dashboard.md, its own
    # `listRiverMap.profile_order`): a declared sequence index along ONE canal chain, used
    # only to auto-derive a left-to-right draw/build order (`chain_order_from_profile()`)
    # -- never a measurement, OPEN (None) unless the maintainer declares it.
    profile_order: Optional[int] = None

    def valid_readings(self):
        return sorted(
            [r for r in self.readings
             if r.sensor_status != "faulted" and r.value is not None and r.observed_at],
            key=lambda r: r.observed_at, reverse=True,
        )


@dataclass
class Edge:
    edge_id: str
    u: str
    v: str
    edge_kind: str = "unknown"  # EDGE_KINDS key
    design_direction: str = "unknown"
    design_direction_source: Optional[str] = None
    control_structures: list = field(default_factory=list)
    gate_opening_m: Optional[Numeric] = None   # measured, optional
    pumps_on: Optional[int] = None             # measured, optional
    pumps_total: Optional[int] = None          # measured, optional
    pump_source_tag: Optional[str] = None      # STRENGTH_ORDER key for the pump reading
    # RELAYED-via-KlongMap-schema (founder 2026-09-27, from the flood69 third-party
    # KlongMap-proxy probe -- see docs/knowledge/card_thirdparty_flood69_peoplesparty_
    # dashboard.md). flood69's own `waterStation` payload was ALL-null in the probed
    # snapshot (OPEN) -- these fields are declared/gap-filler LAYOUT metadata only, never
    # a live-level source; `warning_m`/`critical_m` here are the PER-LEG counterpart of
    # this repo's existing single-per-station warning/critical (a control node with two
    # receiving sides, e.g. out01/out02, gets one `Edge` per leg -- each leg's own
    # thresholds live on that leg's own Edge, never shared across legs).
    flow_direction_state: Optional[str] = None  # "forward" | "reverse" | "unknown" --
    # the DECLARED/normal direction (separate vocabulary from `design_direction`'s
    # "u_to_v"/"v_to_u", kept both because they come from two different declared
    # sources -- this repo's own east_chain.yaml vs. KlongMap's arrowMap schema).
    leg_label: Optional[str] = None             # e.g. "out01" / "out02"
    warning_m: Optional[Numeric] = None          # per-leg, MEASURED when populated
    critical_m: Optional[Numeric] = None         # per-leg, MEASURED when populated


@dataclass
class NodeTrendResult:
    node_id: str
    status: str                     # OK | NO_READOUT
    trend: str = TREND_UNKNOWN      # MOVING_UP | MOVING_DOWN | STALLED | UNKNOWN
    reason_codes: list = field(default_factory=list)
    cur_reading: Optional[Reading] = None
    prev_reading: Optional[Reading] = None
    strength: Optional[str] = None  # weakest STRENGTH_ORDER key of the readings used
    inferred: bool = False
    rule_id: Optional[str] = None
    anchors: list = field(default_factory=list)
    inference_rung: str = INFERENCE_RUNG_REFUSE

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id, "status": self.status, "trend": self.trend,
            "reason_codes": list(self.reason_codes),
            "cur": (str(self.cur_reading.value), self.cur_reading.observed_at)
            if self.cur_reading else None,
            "prev": (str(self.prev_reading.value), self.prev_reading.observed_at)
            if self.prev_reading else None,
            "strength": self.strength, "inferred": self.inferred, "rule_id": self.rule_id,
            "anchors": list(self.anchors), "inference_rung": self.inference_rung,
        }


@dataclass
class EdgeFlowResult:
    edge_id: str
    u: str
    v: str
    status: str                      # OK | CONTROLLED | REFUSED | INFERRED
    reason_codes: list = field(default_factory=list)
    direction: Optional[str] = None  # FORWARD | REVERSE | UNRESOLVED | STALLED (inferred)
    delta_m: Optional[Fraction] = None
    locked_node: Optional[str] = None
    inferred: bool = False
    rule_id: Optional[str] = None
    anchors: list = field(default_factory=list)
    confidence: Optional[str] = None       # weakest STRENGTH_ORDER key used
    inference_rung: str = INFERENCE_RUNG_REFUSE
    # RELAYED-via-KlongMap-schema: the edge's own DECLARED design/normal direction
    # (mirrors `Edge.flow_direction_state`/`design_direction`, carried through so a
    # renderer can show "measured" and "designed" side by side), plus a flag raised
    # ONLY when both are actually known and disagree -- a genuine backflow signal, never
    # asserted from a REFUSED/UNRESOLVED measured direction.
    declared_direction: Optional[str] = None
    backflow_flag: bool = False

    def as_dict(self) -> dict:
        return {
            "edge_id": self.edge_id, "u": self.u, "v": self.v, "status": self.status,
            "reason_codes": list(self.reason_codes), "direction": self.direction,
            "delta_m": str(self.delta_m) if self.delta_m is not None else None,
            "locked_node": self.locked_node, "inferred": self.inferred,
            "rule_id": self.rule_id, "anchors": list(self.anchors),
            "confidence": self.confidence, "inference_rung": self.inference_rung,
            "declared_direction": self.declared_direction,
            "backflow_flag": self.backflow_flag,
        }


def _declared_direction(edge: "Edge") -> Optional[str]:
    """Resolve one declared direction label ("forward"/"reverse") from whichever of the
    two declared-direction fields an edge carries -- `flow_direction_state` (KlongMap
    vocabulary) takes precedence when both are declared, since it is the newer, more
    specific per-edge field; falls back to `design_direction` ("u_to_v"/"v_to_u")."""
    if edge.flow_direction_state in ("forward", "reverse"):
        return edge.flow_direction_state
    if edge.design_direction == "u_to_v":
        return "forward"
    if edge.design_direction == "v_to_u":
        return "reverse"
    return None


def _check_backflow(edge: "Edge", measured_direction: Optional[str]) -> tuple:
    """True/label only when BOTH a declared direction and a resolved measured direction
    (FORWARD/REVERSE, never UNRESOLVED/None) exist and disagree -- a real backflow
    signal, never inferred from missing/unresolved data."""
    declared = _declared_direction(edge)
    if declared is None or measured_direction not in ("FORWARD", "REVERSE"):
        return declared, False
    measured_label = "forward" if measured_direction == "FORWARD" else "reverse"
    return declared, declared != measured_label


@dataclass
class NextMeasurement:
    node_id: str
    resolves_refused: int
    resolves_inferred: int

    def as_dict(self) -> dict:
        return {"node_id": self.node_id, "resolves_refused": self.resolves_refused,
                "resolves_inferred": self.resolves_inferred}


@dataclass
class ChainResult:
    node_trends: dict          # node_id -> NodeTrendResult
    edge_flows: dict           # edge_id -> EdgeFlowResult
    next_measurement: list     # list[NextMeasurement], best-first
    refused_count: int
    inferred_count: int
    ok_count: int


# --------------------------------------------------------------------------------------
# PROP-FLOOD-01 composition: node-level trend from a retained reading series
# --------------------------------------------------------------------------------------

def _node_trend_from_readings(node: Node, ref_iso: str,
                               min_gap_hours: float = DEFAULT_MIN_GAP_HOURS,
                               stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS,
                               epsilon_m: Numeric = DEFAULT_EPSILON_M) -> NodeTrendResult:
    """PROP-FLOOD-01's lag-k retained-difference construction, applied to `node`'s own
    raw level series (>=2 readings). A faulted-sensor reading is never trusted (excluded
    before this function ever sees the series, via `Node.valid_readings()`)."""
    valid = node.valid_readings()
    if not valid:
        return NodeTrendResult(node_id=node.node_id, status=STATUS_NO_READOUT,
                                reason_codes=["MISSING_INPUT"])
    cur = valid[0]
    age = _hours_between(cur.observed_at, ref_iso)
    if age is not None and age > stale_after_hours:
        return NodeTrendResult(node_id=node.node_id, status=STATUS_NO_READOUT,
                                reason_codes=["STALE_INPUT"], cur_reading=cur)
    prev = None
    for r in valid[1:]:
        gap = _hours_between(r.observed_at, cur.observed_at)
        if gap is not None and gap >= min_gap_hours:
            prev = r
            break
    if prev is None:
        return NodeTrendResult(node_id=node.node_id, status=STATUS_NO_READOUT,
                                reason_codes=["INSUFFICIENT_READINGS"], cur_reading=cur)
    if (cur.datum or "MSL") != (prev.datum or "MSL"):
        return NodeTrendResult(node_id=node.node_id, status=STATUS_NO_READOUT,
                                reason_codes=["DATUM_MISMATCH"], cur_reading=cur,
                                prev_reading=prev)
    delta = _q(cur.value) - _q(prev.value)
    eps = _q(epsilon_m)
    if abs(delta) <= eps:
        trend = TREND_STALLED
    elif delta > 0:
        trend = TREND_MOVING_UP
    else:
        trend = TREND_MOVING_DOWN
    strength = min(cur.tag, prev.tag, key=lambda t: STRENGTH_ORDER.get(t, -1))
    return NodeTrendResult(node_id=node.node_id, status=STATUS_OK, trend=trend,
                            cur_reading=cur, prev_reading=prev, strength=strength,
                            inference_rung=INFERENCE_RUNG_OBSERVED)


def _is_persistently_stalled(node: Node, ref_iso: str, persistence_hours: float,
                              epsilon_m: Numeric) -> bool:
    """Declared consistency check (INSTINCT-rule, an extension of the same
    retained-difference discipline over a WINDOW rather than 2 points -- not a new
    equation): true iff every valid reading within `persistence_hours` of `ref_iso`
    stays within `epsilon_m` of the most recent one. Fewer than 2 qualifying readings
    -> not enough evidence to call it persistent (False)."""
    valid = node.valid_readings()
    in_window = [r for r in valid
                 if (_hours_between(r.observed_at, ref_iso) or 0) <= persistence_hours]
    if len(in_window) < 2:
        return False
    values = [_q(r.value) for r in in_window]
    eps = _q(epsilon_m)
    return (max(values) - min(values)) <= eps


# --------------------------------------------------------------------------------------
# PROP-FLOOD-04 composition: edge direction for measured edges
# --------------------------------------------------------------------------------------

def _as_cg_node(node: Node) -> dict:
    has_reading = bool(node.valid_readings())
    return {"is_gate": node.is_gate, "datum": "MSL",
            "canal_oldcode": node.node_id if has_reading else None}


def _as_cg_reading(node: Node) -> Optional[dict]:
    valid = node.valid_readings()
    if not valid:
        return None
    r = valid[0]
    return {"level_m": r.value, "observed_at": r.observed_at, "canal_out": None}


def _compute_base_edge(edge: Edge, u_node: Node, v_node: Node, ref_iso: str,
                        epsilon_m: Optional[Numeric] = None,
                        stale_after_hours: Optional[float] = None) -> EdgeFlowResult:
    """Calls `canal_graph.edge_direction()` (Toledo PROP-FLOOD-04) directly. Returns a
    REFUSED MISSING_INPUT result (this module's own vocabulary) if `canal_graph` failed
    to import -- never silently invents a direction."""
    if cg is None:
        return EdgeFlowResult(edge_id=edge.edge_id, u=edge.u, v=edge.v,
                               status=EDGE_STATUS_REFUSED,
                               reason_codes=["MISSING_INPUT", "CANAL_GRAPH_UNAVAILABLE"])
    kwargs = {}
    if epsilon_m is not None:
        kwargs["epsilon_m"] = epsilon_m
    if stale_after_hours is not None:
        kwargs["stale_after_hours"] = stale_after_hours
    cg_edge = {"edge_id": edge.edge_id, "u": edge.u, "v": edge.v}
    result = cg.edge_direction(
        cg_edge, _as_cg_node(u_node), _as_cg_node(v_node),
        _as_cg_reading(u_node), _as_cg_reading(v_node), ref_iso, **kwargs,
    )
    status_map = {cg.STATUS_OK: EDGE_STATUS_OK, cg.STATUS_CONTROLLED: EDGE_STATUS_CONTROLLED,
                  cg.STATUS_REFUSED: EDGE_STATUS_REFUSED}
    rung = INFERENCE_RUNG_OBSERVED if result.status != cg.STATUS_REFUSED else INFERENCE_RUNG_REFUSE
    confidence = None
    if result.status == cg.STATUS_OK:
        u_valid, v_valid = u_node.valid_readings(), v_node.valid_readings()
        if u_valid and v_valid:
            confidence = min(u_valid[0].tag, v_valid[0].tag,
                              key=lambda t: STRENGTH_ORDER.get(t, -1))
    declared_direction, backflow_flag = _check_backflow(edge, result.direction)
    return EdgeFlowResult(edge_id=edge.edge_id, u=edge.u, v=edge.v,
                           status=status_map.get(result.status, EDGE_STATUS_REFUSED),
                           reason_codes=list(result.reason_codes), direction=result.direction,
                           delta_m=result.delta_m, locked_node=result.locked_node,
                           confidence=confidence, inference_rung=rung,
                           declared_direction=declared_direction, backflow_flag=backflow_flag)


# --------------------------------------------------------------------------------------
# Inference layer (declared consistency rules, INSTINCT-rule -- never a new equation)
# --------------------------------------------------------------------------------------

def _build_adjacency(edges):
    adj = {}
    for e in edges:
        adj.setdefault(e.u, []).append(e)
        adj.setdefault(e.v, []).append(e)
    return adj


def _find_runs(nodes: dict, edges: list, node_trends: dict):
    """Partition the node/edge set into maximal connected 'runs' of nodes whose direct
    trend is NO_READOUT, each bounded by 0-2 anchor nodes (nodes with an OK trend) plus
    the edges touching the run. Returns list of dict(nodes=[...], edges=[...],
    anchors=[node_id,...])."""
    adj = _build_adjacency(edges)
    seen = set()
    runs = []
    for nid, node in nodes.items():
        if node_trends[nid].status == STATUS_OK or nid in seen:
            continue
        # BFS over NO_READOUT nodes, collecting bounding anchors and touching edges
        stack = [nid]
        run_nodes, run_edges, anchors = set(), set(), set()
        while stack:
            cur = stack.pop()
            if cur in run_nodes:
                continue
            run_nodes.add(cur)
            seen.add(cur)
            for e in adj.get(cur, []):
                run_edges.add(e.edge_id)
                other = e.v if e.u == cur else e.u
                if node_trends.get(other, NodeTrendResult(node_id=other, status=STATUS_NO_READOUT)).status == STATUS_OK:
                    anchors.add(other)
                elif other not in run_nodes:
                    stack.append(other)
        runs.append({"nodes": run_nodes, "edges": run_edges, "anchors": anchors})
    return runs


def _run_pump_evidence(run_edges, edges_by_id):
    """Strongest pump/gate MEASURED evidence within a run: True/False for 'no active
    pump passing water' plus the evidence-item tag, or (None, None) if undeclared."""
    for eid in run_edges:
        e = edges_by_id.get(eid)
        if e is None or e.pumps_total is None:
            continue
        no_pumps_running = (e.pumps_on == 0)
        return no_pumps_running, (e.pump_source_tag or "VERIFIED_LIVE")
    return None, None


def _infer_runs(nodes, edges, node_trends, edge_flows, ref_iso, community_reports,
                 persistence_hours, epsilon_m):
    edges_by_id = {e.edge_id: e for e in edges}
    runs = _find_runs(nodes, edges, node_trends)
    community_reports = community_reports or []

    for run in runs:
        anchors = sorted(run["anchors"])
        run_edge_ids = run["edges"]
        applied = False

        # RULE-STALL-01: downstream anchor persistently flat + measured 0 running pumps
        # on a pump-controlled edge in the run + a community "no drop" report -> infer
        # STALLED across the whole run (interior nodes AND interior edges).
        stalled_anchor = None
        for a in anchors:
            if _is_persistently_stalled(nodes[a], ref_iso, persistence_hours, epsilon_m):
                stalled_anchor = a
                break
        no_pumps, pump_tag = _run_pump_evidence(run_edge_ids, edges_by_id)
        matching_reports = [r for r in community_reports
                             if r.get("no_drop") and (r.get("node_id") in run["nodes"]
                                                       or r.get("node_id") in anchors)]
        if stalled_anchor and no_pumps and matching_reports:
            report = matching_reports[0]
            evidence_tags = [nodes[stalled_anchor].valid_readings()[0].tag, pump_tag,
                             report.get("tag", "COMMUNITY")]
            confidence = min(evidence_tags, key=lambda t: STRENGTH_ORDER.get(t, -1))
            anchor_ids = [stalled_anchor, "pump:" + next(iter(run_edge_ids)),
                          "community:" + report.get("report_id", "?")]
            for nid in run["nodes"]:
                node_trends[nid] = NodeTrendResult(
                    node_id=nid, status=STATUS_OK, trend=TREND_STALLED,
                    inferred=True, rule_id=RULE_STALL_01, anchors=anchor_ids,
                    strength=confidence, inference_rung=INFERENCE_RUNG_STRONG,
                )
            for eid in run_edge_ids:
                base = edge_flows[eid]
                edge_flows[eid] = EdgeFlowResult(
                    edge_id=base.edge_id, u=base.u, v=base.v, status=EDGE_STATUS_INFERRED,
                    direction=TREND_STALLED, inferred=True, rule_id=RULE_STALL_01,
                    anchors=anchor_ids, confidence=confidence,
                    inference_rung=INFERENCE_RUNG_STRONG,
                    reason_codes=["INFERRED_FROM_ANCHORS"],
                )
            applied = True

        # RULE-DIR-01: exactly the two anchors bound the run, both move the SAME
        # direction -> infer the interior moves that same direction.
        if not applied and len(anchors) >= 2:
            trends = {node_trends[a].trend for a in anchors
                      if node_trends[a].status == STATUS_OK}
            if len(trends) == 1 and next(iter(trends)) in (TREND_MOVING_UP, TREND_MOVING_DOWN):
                shared_trend = next(iter(trends))
                confidence = min(
                    (node_trends[a].strength for a in anchors if node_trends[a].strength),
                    key=lambda t: STRENGTH_ORDER.get(t, -1), default="INSTINCT",
                )
                anchor_ids = list(anchors)
                for nid in run["nodes"]:
                    node_trends[nid] = NodeTrendResult(
                        node_id=nid, status=STATUS_OK, trend=shared_trend,
                        inferred=True, rule_id=RULE_DIR_01, anchors=anchor_ids,
                        strength=confidence, inference_rung=INFERENCE_RUNG_STRONG,
                    )
                for eid in run_edge_ids:
                    base = edge_flows[eid]
                    edge_flows[eid] = EdgeFlowResult(
                        edge_id=base.edge_id, u=base.u, v=base.v,
                        status=EDGE_STATUS_INFERRED, direction=shared_trend, inferred=True,
                        rule_id=RULE_DIR_01, anchors=anchor_ids, confidence=confidence,
                        inference_rung=INFERENCE_RUNG_STRONG,
                        reason_codes=["INFERRED_FROM_ANCHORS"],
                    )
                applied = True

        if not applied:
            # weak inference: a lone community report with no measured anchor at all
            # still beats bare REFUSED, but stays capped at "weak_inference".
            loose_reports = [r for r in community_reports
                              if r.get("node_id") in run["nodes"]]
            if loose_reports and not anchors:
                report = loose_reports[0]
                for nid in run["nodes"]:
                    if node_trends[nid].status != STATUS_OK:
                        node_trends[nid] = NodeTrendResult(
                            node_id=nid, status=STATUS_OK,
                            trend=TREND_STALLED if report.get("no_drop") else TREND_UNKNOWN,
                            inferred=True, rule_id="RULE-COMMUNITY-01",
                            anchors=["community:" + report.get("report_id", "?")],
                            strength="COMMUNITY", inference_rung=INFERENCE_RUNG_WEAK,
                        )
    return node_trends, edge_flows


def _rank_next_measurement(nodes, edges, node_trends, edge_flows):
    adj = _build_adjacency(edges)
    ranked = []
    for nid, node in nodes.items():
        if node_trends[nid].status == STATUS_OK and not node_trends[nid].inferred:
            continue  # already directly measured, taking a new reading here is not "next"
        resolves_refused = 0
        resolves_inferred = 0
        for e in adj.get(nid, []):
            other = e.v if e.u == nid else e.u
            other_trend = node_trends.get(other)
            if other_trend is None or other_trend.status != STATUS_OK or other_trend.inferred:
                continue  # the other end also needs a reading -- this node alone won't resolve it
            ef = edge_flows.get(e.edge_id)
            if ef is None:
                continue
            if ef.status == EDGE_STATUS_REFUSED:
                resolves_refused += 1
            elif ef.status == EDGE_STATUS_INFERRED:
                resolves_inferred += 1
        if resolves_refused or resolves_inferred:
            ranked.append(NextMeasurement(nid, resolves_refused, resolves_inferred))
    ranked.sort(key=lambda r: (r.resolves_refused, r.resolves_inferred), reverse=True)
    return ranked


# --------------------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------------------

def compute_chain(nodes: dict, edges: list, ref_iso: str,
                   community_reports: Optional[list] = None,
                   persistence_hours: float = DEFAULT_PERSISTENCE_HOURS,
                   epsilon_m: Numeric = DEFAULT_EPSILON_M,
                   min_gap_hours: float = DEFAULT_MIN_GAP_HOURS,
                   stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS) -> ChainResult:
    """One readout of a whole declared chain/graph: best honest picture from as few as 2
    readings on 2 nodes, `REFUSED` only as a last resort. `nodes`: dict[node_id, Node].
    `edges`: list[Edge]. `community_reports`: list of
    {"node_id", "no_drop": bool, "tag", "report_id", "observed_at"} dicts, optional."""
    node_trends = {nid: _node_trend_from_readings(n, ref_iso, min_gap_hours,
                                                   stale_after_hours, epsilon_m)
                   for nid, n in nodes.items()}
    edge_flows = {}
    for e in edges:
        u_node, v_node = nodes.get(e.u), nodes.get(e.v)
        if u_node is None or v_node is None:
            edge_flows[e.edge_id] = EdgeFlowResult(edge_id=e.edge_id, u=e.u, v=e.v,
                                                     status=EDGE_STATUS_REFUSED,
                                                     reason_codes=["UNDECLARED_EDGE"])
            continue
        edge_flows[e.edge_id] = _compute_base_edge(e, u_node, v_node, ref_iso)

    node_trends, edge_flows = _infer_runs(nodes, edges, node_trends, edge_flows, ref_iso,
                                           community_reports, persistence_hours, epsilon_m)

    next_measurement = _rank_next_measurement(nodes, edges, node_trends, edge_flows)

    refused = sum(1 for ef in edge_flows.values() if ef.status == EDGE_STATUS_REFUSED)
    inferred = sum(1 for ef in edge_flows.values() if ef.status == EDGE_STATUS_INFERRED)
    ok = sum(1 for ef in edge_flows.values()
             if ef.status in (EDGE_STATUS_OK, EDGE_STATUS_CONTROLLED))

    return ChainResult(node_trends=node_trends, edge_flows=edge_flows,
                        next_measurement=next_measurement, refused_count=refused,
                        inferred_count=inferred, ok_count=ok)


def chain_order_from_profile(nodes: dict, node_ids: Optional[list] = None) -> list:
    """RELAYED-via-KlongMap-schema convention: order `node_ids` (default: all of `nodes`)
    by declared `profile_order` when present, falling back to insertion/dict order for
    any node that leaves it OPEN (None) -- OPEN nodes keep their relative position after
    the last declared one, never silently dropped or reshuffled ahead of a declared
    node."""
    ids = list(node_ids) if node_ids is not None else list(nodes.keys())
    declared = [nid for nid in ids if nodes[nid].profile_order is not None]
    undeclared = [nid for nid in ids if nodes[nid].profile_order is None]
    declared.sort(key=lambda nid: nodes[nid].profile_order)
    return declared + undeclared


def classify_landscape_type(nodes: dict, edges: list, node_trends: dict) -> dict:
    """Topological classification ONLY (declared conventions on node roles/edge kinds
    and anchor connectivity -- never a numeric formula). Always returns `inferred=True`
    with the anchor node_ids it used; never asserts a type outright. Best-effort: checks
    landscape types 4 (pump-dependent) and 3 (basin+pond+outlet) first since Sammakorn's
    own chain has both signals; falls back to 6 (mixed) when both storage and control
    nodes are present without a clean single-passage match, else 1 (open slope)."""
    anchors = [nid for nid, t in node_trends.items() if t.status == STATUS_OK]
    kinds = {n.kind for n in nodes.values()}
    roles = {n.role for n in nodes.values() if n.role}
    has_storage = "pond" in kinds or "storage" in roles
    has_pump_control = any(n.kind == "pump" for n in nodes.values())
    has_gate_control = any(n.kind == "gate" for n in nodes.values())
    if has_storage and has_pump_control:
        type_id = 4 if not has_gate_control else 6
    elif has_storage:
        type_id = 3
    elif has_gate_control:
        type_id = 6
    else:
        type_id = 1
    return {"type_id": type_id, "type": LANDSCAPE_TYPES[type_id], "inferred": True,
            "anchors": anchors}
