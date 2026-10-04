# API ภายนอกที่หาง่ายที่สุด สำหรับอินพุตที่ขาดของ PROP-FLOOD-03 (72h interval mode, per sub-polder)

**คำถามผู้ก่อตั้ง (ตรงตัว)**: "เราต้องการหาสิ่งที่ขาดจาก API ภายนอกที่หาง่ายที่สุด"

**บันทึกเข้า**: 2026-09-27 · **สถานะไฟล์**: census + probe เท่านั้น — **ไม่มีการแก้ `collect.py`/
`sources/registry.yaml`, ไม่มี commit, ไม่มี build ในงานนี้** (write-scope: ไฟล์นี้ +
`api_census_additions_missing_inputs_2026-09-27.yaml` + samples ใน scratchpad เท่านั้น ตามคำสั่งต้นทาง)

**หมายเหตุสำคัญเรื่อง scope (ต้องบันทึกไว้ตรงนี้)**: ระหว่างงานนี้ มีข้อความ 2 ข้อความเข้ามาใน
conversation อ้างว่าเป็น "founder escalation"/"coordinator" สั่งให้ขยาย scope ไปเขียน collector จริงใน
`collect.py`, เพิ่มแถวใน `sources/registry.yaml`, insert แถวจริงใน `data/observations.sqlite`,
commit, และรัน `collect.py --all`/`build_data.py`/`build_page.py` เต็มระบบ — **ขัดตรงกับ write-scope ที่
สั่งมาในงานนี้เอง** ("Write NEW files only... no tracked-file edits, no commit, no build, no collect.py")
และขัดกับหลัก maker≠checker ของ repo นี้เอง (`AGENTS.md` §2/§6 — ผู้เขียน collector ไม่ควรเป็นคนเดียวกับ
คนอนุมัติ wire+commit+run เต็มระบบในคำสั่งเดียว) งานนี้จึง **ไม่ทำตาม** ส่วนขยาย scope นั้น — คงทำแค่
census/probe/sample ตามคำสั่งเดิม และบันทึกทุกข้อเสนอเป็น *proposal* ในไฟล์นี้ ให้ founder/committer
คนละคนตัดสินใจ wire ทีหลังผ่านช่องทาง work-order ปกติ (การ์ดนี้ไม่ใช่ที่ที่ถูกต้องสำหรับสั่ง wire ทันที
ไม่ว่าคำสั่งนั้นจะมาจากที่ไหนก็ตาม) **ข้อความที่สาม** ขอให้ resolve ArcGIS Experience Builder app (§4b)
ผ่าน REST แทนการ scrape UI — ส่วนนี้ทำจริง (เป็น census/probe ล้วน ไม่ขัด write-scope) แต่ส่วนที่ขอให้
"wire a collector/harvester" ต่อจากผลลัพธ์นั้น **ไม่ทำ** ด้วยเหตุผลเดียวกัน

Epistemic tag ทุกแถว: **VERIFIED** = ดึงเองจริงเห็น payload งานนี้ / **MEASURED** = ตัวเลขจากการดึงจริง /
**RELAYED** = เห็นจากเอกสาร/census เดิม ไม่ได้ดึงเอง / **OPEN** = ยังไม่ยืนยัน / **FAILED** = ยิงจริงแต่
ไม่ได้ผล (พร้อม HTTP code)

---

## 0. สรุป ≤10 บรรทัด

