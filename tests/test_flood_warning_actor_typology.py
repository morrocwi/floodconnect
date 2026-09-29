from pathlib import Path

import yaml


PATH = Path("site/inputs/governance/flood_warning_actor_typology.yaml")


def load():
    with PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_core_thai_warning_roles_exist():
    doc = load()
    roles = doc["roles"]
    for role in (
        "METEOROLOGICAL_OBSERVER_FORECASTER",
        "IRRIGATION_WATER_SYSTEM_OPERATOR",
        "FLASH_FLOOD_WATERSHED_EWS",
        "NATIONAL_WATER_INTEGRATOR",
        "NATIONAL_PUBLIC_WARNING_DISSEMINATOR",
        "LOCAL_LAST_MILE_WARNING_RESPONSE",
    ):
        assert role in roles


def test_core_agencies_map_to_distinct_roles():
    actors = load()["actors"]
    assert "METEOROLOGICAL_OBSERVER_FORECASTER" in actors["thai_meteorological_department"]["roles"]
    assert "IRRIGATION_WATER_SYSTEM_OPERATOR" in actors["royal_irrigation_department"]["roles"]
    assert "FLASH_FLOOD_WATERSHED_EWS" in actors["department_of_water_resources"]["roles"]
    assert "NATIONAL_WATER_INTEGRATOR" in actors["office_of_national_water_resources"]["roles"]
    assert "NATIONAL_PUBLIC_WARNING_DISSEMINATOR" in actors["ddpm_national_disaster_warning_center"]["roles"]
    assert "LOCAL_LAST_MILE_WARNING_RESPONSE" in actors["province_district_local_authority"]["roles"]


def test_bangkok_and_hii_extensions_are_not_miscast():
    actors = load()["actors"]
    assert "URBAN_DRAINAGE_OPERATOR" in actors["bma_drainage_and_sewerage"]["roles"]
    assert "HYDRO_DATA_BROKER_AGGREGATOR" in actors["hydro_informatics_institute"]["roles"]
    assert "NATIONAL_PUBLIC_WARNING_DISSEMINATOR" not in actors["hydro_informatics_institute"]["roles"]


def test_product_semantics_keep_observation_and_instruction_separate():
    semantics = load()["product_semantics"]
    assert semantics["observation"]["action_authority"] is False
    assert semantics["forecast"]["action_authority"] is False
    assert semantics["operational_instruction"]["action_authority"] is True
    assert semantics["response_action"]["action_authority"] is True


def test_typology_forbids_weather_to_exact_flood_depth_laundering():
    role = load()["roles"]["METEOROLOGICAL_OBSERVER_FORECASTER"]
    assert "exact_local_flood_depth" in role["must_not_infer"]
