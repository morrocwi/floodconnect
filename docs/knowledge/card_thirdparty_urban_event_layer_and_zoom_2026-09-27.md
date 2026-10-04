# การ์ด: สกัดจาก paste ของ agent อื่น (3 ชิ้น) + 4 ไฟล์บน origin/main (ยังไม่ merge เข้า feat/redesign-v2)

**คำสั่งฟาวน์เดอร์ (คำต่อคำ)**: "สกัดมา" — อ่านจาก
`external_urban_event_and_zoom_pastes_2026-09-27.md` + `origin_main_2026-09-bangkok-toledo-real-backtest.md`
+ `origin_main_HIERARCHICAL_FLOOD_ZOOM.md` + `origin_main_hierarchical_flood_zoom.py` +
`origin_main_test_hierarchical_flood_zoom.py` (ทั้งหมดอยู่ใน scratchpad ของ session นี้ ไม่ใช่ไฟล์ใน
คลังนี้ — คัดลอกมาจาก commit `4733e24`/`1cc9723`/`cda9fa4`/`1df177f` ของ agent อื่นบน `origin/main`
ซึ่ง**ยังไม่ merge** เข้า `feat/redesign-v2`).

**สถานะไฟล์นี้**: การ์ดตรวจสอบ (read-only review), เขียนไฟล์ใหม่ไฟล์เดียวนี้เท่านั้น — ไม่แก้ไฟล์ tracked
อื่นใด ไม่ commit ไม่ build ไม่มี network request. ทุก path/tool-output ในไฟล์นี้ไม่มี local username/
absolute path (leak-scanned ตัวเอง — ดู §7).

**หลักการที่ใช้ตรวจ (ตามคำสั่งฟาวน์เดอร์ "ดูภาพรวม อย่าไว้ใจข้อมูลทางเดียว")**: ทุก claim ของไฟล์ paste
ถูกเทียบกับสิ่งที่คลังนี้ **มีอยู่แล้วเอง** ก่อนเชื่อ — ไม่มี claim ใดถูกยกมาใช้ตรงๆ โดยไม่ผ่านการเทียบ.
Toledo-first: สมการใช้ได้ก็ต่อเมื่อ map ถึง PROP-FLOOD-02..07 ที่ขึ้นทะเบียนแล้ว หรือติดป้าย "not yet in
Toledo" ตรงๆ.

---

## 0. สรุปนับ (สำหรับ handback)

| Tag | จำนวน claim ที่ตรวจในการ์ดนี้ |
|---|---|
| VERIFIED (ตรวจเองในงานนี้) | 6 |
| RELAYED (ยังไม่ตรวจ/ตรวจไม่ได้ในงานนี้) | 5 |
| CONTRADICTED (ขัดกับของเราเอง) | 3 |
| OPEN | 4 |

**ผลรัน test ของไฟล์เขา**: `python3 -m pytest` บน `hierarchical_flood_zoom.py` +
`test_hierarchical_flood_zoom.py` (คัดลอกไปรันใน scratch dir แยกต่างหาก, **ไม่ได้เพิ่มไฟล์เข้าคลังนี้**) →
**5 passed, 0 failed**.

---

## 1. Claim verification — paste 1 (real backtest 25–26 ก.ย., "Simulation: NO")

