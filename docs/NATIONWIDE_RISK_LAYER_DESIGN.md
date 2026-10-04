# แผนที่ความเสี่ยงน้ำท่วมทั้งประเทศ — ออกแบบ (รายลุ่มน้ำสาขา DWR, 359 หน่วย)

**คำถามผู้ก่อตั้ง (verbatim, 2026-09-27)**: "ทำไงเราถึงจะประเมินแบบ Google ได้นะ"

ไฟล์นี้เป็นการออกแบบ+ต้นแบบ (prototype) — **ไม่ได้ผูกเข้ากับ `site/build_data.py`/`build_page.py` จริง**
(อีก worker เป็นผู้ commit และผู้ตัดสินใจว่าจะ wire อย่างไร) โมดูลที่อ้างถึง (`tools/riskmap/`)
ยิง **ศูนย์คำขอ network ใหม่** — ใช้เฉพาะข้อมูลที่มีอยู่แล้วใน `data/observations.sqlite`,
`sources/dwr_subbasins.yaml`, `sources/coping_thresholds.yaml`, `sources/capacity_ledger*.yaml`

Toledo: ไม่มีสมการใหม่ในไฟล์นี้หรือใน `tools/riskmap/`. Tier ทุกจุดเป็น **PARTIAL mode เสมอ**
(ไม่เคยอ้าง FULL) — ใช้ language เดียวกับ `PROP-FLOOD-06 v6.1 PARTIAL` (mode/coverage/promoters)
และ `docs/LAYER0_IN_OUT_CAPACITY.md` (simplification ที่มีอยู่แล้ว, ไม่ใช่สมการใหม่)

---

## 1. Google Flood Hub ทำอะไร เราทำอะไร

ดูรายละเอียดเต็มที่ `docs/knowledge/card_thirdparty_google_flood_hub_2026-09-27.md`
(การ์ดแยกต่างหาก, MEASURED จากสกรีนช็อต + RELAYED-general สำหรับวิธีการของ Google)

สรุปสั้น — **ช่องว่างที่ซื่อสัตย์**:

| | Google Flood Hub | คลังนี้ (nationwide risk layer) |
|---|---|---|
| หน่วยวิเคราะห์ | virtual/real gauge ต่อจุด (ทั่วโลก) | DWR sub-basin polygon จริง 359 หน่วย |
| ประชากร/พื้นที่กระทบ | มี (ML overlay กับชั้นประชากร) | **ไม่มี** — ไม่มีชั้นข้อมูลประชากรใดๆ ในคลังนี้ (ดู §5) |
| พื้นที่น้ำท่วมจริง (inundation) | มี | **ไม่มี** — ไม่มีโมเดล inundation |
| Return-period risk 4 ชั้น ทุกจุด | มี | **มีบางส่วน** — เฉพาะหน่วยที่มี `sources/coping_thresholds.yaml` (ปัจจุบัน 6 หน่วยที่ตั้งชื่อไว้: bangkok_east, sammakorn, chao_phraya_bkk_reach, nan_town, chiangmai_town, hatyai) |
| Sensor-consistency guard | ไม่ทราบวิธีการภายในของ Google | **มี** — ปฏิเสธค่าที่ขัดกับทิศทางการไหล/เพื่อนบ้านก่อนใช้เป็นฐาน tier (§4) |

## 2. วิธีคำนวณต่อสับเบซิน (`tools/riskmap/subbasin_risk.py`)

ต่อหนึ่ง sb_code (359 หน่วย, `sources/dwr_subbasins.yaml`):

1. **แถบสถานะเกจ (a)**: จับคู่สถานี `thaiwater_waterlevel`/`thaiwater_canal_waterlevel` เข้ากับ
   polygon จริงด้วย `tools/kg/unit_resolver.py` (point-in-polygon, VERIFIED engine) — นับจำนวน
   สถานีที่ ≥warning/≥critical/≥bank **ก็ต่อเมื่อ**คอลัมน์ threshold ไม่ใช่ NULL (ปัจจุบัน: **ทุกแถวของ
   `thaiwater_waterlevel` ใน DB นี้มี warning/critical/bank เป็น NULL** — จำนวนสถานีเป็นของจริง
   แต่แถบสถานะเป็น **ไม่มีข้อมูลจริง / absent** ทั่วประเทศ ณ ตอนที่เขียนไฟล์นี้)
