# Changelog

All notable changes to FloodConnect. Dates are Asia/Bangkok local. This file states
only what actually shipped and is tested in this repository — never a plan (see
`ROADMAP.md` for plans).

## v0.1.4 — 2026-10-05

**"KG-first that AIs cannot skip" (M4, founder ruling 2026-10-05, verbatim "แม้แต่เอไอ
เก่งๆก็อ่านข้าม ตกลงเราต้องทำยังไงให้เอไอไม่ดื้อ"): a chat AI that could read the v0.1.3 KG
mandate was observed (one founder-reported session) skipping straight to raw station
pages. This release makes the KG step small, fast, and load-bearing in `answer`'s and
`locate`'s own output; for a no-tool chat AI it remains an `llms.txt` instruction — no
behavioural measurement of any AI's reading choice was run this release.**

### Added
- `tools/kg/build_index.py` — deterministic per-province KG index builder (networkx +
  stdlib only, reads `output/thailand_water_kg.graphml` only, never writes to it).
  Writes `output/kg_index/index.json` plus one `province_<code>.json` per province node
  in the graph — **79 slices** (77 Thai provinces + 2 non-Thailand geocode codes present
  in the graph: 99, 10499), against the graph measured at **26,727 nodes, 64,441 edges**,
  `sha256` `33fcd36bafb7...`. Each slice carries the province's touched DWR sub-basins /
  ONWR basins, member assets (gauge/gate/weir/dam/pump_station/tide_gate) tagged by
  placement method (`pv`: `"e"` has an `IN_PROVINCE` edge, `"b"` placed by its coordinate
  falling inside the province's bbox, `"n"` placed at the nearest edge-linked member as a
  last resort — only gauges/rain-gauges carry `IN_PROVINCE` edges in this KG build, so
  every gate/weir/dam/pump_station/tide_gate row is `"b"` or `"n"`, stated plainly in that
  slice's own `gaps`), the `ON_REACH` reaches those assets snap to, `RESPONSIBLE_FOR`
  agencies, and an explicit `known_gaps` list. Province bboxes are built from
  `IN_PROVINCE` gauge/rain-gauge members only, rounded OUTWARD (`floor`/`ceil` at 3dp) so
  a member sitting exactly on a rounded boundary is never excluded (a plain `round(.,3)`
  previously excluded a real Pathum Thani member and, with it, 3 gates co-located with
  it). **Measured sizes:** median slice 9,821 B, max 187,072 B (Bangkok — its ~960
  box-placed gates/pumps are the point of that slice), total 1,045,491 B across 79 files —
  within the 30 KB median / 200 KB max budget. `tests/test_kg_index.py` asserts a fresh
  rebuild is byte-identical to the committed files, box members lie inside their own
  bbox, and index counts match slice counts.
- `tools/kg/locate.py` — offline `locate()` (stdlib only, no network, no graphml read):
  resolves a lat,lon point to its province (from a caller-supplied `--province`/`province`
  argument — code, Thai name, or English name via the committed `sources/province_names_en.yaml`
  snapshot — or up to 3 candidates, each tagged `RELAYED`, ranked by nearest `IN_PROVINCE`
  member when omitted, never a single silent guess), nearest sub-basin(s), nearest assets
  with their `ON_REACH` reach, stations sharing that reach/sub-basin, and responsible
  agencies and `known_gaps` **keyed per candidate code** when no province was resolved
  (never one flat list that silently answers for only one of the candidates), plus a
  compact `kg_anchor`. Stations exclude the 162 `gauge:thaiwater_rain:*` ids (rainfall-
  only, mislabelled `class=gauge` in this KG build — recorded in `index.json`'s `gaps`).
  **Measured:** box containment alone places the Pathum Thani test point
  14.0208,100.5343 only in Nonthaburi's box (its nearest Pathum member is 8.865 km away,
  outside Pathum's own rounded bbox) — confirming why `locate` must return candidates,
  never one guess; its `agencies`/`known_gaps` for that point are returned separately for
  each of the 3 candidate provinces, never Nonthaburi's alone. Output capped at 6,000
  characters; measured 3,344-3,827 characters (raw JSON, in-process, `ensure_ascii=False`,
  no indent) and indented CLI/MCP output 4,614–5,188 characters (indent=2; 5,188 at kb.py's
  Sammakorn coordinate 13.758235,100.676084) and in-process call time 0.004-0.023 s on
  the acceptance points (Pathum, Chiang Mai, Sai Buri, Ubon, Sammakorn, Sammakorn at
  kb.py's own coordinate), against the 3 s budget (CLI wall time, including Python
  startup, ~0.09 s per call).
- CLI: `floodconnect locate --at lat,lon [--province X] [--json]` (`kb.cmd_locate`). MCP:
  `floodconnect_locate(at, province=None)`, registered in both the real FastMCP block and
  the stdlib JSON-RPC fallback's `_TOOLS`/`_TOOL_DESCRIPTIONS`.
- `kb.build_answer` now appends `kg_anchor` as the LAST key of every answer (verified
  byte-identical to v0.1.3 otherwise, by diffing an offline Sammakorn answer against
  `origin/main` with `generated_at`/`kg_anchor` excluded). The outside-Thailand branch
  gets `kg_anchor: {"tag": "OPEN", "method": "outside_thailand"}`. When the KG index
  cannot be read, `kg_anchor` degrades to `{"tag": "OPEN", "method": "no_kg_index"}` and
  `next_action.dual_state.confidence` is capped from `HIGH` to `LOW` — `state`'s own
  `resolution_confidence` is a different field and is left untouched, so the two CAN
  differ when the index is missing (by design: `dual_state.confidence` is what a caller
  actually reads to decide how much to trust the colour; `resolution_confidence` records
  what the station data alone supported).
- `llms.txt`'s first non-heading line (both EN and TH) is now the KG-first instruction:
  tool users run `floodconnect locate`/`floodconnect_locate` first; no-tool chat AIs
  fetch the raw `output/kg_index/index.json` URL then the matching province slice; every
  answer must state its `kg_anchor` or it is "not a FloodConnect answer". Mirrored
  (briefly, pointing at the real detail rather than restating it) in `README.md`,
  `docs/AI_TIERS.md`, `docs/NEAREST_STATION_RECIPE.md` (new Step 0b), `docs/KG_QUERY.md`
  (new §0b, the slice schema + `pv` legend), and `system_capabilities.json` (new
  `kg_first` block, `locate`/`floodconnect_locate` added to `entry_points`).
- Token-budget fix: `AI.md`'s "On-demand refresh" section was
  trimmed (full detail already lived, unchanged, at `docs/AI_ENTRYPOINT.md`) from 1,997
  to 1,759 tokens to recover the margin `kg_anchor` costs. **Measured totals**
  (AI.md + SKILL.md + answer, cl100k): populated-DB scenario now 1,759 + 1,226 + 1,579 =
  **4,564** tokens (436 below the 5,000 ceiling, comfortably above the 300-token safe
  margin); `tests/test_token_budget.py`'s existing ceilings are unchanged and stay green.

- `sources/province_names_en.yaml` — a committed, hand-typed (`tag: RELAYED`, not an
  independently re-verified government source) snapshot of the 77 Thai provinces'
  standard English names, cross-checked code-by-code against the Thai names already in
  `output/thailand_water_kg.graphml`'s own province nodes. `build_index.py` reads it to
  fill `index.json`'s `en` field for all 77 (the 2 non-Thailand codes, 99/10499, stay
  `null`); `locate --province "Pathum Thani"` now resolves the same as `--province 13`.
- Per-asset `ag` in each slice now prefers the KG's own `OWNED_BY_AGENCY` edge (VERIFIED,
  from `sources/owner_agency_crosswalk.yaml`) over the previous owner-name string match,
  which missed it whenever the free-text owner field didn't exactly match an agency
  node's `name_th`. **Measured**, before/after this fix: asset rows with `ag=null`
  across all 79 slices dropped from 3,576/5,095 to 866/5,095.
- `locate`'s "province not recognised" error now lists every province in the index
  (previously the first 5 by code only).

### Fixed
- `system_capabilities.json`'s `pyproject_version` was still `"0.1.2"` (a pre-existing
  stale value, found while bumping it for this release) — now tracks `pyproject.toml`.
