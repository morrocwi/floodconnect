# KG_QUERY.md — read the nationwide knowledge graph from git, before anything else

**Mandate (founder ruling 2026-10-04, verbatim): "อย่างแรกให้เอไอต้องอ่านแผนที่กราฟของเราได้
จาก git ก่อนและบังคับว่าต้องหาจาก kggraph นี้ ส่วนจะสกัดย่อออกมาก็อยู่ที่เอไอตัวนั้นเอง" — every
AI session that touches anything basin/province/amphoe/river/station/gate/agency-shaped in
this repo reads `output/thailand_water_kg.graphml` (+ `.jsonld`, same graph in JSON-LD) FIRST,
straight from this git checkout -- never re-derives, re-geocodes, or asks an external map
service for something this file already answers. Extracting a smaller sub-graph for your own
task is your own job; locating the data is not optional.**

Both files are committed directly in git (no Git LFS; each well under the 95 MB cap this repo
works to) — a plain `git clone` is enough, no `raw/` download, no network call, no build step
required to READ them. `output/` is rebuilt from already-committed sources by
`python3 -m tools.kg.build_kg` (see `tools/kg/README.md`) whenever those sources change; this
page is about reading the shipped result, not rebuilding it.

**Honesty note (2026-10-04 regate revision):** every section below states what is MEASURED —
actual coverage numbers from this build, not an aspirational "closed" claim. Several gaps are
genuinely PARTIAL; where they are, this page says so and points at the M2b backlog item that
would close them further, instead of papering over the gap.

## 0. Load it (once per session)

```python
import networkx as nx
G = nx.read_graphml("output/thailand_water_kg.graphml")
print(G.number_of_nodes(), "nodes,", G.number_of_edges(), "edges")
```

Every node and edge carries `tag` (`VERIFIED`/`MEASURED`/`RELAYED`/`INSTINCT`/`OPEN`, plus the
KG-specific extensions `RELAYED-GENERAL`/`VERIFIED-from-official-csv`/
`VERIFIED-from-DWR-service`/`VERIFIED-geometric`/`DERIVED-snap` — see `tools/kg/README.md`'s own
tag table) and `source` — read both before trusting a number; never silently upgrade a tag.

## 1. Walk upstream/downstream from a station or a point (gap 1 — PARTIAL, heuristic)

A gauge/gate/dam/weir/pump/reservoir asset node MAY connect to the river network via an
`ON_REACH` edge to its nearest `river_reach` node — the snap only exists when the nearest
reach's own centroid is within THAT REACH'S OWN `length_km` (never a fixed/invented distance;
see `build_on_reach_edges()` in `tools/kg/build_kg.py`). This is a **nearest-centroid-point
heuristic, not a point-to-polyline measurement** — it was never independently checked, so every
`ON_REACH` edge carries its own fixed tag `DERIVED-snap`, never the snapped asset's own tag (see
`tools/kg/README.md`'s tag table). `rain_gauge` assets are excluded entirely — a rain gauge
measures rainfall at a point, it is not located ON a river reach.

**Measured coverage, this build (785 `ON_REACH` edges total, rain_gauge excluded from the
denominator):**

| asset class | matched | of | coverage |
|---|---:|---:|---:|
| dam | 4 | 86 | 5% |
| gate | 315 | 2,279 | 14% |
| gauge | 251 | 1,231 | 20% |
| pump_station | 117 | 297 | 39% |
| reservoir_medium | 69 | 862 | 8% |
| weir | 29 | 102 | 28% |
| basin / culvert / diversion_channel / levee / pond / reservoir_small / retention_basin / tide_gate / tunnel | 0 | 191 | 0% |

**Most assets nationwide do NOT get an `ON_REACH` edge.** The river network itself is coarse
(2,250 HydroRIVERS reaches at Strahler order ≥ 6 nationwide, plus 8 `river_reach` nodes from
other sources). **A canal-sited station often DOES snap, but to a distant, unreliable
reach** — 250 of the 785 `ON_REACH` edges nationwide are from an asset whose own `name_th`
contains คลอง ("canal"), e.g. `gate:hii_watergate:11` (คลองลาดพร้าว ท้ายปตร.คลอง2) snaps 12.76 km
away, and `gauge:thaiwater_bma:KP03` (คลองเปรมประชากร) snaps 9.44 km away — the heuristic finds
the nearest river-reach POINT regardless of whether a canal, not a river, is what the asset
actually sits on. Measured snap-distance distribution nationwide: median 1.71 km, 100 of 785
edges over 5 km, 34 over 10 km, max 15.71 km. **Treat any `ON_REACH` edge from a canal-named
asset, or any edge with a large implied snap distance, as unreliable for an
upstream/downstream walk** — true point-to-polyline snapping across river AND canal reaches
together is **M2b** (out of scope for this build — see `tools/kg/README.md` "Known gaps").

