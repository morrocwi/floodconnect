# Card — HII waterchart.thaiwater.net/basin/chaophraya: เชื่อมกับ API เราอยู่แล้วหรือไม่

**คำถามผู้ก่อตั้ง (ตรงตัว)**: "https://waterchart.thaiwater.net/basin/chaophraya ทำไงให้เชื่อมกับ
api นี้ หรือเชื่อมอยู่แล้ว"

**บันทึกเข้า**: 2026-09-27 · **วิธีตรวจ**: MEASURED — โหลดหน้าเว็บจริง 1 ครั้งด้วย Playwright headless
Chromium (`mcp__playwright`), ดักทุก network request 20 วินาทีหลังโหลด, ปิดหน้าเว็บ, ยิง sample request
เพิ่มเติมด้วย `curl` เฉพาะ endpoint ที่ยังไม่เคยเห็น (คนละ 1 ครั้งต่อ endpoint)

**สรุปสั้นสำหรับผู้ก่อตั้ง**: หน้า waterchart นี้ **เชื่อมอยู่แล้วบางส่วน** — ข้อมูลเขื่อน (`analyst/dam`) และ
ประตูระบายน้ำ (`public/watergate_load`) เป็น **host+path เดียวกัน** กับที่ `collect.py` ดึงอยู่ทุก 30 นาที
(`hii_dam`, `hii_watergate` ใน `sources/registry.yaml`) — หน้านี้แค่เรียกซ้ำพร้อม query filter ตาม basin
เท่านั้น ไม่ใช่ของใหม่. แต่มี **2 endpoint ที่ยังไม่ได้เชื่อม**: `public/waterlevel_load` (ข้อมูลระดับน้ำ+
ปริมาณน้ำ**cms**+% ตลิ่งต่อสถานี ละเอียดกว่า `public/waterlevel` ที่มีอยู่) และ `analyst/cctv` (กล้อง CCTV
สถานีน้ำทั่วประเทศ). ทั้งสอง endpoint เป็น JSON เปิดสาธารณะ **ไม่ต้องใช้ token/auth** อยู่บน host เดิม
(`api-v3.thaiwater.net`) ที่เราเชื่อมอยู่แล้ว — ความเสี่ยงต่ำมากถ้าจะเพิ่ม. นอกจากนี้หน้าเว็บยังใช้ไฟล์ SVG
ผังลุ่มน้ำ (`chaophraya.svg`) ที่ฝัง **ลำดับสถานีจริงตามผังภูมิศาสตร์ + เวลาที่น้ำเดินทางถึงสถานีถัดไป**
(เช่น "2 วัน", "1 วัน", "6 ชม.") — นี่คือของใหม่ที่มีค่าที่สุดสำหรับ `NATIONWIDE_HIERARCHY.md`/
`capacity_ledger` เพราะเป็น **โทโพโลยีที่ยืนยันจาก HII เอง** ไม่ใช่การอนุมานของทีมนี้.

## (1) รายการ endpoint ที่พบ (20 วินาทีหลังโหลดหน้า + curl sample)

