# ชั้นประสบการณ์มนุษย์ (`docs/knowledge/experience/`)

**โจทย์ต้นทาง (founder, คำต่อคำ)**: "สกัดประสบการณ์มนุษย์เข้าไปในระบบต่างๆ ทั้งด้าน กรอบเลนส์การเมือง
ของประเทศไทย ปรัชญา เชิงโครงสร้าง ระบบ จริยธรรม เพื่อให้เราประเมินปัญหาได้ในอนาคต"

ชั้นนี้เก็บ **เรื่องเล่า/ประสบการณ์ที่คนพาสต์มาให้** (โพสต์โซเชียล, คอมเมนต์, บทสัมภาษณ์, ข้อความวาง)
แล้วอ่านผ่าน **5 เลนส์คงที่** (การเมือง/ปรัชญา/โครงสร้าง/ระบบ/จริยธรรม) เพื่อให้ทีมนี้ประเมินสถานการณ์
คล้ายกันในอนาคตได้เร็วขึ้น — **ไม่ใช่** ฐานข้อมูลข้อเท็จจริงที่ตรวจสอบแล้ว ทุกบัตร = ประสบการณ์ที่ถูก
"รับช่วง" มา ไม่ใช่สิ่งที่ทีมนี้ยืนยันเอง

## วินัย (บังคับ)

1. **ทุกบัตรติด `tag: RELAYED-EXPERIENCE` เสมอ** — ไม่ใช่ VERIFIED/MEASURED ไม่ว่าเนื้อหาจะฟังดูน่าเชื่อแค่ไหน
2. **ห้ามระบุชื่อบุคคล/handle/ร่องรอยที่ระบุตัวตนได้** — ถอดความ (paraphrase) เป็นภาษาที่เป็นกลาง; บุคคลสาธารณะ
   อ้างเฉพาะ **บทบาท** (เช่น "ภูมิสถาปนิกผู้ได้รางวัลภูมิอากาศ UN") ไม่ใช่ชื่อ
3. **ไม่เขียนเรื่องเล่าเป็นข้อเท็จจริงที่ยืนยันแล้ว** — ใช้คำเช่น "ผู้เล่าระบุว่า...", "ตามที่เล่ามา..." เสมอ
4. **ห้ามกล่าวหาองค์กรที่ระบุชื่อเกินกว่าที่เรื่องเล่าเองพูด** (quote-faithful) — ไม่เติมข้อกล่าวหาของทีมนี้เอง
5. เชื่อมโยงกับกราฟ/เอกสารจริงในคลังเสมอที่ทำได้ (`node_ids`, `dag_gaps`, ลิงก์ท้ายบัตร) — ถ้าจับคู่ไม่ได้ ให้เว้นว่าง (`[]`)
   ไม่ใช่เดา

## Front-matter schema (YAML, ทุกบัตรต้องมีครบ)

```yaml
id: exp_YYYY-MM-DD_slug          # ไม่ซ้ำ, ใช้เป็น primary key
date_event: YYYY-MM-DD            # วันที่เหตุการณ์เกิดขึ้นจริง (ตามที่ผู้เล่าระบุ)
date_collected: 2026-09-27        # วันที่ทีมนี้รับเรื่องเข้าคลัง
source_type: social_post | comment | interview | paste
role: ผู้อยู่อาศัย | ผู้เดินทาง | นักวิชาการ | สื่อ | ผู้นำชุมชน
place: <สถานที่ ข้อความอิสระ>
node_ids: [<asset_id หรือ canal_graph/DAG node id ถ้าจับคู่ได้, ไม่งั้น []>]
tag: RELAYED-EXPERIENCE            # ค่าคงที่เสมอ
measurables:
  - {what: <สิ่งที่วัด>, value: <ตัวเลข/ข้อความ>, unit: <หน่วย>}
lenses:
  politics: <1-3 ประโยคภาษาไทย>
  philosophy: <1-3 ประโยคภาษาไทย>
  structure: <1-3 ประโยคภาษาไทย>
  system: <1-3 ประโยคภาษาไทย>
  ethics: <1-3 ประโยคภาษาไทย>
dag_gaps: [G1|G2|G3|G4, ...]        # อ้างอิง docs/knowledge/WATER_SYSTEM_DAG.md ถ้าเข้าเกณฑ์
ews_element: 1 | 2 | 3 | 4           # ตาม WMO/UNDRR People-Centred EWS (ดู docs/ARCHITECTURE_world_frameworks.md §(c))
                                     # 1=risk knowledge 2=monitoring/forecasting 3=warning dissemination 4=response capability
sprc: S | P | R | C                 # Source/Pathway/Receptor/Consequence (ดู docs/ARCHITECTURE_world_frameworks.md §(a))
proposed_indicators: [<ข้อเสนอ indicator ที่วัดได้จริง>]
future_signal: "ถ้าเห็นแบบนี้อีก แปลว่า…"   # 1 ประโยค
```

