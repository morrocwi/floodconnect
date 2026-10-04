"""tests/test_export_api.py -- Component A generator tests.

Runs tools/api/export_api.py against small synthetic fixtures (never real/live
data) and checks the acceptance shape from the FloodConnect API v1 spec:
dual-state presence, staleness tags, no secret-shaped strings, contradictions
round-trip both-sides, and freshness reuse (not reinvention).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

import sys
sys.path.insert(0, str(ROOT))
from tools.api import export_api  # noqa: E402


@pytest.fixture()
def exported(tmp_path):
    out_dir = tmp_path / "api" / "v1"
    result = export_api.export_api(
        data_json_path=str(FIXTURES / "data_json_sample.json"),
        typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
        typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
        self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
        sources_registry_path=str(FIXTURES / "sources_registry_sample.yaml"),
        out_dir=str(out_dir),
    )
    return out_dir, result


EXPECTED_FILES = [
    "index.json",
    "areas/sammakorn.json",
    "areas/ram53.json",
    "typology/graph.json",
    "typology/subgraph/sammakorn.json",
    "community/self_help_dag.json",
    "sources.json",
    "schema/index.schema.json",
    "schema/area.schema.json",
    "schema/typology_graph.schema.json",
    "schema/self_help_dag.schema.json",
    "schema/sources.schema.json",
    "openapi.yaml",
]


def test_all_listed_files_written(exported):
    out_dir, result = exported
    for rel in EXPECTED_FILES:
        assert (out_dir / rel).exists(), f"missing {rel}"
    assert result.endpoint_count == len(result.files_written)


def test_index_areas_match_fixture(exported):
    out_dir, _ = exported
    index = json.loads((out_dir / "index.json").read_text())
    assert sorted(index["areas"]) == ["ram53", "sammakorn"]
    assert index["api_version"] == "1.0.0"


def test_dual_state_present_and_distinct(exported):
    out_dir, _ = exported
    for area_id in ("sammakorn", "ram53"):
        area = json.loads((out_dir / f"areas/{area_id}.json").read_text())
        assert "current_local_state" in area
        assert "forward_hazard" in area
        assert area["current_local_state"] != area["forward_hazard"]
        assert set(area["current_local_state"].keys()) != set(area["forward_hazard"].keys())


ALLOWED_TAGS = {"VERIFIED", "MEASURED", "MEASURED-community", "MEASURED-history",
                "RELAYED", "INSTINCT", "OPEN", "PROPOSAL-derived"}
ALLOWED_AGE_CLASSES = {"fresh", "stale", "expired"}


def test_canal_and_water_balance_staleness_tags(exported):
    out_dir, _ = exported
    area = json.loads((out_dir / "areas/sammakorn.json").read_text())
    canals = area["current_local_state"]["canals"]
    assert canals, "fixture has canal stations"
    for c in canals:
        st = c["staleness"]
        assert st["tag"] in ALLOWED_TAGS
        assert st["age_class"] in ALLOWED_AGE_CLASSES
    wb_st = area["current_local_state"]["water_balance"]["staleness"]
    assert wb_st["tag"] in ALLOWED_TAGS
    assert wb_st["age_class"] in ALLOWED_AGE_CLASSES


def test_fresh_station_is_fresh_and_stale_one_is_not(exported):
    """Reproduces the incident this spec exists for: WL.SSB.08 was observed
    5 minutes before generation -> fresh, VALUE present, never UNKNOWN.
    WL.BMA.02 in this fixture is ~29h old -> stale, not conflated with fresh."""
    out_dir, _ = exported
    area = json.loads((out_dir / "areas/sammakorn.json").read_text())
    by_code = {c["station_code"]: c for c in area["current_local_state"]["canals"]}
    fresh = by_code["WL.SSB.08"]
    assert fresh["level_m"] == 0.42
    assert fresh["staleness"]["age_class"] == "fresh"
    stale = by_code["WL.BMA.02"]
    assert stale["staleness"]["age_class"] == "stale"


SECRET_PATTERNS = [re.compile(p) for p in (r"sk-[A-Za-z0-9]{8,}", r"Bearer\s+\S+", r"://[^/\s]+:[^/\s@]+@")]


def test_no_secret_shaped_strings_in_sources(exported):
    out_dir, _ = exported
    sources = json.loads((out_dir / "sources.json").read_text())
    blob = json.dumps(sources)
    for pat in SECRET_PATTERNS:
        assert not pat.search(blob), f"secret-shaped string matched {pat.pattern}"
    for s in sources["sources"]:
        assert s["auth"] in {"none", "key"}


def test_contradictions_round_trip_both_sides_never_merged(exported):
    out_dir, _ = exported
    area = json.loads((out_dir / "areas/sammakorn.json").read_text())
    contradictions = area["contradictions"]
    assert len(contradictions) == 1
    row = contradictions[0]
    assert row["source_a"] == "thaiwater_canal_waterlevel"
    assert row["source_b"] == "bma_watermap"
    assert row["value_a"] == 0.42
    assert row["value_b"] == 0.71
    assert row["merged"] is False
    # no single "resolved" value anywhere else in the area payload
    assert "resolved_value" not in json.dumps(area)


def test_self_help_dag_schema_status_not_upgraded(exported):
    out_dir, _ = exported
    dag = json.loads((out_dir / "community/self_help_dag.json").read_text())
    assert dag["schema_status"] == "proposal_operational_schema"


def test_freshness_reuse_no_local_cutoff_constant():
    """export_api.py must import age_class from site/build_data.py rather
    than defining its own numeric time-cutoff constant."""
    src = (ROOT / "tools" / "api" / "export_api.py").read_text()
    assert "age_class" in src and "_load_build_data_module" in src
    tree = ast.parse(src)
    bare_hour_like_floats = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Constant,)):
            if isinstance(node.value.value, (int, float)) and not isinstance(node.value.value, bool):
                for t in node.targets:
                    name = getattr(t, "id", "").upper()
                    if "HOUR" in name or "STALE" in name or "CUTOFF" in name or "AGE" in name:
                        bare_hour_like_floats.append(name)
    assert not bare_hour_like_floats, f"found local freshness-cutoff constants: {bare_hour_like_floats}"


def test_build_data_module_actually_called(monkeypatch, tmp_path):
    """Spy on the real age_class function (imported from build_data.py, not
    reimplemented) and assert export_api calls it at least once."""
    mod = export_api._load_build_data_module()
    calls = []
    orig = mod.age_class

    def spy(*a, **kw):
        calls.append((a, kw))
        return orig(*a, **kw)

    monkeypatch.setattr(mod, "age_class", spy)
    monkeypatch.setattr(export_api, "_load_build_data_module", lambda: mod)
    export_api.export_api(
        data_json_path=str(FIXTURES / "data_json_sample.json"),
        typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
        typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
        self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
        sources_registry_path=str(FIXTURES / "sources_registry_sample.yaml"),
        out_dir=str(tmp_path / "out"),
    )
    assert len(calls) > 0


def test_secret_shaped_auth_aborts_build(tmp_path):
    bad_registry = tmp_path / "registry.yaml"
    bad_registry.write_text(
        "sources:\n"
        "  - id: leaky\n"
        "    agency: {th: x, en: x}\n"
        "    url: https://example.invalid\n"
        "    method: GET\n"
        "    auth: 'Bearer sk-abcdefgh12345678'\n"
        "    trust_tier: third_party\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        export_api.export_api(
            data_json_path=str(FIXTURES / "data_json_sample.json"),
            typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
            typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
            self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
            sources_registry_path=str(bad_registry),
            out_dir=str(tmp_path / "out2"),
        )


# ---------------------------------------------------------------------------
# Stale forward_hazard field drop (2026-10-04): a forecast already stale AT BUILD
# TIME (its own `fetched_at` far from `generated_at_utc`) must never be baked
# into the exported JSON with its forward-looking figures intact -- see
# `tools/mcp/floodconnect_mcp.py::_recompute_area_freshness`'s own FIX B
# comment for the sibling guard at MCP-call time (this one guards the build).
# ---------------------------------------------------------------------------

def _data_with_stale_forecast(tmp_path) -> str:
    raw = json.loads((FIXTURES / "data_json_sample.json").read_text(encoding="utf-8"))
    generated_at = raw["generated_at_utc"]
    stale_fetched_at = "2020-01-01T00:00:00+00:00"  # far older than any STALE_HOURS cutoff
    forecast = {
        "available": True, "status": "ok",
        "items": [{"h": "19:00", "mm": 1.0}],
        "hourly": [{"h": "19:00", "mm": 1.0, "prob": 59}],
        "hourly_full": [{"time_local": "2020-01-01T19:00", "mm": 1.0}],
        "direction": "falling", "trend_word": "ฝนกำลังจะเบาลงหลัง 22:00 น.",
        "next6h_mm": 1.3, "next24h_mm": 7.8, "h24_48_mm": 4.3, "h48_72_mm": 5.5,
        "first_dry_6h_start": "22:00",
        "fetched_at": stale_fetched_at,
    }
    raw["areas"]["sammakorn"]["forecast"] = forecast
    raw["areas"]["sammakorn"]["forecast_short"] = dict(forecast)
    raw["areas"]["sammakorn"]["forecast_72h_worst"] = {
        "value_mm": 42.7, "model_id": "jma_seamless", "model_th": "JMA"}
    layer0_area = raw.setdefault("layer0_public", {}).setdefault("areas", {}).setdefault("sammakorn", {})
    layer0_area["in_items"] = [{"label_th": "ECMWF", "text_th": "พรุ่งนี้ 2 มม. · รวม 7 วัน 68 มม.",
                                 "tag_th": "ข่าว/บุคคลที่สาม"}]
    layer0_area["prop_flood_06"] = {
        "forecast_72h_worst_text_th": "ฝนพยากรณ์ 72 ชม. (กรณีแย่สุด): 42.7 มม. (JMA)",
        "forecast_72h_worst_value_mm": 42.7,
        "forecast_72h_worst_model_th": "JMA",
        "forecast_72h_items_th": ["JMA: 42.7 มม."],
    }
    out_path = tmp_path / "data_stale_forecast.json"
    out_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return str(out_path)


def test_build_time_stale_forecast_is_suppressed_in_the_exported_json(tmp_path):
    data_path = _data_with_stale_forecast(tmp_path)
    out_dir = tmp_path / "api" / "v1"
    export_api.export_api(
        data_json_path=data_path,
        typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
        typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
        self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
        sources_registry_path=str(FIXTURES / "sources_registry_sample.yaml"),
        out_dir=str(out_dir),
    )
    area = json.loads((out_dir / "areas" / "sammakorn.json").read_text(encoding="utf-8"))
    fh = area["forward_hazard"]
    for block_key in ("forecast", "forecast_short"):
        block = fh[block_key]
        assert block["trend_word"] is None
        assert block["next6h_mm"] is None
        assert block["items"] is None
        assert block["available"] is False
    assert fh["forecast_72h_worst"]["value_mm"] is None

    layer0 = area["current_local_state"]["layer0"]
    assert "พรุ่งนี้" not in layer0["in_items"][0]["text_th"]
    assert layer0["prop_flood_06"]["forecast_72h_worst_value_mm"] is None


def test_stale_forecast_field_list_matches_mcp_layer(monkeypatch):
    """The field list this module nulls on a build-time-stale forecast and the
    one `tools/mcp/floodconnect_mcp.py` nulls at call time must stay in sync --
    see both modules' own FIX B comments for why the logic is duplicated
    (no shared import path) rather than imported once."""
    import importlib.util
    ROOT_ = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "floodconnect_mcp", ROOT_ / "tools" / "mcp" / "floodconnect_mcp.py")
    mcp_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mcp_mod)
    assert export_api._STALE_FORECAST_FIELDS == mcp_mod._STALE_FORECAST_FIELDS
    assert export_api._STALE_FORECAST_72H_FIELDS == mcp_mod._STALE_FORECAST_72H_FIELDS
    assert export_api._LAYER0_FORECAST_TAG_TH == mcp_mod._LAYER0_FORECAST_TAG_TH
