# Nationwide water knowledge graph (PHASE 3, build 7 as of 2026-10-04)

One combined graph over everything this repo already knows, with no new geocoding,
no new equations, and no geometric inference added by this step.

## Build

```
python3 -m tools.kg.build_kg --out output/thailand_water_kg
```

Writes `output/thailand_water_kg.graphml` and `output/thailand_water_kg.jsonld`. **Requires
`raw/gis/dwr_subbasin/page_*.geojson`** (the archived DWR Sub_Basin polygons, gitignored --
run `python3 -m tools.harvest.dwr_subbasin` first, or copy/symlink an existing archive) --
the builder **exits non-zero** when that archive is absent, rather than silently shipping a
graph with zero `IN_SUBBASIN` edges (review finding HIGH-1, 2026-10-04); pass
`--allow-missing-subbasin` only for a deliberately degraded build, and never commit one.
Reads from (never writes to, except its two output files):

- `data/observations.sqlite` (`assets`, `readout_log` tables via `store.py` -- now 9,403
  asset rows across all classes, nationwide, see counts below)
- `output/thailand_river_flow.graphml` (HydroRIVERS, already clipped to Thailand)
- `output/bangkok_canals.graphml` (OSM heuristic canal survey)
- `site/inputs/canals/east_chain.yaml` (declared canal chain)
- `docs/knowledge/water_system_dag.mmd` (239-node governance DAG, incl. `LAW_*` nodes,
  `AUTHORIZES`/`CONSTRAINS` edges, and the 2026-09-27 TIER-0..4 nationwide hierarchy
  subgraph -- dams, C.2/C.13, mid-river provinces, basin committees; all ingested by the
  same generic prefix-based loader, no code change needed for the tiers themselves)
- `sources/api_census.yaml` (data-feed census)
- `sources/wikipedia_canals.yaml` (190 Wikipedia canal records -- `canal` nodes, `WATER`
  edges only where upstream/downstream resolve by exact name match, `SAME_AS_CANDIDATE`
  edges to the file's own declared `matches`, never a merge)
- `docs/knowledge/edge_problems.yaml` (120 rows -- attached to the matching DAG edge as
  `problem_academic`/`problem_tag`/`problem_sources`, or, where no edge exists, recorded
  as a node-level `missing_edge_problem` attribute; +12 rows added 2026-09-27, build 2,
  HANDOFF/CASE_LESSON/INTERPROVINCIAL_CONFLICT)
- `docs/knowledge/node_attributes.yaml` (added 2026-09-27, wired into `build_river_kg.py` build 2
  same day via `apply_node_attributes()` -- `de_facto_authority`/evidence/note attached
  directly onto the matching DAG node, fail-loud `MissingNodeError` if a node id no longer
  exists)
- `sources/owner_agency_crosswalk.yaml` (added 2026-09-27, wired into `build_river_kg.py` build 2
  same day via `load_owner_agency_crosswalk()`/`build_owned_by_agency_edges()` -- `VERIFIED`
  rows only become `OWNED_BY_AGENCY` edges asset -> `AG_*` node; `OPEN` rows left unlinked)
- `sources/bma_drain_pipes.yaml` (added 2026-09-27, build 3 -- founder ask 17:08 "เอาเลย
  สร้าง floodconnect topology จากสิ่งที่เรามี". Produced by
  `tools/harvest/bma_drain_pipes.py` from the two already-archived BMA Open Data CSVs,
  `raw/live/bma_open_data_drainage_org/drain_pipe_full.csv` (2,903 rows, cp874 encoded)
  and `.../pipe_jacking_full.csv` (13 rows, UTF-8, real UTM47N coordinates). Wired via
  `load_bma_drain_pipes()` -> `drain_segment`/`drain_junction` nodes + `DRAINS_TO` edges,
  explicit `PIPE_FROM`/`PIPE_TO` topology only, no geocoding)
- `sources/bkk_district_elevation.yaml` (added 2026-09-27, build 3 -- 50-row RTSD-2010
  map-sample per Bangkok เขต. Wired via `load_bkk_districts()` -> `district` geo-nodes
  (25 with a real elevation reading, 25 `OPEN`) + `IN_DISTRICT` edges from
  `drain_segment` nodes and from asset `notes` fields carrying `"district: <name>"`)
- `sources/capacity_ledger.yaml` (added 2026-09-27, build 4 -- 68-row system-wide
  drainage/discharge capacity ledger, dam-spillway to canal/tunnel/pump/gate to river/sea
  outfall). Wired via `apply_capacity_ledger()` -- attaches `capacity_*`-prefixed
  attributes onto the matching node (an existing DAG `AS_*` node, an existing sqlite
  asset_id node, or a brand-new `capacity_ledger_node`-kind node when neither exists),
  plus `OUTFALL` edges (pump/tunnel/gate -> the outfall row it discharges into) and
  `CAPACITY_OF` edges (a row -> a `river_reach`-kind row it names) -- both derived only
  by regexing the ledger's own already-written `source`/`notes` text for another id
  already written there, never geometric/inferred)
