# API/ชุดข้อมูลฟรีระดับโลก สำหรับดินถล่ม-น้ำท่วมล่วงหน้า (ยุบลงมาไทย)

**คำสั่งของ founder (verbatim, 2026-09-27 15:38):** "ตรวจหา api ที่แจกฟรีของโลกก่อน แล้วยุบลงมาไทย
เพื่อเชื่อมเข้ากับระบบ" -- เป้าหมาย: อินพุตสำหรับ (1) ดินถล่ม/โคลนถล่มที่เกิดจากฝน และ (2)
เตือนภัยน้ำท่วมล่วงหน้า

**เพิ่ม 15:41:** "โมเดลการพยากรณ์ของโลกก็มี ฝนฟ้า อื่นๆ ที่ฟรีเข้าถึงได้ ของ WHO ถ้ามีก็เลือกมาแล้ว
โฟกัสที่ไทย" -- ขยายให้ครอบคลุมโมเดลพยากรณ์อากาศ (NWP/ensemble) ทั้งหมดที่ฟรี บวกแหล่งของ
WHO/WMO/UN

ไฟล์นี้เป็น**การสำรวจ (census) + ข้อเสนอ**เท่านั้น -- ไม่มีการ implement ใน `collect.py` งานนี้
รายการดิบทั้งหมด (schema เต็ม, field `thailand_q`, `notes`, `tag`) อยู่ที่
`sources/api_census.yaml` ส่วนท้าย (25 แหล่งใหม่, ต่อจาก census ของแหล่งไทยเดิม) --
ไฟล์นี้เป็นสรุปอ่านง่ายภาษาไทยของรายการเดียวกัน

Epistemic tag ทุกแถว: VERIFIED = task นี้ดึงเองจริงและเห็น payload / MEASURED = วัดจากการรันจริง
งานนี้ (รวมถึงความล้มเหลวที่สังเกตได้ เช่น HTTP error) / RELAYED = เห็นจาก WebSearch/เอกสาร
เท่านั้น ยังไม่ได้ดึงเอง / OPEN = ยังไม่ยืนยันได้ภายในงบ probe ของ task นี้

---

## ตารางแหล่งข้อมูลทั้งหมด (global, ก่อนยุบลงไทย)

