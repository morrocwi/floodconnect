#!/usr/bin/env python3
"""tools/api/export_api.py -- FloodConnect API v1 generator.

Reads EXISTING build artifacts only:
  - site/dist/data.json            (written by site/build_data.py)
  - output/typology_graph.json     (networkx node-link JSON)
  - output/typology_<area>_subgraph.json  (per-area, if present)
  - site/inputs/community/self_help_dag.yaml
  - sources/registry.yaml

Writes site/dist/api/v1/**. Pure transform -- never fetches network data,
never calls collect.py, never writes outside --out-dir.

Freshness rule (FloodConnect API v1 spec sec. 1, "reuse, do not reinvent"):
this file imports `age_class`/`STALE_HOURS`/`is_stale` from site/build_data.py
by path (build_data.py is a script, not an installed package) and calls them.
It does not define, or fall back to, any second age-cutoff number of its own.
A grep/AST check for that is tests/test_export_api.py::test_no_local_cutoff_constant.

No new equations: every derived field here is a straight read-through of a
value site/build_data.py or output/typology_graph.json already computed
(their own PROP-FLOOD-0x codes are carried through verbatim in the source
records, e.g. water_balance.status/reason_codes) -- this generator computes
no new number.
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a repo-wide dependency already
    yaml = None

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

API_VERSION = "1.0.0"

# Fixed 5-value tag set this exporter is allowed to emit in any `staleness.tag` field.
# Imported from the single shared tag_vocabulary module (see that file's docstring) --
# kept identical to AI.md's documented vocabulary and to
# tools/mcp/floodconnect_mcp.py's TAG_VOCABULARY and kb.py's TAG_ORDER, all three now
# importing the same object rather than three hand-copied constants
# (tests/test_tag_vocabulary.py fails if any of them drifts). A finer-grained reason
# (e.g. a value computed from a not-yet-Toledo-registered proposal equation) belongs
# in the optional `basis` key next to the tag, never as a sixth `tag` value.
from tag_vocabulary import TAG_VOCABULARY  # noqa: E402 -- _REPO_ROOT is already on sys.path

# Secret-shaped strings that must never appear in a value we emit (sec. 2.3 /
# acceptance check 2). Heuristic only -- not a substitute for the human leak
# scan the handoff instructions require before commit.
_SECRET_LIKE_RE = re.compile(r"sk-[A-Za-z0-9]{8,}|Bearer\s+\S+|://[^/\s]+:[^/\s@]+@")
_ALLOWED_AUTH_VALUES = {"none", "key"}

HOTLINES = [
    {"name": "1669 (medical emergency)", "number": "1669"},
    {"name": "1784 (DDPM disaster)", "number": "1784"},
    {"name": "1555 (BMA)", "number": "1555"},
    {"name": "1130 (MEA -- electrical hazard in floods)", "number": "1130"},
    {"name": "Traffy Fondue", "number": "N/A (app/LINE)"},
]

FORWARD_HAZARD_NOTE = (
    "a green/normal current_local_state never clears an active forward_hazard; "
    "read both blocks independently"
)


def _load_build_data_module():
    """Import site/build_data.py's `age_class`/`is_stale`/`STALE_HOURS` by
    file path (it is a script, not a package) rather than reimplementing
    freshness logic here. Raises ImportError loudly if the module cannot be
    loaded -- a silent fallback would be exactly the "second, drifting
    freshness rule" the spec forbids."""
    here = Path(__file__).resolve()
    build_data_path = here.parent.parent.parent / "site" / "build_data.py"
    spec = importlib.util.spec_from_file_location("_floodconnect_build_data", build_data_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load site/build_data.py from {build_data_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_floodconnect_build_data", mod)
    spec.loader.exec_module(mod)
    return mod


@dataclasses.dataclass
class ExportResult:
    files_written: list[str]
    endpoint_count: int
    warnings: list[str]


def _staleness(observed_at: str | None, generated_at_utc: str, build_data_mod, tag: str,
                basis: str | None = None) -> dict[str, Any]:
    """`tag` MUST be one of TAG_VOCABULARY (see module docstring note above it). A
    finer-grained reason goes in the optional `basis` key, never as a sixth tag."""
    if tag not in TAG_VOCABULARY:
        raise ValueError(f"_staleness got a tag outside TAG_VOCABULARY: {tag!r}")
    cls = build_data_mod.age_class(observed_at, generated_at_utc)
    effective_tag = tag if observed_at else "OPEN"
    out: dict[str, Any] = {
        "observed_at": observed_at,
        "fetched_at": generated_at_utc,
        "age_class": cls,
        "tag": effective_tag,
    }
    if basis:
        out["basis"] = basis
    return out


def _write_json(out_dir: Path, rel_path: str, payload: Any, files_written: list[str]) -> None:
    p = out_dir / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    files_written.append(str(p))


def _canal_from_station(station: dict, generated_at_utc: str, build_data_mod) -> dict[str, Any]:
    trend = "OPEN"
    if station.get("delta_m") is not None:
        d = station["delta_m"]
        trend = "rising" if d > 0 else ("falling" if d < 0 else "steady")
    tag = "MEASURED" if station.get("value_m") is not None else "OPEN"
    return {
        "station_code": station.get("code"),
        "level_m": station.get("value_m"),
        "warning_m": station.get("warning"),
        "critical_m": station.get("critical"),
        "bank_m": station.get("bank"),
        "trend": trend,
        "staleness": _staleness(station.get("observed_at"), generated_at_utc, build_data_mod, tag),
    }


def _pump_entry(pump: dict, generated_at_utc: str, build_data_mod) -> dict[str, Any]:
    observed_at = pump.get("observed_at")
    tag = "MEASURED" if pump.get("running") is not None else "OPEN"
    return {
        "id": pump.get("code") or pump.get("id"),
        "running": pump.get("running"),
        "staleness": _staleness(observed_at, generated_at_utc, build_data_mod, tag),
    }


def _contradictions_for_area(cross_source_reconciliation: Any, station_codes: set[str]) -> list[dict]:
    """Both-sides only -- never averaged/merged (founder rule, DEC feedback-
    floodconnect-conflicting-data-rule). `cross_source_reconciliation` (from
    data.json, produced by this repo's own reconcile module) is a list of
    rows already carrying both sides; this just filters to the area's own
    station codes and does not touch the values."""
    rows = []
    if not cross_source_reconciliation:
        return rows
    candidates = cross_source_reconciliation
    if isinstance(candidates, dict):
        candidates = candidates.get("rows") or candidates.get("contradictions") or []
    for row in candidates or []:
        code = row.get("station_code") or row.get("code") or row.get("topic")
        if station_codes and code not in station_codes:
            continue
        rows.append({
            "topic": row.get("topic") or row.get("station_code") or row.get("code"),
            "source_a": row.get("source_a"),
            "value_a": row.get("value_a"),
            "observed_a_utc": row.get("observed_a_utc") or row.get("observed_a"),
            "source_b": row.get("source_b"),
            "value_b": row.get("value_b"),
            "observed_b_utc": row.get("observed_b_utc") or row.get("observed_b"),
            "note": row.get("note"),
            "merged": False,
        })
    return rows


def _build_area_json(area_id: str, ad: dict, data: dict, build_data_mod) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    generated_at_utc = data.get("generated_at_utc") or data.get("generated_at_bkk") or ""

    stations = ad.get("stations_near") or []
    station_codes = {s.get("code") for s in stations if s.get("code")}
    canals = [_canal_from_station(s, generated_at_utc, build_data_mod) for s in stations]

    pumps = [_pump_entry(p, generated_at_utc, build_data_mod) for p in (ad.get("pumps") or [])]

    layer0_area = ((data.get("layer0_public") or {}).get("areas") or {}).get(area_id) or {}
    if not layer0_area:
        warnings.append(f"{area_id}: no layer0_public block found, current_local_state.layer0 is empty/OPEN")

    wb = ad.get("water_balance") or {}
    wb_is_proposal = wb.get("status") not in (None, "REFUSED")
    # Toledo-first: this value comes from a not-yet-registered
    # proposal equation, not an instrument reading -- tag stays OPEN, the reason goes
    # in `basis`, never as a sixth `tag` value (see _staleness docstring).
    water_balance = {
        **wb,
        "staleness": _staleness(generated_at_utc if wb else None, generated_at_utc, build_data_mod, "OPEN",
                                 basis="PROPOSAL-derived" if wb_is_proposal else None),
    }

    rain = ad.get("rain")
    rain_out = None
    if rain:
        # Finding: this used to pass `generated_at_utc` as the
        # observed_at too, so a rain reading taken well before the build run always
        # showed as freshly observed AT build time -- fabricated freshness, not a
        # MEASURED one. Use the reading's own real `observed_at`; if it somehow has
        # none, this is honestly OPEN (never MEASURED), same as the no-rain branch.
        rain_observed_at = rain.get("observed_at")
        rain_out = {**rain, "staleness": _staleness(
            rain_observed_at, generated_at_utc, build_data_mod,
            "MEASURED" if rain_observed_at else "OPEN")}
    else:
        rain_out = {"staleness": _staleness(None, generated_at_utc, build_data_mod, "OPEN")}

    tide = ad.get("tide")
    tide_out = None
    if tide:
        tide_observed_at = tide.get("observed_at")
        tide_out = {**tide, "staleness": _staleness(
            tide_observed_at, generated_at_utc, build_data_mod,
            "MEASURED" if tide_observed_at else "OPEN")}
    else:
        tide_out = {"staleness": _staleness(None, generated_at_utc, build_data_mod, "OPEN")}

    l_tier = {
        "value": ad.get("tiers"),
        "prop_flood_code": "PROP-FLOOD-06",
        "status": "PROPOSAL, unverified",
        "staleness": _staleness(generated_at_utc if ad.get("tiers") else None, generated_at_utc, build_data_mod,
                                 "OPEN", basis="PROPOSAL-derived" if ad.get("tiers") else None),
    }

    # Stale forward_hazard field drop (2026-10-04): guard the EXPORTED JSON itself
    # against baking in a forecast that was already stale at build time (a
    # source can fail a refresh while the rest of the build succeeds). This is
    # independent of `tools/mcp/floodconnect_mcp.py::_recompute_area_freshness`,
    # which re-checks staleness again at MCP-call time against the real
    # wall-clock (this guard only catches "stale when exported"; the MCP layer
    # catches "became stale after export" for anyone fetching the static JSON
    # directly, since a static file cannot recompute itself on every read).
    forecast_in = ad.get("forecast") if isinstance(ad.get("forecast"), dict) else None
    forecast_fetched_at = forecast_in.get("fetched_at") if forecast_in else None
    forecast_age_class = build_data_mod.age_class(forecast_fetched_at, generated_at_utc) \
        if forecast_fetched_at else "expired"
    forecast_stale = forecast_age_class != "fresh"

    contradictions = _contradictions_for_area(data.get("cross_source_reconciliation"), station_codes)

    age_classes = [c["staleness"]["age_class"] for c in canals] or ["expired"]
    order = {"fresh": 0, "stale": 1, "expired": 2}
    overall = max(age_classes, key=lambda a: order.get(a, 2))
    oldest_field = "canals" if canals else "none"

    area_json = {
        "api_version": API_VERSION,
        "generated_at_bkk": data.get("generated_at_bkk"),
        "area_id": area_id,
        "label": ad.get("label"),
        "current_local_state": {
            "water_balance": water_balance,
            "pumps": pumps,
            "layer0": layer0_area,
            "canals": canals,
        },
        "forward_hazard": {
            "forecast": ad.get("forecast"),
            "forecast_short": ad.get("forecast_short"),
            "forecast_72h_worst": ad.get("forecast_72h_worst"),
            "forecast_7day_compare": data.get("forecast_7day_compare"),
            "forecast_caveat_th": data.get("forecast_caveat_th"),
            "note": FORWARD_HAZARD_NOTE,
        },
        "rain": rain_out,
        "tide": tide_out,
        "l_tier": l_tier,
        "contradictions": contradictions,
        "safety": {
            "hotlines": HOTLINES,
            "note": "informational numbers only; this endpoint issues no evacuation order",
        },
        "sources": ad.get("sources") or [],
        "data_freshness": {
            "overall_age_class": overall,
            "oldest_field": oldest_field,
            "computed_via": "reused staleness fn (site/build_data.py:age_class), see FloodConnect API v1 spec sec.1",
        },
    }
    if forecast_stale:
        _suppress_stale_forecast_fields(area_json, forecast_age_class, forecast_fetched_at)
    return area_json, warnings


# Mirrors `tools/mcp/floodconnect_mcp.py::_STALE_FORECAST_FIELDS` /
# `_null_stale_forecast_block` -- duplicated here (not imported) because this
# module runs at BUILD time with no MCP-server import path, and the two call
# sites guard against two different failure modes (see the FIX B comment
# above the `forecast_stale` computation). Keep the two field lists in sync;
# `tests/test_export_api.py` cross-checks them.
_STALE_FORECAST_FIELDS = (
    "direction", "trend_word", "next6h_mm", "next24h_mm", "h24_48_mm", "h48_72_mm",
    "first_dry_6h_start", "items", "hourly", "hourly_full",
)
_STALE_FORECAST_72H_FIELDS = ("value_mm", "model_id", "model_th")
_LAYER0_FORECAST_TAG_TH = "ข่าว/บุคคลที่สาม"
_STALE_TEXT_TH = "[STALE -- ตัวเลขพยากรณ์เก่าถูกระงับ, รัน floodconnect_answer --refresh เพื่อดูค่าสด]"


def _suppress_stale_forecast_fields(area_json: dict, age_class: str, fetched_at: str | None) -> None:
    """Nulls every forward-looking forecast figure/word IN `area_json` itself
    (not a printer) when the forecast was already stale/expired at build
    time. Mutates `area_json` in place -- it is a fresh dict this function
    built, never a shared/cached object."""
    fh = area_json.get("forward_hazard") or {}
    for block_key in ("forecast", "forecast_short"):
        block = fh.get(block_key)
        if isinstance(block, dict):
            for key in _STALE_FORECAST_FIELDS:
                if key in block:
                    block[key] = None
            block["available"] = False
            block["status"] = f"STALE at build time (age_class={age_class}) -- figures suppressed"
    worst = fh.get("forecast_72h_worst")
    if isinstance(worst, dict):
        for key in _STALE_FORECAST_72H_FIELDS:
            if key in worst:
                worst[key] = None
    layer0 = (area_json.get("current_local_state") or {}).get("layer0")
    if isinstance(layer0, dict):
        for items_key in ("in_items", "out_items"):
            for row in layer0.get(items_key) or []:
                if isinstance(row, dict) and row.get("tag_th") == _LAYER0_FORECAST_TAG_TH:
                    row["text_th"] = _STALE_TEXT_TH
        pf06 = layer0.get("prop_flood_06")
        if isinstance(pf06, dict):
            pf06["forecast_72h_worst_text_th"] = _STALE_TEXT_TH
            pf06["forecast_72h_worst_value_mm"] = None
            pf06["forecast_72h_worst_model_th"] = None
            pf06["forecast_72h_items_th"] = None


def _wrap_typology(graph_json: dict, generated_at_bkk: str) -> dict:
    return {"api_version": API_VERSION, "generated_at_bkk": generated_at_bkk, "graph": graph_json}


def _normalize_auth(raw_auth: Any, source_id: str, warnings: list[str]) -> str:
    """Collapse a registry `auth` value to the public enum {'none','key'}.
    `sources/registry.yaml` entries carry free-text notes on this field
    (e.g. "none (User-Agent identification required by ToS, not a key)") --
    real engineering nuance we don't want to lose upstream, but the PUBLIC
    API's `auth` field is restricted to the bare enum (spec sec. 2.3) so an
    external caller can branch on it without parsing prose. Any value that
    looks like it could carry a live secret aborts the build outright,
    never gets normalized away silently."""
    if raw_auth is None:
        return "none"
    text = str(raw_auth).strip()
    if _SECRET_LIKE_RE.search(text):
        raise ValueError(
            f"sources/registry.yaml entry {source_id!r} has auth={raw_auth!r}, which "
            f"looks like it may contain a live credential -- build aborted rather than "
            f"risk emitting a secret."
        )
    if text == "none" or text.startswith("none"):
        if text != "none":
            warnings.append(f"{source_id}: auth note {raw_auth!r} normalized to 'none' for the public API")
        return "none"
    if text == "key" or text.startswith("key") or text == "api_key" or text.startswith("api_key"):
        if text != "key":
            warnings.append(f"{source_id}: auth note {raw_auth!r} normalized to 'key' for the public API")
        return "key"
    if text.upper().startswith("UNKNOWN"):
        # candidate_unregistered rows (no collector wired yet, auth investigation not
        # done -- see registry.yaml's own `kind` field) carry a prose UNKNOWN value.
        # Defaulting to the MORE restrictive public value ("key", i.e. "assume you
        # need a credential, go check") rather than aborting the whole export, and
        # rather than the LESS restrictive "none" -- never guess toward "safer to
        # call", only toward "safer to require a check first".
        warnings.append(f"{source_id}: auth note {raw_auth!r} (not yet investigated) "
                         "defaulted to 'key' for the public API -- never 'none'")
        return "key"
    raise ValueError(
        f"sources/registry.yaml entry {source_id!r} has auth={raw_auth!r}, which is "
        f"outside the allowed enum {_ALLOWED_AUTH_VALUES} and does not start with a "
        f"recognized prefix -- build aborted rather than guess."
    )


def _load_sources_registry(path: Path, warnings: list[str]) -> list[dict]:
    if yaml is None:
        raise ImportError("pyyaml is required to read sources/registry.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("sources") or []
    out = []
    for s in entries:
        agency = s.get("agency") or {}
        host_rule = s.get("host_rule") or {"max_requests_per_run": 1, "note": "one request per URL, no retry loops"}
        if "note" not in host_rule and "notes" in host_rule:
            host_rule = {**host_rule, "note": host_rule["notes"]}
        licence = s.get("licence_status") or {"text": None, "unresolved": True}
        out.append({
            "id": s.get("id"),
            "agency_th": agency.get("th"),
            "agency_en": agency.get("en"),
            "url": s.get("url"),
            "method": s.get("method") or "GET",
            "auth": _normalize_auth(s.get("auth"), s.get("id") or "?", warnings),
            "cadence": s.get("cadence"),
            "format": s.get("format"),
            "host_rule": {
                "max_requests_per_run": host_rule.get("max_requests_per_run", 1),
                "note": host_rule.get("note") or "one request per URL, no retry loops",
            },
            "licence_status": {
                "text": licence.get("text"),
                "unresolved": bool(licence.get("unresolved", True)),
            },
            "trust_tier": s.get("trust_tier"),
            "last_status": s.get("last_status") or {"date": None, "http": None, "note": "not probed by this generator"},
        })
    return out


def _generate_schemas(out_dir: Path, files_written: list[str]) -> None:
    """Minimal-but-real JSON Schema (draft 2020-12) per endpoint -- loose on
    purpose (this generator's own honest OPEN/None values must validate),
    strict on the shape a consumer actually needs: dual-state presence,
    array-of-object endpoints, and the tag/age_class enums."""
    base = "https://json-schema.org/draft/2020-12/schema"
    tag_enum = list(TAG_VOCABULARY)
    age_enum = ["fresh", "stale", "expired"]
    staleness_schema = {
        "type": "object",
        "required": ["observed_at", "fetched_at", "age_class", "tag"],
        "properties": {
            "observed_at": {"type": ["string", "null"]},
            "fetched_at": {"type": ["string", "null"]},
            "age_class": {"enum": age_enum},
            "tag": {"enum": tag_enum},
            "basis": {"type": "string"},
        },
    }

    def w(name: str, schema: dict) -> None:
        schema = {"$schema": base, "$id": f"floodconnect-api-v1/{name}", **schema}
        _write_json(out_dir, f"schema/{name}", schema, files_written)

    w("index.schema.json", {
        "type": "object",
        "required": ["api_version", "generated_at_bkk", "areas", "endpoints"],
        "properties": {
            "api_version": {"type": "string"},
            "areas": {"type": "array", "items": {"type": "string"}},
            "endpoints": {"type": "object"},
        },
    })
    w("area.schema.json", {
        "type": "object",
        "required": ["api_version", "area_id", "current_local_state", "forward_hazard",
                     "contradictions", "safety", "sources", "data_freshness"],
        "properties": {
            "api_version": {"type": "string"},
            "area_id": {"type": "string"},
            "current_local_state": {
                "type": "object",
                "required": ["water_balance", "pumps", "layer0", "canals"],
            },
            "forward_hazard": {"type": "object", "required": ["note"]},
            "contradictions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["topic", "source_a", "value_a", "source_b", "value_b", "merged"],
                    "properties": {"merged": {"const": False}},
                },
            },
            "l_tier": {"type": ["object", "null"]},
            "safety": {"type": "object", "required": ["hotlines", "note"]},
            "sources": {"type": "array"},
            "data_freshness": {
                "type": "object",
                "required": ["overall_age_class", "oldest_field", "computed_via"],
                "properties": {"overall_age_class": {"enum": age_enum}},
            },
        },
        "$defs": {"staleness": staleness_schema},
    })
    w("typology_graph.schema.json", {
        "type": "object",
        "required": ["api_version", "generated_at_bkk", "graph"],
        "properties": {"graph": {"type": "object", "required": ["nodes", "edges"]}},
    })
    w("self_help_dag.schema.json", {
        "type": "object",
        "required": ["api_version", "generated_at_bkk", "schema_status", "nodes", "edges"],
        "properties": {"schema_status": {"type": "string"}},
    })
    w("sources.schema.json", {
        "type": "object",
        "required": ["sources"],
        "properties": {
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "url", "method", "auth", "host_rule", "trust_tier"],
                    "properties": {
                        "auth": {"enum": sorted(_ALLOWED_AUTH_VALUES)},
                        "host_rule": {
                            "type": "object",
                            "required": ["max_requests_per_run", "note"],
                        },
                    },
                },
            },
        },
    })


