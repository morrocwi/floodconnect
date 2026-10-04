# Card — เรือผลักดันน้ำ (water-pushing boats) as a flood-response tool

**Tag**: RELAYED (news reports + one operator interview, none of it a primary document
opened directly by this repo) · **บันทึกเข้า**: 2569-09-28 · **ผู้แถลง/ผู้ให้สัมภาษณ์**:
ROLE เท่านั้น (ผู้ประกอบการเรือโดยสารคลองแสนแสบ; ไม่มีชื่อบุคคล/ชื่อบริษัท ตามกฎห้ามใส่ชื่อบุคคล
ที่ไม่ได้รับอนุญาต) · **status**: OPEN on effectiveness (see §4)

## เกี่ยวข้องกับ node/สถานีใดในโปรเจกต์นี้

- `RES.BOAT_PUSH.AG_UNKNOWN.01` (typology/nodes/resources.yaml) — node นี้มีอยู่แล้วในคลัง
  ก่อนงานนี้ (source เดิม: STRUCTURAL_ISSUES_2026-09-28.md ภาคผนวก 4.3, S11/JS100). งานวิจัยนี้
  เป็น **แหล่งอิสระที่สอง** สำหรับเรือผลักดันน้ำคลองแสนแสบชุดเดียวกันในเหตุการณ์ 2569 เดียวกัน —
  **reuse-first**: อัปเดตแถวเดิม ไม่สร้าง node ซ้ำ (ดูเหตุผลใน §5)
- `tunnel:bma_dds:saensaeb_ladprao` (จุดรับน้ำอุโมงค์แสนแสบ-ลาดพร้าว, alias candidate "อุโมงค์
  พระราม 9" — `typology/nodes/environman_extension_2026-09-28.yaml`)
- `AG_BMA_GOV`, `AG_DDS` (สนน.)

## 1. เหตุการณ์ 2569 (S9 ใกล้อุโมงค์พระราม 9)

แหล่ง: The Bangkok Insight, 27 ก.ย. 2569
<https://www.thebangkokinsight.com/news/politics-general/general/1701479/> และ MGR Online,
27 ก.ย. 2569 <https://mgronline.com/business/detail/9690000094733> (ทั้งสองแหล่ง RELAYED,
ไม่ใช่เอกสารปฐมภูมิ)

- ผู้ประกอบการเรือโดยสารคลองแสนแสบรายหนึ่งนำเรือมาจอดใกล้จุดรับน้ำอุโมงค์ระบายน้ำใต้ดิน
  บริเวณพระราม 9 (ระยะที่แหล่งข่าวระบุ: **"ประมาณ 1 กิโลเมตร"**) เดินเครื่องยนต์เรือเพื่อ
  "ผลักดัน"/เร่งน้ำให้ไหลเข้าอุโมงค์ และลงสู่คลองพระโขนง
- หมุนเวียนเรือทำงาน **"ตลอด 24 ชั่วโมง"** (ตัวเลขนี้เป็นข้อความอ้างอิงจากข่าว ไม่ใช่ค่าที่วัดเอง)
- ผู้ประกอบการให้สัมภาษณ์ว่าได้ประสาน/ได้รับความเห็นชอบจาก กทม. ก่อนดำเนินการ (คำกล่าวอ้างของผู้
  ประกอบการเอง — RELAYED, ไม่ใช่คำยืนยันจาก กทม. โดยตรงในแหล่งเดียวกัน)
- มีการพิจารณาข้อจำกัดเรื่องสะพาน/การเดินเรือ (bridge/navigation clearance) ก่อนวางเส้นทางเรือ
- ผู้ประกอบการอ้างว่าระดับน้ำลดลง (ตัวเลข cm ที่ระบุในข่าว หากมี ให้ถือเป็น**คำให้สัมภาษณ์ ไม่ใช่ค่า
  วัดอิสระ** — **effect_measured: OPEN**, ไม่มีเกจอิสระของคลังนี้ยืนยัน)

