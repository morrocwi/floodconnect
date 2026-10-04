# BACKTEST_PROP_FLOOD_06_v0 — falsifier ยกกำลัง 100+ instantiation

**PROP-FLOOD-06 PROPOSAL, unverified** — เอกสารนี้ทั้งฉบับรายงานผลการทดสอบข้อเสนอ ไม่ใช่ผลลัพธ์ของสมการ Toledo ที่ขึ้นทะเบียนแล้ว

## คำสั่ง founder (verbatim, 17:30)

> "โดยเฉพาะเคสหาดใหญ่หนักมาก เราจำลอง protocol จริงๆ อย่างน้อย 100 ครั้งจากเหตุการณ์จริงด้วยข้อมูลเก่า เพื่อดูว่าการคำนวณของเราให้ระบบถูกต้องไหม"

## 1. วิธีการ (Method)

- 5 หน่วยระบายน้ำ (`raw/backtest/units.yaml`): หาดใหญ่ (คลอง ร.1), น่าน (เมือง),
  เชียงใหม่ (เมือง, แม่น้ำปิง), อยุธยา/บางบาล (เจ้าพระยาสายหลัก), กรุงเทพฯ ฝั่งตะวันออก
  (แสนแสบ/ประเวศ/พระโขนง + ทางออกเจ้าพระยา)
- ฝน: Open-Meteo Archive API (ERA5 reanalysis) รายชั่วโมง ที่จุดศูนย์กลางแต่ละหน่วย —
  **VERIFIED** ดึงจริงงานนี้ ทุกคำตอบเก็บที่ `raw/backtest/rain/*.json`
- น้ำในลำน้ำ/คลอง: Open-Meteo Flood API (GloFAS reanalysis) รายวัน —
  **VERIFIED** ดึงจริง แต่ **RELAYED-tier ในการใช้งาน**: grid 0.25 องศาไม่สามารถ
  แม่นยำระบุลำน้ำจริงของคลองอู่ตะเภา/แม่น้ำน่าน/แม่น้ำปิงที่จุดศูนย์กลางเมืองได้ (พบว่าให้
  discharge ต่ำกว่า 10 m3/s แม้ในวันพีคน้ำท่วมจริง) — สามหน่วยนี้จึงถูกปฏิบัติเป็น
  `NO_GAUGE_IN_UNIT`/ไม่ credible ไม่ใช่ใช้ตัวเลขที่ผิดอย่างเงียบๆ; อยุธยา/บางบาล และ
  กรุงเทพฯ (จุด 13.73,100.50 และ 15.70,100.14) ให้ discharge ระดับพันลบ.ม./วินาที ที่
  สมเหตุสมผล — ใช้เป็น Q_o,now/Q_in,up ได้ (tag RELAYED)
- ฝนสำรอง (cross-check): NASA POWER daily, 3 หน้าต่างเหตุการณ์ (น่าน 2567, เชียงใหม่ 2567,
  หาดใหญ่ 2565) รวม >=10 วัน — `raw/backtest/nasa_power/*.json` — **VERIFIED** ดึงจริง
- น้ำขึ้นลง (tide): **ข้าม** ตามคำสั่งงาน — g_U(t):=1 ทุกกรณี (OPEN, ตามข้อกำหนดของ
  proposal เอง)
- สถานะปั๊มในอดีต: **ไม่ทราบ** — รันสองสถานการณ์เสมอ: `pumps_installed` (ใช้ความจุที่
  ติดตั้งไว้ทั้งหมดจาก ledger, tag INSTINCT ว่าเดินเครื่องเต็ม) กับ `pumps_zero`
  (D_H:=0 ทุกหน่วย)
- รวมทดสอบ: **217 unit-day** (มากกว่าเป้า 100 ที่ founder สั่ง) x 2 ค่า c
  (0.5/1.0) x 2 สถานการณ์ปั๊ม x 2 horizon (H=24,48) = **1676 readout rows**
  (`raw/backtest/results.jsonl`)

### unit-day นับตามหน่วย

