# ROADMAP.md — release slots after v0.1.0

> Read `ARCHITECTURE.md` first — it explains *why* these slots are ordered this way
> (the Water-Debt Core at the centre, Toledo-first for every equation). This file is
> the *sequence* and the *acceptance criteria*; it does not re-derive the model.

**Status key**: `done` (shipped, measured) / `next` (first slot after v0.1.0) /
`planned` (ordered, not started) / `backlog` (not yet slotted into a specific release).
Never state a `planned`/`backlog` item as current — see `ARCHITECTURE.md` §9 for the
implemented-vs-planned table this roadmap extends.

## Binding rules (apply to every item below, no exceptions)

- **No hosted data.** No release ships a pre-computed reading, a live Pages dashboard,
  or any server-side fetch. Every item below that adds a data source makes it
  *installable and fetchable by the caller*, never served by us.
- **Caller-side only, no scheduler on our side.** Every live fetch still runs on the
  installer's own machine/network/keys; `floodconnect watch` (V10) is scheduled by the
  caller's own OS/assistant, not by any cron we operate.
- **UNKNOWN != SAFE**, everywhere, unconditionally.
- **Toledo-first.** No equation ships in the decision path (`state`/`hazard`/
  `next_action`) until it is at minimum a registered proposal; see
  `ARCHITECTURE.md` §1 for current registration status per PROP-FLOOD code. An
  equation still in an open PR or a draft branch stays confined to the
  experiment/proposal branch of the code, never the shipped decision path.