def _generate_openapi(out_dir: Path, index_endpoints: dict[str, str], files_written: list[str]) -> None:
    lines = [
        "openapi: 3.1.0",
        "info:",
        "  title: FloodConnect API v1",
        "  version: \"1.0.0\"",
        "  description: >-",
        "    Read-only static export of FloodConnect's readout + typology graph +",
        "    self-help DAG + source registry. GET-only. One request per URL, no",
        "    retry loops. UNKNOWN is never SAFE; current_local_state and",
        "    forward_hazard are independent.",
        "servers:",
        "  - url: /api/v1",
        "    description: relative base -- resolve against whatever host serves this export",
        "paths:",
    ]
    schema_map = {
        "area": "area.schema.json",
        "typology_graph": "typology_graph.schema.json",
        "typology_subgraph": "area.schema.json",
        "self_help_dag": "self_help_dag.schema.json",
        "sources": "sources.schema.json",
        "schema": None,
        "openapi": None,
    }
    lines.append("  /index.json:")
    lines.append("    get:")
    lines.append("      operationId: getIndex")
    lines.append("      responses:")
    lines.append("        \"200\":")
    lines.append("          description: API index")
    lines.append("          content:")
    lines.append("            application/json:")
    lines.append("              schema:")
    lines.append("                $ref: \"./schema/index.schema.json\"")
    for name, tmpl in index_endpoints.items():
        schema_file = schema_map.get(name)
        path = "/" + tmpl.replace("/api/v1/", "")
        lines.append(f"  {path}:")
        lines.append("    get:")
        lines.append(f"      operationId: get{name.title().replace('_', '')}")
        lines.append("      responses:")
        lines.append("        \"200\":")
        lines.append("          description: " + name)
        if schema_file:
            lines.append("          content:")
            lines.append("            application/json:")
            lines.append("              schema:")
            lines.append(f"                $ref: \"./schema/{schema_file}\"")
    text = "\n".join(lines) + "\n"
    p = out_dir / "openapi.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    files_written.append(str(p))


