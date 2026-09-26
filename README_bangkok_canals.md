# Bangkok Canal (Khlong) Graph — extension to the main river-flow KG

## What this is NOT — read this first

**Most of this graph's edges have NO reliable direction.** Unlike `build_kg.py`'s
major-river graph (direction = HydroRIVERS' own `NEXT_DOWN` field, `finite_diagnostic`
tier), this canal graph's direction comes from a `Dr`-tier (INSTINCT) heuristic: only
canal-network components that happen to have a major-river graph node within 3km of one of
their junctions get oriented at all (BFS tree pointing toward that nearest major-river
connection point, on the assumption canals drain toward it). **380 of 2,595 connected
components (≈15%) got a directional guess this way; the remaining 2,215 components
(≈85% — almost all of inner Bangkok) are `direction="unknown"`**, kept as bidirectional
edges. No DEM/elevation data, no gate-operation schedule, and no real flow observation
were used. Do not treat any edge's direction here as verified fact.

## What this is

A junction-graph of Bangkok-area canals/ditches/streams/drains from OpenStreetMap
(HOTOSM Thailand waterways export), with BMA floodgate/pump-station locations overlaid as
node context. It exists to answer, at least partially, the question `build_kg.py`'s
major-river graph structurally cannot: what's the local drainage network near an
inner-Bangkok point like เขตสะพานสูง (Saphan Sung), whose nearest **major** river node is
~14km away and therefore useless for local risk assessment.

## Pipeline (`build_bangkok_canals.py`)

1. Load OSM waterway lines (`waterway` in canal/ditch/stream/river/drain) clipped to a
   Bangkok-area bbox (100.32–100.95°E, 13.49–13.96°N) from the HOTOSM Thailand waterways
   export (`data.humdata.org/dataset/hotosm_tha_waterways`, `lines_gpkg` resource).
2. Snap line endpoints to a ~33m grid to merge near-duplicate OSM vertices into shared
   junction nodes; build an **undirected** graph (node = junction, edge = canal segment).
   Parallel OSM ways between the same two junctions: keep the shorter one only (networkx
   `Graph` can't hold parallel edges; shorter is the more conservative pick against
   digitization artifacts).
3. Load `build_kg.py`'s major-river graph nodes that fall within Bangkok's bbox + 0.3°
   padding, as candidate "sinks" (points a canal could plausibly discharge into).
4. For each connected component of the canal graph: find its junction closest to any sink.
   If that distance is ≤ 3km, orient the whole component as a BFS tree pointing toward that
   junction (`direction_basis="heuristic_nearest_river_sink"`, tier `Dr`). Otherwise leave
   every edge in that component `direction="unknown"` and keep both directions traversable.
5. Overlay BMA floodgate/pump-station points (`floodgate.csv`, 237 rows, `data.bangkok.go.th`)
   onto nodes within 300m as a `nearby_floodgates_km_0.3` attribute.
6. Fuzzy-match the BMA daily water-level CSVs' station names onto `floodgate.csv`'s
   coordinates (`match_water_level_stations_to_floodgates()`), then overlay matched
   stations onto nearby nodes as `nearby_water_level_stations` +
   `water_level_match_confidence`. **Water level only, not direction** — see the
   "2026-09-23 global sweep" section below for why.
7. Export `output/bangkok_canals.graphml` and `output/bangkok_canals.jsonld`.

### Re-running

```bash
# one-time: get the raw data (all free, no API key)
mkdir -p raw/bangkok
curl -o raw/bangkok/hotosm_waterways_lines.gpkg.zip \
  https://s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/THA/waterways/lines/hotosm_tha_waterways_lines_gpkg.zip
unzip raw/bangkok/hotosm_waterways_lines.gpkg.zip -d raw/bangkok/hotosm_lines/
curl -o raw/bangkok/floodgate.csv \
  "https://data.bangkok.go.th/dataset/83ae5639-a37f-4e19-bd37-e1c97930f39d/resource/42948cf7-0759-4719-a32f-8eeabd89b8ee/download/floodgate.csv"

# build_kg.py must have already been run at least once (this script reads its
# output/thailand_river_flow.jsonld for sink candidates; runs fine without it too,
# but then every component is direction=unknown)
python3 build_bangkok_canals.py
```

## Confirmed run (this session)

- 6,714 OSM waterway lines in the Bangkok bbox (canal 4,052 / ditch 1,087 / river 951 /
  drain 506 / stream 118, before further filtering)
- Graph: **8,672 junction nodes, 6,155 undirected canal-segment edges**
- 59 major-river sink candidates found near Bangkok
- **380/2,595 components (≈15%) got a directional guess; 2,215 (≈85%) are
  `direction="unknown"` — UNCHANGED from the previous run.** The 2026-09-23 global
  research sweep (below) found no method that could honestly raise this without
  fabricating confidence the data doesn't support — see that section for what was tried
  and why each avenue was a dead end.
- 230 of 237 BMA floodgate points had valid coordinates and were loaded
- **New this session**: 6/10 BMA water-level station names fuzzy-matched onto
  `floodgate.csv` coordinates (see "Station name↔coordinate join" below) — water level
  context only, does not affect direction coverage.
- **Also new this session**: the per-canal 1D arc-length bridge idea (below) was implemented
  and actually run against the pipeline — 0/21 eligible canals cleared its own trust
  threshold, 0 edges integrated. Direction coverage remains 380/2,595 components,
  2,170/6,155 edges (identical before/after — confirmed from the executed run, not assumed).