- `sources/bma_drain_pipes.yaml`'s `sump_wells` list (13 rows, real WGS84 coordinates;
  present since build 3 but not wired into the graph until build 4). Wired via
  `load_sump_wells()`/`build_sump_well_district_edges()` -> `sump_well` nodes + an
  `IN_DISTRICT` edge where the row's own English district name exact-matches a
  `district` node's `name_en` (never fuzzy))

The repo's raw global HydroRIVERS shapefile/parquet is never touched -- only the
already-clipped `output/*.graphml` derivatives (a few MB each). Peak RSS observed on
this build: ~170 MB (well under the 1.5 GB budget); each graphml is dropped
(`del` + `gc.collect()`) before the next source loads.

## Node schema

| field | meaning |
|---|---|
| `kind` | `asset` / `river_reach` / `canal_node` / `canal` / `agency` / `data_feed` / `asset_class` / `governance_dag` / `dag_asset` / `decision` / `channel` / `affected_people` / `law` / `drain_segment` / `drain_junction` / `district` (build 3) / `capacity_ledger_node` / `sump_well` (last two added build 4) / `sub_basin` (build 6) / `province` / `amphoe` (build 7) |
| `class` | asset class (`gauge`, `gate`, `pump_station`, `dam`, `tunnel`, `pond`, `culvert`, `rain_gauge`, `basin`, `retention_basin`, `levee`, `diversion_channel`, `tide_gate`) for asset nodes; `canal` for Wikipedia-sourced canal nodes (a separate node family from `canal_node`, which is the OSM/declared-chain family); `governance_dag` for every DAG-sourced node (agency/decision/channel/law/etc, which the DAG's own prefix already distinguishes via `kind`); `drain_segment` / `drain_junction` (build 3, BMA drain-pipe CSV -- one segment node per (CSV row, R/L/ROAD/PJ side), one junction node per distinct PIPE_FROM/PIPE_TO street/canal name); `district` (build 3, geography -- distinct from the governance-DAG's `AG_DIST_SS` office/authority node, see `docs/FLOODCONNECT_TOPOLOGY.md`); for `capacity_ledger_node` (build 4, only on a brand-new node with no existing asset_id/DAG id), `class` is the ledger's own `kind` string verbatim (e.g. `dam_spillway`/`diversion`/`floodway_canal`/`outfall`) -- not remapped to the asset-class vocabulary; `sump_well` (build 4) |
| `name_th` | Thai label, where the source has one |
| `lat`/`lon` | may be `null` for `OPEN` rows -- never geocoded, never inferred (`drain_segment`/`drain_junction`/`district`/`capacity_ledger_node` nodes are always `null` here -- no coordinate anywhere in their source; `sump_well` nodes DO carry real WGS84 coordinates, converted from the source's own UTM47N numbers in build 3's harvester, first wired as graph nodes in build 4) |
| `owner` | asset nodes only, verbatim from the assets table |
| `tag` | `VERIFIED` / `RELAYED` / `RELAYED-GENERAL` / `OPEN` / `VERIFIED-from-official-csv` (build 3 -- fetched directly from an official agency CSV, independently checked, but carries no coordinate at all; kept distinct from plain `VERIFIED` so a reader never conflates "official source" with "has a real lat/lon") / `VERIFIED-from-DWR-service` (build 6, `sub_basin` nodes) / `VERIFIED-geometric` (build 6, `IN_SUBBASIN` edges -- real point-in-polygon against an official DWR polygon) / `DERIVED-snap` (build 7, `ON_REACH` edges ONLY -- a nearest-centroid-point heuristic, never checked, so it is NEVER the snapped asset's own tag, see "Edge schema" below), exactly as the source states -- **never upgraded**. A `capacity_ledger_node` created in build 4 carries the ledger row's own tag as its ONE tag (it has no other source); an EXISTING node that a build-4 ledger row attaches onto keeps its own original `tag` unchanged -- the ledger row's tag is stored separately as `capacity_tag` (see below), never overwriting the node's own provenance tag |
| `source` | which file/table produced this node |
| `latest_value`/`latest_ts`/`latest_run_id` | asset nodes only; see "Latest-readout linkage" below |
| `capacity_value` / `capacity_unit` / `capacity_m3s` / `capacity_basis` / `capacity_tag` / `capacity_year_of_statement` / `capacity_source` / `capacity_current_value_this_week` / `capacity_observed_at` | build 4, from `sources/capacity_ledger.yaml` -- attached onto ANY node whose id matches a ledger row's `id` (existing or newly created); `capacity_m3s` is populated only when the ledger row's `unit` is `m3s`, else `null` (raw value/unit are still kept in `capacity_value`/`capacity_unit`, e.g. the design-rainfall row's `mm_per_day`) |
| `discharges_to` / `outfall_bank` / `gravity_threshold` | build 4, `kind: outfall` ledger rows only, copied verbatim from `sources/capacity_ledger.yaml` |
| `district_en` / `power_kw` / `coord_source` | build 4, `sump_well` nodes only, from `sources/bma_drain_pipes.yaml`'s `sump_wells` list |
| `drainage_unit` | build 4, `"candidate"` on every `basin` and `district` node -- a bare marker for PROP-FLOOD-06's future 22-basin unit framing, no computation performed |

Governance-DAG nodes (`AG_*`/`AS_*`/`DT_*`/`DC_*`/`CH_*`/`PP_*`) carry `tag: null` --
`water_system_dag.mmd` tags its **edges**, not its nodes. See "Known gaps".

## Edge schema

Every edge carries `kind`, `source`, `tag`.

| kind | meaning | source(s) |
|---|---|---|
| `WATER` | flow direction/adjacency | HydroRIVERS `flowsInto`, OSM canal graph, the declared canal chain, DAG `WATER:*` edges |
| `OWNS` | agency/entity owns an asset or another entity | assets table `owner` field; DAG `OWNS:*` edges |
| `DATA` | a feed covers an asset class (or, in the DAG, a telemetry node feeds a physical node) | `sources/api_census.yaml`; DAG `DATA:*` edges |
| `COMMANDS` | governance chain of command (mermaid `CMD:*`, renamed `COMMANDS` per this check's spec) | `water_system_dag.mmd` only |
| `LOCATED_ON` | an asset sits at a declared canal-chain reach position | `site/inputs/canals/east_chain.yaml`'s own explicit `asset_id` field on a node -- **never geometrically snapped or inferred** |
| `FUNDS` / `INFORMS` / `POWER` / `SHARES` | carried through unchanged from the governance DAG | `water_system_dag.mmd` |
| `AUTHORIZES` / `CONSTRAINS` | a law creates/empowers, or limits, an agency | `water_system_dag.mmd` (`LAW_*` node edges, added 2026-09-27) |
| `IN_BASIN` | an asset's own registry row names the ONWR river basin it falls in | `assets` table `notes` field (`"basin: <name>"`, from HII census harvests), matched by exact `name_th` to a `basin`-class asset node -- never geocoded/inferred |
| `SAME_AS_CANDIDATE` | a Wikipedia canal record's own declared `matches` list names a possible same-structure asset | `sources/wikipedia_canals.yaml` -- **a candidate only, never merged/collapsed** into one node |
| `OWNED_BY_AGENCY` | an asset's `owner` string crosswalks, `VERIFIED`, to a governance-DAG `AG_*` node | `sources/owner_agency_crosswalk.yaml` -- added 2026-09-27, build 2; `OPEN` crosswalk rows produce no edge (never fuzzy-matched) |
| `DRAINS_TO` | drain-segment -> junction, junction -> drain-segment, and (where the junction's normalised name exact-matches an existing canal name) junction -> canal node | `sources/bma_drain_pipes.yaml` -- build 3, added 2026-09-27; wired only where `PIPE_FROM`/`PIPE_TO` is non-empty in the source row, canal match via `normalize_canal_name()` against a combined canal/canal_node/OSM-edge-name index, **never geometric** |
| `IN_DISTRICT` | a `drain_segment` or asset sits administratively in a Bangkok เขต | `sources/bkk_district_elevation.yaml` -- build 3; `drain_segment.district` (from the CSV's own `DISTRICT_NAME` field) or an asset's `notes` field `"district: <name>"` fragment, exact string match only; build 4 adds `sump_well -> district` edges by exact `district_en` match |
| `OUTFALL` | a pump/tunnel/gate structure discharges into a named outfall/boundary node | `sources/capacity_ledger.yaml` -- build 4, added 2026-09-27; derived by regexing an outfall-kind row's own `source` text for another ledger id whose kind is `pump_station`/`tunnel`/`gate`, never geometric |
| `CAPACITY_OF` | a row's capacity pertains to a named `river_reach`-kind row | `sources/capacity_ledger.yaml` -- build 4, added 2026-09-27; derived the same way as `OUTFALL`, target restricted to rows of kind `river_reach` |
| `IN_SUBBASIN` | an asset's real lat/lon falls inside a DWR Sub_Basin polygon | `sources/dwr_subbasins.yaml` + `tools/kg/unit_resolver.py` (point-in-polygon against the real archived DWR polygon, build 6, added 2026-09-27) -- tag `VERIFIED-geometric` (its own family, distinct from `IN_BASIN`/`IN_DISTRICT`'s exact-field-match family: this is a computed geometric containment fact against an official polygon, not a plain field read); an asset with no lat/lon, or one outside every archived polygon, gets no edge |
| `ON_REACH` | an asset's nearest `river_reach` node, by HEURISTIC nearest-centroid snap | `tools/kg/build_kg.py` `build_on_reach_edges()` (build 7, added 2026-10-04) -- snap tolerance = that reach's OWN HydroRIVERS `length_km`, never a fixed/invented distance, but this measures distance to the reach's representative POINT, not to its line geometry (true point-to-polyline snapping is M2b); tag is always `DERIVED-snap` (its own fixed heuristic tag, NEVER the snapped asset's own tag -- a nearest-point guess must never be laundered into VERIFIED/MEASURED); `rain_gauge` assets are excluded entirely (not located ON a reach); coverage is partial and reported per asset class in `docs/KG_QUERY.md` |
| `IN_PROVINCE` / `IN_AMPHOE` | an asset's `asset_id` already matches a row in the HII geocode harvest | `sources/hii_station_geocode.yaml` (build 7, added 2026-10-04) -- id-matched only, never geocoded/snapped; `hii_watergate:`/`hii_dam:`-prefixed source rows do not match any existing asset node id, no edge for those (known id-crosswalk gap) |
| `RESPONSIBLE_FOR` | an `AG_*` governance-DAG node is accountable for a named `province:*`/`basin:onwr:*` area node | `sources/province_agency_crosswalk.yaml` (build 7, added 2026-10-04) -- `VERIFIED` only for the crosswalk's own named per-area rows; every other province/basin gets the generic role template, tag `RELAYED-GENERAL`. Resolving a bare lat,lon (not a named area id) to this edge is NOT wired (M2b, see "Known gaps") |

`FUNDS`/`INFORMS`/`POWER` are outside the five kinds named in the task's edge-kind list,
but the DAG file already tags and sources them like every other edge, and dropping them
would silently discard real information the DAG maintainer already recorded -- kept
rather than thrown away, and called out here so nothing is hidden.

## Latest-readout linkage

`readout_log` is keyed by short structure codes (e.g. `ssb10`, `pwt03`) only for
`kind='burden'` rows -- every other `readout_log` kind (`rain`, `pump`, `tide`,
`status`, `balance`, `edge`, `briefing`) is an area-level or edge-level aggregate, not
an individual station reading, and is **not** attached to any single asset node here
(attaching it would mean guessing which asset "owns" an area label -- not done).
`burden` keys are mapped to `asset_id` via `east_chain.yaml`'s own explicit `asset_id`
field (the same file used for `LOCATED_ON`), then the most recent row per asset is kept.
This schema has no separate `run_id` column, so `run_at_utc` is reused as
`latest_run_id` -- a surrogate, not a distinct identifier, documented here rather than
silently invented.

## Counts (build 7, 2026-10-04 -- fresh measured totals, this exact shipped build;
regenerate with `python3 -m tools.kg.build_kg --out output/thailand_water_kg`, printed to
stdout on every run, never hand-edit this table)

**Total: 26,727 nodes, 64,441 edges.**

### Nodes by class x tag

| class | tag | count |
|---|---|---:|
| canal_node | RELAYED | 8,684 |
| rain_gauge | VERIFIED | 4,428 |
| drain_segment | VERIFIED-from-official-csv | 3,406 |
| gate | VERIFIED | 2,266 |
| river_reach | RELAYED | 2,254 |
| gauge | VERIFIED | 1,231 |
| drain_junction | VERIFIED-from-official-csv | 1,077 |
| reservoir_medium | VERIFIED | 857 |
| amphoe | VERIFIED | 735 |
| sub_basin | VERIFIED-from-DWR-service | 359 |
| pump_station | VERIFIED | 299 |
| governance_dag | (none -- DAG tags edges only) | 240 |
| canal | RELAYED | 190 |
| weir | VERIFIED | 102 |
| data_feed | VERIFIED | 94 |
| dam | VERIFIED | 86 |
| province | VERIFIED | 79 |
| reservoir_small | VERIFIED | 60 |
| data_feed | RELAYED | 52 |
| district | OPEN | 50 |
| basin | VERIFIED | 23 |
| asset_class | RELAYED-GENERAL | 21 |
| retention_basin | RELAYED | 15 |
| data_feed | OPEN | 13 |
| gate | OPEN | 13 |
| sump_well | VERIFIED-from-official-csv | 13 |
| tunnel | OPEN | 13 |
| diversion | OPEN | 8 |
| dam_spillway | OPEN | 7 |
| canal_node | OPEN | 6 |
| outfall | OPEN | 5 |
| reservoir_medium | OPEN | 5 |
| data_feed | MEASURED | 4 |
| outfall | MEASURED | 4 |
| river_reach | OPEN | 4 |
| diversion_channel | OPEN | 3 |
| agency | VERIFIED | 2 |
| bkk_canal | OPEN | 2 |
| floodway_canal | RELAYED | 2 |
| levee | OPEN | 2 |
| outfall | RELAYED | 2 |
| pump_station | RELAYED | 2 |
| agency | OPEN | 1 |
| agency | RELAYED | 1 |
| bkk_canal | VERIFIED | 1 |
| culvert | OPEN | 1 |
| gate | MEASURED | 1 |
| pond | OPEN | 1 |
| pump_station | OPEN | 1 |
| tide_gate | RELAYED | 1 |
| tunnel | RELAYED | 1 |
| **total** | | **26,727** |

Note: the `district` class's 50 rows are all `OPEN` at the node-tag level because
`load_bkk_districts()` uses the row's own `elevation_tag` as the node tag (25 districts
have a real RTSD-map elevation reading tagged `VERIFIED-from-map` upstream in
`sources/bkk_district_elevation.yaml`, but that finer tag isn't one of this graph's
`VALID_TAGS`, so it folds to `OPEN` here rather than being silently upgraded to
`VERIFIED` -- see `docs/FLOODCONNECT_TOPOLOGY.md` for the per-district detail).

### Edges by kind x tag

| kind | tag | count |
|---|---|---:|
| WATER | RELAYED | 12,339 |
| IN_SUBBASIN | VERIFIED-geometric | 9,307 |
| OWNS | VERIFIED | 9,106 |
| OWNED_BY_AGENCY | VERIFIED | 7,903 |
| IN_BASIN | VERIFIED | 6,773 |
| IN_PROVINCE | VERIFIED | 5,967 |
| DRAINS_TO | VERIFIED-from-official-csv | 5,885 |
| IN_DISTRICT | VERIFIED-from-official-csv | 3,184 |
| DRAINS_TO | RELAYED | 1,264 |
| IN_AMPHOE | VERIFIED | 801 |
| ON_REACH | DERIVED-snap | 785 |
| RESPONSIBLE_FOR | RELAYED-GENERAL | 227 |
| DATA | VERIFIED | 141 |
| IN_DISTRICT | VERIFIED | 96 |
| COMMANDS | RELAYED-GENERAL | 94 |
| DATA | RELAYED | 57 |
| OWNS | OPEN | 52 |
| OWNS | RELAYED-GENERAL | 46 |
| COMMANDS | OPEN | 39 |
| COMMANDS | RELAYED | 38 |
| SAME_AS_CANDIDATE | RELAYED | 37 |
| WATER | RELAYED-GENERAL | 34 |
| AUTHORIZES | RELAYED-GENERAL | 32 |
| RESPONSIBLE_FOR | VERIFIED | 30 |
| DATA | RELAYED-GENERAL | 29 |
| OWNS | RELAYED | 24 |
| DATA | OPEN | 15 |
| WATER | OPEN | 15 |
| INFORMS | RELAYED | 13 |
| INFORMS | RELAYED-GENERAL | 12 |
| LOCATED_ON | RELAYED | 12 |
| AUTHORIZES | RELAYED | 11 |
| WATER | VERIFIED | 11 |
| INFORMS | OPEN | 9 |
| INFORMS | VERIFIED | 8 |
| OUTFALL | MEASURED | 6 |
| SHARES | RELAYED-GENERAL | 6 |
| FUNDS | RELAYED-GENERAL | 5 |
| SHARES | OPEN | 4 |
| CONSTRAINS | OPEN | 3 |
| DATA | MEASURED | 3 |
| POWER | OPEN | 3 |
| SHARES | RELAYED | 3 |
| CAPACITY_OF | OPEN | 2 |
| CAPACITY_OF | RELAYED | 2 |
| FUNDS | OPEN | 2 |
| FUNDS | RELAYED | 2 |
| AUTHORIZES | OPEN | 1 |
| CONSTRAINS | RELAYED-GENERAL | 1 |
| OUTFALL | RELAYED | 1 |
| POWER | RELAYED-GENERAL | 1 |
| **total** | | **64,441** |

`DRAINS_TO / RELAYED` (1,264) is every junction->canal match (segment/junction-internal
`DRAINS_TO` edges are tagged with the segment's own row tag,
`VERIFIED-from-official-csv`; the junction->canal match itself is tagged `RELAYED`
because the MATCH is a name-string heuristic even though the underlying segment data is
official -- same discipline as `SAME_AS_CANDIDATE`).

`ON_REACH / DERIVED-snap` (785) is a nearest-centroid heuristic, never the snapped asset's
own tag (see "Node schema"/"Edge schema" above) -- **785 of 4,899 geolocated non-rain_gauge
assets (16%) is a PARTIAL result, not a closed gap**; per-class coverage is in
`docs/KG_QUERY.md` section 1.

Re-run `python3 -m tools.kg.build_kg --out output/thailand_water_kg` to regenerate this
table (printed to stdout on every run) if any upstream source changes.

## Known gaps

- **`ON_REACH` coverage is PARTIAL -- 785 edges nationwide, most asset classes barely
  reached** (build 7, 2026-10-04): dam 4/86, gate 315/2,279, gauge 251/1,231,
  pump_station 117/297, reservoir_medium 69/862, weir 29/102; every other class (basin,
  culvert, diversion_channel, levee, pond, reservoir_small, retention_basin, tide_gate,
  tunnel) is 0. `rain_gauge` (4,428 assets) is excluded entirely, by design. The snap
  heuristic measures distance to a reach's representative POINT, not its line geometry,
  and never snaps to a `canal_node`/declared canal-chain reach -- but it DOES snap a
  canal-sited asset to the nearest HydroRIVERS `river_reach` regardless, often far away:
  288 of the 785 edges are from an asset with คลอง (canal) in its own name (median snap
  1.71 km, 100 over 5 km, 34 over 10 km, max 15.71 km) -- an upstream/downstream walk
  from such an edge is not reliable. True point-to-polyline snapping across river AND
  canal reaches together is **M2b**. See `docs/KG_QUERY.md` section 1 for the full
  per-class table and the snap-distance numbers.
- **`main_stem` is per HydroRIVERS river system (`main_river_id` group), not the Thai
  administrative "แม่น้ำสายหลัก" (the one designated main river per ONWR basin)** -- under
  this build's definition Ping, Mun and Chi are `main_stem=False` because each is a
  tributary piece INSIDE a larger HydroRIVERS group (the Chao Phraya group for Ping, the
  Mekong group for Mun/Chi), not because each has its own group. The Nan river is
  `main_stem=True`, not because it is its own system, but because it is the
  highest-discharge branch within the SAME Chao Phraya group that also contains the Chao
  Phraya reach itself -- `main_stem` picks one branch per group by discharge, which need
  not match the Thai per-basin "สายหลัก" designation. A second, explicit per-ONWR-basin
  `basin_main_river` flag (or a crosswalk to the Thai sense) is **M2b**.
- **Point -> province/accountability resolution is not wired for a bare lat,lon outside
  Sammakorn/Ram53** -- `province:*`/`amphoe:*` nodes carry no geometry (`lat`/`lon` both
  `null`), and `tools/kg/accountability.py`'s own Q1 (`nearest_assets()`) never reads
  `RESPONSIBLE_FOR` or walks to a province/basin node, so
  `python3 -m tools.kg.accountability --at "14.0208,100.5343"` (Pathum Thani) still
  refuses unless a geolocated asset happens to be nearby. Only gates/dams whose
  `hii_watergate:`/`hii_dam:`-prefixed id matches an existing asset node get an
  `IN_PROVINCE` edge at all -- most do not (see "Counts" above, the 3,232 unmatched
  source rows). Wiring point -> province resolution into `accountability.py`'s Q1, plus a
  real id crosswalk for gates/dams, is **M2b**.
- **Governance-DAG nodes carry no tag.** `water_system_dag.mmd` only tags edges. A node
  like `AG_BMA_GOV` has `tag: null` in this graph -- readers must look at the edges
  touching it, not the node itself, for an evidence tag.
- **Owner-agency nodes are still separate from the governance DAG's `AG_*` nodes** (the
  synthetic `agency:<slug>` node from `assets_registry.py`'s `owner` field is still a
  distinct node from the DAG's `AG_DDS`/etc for the same real-world agency). Build 2
  (2026-09-27) adds `sources/owner_agency_crosswalk.yaml` -> `OWNED_BY_AGENCY` edges as an
  **additive parallel link** (asset -> `AG_*` node directly) for every `VERIFIED` crosswalk
  row, rather than merging/replacing the `agency:<slug>` nodes -- so both representations
  now coexist. `OPEN` crosswalk rows (no `AG_` node exists, e.g. Department of Fisheries,
  most individual Bangkok districts other than Saphan Sung, or a compound owner string
  naming more than one real agency) are deliberately left unlinked, never guessed.
- **`AG_GONCH` stray-node gap (flagged in build 2) is resolved as of build 3** -- the
  node now carries a proper `class=governance_dag`/`name_th` (`water_system_dag.mmd` was
  edited between build 2 and build 3, out of this check's scope/file-lock; confirmed by
  re-reading the node's attributes in the rebuilt graph, not re-verified against the
  `.mmd` diff itself).
- **LOCATED_ON is thin: 12 edges.** Only the declared `east_chain.yaml` canal chain
  carries an explicit asset-to-reach reference in its own source data. No asset in the
  `assets` table carries a HydroRIVERS `HYRIV_ID` or an OSM canal-node coordinate key,
  so no LOCATED_ON edge connects any asset to the HydroRIVERS or OSM-canal subgraphs --
  a real, honest gap, not a bug to silently paper over.
- **4 river-reach nodes have a longitude slightly past 105.7E** (up to 105.71042),
  inherited from the pre-existing Thailand bbox clip's own "approx, incl. some border
  overlap" (see `build_river_kg.py` in the repo root, `THAILAND_BBOX` comment) -- these are a
  handful of Mekong-border reaches in the source HydroRIVERS clip, not something this
  build introduced. `tests/test_kg_build.py::test_no_coords_outside_thailand_bbox`
  **fails** on this (see test output below) rather than silently loosening the bound to
  make it pass.
- **coordinates: none geocoded, none inferred.**
- **IN_BASIN: 5 basin-name strings in asset notes did not match a basin node** (mostly
  non-Thailand/annotated variants, e.g. `"ไม่ระบุ"` unspecified) -- no edge created, no
  fuzzy match attempted.
- **Wikipedia canals: build 3 improves resolution from 7/175 to 72/175** by adding
  normalised-name matching (`normalize_canal_name()` -- strips a leading `คลอง`,
  collapses whitespace) against the OSM canal-edge name index (939 distinct names) and
  the 18 site canal_graph (`east_chain.yaml`) node labels, on top of the existing exact
  name_th match. **103 of 175 names remain unresolved** (mostly geographic features --
  mountains, provinces, river mouths -- not present as a named node anywhere in this
  graph, or spelling variants this repo's "exact-after-normalisation only, never fuzzy"
  rule correctly refuses to guess at) -- kept as a node attribute only, no WATER edge
  fabricated.
- **Owner-agency nodes still not cross-walked to the DAG's `AG_*` nodes** (unchanged from
  the previous build).
