# `kb.py accountability` -- ใครรับผิดชอบที่นี่ / อำนาจซ้อนทับ / กฎหมายมีปัญหา / ประชาชนทำอะไรได้เอง

**คำสั่งของ founder (verbatim)**: "ระบบต้องรู้เลยว่า น้ำท่วมที่นี่ใครรับผิดชอบ และอำนาจในการควบคุม
ทรัพยากรที่ซ้อนทับกันหรือต้องการความร่วมมือระหว่าง node คืออะไร และมีกฎหมายหรืออำนาจข้อไหนที่อาจมี
ปัญหา แล้วประชาชนจะดูแลตัวเองอย่างไรในสภาพ ecosystem แบบนั้น" + เลนส์: "มองผ่านเลนส์ประชาชนแบบ
ช่วยตัวเองได้ จากข้อมูลทั้งระบบ โดยใช้สารสนเทศทั้งหมดที่เรามี".

โค้ดจริงอยู่ที่ `tools/kg/accountability.py`; `kb.py accountability` เป็นแค่ dispatcher (per this
task's own instruction ที่ให้ตรรกะอยู่ใน tools/kg/, kb.py แค่เรียก).

## วิธีใช้

```
python3 kb.py accountability --at "13.758235,100.676084"     # lat,lon
python3 kb.py accountability --at sammakorn                    # area_id (จาก site/build_data.py's
                                                                # own declared centre_lat/lon, RELAYED)
python3 kb.py accountability --at "gauge:thaiwater_waterlevel:C.13" --radius 5   # asset_id ในกราฟ
python3 kb.py accountability --at sammakorn --json             # JSON output
```

`--radius` เป็นกิโลเมตร ค่า default 3.0 กม. (ตามที่ founder ระบุ). พื้นที่ `sammakorn`/`ram53` มาจาก
`site/build_data.py`'s เอง `centre_lat`/`centre_lon` (RELAYED, ไม่ใช่ geocode ใหม่).

## ตรรกะ 4 คำถาม (ทุกบรรทัดมี tag)

- **Q1 ใครรับผิดชอบที่นี่** -- หา asset ที่มี lat/lon ใน radius (จาก
  `output/thailand_water_kg.graphml`) → เดินตาม edge `OWNS` ไปยัง owner string ของ asset นั้น →
  แปลง owner string เป็น `AG_*` node ผ่าน `sources/owner_agency_crosswalk.yaml` (ไฟล์ crosswalk
  ใหม่ที่ task นี้สร้าง แก้ known gap ที่ `tools/kg/README.md` ระบุไว้แล้ว) → เดินย้อน edge
  `COMMANDS` ขึ้นไปเรื่อย ๆ "ไกลเท่าที่กราฟมี" (โค้ด generic ไม่ hardcode จำนวนชั้น เผื่อ nationwide
  hierarchy ที่กำลังทำคู่ขนานเพิ่ม node เข้ามา) → หา edge `AUTHORIZES` ที่ชี้เข้า agency นั้นจาก
  `LAW_*` node (บอกด้วยว่ามาตรา "OPEN" หรือระบุไว้ในป้ายชื่อแล้ว).
- **Q2 อำนาจซ้อน/ต้องร่วมมือ** -- เรียกฟังก์ชันจาก `tools/dag/bottlenecks.py` ตรง ๆ (import ไม่ copy):
  `conflicting_commanders`, `ownership_gaps`, `shares_without_arbitration` บนกราฟ mermaid ที่ parse
  ด้วย `bn.parse_dag` แล้วกรองเฉพาะแถวที่แตะ agency ที่ Q1 เจอ.
- **Q3 กฎหมาย/อำนาจมีปัญหา** -- อ่าน attribute `problem_academic`/`problem_tag`/`problem_sources`
  ที่ `tools/kg/build_kg.py`'s `apply_edge_problems()` แปะไว้บน edge ของกราฟรวมอยู่แล้ว (จาก
  `docs/knowledge/edge_problems.yaml`) เฉพาะ edge ที่อยู่บน "เส้นทาง" ของ Q1 (edge OWNS/COMMANDS/
  AUTHORIZES ที่เดินผ่านจริง) + node ที่มี attribute `missing_edge_problem` บนเส้นทางนั้น + กฎหมายที่
  ป้ายชื่อยังเขียน "มาตรา OPEN".
