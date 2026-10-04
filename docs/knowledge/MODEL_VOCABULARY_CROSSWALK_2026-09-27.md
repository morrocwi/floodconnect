# คำศัพท์เดียวกันทั่วโลก — โมเดล/มาตรฐานที่ใช้เชื่อมกับ FloodConnect (2026-09-27)

**Tag**: ผสม VERIFIED/RELAYED/OPEN ต่อแถว (ดูรายละเอียดใน
`sources/model_vocabulary_crosswalk.yaml` — ไฟล์นี้เป็นคำอธิบายภาษาไทยของไฟล์นั้น ไม่ใช่แหล่งข้อมูลใหม่) ·
**บันทึกเข้า**: 2026-09-27 · **เขียนโดย**: worker เฉพาะงานนี้ (ไม่แก้ไฟล์ที่ track อยู่, ไม่ build, ไม่
commit, ไม่ collect)

## ทำไมต้อง "คำศัพท์เดียวกัน"

คำสั่งฟาวน์เดอร์ (verbatim): *"ทำให้ภาษาเป็นภาษาเดียวกัน เชื่อมกับทั่วโลกด้วย โดยเฉพาะกับโมเดลที่ประเทศไทยนิยมใช้"*

ตอนนี้ระบบเรามีคำของตัวเอง (เช่น `S_b(k)`, `Q_out(k)`, "พื้นที่ปิดล้อมย่อย") ซึ่งถูกต้องและมีที่มาชัดเจน
(BMA แผน 2569, PROP-FLOOD-xx) แต่ถ้าจะ**ส่งข้อมูลออกไปให้โมเดลอื่นอ่าน** หรือ**อ่านข้อมูลจากโมเดลอื่นเข้ามา**
โดยไม่ต้องตีความใหม่ทุกครั้ง ต้องมีตารางเทียบคำ — นี่คือไฟล์นั้น

## การตัดสินใจ "เลือกให้เลยระดับโลก" (orchestrator decision, ฟาวน์เดอร์แก้ไขได้ทุกเมื่อ)

ฟาวน์เดอร์บอกให้เลือกคำมาตรฐานให้เลยแทนที่จะแค่ทำตาราง — บันทึกการตัดสินใจนี้ (เหตุผลในวงเล็บ):

| ชั้น (layer) | มาตรฐานที่เลือกเป็นหลัก | เหตุผล |
|---|---|---|
| ตัวแปร/ปริมาณ (variables) | **CF Conventions** `standard_name` + หน่วย SI | มาตรฐานสากลที่ใช้กว้างที่สุดสำหรับข้อมูลภูมิอากาศ/อุทกวิทยา, ฟรี, มี list กลาง |
| การแลกเปลี่ยนข้อมูล (exchange) | **OGC WaterML 2.0** (time series) / **OGC SensorThings** (sensor สด); ISO 8601 UTC; EPSG:4326/32647; datum ระบุชัดทุกครั้ง | มาตรฐาน OGC เปิด ใช้แลกเปลี่ยนข้อมูลน้ำ/เซนเซอร์ทั่วโลก |
| โครงข่ายเมือง (urban network) | **EPA SWMM** (Subcatchment/Junction/Storage Unit/Conduit/Pump/Orifice/Weir/Outfall) | ฟรี เป็น node-link เหมือน KG เรา และ**มีหลักฐานจริงในคลังเอกสารเรา**ว่างานวิจัยไทยใช้ (EEC 5 เมือง, จันทบุรี — VERIFIED) |
| โครงข่ายแม่น้ำ/ลุ่มน้ำ (river/basin) | **HEC-RAS** / **HEC-HMS** (USACE) | ฟรี, เป็นกลุ่มเครื่องมือที่เอกสารเราเองแนะนำให้หาต่อ (RELAYED — ยังไม่ยืนยันว่า RID ใช้จริงกับลุ่มน้ำนี้) |
| การแจ้งเตือน (alerts) | **CAP** (Common Alerting Protocol) — ทีมคู่ขนานกำลังใช้ใน `sources/rain_alert_thresholds_crosswalk.yaml` | มาตรฐานแจ้งเตือนสากล (severity/urgency/certainty), WMO เองก็ใช้ CAP profile |
| รอง (secondary) | DHI MIKE 11/MIKE+/MIKE FLOOD/MIKE 21, InfoWorks ICM, Delft-FEWS | เป็น commercial/เฉพาะแพลตฟอร์ม — เก็บเป็น alias เทียบเท่าเท่านั้น ไม่ใช่คำหลัก |

