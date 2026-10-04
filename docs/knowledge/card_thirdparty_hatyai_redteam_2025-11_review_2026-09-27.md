# บัตรทบทวน — Hat Yai 2568 (Nov 2025) red-team ของ AI ตัวอื่น (origin/main) เทียบกับภาพรวมคลังนี้

**สั่งงานโดย founder (verbatim)**: "ตรงกันให้ดูภาพรวมด้วย อย่าไว้ใจข้อมูลทางเดียว" — ให้ cross-check
red-team ของ agent อีกตัว (`experiments/2025-11-hat-yai-real-data-redteam.md`, commit `6cb93b18`,
origin/main) กับ**ภาพรวม**ของคลังนี้ ไม่เชื่อช่องทางเดียว. ต่อมามีการเพิ่มขอบเขต (ผู้ก่อตั้งส่งต่อ
follow-up ของ agent เดียวกันเรื่อง "contradiction → action policy") — ดู §3b.

**สถานะไฟล์นี้**: READ-ONLY review, สร้างไฟล์ใหม่ไฟล์เดียวนี้เท่านั้น ไม่แก้ไฟล์อื่น ไม่ commit ไม่รัน
`collect.py --all`. งานนี้ทำโดย กระบวนการคู่ขนานกับ worker อื่นในเวิร์กทรีเดียวกัน (ไม่แตะไฟล์ untracked
ของทีมอื่น).

**คำเตือนต้นทาง**: ไฟล์ต้นทางของ red-team (`origin_main_hatyai_redteam_*.md`) และ paste สรุปของ
founder เป็น **third-party AI output, RELAYED** ตามหลักที่ founder สั่งไว้ในบทสนทนา — ทุกอย่างในไฟล์นี้
ที่อ้างอิงกลับไปยังไฟล์นั้นถือเป็นการ relay ไม่ใช่ finding ของทีมนี้เอง เว้นแต่มีแหล่งที่สองของคลังนี้เอง
มายืนยัน/หักล้าง (ระบุไว้ทุกแถว).

---

## 1. ตารางตรวจสอบรายข้อกล่าวอ้าง (10 claims, dated Nov 2568)

