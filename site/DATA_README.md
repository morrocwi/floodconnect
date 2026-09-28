# data.json — field-by-field source map

Built by `build_data.py` (read-only, never fetches the network) from CACHED official
snapshots under this repo's `raw/live/` (produced by `collect.py`, re-fetched every CI run,
never committed) plus the curated compiled files checked into `site/inputs/`. Run:
`python3 site/build_data.py` from the repo root — it also prints the top-level counts
shown at the bottom of this file.

**This is a readout, not a forecast.** No risk score, no formula, no trend arrow, no
"hours to prepare" number is computed anywhere in this file — those need Toledo
registration (PROP-FLOOD-01/02) first. `epistemic_note` in the JSON says this in Thai
for anyone reading the raw file directly.


## Static governance reference (not emitted to `data.json`)

`site/inputs/governance/thailand_water_governance_reference.json` is a curated,
partially-verified institutional map extracted from a third-party civic infographic and
cross-checked against official Thai water-governance sources. It is **context only**:
it is not live telemetry, not a forecast, not an authoritative exhaustive agency register,
and is deliberately kept outside `site/inputs/official/` and `sources/registry.yaml`.
See `docs/THAILAND_WATER_GOVERNANCE.md` for verification notes and provenance.

## Top-level fields

- `generated_at_bkk` — when this script ran, Bangkok local time (UTC+7). Not an official
  reading; just this build's own timestamp.
- `epistemic_note` — the fixed Thai sentence "เป็นการอ่านค่าจากหน่วยงาน ไม่ใช่การพยากรณ์".
- `centre` — หมู่บ้านสัมมากร reference point (13.758235, 100.676084 — จุดอ้างอิงสาธารณะ
  (ที่ตั้งสำนักงานที่เผยแพร่บนเว็บไซต์บริษัท), ซอย 44), used only to compute every
  `dist_km`/`dist_m` in this file.
- `sources[]` — one row per upstream data family actually used, each `{id, agency_th,
  url, fetched_at, trust_tier}`. `fetched_at` is the cached FILE's own mtime (i.e. when
  *that snapshot* was taken), not this build's run time. `url`/`agency_th` for the BMA
  canal/pump/flood-road/DDS sources are copied verbatim from this repo's own
  `floodconnect/sources/registry.yaml` (its `trust_tier` vocabulary is reused
  as-is). The rain (`thaiwater_rain_24h`) source is now collected live every CI run
  (2026-09-26 red-team fix HIGH-3) by `collect.py`'s `collect_thaiwater_rain_24h` and
  registered in `sources/registry.yaml`, so its `url`/`agency_th` are also copied
  verbatim from there.

## `stations_near[]` — BMA canal water-level stations (thaiwater.net, republishing BMA
สำนักการระบายน้ำ กรุงเทพมหานคร)

Two groups, both in this one list, told apart by `role`:
- `role: "north"` / `"south"` — every BMA canal station within `NEAR_STATION_RADIUS_KM`
  = 6 km of the village centre (an engineering choice made in this script, not an
  official radius), split north/south purely by latitude vs. the centre. No canal
  station in this dataset sits inside Sammakorn itself — the village's own two ponds/
  pumps are `pumps[]` below, not here.
- `role: "upstream"` — the 12-row watch-list table from
  `site/inputs/upstream_watchlist.md` §3 ("ตาราง watch-list"), parsed straight from that
  markdown table and joined to the same canal snapshot by `canal_oldcode`. Two codes
  (`BKK013`, `BKK015` — Pathum Thani stations on a different thaiwater.net feed not
  cached in this dataset) have no match; they still appear with
  `value_m/out_m/warning/critical/bank: null`, `status: "NO_THRESHOLD"`, `stale: true`
  and a `note` saying why, never a fabricated reading.

