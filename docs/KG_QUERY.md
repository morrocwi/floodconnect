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

## 0. Load it (once per session)

```python
import networkx as nx
G = nx.read_graphml("output/thailand_water_kg.graphml")
print(G.number_of_nodes(), "nodes,", G.number_of_edges(), "edges")
```

Every node and edge carries `tag` (`VERIFIED`/`MEASURED`/`RELAYED`/`INSTINCT`/`OPEN`, plus the
KG-specific extensions `RELAYED-GENERAL`/`VERIFIED-from-official-csv`/
`VERIFIED-from-DWR-service`/`VERIFIED-geometric` — see `tools/kg/README.md`'s own tag table)
and `source` — read both before trusting a number; never silently upgrade a tag.

## 1. Walk upstream/downstream from a station or a point (gap 1, closed 2026-10-04)

A gauge/gate/dam asset node connects to the river network via an `ON_REACH` edge to its
nearest `river_reach` node — the snap only exists when the nearest reach is within THAT
REACH'S OWN `length_km` (never a fixed/invented distance; see `build_on_reach_edges()` in
`tools/kg/build_kg.py`). From the reach, `WATER` edges (direction = HydroSHEDS `next_down`)
walk you downstream; the reverse walk is upstream.

```python
# which reach is this gauge on, and what's downstream of it?
reach = next(v for u, v, d in G.out_edges("gauge:thaiwater_waterlevel:AIT002", data=True)
             if d.get("kind") == "ON_REACH")
downstream = list(nx.descendants(G.subgraph(
    [n for n, d in G.nodes(data=True) if d.get("kind") == "river_reach"]), reach))
```

(Not every gauge gets an `ON_REACH` edge — only those within their nearest reach's own
`length_km` tolerance; `AIT002` is used here because it genuinely has one in the shipped
graph, verified against `output/thailand_water_kg.graphml` directly, not assumed.)

An asset with no `ON_REACH` edge genuinely has no nearby reach within the data's own
tolerance — never snapped by force; check its own `lat`/`lon` and decide manually.

## 2. Which province/amphoe is a point in (gap 2, closed 2026-10-04)

`province:<DOPA code>` and `amphoe:<province_code>-<amphoe_code>` nodes now exist for every
distinct value `sources/hii_station_geocode.yaml`'s own HII geocode harvest observed — not
just Bangkok's 50 `district:*` nodes (those stay, Bangkok-specific, from
`sources/bkk_district_elevation.yaml`). An asset gets an `IN_PROVINCE`/`IN_AMPHOE` edge only
where its own `asset_id` already matches a node in the graph (see that edge's own `source`
for which harvester row produced it).

```python
ptt = G.nodes["province:13"]  # ปทุมธานี -- any DOPA 2-digit code works the same way
amphoe = G.nodes["amphoe:13-01"]  # เมืองปทุมธานี
assets_in_ptt = [u for u, v, d in G.in_edges("province:13", data=True) if d.get("kind") == "IN_PROVINCE"]
```

Two codes in this node family are not real provinces and are kept as their own distinct
nodes, not merged or dropped: `province:99` ("อื่นๆ" / other, HII's own catch-all) and
`province:10499` (a Myanmar cross-border station) — both read verbatim off the source.

## 3. Who is accountable for a province/basin (gap 3, closed 2026-10-04)

`RESPONSIBLE_FOR` edges now connect the governance DAG's `AG_*` agency nodes to every
`province:*`/`basin:onwr:*` area node, from `sources/province_agency_crosswalk.yaml`:

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

## 4. Which reach is the main stem vs. a tributary (gap 4, closed 2026-10-04)

Every `river_reach` node carries `main_stem` (bool) + `main_stem_basis` (the one-line
derivation). It is a deterministic graph walk over data already in
`output/thailand_river_flow.graphml` (HydroRIVERS' own `main_river_id`/`discharge_avg_cms`/
`dist_to_outlet_km` fields) — never an invented Strahler-order or discharge cutoff. See
`compute_main_stem()` in `tools/kg/build_kg.py` for the exact walk.

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
committed) and a local `data/observations.sqlite` with the `assets` table populated (see
`store.py`; this file is gitignored — a fresh clone that only wants to READ the shipped KG
never needs it).