- **Q4 ประชาชนทำอะไรได้เอง** -- ตาราง action ที่คัดจาก `WATER_MANAGER_QUESTION_BANK.md` (แถว VLG),
  card_yucharoen_model_2554.md, card_rangsit_local_gov_flood_2561.md, card_hatyai_city_climate.md
  ผูกกับ (1) class ของ asset ที่อยู่ใกล้ และ (2) สถานะปัจจุบันจาก `readout_log` (เช่น ปั๊มขัดข้อง กี่/กี่
  สถานี, อ่านเมื่อ area_id ที่รู้จักเท่านั้น -- lat/lon ดิบไม่ผูก readout_log). ทุก action ขึ้นต้นด้วย
  "อาจทำได้" และอ้าง card เสมอ; ตรวจแล้วว่าไม่มีคำ "ไม่ต้อง/ห้าม/ไม่ควร/ผ่อนคลาย" ปนอยู่ (assert ใน
  โค้ดเอง, ดู `test_q4_matches_pump_action_and_no_banned_words`).

**Refusal**: ถ้า Q1 ไม่เจอ asset ในรัศมี หรือไม่มี OWNS chain -> `{"refused": "<เหตุผล>"}` เฉพาะ
คำถามนั้น คำถามอื่นยังพยายามตอบเท่าที่ทำได้ (ไม่ใช่ all-or-nothing).

## ผลจริง -- Sammakorn (13.758235, 100.676084, radius 3 km) 2026-09-27

> **Finding**: this is a LOCAL-ONLY result, not reproducible from a
> fresh clone of this public tree as-is. It needs `output/thailand_water_kg.graphml`
> built with the full private pipeline's real collected data; a fresh self-install's
> `python -m tools.kg.build_kg` fails with "no asset node within 3.0 km" because the
> public tree ships no pre-built graph (see `tools/public_sync_exclude.txt`'s exclusion
> of `output/*.graphml` on the private side) and the harvest steps that feed it (the
> asset-registry census, OWNS-chain resolution from live government sources) are not
> fully documented as a standalone runbook here. Treat the transcript below as a
> worked EXAMPLE of the shape of a real answer, not a command you can run and get the
> same output from right now.

รันจาก `python3 kb.py accountability --at "13.758235,100.676084"` (verbatim):