## 2. เทคนิคที่เป็นที่ยอมรับมาก่อน (established technique, RELAYED)

- ริเริ่มในรัชกาลที่ 9 ("เรือผลักดันน้ำ" พระราชดำริ) พัฒนาโดยกรมชลประทาน — **ปีที่เริ่มยังขัดแย้งกัน
  ระหว่างแหล่ง: บางแหล่งระบุ พ.ศ. 2528, บางแหล่งระบุ พ.ศ. 2538 — OPEN**, ไม่เลือกปีใดปีหนึ่งโดย
  ไม่มีหลักฐานชี้ขาด
- วัตถุประสงค์ที่มักอ้างถึง: เร่งการไหลของน้ำเข้าสู่ประตูระบาย/จุดสูบน้ำ, พัดพาตะกอน (flush
  sediment), เร่งการระบายออกสู่ทะเล
- กองทัพเรือเคยนำเรือผลักดันน้ำไปใช้งานหลายครั้ง — bangkokbiznews
  <https://www.bangkokbiznews.com/news/1207987> และ mgronline
  <https://mgronline.com/onlinesection/detail/9600000108261> (ตัวเลขจำนวนเรือ/แรงม้า/รอบเครื่อง
  (hp/rpm) หรืออัตราการไหลที่ปรากฏในสองแหล่งนี้ **เป็นข้อความอ้างอิงในการ์ดนี้เท่านั้น ไม่ใส่ในชั้น
  typology**)

## 3. ประสิทธิผลยังเป็นข้อถกเถียง / ยังไม่วัด (OPEN)

แหล่ง: mgronline, 2554 <https://mgronline.com/daily/detail/9540000135295>

- มีผู้วิจารณ์เรื่องจุดวัดผล (measurement point) และการใช้ในแม่น้ำ/คลองกว้าง ว่าอาจไม่เห็นผลชัดเจน
- วิศวกรบางรายให้ความเห็นว่าเทคนิคนี้อาจช่วยได้จริงในคลองแคบ (narrow canal) มากกว่าลำน้ำกว้าง
- **ไม่มีการวัดผลอิสระ (independent measurement) ของคลังนี้เองสำหรับทั้งเหตุการณ์ 2569 และเทคนิค
  โดยทั่วไป — effectiveness: OPEN เสมอ**, ไม่ยกระดับเป็น RELAYED/MEASURED จนกว่าจะมีเกจอิสระ
  เทียบก่อน/หลังวางเรือในบริเวณเดียวกัน

## 4. เครื่องผลักดันน้ำแบบ axial-flow ติดตั้งจุดตายตัว (แยกเครื่องมือ)

- พบการอ้างถึงเครื่อง "water pusher" แบบ axial-flow ติดตั้งจุดตายตัว (fixed point) ยกข้ามคันดิน/
  คันคลอง (lift over banks) — เป็นเครื่องมือคนละประเภทกับเรือ (ไม่เคลื่อนที่, ไม่ใช้เครื่องยนต์เรือ)
- **ไม่พบคู่มือทางการของกรมชลประทาน (RID) ที่อธิบายเครื่องมือประเภทนี้โดยตรงในการค้นครั้งนี้ —
  OPEN**, ไม่ยืนยัน manufacturer/มาตรฐานใด ๆ

## Typology extension วันนี้ (ดู `typology/nodes/tool_water_push_boats_2026-09-28.yaml` +
`typology/edges/tool_water_push_boats_2026-09-28.yaml`)

เครือข่าย node เท่านั้น (ตามกฎ "ไม่ต้องเอาตัวเลข สกัดแค่เครือข่าย node" ของฟาวน์เดอร์) —
**ไม่มีจำนวนเรือ/แรงม้า/รอบเครื่อง/ซม.ที่ลดลง/จำนวนเรือกองทัพเรือ ในชั้น typology เลย** ตัวเลข
ทั้งหมดอยู่ในการ์ดนี้ (§1-§2) เท่านั้น:

1. `RES.TOOL.WATER_PUSH_BOAT` — node เครื่องมือทั่วไป (generic tool class), `kind: resource`,
   `tool_class: water_push_boat`, `infra_class: soft`, `mode: boat`
2. `RES.TOOL.AXIAL_WATER_PUSHER` — node เครื่องมือทั่วไปอีกประเภท (fixed-point, lift-over-bank),
   ไม่มี edge เชื่อมใด ๆ (orphan โดยตั้งใจ, listed OPEN — ไม่มีคู่มือ RID ยืนยัน)
3. `RES.BOAT_PUSH.AG_UNKNOWN.01` — อัปเดตแถวเดิม: เพิ่ม `tool_class`, `generic_tool_ref`,
   `effectiveness: OPEN` (อ้างอิงการ์ดนี้), `deployment_note_th` (ไม่มีตัวเลขระยะทาง)
4. `AG_OPERATOR_SAENSAEB_BOAT` — node ตัวแทนผู้ประกอบการ (civil agency, `agency_class:
   commercial_operator`), ไม่มีชื่อบุคคล/บริษัท
5. edges: `supplies` (เรือ → จุดรับน้ำอุโมงค์พระราม 9, tag RELAYED), `operates` (ผู้ประกอบการ →
   เรือ, tag RELAYED), `reports_to` (ผู้ประกอบการ → AG_BMA_GOV, tag RELAYED "คำให้สัมภาษณ์ของ
   ผู้ประกอบการ"; ผู้ประกอบการ → AG_DDS, tag OPEN — ไม่มีแหล่งใดยืนยันการประสานกับ สนน. โดยตรง)

## 5. Reuse-first decision (บันทึกไว้ให้ตรวจสอบย้อนกลับได้)

Founder's ask ตั้งต้นเสนอ id ใหม่ `RES.BOAT_WATERPUSH.SAENSAEB_RAMA9` สำหรับ deployment
instance — งานนี้**เลือกใช้ id เดิม `RES.BOAT_PUSH.AG_UNKNOWN.01` แทน** เพราะเป็น real-world
referent เดียวกัน (เรือผลักดันน้ำคลองแสนแสบ ในเหตุการณ์ 2569 เดียวกัน — S11/JS100 vs Bangkok
Insight/MGR 27 ก.ย. น่าจะพูดถึงปฏิบัติการเดียวกันหรือช่วงเวลาเดียวกัน) ตามวินัย reuse-first/
ห้ามสร้าง duplicate หรือ renamed twin ของคลังนี้เอง (ดู `tools/typology/build_graph.py` header
และ `typology/nodes/agencies.yaml` บรรทัด AG_ESTATE สำหรับ precedent เดียวกัน) — บันทึกการ
ตัดสินใจนี้ไว้ให้ตรวจสอบย้อนกลับได้ ไม่ใช่เงียบเปลี่ยนโดยไม่บอก.

Founder's ask ยังเสนอ id ผู้ประกอบการ `CIV.OPERATOR.SAENSAEB_BOAT` — คลังนี้ไม่มี node kind/id
prefix `CIV.*` อยู่จริงที่ไหนเลย (ตรวจแล้วด้วย grep) มีแต่ `kind: agency` + `layer: civil` +
`agency_class` (ตัวอย่าง `AG_ESTATE`, `AG_FB_ADMIN`, `AG_JS100`, `AG_VOLUNTEER_MOTOSAI_
SAMMAKORN`) — งานนี้จึงใช้ id `AG_OPERATOR_SAENSAEB_BOAT` (`kind: agency`, `layer: civil`,
`agency_class: commercial_operator`) ให้ตรงกับ convention จริงของคลังนี้แทนการสร้าง prefix
ใหม่ที่ไม่เคยมีมาก่อน.