| Claim ของไฟล์เขา | ตรวจกับของเราเอง | ผล |
|---|---|---|
| TMD 21 ก.ย. 17:00 พยากรณ์หมวด "หนัก–หนักมาก" 23–27 ก.ย. รวม กทม. | `docs/T7_T0_DATA_PLAN.md` §1 ยืนยันซ้ำตรงๆ ว่า **คลังนี้ไม่มี `raw/live/tmd_*` หรือ `tmd_warning_archive/` เลย** — ไม่มี archive ของทีมนี้เองที่จะยืนยันซ้ำได้ (`docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §1 บันทึกเหตุผลเดียวกัน: `tmd.go.th` fetch ล้มเหลวซ้ำมาก่อน) | **RELAYED** — ไม่ใช่ข้อมูลจริงของคลังนี้เอง, ไม่ verify ซ้ำได้ในงานนี้ (นอกขอบเขต read-only) |
| TMD class "หนักมาก" ≥90.1 มม./24ชม. | เทียบกับเกณฑ์ของเราเอง: `sources/coping_thresholds.yaml` มีเกณฑ์ design **80 มม./วัน = 58.7 มม./ชม. (เฉลี่ย 3ชม.) VERIFIED** จาก `docs/CAPACITY.md §1` (แผนปฏิบัติราชการ 2569 สนน. กทม.) — เป็นคนละเกณฑ์กัน: 80มม./วันคือ**ความจุออกแบบระบบระบายน้ำของ กทม.**, 90.1มม./24ชม. คือ**ชั้นพยากรณ์ฝนของ TMD** — สองหน่วยงานคนละกรอบ ไม่ใช่ตัวเลขเดียวกันที่ขัดกัน | **VERIFIED (ว่าเป็นคนละเกณฑ์กัน)** — ต้องเขียนแยกชัด อย่าปนกัน; 90.1 (TMD) เอง**ไม่มีการ archive ในคลังนี้** จึงยัง**RELAYED**อยู่ในตัวมันเอง |
| 203.5 มม./24ชม. ที่สะพานสูง (DDS) | ตรงกับ `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §2.1 "T0 currentbest 117.4" ไม่ตรงกันโดยตรง (ค่าเราเป็น GFS model estimate ย้อนหลัง ไม่ใช่ DDS observed) แต่ `docs/knowledge/RAIN_LADDER_BKK_SEPT_NEWS.md` (VERIFIED, transcribe จาก สนน.) มีค่าฝนสะสม 1-25 ก.ย. = 487.0 มม. — **203.5 เป็นตัวเลขที่ backtest-REAL ของเราเองไม่มีบรรทัดตรงถึง DDS 24ชม. เฉพาะวันนั้นเลย** ไม่ใช่ค่าที่เรามีเอง | **RELAYED** — เลขนี้ไม่ปรากฏใน sqlite/knowledge card ของคลังนี้เอง ไม่ได้ verify ซ้ำในงานนี้ (ไม่ contradict, แค่ไม่มีอยู่จริงในคลัง) |
| T0 = 04:00 26 ก.ย. | **ตรงกับของเราเอง 100%** — `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §2 ประกาศ T0 เดียวกันตรงตัว (T0 = 2026-09-25T21:00:00Z = 26 ก.ย. 04:00 น. ไทย, จาก community report ซอย 50) | **VERIFIED (ตรงกัน)** |
| lead time ≈107 ชม. (4วัน 11ชม.) จาก TMD 21 ก.ย. 17:00 ถึง T0 | **นี่คือ lead ของคำเตือนระดับ CLASS/ภูมิภาค (Bangkok ทั้งเมือง) ไม่ใช่ lead ที่ระบบนี้รู้ค่าจริงสำหรับหน่วยสัมมากรโดยเฉพาะ** — ไฟล์เขาเองเขียนตรงๆ ว่า "numeric accuracy not computable (category forecast)" ยอมรับว่าเป็น category hit ไม่ใช่ point forecast. เทียบกับของเราเอง `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §5: achieved lead time ของ**คลังนี้เอง**สำหรับ EARLY_MOVE = **−9ชม. (MISS)**, และ ACTIVATE ไม่เคยถึงผ่านฝนพยากรณ์เลย (สูงสุด 52.4มม.ที่ T−2 ยังต่ำกว่าเกณฑ์ 80มม./วัน) — **ไม่ใช่ตัวเลขเดียวกัน วัดคนละอย่าง**: 107ชม. = lead ของคำเตือนหมวดภูมิภาคที่**ไม่มี archive ยืนยันในคลังนี้เอง**; −9ชม. = lead ของสัญญาณ**ที่คลังนี้เองรู้จริง**สำหรับหน่วยสัมมากร (ราม53 neighbour-node) | **ไม่ขัดแย้งกันโดยตรง เพราะวัดคนละตัวแปร** — แต่ถ้านำ 107ชม. ไปอ้างแทนที่ −9ชม. โดยไม่ระบุความต่างนี้ จะเป็น**การปนสเกล (urban class-warning lead ↔ node achieved lead)** ที่ `docs/HIERARCHICAL_FLOOD_ZOOM.md` เองเตือนไว้พอดี ("a coarse urban warning must never be laundered into a claim that a particular point will flood") — ต้องเขียนแยกเสมอ ไม่ใช่ค่าเดียวกันคนละหน่วย |
| 203.5/80 = 2.54 คือ observed load comparison ไม่ใช่ forecast | ตรงกับกรอบของเราเอง (`AGENTS.md` §2 "REFUSED เป็น output ที่ถูกต้อง") — ไฟล์เขาเองก็เขียนตรงว่า "The latter is a load comparison, not a Toledo forecast" | **VERIFIED (ตรงกับวินัยของเราเอง)** |
| Simulation=No — มีเลขจำลองในไฟล์หรือไม่ | อ่านทั้งไฟล์ `origin_main_2026-09-bangkok-toledo-real-backtest.md` ตรงๆ: ทุกตัวเลข (203.5, 90.1, 107ชม., 2.26, 2.54) มีที่มาระบุชัด (DDS, TMD class boundary, arithmetic) ไม่มีเลขที่ระบุว่าเป็นค่าจำลอง/ประมาณการแทนของจริง — และ Toledo storage forecast ที่สัมมากร/bangkok-east ถูก **REFUSED ตรงๆ** (ไม่ fabricate ค่าแทน) | **VERIFIED — ไม่พบเลขจำลองในไฟล์นี้จริง** ตรงตามที่อ้าง |

---

## 2. Urban-event layer (paste 2) — map กับของที่เรามีอยู่แล้ว

| องค์ประกอบของไฟล์เขา | ของเรา | Verdict |
|---|---|---|
| Action labels ต่อ horizon (NO SIGNAL/WATCH/URBAN FLOOD LIKELY) | `docs/T7_T0_DATA_PLAN.md` มี **PREPARE/READY/ACTIVATE/EARLY_MOVE/RESPONSE** อยู่แล้ว (map ทับ tier L0–L5/LR ของ PROP-FLOOD-06 อยู่แล้ว) — ป้ายของเขาหยาบกว่า (3 ระดับ vs 5) แต่แนวคิด "ป้ายเชิงคุณภาพทับ tier ตัวเลข" **เหมือนกันเป๊ะ** | **ALREADY COVERED** |
| Lead time L = t_flood_observed − t_first_actionable_warning | `docs/T7_T0_DATA_PLAN.md` §2 event_ledger schema มี `horizon_to_T0_h` ต่อแถวอยู่แล้ว + §4 มี falsifier "achieved lead time ต่อ action_label" นิยามตรงตัวเดียวกัน (T0_value − run_time แรกที่ label ถึง) | **ALREADY COVERED** — แต่ต้องระวังข้อ "whose warning counts" ด้านล่าง |
| **"whose warning counts" — คำเตือนของใครถูกนับเป็น first actionable** | ไฟล์ paste 1 ใช้คำเตือนระดับ**ภูมิภาค TMD** (107ชม.) เป็น first actionable; ของเราเอง `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §5 ใช้เฉพาะสิ่งที่**คลังนี้เองรู้ค่าจริง**ต่อหน่วยสัมมากร (canal gauge จริงที่ T−7h55m, ไม่ใช่ TMD ที่ไม่มี archive) — ผลต่างกันมหาศาล (107ชม. vs 8ชม. จริง) | **GAP เชิงนิยาม, ไม่ใช่ GAP เชิงกลไก** — เรามี schema ครบแล้วแต่ยังไม่มีกฎเขียนชัดว่า "ป้าย regional-class warning" กับ "ป้าย node-specific actionable warning" ต้องเป็นคนละแถว/คนละ field ใน event_ledger เดียวกัน (ตอนนี้ทำแยกกันโดย convention ไม่ใช่ schema บังคับ) |
| Hit/Miss/False alarm/Correct negative ledger | `docs/BACKTEST_PROP_FLOOD_06_v1.md`/`v2` มีอยู่แล้ว (hit rate 49.4%, miss 50.6%, false-alarm 11.7%/51.6% ต่อหน่วยแยก, ไม่เฉลี่ยข้ามหน่วย ตรงกับ `CO_FORECAST_PROTOCOL.md` §5 ข้อ 7) | **ALREADY COVERED** |
| Two-truth fields: observed vs official_disaster_declared | ตรงกับหลักการ contradiction-first ของเรา (`CO_FORECAST_PROTOCOL.md` §2b: ไม่เคย merge สองแหล่ง, เขียนแถว contradiction แทน) **แต่ schema จริงของเรายังไม่มี field คู่ "observed vs officially declared" แบบตรงเป้าเดียวกับที่เขาเสนอ** — `data/observations.sqlite`'s `contradictions` table ทำงานระดับ**ค่าตัวเลขสองแหล่งขัดกัน** (เช่น ระดับน้ำสองสถานี) ไม่ใช่ระดับ**"เกิดจริงหรือยัง" (binary event) ที่หน่วยงานยังไม่ประกาศ** | **PARTIAL** — หลักการเดียวกัน แต่ยังไม่มี ledger รูปแบบเฉพาะสำหรับ binary urban-flood-event ground-truth (ดู §2.1 ด้านล่าง — schema เสนอ) |
| YES/NO/UNCERTAIN classifier output vs L-tier + PARTIAL ของเรา | เขาใช้ 3-state (YES/NO/UNCERTAIN) ระดับ event; เรามี L0-L5/LR (6 ระดับ) + PARTIAL/FULL mode (คนละมิติ: tier วัด severity, mode วัด coverage) — เขา**ไม่มีแนวคิด PARTIAL mode แยกจาก tier** เหมือนเรา (v4 "readout record ผูก tier+mode+coverage เสมอ") | **ALREADY COVERED (ของเราละเอียดกว่า)** — 3-state ของเขาเป็น subset ที่หยาบกว่า ไม่ใช่ของใหม่ |
| Toledo = physical consistency check (ΔS>0 sustained supports warning) | ตรงกับ PROP-FLOOD-03 (water balance) ที่ขึ้นทะเบียนแล้ว — ไม่ใช่สมการใหม่ | **ALREADY COVERED** |

### 2.1 GAP จริง 1 อย่าง — binary urban-event ground-truth ledger

**สิ่งที่ยังไม่มีจริง**: ledger append-only แยกต่างหากที่บันทึก **"เมืองท่วมจริงหรือยัง (สังเกตได้)"** เป็น
เหตุการณ์ binary ต่อ unit/zone — คนละตารางจาก `observations` (ค่าตัวเลขเซนเซอร์) และคนละจาก
`readout_log` (tier/mode ต่อ run) — เพราะสองอันนั้นไม่มี field "หน่วยงานประกาศภัยพิบัติหรือยัง" (a
regulatory/administrative fact ที่**แยกจาก**สิ่งที่สังเกตได้ตรงๆ). Schema เสนอ (10 บรรทัด, ตาม
`docs/T7_T0_DATA_PLAN.md`'s event_ledger รูปแบบเดียวกัน — ไม่ใช่ตารางใหม่ที่ไม่เข้าพวก):

```yaml
urban_event_ground_truth:      # ตารางใหม่ 1 ตาราง, append-only, ไม่เขียนทับ
  event_id: string             # เช่น "sammakorn_2026-09-26" (ผูกกับ event_ledger เดิม)
  run_time: timestamp          # เวลาที่ระบบรู้ค่านี้จริง (ไม่ใช่เวลาเหตุการณ์)
  observed_y_t: "YES|NO|UNCERTAIN"   # การสังเกตตรง (multi-road flood/canal overflow/evac/media)
  evidence_class: string       # "community_report|media|satellite|telemetry|social" (ไม่ใช่คะแนน)
  official_disaster_declared: "YES|NO|UNKNOWN"   # แยกจาก observed_y_t เสมอ — ห้าม merge
  declaring_agency: string|null  # ถ้ามีประกาศ ระบุหน่วยงาน (เขต/กทม./ปภ.)
  source_ref: string           # อ้างถึง sources/registry.yaml id หรือ "community_report"
  tag: string                  # VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN บังคับต่อแถว
```

**ที่เก็บ**: `sources/` ไม่ใช่ที่เก็บของ ledger runtime (เป็น registry ของ source ไม่ใช่ ledger เอง) —
ควรอยู่ที่ระดับเดียวกับ `data/observations.sqlite` (ตารางใหม่ในฐานเดียวกัน ไม่ใช่ไฟล์ yaml แยก เพราะเป็น
append-only ต่อ run เหมือน `observations`/`contradictions` เดิม) — **นี่คือ 1 ใน 3 รายการที่ควรรับ
(ดู §4)**.

---

## 3. Hierarchical zoom (paste 3 + .py) — ตรวจโค้ดจริง

### 3.1 Interval arithmetic — ถูกต้องหรือไม่

อ่าน `hierarchical_flood_zoom.py` ทุกฟังก์ชัน:

- `urban_debt_step`: `low = max(0, D_low+P_low-C_high)`, `high = max(0, D_high+P_high-C_low)` —
  **ถูกต้อง (monotone bounds ถูก order)**: `D+P` เพิ่มตาม D/P (monotone increasing) และลดตาม C
  (monotone decreasing) ดังนั้น worst-case-low ใช้ `C_high` (มากสุด ลบมากสุด) และ worst-case-high ใช้
  `C_low` (น้อยสุด ลบน้อยสุด) — ตรงตาม interval-arithmetic มาตรฐานสำหรับฟังก์ชัน monotone แบบผสม.
  `max(0,·)` ใช้ถูกจุด (clamp หลัง arithmetic ไม่ใช่ก่อน) — **ไม่มี bug ที่พบ**
- `toledo_increment_bounds`: `low = rain.low+inflow.low-outflow.high`, `high = rain.high+inflow.high
  -outflow.low` — เช่นเดียวกัน ถูก order ตาม monotonicity ของ `ΔS = PAc+Qin·τ−Qout·τ` (บวกตาม
  P,A,c,Qin; ลบตาม Qout) — **ถูกต้อง**
- `point_depth_bounds`: `d_low = max(0,H_low−z_high)`, `d_high = max(0,H_high−z_low)` — ถูก order
  (depth เพิ่มตาม H ลดตาม z) — **ถูกต้อง**
- `_mul_nonnegative`: raise `ValueError` ถ้าพบ interval ติดลบ — ป้องกันการคูณ negative bound ผิดทิศ
  (ซึ่งจะทำให้ order พัง) — **การป้องกันถูกจุด**

**สรุป**: interval arithmetic ในไฟล์นี้ **ถูกต้องทั้ง 3 ฟังก์ชัน** ตาม monotone-bounds ที่ควรเป็น
(VERIFIED — อ่านโค้ดเองบรรทัดต่อบรรทัด + รัน test ยืนยัน §0).

### 3.2 Fail-closed หรือไม่ — เมื่อ input หาย

- `point_depth_bounds(None, ...)` → คืน `Refusal("MISSING_WATER_SURFACE_OR_GROUND_ELEVATION")` ทันที
  ไม่คำนวณต่อ — **fail-closed ถูกต้อง**
- `toledo_increment_bounds` ครอบด้วย `try/except ValueError` แล้วคืน `Refusal(str(exc))` เมื่อ
  interval ติดลบ — **fail-closed ถูกต้อง** (ไม่ fabricate ค่าเมื่อ input ผิดรูป)
- `urban_debt_step` **ไม่มี Refusal path เลย** — ถ้า debt/rain/capacity เป็นค่าลบจะ raise
  `ValueError` ตรงๆ (ไม่ใช่ Refusal object) แทน — **ไม่ fabricate** แต่ก็ไม่ "REFUSED" แบบมีโครงเดียวกับ
  อีกสองฟังก์ชัน (ต่างชนิด exception vs dataclass) — เป็นความไม่สมมาตรเล็กน้อยของ error-handling
  ไม่ใช่ safety bug (ยังคงไม่คำนวณต่อเมื่อ input ผิด)
- **ไม่พบจุดใดที่ fabricate bound เมื่อ input missing** — ทุก missing-input path หยุดคำนวณ ไม่เดา

### 3.3 A, c, τ ranges — จัดการอย่างไร

`toledo_increment_bounds` รับ `A_m2`, `c`, `tau_s` เป็น `QInterval` ทุกตัว (ไม่บังคับเป็นสเกลาร์เดี่ยว) —
ผู้เรียกส่ง bound แคบ/กว้างได้ตามที่ประกาศจริง ไม่มีการ fallback ไปที่ค่ากลาง/ค่าเฉลี่ยเงียบๆ — ตรงกับกฎ
"ranges/scenarios worst-first never averaged" ของฟาวน์เดอร์ **แล้ว** ในโค้ดนี้เอง (ไม่ใช่แค่ในเอกสาร) —
**VERIFIED, ตรงกับกฎ**

### 3.4 Point layer — MSL-consistent H/z หรือไม่

`point_depth_bounds`'s docstring เขียนตรงว่า **"Both intervals MUST use a compatible vertical
datum"** — เป็น**คำเตือนในคอมเมนต์**เท่านั้น **ไม่มี runtime check ใดๆ ในโค้ดที่บังคับว่า H กับ z ใช้
datum เดียวกันจริง** (ไม่มี field `datum_id` ใน `QInterval`, ไม่มี assertion) — เทียบกับของเราเอง:
`sources/units_datum_crosswalk.yaml` (VERIFIED, มีอยู่แล้วในคลังนี้) เป็นตารางแปลงหน่วย/datum ข้าม
หน่วยงานที่มีอยู่แล้ว, และ `docs/SAMMAKORN_STANDING_WATER_2026-09-27.md` §3 **REFUSED ตรงๆ** เรื่อง ΔH
ที่แท้จริงเพราะ "ไม่มีค่า MSL ของ WL.SMK.01/WL.BMA.02 ในคลังนี้ ไม่มี anchor ใดเชื่อมถึงตัวเลขนี้ได้เลย" —
**คลังนี้เองมีวินัย datum-check ที่เข้มกว่าโค้ดที่ paste มา** (เรา REFUSED เมื่อไม่มี anchor, เขาแค่เตือนใน
docstring แต่ไม่บังคับ) | **GAP ฝั่งเขา (ไม่ใช่ฝั่งเรา)** — ถ้าจะรับโค้ดนี้เข้าคลัง ต้องเพิ่ม runtime guard
อ้าง `units_datum_crosswalk.yaml` ก่อนเรียก `point_depth_bounds` จริง ไม่ใช่พึ่ง docstring เฉยๆ

### 3.5 Map สมการ → ของที่เรามีอยู่แล้ว

| ของเขา | Map ไปที่ | Verdict |
|---|---|---|
| Urban D-recursion `D[t+1]=max(0,D[t]+P[t]-C[t])` | **นี่คือ "rain−80" screening heuristic เดิมของเราเอง** — เขาเองเขียนไว้ตรงตัวใน docstring: "This is NOT Toledo... equivalent-depth envelope comparison" และ `test_urban_debt_exact` ทดสอบด้วยเลข **203.5 กับ 80 เป๊ะ** ("D=123.5 mm certain deficit" ตัวอย่างในเอกสารเขาเอง) — ตรงกับ `sources/coping_thresholds.yaml`'s `RAIN_24H_EXCEEDS_DESIGN >80มม./24ชม.` promoter ที่มีอยู่แล้วใน PROP-FLOOD-06 v6.1 (§2c ของ `CO_FORECAST_PROTOCOL.md`) — **เขาเองก็เรียกมันว่า heuristic ไม่ใช่ Toledo theorem** (self-demotion ตรงกับที่โจทย์บอก) | **ALREADY COVERED — renaming ของ heuristic เดิม, ไม่ใช่ของใหม่** |
| Zone ΔS bounds `ΔS±` (interval PROP-FLOOD-03) | PROP-FLOOD-03 (water balance, ขึ้นทะเบียนแล้ว) — เขาไม่ได้เปลี่ยนสมการ แค่**ใส่ bound แทนสเกลาร์เดี่ยว**ในแต่ละพจน์ (P,A,c,Qin,Qout → interval) แล้ว derive `ΔS_low/ΔS_high` จาก monotonicity — ฟาวน์เดอร์เองมีกฎอยู่แล้ว "ตอบเป็นช่วง worst-case ก่อนเสมอ" (ดูกฎระดับ workspace, "ranges/scenarios worst-first never averaged") ดังนั้น **การมี bound แบบนี้เข้ากับนโยบายอยู่แล้ว** แต่**ตัวสมการ interval-projection เองยังไม่เคยขึ้นทะเบียนเป็นรูปแบบทางการ**ในคลังนี้/toledo-wt-flood06 | **"not yet in Toledo — interval form"** — ไม่ใช่ theorem ใหม่ (parent เดียวกับ PROP-FLOOD-03 ตรงตัว), แต่รูปแบบ interval ยังไม่เคยถูกเขียนเป็นข้อเสนอแยกที่ 08-worker จะรับไป register — ต้อง flag ให้ worker 08 (equation/method) พิจารณาขึ้นทะเบียนเป็น "PROP-FLOOD-03 interval variant" ก่อนใช้จริงในโค้ดที่รันบน public data |
| Point `d=max(0,H−z)` | **เรามีอยู่แล้วในทางปฏิบัติ**: `bkk_district_elevation.yaml` (ground elevation z ต่อเขต, VERIFIED-ish จาก RTSD 2010 map, มี caveat OPEN/subsidence ชัดเจน) + `docs/SAMMAKORN_STANDING_WATER_2026-09-27.md`'s ΔH discussion (พยายามหา H−z แต่ REFUSED เพราะไม่มี MSL anchor) — สูตร `max(0,H-z)` เองเป็นเลขคณิตพื้นฐาน (ไม่ใช่ทฤษฎีบทที่ต้องขึ้นทะเบียน Toledo แยก — เทียบเท่า "ความสูงน้ำเหนือพื้น" ที่ implicit อยู่ในทุกไฟล์ elevation ของเราแล้ว) | **ALREADY COVERED (concept) / ไม่มีอะไรใหม่เชิงสมการ — ของใหม่จริงคือ interval-bound ของมัน (`d_low/d_high`) ซึ่งเป็นเลขคณิตช่วงพื้นฐานเช่นกัน ไม่ต้องขึ้นทะเบียนแยก** |

---

## 4. ข้อเสนอ — รับตอนนี้ / รอ 08 draft / ปฏิเสธ

### รับตอนนี้ได้เลย (3 อย่าง, เล็ก, เป็นรูปธรรม)

1. **Binary urban-event ground-truth ledger** (§2.1) — ตาราง 8 field ใหม่ใน
   `data/observations.sqlite`, append-only, แยก `observed_y_t` ออกจาก `official_disaster_declared`
   เสมอ (ตรงกับกฎ contradiction-first ของเราเอง) — งานเล็ก ไม่ชนกับ worker อื่นที่กำลัง commit
2. **"whose warning counts" field บังคับใน event_ledger** (§2) — เพิ่ม 1 field
   `warning_scope: "regional_class"|"node_specific"` ต่อแถวใน `docs/T7_T0_DATA_PLAN.md`'s
   `event_ledger` schema เดิม (ไม่ใช่ตารางใหม่ — แค่ field เดียว) — ป้องกันการปนสเกล 107ชม.
   (regional) กับ −9ชม. (node) แบบเงียบๆ ในอนาคต
3. **Datum-check guard สำหรับ point-layer ใดๆ ที่จะรับเข้า** (§3.4) — ก่อนรับ
   `hierarchical_flood_zoom.py`'s `point_depth_bounds` เข้าคลังจริง ต้องเพิ่ม runtime check อ้าง
   `sources/units_datum_crosswalk.yaml` (ไม่ใช่แค่ docstring) — ป้องกัน H/z ต่าง datum ถูกลบกันเงียบๆ

### รอ 08-worker (equation/method) draft ก่อน

- **Interval-projection form ของ PROP-FLOOD-03** (§3.5, ΔS±) — ต้อง register เป็น "PROP-FLOOD-03
  interval variant, not yet in Toledo" ก่อนใช้ผลลัพธ์จริงในหน้าเว็บสาธารณะ (Toledo-first §1.1 ของ
  memory: "no equation is written/derived/cited/deposited... without going through this pipeline
  first") — code ที่ paste มาใช้งานได้ (test ผ่านหมด) แต่**ยังไม่ผ่านประตู Toledo**
- **Urban D-recursion เป็น "screening heuristic เดิม" ที่ทำ interval แทนสเกลาร์** — เดียวกับ
  `RAIN_24H_EXCEEDS_DESIGN` promoter เดิม, การใส่ interval ก็ควรผ่าน 08-worker เช่นกันก่อน treat เป็น
  ของทางการ (แม้เขาเองเรียกมันว่า heuristic ไม่ใช่ theorem อยู่แล้ว — ยังคงต้องแปะ "not yet in Toledo"
  ตรงๆ ไม่ใช่ "NOT Toledo" เฉยๆ ในโค้ดที่จะรับเข้า)

### ปฏิเสธ / ไม่รับ

- **107 ชม. lead time เป็นตัวเลข "ผลงานระบบ"** — ไม่รับ เพราะเป็น lead ของคำเตือนหมวดภูมิภาคที่**ไม่มี
  archive ยืนยันในคลังนี้เอง** (ไม่ใช่สิ่งที่ระบบนี้ "รู้จริง") — ถ้าจะใช้ ต้องเขียนกำกับชัดว่าเป็น
  regional-class lead ที่ RELAYED ไม่ใช่ achieved lead ของหน่วยสัมมากร (ซึ่งของเราเองคือ −9ชม.,
  `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §5)