**หลักปฏิบัติ**: ชื่อฟิลด์ของเราเองและการ export ในอนาคต **ตามคอลัมน์ canonical** เสมอ — คำของโมเดลอื่นทุกตัวคือ
**alias** ไม่ใช่ตัวเลือกเทียบเท่ากัน ที่ไหนที่ CF ไม่มีชื่อมาตรฐาน เราเสนอชื่อของเราเอง
`floodconnect:<concept_id>` และติดป้าย **"ข้อเสนอ — ยังไม่ลง Toledo"** เสมอ — ไม่เคยอ้างว่าเป็นคำ CF ที่มีจริง

## โมเดลที่พบหลักฐานว่าหน่วยงานไทยใช้จริง (VERIFIED ในคลังเอกสารเรา)

| โมเดล | ใครใช้ (ตามเอกสารที่เราถือ) | หลักฐาน |
|---|---|---|
| **EPA SWMM 5** | เทศบาลเมืองฉะเชิงเทรา/บ้านสวน/ศรีราชา-แหลมฉบัง/พัทยา/พลา (ทุน ม.บูรพา/วช., EEC) | `card_research_2026-09-27_eec_integrated_drainage.md` |
| **EPA SWMM 5** | จังหวัดจันทบุรี (บทความวารสาร TSTJ 2021) | `card_research_chanthaburi_urban_drainage_swmm.md` |
| **Open-Meteo multi-model blend** (ECMWF/GFS/ICON/JMA/GEM/Météo-France ฯลฯ) + **GloFAS-via-Open-Meteo** | คลังเราเองใช้เป็นค่า `third_party` inflow/forecast | `sources/registry.yaml`, `docs/knowledge/GLOBAL_FREE_HAZARD_APIS.md` |
| HEC-RAS / HEC-HMS | **RELAYED เท่านั้น** — เอกสารเราแนะนำให้หาโมเดลนี้ต่อ ไม่ใช่หลักฐานว่ามีอยู่แล้ว | `docs/PROBLEM_STATEMENT_AND_POSITIONING.md` บรรทัด 71, `LITREVIEW...md` แถว 31 |

**โมเดลที่ผู้ประสานงานเอ่ยชื่อมาแต่ grep ทั้งคลังแล้วไม่พบว่ามีหน่วยงานไทยใช้เลย** (ไม่ใช่แปลว่าไม่มีคนใช้จริง —
แปลว่า **คลังเอกสารของเราเองไม่มีหลักฐาน**, tag OPEN สำหรับ "ใช้ในไทยหรือไม่"): DHI MIKE 11/MIKE+/MIKE FLOOD/
MIKE 21, InfoWorks ICM, WRF (เป็นโมเดลอุทกวิทยา — พบแค่ "WRFL" ซึ่งเป็นคำย่อฝนถ่วงน้ำหนักของกรมชลประทาน
คนละเรื่อง), ROMS, SWAT, RRI, Delft-FEWS

## ตารางย่อ (คอนเซ็ปต์ตัวอย่าง — เต็มอยู่ใน YAML)

