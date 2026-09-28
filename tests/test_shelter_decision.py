import copy

import shelter_decision as sd


def _node(kind, *, sustain=None, status="SAFE", fresh=True, capacity=20, occupied=0):
    layers = {
        "household": 0,
        "buddy_cell": 1,
        "zone": 2,
        "internal_safe": 3,
        "egress": 4,
        "external_safe": 5,
        "supply_point": 5,
    }
    out = {
        "kind": kind,
        "layer": layers[kind],
        "status": status,
        "fresh": fresh,
        "capacity_persons": capacity,
        "occupied_persons": occupied,
        "services": [],
    }
    if sustain is not None:
        out["sustainment"] = sustain
    return out


def _sustain(**overrides):
    block = {
        "fresh": True,
        "assessed_horizon_h": 72,
        "physical_safety": "SAFE",
        "potable_water_for_horizon": "SUFFICIENT",
        "service_water_for_horizon": "SUFFICIENT",
        "food_for_horizon": "SUFFICIENT",
        "essential_medicine_for_horizon": "SUFFICIENT",
        "critical_power": "NOT_REQUIRED",
        "sanitation_hygiene": "SUFFICIENT",
        "communications": "SUFFICIENT",
        "vulnerable_support": "SUFFICIENT",
        "official_instruction": "NONE",
        "escalation": {"status": "AVAILABLE", "fresh": True, "verified": True},
        "resupply": {
            "supplier_node": None,
            "route_edges": [],
            "official_movement_conflict": False,
        },
    }
    block.update(overrides)
    return block


def _shelter_ready():
    return {
        "site_hazard_safety": "SAFE",
        "structural_fire_safety": "SAFE",
        "access_accessibility": "AVAILABLE",
        "drinking_water": "SUFFICIENT",
        "service_water": "SUFFICIENT",
        "sanitation_hygiene": "SUFFICIENT",
        "food_special_diets": "SUFFICIENT",
        "medicine_health": "SUFFICIENT",
        "critical_power": "SUFFICIENT",
        "communications": "AVAILABLE",
        "capacity": "SUFFICIENT",
        "member_accountability": "READY",
        "vulnerable_support": "SUFFICIENT",
        "resupply_access": "AVAILABLE",
        "management_staffing": "READY",
        "waste_management": "READY",
        "sleeping_protection": "READY",
        "privacy_dignity": "READY",
        "child_safeguarding": "READY",
        "gbv_protection": "READY",
        "feedback_complaints": "READY",
        "family_unity": "READY",
        "psychosocial_referral": "READY",
        "residual_flood_exposure": "NONE",
        "perimeter_flood_defense": "NOT_REQUIRED",
        "dewatering_capability": "NOT_REQUIRED",
        "post_flood_cleaning": "READY",
        "exit_closure_plan": "READY",
    }


def _movement_chain():
    nodes = {
        "h": _node("household", sustain=_sustain()),
        "b": _node("buddy_cell", sustain=_sustain()),
        "z": _node("zone", sustain=_sustain()),
        "i": _node("internal_safe", sustain=_sustain()),
        "e": _node("egress"),
        "x": _node("external_safe", sustain=_sustain(), capacity=100),
        "shop": {
            "kind": "supply_point",
            "layer": 5,
            "status": "SAFE",
            "fresh": True,
            "verified_service": True,
            "capacity_persons": 100,
            "occupied_persons": 0,
            "services": ["food", "water"],
            "support": {
                "fresh": True,
                "assessed_horizon_h": 72,
                "resources": {
                    "food_for_horizon": "SUFFICIENT",
                    "potable_water_for_horizon": "SUFFICIENT",
                    "service_water_for_horizon": "SUFFICIENT",
                    "essential_medicine_for_horizon": "SUFFICIENT",
                    "sanitation_hygiene": "SUFFICIENT",
                    "communications": "SUFFICIENT",
                    "vulnerable_support": "SUFFICIENT",
                    "critical_power": "SUFFICIENT",
                },
            },
        },
    }
    for support_id in ("b", "z"):
        nodes[support_id]["support"] = {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {
                "food_for_horizon": "SUFFICIENT",
                "potable_water_for_horizon": "SUFFICIENT",
                "service_water_for_horizon": "SUFFICIENT",
                "essential_medicine_for_horizon": "SUFFICIENT",
                "sanitation_hygiene": "SUFFICIENT",
                "communications": "SUFFICIENT",
                "vulnerable_support": "SUFFICIENT",
                "critical_power": "SUFFICIENT",
            },
        }
    nodes["i"]["shelter"] = _shelter_ready()
    nodes["x"]["shelter"] = _shelter_ready()
    nodes["x"]["verified_safe"] = True
    edges = []
    for edge_id, u, v in [
        ("hb", "h", "b"),
        ("bz", "b", "z"),
        ("zi", "z", "i"),
        ("ie", "i", "e"),
        ("ex", "e", "x"),
        ("es", "e", "shop"),
    ]:
        edges.append({
            "id": edge_id,
            "from": u,
            "to": v,
            "status": "OPEN",
            "safety": "CLEAR",
            "fresh": True,
            "field_verified": True,
            "modes": ["walk", "vehicle"],
            "max_group": 10,
            "distance_m": 100,
        })
    nodes["h"]["support_candidates"] = ["h", "b", "z", "i", "x"]
    return {"nodes": nodes, "edges": edges, "support_edges": []}


