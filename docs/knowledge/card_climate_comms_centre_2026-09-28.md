# Card — ศูนย์ความร่วมมือด้านการสื่อสารข้อมูลสภาพภูมิอากาศ (MDES climate-comms centre)

**Tag**: RELAYED (ข่าวแถลงกระทรวงดีอี 28 ก.ย. 2569 -- สื่อที่แถลงไม่ระบุในต้นฉบับที่ส่งต่อมาให้
งานนี้, ไม่ใช่เอกสารปฐมภูมิที่คลังนี้เปิดอ่านเอง) · **บันทึกเข้า**: 2569-09-28 · **ผู้แถลง**:
ROLE เท่านั้น (ไม่มีชื่อบุคคล)

## เกี่ยวข้องกับ node/สถานีใดในโปรเจกต์นี้

- `AG_TMD` (มีอยู่แล้ว, `typology/nodes/agencies.yaml`) -- หน่วยงานเจ้าภาพ/นำร่องศูนย์นี้
- `MINISTRY.DIGITAL` (มีอยู่แล้ว, `typology/nodes/ministries.yaml`) -- reuse แทนการสร้าง
  "AG_DE" ใหม่ (ดู §5)
- `MINISTRY.PMO` (มีอยู่แล้ว) -- สำนักนายกรัฐมนตรี, ที่ตั้งของโฆษกและ PRD

## 1. ข้อเท็จจริงจากข่าวแถลง (28 ก.ย. 2569, RELAYED)

- กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม (ดีอี) เปิด **ศูนย์ความร่วมมือด้านการสื่อสารข้อมูลสภาพ
  ภูมิอากาศ** ที่ศูนย์พยากรณ์อากาศและเตือนภัย ของกรมอุตุนิยมวิทยา (TMD) ตามมติคณะรัฐมนตรี
  (cabinet resolution)
- TMD เป็นหน่วยงานหลัก (lead agency) รับผิดชอบข้อมูลภูมิอากาศที่ชัดเจน เข้าใจง่าย ร่วมกับ
  โฆษกประจำสำนักนายกรัฐมนตรี, กรมประชาสัมพันธ์ (พีอาร์ดี), และ บมจ. อสมท (MCOT,
  รัฐวิสาหกิจ) เพื่อให้ประชาชนได้รับข้อความชุดเดียวกัน (one consistent message)
- ข้อมูลชุดเดียวกันถูกส่งผ่านช่องทาง พีอาร์ดี, อสมท, และทำเนียบรัฐบาล (ทีวี วิทยุ โซเชียลมีเดีย
  ทุกสื่อ)
- กติกาการนำเสนอใหม่: การพยากรณ์/ข้อมูลภัยต้องแสดง**ระดับความรุนแรงเป็นสัญลักษณ์พร้อมตัวเลข**
  เทียบกับเหตุการณ์น้ำท่วม/ภัยในอดีต เพื่อให้ประชาชนเห็นความรุนแรงเทียบเคียงได้
- กระทรวงขอโทษต่อสาธารณะสำหรับเหตุการณ์ล่าสุด (structural-issue evidence: การยอมรับว่าการ
  สื่อสารเตือนภัยล้มเหลว)
- การเฝ้าระวังข่าวปลอม: ศูนย์ต่อต้านข่าวปลอม (Anti-Fake News Center, AFNC) ภายใต้ดีอี --
  สายด่วน **1111 ต่อ 87 (24 ชม.)**, antifakenewscenter.com, LINE @antifakenewscenter

(ตัวเลข/รหัสติดต่อข้างต้นเป็นข้อความอ้างอิงในการ์ดนี้เท่านั้น -- ไม่ใส่ในชั้น typology)

## 2. Typology extension (ดู
`typology/nodes/mdes_climate_comms_2026-09-28.yaml` +
`typology/edges/part_of.yaml` / `operates.yaml` / `reports_to.yaml` / `warns.yaml`)

เครือข่าย node เท่านั้น ไม่มีชื่อบุคคล (เจ้าหน้าที่/โฆษก อ้างถึงด้วยตำแหน่งเท่านั้น):

1. `AG_CLIMATE_COMMS_CENTRE` -- ศูนย์ใหม่ (agency/command node, `permanence:
   established_by_cabinet_resolution`, `level: national`), `part_of` -> `MINISTRY.DIGITAL`
2. `AG_PRD` -- กรมประชาสัมพันธ์, `part_of` -> `MINISTRY.PMO`
3. `AG_MCOT` -- บมจ. อสมท (รัฐวิสาหกิจ), `agency_class: state_enterprise` -- **ไม่มี** `part_of`
   edge (ไม่อยู่ใน 4 รัฐวิสาหกิจของเอกสาร กพร. Joint KPI ที่คลังนี้เคยบันทึกไว้ -- ดู §5)