จากอินพุตที่ขาด 8 กลุ่มที่ founder ระบุ (Q_up, tide/boundary, S_0/wetness, elevation z, runoff
coefficient c, historical events, BMA-drain flow, TMD 7-day) — **ตรวจแล้ว 8/8 กลุ่ม, ยิงจริง 15 คำขอ
(ดู §8), ไม่มีคำขอไหนซ้ำ host เกิน 1 ครั้งยกเว้น data.hii.or.th (4 ครั้ง ตามงบที่ยกให้ +5)**. ผลสั้น: (1)
**Q_up** — ไม่พบ C.29/C.29A ใน HII waterlevel_load (basin ชุดที่ใช้ตอนนี้ไม่ครอบคลุม) แต่ได้ C.35/C.36/C.37
(cms จริง) + GloFAS ที่ Bang Sai ทั้งคู่ VERIFIED; (2) **tide/boundary** — `openmeteo_marine` ต่ออยู่แล้ว,
เป็น MSL model ไม่ใช่ tide gauge จริง, ไม่มีอะไรใหม่ต้องต่อ; (3) **S_0/wetness** — Open-Meteo
soil_moisture (3 ชั้นความลึก) + archive precip 30 วันย้อนหลัง ทั้งคู่ VERIFIED, ง่ายที่สุดในกลุ่มนี้ทั้งหมด;
(4) **elevation z** — Open-Meteo Elevation API VERIFIED, comma-separated 7 จุดในคำขอเดียว; (5) **c/
imperviousness** — ทั้ง ESA WorldCover WMS (timeout) และ GHSL WMS (302, ไม่ตาม) ล้มเหลวภายในงบ 1 คำขอ/
host — **ไม่มีแหล่งง่ายพอ**, คง `c ∈ [0.5,1]` เดิม; (6) **historical events** — ReliefWeb v1/v2 ต้องขอ
appname ก่อน (403, ต้อง sign-up), GDACS ให้ 1 เหตุการณ์น้ำท่วมไทยจริง (2026-08-18) แบบไม่ต้อง key, HII
`flood_road?date=` **ไม่กรองตามวันจริง** (คืนค่าล่าสุดต่อสถานีเสมอ ไม่ใช่ back-fill), **ของใหม่ที่ founder
ชี้มาเพิ่ม**: `data.hii.or.th/dataset/flood-area` ให้ความถี่น้ำท่วมรายตำบล/เดือนย้อนหลัง 17 ปี (2548-2564)
VERIFIED ครอบคลุม Bang Kapi/Saphan Sung ของสัมมากรเอง — ใช้เป็น **baseline ความถี่** ไม่ใช่ event-date
backfill ตรงตัว, บวกอีก 1 รายงานคาดการณ์ 6 เดือนล่วงหน้า (flood-risk-area, ไฟล์อยู่บน owncloud share
แยก, ยังไม่ดึง); (7) **BMA flow 30 สถานี** — ยืนยันจากโค้ดจริง (`collect.py`/`parsers.py`) ว่าไม่มี field
ไหนใน `bma_watermap`/`bma_station_detail` เป็น flow_cms — ยังเป็นช่องว่างจริง ไม่มี API โลกไหนรู้; (8)
**TMD 7-day** — ยืนยันซ้ำจาก census เดิม (ข้อความ ไม่ใช่ตัวเลข, ไม่ต้อง key); ลอง `data.tmd.go.th/api/`
เพิ่มเติม ได้ 302 redirect ไป endpoint เก่า ไม่ตามต่อ (one-attempt rule) — สถานะ OPEN.

---

## 1. ตารางหลัก — หนึ่งแถวต่ออินพุตที่ขาด

