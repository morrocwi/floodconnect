# BMA weather.bangkok.go.th/water/MapLetLeaf — probe readout (2026-09-27)

`RELAYED` + `MEASURED` mixed doc — tags are per-claim below. Ingest date: 2026-09-27.
Raw archives: `raw/live/bma_maplet/` (`mapletleaf.html`, `water_index.html`,
`pagemap_googlemap.json`, `sample_pagemap_googlemap.json`). Draft parser:
`tools/harvest/bma_maplet_draft.py` (not wired into `collect.py` — draft only, per
task scope).

## คำตอบผู้ก่อตั้ง: "เราเชื่อมหรือยัง"

`VERIFIED` (checked this run) — **ยังไม่เชื่อม (not connected).** Only `bma_pumphistory`
(`/Station/PumpHistory`) is live in `sources/registry.yaml`. `bma_klongmap`
(`/Klongmap/GetDataForUpdate`) is DORMANT (403, 2026-09-26). The page the founder pointed
at, `/water/MapLetLeaf`, no longer resolves under that path (see below) — but its
*replacement*, `/water/` (the same BMA "DDS Water Info System" Leaflet/Google-Maps app),
is live, 200, unauthenticated, and backed by a JSON API that **does carry gate-opening
height** — the one thing nothing else in this repo publishes.

## 1. What the request found

| Step | URL | Method | Result |
|---|---|---|---|
| 1 | `https://weather.bangkok.go.th/water/MapLetLeaf` | GET | `MEASURED` 302 redirect to `/water/` (route renamed/retired server-side, not a block) |
| 2 | `https://weather.bangkok.go.th/water/` | GET | `MEASURED` 200, 1.67 MB HTML — this is the live successor page: BMA Leaflet+Google-Maps water-info map |
| 3 | `https://weather.bangkok.go.th/water/PageMap/GoogleMap` | POST (`payload=TEST_DATA_GOES_HERE`) | `MEASURED` 200, `application/json`, 512 KB, 312 station records |

No 403/reset on this host this run — 3 requests total (1 page-load probe as instructed +
2 more, within the "max 3 more GETs" discovery budget; 1 of the "max 4" data-endpoint
calls). Stopped there because the one ajax call the page's own JS makes
(`RefreshDataMap()` → `$.ajax({url:'/water/PageMap/GoogleMap', type:'POST', ...})`) already
returned the full dataset — no second distinct data endpoint was found in the HTML/inline
JS to justify spending more of the budget. The only other externally-called URL in the
page is `cpudgiapp.bangkok.go.th/arcgis/rest/services/PWD/BMAGI_Basemap_2564/MapServer`
(an ESRI **basemap tile service**, different host, out of scope for this workspace's
BMA-host rule and carries no water data — not called).

