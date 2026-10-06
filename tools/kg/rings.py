"""tools/kg/rings.py -- P3 ring extraction for the Jev Sandwich model, reading the
committed output/kg_index/ slices (no graphml load, no live network call) -- same
offline-only contract as tools/kg/locate.py, whose cache and haversine helper this
module reuses rather than re-deriving. One exception, added for the verbatim canal-name
join: `_river_name_cache` does ONE cached read of the locally-collected
`data/observations.sqlite` (never a network call) for thaiwater's own `river_name`
field, which was never carried into the committed kg_index -- see that function's own
docstring. It degrades to `{}` with no error when that file does not exist yet.

Scope note (honest, carried from P2's own out_of_scope): output/kg_index/reaches.json
and canals.json (the two GLOBAL slices a global reach/canal graph would need) were not
built in P2 -- `raw/gis/dwr_subbasin/` is absent from this checkout and the canalchain
layer still has no IN_SUBBASIN edges. This module does NOT need either global slice: the
per-province slice already carries each reach's own `r` row (`[so, ms, dn]`, `dn` =
downstream reach id) and every gauge asset's own `reach`/`sb` (sub_basin) columns (see
`tools/kg/build_index.py`), which is enough to walk the reach graph by hand, one province
file at a time, with a per-process cache (same memoization style as `locate.py`'s
`_cache`). What stays genuinely unavailable without the gitignored DWR polygon archive:
`z3["dams"]` (no committed dam-to-sub-basin join yet) and a global `UPSTREAM_PATH` list
across EVERY reach ever (this module only walks the reach chain that is actually present
in the committed slices, bounded by `_MAX_REACH_HOPS`) -- both are returned honestly
empty/bounded rather than guessed, per BOT != ZERO.

The canalchain layer (site/inputs/canals/*.yaml, sources/canalchain_station_joins.yaml)
is declared-only connectivity for the two MVP pond/canal nodes (Sammakorn's pond,
Khlong Ban Ma) -- those two stations already carry a KG `reach`/`sb` via the stations_v1
augment (P2), so they flow through the exact same reach-walk below as any other gauge;
no separate canalchain-specific traversal is needed here.

`rings(lat, lon, area_id=None, index_dir=KG_INDEX_DIR)` returns:
    {"z0": {"id","km","reach","sb","method"} | None,
     "z1": [{"id","relation"}, ...],   # SAME_REACH / DOWNSTREAM_CHAIN / UPSTREAM_CHAIN
     "z2": [{"id","relation"}, ...],   # UPSTREAM_REACH (first gauged reach past an
                                       #   immediate, ungauged neighbour)
     "z3": {"sub_basin": <id>|None, "basin": None, "stations": [{"id","relation"}, ...],
            "dams": [], "official": "NOT_WIRED"}}
`z0=None` (no gauge within radius) degrades every other ring to empty -- the caller
(`kb.py`'s `_answer_sandwich`) reads that as `colour_ladder`'s own UNKNOWN/NO_Z0.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Any

from tools.kg.locate import (  # noqa: E402 -- reuse, never re-derive
    KG_INDEX_DIR, KGIndexMissing, _cache, _load_index, _load_slice_full, haversine_km,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOINS_PATH = os.path.join(REPO_ROOT, "sources", "canalchain_station_joins.yaml")

# BMA canal gauges (bma_watermap / the pre-existing thaiwater_bma Sammakorn/Ram53
# gauges) are answered at the repo's existing 3.0 km canal-gauge radius; a nationwide
# thaiwater_waterlevel river/dam gauge uses the wider nationwide radius -- same two
# constants `readout.py`/`kb.py` already use elsewhere, duplicated here as plain
# floats (this module takes no repo import beyond locate.py, to stay graph-load-free).
BMA_GAUGE_RADIUS_KM = 3.0
NATIONWIDE_RADIUS_KM = 10.0
_MAX_REACH_HOPS = 300  # bounds the Z3 upstream-path walk; a province graph is finite

# Founder ruling 2026-10-06, verbatim: "ทำไงให้ปิดการเดา โดยให้อยู่แค่ใน kg graph
# ให้ตอบใน kg graph เท่านั้น โดยปิดการจำลองโหลดไปเลย" (how do we turn guessing off,
# so the answer stays only inside the KG graph -- and switch simulated load off
# entirely). KG_ONLY_MODE, default ON, is the single switch this module promises:
# every Z1/Z2 row this function would otherwise return is filtered, just before
# `rings()` returns, down to `basis == "declared"` ONLY -- a row from the real
# declared graph (`site/inputs/canals/east_chain.yaml`'s own edges, walked by
# `_east_chain_neighbors`, and the declared canalchain OUTLET_TO target resolved by
# `_canalchain_outlet_station`). Z3 keeps that same `basis == "declared"` filter
# PLUS one exception: rows whose `relation` is `SAME_SUBBASIN` (`sb_basis`
# IN_SUBBASIN/OUTLET_JOIN/SAME_STATION_JOIN -- a shared-polygon/twin grouping,
# never a declared edge between two specific stations) are kept, because
# `kb.py`'s own outlet-consistency check and drainage-area consistency floor
# both read that membership fact; it is never colour-eligible on its own. Every
# OTHER basis this module computes above the filter -- "DERIVED-snap" (the
# ON_REACH geometric snap the reach-walk `_upstream_rings`/
# `_upstream_path_stations` is built on, and the outlet's own name-pattern-guess
# fallback) and "NAME_JOIN"/"NAME_JOIN-heuristic" (the verbatim canal-name and
# code-family joins) -- is a guess this repo makes FOR the caller, not a fact
# the agencies declared, and is dropped here, not merely hidden from colour. A
# station reachable only through one of these dropped bases simply does not
# appear in the ring; the caller (`kb.py`'s `_answer_sandwich`) reads the
# resulting empty ring as UNKNOWN and logs a KG gap, per the same ruling
# ("where the KG lacks an edge, answer UNKNOWN for that ring").
#
# `_FLOODCONNECT_ALLOW_KG_HEURISTICS` is a read-once escape hatch for offline
# research/backtest comparisons ONLY (e.g. measuring how much ring coverage the
# heuristics used to add) -- it is never set in this repo's own answer path, never
# documented as a user-facing toggle, and defaults OFF (heuristics filtered) even
# if the env var is present but not exactly "1".
KG_ONLY_MODE = os.environ.get("_FLOODCONNECT_ALLOW_KG_HEURISTICS") != "1"


def _canal_code_guess(canal_node: str) -> "str | None":
    """`canalchain:ssb08` -> `SSB.08` -- this repo's declared canalchain node ids
    (site/inputs/canals/east_chain.yaml) follow the same lowercase-letters+digits
    pattern as the station codes they represent (e.g. canalchain:ssb08 names the same
    physical canal `WL.SSB.08`/`gauge:thaiwater_bma:WL.SSB.08` already measure --
    see sources/canalchain_station_joins.yaml's own OUTLET_TO evidence). Returns None
    for a canal_node id that doesn't match this pattern (e.g. `sammakorn_pond`,
    `banma`, `wangyai` -- no bare numbered-code twin exists for those; they stay
    OPEN/unreachable from here, same documented gap as the rest of the canalchain
    layer's null-coordinate nodes)."""
    m = re.fullmatch(r"canalchain:([a-z]+)(\d+)", canal_node)
    if not m:
        return None
    return f"WL.{m.group(1).upper()}.{m.group(2)}"


EAST_CHAIN_PATH = os.path.join(REPO_ROOT, "site", "inputs", "canals", "east_chain.yaml")


def _load_east_chain_asset_ids() -> dict[str, str]:
    """`{bare canal node name (e.g. "ssb08"): declared asset_id}` straight from
    `site/inputs/canals/east_chain.yaml`'s own `nodes.<name>.asset_id` field -- 12
    of its 18 nodes declare one, cross-checked against the
    official thaiwater_bma feed at `assets_registry.py build` time, never guessed
    from the node's name string. Returns {} on any read/parse error (optional for
    this module, same degrade-to-absent convention as `_load_canalchain_joins`)."""
    try:
        import yaml
        with open(EAST_CHAIN_PATH, encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, ValueError, ImportError):
        return {}
    out: dict[str, str] = {}
    for name, node in (doc.get("nodes") or {}).items():
        if isinstance(node, dict) and node.get("asset_id"):
            out[name] = node["asset_id"]
    return out


def _load_canalchain_joins() -> dict[str, Any]:
    """Tiny, one-time parse of sources/canalchain_station_joins.yaml (a handful of
    rows -- not the 30 MB KG, no caching concern): {"located_on": {(station_table,
    station_id): canal_node}, "outlet_to": {canal_node: target_canal_node}}. Returns
    both empty on any read/parse error (the file is optional for this module -- a
    missing/malformed joins file degrades Z1's canalchain-outlet relation to simply
    absent, never a crash)."""
    out: dict[str, Any] = {"located_on": {}, "outlet_to": {}}
    try:
        import yaml
        with open(JOINS_PATH, encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, ValueError, ImportError):
        return out
    for j in doc.get("joins", []) or []:
        if j.get("edge") == "LOCATED_ON" and j.get("station_table") and j.get("station_id"):
            out["located_on"][(j["station_table"], j["station_id"])] = j["canal_node"]
        elif j.get("edge") == "OUTLET_TO" and j.get("canal_node") and j.get("target_canal_node"):
            out["outlet_to"][j["canal_node"]] = j["target_canal_node"]
    return out


def _load_east_chain_edges() -> list[dict]:
    """S5: the declared east_chain.yaml edge list, each as {"u","v","design_direction"}
    (canalchain node names, e.g. "banma"/"sammakorn_pond"; design_direction one of
    "u_to_v"/"v_to_u"/"unknown", read verbatim -- never inferred). Returns [] on any
    read/parse error, same degrade-to-absent convention as `_load_canalchain_joins`."""
    try:
        import yaml
        with open(EAST_CHAIN_PATH, encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, ValueError, ImportError):
        return []
    out = []
    for e in doc.get("edges", []) or []:
        if e.get("u") and e.get("v"):
            out.append({"u": e["u"], "v": e["v"],
                        "design_direction": e.get("design_direction", "unknown")})
    return out


_MAX_EAST_CHAIN_HOPS = 6


def _station_located_on(station_id: str, located_on: dict) -> "str | None":
    """Reverse `station_id` (e.g. "gauge:bma_watermap:WL.SMK.01") into the
    (station_table, station_id) key `_load_canalchain_joins`'s `located_on` dict uses,
    and return the declared canal_node, or None if this station has no LOCATED_ON
    join at all."""
    if station_id.count(":") != 2:
        return None
    _, table, code = station_id.split(":", 2)
    return located_on.get((table, code))


def _east_chain_neighbors(z0_id: str, cache: dict, located_on: dict) -> list[dict]:
    """S5 (founder 2026-10-05): walk the declared east_chain.yaml graph outward from
    Z0's own LOCATED_ON canal node (if it has one), up to `_MAX_EAST_CHAIN_HOPS`,
    resolving every OTHER canal node reached back to a gauge id via the REVERSE of
    the same LOCATED_ON join (e.g. canalchain:banma -> gauge:bma_watermap:WL.BMA.02).
    Each hit gets a relation from the edge's own `design_direction` -- "u_to_v" with
    Z0 on `v` (or "v_to_u" with Z0 on `u`) means the neighbour is UPSTREAM_CHAIN
    (declared, not DERIVED-snap); the reverse means DOWNSTREAM_CHAIN; "unknown" (the
    actual state of most of this hand-declared graph, e.g. banma<->sammakorn_pond)
    means SAME_CANAL_DIRECTION_UNKNOWN -- per the founder's rule, a declared-but-
    undirected edge is never promoted to a direction. Every row's basis is
    "declared" (this IS the maintainer's own stated graph, site/inputs/canals/
    east_chain.yaml -- never DERIVED-snap)."""
    z0_node = _station_located_on(z0_id, located_on)
    if not z0_node:
        return []
    # east_chain.yaml's own edges use bare node names ("banma", "sammakorn_pond"),
    # while `located_on` (sources/canalchain_station_joins.yaml) stores the
    # "canalchain:"-prefixed form -- strip it before walking `adj` below.
    if z0_node.startswith("canalchain:"):
        z0_node = z0_node[len("canalchain:"):]
    edges = _load_east_chain_edges()
    adj: dict[str, list[tuple[str, str]]] = {}  # node -> [(neighbor, relation)]
    for e in edges:
        u, v, dd = e["u"], e["v"], e["design_direction"]
        if dd == "u_to_v":
            adj.setdefault(u, []).append((v, "DOWNSTREAM_CHAIN"))
            adj.setdefault(v, []).append((u, "UPSTREAM_CHAIN"))
        elif dd == "v_to_u":
            adj.setdefault(v, []).append((u, "DOWNSTREAM_CHAIN"))
            adj.setdefault(u, []).append((v, "UPSTREAM_CHAIN"))
        else:
            adj.setdefault(u, []).append((v, "SAME_CANAL_DIRECTION_UNKNOWN"))
            adj.setdefault(v, []).append((u, "SAME_CANAL_DIRECTION_UNKNOWN"))
    reverse_located_on = {}
    for (table, code), node in located_on.items():
        bare_node = node[len("canalchain:"):] if node.startswith("canalchain:") else node
        reverse_located_on.setdefault(bare_node, []).append((table, code))
    out: list[dict] = []
    visited = {z0_node}
    frontier = [z0_node]
    hops = 0
    while frontier and hops < _MAX_EAST_CHAIN_HOPS:
        hops += 1
        nxt = []
        for node in frontier:
            for neighbor, relation in adj.get(node, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                nxt.append(neighbor)
                for table, code in reverse_located_on.get(neighbor, []):
                    for prefix in ("gauge:", "gate:", "pump_station:"):
                        candidate = f"{prefix}{table}:{code}"
                        if candidate in cache["stations"] and candidate != z0_id:
                            out.append({"id": candidate, "relation": relation,
                                        "basis": "declared"})
        frontier = nxt
    return out


def _canalchain_outlet_station(z0_id: str, cache: dict) -> "dict | None":
    """Z0's declared canalchain OUTLET_TO target, resolved back to a gauge id already
    present in this KG, or None if Z0 has no LOCATED_ON join, no OUTLET_TO target, or
    the target resolves to no known gauge.

    Resolution order: the target canal node's own DECLARED
    `asset_id` in `site/inputs/canals/east_chain.yaml` (`basis="declared"`) is tried
    FIRST -- that is the maintainer's own cross-checked statement of which KG asset
    this canal node IS, never a string guess. Only when no node declares one (the 6
    `canal_oldcode: null` nodes, e.g. `sammakorn_pond`/`banma`) does this fall back to
    `_canal_code_guess`'s name-pattern guess (`basis="DERIVED-snap"`, matching the
    tag `tools/kg/stations_layer.py`'s own `ON_REACH` snap uses for the same kind of
    inferred-not-declared join). Among a guessed code's candidate prefixes, the
    `gauge:bma_watermap:`/`gauge:thaiwater_waterlevel:` M8 twin (this run's own
    directly-read source) is preferred over the older `thaiwater_bma`/`gate` one."""
    joins = _load_canalchain_joins()
    if not z0_id.startswith("gauge:"):
        return None
    _, table, code = z0_id.split(":", 2)
    canal_node = joins["located_on"].get((table, code))
    if canal_node is None:
        return None
    target = joins["outlet_to"].get(canal_node)
    if target is None:
        return None
    bare_name = target.split(":", 1)[1] if ":" in target else target
    declared = _load_east_chain_asset_ids().get(bare_name)
    # S4: OUTLET is declared connectivity (the maintainer's own east_chain.yaml
    # statement of which station is downstream of Z0), but it is a drainage
    # CONSTRAINT, not an upstream confirmation -- it contradicts the "water coming
    # toward us" reading a reach/UPSTREAM relation would give, so it is tagged
    # `contradicts: True` with a `ref` back to the declaring file (never silently
    # folded into an UPSTREAM_CHAIN-shaped row). S3: prefer the readable M8 twin of
    # the declared id over the unreadable `thaiwater_bma`/`gate` one when both exist.
    if declared and declared in cache["stations"]:
        resolved = _prefer_readable_twin(declared, cache)
        # `sb_source_id` keeps the ORIGINAL (pre-twin) id for `rings()`'s own
        # sb/OUTLET_JOIN lookup below: the readable M8 twin usually has no
        # IN_SUBBASIN placement of its own (same documented gap `SAME_STATION_JOIN`
        # exists for), while the pre-existing `declared` id does -- swapping the
        # displayed `id` to the readable twin must never also lose that placement.
        return {"id": resolved, "relation": "OUTLET", "basis": "declared",
                "contradicts": True, "ref": "site/inputs/canals/east_chain.yaml",
                "sb_source_id": declared}
    target_code = _canal_code_guess(target)
    if target_code is None:
        return None
    for prefix in ("gauge:bma_watermap:", "gauge:thaiwater_waterlevel:",
                   "gauge:thaiwater_bma:", "gate:thaiwater_bma:"):
        candidate = f"{prefix}{target_code}"
        if candidate in cache["stations"]:
            return {"id": candidate, "relation": "OUTLET", "basis": "DERIVED-snap",
                    "contradicts": True, "ref": "site/inputs/canals/east_chain.yaml",
                    "sb_source_id": candidate}
    return None


_SAME_STATION_PREFIXES = ("gauge:bma_watermap:", "gauge:thaiwater_waterlevel:")
_SAME_STATION_TWIN_PREFIXES = ("gauge:thaiwater_bma:", "gate:thaiwater_bma:")


def _is_readable_prefix(station_id: str) -> bool:
    """True iff `station_id` is on one of the two M8 nationwide-source prefixes this
    module/`kb.py` can actually read a reading for (`_SANDWICH_SOURCE_BY_PREFIX` in
    `kb.py`) -- the pre-existing `gauge:thaiwater_bma:`/`gate:thaiwater_bma:` prefix
    has no M8 reader and answers `NO_READING` for any id on it ."""
    return station_id.startswith(_SAME_STATION_PREFIXES)


def _prefer_readable_twin(station_id: str, cache: dict) -> str:
    """S3 (founder 2026-10-05): when a station id resolves to an unreadable
    `gauge:thaiwater_bma:`/`gate:thaiwater_bma:` node that has a same-agency-code
    `SAME_STATION` twin on a readable M8 prefix already present in this KG, return
    the twin's id instead -- never the unreadable one, when a readable one exists.
    Returns `station_id` unchanged when it is already readable, isn't a `gauge:` id,
    or has no readable twin in this KG."""
    if _is_readable_prefix(station_id) or not station_id.startswith("gauge:"):
        return station_id
    for old_prefix in _SAME_STATION_TWIN_PREFIXES:
        if station_id.startswith(old_prefix):
            code = station_id[len(old_prefix):]
            for new_prefix in _SAME_STATION_PREFIXES:
                candidate = f"{new_prefix}{code}"
                if candidate in cache["stations"]:
                    return candidate
    return station_id


def _dedup_ids_prefer_readable(ids) -> list[str]:
    """De-duplicate an iterable of gauge ids by their bare agency code (the part
    after the last `:`), keeping the readable M8-prefix id over an unreadable
    `thaiwater_bma`/`gate` twin when both carry the same code (same fix as
    `_prefer_readable_twin`, applied to a whole ring's worth of ids at once -- a
    reach/sub-basin membership list built from `cache["stations"]` keys can contain
    BOTH the old and the new M8 node for the same physical station, see this
    module's own `_reach_cache`, which keeps every distinct asset id)."""
    best: dict[str, str] = {}
    order: list[str] = []
    for aid in ids:
        code = aid.rsplit(":", 1)[-1]
        if code not in best:
            best[code] = aid
            order.append(code)
        elif _is_readable_prefix(aid) and not _is_readable_prefix(best[code]):
            best[code] = aid
    return [best[c] for c in order]


def _same_station_twin(station_id: str, cache: dict) -> "str | None":
    """The M8 `stations_v1` `SAME_STATION` edge is built by exact agency-code match
    (`tools/kg/stations_layer.py`, `method="agency_code_exact"`) between a new
    `gauge:bma_watermap:*`/`gauge:thaiwater_waterlevel:*` node and an existing
    `gauge:thaiwater_bma:*`/`gate:thaiwater_bma:*` one that carries the SAME code.
    The per-province kg_index slice this module reads has no edge list at all (see
    module docstring), so this re-derives the same exact-code match stations_layer.py
    already made, rather than walking an edge this slice format cannot carry -- never
    a second, different matching rule. Returns None when `station_id` isn't on one
    of the two M8 node prefixes, or no twin with the same code exists in this KG."""
    for prefix in _SAME_STATION_PREFIXES:
        if station_id.startswith(prefix):
            code = station_id[len(prefix):]
            for twin_prefix in _SAME_STATION_TWIN_PREFIXES:
                candidate = f"{twin_prefix}{code}"
                if candidate in cache["stations"]:
                    return candidate
            return None
    return None


_CANAL_FAMILY_SENSOR_PREFIXES = ("WL.", "RF.", "ST.")
_MAX_CANAL_FAMILY_ROWS = 20  # per family, per ring() call -- token-budget cap


def _canal_family(station_id: str) -> "str | None":
    """S5 (founder 2026-10-05, "น้ำเหนือเราไม่มีสถานีได้ไงหละ ลาก node ไป kg graph"):
    a heuristic NAME-JOIN family key for a gauge id -- the alphabetic canal/site code
    shared by every gauge the agency placed on the same named canal, independent of
    whether build_kg.py's ON_REACH/IN_SUBBASIN snap ever joined them onto the same
    reach/sub-basin row. Examples (verified against this repo's own committed station
    names, 2026-10-05): "gauge:thaiwater_bma:WL.SSB.08" (คลองแสนแสบ) -> "SSB", every
    other WL.SSB.* (.01 through .13) shares it; "gauge:bma_watermap:WL.BMA.02"
    (คลองบ้านม้า) -> "BMA"; "gauge:thaiwater_waterlevel:C.67" (Chao Phraya chainage) ->
    "C", shared by C.2/C.3/C.12/.../C.67. The "WL."/"RF."/"ST." prefix is the agency's
    SENSOR-TYPE marker (water level / rainfall / stage), not part of the canal name,
    and is stripped first. Returns None for a bare code with no leading letters (never
    guessed from the station's free-text Thai name -- this is a code-family join, not
    a fuzzy name match, exactly because free-text matching risks silently merging two
    different canals that happen to share a word)."""
    if ":" not in station_id:
        return None
    bare = station_id.rsplit(":", 1)[-1]
    for pfx in _CANAL_FAMILY_SENSOR_PREFIXES:
        if bare.startswith(pfx):
            bare = bare[len(pfx):]
            break
    m = re.match(r"^([A-Za-z]+)", bare)
    if not m:
        return None
    family = m.group(1)
    # A single bare letter with no further structure (rare; e.g. a stray "A01") is too
    # unspecific to trust as a canal-family join -- require at least 1 char, but this
    # module still skips any family whose membership list has only 1 station (nothing
    # to join), handled at the call site instead of here.
    return family


def _station_source(station_id: str) -> "str | None":
    """The agency/source segment of a `"gauge:<source>:<code>"` id (e.g.
    "thaiwater_waterlevel", "thaiwater_bma", "bma_watermap"). `None` for an id with
    no second segment."""
    parts = station_id.split(":")
    return parts[1] if len(parts) > 2 else None


def _canal_family_cache(index_dir: str) -> "dict[tuple[str, str], list[str]]":
    """Build-once-per-process: {(source, family): [gauge ids sharing that family
    WITHIN THE SAME AGENCY SOURCE, nationwide]} -- the S5 NAME-JOIN index, built
    from the SAME nationwide `stations` dict `_reach_cache` already loads (no
    second KG read).

    fix (S1, founder subtractive-fix ruling 2026-10-06): the family key is now
    `(source, family)`, never a bare `family` string -- a bare code-prefix
    collides across agencies that happen to use the same letters for an unrelated
    canal (MEASURED: BMA's `gauge:thaiwater_bma:WL.BBU.01`, คลองบางบัว, and plain
    thaiwater's `gauge:thaiwater_waterlevel:BBU01`/`BBU02`, แม่น้ำปิง, 453-546 km
    away, both reduce to family "BBU" once the sensor-type prefix is stripped).
    "Never join across agencies on a code prefix" (founder instruction) -- this is
    that guard."""
    key = f"rings_canal_family_cache_v2::{index_dir}"
    if key in _cache:
        return _cache[key]
    cache = _reach_cache(index_dir)
    fam: "dict[tuple[str, str], list[str]]" = {}
    for aid, d in cache["stations"].items():
        if d.get("k") != "gauge" or aid.startswith("gauge:thaiwater_rain:"):
            continue
        f = _canal_family(aid)
        src = _station_source(aid)
        if f and src:
            fam.setdefault((src, f), []).append(aid)
    _cache[key] = fam
    return fam


# -- Verbatim canal-name join (replaces a bare code-family assumption as the basis for
# a "same canal" claim) --------------------------------------------------------------
# `_canal_family` above groups by the agency's CODE prefix only (e.g. "BKK"), which one
# physical agency placed across many DIFFERENT named canals (BKK003 is on
# คลองมหาสวัสดิ์, BKK005 is on คลองภาษีเจริญ -- not the same canal at all). A code
# family is only trustworthy as "same canal" when every member actually names the SAME
# canal; this section reads that verbatim name and builds the real join on it. thaiwater
# publishes it as its own `river_name` field (relayed into `provenance_json` by
# `collect.collect_thaiwater_waterlevel`, not carried into the committed kg_index -- see
# `_river_name_cache` below); BMA has no separate field for it, but already writes it as
# a "คลอง"/"ค."/"ส." - prefixed token inside the station's own `name_th` (e.g.
# "ค.แสนแสบ-โบ๊เบ๊"), read straight off the committed index with no DB at all.
_CANAL_NAME_TOKEN_RE = re.compile(r"(?:คลอง|ค\.|ส\.คลอง|ส\.)\s*([ก-๙]{2,})")


def _canal_name_token(text: "str | None") -> "str | None":
    """One verbatim canal-name token out of a free-text Thai string (a station's own
    `name_th`, or the agency's own `river_name`) -- `None` when no "คลอง"/"ค."/"ส."
    marker is found at all (never a guess off the rest of the string). Case/mark-exact
    (no normalisation) -- a near-miss spelling (e.g. a final tone mark present on one
    source and absent on the other) deliberately fails to join rather than risk a false
    "same canal" merge; this only ever LOSES a real match, never invents one."""
    if not text:
        return None
    m = _CANAL_NAME_TOKEN_RE.search(text)
    return m.group(1) if m else None


def _river_name_db_path() -> str:
    return os.path.join(REPO_ROOT, "data", "observations.sqlite")


def _river_name_cache(index_dir: str) -> dict[str, str]:
    """{gauge id ("gauge:thaiwater_waterlevel:<code>"): agency `river_name` verbatim}
    -- ONE cached read of the committed-at-runtime `data/observations.sqlite`'s most
    recent `thaiwater_waterlevel` provenance per station code (the only source this
    module reads `river_name` for; BMA's canal name already lives in its own `name_th`,
    read with no DB at all -- see `_canal_name_token`). This is the one place in this
    module that is NOT purely the committed `output/kg_index/` slice: `river_name` was
    never carried into that index (`tools/kg/build_index.py`'s own `a_cols`), only into
    the observations store's `provenance_json`. Degrades to `{}` (never guessed, never
    raises) when the DB file does not exist yet (a fresh checkout, an offline test) or
    any row fails to parse -- a caller then simply has no river_name for that station
    and the canal join falls back to whatever `name_th` alone can parse."""
    key = f"rings_river_name_cache::{index_dir}"
    if key in _cache:
        return _cache[key]
    out: dict[str, str] = {}
    db_path = _river_name_db_path()
    if os.path.exists(db_path):
        # fix: this read-only pass must never leave behind a WAL/SHM side file that
        # was not already there (the live DB is opened in WAL mode by `store.py`'s
        # own writer, and even a plain read-only `sqlite3.connect` against a
        # WAL-mode DB creates `<db>-wal`/`<db>-shm` the first time anything touches
        # it) -- MEASURED: this tripped this workspace's own test-isolation guard
        # ("ADDED: data/observations.sqlite-shm/-wal") on a test that reads the
        # real committed DB directly. `-wal`/`-shm` paths that already existed
        # before this call (a live run, or `store.py` mid-write) are left exactly
        # alone; only ones this call itself created are removed again afterward.
        _wal_path, _shm_path = db_path + "-wal", db_path + "-shm"
        _had_wal, _had_shm = os.path.exists(_wal_path), os.path.exists(_shm_path)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                cur = conn.execute(
                    "select station_code, provenance_json from observations "
                    "where source_id='thaiwater_waterlevel' and provenance_json is not null "
                    "order by observed_at_utc asc")
                for code, prov_json in cur.fetchall():
                    if not code:
                        continue
                    try:
                        river = json.loads(prov_json).get("river_name")
                    except (TypeError, ValueError):
                        river = None
                    if river:
                        out[f"gauge:thaiwater_waterlevel:{code}"] = river.strip()
            finally:
                conn.close()
                if not _had_wal and os.path.exists(_wal_path):
                    try:
                        os.remove(_wal_path)
                    except OSError:
                        pass
                if not _had_shm and os.path.exists(_shm_path):
                    try:
                        os.remove(_shm_path)
                    except OSError:
                        pass
        except sqlite3.Error:
            out = {}
    _cache[key] = out
    return out


def _station_canal_name(station_id: str, cache: dict, river_names: dict[str, str]) -> "str | None":
    """The one verbatim canal-name token this module can read for `station_id`:
    thaiwater's own `river_name` (via `_river_name_cache`) takes priority when present
    (it is the agency's dedicated field for exactly this), else whatever
    `_canal_name_token` can parse out of the station's own committed `name_th`.

    Fix: a dedicated agency `river_name` is used
    VERBATIM, never re-run through `_canal_name_token`'s "คลอง"/"ค."/"ส." regex --
    that regex exists only to pull a canal-name token out of a free-text place name
    (BMA's `name_th`), and it silently returned None for a perfectly good agency-given
    name that happens not to start with one of those three words (e.g. thaiwater's own
    "แม่น้ำเลย", "ห้วยน้ำฮวย", "น้ำพอง", "ลำพะเนียง") -- a None then got discarded by
    every caller's `member_names.discard(None)`, which let an ANY-prefix-length code
    family with only ONE *parsed* name (even though its members plainly name different
    real canals/rivers) pass as a genuine same-canal claim. Measured regression:
    AIT001 (river_name "คลองแสนแสบ", Bangkok) was joined to AIT002 ("แม่น้ำเลย", Loei,
    ~471 km away) and AIT003 ("ห้วยน้ำฮวย") as SAME_CANAL_DIRECTION_UNKNOWN purely
    because AIT002/AIT003's names never matched the regex. Using the dedicated field
    verbatim makes all three distinct strings, which correctly demotes the "AIT" code
    family to SAME_CODE_FAMILY (ambiguous) instead of a false same-canal label -- see
    `tests/test_rings.py::test_ait00x_code_family_is_not_a_false_same_canal_join`."""
    river = river_names.get(station_id)
    if river:
        text = river.strip()
        if text:
            return text
    return _canal_name_token(cache["stations"].get(station_id, {}).get("n"))


def _canal_name_cache(index_dir: str) -> dict[str, list[str]]:
    """Build-once-per-process: {verbatim canal-name token: [gauge ids on that same
    named canal, nationwide, ANY agency/code]} -- the real "same canal" join (as
    opposed to `_canal_family_cache`'s same-CODE-prefix guess), built from
    `_station_canal_name` over the same nationwide `stations` dict `_reach_cache`
    already loads, plus the one cached `river_name` read."""
    key = f"rings_canal_name_cache::{index_dir}"
    if key in _cache:
        return _cache[key]
    cache = _reach_cache(index_dir)
    river_names = _river_name_cache(index_dir)
    fam: dict[str, list[str]] = {}
    for aid, d in cache["stations"].items():
        if d.get("k") != "gauge" or aid.startswith("gauge:thaiwater_rain:"):
            continue
        name = _station_canal_name(aid, cache, river_names)
        if name:
            fam.setdefault(name, []).append(aid)
    _cache[key] = fam
    return fam


def _reach_cache(index_dir: str) -> dict[str, Any]:
    """Build-once-per-process: {stations: {id: row_dict}, reach_meta: {reach:
    {so,ms,dn}}, reach_stations: {reach: [ids]}, sb_stations: {sb: [ids]},
    reach_up: {dn_reach: [upstream reach ids]}}. Cached in locate.py's own `_cache`
    dict (same module-level memoization it already uses for index/slice reads), keyed
    by index_dir so a test pointed at a fixture dir never collides with the real one."""
    key = f"rings_reach_cache::{index_dir}"
    if key in _cache:
        return _cache[key]
    index = _load_index(index_dir)
    stations: dict[str, dict] = {}
    reach_meta: dict[str, dict] = {}
    for code, meta in index["prov"].items():
        sl = _load_slice_full(index_dir, meta)
        cols = sl["a_cols"]
        for row in sl["a"]:
            d = dict(zip(cols, row))
            aid = d["id"]
            # Prefer an edge-linked (pv="e") copy over a box/nearest placement
            # (pv="b"/"n") if the same asset id appears in more than one
            # province's slice -- same precedence `locate.py` gives IN_PROVINCE
            # over its own box/nearest fallbacks.
            if aid not in stations or (d.get("pv") == "e" and stations[aid].get("pv") != "e"):
                stations[aid] = d
        for reach, r in sl.get("r", {}).items():
            if reach not in reach_meta:
                so, ms, dn = r
                reach_meta[reach] = {"so": so, "ms": ms, "dn": dn}
    reach_stations: dict[str, list] = {}
    sb_stations: dict[str, list] = {}
    for aid, d in stations.items():
        if d.get("k") != "gauge":
            continue
        if aid.startswith("gauge:thaiwater_rain:"):
            # Mislabelled rain-only gauges (GLOBAL_GAPS, build_index.py) -- never a
            # water-level ring member.
            continue
        reach = d.get("reach")
        if reach:
            reach_stations.setdefault(reach, []).append(aid)
        sb = d.get("sb")
        if sb:
            sb_stations.setdefault(sb, []).append(aid)
    reach_up: dict[str, list] = {}
    for reach, m in reach_meta.items():
        dn = m.get("dn")
        if dn:
            reach_up.setdefault(dn, []).append(reach)
    cache = {
        "stations": stations, "reach_meta": reach_meta,
        "reach_stations": reach_stations, "sb_stations": sb_stations,
        "reach_up": reach_up,
    }
    _cache[key] = cache
    return cache


def _nearest_gauge(lat: float, lon: float, cache: dict) -> dict | None:
    """fix (S3): a `gauge:bma_watermap:`/`gauge:thaiwater_waterlevel:`
    M8 node and its pre-existing `gauge:thaiwater_bma:`/`gate:thaiwater_bma:`
    SAME_STATION twin sit at the SAME declared lat/lon (same physical station, two
    KG asset ids), so they tie on distance. Dict-iteration order alone used to
    decide which one won that tie, and the unreadable twin sometimes won it (215/311
    BMA stations regressed to NO_Z0_READING, MEASURED 2026-10-05). The sort key is
    now (distance rounded to 2 dp -- a 10 m tolerance, well under any real
    duplicate-placement gap -- then a readable-prefix rank), so a tie always prefers
    the id `kb.py`'s `_sandwich_station_reading` can actually read."""
    best = None  # (round(km,2), rank)
    best_row = None
    for aid, d in cache["stations"].items():
        if d.get("k") != "gauge" or aid.startswith("gauge:thaiwater_rain:"):
            continue
        slat, slon = d.get("lat"), d.get("lon")
        if slat is None or slon is None:
            continue
        km = haversine_km(lat, lon, slat, slon)
        is_bma_canal = aid.startswith("gauge:bma_watermap:") or aid.startswith("gauge:thaiwater_bma:")
        cap = BMA_GAUGE_RADIUS_KM if is_bma_canal else NATIONWIDE_RADIUS_KM
        if km > cap:
            continue
        rank = 0 if _is_readable_prefix(aid) else 1
        key = (round(km, 2), rank)
        if best is None or key < best:
            best = key
            best_row = (aid, km, d)
    if best_row is None:
        return None
    aid, km, d = best_row
    return {"id": aid, "km": round(km, 3), "reach": d.get("reach"), "sb": d.get("sb"),
            "method": "nearest_gauge"}


def _upstream_rings(reach: str | None, exclude_id: str, cache: dict) -> tuple[list, list]:
    """Z1 (one hop: DOWNSTREAM_CHAIN on `dn`, UPSTREAM_CHAIN on any immediate upstream
    reach that already has a gauge) and Z2 (continue past an immediate, UNGAUGED
    upstream reach until the first reach that does have a gauge, per branch -- a
    structural stop, no numeric hop cap beyond `_MAX_REACH_HOPS` as a finiteness
    guard against a malformed/cyclic `dn` chain, which should never occur in a real
    DAG but must never hang this function if it did)."""
    z1: list[dict] = []
    z2: list[dict] = []
    if not reach:
        return z1, z2
    meta = cache["reach_meta"].get(reach, {})
    dn = meta.get("dn")
    if dn:
        for s in _dedup_ids_prefer_readable(
                s for s in cache["reach_stations"].get(dn, []) if s != exclude_id):
            z1.append({"id": s, "relation": "DOWNSTREAM_CHAIN"})
    same = _dedup_ids_prefer_readable(
        s for s in cache["reach_stations"].get(reach, []) if s != exclude_id)
    for s in same:
        z1.append({"id": s, "relation": "SAME_REACH"})
    for up_r in cache["reach_up"].get(reach, []):
        stations = _dedup_ids_prefer_readable(
            s for s in cache["reach_stations"].get(up_r, []) if s != exclude_id)
        if stations:
            for s in stations:
                z1.append({"id": s, "relation": "UPSTREAM_CHAIN"})
            continue
        frontier = list(cache["reach_up"].get(up_r, []))
        visited = {reach, up_r} | set(frontier)
        hops = 0
        while frontier and hops < _MAX_REACH_HOPS:
            hops += 1
            nxt: list[str] = []
            for r in frontier:
                st = _dedup_ids_prefer_readable(
                    s for s in cache["reach_stations"].get(r, []) if s != exclude_id)
                if st:
                    for s in st:
                        z2.append({"id": s, "relation": "UPSTREAM_REACH"})
                else:
                    for up2 in cache["reach_up"].get(r, []):
                        if up2 not in visited:
                            visited.add(up2)
                            nxt.append(up2)
            frontier = nxt
    return z1, z2


def _upstream_path_stations(reach: str | None, exclude_id: str, cache: dict) -> set[str]:
    """Every gauge reachable by walking the full upstream reach chain from `reach`
    (bounded by `_MAX_REACH_HOPS`) -- used only to tag a Z3 sub-basin station
    UPSTREAM_PATH vs plain SAME_SUBBASIN, restricting the
    sandwich's RISING-triggers-top_alert scope to UPSTREAM_PATH, not every station in
    a 15,689 km^2 sub-basin)."""
    out: set[str] = set()
    if not reach:
        return out
    frontier = [reach]
    visited = {reach}
    hops = 0
    while frontier and hops < _MAX_REACH_HOPS:
        hops += 1
        nxt: list[str] = []
        for r in frontier:
            for s in cache["reach_stations"].get(r, []):
                if s != exclude_id:
                    out.add(s)
            for up in cache["reach_up"].get(r, []):
                if up not in visited:
                    visited.add(up)
                    nxt.append(up)
        frontier = nxt
    return set(_dedup_ids_prefer_readable(out))


def rings(lat: float, lon: float, area_id: str | None = None,
          index_dir: str = KG_INDEX_DIR) -> dict[str, Any]:
    """See module docstring. Never raises `KGIndexMissing` itself -- a caller that
    wants to distinguish "no KG index at all" from "no gauge within radius" should
    call `tools.kg.locate.locate`/`_load_index` first (as `kb.py`'s `_kg_anchor`
    already does) and only call this after confirming the index is readable."""
    cache = _reach_cache(index_dir)
    z0 = _nearest_gauge(lat, lon, cache)
    if z0 is None:
        return {"z0": None, "z1": [], "z2": [],
                "z3": {"sub_basin": None, "sb_basis": None, "basin": None,
                       "stations": [], "dams": [], "official": "NOT_WIRED"}}
    exclude = z0["id"]
    z1, z2 = _upstream_rings(z0.get("reach"), exclude, cache)
    outlet = _canalchain_outlet_station(exclude, cache)
    # S5: declared east_chain.yaml branch connections (e.g. banma -> sammakorn_pond,
    # design_direction "unknown") that the reach-snap walk above never sees, because
    # Z0 (e.g. WL.SMK.01) has no ON_REACH placement of its own -- see module
    # docstring's own documented gap. UPSTREAM_CHAIN/DOWNSTREAM_CHAIN hits here join
    # Z1 exactly like a reach-walk hit of the same relation name; a
    # SAME_CANAL_DIRECTION_UNKNOWN hit also joins Z1 (it is within the hand-declared
    # branch graph, inherently "near us"), never silently dropped for lack of a
    # direction.
    _located_on = _load_canalchain_joins()["located_on"]
    for _ec_row in _east_chain_neighbors(exclude, cache, _located_on):
        if _ec_row["id"] not in {r["id"] for r in z1}:
            z1.append(_ec_row)
    # fix: tag every z1/z2 row with its great-circle distance from
    # Z0 (`dist_km`, DERIVED-haversine), never a reach-graph hop count, so a caller
    # that must cap a long middle list (e.g. `kb.py`'s `_SANDWICH_MIDDLE_CAP`) can
    # sort the toward-us relations (UPSTREAM_CHAIN/UPSTREAM_REACH) by distance
    # before capping, instead of reading whichever rows the reach walk happened to
    # append first (that walk is DOWNSTREAM_CHAIN-first, see `_upstream_rings`).
    z0_lat, z0_lon = z0.get("lat"), z0.get("lon")
    if z0_lat is None or z0_lon is None:
        z0_row = cache["stations"].get(exclude, {})
        z0_lat, z0_lon = z0_row.get("lat"), z0_row.get("lon")
    for _row in (z1 + z2):
        _st = cache["stations"].get(_row["id"], {})
        _slat, _slon = _st.get("lat"), _st.get("lon")
        if z0_lat is not None and z0_lon is not None and _slat is not None and _slon is not None:
            _row["dist_km"] = round(haversine_km(z0_lat, z0_lon, _slat, _slon), 3)
        else:
            _row["dist_km"] = None
        # fix (S4): basis is set by RELATION, never from a
        # station's own `pv` (`pv` only says how THAT station got placed in a
        # province -- an IN_PROVINCE edge -- it says nothing about the reach join
        # that put it on this ring). Every relation `_upstream_rings` ever emits
        # (SAME_REACH/DOWNSTREAM_CHAIN/UPSTREAM_CHAIN/UPSTREAM_REACH) is a reach-walk
        # on the `reach` column, which `build_index.py` fills only from ON_REACH
        # edges that `build_kg.py` tags `DERIVED-snap` -- so every such row is
        # `DERIVED-snap`, unconditionally. An OUTLET row never reaches this loop (it
        # is appended to z1 AFTER this loop runs) and keeps the basis
        # `_canalchain_outlet_station` already set (declared, with its own
        # `contradicts`/`ref`).
        _row.setdefault("basis", "DERIVED-snap")
    sb_basis = "IN_SUBBASIN"
    sb_for_z3 = z0.get("sb")  # Z0's own dict is never mutated -- `z0["sb"]` always
                              # stays this station's own real IN_SUBBASIN placement
                              # (None here, honestly, when it has none); Z3's basin
                              # membership below may still use an inherited value.
    if outlet is not None and outlet["id"] != exclude and outlet["id"] not in {r["id"] for r in z1}:
        z1.append(outlet)
        # Z0 itself carries no IN_SUBBASIN edge (pv='b', no DWR polygon archive in this
        # checkout -- see tools/kg/stations_layer.py's own docstring); the declared
        # canalchain OUTLET_TO target DOES have one (its own thaiwater_bma twin), so
        # Z3's sub-basin membership is read off that outlet station instead, tagged
        # `sb_basis="OUTLET_JOIN"` so a caller never mistakes this for a direct
        # geometric placement of Z0 itself.
        if not sb_for_z3:
            outlet_sb = cache["stations"].get(
                outlet.get("sb_source_id", outlet["id"]), {}).get("sb")
            if outlet_sb:
                sb_for_z3 = outlet_sb
                sb_basis = "OUTLET_JOIN"
    # fix: most M8 `stations_v1` nodes (bma_watermap/
    # thaiwater_waterlevel) have no IN_SUBBASIN placement of their own (same
    # documented gap as OUTLET_JOIN above), which otherwise degrades Z3 to empty
    # for them and the sandwich answer to TOP_UNREAD across most of the country.
    # When Z0 still has no sb after the OUTLET_JOIN attempt, inherit it from the
    # SAME_STATION twin (the pre-existing thaiwater_bma/gate node with the same
    # agency code) instead, tagged `sb_basis="SAME_STATION_JOIN"` so a caller never
    # mistakes this for a direct geometric placement of Z0 itself.
    if not sb_for_z3:
        twin_id = _same_station_twin(exclude, cache)
        if twin_id:
            twin_sb = cache["stations"].get(twin_id, {}).get("sb")
            if twin_sb:
                sb_for_z3 = twin_sb
                sb_basis = "SAME_STATION_JOIN"
    seen = {r["id"] for r in z1} | {r["id"] for r in z2} | {exclude}
    # S5 full-KG NAME-JOIN walk (founder 2026-10-05): a declared OUTLET or a reach
    # join only ever gives the ON_REACH-snapped slice of a canal (build_kg.py's own
    # documented gap). The agency's own code family (e.g. every WL.SSB.* on
    # คลองแสนแสบ) finds the REST of that same canal even when it never snapped onto
    # Z0's reach -- this is exactly "ลาก node ไป kg graph ก็เจอคลองสำคัญ" (drag the
    # node through the KG graph, you find the important canal). Direction along a
    # name-joined canal is NOT declared anywhere this module reads, so every row gets
    # relation SAME_CANAL_DIRECTION_UNKNOWN (never UPSTREAM/DOWNSTREAM) -- the
    # caller/answer must never claim "water coming" purely from one of these rows
    # (S5's own rule), though a fresh RED one is still carried as a fact exactly like
    # any other Z1/Z2 row.
    #
    # Two separate joins, never conflated (fix, this revision -- a bare code-prefix
    # match previously stood in for "same canal" on its own, which is false whenever
    # one agency code spans more than one physical canal, e.g. "BKK" covers
    # คลองลาดพร้าว/คลองมหาสวัสดิ์/คลองภาษีเจริญ/... as separate stations):
    #   1. `_canal_name_cache` -- the real join, on the agency's own VERBATIM canal
    #      name (thaiwater `river_name`, or a "คลอง"/"ค."/"ส."-prefixed token already
    #      inside BMA's own `name_th`) -- basis stays "NAME_JOIN", relation stays
    #      SAME_CANAL_DIRECTION_UNKNOWN, because this IS a same-canal claim. This is
    #      the join that reaches a station on a different agency code sharing the
    #      same real canal (e.g. thaiwater's AIT001, river_name คลองแสนแสบ, joining
    #      Sammakorn's WL.SSB.* family even though its own code "AIT" never matches
    #      "SSB").
    #   2. `_canal_family_cache` -- the old bare code-prefix guess, kept ONLY as a
    #      fallback for a member neither of the two canal-name reads above could
    #      parse a token for. Accepted as a genuine same-canal claim ONLY when EVERY
    #      member of that code family that DOES have a parseable canal name shares
    #      the exact same one; otherwise the whole family is ambiguous (BKK's four
    #      different real canals, measured 2026-10-05) and is labelled relation
    #      "SAME_CODE_FAMILY" / basis "NAME_JOIN-heuristic" instead -- never
    #      SAME_CANAL_DIRECTION_UNKNOWN, never "NAME_JOIN" on its own, so a caller can
    #      never mistake an ambiguous code-family hit for a same-canal claim.
    # Walked from Z0's own canal-name/code-family AND the OUTLET's (when found) so
    # both "our own canal, beyond the snapped reach" and "the outlet canal, beyond the
    # one declared station" are covered. Every candidate is sorted nearest-first by
    # `dist_km` BEFORE `_MAX_CANAL_FAMILY_ROWS` caps the list (fix -- the cut used to
    # be alphabetical-by-id, which can silently drop the nearest real member of a
    # large family).
    river_names = _river_name_cache(index_dir)
    canal_cache = _canal_name_cache(index_dir)
    fam_cache = _canal_family_cache(index_dir)
    seed_ids = [exclude] + ([outlet["id"]] if outlet is not None else [])

    # fix (S1, founder subtractive-fix ruling 2026-10-06): demote a SAME_REACH row
    # when both ends have a known, declared agency canal/river name and they
    # disagree -- the KG's own ON_REACH snap placed them on the same reach, but
    # their own agencies' names say they are not the same water (MEASURED
    # examples: Y.64 แม่น้ำยม snapped onto N.5A's แม่น้ำน่าน reach; CPY014
    # แม่น้ำเจ้าพระยา onto BKK001/BKK020's คลองหกวา reach; CPY004 onto THA001's
    # แม่น้ำท่าจีน reach). The relation becomes SAME_REACH_RIVER_MISMATCH -- still
    # shown as a fact with its true label, never colour-eligible (see
    # `floodconnect_model.is_colour_eligible`). A row with an unknown name on
    # either side is left as plain SAME_REACH (nothing declared to disagree with).
    _z0_river = _station_canal_name(exclude, cache, river_names)
    if _z0_river is not None:
        for _row in z1:
            if _row.get("relation") != "SAME_REACH":
                continue
            _member_river = _station_canal_name(_row["id"], cache, river_names)
            if _member_river is not None and _member_river != _z0_river:
                _row["relation"] = "SAME_REACH_RIVER_MISMATCH"

    def _dist_km_for(sid: str) -> "float | None":
        _st = cache["stations"].get(sid, {})
        _slat, _slon = _st.get("lat"), _st.get("lon")
        if z0_lat is not None and z0_lon is not None and _slat is not None and _slon is not None:
            return round(haversine_km(z0_lat, z0_lon, _slat, _slon), 3)
        return None

    joined: dict[str, dict] = {}  # id -> row, built up before the distance cap

    canal_names = {n for n in (_station_canal_name(sid, cache, river_names) for sid in seed_ids) if n}
    for name in canal_names:
        for s in canal_cache.get(name, []):
            if s in seen or s in joined:
                continue
            joined[s] = {"id": s, "relation": "SAME_CANAL_DIRECTION_UNKNOWN",
                         "basis": "NAME_JOIN", "canal_name": name}

    code_families = {(src, f) for src, f in
                     ((_station_source(sid), _canal_family(sid)) for sid in seed_ids)
                     if src and f}
    for fam_key in code_families:
        _src, fam = fam_key
        members = fam_cache.get(fam_key, [])
        if len(members) < 2:
            continue
        member_names = [_station_canal_name(m, cache, river_names) for m in members]
        # fix (S1, founder subtractive-fix ruling 2026-10-06): accept the whole
        # family as a real same-canal claim only when EVERY member has a
        # non-null agency river name AND all of them are equal -- a family with
        # even one member whose name is unknown, or whose members disagree, is
        # NOT a declared same-canal claim (the prior `len(member_names) <= 1`
        # test wrongly accepted the all-unknown case too, which is "nothing
        # declared", not "declared and agreeing"). Examples this now refuses to
        # accept: BBD04 (แม่น้ำปิง) with BBD05 (ห้วยแม่ท้อ)/BBD09/BBD10 (แม่น้ำวัง);
        # any family where some members simply have no observation row yet.
        if all(n is not None for n in member_names) and len(set(member_names)) == 1:
            relation, basis = "SAME_CANAL_DIRECTION_UNKNOWN", "NAME_JOIN"
        else:
            relation, basis = "SAME_CODE_FAMILY", "NAME_JOIN-heuristic"
        for s in members:
            if s in seen or s in joined:
                continue
            joined[s] = {"id": s, "relation": relation, "basis": basis, "canal_family": fam}

    ordered_ids = _dedup_ids_prefer_readable(
        sorted(joined, key=lambda sid: (_dist_km_for(sid) is None, _dist_km_for(sid) or 0.0)))
    added = 0
    for s in ordered_ids:
        if added >= _MAX_CANAL_FAMILY_ROWS:
            break
        if s in seen:
            continue
        seen.add(s)
        added += 1
        row = dict(joined[s])
        row["dist_km"] = _dist_km_for(s)
        # Near-radius rows join Z1 ("canals near us"); the rest of the same
        # family (further along the same named canal) join Z2 ("water area
        # above us" layer) -- an honest distance-based split, never a claim
        # about direction (S1b: layers are reported, direction is not implied).
        if row["dist_km"] is not None and row["dist_km"] <= BMA_GAUGE_RADIUS_KM * 3:
            z1.append(row)
        else:
            z2.append(row)
    upstream_path = _upstream_path_stations(z0.get("reach"), exclude, cache)
    z3_stations: list[dict] = []
    for s in sorted(upstream_path):
        if s in seen:
            continue
        seen.add(s)
        # fix (S4): UPSTREAM_PATH is a reach-chain walk (same basis as
        # every z1/z2 reach relation above) -- DERIVED-snap always, never read off
        # a station's own unrelated `pv` (IN_PROVINCE) field.
        z3_stations.append({"id": s, "relation": "UPSTREAM_PATH", "basis": "DERIVED-snap"})
    sb = sb_for_z3
    if sb:
        for s in sorted(_dedup_ids_prefer_readable(cache["sb_stations"].get(sb, []))):
            if s in seen:
                continue
            seen.add(s)
            # fix (S4): SAME_SUBBASIN membership comes from whichever
            # IN_SUBBASIN-family join actually supplied `sb_for_z3` above
            # (`sb_basis`: IN_SUBBASIN direct / OUTLET_JOIN / SAME_STATION_JOIN) --
            # that edge's own tag, never a station's unrelated `pv` field.
            z3_stations.append({"id": s, "relation": "SAME_SUBBASIN", "basis": sb_basis})
    # fix : every Z3 row now also carries `dist_km` (DERIVED-haversine
    # from Z0, same convention z1/z2 rows already have), so a caller that must cap a
    # long facts list (`kb.py`'s `_SANDWICH_FACTS_CAP`) can sort RED facts by
    # relation-then-distance before capping, instead of taking whichever rows
    # happened to sort first alphabetically by id (Ayutthaya's real near-miss: C.67,
    # SAME_SUBBASIN and ~4-5 km away, used to lose to the alphabetically-earlier but
    # 8-11 km-downstream BKC002/BKC003).
    for _row in z3_stations:
        _st = cache["stations"].get(_row["id"], {})
        _slat, _slon = _st.get("lat"), _st.get("lon")
        if z0_lat is not None and z0_lon is not None and _slat is not None and _slon is not None:
            _row["dist_km"] = round(haversine_km(z0_lat, z0_lon, _slat, _slon), 3)
        else:
            _row["dist_km"] = None

    z3_sub_basin, z3_sb_basis = sb, (sb_basis if sb else None)
    if KG_ONLY_MODE:
        # KG-only filter (see KG_ONLY_MODE's own docstring above): keep ONLY
        # (a) the declared east_chain.yaml edges and the declared canalchain
        # OUTLET_TO target (basis "declared"), and (b) the SAME_SUBBASIN
        # membership rows -- NOT a station-to-station guess at all, just a
        # "both inside the same agency-declared sub-basin polygon" fact, kept
        # specifically because `kb.py`'s own founder-declared "เจ้าพระยาคือ
        # ทางออก" outlet-consistency mechanism and the drainage-area
        # consistency floor both read it (never colour-eligible on its own --
        # `kb.py` already excludes plain SAME_SUBBASIN from the layer colour).
        # Every OTHER basis this module computes -- "DERIVED-snap" (the
        # reach-walk SAME_REACH/UPSTREAM_CHAIN/UPSTREAM_REACH/DOWNSTREAM_CHAIN/
        # UPSTREAM_PATH rows, and the outlet's own name-pattern-guess
        # fallback), "NAME_JOIN"/"NAME_JOIN-heuristic" -- is a guessed relation
        # between two SPECIFIC stations and is dropped here, not merely from
        # colour eligibility.
        z1 = [r for r in z1 if r.get("basis") == "declared"]
        z2 = [r for r in z2 if r.get("basis") == "declared"]
        z3_stations = [r for r in z3_stations
                        if r.get("basis") == "declared" or r.get("relation") == "SAME_SUBBASIN"]

    return {
        "z0": z0, "z1": z1, "z2": z2,
        "z3": {"sub_basin": z3_sub_basin, "sb_basis": z3_sb_basis, "basin": None,
               "stations": z3_stations, "dams": [], "official": "NOT_WIRED"},
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin CLI
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="rings")
    parser.add_argument("--at", required=True, help="lat,lon")
    args = parser.parse_args(argv)
    lat_s, lon_s = args.at.split(",")
    try:
        result = rings(float(lat_s), float(lon_s))
    except KGIndexMissing as exc:
        print(json.dumps({"error": "kg index missing", "detail": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main(sys.argv[1:]))