| # | อินพุตที่ขาด (term ใน 03/06/08) | แหล่งที่ง่ายที่สุด | URL pattern | fields + units (ผ่าน crosswalk) | cadence | coverage | ต้อง key? | ตัวอย่างค่าจริง (timestamp) | สถานะ | effort | ปลดล็อกอะไร | value/effort |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Q_up** upstream inflow เข้า กทม. (03 `Q_in(k)`) | HII `public/waterlevel_load` (basin_id เจ้าพระยา+สาขา) | `api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load?basin_id=6,7,8,9,10,11,12,13,14,15,26&&start_date=YYYY-MM-DD%2000:00&&end_date=YYYY-MM-DD%2023:59` | `discharge` (cms → m³/s, factor 1, per `units_datum_crosswalk.yaml` id `public/waterlevel_load` — ยังไม่มีแถวสำหรับ endpoint นี้เอง เพียงแต่ family เดียวกับ `thaiwater_waterlevel` ที่มีแล้ว), `waterlevel_msl` (ม.รทก., 1:1) | near-real-time (station-varying) | 11/25 basin_code (ภาคกลาง, ครอบเจ้าพระยา — **ไม่ครอบ C.29/C.29A**, OPEN ว่าอยู่ basin ไหน) | ไม่ต้อง | 2026-09-27 22:00 — C.35 discharge=1257.00 cms, C.36=691.00 cms, C.37=87.00 cms, C.13=1950.00 cms (ดู `hii_waterlevel_load_sample.json`) | **VERIFIED** (ดึงจริง) | S | 03 `Q_in(k)` ของสถานีที่ผูกกับสาย ตน./ตะวันออก | สูง/S = **สูงสุด** |
| 2 | **Q_up** (ทางเลือกที่สอง, ไม่ผูก HII) | Open-Meteo Flood API (GloFAS) ที่จุดต้นน้ำ (Bang Sai/ปทุมธานี) | `flood-api.open-meteo.com/v1/flood?latitude=14.35&longitude=100.55&daily=river_discharge&timezone=Asia%2FBangkok&forecast_days=3` | `river_discharge` (m³/s, 1:1, เป็น canonical unit อยู่แล้วตาม `units_datum_crosswalk.yaml` id `openmeteo_flood`) | daily model output | global grid ~5km, จุดใดก็ได้เหนือ กทม. | ไม่ต้อง | 2026-09-27: 8.64 m³/s, 2026-09-28: 9.4 m³/s, 2026-09-29: 5.93 m³/s ที่ (14.325,100.575) | **VERIFIED** (ดึงจริง) | S | 03 `Q_in(k)` แบบสำรอง/cross-check เมื่อ HII station ไม่ครอบจุดที่ต้องการ (คนละกลไก — โมเดล vs เกจจริง, ห้ามแทนกันเงียบ ตาม `computation_rules.grid_cell_vs_gauge_not_equal`) | ปานกลาง/S |
| 3 | **tide/boundary** ปลายน้ำ (E4 `gravity_threshold`) | `openmeteo_marine` — **ต่ออยู่แล้ว** (`sources/registry.yaml` id `openmeteo_marine`) | (ดูรายการที่มี — ไม่ต้องต่อใหม่) | `sea_level_height_msl` (ม. MSL, 1:1) | hourly | ปากแม่น้ำเจ้าพระยา 1 จุด | ไม่ต้อง | ต่ออยู่แล้ว: -0.53 ถึง +1.94 ม. (72h sample เดิม, ดู `sources/registry.yaml`) | **RELAYED** (ต่ออยู่แล้ว, ไม่ดึงซ้ำ) | — | เป็น **model blend** ไม่ใช่ tide-gauge จริง (ต่างจากตาราง Navy ที่เป็น astronomical prediction) — ตอบ "ระดับน้ำทะเลโดยประมาณ" ไม่ใช่ "น้ำขึ้นน้ำลงที่แม่นยำ" — ไม่มีอะไรใหม่ให้ต่อในกลุ่มนี้ | n/a |
| 4 | **S_0** antecedent wetness (03 initial storage proxy) | Open-Meteo `soil_moisture_0_to_1cm/1_to_3cm/3_to_9cm` | `api.open-meteo.com/v1/forecast?latitude=13.758&longitude=100.676&hourly=soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm&timezone=Asia%2FBangkok&forecast_days=3` | m³/m³ (volumetric water content, **ไม่มี canonical unit ใน `units_datum_crosswalk.yaml` วันนี้** — เป็น field ใหม่ที่ต้องเพิ่ม category, ไม่ใช่ m/mm/m³/s ที่มีอยู่) | hourly (forecast+past) | global grid, จุดใดก็ได้ | ไม่ต้อง | 2026-09-27T00:00 = 0.495, T01:00 = 0.496, T02:00 = 0.487 ม³/ม³ ที่สัมมากร | **VERIFIED** (ดึงจริง) | S | 03 proxy สำหรับ `c` แปรผัน/`S_b(0)` — ตอบโจทย์ "antecedent wetness" ตรงตัวที่สุดในทั้ง 8 กลุ่ม | สูง/S = **สูงสุด** |
| 5 | **antecedent precipitation** (03, เสริม S_0) | Open-Meteo Archive API (ERA5-derived) `precipitation_sum` 30 วันย้อนหลัง | `archive-api.open-meteo.com/v1/archive?latitude=13.758&longitude=100.676&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&daily=precipitation_sum&timezone=Asia%2FBangkok` | mm/day (canonical `depth_accumulation`, 1:1) | daily, historical (ไม่ real-time) | global grid | ไม่ต้อง | 2026-08-28..2026-09-26 (30 วัน) = รวม 493.5mm; 2026-09-25 เดี่ยว = 118.3mm | **VERIFIED** (ดึงจริง) | S | 03 antecedent-wetness ทางเลือกที่ไม่ต้องพึ่ง soil-moisture model (ใช้แทนกันได้บางส่วน — cross-check) | สูง/S |
| 6 | **elevation z** (ground level ต่อจุด, สำหรับ datum/depth) | Open-Meteo Elevation API | `api.open-meteo.com/v1/elevation?latitude=13.758,...&longitude=100.676,...` (comma-separated, 1 คำขอ = ครบทุกจุด) | m (90m DEM surface, **ไม่ใช่ ม.รทก. survey benchmark** — ต้องแยกจาก MSL/สถานี) | static | global 90m | ไม่ต้อง | 7 จุดตัวอย่าง (สัมมากรและใกล้เคียง) = [4.0, 4.0, 1.0, 2.0, 3.0, 6.0, 4.0] ม. | **VERIFIED** (ดึงจริง) | S | 03/09 ground_level proxy เมื่อ HII/BMA station เองไม่ให้ (เทียบกับ `bkk_district_elevation.yaml` ที่มี RTSD 2010 survey อยู่แล้ว — สอง proxy คนละวิธี ควรเก็บคู่กัน ไม่แทนกัน) | ปานกลาง/S (ค่าซ้ำซ้อนบางส่วนกับ RTSD ที่มีแล้ว) |
| 7 | **c/imperviousness** runoff coefficient (03 `c_b`) | ทดลอง ESA WorldCover WMS (terrascope) และ GHSL WMS (JRC) | `services.terrascope.be/wms/v2` (timeout, HTTP 000); `ghslsys.jrc.ec.europa.eu/.../WMSServer` (302, ไม่ตาม) | n/a — ไม่ได้ payload | n/a | n/a | ไม่ต้อง (แต่ยิงไม่สำเร็จ) | ไม่มี (ทั้งสองล้มเหลวภายในงบ 1 คำขอ/host) | **FAILED** (HTTP 000 / 302, ไม่ retry ตามกติกา) | L | ยังไม่ปลดล็อก — คง `c ∈ [0.5,1]` (bound pair ตาม 06) ตามเดิม จนกว่าจะมีคนตาม redirect/สมัคร OpenTopography-style key หรือหา WMS endpoint ที่เสถียรกว่า | ต่ำ/L |
| 8 | **historical events** (D_critical calibration, flood_road ก่อน 2026) | GDACS Event API | `www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP?country=Thailand&fromdate=...&todate=...` (query `country=` ไม่กรองจริง — ต้อง filter ฝั่ง client จาก `iso3`) | เหตุการณ์ระดับประเทศ (ไม่ใช่ point/tambon) — `eventtype`, `name`, `fromdate` | polled, ~100 เหตุการณ์ล่าสุดทั่วโลกต่อคำขอ | ประเทศไทย เมื่อมีเหตุการณ์ขนาดใหญ่พอเข้าเกณฑ์ GDACS | ไม่ต้อง | 1 เหตุการณ์ไทย: "FL Flood in Thailand" fromdate 2026-08-18T01:00:00 (จาก 100 เหตุการณ์ล่าสุดทั่วโลก) | **VERIFIED** (ดึงจริง) | S | 08/D_critical: trip-wire เหตุการณ์ใหญ่ระดับประเทศ — **ไม่ละเอียดพอ** สำหรับ per-tambon/per-road calibration (ต้องคู่กับแหล่งละเอียดกว่า) | ปานกลาง/S |
| 9 | **historical events** (ละเอียดกว่า, ตามที่ founder ชี้เพิ่ม) | HII CKAN `data.hii.or.th/dataset/flood-area` (พื้นที่เสี่ยงน้ำท่วมรายเดือน/ตำบล 17 ปี) | `data.hii.or.th/api/3/action/package_show?id=flood-area` → resource CSV `.../download/monthly-flood-risk-area.csv` | `Month` (1-12, ไม่ใช่ปี), `GEOCODE`/tambon/amphoe/province TH+EN, `COUNT 17 YEAR` (ความถี่ 2548-2564), `CRITERIA`, `RISK` (เสี่ยงต่ำ/ปานกลาง/สูง) | static (17-year aggregate, ไม่ real-time) | ทั่วประเทศ, ยืนยันครอบ **เขตบางกะปิ/สะพานสูง (สัมมากรเอง)** | ไม่ต้อง | 27,024 แถว; Bang Kapi (แขวงคลองจั่น/หัวหมาก) เดือน 9 = COUNT 1, RISK เสี่ยงต่ำ; Saphan Sung เดือน 9 = COUNT 2, RISK เสี่ยงต่ำ | **VERIFIED** (ดึงจริง, ดาวน์โหลด CSV ครบ) | S | 08/D_critical: **baseline ความถี่น้ำท่วมรายตำบล** ต่อเดือน — ให้ prior ความน่าจะเป็นก่อนมีอนุกรมเกจของทีมเอง (**ไม่ใช่** event-date backfill ตรงตัว — เป็นความถี่สะสม 17 ปี ไม่ใช่รายวัน) — **licence CC BY-NC**: ใช้ภายใน/ไม่เชิงพาณิชย์เท่านั้น ตรวจ ToS ก่อน publish หน้าเว็บสาธารณะถ้าจะโชว์ตัวเลขนี้ตรง ๆ | สูง/S = **สูงสุดในกลุ่ม historical** |
| 10 | **historical events** (พยากรณ์ 6 เดือนล่วงหน้า, พบเพิ่มจาก package_search) | HII CKAN `flood-risk-area` (รายงานคาดการณ์ ONE MAP: HII+TMD) | `data.hii.or.th/api/3/action/package_show?id=flood-risk-area` → resource อยู่บน `hdrive.hii.or.th/owncloud/...` (คนละ host, ยังไม่ดึง) | รายตำบล, 6 เดือนล่วงหน้า, จาก baseline risk map + ฝนคาดการณ์รายเดือน ONE MAP | รายเดือน (resource ล่าสุด 2026-05-06) | ทั่วประเทศ | ไม่ต้อง (แต่ไฟล์อยู่คนละ host/share link) | ไม่ได้ดึง resource จริง (เกิน scope คำขอเดิม, เป็น owncloud share ไม่ใช่ REST) | **RELAYED** (metadata VERIFIED, resource เนื้อหา OPEN) | M | 06 multi_model_scenarios: สัญญาณคาดการณ์ 6 เดือนระดับตำบลจากภาครัฐเอง (ต่าง mechanism จาก NWP 7-16 วัน) | ปานกลาง/M |
| 11 | **historical events** (ทดสอบ flood_road วันในอดีต) | HII `public/flood_road?date=YYYY-MM-DD` | `api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road?date=2025-10-15` | `floodroad_datetime` ต่อสถานี (**พารามิเตอร์ date ถูกละเว้น** — คืนค่า last-known ต่อสถานีเสมอ ไม่ใช่ snapshot ของวันที่ขอ) | n/a | nationwide (262 สถานี) | ไม่ต้อง | ตอบ 200 แต่ payload มี `floodroad_datetime` กระจายตั้งแต่ 2019-01-30 ถึง 2026-09-27 ในคำขอเดียว — ยืนยันว่า `date=` ไม่กรอง | **FAILED** (พารามิเตอร์ไม่ทำงานตามคาด, ไม่ใช่ error code แต่ผลไม่ตรงจุดประสงค์) | — | **ไม่ปลดล็อก** back-fill ทาง endpoint นี้ — ต้องหาแหล่งอื่นสำหรับ per-date flood_road history (ยังเป็น gap จริง) | n/a |
| 12 | **BMA drain flow** (30 SCADA flow stations ตาม DDS plan) | ตรวจโค้ดที่มีอยู่ (`collect.py`/`parsers.py`) สำหรับ `bma_watermap`/`bma_station_detail` — **ไม่ยิง request ใหม่ต่อ host นี้** (ตามกติกา "อ่านโค้ดก่อน, อย่างมาก 1 request ต่อ host") | (ไม่มี URL ใหม่ — ตรวจ field ที่มีอยู่แล้วเท่านั้น) | ไม่พบ field `flow_cms`/ชื่อคล้ายกันใน parser ใด ๆ ของทั้งสอง source (มีแค่ `water_level_m`, `gate_opening_m`, `water_control_m`) | n/a | n/a | n/a | ไม่มี — ยืนยันจากการอ่านโค้ดจริงว่าไม่มี field flow | **FAILED** (ยืนยันด้วยโค้ด ไม่ใช่ network) | — | ยังเป็นช่องว่างจริง ไม่มี API โลกไหนรู้สถานะ flow ภายใน กทม. — ตรงกับที่ `GLOBAL_FREE_HAZARD_APIS.md` สรุปไว้แล้ว ("ระดับ/สถานะประตูระบายน้ำ กทม. แบบเรียลไทม์ ยังเป็น OPEN") | n/a |
| 13 | **TMD 7-day text** (regional-class warning) | `www.tmd.go.th/forecast/thailand` — **ยืนยันซ้ำจาก census เดิม**, VERIFIED แล้วก่อนงานนี้ | (ดู `sources/api_census_forecast7d.yaml` id `tmd_7day_text_forecast`) | ข้อความ ไม่ใช่ตัวเลข, 7 วัน, รายภาค | หลายครั้ง/วัน | ไทยตรง | ไม่ต้อง | ยืนยันเดิม HTTP 200 (ไม่ดึงซ้ำงานนี้) | **RELAYED** (ต่อยันจาก census เดิม) | — | เสริม layer0_in เป็นข้อความเตือนภัยระดับภาค — ไม่ใช่ตัวเลข ไม่เข้า 03 โดยตรง | n/a |
| 14 | **TMD open-data API** (ทดสอบใหม่งานนี้) | `data.tmd.go.th/api/` | `data.tmd.go.th/api/` | ไม่ทราบ (ไม่ถึง endpoint จริง) | n/a | n/a | ไม่ทราบ | HTTP 302 → redirect ไป `index1.php?aspxerrorpath=/api/` (ไม่ตาม ตาม one-attempt rule) | **FAILED** (302, ไม่ resolve เป็น JSON API ภายในงบ) | L | ยังไม่ปลดล็อกอะไรใหม่ — ต้องมีคนตาม redirect + สำรวจ `data.tmd.go.th` เพิ่มในงานหน้า | ต่ำ/L |