| concept | คำเรา | CF/มาตรฐานสากล | SWMM | HEC-RAS/HMS | GloFAS/Open-Meteo |
|---|---|---|---|---|---|
| พื้นที่รับน้ำ | พื้นที่ปิดล้อมย่อย (Sub Polder) | (ไม่มีชื่อ CF — ข้อเสนอ) | Subcatchment | Subbasin (HMS) | grid cell |
| น้ำในที่เก็บกัก | ปริมาตรเก็บกัก | (ไม่มีชื่อ CF — ข้อเสนอ) | Storage Unit | Storage Area / Reservoir | ไม่มี |
| อัตราระบายออก | อัตราระบายน้ำออกได้จริง | water_volume_transport_in_river_channel | Pump curve flow | Flow (Q) | river_discharge |
| น้ำท่วมขัง | น้ำท่วมขังถนน | water_surface_height_above_reference_datum (ส่วนต่าง) | Node Flooding / Ponded Area | 2D inundation depth | ไม่มี |
| ระดับเตือน/วิกฤติ | เตือนภัย/วิกฤติ (ม.รทก.) | water_surface_height_above_reference_datum | Node Head/Depth | Stage | ไม่มี (ไม่มี datum ไทยตรง) |
| ความกดอากาศ (ใหม่) | — (กำลังต่อ feed) | air_pressure_at_mean_sea_level | ไม่มี | ไม่มี | Open-Meteo `pressure_msl` |
| ตำแหน่งพายุ (ใหม่) | — (กำลังต่อ feed) | (ไม่มีชื่อ CF เดี่ยว) | ไม่มี | ไม่มี | ไม่มี |
| ระดับแจ้งเตือน (ใหม่) | L0–L5 (ดู threshold crosswalk) | CAP `<severity>` | ไม่มี | ไม่มี | GloFAS RP flag / Flood Hub severity |

## 5 จุดที่คำ "ดูเหมือนเดียวกัน" แต่ไม่ใช่ (ต้องระวังที่สุด)

1. **"ส่วนขาด/หนี้เก็บกัก" (storage deficit) ของเราเทียบกับสัญลักษณ์บวก/ลบมาตรฐาน** — อ็อบเจกต์ `E_k := max(0,
   S_k - S_safe)` ของเราเป็น "ส่วนเกิน" (excess เหนือระดับปลอดภัย) ไม่ใช่ "หนี้" ในความหมายบัญชี — ไม่มีโมเดล
   ไหนที่ตรวจสอบ (SWMM/HEC-RAS/MIKE) มีชื่อวัตถุนี้ตรงๆ เลย เป็นของที่เราประกอบขึ้นเอง (OPEN ทุกคอลัมน์
   โมเดล) — ถ้าจะ export ต้องระวังเครื่องหมายบวก/ลบให้ตรงกับนิยาม ไม่ใช่แค่ก็อปคำ
2. **SWMM "Node Flooding"/"surcharge" ≠ ของเรา "น้ำท่วมขัง" (ponding depth) โดยตรง** — SWMM's Node Flooding
   วัดเป็น**ปริมาตร**ที่ล้นออกจาก node (ไม่ใช่ความลึกน้ำท่วมถนน) ส่วน surcharge คือสถานะท่อเต็มความดัน — ทั้งคู่
   ใกล้เคียงแต่**ไม่ใช่**ตัวแปรเดียวกับความลึกน้ำท่วมขังที่หน้าเว็บเราแสดง (d := max(0, H-z))
3. **HEC-RAS "Stage" ใช้ datum ของตัวเอง — ต้องระบุ ม.รทก. เสมอเมื่อเทียบข้าม** — ค่า stage จาก HEC-RAS/MIKE
   H-point/SWMM node depth **ไม่มีความหมายอะไรเลย** ถ้าไม่ประกาศ datum เดียวกับที่เราใช้ (ม.รทก. = MSL,
   Ko Lak) — กฎ `never_mix_msl_and_local` ใน units_datum_crosswalk.yaml ใช้ข้ามทุกโมเดลในตารางนี้ด้วย
4. **WRF ให้ฝนสะสม (RAINC/RAINNC) ไม่ใช่ความเข้มฝน — ห้ามบวกเข้ากับ intensity โดยตรง** — เหมือนกฎ
   `never_add_intensity_to_accumulation` เดิมของเรา แต่ตอนนี้ยืนยันแล้วว่าใช้กับ WRF (และโมเดลอื่นที่รายงาน
   accumulated precip) เหมือนกันทุกตัว ไม่ใช่แค่ Open-Meteo