```python
# which reach is this gauge on, and what's downstream of it?
reach = next(v for u, v, d in G.out_edges("gauge:thaiwater_waterlevel:AIT002", data=True)
             if d.get("kind") == "ON_REACH")
downstream = list(nx.descendants(G.subgraph(
    [n for n, d in G.nodes(data=True) if d.get("kind") == "river_reach"]), reach))
```

(`AIT002` is used here because it genuinely has an `ON_REACH` edge in the shipped graph,
verified against `output/thailand_water_kg.graphml` directly, not assumed. Most gauges do not.)

An asset with no `ON_REACH` edge genuinely has no nearby reach within the data's own
tolerance, or is a rain_gauge, or sits on a canal this heuristic doesn't reach — never snapped
by force; check its own `lat`/`lon` and decide manually.

## 2. Which province/amphoe is a point in (gap 2 — province/amphoe nodes present, point lookup still asset-keyed)

`province:<DOPA code>` and `amphoe:<province_code>-<amphoe_code>` nodes exist nationwide (79
provinces, 735 amphoe) for every distinct value `sources/hii_station_geocode.yaml`'s own HII
geocode harvest observed — not just Bangkok's 50 `district:*` nodes (those stay,
Bangkok-specific, from `sources/bkk_district_elevation.yaml`). **Measured this build:** 5,967
`IN_PROVINCE` + 801 `IN_AMPHOE` edges, from 8,464 source rows — 3,232 source rows (every
`hii_watergate:`/`hii_dam:`-prefixed id) do not match any asset node already in the graph, a
known id-crosswalk gap, no edge created for those.

```python
ptt = G.nodes["province:13"]  # ปทุมธานี -- any DOPA 2-digit code works the same way
amphoe = G.nodes["amphoe:13-01"]  # เมืองปทุมธานี
assets_in_ptt = [u for u, v, d in G.in_edges("province:13", data=True) if d.get("kind") == "IN_PROVINCE"]
```

**This only answers "which province is asset X in" (an id already in the graph).** "Which
province is the bare point (14.0208, 100.5343) in" is NOT answerable from the graph alone yet —
province/amphoe nodes carry no geometry (`lat`/`lon` are both `null`), so nothing resolves a
coordinate to a province node directly. Wiring point → province resolution into
`tools/kg/accountability.py`'s Q1 (nearest geolocated asset's `IN_PROVINCE`, or an admin-polygon
fallback) is **M2b** — see "Known gaps" in `tools/kg/README.md` and gap 6 below.