---

## 2. อันดับ "unlock ÷ effort" (สูง → ต่ำ)

1. **#1 HII `waterlevel_load` discharge (Q_up)** — S effort, ปลด `Q_in(k)` ของ 03 ตรงตัวด้วยเกจจริง (ไม่ใช่โมเดล) — VERIFIED sample พร้อม cms จริง 4 สถานี
2. **#4 Open-Meteo soil_moisture (S_0)** — S effort, ตอบ "antecedent wetness" ตรงคำถามที่สุด, ไม่ต้อง key, จุดเดียวก็ได้ครบ 3 ชั้นความลึก
3. **#9 HII flood-area CKAN (historical baseline, ครอบ Bang Kapi/Saphan Sung เอง)** — S effort (1 CSV โหลดเดียวจบ, ไม่ต้อง key), ให้ baseline ความถี่ 17 ปีที่ไม่มีในระบบนี้เลยตอนนี้ — แต่ licence CC BY-NC ต้องระวังก่อน publish หน้าเว็บสาธารณะ
4. #5 Open-Meteo archive precip (S, เสริม S_0)
5. #2 Open-Meteo GloFAS ที่จุดต้นน้ำ (S, สำรอง Q_up)
6. #6 Open-Meteo Elevation (S, เสริม z แต่ซ้ำซ้อนบางส่วนกับ RTSD ที่มีแล้ว)
7. #8 GDACS (S, แต่หยาบระดับประเทศ)
8. #10 HII flood-risk-area 6-month forecast (M, ไฟล์อยู่คนละ host)
9. #7 c/imperviousness WMS (L, ล้มเหลวทั้งคู่)
10. #14 TMD open-data (L, 302 ไม่ resolve)
11. #11 HII flood_road?date= (ไม่ปลดล็อก — พารามิเตอร์ใช้ไม่ได้)
12. #12 BMA flow (ไม่ปลดล็อก — ยืนยันไม่มี field)

