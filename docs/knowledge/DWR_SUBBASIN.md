# DWR Sub_Basin polygons (gis.dwr.go.th) — จุด lat/lon ใดๆ ในไทย → หน่วยลุ่มน้ำสาขา

**สถานะไฟล์นี้**: บัตรความรู้ (RELAYED สำหรับส่วนที่บรรยาย service ของหน่วยงานภายนอก + VERIFIED
สำหรับสิ่งที่ worker นี้ดึงมาเอง) เขียนโดย worker แยกต่างหาก, ต่อมา**ผู้ commit หลักรับข้อเสนอทั้งหมด
แล้ว** (2026-09-27, build 6): `tools/kg/unit_resolver_draft.py` → `tools/kg/unit_resolver.py`
(promoted, draft ถูกลบ), เพิ่ม `sub_basin` node (359 โหนด) + edge `IN_SUBBASIN` (tag
`VERIFIED-geometric`) เข้า `tools/kg/build_kg.py` แล้ว, `sources/api_census.yaml` มีแถว
`dwr_gis_subbasin` แล้ว, `kb.py accountability` พิมพ์ sub-basin ที่ resolve ได้เป็นบรรทัดแรกแล้ว
— เนื้อหาด้านล่างเป็นบันทึกต้นฉบับของ worker ที่เสนองานนี้ ("ขั้นตอนต่อ" ท้ายไฟล์เป็นของเดิม
ตอนที่ยังไม่ commit, เก็บไว้เพื่อ traceability ไม่ได้ลบ)

## Service นี้คืออะไร

`gis.dwr.go.th/arcgis/rest/services` เป็น root ของ ArcGIS Server ของกรมทรัพยากรน้ำ (DWR) —
**ไม่มี authentication ใดๆ** (ยืนยันแล้ว, VERIFIED, เข้าถึงตรงผ่าน HTTP ธรรมดา) เห็น service list
25 รายการ (`raw/gis/dwr_subbasin/layer_info.json`, `arcgis_rest_root.json` จากงาน sweep ก่อนหน้า)

Layer ที่ใช้ในงานนี้: **`Sub_Basin/MapServer/0`** — polygon ของลุ่มน้ำสาขาทั่วประเทศ

- fields: `SB_CODE` (รหัสลุ่มน้ำสาขา 4 หลัก), `SB_NAME_T` (ชื่อไทย), `MB_CODE` (รหัสลุ่มน้ำหลัก
  2 หลัก), `MBASIN_T`/`MBASIN_E` (ชื่อลุ่มน้ำหลัก ไทย/อังกฤษ), `AREA_SQKM`, `Shape_Length`,
  `Shape_Area` — **VERIFIED** จาก `raw/gis/dwr_subbasin/layer_info.json`
- geometryType: Polygon (จริงพบเป็น MultiPolygon ในหลายแถว)
- CRS จัดเก็บจริงของ service: `EPSG:32647` (UTM zone 47N) — แต่คำขอของเราระบุ `outSR=4326`
  ทำให้ผลลัพธ์ GeoJSON เป็น **WGS84 (lon,lat) แล้ว** ไม่ต้อง reproject เพิ่ม — **VERIFIED**
  (ตรวจพิกัดจริงในไฟล์ตรงกับตำแหน่งภูมิศาสตร์ที่ควรเป็น)
- `maxRecordCount`: 2000 ต่อคำขอ
- **จำนวนทั้งหมด: 359 sub-basin** (ยืนยันด้วย `returnCountOnly=true` ก่อน page จริง) — **ดึงมาครบ
  ในหน้าเดียว** (359 < 2000) ไม่ต้อง page ต่อ — เก็บที่ `raw/gis/dwr_subbasin/page_0.geojson`
  (75 MB, gitignored ผ่าน `raw/` ที่มีอยู่แล้วใน `.gitignore`)