```
# accountability card -- ที่: 13.758235,100.676084
[VERIFIED] resolved to lat=13.758235, lon=100.676084 (13.758235,100.676084), radius=3.0 km

## Q1 ใครรับผิดชอบที่นี่
[MEASURED] 9 asset(s) within 3.0 km
  [VERIFIED] pump_station "สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่" (pump_station:pumphistory:ST.SPS.02) — 0.478 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] pump_station "สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2" (pump_station:pumphistory:ST.SPS.03) — 0.981 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] pump_station "สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง" (pump_station:pumphistory:ST.SPS.04) — 1.432 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] gauge "สนข.สะพานสูง" (gauge:thaiwater_rain:RF.SPS.01) — 1.551 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] rain_gauge "สนข.สะพานสูง" (rain_gauge:thaiwater_rain_24h:528759) — 1.551 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] pump_station "สถานีสูบน้ำคลองบ้านม้า 2" (pump_station:pumphistory:ST.SPS.01) — 2.074 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] gauge "ค.แสนแสบ-เสรีไทย 24" (gauge:thaiwater_bma:WL.SSB.08) — 2.487 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] gauge "คลองแสนแสบช่วง ซ.เสรีไทย 24 เขตบึงกุ่ม" (gauge:thaiwater_bma:SS06) — 2.489 km, owner='สำนักการระบายน้ำ กรุงเทพมหานคร', latest=None@None
    [VERIFIED] OWNS -> agency_id=AG_DDS (exact label match: AG_DDS = "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")
    [RELAYED-GENERAL] COMMANDS level 1: AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.)
    [OPEN] COMMANDS level 2: AG_ADMIN_COURT (ศาลปกครอง)
    [RELAYED-GENERAL] COMMANDS level 2: AG_MOI_CMD (รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550)
    [OPEN] COMMANDS level 2: AG_OMBUDSMAN (ผู้ตรวจการแผ่นดิน)
    [RELAYED] COMMANDS level 3: AG_PM (นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว))
  [VERIFIED] pump_station "สถานีสูบน้ำคลองลำพังพวย (นิด้า)" (pump_station:water_station:76) — 2.86 km, owner='เขตบางกะปิ', latest=None@None
    [OPEN] OWNS -> agency_id=None (owner 'เขตบางกะปิ' has no row in sources/owner_agency_crosswalk.yaml (known gap, see tools/kg/README.md 'Known gaps'))

## Q2 อำนาจซ้อน/ต้องร่วมมือ
  [MEASURED-on-graph] conflicting commanders over DC_ALERT (ประกาศระดับเตือนภัย): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'ปภ. กรมป้องกันและบรรเทาสาธารณภัย (ผู้อำนวยการกลาง)', 'สทนช. สำนักงานทรัพยากรน้ำแห่งชาติ', 'กรมอุตุนิยมวิทยา']
  [MEASURED-on-graph] conflicting commanders over DC_MOBILE (ส่งเครื่องสูบเคลื่อนที่เข้าพื้นที่): ['ปภ. กรมป้องกันและบรรเทาสาธารณภัย (ผู้อำนวยการกลาง)', 'สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'ผอ.เขตสะพานสูง (ผู้ช่วยผู้อำนวยการ กทม.)', 'ศูนย์บัญชาการตาม พ.ร.ก.ฉุกเฉิน / วอร์รูม (ผบ.ทสส.)']
  [MEASURED-on-graph] conflicting commanders over AG_BMA_GOV (ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.): ['ศาลปกครอง', 'รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550', 'ผู้ตรวจการแผ่นดิน']
  [MEASURED-on-graph] conflicting commanders over AG_DDPM (ปภ. กรมป้องกันและบรรเทาสาธารณภัย (ผู้อำนวยการกลาง)): ['รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550', 'กมธ.สภาผู้แทนราษฎร (ที่ดิน ทรัพยากรธรรมชาติและสิ่งแวดล้อม / ป้องกันฯ)', 'คณะกรรมการอุทกภัยและภัยแล้งระดับภูมิภาค 5 คณะ (คำสั่งสำนักนายกฯ 275/2569)']
  [MEASURED-on-graph] conflicting commanders over AG_PROV_GOV (ผู้ว่าราชการจังหวัด (= ผอ.จังหวัด ตาม พ.ร.บ.ป้องกันฯ 2550)): ['ศาลปกครอง', 'คณะกรรมการลุ่มน้ำ (36 ลุ่มน้ำ ตาม พ.ร.บ.ทรัพยากรน้ำ 2561)', 'รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550']
  [MEASURED-on-graph] conflicting commanders over DC_BACKUP_POWER (จัดไฟสำรองสถานีสูบ): ['สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'นิติบุคคลหมู่บ้านจัดสรร / คณะกรรมการหมู่บ้านสัมมากร', 'กฟน. การไฟฟ้านครหลวง']
  [MEASURED-on-graph] conflicting commanders over DC_EMERG (ประกาศ พ.ร.ก.ฉุกเฉิน / ตั้งศูนย์บัญชาการเฉพาะกิจ): ['คณะรัฐมนตรี', 'กนช. คณะกรรมการทรัพยากรน้ำแห่งชาติ', 'นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว)']
  [MEASURED-on-graph] conflicting commanders over DC_EVACUATE (สั่งอพยพ): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'ผอ.เขตสะพานสูง (ผู้ช่วยผู้อำนวยการ กทม.)', 'ศูนย์บัญชาการตาม พ.ร.ก.ฉุกเฉิน / วอร์รูม (ผบ.ทสส.)']
  [MEASURED-on-graph] conflicting commanders over DC_GATE_MINBURI (เปิด/ปิด ปตร.แสนแสบ-มีนบุรี): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว)']
  [MEASURED-on-graph] conflicting commanders over DC_SHELTER (เปิดศูนย์พักพิง): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'ผอ.เขตสะพานสูง (ผู้ช่วยผู้อำนวยการ กทม.)', 'มัสยิด/วัด/โบสถ์ ในพื้นที่']
  [MEASURED-on-graph] conflicting commanders over DC_DECLARE (ประกาศเขตภัยพิบัติ/เขตให้ความช่วยเหลือ (กทม.)): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550']
  [MEASURED-on-graph] conflicting commanders over DC_GATE_BANGCHAN (เปิด/ปิด ปตร.บางชัน): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม']
  [MEASURED-on-graph] conflicting commanders over DC_GATE_PRAWET (เปิด/ปิด ปตร.ประเวศ (PWT.03/.04)): ['สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'กรมชลประทาน']
  [MEASURED-on-graph] conflicting commanders over DC_POND_DRAWDOWN (พร่องบึงหมู่บ้านก่อนฝน): ['สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'นิติบุคคลหมู่บ้านจัดสรร / คณะกรรมการหมู่บ้านสัมมากร']
  [MEASURED-on-graph] conflicting commanders over DC_POWER_CUT (ตัดไฟพื้นที่น้ำท่วม): ['ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.', 'กฟน. การไฟฟ้านครหลวง']
  [MEASURED-on-graph] conflicting commanders over DC_RUN_SPS (เดิน/ซ่อมปั๊ม ST.SPS.01-04): ['สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'นิติบุคคลหมู่บ้านจัดสรร / คณะกรรมการหมู่บ้านสัมมากร']
  [MEASURED-on-graph] contested OWNS over AS_SPS_POND (สถานีสูบบึง ST.SPS.02/.03/.04 (2+3+2 เครื่อง)): ['สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม', 'นิติบุคคลหมู่บ้านจัดสรร / คณะกรรมการหมู่บ้านสัมมากร']
  [MEASURED-on-graph] SHARES with no arbiter: กระทรวงการคลัง (ระเบียบเงินทดรองราชการ) <-> ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.

## Q3 กฎหมาย/อำนาจที่อาจมีปัญหา
  [MEASURED-on-graph] ศาลปกครอง -COMMANDS-> ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.: Institutional fragmentation / jurisdictional overlap (sources: docs/knowledge/bottlenecks.derived.json#rule_1_conflicting_commanders; docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md#ปัญหาที่-1)
  [MEASURED-on-graph] รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550 -COMMANDS-> ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.: Institutional fragmentation / jurisdictional overlap (sources: docs/knowledge/bottlenecks.derived.json#rule_1_conflicting_commanders; docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md#ปัญหาที่-1)
  [MEASURED-on-graph] ผู้ตรวจการแผ่นดิน -COMMANDS-> ผู้ว่าฯ กทม. = ผู้อำนวยการ กทม.: Institutional fragmentation / jurisdictional overlap (sources: docs/knowledge/bottlenecks.derived.json#rule_1_conflicting_commanders; docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md#ปัญหาที่-1)
  [RELAYED] นายกรัฐมนตรี (ควบ รมว.มหาดไทย ตามข่าว) -COMMANDS-> รมว.มหาดไทย = ผู้บัญชาการ ตาม พ.ร.บ.ป้องกันฯ 2550: Principal-agent information asymmetry / self-command paradox (sources: docs/knowledge/card_news_2026-09_nationtv_three_laws_overlap.md#(1)-ข้อ-2; docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md#ปัญหาที่-3)

## Q4 ประชาชนทำอะไรได้เอง
  [INSTINCT] อาจทำ "บัญชีทักษะ" ลูกบ้าน (ช่าง/วิศวกร/พยาบาล/คนมีเรือ/บ้าน 3 ชั้น) ไว้ก่อนฤดูฝน (cite: docs/knowledge/card_yucharoen_model_2554.md#(f)-1; always-applicable action for this village context; matches nearby asset class(es): ['pump_station'])
  [INSTINCT] อาจให้บทบาทนิติบุคคล/คณะกรรมการหมู่บ้านเป็น "สถาบัน" มีประชุมประจำ ไม่ผูกกับคนเดียว (cite: docs/knowledge/card_yucharoen_model_2554.md#(f)-2; always-applicable action for this village context)
  [INSTINCT] อาจตั้งกองทุนเล็กที่มีรายได้ประจำ กันไว้สำหรับช่วงน้ำท่วม (cite: docs/knowledge/card_yucharoen_model_2554.md#(f)-3; always-applicable action for this village context)
  [INSTINCT] อาจสอบถามนิติบุคคลหมู่บ้าน/สนน. เรื่องไฟฟ้าสำรอง/ไฟแยกของสถานีสูบใกล้บ้าน (หาดใหญ่ระบุว่าไฟฟ้าดับกระทบสถานีสูบทั้งระบบพร้อมกัน) (cite: docs/knowledge/card_hatyai_city_climate.md#(f)-3; matches nearby asset class(es): ['pump_station'])
  [INSTINCT] อาจติดตามค่าดิบจากป้าย/ฟีดของหน่วยงานที่ประกาศแล้วประกอบการตัดสินใจเอง แทนการอนุมานสาเหตุเอง (cite: docs/knowledge/card_hatyai_city_climate.md#(f)-2; always-applicable action for this village context)
  [INSTINCT] อาจทำ "แผนที่เดินดิน" รายซอย: บ้าน 3 ชั้นที่เป็นจุดพักพิง, ผู้ป่วยติดเตียง/ฟอกไต, เส้นทางน้ำเข้าจุดแรก (cite: docs/knowledge/card_hatyai_city_climate.md#(f)-4; always-applicable action for this village context)
  [INSTINCT] อาจติดตามระดับน้ำที่ประตู/สถานีวัดใกล้บ้านเทียบกับเกณฑ์เตือนภัยที่หน่วยงานเจ้าของ ประกาศไว้ (ไม่ตั้งเกณฑ์ตัวเลขขึ้นเอง) (cite: docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-1; matches nearby asset class(es): ['gauge'])
  [INSTINCT] อาจเตรียมกระสอบทรายและระวังอุปกรณ์ไฟฟ้า/ขนของมีค่าขึ้นที่สูงไว้ล่วงหน้า (มาตรการระดับ 1 ของรังสิตเมื่อสถานีสูบยังปกติแต่มีความเสี่ยง) (cite: docs/knowledge/card_rangsit_local_gov_flood_2561.md#(d)ระดับ-1; matches nearby asset class(es): ['pump_station'])
  [INSTINCT] อาจตั้งสายส่งต่อข่าวแบบ SMS/LINE ประธานชุมชน->เสียงตามสาย/กลุ่มไลน์ซอย เพราะคนนอน-ตื่นไม่พร้อมกัน (cite: docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-3; always-applicable action for this village context)
  [INSTINCT] อาจถามคำถามเรื่องปั๊ม/ประตูโดยตรงกับเจ้าของโครงสร้าง (สนน./กรมชลประทาน) เพราะ อปท./ชุมชนไม่มีอำนาจเหนือประตูระบายน้ำ (cite: docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-5; always-applicable action for this village context; matches nearby asset class(es): ['pump_station'])
```

