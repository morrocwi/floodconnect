# FloodConnect v0.1.5 — release notes

Claims below state only what was built in this repository and verified by its
own tests. The skill's continuity / mandatory-ETA-range / user-side-storage
behaviour (§4-§6 of `skill/SKILL.md`) is an **instruction set for the user's own
AI to follow**, not a capability this repository's code executes on its own —
FloodConnect ships no scheduler, no hosted store, and does not run the skill
itself. The included email report is one worked **example** of the skill's
output format, not a feature this repository sends.

## English

**MVP close.** This release folds the M8 Jev Sandwich decision model, the M7a
government-API fetch manual (reconciled field-by-field against M8's shipped
schemas — the two retired schema files it once pointed at, `ring_readout`/
`sandwich_readout`, are replaced by `layer_readout.schema.json`/
`sandwich_trace.schema.json`), the M5 water-debt backtest experiment, the L0
daily check and cross-session watchlist, and the full MCP tool set, into one
tree, and adds the vendor-neutral skill package any AI can install
(`skill/SKILL.md`). This closes the MVP milestone sequence (M1-M3 scope,
M5/M7a/M8 reconciliation) per the founder's 2026-10-06 instruction to ship a
closed release.

- **Jev Sandwich Zoom decision model (M8):** reads the point (Z0) and the
  basin/overview (Z3) first; extracts the middle rings (Z1/Z2) only on
  conflict or missing data. Closed 5-colour vocabulary
  (GREEN/YELLOW/ORANGE/RED/UNKNOWN), RED reserved for the point's own Z0
  reading, an outlet-critical rule (floors the colour at YELLOW), zero/null
  thresholds treated as UNKNOWN, heuristic joins (bare code-prefix family,
  unscoped same-subbasin membership) barred from ever setting a colour. A
  GREEN overall colour is raised to YELLOW whenever any ring shows a fresh RED.
- **Home-as-shelter verdict (P-D):** `advice/home_shelter.py`'s
  `decide_home_shelter` — missing household input returns `UNKNOWN_ASK_INPUTS`,
  never a silent `STAY_PREPARED`; colour `UNKNOWN` can no longer produce
  `STAY_PREPARED` even with every household input known.
- **Emergency card:** hard 80 cl100k-token budget, enforced by a fail-closed
  assert (`advice/card.py`).
- **Government API fetch manual (M7a, reconciled):** `docs/API_MANUAL.md`,
  `sources/sandwich_fetch_order.yaml`, `sources/live_call_index.yaml` — the
  keyless Sandwich fetch order (BMA `PageMap/GoogleMap` POST, BMA
  `StationDetail?id=` series with its Bangkok-local-time/month-off-by-one
  correction, thaiwater `public/waterlevel`). Two prior schema files
  (`ring_readout.schema.json`, `sandwich_readout.schema.json`) are retired in
  favour of M8's own `layer_readout.schema.json`/`sandwich_trace.schema.json`,
  which this release confirms are the actual runtime shape — the reconciliation
  itself (which fields moved where, which were dropped) is recorded inline in
  `docs/API_MANUAL.md` section 12, not in a separate file.