- **Layer แม่ (basin)**: ลองดึง `25_BASIN/MapServer/0` (ชื่อ layer จริงคือ `BASIN`) มาด้วย 1 ครั้ง
  ตามโจทย์ — พบว่าเป็นตารางระดับ**ลุ่มน้ำสาขา** เช่นกัน (254 แถว, field `SBASIN`/`SBASIN_T`/
  `SBASIN_E` + `MBASIN`/`MBASIN_T`/`MBASIN_E`) **ไม่ใช่ตาราง 22 ลุ่มน้ำหลักล้วนๆ** ตามที่คาด — ไม่ตรง
  1:1 กับ 359 แถวของ `Sub_Basin` (คนละชุด/คนละเวอร์ชันการแบ่งเขต, **OPEN** ว่าทำไมไม่ตรงกัน) — แต่
  **ไม่กระทบงานนี้** เพราะ `Sub_Basin` เองมี `MB_CODE`/`MBASIN_T`/`MBASIN_E` ติดมาในทุกแถวอยู่แล้ว
  จึงใช้ mapping ลุ่มน้ำสาขา→ลุ่มน้ำหลักจาก `Sub_Basin` ตรงๆ ได้โดยไม่ต้อง join กับ `25_BASIN`
- เก็บไว้ทั้งคู่ที่ `raw/gis/dwr_subbasin/basin_layer_info.json` + `basin_attrs.json`
  เผื่อใช้ cross-check ในอนาคต

## Licence / terms — **OPEN**

`copyrightText` ของ layer ว่างเปล่า (`""`) และในการ sweep รอบนี้ (งบ 6 คำขอ, ดู
`docs/knowledge/DATA_SWEEP_2026-09-27.md` §E) **ไม่พบหน้า licence/terms-of-use ของ
gis.dwr.go.th ที่ชัดเจน** — ไม่ได้ตามลิงก์ footer/about ทุกอันเพื่อประหยัดงบ — สถานะยังคง
**OPEN** เหมือนที่บันทึกไว้ก่อนหน้า, **ยังไม่ควรถือว่า cleared สำหรับ redistribution/publish
สาธารณะ** จนกว่าจะเช็คเพิ่ม (เขียนไว้ตรงๆ ใน `sources/dwr_subbasins.yaml` ด้วย)

## จำนวน / ไฟล์ที่ได้

| อะไร | จำนวน/ขนาด | path |
|---|---|---|
| Sub_Basin polygons ทั้งหมด | 359 features (1 หน้า, ครบ) | `raw/gis/dwr_subbasin/page_0.geojson` |
| ดัชนีสรุปไม่มี geometry | 359 แถว | `sources/dwr_subbasins.yaml` |
| Layer metadata | 1 ไฟล์ | `raw/gis/dwr_subbasin/layer_info.json` |
| Basin (25_BASIN) layer, cross-check | 254 แถว attribute-only | `raw/gis/dwr_subbasin/basin_attrs.json` |
| Harvest script (reusable) | — | `tools/harvest/dwr_subbasin.py` (`--offline` รัน rebuild ได้โดยไม่ยิง network ซ้ำ) |
| Resolver (จุด → หน่วย) | — | `tools/kg/unit_resolver_draft.py` |

**คำขอที่ยิงจริงในงานนี้**: 5 ครั้ง (`layer_info?f=json`, `returnCountOnly`, `page_0` query,
`25_BASIN` layer info, `25_BASIN` attrs) — หนึ่งคำขอต่อ URL, ไม่ retry, ตาม AGENTS.md

## ผลทดสอบ 6 จุด (MEASURED — จาก polygon จริง, จุดต่อจุด)

รันจริงด้วย `python3 -m tools.kg.unit_resolver_draft --self-test` (ผ่านทั้งเส้นทาง shapely
และเส้นทาง pure-Python fallback — ผลตรงกันทั้งคู่):

| จุดทดสอบ | lat,lon | sb_code | ชื่อลุ่มน้ำสาขา | ลุ่มน้ำหลัก | area_km2 |
|---|---|---|---|---|---|
| สัมมากร (กทม.) | 13.758235, 100.676084 | **1002** | ที่ราบแม่น้ำเจ้าพระยา | เจ้าพระยา / Chao Phraya | 15,688.53 |
| เทศบาลนครหาดใหญ่ | 7.008765, 100.474455 | **2003** | ทะเลสาบสงขลา (ลุ่มน้ำสาขา) | ทะเลสาบสงขลา / Thale Sap Songkhla | 3,368.11 |
| เมืองน่าน | 18.783958, 100.773636 | **0905** | แม่น้ำน่านส่วนที่ 2/2 | น่าน / Nan | 434.70 |
| เมืองเชียงใหม่ | 18.787747, 98.993128 | **0607** | แม่น้ำปิงส่วนที่ 2/2 | ปิง / Ping | 740.90 |
| บางบาล (อยุธยา) | 14.573611, 100.548333 | **1002** | ที่ราบแม่น้ำเจ้าพระยา | เจ้าพระยา / Chao Phraya | 15,688.53 |
| จุดในทะเลอ่าวไทย | 10.5, 101.0 | **None** | — (นอกทุก polygon ที่มี, tag OPEN — "อาจเป็นทะเล") | — | — |