หมายเหตุ: เรียกด้วย `--at sammakorn` (area_id แทน raw lat,lon) เพิ่มบรรทัดปัจจุบันจริงใน Q4 ที่ raw
lat,lon ไม่มี เพราะ `readout_log` ผูกกับ area_id ไม่ใช่พิกัดดิบ:

```
[MEASURED] current pump readout: 4/4 faulted @ 2026-09-27T07:21:59.882615+00:00
```

(สาเหตุยังไม่ทราบ -- ตรงกับ `docs/LESSONS_nodes_2026-09-27.md` §C.5 และ Q-DURBKK-6 ใน
`WATER_MANAGER_QUESTION_BANK.md`.)

## จุดทดสอบอื่น (ยืนยันว่าเครื่องมือ generic ไม่ hardcode Sammakorn)

- **`--at "gauge:thaiwater_waterlevel:C.13"` (ท้ายเขื่อนเจ้าพระยา, 15.16384,100.18792)**: หา
  asset_id นี้แทน asset dam node ตรง ๆ เพราะไม่มี `dam`-class asset ชื่อ "เขื่อนเจ้าพระยา" ในกราฟ
  (มีแต่ DAG governance node `AS_DAM_RID`/`AS_CHAO_UP`/`AS_CHAO` ที่ไม่มี lat/lon -- ดู "OPEN gaps"
  ด้านล่าง) -- gauge นี้เป็น asset จริงที่ใกล้ที่สุด (0.0 km, เพราะเลือกเป็นจุดศูนย์กลางเอง), owner
  `กรมชลประทาน ` -> `AG_RID` -> COMMANDS ขึ้นไปถึง `AG_REGCOM`/`AG_SNP`/`AG_KOPOR`/`AG_PM` ->
  `AUTHORIZES` จาก `LAW_IRRIGATION2485` (พ.ร.บ.การชลประทานหลวง 2485).
