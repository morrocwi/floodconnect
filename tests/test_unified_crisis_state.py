import unified_crisis_state as ucs


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
        "resupply": {"supplier_node": None, "route_edges": [], "official_movement_conflict": False},
    }
    block.update(overrides)
    return block


def _base_doc():
    nodes = {
        "h": {
            "kind": "household",
            "layer": 0,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 2,
            "occupied_persons": 2,
            "services": [],
            "support_candidates": ["h", "b", "z", "i", "x"],
            "sustainment": _sustain(),
            "crisis_phase": "RESPONSE",
        },
        "b": {
            "kind": "buddy_cell",
            "layer": 1,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 10,
            "occupied_persons": 2,
            "services": [],
        },
        "z": {
            "kind": "zone",
            "layer": 2,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 20,
            "occupied_persons": 2,
            "services": [],
        },
        "i": {
            "kind": "internal_safe",
            "layer": 3,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 20,
            "occupied_persons": 2,
            "services": [],
            "shelter": {
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
                "exit_closure_plan": "READY",
            },
        },
        "e": {
            "kind": "egress",
            "layer": 4,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 50,
            "occupied_persons": 0,
            "services": [],
        },
        "x": {
            "kind": "external_safe",
            "layer": 5,
            "status": "SAFE",
            "fresh": True,
            "verified_safe": True,
            "capacity_persons": 100,
            "occupied_persons": 5,
            "services": [],
            "shelter": {
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
                "exit_closure_plan": "READY",
            },
        },
    }
    edges = []
    for eid, a, b in [
        ("hb", "h", "b"),
        ("bz", "b", "z"),
        ("zi", "z", "i"),
        ("ie", "i", "e"),
        ("ex", "e", "x"),
    ]:
        edges.append({
            "id": eid,
            "from": a,
            "to": b,
            "status": "OPEN",
            "safety": "CLEAR",
            "fresh": True,
            "field_verified": True,
            "modes": ["walk"],
            "max_group": 10,
            "distance_m": 10,
        })
    return {"nodes": nodes, "edges": edges, "support_edges": []}


def test_unified_state_human_only_safe_household():
    doc = _base_doc()
    state = ucs.derive_crisis_state(doc, "h", 24)
    assert state.occupancy == "SAFE"
    assert state.function == "INTACT"
    assert state.movement == "SELF_MOVE"
    assert state.support == "L0_HOUSEHOLD"
    assert state.animal_topology == "HUMAN_ONLY"
    assert state.phase == "RESPONSE"
    assert state.action_pattern == "STAY_SUSTAIN"


def test_unified_state_resource_gap_with_verified_delivery_is_closable():
    doc = _base_doc()
    doc["nodes"]["h"]["sustainment"]["food_for_horizon"] = "INSUFFICIENT"
    doc["nodes"]["h"]["sustainment"]["support_providers"] = ["kitchen"]
    doc["nodes"]["kitchen"] = {
        "kind": "service_node",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "verified_service": True,
        "capabilities": ["food_for_horizon", "food_preparation"],
        "support": {
            "fresh": True,
            "assessed_horizon_h": 72,
            "resources": {"food_for_horizon": "SUFFICIENT"},
        },
    }
    doc["support_edges"] = [{
        "id": "kitchen_h",
        "from": "kitchen",
        "to": "h",
        "status": "OPEN",
        "fresh": True,
        "field_verified": True,
        "capacity_status": "SUFFICIENT",
        "arrival_before_failure": True,
        "resources": ["food_for_horizon"],
    }]
    state = ucs.derive_crisis_state(doc, "h", 24)
    assert state.function == "GAP_CLOSABLE"
    assert state.action_pattern == "DELIVER_INWARD"


def test_forward_hazard_changes_pattern_without_overwriting_current_occupancy():
    doc = _base_doc()
    state = ucs.derive_crisis_state(
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
    assert state.occupancy == "SAFE"
    assert state.forward_hazard == "HIGH"
    assert state.action_pattern == "STAY_PREPARE_WINDOW_CLOSING"


def test_animal_topology_is_modifier_not_new_crisis_type():
    doc = _base_doc()
    doc["nodes"]["h"]["animal_profile"] = {
        "total_animals": 1,
        "counts": {"cat": 1},
        "plan_mode": "CO_RESIDENT_CO_EVACUATING",
        "assessed_horizon_h": 72,
        "animal_food_for_horizon": "SUFFICIENT",
        "animal_drinking_water_for_horizon": "SUFFICIENT",
        "animal_medication_for_horizon": "NOT_REQUIRED",
        "animal_waste_hygiene_for_horizon": "SUFFICIENT",
        "animal_containment_transport": "SUFFICIENT",
        "animal_identification_records": "SUFFICIENT",
        "animal_transport_capacity_verified": True,
        "cats_indoor_or_shelter": True,
        "cat_litter_for_horizon": "SUFFICIENT",
    }
    doc["nodes"]["x"]["capabilities"] = ["companion_animal_accommodation"]
    doc["nodes"]["x"]["animal_accommodation"] = {
        "fresh": True,
        "verified": True,
        "accepted_species": ["cat"],
        "animal_capacity": 10,
        "animals_present": 0,
        "animal_drinking_water": "SUFFICIENT",
        "animal_food": "SUFFICIENT",
        "animal_waste_management": "SUFFICIENT",
        "animal_containment_area": "SUFFICIENT",
        "separation_from_food_preparation": "SUFFICIENT",
    }
    state = ucs.derive_crisis_state(doc, "h", 24)
    assert state.animal_topology == "COMPANION"
    assert state.action_pattern == "STAY_SUSTAIN"


def test_shelter_lifecycle_patterns_are_executable():
    doc = _base_doc()
    shelter = doc["nodes"]["i"]
    occupied = ucs.derive_shelter_response_pattern(shelter, phase="OCCUPIED")
    assert occupied["pattern"] == "SHELTER_OPERATION"

    shelter["shelter"]["service_water"] = "INSUFFICIENT"
    degraded = ucs.derive_shelter_response_pattern(shelter, phase="OCCUPIED")
    assert degraded["pattern"] == "SHELTER_INTERVENTION_RELOCATION"


def test_recovery_pattern_requires_recovery_constraints():
    doc = _base_doc()
    shelter = doc["nodes"]["i"]
    shelter["shelter"]["post_flood_cleaning"] = "READY"
    recovery = ucs.derive_shelter_response_pattern(shelter, phase="RECOVERY")
    assert recovery["pattern"] == "RECOVERY_RETURN"