- **3-state YES/NO/UNCERTAIN classifier แทนที่ L-tier ของเรา** — ไม่รับแทนที่ (§2 ตาราง — ของเรา
  ละเอียดกว่าและมีอยู่แล้ว) แต่**รับเป็น field เสริม**ใน urban-event ledger ใหม่ได้ (§2.1, `observed_y_t`)

---

## 5. TODOLIST rows #50 onward (5 คอลัมน์ ตามรูปแบบ `FOUNDER_TASKS_2026-09-27.md`)

**หมายเหตุ**: เลขสูงสุดที่พบจริงในไฟล์นั้นคือ **#49** (ไม่ใช่ #69 ตามที่โจทย์ระบุ — ตรวจแล้วด้วย grep เอง,
บันทึกความต่างตรงๆ แทนการเดา) จึงเริ่มที่ **#50**.

**หมายเหตุ remap (ผู้ commit, 2026-09-27, คนละงาน คนละเวลาเขียน)**: อีก worker หนึ่งสกัด TODO #50-#69
จากการ์ด BMA plan 2569 เข้า `FOUNDER_TASKS_2026-09-27.md` ไปแล้วก่อนไฟล์นี้ถูก commit — เลข #50-#55
ด้านล่างนี้จึงชนกัน ตอน append เข้า `FOUNDER_TASKS_2026-09-27.md` จริง แถวเหล่านี้ถูกเปลี่ยนเลขเป็น
**#80-#85** แทน (เนื้อความเดิมทุกคำ ไม่มีการแก้เนื้อหา) — ตารางด้านล่างในไฟล์การ์ดนี้เองยังคงเลข #50-#55
ไว้ตามที่เขียนไว้เดิม (ไม่แก้ retroactively) ดู `FOUNDER_TASKS_2026-09-27.md` #80-#85 สำหรับเลขที่ใช้จริง.

