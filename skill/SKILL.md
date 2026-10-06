---
name: floodconnect-sandwich-method
description: "Vendor-neutral method for any AI agent to answer 'is it safe near the water' for a Bangkok-area community (e.g. หมู่บ้านสัมมากร) using free government feeds, the Jev Sandwich Zoom reading order, a closed 5-colour vocabulary, main-pond rise/ETA tracking, and the user's own saved history for continuity. No vendor name, no hosted compute, no scheduler."
version: 0.1.5
---

# FloodConnect Sandwich method (v0.1.5)

## PROVENANCE — read this first, especially if your model is small

**What this is:** a method file (not software) — instructions any AI agent follows
to answer "is it safe near the water" for a Bangkok-area community. **Version
0.1.5, 2026-10-06. Canonical repo: https://github.com/morrocwi/floodconnect** — if
this file and that repo disagree, the repo wins; this copy may be stale.

**Source of truth, by kind — never this file's memory:**
- **Agency data** (level, warning/critical, order) → the issuing agency itself
  (RID/thaiwater, BMA, TMD, ปภ.), fetched fresh, not recalled.
- **Equations** → their Toledo code + tier (e.g. `PROP-FLOOD-02`, the shipped
  linear two-window ETA, tier `Dr`, a *registered proposal*, status
  `unverified` — registered ≠ settled theorem; `PROP-FLOOD-11`, the
  acceleration-aware form, is a separate registered proposal, not implemented
  in this release).
- **Method rules** (what to fetch, what colour, what to say) → this file.

**Tag legend**, on every item any answer produces: `VERIFIED` (checked live
this run) · `MEASURED` (read/computed this run) · `RELAYED` (passed on, not
independently checked) · `PROPOSAL` (unregistered-as-theorem, tier shown) ·
`OPEN` (not yet known, never guessed) · `STALE` (real but old, carries its age).

**Never trust:** a third-party aggregator as a decision source (`RELAYED` at
best), any AI's unchecked memory of a number, or a station relation with no
declared KG source (§2-§3).

**Scope.** Validated against real data for Bangkok and หมู่บ้านสัมมากร only.
Any other area is marked `experimental` here and in the answer's scope tag —
gazetteer, outlet paths and thresholds outside this scope are unchecked.

---

## FAST PATH (shell/MCP agents — §1c; read this, then §0-§3 for why)

1. Call `kb.py answer --at <point>` (or MCP `floodconnect_answer`) **once**.
2. Relay its emergency card as your own first line, verbatim.
3. Split the rest into **FACTS** (sourced + timed readings) and **CONCLUSIONS**
   (colour/ETA/advice, tagged as inference) — never blend them.
4. Never read a raw PDF/HTML/API payload yourself; the tool already did the
   Sandwich.
5. No shell/MCP? Use the install ladder in §1(b)/(d) instead.
6. Precedence: the **safest** action wins — an official order is a floor, never a
   ceiling (§3).

---

This file lets any AI do the full job alone — fetch, decide, track rise/ETA,
save — on the **user's own** machine/account/network/keys, using FloodConnect's
own repo CLI/MCP only as an optional shortcut, never as a hosted dependency it
depends on. Runs on a shell-and-HTTP agent, a chat-only agent with no tools, or
anything between; no vendor name.

---

## 0. Three opening questions (ask these first, every time)

Frame the question with three, mapped onto the "rings" used throughout (Z0 =
the point itself, Z1 = canals near it, Z2 = the water area above it, Z3 = the
basin above it): **น้ำมาจากไหน** (where does the water come from? → Z3, the
overview) · **ไปไหน** (where does it go? → Z1, the outlet) · **เหลือ margin
เท่าไร** (how much margin is left? → Z0, the point's own level vs. its own
bank/critical line, and how fast). Framing only, not an equation — same order
as §3 below (both ends first; middle only on conflict).

---

## 0b. FAST LAYER — one line before the Sandwich zoom

Run this ONE step before any Sandwich Zoom (§3) — it IS the drill engine,
deliberately tiny: 3 rules, no scores, no threshold to tune.

**Report ladder (sources used by this step):**

| Level | Source | Status |
|---|---|---|
| WIDE | TMD downloadable documents (tmd.go.th/service/downloadableDocuments) + RID daily situation report (water.rid.go.th/flood/flood/daily.pdf) | VERIFIED, keyless |
| PROVINCE | Bangkok: BMA DDS prnews index (dds.bangkok.go.th/content/prnews/index.php), newest id matching today's Thai date. Other provinces: the local ปภ./regional RID office — **OPEN, find and add** when first needed | VERIFIED (Bangkok only) |
| POINT | The keyless APIs in §2 | VERIFIED |