| id (ดู api_census.yaml) | หมวด | ฟรี? | Thailand bbox coverage | tag |
|---|---|---|---|---|
| `nasa_lhasa_landslide_nowcast` | ดินถล่ม nowcast รายวัน 1km | free-with-account (Earthdata) | global grid รวมไทย | RELAYED |
| `nasa_global_landslide_catalog` | เหตุการณ์ดินถล่มย้อนหลัง | free, no key | global point รวมไทย | RELAYED |
| `nasa_power_api` | ฝน/อุตุฯ รายวันจากดาวเทียม | free, no key | global point ใดๆ ในไทย | **VERIFIED (ดึงจริง)** |
| `opentopography_copernicus_dem_glo30` | DEM โลก 30m | free-with-key (instant) | global 30m รวมไทย | RELAYED |
| `copernicus_glofas_cems` | ต้นทางน้ำท่วมโลก (ทางการ) | free-with-account (CDS/MARS) | global river network รวมลุ่มเจ้าพระยา | RELAYED |
| `google_flood_hub_api` | พยากรณ์น้ำท่วมแม่น้ำ (Google) | free แต่ waitlist เท่านั้น | อ้าง >150 ประเทศ ยังไม่ยืนยันแม่น้ำในไทย | RELAYED |
| `openmeteo_flood_api` | GloFAS ผ่าน Open-Meteo (ไม่ต้อง key) | free, no key | global 5km cell รวมไทย | **VERIFIED (ดึงจริง)** |
| `openmeteo_ensemble_api` | ฝนแบบ ensemble หลายสมาชิก | free, no key | global รวมไทย | **VERIFIED (ดึงจริง)** |
| `openmeteo_marine_api` | ระดับน้ำทะเล/tide | free, no key | ชายฝั่งอ่าวไทย 8km | **VERIFIED (ดึงจริง)** |
| `openmeteo_multimodel_thailand` | รายชื่อโมเดล NWP ทั้งหมดที่ Open-Meteo เปิดฟรี | free, no key | global รวมไทย (ไม่มี regional high-res เฉพาะไทย) | RELAYED |
| `jrc_global_surface_water` | แผนที่น้ำผิวดินย้อนหลัง 1984- | free, no key | global 30m รวมไทย | RELAYED |
| `esa_worldcover` | สิ่งปกคลุมผิวดิน 10m | free, no key | global 10m รวมไทย | RELAYED |
| `gfw_data_api` | ป่าไม้เสียหาย (GLAD/RADD) | free-with-key (self-service) | global รวมไทย | RELAYED |
| `gdacs_api` | แจ้งเตือนภัยพิบัติหลายประเภททั่วโลก | free, no key | global รวมไทย | RELAYED |
| `reliefweb_api` | รายงานภัยพิบัติ/มนุษยธรรม | free, no key | global รวมไทย | **MEASURED (ดึงจริง, พบ v1 ถูกยกเลิกแล้ว)** |
| `unosat_flood_portal` | แผนที่น้ำท่วมจากดาวเทียม (ต่อเหตุการณ์) | free, ไม่มี REST API ชัดเจน | เปิดใช้เฉพาะเมื่อมีเหตุการณ์ใหญ่ | RELAYED |
| `soilgrids_isric_rest` | ความชื้นในดิน | free, no key (แต่ API หยุดชั่วคราว) | global 250m รวมไทย | RELAYED |
| `osm_overpass_quarry` | เหมือง/บ่อขุด (crowd-sourced) | free, no key | ครอบคลุมไม่สม่ำเสมอในไทย | RELAYED (กติกาเดิม: ใช้เป็น gap-filler เท่านั้น) |
| `who_gho_odata_api` | สถิติสุขภาพรายประเทศ | free, no key (แต่กำลังจะเลิกใช้) | ระดับประเทศเท่านั้น | RELAYED |
| `who_disease_outbreak_news` | ข่าวการระบาดของโรค | free | รายประเทศเมื่อมีประกาศ | OPEN |
| `wmo_swic_cap_warnings` | ศูนย์รวมประกาศเตือนภัยอากาศ (relay กรมอุตุฯ) | free | relay ของไทยเอง | OPEN |
| `wmo_whos_hydrology` | ข้อมูลอุทกวิทยาแบบสหพันธ์ | free | ไม่ยืนยันว่าไทยเข้าร่วม | OPEN |
| `undrr_desinventar` | ฐานข้อมูลความสูญเสียจากภัยพิบัติ | free (ไม่พบ REST API สาธารณะ) | ไม่ยืนยันว่ามี instance ไทยที่ใช้งานได้ | OPEN |
| `ifrc_go_api` | ปฏิบัติการกาชาดสากล | ไม่ยืนยัน auth | ปฏิบัติการกาชาดไทยเมื่อมี | OPEN |
| `cds_era5_reanalysis` | ภูมิอากาศย้อนหลังตั้งแต่ 1940 | free-with-key | global รวมไทย | RELAYED |

---

## ยุบลงไทย: อันดับตามคุณค่า/ความพยายาม (value/effort)

ตอบ 5 คำถามของ founder: (a) ความเสี่ยงดินถล่มจากฝนตอนนี้ (b) พยากรณ์ฝน/น้ำ 1-5 วันข้างหน้า
เหนือ กทม. (c) ภูมิประเทศ/ทางน้ำไหล (d) กองดิน/เหมือง/ป่าเสีย (e) เหตุการณ์ย้อนหลังเพื่อยืนยัน
(f) โมเดลพยากรณ์อากาศ NWP/ensemble (g) น้ำขึ้นน้ำลง/ระดับทะเล (h) สุขภาพ/โรคระบาดหลังน้ำท่วม

**Tier 1 -- ฟรีไม่ต้อง key, ดึงได้ทันที, ตรวจสอบแล้ว (VERIFIED/MEASURED งานนี้):**

1. `openmeteo_flood_api` (b) -- GloFAS ผ่าน Open-Meteo, ไม่ต้อง key, ได้ river discharge
   7-30 วันล่วงหน้า จุดใดก็ได้ในไทย รวมต้นน้ำเจ้าพระยา/แม่กลอง เหนือ กทม.
2. `openmeteo_ensemble_api` (f, b) -- ฝนแบบ ensemble หลายสมาชิก ให้ "ความน่าจะเป็น" แทน
   ตัวเลขเดี่ยว ซึ่งเป็นการยกระดับของจริงจาก endpoint เดี่ยวที่ collect.py ใช้อยู่ตอนนี้