2. **พยากรณ์แม่น้ำ (b)**: ใช้เฉพาะ 3 จุด GloFAS-via-Open-Meteo ที่มีอยู่แล้วในคลัง
   (`chaophraya_dam`, `nakhonsawan`, `sammakorn` — ทั้ง 3 ตกอยู่ใน sb_code เดียวกัน `1002`
   เพราะ DWR แบ่งที่ราบเจ้าพระยาตอนล่างเป็น polygon เดียวขนาด 15,688 ตร.กม.) เทียบกับ
   `sources/coping_thresholds.yaml`'s `derived` block (flooded_min/coped_max ที่มีอยู่แล้ว)
   — **ผ่านการ์ดความสอดคล้อง (§4) ก่อนเสมอ**
3. **ฝน (c)**: max ค่าจริง 24 ชม. จาก `thaiwater_rain_24h` ที่ resolve เข้าสับเบซิน + พยากรณ์
   per-model จาก `openmeteo_forecast16d` (ไม่เฉลี่ยข้ามโมเดล ตามกติกาเดิมของ
   `FORECAST_7DAY_SOURCES.md`) — มีเฉพาะ 8 จุดที่มี per-model forecast ในคลัง
4. **เขื่อน (d)**: `hii_dam` ที่ resolve เข้าสับเบซิน (storage%/release) — ส่วนใหญ่เป็นเขื่อนขนาดกลาง/เล็ก,
   `storage_pct` เป็น null บ่อยครั้ง (ไม่มีข้อมูลจริง / absent, ไม่ใช่ 0)
5. **Tier**: max ของทุกองค์ประกอบที่**มีเกณฑ์เทียบจริง**เท่านั้น (ไม่มีเลขมั่ว/threshold ที่คิดขึ้นเอง) —
   `coverage = n/10` (นับว่ากี่ใน 10 ช่องของ checklist ด้านล่างมีข้อมูลจริง), `mode = PARTIAL` เสมอ
6. **ประชากร**: `None` เสมอ — ดู §5

**10 ช่อง coverage** (checklist, ไม่ใช่สมการ): gauge_waterlevel_present, gauge_status_known,
canal_level_present, river_forecast_present, river_history_percentile_present, rain_24h_present,
rain_forecast_present, dam_present, coping_threshold_known, capacity_ledger_known.

## 3. ครอบคลุมทั้ง 359 หน่วยอย่างไร (แผนงาน, ยังไม่ทำในงานนี้)

- **เกจ/ฝน/เขื่อน**: point-in-polygon กับสถานีที่มีอยู่แล้วครอบคลุมทุกสับเบซินที่มีสถานีจริงอยู่แล้ว
  **โดยไม่ต้องยิง network เพิ่ม** — งานต่อไปแค่รัน `resolve_points_to_subbasins()` แบบเต็มประเทศ
  (ไม่จำกัด bbox กลาง) แล้ว cache ผล ครั้งเดียวต่อการรัน
- **พยากรณ์แม่น้ำ (GloFAS)**: ต้องมีจุด mainstem ต่อสับเบซิน — **งบต่อรัน ≤10 คำขอ** (ตามกติกา
  founder งานนี้) หมายความว่าครบ 359 หน่วยต้องใช้ **≥36 รัน** ถ้าทำ 10 หน่วยต่อรัน — เสนอ:
  จัดคิวตามลำดับความสำคัญ (ลุ่มน้ำเจ้าพระยา/ท่าจีน/บางปะกง/แม่กลอง/ป่าสักก่อน เพราะมีประชากร/
  โครงสร้างพื้นฐานหนาแน่นที่สุด — ดู `sources/dwr_subbasins.yaml`'s `area_sqkm` + `basin_name_th`
  จัดลำดับ), เก็บ cursor แบบเดียวกับ `bma_station_detail_cursor.json` ที่มีอยู่แล้วในคลัง (rotate
  ผ่านทุกหน่วยข้าม runs, ไม่ยิงซ้ำจุดเดิมในรันเดียวกัน)
- **Return-period threshold**: ต้องมี HII history หรือประวัติศาสตร์ยืนยันได้ต่อหน่วย — ปัจจุบันมีแค่
  6 หน่วยที่ตั้งชื่อใน `coping_thresholds.yaml` — งานต่อไป (ไม่ใช่ของ worker นี้) คือขยายไฟล์นั้นทีละ
  หน่วยเมื่อมีเหตุการณ์/แหล่งใหม่ (ไม่ใช่ fetch อัตโนมัติ)
