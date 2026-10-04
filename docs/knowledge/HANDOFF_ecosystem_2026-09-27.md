# Handoff — ecosystem programme (water-management ecosystem for FloodConnect / this repo)

**วันที่เขียน**: 2026-09-27 · **branch**: `feat/redesign-v2` · **จุดประสงค์**: ให้ session ใด ๆ
ในอนาคต (AI หรือมนุษย์) อ่านไฟล์นี้แล้วต่องานได้ทันที ไม่ต้องรื้อบริบทใหม่ทั้งหมด.

---

## 1. คำพูดของ founder (verbatim — ห้ามถอดความ)

> "ทำให้นายกลายเป็นผู้บริหารน้ำในประเทศไทยได้และตอบคำถามที่สำคัญได้หมด ให้ git เราครบมากที่สุด"

> "เข้าไปอ่านพันธกิจแต่ละองค์กร และวางระบบ ecosystem การจัดการน้ำที่เราสามารถรู้ได้เลยว่าใครทำหน้าที่อะไร
> มีเครื่องมืออะไร มีกระบวนการทำงานอย่างไร ต้องหาที่ไหนบ้าง"

> "แผนที่ต่างๆ ระดับน้ำ โครงสร้างเมืองอื่นๆ ตามศาสตร์ด้านการจัดการน้ำระดับโลก นายทำให้ floodconnect
> ถูกวางระบบด้วยแบบนั้นเลย"

> "ให้คนที่ใช้ git นี้เข้าใจแนวทางแก้ปัญหาได้ทันที"

---

## 2. แผนงาน 6 stage

### Stage 1 — Question bank (เสร็จแล้ว รอบนี้)

ไฟล์: `docs/knowledge/WATER_MANAGER_QUESTION_BANK.md` — matrix 4 phase (ก่อนฤดู/ก่อนเหตุ 72
ชม./ระหว่างเหตุ/หลังเหตุ) × 4 level (ชาติ-ลุ่มน้ำ/กทม.-จังหวัด/เขต-อปท./หมู่บ้าน-ครัวเรือน) = 81
คำถาม พร้อมสถานะ (มีแล้ว/RELAYED/อนุมาน/ขาด) เทียบกับสิ่งที่คลังนี้มีอยู่จริงในไฟล์ต่าง ๆ
(`sources/registry.yaml`, `docs/CAPACITY.md`, `docs/DATA_SYSTEM.md`,
`docs/LESSONS_nodes_2026-09-27.md`, `docs/knowledge/README.md`, `site/dist/data.json`,
`data/observations.sqlite`) + top-15 รายการที่ขาดเรียงตามจำนวนคำถามที่ปลดล็อก.

### Stage 2 — Power/resource map + 4-dimension synthesis

**ยังไม่เริ่ม.** งาน: สังเคราะห์จาก 5 เอกสารใน `docs/knowledge/` (ดู §3 ด้านล่าง) เป็นแผนที่
"ใครมีอำนาจ/เครื่องมือ/กระบวนการ" 4 มิติต่อหน่วยงาน: (1) อำนาจตามกฎหมาย (2) เครื่องมือ/ระบบที่ถือ
(3) กระบวนการทำงานจริง (4) จุดต่อกับหน่วยงานอื่น (interface/handoff point). Output ที่แนะนำ:
`docs/knowledge/POWER_RESOURCE_MAP.md` — ทุกแถวต้องมี citation กลับไปยัง card/แหล่งต้นทาง
ห้ามเดาอำนาจ/เครื่องมือที่ไม่มีเอกสารรองรับ (แท็ก OPEN ถ้าไม่แน่ใจ).

### Stage 3 — Crawl พันธกิจ/อำนาจหน้าที่ทางการของแต่ละหน่วยงาน