| # | Endpoint (host+path) | Method | Status | เชื่อมอยู่แล้ว? | หมายเหตุ |
|---|---|---|---|---|---|
| 1 | `api-v3.thaiwater.net/.../analyst/dam` (+`?dam_date=`) | GET | 200 | **เชื่อมอยู่แล้ว** — เหมือน `hii_dam` (`sources/registry.yaml`) ทุกประการ ต่างแค่มี query `dam_date` filter | เห็น 3 ครั้งในหน้านี้ (ไม่มี date, `dam_date=2026-09-27`, `dam_date=2026-09-26` — คนละวันเพื่อโชว์กราฟย้อนหลัง) |
| 2 | `api-v3.thaiwater.net/.../public/watergate_load?basin_id=999\|<codes>&start_date=&end_date=` | GET | 200 | **เชื่อมอยู่แล้ว** — host+path เดียวกับ `hii_watergate` (`sources/registry.yaml` id `hii_watergate`) เราดึงแบบไม่กรอง basin อยู่แล้ว (ครบทั้งประเทศ 2,315 records) ดังนั้นข้อมูลของหน้านี้เป็น **subset** ของที่เรามี | หน้าเว็บยิง 2 แบบ: `basin_id=999` (all-basin summary?) และ `basin_id=6,7,8,9,10,11,12,13,14,15,26` (basin_code ของกลุ่มเจ้าพระยา/สาขา) |
| 3 | `api-v3.thaiwater.net/.../public/waterlevel_load?basin_id=...&start_date=&end_date=` | GET | 200 | **ยังไม่ได้เชื่อม** (endpoint ใหม่ — คนละ path จาก `public/waterlevel` ที่เรามี id `thaiwater_waterlevel`) | ดูรายละเอียด §2 — มี `discharge`(cms), `storage_percent`(% ตลิ่ง), `waterlevel_msl`, `situation_level`, `river_gid`/`river_name`, `is_key_station` ที่ `public/waterlevel` ไม่มี |
| 4 | `api-v3.thaiwater.net/.../analyst/cctv` | GET | 200 | **ยังไม่ได้เชื่อม** (endpoint ใหม่ทั้งหมด) | ดู §3 — 106 กล้อง/สถานีทั่วประเทศ, ภาพนิ่ง (`media_type: img`) จาก URL ของหน่วยงานเจ้าของกล้องเอง (ไม่ใช่ host thaiwater) |
| 5 | `waterchart.thaiwater.net/assets/svg/chaophraya/chaophraya.svg` | GET | 200 | **ของใหม่ (static asset ไม่ใช่ JSON API)** | ดู §4 — ผังโทโพโลยี + travel-time ระหว่างสถานี, id ต่อ node ตรงกับรหัสสถานี (เช่น `C2-wl-value`, `C2-cms-value`) |
| — | analytics/GTM/font/webpack chunk requests (~26 รายการ) | — | 200/204 | ไม่เกี่ยวกับข้อมูลน้ำ | Google Analytics, Google Fonts, Next.js static chunks — ไม่บันทึกในตารางนี้ (ดูไฟล์ raw log) |

Raw log ทั้งหมด (54 request รวม static): ดูผลลัพธ์ดิบใน conversation ของ session นี้ (ไม่ได้บันทึกไฟล์ jsonl
แยก เพราะเครื่องมือ `mcp__playwright` ของ session นี้จำกัด path การเขียนไว้ที่ repo เท่านั้น ไม่ใช่
scratchpad — ดู §6 หมายเหตุเครื่องมือ). สรุป endpoint ข้อมูลน้ำทั้งหมดคือ 5 รายการข้างต้น ไม่มี host ใหม่
นอกเหนือจาก `api-v3.thaiwater.net` (ที่เชื่อมอยู่แล้ว) และ `waterchart.thaiwater.net` เอง (static
assets/SVG เท่านั้น ไม่มี JSON API เพิ่มจากโดเมนนี้).

**Auth/token**: ไม่พบ — ทั้ง 5 request ไม่มี `Authorization` header, ไม่มี cookie/token พิเศษที่สังเกตได้
จาก devtools network list (ไม่ได้ intercept header ระดับ byte เพราะเครื่องมือที่ใช้ให้แค่ URL+status
ไม่ใช่ full header dump — แต่ยืนยันด้วย `curl` ตรงจาก IP นี้แบบไม่มี header พิเศษก็ได้ 200 ทั้งคู่ จึงสรุปว่า
**ไม่ต้องใช้ token** — MEASURED, ไม่ใช่ INSTINCT).

## (2) `public/waterlevel_load` — ของใหม่ที่ควรเพิ่ม

MEASURED จาก 1 คำขอจริง (`curl` ตรง, query เดียวกับที่หน้าเว็บยิง: `basin_id=6,7,8,9,10,11,12,13,14,15,26`,
`start_date=2026-09-27 00:00`, `end_date=2026-09-27 23:59`) — HTTP 200, top-level keys:
`waterlevel_data`, `waterlevel_manual_data`, `basin`, `agency`, `station`, `scale`, `province`.
`waterlevel_data.data` = list, **380 records** ในหน้าต่างนี้ (basin กลุ่มเจ้าพระยา+สาขาเท่านั้น ไม่ใช่
ทั้งประเทศ). ยืนยันพบสถานีโซ่หลักเจ้าพระยาที่ `capacity_ledger`/`NATIONWIDE_HIERARCHY.md` ใช้อ้างอิง —
`C.2`, `C.13`, `C.3`, `C.7A`, `C.12`, `C.35`, `C.36`, `C.37`, `C.67` (จาก `station.tele_station_oldcode`).