หมายเหตุ: สัมมากรกับบางบาลตกอยู่ใน sub-basin เดียวกัน (`1002`, "ที่ราบแม่น้ำเจ้าพระยา") — DWR
แบ่งพื้นที่ราบลุ่มเจ้าพระยาตอนล่างทั้งหมดเป็น sub-basin เดียวขนาดใหญ่ (15,688 ตร.กม.) ไม่ได้แยกย่อย
ระดับตำบล/อำเภอ — **นี่คือความละเอียด (granularity) จริงของชุดข้อมูลนี้**, ไม่ใช่ข้อผิดพลาดของ resolver
— ถ้าต้องการหน่วยละเอียดกว่านี้ (เขต/แขวง กทม.) ต้องใช้แหล่งอื่นร่วมด้วย (เช่น
`sources/bkk_district_elevation.yaml` ที่มีอยู่แล้วในกราฟ)

## แทนที่ radius-fallback INSTINCT ใน PROP-FLOOD-06 ได้อย่างไร

`raw/backtest/units.yaml` (หมายเหตุ HATYAI) และเอกสารวางแผนก่อนหน้าใช้ **รัศมีวงกลมรอบจุดศูนย์กลาง
(radius, INSTINCT)** เป็น proxy ของ "หน่วยลุ่มน้ำ" เพราะตอนนั้นยังไม่มี polygon จริง — ตอนนี้มี
polygon ทางการของ DWR แล้ว การตรวจว่าจุดหนึ่งอยู่ใน polygon ไหน (point-in-polygon กับ polygon
จริงจากหน่วยงาน) เป็น **ข้อเท็จจริงเชิงเรขาคณิต (MEASURED) จาก polygon ทางการ** ไม่ใช่การ "snap"
หรือประมาณระยะทาง — จึงเข้าเงื่อนไข "ไม่ใช่การ snapping ที่ AGENTS.md ห้าม" (การ snap/geocode/
infer ที่ AGENTS.md ระวังคือการ "เดา"/"ประมาณ" จุดหรือความสัมพันธ์ที่ไม่มีหลักฐาน — แต่นี่คือการ
สอบถามว่าจุดพิกัดที่มีอยู่แล้วตกอยู่ใน polygon เรขาคณิตจริงหรือไม่ ซึ่งเป็นการวัด ไม่ใช่การเดา)

**ข้อเสนอ**: ให้ `resolve_unit(lat, lon)` (หรือ logic เดียวกัน wired เข้า `unit_resolver` จริง)
แทนที่ radius-fallback ทุกจุดที่ PROP-FLOOD-06 เรียกใช้ตอนนี้ — radius-fallback เหลือไว้เป็น
**fallback ชั้นสอง** เฉพาะกรณีจุดตกนอกทุก polygon (ทะเล/นอกขอบเขต DWR) เท่านั้น ไม่ใช่ path หลักอีกต่อไป

## Edge class ที่เสนอ (ยังไม่ implement — ผู้ commit ตัดสินใจ)

`IN_SUBBASIN` — asset (จาก `assets` table) → `sub_basin` node (ใหม่, จาก
`sources/dwr_subbasins.yaml`) — สร้างจาก point-in-polygon ของพิกัดจริงของ asset กับ polygon จริง
ของ DWR — **tag ที่เสนอ: `VERIFIED-geometric`** (แยกจาก `VERIFIED` ธรรมดา เพื่อบอกชัดว่านี่คือ
ผลจากการคำนวณ point-in-polygon ไม่ใช่การอ่านค่าจาก field ตรงๆ ของ source — ตาม `tools/kg/README.md`
เอง edge อื่นๆ เช่น `IN_BASIN`/`IN_DISTRICT` ใช้ exact-string-match "never geocoded/inferred";
`IN_SUBBASIN` ต่างออกไปตรงที่เป็น geometric containment กับ polygon ทางการ — จึงควรมี tag
ของตัวเองเพื่อไม่ให้ปนกับ two families นั้น) — ผู้ commit เป็นผู้ตัดสินใจสุดท้ายว่าจะรับ tag ใหม่
นี้เข้า schema หรือไม่