- **ประชากร**: ต้องดาวน์โหลด raster ครั้งเดียว (WorldPop 100m หรือ GHSL) + zonal-stats กับ 359
  polygon — เป็นงาน offline แยกต่างหาก ไม่ใช่ collector รายวัน

## 4. Sensor/flow-consistency guard (project decision 2026-09-27, verbatim)

> "อย่าเชื่อเซนเซอร์มาก ต้องดูความสอดคล้องโดยรวมของสมการการไหลด้วย … ตรงคลองแสนแสบเสรีไทยก็มีค่า
> แปลกๆ ไม่สอดคล้องกับเพื่อนบ้าน"

`tools/riskmap/subbasin_risk.py`'s `flow_consistency_flag()` เป็น**การตรวจทิศทาง**เท่านั้น (ไม่มี
สมการใหม่ — อ้างอิงทิศทางของ PROP-FLOOD-04 "ทิศทางจากผลต่าง head" และงบน้ำของ PROP-FLOOD-03
เชิงคุณภาพ, **ไม่ได้ implement สองสมการนั้น**): ถ้า reach หนึ่งมีแต่โครงสร้างประเภท `diversion`
(ดึงน้ำออกเท่านั้น) ระหว่างจุดต้นน้ำ-ปลายน้ำ ปลายน้ำต้องไหลน้อยกว่าหรือเท่าต้นน้ำเสมอ (บวกการระบาย
จากเขื่อนที่วัดได้จริงถ้ามี) — ถ้าปลายน้ำ**สูงกว่า**ต้นน้ำเกินกว่าการระบายที่วัดได้ ให้ตั้ง
`SUSPECT`, **ไม่ใช้เป็นฐาน tier**, **ไม่เติมเลขทดแทน**, และนับช่องนั้นเป็น absent ใน coverage vector

**กรณีจริงที่พบในงานนี้**: จุด `chaophraya_dam` (proxy สำหรับ C.13 ท้ายเขื่อนเจ้าพระยา ชัยนาท,
GloFAS-via-Open-Meteo) พยากรณ์ discharge สูงกว่าจุด `nakhonsawan` (proxy C.2 นครสวรรค์, ต้นน้ำ)
อยู่ **1,479–2,282 ลบ.ม./วินาที ทุกวัน**ใน 7 วันข้างหน้า — มากกว่าการระบายรวมที่วัดได้จริงของ
เขื่อนภูมิพล+สิรินธรตอนนี้ (6.13 ลบ.ม./วิ) มาก และทุกทางเบี่ยงน้ำระหว่าง C.2-C.13 ใน
`sources/capacity_ledger.yaml` เป็น `kind: diversion` (ดึงออกเท่านั้น, capacity_value เป็น OPEN
ทุกแถว) — **ไม่มีกลไกที่บันทึกไว้จะเพิ่มน้ำขนาดนี้ได้** → ตั้ง `SUSPECT`, ตัด tier ที่ดูเหมือนจะเป็น L4
ออก, บันทึกเป็นหลักฐานดิบไว้ (ไม่ลบ) ใน `raw/forecast_tests/2026-09-27T131216Z_1002.json`

**ข้อจำกัดของ guard นี้**: เทียบแค่ 1 คู่ต้นน้ำ-ปลายน้ำที่มีอยู่จริงในคลัง (`chaophraya_dam` vs
`nakhonsawan`) — ยังไม่ใช่ `neighbour_consistency_check()` แบบเต็ม (ของ `site/build_data.py`,
ออกแบบมาสำหรับสถานีคลองที่มี `order` ประกาศไว้ เช่น กรณี WL.SSB.08 แสนแสบ-เสรีไทย) เพราะ
สับเบซินระดับประเทศส่วนใหญ่ไม่มีคู่ต้นน้ำ-ปลายน้ำที่ archived พร้อมกัน — งานต่อไปควรขยาย guard นี้
ให้ใช้ `site/build_data.py`'s ฟังก์ชันเดิมโดยตรงเมื่อมีลำดับสถานีที่ประกาศไว้ (`order` list)