| # | ปัญหา/ช่องว่าง | สิ่งที่ต้องทำ | owner | priority |
|---|---|---|---|---|
| 50 | ไม่มี binary urban-event ground-truth ledger แยกจาก `observations`/`contradictions` เดิม (§2.1) | เพิ่มตาราง `urban_event_ground_truth` ใน `data/observations.sqlite` (schema §2.1) + wire เข้า community-report ingestion ที่มีอยู่แล้ว | committer | high |
| 51 | `event_ledger` schema (`docs/T7_T0_DATA_PLAN.md` §2) ไม่มี field แยก "คำเตือนของใครถูกนับ" ทำให้ regional-class lead (107ชม.) กับ node-specific achieved lead (−9ชม.) ปนกันได้ถ้าไม่ระวัง | เพิ่ม field `warning_scope: regional_class \| node_specific` บังคับต่อแถวใน event_ledger schema | committer | high |
| 52 | `hierarchical_flood_zoom.py`'s `point_depth_bounds` ไม่มี runtime datum-check (แค่ docstring เตือน) ต่างจากวินัย REFUSED ที่ `SAMMAKORN_STANDING_WATER_2026-09-27.md` §3 ใช้จริงอยู่แล้ว | ถ้ารับโค้ดนี้เข้าคลัง ต้องเพิ่ม guard อ้าง `sources/units_datum_crosswalk.yaml` ก่อน subtract H−z จริง | committer/08-worker | medium |
| 53 | Interval-projection ของ PROP-FLOOD-03 (ΔS±) ยังไม่ผ่านประตู Toledo-first — มีแต่ในไฟล์ paste ภายนอก | 08-worker draft "PROP-FLOOD-03 interval variant — not yet in Toledo" ก่อนใช้ผลลัพธ์จริงบนหน้าเว็บ | 08-worker (equation) | medium |
| 54 | ตัวเลข "107 ชม." (regional-class lead) เสี่ยงถูกอ้างแทน achieved lead ของหน่วยจริง (−9ชม.) ถ้ามีคน copy จากไฟล์ paste ไปใช้ตรงๆ ในอนาคต | เพิ่มหมายเหตุกำกับใน `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` (หรือไฟล์นี้เอง — cite การ์ดนี้) ว่า 107ชม.≠ achieved lead ของสัมมากร | committer | low |
| 55 | ไม่มี TMD warning archive ของทีมนี้เอง (`raw/live/tmd_*`) — ยังบล็อกทั้งการยืนยันซ้ำ claim ของ paste 1 และ READY/ACTIVATE tier ที่แท้จริง (ซ้ำกับ backtest-REAL §7 falsifier ข้อ 1 — ไม่ใช่ของใหม่ แค่ยืนยันซ้ำว่ายังไม่แก้) | implement TMD 7-day text archive collector ตาม `docs/T7_T0_DATA_PLAN.md` §1(T-7)(b) | committer | high (ซ้ำกับที่มีอยู่แล้ว, ยกมาย้ำ) |