5. **CAP "certainty" (ความเชื่อมั่นผลพยากรณ์) ≠ tag epistemic ของเรา (VERIFIED/MEASURED/RELAYED/INSTINCT/
   OPEN)** — สองแกนที่ต่างกันโดยสิ้นเชิง: ของเราวัด "แหล่งข้อมูลนี้เชื่อถือได้แค่ไหน" ส่วน CAP certainty วัด
   "เหตุการณ์ที่พยากรณ์จะเกิดขึ้นจริงแค่ไหน" — ห้ามรวมเป็นคอลัมน์เดียวบนหน้าเว็บสาธารณะ

## Export ขั้นต่ำที่ยังขาด (สรุปจาก `export_notes` ใน YAML)

- **SWMM .inp**: ขาด invert elevation (ม.รทก.) เกือบทุกคลอง/ท่อ, ขาด stage-storage curve ของแก้มลิง
  Sammakorn, ขาดค่า %impervious/runoff coefficient ทุกหน่วย (ทั้งหมด OPEN)
- **HEC-DSS**: ขาด cross-section geometry (station-elevation) แทบทุกคลอง, ขาดค่า Manning's n ทั้งคลัง
  (พบช่องว่างใหม่จากงานนี้)
- **CF-NetCDF**: ตัวแปรส่วนใหญ่ยังไม่มี CF standard_name ที่ลงทะเบียนจริง (มีแต่ข้อเสนอ floodconnect:*),
  ไม่มี attribute CRS/datum ติดกับไฟล์ export ใดๆ ในคลังตอนนี้
- **WaterML2**: ยังไม่มี ObservedProperty URI ของเราเอง, ไม่มี metadata ประเภทการรวมค่า (instantaneous
  vs mean-over-interval) ติดกับ series ที่เก็บอยู่

## TODOLIST (ต่อจาก #140, 5 คอลัมน์)

| # | งาน | เจ้าของ | Priority | สถานะ |
|---|---|---|---|---|
| 140 | ลงทะเบียน `floodconnect:*` proposal names (ทุกแถวที่ CF ไม่มีชื่อ) เป็น Toledo proposal จริง แทนที่จะเป็นแค่ข้อเสนอในไฟล์นี้ | committer | high | OPEN |
| 141 | หา stage-storage curve ของแก้มลิง Sammakorn (จำเป็นสำหรับทั้ง SWMM export และ storage_deficit_available_storage) | committer | high | OPEN |
| 142 | สำรวจ invert elevation (ม.รทก.) รายคลอง/ท่ออย่างน้อยโซน Sammakorn — บล็อกทั้ง SWMM .inp และ HEC-DSS export | committer | medium | OPEN |
| 143 | ยืนยัน (fetch/ติดต่อจริง) ว่า RID/BMA เคยรัน HEC-RAS/HEC-HMS กับลุ่มน้ำนี้หรือไม่ — ตอนนี้เป็น RELAYED ล้วน | committer | medium | OPEN |
| 144 | เพิ่ม CRS/datum attribute (EPSG:4326 หรือ ม.รทก.) ให้ทุกไฟล์ export จาก build_data.py | committer | medium | OPEN |
| 145 | ประสานกับผู้เขียน `rain_alert_thresholds_crosswalk.yaml` ให้ `unified_ladder` อ้างอิงคอลัมน์ `canonical_name` ของไฟล์นี้แทนที่จะตั้งชื่อ CAP ซ้ำ | committer | low | OPEN |

---
*ไฟล์นี้เขียนจาก `sources/model_vocabulary_crosswalk.yaml` เท่านั้น ไม่ได้แก้ไฟล์ที่ track อยู่ ไม่ build
ไม่ commit ตาม write-scope ที่กำหนด*