3. `nasa_power_api` (a, f) -- ฝนดาวเทียมสำรอง จุดใดก็ได้ ใช้ตรวจสอบไขว้กับ Open-Meteo
   หรือเติมพื้นที่ภูเขาที่ไม่มีสถานีวัดฝนของไทยครอบคลุม
4. `openmeteo_marine_api` (g) -- ระดับน้ำทะเล/tide proxy ปากแม่น้ำเจ้าพระยา (ความละเอียด
   หยาบ 8km, ไม่แทนตารางน้ำขึ้นน้ำลงที่แม่นยำ)
5. `reliefweb_api` (e) -- รายงานเหตุการณ์น้ำท่วมไทยในอดีตเพื่อยืนยัน (ต้องใช้ v2 ไม่ใช่ v1)
6. `gdacs_api` (e, b) -- สัญญาณเตือนภัยพิบัติหลายประเภททั่วโลกแบบ near-real-time ไม่ต้อง key

**Tier 2 -- ฟรีแต่ต้องมี key ทันที (self-service, ไม่ใช่ waitlist):**

7. `opentopography_copernicus_dem_glo30` (c) -- DEM 30m สำหรับสร้าง flow-path ต้นน้ำ
   Sammakorn (ต้องสมัคร OpenTopography key เอง, ทันที)
8. `gfw_data_api` (d) -- แจ้งเตือนป่าไม้เสียหายใกล้เรียลไทม์ (GLAD/RADD) สำหรับความเสี่ยง
   ดินถล่มจากพื้นที่ป่าโล่ง/เหมือง
9. `cds_era5_reanalysis` (a, e) -- climatology ย้อนหลังตั้งแต่ 1940 สำหรับวัดว่าพายุปัจจุบัน
   ผิดปกติแค่ไหนเทียบสถิติ

**Tier 3 -- ต้องรออนุมัติ/ไม่ self-service:**

10. `google_flood_hub_api` (b, e) -- ต้องรอคิว pilot ของ Google (ยืนยันสถานะซ้ำ: ยังไม่เปลี่ยน)
11. `nasa_lhasa_landslide_nowcast` (a) -- คุณค่าสูงสุดสำหรับดินถล่ม nowcast แต่ต้องสมัคร
    NASA Earthdata (ฟรี แต่ไม่ใช่ key ทันที) หรือรันโมเดล open-source เอง (nasa/LHASA บน
    GitHub) จากอินพุตฝน+susceptibility ของเราเอง

**Tier 4 -- ทำเป็น context/สำรอง เท่านั้น (OPEN/ไม่ชัดเจนสถานะ):**

`who_gho_odata_api`, `who_disease_outbreak_news`, `wmo_swic_cap_warnings`,
`wmo_whos_hydrology`, `undrr_desinventar`, `ifrc_go_api`, `unosat_flood_portal`,
`soilgrids_isric_rest` (API หยุดชั่วคราว), `jrc_global_surface_water`, `esa_worldcover`,
`osm_overpass_quarry` (ตามกติกาเดิม: RELAYED gap-filler เท่านั้น) --
มีประโยชน์แต่ไม่ใช่อินพุตแบบต่อเนื่องรายชั่วโมง/วัน

---

## โมเดลพยากรณ์อากาศโลก (NWP/ensemble) ที่ Open-Meteo เปิดให้ฟรี -- โฟกัสไทย

Open-Meteo เดียวเป็นประตูเดียวที่รวมโมเดลของหน่วยงานอุตุฯ ระดับชาติ >15 แห่งไว้ ไม่ต้อง key
ทุกโมเดล เข้าถึงได้ผ่าน `&model=` (หรือ `best_match` ให้เลือกอัตโนมัติ):

- **ระดับชาติ (deterministic):** `ecmwf_ifs` (ECMWF, ยุโรป), `gfs_seamless` (NOAA
  GFS/NOMADS, สหรัฐฯ), `icon_seamless` (DWD, เยอรมนี), `jma_seamless` (JMA GSM/MSM,
  ญี่ปุ่น), `gem_seamless` (แคนาดา), `ukmo_seamless` (สหราชอาณาจักร),
  `bom_access_global` (ออสเตรเลีย), `cma_grapes_global` (จีน), `meteofrance_seamless`
  (ฝรั่งเศส -- ส่วน AROME ความละเอียดสูงครอบคลุมเฉพาะยุโรป ส่วน ARPEGE ระดับโลกใช้กับ
  ไทยได้), `knmi_seamless`, `dmi_seamless`, `metno_seamless`
