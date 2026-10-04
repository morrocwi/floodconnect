# Card — Dual-state, re-escalation, degradation-ladder, safe-node-continuity rules
(Hat Yai Nov 2025 lessons, locked in as repo-wide structural rules)

**Tag**: analysis-of-analysis (see provenance below) · **บันทึกเข้า**: 2569-09-28

**Provenance (must be read before anything else in this card)**: การวิเคราะห์ภายนอก
(ผู้ช่วย AI) ที่ผู้ก่อตั้งวาง 28 ก.ย. 2569 เสนอแนวคิด 8 ข้อโดยให้เหตุผลจาก
`experiments/2025-11-hat-yai-real-data-redteam.md` (มีอยู่แล้วในคลังนี้). ตามคำสั่งของ
ผู้ก่อตั้ง: **แนวคิด/การให้เหตุผลของ external analysis ถือเป็น RELAYED/INSTINCT เท่านั้น** —
**ข้อเท็จจริงของเหตุการณ์ (วันที่, จำนวนธง, ปริมาณฝน, การไหลทวน X.173A→X.90→X.44, จำนวนผู้ป่วย
เครื่องช่วยหายใจ) ต้อง re-source จากไฟล์ของคลังนี้เอง เท่านั้น** — ไม่ใช้ตัวเลขจาก external
analysis โดยตรง ถ้าไม่มีในไฟล์ของคลังนี้ **ให้ตัดทิ้ง ไม่ใส่**

## 0. ตรวจสอบตัวเลขที่ external analysis อ้าง เทียบกับไฟล์จริงของคลังนี้

- **"130 ventilator patients"** — **ไม่พบตัวเลขนี้ในไฟล์ใดของคลังนี้เลย**
  (`experiments/2025-11-hat-yai-real-data-redteam.md`, `docs/knowledge/card_hatyai_city_
  climate.md`, `docs/knowledge/case_hatyai_2553_2565.md` — grep ไม่พบ "130"/"ventilator"/
  "เครื่องช่วยหายใจ" คู่กับตัวเลขใดเลย) — ไฟล์ต้นทางของคลังนี้พูดถึงแค่เชิงคุณภาพ: "Hospital Hat
  Yai had an urgent electricity problem while critical patients required ventilators"
  (ไม่มีตัวเลข) — **ตัดตัวเลข "130" ทิ้งตามกฎ "ใช้ได้แค่สิ่งที่ไฟล์ของคลังนี้ระบุ"**
- ตัวเลข/วันที่อื่นทั้งหมดด้านล่าง **re-sourced จาก
  `experiments/2025-11-hat-yai-real-data-redteam.md` โดยตรง** (URL ทางการกำกับทุกบรรทัดในไฟล์
  ต้นฉบับนั้นแล้ว ไม่ re-verify ซ้ำในงานนี้)

## 1. ข้อเท็จจริงที่ re-source ได้จริง (จาก experiments/2025-11-hat-yai-real-data-redteam.md)

- 13-14 พ.ย. 2568: ONWR ประกาศ 30/2568 ระบุหาดใหญ่เป็นพื้นที่เฝ้าระวังน้ำท่วมฉับพลัน 17-22 พ.ย.
- 16-19 พ.ย.: คำเตือนอุตุฯ ต่อเนื่อง (ฝนหนักถึงหนักมาก 17-23 พ.ย.)
- **20 พ.ย. — เทศบาลนครหาดใหญ่ แถลงการณ์ฉบับที่ 2: สถานะเมือง "ปกติ/ธงเขียว"** ขณะที่คำเตือน
  ระดับภูมิภาคยังคงรุนแรงต่อเนื่อง — **นี่คือกรณี dual-state ตัวจริงที่การ์ดนี้ล็อกเป็นกฎ**
- 21 พ.ย.: แถลงการณ์ฉบับที่ 3 ธงเหลือง 12 ชุมชน, ฉบับที่ 4 ธงแดง 65 ชุมชน
- 22 พ.ย. 08:00: แถลงการณ์ฉบับที่ 5 ธงแดง 103 ชุมชน; RID รายงานฝน: คลองวะ 360 มม./24ชม.,
  คลองแตน 346 มม., คลองวัด 366 มม., คลองระบาย ร.1 เดินที่ 1,200 ลบ.ม./วิ (ตัวเลขเหล่านี้อยู่ใน
  การ์ดนี้เป็นข้อความอ้างอิงเท่านั้น ไม่ใส่เป็น attribute กราฟ)
- **24 พ.ย. — ONWR พยากรณ์การไหลทวนขึ้นสู่เมือง: สถานีต้นน้ำ X.173A (สะเดา) ระดับสูงขึ้นจะไหลลง
  มาถึง X.90 (คลองหอยโข่ง) และ X.44 (หาดใหญ่) ในวันที่ 25 พ.ย.** — ลำดับ X.173A → X.90 → X.44
  ที่ founder อ้างถึง **ตรงกับที่ไฟล์ต้นทางระบุจริง**
