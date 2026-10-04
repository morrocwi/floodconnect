# Card — flood69.peoplesparty.or.th "#klong" canal dashboard (third-party aggregator)

**Tag**: RELAYED (third-party political-party dashboard; aggregates/mirrors official BMA
data, is NOT itself an official source) · **บันทึกเข้า**: 2569-09-27 · **ทำโดย**: worker
probe, budget 4/8 HTTP fetches, founder instruction 17:xx: "สกัดหาประโยชน์จากระบบนี้เพื่อทำ
typology ให้แข็งแรงขึ้น"

## คืออะไร / ใครเผยแพร่

`flood69.peoplesparty.or.th` เป็น dashboard ติดตามสถานการณ์น้ำท่วมที่เผยแพร่โดย**พรรคประชาชน**
(a Thai political party). Tier ของโปรเจกต์นี้: **third-party aggregator, RELAYED** —
ไม่ใช่หน่วยงานราชการ ไม่ใช่เจ้าของเครื่องมือวัดใด ๆ. บันทึกนี้อธิบายหน้าเว็บอย่างเป็นกลาง
(หน้าตา, กลไก, ข้อมูลที่มันดึงมาจากไหน) — **ไม่รับ framing ทางการเมืองใด ๆ มาต่อ**, ไม่มีชื่อ
บุคคล/นักการเมือง/เจ้าหน้าที่พรรคในไฟล์นี้.

หน้า `#klong` ("แผนผังการไหลของน้ำในคลอง", "BANGKOK KLONG FLOW") เป็น 1 ใน 5 หน้าของ dashboard
(อีก 4: `#events` เหตุการณ์, `#places` ฝากรถ/พักพิง, `#systems` รวมระบบ, และหน้าแรก).

## มันดึงข้อมูลจากไหนจริง ๆ (upstream แท้)

เป็น React SPA (Vite build) — bundle หลักไม่มี URL literal ของ API (ตรวจด้วย grep แล้ว: ไม่มี
`http://`/`https://`/`/api`/คำว่า "คลอง" ปรากฏใน `index--avEOgbL.js` เลย) จึงต้อง render จริง
ผ่าน Playwright เพื่อจับ network call — พบ **1 endpoint เดียว**:
`GET https://flood69.peoplesparty.or.th/api/klongmap` (JSON, 2MB, ไม่ต้อง auth).

หน้าเว็บบอกตรง ๆ เอง (ข้อความบนหน้า): **"ดึงข้อมูลผ่านเซิร์ฟเวอร์ตัวกลางที่เก็บสำเนาไว้ครั้งละ 5
นาที เพื่อลดภาระระบบของ กทม. และรีเฟรชอัตโนมัติ"** — คือ**พร็อกซี/แคช 5 นาที**ของระบบ กทม. เอง
และ footer ของแผนผังให้เครดิตตรง: **"ภาพแผนผังและข้อมูล © สำนักการระบายน้ำ กทม."** ลิงก์ไปที่
`https://weather.bangkok.go.th/KlongMap` (ต้นทางจริง = **BMA สำนักการระบายน้ำ**, ผ่านระบบ
KlongMap — คนละ URL path จาก `bma_watermap` (`PageMap/GoogleMap`) และ
`BMA_STATION_DETAIL_PROBE` (`water/StationDetail`) ที่โปรเจกต์นี้มีอยู่แล้ว แต่ชื่อฟิลด์
(`water_control` ฯลฯ) ตรงกันเป๊ะ — น่าจะเป็นหน่วยงาน/ตารางเดียวกัน ยังไม่ยืนยัน 100% ว่า backend
เดียวกันหรือ sibling — **OPEN**).

## Schema ที่พบ (payload จริง, archived)

6 คีย์บนสุด: `waterStation` (403 แถว, schema ครบมาก — ดูด้านล่าง), `stationMap` (253 แถว, ป้าย
ชื่อสถานี + ตำแหน่งบนแผนผัง), `arrowMap` (241 แถว, ลูกศรทิศทางการไหล), `riverMap` (12 แถว, ชื่อ
สายคลอง), `listRiverMap` (89 แถว, ลำดับสถานีตามคลอง), `dailyheightwater` (1 object, ตารางน้ำขึ้น
น้ำลง). **หมายเหตุสำคัญ**: ณ เวลา probe จริง แถบ `waterStation` เกือบทุกฟิลด์เป็น `null` (แม้แต่
`water_name`) — ได้เฉพาะ layout table (id/offset_x/offset_y/active) ไม่ใช่ค่าน้ำสด — **OPEN**
ว่าทำไม (อาจต้องมี call แยกสำหรับค่าน้ำจริง ที่ probe นี้ไม่พบ).