- `locate`'s `agencies`/`known_gaps` no longer come from a single silent nearest-member
  vote when no province could be resolved (the exact Pathum Thani 14.0208,100.5343
  pitfall this milestone names: the vote put it in Nonthaburi alone) — see above.
- `cand` entries and `kg_anchor` are now tagged `RELAYED` in candidate mode, matching the
  wording the docs already used.
- `stations`/`kg_anchor.station_ids` no longer include the 162 `gauge:thaiwater_rain:*`
  ids (rainfall-only gauges the KG mislabels `class=gauge`) ahead of real water-level
  gauges.

### Not in scope (frozen, per founder instruction)
- No small-model measurement pass this round (explicitly declined on cost).
- The shipped KG did not become the default for `answer`'s own accountability path;
  `FLOODCONNECT_USE_SHIPPED_KG` is unchanged.
- M2b items still backlog: crosswalking the geocode id-prefix for `pv="b"`/`"n"` assets,
  splitting the Bangkok slice.
- `output/thailand_water_kg.*` is byte-unchanged — this release only reads it.

## v0.1.3 — 2026-10-05

**Nationwide knowledge graph shipped in git, KG-first mandate (founder ruling
2026-10-04, verbatim "อย่างแรกให้เอไอต้องอ่านแผนที่กราฟของเราได้จาก git ก่อนและบังคับว่าต้องหาจาก
kggraph นี้") — milestone M2a of the founder-approved "แบ่ง M2a/M2b" split.**

### Added
- `output/thailand_water_kg.graphml` + `.jsonld` committed directly in git (build 7,
  2026-10-04) — **26,727 nodes, 64,441 edges**, readable with a plain `git clone`, no
  rebuild/network call required. Headline edge counts: `IN_SUBBASIN` 9,307 edges
  (`VERIFIED-geometric`, real point-in-polygon against the archived DWR Sub_Basin
  polygons), `ON_REACH` 785 edges (`DERIVED-snap`, nearest-centroid-point heuristic,
  never the snapped asset's own tag — per-class coverage: dam 4/86, gate 315/2,279,
  gauge 251/1,231, pump_station 117/297, reservoir_medium 69/862, weir 29/102, every
  other class 0; `rain_gauge` excluded by design). 79 `province` nodes + 735 `amphoe`
  nodes (both `VERIFIED`, from the HII geocode harvest).
- `main_stem` (bool) on every `river_reach` node — one branch per HydroRIVERS river
  system (`main_river_id` group) by discharge, including the Mekong group (restarted
  2026-10-04 after its own group was found split into two fragments, 983 + remainder,
  by the Thailand bbox clip — fixed so the in-Thailand portion is never silently left
  untagged). This is the HydroRIVERS-system sense, not the Thai administrative
  "สายหลัก" per-ONWR-basin sense — see `docs/KG_QUERY.md` section on `main_stem` and
  "Known gaps" below. `output/thailand_river_flow.graphml` (+ `.jsonld`) was
  regenerated without a GISTDA flood snapshot: `flood_status` is now `unknown` on
  all 2,250 reaches and `flood_source_node` / `eta_from_flood_hr` are `"null"`
  everywhere (the keys remain). `main_stem` is not in this file; it is only in
  `output/thailand_water_kg.*`.
- `docs/KG_QUERY.md` — the recipe page every AI session reads first for anything
  basin/province/amphoe/river/station/gate/agency-shaped, with measured (not
  aspirational) coverage numbers and runnable Python snippets against the shipped
  graph.
- **KG-first mandate** wired into `AGENTS.md` and `docs/AI_TIERS.md`: before locating
  or reasoning about any place outside Sammakorn/Ram53, a file-reading AI session
  reads the shipped graph from git first, never re-derives/re-geocodes it. A new
  `docs/knowledge/INDEX.yaml` entry (`KG_QUERY`) points at the same page.
- `FLOODCONNECT_USE_SHIPPED_KG` environment guard in `kb.py` — the shipped nationwide
  graph is only consulted for a bare lat,lon's accountability answer when this guard
  is set; the default (unset) answer path is unchanged from v0.1.2 (nationwide coarse
  station/basin reading + `_nationwide_accountability_fallback`'s text-only
  province/agency fallback), so shipping the KG does not silently change what a
  default `floodconnect answer` call returns.

### KNOWN GAPS → M2b (not closed by this build, stated here rather than papered over)
- **Pathum Thani: 0 of 15 Pathum assets have an `ON_REACH` edge** (4 water-level
  gauges + 11 rain gauges, the latter excluded from `ON_REACH` by design); 13 of the
  28 HII-geocoded Pathum ids ARE nodes in the shipped graph (as `gate:hii_watergate:<id>`)
  but carry no `IN_PROVINCE` edge, because the geocode join misses them on an id-prefix
  mismatch (see the geocode file's own `known_limitation`) — a join/crosswalk gap, not a
  missing-node gap. The "0 `ON_REACH` for Pathum" figure holds either way, these 13 included.
- **Canal snapping**: the `ON_REACH` heuristic never snaps to a declared canal-chain
  reach — a canal-sited asset still snaps to the nearest HydroRIVERS river reach
  regardless, often far away (250 of the 785 edges are from an asset whose name_th
  contains คลอง; among those 250 canal-sited edges: median snap 1.58 km, 34 over 5 km,
  15 over 10 km, max 15.71 km). True point-to-polyline snapping across river AND canal
  reaches together is M2b.
- **Point → province/accountability resolution is not wired** for a bare lat,lon
  outside Sammakorn/Ram53: `province`/`amphoe` nodes carry no geometry, and
  `tools/kg/accountability.py`'s `nearest_assets()` never reads `RESPONSIBLE_FOR` or
  walks to a province/basin node. Wiring this, plus a real id crosswalk for
  unmatched gates/dams, is M2b.
- **Per-basin main river**: `main_stem` is per HydroRIVERS system, not per ONWR
  basin — a second, explicit `basin_main_river` flag (or a crosswalk to the Thai
  "สายหลัก" sense) is M2b.

## v0.1.2 — 2026-10-04

**Nationwide coarse (station/basin) coverage — founder ruling 2026-10-04, verbatim
"ทำเลย v0.1.2 ทั้งประเทศ แล้วค่อยพัก".**

### Added
- Any `lat,lon` in Thailand now gets a real `current_local_state`/`forward_hazard`
  reading, not just the two Bangkok MVP areas (Sammakorn village, Soi Ramkhamhaeng 53,
  which keep their existing household/node-level detail, unchanged). Resolution is
  **coarse (station or basin), never household-level**, outside those two areas:
  - **Station resolution:** every fresh `thaiwater_waterlevel` station within 10 km
    (any water body, not checked against `river_name`) decides, worst colour wins —
    not just the nearest one (Chanthaburi has 3 deciding stations at once).
  - **Basin resolution:** failing that, a fresh reading sharing the NEAREST station's
    own `sub_basin_id` (a stand-in for "same basin", not a check that both stations
    sit on the same named river) within 50 km decides — but can **never** produce
    GREEN on its own (it can still raise YELLOW/RED), and only when no local
    colour-bearing factor-4 source (Bangkok canal/pump telemetry) already decided
    this point. A local reading never suppresses a nationwide STATION-resolution
    row (<=10 km) this way — only a basin-resolution one — so a station sitting at
    0.0 km on a fresh agency OVERBANK status still decides even when the point also
    has fresh local telemetry.
  - No fresh reading within 50 km sharing that sub-basin → `UNKNOWN` (never GREEN by
    default).
  - Both radii are FloodConnect's own stated design choice (`docs/INDICATORS.md` §11),
    never an agency threshold.
- `parsers.parse_thaiwater_waterlevel` now keeps `min_bank`, `ground_level`,
  `critical_level_msl`, `situation_level`, `diff_wl_bank`, `diff_wl_bank_text`,
  `river_name`, `sub_basin_id`, `basin_id`, `basin_name_th`, agency shortname, amphoe/
  tambon, and `waterlevel_msl_previous` (exact field paths MEASURED against one live
  GET of the feed, 2026-10-04 — `diff_wl_bank`/`diff_wl_bank_text`/`situation_level`/
  `storage_percent` are top-level, NOT nested under `station`).
- `collect.collect_thaiwater_waterlevel` fills `observations.bank`/`critical`/`status`
  (status is the agency's own verbatim code, `thaiwater_situation_<n>`, or `OVERBANK`
  when the agency's own `diff_wl_bank_text` itself reads "ล้นตลิ่ง"), and the source is
  now in `collect.ANSWER_SOURCES` with an explicit `max_age_hours: 24` in
  `sources/registry.yaml`.
- `floodconnect_model.STATUS_TO_LEVEL`: the ONE closed status-word → colour map this
  repository uses. `readout.py` and `kb.py` now read their `*_LIKE_STATUS` sets off it
  instead of keeping separate copies.
- The 16-day forecast (`forward_hazard`) is now fetched and read at the queried
  coordinate for any `lat,lon`, not only the 11 previously hardcoded forecast points
  — EXCEPT a point within the snap radius of one of those named points, which is
  still read under that named point (e.g. a Chiang Mai-area query prints "จุด
  chiangmai", not its own raw coordinate).
- Accountability for a nationwide (non-MVP-area) point is now **text**: the deciding
  station's own feed-published province and owning agency — never a fabricated phone
  number, never a graph lookup (the governance knowledge graph is a separate,
  not-yet-built piece of work).
- `state.evidence` rows from the nationwide path carry `dist_km`, `resolution`
  (`"station"`/`"basin"`), and `agency` — shown even in the default (non-`--verbose`)
  answer, never dropped into the stale-rows cap.

### Fixed
- **`NO_THRESHOLD` (no agency level published at all for a station) no longer
  classifies as GREEN.** It carried no basis for that colour — it now correctly gives
  `UNKNOWN`, both in `floodconnect_model.classify_counts`/`classify` and in
  `kb._classify_current_local_state`.
- The Thai colour-contract heading in `docs/INDICATORS.md` ("ใช้กับทุกตัวชี้วัด
  ไม่มีข้อยกเว้น") and the unscoped sentence in `docs/AI_TIERS.md` are corrected to say
  the RED/YELLOW/GREEN/UNKNOWN contract applies only to `current_local_state` and
  `one_decision.level` — every other indicator has its own closed vocabulary.
- `docs/NEAREST_STATION_RECIPE.md` Step 4 now names `situation_level` and
  `critical_level_msl` explicitly, states that a bare bank number never sets a colour
  on its own, and copies the full §1 status-word mapping (previously missing the
  "any other status word → YELLOW" fallback and the agency-overflow-text rule).
- Field-path statements in `docs/INDICATORS.md` §7/§8 and the recipe's source table
  corrected to the real, measured feed shape.
- `docs/NEAREST_STATION_RECIPE.md` no longer cites an internal, unpublished note name
  as its source for the conflicting-data rule — it now points at `AI.md`.

### Changed
- `pyproject.toml` version and the MCP server's `serverInfo.version` bumped to
  `0.1.2`.
- README.md, `llms.txt`, `docs/INDICATORS.md` §11, `system_capabilities.json`
  (`areas_covered`), and `ROADMAP.md` updated to say nationwide COARSE coverage is
  shipped, not "in progress" — and that it is coarse, never household-level, outside
  the two named Bangkok areas.

### Not included in this release
- `distance_to_bank_m`/`bank_fill_percent` (§7/§8) are relayed in `provenance` only,
  not a standalone top-level answer field or a numeric colour cutoff — Toledo-first
  discipline: no invented threshold. The agency's own `situation_level`/
  `diff_wl_bank_text` words are what actually drives the colour.
- The agency's own Thai label/colour for each `situation_level` code (1–5) is
  VERIFIED (fetched from the public bundle
  `https://www.thaiwater.net/dist/js/app.chunk.js`, 2026-10-04) — see
  `floodconnect_model.py`'s `STATUS_TO_LEVEL` comment for the full table. Level
  4 ("มาก") is coloured BLUE by the agency and is not called a warning there;
  FloodConnect's own mapping of level 4 → YELLOW (and 1/2 → GREEN) is this repo's own
  conservative choice on top of the agency's labels, not an agency threshold.
- The Water-Debt/Jev/DSVA one-decision envelope, the `--level` tiers, and a
  geolocated nationwide governance/accountability knowledge graph remain v0.2+ work
  (see `ROADMAP.md`).

## v0.1.1 — 2026-10-04

See `.ai/claims/20261004-floodconnect-v011-claim.yaml` and git history — predates this
file.