- 25 พ.ย.: จุดวิกฤต — ใช้รถยกสูง เรือ กำลังทหาร; ONWR ระบุระดับน้ำ 2568 เกินสถิติน้ำท่วมใหญ่ 2553
  ในลุ่มน้ำอู่ตะเภา
- 27 พ.ย. 06:00: X.44 = 7.59 ม. (ต่ำกว่าสูงสุด 2.38 ม., ยังเหนือตลิ่ง 0.19 ม.), X.174 (คลองวะ) =
  9.15 ม. (ต่ำกว่าสูงสุด 2.67 ม., ยังเหนือตลิ่ง 0.27 ม.) — ยืนยันว่าจุดสูงสุดคือ 25 พ.ย.

## 2. สิ่งที่มีอยู่แล้วในคลังนี้ (จาก
`docs/knowledge/card_thirdparty_hatyai_redteam_2025-11_review_2026-09-27.md`, review
card ที่มีอยู่ก่อนงานนี้แล้ว) — ไม่สร้างซ้ำ

| ข้อ | สถานะที่มีอยู่แล้ว | หลักฐาน |
|---|---|---|
| dual-state (current vs forward) | **PARTIAL** — mechanism มีอยู่แล้วแบบ implicit ผ่าน PROP-FLOOD-06 v4's `base_tier := max(band_tier, promoter_max)` (`toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md` บรรทัด ~450) + T7_T0's "สองนาฬิกา" (`docs/T7_T0_DATA_PLAN.md`) แต่ไม่มี field ชื่อ `current_state`/`hazard_state` แยกกันตรง ๆ ที่ใดในคลังนี้ | review card §3 แถว A |
| re-escalation/hysteresis สองพีค | **PARTIAL — SPEC-ONLY** (registered in the PROP-FLOOD-06 v6 proposal; NOT implemented: no `persisted_v6` persistence step in `compute()`/`apply_persistence()`, see `ENGINE_VERSION_DELTA_ITEMS` in `tools/backtest/compute_prop_flood_06_sammakorn.py`) — raise เข้า L5/LR ทันที, lower ต้องรอ p ชั่วโมงเหมือนเดิม, ตาม proposal เท่านั้น ยังไม่มีในโค้ด; v5's `upstream_rise_rate` promoter เป็นของจริงที่ implement แล้ว แยกจาก `persisted_v6` | review card §3 แถว C; a safety fix 2026-10-02 defect 2 |
| OUTSIDE_CALIBRATED_RANGE | **PARTIAL** — มี L5/LR แต่ไม่มี state ที่แปลว่า "เกินทุกค่าที่เคย calibrate มา" แยกต่างหาก | review card §3 แถว H |
| catchment DAG ลุ่มน้ำอู่ตะเภา (X.173A→X.90→X.44) | **GAP ยืนยันแล้ว** — 0 node ในกราฟ KG ของคลังนี้ทั้งที่มี live telemetry จริงแล้ว | review card §3 แถว D, TODOLIST #13 |
| multimodal edge state | **GAP** — ไม่มี schema นี้ที่ใดในคลังนี้ | review card §3 แถว E |
| safe-node 7 มิติ | **PARTIAL** — มีบทเรียนในการ์ด แต่ไม่มี field จริงใน schema | review card §3 แถว F |
| dynamic freshness + throughput routing | **GAP** — ไม่มีร่างในคลังนี้ ณ ตอนนั้น | review card §3 แถว G/I |

## 3. กฎที่ล็อกเข้าระบบวันนี้ (งานนี้)