## เทียบ field-by-field กับสิ่งที่เรามีแล้ว

| ด้าน | flood69 มี | เรามีอยู่แล้ว |
|---|---|---|
| ทิศทางการไหล | `arrowMap`: มุมหมุน (deg) + สี + ชุด `reverse`/`configs_reverse` แยกต่างหาก = **โครงสร้างรองรับการไหลย้อน/สองทิศทาง** ในตัว schema | เราไม่มี flow-direction เป็น field ของตัวเอง — คลองใน `east_chain.yaml` เป็น chain ทางเดียว (upstream→downstream โดย maintainer ประกาศเอง) |
| ลำดับสถานีตามคลอง | `listRiverMap.profile_order` + `point` (wl_out01/wl_out02 ฯลฯ ระบุ "ขาไหน" ของสถานี) | เราทำ manual chain ผ่าน `canal_graph.py`/`east_chain.yaml` — ไม่มี field ระบุ "ขาเข้า/ขาออก" ต่อสถานีแบบมีชื่อชัดเจน |
| จัดกลุ่มคลอง | `riverMap` (12 สาย) + `system_id` (2 ฝั่ง: ธนบุรี/พระนคร) | เรามี `basin`/`district` grouping แต่ไม่มี "ฝั่งธน/ฝั่งพระนคร" เป็น field แยก |
| ระดับควบคุม | `water_min`/`water_max`/`bed_bank`/`left_bank`/`right_bank`/`warning`×2/`critical`×2 (สองชุดสำหรับ 2 ทางออก) | เรามี `water_control` field เดียวจาก `BMA_STATION_DETAIL_PROBE` — flood69's schema มี**2 ชุด threshold ต่อสถานี** (out01/out02) ซึ่งคม/ละเอียดกว่า field เดียวที่เรามี ถ้าเคย populate จริง (ตอน probe นี้เป็น null ทั้งหมด — **ยังพิสูจน์ไม่ได้ว่า populate จริงเมื่อไหร่**) |
| สถานะประตู/ปั๊ม | `pump_count`/`water_gate_count`/`station_status`/`waterstatus`/`statusColor` เป็น field พร้อมใช้ (แต่ null ใน snapshot นี้) | เราไม่มี field รวม pump+gate ต่อสถานีเดียวแบบนี้ — เรามี pump station กับ gate เป็นคนละ node |
| ระดับน้ำขึ้นลง | `dailyheightwater`: AM/PM high/low tide time+height, ตรงรูปแบบเดียวกับตารางกรมอุทกศาสตร์ที่เรามีแล้วใน `sources/capacity_ledger.yaml` | เรามีอยู่แล้ว (23-27 ก.ย. 2569) — **ตรงกัน ไม่ใช่ของใหม่** |
| UI canal-as-node | แผนผังเดียว (SVG/canvas) ซูมได้ + "ใกล้ฉัน" (ตำแหน่งผู้ใช้ → หาสถานีใกล้สุด) + ค้นหาสถานี + toggle ฝั่งธน/พระนคร/ภาพรวม | เราไม่มี geo-nearest-station UI หรือ canal-wide single-map view ในหน้า public ตอนนี้ |

## สิ่งที่เขามีเราไม่มี

1. **flow-direction field พร้อม reverse-state** (`arrowMap.reverse`/`configs_reverse`) — โครงสร้าง
   schema ที่ตั้งใจรองรับ "น้ำไหลย้อน" เป็น first-class field ไม่ใช่แค่ note.
2. **profile_order + point (ขาเข้า/ขาออก)** ต่อสถานีตามคลองอย่างเป็นระบบ (`listRiverMap`).
3. **2 ชุด threshold ต่อสถานี** (out01/out02) แทน 1 ชุด.
4. **"ใกล้ฉัน" geo-nearest UI** — หาสถานีใกล้ตำแหน่งผู้ใช้ที่สุด.

## สิ่งที่เรามีเขาไม่มี

- Water-balance equation (`PROP-FLOOD-03`ฯลฯ), F1–F6 flow-state typology, tier ladder ที่ผ่าน
  calibration (`TIER_THRESHOLDS_RATIONALE.md`), append-only readout log, epistemic tagging
  ต่อค่า — flood69 ไม่มีสิ่งเหล่านี้เลย เป็นแค่ visual proxy ของ BMA raw data ไม่มีชั้นวิเคราะห์ทับ.
- ค่า `waterStation` ของเขา ณ เวลาที่ probe นี้ทำ **เป็น null เกือบทั้งหมด** — เรามีค่าจริงจาก
  `thaiwater_canal_waterlevel`/`bma_watermap` ที่ populate ทุกครั้ง.