**ยังไม่เริ่ม.** งาน: เข้าเว็บทางการของแต่ละหน่วยงาน (รายชื่อใน §4) อ่านหน้า "พันธกิจ/หน้าที่
ความรับผิดชอบ/โครงสร้างองค์กร" แล้วเติมแถว VERIFIED (อ้าง URL/ชื่อหน้าเว็บ + วันที่เข้าถึง) ลงใน
power/resource map จาก stage 2 พร้อมระบุ "ควรหาข้อมูลเพิ่มเติมได้ที่ไหน" (feed/endpoint/หน้า
รายงาน) ต่อหน่วยงาน. **นี่คือ WebFetch/WebSearch งานจริง — ห้าม fabricate URL ที่ไม่เคยเห็น**
ถ้าหาไม่เจอให้เขียน "ต้องค้น" ตรง ๆ

### Stage 4 — ตอบคำถามจากคลัง + list สิ่งที่ยังตอบไม่ได้

**ยังไม่เริ่ม.** งาน: ไล่ตาราง `WATER_MANAGER_QUESTION_BANK.md` ทุกแถว ใช้ผลจาก stage 2-3 อัปเดต
สถานะคำถามที่เดิม "ขาด" ให้กลายเป็น "มีแล้ว/RELAYED" เมื่อพบแหล่งจริง แล้วสรุปรายการที่ยัง
"ตอบไม่ได้" (unanswerable) เป็นเอกสารแยก หรืออัปเดตคอลัมน์สถานะในไฟล์เดิมโดยตรง (ต้องรักษา
format matrix เดิม).

### Stage 5 — จัดวางสถาปัตยกรรม FloodConnect ให้สอดคล้องกรอบสากล

**ยังไม่เริ่ม. เริ่มได้ก็ต่อเมื่อ docs/knowledge ถูก commit แล้ว (ดู §6 sequencing).**
คำพูด founder ตรง ๆ: "แผนที่ต่างๆ ระดับน้ำ โครงสร้างเมืองอื่นๆ ตามศาสตร์ด้านการจัดการน้ำระดับโลก
นายทำให้ floodconnect ถูกวางระบบด้วยแบบนั้นเลย"

งาน: เขียน `docs/ARCHITECTURE_world_frameworks.md` เทียบ FloodConnect กับกรอบการจัดการความเสี่ยง
น้ำท่วมระดับสากล (ทุก claim เรื่องกรอบต้องแท็ก **RELAYED** — เป็นความรู้ที่ relay มาจากวรรณกรรม
สากล ไม่ใช่ของทีมนี้เอง):
- **Source–Pathway–Receptor–Consequence (SPRC)** — กรอบวิเคราะห์ห่วงโซ่ความเสี่ยงมาตรฐานของ
  UK/EU flood risk management
- **EU Floods Directive (2007/60/EC)** — โครงสร้าง hazard/risk map layers: DEM
  (digital elevation model), water network + control assets (คลอง/ประตู/ปั๊ม), hazard
  by scenario/return-period level, risk = hazard × exposure × vulnerability
- **WMO/UNDRR 4-element people-centred early-warning system** — (1) risk knowledge
  (2) detection/monitoring/forecasting (3) warning dissemination/communication
  (4) preparedness/response capability
- **Dutch multi-layer safety (meerlaagsveiligheid)** — layer 1 prevention (defence
  structures), layer 2 spatial planning (ลดความเสียหายผ่านผังเมือง), layer 3
  disaster management (เตรียมพร้อม/อพยพ/กู้ภัย)

Output ต้องมี **coverage matrix**: กรอบแต่ละอัน × องค์ประกอบของกรอบ × "FloodConnect มีอะไรแล้ว"
vs "ยังขาดอะไร" (อ้างอิงไฟล์จริงในคลังนี้ต่อองค์ประกอบ เช่น DEM → `rtsd_2010_ground_level_map`,
warning dissemination → ยังไม่มีระบบแจ้งเตือนอัตโนมัติ). ห้ามอ้างว่า FloodConnect "ตรงตามกรอบ X
แล้ว" ถ้าไม่มีองค์ประกอบครบ — รายงานช่องว่างตรง ๆ.

### Stage 6 — START_HERE.md (จุดเข้าใจแนวทางแก้ปัญหาทันที)

