# Card — โดรนกู้ภัย เคหะชุมชนร่มเกล้า (rescue/survey drones, access-first case)

**Tag**: RELAYED (Facebook page ทางการของกระทรวง อว. -- MHESI, โพสต์ 28 ก.ย. 2569; ไม่ใช่
เอกสารปฐมภูมิที่คลังนี้เปิดอ่านเอง) · **บันทึกเข้า**: 2569-09-28 · **ผู้แถลง**: ROLE/หน่วยงาน
เท่านั้น (ไม่มีชื่อเจ้าหน้าที่บุคคล -- ชื่อบริษัท/สมาคม/มูลนิธิ ถือเป็นชื่อองค์กร ไม่ใช่บุคคล จึงใส่ได้)

## เกี่ยวข้องกับ node/สถานีใดในโปรเจกต์นี้

- `site/inputs/community/self_help_dag.yaml` -- เพิ่ม area `romklao` (zone + support nodes)
- ยังไม่มี node สำหรับเคหะร่มเกล้าในคลังนี้มาก่อนงานนี้ -- ทุก node ใน node registry ใหม่นี้
  เป็นของใหม่ทั้งหมด

## 1. บริบท (RELAYED, กระทรวง อว. Facebook post 28 ก.ย. 2569)

- เคหะชุมชนร่มเกล้า (เขตลาดกระบัง) เป็นชุมชนหนาแน่น -- จุดที่โพสต์เรียกว่า "ไข่แดง" ของศูนย์กลาง
  ชุมชนท่วมหนักมาก
- เรือเข้าไม่ถึงหลายจุดเพราะสิ่งกีดขวาง/รั้ว (obstacles/fences) ขวางเส้นทางเรือ -- เกิดช่องว่างการ
  เข้าถึง (access gap)
- มีการใช้โดรนเข้าถึงพื้นที่ที่เรือเข้าไม่ได้ -- **ตัวอย่างจริงของกติกา "restore access เมื่อโหมด
  หนึ่งใช้ไม่ได้": เรือ (boat mode) ถูกบล็อก -> เปลี่ยนไปใช้โหมดอากาศ/โดรน (air/drone mode)**
- โดรนที่ใช้มี 2 กลุ่มหน้าที่ตามที่โพสต์อธิบาย: (1) โดรนสำรวจ ISR วิเคราะห์ภาพ/เรดาร์ (ISR survey
  drone) และ (2) โดรนขนส่งยกของหนัก (heavy-lift transport drone) ปล่อยของผ่านสายสลิง (sling)
- หน่วยงาน/องค์กรที่ร่วมงาน (ตามโพสต์): กระทรวง อว. (MHESI), กระทรวง พม. (MSDHS) ซึ่งมีครัวกลาง
  ของตัวเอง, มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ (มจพ.), สมาคมอุตสาหกรรมเพื่อการป้องกัน
  ประเทศ (สอป.), บริษัทเอกชนด้านโดรน (บริษัท ซิสทรอนิกส์ จำกัด -- ชื่อบริษัท ไม่ใช่ชื่อบุคคล), และ
  มูลนิธิกู้ภัยร่มไทร (rescue foundation, ภาคประชาสังคม)
- จุดปฏิบัติการ/ครัวที่โพสต์ระบุ: ศูนย์ปฏิบัติการ+ครัวกลางที่ปากซอยรามคำแหง 192 (มีนบุรี), ฐานหลักที่
  ร่มเกล้า 2, แผนย้ายครัวกลางไปวัดปากบึง, จุดจอดรถ 4WD สำรอง

(ตัวเลข: จำนวนประชากร, จำนวนโดรน, พิกัดยกน้ำหนัก/lift capacity, ความยาวสายสลิง, ระยะทาง --
**ระบุไว้ในการ์ดนี้เป็นข้อความอ้างอิงเท่านั้น** ตามที่โพสต์ต้นทางระบุ (ไม่ยกระดับเป็น MEASURED,
ยังไม่มีตัวเลขที่ยืนยันแยกต่างหากจากคลังนี้เอง) -- **ไม่มีตัวเลขเหล่านี้ในชั้น typology เลย**)

## 2. Access-first link (RESTORE_ACCESS)