- **`--at "13.758235,100.676084"` (raw lat,lon, Sammakorn)**: ผลเหมือนกับ `--at sammakorn` ทุก
  ประการ ยกเว้น Q4 ไม่มี `pump_state` (เพราะไม่รู้ area_id).

## REFUSED discipline (ตรวจจริง)

```
$ python3 kb.py accountability --at "0,0"
REFUSED [OPEN]: no asset node within 3.0 km of (0.0,0.0)
```

Q2/Q3/Q4 ยัง "REFUSED" ต่อเมื่อ Q1 ไม่เจอ agency chain เลย (ดูโค้ด `q2_overlapping_authority`,
`q3_problematic_law`, `q4_self_help`) -- ไม่ invent คำตอบ.

## OPEN gaps ที่การรันนี้เผยออกมา

1. **Owner-string -> AG_ crosswalk เดิมไม่มีเลย** (known gap ใน `tools/kg/README.md`) -- แก้บางส่วน
   ด้วย `sources/owner_agency_crosswalk.yaml` ใหม่ (task นี้สร้าง): ตรวจ owner string ทั้ง 61
   ค่าที่ต่างกันใน `assets` table, map ได้ VERIFIED 9 แถว (RID/DWR/DDPM/TMD/MARINE/EGAT/ESTATE/HII/
   DDS + ตัวแปร trailing-space), OPEN 8 แถว (compound owner, malformed owner field, agency ที่ยัง
   ไม่มี AG_ node เช่นกรมประมง/กรมอุทยานฯ/มูลนิธิ), และ **เขต (Bangkok district office) ทุกเขตยกเว้น
   เขตสะพานสูง (AG_DIST_SS) ยังคง OPEN** เพราะ DAG ไม่มี AG_ node รายเขตครบ 50 เขต -- เห็นได้จริงใน
   ผลด้านบน: `pump_station:water_station:76` (เจ้าของ เขตบางกะปิ) หยุดที่ Q1 ด้วย `OPEN`.
