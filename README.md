# FloodConnect

**FloodConnect คืออะไร:** เว็บเพจสาธารณะที่รวบรวมข้อมูลระดับน้ำคลอง ปั๊มระบายน้ำ ปริมาณฝน
น้ำขึ้น-ลง และรายงานจากชาวบ้าน สำหรับพื้นที่เสี่ยงน้ำท่วมในกรุงเทพฯ (เริ่มที่หมู่บ้านสัมมากร
รามคำแหง 112 และซอยรามคำแหง 53) โดยอัปเดตตัวเองอัตโนมัติทุก 30 นาทีผ่าน GitHub Actions —
**อัปเดตด้วย GitHub Actions ล้วน ๆ ไม่ใช้ AI และไม่พึ่งอินเทอร์เน็ตบ้านของใครคนใดคนหนึ่ง**

**ดูหน้าเว็บสาธารณะได้ที่:** https://morrocwi.github.io/floodconnect/ *(placeholder — จะใช้งานได้เมื่อ
เปิด GitHub Pages ของ repo นี้)*

**แหล่งข้อมูล / Data attribution (จากหน่วยงาน — ไม่ใช่การพยากรณ์ของทีมนี้):**
- ระดับน้ำคลอง + ปั๊มระบายน้ำ — สำนักการระบายน้ำ กรุงเทพมหานคร (ผ่าน HII/สสน. thaiwater.net และ
  weather.bangkok.go.th)
- ถนนน้ำท่วม — สำนักการระบายน้ำ กรุงเทพมหานคร (thaiwater.net)
- รายงานประจำวัน — ศูนย์ควบคุมระบบป้องกันน้ำท่วม กทม. (dds.bangkok.go.th)
- น้ำขึ้น-น้ำลง — กรมอุทกศาสตร์ กองทัพเรือ
- รายงานชาวบ้าน/สื่อสังคมออนไลน์ — RELAYED เท่านั้น ไม่เก็บชื่อผู้โพสต์ ไม่ใช่หน่วยงานราชการ
- ถนน/คลอง/โรงพยาบาล (แผนที่พื้นฐาน) — © OpenStreetMap contributors, licensed under the
  Open Database License (ODbL) — see openstreetmap.org/copyright
- `output/*.graphml` (โครงข่ายแม่น้ำ/ลำคลอง) — HydroSHEDS/HydroRIVERS (Lehner group).
  HydroSHEDS is freely available for scientific, educational and commercial use under its
  licence agreement — see hydrosheds.org
- แบบจำลองระดับสูงภูมิประเทศ (DEM) — Copernicus DEM (ESA), free to use with attribution
- สสน./HII (thaiwater.net), สำนักการระบายน้ำ กรุงเทพมหานคร, กรมอุทกศาสตร์ กองทัพเรือ — ข้อมูล
  สาธารณะของหน่วยงานรัฐ (terms: OPEN)

**คำเตือนที่ต้องอ่าน:** ทีมนี้เป็นทีมอาสาสมัคร ไม่ใช่หน่วยงานราชการ ไม่มีเครื่องมือวัดของตัวเอง
ทุกตัวเลขคือการ "อ่านค่า" จากแหล่งข้อมูลของหน่วยงานที่ระบุไว้ ณ เวลาที่ระบุ ไม่ใช่การพยากรณ์หรือ
การยืนยันความปลอดภัย ข้อมูลอาจล่าช้า ขาดหาย หรือคลาดเคลื่อนได้ — ใช้ร่วมกับดุลยพินิจของตัวเอง
และช่องทางทางการเสมอ (โทร 1669 เหตุฉุกเฉิน, 1555 แจ้งน้ำท่วม กทม.)

**เครดิต:** ทีม ศูนย์ความรู้พลเมืองปัญญาประดิษฐ์ · อารยานิกะห์ วิสาหกิจเพื่อสังคม ประเทศไทย

**สัญญาอนุญาต (Licence):**
- โค้ด (code): MIT — ดูไฟล์ `LICENSE` ของ repo นี้ (อาจเปลี่ยนแปลงได้โดยผู้ดูแลโครงการ)
- เอกสาร/ข้อความ (documentation/text): Creative Commons Attribution 4.0 International (CC BY 4.0)
- ข้อมูลของหน่วยงาน/บุคคลที่สาม (third-party data): แต่ละแหล่งคงสัญญาอนุญาตเดิมของตัวเอง — ดูหัวข้อ
  "แหล่งข้อมูล / Data attribution" ด้านบน; รายงานชาวบ้าน/สื่อสังคมออนไลน์เป็น RELAYED (นำมาเล่าซ้ำ
  พร้อมระบุแหล่ง ไม่ใช่ของทีมนี้เอง และไม่ใช่การยืนยันจากทีมนี้).

