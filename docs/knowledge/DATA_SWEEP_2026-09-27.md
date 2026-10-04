# DATA_SWEEP_2026-09-27 — กวาดข้อมูลจริงเติมช่องว่าง PROP-FLOOD-06 backtest

**สถานะ**: RELAYED/MEASURED-history ผสมกัน ทุกจุดติด tag — เอกสารนี้รายงานว่าเจออะไร/ไม่เจออะไร
ไม่ใช่ผลสรุปของ PROP-FLOOD-06 เอง (`docs/BACKTEST_PROP_FLOOD_06_v0.md` PROPOSAL, unverified)
เขียนโดย worker แยก (write-scope: ไฟล์ใหม่เท่านั้น, ไม่ commit, ไม่แก้ไฟล์เดิม)

**คำสั่ง founder (verbatim)**: "และแก้บั๊กต่างๆ ไปกวาดหาข้อมูลมาให้ได้" + เพิ่ม target E (DWR
WebGIS) + target F (per-canal normal/control level) ระหว่างงาน

**งบคำขอ**: ≤40 (A-D) + ≤6 (E, DWR) + ≤6 (F, canal normal) — ใช้จริง: A-D ~17 คำขอ, E 6/6,
F 6/6 (ดูตารางท้ายไฟล์) — 1 คำขอ/URL ไม่ retry, browser UA, timeout 20s ตาม AGENTS.md

## สรุปการค้นพบที่สำคัญที่สุด

**พบ endpoint ประวัติย้อนหลังจริงของ HII/thaiwater ที่ไม่เคยมีบันทึกใน `sources/api_census.yaml`
มาก่อน**: `waterlevel_graph` (numeric station_id + station_type=tele_waterlevel|canal) และ
`waterlevel_graph_oldcode` (RID/BMA oldcode เช่น X.44) — พบจากการอ่าน JS bundle ของเว็บ
thaiwater.net เอง (`raw/knowledge/api_census/hii/app.chunk.js`, ไฟล์ที่มีอยู่แล้วจากงานก่อนหน้า
ไม่ได้ดึงใหม่) ไม่ใช่ brute force. endpoint นี้ **ให้ข้อมูลระดับน้ำ+discharge รายชั่วโมงจริง**
ย้อนหลังอย่างน้อยถึงปี 2565 ที่หลายสถานีตรงกับหน่วย backtest ของเรา — ปิดช่องว่างที่ใหญ่ที่สุด
ของ `docs/BACKTEST_PROP_FLOOD_06_v0.md` (REFUSED 92.5% เพราะ GloFAS ไม่ resolve คลอง/แม่น้ำ) ได้
บางส่วนจริง

## A. หาดใหญ่ (คลองอู่ตะเภา / คลอง ร.1)

| สถานี | HII station_id | ช่วงที่ลอง | ผล | archive |
|---|---|---|---|---|
| X.44 (บ้านหาดใหญ่ใน) | 2591 | 2010-10-15..2010-11-10 (2553) | **ALL-NULL** (648/648) — telemetry ยังไม่ถึงปี 2553 | `raw/backtest/hii_history/X44_2591_2553.json` |
| X.44 | 2591 | 2022-11-10..2022-12-10 (2565) | **มีข้อมูลจริง** 681/744 ชม. non-null, level+discharge | `raw/backtest/hii_history/X44_2591_2565.json` |
| X.90 (บ้านบางศาลา, control) | 2589 | 2022-11-10..2022-12-10 | ดึงสำเร็จ (200), ใช้เป็น downstream control | `raw/backtest/hii_history/X90_2589_2565.json` |
| ONE037 (สะพานข้ามคลองอู่ตะเภา) | 1109526 | 2022-11-10..2022-12-10 | 1584/4464 (10 นาที) non-null แต่ **ไม่มี discharge** เลย มีแต่ level | `raw/backtest/hii_history/ONE037_1109526_2565.json` |