## ขั้นตอนต่อสำหรับผู้ commit (ยังไม่ทำในงานนี้ — DRAFT เท่านั้น)

1. **`sources/api_census.yaml`**: อัปเดตแถว `dwr_*` ที่เกี่ยวข้อง (หรือเพิ่มแถวใหม่
   `dwr_gis_subbasin`) ให้ `status: connected`, `tag: VERIFIED`, อ้างถึง
   `sources/dwr_subbasins.yaml` + `tools/harvest/dwr_subbasin.py` — **ยังไม่แก้ไฟล์นี้ในงานนี้**
   (worker นี้ไม่แตะไฟล์เดิม ตามกติกาที่ได้รับ)
2. **KG (`tools/kg/build_kg.py`)**: เพิ่ม loader ใหม่ที่:
   a. โหลด `sources/dwr_subbasins.yaml` → สร้าง node `kind: sub_basin` ต่อแถว (`sb_code`,
      `name_th`, `basin_code`, `basin_name_th`/`basin_name_en`, `area_km2`, `tag`) — ไม่มี
      geometry inline ใน node เอง (ตาม pattern ของ node อื่นในกราฟ)
   b. สำหรับทุก asset ที่มี `lat`/`lon` จริง เรียก `tools/kg/unit_resolver_draft.resolve_unit()`
      (หรือย้ายมาเป็น non-draft module ก่อน) แล้วเติม edge `IN_SUBBASIN` → `sub_basin` node ที่ตรง
      — asset ที่ resolve ไม่ได้ (ทะเล/นอกขอบเขต) **ไม่สร้าง edge** ไม่ fabricate
   c. ตรวจ `docs/knowledge/README.md`'s edge-kind list (`tools/kg/README.md`'s Edge schema
      table) ให้เพิ่มแถว `IN_SUBBASIN` ตามรูปแบบเดียวกับแถวอื่น
3. **`tools/kg/unit_resolver_draft.py` → non-draft**: ถ้าตัดสินใจรับ ให้ย้าย/rename เป็นโมดูล
   จริง (ตัดคำ `_draft`) แล้วอัปเดตจุดอ้างอิงใน `accountability.py`/`build_river_kg.py` ที่ปัจจุบันยังใช้
   radius-fallback (ดูหัวข้อ "แทนที่ radius-fallback" ด้านบน)
4. **ทดสอบ**: `python3 -m pytest tests/test_dwr_subbasin.py -q` (11 ผ่านแล้วในงานนี้) +
   full suite ครั้งเดียวก่อน commit จริง ตาม "no repeated full-arc audits"

## Known gaps / OPEN

- Licence/terms ของ `gis.dwr.go.th` — **OPEN**, ห้ามใช้บน public page จนกว่าจะเช็ค
- `25_BASIN` service ไม่ตรงกับ 22-25 ลุ่มน้ำหลักตามที่คาด (254 แถวระดับ sub-basin) — **OPEN**
  ว่าทำไมไม่ตรงกับ `Sub_Basin`'s 359 แถว (คนละ vintage/revision ของการแบ่งเขตหรือไม่ — ไม่ได้
  ตรวจต่อในงบนี้)
- pure-Python fallback (เมื่อไม่มี shapely) **ไม่ตัด hole ออกจาก polygon** — จุดที่อยู่ใน "รู"
  ของ polygon (ถ้ามีในข้อมูลจริง) จะรายงานผิดว่าอยู่ในลุ่มน้ำนั้น — เอกสารไว้ใน docstring ของ
  `tools/kg/unit_resolver_draft.py` และมี test คุมพฤติกรรมนี้ตรงๆ ใน `tests/test_dwr_subbasin.py`
  (`test_hole_polygon_shapely_excludes_hole`, skip อัตโนมัติถ้าไม่มี shapely)
- EWS (~1,500+ หมู่บ้าน) history — ยังไม่พบ service — อยู่นอกขอบเขตงานนี้ (ดู
  `docs/knowledge/DATA_SWEEP_2026-09-27.md` §E เดิม)