---


## Community self-help DAG

FloodConnect now includes a **human-response DAG** in addition to water/flood readouts:

`Self / Household → Buddy cell → Zone → Internal safe node → Egress → Verified external safe node`

- Model + field protocol: `docs/COMMUNITY_SELF_HELP_DAG.md`
- Declared topology for the current FloodConnect areas: `site/inputs/community/self_help_dag.yaml`
- Validator / constraint-first route selector: `community_dag.py`
- Tests: `tests/test_community_dag.py`

The routing layer is deliberately fail-closed: **UNKNOWN, stale, blocked, or unverified routes are not used**.
It does not create a flood-risk score or declare a place safe from map proximity alone. An external target must
be field-verified, fresh, explicitly `SAFE`, have enough declared capacity, and provide any required services.

### Shelter decision + community sustainment

FloodConnect now has a proposal layer for the question that comes **before** evacuation:
what is the **lowest support node at which the household/community can still remain safe and
function for a declared planning horizon**?

The repo-specific construct is **Lowest Viable Community Node (LVCN)**:

`household → buddy_cell → zone → internal/community shelter → external_safe`

`egress` remains a movement connector and is not an LVCN candidate. Resource/help delivery is
a separate support network, because supplies/helpers can move inward while residents stay put.

The aim is to preserve safe self-sustainment at the lowest feasible layer, not to move people
to a shelter earlier than necessary. It also introduces the states `STAY_AND_SUSTAIN`,
`RESUPPLY_WINDOW`, `PREPARE_TO_MOVE`, shelter screening/operation, and
return/relocation/closure.

- Decision engine: `shelter_decision.py`
- Design + research anchors: `docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md`
- Thailand-first equations/typology: `docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md`
- AI implementation handoff: `docs/HANDOFF_SHELTER_DECISION_AND_SUSTAINMENT.md`
- Operational fail-closed schema: `site/inputs/community/sustainment_policy.yaml`
- Field failure modes: `site/inputs/community/shelter_field_evidence_2026-09-28.md`
- Tests: `tests/test_shelter_decision.py`
- Environmental time-to-unsafety engine: `environmental_degradation.py`
- Environmental degradation equations/evidence: `docs/ENVIRONMENTAL_DEGRADATION_CLOCKS.md`
- Environmental tests: `tests/test_environmental_degradation.py`
- Human–Animal Household Unit: `human_animal_household.py`
- Human–animal equations/evidence: `docs/HUMAN_ANIMAL_HOUSEHOLD_UNIT.md`
- Thai animal field evidence: `site/inputs/community/human_animal_field_evidence.md`
- Human–animal tests: `tests/test_human_animal_household.py`
- Unified crisis-state readout: `unified_crisis_state.py`
- Unified state tests: `tests/test_unified_crisis_state.py`

FloodConnect now also models **safe-now -> degrading -> unsafe** transitions that can occur
without rising water depth: sewage/backflow contamination, sewer-gas/H2S uncertainty,
wet-material/mold clocks, standing-water/vector clocks, and stagnant organic-water odor
potential. These mechanisms remain separate; there is no single universal "age of floodwater"
threshold.

**LVCN is a FloodConnect proposal, not a claimed FEMA/Sphere/UNHCR/CCCM standard.**
The design remains fail-closed: no universal stock-duration default, no weighted safety score,
no unverified resupply route, and no building treated as a shelter from its name/type alone.

## Technical

The sections below are the original technical documentation for the underlying river-network
knowledge graph and live flood-context data system that FloodConnect's public page is built
on top of (`site/build_data.py` / `site/build_page.py`, driven by `collect.py` +
`sources/registry.yaml`; see `docs/DATA_SYSTEM.md` and `site/DATA_README.md` for the full
field-by-field source map).

### Thailand River Flow-Propagation Knowledge Graph

## Repo notes

- `raw/` is **not committed** (git-ignored) — it's large (~113MB: HydroRIVERS clip, HOTOSM
  waterways, BMA CSVs, a Copernicus DEM tile) and trivially re-downloadable. Regenerate it by
  following each build script's "Re-running" section below / in `README_bangkok_canals.md`.
