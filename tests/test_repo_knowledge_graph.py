from pathlib import Path

import repo_knowledge_graph as rkg


KG_PATH = Path("site/inputs/meta/floodconnect_repo_kg.yaml")


def test_repo_knowledge_graph_is_structurally_valid():
    doc = rkg.load_kg(KG_PATH)
    errors = rkg.validate_kg(doc, Path("."))
    assert errors == []


def test_core_constructs_are_present():
    doc = rkg.load_kg(KG_PATH)
    nodes = doc["nodes"]
    for node_id in (
        "RIVER_KG",
        "BANGKOK_CANAL_KG",
        "LIVE_DATA_SYSTEM",
        "SAMMAKORN_HYDRAULIC",
        "COMMUNITY_DAG",
        "LVCN",
        "TDLC",
        "LCF",
        "LCB",
        "SOCL",
        "ORCG",
        "PSSS",
        "HAHU",
        "ENV_DEGRADATION",
        "UNIFIED_CRISIS",
        "GOVERNANCE",
        "WARNING_TYPOLOGY",
    ):
        assert node_id in nodes


def test_ai_boot_path_starts_with_single_entrypoint_and_kg():
    doc = rkg.load_kg(KG_PATH)
    assert doc["ai_boot_sequence"][:2] == [
        "docs/AI_ENTRYPOINT.md",
        "site/inputs/meta/floodconnect_repo_kg.yaml",
    ]


def test_warning_typology_depends_on_canonical_governance_identity():
    doc = rkg.load_kg(KG_PATH)
    edges = {
        (x["from"], x["relation"], x["to"])
        for x in doc["edges"]
    }
    assert (
        "GOVERNANCE",
        "PROVIDES_CANONICAL_ACTOR_IDENTITIES_TO",
        "WARNING_TYPOLOGY",
    ) in edges


def test_shelter_board_is_gated_by_shelter_operation_level():
    doc = rkg.load_kg(KG_PATH)
    edges = {
        (x["from"], x["relation"], x["to"])
        for x in doc["edges"]
    }
    assert ("SOCL", "GATES", "LCB") in edges


def test_tool_graph_never_replaces_route_or_dry_gate():
    doc = rkg.load_kg(KG_PATH)
    non_edges = set(doc["hard_non_edges"])
    assert "tool_node -/-> route safe" in non_edges
    assert "pump present -/-> Dry Gate passed" in non_edges


def test_question_routes_cover_major_user_intents():
    doc = rkg.load_kg(KG_PATH)
    routes = doc["question_routes"]
    for route in (
        "current_water_or_flood_status",
        "sammakorn_pond_pump_gate",
        "household_or_community_survival",
        "route_or_evacuation",
        "supplies_support_or_last_mile",
        "shelter_or_dry_node",
        "government_agency_or_who_is_responsible",
        "warning_alert_or_who_warns",
        "overall_decision_state",
    ):
        assert route in routes


def test_jsonld_export_contains_nodes_and_relations():
    doc = rkg.load_kg(KG_PATH)
    exported = rkg.to_jsonld(doc)
    graph = exported["@graph"]
    assert any(x.get("@id") == "fc:FC_ROOT" for x in graph)
    assert any(x.get("@type") == "fc:Relation" for x in graph)