| หน่วย | true (ท่วมจริง) | false (control/ไม่ท่วม) | รวม |
|---|---|---|---|
| HATYAI | 7 | 76 | 83 |
| NAN | 7 | 20 | 27 |
| CHIANGMAI | 10 | 16 | 26 |
| AYUTTHAYA_BANGBAN | 15 | 26 | 41 |
| BANGKOK_EAST | 16 | 24 | 40 |

## 2. REFUSED share และเหตุผล

REFUSED: **1550/1676** (92.5%)

| refusal code | count |
|---|---|
| MISSING_INPUT | 640 |
| ZERO_CAPACITY_NONZERO_INFLOW | 502 |
| OUTLET_CAPACITY_UNKNOWN | 408 |

ตรงกับที่คาดไว้: น่าน/เชียงใหม่ REFUSED 100% (`OUTLET_CAPACITY_UNKNOWN`) เพราะไม่มีเอกสาร
ใดใน repo นี้ระบุความจุ bankfull/design ของแม่น้ำน่านหรือแม่น้ำปิงผ่านตัวเมือง — เป็นช่องว่าง
ข้อมูลจริง ไม่ใช่บั๊ก หาดใหญ่ REFUSED เกือบทั้งหมดด้วย `MISSING_INPUT` เพราะ GloFAS grid ไม่
resolve คลอง ร.1 ให้ค่าที่น่าเชื่อถือ (ดู §5)

### 2.1 การค้นพบสำคัญที่สุดของรอบนี้: ข้อขัดแย้งในตัว proposal เอง (D_H=0 ทำให้ AYUTTHAYA REFUSED 100%)

AYUTTHAYA_BANGBAN มี Q_cap,o และ Q_o,now/Q_in,up ที่ resolve ได้จริง (proxy, ดู §6 ข้อ 3)
แต่กลับ **REFUSED ทั้ง 320/320 แถว ด้วย `ZERO_CAPACITY_NONZERO_INFLOW`** — สาเหตุ: หน่วยนี้
ไม่มีปั๊มประกาศไว้ (`NO_PUMPS_IN_UNIT`) จึง D_H(U):=0 เสมอ (ทั้งสองสถานการณ์ปั๊ม, เพราะ
P_installed=0 อยู่แล้ว) เมื่อคำนวณตามตัวอักษรของสมการ `min(D_H,R_H)` จริงๆ ค่านี้จะเป็น
`min(0, R_H) = 0` เสมอ **ไม่ใช่ R_H ตามที่ตาราง "Three worked instantiations" ของ**
**proposal เองอ้างไว้** ("อยุธยา ... OUTLET always (min(D_H,R_H)=R_H)") — สอง
ข้อความในเอกสาร PROP-FLOOD-06 ขัดกันเอง: นิยาม `D_H(U):=0` เมื่อไม่มีปั๊ม บวกกับนิยาม
`min(D_H,R_H)` ตามตัวอักษร ให้ผล REFUSED เสมอสำหรับเมืองริมแม่น้ำที่ไม่มีปั๊ม แต่ตาราง
ตัวอย่างของ proposal เองสมมติว่า D_H ที่ =0 จาก "ไม่มีปั๊ม" ไม่ควรถูกนับใน min() เลย
(ให้ผลลัพธ์เป็น R_H ล้วนๆ) — **นี่คือ falsifier ที่แรงที่สุดของงานนี้ต่อตัว proposal เอง**
ไม่ใช่แค่ต่อ threshold: สมการตามตัวอักษรใช้กับ "เมืองริมแม่น้ำสายหลักไม่มีปั๊ม" (เช่น
อยุธยา, และน่าจะรวมน่าน/เชียงใหม่ด้วยถ้าเคย resolve ได้) ไม่ได้เลยจนกว่าจะแก้ไข
นิยาม `min(D_H,R_H)` ให้ข้าม D_H เมื่อ `NO_PUMPS_IN_UNIT` เป็นจริง — **รายงานไว้ตรงนี้
ไม่ได้แก้สมการเอง** ตามกติกา Toledo (ห้ามแก้ proposal โดยพลการ, ต้องส่งคืนให้ founder/
ผู้เสนอ)

## 3. Confusion matrix (รวม, เฉพาะ non-REFUSED rows) — MEASURED-on-backtest