- `.env` is **not committed**. Copy `.env.example` to `.env` and fill in a real
  `GISTDA_API_KEY` to re-run the live flood-overlay parts of the pipeline.

## What this is NOT — read this first

**This graph's "next downstream node" answer is a topological readout of river-network
connectivity (deterministic from the HydroRIVERS dataset), NOT a flood forecast or
prediction.** It does not model discharge propagation timing, rainfall, or reservoir
operation. It answers "which node is structurally downstream of this one" — not "will it
flood, when, or how high." Treat it as a static map of *where water can go*, not a
predictive alert system. Do not present its output as a forecast.

## What this is

A directed graph of Thailand's major river reaches. Given a flooded node, the next
downstream node(s) — the ones structurally positioned to receive that water next — are
its graph successors:

```python
import networkx as nx
G = nx.read_graphml("output/thailand_river_flow.graphml")
list(G.successors("41177595"))   # -> next downstream reach id(s)
```

or in the JSON-LD export, read the `flowsInto` array on that node's entry.

**Direction is topological, not geometric.** Every edge in this graph comes directly from
HydroRIVERS' own `NEXT_DOWN` field — a value HydroSHEDS derived from DEM-based flow
routing, not from anything this pipeline computed. Nowhere does this pipeline infer flow
direction from lat/lon bearing (no `atan2`/`acos` on coordinates anywhere in
`build_kg.py`). This is a deliberate design choice: geographic bearing between two points
says nothing about which way water actually flows (rivers meander, and a "downstream"
neighbor can sit north, south, east, or west of its upstream neighbor); only the
network's own recorded topology can say that.

## Pipeline

`build_kg.py`:
1. Load HydroRIVERS v1.0 Asia extract, clip to Thailand's bbox (97.3–105.7°E, 5.5–20.5°N).
2. Filter to "major rivers": keep reaches with Strahler order (`ORD_STRA`) ≥ 6.
3. Build a directed graph: node = HydroRIVERS reach (`HYRIV_ID`), edge = flows into the
   next reach that also survived the order filter. Where the raw `NEXT_DOWN` pointer
   lands on a *minor* (filtered-out) reach first, the pipeline walks further downstream
   through the full (unfiltered) network until it reaches the next *major* reach, so the
   major-river graph stays end-to-end connected instead of fragmenting at every small
   tributary confluence. The physical length of every skipped minor reach is accumulated
   into that edge's `length_km` attribute.
4. Compute centrality (Degree, Closeness, Betweenness, Eccentricity, Eigenvector) on the
   undirected projection, mirroring the methodology in Phukseng (2020), *J Sci Technol
   MSU* 39(4):388–399, "An Analysis of Water Network Employed by Graph Theory-based
   Centrality: A Case Study of Flood Risk Areas in Chanthaburi Province." Closeness and
   Betweenness use `weight="length_km"` — shortest path means shortest *river distance*
   (summed reach lengths along the path), not hop count.
5. Assign a basin-proxy grouping (see caveat below).
6. Optionally overlay live flood extent from GISTDA's Disaster API (needs `GISTDA_API_KEY`
   env var; skipped otherwise, `flood_status` stays `"unknown"`).
7. Export GraphML (opens directly in Gephi, same tool the Thai paper used) and JSON-LD.

### Re-running

```bash
# one-time: get the raw HydroRIVERS Asia shapefile (~90MB zip, ~370MB unzipped)
mkdir -p raw
curl -o raw/HydroRIVERS_v10_as_shp.zip \
  https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip
unzip raw/HydroRIVERS_v10_as_shp.zip -d raw/

# build the graph
python3 build_kg.py --strahler-min 6

# build it with a live flood overlay
GISTDA_API_KEY=your_key_here python3 build_kg.py --strahler-min 6
```

The Thailand-bbox clip is cached at `raw/thailand_bbox_clip.parquet` after the first run
(re-run deletes/skips re-clipping automatically by reusing that cache — delete it if the
upstream HydroRIVERS data is ever updated).

## Epistemic tiering

