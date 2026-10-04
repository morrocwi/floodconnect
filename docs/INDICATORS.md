# FloodConnect indicators — the closed dictionary

**Founder ruling 2026-10-04 (verbatim): "ที่สำคัญคือให้ ตัวชี้วัดนี้น้ำน้ำท่วมต้องชัด" — the
flood indicators must be crystal clear.** This page is the single place that names every
indicator FloodConnect's compute path (or its by-hand companion, `floodconnect_model.py`)
can produce, with its exact meaning, unit, source, threshold rule, colour mapping,
freshness rule, resolution label, a worked example, and what it does **not** mean.

The same list, as data, lives in `model_spec.json`'s `"indicators"` array and is mirrored
into `system_capabilities.json`'s `"indicators"` field — a test
(`tests/test_floodconnect_model.py`) checks the two match, that every name below also
appears in README.md's top section, `llms.txt`, `docs/AI_TIERS.md` and
`docs/EQUATIONS_FOR_AI.md`, AND that a real, offline answer actually only ever emits a
value inside that indicator's own declared `levels` (never an undeclared word). Every
`kb.py`-level answer also carries `"indicators_doc": "docs/INDICATORS.md"` at its top
level, so a caller reading only the JSON still gets pointed here. Each indicator's own
section below states its exact `levels` and its real `json_path` inside that answer (or
says plainly that it is by-hand-only / not yet wired) — **never assume the
RED/YELLOW/GREEN/UNKNOWN contract applies to a field whose own section does not say so.**