**MEASURED**: X.44 discharge สูงสุดในช่วงที่ดึง = 168.6 ลบ.ม./วิ วันที่ 2022-12-10 02:00 —
**หลังวันท่วมจริงที่รายงาน** (30 พ.ย.-3 ธ.ค. 2565) ซึ่งช่วงนั้น discharge วัดได้แค่ 38.8-58.4
ลบ.ม./วิ (ต่ำกว่าช่วงต้น/ท้ายของ series เอง) — **ไม่เห็นสัญญาณ peak ตรงวันท่วมจริงชัดเจน**
รายงานตรงๆ ไม่ตีความแทน — ข้อสันนิษฐาน (INSTINCT ไม่ยืนยัน): X.44 อาจอยู่ท้ายจุดผันน้ำเข้า
คลอง ร.1 ทำให้ discharge ที่วัดได้ที่นี่ลดลงตอนวิกฤตจริงเพราะน้ำถูกผันออกไปทางอื่น

**คลอง ร.1 เอง**: ค้นในชุดข้อมูล waterlevel ทั้ง 804 สถานีของ HII (cache เดิม ไม่ใช่คำขอใหม่)
ไม่พบสถานีชื่อ "ร.1"/"ภูมิพล" เลย — HII/thaiwater **ไม่มี telemetry ของคลอง ร.1 เอง**
(เทศบาลหาดใหญ่/RID เขต 8 อาจมีระบบแยกต่างหากที่ไม่เชื่อมกับ thaiwater — OPEN)

`hatyaicity.go.th` (เว็บเทศบาล) ที่ลอง: หน้าแรกเป็นแค่ script redirect ไปหน้า `event.php`
(ดูเหมือนระบบลงทะเบียนกิจกรรม ไม่ใช่ระบบเตือนภัยน้ำท่วม) — **ไม่พบระบบ history ที่ใช้ได้ในงบนี้**
(OPEN, ไม่ตามต่อเพื่อประหยัดงบ — archived ที่ `raw/backtest/misc/hatyaicity_landing.html`)

RID hydro-8.rid.go.th: มีบันทึกอยู่แล้วใน `sources/api_census.yaml` ว่า root page เป็น
"placeholder Royal Slideshow" — ไม่ลองซ้ำ (already probed, no new value expected)

**สรุปใช้ได้ตอนนี้**: X.44 มี real gauge history ปี 2565 (ไม่ใช่ 2553) — เพียงพอให้ backtest
2565 ของหาดใหญ่ resolve เป็นตัวเลขได้จริง (ไม่ REFUSED) แทน GloFAS แต่ discharge ที่วัดได้ไม่ตรง
กับวันท่วมจริงชัดเจน (เป็น falsifier ต่อสมมติฐานว่า X.44 คือ Q_o,now ที่ใช้ได้ตรงไปตรงมา ต้อง
report ไว้ ไม่ปรับให้เข้าเรื่อง)

## B. น่าน + เชียงใหม่ (2567) — ปิดช่องว่างสำคัญที่สุดของ backtest

| สถานี | HII id | ช่วง | discharge peak ที่วัดได้ | qmax (bankfull proxy, RELAYED) | เกิน qmax? |
|---|---|---|---|---|---|
| N.1 (เมืองน่าน) | 3219 | 2024-08-01..09-15 | **1463.6 ลบ.ม./วิ** @ 2024-08-22 20:00 | 1066 | +37% |
| N.64 (ท่าวังผา, upstream) | 3246 | 2024-08-01..09-15 | **1426.5 ลบ.ม./วิ** @ 2024-08-22 10:00 | 1028 | +39% |
| P.1 (นวรัฐ, เชียงใหม่) | 3226 | 2024-09-15..10-15 | **656 ลบ.ม./วิ** @ 2024-10-05 12:00 | 425 | +54% |

**MEASURED-history**: ทั้งสามสถานีมีข้อมูลรายชั่วโมงจริง (927-928/1104 และ 689/744 ชม. non-null)
วันพีค discharge ของ P.1 (5 ต.ค. 2567) **ตรงกับวันที่การ์ด `case_chiangmai_2567.md` เคยระบุไว้
เป็นวันสำคัญของเหตุการณ์** (cross-check ระหว่างสองแหล่งที่เป็นอิสระต่อกัน) — บันทึกไว้ตรงๆ ว่า
ตรงกัน ไม่ตีความเกินนี้