def test_sustainment_is_separate_from_escalation():
    node = _node(
        "household",
        sustain=_sustain(
            escalation={"status": "UNAVAILABLE", "fresh": True, "verified": True}
        ),
    )
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.SUSTAINABLE
    assert result.escalation_state == sd.ISOLATED
    assert sd.REASON_NO_ESCALATION_MECHANISM in result.reason_codes


def test_unknown_essential_never_becomes_sufficient():
    node = _node(
        "household",
        sustain=_sustain(food_for_horizon="UNKNOWN"),
    )
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.UNKNOWN
    assert "food_for_horizon" in result.unknown_fields


def test_declared_food_gap_is_not_sustainable():
    node = _node(
        "household",
        sustain=_sustain(food_for_horizon="INSUFFICIENT"),
    )
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.NOT_SUSTAINABLE
    assert sd.REASON_INSUFFICIENT_FOOD in result.reason_codes


def test_household_can_be_exact_lvcn():
    doc = _movement_chain()
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.state == sd.EXACT_LVCN
    assert result.node_id == "h"
    assert result.exact is True


def test_buddy_can_close_resource_gap_only_with_verified_support_edge():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["support_edges"] = [{
        "id": "b_to_h",
        "from": "b",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "capacity_status": "SUFFICIENT",
        "arrival_before_failure": True,
        "resources": ["food_for_horizon"],
    }]
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.state == sd.EXACT_LVCN
    assert result.node_id == "b"


def test_unverified_support_edge_cannot_promote_buddy():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["support_edges"] = [{
        "id": "b_to_h",
        "from": "b",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": False,
        "resources": ["food_for_horizon"],
    }]
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.node_id != "b"


def test_egress_is_never_lvcn_candidate():
    doc = _movement_chain()
    doc["nodes"]["h"]["support_candidates"] = ["e", "x"]
    doc["nodes"]["h"]["sustainment"]["physical_safety"] = "UNSAFE"
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.node_id != "e"


def test_higher_known_viable_does_not_erase_lower_unknown():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "UNKNOWN"
    doc["nodes"]["b"]["sustainment"]["food_for_horizon"] = "UNKNOWN"
    doc["nodes"]["z"]["sustainment"]["food_for_horizon"] = "UNKNOWN"
    # Internal shelter is known viable and reachable.
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.state == sd.KNOWN_VIABLE_UPPER_BOUND
    assert result.node_id == "i"
    assert result.exact is False
    assert sd.REASON_LOWER_NODE_UNRESOLVED in result.reason_codes


def test_resupply_window_requires_verified_route_and_supplier():
    doc = _movement_chain()
    h = doc["nodes"]["h"]
    h["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    h["sustainment"]["resupply"] = {
        "supplier_node": "shop",
        "route_edges": ["hb", "bz", "zi", "ie", "es"],
        "official_movement_conflict": False,
    }
    result = sd.evaluate_resupply_window(doc, "h", 24, mode="walk")
    assert result.admitted is True
    assert result.state == "RESUPPLY_WINDOW"