**The sandwich is on the REPORTS, not the stations.** TOP = the WIDE row.
BOTTOM = the PROVINCE row for the point's own province. Skim each with one
question only ("มีอะไรที่พื้นที่ user สนใจต้องรู้ไหม") and note its issue time —
never a side-by-side cross-check (rejected on token cost). Apply the first
matching rule, in order:

| # | Rule | Output |
|---|---|---|
| 1 | TOP and BOTTOM **both calm** | `ต้องขยับไหม: ไม่` |
| 2 | TOP and BOTTOM **both** name the point's own area/basin at warning-or-worse | `ต้องขยับไหม: ใช่` — show the emergency card FIRST, then continue |
| 3 | TOP and BOTTOM **conflict** (one calm, one not), or **either is missing**, unreadable, or older than its own usual cadence | `ต้องขยับไหม: ใช่` |

Output exactly one line: `ต้องขยับไหม: ไม่/ใช่ — <เหตุผลสั้น> (<source> @<issue time>, ...)`.
`ไม่` → stop here, this IS the answer. `ใช่` → continue into §2-§3 and pull the
middle from the APIs; do not re-run this table once already inside the
Sandwich zoom it triggered.

---

## 1. Install (pick whichever of (a)-(d) fits the user's AI)

**(a) Skill folders.** If the user's AI loads skills from a folder, copy this
whole `skill/` directory into it. Nothing else to configure.

**(b) Custom instructions / project knowledge.** If the AI only accepts pasted
text or uploaded files, paste §2-§9 in full and upload `skill/examples/` if it
accepts attachments. No code needed — §2's fetches are plain HTTP GET/POST,
§3-§5's computation is arithmetic simple enough to do inline.

**(c) Agents with shell/HTTP (optional repo CLI/MCP).** If the user's AI can run
shell commands or call an MCP server, and the user has cloned the FloodConnect repo,
it can call the repo's own entrypoints instead of re-implementing §2-§5 by hand:

- CLI: `python kb.py answer --at sammakorn --household '<json>'` (aliased
  `compute`; omit `--household` to get `UNKNOWN_ASK_INPUTS`, not a silent STAY).
- CLI: `python kb.py locate --at <lat,lon>` — point → province/sub-basin/
  nearest assets, offline, <3s.
- CLI: `python kb.py forecast --at sammakorn` — per-model rain forecast.
- MCP tool names (server `floodconnect`, stdio) — all 11 the server registers:
  `floodconnect_answer`, `floodconnect_locate`, `floodconnect_check`,
  `floodconnect_watch`, `floodconnect_list_areas`, `floodconnect_get_area_state`,
  `floodconnect_get_station`, `floodconnect_get_typology_subgraph`,
  `floodconnect_find_safe_route`, `floodconnect_list_upstream_sources`,
  `floodconnect_explain_rules`. `floodconnect_check` is the L0 daily check (3
  keyless sources, one QUIET/ESCALATE line); `floodconnect_watch` is the same
  check plus the cross-session watchlist state machine — prefer `watch` over
  bare `check` for any point worth remembering across sessions.

These names are verbatim as of v0.1.5 — never invent a different spelling.
Still follow §3-§8 below for anything the repo's own output does not already
cover (continuity, ETA range, saving, the email example).

**(d) No tools at all.** If the AI cannot fetch URLs or run code, ask the user
to open the agency pages in their own browser and paste back the numbers
(level, warning, critical, bank, status word, observed time); continue from
§3 using those values, tagged RELAYED (the user read it, not the AI).

---

## 2. Fetch — keyless endpoints, in Sandwich order

No API key is needed for the three sources below; a keyed source (HII etc.,
see below) is never pre-filled with an embedded key.

Fetch order follows the Sandwich: read the point (Z0) and the overview (Z3) first;
only fetch the middle (Z1/Z2) if they disagree, one is missing/stale, or a horizon
question needs it (see §3). In pseudocode:

```text
S0  GET  thaiwater public/waterlevel   (all stations, keyless)
        https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel
    -> for each station: level (waterlevel_msl), station.min_bank, situation_level
       (1-5, agency ordinal), status word, observed time, "ล้นตลิ่ง (ม.)" text.
    -> filter to the point's own KG-connected basin/sub-basin + its upstream chain
       (never nationwide for a local question) = your Z2/Z3 candidate set.
    -> a hotspot read: keep only rows at/over critical or carrying ล้นตลิ่ง/situation 5,
       PLUS the one or two stations the point itself is anchored to.

S1  POST bma_watermap  (one POST, all BMA stations, keyless)
        https://weather.bangkok.go.th/water/PageMap/GoogleMap
        body: payload=TEST_DATA_GOES_HERE   (the page's own "get everything" value)
        (verified keyless, HTTP 200 with real station data, 2026-10-07)
        headers: Content-Type: application/x-www-form-urlencoded,
                 Referer: https://weather.bangkok.go.th/water/
    -> gives water_id, water_code, water_name, wl_in (level), warning/critical,
       observed time, for every BMA canal/pond station, e.g. WL.SMK.01 water_id=284.
    -> this is the point (Z0) for a BMA-covered pond, and the Z1 canals near it.

S2  GET  StationDetail?id=<water_id>   (ONE GET per point you actually need history for)
        https://weather.bangkok.go.th/water/StationDetail?id=<water_id>
    -> parse the inline Highcharts series: Date.UTC(Y, M0, D, h, m, s), v
    -> M0 is 0-based (BMA's own JS convention) — add 1 to get the real month.
    -> the whole literal is Bangkok LOCAL wall-clock time, NOT UTC, despite the name
       "Date.UTC" — subtract 7 hours from the naive local datetime to get real UTC
       (confirmed against the same station's own watermap timestamp).
    -> this is the point's (Z0's) own rise/fall series: use it for §4's trend and ETA.
```

**One GET/POST per source per answer, no retry, no polling.** On failure
(non-200, non-JSON, network error), say so plainly and fall back to the last
locally saved value if one exists (§6), tagged STALE with its age — never a
fresh colour from a stale value, never a fabricated number.

**KlongMap pump links — still OPEN.** `weather.bangkok.go.th/Klongmap/GetDataForUpdate`
is VERIFIED keyless and its schema carries `pump_count`, but every row probed
(2026-10-06) came back `null` for pump fields — map geometry, not live pump
data. Keep pump links OPEN until a call actually returns populated counts/ids.

**Keyed sources.** HII's own endpoints (`waterlevel_graph`, dam data) need a
key — if used, it is the **user's own**, requested from HII
(`contact@hii.or.th`) or the issuing agency, never a key found in a script or
a prior chat turn. Anything the user has not connected is OPEN, never guessed.

**TLS on `.go.th` hosts.** Some serve an incomplete certificate chain. Use a
client that completes it itself (a real browser, or the OS trust store), or
supply this repo's own `assets/tmd_intermediate_ca.pem` to complete the chain.
**Never bypass certificate verification** (no `curl -k`/`--insecure`, no
`verify=False`) — this is forbidden, not merely discouraged, and there is no
"genuinely has to be bypassed" case: use the shipped intermediate certificate
instead.

**KG-only — no heuristic relation anywhere, fetch or answer.** A relation
between the point and any other station exists ONLY if it is a **declared KG
edge carrying a declared source** (agency-published flow direction, a
same-named-canal match with matching river name, a station ON the declared
outlet path). Heuristic joins — bare code-prefix family, unscoped
same-sub-basin membership, an OSM edge with unknown direction, any
radius/distance "nearest station" pick — are **removed entirely**: with no
declared edge, a station does not appear in the fetch or the evidence list at
all. Where the KG lacks an edge the method needs, the ring is `UNKNOWN` and
the gap is logged `policy_gap` — never guessed, never silently dropped.

**Simulation is OFF by default.** Any modelled/simulated/extrapolated load —
the water-debt model (M5), a forecast load ladder, any synthetic series — sits
behind one config flag, off by default; the answer says so when such a source
would otherwise apply. What remains: measured readings, KG edges, and the
time-to-bank arithmetic on measured slopes (§4, PROP-FLOOD-02) — arithmetic on
two real rates, never simulation.

---

## 3. Decide — Jev Sandwich Zoom + the 5 colours

**Read order (the sandwich, not a straight ladder):**

1. Read the two ends first: Z0 (the point, §2 S1/S2) and Z3 (the overview, §2 S0
   filtered to the connected basin).
2. If they agree (both calm, or both pointing the same way), decide now — skip the
   middle.
