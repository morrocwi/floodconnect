from pathlib import Path

import yaml


REGISTRY = Path("site/inputs/community/operational_tools.yaml")


def load():
    with REGISTRY.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_tool_node_is_separate_operational_resource_graph():
    doc = load()
    schema = doc["tool_node_schema"]
    assert schema["kind"] == "tool_node"
    assert schema["graph"] == "operational_resource_graph"
    assert schema["spatial_layer"] is None
    assert "node" in schema["may_attach_to"]
    assert "edge" in schema["may_attach_to"]


def test_field_vehicle_types_are_registered():
    tools = load()["tools"]
    for tool_id in (
        "high_clearance_response_vehicle",
        "heavy_cargo_truck",
        "pickup_4x4",
        "atv_utv",
        "powered_rescue_boat",
        "inflatable_rescue_boat",
        "evacuation_transport_truck",
    ):
        assert tool_id in tools


def test_vehicle_type_does_not_claim_flood_route_safety():
    tools = load()["tools"]
    assert tools["standard_passenger_car"]["floodwater_entry"] == "PROHIBITED_BY_DEFAULT"
    assert tools["pickup_4x4"]["floodwater_entry"] == "NOT_INFERRED_FROM_4X4"
    assert "ONLY_WITH_SPECIALIZED_TEAM" in tools["high_clearance_response_vehicle"]["floodwater_entry"]


def test_mobile_service_vehicles_connect_to_shelter_capabilities():
    tools = load()["tools"]
    assert "potable_water" in tools["mobile_drinking_water_truck"]["node_effect"]
    assert "safe_food_preparation_or_provision" in tools["mobile_cooking_truck"]["node_effect"]
    assert "night_lighting" in tools["mobile_power_lighting_truck"]["node_effect"]


def test_pump_cannot_self_certify_dry_gate():
    tools = load()["tools"]
    note = tools["portable_pump_dewatering"]["note"]
    assert "does not make a wet operating footprint pass the Dry Gate" in note


def test_capability_cascade_keeps_hard_boundaries():
    doc = load()
    boundaries = doc["capability_cascade"]["hard_boundaries"]
    assert "tool capability never overrides Dry Gate" in boundaries
    assert "vehicle/watercraft type never overrides route safety" in boundaries