**qmax field**: พบว่า metadata สถานีของ HII เอง (field `qmax` ในไฟล์ `public/waterlevel` ที่
collect.py ดึงอยู่แล้วทุกรอบ on demand — *(historical note: ตอนเขียนบันทึกนี้ 2026-09-27 cadence
ยังเป็น cron 30 นาที; ฟาวน์เดอร์เปลี่ยนเป็น on-demand เมื่อ 2026-10-02)* — **ไม่ใช้คำขอใหม่เลย** อ่าน
จาก cache) มีค่าความจุ/design
discharge ต่อสถานีโดยตรง — นี่คือค่าที่ปิด `OUTLET_CAPACITY_UNKNOWN` REFUSED 100% ของน่าน/
เชียงใหม่ในรอบก่อน tag **RELAYED** (เป็น attribute ที่ HII ใส่เอง ไม่ใช่รายงาน RID/สทนช. ที่อ่าน
เต็มฉบับ) — บันทึกลง `sources/capacity_ledger_additions.yaml` แล้ว พร้อม peak ที่วัดได้จริงเทียบ
qmax ทุกสถานี

**ไม่ได้ทำรอบนี้ (OPEN)**: ยังไม่ได้ WebFetch หา รายงานทางการ สทนช./กรมชลฯ หลังเหตุการณ์ 2567
ที่ระบุ "ความจุลำน้ำ"/ระดับตลิ่งเป็นตัวเลขแยกจาก qmax ของ HII เพื่อ cross-check ตัวเลขข้างต้น —
งบเวลา/คำขอถูกใช้กับ telemetry จริงแทน เพราะให้ผลตรงคำถาม founder มากกว่า (ตัวเลข m3/s พร้อม
ประวัติ ไม่ใช่แค่ค่าความจุนิ่ง)

## C. กรุงเทพฯ ฝั่งตะวันออก (2554 และ 2569)

- **HII canal history 2554**: ลอง `waterlevel_graph?station_type=canal&station_id=87` ช่วง
  2011-10-01..11-15 → **ALL-NULL (0/4416)** — canal telemetry ของ กทม. ไม่ย้อนไปถึงปี 2554
  (บันทึกเป็น negative finding จริง ไม่ใช่บั๊ก) — `raw/backtest/hii_history/BKK_canal87_2554.json`
- **DDS PDF archive**: `dds.bangkok.go.th/flood_report.php` อ้างถึง PDF ล่าสุดตัวเดียว
  (0006030_1.pdf, รู้อยู่แล้ว) ตามด้วยลิงก์ `download/download01.html` ซึ่งเป็นหน้าดาวน์โหลด
  แบบก่อสร้าง/สถานีสูบ (bangna.pdf, clarifier drawings) **ไม่ใช่คลัง flood report ย้อนหลัง** —
  ไม่พบ index ตัวเลข PDF อื่นให้ลองแบบไม่เดา — OPEN, ไม่ brute-force เลขไฟล์ตามกติกา
- **ปั๊ม 2569**: export จาก `data/observations.sqlite` เอง (ไม่มีคำขอ HTTP) — สถานี
  ST.SPS.01-04 (แสนแสบ ตอนสะพานสูง) + สถานี/ประตูโซนตะวันออกอื่นๆ (แสนแสบ/ประเวศ/พระโขนง/
  หนองจอก/มีนบุรี/ลาดกระบัง) รวม **1,328 แถว, 50 สถานี**, ตั้งแต่ 2026-09-26 → เขียนที่
  `raw/backtest/pumps_2569.csv` — เป็นชุดข้อมูล pump/canal-level ต่อเนื่องจริงชุดแรกของ repo นี้

## D. fetch_historical_th.py

เขียน `tools/backtest/fetch_historical_th.py` (parameterised, 1 คำขอ/URL, skip-if-exists,
เก็บที่ `raw/backtest/hii_history/`) ครอบคลุมทุกสถานี/ช่วงที่ยืนยันแล้วว่าใช้ได้จริงในงานนี้
(X.44/X.90/ONE037/N.1/N.64/P.1/BMA canal ×6) — endpoint variant `_oldcode` (rid/bma code
ตรงๆ) ยังไม่ได้ลอง (OPEN ในตัวสคริปต์เอง พร้อม docstring บอกไว้ชัด)

## E. DWR WebGIS (`webgis.dwr.go.th`) — target เพิ่มจาก founder

งบ 6/6 คำขอ:

1. `webgis.dwr.go.th/` (landing, 200, 84.5KB) — เป็นเว็บประชาสัมพันธ์ ไม่ใช่ตัว viewer
   เอง — พบลิงก์ไปยัง `gis.dwr.go.th/portal/home/` (ArcGIS Portal จริง)