- **Water-debt backtest experiment (M5):** `tools/backtest/run_m5_water_debt.py`
  over 6 real flood events + 8 control periods. Reported finding: every one of
  219 unit-day rows refuses with `MISSING_INPUT` (S0 initial storage and
  `gate_flag` are universal blockers); the claim is additionally refused
  `FEW_EVENTS` (n_independent=6 < N_min=10). This is an experiment result, not
  a shipped capability — no change to `kb.py`, `floodconnect_model.py`, or
  `collect.py`, and no forecast-skill claim follows from it (see "Validation
  basis" below).
- **L0 daily check + cross-session watchlist:** `l0_check.py` (the cheapest-
  first check — exactly 3 keyless sources: TMD CAP, rain, Z0 level+trend —
  one QUIET/ESCALATE line) and `watchlist.py` (the same check plus a
  persistent ACTIVE/COOLING/CLOSED watchlist state machine, this
  installation's own local store). Exposed via the CLI (`kb.py check`) and as
  the MCP tools `floodconnect_check`/`floodconnect_watch`.
- **MCP tools (11, `tools/mcp/floodconnect_mcp.py`):**
  `floodconnect_answer`, `floodconnect_locate`, `floodconnect_check`,
  `floodconnect_watch`, `floodconnect_list_areas`, `floodconnect_get_area_state`,
  `floodconnect_get_station`, `floodconnect_get_typology_subgraph`,
  `floodconnect_find_safe_route`, `floodconnect_list_upstream_sources`,
  `floodconnect_explain_rules`.
- **Skill package (M9):** `skill/SKILL.md` + `skill/examples/` +
  `skill/INSTALL_CHECK.md` — a self-contained, vendor-neutral method any AI can
  load (skill folder, pasted custom instructions, or an agent with shell/MCP
  access to this repo's own CLI/MCP tools) to answer flood/canal status
  questions for a covered community, including the mandatory RISING time-to-
  threshold range (labelled PROPOSAL, PROP-FLOOD-02 — linear, two windows;
  this is an already-registered, already-merged Toledo proposal, NOT
  PROP-FLOOD-11, which is a separate, also-registered proposal that is NOT
  IMPLEMENTED in this release, v0.2 target), continuity against the
  user's own saved history, and an opt-in, user-side-only save-your-own-record
  invitation. No hosted compute, no scheduler, no embedded credentials.
- **Fast layer (§0b, founder simplification 2026-10-06):** one step before any
  Sandwich zoom — a 3-rule, no-scoring drill table applies the Sandwich
  technique to the REPORTS themselves (TOP = TMD + RID wide reports, BOTTOM =
  the point's province report, Bangkok's BMA DDS prnews VERIFIED, other
  provinces OPEN/find-and-add) and outputs exactly one line,
  `ต้องขยับไหม: ไม่/ใช่ — <reason> (<source> @<issue time>)`. Both calm →
  answer now; both name the area at warning-or-worse → drill with the card
  shown first; conflict or a missing/stale report → zoom via the existing
  Sandwich (§2-§3). This replaces asking the user whether to drill; no
  side-by-side cross-check of the two reports (explicitly rejected, token
  cost). KlongMap's pump-count field (`weather.bangkok.go.th/Klongmap/
  GetDataForUpdate`) is now VERIFIED to exist keyless but returns null pump
  data in this probe — the pump-link rule stays OPEN, unchanged.
- **Precedence corrected — the safest action wins (§3):** an official order is
  a FLOOR, never a ceiling. An evacuate/warning always raises the verdict; a
  missing, late, or weaker order never lowers a RED/LEAVE verdict already
  reached from the reading or ground truth. With no order yet and a RED/LEAVE
  reading, the answer says to move to safety now plus "ยังไม่มีคำสั่งทางการ —
  อย่ารอ", never only "ทำตามประกาศทางการ". The earlier "official > ground >
  reading" wording is removed from every section that carried it.
- **KG-only answer path (§2-§3):** every relation between the point and any
  other station must now be a declared KG graph edge with a declared source;
  heuristic joins (bare code-prefix family, unscoped same-sub-basin
  membership, OSM edges with unknown direction, any radius/distance pick) are
  removed from the fetch and the evidence list entirely, not only from the
  colour. A missing edge gives UNKNOWN for that ring plus a logged
  `policy_gap`, never a guess. Simulated/modelled load (the water-debt model,
  a forecast load ladder, any synthetic series) sits behind one config flag,
  off by default; what remains is measured readings, KG edges, and the
  time-to-bank arithmetic on measured slopes, labelled arithmetic, not
  simulation.
- **ETA honesty (relabelled, 2026-10-07):** the shipped RISING ETA is a LINEAR
  two-window slope extrapolation — PROP-FLOOD-02 (merge `65297f0` is a
  different, separately-registered proposal; PROP-FLOOD-02 itself was
  registered and merged earlier, PR #59), labelled `PROPOSAL` on every RISING
  answer. `PROP-FLOOD-11` (the acceleration-aware quadratic, 2nd retained
  difference, with a least-n search; Toledo PR #65, merged 2026-10-06 at
  `65297f05`, tier `Dr`, status `unverified`) is a SEPARATE, also-registered
  proposal that is registered but **NOT IMPLEMENTED** in this release (v0.2
  is the target for wiring it in) — it was mislabelled as the shipped
  mechanism in earlier drafts of this release; that is corrected here. The
  refusals the shipped code actually applies, in order: `AT_BANK` →
  `NO_READOUT` → `PUMP_STATE_CHANGED` → `PUMP_STATE_UNDECLARED` → `NO_RISE` →
  `NOT_WITHIN_HORIZON`. The founder-mandated behaviour is unchanged: the ETA
  is always computed whenever Z0 is RISING, never silently skipped.
- **PROVENANCE block added** at the top of the skill — what the method is,
  its version, the canonical repo, the source of truth per kind of claim, and
  the VERIFIED/MEASURED/RELAYED/PROPOSAL/OPEN/STALE tag legend. A FAST PATH
  summary and an explicit scope note (Bangkok/หมู่บ้านสัมมากร validated,
  elsewhere experimental) sit right under it.
- **Calculation + confidence shown for every computed output** (colour basis,
  headroom, trend, ETA, home-shelter verdict): formula/eq code, each input
  with its own source and time, the result, and — when an input is missing —
  the input is named (never guessed) with an ordinal confidence
  (HIGH/MEDIUM/LOW/NONE) and its reason. A missing household vulnerable-group
  count explicitly lowers the home-shelter confidence/score with its own
  stated reason.
- **On-trigger write:** a fired trigger now writes an `alert_event` into the
  user's own connected calendar/sheet/DB/notes through the user's own
  storage connection, deduplicated by event id, after a one-time offer; with
  no connected tool it is shown in the answer only.
- **TLS note added** for `.go.th` hosts that serve an incomplete certificate
  chain — use a client that completes the chain itself, or the shipped
  `assets/tmd_intermediate_ca.pem`. Bypassing certificate verification is
  **forbidden**, not merely discouraged — there is no "genuinely had to be
  bypassed" exception.
- **`INSTALL_CHECK.md` gained Q11-Q12** covering the floor-precedence rule and
  the PROVENANCE block's KG-only/source-of-truth guarantees.

**Validation basis, stated honestly:** the MVP scope tag (`VALIDATED_MVP` for
Bangkok and หมู่บ้านสัมมากร, `EXPERIMENTAL` elsewhere) rests on **live
invariant sweeps** over the real committed station set (the M8 safety
revision's full sweep of 311 `bma_watermap` + 807 `thaiwater_waterlevel`
stations, 13 invariant counts all 0; the M8 subtractive-fix revision's
1,164-coordinate sweep, all three sources, 10 household variants each) —
**not** on the M5 water-debt backtest, which **REFUSED all 219 of its rows**
(`MISSING_INPUT`, additionally `FEW_EVENTS`). No forecast-skill claim follows
from M5; it is reported as an experiment result, not a capability.

- `PROP-FLOOD-11` (acceleration/time-to-threshold) is a registered Toledo
  proposal (PR #65, merged `65297f05`, tier `Dr`, status `unverified`) that
  is registered but **NOT IMPLEMENTED** in this release (v0.2 target). The
  shipped RISING ETA is PROP-FLOOD-02 (linear, two windows) instead — see
  the "ETA honesty" bullet above. `floodconnect_model._rise_eta_prop11_computation`
  (the real PROP-FLOOD-11 quadratic) exists and is tested but is never
  reached from any answer path.
- The M5 backtest's own headline finding is that it cannot currently produce a
  usable water-debt number for any of its 219 rows — this is reported as a
  result, not fixed by this release, and no forecast-skill claim is made from
  it (see "Validation basis" above).
- `docs/handoff/NEXT_AI_HANDOFF.md` carries M5's addition appended, not
  replacing any existing section.

**Known gaps carried over from `CHANGELOG.md`'s "Known issues (v0.1.5)"
(never silently dropped):**
- **BKK007 (Bang Yai, Nonthaburi)** still resolves `VALIDATED_MVP` — a
  KG-data-coverage gap (too few Nonthaburi `IN_PROVINCE`-declared member
  points near it for the nearest-member-distance ranking to prefer
  Nonthaburi over Bangkok), not a code bug; covered by an `xfail` test
  (`tests/test_kb_answer_sandwich.py::test_bkk007_in_nonthaburi_is_
  experimental_not_validated`).
- **LEAVE_NOW over-escalation:** a GREEN colour combined with a single-storey
  house or a stale declaration can still produce `LEAVE_NOW` — tracked as a
  FloodConnect default pending the founder (`_assemble`'s rules 4-9 note),
  not changed in this release.
- **The move-now line can appear on a GREEN card:** `PREPARE_TO_LEAVE`'s own
  move-now/no-official-order line also shows on a GREEN card when the
  household's own need profile triggers it, which can read as more urgent
  than the card's colour suggests — not yet reconciled.

## ภาษาไทย

**ปิด MVP.** รุ่นนี้รวม Jev Sandwich decision model (M8), คู่มือเรียก API หน่วยงานรัฐ
(M7a, ปรับให้ตรงกับ schema จริงของ M8 — schema เก่าสองตัว ring_readout/sandwich_readout
เลิกใช้แล้ว ใช้ layer_readout/sandwich_trace แทน) การทดลอง backtest หนี้น้ำ (M5),
ระบบเช็กรายวัน L0 + watchlist, และ MCP tools ทั้งหมด เข้าเป็นต้นไม้เดียว พร้อม
แพ็กเกจสกิลที่ไม่ผูกกับผู้ให้บริการ AI ตัวใด ติดตั้งได้ (`skill/SKILL.md`) —
ตามคำสั่งผู้ก่อตั้ง 2026-10-06 ให้ออก release และปิด MVP

- **Jev Sandwich Zoom decision model (M8):** อ่านจุด (Z0) และภาพรวมลุ่มน้ำ (Z3)
  ก่อนเสมอ ดึงชั้นกลาง (Z1/Z2) เฉพาะเมื่อขัดแย้งหรือข้อมูลขาด ใช้สีปิด 5 ค่า
  (เขียว/เหลือง/ส้ม/แดง/ไม่ทราบ) สีแดงสงวนไว้สำหรับจุดของเราเองเท่านั้น มีกฎทางออก
  (คลองวิกฤตที่ปลายทางยกสีขึ้นเป็นเหลืองอย่างน้อย) ค่าขีดจำกัดที่เป็น 0/null ถือว่า
  ไม่ทราบ ไม่ใช่สีเขียวหรือแดงโดยอัตโนมัติ
- **คำตัดสินบ้านเป็นที่หลบภัย (P-D):** ข้อมูลครัวเรือนขาด → `UNKNOWN_ASK_INPUTS`
  เสมอ ไม่ใช่ "อยู่ต่อ" แบบเงียบๆ
- **คู่มือเรียก API หน่วยงานรัฐ (M7a, ปรับแล้ว):** ลำดับการดึงข้อมูลแบบแซนวิชที่ไม่ต้อง
  คีย์ API (BMA PageMap/GoogleMap, BMA StationDetail พร้อมแก้เวลาท้องถิ่นกรุงเทพฯ/เดือน
  เลื่อนหนึ่ง, thaiwater public/waterlevel) schema เก่าสองตัวถูกเลิกใช้แล้วให้ใช้ของ
  M8 จริงแทน
- **การทดลอง backtest หนี้น้ำ (M5):** ผลที่รายงาน — ทั้ง 219 แถวถูกปฏิเสธเพราะข้อมูล
  ขาด (`MISSING_INPUT`) นี่คือผลการทดลอง ไม่ใช่ความสามารถที่ใช้งานได้จริงในระบบคำตอบ
  และไม่ได้ใช้เป็นข้ออ้างความสามารถพยากรณ์ใดๆ (ดู "พื้นฐานการตรวจสอบ" ด้านล่าง)
- **เช็กรายวัน L0 + watchlist ข้ามเซสชัน:** `l0_check.py` (เช็กราคาถูกที่สุด — 3
  แหล่งไม่ต้องคีย์เท่านั้น: TMD CAP, ฝน, ระดับ+แนวโน้ม Z0 — ออกบรรทัดเดียว
  QUIET/ESCALATE) และ `watchlist.py` (เช็กแบบเดียวกันบวก state machine
  ACTIVE/COOLING/CLOSED ที่เก็บถาวรในเครื่องผู้ใช้) เรียกผ่าน CLI (`kb.py check`)
  และ MCP tool `floodconnect_check`/`floodconnect_watch`
- **MCP tools (11 ตัว):** `floodconnect_answer`, `floodconnect_locate`,
  `floodconnect_check`, `floodconnect_watch`, `floodconnect_list_areas`,
  `floodconnect_get_area_state`, `floodconnect_get_station`,
  `floodconnect_get_typology_subgraph`, `floodconnect_find_safe_route`,
  `floodconnect_list_upstream_sources`, `floodconnect_explain_rules`
- **แพ็กเกจสกิล (M9):** `skill/SKILL.md` — AI ตัวใดก็ติดตั้งได้ ไม่มีชื่อผู้ให้บริการ
  AI ระบุไว้ รวมกฎการคำนวณช่วงเวลาถึงขีดจำกัดเมื่อน้ำกำลังขึ้น (PROP-FLOOD-02 แบบ
  เส้นตรงสองช่วงเวลา ขึ้นทะเบียนและ merge แล้ว — ไม่ใช่ PROP-FLOOD-11 ซึ่งขึ้นทะเบียน
  แล้วแต่ยังไม่ได้ implement ในรุ่นนี้ เป้าหมาย v0.2 — ต้องติดป้าย PROPOSAL เสมอ)
  ความต่อเนื่องกับประวัติที่ผู้ใช้บันทึกเอง และคำเชิญให้บันทึกเองแบบสมัครใจ —
  ไม่มีการประมวลผลบน host ของ FloodConnect ไม่มีการตั้งเวลาอัตโนมัติ ไม่มี credential
  ฝังไว้ในสกิล
- **ชั้นเร็ว (§0b, คำสั่งลดขั้นตอนของผู้ก่อตั้ง 2026-10-06):** ก่อนซูมแซนวิชทุกครั้ง
  ใช้กฎ 3 ข้อ (ไม่มีคะแนน ไม่มีค่าต้องปรับ) แซนวิชกับ "รายงาน" เอง — บนสุดคือรายงาน
  กว้าง (ทีเอ็มดี+กรมชลประทาน) ล่างสุดคือรายงานจังหวัดของจุดนั้น (กรุงเทพฯ ใช้ BMA
  DDS prnews ยืนยันแล้ว จังหวัดอื่นยังเปิดอยู่ ต้องหาเพิ่ม) ออกมาเป็นหนึ่งบรรทัด
  "ต้องขยับไหม: ไม่/ใช่" พร้อมเหตุผลและเวลาออกรายงาน ถ้าเงียบทั้งคู่ตอบได้ทันที
  ถ้าทั้งคู่ระบุพื้นที่ที่เฝ้าระวังหรือแย่กว่า ให้ซูมแต่โชว์การ์ดก่อน ถ้าขัดแย้งหรือ
  รายงานขาด ให้ซูมด้วยแซนวิชเดิม ไม่มีการถามผู้ใช้ และไม่มีการเทียบรายงานสองฉบับแบบ
  cross-check (ถูกปฏิเสธแล้ว เรื่อง token)
- **แก้ลำดับความสำคัญ — ระดับที่ปลอดภัยที่สุดชนะ (§3):** คำสั่งทางการเป็น "พื้น" ไม่ใช่
  "เพดาน" คำสั่งอพยพ/เตือนยกระดับได้เสมอ แต่คำสั่งที่ขาด มาช้า หรือเบากว่า จะไม่ลด
  ระดับที่ประเมินจากข้อมูลจริงหรือสภาพหน้างานลงเด็ดขาด ถ้ายังไม่มีคำสั่งและจุดอยู่ที่
  แดง/ต้องออก ให้บอกให้ย้ายไปที่ปลอดภัยทันที พร้อมข้อความ "ยังไม่มีคำสั่งทางการ —
  อย่ารอ" ห้ามตอบแค่ "ทำตามประกาศทางการ"
- **ตอบในกราฟความรู้ (KG) เท่านั้น (§2-§3):** ความสัมพันธ์ระหว่างจุดกับสถานีอื่นต้องมา
  จาก edge ของ KG ที่ประกาศแหล่งที่มาเท่านั้น การจับคู่แบบเดา (รหัสตระกูลเดียวกัน ชื่อ
  คล้ายกัน ระยะทาง หรือลุ่มน้ำย่อยเดียวกันแบบไม่ระบุทิศทาง) ถูกตัดออกทั้งหมด ไม่ใช่แค่
  จากสีอีกต่อไป ขาด edge = ไม่ทราบ (UNKNOWN) พร้อมบันทึก policy_gap การจำลอง/โหลด
  สมมุติ (เช่น water-debt) ปิดเป็นค่าเริ่มต้นด้วยหนึ่งแฟล็ก เหลือไว้แค่ค่าที่วัดจริง
  ขอบ KG และการคำนวณเวลาถึงตลิ่งจากความชันที่วัดจริง (ไม่ใช่การจำลอง)
- **แก้ป้ายชื่อ ETA ให้ตรงความจริง (2026-10-07):** ETA ที่ส่งจริงเป็นการต่อเส้นตรง
  (linear) จากสองช่วงเวลา — PROP-FLOOD-02 (merge แล้วก่อนหน้านี้ PR #59) ติดป้าย
  PROPOSAL ทุกคำตอบที่น้ำกำลังขึ้น ส่วน PROP-FLOOD-11 (อัตราเร่ง 2nd retained
  difference, Toledo PR #65, merge `65297f05` วันที่ 2026-10-06, tier `Dr`, status
  `unverified`) เป็น proposal แยกที่ขึ้นทะเบียนแล้วแต่ **ยังไม่ได้ implement** ใน
  รุ่นนี้ (เป้าหมาย v0.2) — ร่างก่อนหน้านี้เรียกผิดว่าเป็นตัวที่ใช้จริง แก้ไขแล้วที่นี่
- **เพิ่ม PROVENANCE block** ที่หัวไฟล์สกิล และ **แสดงผลการคำนวณ + ระดับความมั่นใจ**
  ทุกค่าที่คำนวณ (สี, ETA, คำตัดสินบ้านเป็นที่หลบภัย) พร้อม **on-trigger write**
  เขียนเตือนเข้าระบบผู้ใช้เองเมื่อทริกเกอร์ทำงาน

**พื้นฐานการตรวจสอบ (บอกตรงๆ):** ป้าย scope `VALIDATED_MVP` (กรุงเทพฯ/หมู่บ้านสัมมากร)
มาจากการสวีป invariant จริงแบบ live (311 สถานี bma_watermap + 807 thaiwater_waterlevel,
13 invariant = 0 ทั้งหมด; สวีปรอบ 1,164 จุดพิกัดจริง 10 รูปแบบครัวเรือนต่อจุด) —
**ไม่ใช่** จาก M5 water-debt backtest ซึ่ง**ปฏิเสธทั้ง 219 แถว** (`MISSING_INPUT`
และ `FEW_EVENTS`) ไม่มีการอ้างความสามารถพยากรณ์ใดๆจาก M5

**ช่องว่างที่ยังเหลือ (บอกตรงๆ ไม่ปิดไว้):** ผลการทดลอง M5 ยังไม่สามารถให้ตัวเลข
หนี้น้ำที่ใช้ได้เลยแม้แต่แถวเดียว

**ช่องว่างที่ยกมาจาก `CHANGELOG.md` "Known issues (v0.1.5)" (ไม่ปิดไว้):**
- **BKK007 (บางใหญ่ นนทบุรี)** ยังขึ้น `VALIDATED_MVP` — ช่องว่างข้อมูล KG
  (จุดใกล้เคียงที่ประกาศ `IN_PROVINCE` ในนนทบุรีมีน้อยเกินไป) ไม่ใช่บั๊กโค้ด
  มี xfail test คลุมไว้แล้ว
- **LEAVE_NOW ยกระดับเกินจริง:** สีเขียวร่วมกับบ้านชั้นเดียวหรือข้อมูลเก่า
  อาจยังให้ผล LEAVE_NOW — เป็นค่าเริ่มต้นของ FloodConnect เอง รอผู้ก่อตั้ง
- **บรรทัด "ย้ายตอนนี้" อาจขึ้นบนการ์ดสีเขียว:** เมื่อ need profile ของครัวเรือน
  กระตุ้น ยังไม่ได้ reconcile