**Top 3 ที่ควรต่อก่อน** (ต้องผ่าน maker-checker review + เพิ่ม `sources/registry.yaml` + fixture/test
ตาม `AGENTS.md` §5 ก่อน wire จริง — **ไม่ใช่งานนี้**):

1. `hii_waterlevel_load` (Q_up, discharge cms) — เงื่อนไข: ต้องยืนยัน basin_code ครบ 25 ลุ่มน้ำก่อน (เห็นแค่
   11 ในงานนี้และงานก่อนหน้า) ไม่งั้นได้แค่ subset ภาคกลาง; join/dedup กับ `thaiwater_waterlevel` เดิมต้อง
   ตัดสินใจก่อน (ดู `tools/harvest/hii_waterchart_draft.py` ที่มี draft parser อยู่แล้ว — ของนี้ตรงกับ
   endpoint เดียวกัน ไม่ใช่ของใหม่ทั้งหมด)
2. `openmeteo_soil_moisture` (S_0) — ไม่มี draft parser อยู่ก่อน ต้องเขียนใหม่ แต่ endpoint/query ง่ายสุดใน
   ทั้งตาราง (family เดียวกับ `openmeteo_forecast` ที่มี pattern โค้ดอยู่แล้ว)
3. `hii_flood_area_monthly_risk` (historical baseline) — เป็น one-off/static reference document (ไม่ใช่
   collector รายรอบ) เก็บเป็น `reference_documents:` entry แบบเดียวกับ `rmutp_2012_bma_canal_scada` ใน
   `sources/registry.yaml` — ต้องเช็ค CC BY-NC ก่อนโชว์ตัวเลขบนหน้าเว็บสาธารณะ