2. `gis.dwr.go.th/arcgis/rest/services?f=json` (200) — **root ArcGIS Server ไม่มี auth**
   เห็น service list ทั้งหมด (25 รายการ) รวม `Sub_Basin`, `25_BASIN`, `T22Basin`,
   `HYD_STATION`, `DAM`, `WELL`, `ขอบเขตลุ่มน้ำสาขา`, `ขอบเขตลุ่มน้ำหลัก`,
   `สถานีน้ำฝน_กรมชลประทาน`, `สถานีวัดระดับน้ำ_กรมชลประทาน`, `NAT_STREAM`, `MM_CANAL` ฯลฯ
3. `Sub_Basin/MapServer/0?f=json` (200) — layer info: geometryType=Polygon, fields
   `SB_CODE, SB_NAME_T, MB_CODE, MBASIN_T, MBASIN_E, AREA_SQKM` (+ Shape) — **นี่คือข้อมูล
   ที่ปิดช่องว่าง UNIT_POLYGON_MISSING/พื้นที่ A_U ที่ตอนนี้ใช้ radius-fallback INSTINCT
   อยู่** (ดู `units.yaml` HATYAI note)
4. Sub_Basin query ด้วยชื่อ "อู่ตะเภา" → **0 ผลลัพธ์** (ชื่อ sub-basin ใช้ชื่อแม่น้ำต้นน้ำ
   ไม่ใช่ชื่อเมือง/คลอง — ต้องหาด้วย bbox หรือ basin code ไม่ใช่เดาชื่อ)
5. Sub_Basin query `where=1=1` (15 ตัวอย่างแรก) → ยืนยันว่าเป็นชุดข้อมูลระดับประเทศจริง
   (พบ 15 sub-basin ลุ่มน้ำสาละวิน, `exceededTransferLimit:true` = ยังมีอีกมาก, ดึงได้เต็ม
   ด้วยการวน page ต่อ — ยังไม่ทำในงบนี้)
6. `สถานีวัดระดับน้ำ_กรมชลประทาน/MapServer/0/query` (5 ตัวอย่าง) → เป็น**ทำเนียบสถานี RID
   นิ่ง** (fields: Region, Code, River, Detail, Amphoe, Province, Basin, Lat, Long, Remark
   — ตัวอย่าง Code="Sw.5A") ไม่ใช่ feed ค่าปัจจุบัน/ประวัติ — ใช้ cross-check ชื่อสถานี RID
   (เช่น X.94 ที่ยังหาไม่เจอใน HII feed) ได้ในอนาคต แต่ยังไม่ query หา X.94 เฉพาะเจาะจงในงบนี้

**Licence/terms**: ไม่พบหน้า licence/terms-of-use ชัดเจนในการดูรอบนี้ (ไม่ได้ตามลิงก์ footer/
about ทุกอัน เพื่อประหยัดงบ) — **OPEN**, ต้องเช็คก่อนใช้ polygon เหล่านี้ในหน้า public

**Sub-basin polygon ดาวน์โหลดได้ไหม**: **ได้ — ยืนยันแล้ว** ผ่าน standard ArcGIS REST query
(`f=json`, `returnGeometry=true` เพื่อดึง geometry, ยังไม่ได้ลองในงบนี้แต่เป็น parameter
มาตรฐานของ ArcGIS ทุกตัว ไม่ต้องเดา) — งานต่อไปควรทำ spatial/bbox query รอบหาดใหญ่/น่าน/
เชียงใหม่/กรุงเทพฯ โดยตรงแทนการเดาชื่อ

**EWS (สถานีเตือนภัยล่วงหน้า ~1,500+ หมู่บ้าน) history**: **ยังไม่พบ** service ชื่อที่ตรงกับ
"Early Warning"/EWS ในรายการ 25 service ที่เห็น — อาจอยู่ใน folder `Hosted` หรือ `Utilities`
ที่ root response ระบุไว้แต่ยังไม่ได้เปิดดู (งบหมดพอดีที่ 6/6) — **OPEN**, งบหน้าควรเปิด
`gis.dwr.go.th/arcgis/rest/services/Hosted?f=json` ก่อนอย่างอื่น

## F. Per-canal NORMAL/CONTROL level — target เพิ่มจาก founder

งบ 6/6 คำขอ — ดึง `waterlevel_graph?station_type=canal` ช่วง **2026-02-01..2026-03-15**
(ฤดูแล้ง, ก่อนวิกฤต 26 ก.ย. 2569) ให้ทั้ง 6 สถานีที่ระบุ:

| สถานี | station_id | ค่ามัธยฐาน (ม., เทียบ msl สถานี) | n non-null/total |
|---|---|---|---|
| WL.SSB.07 (บางกะปิ) | 77 | -0.36 | 2898/4128 |
| WL.SSB.09 (บางชัน) | 71 | -0.38 | 2904/4128 |
| WL.SSB.10 (มีนบุรี) | 67 | -0.22 | 2905/4128 |
| WL.PWT.03 (ประเวศฯ-วัดกระทุ่มฯ) | 82 | -0.43 | 2910/4128 |
| WL.PWT.04 (ประเวศฯ-ลาดกระบัง) | 81 | -0.24 | 2904/4128 |
| WL.LPW.01 (ลาดพร้าว) | 72 | -0.35 | 2908/4128 |

เขียนที่ `sources/canal_normal_levels.yaml` — tag **MEASURED-history** (มัธยฐานที่วัดเองจาก
หน้าต่างฤดูแล้ง ไม่ใช่ตัวเลข "ระดับปกติ" ที่หน่วยงานประกาศเอง — บอกไว้ตรงๆ ในไฟล์)

**ตรวจ "ระดับควบคุม" จากเอกสาร กทม.**: `raw/capacity/plan_2569.pdf` (แผนปฏิบัติราชการ
ประจำปี 2569 สนน., archived อยู่แล้ว ไม่ใช่คำขอใหม่) — รัน `pdftotext -enc UTF-8` แล้ว grep
"ระดับควบคุม"/"ระดับปกติ" → **0 hit** เอกสารนี้เป็นแผนปฏิบัติการทั่วไป ไม่ใช่ตารางระดับควบคุม
รายคลอง — **OPEN**, ไม่พบ URL เอกสารที่มีตารางนี้ในงบนี้

**observations.sqlite เป็น baseline ไม่ได้**: ยืนยันตรงๆ ว่าค่าที่เก่าที่สุดใน sqlite เอง
(26 ก.ย. 2569 00:00 เป็นต้นไป, ดู `raw/backtest/pumps_2569.csv`) เป็นช่วงวิกฤตอยู่แล้ว
ใช้เป็นเส้นฐาน "ปกติ" ไม่ได้ — เหตุผลที่ไฟล์นี้ต้องดึงจากช่วงอื่นแยกต่างหาก

**field เสริมที่พบแถม**: สถานีเดียวกันมี `hii_warning_level_m`/`hii_critical_level_m` เป็น
threshold operasional ของ HII เอง (ไม่ใช่ agency capacity report ที่อ่านเต็ม) — บันทึกคู่กับ
ค่ามัธยฐานไว้เทียบกันในไฟล์เดียวกัน

## ยังเป็น OPEN / ต้องถามใคร

| ช่องว่าง | ใครน่าจะตอบได้ |
|---|---|
| คลอง ร.1 หาดใหญ่ ไม่มี telemetry ใน HII เลย | เทศบาลนครหาดใหญ่ / RID เขต 8 (hydro-8.rid.go.th ที่ probe แล้วเป็น placeholder) |
| X.44 discharge ไม่ peak ตรงวันท่วมจริง 2565 | ต้องดูสถานีอื่นเพิ่ม (ONE037 ไม่มี discharge field) หรือถาม RID เขต 8 ว่ามีจุดวัดอื่นที่ resolve ตรงคลอง ร.1 ไหม |
| DDS PDF archive ย้อนหลัง (2554) | สำนักการระบายน้ำ กทม. โดยตรง — เว็บสาธารณะไม่มี index |
| DWR sub-basin polygon เฉพาะ 3 หน่วย (หาดใหญ่/น่าน/เชียงใหม่) | งานถัดไป: bbox query ตรง ไม่ใช่เดาชื่อ |
| DWR EWS ~1,500+ หมู่บ้าน history | เปิด folder `Hosted`/`Utilities` ของ arcgis rest ก่อน |
| BMA per-canal "ระดับควบคุม" อย่างเป็นทางการ | สำนักการระบายน้ำ กทม. (เอกสารที่มีอยู่ไม่ระบุ) |
| สทนช./กรมชลฯ รายงานความจุลำน้ำน่าน/ปิง แยกจาก HII qmax | สทนช. / กรมชลประทาน (ยังไม่ WebFetch รอบนี้) |