ตัวอย่าง 1 แถว (ตัดบางฟิลด์):
```json
{
  "waterlevel_datetime": "2026-09-27 18:00",
  "waterlevel_msl": "65.79", "waterlevel_msl_previous": "65.56",
  "discharge": "0.00", "storage_percent": "209.48",
  "station_type": "tele_waterlevel", "situation_level": 5,
  "station": {"tele_station_oldcode": "MKVKD07", "tele_station_lat": 14.44497,
    "tele_station_long": 98.80493, "left_bank": 72.14, "right_bank": 60.48,
    "min_bank": 60.48, "ground_level": 55.63, "is_key_station": false,
    "critical_level_msl": 62.4},
  "river_gid": 181830, "river_name": "ห้วยแม่น้ำน้อย"
}
```

**สิ่งที่ได้เพิ่มเทียบกับ `public/waterlevel` ที่มีอยู่แล้ว** (`thaiwater_waterlevel`, `sources/registry.yaml`
บรรทัด 118-138):
- `discharge` (ปริมาณน้ำ, cms) ต่อสถานี — `public/waterlevel` ไม่มีฟิลด์นี้ (MEASURED, ต้อง diff schema
  จริงอีกครั้งก่อนอ้างเป็น VERIFIED สมบูรณ์ — งานรอบนี้ยังไม่ได้ fetch `public/waterlevel` คู่กันมา diff
  field-by-field แบบ byte-exact เพื่อประหยัด budget คำขอ)
- `storage_percent` — น่าจะคือ % เทียบตลิ่ง/ความจุ (ต้องยืนยันหน่วยกับ HII glossary ก่อนใช้จริง — OPEN)
- `waterlevel_msl` / `waterlevel_msl_previous` — ระดับน้ำเทียบระดับน้ำทะเลปานกลาง (MSL) ไม่ใช่แค่ค่าดิบ
  จากเซนเซอร์ — มีค่าเวลาก่อนหน้าด้วย ทำให้คำนวณ trend ได้โดยไม่ต้องเก็บ 2 รอบเอง
- `situation_level` (ตัวเลข 0-5 ในตัวอย่าง) — ธงสถานะความรุนแรงที่ HII คำนวณเอง (ไม่ทราบ scale เต็ม — OPEN)
- `river_gid` / `river_name` — เชื่อมสถานีเข้ากับ **สายน้ำ** โดยตรง (ตรงกับ `WATER_SYSTEM_DAG.md` ที่กำลังทำ)
- `is_key_station`, `left_bank`/`right_bank`/`min_bank`/`ground_level`/`critical_level_msl` — พารามิเตอร์
  หน้าตัดสถานีที่ `public/waterlevel` ไม่มีให้ (ค่า capacity ต่อสถานีที่ยืนยันจาก HII เอง แทนที่จะต้องหาจาก
  เอกสารแยก)

**ข้อควรระวัง**: การเรียกต้องระบุ `basin_id` (comma-separated basin_code list) + `start_date`/`end_date`
เสมอ ไม่เหมือน `public/waterlevel` ที่ไม่ต้องมี query — ถ้าจะดึงทั้งประเทศต้องหา basin_code ครบทุกลุ่มน้ำก่อน
(HII มีลุ่มน้ำหลัก 25 ลุ่มทั่วประเทศ — งานนี้เห็นแค่ 11 รหัส `6,7,8,9,10,11,12,13,14,15,26` ที่หน้าเจ้าพระยา
ใช้ ยังไม่ยืนยันรหัสที่เหลือ — OPEN, ต้องหาใน JS bundle หรือถามหน้า basin อื่นก่อน implement เต็มรูป).

## (3) `analyst/cctv` — ของใหม่ทั้งหมด

