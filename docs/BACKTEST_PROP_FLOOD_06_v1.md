# BACKTEST_PROP_FLOOD_06_v1 — falsifier loop รอบ 2 (PARTIAL-mode ladder + ข้อมูลทางการไทย)

**PROP-FLOOD-06 PROPOSAL, unverified** — เอกสารนี้ทั้งฉบับรายงานผลการทดสอบข้อเสนอ ไม่ใช่ผลลัพธ์ของ
สมการ Toledo ที่ขึ้นทะเบียนแล้ว เขียนโดย worker แยก (write-scope: ไฟล์ใหม่เท่านั้น ไม่ commit
ไม่แก้ไฟล์เดิม)

**Version implemented**: `toledo-wt-flood06/registry/proposals/flood_outlet_coping.json`
**v3** (commit `4ceb9f2e`), read-only, ตรวจซ้ำก่อนปิดงาน (git log ล่าสุด ณ เวลาที่เขียนเอกสารนี้)
— **ไม่พบ v4** ที่ HEAD ณ เวลาที่รันงานนี้ จึงใช้กติกา C_H(U)/PARTIAL/promoter table ของ v3 ตามที่
ลงทะเบียนไว้ตรงๆ ไม่ได้เดา monotonic-max rule ของ v4 เอง

Code: `tools/backtest/prop_flood_06_v3.py` (engine), `tools/backtest/run_backtest_v1.py`
(runner) → `raw/backtest/results_v1.jsonl` (1,308 readout rows)

## 1. วิธีการ (สรุป)

- Engine ใหม่ implement C_H(U) case split (NO_PUMPS_IN_UNIT→R_H; pump-only-no-outlet→D_H
  ติด flag PARTIAL term; ทั้งคู่ resolve→min เดิม; ไม่มีทั้งคู่→REFUSED) และ mode
  `FULL`/`PARTIAL`/`LR` ตาม promoter table ของ v3 ทุกตัวอักษร (RAIN_24H_EXCEEDS_DESIGN,
  CANAL_AT_WARNING/CRITICAL/BANK_LEVEL, PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD) —
  `DAM_RELEASE_ABOVE_SPILL_THRESHOLD` และ `VULNERABLE_UNIT_PROMOTION` **ไม่ได้ประเมิน**
  งานนี้ (ไม่มี feed ข้อมูล dam-release หรือ vulnerable-population flag ใน repo นี้ — OPEN,
  ไม่ได้ตัดสินแทนว่าไม่ fire)
- **แหล่งข้อมูล Thai official history แทน GloFAS**: N.1 (สถานี 3219)/N.64 (3246) แม่น้ำน่าน
  2567, P.1 (3226) แม่น้ำปิงเชียงใหม่ 2567 — ใช้ `qmax` (field metadata ของ HII เอง, tag
  **RELAYED-HII-metadata**) เป็น `Q_cap,o` แทนช่องว่าง OUTLET_CAPACITY_UNKNOWN เดิม, และ
  discharge รายชั่วโมงจริงเป็น `Q_o,now` (**MEASURED-history**); X.44 (2591) คลองอู่ตะเภา
  หาดใหญ่ 2565 เช่นกัน; กรุงเทพฯ ฝั่งตะวันออก 2569 ใช้ `pumps_2569.csv` (สถานะปั๊ม
  ST.SPS.01-04 จริง, ไม่ใช่สมมติสถานการณ์ installed/zero อีกต่อไป) +
  `canal_normal_levels.yaml`/BMA warning-critical-bank lines จริงต่อสถานี — ทั้งหมด
  **MEASURED-on-backtest** ต่อ record
- GloFAS ยังใช้เฉพาะ AYUTTHAYA_BANGBAN (ไม่มีสถานีย้อนหลังในงานนี้) และ event เดิมของ
  HATYAI 2553/NAN(2567 ก่อน 1 ส.ค.)/CHIANGMAI(GloFAS ปี 2567 บางส่วน)/BANGKOK_EAST 2011
  ที่ carry-over จาก v0 (`events.yaml`) — **flagged RELAYED-GloFAS ทุกแถว** ผ่าน rerun ใน
  engine ใหม่เท่านั้น ไม่ได้ดึงใหม่
