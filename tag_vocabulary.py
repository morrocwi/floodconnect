#!/usr/bin/env python3
"""tag_vocabulary.py -- the ONE source for FloodConnect's fixed epistemic tag set.

AI.md documents this five-value vocabulary in prose for a human/AI reader.
kb.py's TAG_ORDER, tools/mcp/floodconnect_mcp.py's TAG_VOCABULARY and
tools/api/export_api.py's TAG_VOCABULARY used to be three independently
hand-copied constants -- this module makes all three import the same object
instead, so a future edit cannot drift one copy away from the others
(the constants agreed with each other, but
tools/typology/build_graph.py's own allowed-set did not, and three compound
values it let through -- VERIFIED-CONTRADICTED, MEASURED+OPEN,
RELAYED-unverified -- reached api/v1 and MCP unchanged).

A tag value outside TAG_VOCABULARY is never served as `tag` in any surface
(api/v1 JSON, MCP tool response, kb.py CLI output). A finer-grained reason
(contradicted-but-not-yet-reconciled, partly-measured, unverified relay)
belongs in the sibling `basis` / `contradicted` keys next to the tag, never
as a sixth `tag` value -- `COMPOUND_TAG_MAP` below is how a source registry
that still writes one of the three old compound strings gets normalized at
graph-build time.
"""
from __future__ import annotations

TAG_VOCABULARY = ("VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN")

# Allowed `basis` values when a tag carries one (AI.md documents this list).
BASIS_VALUES = ("unverified", "partly measured")

# Pre-lock compound tag strings some typology source registries still write
# (typology/edges/owned_by.yaml, typology/edges/decides.yaml,
# typology/nodes/sensors.yaml) -- tools/typology/build_graph.py normalizes
# each of these down to a TAG_VOCABULARY value plus the qualifier dict shown,
# at node/edge-build time, so nothing outside TAG_VOCABULARY ever reaches a
# served surface.
COMPOUND_TAG_MAP = {
    "VERIFIED-CONTRADICTED": ("VERIFIED", {"contradicted": True}),
    "RELAYED-unverified": ("RELAYED", {"basis": "unverified"}),
    "MEASURED+OPEN": ("OPEN", {"basis": "partly measured"}),
}