Two codes in this node family are not real provinces and are kept as their own distinct
nodes, not merged or dropped: `province:99` ("อื่นๆ" / other, HII's own catch-all) and
`province:10499` (a Myanmar cross-border station) — both read verbatim off the source.

## 3. Who is accountable for a NAMED province/basin (gap 3 — wired for a named area node, not yet for a bare point)

`RESPONSIBLE_FOR` edges connect the governance DAG's `AG_*` agency nodes to every
`province:*`/`basin:onwr:*` area node, from `sources/province_agency_crosswalk.yaml`.
**Measured this build:** 257 `RESPONSIBLE_FOR` edges (30 `VERIFIED`, from the crosswalk's 11
province/BMA-area + 2 basin specific rows; 227 `RELAYED-GENERAL`, the generic role template for
every province/basin without its own named DAG row).

```python
responsible = [u for u, v, d in G.in_edges("province:13", data=True)
               if d.get("kind") == "RESPONSIBLE_FOR"]
# -> AG_PROV_GOV_PTT, AG_PROV_RID_PTT, AG_PROV_PAO_PTT  (tag VERIFIED -- a specific DAG node
#    names this exact province)
```

A province/basin with no per-area DAG node of its own gets the GENERIC role node instead
(`AG_PROV_GOV`/`AG_PROV_RID`/`AG_PROV_PAO`/`AG_BASIN_CMT`), tag `RELAYED-GENERAL` — the role is
legally real (`LAW_DISASTER2550` for provinces, the Water Resources Act 2561 for basin
committees) even though the DAG has not yet been given that area's own named node. Check the
edge's own `tag` before treating a generic-role answer as equivalent to a specific one.
`basin:onwr:88` ("นอกประเทศไทย" / outside Thailand, a sentinel) deliberately gets no generic
basin-committee edge — no Thai lum-nam committee governs it.

**This only works starting from a named `province:*`/`basin:onwr:*` node — `python3 -m
tools.kg.accountability --at "<lat,lon>"` for a bare point outside the two MVP areas
(sammakorn/ram53) still refuses** ("no asset node within 3.0 km") unless a geolocated asset
happens to be nearby, because `accountability.py`'s own Q1 never reads `RESPONSIBLE_FOR` or
walks to a province node — only `nearest_assets()`. Wiring that walk in is **M2b** (gap 6, see
`tools/kg/README.md`).

## 4. Which reach is the main stem vs. a tributary (gap 4 — per HydroRIVERS river system, not the Thai per-basin "แม่น้ำสายหลัก")

Every `river_reach` node carries `main_stem` (bool) + `main_stem_basis` (the one-line
derivation). It is a deterministic graph walk over data already in
`output/thailand_river_flow.graphml` (HydroRIVERS' own `main_river_id`/`discharge_avg_cms`/
`dist_to_outlet_km` fields) — never an invented Strahler-order or discharge cutoff. The walk
also restarts on every weakly-connected fragment of the SAME `main_river_id` group a border/clip
gap splits apart (fixed 2026-10-04 — the Mekong's own group splits into 2 such fragments, 983 +
302 reaches, inside this repo's Thailand-bbox extract alone), so a border river's segment still
inside Thailand is not silently left untagged. See `compute_main_stem()` in
`tools/kg/build_kg.py` for the exact walk, and `tests/test_kg_build.py`'s
`test_mekong_reach_near_nong_khai_is_main_stem_on_the_real_graph` for the regression.

**`main_stem` means "lies on the main-stem path of its own HydroRIVERS river system
(`main_river_id` group)" — it is NOT the Thai administrative sense of แม่น้ำสายหลัก (the single
designated main river per ONWR river basin).** Ping, Mun and Chi are `main_stem=False`
because each is a tributary piece INSIDE a larger HydroRIVERS group — Ping inside the Chao
Phraya group, Mun and Chi inside the Mekong group — not because each has its own system. The
Nan river is `main_stem=True` because it is the highest-discharge branch within the SAME
Chao Phraya group that the Chao Phraya reach itself belongs to, not because it is its own
system — a reader expecting the Thai per-basin sense should NOT read `main_stem=True` as "the
one official main river of this ONWR basin", since this measure picks one branch per
HydroRIVERS group by discharge, which need not match the Thai designation. A second,
per-ONWR-basin `basin_main_river` flag (or an explicit crosswalk to the Thai sense) is
**M2b**.

```python
main_stem_reaches = [n for n, d in G.nodes(data=True)
                      if d.get("kind") == "river_reach" and d.get("main_stem") is True]
```

(`main_stem` is declared as a real GraphML `boolean` attribute -- `nx.read_graphml` gives you
back the Python `bool` `True`/`False`, not the string `"true"`; most other attributes in this
graph round-trip as plain strings instead, see `export_graphml()`'s `_sanitize_for_graphml`.)

## 5. Rebuilding (only if you changed a source, not to read the graph)

```bash
python3 -m tools.kg.build_kg --out output/thailand_water_kg
```

Needs `output/thailand_river_flow.graphml` and `output/bangkok_canals.graphml` (both already
committed), a local `data/observations.sqlite` with the `assets` table populated (see
`store.py`; gitignored — a fresh clone that only wants to READ the shipped KG never needs it),
and **`raw/gis/dwr_subbasin/page_*.geojson`** (the archived DWR Sub_Basin polygons, gitignored —
run `python3 -m tools.harvest.dwr_subbasin` first, or copy/symlink an existing archive). Without
that polygon archive the builder **exits non-zero** rather than silently shipping a graph with
zero `IN_SUBBASIN` edges — pass `--allow-missing-subbasin` only if you genuinely intend a
degraded build, and never commit that build's output.