MEASURED จาก 1 คำขอจริง — HTTP 200, shape `{"result": "...", "data": [...]}`, **106 กล้อง/สถานีทั่ว
ประเทศ** (ไม่ได้กรอง basin — คำขอนี้ไม่มี query param เลย). แต่ละแถวมี `lat`/`long`, `basin`/`basin_name`,
`agency` (เจ้าของกล้อง เช่น กรมทรัพยากรน้ำ), `title`/`description` (ชื่อสถานี+อำเภอ/จังหวัด), `cctv_url`
(ลิงก์ภาพนิ่ง/สตรีมตรงจากเซิร์ฟเวอร์หน่วยงานเจ้าของ ไม่ใช่ thaiwater เอง — เช่น
`http://woc-lampang.dyndns.org:5001/axis-cgi/jpg/image.cgi?...`), `media_type` (`img` ในตัวอย่าง),
`is_active`. **คุณค่า**: ภาพยืนยันภาคสนามของสถานีที่เรามีอยู่แล้ว (ไม่ใช่ตัวเลขใหม่ แต่เป็นวิธี VERIFIED
ด้วยตาแทนอนุมานจากตัวเลขอย่างเดียว) — เหมาะเป็น "ดูภาพจริงที่สถานี X" ลิงก์ประกอบใน UI ไม่ใช่ตัวเลข telemetry
เข้า `data/observations.sqlite`.

**ข้อจำกัด**: `cctv_url` แต่ละอันชี้ไป host คนละที่ (dyndns ส่วนตัวของหน่วยงานปลายทาง) — ความเสถียร/เวลา
ทำงานไม่ยืนยัน (OPEN, ต้องเช็คทีละลิงก์ก่อนใช้จริง ไม่ใช่ทุกลิงก์จะมีอายุยืน).

## (4) `chaophraya.svg` — โทโพโลยียืนยันจาก HII เอง

Static asset, HTTP 200 (ต้อง `curl -k` — TLS chain verify fail บน `waterchart.thaiwater.net` ตรงกับที่
บันทึกไว้แล้วใน `sources/api_census.yaml` id `hii_waterchart_thaiwater_net`; **host คนละตัวกับ
`api-v3.thaiwater.net` ที่ verify ผ่านปกติ** — แยกสถานะ TLS ต่อ host ให้ชัด). ไฟล์ SVG มี text-element id
ต่อสถานีแบบ `<code>-wl-value` / `<code>-cms-value` / `<code>-msl-value...` (ตำแหน่งว่างรอ JS เติมค่าจาก
API ตอน runtime) ครอบคลุมรหัสสถานีอย่างน้อย: `C2`, กลุ่ม `CPY001-017` (สายหลักเจ้าพระยา), กลุ่ม
`PIN001-006`/`NAN003-014`/`YOM005-012`/`WAN001-005` (ปิง/น่าน/ยม/วัง — 4 แม่น้ำต้นน้ำ), กลุ่ม `BKK*`/
`ATG*`/`BPK*`/`DIV*`/`CHM*`/`temp*`/`DR*`/`GLF*`/`KWN*`/`LBI*`/`SKG*`/`TCY37`/`THA*`/`TN21`/`TY54`
(รวม ~90 node). **มี label เวลาน้ำเดินทาง** ระหว่าง node บางคู่ (ข้อความดิบจาก SVG: "2 วัน", "1 วัน",
"6 ชม.", "3 วัน", "20 ชม.", "2.5 วัน") — นี่คือ **lag time ที่ HII ยืนยันเองระหว่างจุดในผัง** ยังไม่ได้จับคู่
ว่า label ไหนอยู่ระหว่าง node คู่ไหนแบบ pixel-exact (งานนี้แค่ดึง raw text ออกมา — ต้องอ่าน `<g>`/transform
grouping เพิ่มถ้าจะ map แม่นยำ, OPEN).

**นัยสำคัญต่อ `NATIONWIDE_HIERARCHY.md`/`capacity_ledger`**: node id ของ HII (`CPY001`...`CPY017` ตาม
ลำดับในไฟล์) น่าจะ**คือลำดับภูมิศาสตร์ตามน้ำไหลของสายหลักเจ้าพระยา** ตามที่ HII วาดเอง — ถ้ายืนยันได้ (ต้อง
map `CPY0xx` → `tele_station_oldcode`/`C.x` ผ่าน node position หรือ JS chunk อีกที) จะเป็น **VERIFIED
topology จากต้นทาง** แทนที่การไล่ node ด้วยพิกัด lat/long เอง — เก็บเป็น OPEN item ไว้ก่อน ไม่ด่วนสรุปว่า
`CPY001` = C.2 หรือสถานีไหนโดยไม่ยืนยัน.

## (5) Licence/ToS

