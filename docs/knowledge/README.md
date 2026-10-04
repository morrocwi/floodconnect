# Knowledge map — การจัดการน้ำระดับต่าง ๆ ที่เกี่ยวข้องกับโปรเจกต์นี้

**กฎ**: เอกสารทุกชิ้นที่เพิ่มเข้ามาในดัชนีนี้ต้องมีบัตร (card) ที่ระบุ tag **RELAYED** + วันที่
บันทึก/รับเข้า + อธิบายว่าเอกสารนี้ "อธิบายอะไร" เกี่ยวกับ node/สถานีที่โปรเจกต์นี้ติดตามอยู่จริง
(สัมมากร, เขตสะพานสูง/บางกะปิ ฯลฯ) ห้ามเพิ่มเอกสารโดยไม่มีบัตร และห้ามอ้างว่า "ยืนยันแล้ว" กับข้อมูล
ที่เป็นเพียงการ relay จากเอกสารบุคคลที่สาม — ดู epistemic floor ของ workspace นี้ (RELAYED/VERIFIED/
MEASURED/INSTINCT/OPEN)

ดัชนีนี้จัดเรียงเป็น 5 ระดับภูมิศาสตร์/สถาบัน จากประเทศ ลงไปถึงหมู่บ้านที่โปรเจกต์ติดตามจริง —
ระดับที่ยังไม่มีเอกสารจะระบุ "ยังไม่มีเอกสาร" ไว้ตรง ๆ แทนการละเว้นเฉย ๆ

## ระดับ 1 — ระดับประเทศ (สทนช. / กรมชลประทาน / กรมอุตุนิยมวิทยา / GISTDA)

- สทนช. (สำนักงานทรัพยากรน้ำแห่งชาติ): **ยังไม่มีเอกสาร**
- กรมชลประทาน (RID): **ยังไม่มีเอกสาร** — มีเพียง source ใน `sources/registry.yaml` id
  `rid_flood_risk_map` (static reference asset, ไม่ใช่เอกสารวิชาการ/นโยบาย)
- กรมอุตุนิยมวิทยา (TMD): **ยังไม่มีเอกสาร** — โปรเจกต์นี้ใช้ Open-Meteo (third-party model, ไม่ใช่ TMD
  โดยตรง) ดู `sources/registry.yaml` id `openmeteo_forecast`
- GISTDA: **ยังไม่มีเอกสาร**
- วช. (สำนักงานการวิจัยแห่งชาติ) / อว.: โพสต์ Facebook ทางการ 26 ก.ย. 2569 เรื่องเสวนา "Hub of Talents
  รับมือภัยพิบัติ" — RELAYED (official-agency-via-social) — `docs/knowledge/card_news_2026-09-26_nrct_hub_of_talents.md`
  (ยังไม่มี node วช./อว. เองในกราฟหลัก — บันทึกเป็นช่องว่างในบัตรนี้)
- JICA "Basic Plan of Flood Management Information System of Thailand" (Feb 2013, Attachment 05):
  แผนระบบข้อมูลน้ำท่วมระดับประเทศหลังอุทกภัย 2554 — ยุทธศาสตร์ 6 ข้อ, Fig.4 estimated discharge
  distribution (4,800/3,700/3,300-4,000 ลบ.ม./วิ, event-model ไม่ใช่ design capacity), Fig.8/10
  โครงสร้างหน่วยงาน RID/DWR/TMD/EGAT/BMA/GISTDA/HAII/DDPM → War Room → NDWC — RELAYED (เอกสารวางแผน
  2556, เทียบกับสถานะจริง 2569 ในการ์ดเอง) — `docs/knowledge/card_report_jica_flood_info_system_plan.md`

## ระดับ 2 — ลุ่มน้ำเจ้าพระยา / บางปะกง

- น้ำเหนือ→คลองสัมมากร (สรุปเพื่อเฝ้าระวัง): เส้นทางเขื่อนต้นน้ำ/แม่น้ำป่าสัก/คลองระพีพัฒน์-รังสิต-หกวา
  ที่ไล่บ่าลงมาถึงคลองตะวันออก กทม. — RELAYED (คัดลอกจากบันทึกสำรวจ 2026-09-26 ตรงตัว) —
  `docs/knowledge/UPSTREAM_CHAIN_SOURCE_2026-09-26.md`