- **BMA drain-pipe topology is heavily fragmented: 513 connected components** over 4,483
  segment+junction nodes -- the source CSV's `PIPE_FROM`/`PIPE_TO` fields are blank on
  many rows (only 2,915 of 3,406 (row,side) entries have both ends; the underlying
  2,903-row CSV has many fully-blank-topology rows, see
  `docs/knowledge/DRAINAGE_NETWORK_SOURCES.md`), so most segments end up in small,
  disconnected islands rather than one nationwide-drain component -- an honest finding
  about how incomplete the official inventory's topology fields are, not a bug in this
  build's join logic (see `docs/FLOODCONNECT_TOPOLOGY.md` for detail and the Sammakorn
  case).
- **1,264 junction->canal `DRAINS_TO` matches out of 1,077 distinct junction nodes**
  (one junction can produce more than one matching edge -- both a PIPE_FROM-side and a
  PIPE_TO-side match against the same canal name in different rows -- hence more match
  edges than junction nodes) -- most `PIPE_FROM`/`PIPE_TO` names are street/intersection
  names, not canal names, so most junctions correctly have NO canal match; never
  geocoded.
- **3 district names in the assets `notes` field did not match any of the 50
  `sources/bkk_district_elevation.yaml` district names** (`บางชื่อ`/`ป้อมปราบฯ`/
  `ราษฎร์บูรณะ` vs. that file's `บางซื่อ`/`ป้อมปราบศัตรูพ่าย`/`ราษฏร์บูรณะ` -- genuine
  cross-source Thai spelling variants, e.g. ฎ vs. ฏ in the last pair) -- no edge
  created, never fuzzy-matched.