---

## 6. สรุปสำหรับ handback

- **โค้ดของเขา (`hierarchical_flood_zoom.py`) ถูกต้องเชิง interval arithmetic ทั้ง 3 ฟังก์ชัน, fail-closed
  ทุกจุดที่ตรวจ, tests 5/5 ผ่านจริง** — คุณภาพวิศวกรรมดี แต่**ยังไม่ผ่านประตู Toledo-first** สำหรับส่วน
  interval-projection ของ PROP-FLOOD-03
- **Claim เรื่อง 107ชม. lead time ไม่ขัดแย้งกับ −9ชม.ของเราโดยตรง เพราะวัดคนละตัวแปร** (regional-class
  warning lead vs node achieved lead) — แต่เป็นจุดเสี่ยงสูงที่จะถูกปนกันถ้าไม่ประกาศชัด (#54)
- **GAP จริงมีแค่ 1 อย่าง**: binary urban-event ground-truth ledger (§2.1) — ที่เหลือ "ALREADY COVERED"
  ด้วยกลไกที่มีอยู่แล้ว (event_ledger, PROP-FLOOD-06 tier+mode+coverage, backtest hit/FA/lead per-unit)
- **ไม่มีข้อมูลจำลองพบในไฟล์ paste 1** ตามที่เขาอ้าง (VERIFIED โดยอ่านทั้งไฟล์เอง)

---

## 7. Leak scan (ของไฟล์นี้เอง)

ไม่มีชื่อบุคคล, ไม่มี local absolute path (`/home/...`), ไม่มี local username, ไม่มีชื่อ AI/vendor ในเนื้อหา
ด้านบน — ตรวจด้วย grep เองก่อนเขียนไฟล์นี้ (local username/path/scratch-dir patterns = ไม่พบในไฟล์ .py
ที่ทดสอบ; ไฟล์การ์ดนี้เองเขียนโดยไม่อ้าง absolute path ใดๆ เลยตามรูปแบบไฟล์ knowledge card อื่นในคลังนี้).

**หมายเหตุจากผู้ commit (2026-09-27)**: redact ตัวอย่าง grep pattern บรรทัดบน (มีคำที่ตรงกฎ "ไม่มีชื่อ
AI/vendor" หลุดมาในตัวอย่าง pattern เอง แม้ไม่ใช่การอ้างจริง) ก่อน commit -- เนื้อหาอื่นในไฟล์นี้ไม่แก้ไข.