## ลิขสิทธิ์/เงื่อนไขการใช้

ไม่พบข้อความ licence/terms-of-use แยกต่างหากบนหน้านี้ระหว่าง probe (มีแค่เครดิตแหล่งที่มาใน
footer) — **OPEN, unresolved**, เหมือนสถานะของแหล่ง BMA อื่น ๆ ในโปรเจกต์นี้.

## 3–6 ข้อเสนอเสริม typology (concrete, ระบุ what/why/tag)

1. **เพิ่ม field `flow_direction_state`** ต่อ edge ในกราฟคลอง (ค่า: forward / reverse /
   unknown) แยกจาก topology edge เดิม — **why**: `arrowMap`'s `reverse`/`configs_reverse`
   ยืนยันว่าทิศทางการไหลเป็นสถานะที่เปลี่ยนได้จริง ไม่ใช่ static, ตรงกับ F4
   (tailwater/backwater) ของ typology proposal ที่ยังไม่มี field รองรับเป็นรูปธรรม — **tag: INSTINCT** (ยืมโครงสร้าง schema มา ไม่ใช่ค่าที่ verified จริง จนกว่าจะมีข้อมูลมา populate).
2. **เพิ่ม `leg_id`/`point` ต่อสถานีที่มีมากกว่า 1 ทางออก** (เช่น out01/out02) แทนเก็บ threshold
   เดียวต่อสถานี — **why**: สถานีประตูจริงมักมี 2 ทางน้ำจริง (เข้า/ออก) การรวมเป็นค่าเดียวบดบัง
   ΔH ที่ typology proposal ต้องใช้ (ΔH1/ΔH2 ต้องเทียบจุดต่อจุด ไม่ใช่สถานีต่อสถานี) — **tag:
   INSTINCT** (แนวทาง ไม่ใช่ verified schema change).
3. **เพิ่ม `profile_order` ต่อสถานีในแต่ละ canal chain** (`east_chain.yaml` และ chain อื่น) —
   **why**: ทำให้ query "สถานีถัดไปตามน้ำไหล" เป็นเชิงตัวเลขได้ (sort by order) แทนอาศัยลำดับใน
   YAML list เฉย ๆ ซึ่งเปราะบางต่อการแก้ไขในอนาคต — **tag: INSTINCT**.
4. **เพิ่ม "หาสถานีใกล้ฉัน" (geo-nearest)** เป็น UI/query capability บนหน้า public ของเราเอง —
   **why**: ผู้ใช้ทั่วไปอยากรู้ "สถานีที่ใกล้ฉันที่สุดสถานะเป็นอย่างไร" ไม่ใช่เลื่อนหาเอง — **tag:
   INSTINCT** (UX borrow, ไม่กระทบ data model).
5. **ทดสอบว่า `weather.bangkok.go.th/KlongMap`'s backend เป็นตารางเดียวกับ
   `BMA_STATION_DETAIL_PROBE`'s `water/StationDetail` หรือ sibling** — **why**: ถ้าใช่ table
   เดียวกัน อาจได้ field `water_control`/threshold คู่ (out01/out02) เพิ่มเติมจากที่ probe เดิม
   เจอ (ซึ่งพบแค่ null ทุกสถานี) — ต้องยืนยันก่อนนำมาใช้จริง — **tag: OPEN** (ต้องการ probe เพิ่ม
   ในงานถัดไป, นอกงบของงานนี้).
6. **อย่ายืม flood69 เป็น upstream source โดยตรง** — มันเป็นแค่ cache 5 นาทีของ BMA เอง (มี delay
   ในตัว + ไม่มี licence ชัดเจน) — ถ้าต้องการข้อมูลสด ให้ต่อ BMA endpoint ตรง
   (`bma_watermap`/`BMA_STATION_DETAIL_PROBE`) ไม่ใช่ผ่าน proxy ของพรรคการเมือง — **why**:
   หลีกเลี่ยงการพึ่งพา third-party ที่อาจเปลี่ยน/ปิดได้ทุกเมื่อโดยไม่แจ้ง และหลีกเลี่ยงความสับสน
   เรื่อง provenance (ข้อมูลเดียวกัน ป้ายชื่อคนละหน่วยงาน) — **tag: INSTINCT** (นโยบาย ไม่ใช่
   ข้อเท็จจริงที่วัดได้).

## แหล่งข้อมูลดิบที่เก็บไว้

`raw/live/flood69_peoplesparty/index_2026-09-27.html`,
`raw/live/flood69_peoplesparty/index_bundle_2026-09-27.js`,
`raw/live/flood69_peoplesparty/api_klongmap_2026-09-27.json` — ดู census แถวใน
`sources/api_census_flood69.yaml`.