**Colour contract — scope (fix, 2026-10-04, review finding #3): RED/YELLOW/GREEN/UNKNOWN
below applies ONLY to `current_local_state` (§1) and `one_decision.level` (§9). Every
other indicator in this dictionary has its OWN closed vocabulary — stated in that
section's own "Levels" line and in `model_spec.json`'s per-indicator `levels` field —
and is never silently re-expressed as RED/YELLOW/GREEN/UNKNOWN.**

| Colour | Means |
|---|---|
| `RED` | An agency has published a critical/overflow reading for this station, right now. |
| `YELLOW` | WATCH/warning-like, OR a value genuinely rising toward a published threshold. |
| `GREEN` | Normal, **and** there is a fresh, real reading backing that call. |
| `UNKNOWN` | No fresh basis to call GREEN/YELLOW/RED. **UNKNOWN is never treated as safe.** |

**สีแดง/เหลือง/เขียว/ไม่ทราบ ใช้กับ `current_local_state` และ `one_decision.level`
เท่านั้น — ตัวชี้วัดอื่นมีค่าของตัวเอง (ดูหัวข้อ "Levels" ของแต่ละตัวชี้วัดด้านล่าง):**

| สี | ความหมาย |
|---|---|
| `RED` (แดง) | หน่วยงานประกาศค่าวิกฤต/ล้นตลิ่งของสถานีนี้ ณ ขณะนี้ |
| `YELLOW` (เหลือง) | เฝ้าระวัง/เตือนภัย หรือค่ากำลังขึ้นจริงเข้าใกล้ค่าที่ประกาศไว้ |
| `GREEN` (เขียว) | ปกติ **และ** มีค่าที่วัดจริงและใหม่พอรองรับคำตอบนี้ |
| `UNKNOWN` (ไม่ทราบ) | ไม่มีข้อมูลสดพอจะฟันธง GREEN/YELLOW/RED **UNKNOWN ไม่เท่ากับปลอดภัย** |

---

## 1. `current_local_state`

- **One line:** is the water level at the nearest station reading normal, watch, or
  critical, right now.
- **ความหมายสั้น:** ระดับน้ำที่สถานีใกล้บ้านคุณตอนนี้ ปกติ เฝ้าระวัง หรือวิกฤต
- **Exact definition:** classification of the freshest `status_counts` (the agency's own
  published station-status words — e.g. `CRITICAL`, `OVERBANK`, `WATCH`, `NORMAL`,
  `NO_THRESHOLD`, or the BMA DDS Thai keys `ระดับน้ำวิกฤติ`/`ระดับน้ำปกติ`) for the stations
  feeding this answer, with sensor-fault rows (`ขัดข้อง`) excluded first.
- **Unit:** none (categorical).
- **Levels:** `RED` / `YELLOW` / `GREEN` / `UNKNOWN` (the colour contract above).
- **JSON path:** `next_action.dual_state.current_local_state` in `kb.py`'s `answer`
  output (CLI `--json` / MCP `floodconnect_answer`).
- **Input source:** `floodconnect_model.STATUS_TO_LEVEL` (the ONE closed status-word
  map, v0.1.2 — `readout.py`/`kb.py` read their sets off it) plus `site/build_data.py`'s
  `_DDS_STATUS_TH`, fed by `live_water_level.py`/BMA station rows, the BMA DDS
  bulletin, and (v0.1.2 nationwide) `thaiwater_waterlevel`'s own `situation_level`/
  `diff_wl_bank_text` (see §7 below for exactly how that feed maps to a status word).
- **Thresholds:** the agency's own status word only — never a number this project invents.
- **`thaiwater_situation_N` legend — the agency's own label/range/colour (VERIFIED,
  fetched from the public bundle `https://www.thaiwater.net/dist/js/app.chunk.js`,
  captured 2026-10-04; `storage_percent` bands in the live feed match these ranges
  exactly):**

  | Code | Agency label (TH) | `storage_percent` range | Agency colour |
  |---|---|---|---|
  | 0 | ไม่มีข้อมูล | – | grey `#BDBDBD` |
  | 1 | น้อยวิกฤต | ≤10 | orange `#db802b` |
  | 2 | น้อย | >10–30 | yellow `#ffc000` |
  | 3 | ปกติ | >30–70 | green `#00b050` |
  | 4 | มาก | >70–100 | **blue** `#003cfa` |
  | 5 | ล้นตลิ่ง | >100 | red `#ff0000` |

  **Codes 4→`YELLOW` and 1/2/3→`GREEN` below are FloodConnect's OWN conservative
  mapping, not the agency's.** The agency colours level 4 ("มาก"/high) BLUE and does
  not call it a warning at all; mapping it to `YELLOW` here is this project's
  judgment call that a high-but-not-overbank reading deserves a watch. Likewise 1/2
  ("น้อยวิกฤต"/"น้อย") → `GREEN` is this project's own choice that low water is not a
  flood signal, not an agency claim.

  **⚠ `น้อยวิกฤต` (code 1) means critically LOW water, not a flood risk — it is NOT
  `RED`.** The label contains the Thai word "วิกฤต" ("critical"), but an AI or human
  reading `diff_wl_bank_text`/labels by hand must not pattern-match that word onto
  `RED` here; code 1 maps to `GREEN` (see `docs/NEAREST_STATION_RECIPE.md`). Only the
  distinct keys `วิกฤต`/`วิกฤติ`/`ระดับน้ำวิกฤติ`/`thaiwater_situation_5` (code 5,
  overbank) are `RED`.
- **Colour/level mapping (founder ruling 2026-10-04, verbatim "WATCH = YELLOW (แนะนำ)";
  fix 2026-10-04, regate finding #2: `NO_THRESHOLD` moved OUT of the GREEN set — a
  station with no agency level published at all has no basis for GREEN):**
  - `RED` — any agency-declared critical/overflow word present (`CRITICAL`, `OVERBANK`,
    `ระดับน้ำวิกฤติ`, `วิกฤต(ิ)`, `thaiwater_situation_5`, or `diff_wl_bank_text`
    starting with "ล้นตลิ่ง").
  - `YELLOW` — `WATCH`/เฝ้าระวัง/เตือนภัย/`thaiwater_situation_4` present, or any status
    word not in the normal-like, critical-like, or no-basis sets.
  - `GREEN` — every status word present is normal-like (`NORMAL`, `ปกติ`,
    `ระดับน้ำปกติ`, `thaiwater_situation_1/2/3`), and at least one such row is fresh.
  - `UNKNOWN` — no status word at all, every fresh row was a sensor fault, or every
    fresh row's only status is `NO_THRESHOLD` (no agency level published at all).