**ยังไม่เริ่ม. เริ่มได้ก็ต่อเมื่อ docs/knowledge ถูก commit แล้ว (ดู §6 sequencing).**
คำพูด founder ตรง ๆ: "ให้คนที่ใช้ git นี้เข้าใจแนวทางแก้ปัญหาได้ทันที"

งาน: เขียน `START_HERE.md` ที่ root ของ repo (ไม่ใช่ใน `docs/knowledge/`) โครงสร้าง: ปัญหา (problem)
→ แนวทาง (approach) → ไฟล์ไหนตอบคำถามอะไร (ตารางชี้ทาง: คำถามประเภทไหน → เปิดไฟล์ไหน เช่น "ขีด
ความสามารถระบายน้ำ?" → `docs/CAPACITY.md`, "แหล่งข้อมูลมีอะไรบ้าง?" → `sources/registry.yaml`,
"คำถามผู้บริหารน้ำต้องตอบอะไรบ้าง?" → `docs/knowledge/WATER_MANAGER_QUESTION_BANK.md") →
"ทำอะไรได้ใน 5 นาที" (เช่น รัน `python3 readout.py --centre 13.758235 100.676084` เพื่อดู
สถานะสด). ต้องอัปเดต `README.md` ที่ root ให้ชี้ (point) มาที่ `START_HERE.md` ด้วย (เพิ่มลิงก์
ต้น ๆ ของไฟล์ ไม่ใช่แทนที่ README เดิม).

---

## 3. สิ่งที่มีอยู่แล้วตอนนี้ (2026-09-27)

**`docs/knowledge/` (ก่อน worker รอบนี้เขียนเพิ่ม):**
- `README.md` — ดัชนี 5 ระดับภูมิศาสตร์/สถาบัน (ชาติ → ลุ่มน้ำ → กทม. → เขต → หมู่บ้าน), ระดับ 1-2
  (ชาติ/ลุ่มน้ำ) ระบุ "ยังไม่มีเอกสาร" ทุกหน่วยงาน (สทนช./RID/TMD/GISTDA)
- `bma_canal_scada_rmutp2012.md` — เอกสารวิชาการ 2012 สถาปัตยกรรม SCADA คลอง กทม. (RELAYED)
- `card_participatory_flood_mgmt.md` — บทความวิชาการ 2564 การจัดการแบบมีส่วนร่วม (RELAYED)
- `card_yucharoen_model_2554.md` — กรณีศึกษาชุมชนอยู่เจริญ ปี 2554 (RELAYED)
- (ไฟล์รอบนี้) `WATER_MANAGER_QUESTION_BANK.md`, `HANDOFF_ecosystem_2026-09-27.md` (ไฟล์นี้เอง)

**หมายเหตุ**: มีอีก 2 worker กำลังเขียนไฟล์อื่นใน `docs/knowledge/` พร้อมกันในรอบนี้ (extraction
ของเอกสาร/คลังความรู้เพิ่มเติม) — session ในอนาคตควร `ls docs/knowledge/` ใหม่ก่อนอ้างว่ารายการ
ด้านบนคือรายการล่าสุด.

**เอกสารอื่นที่เกี่ยวข้อง:**
- `docs/LESSONS_nodes_2026-09-27.md` — ถอดบทเรียนโหนดข้อมูล/กายภาพ/สัญญาณนำ จากเหตุการณ์จริง
  26-27 ก.ย. 2569 (internal, ยังไม่เผยแพร่สาธารณะ -- ไม่ได้รวมอยู่ใน public tree นี้)
- `docs/CAPACITY.md` — ขีดความสามารถระบายน้ำ กทม. vs ฝนจริง (58.7 มม./ชม. VERIFIED, ตัวเลข
  โครงสร้างพื้นฐานขัดแย้งกันเองหลายจุด)
- `docs/DATA_SYSTEM.md` — pipeline: registry.yaml → collect.py → raw/live/ → store.py →
  observations.sqlite → readout.py → output/
- `sources/registry.yaml` — `sources:` (12 live/reference sources ที่ collect.py ดึงจริง) +
  `reference_documents:` (เอกสารวิชาการ static, ต้องมี card คู่กันใน docs/knowledge/)
- `data/observations.sqlite` — ตาราง `observations, documents, method_evaluation,
  contradictions, readout_log`
- `site/dist/data.json` — คีย์: `generated_at_bkk, epistemic_note, default_area, forecast,
  forecast_caveat_th, all_sources, bangkok_east_water_balance, bma_briefing,
  capacity_records, drain_timeline, sammakorn_rough, forecast_7day_compare, canal_graph,
  burden_ledger, areas`

---

## 4. รายชื่อหน่วยงานสำหรับ stage 3 (verbatim จากคำสั่ง)

สทนช., กรมชลประทาน, กรมทรัพยากรน้ำ, กรมอุตุนิยมวิทยา, สสน./thaiwater, GISTDA, กฟผ., ปภ.,
กระทรวงมหาดไทย, กทม. สำนักการระบายน้ำ, สำนักงานเขตสะพานสูง/บางกะปิ, กฟน., กรมทางหลวง/กทพ.,
กรมเจ้าท่า, กรมโยธาธิการและผังเมือง, สภาพัฒน์/สำนักงบประมาณ (งบน้ำ),
คณะกรรมการลุ่มน้ำเจ้าพระยา/บางปะกง

---

## 5. กติกาที่บังคับใช้ (rules in force)

- **แท็ก epistemic**: `VERIFIED` (ตรวจสอบเองแล้ว) / `MEASURED` (วัด/อ่านจากไฟล์ข้อมูลจริงเอง) /
  `RELAYED` (รับช่วงจากแหล่งอื่น ยังไม่ตรวจสอบเอง) / `INSTINCT` (การประเมิน/ความเห็น) / `OPEN`
  (ยังไม่มีคำตอบ/ขัดแย้งกัน) — ทุกบรรทัดที่เป็น claim ต้องติดแท็ก
- **ห้ามใส่ชื่อบุคคล** ในไฟล์ที่ tracked (ดู card สองใบที่มีอยู่แล้ว: ระบุ "ไม่ระบุชื่อบุคคลตามกฎ
  ของคลัง")
- **ห้ามใส่ชื่อ AI/vendor** เป็นผู้แต่ง/co-author ในไฟล์ใด ๆ ที่จะออกจากเครื่อง
- **ห้ามมี local filesystem path ของเครื่องผู้ใช้** ในไฟล์ที่ tracked โดย git
- **One committing worker per worktree** — worker หลายตัวเขียนไฟล์คนละไฟล์ใน `docs/knowledge/`
  ได้พร้อมกัน แต่ **ห้าม `git add/commit/push` จาก worker ที่ไม่ใช่เจ้าของ worktree/commit นั้น**
- **Toledo-first**: ห้ามเขียน/อ้างสมการใด ๆ ที่ไม่ผ่านการลงทะเบียนก่อน — ดูตัวอย่างจริงในคลังนี้:
  สมการสมดุลน้ำ PROP-FLOOD-03 ยังเป็น "proposal" เท่านั้น คำนวณ REFUSED ที่ระดับหมู่บ้านจนกว่าจะมี
  อินพุตครบ (`docs/CAPACITY.md` §7)
- **Wording law สำหรับหน้าเว็บสาธารณะ**: `docs/DATA_SYSTEM.md` ระบุชัดว่านี่คือ "ระบบเก็บ+อ่าน
  ข้อมูล" ไม่ใช่ "ระบบพยากรณ์น้ำท่วม" — ไม่มีสูตร/คะแนนความเสี่ยงในโค้ด ทุกตัวเลขที่แสดงต้อง relay/
  วัดมาตรงจากหน่วยงานต้นทางพร้อม trust tier

---

## 6. สิ่งที่ห้ามทำ (what NOT to do)

- **ห้าม prune ข้อมูล** — สถานีที่ข้อมูลค้าง/ขัดแย้งกัน (เช่น จำนวนสถานีสูบ 195 vs 200) เก็บไว้ทั้งคู่
  พร้อมแท็ก OPEN/RELAYED ห้ามตัดทิ้งเพื่อความสวยงาม
- **ห้าม public push ของ `docs/knowledge/` โดยไม่ผ่าน leak scan** — ต้องรัน adversarial review/
  leak scan (ค้นหาชื่อ vendor AI ใด ๆ, absolute filesystem path ของเครื่องผู้ใช้, ชื่อผู้ใช้ระบบ,
  และตัว repo directory name เอง เป็นต้น) ก่อนทุกครั้งที่จะเผยแพร่สู่ภายนอก
- **ห้ามสร้างสมการใหม่** โดยไม่ผ่าน Toledo lookup → Genesis compatibility → reuse/derive → mark
  "NEW DERIVATION / PROPOSAL" ตามลำดับที่กำหนดไว้ในกฎ equation discipline ระดับ workspace
- **Sequencing**: stage 5-6 **เริ่มได้ก็ต่อเมื่อ** worker สกัดเอกสาร 2 ตัวที่กำลังทำงานคู่ขนานใน
  `docs/knowledge/` เสร็จแล้ว **และ** ไฟล์ทั้งหมดใน `docs/knowledge/` ถูก commit แล้ว (ผ่าน worker
  เจ้าของ worktree เท่านั้น — ไม่ใช่ session นี้ ซึ่งไม่ได้รับอนุญาตให้ commit)

---

## 7. Concrete next step ต่อ stage

| Stage | Next concrete step | ใครทำ |
|---|---|---|
| 2 | อ่าน 5 เอกสารใน `docs/knowledge/` (2 card ที่มีแล้ว + เอกสารที่ 2 กระบวนการคู่ขนานกำลังเขียน) → ร่าง `docs/knowledge/POWER_RESOURCE_MAP.md` 4 มิติต่อหน่วยงาน | session ถัดไป (ใน worktree แยก) |
| 3 | ใช้ WebFetch/WebSearch เข้าเว็บทางการของ 17 หน่วยงานใน §4 → เติมแถว VERIFIED ในแผนที่จาก stage 2 | session ถัดไป (ต้องมี worktree ของตัวเอง, ห้าม commit ทับ worker อื่น) |
| 4 | ไล่ทุกแถวใน `WATER_MANAGER_QUESTION_BANK.md` เทียบผลจาก stage 2-3 → อัปเดตสถานะ + สรุป unanswerable | session ถัดไป |
| 5 | เขียน `docs/ARCHITECTURE_world_frameworks.md` (SPRC, EU Floods Directive, WMO/UNDRR 4-element, Dutch multi-layer safety) + coverage matrix — **รอ docs/knowledge commit เสร็จก่อน** | session ถัดไป (หลัง sequencing gate ผ่าน) |
| 6 | เขียน `START_HERE.md` ที่ root + แก้ `README.md` ให้ชี้มาที่ไฟล์นี้ — **รอ docs/knowledge commit เสร็จก่อน** | session ถัดไป (หลัง sequencing gate ผ่าน) |

---

## 8. สรุปสิ่งที่ session นี้ทำ (2026-09-27)

- เขียน `docs/knowledge/WATER_MANAGER_QUESTION_BANK.md` (81 คำถาม, matrix 4×4, top-15 missing
  items) — รวมกลุ่มคำถาม "แผนที่/ระดับพื้นดิน/hazard-risk" ที่เพิ่มเข้ามาระหว่างทำงาน
- เขียน `docs/knowledge/HANDOFF_ecosystem_2026-09-27.md` (ไฟล์นี้)
- **ไม่ได้แตะไฟล์อื่นใดใน `docs/knowledge/`** (worker อื่นเป็นเจ้าของ) และ **ไม่ได้รัน git
  add/commit/push/stash/checkout ใด ๆ** ตามขอบเขตที่ได้รับมอบหมาย
- Stage 5-6 (ARCHITECTURE_world_frameworks.md, START_HERE.md) **ยังไม่ได้เขียน** — บันทึกไว้เป็น
  แผนในไฟล์นี้เท่านั้น ตาม sequencing gate ใน §6