3. If they conflict (Z3 shows upstream trouble but Z0 is calm, or vice versa),
   extract the middle: Z1 (canals near the point) and Z2 (the water area just above
   it), walking the KG path toward the point. Check whether the water is actually
   moving toward the point, and whether a gate/pump is holding it back.
4. Decide from whichever evidence you actually have. Missing data at any layer is
   UNKNOWN for that layer — never GREEN by default.

**3-state trend**, computed per station from two readings k ticks apart:
`RISING` / `STABLE` / `FALLING` (and `UNKNOWN`/`NO_READOUT` when there is no
comparable prior reading). Only compute acceleration/ETA (§4) when the trend is
RISING — do not compute it for STABLE or FALLING.

**The 5 colours — icon and label are always a pair, never split:**

| Key | Icon | Thai label | Meaning |
|---|---|---|---|
| `GREEN` | 🟢 | ปกติ | Normal, with a fresh real reading backing it. |
| `YELLOW` | 🟡 | เฝ้าระวัง | Agency WATCH/warning word, OR confirmed water coming but not yet confirmed close, OR an outlet at/over critical (see below). |
| `ORANGE` | 🟠 | เตรียมพร้อม | **FloodConnect's own label**, not an official tier (echoes "เฝ้าระวังและเตรียมพร้อม"). Point RISING above its own warning level but not yet critical, OR middle layer confirms water moving toward it along the KG path. |
| `RED` | 🔴 | วิกฤต | **Reserved for the point's OWN Z0 reading** at/over its own bank/critical level. An upstream/nearby RED does NOT make the point RED — see outlet rule. |
| `UNKNOWN` | ⚪ | ไม่ทราบ | No fresh basis to call any of the above. **UNKNOWN ≠ ปลอดภัย (UNKNOWN is never SAFE).** |

**RED is only ever the point's own ring.** An upstream/nearby RED with the
point itself below critical: ORANGE if the middle layer confirms water moving
toward it along a declared KG path, otherwise YELLOW. No distance/km rule —
nearness is evidenced by the middle layer actually rising, not kilometres.

**Outlet rule.** The outlet is the point's declared drainage path, not any
nearby canal. For หมู่บ้านสัมมากร: **คลองแสนแสบ → แม่น้ำเจ้าพระยา** (the Chao
Phraya main stem). A station on that path at/over critical floors the point
**at least YELLOW**, even with a calm Z0 — never upgraded to "water coming"
by congestion alone.

**Zero/null thresholds mean UNKNOWN, never a free pass.** A declared
warning/critical/bank value of `0`/`null`/at-or-below ground level is **not
usable** — UNKNOWN for that ring, never GREEN by default, never a fabricated
RED from a reading vs. a broken zero threshold.

