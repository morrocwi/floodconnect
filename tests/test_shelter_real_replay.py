"""Real-evidence mechanism replays for Thai shelter/community sustainment.

These tests do not simulate flood depth, travel time, stock quantity or saved outcomes.
They encode only qualitative failure mechanisms documented in the project's 28 Sep 2026
field-evidence ledger and the Yodsuban & Nuntaboot (2021) Thai community study.

A passing test means the decision logic represents the observed mechanism coherently.
It is NOT a claim that FloodConnect would have changed the historical outcome.
"""
import shelter_decision as sd


def _base_sustain(**overrides):
    x = {
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
    x.update(overrides)
    return x


def _ready_shelter():
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


def test_real_mechanism_khlong_chan_electricity_does_not_cancel_service_water_failure():
    """Field case: occupied residential blocks reportedly had electricity but lacked usable water."""
    node = {
        "kind": "internal_safe",
        "status": "SAFE",
        "fresh": True,
        "capacity_persons": 100,
        "occupied_persons": 10,
        "services": [],
        "shelter": _ready_shelter(),
    }
    node["shelter"]["critical_power"] = "SUFFICIENT"
    node["shelter"]["service_water"] = "INSUFFICIENT"
    result = sd.screen_shelter_candidate(node, phase="OCCUPIED")
    assert result.admitted is False
    assert "service_water" in result.details["failed"]


def test_real_mechanism_low_flood_exposed_community_building_not_safe_by_label():
    """Field case: a mosque/community site was reported lower than a receiving canal and inundated."""
    node = {
        "kind": "internal_safe",
        "status": "UNKNOWN",
        "fresh": True,
        "capacity_persons": 100,
        "occupied_persons": 0,
        "services": [],
        "shelter": _ready_shelter(),
    }
    node["shelter"]["site_hazard_safety"] = "UNSAFE"
    result = sd.screen_shelter_candidate(node, phase="PRE_OPEN")
    assert result.admitted is False
    assert sd.REASON_SHELTER_UNSAFE in result.reason_codes


def test_real_mechanism_dry_kitchen_can_move_food_inward_without_becoming_shelter():
    """Field case: dry-area private/community kitchen cooked food and delivered into flooded areas."""
    doc = {
        "nodes": {
            "home": {
                "kind": "household",
                "layer": 0,
                "status": "SAFE",
                "fresh": True,
                "capacity_persons": 3,
                "occupied_persons": 3,
                "services": [],
                "support_candidates": ["home"],
                "sustainment": _base_sustain(
                    food_for_horizon="INSUFFICIENT",
                    support_providers=["kitchen"],
                ),
            },
            "kitchen": {
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
            },
        },
        "edges": [],
        "support_edges": [{
            "id": "meal_delivery",
            "from": "kitchen",
            "to": "home",
            "status": "OPEN",
            "fresh": True,
            "field_verified": True,
            "capacity_status": "SUFFICIENT",
            "arrival_before_failure": True,
            "resources": ["food_for_horizon"],
        }],
    }
    delivery = sd.evaluate_support_delivery(doc, "home", "kitchen", ["food_for_horizon"], 24)
    assert delivery.admitted is True

    # Service node identity must not be laundered into a shelter declaration.
    screened = sd.screen_shelter_candidate(doc["nodes"]["kitchen"], phase="OCCUPIED")
    assert screened.admitted is False
    assert sd.REASON_INVALID_NODE_KIND in screened.reason_codes

    action = sd.recommend_protective_state(doc, "home", 24)
    assert action.state == "REQUEST_OR_RECEIVE_SUPPORT_DELIVERY"


def test_real_mechanism_older_person_alone_requires_relationship_check_not_age_score():
    """Thai community research supports mapping older households + functional assistance needs."""
    profile = {
        "total_persons": 1,
        "living_arrangement": "ALONE",
        "older_adult_60_plus": 1,
        "needs_essential_medication": 1,
        "medical_support_link_uncovered": 0,
        "older_adult_support_link_uncovered": 0,
        "living_alone_buddy_link_uncovered": "UNKNOWN",
    }
    result = sd.evaluate_dependency_coverage(profile)
    assert result.admitted is False
    assert result.state == "DEPENDENCY_COVERAGE_UNKNOWN"
    assert "living_alone_buddy_link_uncovered" in result.details["unknown_links"]


def test_real_mechanism_child_with_older_only_is_assessment_tag_not_automatic_failure():
    profile = {
        "total_persons": 2,
        "living_arrangement": "PAIR",
        "child_6_12": 1,
        "older_adult_60_plus": 1,
        "adult_18_59": 0,
        "child_caregiver_link_uncovered": 0,
    }
    config = sd.classify_group_configuration(profile)
    assert config.admitted is True
    assert "CHILD_WITH_OLDER_ONLY" in config.details["composition_tags"]

    coverage = sd.evaluate_dependency_coverage(profile)
    assert coverage.admitted is True