| Artifact | Tier | Note |
|---|---|---|
| Reach topology, `NEXT_DOWN`, Strahler order, discharge (`DIS_AV_CMS`), reach length | `finite_diagnostic` | Measured/derived by HydroSHEDS from satellite+DEM data (HydroRIVERS v1.0 Technical Documentation). This pipeline did not independently verify these values — relayed from the source, cited, not laundered as this pipeline's own finding. |
| Strahler-order threshold (≥ 6, yielding 2,250 of 91,116 reaches in the Thailand bbox) | `Dr` (engineering judgment) | Order distribution in-bbox: order 1–47,223 · 2–21,254 · 3–10,691 · 4–5,999 · 5–3,699 · 6–1,123 · 7–968 · 8–159. Order ≥ 6 was chosen to land in the "few hundred to ~2,000 major reaches" range the task asked for; ≥ 7 (1,127 reaches) or ≥ 5 (5,949 reaches) are equally defensible alternative cuts — this is not a proven-optimal threshold. |
| `basin_proxy_id` (13 groups) | `Dr` (approximate, not authoritative) | Grouped by HydroRIVERS' own `MAIN_RIV` id (reaches draining to the same river mouth). **This is NOT the official 25 ลุ่มน้ำหลัก (major river basins) of Thailand's Office of National Water Resources** — no authoritative Thai basin-boundary shapefile was fetched for this run, so this is a topology-based proxy, not a verified administrative boundary. Expect it to disagree with the official 25-basin map in places (fewer groups here, since some officially-separate adjacent basins may share/merge at this order threshold, and some very short coastal basins may have no reach reaching order 6 at all and are absent). |
| `flood_status` (when populated via `GISTDA_API_KEY`) | `finite_diagnostic` | GISTDA's own satellite-derived flood-extent readout for the request's `/flood/30days` window, spatially joined onto node centroids at run time. **The endpoint is paginated (OGC-features style)**: an unparameterized call returns only ~10 of the true total — confirmed live at 14,376 flood polygons nationwide (`numberMatched`) behind a default page of ~10 (`numberReturned`), detected via the response's `links` `rel:"next"` entry. `overlay_gistda_flood()` now pages with `limit=1000&offset=N` (1000 accepted as-is, not silently clamped) through all 15 pages to collect the full 14,376 before joining. A single unparameterized call would have silently undercounted by >99% (this was caught and fixed after an initial run wrongly returned 0 flooded nodes). The result is still a **snapshot**, not a live feed — this pipeline stamps every run with the UTC fetch timestamp (printed to stdout, e.g. `2026-09-22T16:53:29Z`); re-run to refresh. Confirmed run: 30 of 2,250 nodes flagged `"flooded"`. |
| Centrality scores (Degree/Closeness/Betweenness/Eccentricity/Eigenvector) | `finite_diagnostic` (computation), applied to a `Dr`-tier graph | The centrality math itself is exact given the graph; the graph it's computed on already carries the `Dr`-tier threshold/basin choices above, so treat centrality-based risk rankings as suggestive, not settled. |

## Future integration: Google Flood Forecasting API (stubbed, not active)

`overlay_google_flood_forecast()` in `build_kg.py` is a documented stub, not a working
integration — it raises `NotImplementedError` if called. Why it matters and why it's not
wired up yet:

- GISTDA's `/flood/30days` (used by `overlay_gistda_flood()`) is a **snapshot** of
  currently/recently detected flood extent — it answers "is this node flooded right now,"
  not "will it flood." Google's Flood Forecasting API (developers.google.com/flood-forecasting,
  part of Google Flood Hub) publishes up to **7-day-ahead riverine forecasts**, which is
  the actual missing piece for turning this graph into a forward-looking tool.
- **Access is gated**, not a self-serve key: join a waitlist, supply a Google Cloud
  Project ID, wait for manual approval. Confirmed via web research 2026-09-23
  (`Dr`/relayed tier — not independently verified by calling the API, since no access
  exists yet).
- Coverage is 150+ countries / 1,800+ gauge sites globally as of that research pass;
  **Thailand-specific gauge density was not confirmed** — would need to inspect
  floodhub.google.com's map directly (a JS app, not checkable via a headless fetch).
- The gauge ID scheme is undocumented in the pages checked and is almost certainly not
  HydroRIVERS' `HYRIV_ID` — once real access and gauge coordinates exist, joining gauges
  onto this graph's nodes will likely need a nearest-neighbor spatial match, not a direct
  ID join. Don't assume that match works until it's built and checked against real data.

To activate: get API access, then implement the function per its docstring.