- **Drain-pipe/district node coordinates: none geocoded, none inferred** (same
  discipline as every other node class in this graph) -- `drain_segment`,
  `drain_junction`, `district`, and `capacity_ledger_node` nodes all carry
  `lat: null, lon: null`. The 13 pipe-jacking sump-well rows in `sources/
  bma_drain_pipes.yaml` DO carry real coordinates (their own file's UTM47N numbers,
  converted to WGS84 in build 3) and **are wired into `build_river_kg.py` as `sump_well`
  graph nodes as of build 4** (2026-09-27) -- see "Counts" above and
  `docs/KG_VERIFY_2026-09-27.md`'s "Build 4" section.

## Pending inputs for a future build

- `data-pipe-jacking.csv`'s companion large-bore culvert rows (distinct from the
  small `sump_wells` UTM list) were seen linked but not downloaded this check
  (see `docs/knowledge/DRAINAGE_NETWORK_SOURCES.md`) -- a candidate for a future fetch.
- `AG_DIST_<code>` per-district governance-office nodes (one per เขต, alongside the
  existing lone `AG_DIST_SS`) are proposed but **deliberately not added to
  `water_system_dag.mmd`** this check (out of scope, per the task's own instruction) --
  see `docs/FLOODCONNECT_TOPOLOGY.md` for the full generated candidate list.

## Test output (2026-09-27, build 3)

```
$ python3 -m pytest tests/test_kg_build.py -q
......F                                                                  [100%]
FAILED tests/test_kg_build.py::test_no_coords_outside_thailand_bbox -- same 4 river-reach
nodes as build 1/2 (border-overlap reaches inherited from the pre-existing HydroRIVERS
bbox clip, see "Known gaps" above) -- no new out-of-bbox nodes introduced by build 3
1 failed, 6 passed in ~7s

$ python3 -m pytest tests/test_bma_drain_pipes.py -q
.......                                                                  [100%]
7 passed in ~0.3s

$ python3 -m pytest tests/ -q
2 failed, 370 passed  # the 2 failures are the pre-existing, documented AGENTS.md §8
                       # items (bbox test above, and test_readout.py's known fixture
                       # issue) -- both re-checked this build, neither caused by it.
```

Full P4-equivalent verify (acyclicity, duplicate-id, leak-scan) for build 3 is in
`docs/KG_VERIFY_2026-09-27.md`, "Build 3" section.
