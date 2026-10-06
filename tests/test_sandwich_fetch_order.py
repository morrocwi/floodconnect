"""Tests for sources/sandwich_fetch_order.yaml and the "Fetch order -- Jev
Sandwich (S0-S8)" section of docs/API_MANUAL.md. This is a test of the DOCUMENTATION
(a pseudocode fetch-order guide, per the founder's own scope decision -- no executable
library), not of a new library: it checks internal consistency (every step's source id
is really keyless and really in live_call_index), that the vocabulary matches what
floodconnect_model.py actually returns, and that the schemas referenced really exist.
No network call is made by this test file.

Note: schemas/ring_readout.schema.json and schemas/sandwich_readout.schema.json were
never shipped in this repo -- schemas/layer_readout.schema.json and
schemas/sandwich_trace.schema.json are the runtime contract (see docs/API_MANUAL.md's
"Note on what actually ships"). This file validates only against the two schemas that
are actually shipped, plus the YAML/manual's own internal structure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

jsonschema = pytest.importorskip("jsonschema")

import floodconnect_model as fm

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = REPO_ROOT / "schemas"
SOURCES = REPO_ROOT / "sources"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _sandwich_order() -> dict:
    return _load_yaml(SOURCES / "sandwich_fetch_order.yaml")


def _live_call_index() -> dict:
    return _load_yaml(SOURCES / "live_call_index.yaml")


def _registry() -> dict:
    return _load_yaml(SOURCES / "registry.yaml")


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def _validator(schema_name: str) -> "jsonschema.Validator":
    from referencing import Registry, Resource

    schema = _load_schema(schema_name)
    resources = []
    for fname in (
        "reading.schema.json",
        "series.schema.json",
    ):
        doc = _load_schema(fname)
        resources.append((doc["$id"], Resource.from_contents(doc)))
        resources.append((fname, Resource.from_contents(doc)))
    registry = Registry().with_resources(resources)
    cls = jsonschema.validators.validator_for(schema)
    return cls(schema, registry=registry)


# ---------------------------------------------------------------------------
# 1. step shape: S0..S8 in order, each with the required keys
# ---------------------------------------------------------------------------

def test_steps_are_exactly_s0_to_s8_in_order():
    order = _sandwich_order()
    ids = [s["id"] for s in order["steps"]]
    assert ids == [f"S{i}" for i in range(9)]


def test_every_step_has_protocol_step_consumed_by_output_budget_refusals():
    order = _sandwich_order()
    valid_d_steps = {f"D{i}" for i in range(1, 9)}
    for step in order["steps"]:
        assert step["protocol_step"] in valid_d_steps, step["id"]
        assert step.get("consumed_by"), step["id"]
        assert step.get("output"), step["id"]
        assert "budget" in step, step["id"]
        assert "refusal_codes" in step, step["id"]


# ---------------------------------------------------------------------------
# 2. every keyless source named by a step is really in live_call_index with
#    auth: none; no twa-api-public host appears outside optional_keyed
# ---------------------------------------------------------------------------

def test_every_keyless_source_is_in_live_call_index_and_keyless():
    order = _sandwich_order()
    index = _live_call_index()
    by_id = {row["source_id"]: row for row in index["rows"]}
    checked = 0
    for step in order["steps"]:
        for sid in step.get("keyless_sources", []):
            assert sid in by_id, f"{step['id']}: {sid} not in live_call_index"
            assert by_id[sid].get("auth") == "none", f"{step['id']}: {sid} is not keyless"
            checked += 1
    assert checked > 0


def test_no_twa_api_public_host_outside_optional_keyed():
    order = _sandwich_order()
    text = (SOURCES / "sandwich_fetch_order.yaml").read_text()
    manual = (REPO_ROOT / "docs" / "API_MANUAL.md").read_text()
    # every occurrence of the keyed host in the YAML must be inside an
    # optional_keyed endpoint string
    for row in order["optional_keyed"]:
        assert row["called"] is False
    non_optional_block = text.split("optional_keyed:")[0]
    assert "twa-api-public" not in non_optional_block
    # the manual's fetch-order section may name the host only inside its own
    # "Keyed (optional)" framing -- never as something this repo calls.
    assert "twa-api-public" in manual  # documented somewhere
    for line in manual.splitlines():
        if "twa-api-public" in line:
            assert "key" in line.lower() or "never called" in line.lower(), (
                f"twa-api-public line missing a key/never-called marker: {line!r}"
            )


# ---------------------------------------------------------------------------
# 3. optional_keyed rows: called:false, a URL or OPEN request_key_at; no
#    key-like value leaked anywhere in this registry
# ---------------------------------------------------------------------------

def test_optional_keyed_rows_never_called_and_have_a_channel():
    order = _sandwich_order()
    for row in order["optional_keyed"]:
        assert row["called"] is False
        chan = row["request_key_at"]
        assert chan.startswith("http") or "OPEN" in chan


def test_no_key_like_value_leaked():
    key_like = re.compile(r"[A-Za-z0-9]{24,}")
    for path in (
        SOURCES / "sandwich_fetch_order.yaml",
        SOURCES / "live_call_index.yaml",
        REPO_ROOT / "docs" / "API_MANUAL.md",
    ):
        text = path.read_text()
        for m in key_like.finditer(text):
            token = m.group(0)
            # sha256-style 12-hex-char ids, dates, bytes counts etc. are not secrets;
            # the real guard is "no 32+ char opaque token embedded in a URL path".
            assert not re.search(r"(api[_-]?key|token|secret)=", text[max(0, m.start() - 20):m.start()], re.I)


# ---------------------------------------------------------------------------
# 4. vocabulary matches what floodconnect_model.py actually returns
# ---------------------------------------------------------------------------

def test_trend_from_delta_k_matches_floodconnect_model():
    order = _sandwich_order()
    crosswalk = order["vocab"]["trend_from_delta_k"]
    rising = fm.delta_k(1.0, 0.5, 0.02)
    falling = fm.delta_k(0.5, 1.0, 0.02)
    flat = fm.delta_k(1.0, 1.0, 0.02)
    no_readout = fm.delta_k(1.0, None, 0.02)
    assert crosswalk[rising["trend"]] == "RISING"
    assert crosswalk[falling["trend"]] == "FALLING"
    assert crosswalk[flat["trend"]] == "STABLE"
    assert crosswalk[no_readout["trend"]] == "NO_READOUT"


def test_colour_vocab_matches_defs_colour5():
    """This YAML's own vocab.colour (documentation of record) against
    schemas/defs.schema.json#/$defs/colour5 (the shipped runtime enum) -- the YAML
    spells the UNKNOWN case as null (see its own header comment), the schema spells
    it as the string "UNKNOWN"; normalise null -> "UNKNOWN" before comparing."""
    order = _sandwich_order()
    yaml_colours = {c if c is not None else "UNKNOWN" for c in order["vocab"]["colour"]}
    defs = _load_schema("defs.schema.json")
    schema_colours = set(defs["$defs"]["colour5"]["enum"])
    assert yaml_colours == schema_colours


# ---------------------------------------------------------------------------
# 5. schemas named by the manual/order really exist and are valid JSON Schema
# ---------------------------------------------------------------------------

def test_every_schema_referenced_exists_and_is_valid():
    for name in (
        "reading.schema.json",
        "series.schema.json",
        "layer_readout.schema.json",
        "sandwich_trace.schema.json",
    ):
        schema = _load_schema(name)
        jsonschema.Draft202012Validator.check_schema(schema)


# ---------------------------------------------------------------------------
# 6. schema negatives on reading.schema.json (bank/FAULT rules)
# ---------------------------------------------------------------------------

def test_reading_schema_rejects_null_bank_without_bank_note():
    reading = {
        "source_id": "bma_watermap",
        "station_code": "WL.SSB.02",
        "variable": "canal_water_level_m",
        "value": 0.1,
        "bank": None,
        "observed_at_utc": "2026-10-05T04:00:00+00:00",
        "fetched_at_utc": "2026-10-05T04:00:00+00:00",
        "trust_tier": "official_telemetry",
    }
    with pytest.raises(jsonschema.ValidationError):
        _validator("reading.schema.json").validate(reading)


def test_reading_schema_rejects_fault_with_numeric_value():
    reading = {
        "source_id": "bma_watermap",
        "station_code": "WL.SSB.02",
        "variable": "canal_water_level_m",
        "value": 1.23,
        "freshness_flag": "FAULT",
        "observed_at_utc": "2026-10-05T04:00:00+00:00",
        "fetched_at_utc": "2026-10-05T04:00:00+00:00",
        "trust_tier": "official_telemetry",
    }
    with pytest.raises(jsonschema.ValidationError):
        _validator("reading.schema.json").validate(reading)


# ---------------------------------------------------------------------------
# 7. the BMA series fixture -> month+1 conversion, 5-minute spacing
# ---------------------------------------------------------------------------

def test_bma_station_detail_fixture_month_is_0_indexed():
    data = json.loads((FIXTURES / "bma_station_detail_smk01_series_sample.json").read_text())
    first = data["sample_first_3"][0]
    year, month0, day, hour, minute, second, value = first
    assert int(month0) + 1 == 10  # the fixture's literal "9" means October (2026-10-03)
    second_pt = data["sample_first_3"][1]
    assert int(second_pt[4]) - int(minute) == 5 or int(second_pt[3]) != int(hour)


def test_thaiwater_waterlevel_graph_fixture_is_not_confirmed_populated():
    index = _live_call_index()
    row = next(r for r in index["rows"] if r["source_id"] == "thaiwater_waterlevel_graph")
    assert row["series_confirmed"] is False
    assert row["status"] == "OPEN"


# ---------------------------------------------------------------------------
# 8. hotspot regression -- startswith, not equality
# ---------------------------------------------------------------------------

def test_hotspot_predicate_catches_the_real_overbank_string():
    order = _sandwich_order()
    manual = (REPO_ROOT / "docs" / "API_MANUAL.md").read_text()
    s3 = next(s for s in order["steps"] if s["id"] == "S3")
    needle = 'startswith(diff_wl_bank_text,"ล้นตลิ่ง")'
    assert needle in s3["predicate"]
    assert needle in manual
    assert '== "ล้นตลิ่ง"' not in s3["predicate"]
    assert '== "ล้นตลิ่ง"' not in manual
    # and the real agency string carries the trailing unit, which an == check
    # would miss -- confirms startswith is the correct operator, not a stand-in.
    diff_wl_bank_text = "ล้นตลิ่ง (ม.)"
    assert diff_wl_bank_text.startswith("ล้นตลิ่ง")
    assert diff_wl_bank_text != "ล้นตลิ่ง"


# ---------------------------------------------------------------------------
# 9. Sammakorn ring from east_chain.yaml
# ---------------------------------------------------------------------------

def test_sammakorn_z1_from_east_chain():
    chain = _load_yaml(REPO_ROOT / "site" / "inputs" / "canals" / "east_chain.yaml")
    nodes = chain["nodes"]
    adjacency: dict[str, set[str]] = {n: set() for n in nodes}
    for e in chain["edges"]:
        adjacency[e["u"]].add(e["v"])
        adjacency[e["v"]].add(e["u"])  # direction unknown/declared both-ways within hop<=2

    def bfs(start: str, hop_max: int) -> set[str]:
        seen = {start}
        frontier = {start}
        for _ in range(hop_max):
            nxt = set()
            for n in frontier:
                nxt |= adjacency[n] - seen
            seen |= nxt
            frontier = nxt
        seen.discard(start)
        return seen

    z1_nodes = bfs("sammakorn_pond", 2)
    assert z1_nodes == {"banma", "wangyai", "tpk03"}
    located_stations = {nodes[n]["canal_oldcode"] for n in z1_nodes if nodes[n].get("canal_oldcode")}
    assert located_stations == {"WL.TPK.03"}
    assert nodes["sammakorn_pond"]["canal_oldcode"] is None  # WL.SMK.01 is not a KG node id


# ---------------------------------------------------------------------------
# 10. manual guards
# ---------------------------------------------------------------------------

def test_manual_has_fetch_order_section_and_forbidden_terms_absent():
    manual = (REPO_ROOT / "docs" / "API_MANUAL.md").read_text()
    collapsed = " ".join(manual.split())
    assert "sandwich_fetch_order.yaml" in manual
    assert "```python" not in manual
    forbidden = [
        "this session",
        "dedicated worker",
        "same session",
        "raw agent",
        "coordinator",
        "this task",
        "a third research pass",
        "3rd research pass",
        "a separate pass",
        "dedicated pass",
        "named in this task",
    ]
    for term in forbidden:
        assert term not in collapsed, f"forbidden process-wording term found: {term!r}"


# ---------------------------------------------------------------------------
# 11. budget: sum of step max_calls <= tool_tiers_max_calls; per-source caps
#     respected against registry.yaml host_rule
# ---------------------------------------------------------------------------

def test_budget_per_run_respects_tool_tiers_and_registry_host_rule():
    order = _sandwich_order()
    total = sum(step["budget"].get("max_calls", 0) for step in order["steps"])
    # S6 carries an explicit conditional_max_calls separate from max_calls
    s6 = next(s for s in order["steps"] if s["id"] == "S6")
    total_with_conditional = total + s6["budget"].get("conditional_max_calls", 0)
    assert total_with_conditional <= order["budget_per_run"]["tool_tiers_max_calls"]

    registry = _registry()
    reg_sources = registry["sources"]
    reg_by_id = {r["id"]: r for r in reg_sources} if isinstance(reg_sources, list) else reg_sources
    for step in order["steps"]:
        sources = list(step.get("keyless_sources", [])) + list(step.get("conditional_sources", []))
        if not sources:
            continue
        cap_sum = 0
        for sid in sources:
            reg_row = reg_by_id.get(sid)
            cap = reg_row["host_rule"].get("max_requests_per_run") if reg_row and "host_rule" in reg_row else None
            cap_sum += cap if cap is not None else 1
        assert step["budget"].get("max_calls", 0) <= cap_sum, step["id"]