- ฝน: ใช้ ERA5 archive เดิม (`raw/backtest/rain/*.json`) ตามคำสั่งงาน "reuse" — ไม่ดึงใหม่
- Unit-day: 217 แถวเดิม (v0 carryover) + HATYAI 2565 (31 วัน, X.44) + NAN 2567 (46 วัน,
  ±10 วันรอบพีค 22 ส.ค. + วันควบคุม รวมในหน้าต่างเดียวกัน ≥20 วัน) + CHIANGMAI 2567 (31 วัน,
  ±10 วันรอบ 5 ต.ค. เช่นกัน) + BANGKOK_EAST 2569 (2 วัน, 26–27 ก.ย., ทุกช่วงเวลาที่มีจริงใน
  sqlite export) × c∈{0.5,1} × H∈{24,48} = **1,308 readout rows**, **271 unit-days**
  (HATYAI 93, NAN 56, CHIANGMAI 41, AYUTTHAYA 41, BANGKOK_EAST 40 — บางวันซ้อนทับระหว่าง
  v0-carryover กับข้อมูลใหม่ นับเป็นวันเดียวแต่มีสองแหล่งข้อมูล)
- ground truth ทุกวันที่มีอยู่แล้วใน `events.yaml` (จาก case cards) **ใช้ตรงๆ ไม่เขียนทับ** —
  วันใหม่ (นอกช่วง events.yaml เดิม) ใช้ window ที่ระบุใน founder's instructions (ป้าย INSTINCT ชัดเจน)

## 2. REFUSED (LR) share — MEASURED-on-backtest

**LR: 12/1,308 (0.9%)**, ลดจาก 92.5% ใน v0 อย่างมีนัยสำคัญตามที่ v3 proposal ตั้งใจ — ทั้ง 12
แถวเป็น NAN วันที่ 2024-09-04/07/08 (×4 scenario) ที่ **ไม่มี input จริงเหลือเลย**: อยู่นอกหน้าต่าง
ฝน ERA5 ที่ดึงไว้ (2024-08-15..08-31) และ N.1 discharge เป็น null ที่ชั่วโมงเหล่านั้นจริง —
ตรงตามนิยาม LR ของ v3 ("cov(U) entirely absent") ไม่ใช่บั๊ก

### Mode split (FULL/PARTIAL/LR), รวมและต่อหน่วย

| หน่วย | FULL | PARTIAL | LR | รวม |
|---|---|---|---|---|
| HATYAI | 84 | 372 | 0 | 456 |
| NAN | 68 | 212 | 12 | 292 |
| CHIANGMAI | 64 | 164 | 0 | 228 |
| AYUTTHAYA_BANGBAN | 164 | 0 | 0 | 164 |
| BANGKOK_EAST | 168 | 0 | 0 | 168 |
| **รวม** | **548** | **748** | **12** | **1,308** |

## 3. Confusion matrix (act-now L3-L5 vs time-有 L0-L2), เฉพาะ non-LR rows — MEASURED-on-backtest

รวม non-LR: 1,296/1,308 (99.1%)

| | ท่วมจริง | ไม่ท่วม |
|---|---|---|
| ทำตอนนี้ (L3-L5) | 152 (hit) | 116 (false alarm) |
| ยังมีเวลา (L0-L2) | 156 (miss) | 872 |

- Hit rate = 152/(152+156) = **49.4%** (ของวัน "ท่วมจริง" เท่านั้น)
- Miss rate = 156/308 = **50.6%**
- False-alarm rate = 116/(116+872) = **11.7%** (ของวัน "ไม่ท่วม")

### แยกตามหน่วย (act_now × flooded)

| หน่วย | act&flooded (hit) | act&not (false alarm) | time&flooded (miss) | time&not |
|---|---|---|---|---|
| HATYAI | 8 | 0 | 32 | 416 |
| NAN | 16 | 0 | 40 | 224 |
| CHIANGMAI | 28 | 8 | 52 | 140 |
| AYUTTHAYA_BANGBAN | 60 | 64 | 0 | 40 |
| BANGKOK_EAST | 40 | 44 | 32 | 52 |