| # | Claim (จาก red-team) | สิ่งที่คลังนี้เองพูด (แหล่งที่สอง) | Tag | หมายเหตุ |
|---|---|---|---|---|
| 1 | 13–14 พ.ย. — ONWR ประกาศ 30/2568 (13 พ.ย., เผยแพร่ผ่าน ปชส. 14 พ.ย.) ระบุหาดใหญ่เป็นพื้นที่เฝ้าระวังน้ำท่วมฉับพลัน 17–22 พ.ย.; ศูนย์อุตุฯ ภาคใต้ฝั่งตะวันออกออกเตือนภัยฉบับ 1 (59/2568) 14 พ.ย. | คลังนี้ไม่มี collector/archive ต่อ ONWR announcement หรือ TMD Songkhla-specific warning เลย (`sources/registry.yaml` ไม่มีแถวสำหรับ `songkhla.tmd.go.th` หรือ ONWR ประกาศเฉพาะกิจ); `docs/T7_T0_DATA_PLAN.md` §1(b) ระบุตรงว่า "TMD 7-day text page ไม่เคยถูกเก็บถาวรรายวัน" เป็นช่องว่างที่ยังไม่ทำ | RELAYED | URL 2 เส้นที่อ้างระบุชื่อ claim ตรง (ONWR 30/2568, ศูนย์อุตุฯ ฝั่งตะวันออก 59/2568) — ไม่ WebFetch (ไม่ใช่ 1 ใน 3 claim ที่ถูกกำหนดไว้ว่า pivotal) |
| 2 | 16–18 พ.ย. — TMD forecast รายวัน 16 พ.ย. + ศูนย์อุตุฯ ฝั่งตะวันออก 18 พ.ย. เตือนฝนหนักถึงหนักมากภาคใต้ฝั่งตะวันออก 17–23 พ.ย. | เหมือนข้อ 1 — ไม่มี archive อิสระของคลังนี้ที่ตรวจย้อนได้ | RELAYED | URL ระบุชัดพอ (TMD daily forecast 161120251200; ศูนย์อุตุฯ PDF 2025-11-18) |
| 3 | 19 พ.ย. — TMD ประกาศเตือนภัยที่ 10 (349/2568) 17:00 น. ยืนยันฝนหนัก/หนักมากต่อเนื่อง | เหมือนข้อ 1-2 | RELAYED | — |
| 4 | 20 พ.ย. — เทศบาลนครหาดใหญ่ แถลงการณ์ฉบับที่ 2 ระบุสถานะปกติ/ธงเขียว ขณะที่คำเตือนระดับภูมิภาคยังรุนแรงต่อเนื่อง | **มีแหล่งที่สองอิสระในคลังนี้เอง**: `docs/knowledge/card_hatyai_city_climate.md` (self-description ของเครือข่าย Hat Yai City Climate, ไม่ใช่แหล่งเดียวกับ red-team) บันทึกรูปแบบเดียวกันตรงๆ — "คืน 21 พ.ย. นายกเทศมนตรียกธงเหลือง 12 ชุมชน (20.30 น.)... **ขณะที่น้ำในอู่ตะเภายังไม่เข้าเกณฑ์ของทีมประเมินจังหวัด**"; และบันทึกบทเรียนตรงว่า "ขาดเอกภาพระหว่างทีมประเมินน้ำของเทศบาลกับของจังหวัด" | **VERIFIED (pattern)**, ไม่ VERIFIED (วันที่ 20 พ.ย. เป๊ะ) | รูปแบบ "ท้องถิ่นยกธงคนละจังหวะกับเกณฑ์ของทีมจังหวัด" ตรงกันระหว่างสองแหล่งอิสระ 2 แหล่ง (municipality statement ผ่าน red-team vs city-climate network self-description) — **นี่คือหลักฐานภาพรวม 2 ช่องทางที่ไม่ใช่ช่องทางเดียว ตามคำสั่ง founder** |
| 5 | 21 พ.ย. — แถลงการณ์ฉบับที่ 3 (เหลือง 12 ชุมชน) แล้วฉบับที่ 4 (แดง **65 ชุมชน**) ในวันเดียวกัน | `card_hatyai_city_climate.md` บันทึกเหลือง 12 ชุมชนตรงกัน (21 พ.ย. 20.30 น.) **แต่ไม่กล่าวถึงธงแดง 65 ชุมชนเลย** — การ์ดกระโดดจากเหลือง 12 ชุมชนตรงไปยังแดง 103 ชุมชน (22 พ.ย. 08.00 น.) โดยตรง | **CONTRADICTED (บางส่วน)** | ความต่างเฉพาะจุด "ธงแดง 65 ชุมชนในวันที่ 21" — แหล่งหนึ่งมี อีกแหล่งไม่มี ไม่ merge/เลือกฝั่งใดฝั่งหนึ่ง บันทึกไว้ตรงๆ ว่าขัดกัน (ตามกฎ `reconcile.py`/AGENTS.md — เก็บทั้งคู่ ไม่ตัดสินแทน) |
| 6 | 22 พ.ย. 08:00 — แถลงการณ์ฉบับที่ 5 ยกธงแดงขยายเป็น 103 ชุมชน | `card_hatyai_city_climate.md` ยืนยันตรงเป๊ะ: "22 พ.ย. 08.00 น." + "103 ชุมชน" | **VERIFIED** (สองแหล่งอิสระตรงกันทุกตัวเลข) | จุดเดียวใน 10 claims ที่ตรงกัน 100% ระหว่างสองแหล่ง |
| 7 | 22 พ.ย. — RID รายงานฝนลุ่มน้ำอู่ตะเภา 351.3 มม./24ชม., คลองหวะ 360, คลองแตน 346, คลองวัด 366; คลอง ร.1 ระบายที่ 1,200 ลบ.ม./วิ | ตัวเลขฝน (346–366 มม.) **ไม่มีแหล่งเทียบอิสระในคลังนี้** (ไม่มี rain gauge history ของลุ่มน้ำอู่ตะเภาเก็บไว้เลย). **แต่ตัวเลข "ร.1 ที่ 1,200 ลบ.ม./วิ" ตรงกับ design capacity ที่คลังนี้บันทึกไว้เองอิสระ**: `sources/coping_thresholds.yaml` แถว `hatyai / design_river_flow_m3s = 1200.0 m3/s` ("คลอง ร.1 … ออกแบบรับฝนรอบ 50 ปี", แหล่ง `case_hatyai_2553_2565.md`) | **RELAYED** (ตัวเลขฝน) / **VERIFIED-consistent** (ตัวเลข ร.1) | **pivotal claim ตามที่ founder กำหนด — ไม่ WebFetch URL** (คำสั่งจำกัดไว้ที่ ≤3 fetch รวม และงานนี้ไม่ fetch เลยเพราะ cross-check ภายในคลังก็เพียงพอ, ดู §"live fetches" ท้ายเอกสาร); ตีความ: ถ้าตัวเลข 1,200 ลบ.ม./วิ ถูกต้อง หมายความว่า ร.1 ถูกใช้งาน**เต็ม design capacity**ระหว่างเหตุการณ์นี้ — สอดคล้องกับสถานการณ์ "เกินขีดความสามารถ" ที่ red-team อ้าง |
| 8 | 24 พ.ย. — ONWR พยากรณ์ยอดน้ำ X.90 = +2.26–2.46 ม. เหนือตลิ่ง (00:00–01:00, 25 พ.ย.), X.44 = +2.00–2.20 ม. เหนือตลิ่ง (06:00–07:00, 25 พ.ย.) | **ตรวจไม่ได้จากข้อมูลของคลังนี้**: (1) `data/observations.sqlite` มี live telemetry จริงของ X.44/X.90/X.173A (`thaiwater_waterlevel`, official_telemetry) แต่เป็นค่าวันนี้ (2026-09-27, ระดับปกติ: X.44≈0.7ม., X.90≈3.0ม., X.173A≈9.8ม. MSL) **ไม่ใช่ข้อมูลย้อนหลัง พ.ย. 2568**; (2) คอลัมน์ `bank`/`critical` ของสามสถานีนี้ในตารางว่างเปล่าทุกแถว — คลังนี้ไม่มีเส้น "ตลิ่ง" ที่ verified ไว้เองสำหรับ X.44/X.90/X.173A เลย จึงเทียบ "+2.0–2.2 ม. เหนือตลิ่ง" ไม่ได้แม้จะมีข้อมูลย้อนหลัง; (3) HII history archive ของคลังนี้ (`raw/backtest/hii_history/X44_2591_2565.json`, `X90_2589_2565.json`) ครอบเฉพาะปี 2565 ไม่ใช่ 2568 | **OPEN** (ทั้ง pivotal claim) | **pivotal claim ตามที่ founder กำหนด** — ตัดสินใจไม่ WebFetch เพราะ (ก) จำกัด ≤3 fetch รวมทั้งงาน (เก็บไว้ให้ claim #9 ถ้าจำเป็น) (ข) แม้ fetch ได้ตัวเลขจริง ก็ยังไม่มี "เส้นตลิ่ง" ที่ verified ในคลังนี้มาเทียบอยู่ดี — การ fetch จะยืนยันแค่ "red-team อ้างตัวเลขนี้จริง" ไม่ใช่ "ตัวเลขนี้ตรงกับความเป็นจริง" |
| 9 | 25 พ.ย. — วิกฤตสูงสุด, ใช้รถ high-clearance/เรือ/ทหาร; ONWR ระบุระดับน้ำลุ่มอู่ตะเภาเกินสถิติ 2553 | ตรวจไม่ได้ — ไม่มีแหล่งอิสระของคลังนี้ครอบเหตุการณ์ 2568 เลย (การ์ดกรณีศึกษาที่มีอยู่ `case_hatyai_2553_2565.md` ครอบเฉพาะปี 2553/2565 **ไม่ครอบปี 2568**) | **OPEN** | ยืนยันด้วยว่า claim นี้ **plausible ในทิศทาง** (2565 เคยทำสถิติเหนือ 2553 ไปแล้ว ตาม `case_hatyai_2553_2565.md`(a): 11.66ม. > 10.25ม.) — ไม่ได้แปลว่า claim ถูก แค่ไม่ขัดกับที่รู้อยู่แล้ว |
| 10 | 27 พ.ย. 06:00 — ONWR รายงาน X.44 = 7.59ม. (ต่ำกว่าค่าสูงสุด 2.38ม., ยังเหนือตลิ่ง 0.19ม.); X.174 = 9.15ม. (ต่ำกว่าค่าสูงสุด 2.67ม., ยังเหนือตลิ่ง 0.27ม.) | ตรวจไม่ได้ — คลังนี้ไม่มีข้อมูล X.44 ช่วง พ.ย. 2568 เลย (มีแค่ 2565 กับวันนี้ 2026-09-27); ไม่มีสถานี X.174 ปรากฏที่ใดในคลังนี้เลย (grep ทั้ง registry/observations = 0 แถว) | **OPEN** | X.174 เป็นสถานีใหม่ที่คลังนี้ไม่เคยรู้จักมาก่อนแม้แต่ในการ backtest ปี 2565 (ที่ใช้ X.44/X.90 เท่านั้น) — บันทึกไว้เป็นช่องว่างเพิ่ม ไม่ใช่แค่ "ตรวจไม่ได้" |

**สรุปนับ**: VERIFIED (pattern/consistent) = 2 (claim #4 pattern, #7 ร.1 number) · VERIFIED เป๊ะทุกตัวเลข = 1 (claim #6) · RELAYED (ไม่มีแหล่งเทียบ) = 5 (claims #1,#2,#3,#7-rain,#9) · CONTRADICTED (บางส่วน) = 1 (claim #5) · OPEN (ตรวจไม่ได้เลย) = 3 (claims #8,#9-partial ทับซ้อนกับ RELAYED,#10) — นับรวมแบบไม่ทับซ้อน: **VERIFIED=1 exact + 2 pattern/consistent, RELAYED=5, CONTRADICTED=1, OPEN=3** ต่อ 10 claims (บาง claim ติดสองแท็ก เพราะมีทั้งส่วนที่ยืนยันได้และส่วนที่ยืนยันไม่ได้ในบรรทัดเดียวกัน — บันทึกไว้ตรงๆ แทนการปัดเป็นแท็กเดียว)

---

## 2. ความสอดคล้องกับภาพรวม (whole-picture consistency)

1. **346–366 มม./24ชม. (RID, ลุ่มน้ำอู่ตะเภา) เทียบกับ crisis_min 203 มม./24ชม. ของคลังนี้**: หน่วยเดียวกัน
   (มม./24ชม.) แต่**คนละบันได/คนละลุ่มน้ำ** — `crisis_min 203 มม./24ชม.` มาจาก `sources/coping_thresholds.yaml`
   แถว `bangkok_east` (สถานีพญาไท, เหตุการณ์ กทม. 2569) ไม่ใช่เกณฑ์ของลุ่มน้ำอู่ตะเภา/หาดใหญ่ — คลังนี้**ไม่มี
   แถว `hatyai / rain_24h_mm` เลยใน `coping_thresholds.yaml`** (มีแค่ `river_flow_m3s` กับ `canal_level_m`
   สำหรับหาดใหญ่) จึงไม่มีเกณฑ์ฝนของหาดใหญ่เองมาเทียบ 346–366 มม. โดยตรง — **นี่คือช่องว่างจริง ไม่ใช่แค่
   "หน่วยต่างกัน"**: เอาตัวเลข BKK ไปเทียบกับหาดใหญ่ตรงๆ จะผิดหลักการเดียวกับที่ `TIER_THRESHOLDS_RATIONALE.md`
   §3.4 เตือนไว้เรื่อง Manning's N vs runoff coefficient ("ห้ามแทนค่าโดยตรง") — บันทึกเป็น **OPEN**:
   ต้องการแถว `hatyai / rain_24h_mm` ของตัวเองใน `coping_thresholds.yaml` ก่อนเทียบได้อย่างมีความหมาย
2. **X.44 +2.0–2.2 ม. เหนือตลิ่ง เทียบกับสถิติพีค 2553/2565**: เทียบตรงไม่ได้ — `case_hatyai_2553_2565.md`
   บันทึก `canal_level_m` แบบ absolute (10.25ม. ปี 2553, 11.66ม. ปี 2565) ที่สถานี "คลองอู่ตะเภา หาดใหญ่"
   ซึ่ง**ไม่ชัดว่าเป็นจุดวัดเดียวกับ X.44** (HII station 2591) หรือคนละจุด/คนละ datum (MSL vs local canal
   reference) — คลังนี้เองยังไม่ reconcile สองระบบนี้ (`CO_FORECAST_PROTOCOL.md` §7 ข้อ 3 บันทึก
   "control level เป็น null ใน PageMap แต่ปรากฏใน StationDetail" เป็นปัญหา cross-endpoint คล้ายกัน) — ไม่มี
   ค่า "ตลิ่ง"/bank ของ X.44 ที่ verified ในคลังนี้เลย (คอลัมน์ `bank` ว่างทุกแถวที่ตรวจ) จึงบอกไม่ได้ว่า
   2568 (สมมติ 2.0–2.2ม.เหนือตลิ่ง) เทียบกับ 2565 (11.66ม. absolute) แล้วรุนแรงกว่าหรือน้อยกว่า — **OPEN**
3. **"พีคผ่านไป 25 พ.ย., ลดลง 2.38ม. ภายใน 27 พ.ย." — ความเป็นไปได้ของการลดระดับลุ่มอู่ตะเภา**: คลังนี้ไม่มี
   discharge/level record ของ U-Tapao ช่วงหลังท่วมที่จะเทียบอัตราการลดระดับได้ (HII archive ของคลังนี้เอง
   ครอบเฉพาะปี 2565: discharge สูงสุดที่วัดได้จริงคือ 168.6 ลบ.ม./วิ **หลังวันท่วมที่รายงาน** ไม่ใช่ระหว่าง —
   ตาม `docs/knowledge/DATA_SWEEP_2026-09-27.md` — เป็น falsifier ต่อการใช้ X.44 เป็นตัวเลขวิกฤตตรงไปตรงมาอยู่แล้ว
   ในปี 2565) — ทิศทาง (ลดลงภายใน 48ชม.) ไม่ขัดกับสามัญสำนึกทางอุทกวิทยาลุ่มน้ำขนาดกลาง แต่**ไม่มีตัวเลขของ
   คลังนี้เองมายืนยันอัตราจริง** — **OPEN, ไม่ใช่การเดา ระบุตรงว่าไม่มีข้อมูลเทียบ**

**ข้อสังเกตที่ต้องพูดตรงๆ**: จุดที่ตรวจสอบได้แน่นอนที่สุด (claims #4, #6) มาจากแหล่งที่สองที่เป็น
**self-description ของเครือข่ายพลเมืองท้องถิ่นเอง** (`card_hatyai_city_climate.md`, RELAYED ทั้งฉบับตาม
tag เดิมของการ์ดนั้น) ไม่ใช่แหล่งราชการอิสระที่สาม — นี่ยังคง**ดีกว่าช่องทางเดียว** ตามคำสั่ง founder (สอง
self-description ที่ต่างที่มา ต่างวันเขียน ยืนยันรูปแบบเดียวกัน มีน้ำหนักมากกว่าไม่มีแหล่งที่สองเลย) แต่
ไม่ควรเรียกว่า "VERIFIED จากบุคคลที่สาม" — เป็น **VERIFIED (pattern, cross-source)** เท่านั้น

---

## 3. แมป 7 ข้อค้นพบเชิงออกแบบเข้ากับสิ่งที่คลังนี้มีอยู่แล้ว

| # | ข้อค้นพบของ red-team | สถานะ | สิ่งที่คลังนี้มีอยู่แล้ว (ไฟล์อ้างอิง) |
|---|---|---|---|
| A | current-vs-forward state ต้องแยกสองแกน | **PARTIAL** | `docs/T7_T0_DATA_PLAN.md` มี "สองนาฬิกา" (`forecast_horizon` vs `action_horizon`) เป็น label ทับ tier L0-L5/LR อยู่แล้ว + PROP-FLOOD-06 v4's `base_tier := max(band_tier, promoter_max)` (`toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md` บรรทัด ~450) ทำให้ promoter ที่มาจาก forecast/upstream (ไม่ใช่ current in-unit reading) เป็น**floor**ที่ current-state ที่สงบกว่าจะดึงลงไม่ได้ — โครงสร้างรองรับ แต่**ไม่มี field ชื่อ `hazard_state`/`current_state` แยกกันตรงๆ**ที่ใดในคลังนี้ (grep ไม่พบ) — เป็นกลไกที่ implicit ใน max() ไม่ใช่ schema ที่ explicit |
| C | re-escalation/hysteresis สำหรับ two-pulse flood | **PARTIAL — SPEC-ONLY** (registered in the PROP-FLOOD-06 v6 proposal; NOT implemented: no `persisted_v6` persistence step in `compute()`, see `ENGINE_VERSION_DELTA_ITEMS` in `tools/backtest/compute_prop_flood_06_sammakorn.py`) | PROP-FLOOD-06 v6's `persisted_v6` — "raise **into** T_L5/T_LR bypasses the p-consecutive-hour requirement... lowering — including a lowering out of T_L5/T_LR — is unchanged: still requires p consecutive lower-tier hours" (`PROP-FLOOD-06.md` บรรทัด 89-93) ตรงกับปัญหา "ระบบที่ de-escalate หลังพีคแรกแล้วพังพีคสอง" ที่ red-team ยกมา ตรงๆ **ในระดับ proposal เท่านั้น ยังไม่มีในโค้ดจริง**; เสริมด้วย `upstream_rise_rate` promoter (v5, บรรทัด 271-297, ของจริงที่ implement แล้ว) ซึ่งเป็นแนวคิด "leading upstream rise" ที่ red-team เสนอเอง — a safety fix 2026-10-02 defect 2 |
| H | OUTSIDE_CALIBRATED_RANGE state สำหรับฝน/น้ำเกินช่วงที่เคยเจอ | **PARTIAL** | มี `L5` (เกินระบบแล้ว) และ `LR` (refused) แต่ไม่มี state ที่แปลว่า "เกินทุกช่วงที่เคย calibrate มา โดยเฉพาะ" แยกจาก `L5` — `TIER_THRESHOLDS_RATIONALE.md` §4 ข้อ 1 มี promoter ใกล้เคียง (`RAIN_24H_EXCEEDS_BMA_DESIGN`, ฝน>80มม.→ floor L3) แต่ผูกกับ **design capacity ของ กทม.** เท่านั้น ไม่ใช่ "เกินทุกค่าที่เคยสังเกตมา" เชิงสถิติของหน่วยนั้นๆ — ยังไม่มี mechanism เทียบค่าปัจจุบันกับ max ที่เคยบันทึกใน `coping_thresholds.yaml` ของหน่วยเดียวกัน |
| D | catchment DAG (X.173A→X.90→X.44 + คลองแตน/คลองวัด/ร.1) | **GAP (ยืนยันด้วยการ query จริง)** | `docs/knowledge/water_system_dag.mmd` (240 nodes, ครอบทั้งประเทศ) — grep "hatyai\|utapao\|songkhla" = **0 hits**; `docs/knowledge/DWR_SUBBASIN.md` (edge `IN_SUBBASIN`, 359 sub-basin nodes) มีคำว่า "หาดใหญ่/สงขลา" แค่ 2 hits (บริบทเป็นการยกตัวอย่างทั่วไป ไม่ใช่ node จริงของลุ่มน้ำอู่ตะเภา) — **ลุ่มน้ำอู่ตะเภาไม่มีอยู่ในกราฟ KG ของคลังนี้เลย ไม่มี node/edge สักเส้น** แม้จะมี live telemetry จริงของ X.44/X.90/X.173A ใน `sources/registry.yaml`/`observations.sqlite` แล้วก็ตาม — ข้อมูลดิบมีก่อนกราฟ ยังไม่เชื่อมกัน |
| E | multimodal edge state (normal→high-clearance→boat→blocked) | **GAP** | ไม่พบ schema นี้ที่ใดในคลังนี้ (route/edge schema ปัจจุบันเท่าที่ค้นเจอเป็น open/closed แบบไบนารีจากเอกสาร Community DAG ที่ยังไม่ merge) |
| F | safe-node = access∩power∩backup∩water∩comms∩capacity∩services | **PARTIAL** | `docs/knowledge/card_hatyai_city_climate.md` (f)-3 มีบทเรียนตรง ("แยกระบบไฟฟ้าจากที่สูบน้ำ… ไฟฟ้าสำรอง/ไฟแยกของสถานีสูบ") ที่แปลงเป็นข้อ (f)-3 ของสัมมากรแล้วในการ์ดเดียวกัน; `docs/knowledge/FOUNDER_TASKS_2026-09-27.md`'s Community Self-Help DAG TODOLIST (unmerged, origin/main) มีแถว #6 "vulnerable flag + priority ladder" และ #8 "skills registry / standing fund" ที่ใกล้เคียงแต่**ยังไม่ครบทั้ง 7 มิติ**ที่ red-team ระบุ (ไม่มี field ไฟฟ้า/น้ำ/สื่อสาร/capacity คงเหลือแยกช่องชัดเจนใน schema ที่อ่านเจอ) |
| G/I | dynamic freshness (function ของ rate/rain/upstream/edge/mode) + throughput/capacity routing | **GAP** | Community DAG TODOLIST (11 แถวเดิม, `FOUNDER_TASKS_2026-09-27.md`) ไม่มีแถวใดพูดถึง dynamic freshness window หรือ throughput-aware routing เลย — เป็นแนวคิดใหม่จริงที่ไม่มีร่างในคลังนี้ ณ ตอนนี้ |

---

## 3b. Contradiction → Action policy (เพิ่มตามคำสั่ง follow-up ของผู้ก่อตั้ง)

**Claim ของ agent อีกตัว (follow-up)**: สถาปัตยกรรม trust_tier + preserve-disagreement +
contradictions ของคลังนี้ "already does" การเก็บความขัดแย้งเป็น first-class แล้ว — Hat Yai 20 พ.ย. 2568
(ธงเขียวท้องถิ่น vs คำเตือนรุนแรงระดับภูมิภาค) ไม่ใช่จุดอ่อนใหม่ แต่**ยืนยัน**สถาปัตยกรรมเดิม — ช่องว่างจริง
คือ "contradiction → action policy"

**ตรวจสอบบนกิ่ง (branch) ของงานนี้เอง ไม่ใช่แค่ origin/main**: `docs/DATA_SYSTEM.md` **มีอยู่จริงบน
`feat/redesign-v2` เช่นกัน** และเป็น**เวอร์ชันที่ครอบคลุมกว่า** origin/main ด้วยซ้ำ (`git diff` พบว่า
กิ่งนี้เพิ่ม trust_tier แถวใหม่: `thaiwater_waterlevel`, `hii_dam`, `hii_watergate`, `rid_res_table`,
`egat_water_crisis` เข้า `official_telemetry`/`official_report`, และเพิ่ม `third_party` tier ให้
Open-Meteo/NASA POWER ที่ origin/main ยังไม่มี) — **claim ที่ว่า trust_tier + contradictions มีอยู่จริง
เป็น VERIFIED บนกิ่งนี้เอง ไม่ใช่แค่ relay จาก origin/main**

| องค์ประกอบที่ agent อีกตัวเสนอ | สถานะ | หลักฐาน |
|---|---|---|
| Multiple sources → trust_tier → preserve disagreement → contradictions (first-class) | **ALREADY COVERED** | `docs/DATA_SYSTEM.md` (VERIFIED บนกิ่งนี้ตามข้างบน) + `CO_FORECAST_PROTOCOL.md` §2(b) (`tools/reconcile.py`: `DISAGREE_MINUTES=60`/`DISAGREE_LEVEL_M=0.05` → เขียนแถว `contradictions`, append-only, ไม่เคย merge/เลือกข้าง) |
| "ข้อมูลเพิ่มไม่เคยลดระดับ" (more data never lowers tier) | **ALREADY COVERED for v4** (`full_tier_v4_promoter_monotone`) — the v6 extension (`full_tier_v6_promoter_monotone`) is **SPEC-ONLY, not implemented** in this repo's code, same as the L5/LR hysteresis-bypass row below | v4: MEASURED by `tests/test_prop_flood_06_sammakorn.py::test_removing_a_present_input_never_raises_the_tier` against real inputs (contrapositive: taking a present input away never raises the tier). v6's wider "**any rank-increasing change to `cov6(U)`** — in particular `inferred → present` — **never lowers the reported tier**" claim is the proposal's own statement, not yet backed by code in this repo. |
| forecast-72h / leading-upstream-rise promoters | **ALREADY COVERED** | v5's `upstream_rise_rate`/`basin_rain_accum`/`forecast_rain_72h` promoter table (`PROP-FLOOD-06.md` บรรทัด 271-309) — ทั้งสามเป็น "ตัวที่สาม" ที่ promote tier ขึ้นเท่านั้น (ไม่เคยลด) ผ่าน `promoter_max` floor เดียวกัน |
| L5/LR hysteresis bypass | **PARTIAL — SPEC-ONLY** (registered in the PROP-FLOOD-06 v6 proposal; NOT implemented: no persistence step in `compute()`, see `ENGINE_VERSION_DELTA_ITEMS` in `tools/backtest/compute_prop_flood_06_sammakorn.py`) | `persisted_v6`: ขึ้นเข้า L5/LR ทันที (ไม่รอ p ชั่วโมง), ลงออกจาก L5/LR ยังต้องรอ p ชั่วโมงเหมือนเดิม (`PROP-FLOOD-06.md` บรรทัด 89-99) — **proposal doc เท่านั้น ยังไม่มีในโค้ด** — a safety fix 2026-10-02 defect 2 |
| T7→T0 action labels (PREPARE/READY/ACTIVATE/EARLY MOVE/RESPONSE) | **ALREADY COVERED** | `docs/T7_T0_DATA_PLAN.md` หัวข้อ "สองนาฬิกา" — ตารางแมป label ↔ tier ตรงเป๊ะ 5 แถว |
| **formal policy object `C(t) → Action`** (รับ contradiction rows เป็น input โดยตรง แล้ว output action) | **GAP จริง** | `tools/reconcile.py` เขียนแถว `contradictions` เพื่อให้**ผู้อ่านตัดสินใจเอง** (`CO_FORECAST_PROTOCOL.md` §2(b): "burden ledger... ไม่ใช่หน้าที่ของ reconcile.py ที่จะตัดสิน") — PROP-FLOOD-06's tier engine **ไม่เคยอ่านแถว `contradictions` เป็น input** เลย ทั้งสองระบบทำงานคู่ขนานกัน ไม่เชื่อมกัน — นี่คือช่องว่างที่ agent อีกตัวชี้ถูก: ไม่มีวัตถุที่รับ "สองแหล่งขัดกัน" แล้วคำนวณ action โดยตรง (ปัจจุบันต้องอาศัยกลไกอ้อม: promoter ที่มาจาก forecast/upstream ชนะ current-state ที่สงบกว่าอยู่แล้วผ่าน `max()` — **ใช้ได้บางกรณี แต่ไม่ใช่ policy object ที่ประกาศ contradiction-awareness ตรงๆ**) |

**คำถามของ follow-up**: "ตัวอย่าง 20 พ.ย. เขียว-vs-เตือนรุนแรง เข้าข่ายกฎเดิมที่ว่า 'ค่าที่ tier ต่ำกว่าไม่เคย
ลด tier ที่ active อยู่แล้ว' หรือไม่ — ตอบจากข้อความ v6.1 พร้อมอ้างไฟล์"

**คำตอบ**: **ใช่ โดยโครงสร้าง แต่ยังไม่เคยถูกทดสอบกับกรณีนี้จริง**. กลไกที่ตรงที่สุดคือ v4's
`base_tier := max(band_tier, promoter_max)` (`PROP-FLOOD-06.md` บรรทัด 450, "FULL's ledger tier and
the promoter floor are..." — max ไม่ใช่ min) — ถ้า promoter ที่อิง forecast/upstream ยิง (`FORECAST_RAIN_72H_EXCEEDS`
→ floor L1, `BASIN_RAIN_ACCUM_EXCEEDS` → floor L2, `UPSTREAM_RISE_RATE_EXCEEDS` → floor L3, บรรทัด
297-302) ค่า `band_tier` ที่มาจากการอ่านสถานะปัจจุบันที่สงบกว่า (คล้ายธงเขียวของเทศบาล) **ไม่มีทางดึง
`base_tier` ลงต่ำกว่า `promoter_max` ได้** เพราะเป็น max() ไม่ใช่ average — ตรงกับหลักการที่ v6.1
"no S_H/T_act/promoter/p/q threshold VALUE is changed... " ยืนยันซ้ำว่ากลไกนี้ยังคงอยู่ไม่เปลี่ยน
(`PROP-FLOOD-06.md` บรรทัด 65). **ข้อจำกัดที่ต้องบันทึกตรงๆ**: กลไกนี้พิสูจน์ในระดับ**คณิตศาสตร์ของสูตร**
(Coq) เท่านั้น — หาดใหญ่/ลุ่มน้ำอู่ตะเภา**ไม่เคยถูกคำนวณเป็น unit จริงในกราฟ/engine ของคลังนี้เลย** (§3
ข้อ D ข้างบน: 0 node ในกราฟ) จึงไม่เคยมีการรันสูตรนี้จริงกับข้อมูลหาดใหญ่ 2568 — เป็น**การยืนยันเชิง
โครงสร้างที่ยังไม่ผ่านการทดสอบกับกรณีนี้โดยเฉพาะ** ไม่ใช่ทั้งสองอย่าง (ทั้ง covered และยังไม่ทดสอบ อยู่พร้อมกัน)

**TODOLIST row สำหรับช่องว่างจริง** (ดู §4 แถว #12 ด้านล่าง) — เขียนตามคำสั่งตรง: ห้าม derive สมการเอง
ในไฟล์นี้ ให้เขียนเป็น candidate `PROP-FLOOD-08` เท่านั้น

---

## 4. TODOLIST (ต่อจากตาราง 11 แถวเดิมใน `FOUNDER_TASKS_2026-09-27.md`)

| # | Mismatch | Fix | Owner | Prio |
|---|---|---|---|---|
| 12 | ไม่มี formal policy object รับ `contradictions` rows เป็น input แล้ว output action โดยตรง (§3b) | เสนอ candidate `PROP-FLOOD-08`, **Toledo-first**: ต้องขึ้นทะเบียนก่อนโค้ดใดใช้งาน; จนกว่าจะขึ้นทะเบียน ให้ทำเครื่องหมาย "not yet in Toledo" ในโค้ด/เอกสารทุกจุดที่พูดถึง — **ห้าม derive สมการเองในงานนี้หรืองานถัดไปก่อนขึ้นทะเบียน** | founder+committer | high |
| 13 | ลุ่มน้ำอู่ตะเภา/หาดใหญ่ไม่มี node/edge เลยใน `water_system_dag.mmd` (0 hits ยืนยันด้วย grep) แม้มี live telemetry จริงของ X.44/X.90/X.173A ใน registry แล้ว | เพิ่ม sub-basin + station node ของลุ่มน้ำอู่ตะเภา (X.173A→X.90→X.44 + คลองแตน/คลองวัด/ร.1) เข้า KG ตาม `DWR_SUBBASIN.md`'s `IN_SUBBASIN` pattern เดิม — **X.90/X.173A ในฐานะ upstream leading gauge ยังเป็น OPEN ใน PROP-FLOOD-06 v5 เอง** (`toledo-wt-flood06/.../PROP-FLOOD-06.md`: "X.90 confirmed present but used only as a downstream control station... its suitability as an upstream leading gauge is itself OPEN, not assumed; X.173 unconfirmed") — ต้อง**ยืนยันสถานะนี้ก่อน**ไม่ใช่สมมติว่า X.90/X.173A ใช้เป็น leading gauge ได้ตรงๆ ตามที่ red-team เสนอ | committer | high |
| 14 | ไม่มีการ์ดกรณีศึกษาของเหตุการณ์ พ.ย. 2568 (2025) เอง — การ์ดที่มีอยู่ (`case_hatyai_2553_2565.md`) ครอบเฉพาะ 2553/2565 | เพิ่มการ์ด `case_hatyai_2568.md` (RELAYED) สังเคราะห์จาก red-team + แหล่งอิสระเพิ่มเติม (เช่น `card_hatyai_city_climate.md` paper/640 ที่ครอบเหตุการณ์นี้อยู่แล้วบางส่วน) — แก้ contradiction claim #5 (ธงแดง 65 ชุมชน) ให้ตรงด้วยการอ่านแหล่งเพิ่ม ไม่ใช่เดา | committer | medium |
| 15 | ไม่มีแถว `hatyai / rain_24h_mm` ใน `coping_thresholds.yaml` — เทียบ 346-366มม./24ชม.ของเหตุการณ์นี้ไม่ได้กับเกณฑ์ของหน่วยเดียวกันเอง (ใช้ BKK 203มม. เทียบข้ามลุ่มน้ำผิดหลักการ) | เพิ่มแถว `hatyai / rain_24h_mm` (flooded_min/coped_max) เมื่อมีแหล่งปฐมภูมิยืนยันตัวเลขฝน 2568/2565 ได้จริง | committer | medium |
| 16 | ไม่มีเส้น `bank`/`critical` ที่ verified สำหรับ X.44/X.90/X.173A ใน `observations.sqlite` (คอลัมน์ว่างทุกแถว) — เทียบ "เหนือตลิ่ง" จาก red-team ไม่ได้เลย | หาเอกสารทางการระบุเส้นตลิ่ง/วิกฤตของสามสถานีนี้ (RID เขต 8 หรือเทศบาลนครหาดใหญ่) แล้วเติมเป็นค่า MEASURED ใน registry — ห้ามเดา/derive เอง | committer | medium |
| 17 | Multimodal edge state (normal/high-clearance/boat/blocked) และ dynamic freshness window ไม่มี schema ใดๆ ในคลังนี้เลย | ออกแบบ field ใหม่ต่อ route/edge (mode-state enum + freshness ผูก rate-of-change) — ตรวจสอบ Toledo status ก่อนถ้ามีสูตรคำนวณเข้ามาเกี่ยวข้อง (ตาม §3b เดียวกัน) | committer | medium |
| 18 | safe-node schema ยังไม่ครบ 7 มิติ (access/power/backup/water/comms/capacity/services) ตามที่ red-team เสนอ — มีแค่ (f)-3 บทเรียนไฟฟ้าสำรองในการ์ด ไม่มี field จริงใน Community DAG schema | เพิ่ม field ต่อ safe-node ใน `docs/COMMUNITY_SELF_HELP_DAG.md` schema (รอ D2 merge ตาม `FOUNDER_TASKS_2026-09-27.md` อยู่แล้ว) — รวมเข้ากับ TODOLIST เดิมแถว #6 ไม่ใช่แถวใหม่แยก | committer | medium |

---

## 5. ความซื่อสัตย์ (honesty section)

- **สิ่งที่ red-team ทดสอบไม่ได้เอง (ตามที่ไฟล์ต้นทางประกาศไว้)**: red-team ประกาศตัวเองตรงๆ ว่า "This is
  an evidence replay... **not** a reconstructed hydraulic simulation and does not invent water depth
  or travel time" — คือไม่ทดสอบ route-by-route/hydraulic propagation จริง เป็นแค่ evidence-timeline replay
- **คลังนี้ทดสอบแบบ route-by-route ได้หรือไม่**: **ไม่ได้เช่นกัน** — และแย่กว่านั้นคือ**ทดสอบ route-by-route
  ของหาดใหญ่ไม่ได้เลยแม้แต่แบบง่ายที่สุด**เพราะไม่มี node/edge ของลุ่มน้ำอู่ตะเภาในกราฟเลย (§3 แถว D) —
  ทั้งสองฝ่าย "ไม่ได้ทดสอบ" แต่ด้วยเหตุผลคนละระดับ: red-team เลือกไม่ทำ (by design, มีข้อมูลพอจะลองระดับหนึ่ง),
  คลังนี้**ทำไม่ได้**เพราะไม่มีโครงสร้างข้อมูลตั้งต้นด้วยซ้ำ — ต้องพูดตรงๆ ว่าช่องว่างของเราหนักกว่า
- **ตรวจสอบ claim "Simulation: NO" ของไฟล์ต้นทาง**: **VERIFIED ว่าคำกล่าวนี้เป็นจริงตามที่อ่านได้** — อ่าน
  ไฟล์ทั้งฉบับ (296 บรรทัด) แล้ว ทุกตัวเลข (ปริมาณฝน, ระดับน้ำ, จำนวนชุมชน, วันที่) มี URL แหล่งราชการกำกับ
  รายบรรทัด ไม่มีจุดใดที่ไฟล์คำนวณ/ประมาณค่าที่ไม่มา จาก source ที่อ้างแล้วนำเสนอเป็นค่าที่วัดได้ — ส่วนที่เป็น
  การตีความ/ข้อเสนอ (หัวข้อ "What the real replay says" เป็นต้นไป) ถูกแยกชั้นชัดเจนจากไทม์ไลน์แหล่งข่าว
  ไม่ปนกัน — **ไม่พบตัวเลขจำลอง (simulated number) ปลอมปนใดในไฟล์นี้**

---

## Live fetches ที่ทำในงานนี้

**0 ครั้ง**. แม้มี 2 claim ที่ founder ระบุไว้ว่า pivotal (22 พ.ย. RID rain, 24 พ.ย. crest forecast) แต่
เมื่อตรวจสอบพบว่า (1) ตัวเลข ร.1 1,200 ลบ.ม./วิ ของ claim แรกยืนยันได้อยู่แล้วจากแหล่งภายในคลังนี้เอง
(`sources/coping_thresholds.yaml`) โดยไม่ต้อง fetch, และ (2) claim ที่สอง (X.44/X.90 เหนือตลิ่ง) ตรวจไม่ได้
อยู่ดีแม้ fetch สำเร็จ เพราะคลังนี้ไม่มีเส้น "ตลิ่ง" ที่ verified ของสองสถานีนี้มาเทียบ (§1 claim #8) — การ
fetch จะยืนยันได้แค่ "ข้อความนี้มีอยู่จริงบนเว็บ ONWR/ปชส." ไม่ใช่ "ตัวเลขนี้ตรงกับความเป็นจริง" ซึ่งไม่ใช่
สิ่งที่ founder ขอให้ยืนยัน (ขอ cross-check กับภาพรวมของคลังนี้ ไม่ใช่ตรวจสอบว่า URL มีจริง) — บันทึกการ
ตัดสินใจนี้ตรงๆ แทนการ fetch แบบพิธีกรรม

---

*ไฟล์นี้เป็นการสังเคราะห์ (synthesis) + cross-check จากไฟล์ที่มีอยู่แล้วในคลังนี้ (read-only) กับไฟล์
third-party AI สองไฟล์ที่ founder ส่งต่อมา — ไม่ใช่แหล่งปฐมภูมิใหม่ ไม่แก้ไฟล์อื่นใดในคลังนี้*