def test_stale_resupply_route_is_refused():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["sustainment"]["resupply"] = {
        "supplier_node": "shop",
        "route_edges": ["hb", "bz", "zi", "ie", "es"],
        "official_movement_conflict": False,
    }
    doc["edges"][-1]["fresh"] = False
    result = sd.evaluate_resupply_window(doc, "h", 24, mode="walk")
    assert result.admitted is False
    assert sd.REASON_RESUPPLY_ROUTE_UNVERIFIED in result.reason_codes


def test_official_movement_conflict_blocks_resupply():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["sustainment"]["resupply"] = {
        "supplier_node": "shop",
        "route_edges": ["hb", "bz", "zi", "ie", "es"],
        "official_movement_conflict": True,
    }
    result = sd.evaluate_resupply_window(doc, "h", 24)
    assert result.admitted is False
    assert sd.REASON_OFFICIAL_MOVEMENT_CONFLICT in result.reason_codes


def test_shelter_with_service_water_failure_is_rejected():
    node = _node("internal_safe", sustain=_sustain())
    node["shelter"] = _shelter_ready()
    node["shelter"]["service_water"] = "INSUFFICIENT"
    result = sd.screen_shelter_candidate(node, phase="OCCUPIED")
    assert result.admitted is False
    assert "service_water" in result.details["failed"]


def test_shelter_on_unsafe_site_rejected_even_if_everything_else_ready():
    node = _node("internal_safe", sustain=_sustain())
    node["shelter"] = _shelter_ready()
    node["shelter"]["site_hazard_safety"] = "UNSAFE"
    result = sd.screen_shelter_candidate(node, phase="OCCUPIED")
    assert result.admitted is False
    assert sd.REASON_SHELTER_UNSAFE in result.reason_codes


def test_recovery_phase_requires_cleaning_and_waste_management():
    node = _node("internal_safe", sustain=_sustain())
    node["shelter"] = _shelter_ready()
    node["shelter"]["post_flood_cleaning"] = "UNKNOWN"
    result = sd.screen_shelter_candidate(node, phase="RECOVERY")
    assert result.admitted is False
    assert "post_flood_cleaning" in result.details["unknown"]


def test_member_profile_strips_personal_fields():
    profile = {
        "total_persons": 5,
        "older_adult_alone": 1,
        "infant_feeding": 1,
        "essential_medication": 2,
        "name": "SHOULD NOT LEAK",
        "phone": "SHOULD NOT LEAK",
        "diagnosis": "SHOULD NOT LEAK",
    }
    out = sd.aggregate_member_need_profile(profile)
    assert out["total_persons"] == 5
    assert out["older_adult_alone"] == 1
    assert "name" not in out
    assert "phone" not in out
    assert "diagnosis" not in out


def test_not_sustainable_without_route_requests_logistics_not_unsafe_walkout():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    for edge in doc["edges"]:
        edge["fresh"] = False
    result = sd.recommend_protective_state(doc, "h", 24)
    assert result.state == "REQUEST_LOGISTICS_OR_REASSESS_MOVEMENT"
    assert result.admitted is False


def test_official_evacuation_with_no_verified_route_requests_assistance():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["official_instruction"] = "EVACUATE"
    for edge in doc["edges"]:
        edge["field_verified"] = False
    result = sd.recommend_protective_state(doc, "h", 24)
    assert result.state == "REQUEST_ASSISTED_EVACUATION"
    assert result.admitted is False


def test_verified_inward_delivery_preserves_household_support_option():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["kitchen"] = {
        "kind": "supply_point",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "verified_service": True,
        "capacity_persons": 0,
        "occupied_persons": 0,
        "services": ["food_for_horizon"],
        "support": {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {"food_for_horizon": "SUFFICIENT"},
        },
    }
    doc["support_edges"] = [{
        "id": "kitchen_to_household",
        "from": "kitchen",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "capacity_status": "SUFFICIENT",
        "arrival_before_failure": True,
        "resources": ["food_for_horizon"],
    }]
    result = sd.evaluate_support_delivery(
        doc, "h", "kitchen", ["food_for_horizon"], 24
    )
    assert result.admitted is True
    assert result.state == "SUPPORT_DELIVERY_NEED_CLOSABLE"