- **Freshness rule:** only rows within the source's own `max_age_hours`
  (`sources/registry.yaml`, 24 h for the sources feeding this indicator today) are
  counted; a stale row is shown but excluded from the classification.
- **Confidence:** `next_action.dual_state.confidence` (shipped v0.1.2, `kb.py`'s
  production answer) — `HIGH`/`LOW`, absent (read as `NONE`) when `UNKNOWN`; see §9
  for the exact rule and §11 for station vs. basin resolution.
- **Resolution label:** **station-level**, not household-level — "ประเมินระดับสถานี
  ใกล้เคียง ไม่ใช่ระดับบ้าน". Today's v0.1.x answer is scoped to two Bangkok sites
  (Sammakorn, Soi Ramkhamhaeng 53) at station/node resolution; nationwide coarse
  (basin/province) resolution is **not yet wired into this field** — see §11.
- **Worked example:** Sammakorn, a fresh `WATCH` row at the nearest canal station, no
  critical-like row present → `current_local_state = YELLOW`.
- **Does NOT mean:** a flood-depth prediction, a forecast, or a statement about any
  location other than the deciding station itself.

## 2. `forward_hazard`

- **One line:** is there an active rain-forecast signal for the next few days that could
  change things, separate from the reading right now.
- **ความหมายสั้น:** มีสัญญาณพยากรณ์ฝนล่วงหน้าที่อาจทำให้สถานการณ์เปลี่ยนหรือไม่ แยกจากค่าปัจจุบัน
- **Exact definition:** `_classify_forward_hazard` over the per-model 7-day rain forecast
  rows (`kb.py::cmd_forecast`), never averaged into a single flood-depth number.