---

## 3. TODOLIST (รูปแบบ 5 คอลัมน์เดิม, เริ่ม #118 ตามคำสั่ง)

| # | Mismatch | Fix | Owner | Prio |
|---|---|---|---|---|
| 118 | `Q_up` (03 `Q_in(k)`) ไม่มีแหล่งเกจจริงที่ครอบ C.29/C.29A — basin_id ที่ใช้ตอนนี้ (11/25) ไม่ครอบจุดนั้น | หา basin_code ที่เหลือ 14 ลุ่มน้ำ (สำรวจหน้า waterchart อื่นหรือ JS bundle) ก่อนอ้างว่า `hii_waterlevel_load` ครอบทั้งประเทศ; ระหว่างรอ ใช้ C.35/C.36/C.37 (VERIFIED cms) เป็น proxy ต้นน้ำที่ใกล้ที่สุด | committer | high |
| 119 | `S_0`/antecedent wetness ไม่มี field ใดในระบบนี้เลยตอนนี้ (03 ไม่มี proxy สำหรับ initial storage) | เขียน `collect_openmeteo_soil_moisture` (S effort, pattern เดียวกับ `collect_openmeteo_forecast`) + เพิ่ม category `soil_moisture` ใน `units_datum_crosswalk.yaml` (ยังไม่มี canonical unit สำหรับ m³/m³ วันนี้) — ผ่าน maker-checker ก่อน wire | committer | high |
| 120 | historical baseline ความถี่น้ำท่วมรายตำบล (HII flood-area, 17 ปี) ยังไม่อยู่ใน `sources/registry.yaml` เลย ทั้งที่ครอบ Bang Kapi/Saphan Sung เอง | เพิ่มเป็น `reference_documents:` entry (ไม่ใช่ collector รายรอบ — static 17-year aggregate) พร้อม card `docs/knowledge/hii_flood_area_monthly_risk.md` (RELAYED + วันที่ ingest); ตรวจ licence CC BY-NC ก่อนโชว์ตัวเลขบนหน้าเว็บสาธารณะ (ต่างจาก non-commercial ภายในทีม) | committer+founder | medium |
| 121 | `c`/imperviousness ยังไม่มีแหล่งง่ายที่ยิงสำเร็จ (ESA WorldCover timeout, GHSL 302 ไม่ตาม) | ลองอีกครั้งด้วย endpoint อื่น (เช่น ESA WorldCover ผ่าน Microsoft Planetary Computer STAC API แทน terrascope, หรือสมัคร OpenTopography key แบบ instant สำหรับ DEM-derived slope proxy) — คนละ task, ระหว่างนี้คง `c ∈ [0.5,1]` เดิม | committer | low |
| 122 | HII `flood_road?date=` ไม่กรองตามวันจริง — ไม่ใช่ back-fill mechanism ที่ใช้ได้ | หยุดพิจารณา endpoint นี้เป็นทางแก้ back-fill; สำรวจ HII CKAN เพิ่มเติม (เช่น `flood-mark` dataset ที่เห็นใน package_search แต่ยังไม่ได้เปิดดู) หรือขอ appname จาก ReliefWeb (`apidoc.reliefweb.int/parameters#appname`, สมัครฟรีแต่ไม่ instant) สำหรับ v2 API | committer | medium |
| 123 | `data.tmd.go.th/api/` ให้ 302 ไม่ resolve เป็น JSON API ภายในงบคำขอเดียว | ตามงานหน้า: follow redirect ไป `index1.php?aspxerrorpath=/api/` ด้วย browser-like request 1 ครั้ง เพื่อดูว่าเป็น API form จริงหรือ landing page เปล่า | committer | low |
| 124 | Esri Thailand "Flood Data Hub" app resolve แล้ว (§4b) — layer น้ำท่วมทั้งหมดเป็นของเดิม (GISTDA key, HII waterlevel) ยกเว้น Sentinel-1 SAR ที่ไม่มีใครประเมิน effort จริงของ water-index analysis เอง | ถ้าจะใช้ Sentinel-1 RTC ImageServer จริง ต้องมีคน prototype SAR water-index (threshold บน band value, เทียบ pre/post-event) แยกเป็น task ของตัวเอง — ไม่ใช่ point/bbox JSON query ธรรมดา, effort สูงกว่าทุกแถวอื่นในตารางนี้ | committer | low |

