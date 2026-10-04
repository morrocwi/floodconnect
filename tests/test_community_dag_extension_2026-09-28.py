"""
tests/test_community_dag_extension_2026-09-28.py -- extensions to the imported
Community Self-Help DAG protocol (public/main 5364c23): boat/high_clearance modes,
`support` node kind, and the access-first priority rule. Extends the protocol, does not
fork it -- reuses community_dag.py's own hard-constraint discipline throughout.
"""
import copy

import community_dag as cd


def _base_doc():
    return {
        "nodes": {
            "h": {"kind": "household", "layer": 0, "status": "UNKNOWN", "fresh": False},
            "b": {"kind": "buddy_cell", "layer": 1, "status": "SAFE", "fresh": True,
                  "capacity_persons": 20, "occupied_persons": 1},
            "z": {"kind": "zone", "layer": 2, "status": "SAFE", "fresh": True,
                  "capacity_persons": 30, "occupied_persons": 3},
            "sup": {"kind": "support", "layer": 3, "status": "SAFE", "fresh": True,
                    "capacity_persons": None, "occupied_persons": None,
                    "services": ["kitchen", "charging"]},
            "i": {"kind": "internal_safe", "layer": 3, "status": "SAFE", "fresh": True,
                  "capacity_persons": 20, "occupied_persons": 2},
            "e": {"kind": "egress", "layer": 4, "status": "SAFE", "fresh": True,
                  "capacity_persons": 50, "occupied_persons": 0},
            "x": {"kind": "external_safe", "layer": 5, "status": "SAFE", "fresh": True,
                  "verified_safe": True, "capacity_persons": 100, "occupied_persons": 10,
                  "services": ["water", "power", "toilet"]},
        },
        "edges": [
            {"id": "hb", "from": "h", "to": "b", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk"], "max_group": 10,
             "distance_m": 50},
            {"id": "bz", "from": "b", "to": "z", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk"], "max_group": 10,
             "distance_m": 100},
            {"id": "z_sup", "from": "z", "to": "sup", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk"], "max_group": 10,
             "distance_m": 20},
            {"id": "zi", "from": "z", "to": "i", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk", "boat"],
             "max_group": 10, "distance_m": 150},
            {"id": "ie", "from": "i", "to": "e", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk", "high_clearance"],
             "max_group": 10, "distance_m": 200},
            {"id": "ex", "from": "e", "to": "x", "status": "OPEN", "safety": "CLEAR",
             "fresh": True, "field_verified": True, "modes": ["walk", "vehicle"],
             "max_group": 50, "distance_m": 500},
        ],
    }


def test_support_kind_valid_and_shares_layer_3_with_internal_safe():
    doc = _base_doc()
    result = cd.validate_document(doc)
    assert result["valid"], result["errors"]
    assert cd.KIND_LAYER["support"] == cd.KIND_LAYER["internal_safe"] == 3


def test_zone_to_support_edge_is_forward_valid():
    doc = _base_doc()
    result = cd.validate_document(doc)
    assert not any("z_sup" in e for e in result["errors"])


def test_boat_and_high_clearance_are_valid_modes():
    doc = _base_doc()
    result = cd.validate_document(doc)
    assert result["valid"], result["errors"]
    assert "boat" in cd.EDGE_MODES
    assert "high_clearance" in cd.EDGE_MODES


def test_unknown_mode_is_a_schema_error():
    doc = _base_doc()
    doc["edges"][3]["modes"] = ["walk", "jetpack"]
    result = cd.validate_document(doc)
    assert not result["valid"]
    assert any("jetpack" in e for e in result["errors"])


def test_find_safe_route_by_boat_uses_boat_only_edge():
    doc = _base_doc()
    result = cd.find_safe_route(doc, "h", mode="boat")
    # "zi" allows boat, "ie" does NOT allow boat (only walk/high_clearance) -- so a
    # boat-only traveller should NOT find a route through this specific doc (hard
    # constraint, not a guess)
    assert result.found is False


def test_find_safe_route_by_high_clearance_end_to_end():
    doc = _base_doc()
    # give every edge along the path a high_clearance option so a full route exists
    for e in doc["edges"]:
        modes = set(e["modes"])
        modes.add("high_clearance")
        e["modes"] = sorted(modes)
    result = cd.find_safe_route(doc, "h", mode="high_clearance")
    assert result.found is True
    assert result.target == "x"


def test_zone_priority_restore_access_when_no_fitting_mode_edge():
    """Zone's onward edge only supports walk/boat; zone's demand requires high_clearance
    (deep water, mobility-limited household) -- no verified edge fits -> RESTORE_ACCESS
    first."""
    doc = _base_doc()
    order = cd.zone_priority_order(doc, "z", required_modes={"high_clearance"})
    assert order[0] == cd.PRIORITY_RESTORE_ACCESS
    assert order == [cd.PRIORITY_RESTORE_ACCESS, cd.PRIORITY_SUPPORT, cd.PRIORITY_EVACUATE]


def test_zone_priority_support_first_when_access_exists():
    doc = _base_doc()
    order = cd.zone_priority_order(doc, "z", required_modes={"walk"})
    assert order == [cd.PRIORITY_SUPPORT, cd.PRIORITY_EVACUATE]
    assert cd.PRIORITY_RESTORE_ACCESS not in order


def test_zone_priority_unknown_status_not_treated_as_safe():
    """An edge/transit node with UNKNOWN status must never count as access, even if its
    mode matches -- matches the protocol's existing 'UNKNOWN is not routable' rule."""
    doc = _base_doc()
    doc["nodes"]["e"]["status"] = "UNKNOWN"
    order = cd.zone_priority_order(doc, "z", required_modes={"walk"})
    assert order[0] == cd.PRIORITY_RESTORE_ACCESS


def test_zone_priority_edge_not_field_verified_not_treated_as_access():
    doc = _base_doc()
    doc["edges"][3]["field_verified"] = False  # zi
    doc["edges"][4]["field_verified"] = False  # ie
    order = cd.zone_priority_order(doc, "z", required_modes={"walk"})
    assert order[0] == cd.PRIORITY_RESTORE_ACCESS


def test_support_services_vocabulary_documented():
    assert cd.SUPPORT_SERVICES == {"kitchen", "medical_post", "charging", "supply_depot",
                                     "donation_point", "rescue_staging"}