## 5. ประชากร — WorldPop/GHSL (census-only, ไม่ได้ fetch งานนี้)

คลังนี้ไม่มีชั้นข้อมูลประชากรใดๆ ทั้งสิ้น — สองแหล่งฟรีไม่ต้อง key ที่เหมาะสม:

- **WorldPop** (worldpop.org) — raster 100m ต่อประเทศ, ปรับปีได้, ฟรี ไม่ต้อง key
- **GHSL — Global Human Settlement Layer** (ghsl.jrc.ec.europa.eu) — raster ความละเอียดหลายระดับ
  ทั่วโลก, ฟรี ไม่ต้อง key

ทั้งสองต้องการ **ดาวน์โหลด raster ครั้งเดียว + zonal-stats กับ 359 polygon** (ไม่ใช่ collector
รายชั่วโมง/วัน) — OPEN, ไม่ได้ทำในงานนี้

## 6. ทดสอบพยากรณ์ล่วงหน้า (project decision 2026-09-27: "ทดลองหาพื้นที่เสี่ยงมากที่สุดในภาคกลางตอนนี้
แล้วลองทดสอบพยากรณ์" + "ทดสอบข้อมูลจริงไม่จำลอง ทดสอบใหม่")

**ข้อมูลจริงทั้งหมด ไม่มีการจำลอง** — ทุกตัวเลขในหัวข้อนี้มาจากแถวจริงใน `data/observations.sqlite`
หรือไฟล์จริงใน `sources/`, อ้างชื่อแหล่ง+เวลาต่อค่า ดู `raw/forecast_tests/2026-09-27T131216Z_1002.json`
(บันทึก append-only, ไม่แก้ไขภายหลัง — การแก้ไขคือบันทึกใหม่ที่มีวันที่ใหม่)

### วิธีจัดอันดับ

จำกัดเฉพาะสับเบซินภาคกลาง (ที่ราบเจ้าพระยา, ท่าจีน, ป่าสัก, บางปะกง, แม่กลอง — centroid อยู่ในกรอบ
13.0–16.5°N, 99.0–101.8°E ตามที่ผู้ก่อตั้งกำหนด) — ประเมินจริง **43 สับเบซิน** จาก 359 หน่วย
(สับเบซินอื่นในกรอบพิกัดเดียวกันแต่ไม่ใช่ลุ่มน้ำที่ระบุ เช่น มูล/ชี ถูกตัดออก) จัดอันดับตาม
(tier ก่อน, coverage รองลงมา) — **ผลจริง: ไม่มีสับเบซินใดยืนยัน tier สูงกว่า L0** หลังผ่านการ์ด
ความสอดคล้อง (§4) — สัญญาณเดียวที่ดูเหมือนจะสูง (C.13) ถูกปฏิเสธเพราะ SUSPECT

### Top 3 (ตาม tier/coverage; ค่าดิบทั้งหมด MEASURED จริง)

| อันดับ | sb_code | ชื่อ | ลุ่มน้ำ | Tier | Coverage | หลักฐานหลัก |
|---|---|---|---|---|---|---|
| 1 | **1002** | ที่ราบแม่น้ำเจ้าพระยา | Chao Phraya | L0 (SUSPECT signal excluded) | 6/10 | 59 เกจระดับน้ำ, 258 เกจคลอง, ฝนจริง 132.8มม./24ชม. (228 เกจ), เขื่อนใน 19 แห่ง, พยากรณ์ฝน 8 โมเดล (worst-case knmi_seamless 125.4มม./7วัน), พยากรณ์แม่น้ำ GloFAS ที่ C.13 **ถูกปฏิเสธ (SUSPECT)** เพราะขัดทิศทางการไหลกับ C.2 |
| 2 | **1510** | ที่ราบแม่น้ำบางปะกงส่วนที่ 2 | Bang Pakong | L0 | 4/10 | 4 เกจระดับน้ำ, ฝนจริง 58.6มม./24ชม., เขื่อนใน 2 แห่ง — รวม bangkok_east (ฝั่งตะวันออกกรุงเทพฯ, DWR จัดอยู่ใต้ลุ่มน้ำบางปะกง ไม่ใช่เจ้าพระยา, MEASURED จากการ resolve พิกัดจริง) |
| 3 | **1408** | ห้วยตะเพิน | Mae Klong | L0 | 3/10 | ฝนจริงสูงสุดในกลุ่มที่ประเมิน **170.4มม./24ชม.** (5 เขื่อนใน, 4 เกจระดับน้ำ) — ไม่มี coping threshold ที่ตั้งชื่อไว้สำหรับหน่วยนี้ จึงไม่มี tier แม้ฝนจะสูงมาก (ช่องว่างที่ซื่อสัตย์ ไม่ใช่ "ปลอดภัย") |