def export_api(
    data_json_path: str,
    typology_graph_path: str,
    typology_subgraph_dir: str,
    self_help_dag_path: str,
    sources_registry_path: str,
    out_dir: str,
    generated_at_bkk: str | None = None,
) -> ExportResult:
    build_data_mod = _load_build_data_module()

    data = json.loads(Path(data_json_path).read_text(encoding="utf-8"))
    generated_at_bkk = generated_at_bkk or data.get("generated_at_bkk") or ""
    generated_at_utc = data.get("generated_at_utc")
    if not generated_at_utc and generated_at_bkk:
        try:
            import datetime as _dt
            generated_at_utc = _dt.datetime.fromisoformat(generated_at_bkk).astimezone(_dt.timezone.utc).isoformat()
        except ValueError:
            generated_at_utc = None
    data = {**data, "generated_at_utc": generated_at_utc}

    out = Path(out_dir)
    files_written: list[str] = []
    warnings: list[str] = []

    areas = data.get("areas") or {}
    area_ids = sorted(areas.keys())

    for area_id in area_ids:
        area_json, area_warnings = _build_area_json(area_id, areas[area_id], data, build_data_mod)
        warnings.extend(area_warnings)
        _write_json(out, f"areas/{area_id}.json", area_json, files_written)

    typology_graph_p = Path(typology_graph_path)
    if typology_graph_p.exists():
        graph = json.loads(typology_graph_p.read_text(encoding="utf-8"))
        _write_json(out, "typology/graph.json", _wrap_typology(graph, generated_at_bkk), files_written)
    else:
        warnings.append(f"typology graph not found at {typology_graph_path}, typology/graph.json skipped")

    subgraph_dir = Path(typology_subgraph_dir)
    for area_id in area_ids:
        sub_path = subgraph_dir / f"typology_{area_id}_subgraph.json"
        if sub_path.exists():
            sub = json.loads(sub_path.read_text(encoding="utf-8"))
            _write_json(out, f"typology/subgraph/{area_id}.json", _wrap_typology(sub, generated_at_bkk), files_written)
        else:
            warnings.append(f"{area_id}: no typology subgraph file at {sub_path}, subgraph endpoint skipped")

    dag_p = Path(self_help_dag_path)
    if dag_p.exists() and yaml is not None:
        dag_raw = yaml.safe_load(dag_p.read_text(encoding="utf-8")) or {}
        dag_out = {
            "api_version": API_VERSION,
            "generated_at_bkk": generated_at_bkk,
            "schema_status": dag_raw.get("status"),
            "version": dag_raw.get("version"),
            "layers": dag_raw.get("layers"),
            "nodes": dag_raw.get("nodes"),
            "edges": dag_raw.get("edges"),
        }
        _write_json(out, "community/self_help_dag.json", dag_out, files_written)
    else:
        warnings.append(f"self_help_dag not readable at {self_help_dag_path}, community/self_help_dag.json skipped")

    sources_p = Path(sources_registry_path)
    sources_list: list[dict] = []
    if sources_p.exists():
        sources_list = _load_sources_registry(sources_p, warnings)
        _write_json(out, "sources.json", {"sources": sources_list}, files_written)
    else:
        warnings.append(f"sources registry not found at {sources_registry_path}, sources.json skipped")

    endpoints = {
        "area": "/api/v1/areas/{area_id}.json",
        "typology_graph": "/api/v1/typology/graph.json",
        "typology_subgraph": "/api/v1/typology/subgraph/{area_id}.json",
        "self_help_dag": "/api/v1/community/self_help_dag.json",
        "sources": "/api/v1/sources.json",
        "schema": "/api/v1/schema/{name}.schema.json",
        "openapi": "/api/v1/openapi.yaml",
    }
    index = {
        "api_version": API_VERSION,
        "generated_at_bkk": generated_at_bkk,
        "generated_at_utc": data.get("generated_at_utc"),
        "epistemic_note": "readout, not truth; UNKNOWN is never a verified-safe verdict; "
                           "every value carries source+observed_at+tag",
        "areas": area_ids,
        "endpoints": endpoints,
    }
    _write_json(out, "index.json", index, files_written)

    _generate_schemas(out, files_written)
    _generate_openapi(out, endpoints, files_written)

    return ExportResult(files_written=files_written, endpoint_count=len(files_written), warnings=warnings)


def _cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-json", required=True)
    ap.add_argument("--typology-graph", required=True)
    ap.add_argument("--typology-subgraph-dir", required=True)
    ap.add_argument("--self-help-dag", required=True)
    ap.add_argument("--sources-registry", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    result = export_api(
        data_json_path=args.data_json,
        typology_graph_path=args.typology_graph,
        typology_subgraph_dir=args.typology_subgraph_dir,
        self_help_dag_path=args.self_help_dag,
        sources_registry_path=args.sources_registry,
        out_dir=args.out_dir,
    )
    print(json.dumps({
        "endpoint_count": result.endpoint_count,
        "files_written": len(result.files_written),
        "warnings": result.warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