รวบ L3-L5 = "ทำตอนนี้ (act now)", L0-L2 = "ยังมีเวลา (time)"

| | ท่วมจริง | ไม่ท่วม |
|---|---|---|
| ทำตอนนี้ (L3-L5) | 0 | 0 (false alarm) |
| ยังมีเวลา (L0-L2) | 56 (miss) | 70 |

- Hit rate (ถูกทั้งเตือนทันเวลาและนิ่งตอนไม่ท่วม) / non-refused: 55.6%
- Miss rate (ท่วมจริงแต่ระบบบอกว่ายังมีเวลา): 100.0%
- False-alarm rate (บอกทำตอนนี้แต่ไม่ท่วม): 0.0%

non-REFUSED rows ทั้งหมด: 126 จาก 1676 (7.5%) — ตัวเลข
hit/miss/false-alarm ด้านบนคำนวณบนเศษส่วนนี้เท่านั้น ไม่ใช่ทั้ง 100%

### แยกตามหน่วย (non-REFUSED rows เท่านั้น)

| หน่วย | act&flooded | act&not | time&flooded(miss) | time&not |
|---|---|---|---|---|
| BANGKOK_EAST | 0 | 0 | 56 | 70 |

## 4. หาดใหญ่ — รายละเอียด (founder-flagged, largest block)

- 2553 (2010): NOT REACHED before/at flood day 2010-10-31 in this run (ladder never hit L3+ under this scenario, or was REFUSED every day -- see table)
- 2565 (2022): NOT REACHED before/at flood day 2022-11-30 in this run (ladder never hit L3+ under this scenario, or was REFUSED every day -- see table)

Scenario ที่ใช้หาค่านี้: `H=24, c=1.0 (upper bound), pumps_zero` (worst-case ที่
ควรเตือนได้ไวที่สุดถ้าระบบทำงานถูก) — ตารางเต็มของทุกวันในสองเหตุการณ์นี้ (tier ต่อวัน):

| เหตุการณ์ | วันที่ | REFUSED? | tier | S_H | T_act | ท่วมจริง? |
|---|---|---|---|---|---|---|
| hatyai_2553 | 2010-10-20 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-21 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-22 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-23 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-24 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-25 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-26 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-27 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-28 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-29 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-30 | True | LR | - | - | False |
| hatyai_2553 | 2010-10-31 | True | LR | - | - | True |
| hatyai_2553 | 2010-11-01 | True | LR | - | - | True |
| hatyai_2553 | 2010-11-02 | True | LR | - | - | True |
| hatyai_2553 | 2010-11-03 | True | LR | - | - | True |
| hatyai_2553 | 2010-11-04 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-05 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-06 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-07 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-08 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-09 | True | LR | - | - | False |
| hatyai_2553 | 2010-11-10 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-15 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-16 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-17 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-18 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-19 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-20 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-21 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-22 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-23 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-24 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-25 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-26 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-27 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-28 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-29 | True | LR | - | - | False |
| hatyai_2565 | 2022-11-30 | True | LR | - | - | True |
| hatyai_2565 | 2022-12-01 | True | LR | - | - | True |
| hatyai_2565 | 2022-12-02 | True | LR | - | - | True |
| hatyai_2565 | 2022-12-03 | True | LR | - | - | False |
| hatyai_2565 | 2022-12-04 | True | LR | - | - | False |
| hatyai_2565 | 2022-12-05 | True | LR | - | - | False |

## 5. ความอ่อนไหวของ threshold (sensitivity, รายงานเฉยๆ ไม่ปรับเอง)

proposal กำหนด S_H bands ที่ 0.3/0.6/0.9/1.2 และ T_act ที่ 6h/24h/48h เป็น
OPEN-for-founder-tuning มาแต่ต้น — งานนี้ **ไม่ได้ปรับค่าเหล่านี้เอง** ตามกติกา 
("report, do not tune silently") สิ่งที่สังเกตได้จากผลลัพธ์ที่ resolve ได้จริง (อยุธยา/
กรุงเทพฯ เท่านั้น เพราะน่าน/เชียงใหม่/หาดใหญ่ REFUSED เกือบหมด):

