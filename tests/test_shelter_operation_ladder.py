import shelter_operation_ladder as so


def base_node(**overrides):
    node = {
        "dry_operating_surface": True,
        "dry_status_verified": True,
        "dry_status_fresh": True,
        "immediate_site_hazard_safe": True,
        "drainage_not_blocking_operation": True,

        "provider_access_verified": True,
        "community_distribution_access_verified": True,
        "communications_available": True,
        "basic_first_aid_access": True,

        "safe_loading_unloading": True,
        "goods_staging_area": True,
        "people_vehicle_separation": True,
        "basic_lighting_or_daylight": True,
        "drinking_water_for_workers": True,
        "waste_handling": True,

        "capacity_declared": True,
        "potable_water": True,
        "toilets_and_hand_hygiene": True,
        "weather_protection": True,
        "accessible_waiting_area": True,
        "food_distribution_safe": True,
        "health_referral_access": True,
        "vulnerable_support": True,

        "sleeping_space": True,
        "bedding_or_sleeping_surfaces": True,
        "privacy_and_dignity": True,
        "bathing_or_washing": True,
        "safe_food_preparation_or_provision": True,
        "night_lighting": True,
        "structural_and_fire_safety": True,
        "medicine_health_support": True,
        "critical_power_if_required": True,
        "resident_accountability": True,
        "protection_arrangements": True,

        "service_water": True,
        "sanitation_wastewater": True,
        "solid_waste_management": True,
        "resupply_continuity": True,
        "maintenance_staffing_or_mechanism": True,
        "feedback_complaints": True,
        "child_safeguarding": True,
        "gbv_protection": True,
        "family_unity": True,
        "psychosocial_referral": True,
        "animal_plan_if_present": True,
        "contingency_relocation_plan": True,
        "return_or_closure_plan": True,
        "reassessment_cycle": True,
    }
    node.update(overrides)
    return node


def test_wet_operating_surface_blocks_every_level():
    result = so.evaluate_shelter_operation(base_node(dry_operating_surface=False))
    assert result.state == so.NO_SHELTER_OPERATION
    assert result.level is None
    assert "dry_operating_surface" in result.failed_fields


def test_unknown_dry_status_never_promotes_to_l0():
    result = so.evaluate_shelter_operation(base_node(dry_status_verified=None))
    assert result.state == so.UNKNOWN
    assert result.level is None
    assert result.next_level == so.LEVEL_0


def test_l0_is_minimum_dry_interface():
    node = base_node()
    node["safe_loading_unloading"] = None
    result = so.evaluate_shelter_operation(node)
    assert result.state == "LEVEL_CONFIRMED"
    assert result.level == so.LEVEL_0
    assert result.next_level == so.LEVEL_1


def test_day_support_requires_wash_and_waiting_capability():
    node = base_node(toilets_and_hand_hygiene=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_1
    assert result.next_level == so.LEVEL_2
    assert "toilets_and_hand_hygiene" in result.failed_fields


def test_overnight_requires_sleeping_privacy_fire_and_health():
    node = base_node(structural_and_fire_safety=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_2
    assert result.next_level == so.LEVEL_3


def test_full_operation_is_cumulative_not_weighted():
    node = base_node(return_or_closure_plan=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_3
    assert result.next_level == so.LEVEL_4
    assert "return_or_closure_plan" in result.failed_fields


def test_full_operation_when_all_hard_requirements_pass():
    result = so.evaluate_shelter_operation(base_node())
    assert result.state == "LEVEL_CONFIRMED"
    assert result.level == so.LEVEL_4
    assert result.next_level is None