**หมายเหตุความซื่อสัตย์**: สับเบซินแม่กลองอีกหลายหน่วย (1413, 1411, 1412, 1407) มีฝนจริงสังเกต
200.8/194.0/168.0/152.9 มม./24ชม. — **สูงกว่า sb 1002 ทั้งหมด** — แต่ coverage ต่ำกว่า (1-3/10,
ไม่มี coping threshold ตั้งชื่อไว้) จึงไม่ติด top-3 ตามกติกา (tier, coverage) ที่ประกาศไว้ — นี่คือ
**ความตึงเครียดจริงระหว่าง "coverage สูง" กับ "สัญญาณดิบสูง"** ที่ควรอ่านคู่กัน ไม่ใช่เลือกใช้เพียง
อันใดอันหนึ่ง — ดูตารางเต็มใน `raw/forecast_tests/` และ `/tmp` run output (reproduce:
`python3 -m tools.riskmap.subbasin_risk --central`)

### บันทึกพยากรณ์ล่วงหน้าของ #1 (sb_code 1002)

ไฟล์: `raw/forecast_tests/2026-09-27T131216Z_1002.json` — สรุป:

- **พยากรณ์แม่น้ำ C.13** (chaophraya_dam, GloFAS-via-Open-Meteo): 3,800.89 → 4,741.42 ลบ.ม./วิ
  (26 ก.ย. – 2 ต.ค. 2569) — **SUSPECT, ไม่ใช้เป็นฐาน tier** (ดู §4)
- **พยากรณ์ฝน 7 วัน 8 โมเดล** (ไม่เฉลี่ย): cma_grapes_global 33.2, ecmwf_ifs025 90.3,
  gem_seamless 38.3, gfs_seamless 19.1, icon_seamless 65.7, jma_seamless 107.3,
  **knmi_seamless 125.4 (worst-case)**, meteofrance_seamless 51.0, ukmo_seamless 52.0 มม.
  รวม 7 วัน — โมเดลไม่ตรงกันมาก (ต่าง >3 เท่า)
- **เกจระดับน้ำ**: 59 สถานีจริง แต่แถบสถานะ (≥warning/critical/bank) **ไม่มีข้อมูลจริง / absent**
  ทั้งหมด (คอลัมน์ NULL)
- **เขื่อนใน sb 1002**: 19 แห่ง ส่วนใหญ่ storage% เป็น null (absent), มี 1 แห่งที่ยืนยัน 0.0%
- **Tier ตอนนี้ / คาดการณ์ worst-case 7 วัน**: L0 / L0 (PARTIAL, coverage 6/10)
- **Falsifier**: ดูรายละเอียดเต็มใน JSON — เช็คซ้ำ 2026-10-04 ว่า (a) สถานี C.13 จริงของกรมชล
  ตรงกับช่วงที่พยากรณ์ไว้หรือไม่ (ถ้าตรง → SUSPECT flag ผิด, ต้องทบทวน guard), (b) มีน้ำท่วมจริง
  เกิดขึ้นหรือไม่ (ถ้าไม่มี → ยืนยันว่า L0/ไม่มีสัญญาณถูกต้อง), (c) มีน้ำท่วมเกิดขึ้นจริง (→ guard
  เข้มไป พลาดสัญญาณจริง)
