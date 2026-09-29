import json
from pathlib import Path

import yaml


TYPOLOGY = Path("site/inputs/governance/flood_warning_actor_typology.yaml")
GOVERNANCE = Path("site/inputs/governance/thailand_water_governance_reference.json")


def load_typology():
    with TYPOLOGY.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_governance():
    with GOVERNANCE.open(encoding="utf-8") as f:
        return json.load(f)


def governance_ids():
    return {x["id"] for x in load_governance()["verified_anchors"]}


def test_core_thai_warning_roles_exist():
    roles = load_typology()["roles"]
    for role in (
        "METEOROLOGICAL_OBSERVER_FORECASTER",
        "IRRIGATION_WATER_SYSTEM_OPERATOR",
        "FLASH_FLOOD_WATERSHED_EWS",
        "NATIONAL_WATER_INTEGRATOR",
        "NATIONAL_PUBLIC_WARNING_DISSEMINATOR",
        "LOCAL_LAST_MILE_WARNING_RESPONSE",
    ):
        assert role in roles


def test_typology_reuses_canonical_governance_actor_nodes():
    refs = load_typology()["canonical_actor_registry"]["actor_refs"]
    ids = governance_ids()
    for actor_ref in refs:
        assert actor_ref in ids


def test_roles_point_to_canonical_actor_refs_not_duplicate_actor_objects():
    doc = load_typology()
    assert "actors" not in doc
    roles = doc["roles"]
    assert roles["METEOROLOGICAL_OBSERVER_FORECASTER"]["primary_actor_ref"] == "tmd"
    assert roles["IRRIGATION_WATER_SYSTEM_OPERATOR"]["primary_actor_ref"] == "rid"
    assert roles["FLASH_FLOOD_WATERSHED_EWS"]["primary_actor_ref"] == "dwr"
    assert roles["NATIONAL_WATER_INTEGRATOR"]["primary_actor_ref"] == "onwr"
    assert roles["NATIONAL_PUBLIC_WARNING_DISSEMINATOR"]["primary_actor_ref"] == "ddpm_ndwc"


def test_bangkok_and_hii_extensions_are_existing_governance_nodes():
    refs = load_typology()["canonical_actor_registry"]["actor_refs"]
    assert "URBAN_DRAINAGE_OPERATOR" in refs["bma_dds"]["warning_roles"]
    assert "HYDRO_DATA_BROKER_AGGREGATOR" in refs["hii"]["warning_roles"]


def test_product_semantics_keep_observation_and_instruction_separate():
    semantics = load_typology()["product_semantics"]
    assert semantics["observation"]["action_authority"] is False
    assert semantics["forecast"]["action_authority"] is False
    assert semantics["operational_instruction"]["action_authority"] is True
    assert semantics["response_action"]["action_authority"] is True


def test_typology_forbids_weather_to_exact_flood_depth_laundering():
    role = load_typology()["roles"]["METEOROLOGICAL_OBSERVER_FORECASTER"]
    assert "exact_local_flood_depth" in role["must_not_infer"]