- **Also new this session**: Delaunay-triangulation rubber-sheeting (below), a third and
  literature-standard attempt at the whole-panel georeferencing problem, was implemented
  and leave-one-out validated on all 199 control points — median LOO error 867 m
  (mean 1,362 m, max 16.5 km), 6/199 stations under the 150 m trust bar, 0/241 arrows
  passed the per-triangle local-trust gate. **Zero edges integrated.** Direction coverage
  remains 380/2,595 components, 2,170/6,155 edges — identical before/after, confirmed from
  the executed run.
- **Also new this session**: a 4th attempt — using KlongMap arrow directions as a much
  weaker "local bearing corroboration" soft prior instead of precise snapping — was
  implemented and calibrated against real ground truth (major-river `NEXT_DOWN` direction).
  Measured agreement rate sat at or below the 50% chance baseline in 22/24 tested parameter
  configurations (best: 66.7% on n=12; every statistically larger sample, n=29/42, was
  31–45%, i.e. at/below chance). **Not usable, zero edges/components integrated.** See the
  dedicated section below for the full sweep.

## 2026-09-23 global research sweep — what was checked, what happened

Requested: sweep for better methods/data to fill the ~85% direction gap, and evaluate the
"2013 chart" page the maintainers referenced. Every avenue below was actually tested against
real downloaded data or a real fetch, not assumed.