**ข้อค้นพบสำคัญ — falsifier ของ v0 (Ayutthaya 320/320 REFUSED) ถูกแก้จริง**: AYUTTHAYA_BANGBAN
เดิม REFUSED 100% ด้วย `ZERO_CAPACITY_NONZERO_INFLOW` ใน v0; ในรอบนี้ (C_H(U):=R_H เมื่อ
`NO_PUMPS_IN_UNIT`) resolve เป็น FULL 164/164 แถว, **miss = 0** — แต่ false-alarm สูง (64/124,
51.6%) และ S_H ของวันท่วมจริง (1.745–2.977) ทับซ้อนกับวันไม่ท่วม (สูงสุด 2.843) มาก — threshold
ปัจจุบัน (0.9/1.2 บน S_H) **ไม่แยกสองกลุ่มนี้ได้ดีเลย** สำหรับหน่วยนี้ แม้จะไม่ REFUSED แล้วก็ตาม —
รายงานตรงๆ ไม่ปรับ threshold เอง

## 4. Lead time ที่ทำได้จริง (ชั่วโมงระหว่าง first L3+ กับวันท่วมจริง) — scenario c=1.0,H=24,
MEASURED-on-backtest ต่อ event

| เหตุการณ์ | first L3+ (mode/tier) | onset ท่วมจริง (ground truth) | lead time | ป้าย |
|---|---|---|---|---|
| HATYAI 2553 | 2010-11-01 (PARTIAL/L3) | 2010-10-31 | **-24h (ทำงานช้ากว่า onset 1 วัน)** | RELAYED ground truth |
| HATYAI 2565 (X.44) | **ไม่เคยขึ้น L3+ เลยทุก scenario** | 2022-11-30 | **ไม่พบสัญญาณเตือนล่วงหน้า** | MEASURED-history |
| NAN 2567 (N.1) | 2024-08-21 (FULL/L5) | 2024-08-19 | **-48h (ช้ากว่า onset 2 วัน)** | MEASURED-history |
| CHIANGMAI 2567 (P.1) | 2024-09-24 (FULL/L5) | 2024-09-24 | **0h (พร้อมกันพอดี)** | MEASURED-history/RELAYED |
| AYUTTHAYA 2011 | 2011-09-20 (FULL/L4) | 2011-10-01 | **+264h (~11 วันล่วงหน้า)** | RELAYED-GloFAS |
| BANGKOK_EAST 2011 | 2011-10-20 (FULL/L5) | 2011-10-25 | **+120h (5 วันล่วงหน้า)** | RELAYED-GloFAS |
| BANGKOK_EAST 2569 | 2026-09-20 (FULL/L5, ข้อมูลเก่า)/**ข้อมูลจริงเริ่ม 26 ก.ย.** | 2026-09-24/26 | **ข้อมูลจริง (pumps_2569.csv) เริ่มหลัง onset** | MEASURED |

**พูดตรงๆ**: 3 ใน 7 เหตุการณ์ (HATYAI 2553/2565, NAN 2567) ระบบเตือน**ไม่ทันหรือไม่เตือนเลย** —
HATYAI 2565 คือ falsifier ที่หนักที่สุดของรอบนี้: แม้จะมี **real gauge (X.44) แทน GloFAS แล้ว**
ตาม DATA_SWEEP ก็ตาม S_H ยังคง ≈0 ตลอดทั้งช่วง (discharge ที่วัดได้ช่วงวิกฤตจริงต่ำกว่าช่วงก่อน/
หลังหน้าเหตุการณ์ — ดู `DATA_SWEEP_2026-09-27.md` §A) — สมมติฐาน (INSTINCT ไม่ยืนยัน): X.44 อยู่
ปลายจุดผันน้ำเข้าคลอง ร.1 ทำให้ discharge ที่นี่ไม่สะท้อนวิกฤตจริง สำหรับ BANGKOK_EAST 2569
ข้อมูลจริง (pumps_2569.csv) เริ่มบันทึกวันที่ 26 ก.ย. เท่านั้น ขณะที่ ground truth ใน events.yaml
ระบุว่าเริ่มท่วม 24 ก.ย. แล้ว — **ไม่มีข้อมูลจริงให้ทดสอบว่าระบบเตือนทันหรือไม่ก่อนวันที่ 26** (ข้อจำกัด
ของชุดข้อมูล ไม่ใช่ของ proposal)

## 5. Promoter ที่ carry hit — MEASURED-on-backtest

จาก 748 แถว PARTIAL: promoter ที่ fire จริงมีเพียง **`RAIN_24H_EXCEEDS_DESIGN` (8 ครั้ง)**
ทั้งหมดในหน่วย CHIANGMAI — ไม่มีแถวใดที่ `CANAL_AT_*`/`PUMPS_ZERO_RUNNING_*` fire ในโหมด PARTIAL
เลย (เพราะ BANGKOK_EAST ซึ่งมี canal/pump feed จริง resolve เป็น **FULL** เสมอ ไม่ใช่ PARTIAL — ดู
§2 ตาราง mode split — canal/pump promoters จึงไม่เคยถูกทดสอบในโหมด PARTIAL รอบนี้เลย เป็น
ข้อจำกัดของ dataset ไม่ใช่ตัว promoter table เอง) `DAM_RELEASE_ABOVE_SPILL_THRESHOLD` และ
`VULNERABLE_UNIT_PROMOTION` **ไม่ได้ประเมินเลย** (ไม่มี feed) — OPEN

## 6. Sensitivity (รายงานเฉยๆ ไม่ปรับเอง) — S_H บน FULL-mode rows เท่านั้น, MEASURED-on-backtest

| หน่วย | S_H วันท่วมจริง | S_H วันไม่ท่วม | แยกได้ชัดไหม |
|---|---|---|---|
| AYUTTHAYA_BANGBAN | min=1.745 max=2.977 n=60 | min=0.058 max=2.843 n=104 | **ทับซ้อนมาก** (2.843 vs 1.745) |
| BANGKOK_EAST | min=0.000 max=1046.9 n=72 | min=0.000 max=0.003 n=96 | แยกได้บางส่วน (max ต่างกันมาก แต่ min ทับ 0.000 ทั้งคู่) |
| HATYAI | min=0.000 max=0.009 n=12 | min=0.000 max=0.043 n=72 | **แยกไม่ได้เลย** (ช่วงทับสนิท) |
| NAN | min=0.000 max=0.086 n=28 | min=0.001 max=0.443 n=40 | **แยกไม่ได้** (วันไม่ท่วมมี S_H สูงกว่าวันท่วมจริงด้วยซ้ำ) |
| CHIANGMAI | min=0.000 max=0.082 n=40 | min=0.000 max=0.483 n=24 | **แยกไม่ได้** เช่นกัน |

ไม่มี threshold เดี่ยวใน (0.3/0.6/0.9/1.2) ที่จะแยกสองกลุ่มได้ดีสำหรับ HATYAI/NAN/CHIANGMAI —
ปัญหาอยู่ที่การ resolve ตัวเลข (rain ERA5 ต่ำกว่าฝนจริงมาก, discharge ไม่สะท้อนวิกฤต) ไม่ใช่ตำแหน่ง
threshold — สอดคล้องกับข้อสังเกตเดิมใน v0/PROP-FLOOD-06 v3's OPEN calibration note

## 7. เปรียบเทียบ v0 → v1

| ตัวชี้วัด | v0 (min literal, REFUSED-on-any-gap) | v1 (C_H + PARTIAL) |
|---|---|---|
| REFUSED share | 92.5% (1550/1676) | **0.9% (12/1308)** |
| AYUTTHAYA miss rate | ไม่ resolve เลย (REFUSED 320/320) | **0% miss (60/60 hit)**, false-alarm 51.6% |
| หน่วยที่ resolve เป็นตัวเลขได้ | เฉพาะ BANGKOK_EAST, AYUTTHAYA (บางส่วน) | ทุกหน่วย (FULL หรือ PARTIAL) |
| HATYAI | REFUSED เกือบ 100% | resolve จริง (X.44) แต่ **ไม่เตือนทันเวลาเลย** (ใหม่: falsifier เชิงข้อมูล ไม่ใช่เชิง REFUSED) |

## 8. ข้อจำกัดที่ต้องพูดตรงๆ

1. **ERA5 rain ยังต่ำกว่าฝนจริงมาก** (เดิมจาก v0, ยังไม่แก้ในรอบนี้ตามคำสั่งงาน "reuse the ERA5
   archive") — กระทบ F_H ของทุกหน่วยที่ไม่มี rain gauge จริงในสมการ
2. **X.44 (หาดใหญ่) ไม่สะท้อนวิกฤตจริง** — discharge วัดได้ต่ำสุดพอดีช่วงท่วมจริง (§4) —
   นี่คือข้อค้นพบใหม่ของรอบนี้ ไม่ใช่ REFUSED แบบเดิม แต่เป็น falsifier ที่แรงกว่า: มีข้อมูลจริง
   แต่ข้อมูลนั้น **ไม่สัมพันธ์กับเหตุการณ์**
3. **qmax เป็น RELAYED-HII-metadata** ไม่ใช่ VERIFIED bankfull capacity จากรายงาน สทนช./RID
   ฉบับเต็ม (ตามที่ DATA_SWEEP ระบุไว้เอง) — ทั้ง N.1/N.64/P.1 measured peak เกิน qmax proxy
   37-54% ทุกสถานี ซึ่งอาจแปลว่า qmax เป็นค่าความจุ "ปกติ/design" ไม่ใช่ "bankfull สูงสุดจริง"
   — ไม่ตีความเกินนี้
4. **T_act เป็น INSTINCT approximation** เช่นเดียวกับ v0 (ยังไม่มี hourly F_H series จริง —
   ใช้ discharge/rain รายวันคงที่ตลอด horizon แทน) — ไม่ใช่การค้นหาจุดตัด T_act ตามนิยาม
   proposal ทุกตัวอักษร (ระบุไว้ในโค้ดเอง `prop_flood_06_v3.py`)
5. **BANGKOK_EAST 2569 มีข้อมูลจริงแค่ 2 วัน (26–27 ก.ย.)** — สั้นเกินกว่าจะทดสอบ lead time
   ล่วงหน้าจริง (ground truth บอกว่าท่วมเริ่ม 24 ก.ย. ก่อนข้อมูลจริงเริ่มบันทึกด้วยซ้ำ)
6. **Chao Phraya discharge ปี 2569 ไม่มีในงานนี้** — ทำให้ BANGKOK_EAST เป็น FULL ทุกแถวผ่าน
   `C_H(U):=D_H` (case b, outlet unresolved) เท่านั้น ไม่เคยทดสอบ `min(D_H,R_H)` จริงสำหรับ
   หน่วยนี้ในปี 2569
7. **`DAM_RELEASE_ABOVE_SPILL_THRESHOLD`/`VULNERABLE_UNIT_PROMOTION` ไม่ได้ทดสอบเลย** —
   ไม่มี feed ข้อมูลใน repo นี้งานนี้ — OPEN, ยังไม่ falsify/verify
8. **canal/pump promoters (BANGKOK_EAST) ไม่เคยเข้าโหมด PARTIAL** เพราะ resolve เป็น FULL
   เสมอ — promoter table ส่วนนี้ยังไม่ผ่านการทดสอบจริงในโหมดที่มันถูกออกแบบมาสำหรับ (PARTIAL)
9. **HATYAI 2553 ใช้ GloFAS เดิม (RELAYED, ไม่แม่นยำ)** — carry-over จาก v0 ไม่ได้แทนที่ด้วย
   ข้อมูลจริง เพราะ telemetry X.44 ไม่ย้อนไปถึงปี 2553 (all-null, ยืนยันจาก DATA_SWEEP)
10. **ground truth วันต่อวันยังเป็น RELAYED เป็นส่วนใหญ่** (การ์ดเคสให้ช่วงกว้าง ไม่ใช่ทุกวัน) —
    เหมือน v0

## 9. คำตัดสิน (verdict) ต่อหน่วยและภาพรวม

- **AYUTTHAYA_BANGBAN**: falsifier ที่หนักที่สุดของ v0 (contradiction ใน `min(D_H,R_H)`) **ถูกแก้
  จริง** ด้วย `C_H(U)` — ผ่าน self-falsifier ในแง่ REFUSED, แต่ **ยังไม่ผ่านในแง่ calibration**
  (false-alarm 51.6%, S_H ทับซ้อนหนัก §6) — ต้อง re-tune threshold หรือหา term เพิ่ม (เช่น
  upstream gauge จริงแทน proxy) ก่อนเชื่อถือได้
- **BANGKOK_EAST**: resolve เป็น FULL เสมอ, hit 40/72 บนวันท่วมจริง (55.6%) — ดีขึ้นจาก v0
  (0% hit) แต่ 2569 มีข้อมูลจริงสั้นเกินจะสรุป lead time ได้จริง
- **HATYAI**: **ยังไม่ผ่าน** — มีข้อมูลจริงแล้ว (X.44) แต่ระบบไม่เตือนทันเวลาเลยทั้ง 2553/2565 —
  falsifier เชิงข้อมูล (gauge ไม่สะท้อนวิกฤต) หนักกว่า falsifier เชิง REFUSED เดิมของ v0
- **NAN/CHIANGMAI**: resolve เป็นตัวเลขได้จริงแล้ว (ปิดช่องว่าง OUTLET_CAPACITY_UNKNOWN 100%
  เดิม) แต่ lead time ติดลบหรือเป็นศูนย์ทั้งคู่ — **เตือนไม่ทันหรือพร้อมกับ onset พอดี** ไม่ใช่
  ล่วงหน้า — S_H ไม่แยกสองกลุ่มได้ (§6)
- **ภาพรวม**: `C_H(U)` + PARTIAL mode **แก้ falsifier REFUSED ของ v0 ได้จริงตามที่ v3 proposal
  ตั้งใจ** (92.5%→0.9%) — นี่คือความสำเร็จที่ยืนยันได้ (MEASURED-on-backtest) แต่**ไม่ได้แปลว่า
  ระบบเตือนภัยทำงานถูกต้อง**: 3/7 เหตุการณ์จริง (HATYAI×2, NAN) เตือนช้ากว่าหรือไม่เตือนเลย, และ
  ที่ resolve เป็น FULL ได้ (AYUTTHAYA) ก็มี false-alarm สูง — **การอ้างว่า PROP-FLOOD-06 v3
  "ให้ระบบถูกต้อง" ยังเป็นการอ้างเกินหลักฐานเช่นเดียวกับ v0** เพียงแต่ตอนนี้ REFUSED ไม่ใช่
  ข้อจำกัดหลักอีกต่อไป — **falsifier ต่อไป**: ต้องหา (a) rain gauge จริง (ไม่ใช่ ERA5) สำหรับ
  น่าน/เชียงใหม่/หาดใหญ่ (b) คำอธิบาย/แก้ไขว่าทำไม X.44 discharge ไม่สะท้อนวิกฤตหาดใหญ่
  (c) Chao Phraya discharge ปี 2569 จริง (d) threshold ใหม่หรือ term เพิ่มสำหรับ AYUTTHAYA
  ก่อนที่ tier ladder นี้จะน่าเชื่อถือพอสำหรับ resident-facing use

## Sources / raw data

- `tools/backtest/prop_flood_06_v3.py` — engine (C_H/PARTIAL/promoter/mode)
- `tools/backtest/run_backtest_v1.py` — runner (unit-day construction, v0 carryover + Thai history)
- `raw/backtest/results_v1.jsonl` — 1,308 readout rows (unit × date × c × H)
- `raw/backtest/hii_history/*.json`, `sources/capacity_ledger_additions.yaml`,
  `sources/canal_normal_levels.yaml`, `raw/backtest/pumps_2569.csv` — Thai official history
  used in place of GloFAS (§1)
- `raw/backtest/events.yaml`, `raw/backtest/units.yaml`, `raw/backtest/rain/*.json` — v0
  carryover inputs (GloFAS/ERA5), unchanged

*PROP-FLOOD-06 PROPOSAL, unverified — v3 implemented, re-checked against toledo-wt-flood06
HEAD (commit `4ceb9f2e`) immediately before writing this report, no v4 found*