2. **ปั๊ม ST.SPS.01-04 (Sammakorn) มีสอง "เจ้าของ" ที่ขัดกัน** -- `assets` table (จาก thaiwater
   pumphistory feed) บันทึก owner = `สำนักการระบายน้ำ กรุงเทพมหานคร` (สนน./AG_DDS) ทุกแถว แต่
   `docs/knowledge/water_system_dag.mmd` เอง (governance model) ให้ `AG_ESTATE` (นิติบุคคลหมู่บ้าน
   สัมมากร) เป็นผู้ `OWNS` `AS_SPS_POND` (ST.SPS.02/.03/.04) -- Q2 จับ contested-ownership นี้ได้จริง
   (`rule_2_ownership_gaps` -> `AS_SPS_POND` มีเจ้าของ 2 ราย). ตรงกับ `AGENTS.md` §8's เดิมที่เขียนว่า
   ST.SPS.01-04 "เป็นปั๊มของหมู่บ้านเอง ไม่ใช่ของ กทม." -- การรันนี้แสดงว่าแหล่งข้อมูลสองชุดในคลังเอง
   ยังไม่ตรงกัน (OPEN, ไม่ได้แก้ในนี้ ต้องยืนยันจริงกับ สนน./นิติบุคคลหมู่บ้าน).
3. **ไม่มี `dam`-class asset สำหรับ "เขื่อนเจ้าพระยา" เอง** -- มีแค่ gauge/gate ใกล้เขื่อนและ DAG
   governance node (`AS_DAM_RID` ฯลฯ) ที่ไม่มีพิกัด -- ทดสอบจุดต้นน้ำนี้ต้องใช้ gauge ข้างเคียงแทน
   asset ของเขื่อนเอง (ดูด้านบน) -- ช่องว่างข้อมูล ไม่ใช่บั๊กของเครื่องมือนี้.
4. **Q3 เป็น per-path readout ไม่ใช่ graph-wide** -- ถ้า path ที่เดินไม่บังเอิญผ่าน edge ที่มี
   `edge_problems.yaml` row เครื่องมือนี้จะไม่รายงานอะไรเลย (ไม่ใช่แปลว่าไม่มีปัญหาในกราฟทั้งหมด) --
   ดู `docs/knowledge/RESOURCE_AUTHORITY_AND_BOTTLENECKS.md` สำหรับภาพรวมทั้งกราฟ.
5. **`readout_log`'s `pump`-kind row ผูกกับ `area_id` (`sammakorn`/`ram53`) เท่านั้น** -- เรียกด้วย
   raw lat,lon (แม้จะเป็นพิกัดเดียวกับ Sammakorn เป๊ะ) จะไม่ได้ pump_state ใน Q4 เพราะเครื่องมือนี้ไม่
   เดารีบูรณาการ area_id จาก lat,lon เอง (ป้องกันการเดาผิดพื้นที่) -- ต้องเรียกด้วย `--at sammakorn`
   ให้ได้ readout ปัจจุบันจริง.

## Test

```
$ python3 -m pytest tests/test_accountability.py -q
13 passed in 0.32s
```

(รันเฉพาะไฟล์นี้ ตาม AGENTS.md "no repeated full-arc audits while iterating" -- ไม่ต้องรันเต็ม
`tests/` สำหรับ task นี้.)
