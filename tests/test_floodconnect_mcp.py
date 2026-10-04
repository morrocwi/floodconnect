"""tests/test_floodconnect_mcp.py -- Component B MCP server tests.

Exports Component A's fixtures to a temp dir and calls each tool's core
function directly (module import; the FastMCP decorator wraps the exact
same function, so this exercises the real logic without needing a stdio
transport in test). Also covers the no-hosted-access case: a URL
FLOODCONNECT_API_BASE is refused outright, never fetched.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT))

from tools.api import export_api  # noqa: E402


def _load_mcp_module():
    spec = importlib.util.spec_from_file_location("floodconnect_mcp", ROOT / "tools" / "mcp" / "floodconnect_mcp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mcp_mod():
    return _load_mcp_module()


@pytest.fixture()
def api_dir(tmp_path):
    out = tmp_path / "api" / "v1"
    export_api.export_api(
        data_json_path=str(FIXTURES / "data_json_sample.json"),
        typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
        typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
        self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
        sources_registry_path=str(FIXTURES / "sources_registry_sample.yaml"),
        out_dir=str(out),
    )
    return str(out)


def assert_has_epistemic_envelope(resp: dict) -> None:
    assert "source" in resp
    assert "staleness" in resp
    assert "tag" in resp["staleness"]


def test_list_areas(mcp_mod, api_dir):
    resp = mcp_mod.list_areas(api_dir)
    assert_has_epistemic_envelope(resp)
    ids = sorted(a["area_id"] for a in resp["areas"])
    assert ids == ["ram53", "sammakorn"]


def test_get_area_state_always_has_both_top_level_keys(mcp_mod, api_dir):
    resp = mcp_mod.get_area_state(api_dir, "sammakorn")
    assert_has_epistemic_envelope(resp)
    assert "current_local_state" in resp
    assert "forward_hazard" in resp


def test_get_area_state_unknown_area_raises_typed_error(mcp_mod, api_dir):
    with pytest.raises(mcp_mod.FloodConnectMCPError) as exc_info:
        mcp_mod.get_area_state(api_dir, "not-a-real-area")
    assert exc_info.value.code == "AREA_NOT_FOUND"
    # error text carries no local filesystem path
    assert str(api_dir) not in str(exc_info.value)


def _write_area_json(api_dir: str, area_id: str, area_json: dict) -> None:
    p = Path(api_dir) / "areas" / f"{area_id}.json"
    p.write_text(json.dumps(area_json, ensure_ascii=False), encoding="utf-8")


def _forecast_area_fixture(fetched_at: "str | None") -> dict:
    """A minimal area.json with a real forward_hazard.forecast block (items,
    trend_word, next*_mm, hourly) plus a layer0 in_items row carrying the
    same third-party-forecast prose, shaped like the real
    `tools/api/export_api.py`/`site/build_data.py` output -- used to prove
    Stale forward_hazard field drop () nulls these fields IN THE DATA when stale,
    not only in a CLI printer."""
    forecast = {
        "available": True,
        "status": "ok",
        "items": [{"h": "19:00", "mm": 1.0}],
        "hourly": [{"h": "19:00", "mm": 1.0, "prob": 59}],
        "hourly_full": [{"time_local": "2026-10-02T19:00", "mm": 1.0}],
        "source": "Open-Meteo",
        "trust_tier": "third_party_forecast",
        "direction": "falling",
        "trend_word": "ฝนกำลังจะเบาลงหลัง 22:00 น.",
        "next6h_mm": 1.3,
        "next24h_mm": 7.8,
        "h24_48_mm": 4.3,
        "h48_72_mm": 5.5,
        "first_dry_6h_start": "22:00",
        "fetched_at": fetched_at,
    }
    return {
        "api_version": "1.0.0",
        "generated_at_bkk": fetched_at,
        "area_id": "sammakorn",
        "label": "สัมมากร",
        "current_local_state": {
            "water_balance": None,
            "pumps": [],
            "layer0": {
                "in_items": [{"label_th": "ECMWF", "text_th": "พรุ่งนี้ 2 มม. · รวม 7 วัน 68 มม.",
                               "tag_th": "ข่าว/บุคคลที่สาม"}],
                "out_items": [],
                "prop_flood_06": {
                    "forecast_72h_worst_text_th": "ฝนพยากรณ์ 72 ชม. (กรณีแย่สุด): 42.7 มม. (JMA)",
                    "forecast_72h_worst_value_mm": 42.7,
                    "forecast_72h_worst_model_th": "JMA",
                    "forecast_72h_items_th": ["JMA: 42.7 มม."],
                },
            },
            "canals": [],
        },
        "forward_hazard": {
            "forecast": forecast,
            "forecast_short": dict(forecast),
            "forecast_72h_worst": {"value_mm": 42.7, "model_id": "jma_seamless", "model_th": "JMA"},
            "note": "placeholder",
        },
        "contradictions": [],
        "safety": {"hotlines": [], "note": "informational numbers only"},
        "data_freshness": {"overall_age_class": "expired", "oldest_field": "none"},
    }


def test_get_area_state_nulls_stale_forecast_figures_in_the_data(mcp_mod, api_dir):
    """Stale forward_hazard field drop (2026-10-04): a 31h-old forecast must come
    back with `trend_word`/`direction`/`next6h_mm`/`items`/`hourly` all None
    (and the mirrored layer0 prose replaced), not just suppressed by a
    printer -- MEASURED later as still present before
    this fix."""
    import datetime as dt
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=31)).isoformat()
    _write_area_json(api_dir, "sammakorn", _forecast_area_fixture(old))

    resp = mcp_mod.get_area_state(api_dir, "sammakorn")

    fh = resp["forward_hazard"]
    assert fh["recomputed_staleness"]["stale"] is True
    for block_key in ("forecast", "forecast_short"):
        block = fh[block_key]
        assert block["trend_word"] is None
        assert block["direction"] is None
        assert block["next6h_mm"] is None
        assert block["next24h_mm"] is None
        assert block["h24_48_mm"] is None
        assert block["h48_72_mm"] is None
        assert block["items"] is None
        assert block["hourly"] is None
        assert block["hourly_full"] is None
        assert block["available"] is False
    worst = fh["forecast_72h_worst"]
    assert worst["value_mm"] is None
    assert worst["model_id"] is None
    assert worst["model_th"] is None

    layer0 = resp["current_local_state"]["layer0"]
    in_row = layer0["in_items"][0]
    assert "พรุ่งนี้" not in in_row["text_th"]
    assert "STALE" in in_row["text_th"]
    pf06 = layer0["prop_flood_06"]
    assert pf06["forecast_72h_worst_value_mm"] is None
    assert pf06["forecast_72h_worst_model_th"] is None
    assert pf06["forecast_72h_items_th"] is None

    # the payload carries its own snapshot markers (not only the intermediate dict)
    assert resp["snapshot"] is True
    assert resp["snapshot_generated_at"] == old


def test_get_area_state_keeps_fresh_forecast_figures_in_the_data(mcp_mod, api_dir):
    """The flip side of the stale case: a forecast fetched moments ago keeps
    its real trend_word/next6h_mm/items -- this fix must never null a FRESH
    forecast."""
    import datetime as dt
    recent = dt.datetime.now(dt.timezone.utc).isoformat()
    _write_area_json(api_dir, "sammakorn", _forecast_area_fixture(recent))

    resp = mcp_mod.get_area_state(api_dir, "sammakorn")

    fh = resp["forward_hazard"]
    assert fh["recomputed_staleness"]["stale"] is False
    assert fh["forecast"]["trend_word"] == "ฝนกำลังจะเบาลงหลัง 22:00 น."
    assert fh["forecast"]["next6h_mm"] == 1.3
    assert fh["forecast"]["items"] == [{"h": "19:00", "mm": 1.0}]
    assert fh["forecast_72h_worst"]["value_mm"] == 42.7
    layer0 = resp["current_local_state"]["layer0"]
    assert layer0["in_items"][0]["text_th"] == "พรุ่งนี้ 2 มม. · รวม 7 วัน 68 มม."


def test_get_area_state_marks_stale_tier_colour_never_served_fresh(mcp_mod, api_dir):
    """fix (2026-10-04): MEASURED later --
    `layer0.prop_flood_06.tier`/`tier_color`/`tier_word_th` were baked at build time
    and NEVER recomputed, so a RED tier colour from an old build could be served as
    if current. This fixture has no water_balance/canals at all, so `overall` is
    always "expired" -- the tier fields must be suppressed, never the raw baked
    colour."""
    area = _forecast_area_fixture(None)  # fetched_at=None -> always stale/expired
    area["current_local_state"]["layer0"]["prop_flood_06"].update({
        "tier": "L5", "tier_word_th": "วิกฤต", "tier_color": "#D32F2F",
    })
    _write_area_json(api_dir, "sammakorn", area)
    resp = mcp_mod.get_area_state(api_dir, "sammakorn")
    pf06 = resp["current_local_state"]["layer0"]["prop_flood_06"]
    assert pf06["tier_color"] is None, "a stale tier colour must never be served as-is"
    assert pf06.get("tier_stale") is True
    assert "STALE" in pf06["tier_word_th"]


def test_get_area_state_marks_measured_layer0_row_stale_not_silently_current(mcp_mod, api_dir):
    """fix (2026-10-04): a MEASURED-tagged layer0 row (e.g. "ฝนวัดจริง
    (24 ชม.) 0.0 มม.", tag_th="วัดจากไฟล์ข้อมูล") used to keep that tag forever, with no
    staleness marking at all -- only the separately-tagged forecast rows got one.
    This fixture has no water_balance/canals, so `overall` is always "expired"."""
    area = _forecast_area_fixture(None)
    area["current_local_state"]["layer0"]["out_items"] = [
        {"label_th": "ฝนวัดจริง (24 ชม.)", "text_th": "0.0 มม.", "tag_th": "วัดจากไฟล์ข้อมูล"},
    ]
    _write_area_json(api_dir, "sammakorn", area)
    resp = mcp_mod.get_area_state(api_dir, "sammakorn")
    measured_row = resp["current_local_state"]["layer0"]["out_items"][0]
    assert measured_row.get("stale") is True
    assert "STALE" in measured_row["text_th"]


def test_get_area_state_missing_export_has_explicit_unknown_dual_state(mcp_mod, tmp_path):
    """fix (2026-10-04): a missing local export used to return only
    `next_action` + the envelope's `tag: OPEN` -- a caller reading `current_local_state`
    /`forward_hazard` directly (the fields every OTHER response has) saw neither key.
    Both must now be explicitly 'UNKNOWN', never absent."""
    empty_api_dir = str(tmp_path / "empty_api_v1")
    resp = mcp_mod.get_area_state(empty_api_dir, "sammakorn")
    assert resp["current_local_state"] == "UNKNOWN"
    assert resp["forward_hazard"] == "UNKNOWN"
    assert resp["staleness"]["tag"] == "OPEN"
    assert resp.get("next_action")


def test_get_station_known_code_returns_found_with_source_and_observed_at(mcp_mod, api_dir):
    """Reproduces the incident (spec sec. 0): WL.SSB.08 is fresh in the
    fixture -> found:true with a real value, never UNKNOWN."""
    resp = mcp_mod.get_station(api_dir, "WL.SSB.08")
    assert_has_epistemic_envelope(resp)
    assert resp["found"] is True
    assert resp["station"]["level_m"] == 0.42
    assert resp["staleness"]["observed_at"] is not None


def test_get_station_unknown_code_never_bare_false_or_null(mcp_mod, api_dir):
    resp = mcp_mod.get_station(api_dir, "NOT-A-REAL-CODE")
    assert resp["found"] is False
    assert resp["tag"] == "OPEN"
    assert "staleness" in resp


def test_find_safe_route_returns_route_found_for_verified_safe_target(mcp_mod, api_dir):
    resp = mcp_mod.find_safe_route(api_dir, "household_a", "walk", 2)
    assert resp["result"] == "ROUTE_FOUND"
    assert resp["target"] == "external_safe_good"
    assert_has_epistemic_envelope(resp)


def test_find_safe_route_rejects_unsafe_node_calls_canonical_function(mcp_mod, api_dir):
    """Regression: the superseded local walk (`_dag_node_ok`)
    only checked status not in (None, "UNKNOWN") and fresh truthy, so it
    wrongly accepted an UNSAFE-but-fresh node. The canonical
    `community_dag.find_safe_route` rejects it (status must be SAFE for a
    target, SAFE/DEGRADED for a transit node) -- this must still be
    NO_FEASIBLE_SAFE_ROUTE now that the MCP tool delegates to it."""
    resp = mcp_mod.find_safe_route(api_dir, "household_b", "walk", 1)
    assert resp["result"] == "NO_FEASIBLE_SAFE_ROUTE"
    assert "checked_nodes" in resp


def test_find_safe_route_unknown_zone(mcp_mod, api_dir):
    resp = mcp_mod.find_safe_route(api_dir, "no-such-zone", "walk", 1)
    assert resp["result"] == "NO_FEASIBLE_SAFE_ROUTE"


def test_list_upstream_sources_filter(mcp_mod, api_dir):
    resp = mcp_mod.list_upstream_sources(api_dir)
    assert_has_epistemic_envelope(resp)
    assert len(resp["sources"]) == 2
    filtered = mcp_mod.list_upstream_sources(api_dir, agency="Test BMA")
    assert len(filtered["sources"]) == 1


def test_explain_rules_has_unknown_not_safe_sentence(mcp_mod):
    resp = mcp_mod.explain_rules()
    assert "UNKNOWN is not SAFE" in resp["unknown_is_not_safe"]


def test_all_tool_docstrings_carry_unknown_not_safe_sentence(mcp_mod):
    """Spec sec. 3.3: the MCP `description` string (the function docstring
    FastMCP reads) must state the sentence verbatim for every tool."""
    if mcp_mod.mcp is None:
        pytest.skip("mcp SDK not importable in this environment; fallback path tested separately")
    import asyncio
    tools = asyncio.run(mcp_mod.mcp.list_tools())
    assert tools, "no tools registered"
    for t in tools:
        desc = t.description or ""
        assert "UNKNOWN is not SAFE" in desc, f"{t.name} description missing required sentence: {desc!r}"


def test_url_base_refused_no_hosted_access(mcp_mod):
    """Project decision 2026-10-04 (no-hosted-access): a hosted/remote
    FLOODCONNECT_API_BASE is itself a forbidden access channel -- this server must
    refuse it outright (OPEN + a local-refresh action), never issue a GET at all."""
    with pytest.raises(mcp_mod.FloodConnectMCPError) as exc_info:
        mcp_mod._read("https://example.invalid/api/v1", "index.json")
    assert exc_info.value.code == "OPEN"
    assert "local" in str(exc_info.value).lower()

    with pytest.raises(mcp_mod.FloodConnectMCPError):
        mcp_mod._read("http://example.invalid/api/v1", "index.json")


def test_default_base_resolves_against_repo_root_not_cwd(mcp_mod, monkeypatch, tmp_path):
    """`DEFAULT_BASE` used to be the bare relative string
    "site/dist/api/v1", resolved against whatever process cwd an MCP client happened to
    launch this server with -- never this repo's own location. Running from an
    unrelated cwd (a fresh tmp_path) must still resolve to this repo's own
    `site/dist/api/v1` path, via `_REPO_ROOT`, with no `FLOODCONNECT_API_BASE`
    override set -- regardless of whether that path has been populated yet."""
    monkeypatch.delenv("FLOODCONNECT_API_BASE", raising=False)
    monkeypatch.chdir(tmp_path)
    base = mcp_mod._resolve_base()
    assert Path(base).is_absolute(), "default base must not depend on the caller's cwd"
    assert base == str(mcp_mod._REPO_ROOT / "site" / "dist" / "api" / "v1")


def test_default_base_missing_export_is_unknown_with_refresh_action(mcp_mod, monkeypatch, tmp_path):
    """FIX D (2026-10-04, project decision -- no hosted access): this repo ships NO
    pre-computed `site/dist/api/v1/**` export (gitignored, never committed) -- a fresh
    clone's default base therefore has nothing at it until a caller runs the local
    export pipeline themselves. `list_areas`/`get_area_state` must return an honest
    UNKNOWN + `next_action`, never raise an opaque error and never read a value from
    some tracked snapshot (that fallback no longer exists)."""
    empty_base = str(tmp_path / "no" / "export" / "here")
    resp = mcp_mod.list_areas(empty_base)
    assert resp["areas"] == []
    assert resp["staleness"]["tag"] == "OPEN"
    assert resp.get("next_action")

    resp2 = mcp_mod.get_area_state(empty_base, "sammakorn")
    assert resp2["staleness"]["tag"] == "OPEN"
    assert resp2.get("next_action")

    # a genuinely unknown area_id still raises the typed error, not a soft OPEN
    with pytest.raises(mcp_mod.FloodConnectMCPError) as exc_info:
        mcp_mod.get_area_state(empty_base, "not-a-real-area")
    assert exc_info.value.code == "AREA_NOT_FOUND"


def test_floodconnect_answer_tool_calls_kb_build_answer_in_process(mcp_mod, monkeypatch, tmp_path):
    """The MCP server now has a `floodconnect_answer` tool
    equivalent to `kb.py answer --at <at> [--refresh]`, calling `kb.build_answer` (the
    SAME function the CLI uses) in-process -- never a second implementation, never a
    subprocess/shell-out. `refresh=False` here (no network in this test).

    `kb.DB_PATH` is monkeypatched to a path that does not exist (this test's own concern
    is the MCP wiring, not any particular DB content) -- this repo's session-wide guard
    (tests/conftest.py) refuses a test that leaves the real gitignored
    data/observations.sqlite touched, and importing `kb` here patches the SAME module
    object `tools/mcp/floodconnect_mcp.py`'s own `import kb` resolves to (one entry in
    `sys.modules`), so the patch reaches the tool call too."""
    import kb
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")
    out = mcp_mod.floodconnect_answer_core("sammakorn", refresh=False)
    assert out["at"] == "sammakorn"
    assert set(out.keys()) >= {
        "state", "hazard", "accountability", "next_action", "source_tags"}
    assert out["refresh"] is None  # refresh=False -> no refresh report, matches kb.py CLI
    # fix (2026-10-04): the MCP tool gets the SAME `cctv` handling
    # as the CLI -- ALWAYS present, compact {tag: OPEN, next_action} when no camera is
    # in range (no DB in this test), never omitted and never an error; see
    # `test_build_answer_includes_cctv_field_with_real_camera` (tests/test_kb_answer.py)
    # for the present case through the SAME `kb.build_answer` this tool calls.
    assert out["cctv"]["tag"] == "OPEN"


def test_floodconnect_answer_tool_db_missing_is_unknown_with_refresh_action(mcp_mod, monkeypatch, tmp_path):
    """FIX D (2026-10-04, project decision -- no hosted access): the MCP
    `floodconnect_answer` tool reads `kb.build_answer`'s SAME `hazard` dict the CLI
    `--json` path does. This used to fall through to a tracked offline snapshot when
    `data/observations.sqlite` was missing (regression-tested by nulling that
    snapshot's stale forecast figures) -- that fallback and the file it read are both
    removed (this repo ships no pre-computed reading). A missing DB now gives an
    honest OPEN `hazard` with a `next_action`, never a stale or retained figure."""
    import kb
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")

    out = mcp_mod.floodconnect_answer_core("sammakorn", refresh=False)
    hazard = out["hazard"]
    assert hazard["tag"] == "OPEN"
    assert hazard.get("next_action")
    assert "offline_snapshot" not in hazard


def test_floodconnect_answer_tool_bad_at_raises_typed_mcp_error(mcp_mod, monkeypatch, tmp_path):
    """A bad `at` must surface as the server's own typed `FloodConnectMCPError`
    (`BAD_AT`), never a raw traceback reaching the MCP transport."""
    import kb
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")
    with pytest.raises(mcp_mod.FloodConnectMCPError) as exc_info:
        mcp_mod.floodconnect_answer_core("not,a,valid,at,value", refresh=False)
    assert exc_info.value.code == "BAD_AT"


def test_real_stdio_initialize_handshake(api_dir):
    """A real MCP client must be able to complete the
    stdio handshake and call a tool against THIS SAME subprocess entrypoint
    (`python3 tools/mcp/floodconnect_mcp.py`) -- not just the in-process
    functions the other tests in this file call directly. Requires the real
    `mcp` SDK (`pip install -e '.[mcp]'`); skips rather than fails if it is
    not importable in this environment, since the fallback-path tests above
    cover the no-SDK branch separately."""
    pytest.importorskip("mcp")
    import asyncio

    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def _run() -> list:
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "tools" / "mcp" / "floodconnect_mcp.py")],
            env={"FLOODCONNECT_API_BASE": api_dir, "PYTHONPATH": str(ROOT)},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                names = {t.name for t in tools}
                assert "floodconnect_list_areas" in names
                result = await session.call_tool("floodconnect_list_areas", {})
                return result.content

    content = asyncio.run(_run())
    assert content, "tools/call returned no content blocks"
    payload = json.loads(content[0].text)
    assert "sammakorn" in [a["area_id"] for a in payload["areas"]]
