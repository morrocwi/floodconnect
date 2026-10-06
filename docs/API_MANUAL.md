# GOV API MANUAL -- Thai government water-data sources for FloodConnect

**Dated evidence samples only, never current values.** Every byte count, field sample and
"confirmed populated" claim below is dated to its own call-proof timestamp (2026-10-05) --
read it as evidence that a field path/behaviour existed on that date, never as today's
water level.

**Audience:** any AI (or human) that needs to fetch live values from the Thai government
water agencies FloodConnect watches. **What this is:** a reading of `collect.py` /
`parsers.py` / `sources/registry.yaml` plus one live GET per source (run 2026-10-05,
Asia/Bangkok), never a certification by the agencies themselves.

**What this is NOT:** a cache of live values. This repo's own rule ("the KG node only
says what to call; the live API returns the values") applies here too -- no live reading
is committed to this file or this repo. Trimmed samples below are evidence that a field
path exists, dated to the call-proof row beside them, not a current value to trust later.

**Epistemic tags used throughout:** VERIFIED (checked live by this pass), MEASURED (a
number this repo's own code computed, e.g. a derived m3/s), RELAYED (this repo repeating
an agency/registry claim it did not independently re-verify, e.g. a licence posture),
PROPOSAL (a registered, proposal-tier Toledo equation output, not yet a settled theorem --
PROP-FLOOD-01/02 are registered and merged; PROP-FLOOD-11 is registered but not
implemented in this release, v0.2 target), OPEN (genuinely unresolved). A raw agency
number itself, once fetched live, is tagged RELAYED (it is the agency's word, not this
repo's), never VERIFIED-as-fact about the real world.

---

## Fetch order -- Jev Sandwich (S0-S8)

**Founder's rings** (Z1-Z3 verbatim; Z0 wording "จุดเก็บน้ำเล็กที่สุด" is FloodConnect's own): Z0 = the smallest storage point ("จุดเก็บน้ำ
เล็กที่สุด", e.g. บึงรับน้ำหมู่บ้านสัมมากร). Z1 = "คลองใกล้เรา" (canals near us). Z2 =
"พื้นที่น้ำเหนือเรา" (water area above us). Z3 = "ลุ่มน้ำเหนือเรา" (basin above us).
**Sandwich rule** ("ใช้แซนวิช หัวท้าย ถ้าขัดแย้งกัน คือ สกัดตรงกลางออกมา" -- use the two
ends first; only on conflict, extract the middle): read Z0 and Z3 first; fetch Z1/Z2 only
when Z0/Z3 disagree, a slice is missing/stale, or a slice is rising. The machine-readable
form of every step below is `sources/sandwich_fetch_order.yaml`; this section is its
pseudocode narrative. **This is pseudocode only** (founder scope decision, see section 14)
-- no executable library ships with S0-S8; nothing here is imported by this repo's code.

```text
S0 LOCATE    {lat, lon, province?} -> tools/kg/locate.py:locate() -> kg_anchor
             {kg_sha256, method, province|cand+province_tag, sub_basin, reach,
              station_ids[<=2]}. 0 live calls (offline, reads output/kg_index/).
             Refuse (design target -- kb.py's own code paths today are
             method=no_kg_index and method=outside_thailand, not these three
             names): KG_INDEX_MISSING (design target, maps to kb.py's
             no_kg_index), OUTSIDE_THAILAND (design target, maps to kb.py's
             outside_thailand), PROVINCE_NOT_RECOGNISED (design target -- no
             matching kb.py method exists today).

S1 RINGS     walk from kg_anchor: Z0 = caller-declared storage point (e.g.
             canalchain:sammakorn_pond / WL.SMK.01) else kg_anchor.station_ids[0].
             Z1 = canal_chain WATER hop<=2 both ways (site/inputs/canals/
             east_chain.yaml) -> LOCATED_ON stations, OR river_reach ON_REACH
             upstream hop<=1. Z2 = canal_chain upstream hop 3-6, OR river_reach
             upstream hop 2-5 within the same IN_SUBBASIN. Z3 = river_reach
             upstream closure (no hop cap) within the same IN_BASIN, plus
             dam:/reservoir_*:hii_dam IN_BASIN members. EXCLUDED from station
             selection: osmcanal WATER (OSM heuristic, direction mostly unknown),
             DRAINS_TO (the drain network, no gauge sits on it), AS_* WATER
             (hand-declared DAG, S6 path evidence only). An empty ring -> BOT,
             never ZERO. Refuse: NOT_JOINED, EMPTY_RING.

S2 SNAPSHOT  for each ring's station_ids: GET thaiwater_waterlevel (nationwide,
             whenever a Z3 river station is in play) and/or bma_watermap (POST,
             whenever a *:thaiwater_bma:<WL code> station is in play) -> one
             reading per station (schemas/reading.schema.json), freshness_flag
             set. Fallback thaiwater_canal_waterlevel only if bma_watermap fails
             AND still fresh enough. Non-200 -> no retry, that family's rings BOT.
             Refuse: NO_LIVE_SOURCE, HTTP_ERROR, STALE, FAULT.

S3 HOTSPOT   over each ring's own readings (never nationwide): is_hotspot :=
             startswith(diff_wl_bank_text,"ล้นตลิ่ง") OR situation_level==5 OR
             value>=bank OR value>=critical OR classify(status) in [RED,YELLOW]
             -> ring.worst_status, ring.closest_to_bank (h-bank, h-critical).
             0 live calls.

S4 Z0 TREND  3-state readout ("มีสามสถานะ เพิ่มขึ้น เสถียร ลดลง", founder ruling
             2026-10-05): GET bma_station_detail?id=<water_id> for a BMA Z0 (1
             call, 5-min series) OR read S2's own waterlevel_msl_previous for a
             thaiwater Z0 (0 calls) -> delta_k (PROP-FLOOD-01) -> RISING/STABLE/
             FALLING/NO_READOUT. ONLY IF RISING: compute eta_to_bank
             (PROP-FLOOD-02, linear, two windows -- the shipped M8 ETA, see
             `rise_eta_hours_range`; wall-clock only when the source declares a
             tick spacing). Acceleration (PROP-FLOOD-11, the 2nd retained
             difference) is a SEPARATE, also-registered Toledo proposal (PR #65
             merged 2026-10-06, tier Dr) that is registered but NOT IMPLEMENTED
             in this release (v0.2 target) -- never cite it as the equation
             behind the shipped eta_to_bank number.
             waterlevel_graph is OPEN (every sampled HII value was null; RID
             returns HTTP 500) -- not called. HOST NOTE (updated 2026-10-07,
             VERIFIED by one live GET, HTTP 200 with a real
             576-point series for id=284): `bma_station_detail`'s own endpoint
             is reachable keyless today -- the 2026-09-27 403 does not
             reproduce. It stays `DORMANT_NOT_IN_ALL` in `collect.py` only in
             the sense that it is excluded from the bulk "fetch every source"
             rotation (deliberate no-burst policy, one-station-at-a-time); the
             M8 Jev Sandwich path (`kb._bma_series_trend`) calls it directly,
             one GET per answer, no retry; on a future 403/reset stop touching
             the host, trend = NO_READOUT (BOT), never retry. Refuse:
             SPARSE_SERIES, NO_READOUT, UNRESOLVED, NOT_APPLICABLE,
             NOT_IN_TOLEDO.

S5 Z3 OVERVIEW keyless only: GET hii_dam (dam_released > dam_inflow for Z3 dams),
             GET openmeteo_forecast16d (worst-first across models, any model
             daily >=35.1mm "ฝนหนัก" within 3 days, INSTINCT window), GET
             dds_daily_pdf (Bangkok anchors only, agency bulletin word). Official
             warning outside Bangkok, keyless, is OPEN. Refuse: OPEN,
             NO_LIVE_SOURCE.

S6 ESCALATE  z0_state, z3_state in {ALARM, RISING, QUIET, UNKNOWN}. agree :=
             z0_state==z3_state in {ALARM, QUIET} -> STOP, decide (S8), never
             fetch the middle. Else (DISAGREE, MISSING_OR_STALE, or RISING) ->
             open Z1/Z2 using S2's own snapshots (0 calls) + trend from the
             previous tick (0 calls) + ONE bma_station_detail GET to the decisive
             BMA middle station if S4 did not already use it + ONE hii_watergate
             GET for gates/pumps on the path. bma_watermap watergateNN/
             water_control (0 calls, already fetched). bma_pumphistory is OPEN
             (dead, HTTP 404). HOST NOTE (updated 2026-10-07, see S4 above):
             `bma_station_detail` is reachable keyless today -- that one
             conditional GET runs, exactly 1 per run, no retry; on a future
             403/reset stop touching the host, trend = NO_READOUT (BOT), never
             retry.

S7 RINGS OUT (retired design, superseded): the original plan was one
             ring_readout per ring via `schemas/ring_readout.schema.json`
             (worst_status, closest_to_bank, trend, eta_to_bank, acceleration,
             end_state, s4). That schema file is RETIRED, never shipped --
             the M8 build (2026-10-05/06) replaced it with
             `schemas/layer_readout.schema.json`/`schemas/sandwich_trace.schema.json`,
             the actual runtime shape `_answer_sandwich`/`sandwich_decision`
             produce. 0 live calls either way.

S8 DECIDE    feed Z0 (h_t, h_t_minus_k, k, epsilon, theta, official_status) into
             floodconnect_model.one_decision() -> {decision, confidence, level,
             checks, gate, why}. Ladder outcome (ALARM_LOCAL / INCOMING / HELD /
             QUIET / UNKNOWN) comes from S6/S7. The Choice/Score/Noul/gate Jev
             ENVELOPE around this IS implemented and on the answer path as of
             M8 (`kb._build_jev_decision`'s `choice`/`score`/`noul`/`gate`
             fields, `schemas/jev_decision.schema.json`) -- not the earlier
             v0.2.0 design-target wording. The Z0 at-or-over-critical fact is
             ALWAYS reported, whatever the ladder decides.
```

**Ladder (founder ruling 2026-10-05, supersedes an earlier ordering):** L1 = S2-S5
(both ends, top+bottom); L2 = S6 agree -> decide directly; L3 = S6 conflict -> extract
the middle (Z1/Z2); L4 = S7/S8 -> decide. If the middle confirms water moving toward us
-> "AT RISK -- water coming" (เสี่ยง — น้ำกำลังมา, FloodConnect wording, not
founder-verbatim). If the middle shows water held/
diverted, state that with reasons. Middle data missing/stale -> UNKNOWN, never "safe".

**4-colour scale (founder ruling 2026-10-05, Thai labels):**

| colour | label (TH) | when | official agency tier? |
|---|---|---|---|
| 🟢 GREEN | ปกติ | agency says normal, data fresh, Z0/Z3 agree | yes |
| 🟡 YELLOW | เฝ้าระวัง | an agency watch/warning, OR an upstream overflow while the middle layer is not yet rising | yes -- aligned with DDPM stage 1 "การเฝ้าระวังและติดตามสถานการณ์", RELAYED (founder ruling 2026-10-05), not independently re-read against a cited DDPM plan document by this repo |
| 🟠 ORANGE | เตรียมพร้อม | water confirmed coming (middle layer rising along the KG path toward us), OR local level rising above warning toward critical | **no** -- FloodConnect's own choice, aligned with (not equal to) the common agency phrase "เฝ้าระวังและเตรียมพร้อม" |
| 🔴 RED | วิกฤต | at or over the agency critical/bank level, by the agency's own word or level | yes |
| UNKNOWN | ไม่ทราบ | missing or stale data | no -- never SAFE |

**Integration map** (founder addition 2026-10-05: "schema ต้องต่อเข้า model tool
protocol api skill ในการวิเคราะห์อย่างเป็นระบบ"). Every row below uses names that already
exist in this repo; "design target" marks what does not exist yet.

| schema object | produced by (API/step) | consumed by (model fn / tool field) | protocol step | skill step |
|---|---|---|---|---|
**Note (updated 2026-10-07): this table is a dated M7a design-time map (2026-10-05) and the "design target"/"K-step" column predates both `tools/kg/rings.py` (which ships and builds real rings offline from `output/kg_index/`) and `skill/SKILL.md`'s own numbered sections (§0-§10, which now exist) -- read the "K" references below as pointers to that M7a-era plan, not as a claim that SKILL.md still has no numbered steps.**

| `kg_anchor` | S0, `tools/kg/locate.py:locate` | `kb.py:_kg_anchor` -> `answer.kg_anchor`; MCP `floodconnect_locate` | D1 | SKILL.md §1(c)/§2 S0 (K1) |
| ring station set | S1, `site/inputs/canals/east_chain.yaml` + `output/kg_index` slices | `tools/kg/rings.py:rings` (shipped, M8 -- offline from `output/kg_index/`, no graphml load) | D1 | SKILL.md §2-§3 (K2) |
| `reading` (schemas/reading.schema.json) | S2, `thaiwater_waterlevel`/`bma_watermap` | `store.insert_observation`; `floodconnect_model.classify`/`classify_counts`; `kb.py` `dual_state.current_local_state` | D2 | SKILL.md §2 (K3) |
| `ring_readout.worst_status`/`closest_to_bank` | S3, hotspot filter | `floodconnect_model.CRITICAL_LIKE_STATUS`/`WATCH_LIKE_STATUS`/`classify` | D3, D6 | SKILL.md §3 (K4) |
| `series` (schemas/series.schema.json), `ring_readout.trend`/`eta_to_bank`/`acceleration` | S4, `bma_station_detail` | `floodconnect_model.delta_k`, `floodconnect_model.time_to_threshold`; `one_decision` inputs h_t/h_t_minus_k/k/epsilon/theta | D5 | SKILL.md §4 (K5) |
| `sandwich_readout.z3_overview` | S5, `hii_dam`/`openmeteo_forecast16d`/`dds_daily_pdf` | design target (`kb.py` `dual_state.forward_hazard` exists but is not wired to this object) | D3, D6 | SKILL.md §0b/§3 (K6) |
| `sandwich_readout.escalation`/`path` | S6 | design target | D2, D3 | SKILL.md §3 (K7) |
| `ring_readout.end_state`/`s4` | S7 | design target (Noul check) | D7 | SKILL.md §3 (K7) |
| `sandwich_readout.ladder`/`one_decision`/`envelope` | S8 | `floodconnect_model.one_decision`; `envelope` (choice/score/noul/gate) is shipped as of M8, see §12's UPDATE note | D7, D8 | SKILL.md §3/§7 (K8) |

**Toledo status** (updated 2026-10-07; founder addition 2026-10-05 for the
PROP-FLOOD-01/02/09/12 part, still accurate): PROP-FLOOD-01/02: registered
unverified proposals on Toledo main (PR #59, tier Dr, placeholder code
`weld/M.??.v1`) -- PROP-FLOOD-02 (linear, two windows) is the ETA this release
actually ships; PROP-FLOOD-09: draft branch, not on main; PROP-FLOOD-11:
registered, unverified proposal on Toledo main (PR #65 merged 2026-10-06 at
commit `65297f05`, tier Dr, in `model_spec.json`) -- registered but NOT
IMPLEMENTED in this release (v0.2 target), never the equation behind the
shipped ETA; PROP-FLOOD-12: name only.

**Keyed (optional) endpoints** -- never called by this repo. See section 9a below and
`sources/sandwich_fetch_order.yaml`'s `optional_keyed` list for the full table and the
key-request channel.

See `sources/sandwich_fetch_order.yaml` for this same order as queryable YAML (one row
per step, with `protocol_step`/`consumed_by` fields matching the Integration map above).

---

## 0. Values index -- "which source gives me X?"

| value you want | sources that give it |
|---|---|
| water level (current) | `thaiwater_waterlevel`, `thaiwater_canal_waterlevel`, `hii_waterlevel_load`, `bma_watermap`, `bma_klongmap`, `bma_station_detail` |
| bank level (agency) | `thaiwater_waterlevel` (`station.min_bank`), `bma_watermap` (`left_bank`/`right_bank`), `hii_waterlevel_load` (`station.left_bank`/`right_bank`/`min_bank`), `bma_station_detail` (`txt_left_bank`/`txt_right_bank`) |
| critical/warning level (agency) | `thaiwater_waterlevel` (`station.critical_level_msl`), `bma_watermap` (`critical`/`warning`), `bma_station_detail` (`txt_critical`/`txt_warning`), `hii_waterlevel_load` (`station.critical_level_m`/`warning_level_m`) |
| agency status word | `thaiwater_waterlevel` (`situation_level`/`diff_wl_bank_text`), `bma_watermap` (`txtStatus`), `dds_daily_pdf` (canal `status_th`), `dds_flood_report` (narrative only). `situation_level`'s own scale (0-5, `storage_percent` band + agency colour) is already documented and cited in `docs/INDICATORS.md` lines 70-77 (0 ไม่มีข้อมูล / 1 น้อยวิกฤต <=10% / 2 น้อย 10-30% / 3 ปกติ 30-70% / 4 มาก 70-100% blue / 5 ล้นตลิ่ง >100% red) -- readouts should cite that table rather than leaving the Z3/basin-wide roll-up forced to OPEN. |
| rain observed (24h) | `thaiwater_rain_24h` (`rain_24h`), `dds_daily_pdf` (`rain_stations[].rain_mm`) |
| rain 1h | `thaiwater_rain_24h` (`rain_1h`, absent on a variable, often large fraction of rows -- ~60% on 2026-10-05); no `rain_3h`/`rain_7d`/`rain_monthly` field exists in any source checked |
| rain observed, TMD's own numbers | none without a key -- `tmd_opendata` needs `TMD_OPENDATA_API_KEY` (OPEN, not configured) |
| rain observed, BMA-specific | no dedicated BMA rain endpoint found -- folded into `thaiwater_rain_24h` and `dds_daily_pdf` |
| dam storage / inflow / release | `hii_dam` (`analyst/dam`), `rid_app_reservoir` (`app.rid.go.th`), `egat_water_crisis`, `rid9_chonburi_rpt` (Chonburi region only) |
| discharge (m3/s) | `hii_waterlevel_load` (`discharge`, real gauge), `openmeteo_flood` (GloFAS model, NOT a gauge) |
| gate opening / pump state | `hii_watergate`, `bma_watermap` (`watergateNN`), `bma_pumphistory` (**404, dead** -- see category C) |
| flood road depth | `thaiwater_flood_road` |
| official bulletin / warning text | `dds_daily_pdf`, `dds_flood_report`, `dds_tide_pdf` |
| forecast rain, per model | `openmeteo_forecast16d`/`openmeteo_multimodel` (9/6 models), `openmeteo_ensemble_daily` (31-member GEFS), `metno_locationforecast` (independent pipeline) |
| forecast discharge | `openmeteo_flood` (GloFAS) |
| sea level / tide (model) | `openmeteo_marine`, `dds_tide_pdf` (predicted table), `dds_daily_pdf` (`tide_dedicated`, observed) |

---

## 1. Master table

How column: **API-JSON** / **API-POST** / **HTML-scrape** / **PDF** / **CSV** / **GIF (unparsed)** / **no fetcher**.

| cat | source_id | agency | how | auth | history/series | tier | live-tested (2026-10-05) |
|---|---|---|---|---|---|---|---|
| A | `thaiwater_waterlevel` | HII+owning agency (thaiwater.net) | API-JSON | none | none (1 reading/station) | official_telemetry | YES 11:20, 200, 1.34MB, 807 stn |
| A | `thaiwater_canal_waterlevel` | BMA Drainage (via thaiwater.net) | API-JSON | none | none | official_telemetry | YES 11:20, 200, 226KB, 282 stn |
| A | `hii_waterlevel_load` | HII+owning agency | API-JSON | none | accepts start/end but **returns 1 row/station regardless of range** -- NOT a series | official_telemetry | YES 11:21, 200, 684KB, 382 rows |
| A | `thaiwater_flood_road` | BMA Drainage (via thaiwater.net) | API-JSON | none | none | official_telemetry | YES 11:20, 200, 204KB, 262 stn |
| A | `bma_klongmap` | BMA Drainage | API-JSON (POST) | none | none found | official_telemetry | YES 11:20, **200** (code's own DORMANT_NOT_IN_ALL note says 403 since 2026-09-26 -- the block appears to have lifted; flagged for a human re-check, no file edited) |
| A | `bma_station_detail` | BMA Drainage | HTML scrape | none | **YES -- see section 10**, inline per-station chart, ~2 days at ~5min steps (id=88 confirmed populated: 576 Highcharts points; id=284 (WL.SMK.01) confirmed populated: 575-576 points) | official_telemetry | YES 11:20/11:21, 200 (id=51 and id=88 both) |
| A | `bma_pak_khlong_csv` | BMA (data.bangkok.go.th CKAN) | CSV | none | the CSV itself is a daily series back to 2026-01-01, but **~2 months stale** (newest row 2026-08-04 on two separate checks) | official_telemetry | YES 11:24, 200, 3.7KB |
| B | `bma_watermap` | BMA Drainage | API-JSON (POST) | none | none in this payload (only now + 2 daily maxima) -- see section 10 for the richer StationDetail chart | official_telemetry | YES 11:20 (this pass, multiple calls), 200, 510KB, 311 stn -- **WL.SMK.01 confirmed, critical=0.44** |
| C | `hii_watergate` | HII+owning agency | API-JSON | none | none found | official_telemetry | YES 11:19, 200, 3.59MB, 2315 rows |
| C | `bangkok_floodgate_locations` | BMA Open Data | CSV | none | static asset inventory, not telemetry | official_report | YES 11:25, 200, 52KB |
| C | `bangkok_pump_station_and_floodgate_physical_data` | BMA Open Data | CSV | none | static asset inventory | official_report | YES 11:25, 200, 98KB |
| C | `bma_pumphistory` | BMA Drainage | HTML (dead) | none | n/a | official_telemetry | YES 11:13 + 11:20, **HTTP 404, confirmed dead twice** -- NO_LIVE_SOURCE; see category C note on the `bmawaterflow.bangkok.go.th` lead |
| D | `hii_dam` | HII+RID/EGAT | API-JSON | none | none (census snapshot) | official_telemetry | YES 11:20, 200, 1.05MB, 989 rows (4 station types) |
| D | `rid_app_reservoir` | RID (app.rid.go.th) | API-JSON (POST) | none | one year-ago comparison point only, not a series | official_report | YES 11:20, 200, 30KB (+alert feed 25B) |
| D | `egat_water_crisis` | EGAT | HTML scrape | none | none (daily table) | official_report | YES 11:20, 200, 30KB, 17 dams |
| D | `rid9_chonburi_rpt` | RID region 9 (Chonburi) | HTML scrape | none | walkable by date, no range endpoint | official_report | YES 11:20, 200, 260KB, 61 rows (eastern seaboard, not Chao Phraya) |
| D | `hii_reservoir_metadata` | HII | CSV | none | static survey catalog | official_report | YES 11:20, 200, 16KB, 65 rows |
| H | `rid_res_table` | RID | HTML scrape | none | none, name list only, no coordinates | official_report | YES 11:20, 200, 12KB (name-only, no numeric value exists on the page) |
| E | `thaiwater_rain_24h` | multi-agency (via thaiwater.net) | API-JSON | none | none (rolling 24h total) | official_telemetry | YES 11:20, 200, 4.63MB, 4552 stn |
| F | `openmeteo_forecast` | Open-Meteo (ECMWF/GFS blend) | API-JSON | none | forward series itself | third_party | YES 11:21, 200, 2.3KB |
| F | `openmeteo_forecast16d` | Open-Meteo (9 models) | API-JSON | none | forward series itself | third_party | YES 11:19, 200, 1.9KB |
| F | `openmeteo_ensemble_daily` | Open-Meteo (NOAA GEFS 31-member) | API-JSON | none | forward series itself | third_party | YES 11:20, 200, 5.1KB |
| F | `metno_locationforecast` | MET Norway | API-JSON | none (UA string required by ToS) | forward series itself | third_party | YES 11:20, 200, 40KB |
| F | `openmeteo_previous_runs` | Open-Meteo (skill-check) | API-JSON | none | this IS the history/skill-check endpoint | third_party | YES 11:21, 200, 5.3KB |
| F | `openmeteo_pressure` | Open-Meteo (9 models) | API-JSON | none | past_days=7 built in | third_party | YES 11:22, 200, 44KB |
| F | `openmeteo_sst` | Open-Meteo Marine | API-JSON | none | past_days=7 built in | third_party | YES 11:23, 200, 18KB |
| F | `openmeteo_flood` (GloFAS) | Open-Meteo | API-JSON | none | multi-day array per call | third_party | YES 11:21, 200, 2.2KB |
| F | `openmeteo_ensemble` | Open-Meteo (icon_seamless) | API-JSON | none | forward series itself | third_party | YES 11:21, 200, 18KB |
| F | `openmeteo_marine` | Open-Meteo | API-JSON | none | forward series itself | third_party | YES 11:21, 200, 4.3KB |
| F | `openmeteo_soil_moisture` | Open-Meteo | API-JSON | none | forward series itself | third_party | YES 11:21, 200, 3.1KB |
| F | `openmeteo_archive_precip` | Open-Meteo (ERA5) | API-JSON | none | this IS the history query | third_party | YES 11:22, 200, 841B |
| F | `openmeteo_multimodel` | Open-Meteo (6 models) | API-JSON | none | forward series itself | third_party | YES 11:21, 200, 4.3KB (first confirmed-live run per registry) |
| F | `nasa_power` | NASA POWER | API-JSON | none | this IS the history query | third_party | YES 11:22, 200, 620B (fill-value gap 4 days this run) |
| G | `gdacs_events` | GDACS (EU JRC+UN OCHA) | API-JSON | none | ~100-item rolling window | third_party | YES 11:22, 200, 136KB, 2 Thailand FL events found |
| F | `noaa_oni` | NOAA CPC | text file | none | the file IS 76yr of history | official_report | YES 11:23, 200, 23KB |
| G | `dds_daily_pdf` | BMA Drainage (DDS) | PDF | none | none (1 PDF/day) | official_report | YES 11:21, 200, 2.02MB |
| G | `dds_tide_pdf` | Royal Thai Navy Hydrographic Dept | PDF | none | the PDF IS the year's table | official_report | YES 11:21, 200, 179KB |
| G | `dds_flood_report` | BMA Drainage (DDS) | HTML scrape | none | none | official_report | YES 11:21, 200, 85KB |
| H | `dds_nowcast_gif` | BMA Drainage (DDS) | GIF (unparsed) | none | each fetch is 1 frame | official_report | YES 11:21, 200, 3.33MB (image only, never parsed) |
| H | `hii_analyst_cctv` | HII (camera catalog) | API-JSON | none | none, catalog | official_telemetry | YES 11:24, 200, 169KB, 106 cams |
| H | `bangkok_ckan_portal` | BMA CKAN | API-JSON | none | none, catalog (truncated 20/132) | official_report | YES 11:25, 200, 167KB |
| H | `hii_mou_station_metadata` | HII (watershed-forest stations) | CSV | none | static catalog | official_report | YES 11:20, 200, 86KB, 259 stn |
| H | `dnp_yom_basin_telemetry` | DNP (Yom basin) | CSV | none | static catalog, UTM zone 47 coords | official_report | YES 11:21, 200, 10KB, 33 stn |
| H | `pcd_mwqi` | PCD (marine water quality) | CSV | none | file IS a 2015-2024 annual series | official_report | YES 11:21, 200, 223KB |
| H | `dmcr_marine_acidification` | DMCR | CSV | none | historical casts, 2018 + 2025 mixed | official_report | YES 11:21, 200, 115KB |
| H | `royalrain_operations` | Royal Rainmaking Dept | API-JSON | none | none, daily snapshot | official_report | YES 11:21, 200, 54B (empty today -- real, not an error) |
| H | `royalrain_agriculture_rainfall` | Royal Rainmaking Dept | API-JSON | none | none | official_report | YES 11:21, 200, 54B (empty today) |
| H | `hii_water_level_catalog` | HII (nationwide station catalog) | CSV | none | static catalog | official_report | YES 11:20, 200, 436KB, 1396 stn |
| H | `pcd_coastal_marine_quality` | PCD | CSV | none | 5 round-files exist, only latest wired | official_report | YES 11:20/21, 200, 104KB |
| H | `google_flood_hub_api` | Google Research | API (key, waitlist) | api_key | unknown | third_party | NOT CALLED -- no key (waitlist, not instant self-service) |
| H | `cds_era5_reanalysis` | Copernicus/ECMWF | async submit/poll | api_key | the async flow itself IS history | third_party | NOT CALLED -- no key; NOT a plain GET, needs `cdsapi` client |
| H | `nasa_lhasa_landslide_nowcast` | NASA LHASA-2 | API (key) | api_key | unknown | third_party | NOT CALLED -- no key; granule URL itself unconfirmed |
| H | `opentopography_copernicus_dem_glo30` | OpenTopography | API (key, instant signup) | api_key | n/a (static DEM) | third_party | NOT CALLED -- no key (collector DOES real-fetch once a key exists) |
| H | `gfw_data_api` | Global Forest Watch | API (key, instant signup) | api_key | near-real-time alerts | third_party | NOT CALLED -- no key; auth transport itself unconfirmed |
| H | `reliefweb_api_v2` | ReliefWeb (UN OCHA) | API (appname) | api_key-like | none | third_party | NOT CALLED -- no appname configured (free registration, not instant) |
| H | `gistda_flood_extent_api` | GISTDA | API (key) | api_key | sibling 30-day endpoint exists elsewhere in repo | official_telemetry | NOT CALLED -- no `GISTDA_API_KEY` |
| H | `governor_shared_flooded_roads` | Office of the Governor (BKK) | no fetcher | -- | -- | official_shared_inference | n/a -- manual import only |
| H | `rtsd_2010_ground_level_map` | Royal Thai Survey Dept | no fetcher | -- | -- | official_report | n/a -- static reference asset |
| H | `rid_flood_risk_map` | RID | no fetcher | -- | -- | official_report | n/a -- static reference asset |
| H | `social_listening_google` | public (Google-indexed posts) | no fetcher (own CLI) | -- | -- | community_report | n/a -- imported via `social_listening.py --import-google` |
| H | `social_listening_paste` | public (maintainer-pasted) | no fetcher (own CLI) | -- | -- | community_report | n/a -- imported via `social_listening.py --import-paste` |
| H | `tmd_opendata` | TMD | API (key) | api_key | unknown | official_telemetry | not in this pass (registry: no code wired yet) |
| H | `data_go_th_ckan` | data.go.th | API | none | n/a | official_report | not in this pass |
| H | `gistda_portal` | GISTDA | unknown | unknown | unknown | official_report | not in this pass |
| H | `ddpm_portal` | DDPM | unknown | unknown | unknown | official_report | not in this pass |
| A | `mwa_chaophraya_bigdata_api` | MWA | API (key) | api_key | unknown | official_telemetry | not in this pass |
| A | `mwa_chaophraya_level_csv` | MWA | CSV | none | unknown | official_telemetry | not in this pass |
| H | `tmd_main_site` | TMD | HTML | none | n/a | official_report | not in this pass |
| E | `dwr_ews_rain_daily` | DWR | unknown | none | unknown | official_telemetry | not in this pass |
| H | `dwr_main_site` | DWR | HTML | none | n/a | official_report | not in this pass |
| H | `marine_imis` | Marine Dept | unknown | none | unknown | official_report | not in this pass |
| H | `marine_elaws` | Marine Dept | HTML (legal db) | none | n/a | official_report | not in this pass |
| A | `thaiwater_waterlevel_graph` | HII+owning agency (thaiwater.net) | API-JSON | none | 15-min time grid, but **series_confirmed: false, status OPEN** -- every value sampled was null for HII stations 160/48; RID (station_id=1095849) returns HTTP 500 | official_telemetry | YES 11:29:53, 200, 256,566 bytes, 3,310 points, all-null sample |

### 9a. Keyed (optional) endpoints -- never called by this repo

All on `twa-api-public.thaiwater.net`, header `x-api-key`. Documented as "optional --
request your own key" so a reader who gets a key can use these; the key embedded in the
agency web app is never copied or used by this repo.

| step | endpoint | what it adds | request your own key at |
|---|---|---|---|
| S2/S4 | `/v2/waterlevel/list` | `percentageDiff` (the agency trend field, preferred over Δ sign when present, RELAYED), `diffWlBank` | https://www.hii.or.th/ -- mailto:contact@hii.or.th confirmed live 2026-10-05; no self-service key-request page found (OPEN) |
| S4/S6 | `/data/platform/v1/public/tele_waterlevel/graph?stationId&startDate&endDate&limit=-1` | hourly RID series (e.g. C.67 = stationId 7576) | same channel -- OPEN |
| S5 | `/v2/summary/summary4dam`, `/data/platform/v1/public/dam_pdaily_sum_by_date?year=` | dam summary and history | same channel -- OPEN |
| S5 | `/v2/rainfall/rainfall_c1440/list`, `/v2/summary/rainfall-forecast` | rain and rain forecast | same channel -- OPEN |
| S5 | `/v2/summary-area/flashflood-warning`, `/v2/storm/alert` | official warning outside Bangkok, storm alert | same channel -- OPEN |
| S5 | TMD `tmd_opendata` | Rain/weather data direct from TMD | `https://data.tmd.go.th/api/` -- probed live 2026-10-05, HTTP 302 (non-200); self-service procedure OPEN |

**Coverage note (honest):** of the 56 sources `collect.py` can actually fetch, **49 got a
real live GET in this pass** (2026-10-05, listed above with a call-proof time). 7 are
key/appname-gated and were honestly skipped (no key configured, verified via `env | grep`
-- never attempted without authorization). The remaining 16 registry rows have no
`collect.py` fetcher at all (5 by design: static references + social-listening's own CLI
import path; the other 11 -- `tmd_opendata`/`data_go_th_ckan`/`gistda_portal`/
`ddpm_portal`/`mwa_chaophraya_*`/`tmd_main_site`/`dwr_*`/`marine_*` -- are registry rows
describing a source this repo has not yet wired a collector for at all; this pass added
no collector code.

---

## 2. Category A -- river and canal water level + bank/critical

The core value: **h - bank** and **h - critical**, same datum, same station. This is
where "water over the bank" actually gets read off a number.

**`thaiwater_waterlevel`** (nationwide, 807 stations) -- `GET
https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel`, no auth, no query
params (filter client-side). Fields: `waterlevel_msl` (value), `station.min_bank` (bank),
`station.critical_level_msl` (critical), `diff_wl_bank`/`diff_wl_bank_text` (agency's own
over-bank flag, e.g. "ล้นตลิ่ง (ม.)"), `situation_level` (1-5, agency ordinal),
`waterlevel_datetime` (obs time), `station.ground_level` (**different datum -- never put
into bank fields**). Station key: `station.tele_station_oldcode` -> KG node
`gauge:thaiwater_waterlevel:<tele_station_oldcode>`. No history endpoint found. Pitfall:
`situation_level` and `diff_wl_bank_text` can disagree -- overbank text wins. CALL-PROOF:
2026-10-05 11:20:11, HTTP 200, 1,344,773 bytes, newest `waterlevel_datetime` "2026-10-05
11:00" (age ~20min).

```text
GET   api-v3.thaiwater.net/.../public/waterlevel     params: none  headers: User-Agent
READ  data[].waterlevel_msl -> value; data[].station.min_bank -> bank;
      data[].station.critical_level_msl -> critical; data[].diff_wl_bank_text,
      data[].situation_level -> agency_status_word; data[].waterlevel_datetime -> observed_at
MAP   -> reading{station_id=data[].station.tele_station_oldcode,
                 source="thaiwater_waterlevel"}        (= schemas/reading.schema.json)
```

**`thaiwater_canal_waterlevel`** (BMA canals, 282 stations) -- same host, `public/
canal_waterlevel`. Fields: `canal_value` (m), `canal_datetime`, `station.canal_oldcode`,
`station.bank`/`warning_level`/`critical_level` (often null). CALL-PROOF: 11:20:02, 200,
226,086 bytes -- **newest `canal_datetime` across 282 stations was only 2026-10-04 12:05,
~23h stale at fetch time** (MEASURED finding, 2026-10-05 -- not every station in this feed
refreshes every run).

**`hii_waterlevel_load`** (richer per-station shape incl. real discharge) -- `GET
https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load?basin_id=<csv>
&&start_date=<YYYY-MM-DD HH:MM>&&end_date=<YYYY-MM-DD HH:MM>`. Fields: `discharge` (m3/s,
real gauge-based Q), `waterlevel_msl`, `station.critical_level_m`/`min_bank`.
**MEASURED FINDING (2026-10-05 (this pass), confirmed with both a 1-day and a 3-day
window): this endpoint returns exactly ONE row per station regardless of the date range
requested** -- despite accepting `start_date`/`end_date`, it is NOT a time series. Treat
as `SPARSE_SERIES` for rate/acceleration. CALL-PROOF: 11:21:39, 200, 683,832 bytes, 382
rows, newest tick "2026-10-05 11:10" (age ~29min); re-confirmed again at 11:21:02 with a
3-day window -> still 1 row/station (e.g. station C.67 had exactly one tick, "2026-10-05
10:00", in both the 1-day and 3-day pulls).

**`bma_klongmap`** -- `GET https://weather.bangkok.go.th/Klongmap/GetDataForUpdate`, POST
not required. **The code's own `DORMANT_NOT_IN_ALL` comment says this returned 403 on
2026-09-26; this pass's live call got HTTP 200** (1,974,758 bytes, keys `waterStation`/
`stationMap`/`arrowMap`/`riverMap`/`listRiverMap`/`dailyheightwater`). Flagging for a
human to re-run the repo's own `collect.py --source bma_klongmap` and consider removing
it from `DORMANT_NOT_IN_ALL` -- no file was edited by this pass (read-only check).

**`bma_station_detail`** -- `GET https://weather.bangkok.go.th/water/StationDetail?id=
<water_id>`. Admin-set thresholds (`txt_water_control`/`txt_warning`/`txt_critical`/
`txt_left_bank`/`txt_right_bank`/`txt_bed_bank`) PLUS -- confirmed this pass (2026-10-05) -- an
**inline per-station history chart** (Highcharts Stock, `var series1 = ...`) with
real content confirmed for **`StationDetail?id=284` (WL.SMK.01)** -- populated, 575
`Date.UTC()` points, 5-minute steps, ~2 days -- and for id=88 (WL.SSB.08, "ค.แสนแสบ-
เสรีไทย 24": warning 0.35, critical 0.45 ม.รทก., 576 points). **This is the confirmed
series lead for this registry** -- see section 10 for the full graph/series hunt. The
sibling, LIGHTER `GraphOnIframe/Index?id=<water_id>&countwl=0` route is the EMPTY one
(`appl = []`) -- never confuse it with `StationDetail`, which is the populated page. id=51
and id=312 (WL.SSB.13) returned the threshold fields but an EMPTY series on the
`StationDetail` endpoint shape -- population is per-station, not universal.
CALL-PROOF: id=284, 11:24:38, 200, 480,017 bytes, 575 points; id=88, 11:2x, 200, 480,378
bytes, 576 `Date.UTC()` occurrences confirmed by direct text search.

**`bma_station_series`** (`collect_bma_station_series`, M8) -- a thin wrapper over the
same `StationDetail?id=<water_id>` page as `bma_station_detail` above, called only from
the Jev Sandwich path for one specific named Z0/middle station id (never part of
`collect.ANSWER_SOURCES`'s `--all`/rotation sweep, and never a batch/rotation guess over
an id list). Refuses (`ok=False`, no network call) when no `water_id` is given. Not a
separate endpoint -- same host, same series shape, documented here only to name the
registry/collect.py entry.

**`bma_pak_khlong_csv`** -- static CSV, Chao Phraya at Pak Khlong, **confirmed ~2 months
stale** (newest row 2026-08-04 on two independent checks, 2026-10-03 and 2026-10-05) --
do not treat as a live signal.

---

## 3. Category B -- ponds / retention / local gauges

**`bma_watermap`** -- `POST https://weather.bangkok.go.th/water/PageMap/GoogleMap`, body
`payload=TEST_DATA_GOES_HERE` (the page's own JS placeholder; returns the full unfiltered
~311-station set), headers `Referer: https://weather.bangkok.go.th/water/`,
`X-Requested-With: XMLHttpRequest`. No auth.

Fields per station: `wl_in` (current level, m), `left_bank`/`right_bank` (m, pick the one
nearer the community side), `warning`/`critical` (m, same datum as `wl_in`),
`site_timestampTH` (Thai Buddhist-Era local string, "DD/MM/YYYY HH:MM" -- subtract 543
from the year), `datediffnow` (minutes since reading, agency's own freshness field),
`max_in_day`/`max_in_yesterday` (two daily maxima -- NOT a time series), `txtStatus`
(agency status word, e.g. "ปกติ"), `water_control` (null on every station checked),
`watergate01..06` (gate openings, null unless a gate station), `water_id`/`water_code`
(station key).

**WL.SMK.01 (`water_code`), the Sammakorn pond gauge** -- CONFIRMED LIVE, 2026-10-05
11:20:19 Bangkok: `water_name` (verbatim, agency's own Thai, never back-transliterated):
"จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2" (EN: "Bueng Muban
Sammakorn Measurement Point, Lake 2 Pumping Station, Khlong Ban Ma 2"); `water_id=284`;
`wl_in=-0.45`; `left_bank=0.83`; `right_bank=0.44`; `warning=0.35`; **`critical=0.44`
(matches the agency critical level named in this pass (2026-10-05), and equals `right_bank`)**;
`txtStatus="ปกติ"` (Normal); `site_timestampTH="05/10/2569 11:15"`; `datediffnow=5`
(minutes). **This directly corrects the earlier miss that WL.SMK.01 had no live source --
it does, via `bma_watermap`.** Series data: see category A's `bma_station_detail` entry --
the richer per-station endpoint, not this one, is where a real chart lives.

Station key: `water_code` (e.g. `WL.SMK.01`) -> KG node not yet assigned a canonical id in
this repo (`gauge:bma_watermap:<water_code>` is this manual's own proposed pattern, OPEN).
For a gate sub-reading, `collect_bma_watermap` uses `<water_code>#gate<NN>` as the
observations table's station_code (never the bare water_code, to avoid colliding on the
(source_id, station_code, variable, observed_at_utc) identity index when several gates on
one station share a timestamp).

Pitfall: a station carrying a non-null `water_url` (30/311 stations in the live payload)
points to `https://bmawaterflow.bangkok.go.th/station?id=<uuid>` -- probed once in this
pass (read-only GET): it is a client-rendered single-page app shell (Vue, via
`axios`), 200 OK but no JSON visible in that one GET -- the real data call is behind
further client-side JS routing not resolved in this pass. Treat as an OPEN lead, not a
working data source yet.

CALL-PROOF: 2026-10-05 11:20:19, HTTP 200, 510,242 bytes, 311 stations, WL.SMK.01 present.

```text
POST  weather.bangkok.go.th/water/PageMap/GoogleMap   body: payload=TEST_DATA_GOES_HERE
      headers: Referer=.../water/, X-Requested-With=XMLHttpRequest,
               Content-Type=application/x-www-form-urlencoded
READ  data[].wl_in -> value; data[].left_bank/right_bank -> bank;
      data[].critical -> critical; data[].txtStatus -> agency_status_word;
      data[].site_timestampTH -> observed_at (Thai Buddhist Era, Bangkok local)
MAP   -> reading{station_id=data[].water_code, source="bma_watermap"}
      (= schemas/reading.schema.json); filter data[] by water_code=="WL.SMK.01"
```

---

## 4. Category C -- gates, pumps, weirs (operations)

**`hii_watergate`** -- `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/
watergate_load`, no auth, nationwide (2315 rows, 139 placeholder `station.id==0` rows
skipped). Fields: `watergate_in`/`watergate_out` (upstream/downstream level, m),
`floodgate_open`/`pump_on` (bool, mostly null in practice), `watergate_datetime_in/out`.
CALL-PROOF: 11:19:49, 200, 3,593,188 bytes. Pitfall: newest `watergate_datetime_in` on
this run ("2026-10-05 22:10") was AHEAD of the actual fetch time (11:19) -- a clock/feed
anomaly on HII's side, not this repo's bug; treat any single-row freshness claim from this
source with suspicion until cross-checked.

**`bangkok_floodgate_locations`** / **`bangkok_pump_station_and_floodgate_physical_data`**
-- static CSV asset inventories (gate/pump location + design opening/control/critical/
warning thresholds), BMA Open Data portal. Not live telemetry -- a design-reference layer
to pair WITH a live reading, never a current state by itself. CALL-PROOF: both 11:25, 200,
52KB / 98KB.

**`bma_pumphistory`** -- **DEAD.** `GET https://weather.bangkok.go.th/Station/
PumpHistory` returns **HTTP 404**, confirmed independently TWICE in this pass (11:13:18
and again 11:20:37 Bangkok time) and by this pass (2026-10-05). This is a real regression
from whatever page used to exist -- `NO_LIVE_SOURCE` for pump status via this URL.
**Lead investigated:** `bma_watermap`'s own payload carries a `water_url` field for 30/311
stations pointing to `https://bmawaterflow.bangkok.go.th/station?id=<uuid>`. Probed once
(read-only GET, no auth): HTTP 200, but it is a client-rendered Vue single-page app shell
(axios-based) -- the actual pump-status JSON call is behind further client-side routing
not resolved in this one GET. **Verdict: promising lead, not yet a working replacement.**
Pump operational state should, until this is resolved, be read from `bma_watermap`'s
`watergateNN`/`water_control` fields where populated (mostly null) or treated as OPEN.

---

## 5. Category D -- dams and reservoirs (storage, inflow, release)

**`hii_dam`** -- `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam`, no
auth, 4 station types (`dam_hourly`/`dam_daily`/`dam_medium`/`dam_small_tele`, 989 rows).
Fields vary BY TYPE -- `dam_storage_percent`/`dam_storage`/`dam_inflow`/`dam_released`/
`dam_spilled`/`dam_level` for the first 3 types; `dam_small_tele` uses a different set
entirely (`percent_storage`/`volume`/`inflow`/`outflow`/`water_level`, plus
`tele_station_lat/_long` instead of `dam_lat/_long`). Derives `<type>_release_m3s_computed
= release_mcm*1e6/86400`, tagged `provenance: "MEASURED-derived"`. **The Chao Phraya Dam
(a diversion weir, not a storage dam) has no entry in this feed** -- confirmed by this
pass (2026-10-05); use `dds_daily_pdf`'s `chaophraya_rows` (RID_CHAOPHRAYA) for its
discharge instead. CALL-PROOF: 11:20:13, 200, 1,050,560 bytes; newest `dam_hourly.dam_date`
= "2026-10-05 10:00" (age ~1h20m); `dam_medium`/`dam_daily`/`dam_small_tele` are date-only
granularity.

**`rid_app_reservoir`** -- `POST https://app.rid.go.th/reservoir/api/dams`, body
`{"date": "<YYYY-MM-DD>"}`, plus a best-effort `GET .../api/alert`. Carries real
`DAM_Lat`/`DAM_Lon` (unlike `rid_res_table`). Fields: `DMD_QUse` (current storage, MCM --
despite the field name looking like a capacity field), `PERCENT_DMD_QUse` (storage %),
`DMD_Inflow`/`DMD_Outflow` (MCM/day). Numbers arrive as STRINGS, and missing is the
literal `" - "` -- never fabricate 0. CALL-PROOF: 11:20:50, 200, 30,301 bytes, `DMD_Date`
"2026-10-05" (today); alert feed 11:20:59, 200, 25 bytes, `{"Dam":[],"Reservoir":[]}` (0
active alerts, not a broken feed).

**`egat_water_crisis`** -- `GET http://water.egat.co.th/water_crisis.php`, HTML table, no
coordinates at all (name-keyed only). Fields: `storage_level_m`, `storage_pct`,
`inflow_today_mcm`, `release_today_mcm` (+ derived m3/s). **Header date on this run was
"04 ต.ค. 2569" (2026-10-04) fetched on 2026-10-05 -- the table reports the PREVIOUS day,
and this collector stamps `observed_at=fetched_at`, not the header date -- a real
under-reported freshness gap, ~1 day stale even when the fetch itself succeeds.**
CALL-PROOF: 11:20:12, 200, 29,772 bytes, 17 dams.

**`rid9_chonburi_rpt`** -- Chonburi/Rayong/Chachoengsao/Prachinburi (eastern seaboard),
**NOT the Chao Phraya basin** this repo otherwise serves. `GET http://irrigation.rid.
go.th/rid9/rid9_new/rpt_show.php?dateid=<Buddhist-Era YYYYMMDD>`. CALL-PROOF: 11:20:25,
200, 259,889 bytes, dateid=25691005, 61 rows.

**`hii_reservoir_metadata`** -- static CSV, 65 small reservoirs, survey-dated (not a live
reading). CALL-PROOF: 11:20, 200, 16,127 bytes.

**`rid_res_table`** (category H) -- `GET http://water.rid.go.th/flood/flood/res_table.htm`
is a NAME LIST ONLY -- no numeric value, no coordinate anywhere on the page (confirmed by
reading the full decoded HTML, cp874 encoding). Not usable as a reading source at all.

---

## 6. Category E -- rain observed

**`thaiwater_rain_24h`** -- station key `station.id`, KG node class
`gauge:thaiwater_rain:<station.id>` (no canonical KG node assigned yet -- this manual's
own proposed pattern). `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/
rain_24h`, no auth, nationwide, 4552 stations (mixed agencies -- TMD/RID/HII feed the
SAME endpoint; there is no separate BMA-only rain feed, see below). Value fields:
`rain_24h` (mm, rolling 24h accumulation window), `rain_1h` (mm, rolling 1h window,
absent on a variable, often large fraction of rows -- ~60% on 2026-10-05 -- never fabricate as 0). **No `rain_3h`/`rain_7d`/`rain_monthly`
field exists anywhere in this API family** (MEASURED, confirmed by this repo's own prior
probe and re-confirmed by reading the live schema this pass -- only the two accumulation
windows exist). Observation time: `rainfall_datetime` (Bangkok local). Freshness:
`max_age_hours=24`. CALL-PROOF: 2026-10-05 11:20:07, HTTP 200, 4,628,300 bytes, newest
"2026-10-05 11:00" (~20min old).

```text
GET   api-v3.thaiwater.net/.../public/rain_24h          params: none
READ  data[].rain_24h -> value (mm, 24h window); data[].rain_1h -> value (mm, 1h window)
READ  data[].rainfall_datetime -> observed_at
MAP   -> reading{station_id=data[].station.id, source="thaiwater_rain_24h",
                 agency_status_word=null (no status word on this feed)}
```

**BMA-specific rain gauge** -- **no separate feed found.** `weather.bangkok.go.th` (the
BMA Watermap/Klongmap host) carries water-LEVEL endpoints only; this pass found no
dedicated BMA rain-gauge JSON endpoint on that host (checked via the same JS-bundle read
used for the StationDetail graph hunt -- no `rain`/`Rain` route found alongside
`Klongmap`/`PageMap`/`StationDetail`). BMA's own rain gauges are folded into
`thaiwater_rain_24h` (many stations there carry a BMA/DDS agency tag) and into
`dds_daily_pdf`'s `rain_stations[]` section (per-district daily total, see category G).
State this plainly as OPEN rather than inventing a BMA-only rain URL.

**TMD (Thai Meteorological Department) observations** -- **no public endpoint reachable
without a key.** `tmd_opendata` (registry id) is `auth: api_key`, `key_env:
TMD_OPENDATA_API_KEY` -- not configured in this environment, not called (honest gap,
consistent with every other key-gated source in this manual). `tmd_main_site` is an HTML
site, not an API, and was not probed this pass (registry marks it "not in this pass").
**If a reader needs TMD's own rain numbers specifically (not the HII-republished feed
above), they need `TMD_OPENDATA_API_KEY` first.**

**`nasa_power`** -- station key: fixed point (`"sammakorn"`), no real gauge. Daily
bias-corrected rain (`PRECTOTCORR`), NASA reanalysis -- NOT a Thai agency, NOT an
observation in the normal sense (it's a reanalysis product with a processing lag). Fill
value **-999.0** for days not yet processed upstream -- on this live run the last **4**
of 8 requested days were fill-value (registry documents "last 1-3 days" as the norm;
today's run showed a 4-day lag, worth flagging). CALL-PROOF: 11:22:12, 200, 620 bytes.

---

## 7. Category F -- forecasts (rain per model, discharge)

15 sources here, all `third_party` (Open-Meteo, MET Norway, NASA, NOAA, GDACS) -- **none
is the Thai Meteorological Department (TMD)**. All are RELAYED model output, no auth,
documented in the master table with full call-proof.

**Issue time vs. valid time (applies to every source in this category):** every record's
`observed_at_utc` this repo stores is the row's own forecast TARGET date/hour (the "valid
time"), converted from the Open-Meteo/MET-Norway local string -- it is NEVER the moment
the model was run (the "issue time"), which none of these APIs publish per-call. A reader
must not treat a forecast row's timestamp as "when this was measured" -- it is "the hour
this number describes," always in the future (or very recent past) relative to the
model's own last run, tagged `third_party`/RELAYED, never VERIFIED-as-fact about real
rain that fell.

**Licence/attribution:** data **CC BY 4.0** (attribution required); free API tier
non-commercial per Open-Meteo's own published terms (RELAYED) -- this repo's registry marks
every `openmeteo_*` entry `unresolved: true` (RELAYED, not independently re-read against
the formal licence text by every pass). ERA5 (feeding `openmeteo_archive_precip`) and
GloFAS (feeding `openmeteo_flood`) are **Copernicus** products -- Copernicus's own licence
is also attribution-required, open use; same RELAYED posture here (this repo has not
independently re-read Copernicus's licence text either). MET Norway's Locationforecast
is the one source in this category with a **VERIFIED** licence tag (CC-BY-4.0, read
directly off MET Norway's own published terms per the registry note).

**How FloodConnect uses multi-model forecasts: worst-first, never averaged.** Where
several models disagree (`openmeteo_forecast16d`'s 9 models, `openmeteo_multimodel`'s 6,
`openmeteo_ensemble_daily`'s 31-member GEFS), the correct reading discipline is to surface
the HIGHEST (worst-case) precipitation value across models/members for a hazard trip-wire,
never a mean -- averaging a 9-model spread launders away the one model that is warning
loudest. This is this manual's own stated discipline (consistent with BOT!=ZERO's spirit
of never laundering a real signal into a softer blended number); `floodconnect_model.py`
does not currently implement a named worst-first aggregator -- OPEN, do not cite one that
doesn't exist in code.

**TMD forecasts/warnings** -- same honest gap as category E: `tmd_opendata` needs
`TMD_OPENDATA_API_KEY` (not configured, not called); no free/no-key TMD forecast endpoint
was found reachable in this pass.

**HII/thaiwater rain forecast (twa.thaiwater.net)** -- this pass (2026-10-05) enumerated
the `twa.thaiwater.net` JS bundle (station modal, trend field, chart endpoints) once,
reused in section 10's series hunt below rather than fetched twice; the ONEMAP/WRF-style
forecast specifically has no confirmed endpoint here -- OPEN.

Highlights (full field tables/pitfalls/call-proof for every F-category source are in the
master table, section 1):

- **`openmeteo_forecast16d`** -- 9 deterministic models at once (`&models=ecmwf_ifs025,
  gfs_seamless,icon_seamless,jma_seamless,gem_seamless,meteofrance_seamless,ukmo_seamless,
  knmi_seamless,cma_grapes_global`), 16-day daily `precipitation_sum`.
- **`openmeteo_ensemble_daily`** -- real 31-member NOAA GEFS ensemble spread (member00-31),
  distinct from the 9-model deterministic spread above -- do not conflate the two kinds of
  "spread".
- **`openmeteo_flood`** -- GloFAS daily river discharge (m3/s) at fixed upstream points
  (Nakhon Sawan, Chao Phraya Dam, Sammakorn, Bang Sai). **A model grid-cell value, never a
  substitute for `hii_waterlevel_load`'s real gauge `discharge`.**
- **`metno_locationforecast`** -- the one genuinely independent (non-Open-Meteo) pipeline,
  CC-BY-4.0, requires only an identifying `User-Agent` string (not a key).
- **`gdacs_events`** -- country-level trip-wire only, `country=` filter does NOT work
  server-side (confirmed: must filter client-side). Found 2 active Thailand flood events
  live, one brand-new (`from_date=2026-10-05`) not present in the registry's last capture.

Full field tables, pitfalls and call-proof rows for every F-category source are in the
master table (section 1).

---

## 8. Category G -- official bulletins and warnings (DDS etc.)

**`dds_daily_pdf`** -- `GET https://dds.bangkok.go.th/public_content/files/001/
0004901_1.pdf`, BMA's daily situation bulletin (rain + canal levels + Chao Phraya
discharge + tide + reservoirs, all in one PDF). Parsed via `pdftotext -layout`. CALL-PROOF
(2026-10-05 11:21:16): HTTP 200, 2,022,617 bytes; header "ประจำวันจันทรที่ 5 ตุลาคม 2569
(ฉบับที่ 277/69)" confirms issue 277/69, **same-day bulletin**. Canal section sample:
"ปตร.คลองสองสายใต +1.80 +1.88 +1.81 ระดับน้ำวิกฤติ" (critical=+1.80, today_0700=+1.81,
status "critical level"). Pitfall: Thai tone marks get remapped to PUA codepoints by
`pdftotext` on this specific file -- kept verbatim, never "corrected". Pages 4-6 are
raster images (OPEN, no OCR).

**`dds_tide_pdf`** -- yearly PREDICTED tide table (Royal Thai Navy Hydrographic Dept,
Navy HQ station). Not an observed reading -- pair with `dds_daily_pdf`'s
`tide_dedicated` section for the OBSERVED AM/PM levels. CALL-PROOF: 11:21:18, 200,
178,562 bytes, confirmed covering calendar year 2026.

**`dds_flood_report`** -- per-road flood height/duration HTML table, no station code (rows
keyed by district/road/area text). CALL-PROOF: 11:21:13, 200, 84,929 bytes, 2 real flood
rows this run (one still-flooded, `flood_end=None`, never fabricated).

---

## 9. Category H -- catalogue-only / login-gated / not usable, with the reason

| source_id | reason |
|---|---|
| `rid_res_table` | name list, no numeric value, no coordinate at all |
| `bma_pumphistory` | HTTP 404, confirmed dead twice live; lead to `bmawaterflow.bangkok.go.th` found but not yet a working replacement |
| `dds_nowcast_gif` | binary image, never parsed into any field |
| `hii_analyst_cctv`, `bangkok_ckan_portal` | catalog/document listing, not a numeric reading (in collect.py's own `CATALOG_ONLY_NOT_IN_REFRESH`) |
| `hii_mou_station_metadata`, `hii_water_level_catalog`, `hii_reservoir_metadata`'s siblings, `dnp_yom_basin_telemetry`, `pcd_mwqi`, `dmcr_marine_acidification`, `pcd_coastal_marine_quality`, `royalrain_operations`, `royalrain_agriculture_rainfall` | static/annual/event-driven catalogs, nationwide but outside this repo's served Chao-Phraya-basin areas (`AREA_RELEVANT_SOURCES` empty-set entries) |
| `google_flood_hub_api`, `nasa_lhasa_landslide_nowcast`, `gfw_data_api`, `cds_era5_reanalysis` | needs an API key not configured in this environment (verified via `env`); 3 of these are pilot/waitlist, not instant self-service |
| `opentopography_copernicus_dem_glo30` | needs a key (instant self-service exists, but none configured here); even with a key, returns a raw GeoTIFF, not a field-level reading |
| `reliefweb_api_v2` | needs a free `appname` registration, not instant, none configured |
| `gistda_flood_extent_api` | needs `GISTDA_API_KEY`, none configured; the only observed real response against THIS endpoint (2026-09-27, a non-owned key) was HTTP 403 `REFERER_REQUIRED` |
| `governor_shared_flooded_roads`, `rtsd_2010_ground_level_map`, `rid_flood_risk_map` | static reference assets / manually relayed links, no fetcher by design |
| `social_listening_google`, `social_listening_paste` | imported via `social_listening.py`'s own CLI, not a `collect.py` fetcher |
| `tmd_opendata`, `data_go_th_ckan`, `gistda_portal`, `ddpm_portal`, `mwa_chaophraya_bigdata_api`, `mwa_chaophraya_level_csv`, `tmd_main_site`, `dwr_ews_rain_daily`, `dwr_main_site`, `marine_imis`, `marine_elaws` | registry rows with no `collect.py` fetcher wired at all as of this pass -- not investigated live here |

---

## 10. The per-station graph / series hunt (founder priority, 2026-10-05)

**Founder's hypothesis:** every BMA canal already has a chart showing rate of rise, and
there must be an API call behind it. **Finding, this pass (read-only, ≤1 req/s/host, no
auth):**

- **BMA `weather.bangkok.go.th/water/StationDetail?id=<n>`** -- confirmed real per-station
  page with a "กราฟระดับน้ำ" (water-level graph) section + a DataTables table
  ("ตารางข้อมูลระดับน้ำย้อนหลัง", with Copy/CSV buttons) below it. **id=88** ("คลองแสนแสบ :
  จุดวัดคลองแสนแสบ ช่วงซอยเสรีไทย 24", warning 0.35 / critical 0.45 ม.รทก.) has **576
  `Date.UTC()` calls embedded in the page** -- confirms a real, populated, roughly-2-day
  history IS server-rendered inline for this station. The simpler `GraphOnIframe/
  Index?id=<water_id>&countwl=<countWaterId>` endpoint (same site, different route) was
  checked for WL.SMK.01 (`id=284`) and was **EMPTY** (`appl = []`) -- and no station in
  the live `PageMap/GoogleMap` payload had `series>0` at fetch time, so that lighter
  endpoint is not currently a working series source for any station, even though the
  heavier `StationDetail` page is.
- This same pass (2026-10-05) isolated the exact inline-array field path, sampling
  interval, and span for `StationDetail?id=88`, found WL.SMK.01's own StationDetail id
  (284), and did the same hunt on `twa.thaiwater.net`'s station modal (which shows a
  verbatim agency trend field, "-0.17%", for station G07003-T.10) -- see the "-0.17%"
  paragraph below for that finding.
- **`bmawaterflow.bangkok.go.th`** (the `water_url` lead) -- confirmed a Vue/axios
  single-page app shell, HTTP 200, but the actual data-fetch call was not resolved in one
  GET of the HTML shell (client-side routing). OPEN.
- **thaiwater per-station graph** -- `public/waterlevel_load` (documented in category A)
  is the only candidate found and it does **not** return a multi-tick series (one row per
  station regardless of date range, confirmed twice). Whether `twa.thaiwater.net`'s own
  station-modal chart calls a DIFFERENT endpoint than `waterlevel_graph` (below) remains
  OPEN.

**Findings, this pass (2026-10-05, MEASURED):**

**(1) BMA `StationDetail?id=<water_id>` -- confirmed series, 5-minute steps, ~2 days.**
No XHR -- the series is rendered server-side inline inside a `<script>` block as
`Highcharts.chart()` data, literal `[Date.UTC(Y, M0, D, h, m, s), value]` pairs. **`M0` is
0-indexed JS-style -- the real calendar month is `M0+1`** (MEASURED 2026-10-05: the
fixture's literal month digit "9" means October, not September -- a caller that stores
`M0` as the month without the `+1` silently shifts every reading one calendar month into
the past). **The timestamps are Bangkok LOCAL wall-clock written into
`Date.UTC` -- treat as `+07:00`, never shift as if already UTC.** Values in ม.รทก. (MSL).
`id` is looked up by joining against `bma_watermap`'s own `water_id` field (the same POST
as category B) -- confirmed: WL.SSB.08 -> id 88, **WL.SMK.01 -> id 284**, WL.BMA.02 ->
id 288. The page's own `#txt_warning`/`#txt_critical` form fields are EDIT-FORM DEFAULTS,
not the authoritative threshold -- always read warning/critical from the `bma_watermap`
POST payload instead, never from this page's form fields. CALL-PROOF (WL.SMK.01, id=284):
2026-10-05 11:24:38 +07:00, HTTP 200, 480,017 bytes, 575 points, 5-minute steps, span
confirmed **2026-10-03 11:30 through 2026-10-05 11:20** (~2 days) in this capture, newest
point 11:20.

```text
GET  weather.bangkok.go.th/water/StationDetail?id=284         (no params beyond id)
READ inline <script> Highcharts series array: [Date.UTC(Y,M0,D,h,m,s), value_m]
MAP  -> observed_at = Y-(M0+1)-D Th:m:s+07:00     # month is 0-indexed, Bangkok local
     -> series{station_code:"WL.SMK.01", ticks:[{observed_at_utc, value}],
                declared_tick_spacing_minutes: 5}
```

**(2) thaiwater `public/waterlevel_graph?station_id=<int>&start_date=&end_date=` -- OPEN.**
Returns a real 15-min time grid shape (`GET https://api-v3.thaiwater.
net/api/v1/thaiwater30/public/waterlevel_graph?station_id=160&start_date=2026-09-01&
end_date=2026-10-05`, Christian-era dates -> `data.graph_data[]`, each `{datetime, value,
value_out, discharge}`, a 34-day span in one call) -- but **every `value` sampled was
null for every HII station checked (160, 48), re-checked again this pass (2026-10-05
11:29:53, HTTP 200, 256,566 bytes, 3,310 points, all-null)**, and a RID station such as
C.67 (`station.id=1095849`) returns HTTP 500 ("index out of range"). **A populated series
via this endpoint is NOT confirmed.** For a RID station, the only fallback is the
snapshot's own `waterlevel_msl_previous` (exactly one prior tick, k=1 only -- still
`SPARSE_SERIES` for anything needing 3+ points).

```text
# if a populated series is ever confirmed for this endpoint:
GET  api-v3.thaiwater.net/.../public/waterlevel_graph    params: station_id=<int>,
                                                                   start_date=YYYY-MM-DD,
                                                                   end_date=YYYY-MM-DD
READ data.graph_data[].datetime  -> observed_at (CE, Bangkok local)
READ data.graph_data[].value     -> value (m)
READ data.graph_data[].discharge -> discharge (m3/s, HII stations only)
MAP  -> series{station_code:<station_id>, ticks:[...], declared_tick_spacing_minutes: 15}
```

**The "-0.17%" agency trend field (twa.thaiwater.net station modal)** -- **no explicit
field found carrying this value in any keyless endpoint.** The keyed endpoint
`/v2/waterlevel/list` carries `percentageDiff` (the agency trend field, RELAYED; not
called by this repo -- see section 9a); no keyless field carrying this specific "-0.17%"
modal value was found this pass. Whether the modal value is the keyed
`percentageDiff` is OPEN.

**twa.thaiwater.net's 4-dam panel** -- exact REST path still **OPEN** (client keys
`summary_4_dam` / `summary_4_dam,graph,<range>` fetched via react-query, resolved
endpoint not yet confirmed in this pass). Known fields from the client bundle:
`waterUsePlan`, `summary.measureUsesWater`, `damDate`, `totalMeasureUsesWater`,
`totalMeasureInflowAcc`, `totalMeasureReleasedAcc`. "ต้องการน้ำเก็บกักเพิ่ม" (additional
storage needed) is computed client-side as `waterUsePlan - measureUsesWater` -- not an
agency field either.

**`public/waterlevel_load` -- re-confirmed NOT a series** (app bootstrap + scale metadata
only, consistent with category A's own finding above).

**G07003-T.10** (the twa.thaiwater.net example station, "บ้านวัดพระรูป") is **NOT present
in the 807-station `public/waterlevel` snapshot** -- OPEN, a different station universe
or a since-rotated station code; do not assume it is reachable via `thaiwater_waterlevel`.

**Conclusion for rate/acceleration:** the agencies DO supply a real per-station series at
BMA StationDetail (5-min steps, confirmed populated for at least ids 88 and 284) --
`delta_k`/`time_to_threshold` (PROP-FLOOD-01/02, PROPOSAL tier) can be computed from that
real agency series rather than guessed, for stations reachable by that one path.
`waterlevel_graph` is OPEN, not a confirmed series source (see (2) above). Every OTHER
source in this registry remains `SPARSE_SERIES` as stated above -- this is a real,
bounded improvement at one path, not a blanket fix.

---

## 11. NORMALISE TO MODEL INPUT

**This library invents no new format.** The one record every source maps into is this
repo's own `observations` SQL table (`store.py`, `CREATE TABLE observations`), expressed
as JSON Schema at `schemas/reading.schema.json`. Fields the founder asked about that are
NOT columns (`agency`, `province`, `water_body`, `kind`) are not stored directly -- they
ride in `provenance_json` (per-source MAPPING TABLE below) or are derivable by joining
`source_id` against `sources/registry.yaml`. See that schema file for the full field-by-
field "which code reads this" trace.

For rate/acceleration/ETA inputs, see `schemas/series.schema.json` -- and read section 1/6
above first: **almost no source in this registry currently supplies a true series**; the
schema documents the shape a caller needs, and the refusal code (`SPARSE_SERIES`) to use
when fewer than 2 (rate) or 3 (acceleration = PROP-FLOOD-11, registered but not
implemented in this release, v0.2 target -- never computed on this answer
path) ticks exist.

### 11.1 Per-source mapping table (selected; full set follows the same pattern -- see each
collector's own insert call in `collect.py` for the ones not listed)

| source | raw field | canonical field | unit conv. | datum note |
|---|---|---|---|---|
| `thaiwater_waterlevel` | `waterlevel_msl` | `value` | none (already m) | MSL |
| `thaiwater_waterlevel` | `station.min_bank` | `bank` | none | MSL, same as value |
| `thaiwater_waterlevel` | `station.critical_level_msl` | `critical` | none | MSL |
| `thaiwater_waterlevel` | `station.ground_level` | (provenance only, NEVER `bank`) | none | **different datum -- do not mix** |
| `thaiwater_waterlevel` | `situation_level`/`diff_wl_bank_text` | `status` (via `_thaiwater_status_word`) | n/a | verbatim agency word/code |
| `bma_watermap` | `wl_in` | `value` | none | station-local gauge zero |
| `bma_watermap` | `right_bank`/`left_bank` | `bank` (pick nearer the community) | none | same as `wl_in` |
| `bma_watermap` | `critical` | `critical` | none | same as `wl_in` -- WL.SMK.01: critical=0.44=right_bank |
| `bma_watermap` | `site_timestampTH` | `observed_at_utc` | BE year -543, Bangkok local -> UTC | Thai Buddhist Era string |
| `bma_watermap` | `txtStatus` | `status` | n/a | verbatim Thai agency word |
| `hii_dam` | `dam_storage_percent` | `value` (variable=`<type>_storage_pct`) | none | % of capacity |
| `hii_dam` | `dam_released` | `value` (variable=`<type>_release_mcm`) + derived `..._m3s_computed` | `*1e6/86400` for the derived field, tagged MEASURED-derived | MCM/day -> m3/s |
| `dds_daily_pdf` | canal `today_0700_m` | `value` | none | 07:00 Bangkok snapshot |
| `dds_daily_pdf` | canal `status_th` | `status` | n/a | verbatim |

### 11.2 Worked example per category

**A (river level):** raw `thaiwater_waterlevel` record for station `C.67`
(`waterlevel_msl="5.49"`, `station.min_bank=2.75`, `situation_level=5`) -> normalised
reading `{"source_id":"thaiwater_waterlevel","station_code":"C.67","variable":
"waterlevel_msl","value":5.49,"unit":"m","bank":2.75,"status":"thaiwater_situation_5",
"observed_at_utc":"2026-10-05T03:00:00Z","trust_tier":"official_telemetry"}` -> model call
`floodconnect_model.classify("thaiwater_situation_5")` -> `"RED"` (via `STATUS_TO_LEVEL`).

**B (pond):** raw `bma_watermap` WL.SMK.01 record (`wl_in=-0.45`, `critical=0.44`,
`txtStatus="ปกติ"`) -> normalised reading `{"station_code":"WL.SMK.01","variable":
"canal_water_level_m","value":-0.45,"unit":"m","critical":0.44,"bank":0.44,
"status":"ปกติ","observed_at_utc":"2026-10-05T04:15:00Z"}` -> `classify("ปกติ")` ->
`"GREEN"` (via `NORMAL_LIKE_STATUS`).

**D (dam):** raw `hii_dam` Sirikit record (`dam_storage_percent`, say 80.74 from
`egat_water_crisis`'s cross-check) -> normalised reading, variable=`dam_hourly_storage_pct`
-> no `classify()` call exists for dam storage in `floodconnect_model.py` today (OPEN --
this repo's `one_decision` is water-level/threshold-shaped, not dam-storage-shaped; do not
fabricate a dam-colour function that doesn't exist).

### 11.3 Tests

`tests/test_api_manual.py` validates the `bma_watermap` and `thaiwater_waterlevel`
fixtures against `schemas/reading.schema.json` after running each through the mapping
table above, checks that the normalised records produce the SAME colour as
`floodconnect_model.classify()` already gives for the same raw status word, converts the
`bma_station_detail` series fixture (month+1, +07:00) and validates it against
`schemas/series.schema.json`, and validates a `ring_readout` built from the
`bma_watermap` fixture. It does not claim to validate every fixture in this pass against
every schema -- see the test file itself for the exact set covered.

---

## 12. From readings to the Jev Sandwich Decision

**UPDATE (v0.1.5, 2026-10-06/07, reconciled against the shipped code): the
status paragraph immediately below is a DATED snapshot of the M7a pass
(2026-10-05), BEFORE the M8 build. It is no longer current.** As of this
release, the Choice/Score/Noul/gate Jev ENVELOPE IS implemented and IS on the
answer path -- see `kb._build_jev_decision` (`choice`, `score`, `noul`, `gate`
fields) and `schemas/jev_decision.schema.json`; the smoke test's
`jev_decision` output carries it. The `ring_readout`/`sandwich_readout`
schema files this section describes below are RETIRED and were never shipped
-- the real runtime shape is `schemas/layer_readout.schema.json` /
`schemas/sandwich_trace.schema.json` (see the "Note on what actually ships"
paragraph below, which is still accurate). The rest of this section is kept
as a historical record of the M7a-era input shape, not a current status
claim.

**Status as of the M7a pass, 2026-10-05 (historical; per `ARCHITECTURE.md`'s
own "Reality check" table, lines ~266-269): the full D1-D8 / Jev envelope
(Choice/Score/Noul/gate) was a v0.2.0 DESIGN TARGET, not implemented in
`kb.py answer` at that time.** This section documents an INPUT shape toward
that envelope -- it did **not** implement decision logic at the time it was
written, per the founder's explicit scope decision (section 14).

`schemas/ring_readout.schema.json` defines one record per Sandwich-Zoom ring (Z0 the point
itself / Z1 canals near it / Z2 water area above it / Z3 basin above it). **Z0-Z3 are the
founder's own Jev Sandwich rings** (verbatim Thai terms given at the top of this manual's
"Fetch order -- Jev Sandwich (S0-S8)" section); the edge families and hop caps used to walk
each ring are defined once, in that section's S1 step and in
`sources/sandwich_fetch_order.yaml`'s `edge_families`/`rings` blocks -- hop caps there are
tagged `hop_caps_tag: INSTINCT` (this library's own default, not founder-confirmed or
code-enforced), never restated or re-derived here. The ring-to-KG-edge mapping in this
schema only names edge kinds that really exist in `tools/kg/build_kg.py` (`WATER`,
`LOCATED_ON`, `ON_REACH`, `DRAINS_TO`, `IN_BASIN`, `IN_SUBBASIN`) -- `canal`/`canal_node`
are KG NODE kinds, never listed here as an edge kind.

**Note on what actually ships:** `schemas/ring_readout.schema.json` and
`schemas/sandwich_readout.schema.json`, as described in this section, are NOT shipped
schema files in this repo. The rich per-ring shape documented here (`worst_status`,
`freshness`/`coverage`, `trend.tag`, `acceleration`, `eta_to_bank`, `end_state`,
`not_joined`, `kg_traversal`) is kept as fetch/traversal documentation only. What the
running code actually validates against is `schemas/layer_readout.schema.json` (a bare
`{Z0,Z1,Z2,Z3}` object whose values are only `colour5` strings) and
`schemas/sandwich_trace.schema.json` (`steps`/`reasons`/`needs_middle`/`mid`). Do not
expect a caller to receive the richer object described above.

**Worked example (Sammakorn, from the real WL.SMK.01 fixture captured this pass, 2026-10-05):**
Z0 reading = WL.SMK.01 (`value=-0.45`, `critical=0.44`, `h - critical = -0.89`, well below
critical, status "ปกติ") -> ring readout `{"ring":"Z0","station_ids":["WL.SMK.01"],
"worst_status":{"status":"ปกติ","source_id":"bma_watermap"},"closest_to_bank":
{"station_code":"WL.SMK.01","h_minus_bank":-0.89,"h_minus_critical":-0.89},
"trend":{"value":"NO_READOUT","tag":"PROPOSAL","basis":"bma_watermap carries no tick
series"},"eta_to_bank":{"tag":"REFUSED","refusal_code":"SPARSE_SERIES"},
"acceleration":{"value":null,"tag":"REFUSED","refusal_code":"SPARSE_SERIES"},
"end_state":"UNKNOWN","freshness":{"fresh_count":1,"total_count":1},
"coverage":"1/1 stations fresh","s4":"BOT"}` (NO_READOUT forces end_state UNKNOWN and
s4 BOT -- UNKNOWN != SAFE, never QUIET/GREEN, even though a real fresh reading exists and
is below threshold; `bma_station_detail` at `StationDetail?id=284` DOES have a real
series for this exact station -- see section 10 -- a caller that fetches it instead would
compute a real trend rather than refuse). Separately, `floodconnect_model.one_decision()`'s
own existing fields (not part of this ring_readout object) still give `level="GREEN"`,
`gate="LICENSED_WITHIN_ENVELOPE"`, `confidence="HIGH"` from the official-status path
alone, since `txtStatus` is present and fresh -- the ring's trend/s4 (series-based) and
`one_decision`'s level (status-word-based) are two separate dimensions, never conflated.
(Historical note on the Choice/Score/Noul/gate ENVELOPE wrapper, ARCHITECTURE.md
section 5: it was a v0.2.0 design target at the time this worked example was
written; see the UPDATE note at the top of this section for its current,
shipped status.) This worked example fills only the fields `one_decision()`
computed at the time it was written.

This worked example is documentation only, built from the real captured WL.SMK.01
fixture -- there is no shipped schema file to validate it against (see the "Note on
what actually ships" above); `tests/test_api_manual.py` checks the manual's content and
structure, not this object's shape.

**Known gap, recorded honestly (MEASURED, live Jev Sandwich run 2026-10-05 11:31-11:35 at
หมู่บ้านสัมมากร): the knowledge graph has NO node for WL.SMK.01, WL.BMA.02, or WL.SSB.13
today.** These stations are `NOT_JOINED` -- a real reading exists (`bma_watermap`,
`bma_station_detail`), but there is nothing in the KG to walk a ring from or to. This is a
KG-build gap, not an API gap, and belongs to a follow-on milestone (M7b) -- this manual
documents the live sources correctly either way; it does not fabricate a KG node to paper
over the gap.

---

## 13. Recipes

**"Is this station over the bank now?"** -> fetch the owning source (category A/B),
compare `value` against `bank`/`critical` on the SAME row, AND check `status`/
`diff_wl_bank_text` for the agency's own overbank word -- an agency word always outranks
a locally-computed comparison (same priority order as `floodconnect_model.one_decision`'s
official-status-first rule).

**"List over-bank/critical stations in my Z1/Z2/Z3."** -> the hotspot filter (below),
scoped to the KG-connected station set for that ring (S1 / `sources/sandwich_fetch_order.yaml` rings).

**"Get a level series for rate/acceleration."** -> read section 6/10 first: almost
nothing in this registry has a real series. `bma_station_detail`'s `StationDetail?id=<n>`
page is the one confirmed-populated lead (per-station, not universal) -- use
`schemas/series.schema.json`'s `SPARSE_SERIES` refusal for everything else, never
interpolate.

**"What pumps/gates near me are running?"** -> `hii_watergate` (`pump_on`/`floodgate_open`,
mostly null in practice) + `bma_watermap` (`watergateNN`, `water_control`) + the static
`bangkok_pump_station_and_floodgate_physical_data`/`bangkok_floodgate_locations` for design
capacity context. `bma_pumphistory` is dead (404) -- do not call it.

### Hotspot query (over-bank / critical filter)

**Canonical predicate: `sources/sandwich_fetch_order.yaml`'s S3 `predicate` string.** The
text below is that same predicate, restated only for readability -- never a second,
separately-maintained version.

```text
is_hotspot(reading) :=
    startswith(diff_wl_bank_text,"ล้นตลิ่ง")   # real string is "ล้นตลิ่ง (ม.)" -- an
                                                # == check would miss it (thaiwater)
    OR situation_level==5                      # agency ordinal overflow code
    OR (value>=bank, same row)                 # over the bank
    OR (value>=critical, same row)              # BMA watermap / bma_station_detail style
    OR classify(status) in [RED, YELLOW]        # floodconnect_model.classify
```

Applied to the KG-connected station set for one ring (Z1/Z2/Z3), using the edge kinds and
hop caps named in S1 / `sources/sandwich_fetch_order.yaml` rings -- this is a filter over readings,
never a new decision engine.

---

## 14. Calling convention -- pseudocode only

**This manual is a calling GUIDE, not a library** (founder scope decision, 2026-10-05:
"ทำเป็น pseudocode แค่แนวทางการเรียก api ไม่ต้องทำให้แทน" -- pseudocode showing how to
call, do not build it for the caller). No executable wrapper module is shipped by this
pass. Every per-source card above gives its call as GET/READ/MAP pseudocode (no
language-specific snippet) in this same shape:

```text
GET  <url pattern>        params: station_id=<KG key>, start=<YYYY-MM-DD>, end=<YYYY-MM-DD>
READ <json.path.to.value>      -> value
READ <json.path.to.critical>   -> critical
READ <json.path.to.status>     -> agency_status_word   (verbatim, never translated)
READ <json.path.to.time>       -> observed_at
MAP  -> reading{station_id, value, unit, bank, critical, agency_status_word,
                observed_at, fetched_at, source}        (= schemas/reading.schema.json)
```

### Jev Sandwich flow

See "Fetch order -- Jev Sandwich (S0-S8)" at the top of this manual and
`sources/sandwich_fetch_order.yaml`; that section and that file are the only fetch
order -- never a second, separately-maintained one.

Z0/Z1 CAUSE -- thaiwater_rain_24h is NOT fetched by S0-S8 today (design target; would join S2 and raise its budget).
Z3 OUTLOOK -- category-F forecast enters only at S5 (openmeteo_forecast16d, worst-first).
PROP-FLOOD-12 -- name only.

No `govapi.py` or other callable module is part of this delivery -- a prior draft plan to
build one was cancelled by the founder before any file was written, so there is nothing to
remove.