- **AI models:** ECMWF **AIFS** (โมเดล AI ของ ECMWF เอง, step ราย 6 ชม.), Google DeepMind
  **GraphCast** และ **WeatherNext 2** (ensemble AI 64 สมาชิก, grid 0.25 องศา, พยากรณ์ถึง
  15 วัน) -- ทั้งหมดผ่าน Open-Meteo โดยไม่ต้อง key
- **Ensemble (probability):** `/v1/ensemble` -- ICON-EPS, GFS-ENS, ECMWF-ENS, GEM-EPS
  (สูงสุด 51 สมาชิกต่อโมเดล, ขอบฟ้าถึง 35 วัน)
- **ที่ไม่ครอบคลุมไทย:** โมเดล regional ความละเอียดสูงพิเศษ (ICON-D2, HRRR, AROME) ครอบคลุม
  เฉพาะยุโรป/อเมริกาเหนือ -- ไทยได้แค่โมเดลระดับโลก (9-11km) ไม่มีตัวความละเอียดสูงเฉพาะภูมิภาค
  ในชุดฟรีนี้

**สถานะปัจจุบันของ collect.py (ตรวจแล้ว, ดู `parsers.py` บรรทัด ~589):** เรียก
`api.open-meteo.com/v1/forecast` แบบไม่ระบุ `model=` เลย (ใช้ default `best_match` โดย
ปริยาย) -- **ไม่ใช่ "6 โมเดล" อย่างที่สมมติไว้ในคำสั่ง founder** เป็นโมเดลเดียว (auto-selected)
ต่อการรันหนึ่งครั้ง ข้อเท็จจริงนี้เป็น MEASURED จากการอ่านโค้ดจริง ไม่ใช่การเดา

**อันดับ skill สำหรับไทยเฉพาะ (OPEN -- ยังไม่มีแหล่งไหนใน task นี้ยืนยัน verified skill
score เฉพาะจุดในไทย):** ไม่มีแหล่งใดที่ค้นเจอระบุ skill score เฉพาะประเทศไทย/ภูมิภาคเอเชีย
ตะวันออกเฉียงใต้อย่างเป็นทางการภายในงบ fetch ของ task นี้ -- **ห้ามอ้างจากความจำว่าโมเดลไหน
"แม่นกว่า" สำหรับไทย** จนกว่าจะมีแหล่งที่ระบุไว้จริง (เช่น WMO verification reports หรือ
ECMWF forecast verification เฉพาะภูมิภาค SE Asia ซึ่งยังไม่ได้ค้นในงานนี้) -- tag: OPEN

---

## แหล่งของ WHO/WMO/UN (คำสั่ง founder 15:41)

| แหล่ง | ให้อะไร | ความเหมาะกับระบบนี้ |
|---|---|---|
| WHO GHO OData API | สถิติสุขภาพรายประเทศ, กำลังจะเลิกใช้ปลายปี 2025 | อ่อนแอสุดในกลุ่ม -- ไม่ใช่ feed ต่อเหตุการณ์น้ำท่วม |
| WHO Disease Outbreak News | ข่าวโรคระบาดต่อเหตุการณ์ | มีประโยชน์ถ้า WHO ประกาศโรคหลังน้ำท่วมไทย (เช่น leptospirosis) แต่ไม่ต่อเนื่อง |
| WMO SWIC (CAP warnings) | relay ประกาศเตือนภัยของกรมอุตุฯ ไทยเอง | เป็นแค่ mirror สำรอง ไม่ใช่แหล่งอิสระที่สอง |
| WMO WHOS/HydroHub | สหพันธ์ข้อมูลอุทกวิทยา | ไม่ยืนยันว่าหน่วยงานไทยเข้าร่วม -- ความสำคัญต่ำ (มี RID/HII ตรงอยู่แล้ว) |
| UNDRR DesInventar | ฐานข้อมูลความสูญเสียจากภัยพิบัติ | ไม่ยืนยัน instance ไทยที่ใช้งานได้จาก REST |
| IFRC GO API | ปฏิบัติการกาชาดสากล | สัญญาณผลกระทบ/การตอบสนอง ไม่ใช่พยากรณ์ภัย |

