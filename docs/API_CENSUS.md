# API_CENSUS.md -- PHASE 1 summary (2026-09-27)

Full detail: `sources/api_census.yaml` (105 entries). This is a readout of what this
task's probe budget found -- not a decision to ingest anything, not a certification of
quality. Tags: VERIFIED (this check or a same-day agency-card fetch actually saw the
payload) / RELAYED (only seen on a portal/menu/CKAN listing, or merged in from an earlier
2026-09-27 sweep recovered from a crashed session's workflow journal -- not re-fetched by
this check) / OPEN (existence/shape unresolved).

Merge note: 86 feed rows recovered from an earlier same-day sweep's crashed workflow
journal were reconciled against the 42-entry base -- 23 matched existing entries by
normalized URL/id (only missing fields filled in, no VERIFIED tag ever downgraded or
upgraded), and 63 were unmatched and appended as new RELAYED entries under the
`# --- merged from earlier 2026-09-27 sweep (RELAYED) ---` marker.

## Counts by agency

| agency | entries |
|---|---:|
| RID | 31 |
| HII | 14 |
| BMA | 14 |
| DWR | 7 |
| Marine Dept. (กรมเจ้าท่า) | 6 |
| GISTDA | 5 |
| MWA | 3 |
| ACS | 3 |
| MEA | 3 |
| TMD | 2 |
| DDPM | 2 |
| Royal Rain Making (ฝนหลวง) | 2 |
| PCD | 2 |
| MOI | 2 |
| DOH | 2 |
| Open-Meteo, ONWR, EGAT, DNP, DMCR, DPT, NESDC | 1 each |

## Counts by status

| status | count |
|---|---:|
| reachable | 55 |
| unknown (listing seen, not fetched/probed) | 24 |
| unreachable | 13 |
| connected (already in registry.yaml) | 11 |
| needs_key | 2 |

## Counts by tag

| tag | count |
|---|---:|
| RELAYED | 87 |
| VERIFIED | 15 |
| OPEN | 3 |

`has_coords: true`: **27** sources across both sweeps (thaiwater_waterlevel,
bma_pumphistory, openmeteo_forecast, acs_flapgate_floodgateinfo,
thaiwater_canal_waterlevel, thaiwater_flood_road, thaiwater_rain_24h,
gistda_flood_extent_api, marine_imis,
gistda_flood_recurrence, gistda_sst_wms, hii_water_level_catalog, hii_flood_mark_shp,
hii_reservoir_elevation_capacity_curve, hii_tonnamforest_telemetry_water_level,
bangkok_floodgate_locations, bangkok_pump_station_and_floodgate_physical_data,
dnp_yom_basin_telemetry_33_stations, dwr_drought_flood_risk_areas_shp,
royalrain_agriculture_rainfall_areas_api, royalrain_operation_positions_api,
dmcr_marine_acidification, hii_thaiwater_net, marine_imis_map_view,
thaiwater30_analyst_dam, thaiwater30_public_watergate_load,
thaiwater30_sea_level_tide, plus the already-connected `bma_klongmap`'s status is
currently OPEN pending re-check -- see file).

## Top Phase-2 candidates

Reachable + no-auth + has_coords, **not** already in `sources/registry.yaml`:

1. **acs_flapgate_floodgateinfo** -- 57/67 stations nationwide with precise lat/lon,
   POST no-auth (per same-day agency card; this check's GET probe failed on method, not
   auth) -- best-coordinated feed found this sweep, but ownership is a `.com` domain,
   not confirmed `.go.th` -- needs an explicit rights check before real ingestion.
2. **gistda_flood_extent_api** -- has coordinates and is a real GISTDA endpoint, but is
   Referer-locked (`needs_key`, confirmed 403 `REFERER_REQUIRED`) -- not usable from a
   bare server-side fetch without GISTDA issuing a Referer-unlocked key.
3. **rid_app_reservoir** (`app.rid.go.th/reservoir/`) -- reachable, unconfirmed whether
   it has an API behind it (needs a browser network capture).
4. **rid9_chonburi_rpt** -- reachable HTML table, no coordinates found on the page
   itself (would need geocoding against gate names).
5. **dwr_ews_rain_daily** -- reachable, large page, coordinate presence unconfirmed.
6. **bangkok_ckan_portal** / **bangkok_river_pak_khlong_csv** -- a whole BMA open-data
   CKAN portal not yet surveyed on its own terms (only surfaced indirectly via
   data.go.th's federated search this sweep).
7. **hii_tiwrm_chaopraya_chart** -- reachable dam-release chart page, no coordinates
   (dam identity implicit, not a lat/lon feed).
8. **marine_imis** / **marine_gis** -- named menu item "สถานีวัดระดับน้ำอัตโนมัติ"
   (automatic water-level stations) not yet opened to confirm coordinates.

None of the above 8 has both confirmed coordinates AND confirmed no-auth AND confirmed
Bangkok-direct relevance except **acs_flapgate_floodgateinfo** (rights-gated) and
**thaiwater_waterlevel** (already connected). This is the honest state: the best
coordinate-bearing new candidate is a non-government domain of unconfirmed rights.

## Gaps this check could not cover (budget/scope)

- **EGAT dam telemetry**: main site is a cookie-consent interstitial only; no real dam
  water-level URL found. Two guessed sub-paths both failed.
- **TMD flash-flood risk forecast**: menu item confirmed to exist, sub-URL unresolved;
  one guessed path timed out.
- **DDPM (ปภ.) warning/hotline system**: complete JS-only SPA shell, sitemap.xml 404s --
  no URL reachable via curl at all.
- **ONWR "สถานการณ์น้ำ" dashboard**: named in nav, URL unresolved.
- **DWR tele-pwps.dwr.go.th**: named in a CKAN dataset alongside rain telemetry, but
  this check's own fetch timed out (000) -- worth a longer-timeout retry.
- **marine_gis (gis.md.go.th)**: connection timeout, not retried.
- **MWA bigdata API token**: a long token is embedded directly in a public CKAN listing
  -- deliberately not fired (looks like it could be a leaked long-lived credential
  rather than an intentionally public key; flagging, not using).
- Several agencies (RID main site, DWR main site, ONWR, TMD, EGAT, BMA DDS, DDPM) serve
  JS-only SPA shells to a plain curl -- a browser-driven pass (Playwright) would likely
  surface real API calls behind several of these that plain HTTP cannot see; not run
  this check (RAM/scope).
- data.go.th CKAN search covered 9 Thai terms (~9 requests) and surfaced almost entirely
  *provincial* open-data-catalog datasets (gdcatalog.go.th per-province mirrors) rather
  than a single national feed -- Bangkok/Sammakorn-relevant hits were the exception, not
  the rule; a full census of all 77 provincial catalogs was out of scope.