ไม่พบลิงก์ licence/terms บนหน้า `basin/chaophraya` เอง ระหว่างโหลด (ไม่ได้ scroll ไป footer โดยเฉพาะ —
ไม่นับเป็น "ตรวจครบ", OPEN). สถานะเดิมใน `sources/registry.yaml`/`api_census.yaml` (RELAYED,
unresolved — "ไม่มี terms/licence link ในหน้า footer" จากการเช็ครอบก่อน) **ยังใช้ได้เหมือนเดิม** ไม่มี
หลักฐานใหม่ที่เปลี่ยนสถานะนี้.

## (6) Feasibility / ข้อเสนอ collector

- **`hii_waterlevel_load`** (draft: `tools/harvest/hii_waterchart_draft.py`) — เป็นไปได้ 1 คำขอ/รัน (ไม่มี
  auth, JSON สาธารณะ) แต่ **ต้องแก้ปัญหา basin_code ครบทุกลุ่มน้ำก่อน** (เห็นแค่ 11/25 รหัส) มิเช่นนั้นจะได้
  แค่ subset ภาคกลาง — เสนอ**ไม่รีบ wire เข้า `collect.py --all`** จนกว่าจะยืนยัน basin_code ครบ หรือ
  ยืนยันว่า `basin_id=999` (ที่หน้าเว็บก็ยิงคู่กันมา) หมายถึง "ทั้งประเทศ" จริง (OPEN, ยังไม่ทดสอบ)
- **`hii_cctv`** — ง่ายกว่า (ไม่มี query param, ได้ทั้งประเทศในคำขอเดียว) แต่เก็บแค่ metadata+ลิงก์ภาพ ไม่ใช่
  telemetry ตัวเลข — เหมาะเป็น reference document (เหมือน "static reference asset") มากกว่าจะ parse เข้า
  `observations.sqlite`
- **`chaophraya.svg` topology** — ไม่ใช่ collector (static asset ไม่เปลี่ยนบ่อย) เสนอเก็บเป็น **document
  card แยก** (`docs/knowledge/HII_WATERCHART_TOPOLOGY.md` — ยังไม่เขียน, งานรอบหน้า) เพื่อ map
  `CPY0xx`/node id → `tele_station_oldcode` ให้ครบ แล้วจึงใช้เป็น VERIFIED topology ป้อน
  `NATIONWIDE_HIERARCHY.md`

## (7) หมายเหตุเครื่องมือ/ขอบเขตงานนี้

Session นี้เป็น **read-only reviewer active** — ห้าม commit/stash/checkout/แก้ tracked file ใด ๆ, เขียนได้
เฉพาะไฟล์ใหม่ 3 ไฟล์ตามที่สั่ง (การ์ดนี้ + `docs/knowledge/api_census_additions_hii_waterchart.yaml` +
draft collector `tools/harvest/hii_waterchart_draft.py`) — **ไม่ได้**เพิ่มแถวใน `docs/knowledge/README.md`
หรือรัน `kb.py reindex` ตามธรรมเนียมปกติของ repo (ดู `AGENTS.md` §5) เพราะขัดกับข้อจำกัด
read-only-reviewer ของ session นี้ — ต้องมีคนแยก (maker≠checker) รับช่วงทำ 2 ขั้นนั้นต่อก่อน merge.

**จำนวนคำขอ live ทั้งหมดที่ยิงเองในงานนี้** (ไม่นับที่ browser โหลดอัตโนมัติตอนเปิดหน้า):
1. `curl -k` → `chaophraya.svg` (ต้อง `-k` เพราะ TLS chain verify fail บน `waterchart.thaiwater.net`,
   ตรงกับสถานะเดิม)
2. `curl` → `public/waterlevel_load?basin_id=6,7,8,9,10,11,12,13,14,15,26&start_date=...&end_date=...`
   (verify ผ่านปกติบน `api-v3.thaiwater.net`)
3. `curl` → `analyst/cctv` (verify ผ่านปกติ)

รวม browser page load (1 ครั้ง, Playwright, ปิดหลัง 20 วินาที ก่อนเริ่มคำขอ curl เหล่านี้) + curl แยก 3
ครั้ง = **4 live fetches ทั้งหมด** ไม่มีการ reload หน้าเว็บซ้ำ ไม่มี retry ใด ๆ.
