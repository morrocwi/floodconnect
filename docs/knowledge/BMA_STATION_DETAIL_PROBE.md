# BMA weather.bangkok.go.th/water/StationDetail — probe readout (2026-09-27)

`RELAYED` + `MEASURED` mixed doc — tags are per-claim below. Ingest date: 2026-09-27.
Raw archives: `raw/live/bma_station_detail/` (`stationdetail_id51.html`, `crossection_id51.bin`
[`image/png`], `switchBasemap.js`, `waterhistory.html`, `waterhistory_post_dry_season_id51.html`,
plus each response's saved headers). Draft parser: `tools/harvest/bma_station_detail_draft.py`
(not wired into `collect.py` — draft only, per task scope). This probe follows on from
`docs/knowledge/BMA_WATER_MAP_PROBE.md` (the `/water/PageMap/GoogleMap` 312-station endpoint) —
read that doc first for the live-status/gate-height endpoint this one complements.

## คำตอบผู้ก่อตั้ง (ต่อจากรอบก่อน): "ระดับปกติของแต่ละคลองมีจริงไหม"

`MEASURED` — **มีจริง.** `PageMap/GoogleMap` exposes a `water_control` field but it was `null`
for all 312 stations in the prior probe. `StationDetail?id={water_id}` (this probe, station
`id=51` = `WL.SSB.12`, สถานีสูบน้ำ คลองแสนแสบ หนองจอก) returns that **same conceptual field,
populated**, at `0.70` m, inside the page's admin-edit form fields (`txt_water_control`) — read
straight off an **unauthenticated GET**, no login needed to view it (only `UpdateStationinfo`,
the write path, is behind `/water/StationDetail/Login`). This is the concrete answer to the
founder's original "ระดับปกติของแต่ละคลอง" question: BMA's own data model has a per-canal
control/target level, it is simply not exposed through the map's live JSON feed — it lives on
each station's own detail page instead.

## 1. Requests made this probe

| # | URL | Method | Result |
|---|---|---|---|
| 1 | `https://weather.bangkok.go.th/water/StationDetail?id=51` | GET | `MEASURED` 200, 960 KB HTML |
| 2 | `https://weather.bangkok.go.th/water/Scripts/SwitchMap/switchBasemap.js` | GET | `MEASURED` 200, 2.5 KB — Leaflet basemap-switcher UI control only, no data endpoints, confirmed by reading the file in full |
| 3 | `https://weather.bangkok.go.th/water/StationDetail/CreateCrossection?id=51` | GET | `MEASURED` 200, `image/png`, 102 KB — canal cross-section drawing, not JSON |
| 4 | `https://weather.bangkok.go.th/water/WaterHistory` | GET | `MEASURED` 200, 919 KB HTML — the real per-station history *search* page (separate app section from `StationDetail`, linked from the same nav menu) |
| 5 | `https://weather.bangkok.go.th/water/WaterHistory` | POST (`water_station=51`, `datePick_start=01/02/2026`, `StationTime_start=00:00`, `datePick_end=31/03/2026`, `StationTime_end=23:55`, `rain_field_selected=0`) | `MEASURED` 200, 919.6 KB — form accepted (result panel's `visibility:hidden` flips to `visible`), but the results `<tbody id="waterhistorybody">` came back **empty** and the JS variable that would fill it (`waterhistoryList`) is hardcoded `const waterhistoryList = null;` in this server-rendered response |

5 requests total, well inside the "max 5" sampling budget (plus 1 of the "max 3" JS-discovery
budget used). No 403/reset on this host this run — stopped deliberately at request 5 rather than
retrying request 5 with a session cookie (the GET in request 4 issued an `ASP.NET_SessionId`
cookie our POST did not carry) — per this workspace's no-retry rule, that is a decision for a
human to make, not this probe to re-attempt.

## 2. Endpoint table

| URL pattern | Method | Params | Returns | Cadence | Licence |
|---|---|---|---|---|---|
| `/water/StationDetail?id={water_id}` | GET | `id` (integer, same key as PageMap's `water_id` field) | Server-rendered HTML: station metadata, admin-edit form values (thresholds incl. **`water_control`**, bank levels), one Highcharts graph with **2 days of 5-minute-interval water-level history baked directly into the page's inline `<script>`** (no separate JSON call), a static `allData` array (~304 stations, metadata-only, `water_code`/`latitude`/`longitude` all null — same shape as PageMap's own static `allData`, not the live layer) | Static per-load; history window is a fixed trailing 2 days, not adjustable via query string (`id` is the only param this page reads) | `RELAYED`, unresolved — no terms/licence text found |
| `/water/StationDetail/CreateCrossection?id={water_id}` | GET | `id` | PNG image, canal cross-section drawing (bed/bank profile) | On demand | `RELAYED`, unresolved |
| `/water/StationDetail/Login` | POST | `user`, `pass` | Admin session (not tested — out of scope, no credentials held by this probe) | n/a | n/a — do not probe further without founder authorization |
| `/water/StationDetail/UpdateStationinfo` | POST | full threshold/metadata field set (write path for the same fields `StationDetail` displays) | Write confirmation (not tested — requires the `Login` session above) | n/a | n/a — write endpoint, never call from a read-only collector |
| `/water/WaterHistory` | GET | none (renders the search form + empty result shell) | Server-rendered HTML search form: `water_station` (dropdown, **same integer id space as `StationDetail`'s `id`** — confirmed: option value `51` labelled "คลองแสนแสบ : ส.คลองแสนแสบ หนองจอก", matching `id=51`'s own station name exactly), `datePick_start`/`StationTime_start`, `datePick_end`/`StationTime_end` (free date-range, format `DD/MM/YYYY` + `HH:MM`, **Gregorian year**, not Buddhist), `rain_field_selected` (0=unfiltered, 1/2/3 = ด้านใน/ด้านนอก/ด้านนอกสุด) | On demand | `RELAYED`, unresolved |
| `/water/WaterHistory` (same URL) | POST | same fields as the GET form | Full-page HTML re-render with a results table (`#waterhistorybody`, columns: รหัส/คลอง/สถานี/วัน-เวลา/ระดับน้ำ ด้านใน-นอก-นอกสุด) and a Highcharts `graphContainer` — **in this probe's one sample (station 51, Feb 1 – Mar 31 2569/2026) both came back empty** | On demand | `RELAYED`, unresolved |
| `/water/languages/{lang}.json` | GET (`fetch`) | `lang` (`th`/`en`), cache-busted with `?v={timestamp}` | UI i18n strings only — confirmed by name (`Menu.drainageoffice` etc used to set nav labels), **not water data** | On demand (client-side language switch) | n/a — static UI asset |

## 3. Why `WaterHistory`'s dry-season query came back empty — three live hypotheses, none resolved

`OPEN`, not resolved by this probe — do not treat any of these as settled without a follow-up
check:

1. **Session/cookie requirement.** The `GET /water/WaterHistory` response set an
   `ASP.NET_SessionId` cookie; this probe's POST (a separate `curl` invocation) did not send it
   back. If the server's search action reads anything from session state (e.g. a
   server-side-cached station list built on the GET), a cookie-less POST could legitimately
   return nothing even with fully valid form fields. **Untested** — testing it means a second POST
   to the same URL, which this probe deliberately declined per the no-retry rule; flagging for a
   human decision, not re-probing.
2. **Retention window shorter than dry season 2569.** `StationDetail`'s own default graph caps at
   a fixed trailing 2 days with no query-string override observed. If BMA's backing store for
   `WaterHistory` also only retains a recent rolling window (weeks, not the ~7 months back to
   February 2569 this probe requested), an empty result for that date range would be the honest,
   correct answer, not a bug in this probe's request.
3. **Field-name mismatch on the actual POST contract.** The visible `<form>` fields
   (`water_station`, `datePick_start/end`, `StationTime_start/end`, `rain_field_selected`) are the
   only named inputs found in the HTML, and `$("#FrmIndex").submit()` is a native (non-AJAX,
   non-intercepted) submit — no evidence of a hidden required field (no anti-forgery token was
   found in this form, ruling out the most common such gap) — but a required field this probe
   didn't spot is not ruled out.

**Recommendation, not yet implemented**: before building a `bma_station_history` collector that
depends on `WaterHistory`, a human (or a follow-up probe with founder sign-off to spend one more
request) should retry hypothesis 1 with a cookie jar and, separately, request a *recent* 2-3 day
range (inside `StationDetail`'s own confirmed-working window) to isolate hypothesis 1 from
hypothesis 2 — a non-empty recent-range result would confirm the endpoint works at all and
narrow the empty dry-season result to "too far back," not "broken."

## 4. Cross-check: `id=51` ↔ `water_code` ↔ PageMap

`MEASURED`, fully confirmed — no ambiguity:

- `StationDetail?id=51` → `txt_water_code = WL.SSB.12`, `txt_water_name = สถานีสูบน้ำ คลองแสนแสบ
  หนองจอก`, `txt_warning = 1.00`, `txt_critical = 1.10`.
- These exact values (`WL.SSB.12`, warning `1.00`, critical `1.10`) already appear, independently,
  in `docs/knowledge/BMA_WATER_MAP_PROBE.md`'s §"ระดับปกติของแต่ละคลอง" five-canal sample table
  from the *other* endpoint (`PageMap/GoogleMap`) — same station, same numbers, two different BMA
  systems agreeing with each other. This is the strongest possible confirmation available without
  a third independent source.
- **`id` is the same integer as PageMap's own `water_id` field** — the join key was already in
  the field list `BMA_WATER_MAP_PROBE.md` recorded (`water_id` is literally the 2nd field in that
  doc's 69-field list). No new field needed to enumerate: pull `water_id` from every
  `PageMap/GoogleMap` record and it is directly usable as `StationDetail?id=`.
- `StationDetail`'s own embedded static `allData` array independently contains `water_id` values
  spanning `0..332` (304 non-null-code... actually all-null-code entries, metadata-only, same
  caveat as PageMap's static array) — consistent with, not larger than, PageMap's 312-station
  live count. No second station's page was fetched to re-confirm this (would have cost another
  request against the same host for a fact already derivable from the one archived sample) —
  tagged `MEASURED` on the one sample, `INSTINCT` that the pattern holds workspace-wide for all
  312 ids.

## 5. What this adds beyond `PageMap/GoogleMap`

1. **`water_control` (ระดับน้ำควบคุม), populated** — `0.70` m for `WL.SSB.12` in this sample. This
   is the single biggest addition: the exact field the founder asked about twice now, unavailable
   live via the map JSON, available per-station via this page.
2. **Bank/bed levels** — `left_bank`/`right_bank` (`1.75`/`1.75` m) and `bed_bank` (`-1.24` m,
   i.e. below the same reference datum) — canal cross-section geometry, not present in PageMap at
   all.
3. **A second, independent outer-canal threshold pair** — `warning_out01`/`critical_out01`
   (`1.40`/`1.60`) alongside the inner-canal pair PageMap already carries — PageMap's own
   `warning_out01`/`critical_out01` fields exist too (per the prior probe's field list) so this is
   corroboration, not a new field, but this page is where a human can *read* it without
   reconstructing it from raw JSON.
4. **Canal cross-section image** (`CreateCrossection`) — a rendered bed/bank profile drawing, a
   presentation asset (PNG), not structured data — noted for completeness, not proposed for
   ingestion into `observations.sqlite` (this repo stores facts/numbers, not images, per its
   existing pattern for `dds_nowcast_gif`).
5. **A real (if currently empty-on-this-sample) per-station history *search* system**
   (`WaterHistory`), independent of `StationDetail`'s own fixed 2-day graph — potentially the path
   to longer-than-2-day history if hypothesis 1 or 2 above gets resolved in a follow-up.

## 6. Proposed collector design (draft — not implemented)

- **New source id**: `bma_station_thresholds` (working name, distinct from `bma_watermap` which
  already covers live status/gate-height/coords — this one is for the mostly-static per-station
  control/bank/bed fields that `PageMap` does not expose). Final id owned by whoever owns
  `sources/registry.yaml`; this probe does not edit that file.
- **URL**: `https://weather.bangkok.go.th/water/StationDetail?id={water_id}` (GET, `id` taken from
  `bma_watermap`'s own `water_id` field — no separate enumeration call needed).
- **Method**: single GET per station per run, browser UA + Referer
  `https://weather.bangkok.go.th/water/`, 20s timeout, no retries — same BMA-host rule as every
  other `weather.bangkok.go.th` source in this registry.
- **Cadence and rotation (the 312-requests-per-pass problem)**: pulling all 312 stations' detail
  pages in one `collect.py --all` run means 312 requests to one host in one run — this violates
  the spirit of the one-request-per-URL/no-burst rule even though each URL differs (`?id=` varies)
  because it is still 312 near-simultaneous hits on the same host. **Proposed schedule**: rotate a
  fixed-size subset per run.
  - *(historical note: this proposal was written against a 30-minute GitHub Actions
    cadence that existed before 2026-10-02; as of 2026-10-03, GitHub Actions never runs
    `collect.py` on our runner at all — it only validates, tests and builds the page
    from the committed snapshot. `collect.py --all` is caller-side only, run on demand
    on the caller's own machine/network/keys, so this rotation math below is now a
    per-caller-run count, not a per-30-minutes count.)* `collect.py --all` (every 30
    minutes, per the then-existing GitHub Actions cadence) already runs
    48 times/day. A subset of **10 stations per run** completes a full 312-station sweep in
    `ceil(312/10) = 32` runs ≈ **16 hours** for one full pass — acceptable for fields (`water_control`,
    bank/bed levels, thresholds) that this probe found to be effectively static, not real-time
    telemetry.
  - Rotation state: a single small persisted cursor (e.g. `data/bma_station_detail_cursor.txt` or
    a `readout_log`-adjacent table row) recording the last `water_id` completed; each run takes
    the next 10 ids (wrapping at 312 back to the smallest known id), fetches, stores, advances the
    cursor. No burst: exactly 10 requests to this host per 30-minute run, spread evenly.
  - Any single `id` returning non-200/reset **that run** is skipped (not retried), logged, and
    left for the next time that id's turn in rotation comes back around (~16 hours later) — never
    a same-run retry.
  - If **any** request in a run's batch of 10 returns 403, the collector should treat that as a
    signal the whole host may be blocking this run (same posture as `bma_klongmap`'s DORMANT
    handling) — stop the remaining ids in that batch immediately, mark `bma_station_thresholds`
    DORMANT with the date, exclude from `--all`, require an explicit human-initiated re-check.
- **Fields to store** (see `KEEP_FIELDS` in the draft parser): `water_code`, `water_name`,
  `water_shortname`, `water_control` (**the new field**), `warning`, `critical`,
  `warning_out01`, `critical_out01`, `left_bank`, `right_bank`, `bed_bank`. These map 1:1 onto
  `PageMap`'s own field names (per `BMA_WATER_MAP_PROBE.md`'s field list) except `water_control`,
  `left_bank`, `right_bank`, `bed_bank` are read here because `PageMap` does not populate them.
- **`WaterHistory` (long-range history)**: left **out of scope for this collector**, pending
  resolution of §3's open hypotheses — do not wire it into `collect.py` until a human confirms
  whether it can return non-empty data at all (with or without a session cookie) and, if so, how
  far back.
- **Parser**: draft pure functions in `tools/harvest/bma_station_detail_draft.py` (this run) —
  `parse_station_detail_html()` (extracts the `txt_*` admin-form field values, the `water_id`),
  `parse_history_series(html)` (extracts the inline 2-day Highcharts series as `[timestamp, value]`
  pairs, for the fields that are already populated this way, tagged `MEASURED` from the archived
  sample), `water_control_value()` (the specific field the founder asked about, returned with an
  explicit tag so a caller never has to re-derive whether it's populated). Not wired into
  `collect.py`; that wiring, plus a `tests/` fixture test, a rotation-cursor implementation, and a
  registry entry, is left for whoever owns those files (per this repo's one-committing-worker
  rule — this probe writes new files only, does not commit).

## 7. Wiring steps for the committing worker

1. Add `bma_station_thresholds` to `sources/registry.yaml` (id, agency, url template, `host_rule:
   {max_requests_per_run: 10, notes: "..."}`, `trust_tier: official_telemetry`,
   `variables: [water_control, warning, critical, warning_out01, critical_out01, left_bank,
   right_bank, bed_bank]`).
2. Add a rotation cursor (see §6) — smallest possible persisted state, not a new subsystem.
3. Port `tools/harvest/bma_station_detail_draft.py`'s pure functions into `collect.py`'s fetch
   layer (mirroring however `bma_pumphistory`/`bma_watermap` are already wired), respecting the
   10-per-run cap and the DORMANT-on-403 handling in §6.
4. Add a fixture (`tests/fixtures/bma_station_detail_sample.html`, trimmed from
   `raw/live/bma_station_detail/stationdetail_id51.html`) + a `tests/test_bma_station_detail.py`
   exercising the parser against it, following the pattern of `tests/test_bma_watermap.py`.
5. Cross-reference new `water_control`/bank/bed values against `sources/canal_normal_levels.yaml`
   (already present in this branch) — do not duplicate a "normal level" concept under two
   different names in this repo; reconcile or explicitly note the difference (e.g. BMA's own
   `water_control` vs. this repo's derived/community `canal_normal_levels.yaml`) before both ship
   to the public page.
6. Run the leak scan + `pytest` gate (AGENTS.md §6) before any commit; this probe made no attempt
   to log in or write via `/water/StationDetail/Login` or `/UpdateStationinfo` and no future
   collector should either — read-only, always.

---
*Tags used above: `MEASURED` = read from this repo's own archived data; `RELAYED` = from BMA,
not independently re-derived; `INSTINCT` = judgment call; `OPEN` = unresolved. No personal names,
no AI/vendor names, no local filesystem paths in this file.*