- **Unit:** none (categorical).
- **Levels:** `ACTIVE` / `NONE` / `UNKNOWN` — this field's own closed vocabulary. It is
  **not** re-expressed as RED/YELLOW/GREEN/UNKNOWN anywhere (fix, 2026-10-04, review
  finding #3: an earlier draft of this line claimed such a mapping existed in `kb.py`;
  it does not — removed rather than left pointing at code that isn't there).
- **JSON path:** `next_action.dual_state.forward_hazard`.
- **Input source:** Open-Meteo/ECMWF/GFS/JMA/CMA/GEM/MET Norway and sibling public
  weather models, fetched at the queried coordinate.
- **Thresholds:** none published by any agency for "hazardous rain" — this field reports
  presence/absence of a forecast signal, not a flood call on its own.
- **Freshness rule:** same per-source cache/fetch freshness as the forecast call itself;
  a forecast model's own update cadence, not a fixed hour count.
- **Resolution label:** per-coordinate (the lat,lon queried), not per-basin.
- **Worked example:** `per_model` shows rising 7-day totals across most models while
  `current_local_state=GREEN` → dual-state reminder shown, `current_local_state` itself
  stays `GREEN` (this field never promotes or overrides §1 on its own).
- **Does NOT mean:** a flood warning, a water-level forecast, or an average "chance of
  flooding" — it is a relayed rain signal only, dual-state alongside §1.

## 3. `rise_rate_dk` (Δk)

- **One line:** is the water level at this station rising, falling, or flat, and by how
  much, over the last k ticks.
- **ความหมายสั้น:** ระดับน้ำที่สถานีนี้กำลังขึ้น ลง หรือทรงตัว และเปลี่ยนไปเท่าไรในช่วง k ครั้งที่ผ่านมา
- **Exact definition / formula:** `Δk(t) := h(t) − h(t−k)`.
  **PROPOSAL, not yet a registered Toledo theorem** — Toledo code `weld/M.??.v1`, tier
  `Dr`, tracked as `PROP-FLOOD-01` in `model_spec.json` (Toledo PR #59, merged
  proposal-tier, not promoted to `CANONICAL.json`).
- **Unit:** m per k ticks (caller declares what one tick is — e.g. 1 reading or 1 hour —
  before computing, never after).
- **Levels:** `RISING` / `FALLING` / `FLAT` / `NO_READOUT` — this field's own closed
  vocabulary, never RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** not in `kb.py`'s `answer` JSON — this is computed by the by-hand
  companion module only: `floodconnect_model.delta_k(...)["trend"]`
  (`docs/EQUATIONS_FOR_AI.md` §5 shows how to run it against a reading pair by hand).
- **Input source:** two readings of the same station, `h(t)` and `h(t−k)`.
- **Thresholds:** the station's own declared sensor resolution `epsilon` — if the source
  states none, `epsilon` is `INSTINCT` (a judgment call), never `MEASURED`.
- **Colour/level mapping:** this indicator has no colour of its own — `RISING` feeds into
  `one_decision` (§9) as at least `YELLOW`; a missing `h(t−k)` returns `NO_READOUT`
  (never silently `FLAT`, per BOT≠ZERO).
- **Resolution label:** single-station.
- **Worked example:** WL.SSB.08, `h_t=0.38`, `h_t_minus_k=0.30`, `k=1`, `epsilon=0.01` →
  `Δk=0.08 m, RISING`.
- **Does NOT mean:** that the rate will continue — it is a readout of two already-observed
  readings, never a prediction.

## 4. `time_to_threshold_tk` (Tk)

- **One line:** at the current rate, roughly how long until the water reaches a published
  threshold — or an explicit refusal when that cannot be said honestly.
- **ความหมายสั้น:** ถ้าอัตราตอนนี้คงที่ อีกนานเท่าไรน้ำจะถึงค่าที่ประกาศไว้ หรือปฏิเสธตอบตรงๆถ้าบอกไม่ได้
- **Exact definition / formula:** `Tk := (θ − h(t)) · k / Δk(t)`, defined only when
  `Δk(t) > epsilon` (genuinely rising) and `h(t) < θ`.
  **PROPOSAL, same Toledo PR/tier/code as §3** — `PROP-FLOOD-02`.
- **Unit:** ticks (the same tick §3 declared, e.g. "~53 minutes at k=1 h").
- **Levels:** a numeric tick value, or the refusal pair `REFUSED/UNRESOLVED` /
  `REFUSED/NOT_APPLICABLE` — this field's own closed vocabulary, never
  RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** not in `kb.py`'s `answer` JSON — by-hand companion module only:
  `floodconnect_model.time_to_threshold(...)`.
- **Input source:** §3's `Δk` plus `θ`.
- **Thresholds:** `θ` is the station's own declared warning/critical/bank value — never a
  number this project chooses.
- **Colour/level mapping:** none of its own; feeds `one_decision` (§9).
- **Freshness/refusal rule:** `REFUSED/UNRESOLVED` when `|Δk| ≤ epsilon` (can't tell if it
  is really moving); `REFUSED/NOT_APPLICABLE` when falling, already past `θ`, or `Δk` was
  `NO_READOUT`. REFUSED is a non-value, never printed as `0`, infinity, or blank.
- **Resolution label:** single-station.
- **Worked example:** `h_t=0.38`, `θ=0.45`, `k=1`, `Δk=0.08` → `Tk≈0.875` ticks
  (~53 minutes at k=1 h) — reported as an interval across at least two lags, never one
  bare point number.
- **Does NOT mean:** a guaranteed arrival time — it is a linear extension of the last
  observed rate only.

## 5. `rain_24h_mm`

- **One line:** rain reported in the last 24 hours near this area, from the official DDS
  bulletin.
- **ความหมายสั้น:** ฝนที่ตกในช่วง 24 ชม.ที่ผ่านมาใกล้พื้นที่นี้ ตามประกาศ DDS
- **Exact definition:** the `rain_24h_mm` variable rows from the DDS bulletin
  (`readout.py`'s `dds_obs` filter), no new arithmetic.
- **Unit:** mm.
- **Levels:** a numeric value only — this indicator has no colour/level vocabulary of
  its own and is never re-expressed as RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** not in `kb.py`'s `answer` JSON — a separate entrypoint,
  `readout.build_readout(...)["factors"]["1"]["measured"][*]["value"]`.
- **Input source:** BMA DDS bulletin (`readout.py` factor 1).
- **Thresholds:** none applied here — this is a relayed reading, it does not by itself
  drive §1's colour.
- **Freshness rule:** the bulletin's own publication cadence; stale rows are shown, not
  used.
- **Resolution label:** area/bulletin-level, not per-station.
- **Worked example:** see `docs/EQUATIONS_FOR_AI.md` §2 for a live-captured row.
- **Does NOT mean:** a flood-risk class — any TMD/DDS rain-class label attached to it is
  `RELAYED`, never used to change a colour on its own.

## 6. `rain_7day_per_model_mm`

- **One line:** 7-day rain forecast at this coordinate, shown separately per weather
  model — never averaged into one number.
- **ความหมายสั้น:** พยากรณ์ฝน 7 วันข้างหน้าที่พิกัดนี้ แยกตามแต่ละโมเดลพยากรณ์ ไม่เฉลี่ยรวมเป็นตัวเดียว
- **Exact definition:** `per_model` list from `kb.py::cmd_forecast` / `_answer_hazard`,
  one row per public weather model (today 10 models: Open-Meteo/ECMWF/GFS/JMA/CMA/GEM/MET
  Norway and siblings).
- **Unit:** mm per model, per day/total.
- **Levels:** a numeric value per model only — no colour/level vocabulary of its own,
  never re-expressed as RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** `hazard.per_model[*]["7day_total_mm"]` (each row also carries
  `tomorrow_mm` and the model's own name).
- **Input source:** each model's own public forecast API, fetched at the queried
  coordinate.
- **Thresholds:** none — a relayed forecast, not a flood-depth prediction.
- **Freshness rule:** per-model fetch cadence; min/median/max summary shown with a note
  on how many models carried a value.
- **Resolution label:** per-coordinate.
- **Does NOT mean:** a forecast of flood depth, water level, or inundation at any point —
  rain only, and never one blended number across models.

## 7. `distance_to_bank_m`

- **One line:** how far (in metres) the current reading is below the station's bank
  level, where the agency publishes both numbers.
- **ความหมายสั้น:** ระดับน้ำปัจจุบันต่ำกว่าตลิ่งเท่าไร (เมตร) เฉพาะสถานีที่หน่วยงานเผยแพร่ทั้งสองค่า
- **Exact definition:** the agency's own `diff_wl_bank` (bank minus current reading, sign
  from the agency's own `diff_wl_bank_text` — "ล้นตลิ่ง"/overflow vs "ต่ำกว่าตลิ่ง"/below
  bank) — no new equation, a direct relay of the agency's own field.
- **Unit:** m.
- **Levels:** a numeric value where wired, otherwise `OPEN` — no colour/level vocabulary
  of its own, never re-expressed as RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** `state.evidence[*]` rows do not carry this field directly yet (they
  carry `value`/`status`/`dist_km`/`resolution`) — a caller wanting the metre figure
  reads `collect.collect_thaiwater_waterlevel`'s stored `provenance.diff_wl_bank` for
  that row, or computes it itself from `observations.bank` minus `value`.
- **Input source:** the nationwide `thaiwater_waterlevel` feed's **top-level**
  `diff_wl_bank`/`diff_wl_bank_text` fields (NOT under `station` — fix, 2026-10-04,
  regate finding #5, exact path MEASURED against the live feed 2026-10-04) and
  `station.min_bank`.
- **Status in this release (v0.1.2): the agency word this field's SIGN comes from
  (`diff_wl_bank_text` starting "ล้นตลิ่ง") now drives `current_local_state` directly
  (§1, `OVERBANK` → RED) for every point in Thailand via `thaiwater_waterlevel` — see
  §11. The METRE VALUE itself (`distance_to_bank_m` as a standalone number) is still
  relayed only in `provenance`, not surfaced as its own top-level answer field.**
- **Resolution label:** station or basin, per §11 — never promoted past what the
  deciding row's own `resolution` says.
- **Does NOT mean:** a number this project computed — it is the agency's own
  `diff_wl_bank`, relayed.

## 8. `bank_fill_percent`

- **One line:** what percent of the gap between the riverbed/canal floor and the bank the
  current reading has filled.
- **ความหมายสั้น:** ระดับน้ำปัจจุบันเติมเต็มช่องว่างระหว่างพื้นคลอง/แม่น้ำกับตลิ่งไปกี่เปอร์เซ็นต์
- **Exact definition / formula:** the agency's own `storage_percent` field — relayed as
  the agency publishes it, `(wl − ground_level) / (min_bank − ground_level) · 100` is
  the agency's own stated definition of that field (relayed here for the reader's
  benefit, **not a Toledo-registered equation** — it is cited, not derived, and is not
  in `registry/CANONICAL.json` or `registry/proposals/*.json`; treat the written-out
  formula as `RELAYED`, the same tag as the field itself).
  (Fix, 2026-10-04, review finding #6: an earlier draft of this section claimed "verified
  against the feed's own numbers, 0 mismatches ... see the v0.1.2 design review" — no
  such review is committed anywhere in this repository, so that sentence is removed
  rather than left as an unverifiable claim.)
- **Unit:** %.
- **Levels:** a numeric value where wired, otherwise `OPEN` — no colour/level vocabulary
  of its own, never re-expressed as RED/YELLOW/GREEN/UNKNOWN.
- **JSON path:** not a standalone top-level answer field in v0.1.2 — relayed in
  `collect.collect_thaiwater_waterlevel`'s stored `provenance.storage_percent` for the
  row (same `provenance` a caller already reads for §7).
- **Input source:** the nationwide `thaiwater_waterlevel` feed's **top-level**
  `storage_percent` field (fix, 2026-10-04, regate finding #5: not nested under
  `station`), plus `station.min_bank`/`station.ground_level`.
- **Status in this release:** relayed in `provenance`, not yet its own top-level
  answer field — the agency's own `situation_level` code (which this same feed
  publishes, and which correlates with `storage_percent`'s bins, MEASURED 2026-10-04 on
  one live capture) is what drives §1's colour today, not a `bank_fill_percent`
  numeric cutoff of this project's own choosing (Toledo-first: no invented threshold).
- **Does NOT mean:** a numeric cutoff this project chose — any percent-based colour
  rule would be an invented threshold; §1 never uses one.

## 9. `one_decision` + `confidence`

- **One line:** one plain decision in words, with a confidence label, instead of making
  the reader combine several numbers themselves.
- **ความหมายสั้น:** คำตัดสินใจเดียวเป็นคำพูดธรรมดา พร้อมระดับความมั่นใจ ไม่ต้องให้ผู้อ่านรวมตัวเลขเอง
- **Two separate confidence fields exist — do not conflate them:**
  1. `next_action.dual_state.confidence` — `kb.py`'s own production CLI/MCP/JSON
     answer (shipped v0.1.2). Rule below.
  2. `floodconnect_model.one_decision(inputs).confidence` — the by-hand companion
     module's own six-step procedure (`docs/EQUATIONS_FOR_AI.md` §5), a separate
     `HIGH`/`MEDIUM`/`LOW`/`NONE` vocabulary for a tool-less AI working from §3/§4's
     trend. Described below the production field.

### `next_action.dual_state.confidence` (production, `kb.py`)

- **Exact definition:** a resolution-based confidence label for whatever colour
  `current_local_state` (§1) decided, computed in `kb._answer_state` from the
  UNCAPPED deciding-evidence list (never the token-budget-capped sample), then
  carried into `next_action.dual_state` by `kb._answer_next_action`.
- **Levels:** `HIGH` / `LOW` / `NONE` — never `MEDIUM` (that value belongs only to
  the by-hand module's separate field below).
- **JSON path:** `next_action.dual_state.confidence` in `kb.py`'s `answer` output
  (CLI `--json` / MCP `floodconnect_answer`) — **present only as `HIGH`/`LOW`; `NONE`
  is never written as a literal key, the same convention `dual_state.resolution`/
  `dist_km` already use (never a `null` placeholder on every answer). A caller must
  treat a MISSING `confidence` key as `NONE` — exactly the same way it already must
  for a missing `resolution`.**
- **Rule:**
  - `HIGH` — at least one deciding row is a fresh agency status word read at
    **station resolution** (a nationwide `thaiwater_waterlevel` row within
    `NATIONWIDE_RIVER_RADIUS_KM` = 10 km, §11) or a **local** reading (the two MVP
    areas' own already-radius-filtered Bangkok canal/pump/DDS source, which carries
    no `resolution` field at all — as close as a reading gets).
  - `LOW` — every deciding row is nationwide **basin resolution** only (§11: same
    `sub_basin_id`, 10–50 km, a different water body) — no station-resolution or
    local reading decided.
  - `NONE` (key absent) — `current_local_state == UNKNOWN` (forced, regardless of
    what the evidence says) — covers both "nothing decided" and the fault-only-
    sensor exclusion case (§1), where a deciding row can technically exist yet the
    state still classifies `UNKNOWN`.

### `floodconnect_model.one_decision(inputs).confidence` (by-hand companion module)

- **Exact definition:** `floodconnect_model.one_decision(inputs)` — the six-step
  by-hand procedure in `docs/EQUATIONS_FOR_AI.md` §5: an official status word (§1)
  always outranks the trend computed from §3/§4; without one, `RISING` alone is at
  least `YELLOW`, never `GREEN`.
- **Unit:** none (categorical `level` + free text `decision`/`why`).
- **Levels:** `level` — `RED` / `YELLOW` / `GREEN` / `UNKNOWN` (the colour contract
  above, the only other field it applies to besides §1). `confidence` — `HIGH` /
  `MEDIUM` / `LOW` / `NONE` (its own closed vocabulary, never the colour contract,
  and never the same field as `dual_state.confidence` above).
  `gate` — `LICENSED_WITHIN_ENVELOPE` / `REFUSED`.
- **JSON path:** not in `kb.py`'s `answer` JSON — by-hand companion module only:
  `floodconnect_model.one_decision(inputs)` returns
  `{"decision", "confidence", "level", "checks", "gate", "why"}`.
- **Input source:** §1 (`official_status`), §3/§4 (`h_t`, `h_t_minus_k`, `epsilon`, `θ`).
- **Confidence rule (this project's own judgment call, `INSTINCT`, not an agency
  figure):**
  - `HIGH` — a fresh official status word backed the call.
  - `MEDIUM` — no official status word; the call came from the trend (`Δk`/`Tk`) alone.
  - `LOW` — basin-level-only resolution (§11): no fresh station within 10 km, only a
    same-sub_basin reading within 50 km decided.
  - `NONE` — no current reading at all (`h_t` missing) or a stale reading.
- **Status in this release:** implemented and tested in the by-hand companion module
  (`floodconnect_model.py`), pinned against `kb.py`'s own classifier for the status-word
  case — see `docs/EQUATIONS_FOR_AI.md` for how to run this by hand.
- **Does NOT mean:** a safety certification — `gate=LICENSED_WITHIN_ENVELOPE` means "a
  real, fresh reading backed this", never "safe"; `gate=REFUSED` is the honest default
  whenever there is nothing fresh to decide from.

## 10. `water_debt`

- **Status: `planned (v0.2+)`.** No value, no field, no equation is computed for this in
  v0.1.x. The underlying proposals (`PROP-FLOOD-03/06/07`) are **OPEN Toledo pull
  requests, not merged** — see `model_spec.json`. Any mention of "water debt"/"Jev"/
  "One-Decision Network" elsewhere in this repository's docs describes this same planned
  direction, never a feature callable today.
- **สถานะ:** วางแผนไว้สำหรับ v0.2+ ยังไม่มีค่า ไม่มีสมการที่คำนวณได้ในเวอร์ชันนี้

## 11. Resolution label — read this before trusting any field above

**v0.1.2 (founder ruling 2026-10-04, "ทำเลย v0.1.2 ทั้งประเทศ"): a nationwide COARSE
path is now shipped.** `current_local_state`/`forward_hazard`/accountability work for
ANY `lat,lon` in Thailand, not only the two named Bangkok household areas — but the
resolution is **station or basin (coarse zoom: nearest telemetry station/basin), never
household-level**. Nationwide ≠ household detail; do not claim street-level precision
outside the two MVP areas.

- **Station resolution** (every indicator above, at its best): EVERY fresh
  `thaiwater_waterlevel` station within **10 km** (any water body — this is not
  checked against `river_name`, despite some older wording in this repo's docs)
  decides, worst colour wins (e.g. Chanthaburi: 3 stations within 10 km decided at
  once). Declared radius, this project's own design choice
  (`readout.NATIONWIDE_RIVER_RADIUS_KM`) — never an agency threshold, and never just
  "the nearest one" despite some older wording in this repo's docs.
- **Basin resolution** (coarser, lower confidence): no fresh station within 10 km, but
  a fresh station sharing the NEAREST station's own `sub_basin_id` (a stand-in for
  "same basin" — the two stations are not checked against a shared named river)
  within **50 km** (`readout.NATIONWIDE_BASIN_RADIUS_KM`, also this project's own
  design choice) exists. A basin-resolution row **can never decide GREEN** on its own
  (far + "normal" is not a clearance) — it is shown, with `resolution: "basin"`, but
  excluded from the decision when its own classified level is GREEN; it still raises
  YELLOW/RED normally.
- **No resolution at all:** no fresh station within 50 km sharing that sub-basin —
  `current_local_state` stays `UNKNOWN`, same as always (UNKNOWN is never SAFE).
- Every `state.evidence` row a nationwide query returns carries `dist_km` and
  `resolution` (`"station"` or `"basin"`) alongside the station name/status/agency —
  never a bare number with no named source. `kb.py answer`'s own printed CLI line for
  the deciding row also shows `dist_km`/`resolution` now, not just the station name.
- The two Bangkok household areas (Sammakorn village, Soi Ramkhamhaeng 53) keep their
  existing node-level detail (fixed station lists, canal/pump sources) as the
  decision for those two areas whenever a local (Bangkok canal/pump) reading is fresh
  AND carries a colour-bearing status word — but only a **basin-resolution**
  nationwide row is stopped from deciding in that case; a nationwide
  **station-resolution** row (<=10 km) decides together with the local rows, worst
  colour wins (fix, 2026-10-04: an earlier version of this suppression wrongly
  excluded a station-resolution row sitting at 0.0 km on a fresh agency OVERBANK
  status, whenever ANY local row was fresh). A basin-resolution row suppressed this
  way is still shown as reference evidence, with its own CLI reason text
  ("ระดับลุ่มน้ำ ไม่ใช้เมื่อมีข้อมูลคลองในพื้นที่" — basin-level, not used when local canal
  data exists) distinct from a genuinely-stale or geo-excluded row's reason.
- `distance_to_bank_m`/`bank_fill_percent` (§7/§8) stay relayed-in-`provenance`-only,
  not wired into a numeric threshold of their own (Toledo-first: no invented cutoff);
  the agency's own `situation_level`/`diff_wl_bank_text` words are what §1 actually
  reads. Accountability for a nationwide point is TEXT only (the deciding station's own
  feed-published province + owning agency) — never a graph lookup; that is a separate,
  not-yet-built piece of work (`tools/kg/*`, a different repo scope).

**ภาษาไทยอย่างง่าย:** v0.1.2 ตอบได้ทั่วประเทศแล้ว (ความละเอียดระดับสถานี/ลุ่มน้ำ ไม่ใช่
ระดับบ้าน) โดยหาสถานีที่สดที่สุดในรัศมี 10 กม. ก่อน ถ้าไม่มีจึงหาสถานีลุ่มน้ำเดียวกันในรัศมี 50
กม. (ซึ่งจะไม่ให้ค่าเขียวเองได้) ถ้าไม่มีทั้งสองอย่างคือ "ไม่ทราบ" เหมือนเดิม — สองพื้นที่ในกรุงเทพฯ
(สัมมากร, ซอยรามคำแหง 53) ยังคงรายละเอียดระดับบ้านเดิม ไม่เปลี่ยนแปลง
