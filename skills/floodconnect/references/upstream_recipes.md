# Upstream API recipes

`GET /api/v1/sources.json` (or `floodconnect_list_upstream_sources`) is the
registry of every upstream agency source FloodConnect itself reads from. It
mirrors `sources/registry.yaml` with secrets stripped and `auth` collapsed to
the public enum `none | key`.

## Rules for calling any upstream source

1. **Read the registry entry first.** Never call an upstream API this
   registry does not list.
2. **Respect `host_rule.max_requests_per_run`.** Most entries are `1` — at
   most one request to that URL per run/session, no exceptions.
3. **One request per URL, no retry loops.** If a request fails (timeout,
   non-200, malformed body), surface that as `tag: OPEN` for the affected
   field and stop. Do not retry with a variant URL or a different
   parameter set hoping for a different result.
4. **`auth: "key"` means the upstream needs a credential you must supply
   yourself** (FloodConnect's own export never carries a live key) — if you
   don't have one, treat that source as unavailable, don't guess or fabricate
   a call.
5. **`licence_status.unresolved: true` is a real caveat**, not decoration —
   it means this repo has not independently confirmed the source's
   redistribution terms. Carry that caveat forward if you cite the source
   onward, don't drop it.
6. **Never call an upstream API on a resident's behalf without going through
   the registry entry** — this keeps every fetch traceable to a documented
   `trust_tier` and `host_rule`, and keeps FloodConnect's own host-safety
   posture (the reason `WL.SSB.*`/`WL.BMA.*` data exists reliably at all)
   from being undermined by an uncoordinated caller.

## Example

```json
{
  "id": "thaiwater_canal_waterlevel",
  "agency_en": "Department of Drainage and Sewerage, BMA (republished via HII/thaiwater.net)",
  "url": "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel",
  "method": "GET",
  "auth": "none",
  "host_rule": { "max_requests_per_run": 1, "note": "one request per URL, no retry loops" },
  "trust_tier": "official_telemetry"
}
```

Call this exactly as: one `GET` to the exact `url`, no query-string
variations tried "just in case," no second attempt if it fails.

## Compact recipe table (8 representative wired sources)

Only needed if you are an external AI that wants to fetch a government/third-party
source yourself rather than running `kb.py answer --refresh` in the repo — e.g. you
have your own quota/compute and no local clone. Every row below is copied from
`sources/registry.yaml` (the real `url`/`method` fields, not re-derived) — read that
file for the full 42-source registry; this is a deliberately short, representative
subset, moved here (read on demand) rather than kept in `AI.md` (loaded every time, and
token-budgeted — see `AI.md`'s own token-budget test). **One GET per URL, no retries,
respect `host_rule.max_requests_per_run`** — same rule this repo's own `collect.py`
follows. TOON form (uniform rows, see the `toon-format` skill):

```toon
upstream_recipes[8]{id,url,method,parse_hint}:
  thaiwater_canal_waterlevel,https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel,GET,"JSON array; see live_water_level.py for the exact field map"
  bma_pumphistory,https://weather.bangkok.go.th/Station/PumpHistory,GET,"server-rendered HTML + embedded `var datapump` JS array; see live_water_level.py"
  openmeteo_forecast,"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation,precipitation_probability&timezone=Asia%2FBangkok&forecast_days=3",GET,"no API key; one request per area, substitute lat/lon"
  hii_dam,https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam,GET,"JSON array of dam records"
  rid_res_table,http://water.rid.go.th/flood/flood/res_table.htm,GET,"HTML table, windows-874/cp874 encoded -- decode before parsing"
  gdacs_events,"https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP?country=Thailand&fromdate={YYYY-MM-DD}&todate={YYYY-MM-DD}",GET,"country= does NOT filter server-side; filter client-side on iso3/country, see parsers.parse_gdacs_events_thailand"
  metno_locationforecast,"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}",GET,"no API key; MET Norway ToS REQUIRES an identifying User-Agent header (project string, never a personal name)"
  openmeteo_archive_precip,"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}&daily=precipitation_sum&timezone=Asia%2FBangkok",GET,"no API key; 30-day trailing window, one request per point"
```

None of these is a FloodConnect equation — they are third-party `trust_tier` reads
(`official_telemetry`/`third_party`, see each registry row), tag whatever you derive
from them `RELAYED`, never `VERIFIED`.

## Government API census — status

`sources/api_census.yaml` (162 entries, closed out 2026-10-03) is the full sweep behind
this file's 8-row subset — every status is one of `connected` (already wired here),
`reachable`/`reachable_*` (HTTP 2xx observed, not yet wired), `needs_key`,
`host_blocked` (confirmed WAF/anti-bot 403, or a host's own stated no-scraping policy —
never retried), `unreachable` (timeout/404/5xx with no block signature),
`unresolved_url` (no single concrete URL exists to probe), or `not_a_source` (a
code-review finding, not a URL-having source). No entry is left `unknown`.
Two Bangkok Open Data sources found reachable this check (real content fetched and
confirmed, both carry `lat`/`long`) are now wired: `bangkok_floodgate_locations` (237
floodgate rows in the captured CSV, 230 with a valid coordinate pair, opening/control/
critical/warning thresholds) and `bangkok_pump_station_and_floodgate_physical_data`
(438 pump-station rows in the captured CSV, 429 with a valid coordinate pair,
gate/pump counts, total capacity). Both are static reference data (locations + design
thresholds, tagged RELAYED), not live telemetry.
