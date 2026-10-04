"""tools/flowmap -- minimal-data "terrain + flow" typology (prototype package).

Composes two already-registered Toledo proposals -- PROP-FLOOD-01 (lag-k
retained-difference trend readout) and PROP-FLOOD-04 (edge_direction() in
`canal_graph.py`, this repo's root) -- into a chain-level "what is moving, what
is stalled, what is REFUSED" readout, plus a declared (INSTINCT-rule, not a new
Toledo equation) inference layer for un-instrumented nodes/edges. See
`docs/FLOW_STALL_TYPOLOGY.md` for the full typology and the rule table.

No new equation is derived here. `flow_stall.py`'s inference rules are declared
consistency constraints on ordered levels (order relations), not arithmetic
formulas, and are tagged INSTINCT-rule throughout -- never cited as a Toledo
theorem. A separate candidate classifier (F1-F6 flow-state, folded in from an
external proposal) is written up as an APPENDIX in the typology doc only --
it is NOT implemented as running code here, pending Toledo registration as
PROP-FLOOD-07 by a different worker.
"""
from .flow_stall import (  # noqa: F401
    Reading,
    TerrainAttr,
    Node,
    Edge,
    NodeTrendResult,
    EdgeFlowResult,
    ChainResult,
    compute_chain,
    classify_landscape_type,
    chain_order_from_profile,
    STRENGTH_ORDER,
    NODE_ROLES,
    EDGE_KINDS,
    LANDSCAPE_TYPES,
    MINIMAL_DATA_SET,
)

__all__ = [
    "Reading",
    "TerrainAttr",
    "Node",
    "Edge",
    "NodeTrendResult",
    "EdgeFlowResult",
    "ChainResult",
    "compute_chain",
    "classify_landscape_type",
    "chain_order_from_profile",
    "STRENGTH_ORDER",
    "NODE_ROLES",
    "EDGE_KINDS",
    "LANDSCAPE_TYPES",
    "MINIMAL_DATA_SET",
]
