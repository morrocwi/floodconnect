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
        "REPO_KG",
        "AGENT_COORDINATION",
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
        "PROSPECTIVE_EXPERIMENTS",
        "RAW_STAGE_FORECAST",
        "HIERARCHICAL_FLOOD_ZOOM",
        "BURDEN_LEDGER",
        "CANAL_CHAIN_MODEL",
        "WATER_BALANCE",
        "DRAINAGE_CAPACITY_INPUTS",
        "SOCIAL_LISTENING",
    ):
        assert node_id in nodes


def test_ai_boot_path_starts_with_single_entrypoint_and_kg():
    """2026-10-02 fix (defect H4/M2): `AI.md` -- the minimal
    compute entrypoint `kb.py answer` points callers at -- is registered right after
    `AGENTS.md` (index 1), not appended as the list's last entry. Before this fix AI.md's
    own "start here" claim contradicted the boot sequence it was never actually first
    (or even early) in."""
    doc = rkg.load_kg(KG_PATH)
    assert doc["ai_boot_sequence"][:4] == [
        "AGENTS.md",
        "AI.md",
        "docs/AI_ENTRYPOINT.md",
        "site/inputs/meta/floodconnect_repo_kg.yaml",
    ]
    assert "AI.md" in doc["ai_boot_sequence"]
    # exactly one occurrence -- never duplicated.
    assert doc["ai_boot_sequence"].count("AI.md") == 1


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
        "multi_agent_write_or_handoff",
        "prospective_test_or_backtest",
        "toledo_water_balance_or_capacity",
        "experimental_flood_model_or_forecast",
        "social_or_community_reports",
    ):
        assert route in routes


def test_jsonld_export_contains_nodes_and_relations():
    doc = rkg.load_kg(KG_PATH)
    exported = rkg.to_jsonld(doc)
    graph = exported["@graph"]
    assert any(x.get("@id") == "fc:FC_ROOT" for x in graph)
    assert any(x.get("@type") == "fc:Relation" for x in graph)


def test_experimental_models_are_not_connected_as_operational_truth():
    doc = rkg.load_kg(KG_PATH)
    assert doc["nodes"]["WATER_BALANCE"]["epistemic_class"] == "PROPOSAL"
    assert doc["nodes"]["CANAL_CHAIN_MODEL"]["epistemic_class"] == "PROPOSAL"
    assert doc["nodes"]["BURDEN_LEDGER"]["epistemic_class"] == "PROPOSAL"
    assert doc["nodes"]["PROSPECTIVE_EXPERIMENTS"]["epistemic_class"] == "FIELD_EVIDENCE"


def test_raw_stage_helper_is_not_laundered_into_hydraulic_forecast():
    doc = rkg.load_kg(KG_PATH)
    assert "raw stage persistence -/-> hydraulic forecast" in set(doc["hard_non_edges"])


def test_node_ontology_separates_hydraulic_community_service_tool_and_actor_nodes():
    doc = rkg.load_kg(KG_PATH)
    ontology = doc["node_ontology"]
    for kind in (
        "hydraulic_node",
        "community_node",
        "service_node",
        "shelter_operation_node",
        "tool_node",
        "governance_actor_node",
        "information_product",
    ):
        assert kind in ontology
    assert ontology["tool_node"]["rule"].startswith("may attach capability")
    assert ontology["governance_actor_node"]["rule"] == "identity is canonical; roles are overlays"


def test_edge_ontology_keeps_movement_and_support_separate():
    doc = rkg.load_kg(KG_PATH)
    edges = doc["edge_ontology"]
    assert "resident_movement_edge" in edges
    assert "lifeline_support_edge" in edges
    assert edges["resident_movement_edge"]["semantics"] != edges["lifeline_support_edge"]["semantics"]


def test_multi_agent_coordination_is_gated_by_claims_and_full_ci():
    doc = rkg.load_kg(KG_PATH)
    edges = {(x["from"], x["relation"], x["to"]) for x in doc["edges"]}
    assert ("AGENT_COORDINATION", "USES_CANONICAL_NODE_IDS_FROM", "REPO_KG") in edges
    assert ("CI", "ENFORCES", "AGENT_COORDINATION") in edges
    non_edges = set(doc["hard_non_edges"])
    assert "file-level non-conflict -/-> semantic non-conflict" in non_edges
    assert "task-specific test pass -/-> full integration safety" in non_edges