Per-station fields: `value_m` = `canal_value` (metres), `out_m` = `canal_out` (outside-
gate level, gate stations only), `warning`/`critical`/`bank` = BMA's own published
thresholds (`null` when BMA publishes none for that station), `status` = one of
`NORMAL/WATCH/CRITICAL/OVERBANK/NO_THRESHOLD` from **`classify_level()`, imported
unchanged from `floodconnect/live_water_level.py`** (never re-implemented here) —
it only compares one reading against that station's own published bands, it is not a
forecast. `stale` = `true` when `observed_at` is missing or older than `STALE_HOURS` =
2 hours relative to `generated_at_bkk` (this script's own convention, chosen for a
resident-facing page — different from `live_water_level.py`'s internal 24h default).

Canal snapshot used: newest file (by mtime) in
`floodconnect/raw/live/thaiwater_bma/` — **not** a fixed `*canal_waterlevel.json`
glob. Observed 2026-09-26: a later fetch in that same directory dropped the
`_canal_waterlevel` filename suffix while keeping an identical JSON schema, so
"newest file in the directory" is used instead of the literal pattern named in the task
brief — documented here rather than silently deviating.

## `pumps[]` — BMA PumpHistory, Sammakorn's own 4 stations (ST.SPS.01–04)

Parsed via `live_water_level.parse_pumphistory_html`/`load_pumphistory_from_file`
(imported, not copied) from the newest file in
`floodconnect/raw/live/pumphistory/`. `level_m`, `pumps_on`/`pumps_total`, `gate`
(first open floodgate reading, metres, `null` if none), `status_th` (BMA's own Thai
status word, e.g. ปกติ/ขัดข้อง) are the page's own columns, unchanged. `pond_name` maps
each pump code to the retention pond it serves, taken from
`raw/community/soi_tiers_2026-09-26.yaml`'s `pond_rings:` section (`pump:` field per
pond) — ST.SPS.01 has no such mapping in that file (its own name already names the
canal, and the yaml's "บึงรับน้ำสัมมากร 3" node has `pump: null`), so `pond_name: null`
for that one station, not a guess.

## `rain`

Nearest rain-gauge station (by haversine distance) to the village centre, selected from
the newest file in `floodconnect/raw/live/thaiwater_rain_24h/` (written every run by
`collect.py`'s `thaiwater_rain_24h` collector, added 2026-09-26); falls back to
`floodconnect/raw/gapfill/rain_24h_1.json` (newest `rain_24h*.json` in that directory)
only when that live collector hasn't run yet or failed this run. `mm_24h` = that
record's own `rain_24h` field (millimetres, 24h total); `observed_at` parsed from
`rainfall_datetime` (Thailand local time → UTC ISO). No averaging or interpolation
across stations — one real station's own reading only.

## `tide`

`floodconnect/raw/tide/hydro_navy_bangkok_2026.json` (นสน.'s own parse of the
Royal Thai Navy Hydrographic Department's official yearly astronomical-tide PDF,
station กองบัญชาการกองทัพเรือ). `datum`/`prediction_basis` are copied verbatim from
that file's own `meta` block — importantly, the source PDF itself states this
prediction **excludes dam releases and rainfall** ("ไม่รวมน้ำระบายจากเขื่อน และปริมาณ
น้ำฝน") and is astronomical only, not a storm-surge forecast. `next_high` = the next 3
high-water (`HW`) rows after `generated_at_bkk`. `week` = every row in the ±7-day window
around now, grouped by date.

## `flood_roads[]`

`floodconnect/raw/live/thaiwater_flood_road/` (newest file; falls back to
`sammakorn/flood_road.json` if that directory is empty), filtered to
`FLOOD_ROAD_RADIUS_KM` = 5 km of the village centre (fixed by the task brief), sorted
deepest-first. `depth_cm` = the source's own `floodroad_value` field, unit as published
by thaiwater/BMA (not independently re-verified against a unit label — see this repo's
`sources/registry.yaml` note on `thaiwater_flood_road`). A road name ending in `*` is
BMA's own asterisk flag in the source data (meaning noted as "unconfirmed" upstream);
carried through as-is, not stripped.

## `tiers[]` — community-reported onset ladder, T1..T5

Primary path: `raw/community/soi_tiers_2026-09-26.yaml` (newest `soi_tiers_*.yaml`),
read with PyYAML. `label_th` per tier comes from that file's own `tiers_definition:`
block. Each soi's `first_time`/`state`/`depth_cm` come from that soi's
`report_2026_09_26:` node — a same-day community report, tagged RELAYED in the source
file, never a name.

Fallback (only if that yaml is missing, or PyYAML isn't installed): built directly from
`raw/community/low_areas_2026-09-26.csv`'s own `report_time`/`depth_cm` columns, using
the **same T1..T5 wording** as `tiers_definition` (hard-coded once in this script as
`TIER_LABELS_FALLBACK`, kept byte-identical to the yaml's own text) — depth ≥20cm or
time ≤06:00 → T1, ≤08:00 → T2, ≤10:00 → T3, later → T4, no report/time → T5. If neither
file exists, `tiers: []` and `tiers_note` says so plainly.

## `dds_quotes[]`

`pdftotext -layout` on the newest `*.pdf` in `floodconnect/raw/live/dds_daily_pdf/`
(where `collect.py` actually writes the live-fetched PDF every run), falling back to
`floodconnect/raw/dds_reports/dds_daily_*.pdf` only if that live directory is empty
(2026-09-26 red-team fix HIGH-2: the two paths had silently diverged and this reader
was pointed at the wrong one) — BMA's daily situation bulletin, keeping only
lines containing สะพานสูง / แสนแสบ / ประเวศ / น้ำทะเลหนุน / คาดการณ์, each tagged with
its PDF page number (pages are split on pdftotext's own `\f` form-feed). Thai-font
ligature artefacts (stray Unicode Private-Use-Area glyphs observed in this PDF's text
layer) are stripped and whitespace is collapsed; nothing else is altered or summarised —
each `text` is a direct quote. The other two PDFs in that directory
(`dds_tide_times_20260926.pdf`, byte-identical to the tide-table PDF already parsed
into `tide` above, and `dds_water_situation_20260926.pdf`) are **not** re-processed here
to avoid mixing page numbers from more than one document in one flat list — OPEN /
future work if their content is needed too.

## `exits[]`

Both entries are read from `sammakorn/community/community_reports_2026-09-26.md`'s
section "## C. ทางเข้า-ออก" (compiled from the same Facebook-group community reports as
`tiers[]`, no names). "ราม 110" quotes that section's own bullet clause mentioning 110.
"ราม 112" is reported as `OPEN` — no source file in this dataset mentions ซอย/ถนน 112 by
that name; this is stated plainly rather than inferring a status for it.

## `staleness`

`newest_official_obs` = the maximum `observed_at` across every official (non-community)
reading actually included (`stations_near`, `pumps`, `rain`, `flood_roads` — `tide` is
excluded, being a forecast table with no single "observed" timestamp). `banner: true`
when that newest observation is `null` or more than 2 hours old relative to
`generated_at_bkk` — the same fail-closed rule as each row's own `stale` flag.

## Known deviations from the task's literal file-glob spec (both documented, not silent)

1. `raw/live/thaiwater_bma/*canal_waterlevel.json` → this script instead takes the
   newest file in that directory regardless of name, because a real newer fetch on
   2026-09-26 dropped that filename suffix while keeping the same JSON shape.
2. `raw/dds_reports/*.pdf` → only the **daily** bulletin (`dds_daily_*.pdf`) is quoted
   into `dds_quotes[]`; the tide-times and water-situation PDFs in the same directory
   are intentionally left out (see `dds_quotes[]` above) rather than merging three
   documents' page numbers into one ambiguous list.

## Top-level counts from the last run (2026-09-26, printed by `build_data.py`)

```json
{
  "sources": 7,
  "stations_near": 26,
  "stations_near_by_status": {
    "NO_THRESHOLD": 3,
    "CRITICAL": 13,
    "WATCH": 2,
    "NORMAL": 7,
    "OVERBANK": 1
  },
  "pumps": 4,
  "rain": 1,
  "tide_next_high": 3,
  "flood_roads": 11,
  "tiers": 5,
  "tiers_sois_total": 103,
  "dds_quotes": 8,
  "exits": 2,
  "staleness_banner": false
}
```
