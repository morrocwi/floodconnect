import human_animal_household as hahu
import shelter_decision as sd


def _animal_profile(**overrides):
    p = {
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
        "animal_veterinary_support": "NOT_REQUIRED",
        "animal_transport_capacity_verified": True,
        "cats_indoor_or_shelter": True,
        "cat_litter_for_horizon": "SUFFICIENT",
    }
    p.update(overrides)
    return p


def _sustain(**overrides):
    b = {
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
    b.update(overrides)
    return b


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


def _doc(pet_compatible=True):
    nodes = {
        "h": {
            "kind": "household",
            "layer": 0,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 3,
            "occupied_persons": 2,
            "services": [],
            "sustainment": _sustain(),
            "animal_profile": _animal_profile(),
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
            "shelter": _shelter_ready(),
        },
        "e": {
            "kind": "egress",
            "layer": 4,
            "status": "SAFE",
            "fresh": True,
            "capacity_persons": 30,
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
            "occupied_persons": 10,
            "services": ["companion_animal_accommodation"] if pet_compatible else [],
            "shelter": _shelter_ready(),
        },
    }
    if pet_compatible:
        nodes["x"]["animal_accommodation"] = {
            "fresh": True,
            "verified": True,
            "accepted_species": ["cat", "dog"],
            "animal_capacity": 20,
            "animals_present": 2,
            "animal_drinking_water": "SUFFICIENT",
            "animal_food": "SUFFICIENT",
            "animal_waste_management": "SUFFICIENT",
            "animal_containment_area": "SUFFICIENT",
            "separation_from_food_preparation": "SUFFICIENT",
        }

    edges = []
    for eid, u, v in [
        ("hb", "h", "b"),
        ("bz", "b", "z"),
        ("zi", "z", "i"),
        ("ie", "i", "e"),
        ("ex", "e", "x"),
    ]:
        edges.append({
            "id": eid,
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
    return {"nodes": nodes, "edges": edges, "support_edges": []}


def test_animal_unit_food_gap_is_not_sustainable():
    p = _animal_profile(animal_food_for_horizon="INSUFFICIENT")
    r = hahu.evaluate_animal_unit(p, 24)
    assert r.state == hahu.NOT_SUSTAINABLE
    assert "animal_food_for_horizon" in r.gaps


def test_cat_litter_is_conditional_hard_hygiene_need_when_declared_indoor():
    p = _animal_profile(cat_litter_for_horizon="UNKNOWN")
    r = hahu.evaluate_animal_unit(p, 24)
    assert r.state == hahu.UNKNOWN
    assert "cat_litter_for_horizon" in r.unknown_fields


def test_separate_verified_animal_plan_can_decouple_destinations():
    p = _animal_profile(
        plan_mode="SEPARATE_VERIFIED_PLAN",
        separate_plan={
            "verified": True,
            "fresh": True,
            "provider_or_destination": "vet-or-trusted-caregiver",
        },
    )
    r = hahu.evaluate_animal_unit(p, 24)
    assert r.state == hahu.SUSTAINABLE
    assert hahu.animal_route_needs(p) == ()


def test_zero_demand_never_returns_infinite_resource_horizon():
    assert hahu.finite_resource_horizon_h(10, 0, 0) is None


def test_finite_resource_horizon_is_exact():
    h = hahu.finite_resource_horizon_h(14, 0, 2)
    assert h is not None
    assert str(h) == "168"


def test_shelter_requires_declared_species_and_animal_capacity():
    doc = _doc(pet_compatible=True)
    p = doc["nodes"]["h"]["animal_profile"]
    r = hahu.screen_animal_accommodation(doc["nodes"]["x"], p)
    assert r.state == hahu.SUSTAINABLE

    doc["nodes"]["x"]["animal_accommodation"]["animal_capacity"] = 2
    doc["nodes"]["x"]["animal_accommodation"]["animals_present"] = 2
    r2 = hahu.screen_animal_accommodation(doc["nodes"]["x"], p)
    assert r2.state == hahu.NOT_SUSTAINABLE
    assert "animal_capacity" in r2.gaps


def test_human_sustainment_includes_declared_animal_food_gap():
    node = _doc()["nodes"]["h"]
    node["animal_profile"]["animal_food_for_horizon"] = "INSUFFICIENT"
    r = sd.evaluate_sustainment(node, 24)
    assert r.state == sd.NOT_SUSTAINABLE
    assert "animal_food_for_horizon" in r.gaps


def test_physical_unsafe_uses_pet_compatible_destination_when_available():
    doc = _doc(pet_compatible=True)
    doc["nodes"]["h"]["sustainment"]["physical_safety"] = "UNSAFE"
    r = sd.recommend_protective_state(doc, "h", 24)
    assert r.state == "PREPARE_TO_MOVE"
    assert r.details["target"] == "x"
    assert "companion_animal_accommodation" in r.details["animal_route_needs"]


def test_physical_unsafe_without_pet_destination_requests_assisted_evacuation_with_animals():
    doc = _doc(pet_compatible=False)
    doc["nodes"]["h"]["sustainment"]["physical_safety"] = "UNSAFE"
    r = sd.recommend_protective_state(doc, "h", 24)
    assert r.state == "REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS"


def test_physical_unsafe_with_no_verified_animal_transport_does_not_recommend_staying():
    doc = _doc(pet_compatible=True)
    doc["nodes"]["h"]["sustainment"]["physical_safety"] = "UNSAFE"
    doc["nodes"]["h"]["animal_profile"]["animal_transport_capacity_verified"] = False
    r = sd.recommend_protective_state(doc, "h", 24)
    assert r.state == "REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS"


def test_animal_profile_unknown_does_not_become_safe():
    node = _doc()["nodes"]["h"]
    node["animal_profile"]["animal_drinking_water_for_horizon"] = "UNKNOWN"
    r = sd.evaluate_sustainment(node, 24)
    assert r.state == sd.UNKNOWN
    assert "animal_drinking_water_for_horizon" in r.unknown_fields


def test_missing_carrier_does_not_make_safe_home_animal_sustainment_fail():
    p = _animal_profile(
        animal_containment_transport="INSUFFICIENT",
        animal_transport_capacity_verified=False,
    )
    stay = hahu.evaluate_animal_sustainment(p, 24)
    move = hahu.evaluate_animal_movement_readiness(p)
    assert stay.state == hahu.SUSTAINABLE
    assert move.state == hahu.NOT_READY
    assert "animal_containment_transport" in move.gaps


def test_assistance_animal_uses_human_access_not_pet_accommodation():
    p = _animal_profile(
        counts={"dog": 1},
        assistance_animal_count=1,
        assistance_animal_handler_continuity="SUFFICIENT",
    )
    assert hahu.movement_route_service_needs(p) == ("assistance_animal_access",)
    node = {
        "kind": "external_safe",
        "status": "SAFE",
        "fresh": True,
        "capabilities": ["assistance_animal_access"],
    }
    result = hahu.screen_animal_destination(node, p)
    assert result.state == hahu.SUSTAINABLE


def test_livestock_requires_livestock_holding_not_companion_pet_shelter():
    p = _animal_profile(
        total_animals=2,
        counts={"goat_or_sheep": 2},
        cats_indoor_or_shelter=False,
    )
    companion_only = {
        "kind": "external_safe",
        "status": "SAFE",
        "fresh": True,
        "capabilities": ["companion_animal_accommodation"],
        "animal_accommodation": {
            "fresh": True,
            "verified": True,
            "accepted_species": ["goat_or_sheep"],
            "animal_capacity": 10,
            "animals_present": 0,
            "animal_drinking_water": "SUFFICIENT",
            "animal_food": "SUFFICIENT",
            "animal_waste_management": "SUFFICIENT",
            "animal_containment_area": "SUFFICIENT",
            "separation_from_food_preparation": "SUFFICIENT",
        },
    }
    result = hahu.screen_animal_destination(companion_only, p)
    assert result.state == hahu.NOT_SUSTAINABLE
    assert "livestock_holding" in result.gaps


def test_linked_colocated_animal_node_can_make_human_shelter_compatible():
    doc = _doc(pet_compatible=False)
    doc["nodes"]["x"]["linked_animal_node"] = "pets"
    doc["nodes"]["pets"] = {
        "kind": "service_node",
        "layer": 5,
        "status": "SAFE",
        "fresh": True,
        "capabilities": ["companion_animal_accommodation"],
        "animal_accommodation": {
            "fresh": True,
            "verified": True,
            "accepted_species": ["cat"],
            "animal_capacity": 20,
            "animals_present": 0,
            "animal_drinking_water": "SUFFICIENT",
            "animal_food": "SUFFICIENT",
            "animal_waste_management": "SUFFICIENT",
            "animal_containment_area": "SUFFICIENT",
            "separation_from_food_preparation": "SUFFICIENT",
        },
    }
    p = doc["nodes"]["h"]["animal_profile"]
    result = hahu.screen_animal_destination(doc["nodes"]["x"], p, doc=doc)
    assert result.state == hahu.SUSTAINABLE


def test_lvcn_skips_human_only_shelter_for_coevacuating_cat():
    doc = _doc(pet_compatible=True)
    doc["nodes"]["h"]["support_candidates"] = ["i", "x"]
    # Internal shelter is safe for people but has no animal compatibility.
    result = sd.find_lowest_viable_node(doc, "h", 24)
    assert result.node_id == "x"
    assert result.node_kind == "external_safe"


def test_unknown_evacuation_plan_does_not_poison_safe_home_sustainment():
    p = _animal_profile(plan_mode="UNKNOWN")
    stay = hahu.evaluate_animal_sustainment(p, 24)
    move = hahu.evaluate_animal_movement_readiness(p)
    assert stay.state == hahu.SUSTAINABLE
    assert move.state == hahu.UNKNOWN


def test_missing_identification_record_is_advisory_not_universal_movement_blocker():
    p = _animal_profile(animal_identification_records="UNKNOWN")
    move = hahu.evaluate_animal_movement_readiness(p)
    assert move.state == hahu.READY
    assert "animal_identification_records" in move.details["advisory_unknowns"]