**No heuristic relation reaches this section (§2's KG-only rule).** A station
without a declared KG edge never appears, so it can never set a colour.

**Precedence — the SAFEST action wins; an official order is a FLOOR, never a
ceiling.** Take the maximum of: the official order (evacuate/warning, if one
exists), ground truth (what the user/community actually reports seeing), and
this method's own reading-based verdict (above). An official EVACUATE/WARNING
always raises the verdict to at least that level. A missing, late, or weaker
official order **never lowers** a verdict already reached from ground truth or
a RED reading — official orders can arrive too late (orders have, in real
events, lagged behind the water). With no order yet and the point's own
reading or the ground report at RED, the answer MUST say to move to safety
now, plus **"ยังไม่มีคำสั่งทางการ — อย่ารอ"** (no official order yet — do not
wait) — **never** just "ทำตามประกาศทางการ" when the reading already says RED.

**A layer check that never gets skipped:** if any ring (Z1/Z2/Z3) is RED, the
overall colour is never GREEN — raise to at least YELLOW, even with a calm Z0,
since a fresh RED anywhere on a declared path is real evidence.

---

## 4. MAIN-POND WATCH — trend, abnormal-rise tag, and mandatory time-to-bank

Every answer reports the main pond's (the point's own Z0) **3-state trend**
(RISING/STABLE/FALLING), not just its bare level — this is the core indicator ("คนริม
น้ำดูว่าน้ำขึ้นเร็วแค่ไหน... น้ำท่วมคือน้ำล้นตลิ่งเป็นเรื่องแรก").

**Abnormal rise tag.** Tag a rise as abnormal ONLY from the user's own saved
history (§6) or an explicitly cited value (e.g. "fastest in your last 10
readings") — never a bare instinct. No saved history → the question stays
OPEN. Once tagged, the tag persists (`tags_carried`, §6) until it resolves.

**Mandatory time-to-bank when RISING.** When — and only when — the trend is RISING,
you MUST compute, as a labelled PROPOSAL (`PROP-FLOOD-02`, linear, two windows —
see the equation-discipline note below; this is NOT `PROP-FLOOD-11`), BOTH of:

- time to the published **warning** level, and
- time to the published **bank/critical** level,

each as a **range**, from two slopes (this IS the linear two-window form — not a
second-difference/acceleration calculation):

1. the **current slope** — the rate over the single latest interval (the two most
   recent readings), and
2. the **longer-window slope** — the rate over a longer span (e.g. the last several
   hours), so the user can see whether the rise is speeding up or slowing down.

This is never silently skipped while RISING. The refusals the shipped code actually
applies, each stated explicitly with its reason, checked in this order per
threshold: `AT_BANK` (already at or over that threshold) → `NO_READOUT` (a
required prior reading is missing or outside its lag tolerance) →
`PUMP_STATE_CHANGED` (the pump at this node switched on/off/mode mid-window,
which invalidates a plain rate extrapolation of the raw level) →
`PUMP_STATE_UNDECLARED` (no pump state declared for this station at all — never
silently assumed unchanged) → `NO_RISE` (neither slope is actually rising) →
`NOT_WITHIN_HORIZON` (the slope never reaches the threshold, or only after an
unreasonably long time).

**Show every computed number as a calculation, not a bare answer** — formula/eq
code, each input with its own source and time, then the result; a missing
input is named, never guessed, and gets an ordinal confidence
(`HIGH`/`MEDIUM`/`LOW`/`NONE`) with its reason instead of a falsely precise
number. Compact pattern:

```text
<field> = <eq code> | inputs: name=value (source, time), ... | missing: <name>, ...
result: <value or range> | confidence: HIGH/MEDIUM/LOW/NONE — <reason>
```

**Worked example (real numbers, WL.SMK.01, 2026-10-06):** level −0.31 m at 05:00;
warning 0.35 m, critical 0.44 m; current-interval slope 0.047 m/h, longer-window
slope 0.02 m/h.

```text
eta_to_warning/critical = PROP-FLOOD-02 (Toledo, tier Dr, PROPOSAL, linear, two windows)
inputs: h(t)=-0.31 m (BMA StationDetail WL.SMK.01, 05:00), warning=0.35 m, critical=0.44 m
        (BMA agency-declared), slope_fast=0.047 m/h (latest interval), slope_slow=0.02 m/h
        (longer window) — no missing inputs
gap to warning  = 0.35 - (-0.31) = 0.66 m
gap to critical = 0.44 - (-0.31) = 0.75 m
time @ fast slope: 0.66/0.047 ≈ 14 h to warning, 0.75/0.047 ≈ 16 h to critical
time @ slow slope: 0.66/0.02  ≈ 33 h to warning, 0.75/0.02  ≈ 37 h to critical
result: about 14-33 h to warning, 16-37 h to critical
confidence: MEDIUM — both slopes measured and dense enough, but n=1 range from only
            two window lengths, not a validated forecast
-> report exactly that, tagged PROPOSAL (PROP-FLOOD-02, linear, two windows),
   never cited as settled.
```

**Missing-input example.** If a household's vulnerable-group count (elderly,
disabled, infants, pets/livestock) is missing, the home-shelter calculation
names it as missing and lowers confidence/score, reason "ไม่มีข้อมูลกลุ่มเปราะบาง"
— never scored as if nobody vulnerable were present.

**Equation-discipline note.** The ETA above is `PROP-FLOOD-02` (linear, two
windows) — an already-**REGISTERED, already-merged** proposal in Toledo main
(tier `Dr`), reusing `PROP-FLOOD-01`/`PROP-FLOOD-02`'s own `delta_k`/
`time_to_threshold` arithmetic called twice, at two different lags. It is NOT
`PROP-FLOOD-11`. `PROP-FLOOD-11` (the acceleration-aware quadratic, 2nd
retained difference) is a SEPARATE, also-registered Toledo proposal (tier `Dr`,
PR #65 merged 2026-10-06, commit `65297f05`) that is **registered but not
implemented** in this release (v0.2 is the target for wiring it in) — do not
cite it as the equation behind the shipped ETA. Use `PROP-FLOOD-02` directly,
labelled `PROPOSAL`, for every RISING answer; this does not depend on the
FloodConnect repo's own internal code path.

---

## 5. Continuity — link every answer to the user's own last saved record

Every answer reads the user's own previously saved report or reading (§6) before
presenting anything new, and states:

- the **gap** since that previous record (how long ago),
- **Δ** (change in the main pond's level since then),
- whether the **trend changed** (SPEEDING_UP / SLOWING_DOWN / UNCHANGED / REVERSED),
- which **tags are still carried** (e.g. an abnormal-rise tag from §4 that has not
  resolved),
- a **prediction_check**: what the last answer's ETA (§4) said vs. what actually
  happened by now, if checkable.

**No previous record found → state `NO_PREVIOUS` explicitly.** Never guess a
previous state or silently treat "no record" as "first-ever reading". **A
long gap (days/weeks) is informational only** — do not strain for a
meaningful Δ/trend-change across a gap too long for that to be meaningful;
just state the gap honestly.

---

## 6. Save (user-side, opt-in) — continuity, learning, offline record, evidence

**Invite once, briefly, never inside the card.** After giving the first answer in a
session, offer in at most 2-3 Thai lines, something like:

> อยากให้บันทึกผลอ่านนี้ไว้ในเครื่อง/บันทึกของคุณเองไหม? จะช่วยให้ (1) ดูความต่อเนื่อง
> ครั้งถัดไปได้ (2) ให้ AI เรียนรู้จากประวัติของคุณเอง (3) มีบันทึกไว้ใช้ได้แม้ไม่มีเน็ต
> (4) เป็นหลักฐานให้ชุมชนอ้างอิงได้ — ไม่มีอะไรถูกส่งไปที่ FloodConnect เลย

If declined, do not ask again this session. **At most one re-invite**, only at
the next 🟠/🔴.

**Storage targets — detect what the user actually has, offer only that:** local
CSV (UTF-8+BOM, one file per table — see `skill/examples/sheets/`); the user's
own connected spreadsheet via their MCP (append rows, never overwrite); or a
database they already run. Remember the pick in the user's own storage.

**Fixed tables, append-only, never pruned (per the retain-every-run rule):**

- `readings`: `ts_utc, station_code, variable, value, unit, bank, critical,
  warning, agency_status_word, trend, source_id, fetched_at_utc, sha256`
- `reports`: `report_id, ts_utc, area_id, colour_key, colour_label_th,
  previous_report_id, delta_since_previous, trend_change, tags_carried,
  eta_warning_h_range, eta_critical_h_range, saved_by`
- `actions`: `report_id, step_id, what_th, how_th, trigger_next, source_tag`
- `api_calls`: `ts_utc, source_id, url, status, fetched_at_utc, sha256, saved_to_local`

**No polling, no scheduler.** Archive only the calls the AI actually made for a real
user question — never a background sweep. **Never a FloodConnect-hosted store** —
everything lands in the user's own disk, their own connected spreadsheet, or their
own database. **No credentials ever go into saved rows.**

**On-trigger write.** When a trigger fires (the colour crosses into 🟠/🔴, or a
watch-listed point worsens), write an `alert_event` into the user's own
connected calendar/sheet/DB/notes via the user's MCP, using the storage
preference from the invitation above. **First time only:** a one-line offer,
same invitation as above. After that, write automatically — the one-decision
rule, no repeated asking. **Never write a duplicate** (dedupe by event id). No
connected tool available → just show the alert in the answer; write nothing.

---

## 7. Answer format

Produce, in this order:

1. **Emergency card FIRST**, ≤ 80 tokens: colour icon+label pair (§3), `now`
   (current reading in one line), one concrete `do` action, hotlines **1784**
   (ปภ., disaster) and **1669** (สพฉ., medical emergency), plus **1555** (BMA,
   Bangkok only), and the line **"ไม่ใช่ประกาศทางการ"** (not an official
   announcement).
2. **Layers/evidence** — Z0/Z1/Z2/Z3 each with its own colour, the reading(s) behind
   it, observed time, and source. Show contradictions as both sides, never silently
   resolved to one.
3. **Preparedness steps as a TABLE**, columns: `ลำดับ | เตรียมอะไร | เตรียมอย่างไร |
   เมื่อไรขยับขั้น | แหล่ง`.
4. **Home-shelter verdict**, only when household info is given, shown as a
   calculation (§4's pattern) — missing fields named, never guessed, confidence
   lowered accordingly. Missing input → never STAY (the verdict is
   `UNKNOWN_ASK_INPUTS`, naming what's missing). Precedence follows §3's floor
   rule — an order can only raise this verdict, never lower one already at
   LEAVE.
5. **Policy-gap note** — if an agency page genuinely carries no instruction text for
   something asked about, say so and mark it OPEN rather than inventing guidance.
   A missing KG edge (§2-§3) is logged the same way, as `policy_gap`.

---

## 8. Email/report EXAMPLE

A full worked example is in `skill/examples/` — the schema itself lives at
`schemas/email_report.schema.json` (so its sibling `$ref`s resolve against
this repo's own schema set), with `example_2026-10-06_1300.json` and its
`.html` render kept in `skill/examples/`. **One example output
format, not the only behaviour required** — the rules above are the
instructions; the email just demonstrates one way to present them.

Rules that example enforces, and any new render must keep:

- Every table is a real table, never a flat list dressed up as prose.
- Every station mentioned links to that station's own page (e.g. its
  `StationDetail?id=<water_id>` URL); every pump mentioned links to its own page.
- If no real URL for a station/pump is known, the link is marked **OPEN** with the
  reason (e.g. "PumpHistory 404 — this endpoint has been dead since it was first
  checked") — **never invent a URL.**

---

## 9. Never

- Never invent a value or a threshold. A missing number is UNKNOWN/OPEN, not a
  guess.
- Never call RED from an upstream/nearby station alone — RED is the point's own Z0
  ring only (§3).
- Never say GREEN for missing data — missing data is UNKNOWN.
- Never let an official order LOWER a verdict already at RED/LEAVE — an
  order is a floor, not a ceiling: it may always RAISE the verdict, but a
  missing, late, or weaker order must never pull a reading- or ground-based
  RED/LEAVE back down (§3's floor rule). Never answer only "ทำตามประกาศทางการ"
  when the reading itself already says LEAVE.
- Never use a heuristic (code-family, name-only, radius/distance, unscoped
  sub-basin) to relate two stations — only a declared KG edge connects them
  (§2-§3).
- Never guess at a KG-graph gap; log it `policy_gap` and answer UNKNOWN.
- Never rename a place/station from the agency's own verbatim Thai name. The pond at
  หมู่บ้านสัมมากร is **บึงรับน้ำหมู่บ้านสัมมากร** — never a mistaken back-transliteration
  like "สามมะกอก". If only an English slug is known, write the slug in Latin letters
  and mark the Thai name OPEN rather than guessing a Thai spelling.

---

## 10. Wording

"Flood" is not only bank/canal overflow — pluvial/road flooding (standing
water with no canal overflow) is a separate channel; this method's core axis
(level vs. agency bank/critical, plus trend) covers river/canal flooding only.

HEC-RAS/SWMM-style simulation is out of scope — not because it "can't run
locally", but because the inputs it needs (storage curves, calibrated
discharge coefficients) are not published by the agencies this method reads.

---

## Integration map (method → tool)

| Step here | API source | Repo function (if using (c)) | Field/output |
|---|---|---|---|
| §2 S0 | thaiwater `public/waterlevel` | `collect.collect_thaiwater_waterlevel` | `reading.schema.json` rows |
| §2 S1 | BMA `PageMap/GoogleMap` POST | `collect.collect_bma_watermap` | per-station `canal_water_level_m` |
| §2 S2 | BMA `StationDetail?id=` | `collect.fetch_bma_station_series` | `station_level_history_m` series |
| §3 | — | `floodconnect_model.sandwich_decision`, `colour_ladder`, `STATUS_TO_LEVEL` | `jev_decision.colour` |
| §4 | — | `floodconnect_model.trend_state`, `rise_eta_hours_range` (PROP-FLOOD-02, shipped); `rise_eta`/`_rise_eta_prop11_computation` (PROP-FLOOD-11, registered, not implemented, v0.2) | `z0.eta`, `calc.eta` (labelled PROPOSAL) |
| §5 | — | (no repo equivalent yet — user-side only) | `reports.previous_report_id` etc. |
| §6 | — | (no repo equivalent yet — user-side only) | local CSV / sheet / DB tables |
| §7 | — | `advice.build_advice`, `advice/card.py` | `emergency_card`, `advice.prepare_steps` |