**สรุป:** กลุ่ม WHO/WMO/UN ให้คุณค่าต่ำกว่ากลุ่ม NASA/Copernicus/Open-Meteo อย่างชัดเจน
สำหรับเป้าหมายเฉพาะของระบบนี้ (ดินถล่ม+น้ำท่วมล่วงหน้า) -- มีประโยชน์เป็น context ชั้นรอง
(สุขภาพ, ผลกระทบด้านมนุษยธรรม) มากกว่าจะเป็นอินพุตหลัก

---

## รายการ collector ที่เสนอสำหรับ collect.py (ชื่อ + cadence + ประมาณแถว/วัน) -- **ยังไม่ implement**

| ชื่อที่เสนอ | cadence | ประมาณแถว/วัน | ให้อะไร |
|---|---|---|---|
| `collect_openmeteo_flood` | ทุก 6 ชม. (4 ครั้ง/วัน) | ~4 แถว/จุด (7 วันข้างหน้า/ครั้ง, เก็บแค่ snapshot ล่าสุด) | river_discharge GloFAS จุดต้นน้ำ+ Sammakorn |
| `collect_openmeteo_ensemble` | ทุก 6 ชม. | ~4 แถว/จุด (หลายสมาชิกต่อแถว) | ฝนแบบความน่าจะเป็น แทน/เสริมของเดิม |
| `collect_openmeteo_marine` | ทุก 6 ชม. | ~4 แถว | ระดับน้ำทะเล proxy ปากแม่น้ำ |
| `collect_nasa_power` | 1 ครั้ง/วัน | 1 แถว/จุด | ฝนดาวเทียมสำรองจุดภูเขา |
| `collect_gdacs` | ทุก 6 ชม. (poll RSS) | 0-หลายแถว ตามเหตุการณ์ | trip-wire ภัยพิบัติ |
| `collect_reliefweb` | 1 ครั้ง/วัน (v2 endpoint) | 0-5 แถว | เหตุการณ์ใหม่ที่เกี่ยวข้องกับไทย |

ทุกตัวข้างต้นเป็น**ข้อเสนอ** -- ต้องผ่าน review/maker-checker และเพิ่มลง
`sources/registry.yaml` + ทดสอบ + fixture ก่อน ตาม `AGENTS.md` §5 จึงจะ wire เข้า collect.py
จริง งานนี้ไม่ได้แตะ `sources/registry.yaml` หรือ `collect.py` เลย

---

## สิ่งที่ยังต้องใช้ข้อมูลหน่วยงานไทยเอง -- ไม่มี API โลกไหนแทนได้

- **เกณฑ์เตือนภัยดินถล่มของกรมทรัพยากรธรณี (DMR)** ต่อหมู่บ้าน/ตำบล -- LHASA ให้แค่ nowcast
  ระดับโลก 1km ไม่ใช่เกณฑ์ปฏิบัติการที่ DMR ประกาศเป็นทางการสำหรับพื้นที่เสี่ยงภัยที่ขึ้นทะเบียนไว้
- **รายชื่อหมู่บ้านเสี่ยงภัยดินถล่มของ DMR** -- ไม่มีแหล่งโลกไหนมีรายชื่อระดับหมู่บ้านของไทย
- **สัมปทานเหมือง/บ่อขุดของกรมอุตสาหกรรมพื้นฐานและการเหมืองแร่ (DPIม)** -- OSM Overpass
  ให้แค่ gap-filler แบบ crowd-sourced (RELAYED เท่านั้นตามกติกาเดิม); DPIM's ข้อมูลสัมปทาน
  จริงเป็นทางการเดียวที่ยืนยันได้ว่าเหมือง/บ่อขุดจุดไหน "ถูกกฎหมาย" และเปิดดำเนินการอยู่จริง
- **ระดับ/สถานะประตูระบายน้ำ กทม. แบบเรียลไทม์** -- ยังเป็น OPEN ในระบบนี้เอง
  (`AGENTS.md` §8), ไม่มี API โลกไหนรู้สถานะประตูภายในของ กทม.

---

*ดูสรุปภาษาอังกฤษของ workflow นี้ใน `sources/api_census.yaml` (header comment ของ section
ใหม่) -- ไฟล์นี้คือฉบับอ่านง่ายภาษาไทย ไม่ใช่แหล่งข้อมูลสำรอง (canonical อยู่ที่ api_census.yaml)*