กรณีนี้เป็นตัวอย่างของกติกา access-first ของคลังนี้: เมื่อโหมดหนึ่ง (boat) ใช้ไม่ได้เพราะสิ่งกีดขวาง
กายภาพ ให้เปลี่ยนโหมด (air/drone) แทนการหยุดปฏิบัติการ -- บันทึกไว้ในความสัมพันธ์ boat mode
blocked -> air/drone mode ผ่านเอกสารนี้และ `community_dag.py`'s `EDGE_MODES` (เพิ่ม
`air_drone`, ดู §4)

## 3. Typology extension (ดู
`typology/nodes/mhesi_rescue_drones_romklao_2026-09-28.yaml` + edges ใน
`typology/edges/part_of.yaml` / `operates.yaml` / `supplies.yaml` / `reports_to.yaml`)

เครือข่ายเท่านั้น ไม่มีตัวเลข ไม่มีชื่อเจ้าหน้าที่บุคคล:

1. `RES.TOOL.RESCUE_DRONE` -- เครื่องมือทั่วไป (`kind: resource`, `tool_class: rescue_drone`,
   `drone_subtypes: [isr_survey, heavy_lift_transport]`, `mode: air_drone`)
2. `RES.DRONE.ROMKLAO_20260928` -- deployment instance, `generic_tool_ref:
   RES.TOOL.RESCUE_DRONE`
3. `RES.KITCHEN.MSDHS_CENTRAL` -- ครัวกลาง พม., `owner_agency: AG_MSDHS`
4. `AG_MHESI`, `AG_MSDHS` (reused ids from `docs/knowledge/water_system_dag.mmd`, ยังไม่เคย
   ถูกประกาศใน typology registry มาก่อนงานนี้ -- ประกาศจริงครั้งแรกที่นี่), `AG_KMUTNB` (มจพ.),
   `AG_SOP` (สอป.), `AG_SYSTRONICS` (บริษัท ซิสทรอนิกส์ จำกัด), `AG_RESCUE_ROMSAI` (มูลนิธิกู้ภัย
   ร่มไทร)
5. `MINISTRY.MHESI`, `MINISTRY.SOCIAL` -- ministry node ใหม่ 2 อัน (คลังนี้ยังไม่เคยมี ministry
   node สำหรับ อว./พม. มาก่อน แม้ AG_MHESI/AG_MSDHS จะปรากฏใน water_system_dag.mmd แล้ว)
6. edges: `part_of` (AG_MHESI/AG_KMUTNB -> MINISTRY.MHESI, AG_MSDHS -> MINISTRY.SOCIAL,
   ministry -> GOV.TH), `operates` (AG_SYSTRONICS/AG_SOP -> โดรน instance, AG_MSDHS ->
   ครัวกลาง), `supplies` (โดรน instance -> romklao_zone, ครัวกลาง -> romklao_zone),
   `reports_to` (AG_SYSTRONICS/AG_SOP -> AG_MHESI, AG_RESCUE_ROMSAI -> AG_MSDHS) ทุก edge
   tag RELAYED

## 4. Self-help DAG (ดู `site/inputs/community/self_help_dag.yaml`,
`docs/COMMUNITY_SELF_HELP_DAG.md`)

- `romklao_zone` (kind zone, layer 2, area_id: romklao) -- node ใหม่, `resources` มีแถว
  `type: drone` อ้างอิง `RES.TOOL.RESCUE_DRONE` (เงื่อนไข boolean/text เหมือนแถว boat ของ
  สัมมากร ไม่มีตัวเลข)
- support node (layer 3) 4 จุด: ศูนย์ปฏิบัติการ+ครัวกลาง ปากซอยรามคำแหง 192, ฐานหลักร่มเกล้า 2,
  แผนย้ายครัวกลางวัดปากบึง, จุดจอดรถ 4WD สำรอง -- **ทุกจุด `status: UNKNOWN`, `fresh: false`**
  (ยังไม่ได้ตรวจภาคสนามโดยคลังนี้เอง ตามกฎเดิมของเอกสารนี้)
- `EDGE_MODES` (`community_dag.py`) เพิ่ม `air_drone` -- **ใช้สำหรับส่งของ/สำรวจเท่านั้น ไม่ใช้
  สำหรับย้ายคน** (บันทึกไว้ชัดในคอมเมนต์โค้ดและเอกสารนี้)