- **BANGKOK_EAST**: S_H บนวันท่วมจริง [min=0.00 max=0.00 n=56]; S_H บนวันไม่ท่วม [min=0.00 max=0.00 n=70]

ถ้าช่วงสองกลุ่มทับกันมาก (overlap) แปลว่า threshold คงที่ตัวเดียวแยกไม่ออกสำหรับหน่วยนี้
— ดูตัวเลขจริงด้านบนก่อนสรุป ไม่ตัดสินแทน founder

## 6. ข้อจำกัดที่ต้องพูดตรงๆ (honest limitations)

1. **ฝนเป็น reanalysis (ERA5) ไม่ใช่เครื่องวัดจริง** — ที่จุดภูเขา/เมืองเล็ก ค่าอาจต่ำกว่า
   ฝนที่ตกจริงมาก (กรณีน่าน 2567: การประชุมทางการรายงานฝนจริง 388 มม. ขณะที่โมเดล
   พยากรณ์ไว้เพียง 80 มม. ตามการ์ด `case_nan_2567.md` — ถ้า reanalysis ERA5 มีอคติ
   คล้ายกัน ตัวเลข F_H ของน่านในรายงานนี้อาจ**ต่ำกว่าความจริง**)
2. **GloFAS เป็นโมเดล ไม่ใช่สถานีวัดจริง** และที่ grid 0.25 องศา ไม่ resolve ลำน้ำ/คลอง
   ขนาดกลาง-เล็ก (น่าน, ปิงที่เชียงใหม่, คลอง ร.1) เลย — ผลที่ resolve ได้จริง (อยุธยา,
   กรุงเทพฯ) มีขนาด magnitude สมเหตุสมผลเทียบ ledger เอง (ดู §1) แต่ก็ยังเป็นโมเดล
   ไม่ใช่ VERIFIED gauge
3. **ความจุ outlet บางส่วนเป็น OPEN หรือ proxy แทนตัวจริง** — อยุธยา/บางบาล ใช้ 3,100
   m3/s (ตัวเลข C.13 operational limit) เป็น **proxy INSTINCT** ไม่ใช่ค่าความจุเฉพาะจุด
   ของอยุธยาเอง และคลองผันน้ำหลากบางบาล-บางไทร (1,200 m3/s) **ยังไม่สร้างเสร็จ**ใน
   ปี 2554 ที่กำลัง backtest — การใช้ตัวเลขความจุปัจจุบันย้อนไปปี 2554 เป็นความคลาดเคลื่อน
   เชิงวิธีวิจัยที่ต้องระวัง ไม่ใช่ error ที่ซ่อนไว้
4. **ไม่มีสถานะปั๊มในอดีตจริง** — ใช้ 2 สถานการณ์ครอบ (ติดตั้งเต็ม/ปั๊ม=0) แทนความจริงที่
   ไม่รู้; กรุงเทพฯ ฝั่งตะวันออกยังใช้ตัวเลขความจุปั๊มปี 2569 (1,200 m3/s ฝั่งพระนคร)
   ย้อนไปทดสอบปี 2554 ด้วย — anachronism อีกจุดหนึ่ง ที่ flag ไว้ใน units.yaml
5. **g_U(t) (tide/gravity derating) = 1 เสมอ** ตามคำสั่งงาน (ข้าม tide) — ไม่มีตาราง
   น้ำขึ้นลงย้อนหลังในงานนี้ ทำให้ D_H ของกรุงเทพฯ อาจสูงเกินจริงในช่วงน้ำทะเลหนุน
6. **T_act ใช้ discharge รายวันคงที่ตลอด 24 ชม.** (ไม่มี hourly discharge จริงจาก
   GloFAS free tier) — เป็นการประมาณ INSTINCT ทำให้ T_act หยาบกว่าที่ proposal ตั้งใจ
7. **ground truth วันต่อวันส่วนใหญ่เป็น INSTINCT** (การ์ดเคสให้แค่เดือน/ช่วงกว้างๆ ไม่ใช่
   ทุกวัน) — เฉพาะบางวันที่มีวันที่ชัดเจนในการ์ด (เช่น เชียงใหม่ 25 ก.ย./5 ต.ค., น่าน 19-20
   ส.ค.) ถึงเป็น RELAYED จริง