- **OPEN — ตัวเลขระบายเขื่อนไม่ตรงกัน, ไม่ใช่ contradiction ของแหล่งข้อมูล แต่เป็นตัวแปรคนละตัว**:
  record 1002 อ้าง `combined_known_dam_release_m3s_now: 6.13` (ภูมิพล+สิรินธร, จาก
  `dam_hourly_release_m3s_computed` แถวล่าสุด 2026-09-27T11:00Z: 1.04 + 5.09). แต่
  `data/observations.sqlite` เก็บ `dam_hourly_release_m3s_computed` ของภูมิพล/สิริกิติ์/ป่าสักชลสิทธิ์
  **และ** `dam_daily_release_m3s_computed` แยกกัน — คอลัมน์ daily ของวันเดียวกัน (2026-09-26T17:00Z)
  ให้ ภูมิพล 34.72, สิริกิติ์ 92.94, ป่าสักชลสิทธิ์ 25.0 ลบ.ม./วิ (ตรงกับตัวเลข ~35/93/25 ที่เอกสารอื่น
  ในคลังนี้เคยอ้างถึง). record 1002 ไม่ผิด (ระบุตัวแปร/สถานีของตัวเองชัดเจนแล้ว, ทั้งคู่มีจริงในฐานข้อมูล)
  แต่การเลือกใช้ hourly ของ ภูมิพล+สิรินธร (ไม่ใช่ สิริกิติ์) แทน daily ทำให้ค่ารวมต่างกันมาก (6.13 vs
  ~153 ลบ.ม./วิ ถ้ารวม daily ของภูมิพล+สิริกิติ์+ป่าสัก) — ไม่แก้ record เดิม (append-only), บันทึกไว้
  ตรงนี้เป็น OPEN สำหรับผู้ที่จะ wire ตัวเลขนี้ต่อว่าจะใช้ hourly หรือ daily variable เป็นฐาน

### แถวเปรียบเทียบ: ฝั่งตะวันออกกรุงเทพฯ / สัมมากร

| หน่วย | sb_code | ลุ่มน้ำ | พยากรณ์ฝน worst-case 7วัน | coping threshold (rain_24h) |
|---|---|---|---|---|
| สัมมากร | 1002 (ร่วมกับ C.13/C.2) | Chao Phraya | knmi_seamless 116.2มม. | flooded_min 196.6มม. (RELAYED), coped_max OPEN |
| ฝั่งตะวันออกกรุงเทพฯ | 1510 | Bang Pakong | knmi_seamless 116.2มม. | flooded_min 203.0มม. (VERIFIED), coped_max OPEN |

ทั้งสองยังต่ำกว่า flooded_min ของตัวเองในทุกโมเดล ณ ตอนที่บันทึก — ไม่มีสัญญาณ L2+ จากพยากรณ์ฝน
7 วันนี้ (ต้องติดตาม canal backflow ของสัมมากรแยกต่างหาก ซึ่งเป็น state ไม่ใช่ตัวเลข — ดู
`docs/LAYER0_IN_OUT_CAPACITY.md` §2, ยังคง active ตามรายงานชุมชนล่าสุด)

## 7. Wiring ต่อไป (ยังไม่ทำในงานนี้)

- Collector แบบ batch สำหรับ GloFAS ต่อสับเบซิน (คิวหมุนข้าม runs, งบ ≤10 คำขอ/รัน, cursor แบบ
  `bma_station_detail_cursor.json`)
- ส่วน "ทั้งประเทศ" บนหน้าเว็บสาธารณะ — ใช้ต้นแบบนี้เป็นจุดเริ่ม, ต้องผ่าน review อิสระ (maker ≠ checker) +
  leak-scan ก่อน publish จริง (ยังไม่ทำ — งานนี้เป็น prototype ใน `site/dist/` ที่ gitignored เท่านั้น)
- ขยาย `flow_consistency_flag()` ให้ใช้ `neighbour_consistency_check()` ของ `site/build_data.py`
  โดยตรงเมื่อมีลำดับสถานีประกาศไว้ (ไม่ต้องเขียนใหม่)

## 8. Epistemic summary

- VERIFIED: การมีอยู่ของ 359 sub-basin polygon, unit_resolver point-in-polygon engine
- MEASURED: ทุกตัวเลขจาก observations.sqlite (เกจ/ฝน/เขื่อน/GloFAS), ผลของ flow_consistency_flag
- RELAYED: coping_thresholds.yaml's flooded_min/coped_max (ตัวเลขเดิมของคลัง, ติด tag ของตัวเอง)
- OPEN: การครอบคลุมประชากร, return-period ของ 353/359 หน่วยที่เหลือ, licence ของ DWR service
  (บันทึกไว้แล้วใน `docs/knowledge/DWR_SUBBASIN.md`)
- ไม่มีชื่อบุคคล, ไม่มี path เครื่อง local, ไม่มีชื่อ AI vendor ในไฟล์นี้
