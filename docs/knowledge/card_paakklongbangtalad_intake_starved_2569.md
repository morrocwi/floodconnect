# Card — ปากคลองบางตลาด: INTAKE_STARVED pattern (field report, 28 ก.ย. 2569)

**Tag**: RELAYED-field-observation (โพสต์ Facebook, ทีมลงพื้นที่ภาคประชาชน, 28 ก.ย. 2569) ·
**scope**: next-version stub area (นอกเขตสัมมากร, ชายแดน กทม.เหนือ/นนทบุรี) — pattern เป็น
generic ใช้ที่อื่นได้

## 1. ข้อสังเกตภาคสนาม (RELAYED)

- ประตูน้ำปากคลองบางตลาด (รับน้ำจาก ถ.สามัคคี, ประชานิเวศน์ 3, ประชาชื่น): ชาวบ้านรายงานน้ำลดช้า
  มาก
- ที่ตัวประตู/สถานีสูบ: ระดับน้ำฝั่งในต่ำเกินกว่าจะให้ปั๊มใหญ่ 4 ตัวเดินได้ ("น้ำมาไม่ถึงจุดสูบน้ำ") —
  ใช้ปั๊มเคลื่อนที่ (mobile pump) ความจุน้อยกว่าแทน
- ที่สะพานถนนติวานนท์: คลองยังมีความจุ (capacity) แต่น้ำไม่มาถึง
- ตลอดแนวถนนติวานนท์ฝั่งตลาดชลประทาน: คลองมีผักตบชวา/ขยะอุดตัน
- คำถามเปิด: สถานีสูบย่อย/relay ("ทอยน้ำ") ตามแนวคลองบางตลาด — ติดขัดจุดไหนบ้าง ยังไม่ทราบ

## 2. Pattern: INTAKE_STARVED (เพิ่มใน `docs/FLOW_STALL_TYPOLOGY.md`)

ปั๊ม/จุดสูบ idle หรือ derated เพราะระดับน้ำฝั่งรับ (forebay) ต่ำเกินไป **ทั้งที่พื้นที่ต้นน้ำยังท่วมอยู่**
— คนละสาเหตุกับ RULE-STALL-01 (จุดยึดปลายทางนิ่ง) ลำดับตรวจสาเหตุ (ไม่ derive สูตร แค่ checklist):

1. สิ่งกีดขวางต้นน้ำ (ขยะ/ผักตบชวา)
2. สถานีสูบ relay ล้มเหลว
3. สถานะประตูน้ำ
4. ท่อ/culvert ตีบ

## 3. Typology (ดู `typology/nodes/paakklongbangtalad_2026-09-28.yaml`)

- `WATER.canal_bangtalad` (canal_reach), `WATER.bangtalad_tiwanon_bridge` (canal_reach,
  `condition: debris_hyacinth`, tag RELAYED-field)
- `ST.BANGTALAD.01` (pump, `stall_state: INTAKE_STARVED`, `stall_cause_confirmed:
  upstream_blockage`, `stall_cause_checklist_pending: [relay_pump_failure, gate_state,
  culvert_constriction]`)
- `ST.BANGTALAD.RELAY.01` (pump, OPEN -- ตำแหน่ง/สถานะ relay ยังไม่ทราบ)
- `SOI.BANGTALAD.SAMAKKEE` (soi_surface/civil -- ถ.สามัคคี/ประชานิเวศน์ 3)
- `RES.TOOL.MOBILE_PUMP` (generic) + `RES.PUMP.BANGTALAD_MOBILE_01` (instance, supplies ->
  ST.BANGTALAD.01)
- `CIV.FIELD_OBSERVER` (generic civil role node, reports_to -> AG_DDS, tag OPEN -- ไม่มี
  แหล่งยืนยันว่า DDS ได้รับรายงานนี้จริง)

## 4. เชื่อมกับของเดิม

- `ISSUE-INFRA-02` (structural_issues, ขยะอุดตันสถานีสูบ, Environman post) -- เคสนี้เป็น
  ตัวอย่างที่สองของปัญหาเดียวกัน คนละจุด
- structural_issues แถวใหม่ `ISSUE-INFRA-03`: ความจุปลายทาง (outlet) ใช้ไม่ได้จริงเมื่อทางน้ำ
  ต้นทางถูกกีดขวาง -- ตัวเลขความจุที่ประกาศไว้จึงสูงกว่าการระบายจริง (both-sides framing)