4. `AG_PM_SPOKES` -- โฆษกประจำสำนักนายกรัฐมนตรี, `part_of` -> `MINISTRY.PMO`
5. `AG_AFNC` -- ศูนย์ต่อต้านข่าวปลอม, `part_of` -> `MINISTRY.DIGITAL`, node นี้เป็น**ช่องทาง
   เฝ้าระวังข่าวปลอม เท่านั้น -- ไม่มีการตัดสิน/อ้างสิทธิ์ใด ๆ ว่าอะไรคือข่าวปลอมในคลังนี้**
6. `AG_TMD` reuse -- มี `part_of -> MINISTRY.DIGITAL` อยู่แล้วในคลังนี้ก่อนงานนี้
7. `operates`: `AG_TMD -> AG_CLIMATE_COMMS_CENTRE` (TMD เดินศูนย์)
8. `reports_to` (channel-partner coordination, ไม่ใช่ chain-of-command): `AG_PRD ->
   AG_CLIMATE_COMMS_CENTRE`, `AG_MCOT -> AG_CLIMATE_COMMS_CENTRE`, `AG_PM_SPOKES ->
   AG_CLIMATE_COMMS_CENTRE`
9. `warns` (hop 1 เท่านั้น, ศูนย์ -> ช่องทาง; hop 2 ไปยัง zone ยังเป็น OPEN เพราะศูนย์นี้สื่อสาร
   ระดับชาติ ไม่ผูกกับ zone ใดใน worked example ของคลังนี้โดยตรง): `AG_CLIMATE_COMMS_CENTRE
   -> WCH.TV_RADIO_PRD_MCOT`, `AG_CLIMATE_COMMS_CENTRE -> WCH.GOV_SOCIAL` --
   `instruction`/`datum`/`area`/`lead_time` = `"OPEN"` ทั้งหมด ยกเว้น `severity_scale:
   "symbolic+numeric compared to past events (announced policy)"`

## 3. Structural-issue rows (ดู `docs/knowledge/structural_issues_2026-09-28.yaml`)

- **ISSUE-WARNING-04** -- กระทรวงยอมรับ/ขอโทษต่อความล้มเหลวของการสื่อสารเตือนภัย ->
  policy response = ข้อความจากแหล่งเดียว (single-source) + severity scale ใหม่ -- เชื่อมกับ
  `ISSUE-WARNING-01` เดิม (ปัญหา "ภาษาคน") และบทบาทของ `AG_TMD` ที่แยกงานพยากรณ์ (มติ
  Joint KPI เดิม) ออกจากงานสื่อสารสาธารณะ (ศูนย์ใหม่นี้)
- **ISSUE-WARNING-05** -- นโยบาย "เสียงเดียว" (single-voice) เทียบกับกติกา conflicting-data
  ของคลังนี้เอง (เก็บทั้งสองฝั่งเสมอเมื่อมีการอ่านค่าขัดแย้งกัน) -- **การมีข้อความทางการเดียวไม่ได้
  ลบล้างค่าที่วัดขัดแย้งกัน** -- ใส่แบบเป็นกลาง (neutral framing) ไม่ตัดสินว่านโยบายถูกหรือผิด

## 4. AFNC -- neutral note

`AG_AFNC` บันทึกไว้เป็น**ช่องทางเฝ้าระวัง** (monitoring channel node) เท่านั้น คลังนี้ไม่ตัดสิน/
อ้างสิทธิ์ใด ๆ ว่าข้อความหรือแหล่งใดเป็น "ข่าวปลอม" -- ไม่มี edge ใดจากศูนย์นี้ไปยัง node ข้อมูล/
เกจของคลังนี้เอง

## 5. Reuse-first decisions

- Founder's ask เรียกกระทรวงนี้ว่า "AG_DE" -- คลังนี้มี `MINISTRY.DIGITAL`
  (กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม) อยู่แล้ว (`typology/nodes/ministries.yaml`,
  จาก Joint KPI list ที่บันทึกไว้ก่อนงานนี้) -- reuse ตรง ไม่สร้าง node ใหม่ซ้ำ
- `AG_MCOT` ไม่อยู่ใน 4 รัฐวิสาหกิจที่เอกสาร กพร. Joint KPI ระบุ (กปน./กปภ./องค์การจัดการน้ำเสีย/
  กนอ., `CATEGORY.STATE_ENTERPRISE`) -- งานนี้จึงไม่เพิ่ม `part_of` edge ไปยังหมวดนั้น (จะเป็น
  การกล่าวอ้างเกินแหล่งที่มา) ใส่แค่ `agency_class: state_enterprise` เป็น attribute แทน