- **Claim-first.** Every semantic change claims its canonical RKG node(s) first (see
  `AGENTS.md` / the DSVA red-team protocol's (DSVA architecture doc) claim-first protocol) before implementation.
- **Failure evidence is preserved, never deleted or quietly rewritten into a pass.**
  Backtests that fail (e.g. `HIT 0 / MISS 12` at the 80mm design threshold) stay
  published and linked, not buried, per the honesty-by-construction rule already in
  `README.md` F5.
- **Never claim what is not implemented.** Anything below not yet shipped is written
  here as "planned (v0.2+)" or a later version, not as a present-tense feature.

## v0.1.1 — external-AI-readability fixes (next)

This release. Started as a doc-only pass, then picked up real code changes from an
independent post-release review (see `.ai/claims/20261004-floodconnect-v011-claim.yaml`
for the authoritative scope — never call this release doc-only elsewhere). Fixes a
free-AI (no-code-execution) clean-room evaluation gap: the repo description/README/
docs still described a hosted 30-minute-cron API that was retired 2026-10-03/04.
Scope: repo description/topics, README first-screen wording (English + Thai), purge
every remaining "hosted API"-looking surface (`docs/AI_INTERFACE.md`,
`docs/DATA_SYSTEM.md`, the local `floodconnect-agent` skill), a
product-path-vs-experiment file map, `llms.txt`, `docs/EVIDENCE.md` (negatives
first), this `ARCHITECTURE.md`/`ROADMAP.md`/`docs/handoff/NEXT_AI_HANDOFF.md` set, a
new static `site/landing/` explainer page (no data) via a minimal `pages-landing.yml`
workflow, the WATCH=YELLOW reclassification + its YELLOW action, and a bbox-scoped
refresh path. **Acceptance**: an unprimed clean-room agent (URL only, no file list
handed to it) answers all of "what is it / is it live / does it forecast / how do I
get an answer / what are the limits / what evidence exists" correctly in one pass, in
English and in Thai; `llms.txt` present; no "every 30 minutes" / "hosted API" string
survives in a public-facing doc (a "GitHub Pages" string IS now expected — it names
the static landing page only, never a data surface); token budget test still green.

> **Sequencing note (2026-10-04):** V8 (Toledo registration) and V6 (water debt) were
> re-sequenced right after v0.2.0 per founder ruling 2026-10-04 ("แกนคือสมการที่เรา
> พัฒนา เอาโมเดลเราเป็นศูนย์กลาง" — V8 moves earlier because every model feature
> depends on it; "สมการหนี้น้ำของเราเอาระบบนั้นเป็นศูนย์กลาง" — V6 moves to right after
> V8 and becomes the spine V1/V2/V3/V4/V7 plug into). The Jev envelope, `--level`
> tiers, and the D1–D8 skeleton were pulled into v0.2.0 itself (same ruling, plus
> "ทำให้ทุกอย่างเป็นภาษา jev one decision" and the token-level ruling). V4 nationwide
> coverage is COARSE zoom only (basin/sub-basin/province, not household detail) per
> the refinement "ไม่ต้องเอาละเอียดเปะ... แค่ให้มันเชื่อมระดับ Zoom กว้างสุด" and moves
> into v0.2.0 alongside V5, rather than keeping its own later slot.

> **DONE in v0.1.2 (2026-10-04, founder ruling "ทำเลย v0.1.2 ทั้งประเทศ"): V4 coarse
> nationwide shipped early**, out of its v0.2.0 slot below — any `lat,lon` in
> Thailand now gets a real `current_local_state`/`forward_hazard`/text-only
> accountability reading at station (≤10 km, nearest station any water body) or basin
> (≤50 km, sharing that nearest station's own sub-basin, never GREEN alone)
> resolution, from the nationwide `thaiwater_waterlevel` feed. See
> `docs/INDICATORS.md` §11 and `CHANGELOG.md`. The V4 bullet below is kept as the
> historical plan text (GISTDA/DWR/GloFAS and basin confidence tiers beyond
> station/basin are NOT part of what shipped) rather than deleted, so the sequencing
> note above still reads correctly.

## v0.2.0 — V5 + V0 skeleton + Jev envelope + `--level` (V4 coarse nationwide shipped early, v0.1.2)

- **V5a/b**: BMA-direct canal gauges + the 233 (later expanded, see F8 note) road
  sensors decide the Bangkok-wide status; ปภ. (DDPM) disaster-area declarations shown
  as official context that always outranks our own reading (D6 in the protocol); any
  stale/contradictory source pair (e.g. the ThaiWater BMA canal set, OPEN conflict as
  of 2026-10-04) recorded as a contradiction row, never silently resolved one way.
- **V0**: the D1–D8 decision-protocol *skeleton* (`ARCHITECTURE.md` §3), covering
  D1–D3 and D6–D7 with today's simpler logic explicitly mapped onto those stage
  boundaries; D4/D5/D8 stay stubbed until V6/V7/V8 land. Two-level hierarchy skeleton
  (area + node) only — full basin→household hierarchy is later.
- **Jev envelope + `--level`**: wrap the current answer into the one-decision
  Choice/Score/Noul/gate shape (`ARCHITECTURE.md` §5), with D4/D5/D8 stubbed until
  V6/V7/V8 fill them from the real model; CLI `--level 1|2|3` + MCP `level` param
  (`ARCHITECTURE.md` §6), default L1 for a home AI (≤5,000 tokens), L2 ≤10,000,
  L3 ≤100,000. Schema + token-budget tests per level.
- **V4 (coarse only)**: nationwide point support — any lat,lon resolves via nationwide
  feeds (HII rain + river gauges, RID, DWR, GISTDA, ปภ., model rain/tide/GloFAS) at the
  WIDE holarchy levels (basin/sub-basin/province, maybe district) only; `--at` also
  resolves from the device's own location, computed locally (never phoned home). No
  household/node-level detail is built nationwide in this slot — fine zoom (community/
  node/household with pumps, gates, water debt) stays only where it is already built
  (Sammakorn, Ram53) and grows case by case later. A coarse-only area states its own
  resolution plainly ("ระดับลุ่มน้ำ/จังหวัด ไม่ใช่ระดับบ้าน") and its confidence reflects
  that.
- **F8 expansion**: CCTV catalog expanded from the current wired set to 600+ cameras
  across agencies (absorbed from the public-API sweep), still `VISUAL-CHECK` only.
- **Acceptance**: BMA-direct + road-sensor status wired with a contract test each; a
  contradiction-row test for the ThaiWater BMA conflict; D1–D3/D6–D7 stage boundaries
  visible in the L2/L3 trace; per-stage latency budget test; Jev envelope schema test
  per `--level`; at least one point outside the Bangkok MVP answers correctly
  end-to-end at coarse resolution (fresh clone → install → `answer --at
  <province-point>`), with its resolution stated plainly; "near me" resolution
  documented as fully local (no location data leaves the caller's machine); full
  regression green.

## v0.2.1 — Toledo registration catch-up (V8, moved right after v0.2.0 — see ARCHITECTURE §1)

Every downstream feature from V6 onward depends on PROP-FLOOD-03..10 being at least
registered proposals, and the core is our model, not the data sources that feed it —
this slot comes right after v0.2.0 for that reason. Merge the four open PRs (#60 water
balance, #61 edge direction, #62 burden ledger, #63 outlet-coping+flow-state), each
through an independent adversarial review (math, Toledo-first parents, Coq, tier
honesty, leak scan, no AI-vendor attribution, no leftover `weld/M.??.v1` placeholder
codes); separately register PROP-FLOOD-08/09/10 from the draft branch. **Acceptance**:
`gh pr view` on each shows `MERGED`; `registry/CANONICAL.json` or an accepted-proposal
file carries a real (non-`??`) code for each; no equation used in `water_balance.py`/
`canal_graph.py`/`burden_ledger.py`/`hierarchical_flood_zoom.py`'s *decision* path
(as opposed to the clearly-marked experiment path) cites an unmerged PR.

## v0.2.2 — V6: water debt as the spine (moved right after V8 — see ARCHITECTURE §1)

PROP-FLOOD-03 water balance → debt `D = inflow − drainable`, with interval support for
partial data (`ARCHITECTURE.md` §7), becomes the spine V1/V2/V3/V4/V7 plug into.
Private-sector sources (pumps/gates/estates/utilities/relief network) wired as a
tracked input class in the registry, read together with government data into the
per-node debt ledger, each still individually tagged. **Acceptance**: `water_balance.py`
returns an interval (not `REFUSED`) on the current Sammakorn partial-input case;
`docs/WATER_DEBT.md` published, citing only Toledo-registered codes (no inline
equations); a worst-case-first test showing an action is only chosen when it holds
across the missing-input interval.

## v0.2.3 — V1: four-driver block

Dams inflow/outflow/% normal storage + day-over-day change as the upstream driver; RID
hourly stations; a 24h trend arrow on every gauge. **Acceptance**: a 4-driver block
(rain/upstream/tide/drainage) with each driver's own tag/source/age, contract tests per
driver, token budget still green.

## v0.2.4 — V2a/b: fallback ladder + crowd evidence rungs

DWR telemetry (capacity %, discharge) and the GISTDA Sentinel-1 extent as additional
observation rungs in the per-driver fallback chain (`ARCHITECTURE.md` §7); Floodboard
crowd reports wired as supporting evidence only, never alone deciding a tier/colour.
**Acceptance**: fallback-chain test demonstrating a driver resolving through at least 3
rungs on synthetic missing-data fixtures; crowd evidence shown but excluded from the
decision in a contract test.

## v0.2.5 — V10: "เกณฑ์บ้านฉัน" (my-home threshold watch)

`floodconnect watch --at X --threshold ...` as a one-shot local check (CLI + MCP tool);
**no scheduler on our side** — if the caller wants recurring checks, their own
OS/assistant schedules repeated one-shot calls. **Acceptance**: one-shot CLI + MCP tool
both exercise the same compute path as `answer` (no second code path to diverge);
documented recipe for wiring it into a caller's own cron/launchd/Task Scheduler/home-AI
scheduler, explicitly not provided by us.

## v0.2.6 — V3: CSV trend + acceleration

BMA water-level/retention-pond (บึง) CSV history for rate-of-rise + acceleration +
time-to-threshold, as a baseline/backtest signal (the live trend still comes from
fresh telemetry, never the lagged CSV). Acceleration (second difference, Δ²) is a
**new** Toledo proposal with PROP-FLOOD-01 as parent (`weld/M.41.v1` +
`WP.S8.SecondDifference` + `PROP-FLOOD-01`, pre-approved for this slot per founder
ruling 2026-10-04) — register it before use, per Toledo-first. **Acceptance**: a
backtest report (hit/miss against real recorded rises, negatives shown) before any
acceleration-derived field reaches the shipped `answer` output; CSV lag stated
explicitly wherever the series is cited (current CKAN series lags ~2 months).

## v0.2.7 — V7: Jev-style decision + DSVA licence gate

The v0.2.0 Jev envelope (`ARCHITECTURE.md` §5: Choice+p / Score / Noul-S4 / gate) is
filled with the real water-debt + tier/flow-state output; the DSVA executable decision
model (`dsva_decision.py`, currently research-track/standalone) is wired as the D8
gate, returning `ADMIT | HOLD | REJECT | ESCALATE` — never `SAFE`. **Acceptance**:
schema test on the envelope shape; a `BOT`-propagates-to-`HOLD` test; at least one real
recorded event (e.g. a Sammakorn 2026 event) run through the full pipeline end-to-end,
with results compared against the fixed-rule baseline already shipped in v0.1.x (never
presented as better without the comparison numbers alongside it).

## v0.3 — V11 local viewer + V9 paper + recommendation kinds

- **V11**: `floodconnect view` renders the caller's own already-computed answer as a
  local HTML/PWA page — the "at-a-glance" ease of a dashboard, still with zero hosted
  data. Ranked **below** every home-AI-relay feature above (the north star is the home
  AI reading the situation and telling the user, not a dashboard — V11 is a convenience
  on top, not the priority).
- **V9**: the DSVA/Jev paper draft (evaluation arms: fixed rules / direct LLM / Jev /
  Jev+DSVA), citing the red-team draft PRs as failure evidence, gated the same way as
  any other publish (Core Epistemic Structure block, no AI co-author, Toledo-first).
- **Recommendation kinds** (backlog, no fixed slot yet): the Jev envelope extended to
  recommend not just an action but a workflow/tool/skill/install — still a Choice among
  declared options + confidence, gated, never auto-installed by FloodConnect itself.

## Backlog sources (not yet slotted into a specific release)

Absorbed or queued from a comparison against peer Thai flood-dashboard products
(peers named only where independently verified, in neutral terms — never a negative
unverified claim about a named competitor):

- **greener.bangkok.go.th** (BKK Big Cleaning) — drain/canal dredging/cleaning
  progress; matters as a drainage-capacity input once a free API is confirmed.
- **Traffy Fondue open-data API** — citizen flood/drain reports with location/time/
  status; wired as crowd evidence (RELAYED/crowd tag), never alone deciding a colour;
  personal-data fields filtered to category/location/time/status only.
- **publicspace.bangkok.go.th** — possible safe-node / assembly-point and storage-area
  data for the self-help DAG and the water balance.
- **citydataportal.bangkok.go.th** — possible fresher district-level flood/drainage/
  rainfall/canal data than the ~2.5-month-lagged CKAN catalog.
- **DWR telemetry portal**, **ปภ. disaster declarations direct endpoint**, **BMA
  floodbangkok direct**, **DOH/motorway/BMA/traffic-centre cameras** — upstream
  government endpoints only (never a peer product's own backend/API), each needing
  direct endpoint discovery before it can be wired (several SPA/404 dead ends found as
  of 2026-10-04; tracked in `sources/api_census.yaml`).

These four BMA-source items ship together as one gated "BMA sources" release once
endpoint discovery is done; they are not pre-assigned a version number above.

## Event archive extraction (v0.3+, explicitly not now)

Real-event materials (BMA road-closure bulletins, plan/drainage PDFs) are archived as
they arrive but **extracted later, not now** — per founder ruling 2026-10-04: archive
now, build the event ledger (road → depth band → time, as observed ground truth for
backtests and for the Jev/DSVA evaluation) in a later version. The archive itself stays
local-only (never published raw) until a specific extraction task defines what, if
anything, is safe to publish from it.

## Fine-zoom (household/node) area sequencing (unchanged from the pre-v0.1.0 plan)

This is the order for adding household/node-level detail (pumps, gates, water debt),
not for nationwide coverage — coarse station/basin-zoom nationwide coverage **shipped
in v0.1.2** (see the DONE note above V4), ahead of this fine-zoom list, which still
adds household detail one area at a time.

Bangkok outer ring → Hat Yai → Nan/Chiang Mai → the country's 359 DWR sub-basins → other
provinces (see `docs/MVP_SCOPE_2026-09-27.md` for the original founder ruling). Any
request that extends area/unit scope is labelled `MVP` or `next-version` before work
starts; a `next-version` item may be recorded as a TODO row but is not run, backtested,
or written into any shipped output until its slot above is reached.
