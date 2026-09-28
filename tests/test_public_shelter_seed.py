import public_shelter_seed as pss
import shelter_operation_ladder as so


def l0_site(site_id, archetype, distance=500, **overrides):
    site = {
        "site_id": site_id,
        "archetype": archetype,
        "distance_to_affected_m": distance,
        "dry_operating_surface": True,
        "dry_status_verified": True,
        "dry_status_fresh": True,
        "immediate_site_hazard_safe": True,
        "drainage_not_blocking_operation": True,
        "provider_access_verified": True,
        "community_distribution_access_verified": True,
        "communications_available": True,
        "basic_first_aid_access": True,
    }
    site.update(overrides)
    return site


def fill_through(site, level):
    site = dict(site)
    for current in so.LEVELS:
        for field in so.LEVEL_REQUIREMENTS[current]:
            site.setdefault(field, True)
        if current == level:
            break
    return site


def test_public_school_can_be_admitted_only_after_real_dry_l0():
    result = pss.evaluate_seed_candidate(l0_site("school_a", "public_school"))
    assert result.admitted is True
    assert result.shelter_level == so.LEVEL_0
    assert result.role == "shelter_seed"


def test_school_label_never_overrides_wet_site():
    site = l0_site("school_wet", "public_school", dry_operating_surface=False)
    result = pss.evaluate_seed_candidate(site)
    assert result.admitted is False
    assert "DRY_GATE_OR_SO_L0_NOT_CONFIRMED" in result.reason_codes


def test_hospital_is_health_referral_not_general_shelter_by_default():
    site = fill_through(l0_site("hospital_a", "hospital"), so.LEVEL_4)
    result = pss.evaluate_seed_candidate(site)
    assert result.admitted is False
    assert result.role == "critical_health_referral_node"
    assert "SUPPORT_NODE_NOT_GENERAL_SHELTER" in result.reason_codes


def test_officially_designated_hospital_may_enter_general_shelter_evaluation():
    site = fill_through(
        l0_site(
            "hospital_designated",
            "hospital",
            officially_designated_general_shelter=True,
        ),
        so.LEVEL_3,
    )
    result = pss.evaluate_seed_candidate(site, target_level=so.LEVEL_3)
    assert result.admitted is True
    assert result.shelter_level in {so.LEVEL_3, so.LEVEL_4}


def test_actual_capability_gap_beats_archetype_discovery_order():
    school = fill_through(l0_site("school", "public_school", distance=200), so.LEVEL_1)
    sports = fill_through(l0_site("sports", "public_sports_youth_center", distance=400), so.LEVEL_2)

    # Make both stop at their current levels by leaving later requirements unknown.
    winner = pss.select_fastest_upgrade_seed(
        [school, sports],
        target_level=so.LEVEL_3,
    )
    assert winner is not None
    assert winner.site_id == "sports"


def test_distance_breaks_tie_only_after_hard_capability_gap():
    a = fill_through(l0_site("a", "public_school", distance=900), so.LEVEL_2)
    b = fill_through(l0_site("b", "public_sports_youth_center", distance=300), so.LEVEL_2)
    winner = pss.select_fastest_upgrade_seed([a, b], target_level=so.LEVEL_3)
    assert winner is not None
    assert winner.site_id == "b"


def test_primary_health_center_remains_support_node_by_default():
    site = fill_through(l0_site("phc", "primary_health_center"), so.LEVEL_2)
    result = pss.evaluate_seed_candidate(site)
    assert result.admitted is False
    assert result.role == "health_support_node"
