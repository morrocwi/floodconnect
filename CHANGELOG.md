# Changelog

All notable changes to FloodConnect. Dates are Asia/Bangkok local. This file states
only what actually shipped and is tested in this repository — never a plan (see
`ROADMAP.md` for plans).

## v0.1.2 — 2026-10-04

**Nationwide coarse (station/basin) coverage — founder ruling 2026-10-04, verbatim
"ทำเลย v0.1.2 ทั้งประเทศ แล้วค่อยพัก".**

### Added
- Any `lat,lon` in Thailand now gets a real `current_local_state`/`forward_hazard`
  reading, not just the two Bangkok MVP areas (Sammakorn village, Soi Ramkhamhaeng 53,
  which keep their existing household/node-level detail, unchanged). Resolution is
  **coarse (station or basin), never household-level**, outside those two areas:
  - **Station resolution:** the nearest `thaiwater_waterlevel` station within 10 km
    (any water body, not checked against `river_name`) decides, if fresh.
  - **Basin resolution:** failing that, a fresh reading sharing the NEAREST station's
    own `sub_basin_id` (a stand-in for "same basin", not a check that both stations
    sit on the same named river) within 50 km decides — but can **never** produce
    GREEN on its own (it can still raise YELLOW/RED), and only when no local
    factor-4 source (Bangkok canal/pump telemetry) already decided this point.
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
- The 16-day forecast (`forward_hazard`) is now fetched and read at the EXACT queried
  coordinate for any `lat,lon`, not only the 11 previously hardcoded forecast points.
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