1. **DUAL STATE rule** — `community_dag.py` เพิ่ม field ทางเลือก (optional) `current_local_
   state` ({GREEN,YELLOW,RED,UNKNOWN}) และ `forward_hazard` ({NONE,ACTIVE,UNKNOWN}) บน node
   ใดก็ได้ — **สอง field เป็นอิสระจากกันโดยสร้าง**: `validate_document()` ตรวจแค่ว่าค่าที่ใส่มา
   อยู่ใน vocabulary ปิด ไม่เคยอนุมานค่าหนึ่งจากอีกค่าหนึ่ง (ไม่มีโค้ดจุดใดตั้ง `forward_hazard`
   จาก `current_local_state`) — mapping ไปยังกลไกเดิม: PROP-FLOOD-06 v4's `max(band_tier,
   promoter_max)` ยังคงเป็น mechanism ที่แท้จริงสำหรับ**การคำนวณ tier จริง** (ไม่แตะสมการ) —
   field ใหม่นี้เป็นแค่ **readout label สองแกนที่แยกกันเก็บ** ไม่ใช่ตัวคำนวณ tier ใหม่
2. **RE-ESCALATION MEMORY** — ไม่ derive สมการใหม่ (persisted_v6 ยังไม่ implement เป็นโค้ดใน
   คลังนี้ ยังอยู่แค่ใน Toledo proposal doc — งานนี้ไม่แตะ) แทนที่ด้วย: (a) test ทั่วไปที่ใช้
   `tools/backtest/prop_flood_06_v5.py::apply_persistence` (มีอยู่แล้ว, reuse ตรง) กับลำดับ
   tier สังเคราะห์สองพีค (synthetic, ไม่อ้างว่าเป็นข้อมูลจริงของหาดใหญ่) เพื่อยืนยันคุณสมบัติ
   ทั่วไปว่าไม่ยุบตัวหลังพีคแรก; (b) การทดสอบกับ**ข้อมูลจริงของหาดใหญ่**ยังเป็นไปไม่ได้เพราะลุ่มน้ำ
   อู่ตะเภาไม่มี node ในกราฟเลย (ข้อ 2 ตาราง §2) — **บันทึกเป็น OPEN + test แบบ xfail** พร้อมเหตุผล
   ชัดเจน (ไม่ใช่เดา/ประดิษฐ์ข้อมูล)
3. **OUTSIDE_CALIBRATED_RANGE flag** — `tools/backtest/outside_calibrated_range.py` (ใหม่):
   เทียบค่าที่สังเกตกับเพดานสูงสุดที่ `sources/coping_thresholds.yaml`'s `derived` block
   คำนวณไว้แล้ว (max() ธรรมดา ไม่ใช่สูตรใหม่) — คืน label `OUTSIDE_CALIBRATED_RANGE`/
   `WITHIN_CALIBRATED_RANGE`/`OPEN` เท่านั้น ไม่คำนวณความลึกน้ำ/ความรุนแรงใด ๆ — wire เข้า
   `tools/typology/validate.py`'s report เป็น `outside_calibrated_range` section (อ่าน node
   attribute `ocr_check` ถ้ามี — ยังไม่มี node ใดประกาศ field นี้จริงในคลังนี้วันนี้ เป็นการต่อสาย
   ให้พร้อมใช้เท่านั้น, ตรงกับวินัย OPEN-gap เดิมของไฟล์นี้) — **เทียบข้ามลุ่มน้ำเป็นสิ่งที่ฟังก์ชันนี้
   ไม่ทำ** (เช่น เอา
   ฝนหาดใหญ่ไปเทียบเพดานกรุงเทพฯ) ตามที่ review card TODOLIST #15 เตือนไว้แล้ว
4. **EDGE MODE DEGRADATION ladder** — `community_dag.py` เพิ่ม `MODE_DEGRADATION_LADDER =
   ("normal", "high_clearance_only", "boat_only", "blocked")` เป็น optional edge attribute
   `mode_degradation` (แยกจาก `modes` เดิมซึ่งบอกว่า edge รองรับโหมดอะไรได้บ้าง) — UNKNOWN ไม่ถูก
   ปฏิบัติเป็น passable (find_safe_route() ยังไม่อ่าน field นี้เลย เป็น readout ladder สำหรับแสดงผล
   ก่อน ยังไม่ผูกเข้า routing logic ในงานนี้)
5. **SAFE NODE verification** — `community_dag.py::SAFE_NODE_CONTINUITY_FIELDS` (7 field:
   access/power/backup_power/water/comms/medical_capacity/occupancy state) สำหรับ
   `internal_safe`/`external_safe`/`support` — `report_safe_node_continuity_gaps()` รายงาน
   node ที่ไม่มี field เหล่านี้เลย (non-error report, เหมือน `tools/typology/validate.py`'s
   capability_gaps) — ค่า "UNKNOWN" ถือว่ามี field แล้ว (honest declaration), ไม่ใช่ gap
6. **NO FEASIBLE SAFE ROUTE** — ตรวจแล้ว: `find_safe_route()` **มีอยู่แล้ว** คืน
   `RouteResult(found=False, reason=...)` ที่ชัดเจนเมื่อไม่มีเส้นทางที่ผ่านเกณฑ์ (ไม่เคยประดิษฐ์
   เส้นทาง) — เพิ่มแค่ constant `REASON_NO_FEASIBLE_SAFE_ROUTE` ตั้งชื่อ string เดิม (ไม่เปลี่ยน
   พฤติกรรม) + test ยืนยันตรง ๆ
7. **Four-graph framing** — เพิ่ม section ใน `docs/TYPOLOGY_GRAPH.md` แมป Hydrology/Control/
   Community/Safe-Logistics เข้ากับ layer เดิม (water/power/self_help/resource+civil) — ไม่มี
   layer name ใหม่
8. **Historical fixture test** — ดูข้อ 2 ด้านบน (xfail สำหรับ re-escalation จริง) + fixture
   test สำหรับ dual-state (ข้อ 1) ที่สร้างจากข้อเท็จจริง §1 (20 พ.ย. ธงเขียว vs คำเตือนภูมิภาค
   ยังทำงาน) — **ไม่ใช่ page feature**, เป็นแค่ fixture ในไฟล์ทดสอบเท่านั้น ไม่เพิ่ม node หาดใหญ่
   เข้า `site/inputs/community/self_help_dag.yaml` (ตามคำสั่งฟาวน์เดอร์ "Hat Yai stays
   next-version scope for page claims")

## 4. Structural-issue row

ดู `docs/knowledge/structural_issues_2026-09-28.yaml` แถว `ISSUE-WARNING-06`
("single-state public flags can read as 'normal' while a forward hazard is active" —
both-sides framing)