- ไฮราคีทั้งประเทศ (ส่วนขยายรอบสอง 2026-09-27, founder: "มองแบบทั้งประเทศด้วยไฮราคี เพราะมันมีเรื่องน้ำเหนือ
  ไล่บ่าลง กทม."): ตารางต่อชั้น TIER-0..6 + ตาราง HANDOFF ระหว่างชั้น + คำแก้ไขต่อ C1 — MEASURED-on-graph +
  RELAYED + INSTINCT (แยกชัดในไฟล์) — `docs/knowledge/NATIONWIDE_HIERARCHY.md`

## ระดับ 3 — กรุงเทพมหานคร

| เอกสาร | วันที่/ปี | Tag | Path |
|---|---|---|---|
| ระบบตรวจวัดระดับน้ำในคลอง กทม. (RMUTP Research Journal Vol.6 No.1) — โครงสร้าง SCADA, ระบบโทรมาตร
  (75 สถานี, UHF 446.25MHz), ระบบตรวจวัดระดับน้ำในคลองหลัก (40 สถานี, GPRS/Modbus), ตัวเลขคลอง กทม.
  1,161 คลอง/2,272 กม. | มีนาคม 2012 (เอกสารรับเข้า 2026-09-27) | RELAYED (2012) | `docs/knowledge/bma_canal_scada_rmutp2012.md` (ต้นฉบับ PDF: `raw/knowledge/rmutp_2012_bma_canal_scada.pdf`, gitignored) |
| SpringNews infographic 851116 — ตัวเลขความจุอุโมงค์ระบายน้ำ กทม. 7 แห่ง (สุขุมวิท 26/36/42, พญาไท,
  เปรมประชากร, แสนแสบ-ลาดพร้าว, มักกะสัน) เติมความจุให้ 4 แถว `tunnel:bma_dds:*` ที่เคย OPEN + พบ
  อุโมงค์มักกะสันใหม่ (45 ลบ.ม./วิ, ไม่มี node เดิม) | 2569-09-27 (media infographic) | RELAYED |
  `docs/knowledge/card_media_springnews_851116.md` |
| บันไดฝน กทม. จากหลักฐาน (rain ladder) — เทียบตัวเลขฝนรายวัน/รายเดือนกับ threshold ที่มีจริง
  (design/TMD/crisis_min 203mm) + เทียบกราฟ สนน. ก.ย. 2566-2569 กับข่าว, ตาราง `coped_max`/
  `danger_min` ที่ยังเป็น OPEN | 2569-09-27 | ผสม VERIFIED/RELAYED/OPEN แยกต่อแถว |
  `docs/knowledge/RAIN_LADDER_BKK_SEPT_NEWS.md` |
| โหมดการระบายน้ำ (gravity/pump/tide-gated) — 4 ปตร.หลักฝั่งตะวันออกมีระดับควบคุมเป็นตัวเลขแต่ไม่มี
  กลไกยืนยัน, 8 แถว "ประตูเปิดลอย" VERIFIED จากข้อมูลเปิด กทม., เส้นทางสัมมากรเองยัง OPEN ทั้งสาม
  ช่วง | 2569-09-27 | ผสม VERIFIED/RELAYED/OPEN แยกต่อแถว | `docs/knowledge/DRAINAGE_MODE_SOURCES.md`
  (ข้อมูลดิบ: `sources/drainage_mode.yaml`) |
| flood69.peoplesparty.or.th `#klong` — third-party (พรรคการเมือง) canal-flow dashboard,
  proxy/cache 5 นาทีของ BMA KlongMap เอง; เทียบ schema (flow-direction field, profile_order,
  2 ชุด threshold ต่อสถานี) กับสิ่งที่โปรเจกต์นี้มีอยู่แล้ว, ไม่รับ framing ทางการเมือง | 2569-09-27 |
  RELAYED (third-party aggregator) |
  `docs/knowledge/card_thirdparty_flood69_peoplesparty_dashboard.md` (ข้อมูลดิบ:
  `sources/api_census_flood69.yaml`) |

ตัวชี้ (pointer) เอกสารระดับ กทม. อื่น ๆ ในโปรเจกต์นี้ (ไม่ได้ทำสำเนาซ้ำในไฟล์นี้):
- `docs/CAPACITY.md` — ขีดความสามารถระบายน้ำ กทม. เทียบฝนที่ตกจริง (สาย Sammakorn/รามคำแหง 53),
  รวมค่า 58.7 มม./ชม. (VERIFIED จากแผนปฏิบัติราชการ 2569) และข้อขัดแย้งกับตัวเลข JICA ที่ relay มา
- `docs/DATA_SYSTEM.md` — ระบบเก็บ/อ่านข้อมูลน้ำท่วมสดของโปรเจกต์นี้เอง (pipeline, trust tier, sources)
- `sources/registry.yaml` — ทะเบียน source ทุกตัวที่โปรเจกต์ดึงข้อมูลจริง (thaiwater.net canal
  waterlevel/flood_road, Open-Meteo, RID static asset, community_report ฯลฯ)
- `docs/knowledge/BMA_STATION_DETAIL_PROBE.md` — probe ของ `weather.bangkok.go.th/water/
  StationDetail?id=` (2026-09-27): พบฟิลด์ `water_control` (ระดับน้ำควบคุมต่อคลอง) เปิดอ่านได้จริง
  แบบไม่ต้อง login — ต่อยอดจาก `BMA_WATER_MAP_PROBE.md` ที่ฟิลด์เดียวกันเป็น null ทุกสถานี
- `docs/knowledge/DATA_SWEEP_2026-09-27.md` — กวาดข้อมูลย้อนหลังจริงเติมช่องว่าง PROP-FLOOD-06
  backtest (HII history endpoint ที่ไม่เคยบันทึกมาก่อน, DWR WebGIS, ค่ากลางฤดูแล้งของคลอง)
- `docs/BACKTEST_PROP_FLOOD_06_v0.md`, `docs/BACKTEST_PROP_FLOOD_06_v1.md`,
  `docs/BACKTEST_PROP_FLOOD_06_v2.md` — falsifier-loop backtest ของ PROP-FLOOD-06 (proposal,
  unverified) รอบ 1/2/3 (v2 = v5 engine, 3 leading promoters + persistence, 1,892 แถว) —
  ไม่ใช่ผลยืนยัน ใช้เป็นบันทึกการทดสอบ
- `docs/knowledge/FORECAST_7DAY_SOURCES.md` — สำรวจ+ต่อจริงแหล่งพยากรณ์ฝนล่วงหน้า 7-16 วัน
  ฟรีไม่ต้อง key (Open-Meteo 9 โมเดล deterministic + GFS-ensemble 31 สมาชิก + MET Norway,
  8 จุดทั่วประเทศ) พร้อม skill-check โมเดลเทียบตัวเอง — RELAYED-forecast ทุกค่า, ต่อเข้า
  `collect.py`/LAYER 0 จริงแล้ว (build 3, 2026-09-27); ข้อมูลดิบ:
  `sources/api_census_forecast7d.yaml`, parser ต้นแบบ: `tools/harvest/forecast7d_draft.py`
- `docs/LAYER0_IN_OUT_CAPACITY.md` — LAYER 0 (น้ำเข้า/น้ำออก/รับมือได้), PROPOSAL-derived
  simplification ของ PROP-FLOOD-06, wired เป็น TOP block ต่อพื้นที่บนหน้าเว็บสาธารณะ (build 3,
  2569-09-27)

## ระดับ 4 — เขตสะพานสูง / บางกะปิ

- **ยังไม่มีเอกสารวิชาการ/นโยบายเฉพาะเขตในดัชนีนี้**
- ตัวชี้ข้อมูลที่มีอยู่แล้วในโปรเจกต์: `site/inputs/community/` (community reports, low_areas, SOI
  tiers), `canal_graph.py` + `site/inputs/canals/east_chain.yaml` และ
  `site/inputs/canals/control_structures.yaml` (โครงสร้างคลอง/ประตูระบายที่โปรเจกต์ประกอบเอง จากข้อมูล
  สาธารณะ+ภาคสนาม ไม่ใช่เอกสารทางการฉบับเดียว)

## ระดับ 5 — หมู่บ้านสัมมากร

- ตัวชี้: `site/inputs/community/soi_tiers_2026-09-26.yaml` และ
  `site/inputs/community/SOI_TIERS_2026-09-26.md` (SOI_TIERS — การจัดชั้นซอยตามข้อมูลชุมชน)
- `site/inputs/community/community_reports_2026-09-26.md` — รายงานชุมชน (community_report trust tier)
- `site/inputs/areas/sammakorn.balance.yaml` — water balance ของพื้นที่สัมมากร
- **`docs/SAMMAKORN_STANDING_WATER_2026-09-27.md`** — น้ำค้างในหมู่บ้านสัมมากร: ผังการไหล
  (ซอย→บึง WL.SMK.01→คลองบ้านม้า 2 WL.BMA.02→แสนแสบ WL.SSB.08), anchor ที่แข็งแรงที่สุด →
  ข้อสรุปเชิงอนุมาน, ตันตรงไหน. แก้ไข 27 ก.ย. 18:00 น. (ยืนยันซ้ำด้วย query ตรงบน
  `data/observations.sqlite`): ข้อความเดิมที่ว่า WL.SSB.08 "นิ่งปกติตลอด 30+ ชม." ผิด — ค่าจริง
  ขึ้นถึง +0.80 ม. ระหว่างเหตุ แล้วเพิ่งกลับสู่ปกติและทรงตัวมา ~6 ชม. เท่านั้น (ณ 17:00 น.) — แก้ไข
  ตรงกับสิ่งที่ `docs/FLOW_STALL_TYPOLOGY.md`'s §6 (ต้นแบบสัมมากร) เจอเป็นอิสระต่อกันในวันเดียวกัน
  (36 แถวเต็มใน sqlite แสดงพิสัย -0.67 ถึง +0.80 ม. เช่นกัน) — สอง worker คนละคนเจอความขัดแย้ง
  เดียวกันโดยไม่รู้จักกัน, tag **VERIFIED**.
- **`docs/FLOW_STALL_TYPOLOGY.md`** — typology "ภูมิทัศน์ + การไหล/การหยุดไหล" ข้อมูลน้อยที่สุด
  (`tools/flowmap/flow_stall.py`, `tools/flowmap/render_profile.py`,
  `tests/test_flow_stall.py`) — ประตู ≠ ทิศทางการไหล ≠ นิ่ง, ทุกสมการประกอบจาก PROP-FLOOD-01/04
  ที่ขึ้นทะเบียนแล้ว ไม่มีสมการใหม่ในโค้ดที่รันจริง. §6 คือต้นแบบสัมมากรจริงจาก sqlite (2 เส้น OK,
  2 เส้น INFERRED, 6 เส้น REFUSED) และเป็นจุดที่พบความขัดแย้งข้อมูล WL.SSB.08 ข้างต้นเป็นครั้งแรก.

## ระดับเทียบเคียง — จังหวัด/เมืองอื่น (ไม่ใช่พื้นที่ที่โปรเจกต์วัดเอง ใช้เป็นเคสเปรียบเทียบ)

| เอกสาร | ปี | Tag | Path |
|---|---|---|---|
| จังหวัด — การบริหารจัดการแก้ไขปัญหาน้ำท่วมปทุมธานี (ม.ปทุมธานี, วารสารมณีเชษฐาราม ปีที่ 6 ฉบับที่ 6): อำนาจแตกตามกฎหมาย, บูรณาการ X̄=2.10, อปท. ขาดคน/งบ, บทเรียนไม่กลายเป็นกติกา | 2566 (เหตุการณ์ 2538–2565; รับเข้า 2026-09-27) | RELAYED | `docs/knowledge/card_pathumthani_flood_mgmt.md` (PDF: `raw/knowledge/pathumthani_flood_mgmt_2566.pdf`) |
| เมือง-หาดใหญ่ — Hat Yai City Climate: เกณฑ์ธงเหลือง/แดงผูกสถานี X.90/X.173A, บทเรียนอุทกภัย 2568, หาดใหญ่โมเดลพลัส (QR "น้องน้ำ", ระบบ 5 สี, แผนกลุ่มชุมชน) | 2555–2569 (ดึงหน้าเว็บ 2026-09-27) | RELAYED (คำบรรยายตนเองของเครือข่าย) | `docs/knowledge/card_hatyai_city_climate.md` (snapshot: `raw/knowledge/hatyaicityclimate_*_snapshot_2026-09-27.html`) |
| จังหวัด — นครสวรรค์: ความพึงพอใจของประชาชนต่อการช่วยเหลือของรัฐหลังอุทกภัย 2554 (แบบจำลอง Logit,
  n=500) — สายบังคับบัญชายาว/ตั้งรับ, การระบายน้ำท่วมขังหลังเหตุการณ์เป็นปัจจัยอันดับ 3 (+26.79%) | 2554
  เหตุการณ์ (รับเข้า 2026-09-27) | RELAYED | `docs/knowledge/card_research_nakhonsawan_flood_assistance_satisfaction.md` |
| อำเภอ — วารินชำราบ อุบลราชธานี: ปัจจัยทำนายความรอบรู้/พฤติกรรมเตรียมพร้อมรับมืออุทกภัยของผู้สูงอายุ
  (วารสารพยาบาล 72(2)) — กลุ่มเปราะบางต้องพึ่งความช่วยเหลือภายนอกในการขนย้าย/อพยพ, ใช้เวลานานกว่า
  ประชากรทั่วไป | 2566 (รับเข้า 2026-09-27) | RELAYED | `docs/knowledge/card_nursing_elderly_flood_preparedness_ubon.md` |
| จังหวัด — จันทบุรี: การจัดการระบบระบายน้ำตามการเปลี่ยนแปลงสภาพภูมิอากาศ (SWMM 5, TSTJ 2021) —
  design event จากฝนสูงสุดรอบ 30 ปี (90-100 มม./ชม.), น้ำท่วมขังจำลอง 0.82 ม., ตาราง Manning's N
  ต่อประเภทพื้นผิว (คนละนิยามกับ runoff coefficient c_U) | 2564 (รับเข้า 2026-09-27) | RELAYED |
  `docs/knowledge/card_research_chanthaburi_urban_drainage_swmm.md` |

## กระบวนการ/ชุมชน (ข้ามระดับ)

| เอกสาร | ปี | Tag | Path |
|---|---|---|---|
| **CO_FORECAST_PROTOCOL** — โปรโตคอลการพยากรณ์ร่วมของคลังนี้: สังเคราะห์จากไฟล์ที่มีอยู่แล้ว
  ทั้งหมด + Toledo PROP-FLOOD-06 (read-only) + readout_genesis Part VI-A §B.2a (read-only)
  เป็นกรอบเดียว "การอ่านค่าร่วม ไม่ใช่การพยากรณ์" (readout-not-truth) ที่ผูกทุก layer/worker/
  source เข้าด้วยกัน — ไม่เสนอสมการใหม่ | สังเคราะห์ 2026-09-27 | RELAYED + INSTINCT (แยกชัดในไฟล์) | `docs/knowledge/CO_FORECAST_PROTOCOL.md` |
| **แผนที่สังเคราะห์** — โครงสร้างการจัดการน้ำในประเทศไทย ทุกมิติ: (0) ปัญหาจริง 8 ข้อ, ชั้นอำนาจ, การเมืองของน้ำ, เครื่องมือ, ชุมชน, วงจรก่อน/ระหว่าง/หลัง, ตารางเคส, checklist ช่องว่างสัมมากร, คำถามเปิดต่อหน่วยงาน | สังเคราะห์ 2026-09-27 | RELAYED + INSTINCT (แยกชัดในไฟล์) | `docs/knowledge/THAI_WATER_GOVERNANCE_MAP.md` |
| **อำนาจบริหารทรัพยากร + คอขวดคำนวณจากกราฟ** — ต่อ node ระบุทรัพยากรที่ถือ+ฐานกฎหมาย+ใช้ร่วมกับใคร; คอขวด 4 กฎ (ผู้สั่งขัดกัน, เจ้าของทรัพยากรไม่ชัด, เส้น SHARES ไม่มีผู้ชี้ขาด, จุดล้มเดียว) คำนวณจริงจาก `water_system_dag.mmd` ด้วย `tools/dag/bottlenecks.py` | สังเคราะห์ 2026-09-27 | MEASURED-on-graph + INSTINCT + RELAYED-GENERAL (แยกชัดในไฟล์) | `docs/knowledge/RESOURCE_AUTHORITY_AND_BOTTLENECKS.md` (ผลดิบ: `bottlenecks.derived.json`) |
| **ปัญหาสังคมไทยเรียกชื่อทางวิชาการ** — 9 ปัญหาเชิงระบบ (institutional fragmentation, polycentric governance ไร้กลไกชี้ขาด, principal-agent asymmetry, contested resource ownership, blame-avoidance risk comms, visibility bias, residual risk transfer, path dependency, unfunded devolution) แต่ละข้อ corroborated ≥2 แหล่งอิสระในคลังนี้ + การ์ดโพสต์ วช. 26 ก.ย. 2569 | สังเคราะห์ 2026-09-27 | MEASURED-on-graph + RELAYED + INSTINCT (แยกชัดในไฟล์) | `docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md` |
| **เลดเจอร์ความสามารถระบายน้ำ** — ความจุ design/operational ของเขื่อน/ลำน้ำ/คลองผัน/อุโมงค์/ปั๊ม/
  ประตูทั้งประเทศ (เจ้าพระยาละเอียดเต็ม, 7 ลุ่มน้ำอื่นเป็นโครงร่าง), แถว `kind: outfall` ผูกเจ้าพระยา/
  อ่าวไทยเป็นทางออก (founder correction 16:44), ผังคอขวดตามตัวเลข + ตารางน้ำขึ้นลง กรมอุทกศาสตร์
  23-27 ก.ย. 2569 | สังเคราะห์ 2026-09-27 | VERIFIED/RELAYED/MEASURED/OPEN แยกต่อแถว | `sources/capacity_ledger.yaml` (68 แถว, ที่มาหลัก) + `docs/knowledge/DRAINAGE_CAPACITY_MAP.md`
  (ผัง+ตาราง+วิเคราะห์คอขวด) |
| **การพัฒนาพื้นที่แก้มลิง** (Kaem Ling / Retarding Basin, JIIR 2565) — กลไก gravity→ปิดประตู→สูบเสริม
  ตามระดับน้ำทะเล (ตรงกับ tide/gravity derating factor g_U(t) ของ PROP-FLOOD-06), 3 ขนาดแก้มลิงตาม
  กรมชลประทาน, ยืนยันหมวดหมู่ "ขนาดเล็ก" ของแก้มลิงสัมมากร | 2565 (รับเข้า 2026-09-27) | RELAYED |
  `docs/knowledge/card_academic_kaemling_retarding_basin_development.md` |
| **การสอบเทียบเกณฑ์ tier ladder PROP-FLOOD-06** — เทียบ WMO/UNDRR/UK EA/US NWS/Japan 5-level กับ
  L0-L5/LR, ค่า proposed สำหรับ S_H/T_act bands, horizon H, runoff coefficient c_U, tide derating
  g_U(t), L5 pre-check, ตัวกระตุ้นเฉพาะไทย (ฝน>80มม./วัน, canal critical line, DMR RELAYED) —
  calibration ไม่ใช่ validation | สังเคราะห์ 2026-09-27 | VERIFIED/RELAYED/INSTINCT แยกต่อแถว |
  `docs/knowledge/TIER_THRESHOLDS_RATIONALE.md` |
| ชุมชน — อยู่เจริญโมเดล: ชุมชนกับอุทกภัย 2554 เขตดอนเมือง (ม.เกริก, วารสารการศึกษาและพัฒนาสังคม ปีที่ 7 ฉบับที่ 2): ผู้นำ/กรรมการเป็นสถาบัน, กองทุนรีไซเคิล, บัญชีทักษะ + บริบทข้อพิพาทประตูคลองสามวา | 2554 (รับเข้า 2026-09-27) | RELAYED | `docs/knowledge/card_yucharoen_model_2554.md` (PDF: `raw/knowledge/yucharoen_model_2554_community_flood.pdf`) |
| กระบวนการ — การบริหารจัดการแบบมีส่วนร่วมเพื่อรับมือและแก้ไขปัญหาอุทกภัย (มรภ.พิบูลสงคราม, วารสารร้อยแก่นสาร ปีที่ 6 ฉบับที่ 11; บทความเชิงสังเคราะห์ ไม่มีข้อมูลภาคสนาม): บันไดการมีส่วนร่วม, 2 แนวทาง 16 ข้อ | 2564 (รับเข้า 2026-09-27) | RELAYED | `docs/knowledge/card_participatory_flood_mgmt.md` (PDF: `raw/knowledge/participatory_flood_mgmt_roikaensarn_2564.pdf`) |

| **บทเรียนกรณีศึกษา 5+1 เหตุการณ์น้ำท่วมไทย** — 2554 กทม./เจ้าพระยา, หาดใหญ่ 2553/2565, น่าน 2567
  (ขยาย), เชียงใหม่ 2567, กทม. 2569, การเมืองประตูน้ำระหว่างจังหวัด: formal vs de facto authority,
  บทบาทคณะกรรมการลุ่มน้ำ/ศูนย์บัญชาการกลาง, ทดสอบสมมติฐาน founder (15:12 2026-09-27) | สังเคราะห์
  2026-09-27 | RELAYED (แต่ละการ์ดแยกชัดต่อบรรทัด) | `docs/knowledge/case_2554_chaophraya_bangkok.md`,
  `case_hatyai_2553_2565.md`, `case_nan_2567.md`, `case_chiangmai_2567.md`, `case_bkk_2569.md`,
  `case_interprovincial_gate_politics.md`, `card_sweep_protests_2554-2569.md`,
  `card_research_thai_flood_governance_fragmentation.md` — สรุปตาราง+คำตัดสินสมมติฐาน:
  `CASE_LESSONS_STRUCTURAL.md` |
| **7 โรค/ปัญหาสุขภาพช่วงน้ำท่วม** — อินโฟกราฟิก "น้ำท่วม: รู้ทันโรค ป้องกันได้" (วช./อว., Hub of
  Talents) ถอดความ 7 โรค + อาการ + การป้องกัน ต่อ FloodConnect phase; เพิ่มสายด่วน **1422** (กรม
  ควบคุมโรค) เข้า help section ของหน้าเว็บสาธารณะแล้ว (ต่อจาก 1555/1669) | 2569-09-27 |
  RELAYED-official-guidance | `docs/knowledge/card_health_2026-09-27_nrct_7_flood_diseases.md` |
| **ร่างพิธีการต่อระยะสุขภาพ (PHASE_PROTOCOL)** — ร่าง input สำหรับ deliverable PHASE_PROTOCOLS ที่
  ยังไม่มีไฟล์หลัก, ทุกบรรทัดใช้ทะเบียน "อาจทำได้" ตามกติกาคำห้ามหน้าเว็บสาธารณะ | 2569-09-27 | ผสม
  RELAYED-official-guidance/INSTINCT/OPEN แยกต่อบรรทัด | `docs/knowledge/HEALTH_PHASE_PROTOCOL_DRAFT.md` |
| **วิเคราะห์ตำแหน่ง third-party ต่อ FloodConnect** — critique จากผู้ช่วย AI ภายนอก (ไม่ใช่ทีมนี้),
  เทียบกับ Google Flood Hub/FloodMapp/Floodbase/Ushahidi; บันทึกเป็นข้อกล่าวอ้างของบุคคลที่สาม
  ไม่ใช่ข้อค้นพบของทีมนี้ | 2569-09-27 | RELAYED (external assistant analysis) |
  `docs/knowledge/card_thirdparty_positioning_analysis_2026-09-27.md` |
| **โจทย์หลัก CORE-FIRST** — สกัด/สรุปโจทย์หลักของ FloodConnect ให้แข็งและครบขึ้นจาก critique
  ข้างต้น, แผน D1-D4 (ground-truth loop / human operation pilot / emergency UX 5-second test /
  offline degraded mode), TODOLIST ผูกกับ `FOUNDER_TASKS_2026-09-27.md`'s Community Self-Help
  DAG item | 2569-09-27 | สังเคราะห์จากไฟล์ที่มีอยู่แล้ว | `docs/PROBLEM_STATEMENT_AND_POSITIONING.md` |

หมายเหตุระดับ 1–2: เอกสารชุดนี้กล่าวถึง สทนช./กรมชลประทาน/ปภ./กรมอุตุฯ เพียงเป็นบริบท (ดูตาราง (1) ใน
`THAI_WATER_GOVERNANCE_MAP.md`) — เอกสารต้นฉบับของหน่วยงานระดับประเทศและลุ่มน้ำยังคง **ยังไม่มีเอกสาร**

---

*ดัชนีนี้จะถูกขยายเมื่อมีเอกสารใหม่เข้ามาในแต่ละระดับ — เพิ่มแถวในตารางระดับ 3 ก่อน (กทม. เป็นระดับที่
active ที่สุดในตอนนี้) แล้วค่อยเติมระดับ 1/2 เมื่อมีเอกสารระดับประเทศ/ลุ่มน้ำเข้ามาจริง.*