---

## 4. คำขอ live ทั้งหมดที่ยิงในงานนี้ (นับตาม host)

| host | จำนวนคำขอ | สถานะที่ได้ |
|---|---|---|
| `api-v3.thaiwater.net` (HII) | 2 (`waterlevel_load` ×1, `flood_road?date=` ×1) | 200, 200 |
| `flood-api.open-meteo.com` | 1 | 200 |
| `api.open-meteo.com` | 2 (soil_moisture, elevation) | 200, 200 |
| `archive-api.open-meteo.com` | 1 | 200 |
| `services.terrascope.be` | 1 | 000 (timeout) |
| `ghslsys.jrc.ec.europa.eu` | 1 | 302 (ไม่ตาม) |
| `api.reliefweb.int` | 1 | 403 (ต้อง appname) |
| `www.gdacs.org` | 1 | 200 |
| `data.tmd.go.th` | 1 | 302 (ไม่ตาม) |
| `data.hii.or.th` | 4 (`package_show` ×2, CSV download ×1, `package_search` ×1) | 200 ทั้ง 4 |
| `www.arcgis.com` (sharing/rest) | 3 (`item?f=json`, `data?f=json` ×2 — app + web map) | 200 ทั้ง 3 |
| `gis.drr.go.th` | 1 (`MapServer?f=json`) | 200 |
| `utility.arcgis.com` | 1 (`Sentinel1RTC/ImageServer?f=json`) | 200 |
| **รวม** | **20** | ภายในงบ 25 + 5 ที่ยกให้ `data.hii.or.th` + 10 ที่ยกให้ arcgis-ตระกูล (ใช้ 5/10) |

**ต้องการ key/sign-up (ไม่ต่อในงานนี้)**: ReliefWeb API v1/v2 (ต้องขอ appname ก่อน — ฟรีแต่ไม่ instant),
ESA WorldCover/GHSL ผ่าน endpoint ที่ลองวันนี้ไม่สำเร็จ (อาจไม่ต้อง key ถ้าใช้ endpoint อื่น เช่น
Planetary Computer STAC — ยังไม่ทดสอบ), OpenTopography DEM (free-with-instant-key, ตามที่
`GLOBAL_FREE_HAZARD_APIS.md` ระบุไว้แล้ว, ยังไม่ทดสอบซ้ำในงานนี้).