**`bma_klongmap` (`/Klongmap/GetDataForUpdate`) was left untouched** — still DORMANT per
its 2026-09-26 403, per the host-safety rule ("stop touching that host" / "no re-probe
without a human decision"). This probe did not re-test it.

## 2. Endpoint: `POST /water/PageMap/GoogleMap`

- Auth: none observed (no cookie/session required for this response; sent generic browser
  UA + Referer `https://weather.bangkok.go.th/water/`, `X-Requested-With: XMLHttpRequest`).
- Request body: `application/x-www-form-urlencoded`, single field `payload`. The page's own
  JS literally sets `var payload = "TEST_DATA_GOES_HERE";` (a placeholder never filled in
  for the "load everything" case) — sending that literal string back returned the full,
  unfiltered 312-record set, so the field appears to be an optional server-side filter
  (by district, most likely) rather than a required key. `INSTINCT` — not reverse-engineered
  further; filter semantics are OPEN.
- Response: JSON array, 312 objects (one snapshot at ~2026-09-27 17:00 Bangkok time), field
  list per object (69 fields):

  `countWaterId, water_id, water_count, water_gate_count, watergate01..watergate06, series,
  district_id, district_name, district_name_en, water_code, water_control, water_name,
  water_name_en, water_shortname, water_shortname_en, water_system_id, water_url,
  rain_expected, riverside, adjust, priorityStatus, latitude, longitude, site_timestamp,
  colorStatus, txtStatus, txtStatus_en, datediffnow, site_timestampTH, site_timestampEN,
  wl_level, wl_pos, wl_pos_name, wl_pos_name_en, wl_in, wl_in_DB, wl_out01, wl_out01_DB,
  wl_out02_DB, wl_out02, left_bank, right_bank, warning, critical, warning_out01,
  critical_out01, warning_out02, critical_out02, max_in_day, max_in_yesterday,
  max_out01_day, max_out01_yesterday, max_out02_day, max_out02_yesterday, status,
  statusColor, river_id, river_name, profile_order, piont, display_graph`

- Station codes: `water_code` uses the **same `WL.xxx.NN` scheme** this repo already
  stores (e.g. `hii_watergate`, `thaiwater_waterlevel`) — `MEASURED` overlap confirmed,
  e.g. `WL.PWT.04` (ประเวศ-ลาดกระบัง), `WL.SSB.09` (แสนแสบ-บางชัน), `WL.LPW.01` (ลาดพร้าว).
  No `ST.SPS.xx` (Sammakorn pump) codes appear in this dataset — those stay
  `bma_pumphistory`-only; this endpoint is water-*level*/gate stations, not pump stations.
- Coordinates: `latitude`/`longitude` populated for essentially every record in the live
  POST response (`MEASURED` — e.g. `WL.PWT.04` → 13.72411, 100.74987), unlike the page's
  static `allData` JS array (304 records, embedded in the HTML, where `latitude`/`longitude`
  are **all null** — that array is metadata-only, real coordinates only come from the live
  POST).
- Refresh cadence: not stated by the server; the page's own JS calls `RefreshDataMap()` on
  a timer — interval not confirmed in this probe (`OPEN`), all 312 records in one snapshot
  carried `site_timestampTH: "27/09/2569 16:55"` or `"...17:00"`, i.e. ~5-minute telemetry
  granularity for the ones that differed.
- Status vocabulary: `txtStatus` ∈ {ปกติ, เตือนภัย, วิกฤต, ขัดข้อง, ขัดข้องชั่วคราว}
  (normal / alert / critical / fault / temporary-fault), `colorStatus` a 5-value hex palette
  matching this repo's own `Water_{Green,Orange,Red,Gray,Blue}.png` icon set used on
  `bma_pumphistory`'s own page — same visual language, different backend table.

### Gate opening height — `MEASURED`, confirmed present

`water_gate_count > 0` for **52 of 312** stations in this snapshot; for those, one or more
of `watergate01..watergate06` carries a numeric height in metres (rounded to 2dp by the
page's own client JS — the raw JSON gives full float precision). Examples pulled directly
from the archived response:

| water_code | water_name (th) | gate reading(s), m |
|---|---|---|
| `WL.PWT.04` | ประตูระบายน้ำ คลองประเวศบุรีรมย์ ตอนลาดกระบัง | `[0.5]` |
| `WL.PWT.03` | ประตูระบายน้ำ คลองประเวศบุรีรมย์ ตอนวัดกระทุ่มเสือปลา | `[4.6, 4.6]` |
| `WL.SSB.09` | ประตูระบายน้ำ คลองแสนแสบ ตอนบางชัน | `[0.0]` (closed) |
| `WL.SSB.04` | สถานีสูบน้ำ คลองแสนแสบตอนคลองตัน | `[7.5, 7.5]` |
| `WL.PKN.01` | สถานีสูบน้ำ พระโขนง | `[0.0, 0.0, 0.0]` |
| `WL.LPW.01` | ประตูระบายน้ำ คลองลาดพร้าว | `[0.0]` |

**This is exactly the gap `docs/LESSONS_nodes_2026-09-27.md` §A and `AGENTS.md` §8 flag**:
gate states (มีนบุรี/ประเวศ-ลาดกระบัง/พระโขนง) are currently **inferred** from level
differences, not measured. `WL.PWT.04` (the Prawet-Lat Krabang gate this repo already
reasons about) has a live, numeric, MEASURED gate-opening reading (`0.5 m`, this snapshot)
in this endpoint. A มีนบุรี-named gate specifically was not found by that Thai substring in
this snapshot (search for "มีนบุรี" returned 0 rows) — the Minburi-area gates in this
dataset are under other names/canal codes (e.g. WL.SSB.* covers คลองแสนแสบ segments through
Nong Chok/Bang Chan which are in/near Minburi district) — needs a district_id cross-check,
`OPEN`, not resolved in this probe.

### "ระดับปกติของแต่ละคลอง — มีในหน้านี้ไหม" (control/normal target level — is it on this page)

`MEASURED`, negative result: the schema **does carry a field for it** —
`water_control` — present on every one of the 312 records, but its value was **`null` for
all 312 records** in this snapshot (`MEASURED`, not `INSTINCT`). So: the field the founder
is asking about exists in BMA's own data model, and is exposed in this same JSON endpoint,
but is **not currently populated** through this API path — `OPEN`, not resolved by this
probe, worth re-checking on a future pull (could be a per-canal admin setting BMA only
fills for some systems, or filled through the `payload` filter parameter we didn't reverse
-engineer, or genuinely unset).

The **closest live substitute** is the `warning` / `critical` pair (also per-record,
non-null for essentially every station) — these are upper-bound alert thresholds, not a
"this is where the canal should sit" target, but they're the only numeric anchor this
endpoint currently gives per canal. Five-canal sample (`MEASURED`, this snapshot,
2026-09-27 ~16:55-17:00 Bangkok time):

| Canal (คลอง) | Station | water_code | wl_in (m) | warning | critical | water_control |
|---|---|---|---|---|---|---|
| แสนแสบ (บางกะปิ) | ตอนสำนักงานเขตบางกะปิ | `WL.SSB.07` | 0.40 | 0.35 | 0.45 | `null` |
| แสนแสบ (หนองจอก, มีนบุรี-adjacent) | สถานีสูบน้ำ คลองแสนแสบ หนองจอก | `WL.SSB.12` | 1.23 | 1.00 | 1.10 | `null` |
| ประเวศ | ประตูระบายน้ำ คลองประเวศบุรีรมย์ ตอนลาดกระบัง | `WL.PWT.04` | 0.80 | 0.40 | 0.60 | `null` |
| ลาดพร้าว | ประตูระบายน้ำ คลองลาดพร้าว | `WL.LPW.01` | 0.62 | 0.20 | 0.40 | `null` |
| บ้านม้า | จุดวัดคลองบ้านม้า ตอนถนนรามคำแหง | `WL.BMA.02` | 0.73 | 2.14 | 2.68 | `null` |

Note the ลาดพร้าว/ประเวศ pair reads as "normal-band-ish" if we treat *below warning* as
normal, while บ้านม้า's own `warning=2.14` sitting far above its live `wl_in=0.73` looks
like a mismatched/legacy threshold for that station (`OPEN` — flagged, not resolved; do not
treat `warning`/`critical` as validated "back-to-normal" numbers without a human check
against BMA's own published criteria, per this repo's Toledo/equation-discipline and
never-fabricate-a-number rules).

**Bottom line for the founder's ask**: no confirmed per-canal "control level" number came
back live in this probe. If BMA ever populates `water_control`, this same endpoint would
carry it with no new integration work — the collector spec below already reads that field
into every observation row so a future non-null value is picked up automatically, tagged
`MEASURED`, without a code change.

## 3. Overlap with existing sources

- **`hii_watergate`** (2,163 gates nationwide, RID's HII feed): publishes gate *identity/
  location* nationwide but **no gate open/close state or opening height** per this repo's
  own registry notes. This BMA endpoint is BMA-only (~300 stations, Bangkok + a few
  adjoining districts) but **does** carry opening height for ~52 of them — complementary,
  not duplicate: HII gives breadth without state, BMA MapLetLeaf-successor gives depth
  (state) for a subset.
- **`bma_pumphistory`**: separate BMA system (pump stations, `ST.SPS.xx` codes, `/Station/
  PumpHistory`), different table/host-path, different code namespace, no gate-height field
  there. No station-code collision observed between the two endpoints in this probe.
- **`bma_klongmap`** (DORMANT, 403): registry marks it `variables: [water_level_m]` only —
  even if it recovers, this MapLetLeaf-successor endpoint already gives a strict superset
  (level in/out, gate height, thresholds, coordinates, status) for the same host family.

## 4. What this would add, concretely

1. **MEASURED gate state** for ~52 named gates/pump-adjacent structures, replacing
   `INFERRED` burden-ledger gate-state reasoning for those specific stations (see
   `docs/LESSONS_nodes_2026-09-27.md` §A) — this is the single biggest upgrade: today
   nothing in this repo publishes gate opening height as a number, this endpoint does.
2. **Real coordinates** for ~300 water-level stations in one call, vs. per-page scraping.
3. **A live warning/critical threshold pair per station**, usable as an interim
   "distance-to-alert" readout even while `water_control` stays null.
4. A **second corroborating water_level reading** on stations this repo may already carry
   from `hii_watergate`/`thaiwater_waterlevel` via matching `water_code` — cross-source
   agreement/disagreement becomes checkable (`OPEN`/`MEASURED` contradiction rows, per this
   repo's never-prune rule).

## 5. Licence / terms

`RELAYED`, unresolved: no dedicated terms-of-use or licence page/text found on
`weather.bangkok.go.th/water/` during this probe (only a generic page-footer "Copyright"
string, no licence terms). Same posture as `bma_pumphistory` in the registry — treat as
RELAYED official telemetry, not confirmed open-data, until a human finds explicit terms.

## 6. Proposed collector spec (draft — not implemented)

- **New source id**: `bma_watermap` (working name; final id to be agreed by whoever owns
  `sources/registry.yaml` — this probe does not edit that file).
- **URL**: `https://weather.bangkok.go.th/water/PageMap/GoogleMap` (POST,
  `payload=ALL` or whatever the eventual reverse-engineered "all stations" value is —
  `TEST_DATA_GOES_HERE` worked in this probe but reads like a placeholder that could change
  server-side; a collector should treat any non-200/non-JSON response as a signal to fall
  back to the last-known-good payload string, not to retry variations).
- **Method**: single POST per run, same header set as this probe (browser UA, Referer
  `https://weather.bangkok.go.th/water/`, `X-Requested-With: XMLHttpRequest`), 20s timeout,
  no retries — same BMA-host rule as `bma_pumphistory`/`bma_klongmap`.
- **Cadence**: align with this repo's then-existing 30-minute `collect.py --all` cycle
  (GitHub Actions) — no evidence the source refreshes faster than that in a way this
  project could usefully consume more often. *(historical note: that 30-minute GitHub
  Actions cadence predates 2026-10-02; as of 2026-10-03, GitHub Actions never runs
  `collect.py` on our runner — it only validates, tests and builds the page from the
  committed snapshot. `collect.py --all` is caller-side only, run on demand on the
  caller's own machine/network/keys, so "cadence" here now means how often a caller
  chooses to run it, not a fixed GitHub Actions interval.)*
- **Fields to store**: `water_code` (station key — join key against `hii_watergate`/
  `thaiwater_waterlevel`), `water_name`/`water_name_en`, `latitude`/`longitude`, `wl_in`/
  `wl_out01`/`wl_out02`, `warning`/`critical` (+ `_out01`/`_out02` variants),
  `watergate01..06` (gate opening, metres — **the new MEASURED field**), `water_control`
  (store even while null — future-proof for when BMA populates it), `txtStatus`/
  `colorStatus`, `site_timestampTH`/`site_timestampEN`, `district_id`/`district_name`.
- **DORMANT handling**: same shape as `bma_klongmap` — if this endpoint 403s/resets on any
  future run, mark `bma_watermap` DORMANT in the registry with the confirmed date, exclude
  it from `collect.py --all`'s default set, and require an explicit `--source bma_watermap`
  human-initiated re-check before it's ever probed again. Do not build a retry loop.
- **Parser**: draft pure functions in `tools/harvest/bma_maplet_draft.py` (this run) —
  `parse_pagemap_stations()`, `gate_stations()`, `find_by_water_code()`. Not wired into
  `collect.py`; that wiring, plus a `tests/` fixture test and a registry entry, is left for
  whoever owns those files (per this repo's one-committing-worker rule — this probe writes
  new files only, does not commit).

---
*Tags used above: `VERIFIED` = checked this run; `MEASURED` = read from this repo's own
archived data; `RELAYED` = from BMA, not independently re-derived; `INSTINCT` = judgment
call; `OPEN` = unresolved. No personal names, no AI/vendor names, no local filesystem
paths in this file.*