| Avenue | Result | Evidence |
|---|---|---|
| **OSM tag-level signals** (`flow_direction` or similar) | **Dead end, confirmed empirically** | Full column list of the actual downloaded HOTOSM gpkg: `name, name:en, waterway, covered, width, depth, layer, blockage, tunnel, natural, water, source, name:th, osm_id, osm_type, geometry`. No direction-relevant field exists. This is a direct check of the real data, not a repeat of the earlier assumption. |
| **DEM-based flow inference (Copernicus GLO-30)** | **Access is easier than assumed (public, no key needed via AWS Open Data mirror), but the elevation signal itself is a dead end** | Downloaded tile `Copernicus_DSM_COG_10_N13_00_E100_00_DEM` anonymously from `copernicus-dem-30m.s3.amazonaws.com` (no CCM registration required — that gate only applies to ESA's own Copernicus Data Space Ecosystem, a different access path). Sampled elevation at all 8,672 canal-graph junctions and computed `\|Δz\|` across all 6,155 edges: **median 0.77 m overall, 0.88 m even restricted to edges ≥200 m long**. GLO-30 is a DSM (rooftops/canopy, not bare earth) with a quoted vertical accuracy on the order of a few meters in easy terrain and materially worse local noise in dense urban terrain — a ~0.8 m signal sits at/below that noise floor. **Not wired into direction inference** — doing so would present noise as a directional claim. Reproducible via `dem_signal_check.py`. |
| **BMA canal-management/zone data** (คันกั้นน้ำ, inner/outer zone boundaries, pump discharge direction) | **Dead end** | `data.bangkok.go.th`'s own "ข้อมูลคลองในพื้นที่กรุงเทพมหานคร" (`canal.csv`, downloaded and inspected) is **water-quality** data (temperature/pH/DO/BOD/COD/SS/TKN/NH3N/NO2/NO3/T-P by canal name) — no geometry, no coordinates, no direction. `floodgate.csv`'s `water_control`/`gate` columns (re-inspected against all 237 rows) are **operating water-level thresholds** ("open when level exceeds X"), not discharge direction. Web search for an explicit เขตควบคุมน้ำ/คันกั้นน้ำ boundary dataset with a machine-readable geometry turned up organizational descriptions only, no dataset. |
| **BMA water-level station name↔coordinate join** (explicit prior next-step) | **Partially unblocked** | See dedicated section below. |
| **Academic/government canal-network study of Bangkok with directionality** | **Dead end — nothing found** | Searched ThaiJO/TCI and general web for a Bangkok-specific equivalent of the Chanthaburi centrality paper already cited in `build_kg.py`'s README. Nothing on record with directional canal-flow analysis for Bangkok specifically. |
| **The "2013" HII chart** (`tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/2013/chaopraya.php`) | **Confirmed dead end, not worth integrating** | Direct fetch confirms it is purely a static chart image (`<img>` of a PNG) plus a "small" variant link — no `<script src>`, no `.json`/`.csv`, no query-parameterized API in the page source of either variant. Swapping `2013` → `2026` in the URL returns a plain **404** — this is not a live year-parameterized endpoint; the directory is effectively archival/frozen (oddly, the cached chart image itself was last regenerated 2024-10-04, suggesting this specific path gets occasionally refreshed by the source system rather than truly abandoned, but there is still no queryable backend behind it). Even if it were live, it is a **basin-level Chao Phraya water-situation chart** (dam levels, trend bands) — the wrong spatial resolution for inner-Bangkok canal direction regardless. The live/current equivalent lives at a different URL scheme entirely on the same `tiwrm.hii.or.th` host (`/v3/sealevel`, `/thaiwater_l5/public/...`), part of HII's newer dashboard generation — not integrated here, out of scope for this task (national/basin telemetry, not Bangkok canal geometry). |
| `standard.thaiwater.net` documented water-level API (found during the sweep, not part of the original candidate list) | **Noted, not pursued** | `standard.thaiwater.net` does document a real water-level/rainfall API service (JSON, station-based) — this exists and is more than the earlier "no accessible API" read gave it credit for. However, its stations are HII/RID's *national* telemetry network, a different station set from BMA's *municipal* floodgate network — even fully explored, it would not resolve the BMA station-name join (different institution, different stations). Time-boxed out of this pass; flagged as a possible future lead for a *separate* national-river-gauge integration, not this canal-direction gap. |

**Bottom line: no avenue in this sweep produced a legitimate way to raise the 15% direction
coverage.** The 85% gap is reported as genuinely unresolved (`OPEN`), not narrowed by force.

## 2026-09-23 KlongMap investigation (`weather.bangkok.go.th/KlongMap`) — real data found, integration dead end

Maintainer lead: BMA's own water-management map app, claimed to have detailed direction info
(มีทิศละเอียดเลย). A plain `WebFetch` earlier only saw a thin JS-app shell (canal/station
dropdowns) and could not find a backend API. This session did a real browser inspection
(Playwright: page load + `browser_network_requests` + in-page `fetch()` calls against the
live API) instead of guessing from the HTML alone.

**What was found — genuinely new, better than the earlier thin read:**
- The page is a jQuery + `svg-pan-zoom.js` app (not Leaflet/OpenLayers — no real GIS map).
  Its one data endpoint, open with no auth/cookie/referer requirement (`curl` alone returns
  200), is `GET https://weather.bangkok.go.th/Klongmap/GetDataForUpdate` — a JSON blob with
  keys `waterStation` (403 records), `stationMap` (253), **`arrowMap` (241 records)**,
  `riverMap` (12 canal names), `listRiverMap` (89), `dailyheightwater`.
- `arrowMap` entries carry a `configs` field like `"23,23,90deg,0000FF"` — width, height, a
  **rotation angle in continuous degrees** (26 distinct values observed, not just the 4
  cardinal directions — e.g. `35deg`, `242deg`, `311deg`), and a color. Reading the page's own
  inline JS (`arrowMap(item)` function, confirmed by reading the served HTML directly) shows
  this `deg` is applied as a literal CSS `rotate()` on a cloned arrow-icon SVG
  (`#svgArrow`/`#arrowGroup`) whose un-rotated (`0deg`) orientation points up the SVG canvas
  (shaft descends from a high-y base to a low-y arrowhead in the `viewBox 0 0 1000 2059`
  path data). **This is a real, intentional flow-direction encoding** — continuous degrees,
  not a decorative fixed icon — genuinely more detailed than anything found in the earlier
  2026-09-23 global sweep (above).
- Each `waterStation` record carries BOTH a schematic pixel position (`offset_x`/`offset_y`,
  used to place its icon on the SVG panner) AND, nested in `water_station_info`, a real
  `latitude`/`longitude`. **199 of 403 stations have both** (150 in the app's "area 2" panel
  = ฝั่งพระนคร-side overview, 45 in "area 3" = ฝั่งธนบุรี-side overview), giving real
  pixel↔geographic control points — in principle enough to fit a pixel→lat/lon transform and
  georeference the 241 `arrowMap` entries (104 of which fall in area 2, 20 in area 3; the
  remaining 117 have `area_id=null` and could not be geo-anchored at all regardless).

**Why this was NOT integrated — tested, not assumed, and it's a dead end:**
Fit both (a) a single global affine (least-squares, `[lon,lat] = A·[offset_x,offset_y]+t`)
and (b) a local k-nearest-neighbor affine (k=6, leave-one-out cross-validated) per area,
using the 199 real control points, then measured prediction error in km via haversine
against each control point's own known true coordinate:

| Area | n control points | Global affine median error | Local k=6 LOO median error |
|---|---|---|---|
| 2 (ฝั่งพระนคร overview) | 150 | 3.0 km (max 8.1 km) | 0.82 km (max 7.0 km) |
| 3 (ฝั่งธนบุรี overview) | 45 | 1.5 km (max 3.7 km) | 1.17 km (max 3.8 km) |

Even the best case (local, leave-one-out) has **median positional error ~0.8–1.2 km**, an
order of magnitude larger than the spacing between adjacent junctions in this pipeline's own
canal graph (hundreds of meters, e.g. the เขตสะพานสูง demo's nearest junctions are
379 m–1.2 km apart *in total*). This means the BMA schematic is a **non-metric diagram**
(drawn for dashboard readability, like a subway map — not a scaled/projected geographic
map), confirmed empirically rather than assumed from the app's look. Any attempt to snap an
`arrowMap` entry's rotation to a specific real-world canal edge would routinely misassign it
to the wrong junction or the wrong canal entirely, and would rotate the claimed bearing by an
unknown, spatially-varying amount inherited from the diagram's own distortion. Presenting
that as a direction claim — at any tier — would be fabricating confidence, which this
pipeline's discipline (see epistemic tiering table) does not allow.

**Bottom line:** a real, more-detailed-than-previously-known flow-direction dataset was
found and is a legitimate `finite_diagnostic`-tier *existence* fact (BMA's own app does
encode a directional bearing at 241 points), but it is unusable for this graph's purpose
without a proper geographic calibration BMA has not published. **Not integrated. Direction
coverage is unchanged this session: still 380/2,595 components (≈15%).** Cached raw response
kept at `raw/bangkok/klongmap_data.json` for reproducibility of the numbers above; no new
code path was added to `build_bangkok_canals.py`, since there is nothing honest to wire in.
Flagged as a possible future lead only if BMA (or a third party) ever publishes true
lat/lon-referenced canal geometry to calibrate against — not pursued further this session.

## 2026-09-23 per-canal 1D arc-length bridge — tested, also a dead end (different failure mode)

Maintainer idea, in direct response to the whole-panel 2D
georeferencing failure above: instead of one 2D geographic transform across an entire mixed-canal
schematic panel (which failed because different canals on the same panel are compressed at
wildly different scales), do it **per named canal, in 1D** — arc-length fraction along that
one canal only, both in the schematic drawing and in real OSM geometry, fit with a simple
monotonic interpolation (`numpy.interp`) between calibration anchors (BMA water-level stations
that carry both a schematic pixel position and a real lat/lon). The hypothesis: even if BMA's
panel badly distorts relative scale *between* canals, any *one* canal might still be drawn as a
roughly arc-length-proportional line along its own length.

**Implementation** (`load_klongmap_anchors_and_arrows`, `match_canal_to_osm`,
`_merge_osm_geometry_for_canal`, `fit_canal_1d_bridge`, `run_klongmap_1d_bridge`,
`assign_arrows_and_orient_edges` in `build_bangkok_canals.py`):

1. Extracted 199 station anchors (schematic `offset_x`/`offset_y` from `waterStation[i]`, real
   `latitude`/`longitude` + canal name `river_name` nested in `water_station_info`) and 241
   arrows (schematic `offset_x`/`offset_y` + rotation `deg` from `configs`) — **all in the
   single main-panel pixel frame**, not the separate per-area `offset_x_area`/`offset_y_area`
   fields (those are only populated for a minority of records and buy nothing once everything
   is already in one shared coordinate frame). Confirmed empirically: `arrowMap` records carry
   no canal-name/id field at all (`flow_id` is null on every record checked), so arrow→canal
   assignment has to be spatial.
2. Grouped anchors by `river_name`: 119 distinct canal names, **21 with ≥3 anchors** (the
   minimum for a leave-one-out test at all).
3. For each of those 21: fuzzy-matched `river_name` to an OSM `name`/`name:th` value (exact
   match preferred, `SequenceMatcher` fallback ≥0.8), with a mandatory spatial cross-check
   (candidate OSM geometry's centroid must be within 5km of the anchors' own centroid — a name
   match whose geometry sits nowhere near the canal's known-latlon anchors is rejected). Merged
   same-name OSM lines via `shapely.ops.linemerge`; if disconnected, kept only the fragment
   that the most anchors actually project onto within 300m.
4. Computed each anchor's **real arc-length fraction** via `line.project(point, normalized=True)`
   on the matched real geometry, and its **schematic arc-length fraction** via the first
   principal component (PCA/SVD) of the canal's own anchor pixel-scatter, min–max normalized.
   Fit `numpy.interp(schematic_frac → real_frac)` on the anchors.
5. **Leave-one-out, per canal**: refit without each anchor, predict its position, measure
   haversine error against its true lat/lon — exactly the same honesty discipline as the
   earlier 2D sweep.

### Leave-one-out results (all 21 canals with ≥3 anchors — every one attempted, none silently skipped)

| Canal | anchors used | OSM match | name ratio | LOO median error | LOO max error | Usable (≤150m)? |
|---|---|---|---|---|---|---|
| คลองบางนา | 4 | คลองบางนา | 1.00 | 1,105 m | 1,992 m | No |
| คลองเคล็ด | 4 | คลองเคล็ด | 1.00 | 1,114 m | 2,389 m | No |
| คลองเปรมประชากร | 5 | คลองเปรมประชากร | 1.00 | 1,175 m | 3,107 m | No |
| คลองหนองบอน | 3 | คลองหนองบอน | 1.00 | 1,535 m | 2,137 m | No |
| คลองผดุงกรุงเกษม | 3 | คลองผดุงกรุงเกษม | 1.00 | 1,747 m | 4,803 m | No |
| คลองบางซื่อ | 3 | คลองบางซื่อ | 1.00 | 1,965 m | 2,579 m | No |
| คลองหัวหมาก | 3 | คลองหัวหมาก | 1.00 | 2,517 m | 3,872 m | No |
| คลองภาษีเจริญ | 3 | คลองภาษีเจริญ | 1.00 | 4,852 m | 10,125 m | No |
| คลองสามเสน | 3 | คลองสามเสน | 1.00 | 5,086 m | 5,754 m | No |
| คลองบางพรม, คลองบางเชือกหนัง, คลองพระยาสุเรนทร์, คลองบางนางจีน, คลองบางเขน | 3–4 | matched | 1.00 | — | — | Not fit: <3 anchors projected within 300m of the matched OSM geometry (real segments too fragmented / digitized as disjoint pieces under the same name) |
| คลองประเวศบุรีรมย์ | 6 | matched | 1.00 | — | — | Not fit: only 1/6 anchors projected within 300m (real geometry likely fragmented/renamed along its length) |
| คลองพระยาราชมนตรี, คลองแสนแสบ, คลองชวดใหญ่, คลองบางอ้อ, คูน้ำวิภาวดี, คลองลาดพร้าว | 3–10 | — | — | — | Not fit: no OSM name passed the fuzzy-ratio + 5km spatial sanity check |

**0/21 canals passed the trust threshold. The idea does not work — confirmed, not assumed.**

**Why, concretely** (worked example, คลองบางนา, the cleanest case — exact name match, all 4
anchors project onto the real line within 7 m): the anchors' schematic pixel x-coordinates
(560, 664, 756, 801, all at the same y — genuinely drawn as a straight horizontal line) map to
real arc-length fractions (0.961, 0.724, 0.272, 0.144) that are **monotonic but not
proportional** — 92 schematic pixels (664→756) span 0.452 of the real 8.76 km canal (≈3.96 km),
while 45 pixels (756→801) span only 0.128 (≈1.12 km). The schematic gets the *order* right
(this is genuinely better than the 2D approach, which sometimes didn't even get relative
position within a panel right) but **not the local scale** — BMA compresses/stretches
different stretches of the *same* canal by different amounts in its own diagram, so a linear
(or any smooth monotonic) 1D interpolation between a handful of anchors still misses the true
position by up to several km. This is the 1D analogue of exactly the same root problem the 2D
sweep found: **the KlongMap panel is a non-metric schematic (subway-map style) at every scale
it was tested at, not just panel-wide** — narrowing to one canal did not fix it.

**Caveats on the negative result itself** (so it isn't overstated either): the fuzzy/spatial
name-matching step rejected 6 canals (including คลองแสนแสบ, the largest group with 10 anchors)
via a simple centroid-distance sanity check that is a poor fit for very long, non-compact
canals (แสนแสบ's own anchors span ~36 km east–west, so its OSM-geometry centroid sits ~9.7 km
from its anchors' centroid even though the name match is almost certainly correct) — this is a
methodology limitation of this pass's spatial check, not a demonstrated accuracy failure for
those specific 6 canals, since they were never actually fit. However, given that the 9 canals
that *did* match cleanly (ratio 1.00, real anchors projecting onto the matched geometry within
meters) still failed by 1–5 km median error from the compression-nonuniformity problem alone,
there is no reason to expect fixing the matching step would change the outcome — the failure
mode is intrinsic to the schematic, not an artifact of which canals got matched.

**Integration**: `assign_arrows_and_orient_edges()` was implemented and wired into the pipeline
(assigns arrows to a canal via nearest-PCA-line-with-band, projects to a real point, snaps to
the nearest same-name graph edge, orients via the arrow's rotation angle converted from CSS
`rotate()` screen convention) but with 0/21 canals passing the trust gate, it integrated
**zero edges** this run — confirmed in the actual pipeline output, not just reasoned about.
The code path is real and will activate automatically if a future, better-calibrated schematic
or a tighter anchor set ever clears the threshold; it did not this session.

**Bottom line: direction coverage is UNCHANGED by this idea.** Still 380/2,595 connected
components (≈15%) with any claimed direction, 2,170/6,155 edges (both counts identical
before/after this run — logged directly from the executed pipeline). The per-canal 1D bridge
is a legitimate, well-motivated idea that was actually implemented and actually tested, and it
genuinely does not clear the bar this pipeline requires. New tier for this specific (unused)
direction source, for completeness: `direction_basis="klongmap_1d_arc_length_bridge"` would
have been `Dr` (calibrated/derived, would have been meaningfully better-grounded than the
geometric-heuristic `heuristic_nearest_river_sink` source *if* any canal had passed) — but no
edge in the exported graph currently carries this basis, because none qualified.

## 2026-09-23 Delaunay-triangulation rubber-sheeting — third attempt, also a dead end, method now confirmed literature-standard not ad hoc

Maintainer-directed third attempt, explicitly requested as a literature-grounded method rather
than another ad hoc invention, after both the whole-panel 2D affine/kNN attempt (median
0.8–3 km) and the per-canal 1D arc-length attempt (median 1.1–5 km, worse) failed. Web
research confirmed **Delaunay-triangulation-based rubber sheeting is the standard GIS
technique for exactly this problem class** — conflating a non-metric/schematic
representation to real geographic coordinates using scattered control points (see e.g.
ESRI's "rubber sheeting" GIS dictionary entry; the general piecewise-linear rubber-sheet
transform used in academic literature for historical/schematic map georeferencing). This is
not a re-run of either prior attempt: it uses ALL 199 known-correspondence stations across
the WHOLE panel at once (unlike the per-canal split), and fits a piecewise-**exact** affine
transform per Delaunay triangle (unlike the single global affine or the smoothed kNN
regression of the first attempt).

**Implementation** (`build_delaunay_rubber_sheet`, `loo_validate_delaunay_rubber_sheet`,
`_build_local_trust_by_index`, `assign_arrows_via_delaunay_rubber_sheet`, `_fit_triangle_affines`,
`_bearing_from_pixel_deg` in `build_bangkok_canals.py`):

1. Deduplicate the 199 station anchors by (near-)identical schematic pixel position (Delaunay
   triangulation requires non-coincident input points); build `scipy.spatial.Delaunay` over
   their schematic `(offset_x, offset_y)` positions.
2. For each triangle, solve the **exact** 2D affine map `real = A·schem + t` through its 3
   corner control points (3 correspondences fully determine an affine transform — no least
   squares, no residual at the corners themselves).
3. To project any other schematic point (an arrow, or a held-out test station): locate the
   containing triangle (`Delaunay.find_simplex`); if outside the convex hull of control
   points, fall back to the nearest triangle by centroid distance and flag the result
   `extrapolated=True` (affine maps are defined everywhere, just less trustworthy outside
   their own triangle — standard rubber-sheeting practice, not a workaround invented here).
4. **Leave-one-out on all 199 stations**: remove each station, rebuild the *entire*
   triangulation from the remaining ones, project the held-out station's own schematic
   position through the rebuilt triangulation, measure haversine error against its known true
   lat/lon. Every station attempted (0 skipped — 198 remaining points is always enough to
   triangulate).
5. Trust gate: for every triangle in the FULL (all-199) triangulation, compute a per-triangle
   local-trust proxy = mean of its own 3 corner stations' individual LOO error (from step 4,
   indexed positionally). An arrow is only integrated if its enclosing/nearest triangle is
   **not** an extrapolation and that triangle's local-trust proxy is `<= 150m`
   (`DELAUNAY_TRUST_KM`, same bar as the per-canal bridge — well under the graph's ~443m
   median / ~151m p25 edge length).
6. For arrows that would pass: snap to the nearest real canal-graph edge (any name — the
   whole-panel method is not partitioned by canal, unlike the 1D bridge) within 300m; convert
   the schematic rotation angle to a real compass bearing using the LOCAL triangle's affine
   *linear part* `A` (`_bearing_from_pixel_deg` — rotates the schematic direction vector
   through `A`, then converts to a compass bearing with a cos(lat) correction for longitude
   compression), not the raw degree value; only overwrite edges still `direction="unknown"`,
   never an edge that already carries the `heuristic_nearest_river_sink` claim.

### Leave-one-out results (all 199 control points, whole panel, executed run)

| Statistic | Value |
|---|---|
| n tested | 199 (0 skipped) |
| median error | **867 m** |
| mean error | 1,362 m |
| p10 / p25 | 296 m / 488 m |
| p75 / p90 / p95 | 1,519 m / 2,446 m / 3,968 m |
| max error | 16,498 m |
| stations ≤150m (the trust bar) | 6/199 (3.0%) |
| stations ≤500m | 53/199 (26.6%) |
| stations ≤1,000m | 111/199 (55.8%) |
| in-hull (interpolated) stations | 189/199, median **815 m** |
| outside-hull (extrapolated) stations | 10/199, median 4,498 m |

**0/241 arrows passed the per-triangle local-trust gate. Zero edges integrated** — confirmed
from the actual executed pipeline run, not reasoned about.

**Bottom line: Delaunay rubber-sheeting does NOT beat either prior attempt** — its median LOO
error (867 m) sits inside the same 0.8–3 km band the first whole-panel affine/kNN attempt
already found (0.82–3.0 km median depending on area/method), and is far better than the
per-canal 1D attempt (1.1–5.1 km) only because it is not restricted to reusing a single
canal's own (badly-behaved) local scale — but it still falls roughly **6× short** of the
150m trust bar even at its best (in-hull) subset. This is now the **third** independently
confirmed negative result on this exact problem, and unlike the first two it used the actual
literature-standard technique for this problem class rather than an ad hoc invention — the
method choice itself was not the limiting factor. **This strengthens rather than weakens the
earlier diagnosis**: the KlongMap panel is fundamentally a non-metric schematic diagram (like
a subway map — topologically faithful, not scale-faithful) at every resolution and every
transform family tested (global affine, local kNN, per-canal 1D arc-length, and now
whole-panel piecewise-affine triangulation). No further transform-method attempt on this
same 199-point control set is likely to succeed; closing this gap would require BMA (or a
third party) publishing better-calibrated or denser ground-truth correspondences, not a
smarter interpolation method.

**Integration**: `assign_arrows_via_delaunay_rubber_sheet()` was implemented and wired into
the pipeline exactly as described above; it ran against all 241 arrows and integrated **zero
edges** because zero triangles cleared the local-trust gate. The code path is real, will
activate automatically if a denser/better-calibrated control-point set is ever supplied, and
did not activate this session. New tier for this specific (unused) direction source, for
completeness: `direction_basis="klongmap_delaunay_rubber_sheet"` would be `Dr`
(calibrated/derived) — but no edge in the exported graph currently carries this basis.

## 2026-09-23 KlongMap local-bearing weak-prior experiment — 4th attempt, measured, also a dead end

Maintainer idea, explicitly framed as **different** from the
prior three (whole-panel 2D affine/kNN, per-canal 1D arc-length bridge, Delaunay
rubber-sheeting — all above, all failed the ~150m precise-snapping bar): stop trying to
precisely georeference KlongMap arrows onto specific edges at all, and instead test whether
KlongMap's arrow directions carry a **weak corroborating signal** — a local bearing trend
usable only as a soft tie-breaker for otherwise-`unknown` components, explicitly
lower-confidence than either input alone. The brief was explicit that this must be
**empirically calibrated against real ground truth before any integration decision** — not
assumed to work because the idea sounds more defensible than the earlier ones.

**Method** (`klongmap_local_prior_experiment.py`, standalone — does not touch
`build_bangkok_canals.py`, per the constraint not to disturb the three existing dead-end
functions):

1. For each of the 199 real-coordinate KlongMap stations, find `arrowMap` entries within a
   pixel radius of that station **in schematic pixel space** (same local cluster) and take
   the circular mean of their rotation angles as a local schematic-pixel bearing trend.
2. Estimate a **local rotation offset**, using only that station's 1–2 (or up to 4, tested
   both) nearest-neighbor stations: compare the bearing from the station to each neighbor in
   schematic-pixel space against the same bearing in real compass terms (haversine-based,
   cos(lat)-corrected). Circular-mean the per-neighbor offsets. This is a genuinely smaller
   extrapolation than the three prior attempts — no panel-wide or per-canal scale/rotation
   assumption, only "this station's immediate neighborhood isn't wildly re-rotated relative
   to itself."
3. `real_world_bearing_estimate = local_schematic_bearing_trend + local_rotation_offset`.
4. **Ground truth for calibration**: `build_kg.py`'s major-river graph, whose direction is
   the real `finite_diagnostic`-tier HydroRIVERS `NEXT_DOWN` field (not a heuristic) — exactly
   the "canal segments where the major-river side's direction is authoritative" ground-truth
   category the brief named. For each station with a local KlongMap bearing estimate, the
   nearest major-river directed edge (by midpoint haversine distance) within a join radius
   was located, and the two bearings compared (angular difference, agree if ≤90°, i.e.
   "roughly same half of the compass" vs "roughly opposite/orthogonal" — chance baseline for
   this threshold under a uniform random bearing is exactly 50%).

### Measured agreement rate — full parameter sweep, not cherry-picked

| radius_px | k_neighbors | gt_radius_km | n | agree | rate | vs 50% chance |
|---|---|---|---|---|---|---|
| 60 | 2 | 1.0 | 12 | 7 | 58.3% | above |
| 60 | 2 | 2.0 | 29 | 11 | 37.9% | below |
| 60 | 2 | 3.0 | 42 | 15 | 35.7% | below |
| 60 | 4 | 1.0 | 12 | 8 | 66.7% | above |
| 60 | 4 | 2.0 | 29 | 13 | 44.8% | below |
| 60 | 4 | 3.0 | 42 | 17 | 40.5% | below |
| 100 | 2 | 1.0 | 12 | 6 | 50.0% | at |
| 100 | 2 | 2.0 | 29 | 10 | 34.5% | below |
| 100 | 2 | 3.0 | 42 | 14 | 33.3% | below |
| 100 | 4 | 1.0 | 12 | 5 | 41.7% | below |
| 100 | 4 | 2.0 | 29 | 9 | 31.0% | below |
| 100 | 4 | 3.0 | 42 | 13 | 31.0% | below |
| 150 | 2 | 1.0 | 12 | 3 | 25.0% | below |
| 150 | 2 | 2.0 | 29 | 7 | 24.1% | below |
| 150 | 2 | 3.0 | 42 | 10 | 23.8% | below |
| 150 | 4 | 1.0 | 12 | 3 | 25.0% | below |
| 150 | 4 | 2.0 | 29 | 6 | 20.7% | below |
| 150 | 4 | 3.0 | 42 | 9 | 21.4% | below |
| 200 | 2 | 1.0 | 12 | 2 | 16.7% | below |
| 200 | 2 | 2.0 | 29 | 5 | 17.2% | below |
| 200 | 2 | 3.0 | 42 | 8 | 19.0% | below |
| 200 | 4 | 1.0 | 12 | 0 | 0.0% | below |
| 200 | 4 | 2.0 | 29 | 2 | 6.9% | below |
| 200 | 4 | 3.0 | 42 | 4 | 9.5% | below |

**22/24 tested configurations sit AT OR BELOW the 50% chance baseline** — most well below
(down to 0–20% at larger radii). Only the two smallest-sample configurations (n=12,
arrow-radius 60px) exceed chance, at 58.3% and 66.7%; given how sharply the rate degrades as
radius or neighbor count changes (a hallmark of overfitting a small sample, not a stable
underlying signal — a genuine effect should not collapse to 0–20% from a 50-150px radius
change), those two are read as noise from a small n, not evidence of a real effect. A
diagnostic check (bearing agreement WITHOUT the local-rotation-correction step, i.e. treating
schematic pixel angle as if it were already a real compass bearing) does slightly better at
the smallest radius (58.6–66.7% at n=12–29) but degrades the same way at larger radii and is
not what the maintainers' method specifies (the rotation-correction step is the actual proposal)
— included here only as a diagnostic, not as a candidate for integration.

**Decision: NOT usable.** Applying the maintainers' own stated bar ("clearly >50-60% on a
large-enough sample"): no configuration is both clearly above that bar AND has a defensible
sample size — the only configs above 60% have n=12, and every larger, more statistically
defensible sample (n=29, n=42) sits at 31–45%, i.e. at or below chance. This reads as no
genuine signal, not a weak-but-real one. **No `Dr-corroborated`/`Dr-weak-prior` tier was
added, and zero components/edges were assigned a direction from this method.** This is
consistent with, and reinforces, the root cause already established in the three prior
KlongMap attempts (above): the panel is a non-metric schematic diagram, and that distortion
is apparently severe enough locally that even the smallest, most locally-scoped extrapolation
tested across four attempts (single global affine → local kNN affine → per-canal 1D
arc-length → whole-panel Delaunay rubber-sheet → now local-neighborhood bearing + rotation
prior) still does not recover a usable directional signal.

**Bottom line: direction coverage is UNCHANGED by this idea, confirmed by re-running the full
pipeline after this experiment** — still 380/2,595 connected components (≈15%), 2,170/6,155
edges, identical to every prior session. This is the **4th** independently confirmed negative
result on extracting real-world direction from KlongMap for this graph. The gap remains
honestly `OPEN`. Reproducible via `klongmap_local_prior_experiment.py` (standalone, does not
modify `build_bangkok_canals.py` or its three existing unused georeferencing functions).

## Epistemic tiering

| Artifact | Tier | Note |
|---|---|---|
| Canal line geometry, `waterway` type, `name` | `finite_diagnostic` | OpenStreetMap crowd-sourced data via HOTOSM's Thailand export — HDX's own caveat: "cannot be considered exhaustive." Not independently verified by this pipeline. |
| Junction snapping (~33m grid) | `Dr` | Engineering judgment on tolerance; a tighter/looser grid would merge/split junctions differently. Not validated against ground survey. |
| **Edge direction** (`direction_basis="heuristic_nearest_river_sink"`) | `Dr` | A geometric-proximity guess, NOT a topological fact like HydroRIVERS' `NEXT_DOWN`. Only covers ~15% of components. The other ~85% are honestly `unknown`, not guessed. |
| BMA floodgate/pump locations | `finite_diagnostic` | Official BMA opendata (`data.bangkok.go.th`), lat/long as published, last updated 2024-06-08 per the portal's metadata — not independently field-verified here. |
| `water_level_outer_daily.csv` / `water_level_inner_daily.csv` raw readings | `finite_diagnostic` (source) | Real 2026 daily max water-level-by-station-name data, BMA opendata. The pipeline does not independently verify these values. |
| Water-level station ↔ `floodgate.csv` coordinate match (`nearby_water_level_stations`) | `Dr` (fuzzy name match, see below) | 6/10 stations matched at SequenceMatcher ratio ≥ 0.55; ratio is stored per node as `water_level_match_confidence` so a consumer can raise the bar. **This is a location join for water-level context, not a direction source** — one scalar reading at one point cannot establish flow direction. |
| KlongMap per-canal 1D arc-length bridge (`direction_basis="klongmap_1d_arc_length_bridge"`) | `Dr` (defined but **unused** — 0 edges carry this basis) | Implemented and leave-one-out tested against real data this session; 0/21 eligible canals cleared the 150m LOO-median trust gate (actual errors 1.1–5.1 km on the 9 cleanly-matched canals). See "2026-09-23 per-canal 1D arc-length bridge" section above. |
| KlongMap Delaunay rubber-sheeting (`direction_basis="klongmap_delaunay_rubber_sheet"`) | `Dr` (defined but **unused** — 0 edges carry this basis) | Literature-standard piecewise-affine conflation, implemented and leave-one-out tested against all 199 control points this session; median LOO error 867m (6/199 stations under the 150m trust gate), 0/241 arrows cleared the per-triangle local-trust gate. See "2026-09-23 Delaunay-triangulation rubber-sheeting" section above. |

## Station name↔coordinate join (2026-09-23, partially unblocked)

`match_water_level_stations_to_floodgates()` fuzzy-matches each of the 10 unique BMA
water-level station names (7 inner-zone + 3 outer-zone — the full station roster in the
downloaded CSVs) against `floodgate.csv`'s 230 coordinate-bearing rows, after stripping the
"ปตร."/"ประตูระบายน้ำ" boilerplate both datasets use inconsistently. Result: **6/10 matched**
at ratio ≥ 0.55 (cutoff is a `Dr`-tier judgment call, not validated against a ground-truth
join):

| Station (water-level CSV) | Matched floodgate.csv name | ratio |
|---|---|---|
| ปตร.คลองสองสายใต้ | ประตูระบายน้ำคลองสองสายใต้ | 1.000 |
| ปตร.คลองทวีวัฒนา (ด้านใน) | ประตูระบายน้ำคลองทวีวัฒนา | 0.774 |
| ปตร.คลองแสนแสบ-มีนบุรี | ประตูระบายน้ำแสนแสบ (มีนบุรี) (ด้านใน) | 0.718 |
| คลองแสนแสบ - เขตบางกะปิ | ประตูระบายน้ำคลองบางกะปิ | 0.688 |
| คลองลาดพร้าว 56 | ประตูระบายน้ำคลองน้ำแก้ว (ตอนซอยลาดพร้าว 41) | 0.591 — **weak, likely wrong** |
| คลองทวีวัฒนา ตัดคลองภาษีเจริญ | ประตูระบายน้ำคลองทวีวัฒนา | 0.585 |

The "คลองลาดพร้าว 56" case is instructive: the true best-name candidate
(`ประตูระบายน้ำลาดพร้าว 56`, ratio would be ~1.0) exists in `floodgate.csv` but has **no
lat/long** (that row's coordinate columns are blank — a data-quality gap in BMA's own
source file, confirmed by inspecting the raw row), so it's correctly excluded from the
candidate pool and the algorithm honestly falls back to a weaker, more doubtful match
instead of silently using a fabricated location. This is exactly why `match_ratio` is kept
on every match rather than presenting the join as settled.

**This does not give flow direction** even where matched — a single water-level reading at
one point says nothing about which way water is moving; that would need two stations on
the same canal reach or a time-lag signal, neither of which exists in this data. It is
wired in purely as location context (`nearby_water_level_stations`,
`water_level_match_confidence` attributes on graph nodes within 300m).

## Known limitations

- **~85% of canal segments have no claimed flow direction — unchanged this session.** This
  is the single biggest limitation — most of inner Bangkok's canal network (including
  everything found near the เขตสะพานสูง demo below) falls in this bucket. Four independent
  attempts this session — the 2026-09-23 global research sweep, the per-canal 1D arc-length
  bridge, the Delaunay-triangulation rubber-sheeting, and the KlongMap local-bearing
  weak-prior/corroboration experiment (all above, all real and separately tested against
  real ground truth, not assumed) — all found no honest way to close this gap; it remains
  `OPEN`. The 4th attempt specifically measured whether a *deliberately weaker, soft-prior*
  use of KlongMap (not precise snapping) could corroborate otherwise-unknown directions and
  found the measured agreement rate against ground truth sat at or below the 50% chance
  baseline in 22/24 tested parameter configurations — not usable even as a low-confidence
  tie-breaker.
- No hydraulic/discharge data on canal edges (OSM doesn't carry it); no connection to
  `build_kg.py`'s `travel_time_hr`/ETA propagation machinery for canals.
- Floodgate join radius (300m) and sink-anchor radius (3km) are both `Dr`-tier judgment
  calls, not tuned or validated.
- OSM waterway completeness in Bangkok is unverified — HDX's own caveat applies (crowd
  sourced, not guaranteed exhaustive); some real canals may be missing or mis-tagged.
- Water-level station join is 6/10 by name only (see above), one of which is a weak/likely
  wrong match; and even matched stations give water level, not direction.
- DEM-based direction inference was tested against real data and found noise-dominated
  (see sweep table above / `dem_signal_check.py`) — not usable for this terrain.

## เขตสะพานสูง (Saphan Sung) demo — confirmed run

Nearest canal junctions to the target point (13.7734, 100.6835), all **379m–1.2km away**
(versus ~14km to the nearest node in the *major-river* graph — this is the concrete
improvement this extension delivers):

```
379 m away | junction=100.68330,13.77000 | floodgates_nearby=None | direction_basis=unknown
691 m away | junction=100.68150,13.77930 | floodgates_nearby=None | direction_basis=unknown
743 m away | junction=100.68510,13.77990 | floodgates_nearby=None | direction_basis=unknown
...
```

Honest reading: local canal infrastructure **is now visible** near this point (sub-km
resolution, versus 14km before) — but **no BMA floodgate fell within 300m** of these
specific junctions, and **direction is unknown** for all of them (this area's canals did
not fall within 3km of a major-river sink). This extension improves *spatial resolution*
for this area; it does not yet give a verified flow direction or flood risk verdict for it.

## Output
- `output/bangkok_canals.graphml` — 8,672 nodes, edges as built above
- `output/bangkok_canals.jsonld`
