import copy

import community_dag as cd


def _base_doc():
    return {
        "nodes": {
            "h": {
                "kind": "household", "layer": 0,
                "status": "UNKNOWN", "fresh": False,
            },
            "b": {
                "kind": "buddy_cell", "layer": 1,
                "status": "SAFE", "fresh": True,
                "capacity_persons": 20, "occupied_persons": 1,
            },
            "z": {
                "kind": "zone", "layer": 2,
                "status": "SAFE", "fresh": True,
                "capacity_persons": 30, "occupied_persons": 3,
            },
            "i": {
                "kind": "internal_safe", "layer": 3,
                "status": "SAFE", "fresh": True,
                "capacity_persons": 20, "occupied_persons": 2,
            },
            "e": {
                "kind": "egress", "layer": 4,
                "status": "SAFE", "fresh": True,
                "capacity_persons": 50, "occupied_persons": 0,
            },
            "x": {
                "kind": "external_safe", "layer": 5,
                "status": "SAFE", "fresh": True, "verified_safe": True,
                "capacity_persons": 100, "occupied_persons": 10,
                "services": ["water", "power", "toilet"],
            },
        },
        "edges": [
            {
                "id": "hb", "from": "h", "to": "b",
                "status": "OPEN", "safety": "CLEAR",
                "fresh": True, "field_verified": True,
                "modes": ["walk"], "max_group": 10, "distance_m": 50,
            },
            {
                "id": "bz", "from": "b", "to": "z",
                "status": "OPEN", "safety": "CLEAR",
                "fresh": True, "field_verified": True,
                "modes": ["walk"], "max_group": 10, "distance_m": 100,
            },
            {
                "id": "zi", "from": "z", "to": "i",
                "status": "OPEN", "safety": "CLEAR",
                "fresh": True, "field_verified": True,
                "modes": ["walk"], "max_group": 10, "distance_m": 150,
            },
            {
                "id": "ie", "from": "i", "to": "e",
                "status": "OPEN", "safety": "CLEAR",
                "fresh": True, "field_verified": True,
                "modes": ["walk"], "max_group": 10, "distance_m": 200,
            },
            {
                "id": "ex", "from": "e", "to": "x",
                "status": "OPEN", "safety": "CLEAR",
                "fresh": True, "field_verified": True,
                "modes": ["walk"], "max_group": 10, "distance_m": 500,
            },
        ],
    }


def test_declared_layering_is_valid_dag():
    check = cd.validate_document(_base_doc())
    assert check["valid"] is True
    assert check["topological_order"][0] == "h"
    assert check["topological_order"][-1] == "x"


def test_backward_edge_is_rejected():
    doc = _base_doc()
    doc["edges"].append({
        "id": "bad", "from": "z", "to": "b",
        "status": "OPEN", "safety": "CLEAR",
        "fresh": True, "field_verified": True, "modes": ["walk"],
    })
    check = cd.validate_document(doc)
    assert check["valid"] is False
    assert any("DAG layer rule violated" in e for e in check["errors"])


def test_unknown_or_unverified_edge_is_not_routed():
    doc = _base_doc()
    doc["edges"][-1]["status"] = "UNKNOWN"
    result = cd.find_safe_route(doc, "h", group_size=2, mode="walk")
    assert result.found is False

    doc2 = _base_doc()
    doc2["edges"][-1]["field_verified"] = False
    result2 = cd.find_safe_route(doc2, "h", group_size=2, mode="walk")
    assert result2.found is False


def test_external_target_requires_services_and_capacity():
    doc = _base_doc()
    result = cd.find_safe_route(
        doc, "h", group_size=2, mode="walk", needs=["water", "power"]
    )
    assert result.found is True
    assert result.target == "x"

    no_service = cd.find_safe_route(
        doc, "h", group_size=2, mode="walk", needs=["first_aid"]
    )
    assert no_service.found is False

    doc["nodes"]["x"]["capacity_persons"] = 11
    doc["nodes"]["x"]["occupied_persons"] = 10
    no_capacity = cd.find_safe_route(doc, "h", group_size=2, mode="walk")
    assert no_capacity.found is False


def test_lexicographic_rule_prefers_no_assistance_over_shorter_route():
    doc = _base_doc()

    # Add a much shorter direct route, but it requires assistance.
    doc["edges"].append({
        "id": "hx_assisted", "from": "h", "to": "x",
        "status": "ASSISTED", "safety": "CLEAR",
        "fresh": True, "field_verified": True,
        "modes": ["walk"], "max_group": 10, "distance_m": 10,
    })

    result = cd.find_safe_route(doc, "h", group_size=1, mode="walk")
    assert result.found is True
    assert result.path == ("h", "b", "z", "i", "e", "x")
    assert result.score[0] == 0  # no assisted edge


def test_stale_safe_node_is_not_a_target():
    doc = _base_doc()
    doc["nodes"]["x"]["fresh"] = False
    result = cd.find_safe_route(doc, "h")
    assert result.found is False


def test_seed_style_unknown_graph_valid_but_not_routable():
    doc = _base_doc()
    for node_id, node in doc["nodes"].items():
        if node_id != "h":
            node["status"] = "UNKNOWN"
            node["fresh"] = False
    doc["nodes"]["x"]["verified_safe"] = False
    for edge in doc["edges"]:
        edge["status"] = "UNKNOWN"
        edge["safety"] = "UNKNOWN"
        edge["fresh"] = False
        edge["field_verified"] = False

    check = cd.validate_document(copy.deepcopy(doc))
    assert check["valid"] is True
    result = cd.find_safe_route(doc, "h")
    assert result.found is False


def test_service_node_can_live_at_multiple_operational_layers():
    doc = _base_doc()
    doc["nodes"]["svc"] = {
        "kind": "service_node",
        "layer": 3,
        "status": "SAFE",
        "fresh": True,
        "capabilities": ["food_preparation", "veterinary_support"],
    }
    check = cd.validate_document(doc)
    assert check["valid"] is True
    assert cd.node_capabilities(doc["nodes"]["svc"]) == {
        "food_preparation", "veterinary_support"
    }


def test_service_node_invalid_layer_is_rejected():
    doc = _base_doc()
    doc["nodes"]["svc"] = {
        "kind": "service_node",
        "layer": 1,
        "status": "SAFE",
        "fresh": True,
        "capabilities": ["food_preparation"],
    }
    check = cd.validate_document(doc)
    assert check["valid"] is False
    assert any("service_node layer" in e for e in check["errors"])


def test_external_target_accepts_capabilities_as_services():
    doc = _base_doc()
    doc["nodes"]["x"]["services"] = []
    doc["nodes"]["x"]["capabilities"] = ["water", "power", "toilet"]
    result = cd.find_safe_route(
        doc, "h", group_size=1, mode="walk", needs=["water", "power"]
    )
    assert result.found is True