def test_unverified_inward_delivery_does_not_push_people_to_assume_supply():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["kitchen"] = {
        "kind": "supply_point",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "verified_service": True,
        "capacity_persons": 0,
        "occupied_persons": 0,
        "services": ["food_for_horizon"],
        "support": {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {"food_for_horizon": "SUFFICIENT"},
        },
    }
    doc["support_edges"] = [{
        "id": "kitchen_to_household",
        "from": "kitchen",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": False,
        "resources": ["food_for_horizon"],
    }]
    result = sd.evaluate_support_delivery(
        doc, "h", "kitchen", ["food_for_horizon"], 24
    )
    assert result.admitted is False
    assert sd.REASON_SUPPORT_DELIVERY_PATH_UNVERIFIED in result.reason_codes


def test_protective_state_prefers_verified_delivery_before_unverified_self_movement():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["sustainment"]["support_providers"] = ["kitchen"]
    doc["nodes"]["kitchen"] = {
        "kind": "supply_point",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "verified_service": True,
        "capacity_persons": 0,
        "occupied_persons": 0,
        "services": ["food_for_horizon"],
        "support": {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {"food_for_horizon": "SUFFICIENT"},
        },
    }
    doc["support_edges"] = [{
        "id": "kitchen_to_household",
        "from": "kitchen",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "capacity_status": "SUFFICIENT",
        "arrival_before_failure": True,
        "resources": ["food_for_horizon"],
    }]
    for edge in doc["edges"]:
        edge["fresh"] = False
    result = sd.recommend_protective_state(doc, "h", 24)
    assert result.admitted is True
    assert result.state == "REQUEST_OR_RECEIVE_SUPPORT_DELIVERY"


def test_shop_presence_without_verified_stock_is_not_resupply():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["shop"]["verified_service"] = False
    doc["nodes"]["h"]["sustainment"]["resupply"] = {
        "supplier_node": "shop",
        "route_edges": ["hb", "bz", "zi", "ie", "es"],
        "official_movement_conflict": False,
    }
    result = sd.evaluate_resupply_window(doc, "h", 24, mode="walk")
    assert result.admitted is False
    assert sd.REASON_RESUPPLY_DESTINATION_UNVERIFIED in result.reason_codes


def test_vulnerable_groups_are_kept_as_distinct_aggregate_categories():
    profile = {
        "total_persons": 7,
        "child_0_5": 1,
        "child_6_12": 1,
        "older_adult_60_plus": 2,
        "pregnant_person": 1,
        "essential_medication": 2,
        "single_person_household": 0,
        "co_resident_caregivers": 2,
        "name": "MUST_NOT_LEAK",
        "diagnosis": "MUST_NOT_LEAK",
    }
    out = sd.aggregate_member_need_profile(profile)
    assert out["child_0_5"] == 1
    assert out["child_6_12"] == 1
    assert out["older_adult_60_plus"] == 2
    assert out["pregnant_person"] == 1
    assert out["co_resident_caregivers"] == 2
    assert "name" not in out
    assert "diagnosis" not in out


def test_dependency_pairing_gap_is_explicit_not_demographic_score():
    profile = {
        "total_persons": 1,
        "older_adult_60_plus": 1,
        "needs_mobility_assistance": 1,
        "older_adult_support_link_uncovered": 1,
        "mobility_support_link_uncovered": 0,
        "living_alone_buddy_link_uncovered": 0,
    }
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is False
    assert result.state == "DEPENDENCY_SUPPORT_GAP"
    assert "older_adult_support_link_uncovered" in result.details["uncovered_links"]


def test_all_dependency_links_covered():
    profile = {
        "total_persons": 2,
        "adult_18_59": 1,
        "child_0_5": 1,
        "child_caregiver_link_uncovered": 0,
    }
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is True
    assert result.state == "DEPENDENCY_COVERED"


def test_unknown_dependency_link_stays_unknown():
    profile = {
        "total_persons": 1,
        "older_adult_60_plus": 1,
        "needs_mobility_assistance": 1,
        "older_adult_support_link_uncovered": "UNKNOWN",
        "mobility_support_link_uncovered": 0,
        "living_alone_buddy_link_uncovered": 0,
    }
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is False
    assert result.state == "DEPENDENCY_COVERAGE_UNKNOWN"


