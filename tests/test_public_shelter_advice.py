"""Tests for `advice.public_shelter` -- P-C."""
from __future__ import annotations

import shelter_operation_ladder as so
import advice.public_shelter as ps


def _l0_site(site_id, archetype="public_school", **overrides):
    site = {
        "site_id": site_id,
        "archetype": archetype,
        "distance_to_affected_m": 500,
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


def test_no_sites_declared_gives_open():
    out = ps.surface_public_shelters()
    assert out["state"] == ps.STATE_OPEN
    assert out["note"]


def test_empty_site_list_gives_open():
    out = ps.surface_public_shelters([])
    assert out["state"] == ps.STATE_OPEN


def test_sites_with_no_admitted_candidate_gives_open():
    # dry_operating_surface False -> no candidate can ever be admitted.
    out = ps.surface_public_shelters([_l0_site("school_a", dry_operating_surface=False)],
                                      target_level=so.LEVEL_0)
    assert out["state"] == ps.STATE_OPEN


def test_admitted_candidate_gives_candidates():
    out = ps.surface_public_shelters([_l0_site("school_a")], target_level=so.LEVEL_0)
    assert out["state"] == ps.STATE_CANDIDATES
    assert "school_a" in out["note"]


def test_real_strategy_file_has_zero_real_sites():
    """VERIFIED (P-C design reuse inventory): `public_shelter_seeds.yaml` holds
    archetypes only and zero real sites -- a default call over the real repo data
    must therefore still be OPEN, never a fabricated candidate."""
    strategy = ps.pss.load_strategy()
    assert "sites" not in strategy or not strategy.get("sites")
    out = ps.surface_public_shelters(strategy.get("sites"), strategy=strategy)
    assert out["state"] == ps.STATE_OPEN