## Known limitations
- Flood-polygon proximity join uses a `0.01` degree (~1.1km at Thailand's latitude)
  fallback buffer for "reach centroid near but not strictly inside a flood polygon."
  `Dr` tier — a judgment call, not validated against ground truth; left as-is for this
  run, not tuned further. A tighter buffer would likely reduce false positives near
  large flood polygons' edges; a looser one would catch more true positives on reaches
  that pass near but not through a mapped polygon.
- No river-name field exists in HydroRIVERS; every node is `name: "unnamed"`, identified
  only by `HYRIV_ID`.
- `basin_proxy_id` is a proxy, not the official 25-basin boundary set (see table above).
- Without `GISTDA_API_KEY`, `flood_status` is `"unknown"` on every node — this pipeline
  does not fabricate flood state.
- Thailand bbox clip includes a thin strip of neighboring countries' border reaches
  (Myanmar/Laos/Cambodia/Malaysia) since it's a rectangular clip, not a country-polygon
  clip — acceptable for a first version, but don't assume every node is inside Thailand
  without checking.

## Sammakorn canal ↔ gate ↔ pond ↔ pump hydraulic DAG

FloodConnect now models the Sammakorn retention system as **two different hydraulic edges** rather than one ambiguous bidirectional link:

`external canal → gate/gravity → retention pond → pump → receiving canal → wider canal network`

- `gate/gravity` = controlled inflow into available storage when the external water surface is above the pond.
- `pump` = mechanical outflow from the pond toward a receiving canal.
- `pumped inflow` into the four ponds is **not established** and must not be inferred from the phrase “ดึงน้ำเข้าบึง”.
- Missing water levels, gate state, or receiving-canal condition remain `UNKNOWN` / fail-closed.

Human-readable model: `docs/SAMMAKORN_HYDRAULIC_DAG.md`

Machine-readable topology/state rules: `site/inputs/canals/sammakorn_hydraulic_dag.yaml`

## Live canal water level

`live_water_level.py` attaches a live Bangkok canal water-level reading onto the canal
graph's nodes (`build_bangkok_canals.py`'s output). **Read "What this is NOT" above first
-- a live reading is a point readout, not a forecast, and (per
`README_bangkok_canals.md`'s water-level-station section) one station's level alone does
not give flow direction.**

Sources checked 2026-09-26:

| Source | Status | Detail |
|---|---|---|
| BMA KlongMap backend (`weather.bangkok.go.th/Klongmap/GetDataForUpdate`) | **Blocked (HTTP 403)** | Confirmed even with full browser-like headers (User-Agent/Accept/Referer). Parsing is implemented and unit-tested against a real recorded response shape (a cached dump from this repo's earlier session) so it activates automatically the moment the block lifts. |
| HII/สสน. `standard.thaiwater.net` (spec doc) | **No queryable host** | This is a national data-exchange *specification* document (its own "Base URL" doc gives a placeholder host), not a hosted API. Superseded below. |
| **HII/สสน. `api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel`** | **LIVE, working** | Found by loading `https://www.thaiwater.net/bma` (HII's own "สถานการณ์น้ำกรุงเทพมหานคร" page) in a browser and reading the page's own XHR calls. Public, unauthenticated `GET` -- no token/cookie/login observed or required; confirmed reachable with a plain `urllib.request` + generic User-Agent (`200 OK`). 282 BMA canal-station records (`agency.agency_name.en == "Department of Bangkok"`, i.e. สำนักการระบายน้ำ กรุงเทพมหานคร), each with real `canal_lat`/`canal_long`, current `canal_value` (m), and `canal_datetime` (local Thailand time, converted to UTC on parse). This is now the live path (`fetch_thaiwater_stations()` / `parse_thaiwater_canal_stations()` in `live_water_level.py`). |

**Licence / attribution note (RELAYED, not independently confirmed against a formal licence text):**
no terms/licence link was found in the `/bma` page's footer during this check. The data is
served under HII/สสน.'s "National Hydroinformatics Data Center" (thaiwater.net) brand and every
record is agency-tagged upstream as สำนักการระบายน้ำ กรุงเทพมหานคร (BMA). Attribute both when
reusing this data: "Source: HII/สสน. (thaiwater.net), data from สำนักการระบายน้ำ กรุงเทพมหานคร
(BMA)." Re-check `thaiwater.net`'s terms directly before any public/commercial redistribution --
this note is a relay of what was observed 2026-09-26, not a legal clearance.

Run `python3 live_water_level.py --probe` to re-check both live sources (KlongMap +
thaiwater canal) with one fresh request each (no retry loop). Run
`python3 live_water_level.py --attach <graph.graphml> --out <file>` to fetch live and
attach onto an existing canal graph, or add `--from-file <saved raw JSON>` to attach
offline from a previously-cached response (e.g. `raw/live/thaiwater_bma/<ts>_canal_waterlevel.json`)
with no network call at all. Nodes gain `live_water_level_m`, `live_water_level_observed_at`,
`live_water_level_station`, `live_water_level_source`, `live_water_level_match_confidence`
-- never overwriting attributes from another source. A real run on 2026-09-26 matched
**179 of 282** stations to graph nodes within the 300 m join radius (all via direct
coordinate join, not the fuzzy name fallback); KlongMap remains 403 (0 readings from it).

**Thresholds/status**: each station also carries BMA's own published `warning_level`,
`critical_level`, `bank` (metres, `None` when BMA publishes none for that station), plus
`canal_oldcode` (BMA code, e.g. `WL.SSB.07`) and, for a floodgate station (`canal_name`
starting `ปตร.`), an outside-gate `canal_out` reading. `classify_level()` turns a reading
into `NORMAL` / `WATCH` / `CRITICAL` / `OVERBANK` / `NO_THRESHOLD` against those bands --
a readout against BMA's own bands, not a forecast. **Staleness**: a station's `observed_at`
is compared to the newest `observed_at` in the same fetched batch; anything more than 24h
older (or with no parseable timestamp) is treated as stale and skipped by both `--attach`
and `--watch`. **`--watch LAT LON [--radius-km 5] [--from-file JSON]`** prints a plain-text
table of every non-stale station within radius, sorted by distance, with a one-line
"N stations, X CRITICAL, Y WATCH, Z stale skipped" summary -- read-only, no graph touched.

**Sammakorn pump stations (ST.SPS.01-04)**: `fetch_pumphistory()` / `parse_pumphistory_html()`
read BMA's `weather.bangkok.go.th/Station/PumpHistory` server-rendered summary table
(confirmed live 200 OK 2026-09-26, one GET, no retry -- note the same host returned 403 on
`/Home` and `/Map` the same day, treated as a per-path difference). Each row gives
`level_m`, `pumps_on`/`pumps_total`, `gate_open` (m, `None` if no gate), `district`,
`lat`/`lon` (real coordinates, `coord_source="pumphistory datapump"` -- from the same
page's own embedded metadata array, not a fuzzy join), and `observed_at`. `--watch
--pump-from-file <saved PumpHistory HTML>` prints them as a separate block sorted by
distance from the --watch centre; `attach_live_pump_status(graph, pumps)` joins each pump
to its nearest canal node within the same 300 m radius (never overwriting), writing
`live_pump_code/_name/_level_m/_pumps_on/_pumps_total/_gate/_status/_observed_at`.

## Output
- `output/thailand_river_flow.graphml` — 2,250 nodes, 2,236 edges
- `output/thailand_river_flow.jsonld`

## Live flood-context data system (registry + collector + readout)

`sources/registry.yaml` + `collect.py` + `store.py` + `readout.py` are a separate,
newer layer on top of `live_water_level.py` (reusing its fetch/parse functions, not
duplicating them): a registry-driven collector that pulls from multiple agencies
(thaiwater canal/flood-road telemetry, BMA PumpHistory, the DDS daily PDF bulletin, the
DDS flood-report HTML table, the Navy Hydrographic monthly tide-table PDF), stores
everything append-only in `data/observations.sqlite` (gitignored), and renders a
Markdown+JSON readout centred on a point (`python3 readout.py --centre LAT LON`).

**No flood-risk score or formula exists anywhere in this system** -- every row is a
MEASURED reading, a RELAYED official forecast/report figure, or explicitly OPEN
(missing), each tagged with a `trust_tier` (Thai agencies compete and sometimes
disagree; this system shows the disagreement as an explicit contradictions section,
never resolves it). Full pipeline diagram, the trust-tier vocabulary, the host-safety
rule, and how to add a new source: **`docs/DATA_SYSTEM.md`** (Thai-first, English
summary at the end).

## Sammakorn pond–canal hydraulic DAG

FloodConnect now separates the Sammakorn pond/canal interface into two different hydraulic edges:

```text
CANAL/DRAIN --[GATE + GRAVITY]--> POND
POND        --[PUMP]-----------> RECEIVING CANAL
```

- Human-readable model: `docs/SAMMAKORN_POND_CANAL_DAG.md`
- Machine-readable topology: `site/inputs/canals/sammakorn_pond_canal_dag.yaml`

Key rule: **“draw water into the pond” does not automatically mean “pump into the pond.”**
Current evidence supports controlled/gravity inflow into storage and verified pumped outflow from Sammakorn pump stations 1–4. Exact gate geometry and the station-to-specific-canal mapping remain fail-closed where unverified.