def test_child_with_older_only_is_flagged_but_not_declared_unsafe():
    profile = {
        "total_persons": 2,
        "child_0_5": 1,
        "older_adult_60_plus": 1,
        "adult_18_59": 0,
        "living_arrangement": "PAIR",
    }
    result = sd.classify_group_configuration(profile)
    assert result.admitted is True
    assert "CHILD_WITH_OLDER_ONLY" in result.details["composition_tags"]
    assert result.state == "GROUP_CONFIGURATION_CLASSIFIED"


def test_two_older_adults_are_not_assumed_to_be_helpers():
    profile = {
        "total_persons": 2,
        "older_adult_60_plus": 2,
        "needs_mobility_assistance": 1,
        "older_adult_support_link_uncovered": 0,
        "mobility_support_link_uncovered": "UNKNOWN",
    }
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is False
    assert result.state == "DEPENDENCY_COVERAGE_UNKNOWN"
    assert "mobility_support_link_uncovered" in result.details["unknown_links"]


def test_single_caregiver_with_child_requires_backup_link():
    profile = {
        "total_persons": 2,
        "child_0_5": 1,
        "adult_18_59": 1,
        "single_caregiver_household": 1,
        "child_caregiver_link_uncovered": 0,
        "backup_caregiver_link_uncovered": 1,
    }
    required = sd.required_support_links(profile)
    assert "child_caregiver_link_uncovered" in required
    assert "backup_caregiver_link_uncovered" in required
    result = sd.evaluate_dependency_coverage(profile)
    assert result.state == "DEPENDENCY_SUPPORT_GAP"


def test_pregnant_person_living_alone_requires_support_and_buddy_checks():
    profile = {
        "total_persons": 1,
        "pregnant_person": 1,
        "living_arrangement": "ALONE",
        "needs_maternal_health_access": 1,
        "pregnancy_support_link_uncovered": 0,
        "living_alone_buddy_link_uncovered": 0,
    }
    required = sd.required_support_links(profile)
    assert "pregnancy_support_link_uncovered" in required
    assert "living_alone_buddy_link_uncovered" in required
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is True


def test_medically_dependent_person_alone_requires_medical_and_buddy_links():
    profile = {
        "total_persons": 1,
        "chronic_or_acute_illness": 1,
        "needs_time_critical_medical_followup": 1,
        "medical_support_link_uncovered": 0,
        "living_alone_buddy_link_uncovered": 0,
    }
    required = sd.required_support_links(profile)
    assert "medical_support_link_uncovered" in required
    assert "living_alone_buddy_link_uncovered" in required


def test_multigenerational_household_tag_does_not_assume_support_capacity():
    profile = {
        "total_persons": 4,
        "child_0_5": 1,
        "adult_18_59": 2,
        "older_adult_60_plus": 1,
        "living_arrangement": "MULTIGENERATIONAL",
        "child_caregiver_link_uncovered": "UNKNOWN",
    }
    result = sd.classify_group_configuration(profile)
    assert "MULTIGENERATIONAL" in result.details["composition_tags"]
    coverage = sd.evaluate_dependency_coverage(profile)
    assert coverage.state == "DEPENDENCY_COVERAGE_UNKNOWN"


def test_sufficient_must_cover_requested_horizon():
    node = _node("household", sustain=_sustain(assessed_horizon_h=12))
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.UNKNOWN
    assert sd.REASON_ASSESSED_HORIZON_TOO_SHORT in result.reason_codes


def test_missing_assessed_horizon_is_unknown_not_safe():
    block = _sustain()
    block.pop("assessed_horizon_h")
    node = _node("household", sustain=block)
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.UNKNOWN
    assert sd.REASON_MISSING_ASSESSED_HORIZON in result.reason_codes


def test_lvcn_sorts_candidates_by_support_layer_not_yaml_order():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["support_candidates"] = ["x", "z", "b", "h", "i"]
    doc["support_edges"] = [{
        "id": "b_to_h",
        "from": "b",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "capacity_status": "SUFFICIENT",
        "arrival_before_failure": True,
        "resources": ["food_for_horizon"],
    }]
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.node_id == "b"


def test_support_path_without_capacity_or_timing_is_not_need_closable():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["kitchen"] = {
        "kind": "supply_point",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "verified_service": True,
        "services": ["food_for_horizon"],
        "support": {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {"food_for_horizon": "SUFFICIENT"},
        },
    }
    doc["support_edges"] = [{
        "id": "k_to_h",
        "from": "kitchen",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "resources": ["food_for_horizon"],
    }]
    result = sd.evaluate_support_delivery(doc, "h", "kitchen", ["food_for_horizon"], 24)
    assert result.admitted is False
    assert result.state == "SUPPORT_DELIVERY_PATH_ONLY"