## ส่วนเนื้อหา (body, หลัง front-matter)

1. **เรื่องเล่าแบบถอดความ (anonymised)** — ภาษาไทย ไม่มีชื่อ/handle/รายละเอียดที่ระบุตัวตนได้
2. **5 เลนส์แบบขยายความ** (การเมือง/ปรัชญา/โครงสร้าง/ระบบ/จริยธรรม) — ยาวกว่าใน front-matter ได้
3. **ลิงก์เอกสารที่คลังนี้มีจริงที่ยืนยัน (corroborating)** — path จริงในคลัง เท่านั้น (อ่านแล้วก่อนอ้าง)

## เอกสารที่อ่านก่อนเขียนบัตรชุดนี้ (อ้างอิงจริง)

- `docs/knowledge/THAI_WATER_GOVERNANCE_MAP.md` §0 (ปัญหาจริง 10 ข้อ, tag RELAYED/INSTINCT)
- `docs/knowledge/OVERLAP_REGISTER.md` (ตารางความซ้ำซ้อนอำนาจ a1–a6+, รหัสแหล่ง [SCADA][RS][YC] ฯลฯ)
- `docs/knowledge/WATER_SYSTEM_DAG.md` §"จุดขาดของกราฟ" (G1–G4) + "10 ช่องว่างที่ใหญ่ที่สุด"
- `docs/ARCHITECTURE_world_frameworks.md` (SPRC, EU map stack, WMO/UNDRR EWS 4 องค์ประกอบ)
- `docs/LESSONS_nodes_2026-09-27.md` (โหนดข้อมูล/โหนดกายภาพ, บทเรียน "เซนเซอร์หนึ่งตัวมีค่ากว่าแหล่งทางการ 10 แหล่ง")
- `docs/METHOD_social_listening.md` + `raw/community/social_listening_paste_sammakorn_2026-09-26.md` (บัตร f)
- `burden_ledger.py` (PROP-FLOOD-05a/05b, proposal ยังไม่ merge เข้า Toledo — ห้ามอ้างเป็นทฤษฎีจนกว่าจะขึ้นทะเบียน)

## เก็บเข้าระบบ

```
python3 experience_log.py add docs/knowledge/experience/<card>.md   # parse front-matter -> ตาราง experience_log
python3 experience_log.py list                                       # แสดงทุกแถว
python3 experience_log.py find "<คำค้น>"                             # ค้นข้ามฟิลด์ข้อความ
```

ตาราง `experience_log` ใน `store.py` เป็น **append-only ระดับตาราง** (schema ใหม่, ไม่แตะฟังก์ชันเดิม) —
แต่ต่อแถวใช้ `INSERT OR REPLACE` คีย์ที่ `id` (จาก front-matter) เพื่อให้แก้บัตรแล้วรัน `add` ซ้ำได้โดยไม่พอกพูน
แถวซ้ำ ไม่ใช่การ "เขียนทับประวัติ" ในความหมายของผู้สังเกตการณ์คนละคน — เป็นบัตรเดียวกัน ฉบับล่าสุด

## Gate ก่อน commit (ทีม workflow เป็นผู้ commit)

ก่อน commit ต้องรัน leak-pattern scanner ของ repo ข้ามไฟล์ใน `docs/knowledge/experience/`
และ `experience_log.py` — ต้องได้ 0 finding (ตรวจ local username, local absolute path,
ชื่อ AI/vendor, และชื่อ repo นี้เอง) และตรวจแยกด้วยตาว่าไม่มีชื่อบุคคล/handle ใดๆ ที่ได้รับมา
(ไม่ได้รับชื่อมาตั้งแต่ต้น ดังนั้นต้องเป็น 0 เสมอ)