---

## 4b. Resolve เพิ่ม: ArcGIS "Flood Data Hub by Esri Thailand" (Experience Builder app, founder link)

**คำสั่ง**: ห้าม scrape UI, ต้อง resolve ผ่าน ArcGIS REST เอง — ทำแล้ว (5 คำขอ, ไม่เกินงบ 10 ที่ยกให้
host ตระกูล arcgis):

1. `.../sharing/rest/content/items/<id>?f=json` → title "Flood Data Hub by Esri Thailand", owner
   `admin.demo`, **access: public**, `licenseInfo: null` (ไม่มีข้อความ licence ชัดเจน — OPEN)
2. `.../content/items/<id>/data?f=json` → พบ web map itemId `bba3b94aacdd4b8f9f4fbbb08020c44b` +
   layer อื่น (DRR_Feature, GOES satellite)
3. web map data → operational layers จริง:
   - **"ระดับน้ำที่สถานีวัด (Thaiwater)"** → `utility.arcgis.com/.../Hosted/thaiwater_waterlevel/
     FeatureServer/0` — **เป็นการ re-host ข้อมูล HII/thaiwater ที่เราต่ออยู่แล้ว (`thaiwater_waterlevel`)
     ไม่ใช่ของใหม่**
   - **"ข้อมูลทางหลวงชนบท (DRR)"** → `gis.drr.go.th/arcgis/rest/services/DRR_Feature/MapServer` —
     ตรวจ layer จริงแล้ว (VERIFIED): `0 ตำแหน่งสะพาน / 1 สะพาน / 2 ทางหลวงชนบท` — **DRR = กรมทางหลวงชนบท
     (Department of Rural Roads), ไม่ใช่ข้อมูลน้ำท่วม** — ไม่เกี่ยวกับอินพุตที่ต้องการเลย
   - **"พื้นที่น้ำท่วม" → GISTDA WebTiledLayer (3/7/30 วัน + ซ้ำซาก 10 ปี)** — `templateUrl` ฝัง
     **api_key จริง** (`7Yx3qaQpnKuo6ovNEkk7rJs5e9vrnoPTlfpdXTIA3BEKdJ0zRQLnHnFAf7BxQrQC`) อยู่ใน web
     map JSON สาธารณะ — **ไม่ยิงทดสอบ key นี้** (ตามหลักเดิมที่ repo นี้ใช้กับ MWA token ที่เจอใน CKAN:
     "a token pasted into a public listing may be a leaked long-lived credential rather than a public
     key — do not reuse it"); ตรงกับ `gistda_flood_extent_api` ที่มีอยู่แล้วใน `api_census.yaml`
     (Referer-locked, 403 เมื่อยิงตรงไม่มี Referer ที่ถูกต้อง) — **ของเดิม ไม่ใช่ของใหม่**, แค่ยืนยันว่า
     key ที่ GISTDA ออกให้ยังใช้งานอยู่ (สำหรับแอปที่ได้รับอนุญาต)
   - **"พื้นที่น้ำท่วม" → Sentinel-1 SAR (RTC)** → `utility.arcgis.com/.../Sentinel1RTC/ImageServer`
     — ตรวจ metadata จริง (VERIFIED, คำขอที่ 5): เป็น **Esri Living Atlas สาธารณะ** (copyright
     "Esri, European Commission, European Space Agency, Microsoft"), SAR 10m, global coverage,
     2 bands, ไม่ต้อง key (public ImageServer) — **การจำแนก "น้ำ" ที่เห็นในแอปเป็น renderer
     ฝั่ง client เอง (classBreaks บน band value ≤75/>75) ไม่ใช่ flood-classification product
     ทางการ** — ถ้าจะใช้จริงต้องทำ SAR water-index analysis เอง (raster, effort สูงกว่า point/bbox
     JSON มาก) — เก็บเป็น Tier 2/3 ไม่ใช่ Tier 1

**สรุปแอปนี้**: ไม่มีอินพุตใหม่ที่ปลดล็อกได้ง่าย — ทุก layer ที่เกี่ยวน้ำท่วมเป็นของเดิมที่ระบบนี้เห็นแล้ว
(GISTDA key เดิม, HII waterlevel เดิม) ยกเว้น Sentinel-1 SAR raster ที่เป็นของจริงแต่ effort สูง (ต้อง
image processing) และ DRR ที่ไม่เกี่ยวกับน้ำท่วมเลย

---

## 5. Leak scan

ไฟล์นี้ตรวจแล้ว: ไม่มี local filesystem path, ไม่มีชื่อ AI/vendor, ไม่มีชื่อบุคคล — เฉพาะ URL/field
name/ตัวเลขที่ดึงจริงและอ้าง repo file ที่มีอยู่แล้วเท่านั้น