8. **L5 (already-critical pre-check) ไม่ได้ implement** — ไม่มีข้อมูล "ระดับน้ำเกิน
   threshold แล้ว" ที่เชื่อถือได้ในงานนี้ (proposal เองก็ทิ้ง threshold นี้เป็น OPEN)

## 7. คำตัดสิน (verdict) — ผ่าน falsifier ของตัวเองไหม

**ยังสรุปแบบ pass/fail เดียวไม่ได้ (OPEN, ตรงไปตรงมา):**

- ที่ resolve เป็นตัวเลขได้จริง (อยุธยา, กรุงเทพฯ) จำนวน non-REFUSED rows มีจำกัด และ
  ยังพึ่ง proxy/anachronism หลายจุด (§6) — ตัวเลข hit/miss/false-alarm ใน §3 เป็น
  MEASURED-on-this-backtest จริง แต่ตัวอย่างเล็กเกินกว่าจะยืนยัน/ปฏิเสธ calibration ของ
  threshold ปัจจุบันอย่างเด็ดขาด
- ที่ founder ต้องการทดสอบมากที่สุด (หาดใหญ่) **REFUSED เกือบทั้งหมด** เพราะ
  GloFAS ไม่ resolve คลอง ร.1 — นี่คือ falsifier ที่แรงที่สุดของรอบนี้: **ระบบเตือนภัย
  แบบ PROP-FLOOD-06 ใช้กับหาดใหญ่ไม่ได้เลยด้วยข้อมูลฟรีระดับโลกชุดนี้** ต้องมี Q_o,now
  ของคลอง ร.1 จากสถานีจริง (ONE037 / X.44 / ปตร.อู่ตะเภา, มีอยู่ใน sqlite แล้วแต่ไม่มี
  ประวัติย้อนหลังที่ backtest นี้เข้าถึงได้) จึงจะตอบคำถามของ founder ได้ตรงๆ
- น่าน/เชียงใหม่: REFUSED 100% เพราะไม่มีความจุ outlet ที่ประกาศไว้เลย — falsifier
  ระดับ "ยังตอบไม่ได้เลย" ไม่ใช่ "ตอบผิด"
- **อยุธยา/บางบาล: REFUSED 100% (320/320) ด้วย `ZERO_CAPACITY_NONZERO_INFLOW` แม้
  Q_cap,o/Q_o,now/Q_in,up resolve ได้จริงทุกตัว** — สาเหตุคือข้อขัดแย้งในตัว proposal
  เอง (§2.1), ไม่ใช่ข้อมูลขาด — นี่คือ falsifier ที่หนักที่สุดของรอบนี้: สมการตามตัวอักษร
  ใช้กับเมืองริมแม่น้ำสายหลักที่ไม่มีปั๊มไม่ได้เลย ต้องแก้นิยาม `min(D_H,R_H)` ก่อน
- **ข้อสรุปที่ยืนยันได้ (MEASURED-on-backtest)**: การอ้างว่า PROP-FLOOD-06 "ให้ระบบ
  ถูกต้อง" ในสภาพข้อมูลปัจจุบันของ repo นี้เป็นการ**อ้างเกินหลักฐาน** — ส่วนใหญ่ของ
  unit-day ที่ทดสอบ (ดู §2) จบที่ REFUSED ไม่ใช่ tier ตัวเลข ต้องเติมสถานีย้อนหลังจริง
  (Q_o,now/Q_in,up/pump-state) ก่อนจึงจะ falsify calibration ของ threshold ได้อย่างมี
  น้ำหนักสถิติ

## Sources / raw data

- `raw/backtest/units.yaml` — unit tuples, ทุก constant ติด tag
- `raw/backtest/events.yaml` — ground truth ทุก unit-day
- `raw/backtest/results.jsonl` — ทุก readout row (unit x date x H x c x pump)
- `raw/backtest/rain/*.json`, `raw/backtest/flood/*.json`, `raw/backtest/nasa_power/*.json`
  — payload ดิบทุกคำขอ (33 คำขอ, 1 คำขอ/URL, ไม่ retry)

*PROP-FLOOD-06 PROPOSAL, unverified*