def test_resource_deficit_does_not_auto_trigger_shelter_movement():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["sustainment"]["support_providers"] = []
    doc["nodes"]["h"]["sustainment"]["resupply"] = {
        "supplier_node": None,
        "route_edges": [],
        "official_movement_conflict": False,
    }
    result = sd.recommend_protective_state(doc, "h", 24)
    assert result.state == "REQUEST_LOGISTICS_OR_REASSESS_MOVEMENT"
    assert result.details["cause"] == "RESOURCE_OR_SERVICE_DEFICIT"


def test_physical_unsafe_still_moves_to_verified_route():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["physical_safety"] = "UNSAFE"
    result = sd.recommend_protective_state(doc, "h", 24)
    assert result.state == "PREPARE_TO_MOVE"
    assert result.details["cause"] == "PHYSICAL_UNSAFE"


def test_forward_hazard_can_coexist_with_current_stay_state():
    doc = _movement_chain()
    result = sd.recommend_protective_state(
        doc,
        "h",
        24,
        forward_hazard={
            "fresh": True,
            "state": "HIGH",
            "horizon_h": 24,
            "mobility_window_closing": False,
        },
    )
    assert result.admitted is True
    assert result.state == "STAY_AND_PREPARE"
    assert result.details["current_state"] == "SUSTAINABLE"
    assert result.details["forward_hazard"] == "HIGH"


def test_forward_hazard_window_closing_is_not_evacuate_by_itself():
    doc = _movement_chain()
    result = sd.recommend_protective_state(
        doc,
        "h",
        24,
        forward_hazard={
            "fresh": True,
            "state": "HIGH",
            "horizon_h": 24,
            "mobility_window_closing": True,
        },
    )
    assert result.state == "STAY_AND_PREPARE_WINDOW_CLOSING"


def test_supplier_presence_without_verified_stock_is_refused():
    doc = _movement_chain()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["shop"]["support"]["resources"]["food_for_horizon"] = "UNKNOWN"
    doc["nodes"]["h"]["sustainment"]["resupply"] = {
        "supplier_node": "shop",
        "route_edges": ["hb", "bz", "zi", "ie", "es"],
        "official_movement_conflict": False,
    }
    result = sd.evaluate_resupply_window(doc, "h", 24)
    assert result.admitted is False
    assert sd.REASON_SUPPLIER_STOCK_UNKNOWN in result.reason_codes


def test_pregnancy_alone_is_assessment_trigger_not_hard_dependency():
    profile = {
        "total_persons": 2,
        "adult_18_59": 1,
        "pregnant_person": 1,
    }
    required = sd.required_support_links(profile)
    assert "pregnancy_support_link_uncovered" not in required


def test_chronic_condition_without_functional_need_does_not_create_medical_link():
    profile = {
        "total_persons": 2,
        "adult_18_59": 2,
        "chronic_or_acute_illness": 1,
    }
    required = sd.required_support_links(profile)
    assert "medical_support_link_uncovered" not in required


def test_flood_defense_is_conditional_for_high_dry_shelter():
    node = _node("internal_safe", sustain=_sustain())
    node["shelter"] = _shelter_ready()
    node["shelter"]["residual_flood_exposure"] = "NONE"
    node["shelter"].pop("perimeter_flood_defense", None)
    node["shelter"].pop("dewatering_capability", None)
    result = sd.screen_shelter_candidate(node, phase="PRE_OPEN")
    assert result.admitted is True


def test_flood_exposed_shelter_requires_defense_and_dewatering():
    node = _node("internal_safe", sustain=_sustain())
    node["shelter"] = _shelter_ready()
    node["shelter"]["residual_flood_exposure"] = "PRESENT"
    node["shelter"]["perimeter_flood_defense"] = "UNKNOWN"
    node["shelter"]["dewatering_capability"] = "READY"
    result = sd.screen_shelter_candidate(node, phase="PRE_OPEN")
    assert result.admitted is False
    assert "perimeter_flood_defense" in result.details["unknown"]
