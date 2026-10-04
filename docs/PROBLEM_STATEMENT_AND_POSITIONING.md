# โจทย์หลักของ FloodConnect ที่สกัด/สรุปให้แข็งและครบขึ้น (2026-09-27)

**คำสั่งฟาวน์เดอร์ (คำต่อคำ)**: "สกัดออกมาทำให้โจทย์เราแข็งและครบขึ้น ส่วนที่ยังอ่อนก็ค่อยขาย
ทำโจทย์หลักก่อน"

**สถานะไฟล์นี้**: เอกสารสังเคราะห์จากไฟล์ที่มีอยู่แล้วในคลังนี้ (`AGENTS.md`, `README.md`,
`docs/DATA_SYSTEM.md`, `docs/knowledge/CO_FORECAST_PROTOCOL.md`,
`docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md`, `docs/LAYER0_IN_OUT_CAPACITY.md`,
`docs/FLOW_STALL_TYPOLOGY.md`, `docs/ACCOUNTABILITY_QUERY.md`, `docs/FLOODCONNECT_TOPOLOGY.md`,
`docs/knowledge/GLOBAL_FREE_HAZARD_APIS.md`, `docs/knowledge/FORECAST_7DAY_SOURCES.md`) +
การ์ด third-party ที่เพิ่งเขียนคู่กัน
(`docs/knowledge/card_thirdparty_positioning_analysis_2026-09-27.md`) — **ไม่ใช่ proposal
สมการใหม่ ไม่แก้ไฟล์อื่นใดเลย** เป็น worker แยกเขียนไฟล์นี้ไฟล์เดียว ไม่ commit เอง.

---

## (a) คำถามหลักหนึ่งบรรทัด (founder-approved lens)

> **"เมื่อรู้ทั้งหมดนี้แล้ว คนธรรมดา (resident) จะจัดตัวเองอย่างไร เพื่อเดินจาก node ที่ไม่
> ปลอดภัยไป node ที่ปลอดภัยกว่า — จากข้อมูลทั้งหมดที่เรามี, ด้วยตัวเอง, โดยไม่สร้างความมั่นใจ
> ปลอม (false confidence)"**

**Tag**: `INSTINCT` (การเลือกกรอบคำถามนี้เป็นการตัดสินใจเชิงบรรณาธิการของทีมนี้ อ้างอิงจาก
การวิเคราะห์ของบุคคลที่สามที่ founder ส่งมา — ดูการ์ด `card_thirdparty_positioning_
analysis_2026-09-27.md` — และตรงกับสิ่งที่คลังนี้ทำอยู่แล้วจริงในหลายไฟล์: `REFUSED` เป็น
first-class outcome (`AGENTS.md` §2), `UNKNOWN`≠`SAFE` (`FLOW_STALL_TYPOLOGY.md` §3), "อย่า
ตัดสินแทนว่าใครถูก" (`DATA_SYSTEM.md`)).

คำถามนี้**ไม่ใช่**"น้ำจะท่วมเมื่อไหร่/สูงเท่าไหร่" (นั่นคือโจทย์ของ hydraulic forecasting ที่
ทีมนี้**ไม่ทำเอง** — ดู (c)) — คำถามของเราคือ **คนที่ยืนอยู่ตรงนี้ ตอนนี้ ทำอะไรได้บ้าง** จาก
ข้อมูลที่มีจริง แม้ข้อมูลจะไม่ครบ.

---

## (b) สิ่งที่เราเป็นเจ้าของ (layer): "Local Evidence + Human Action Infrastructure"

**ชื่อ layer (INSTINCT, รับมาจากการวิเคราะห์ภายนอกที่ founder ส่งมา, ตรงกับสถาปัตยกรรมจริงของ
คลังนี้)**: เราไม่ใช่ผลิตภัณฑ์พยากรณ์น้ำท่วมเชิงพาณิชย์ — เราเป็น**ชั้นล่างสุด**ที่ประกอบ
"หลักฐานท้องถิ่นที่ตรวจสอบได้" (local evidence) เข้ากับ "โครงสร้างที่ทำให้คนลงมือทำได้จริง"
(human action infrastructure). รายการด้านล่างคือส่วนประกอบจริงที่มีอยู่แล้วในคลังนี้ ต่อชิ้น
บอกสถานะ (built / partial / OPEN) + evidence tag ที่มันผลิตออกมา:

| ส่วนประกอบ | ไฟล์/โมดูลจริง | สถานะ | evidence tag ที่ผลิต |
|---|---|---|---|
| Telemetry ทางการหลายหน่วยงาน (คลอง/ปั๊ม/ฝน/น้ำขึ้นลง/เขื่อน/GloFAS) | `sources/registry.yaml` + `collect.py` (28 sources) | **built** | `official_telemetry`/`official_report`/`official_shared_inference`/`third_party` (4 trust tier, `DATA_SYSTEM.md`) |
| ความขัดแย้งข้ามแหล่งต้องปรากฏ (never merge/resolve เงียบ) | `tools/reconcile.py`, ตาราง `contradictions` | **built** | `contradictions` row, ไม่เคยเขียนทับ |
| น้ำเข้า/น้ำออก/รับมือได้ (3 ตัวเลขต่อหน่วย) | `tools/layer0/in_out_capacity.py`, `docs/LAYER0_IN_OUT_CAPACITY.md` | **partial** (ยัง**ไม่ผูก**เข้า `build_data.py`/`build_page.py` — worker อื่นตัดสินใจ wiring) | `MEASURED`/`RELAYED`/`REFUSED` เฉพาะตัวเลขที่ขาด |
| PROP-FLOOD-01..07 เป็นข้อตกลงที่ประกาศไว้ล่วงหน้า (ไม่ใช่สมการลอย ๆ) | `toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md` + `CO_FORECAST_PROTOCOL.md` §2c | **built** (01/03/04/05a/05b live ใน `build_data.py`; 02 อ้างถึงแต่ยังไม่ implement; 07 = ตัวจัดชั้น F1-F6 ยังเป็น candidate ไม่ขึ้นทะเบียน) | `Th_coqc`(v4 monotonicity)/`finite_diagnostic`/`Dr` ตาม tier ladder |
| Accountability query (ใครรับผิดชอบ/อำนาจซ้อน/กฎหมายมีปัญหา/ประชาชนทำอะไรได้เอง) | `tools/kg/accountability.py`, `docs/ACCOUNTABILITY_QUERY.md` | **built** (Q1-Q4 ทำงานจริง, 13 tests ผ่าน) | `VERIFIED`(graph query)/`MEASURED-on-graph`/`RELAYED`/`RELAYED-GENERAL`/`OPEN` ผสมกันต่อบรรทัด |
| Topology/typology ของการไหล-หยุดไหล (landscape + inference ladder) | `tools/flowmap/flow_stall.py`, `docs/FLOW_STALL_TYPOLOGY.md` | **partial** (prototype รันจริงกับ Sammakorn, ยังไม่ wire เข้า page จริง) | evidence-strength ladder `VERIFIED_LIVE`>`VERIFIED_STALE`>`RELAYED`>`COMMUNITY`>`INSTINCT`; inference rung `observed`/`strong_inference`/`weak_inference`/`refuse` |
| Community DAG (Self→Buddy→Zone→Safe Network) | `community_dag.py` (บน `origin/main`, ยังไม่ merge เข้า `feat/redesign-v2` — ดู `REVIEW_COMMUNITY_DAG_ORIGIN_MAIN.md`) | **partial** (โค้ด+test 7/7 ผ่านจริงบน origin/main, แต่**ยังไม่มีคนจริงใช้งาน**, ยังขาด epistemic tag ในเอกสารตามที่ตรวจพบในรอบ review) | สถานะปฏิบัติการ `SAFE`/`DEGRADED`/`UNSAFE`/`UNKNOWN` + `OPEN`/`ASSISTED`/`BLOCKED`/`UNKNOWN` (คนละ namespace จาก epistemic tag — ต้องไม่ปนกัน) |
| ปัญหาเชิงสถาบันของสังคมไทยที่สกัดจากกราฟ (9 ปัญหา, ≥2 แหล่งอิสระ) | `docs/knowledge/THAI_SOCIETY_PROBLEMS_ACADEMIC.md` | **built** | `MEASURED-on-graph` (คำนวณจริงจาก `bottlenecks.derived.json`) + `RELAYED` หลายไฟล์ต่อปัญหา |
| Knowledge graph รวม (แม่น้ำ→คลอง→ท่อระบาย→เขต→สินทรัพย์) | `output/thailand_water_kg.graphml`, `docs/FLOODCONNECT_TOPOLOGY.md` | **built** (build 3) แต่**ครอบคลุมไม่สม่ำเสมอ** (เขตสะพานสูงมีท่อในกราฟแค่ 4 แถว) | `MEASURED` (จากกราฟที่ build จริง) + `RELAYED` เฉพาะจุดอ้างอิงเอกสารอื่น |
| Backflow/canal-connection สำหรับหน่วยที่ต่อคลอง (ไม่ใช่แค่ปั๊ม) | `compute_backflow_state()` ใน `tools/layer0/in_out_capacity.py` §2 | **built** (state-based: active/not_active/unknown/likely, ไม่ใช่ตัวเลข m³/s ที่กุขึ้นมา) | `MEASURED-community`/`INSTINCT` |

**สรุป**: layer นี้แข็งแรงตรงที่ **ไม่มีจุดไหนแต่งตัวเลขขึ้นมาปิดช่องว่าง** — ทุกอย่างข้างบน
เมื่อขาดข้อมูล ระบบ `REFUSED` (หรือ `PARTIAL` ตาม promoter table) แทนที่จะฟันธง; จุดที่ยังอ่อน
คือการ**เชื่อมต่อ**ระหว่างชิ้นส่วน (layer0/typology ยังไม่ wire เข้า public page, community DAG
ยังไม่ merge/ไม่มีคนใช้จริง).

---

## (c) สิ่งที่เราตั้งใจ "ยังไม่ทำ" (DEFER) — กติกา "ซื้อ/รับเข้า อย่าสร้างเอง"

**Tag**: `INSTINCT` (นโยบายของทีมนี้, ตรงกับคำสั่ง founder "ส่วนที่ยังอ่อนก็ค่อยขาย ทำโจทย์หลัก
ก่อน" — อ่านว่า: ส่วนที่มีคนทำดีอยู่แล้วระดับโลก **ไม่ต้องสร้างเอง** รับเข้ามาเป็น input แทน)

**สิ่งที่ deliberately defer** (ไม่ใช่ "ลืม" — ตัดสินใจแล้วว่าไม่ทำเองตอนนี้):

1. **การพยากรณ์ความลึกน้ำระดับถนน (hydraulic street-depth forecasting)** — ต้องใช้แบบจำลอง
   hydraulic เต็มรูป (SWMM/HEC-RAS-class) ซึ่งนอกขอบเขตทีมอาสาสมัครไม่มีเครื่องมือวัดของตัวเอง
2. **การพยากรณ์น้ำท่วมระดับทรัพย์สิน (property-level inundation)** — ต้องมี DEM ละเอียดสูง +
   building footprint + การสอบเทียบต่อแปลง
3. **การตรวจจับน้ำท่วมจากดาวเทียม (satellite flood detection)** — ต้องมีไปป์ไลน์ประมวลผลภาพ
   ดาวเทียม/deep-learning model ของตัวเอง (Floodbase ทำสิ่งนี้อยู่แล้ว — ดูการ์ด third-party)
4. **SLA/ops การันตี (uptime, monitoring, failover, security ระดับ production)** — ทีม
   อาสาสมัคร ไม่มีทรัพยากรพอจะรับประกันระดับองค์กร
5. **การตรวจสอบ/validation เชิงพาณิชย์ (commercial validation deployments)** — ไม่ใช่เป้าหมาย
   ของระบบ readout สาธารณะที่ไม่แสวงกำไรนี้

**กติกา "ซื้อ/รับเข้า อย่าสร้างเอง"**: แต่ละผลิตภัณฑ์ภายนอกด้านบน**กลายเป็น INPUT** ของเรา
เมื่อเข้าถึงได้ โดย**คง tier เดิม**ของมันไว้เสมอ (ไม่ launder เป็น MEASURED ของทีมนี้เอง):

| ผลิตภัณฑ์ภายนอก | สถานะการเข้าถึงตอนนี้ | tier เมื่อรับเข้า |
|---|---|---|
| **Google Flood Hub** (riverine forecast API) | Waitlist/gated (ยืนยันซ้ำ 2026-09-27, ดู `GLOBAL_FREE_HAZARD_APIS.md` Tier 3) — เมื่อมี access จะรับเป็น `RELAYED-forecast` (เหมือนแหล่งพยากรณ์อื่นทั้งหมด, ไม่ใช่ MEASURED) | `RELAYED-forecast`, ผ่าน promoter table เดียวกับ PROP-FLOOD-06 |
| **GloFAS ผ่าน Open-Meteo** (`openmeteo_flood`) | **มีอยู่แล้ว, VERIFIED ดึงจริง** (ดู `GLOBAL_FREE_HAZARD_APIS.md` Tier 1, `sources/registry.yaml`) | `third_party` trust tier, ใช้เป็น `F_H(U)` inflow term |
| **RainViewer** (radar/satellite IR nowcast) | ยืนยัน endpoint ใช้ได้ (HTTP 200) แต่**เรดาร์ภาคพื้นดินในไทย = ยังไม่ยืนยัน** (`FORECAST_7DAY_SOURCES.md` §6) — ยังไม่ต่อจริง | จะเป็น `third_party`, เสริม layer-0 ระยะสั้นมาก (ไม่ใช่ 7-day) |
| **น้ำท่วมจากดาวเทียม (GDACS/UNOSAT)** | GDACS ดึงได้จริงไม่ต้อง key (Tier 1); UNOSAT ไม่มี REST API ชัดเจน เปิดเฉพาะเหตุการณ์ใหญ่ (Tier 4) | `RELAYED`/`OPEN`, ใช้เป็น trip-wire ไม่ใช่ตัวเลขหลัก |
| **FloodMapp / Floodbase** (satellite-based inundation intelligence) | ยังไม่ต่อ — ไม่มี API key/ความร่วมมือในคลังนี้ | จะเป็น `RELAYED` เมื่อมี — ไม่เคยเป็นคู่แข่ง เป็น input ชั้นบนของ epistemic layer เรา |

**ห่วงโซ่ที่ตั้งใจ**: Google Flood Hub (เมื่อมี) + BMA telemetry + Thaiwater + ปั๊ม + ชุมชน +
topology → **ชั้น epistemic ของเรา** (readout-not-truth, contradiction surfacing) → **community
DAG** → **การกระทำของคน** — ผลิตภัณฑ์ภายนอกทั้งหมดป้อนเข้าที่จุดเดียวกับแหล่งไทยอื่น ๆ ไม่มี
สิทธิ์ยับยั้งเชิงญาณเพราะเป็นแบรนด์ใหญ่ (ตรงกับ `CO_FORECAST_PROTOCOL.md` §2a).

---

## (d) แผน CORE-FIRST — 4 ข้อจาก critique แปลเป็นภาษา repo นี้

**ที่มา**: การวิเคราะห์ third-party ระบุ 4 must-do ก่อนโจทย์หลักจะ "แข็ง" (ดูการ์ด
`card_thirdparty_positioning_analysis_2026-09-27.md`) — แปลเป็น deliverable ที่จับต้องได้ใน
คลังนี้ พร้อม acceptance test ต่อข้อ (`INSTINCT` — การแปลนี้เป็นการตัดสินใจเชิงบรรณาธิการของ
ทีมนี้ ไม่ใช่ของผู้เสนอภายนอก):

### D1 — Ground-truth loop: ต่อยอด backtest discipline ไปถึง route/safe-node

**สถานะปัจจุบัน**: มี backtest discipline สำหรับ PROP-FLOOD-06 แล้วจริง (`BACKTEST_PROP_FLOOD_
06_v0.md`/`v1.md`/`v2.md`, hit rate 49.4%/miss 50.6%/false-alarm 11.7% รายงานเปิดเผยไม่ปิดบัง)
แต่**ยังไม่มี ledger ต่อเหตุการณ์สำหรับ route/safe-node** (Prediction → Reality ของ "ทางออกนี้
ใช้ได้จริงไหม", "safe node นี้ปลอดภัยจริงไหมตอนนั้น").

**Deliverable D1**: เพิ่มตาราง `route_reality_ledger`/`safe_node_reality_ledger` (append-only,
รูปแบบเดียวกับ `readout_log`) — แต่ละแถวคือ 1 เหตุการณ์จริง: `predicted_state` (จาก
community DAG ณ เวลานั้น) vs `reality_state` (ยืนยันหลังเหตุการณ์ จากรายงานชุมชน/เจ้าหน้าที่)
+ `lead_time` + `miss`/`hit`/`false_alarm` ต่อ route/node เดียวกับที่ `BACKTEST_PROP_FLOOD_
06_v1.md` ทำกับตัวชี้วัดน้ำ.

**Acceptance test**: มีอย่างน้อย 1 เหตุการณ์จริง (เช่นเหตุการณ์สัมมากร 26-27 ก.ย. 2569 ที่มี
รายงานชุมชนอยู่แล้ว) ที่ผ่านการเขียนแถว ledger ครบ (predicted vs reality) แล้ว publish
hit/miss/lead-time ต่อ route แยกจากกัน (ไม่รวมยอดข้ามหน่วยจนซ่อนหน่วยที่แย่ ตาม
`CO_FORECAST_PROTOCOL.md` §5 ข้อ 7).

### D2 — Human operation: Sammakorn pilot จริง (zone/buddy/safe node + verification cycle)

**สถานะปัจจุบัน**: `community_dag.py` มี schema (zone/buddy_cell/safe_node) และ tests 7/7 ผ่าน
บน `origin/main` แต่**ยังไม่ merge เข้า `feat/redesign-v2`**, **ยังไม่มีคนจริงในสัมมากรใช้งาน**,
ยังขาด epistemic tag ในเอกสารประกอบ (ดู reviewer TODOLIST #1).

**Deliverable D2**: (1) merge community DAG เข้า branch นี้ตาม merge plan ที่เตรียมไว้
แล้ว (`git merge origin/main` + full pytest + `kb.py reindex`); (2) เติม epistemic tag ทุก
claim ใน `docs/COMMUNITY_SELF_HELP_DAG.md`; (3) ประกาศ zone/buddy/safe-node **จริง**สำหรับ
สัมมากร (ไม่ใช่ synthetic) จากข้อมูลที่มีอยู่แล้ว (รายงานชุมชน 26-27 ก.ย., estate 6-wheel truck,
มอเตอร์ไซค์อาสา — ดู "Evidence-based sharpening" §"Sammakorn reports"); (4) รอบ
verification ภาคสนาม: **observe → verify → timestamp → publish → expire → recheck** ต่อ
safe-node หนึ่งจุด อย่างน้อย 1 รอบเต็ม; (5) ซ้อม (drill) กับคนจริงอย่างน้อย 1 ครั้ง.

**Acceptance test**: มี zone/buddy/safe-node อย่างน้อย 1 ชุดที่ผ่านรอบ verification เต็ม
(observe→verify→timestamp→publish→expire→recheck) กับคนจริงในสัมมากร ไม่ใช่ synthetic test
data, และมีบันทึกการซ้อม (drill) อย่างน้อย 1 ครั้งพร้อมผลลัพธ์ (สำเร็จ/ล้มเหลว/บทเรียน).

### D3 — Emergency UX 5-second test: หน้าเว็บต้องตอบ 4 คำถามได้ใน 5 วินาที

**คำถาม (founder-approved lens, คำต่อคำจากการวิเคราะห์ที่ founder รับมา)**:
"ฉันอยู่ตรงไหน → อยู่ต่อได้ไหม → ไปทางไหน → ใครช่วย" — **ห้ามมี graph theory/ศัพท์เทคนิคบนหน้า
จอ**.

**สถานะปัจจุบัน**: หน้า public page ปัจจุบัน (`site/build_page.py`) มีข้อมูลดิบ (ระดับน้ำ ปั๊ม
ฝน) แต่**ยังไม่จัดเรียงตามลำดับ 4 คำถามนี้เป็น hero section** — Layer 0 (IN/OUT/CAPACITY,
`docs/LAYER0_IN_OUT_CAPACITY.md`) และ typology (`FLOW_STALL_TYPOLOGY.md`) ให้เนื้อหาที่ตอบ
คำถามข้อ 2 ("อยู่ต่อได้ไหม") ได้แล้วในเชิงข้อมูล แต่ยังไม่ถูก wire เข้าหน้าเว็บ.

**Deliverable D3**: จัดหน้า public page ใหม่เป็นลำดับ **hero (แผนที่+ตัวเลขสำคัญ) → Layer 0
(IN/OUT/CAPACITY) → actions (Q4 จาก accountability query + community DAG buddy/safe-node)**
ตามลำดับ 4 คำถาม ไม่ใช่ลำดับปัจจุบันที่เรียงตาม data source.

**Acceptance test**: ทดสอบกับคนจริง (ไม่ใช่ทีมพัฒนา) ให้เปิดหน้าเว็บแล้วจับเวลา — ตอบ 4 คำถามได้
ภายใน 5 วินาทีต่อคำถาม (รวม ≤20 วินาทีทั้งหมด) ในสถานการณ์จำลอง (drill) อย่างน้อย 3 คน — ถ้า
ทำไม่ได้ = deliverable นี้ยังไม่ผ่าน, ไม่ใช่แค่ "ทีมคิดว่าอ่านง่าย".

### D4 — Offline/degraded mode: แผนที่กระดาษ, สายโทรศัพท์

**สถานะปัจจุบัน**: ไม่มีในคลังนี้เลย — ระบบทั้งหมดพึ่งพาอินเทอร์เน็ต/GitHub Pages/GitHub Actions
(`AGENTS.md` ระบุว่า "ไม่ใช้ AI และไม่พึ่งอินเทอร์เน็ตบ้านของใครคนใดคนหนึ่ง" สำหรับการอัปเดต
แต่**ผู้รับข้อมูลปลายทาง (resident) ยังต้องมีอินเทอร์เน็ตเพื่อเห็นหน้าเว็บ**).

**Deliverable D4**: (1) เอกสารแผนที่กระดาษ (printable) เวอร์ชันเดียวกับ zone/buddy/safe-node
ของ D2 พิมพ์แจกได้จริงในสัมมากร; (2) สายโทรศัพท์ (phone tree) จากรายชื่อ buddy cell ของ D2 ที่
ทำงานได้แม้ไม่มีอินเทอร์เน็ต/ไฟฟ้า.

**Acceptance test**: มีไฟล์แผนที่กระดาษ (PDF/รูปภาพ พิมพ์ได้จริง A4) ที่สะท้อน zone/buddy/
safe-node ล่าสุดของ D2 อย่างน้อย 1 เวอร์ชัน + รายชื่อ phone tree ที่ทดสอบโทรจริงอย่างน้อย 1
สาย (ไม่ใช่แค่รายชื่อในกระดาษ).

---

## (e) การทั่วไป (generalisation) — DAG เดียวกัน สลับ sensor/constraint

**Tag**: `INSTINCT` (แนวคิดรับมาจากการวิเคราะห์ภายนอก, สอดคล้องกับสิ่งที่คลังนี้ออกแบบไว้แล้ว
จริง — `FLOW_STALL_TYPOLOGY.md` §5 เขียนไว้ตรง ๆ ว่า chain/graph "ไม่ผูกกับสัมมากรโดยตรง" และ
`ACCOUNTABILITY_QUERY.md` ทดสอบแล้วว่า generic ไม่ hardcode พื้นที่เดียว — แต่**ยังไม่มีการ
ทดลองจริงกับภัยประเภทอื่น**ในคลังนี้ จึงเป็น INSTINCT ไม่ใช่ verified).

โครง Self → Buddy → Zone → Safe Network + evidence-strength ladder + contradiction-surfacing
เป็น**สถาปัตยกรรมทั่วไป**ที่ไม่ผูกกับ "น้ำ" โดยเนื้อแท้ — สลับ sensor (เซนเซอร์ไฟไหม้/
seismograph/PM2.5 monitor/สถานะไฟฟ้า) และ constraint (threshold ต่างกัน) แล้วใช้ได้กับ:
ไฟไหม้, แผ่นดินไหว, PM2.5, ไฟฟ้าดับเป็นวงกว้าง — **ยังไม่มีการลองจริง**, เป็นข้อสังเกตทาง
สถาปัตยกรรม ไม่ใช่ roadmap ที่อนุมัติแล้ว.

---

## (f) อะไรจะหักล้าง (falsify) ตำแหน่งนี้

**Tag**: `INSTINCT` (falsifier ที่ทีมนี้ประกาศเอง ตามกติกา "ความชอบธรรมจาก falsifier เท่านั้น"
`CO_FORECAST_PROTOCOL.md` §2d)

1. **ถ้าผู้อยู่อาศัยไม่สามารถลงมือทำอะไรจากหน้าเว็บได้ภายใน 5 วินาทีในการซ้อมจริง (drill)** —
   falsify D3 และ falsify คำกล่าวอ้างหลักของ (a) ทั้งหมด (คำถามหลักไม่มีประโยชน์ถ้าตอบไม่ทัน
   เวลาจริงของสถานการณ์ฉุกเฉิน).
2. **ถ้าแถวใน `contradictions` table ถูกมองข้าม/ไม่มีใครอ่านจริงเมื่อเกิดเหตุจริง** — falsify
   คุณค่าของ "ความขัดแย้งต้องปรากฏ" (b) — แปลว่าการโชว์ contradiction เป็นแค่ความสวยงามทาง
   เอกสาร ไม่ใช่ข้อมูลที่มีผลต่อการตัดสินใจจริง.
3. **ถ้า community DAG ไม่เคยถูก activate โดยคนจริงเลย** (ไม่มีใครใช้ zone/buddy/safe-node จริง
   แม้จะมีเหตุการณ์จริงเกิดขึ้นแล้ว เช่น 26-27 ก.ย. 2569) — falsify D2 และแปลว่า "human action
   infrastructure" เป็นแค่โค้ด ไม่ใช่โครงสร้างที่ใช้งานได้จริง.
4. **ถ้า ground-truth ledger (D1) แสดงว่า miss rate ของ route/safe-node แย่กว่าการเดาสุ่ม** —
   falsify คุณค่าของชั้น epistemic ทั้งหมดที่อ้างว่า "อ่านค่าได้ดีกว่าไม่มีข้อมูล".

---

## สรุป 1 ย่อหน้า

FloodConnect ไม่ใช่คู่แข่งของ Google Flood Hub/FloodMapp/Floodbase — เราเป็นชั้น**หลักฐาน
ท้องถิ่น + โครงสร้างที่ทำให้คนลงมือทำได้** ที่อยู่ใต้ผลิตภัณฑ์เหล่านั้น ซึ่งเราออกแบบให้รับ
พวกมันเป็น input ไม่ใช่สร้างสิ่งที่พวกมันทำอยู่แล้วซ้ำ (hydraulic forecast, satellite
detection, property-level inundation, SLA ระดับองค์กร — ข้อ (c)). สิ่งที่เรามีอยู่แล้วจริง
(telemetry หลายแหล่ง, contradiction surfacing, layer 0, typology, accountability query,
knowledge graph — ข้อ (b)) แข็งแรงในแง่ความซื่อสัตย์ของข้อมูล แต่ยังอ่อนในแง่**การเชื่อมต่อกับ
คนจริง** — 4 deliverable ของ (d) (ground-truth loop, human operation ที่สัมมากร, emergency
UX 5-วินาที, offline mode) คือสิ่งที่ต้องทำให้เสร็จก่อน เพื่อให้โจทย์หลัก "แข็งและครบ" ตามคำสั่ง
founder ก่อนจะไปขายส่วนที่ยังอ่อน.

---

## TODOLIST (append-ready สำหรับ `docs/knowledge/FOUNDER_TASKS_2026-09-27.md`)

```
- [ ] D1: เพิ่ม route_reality_ledger/safe_node_reality_ledger (append-only) + เขียนอย่างน้อย
      1 เหตุการณ์จริง (สัมมากร 26-27 ก.ย. 2569) พร้อม publish hit/miss/lead-time แยกต่อหน่วย
      (owner: worker ที่ commit layer0/backtest ต่อ, prio: high)
- [ ] D2: merge community_dag.py จาก origin/main เข้า feat/redesign-v2 (ตาม merge plan ใน
      REVIEW_COMMUNITY_DAG_ORIGIN_MAIN.md) + เติม epistemic tag ใน
      docs/COMMUNITY_SELF_HELP_DAG.md + ประกาศ zone/buddy/safe-node จริงของสัมมากร + รอบ
      verification เต็ม (observe→verify→timestamp→publish→expire→recheck) 1 รอบ + ซ้อม 1 ครั้ง
      (owner: committer, prio: high)
- [ ] D3: จัดหน้า public page ใหม่ตามลำดับ hero(map+numbers) → Layer 0 → actions ตอบ 4 คำถาม
      "ฉันอยู่ตรงไหน→อยู่ต่อได้ไหม→ไปทางไหน→ใครช่วย" + ทดสอบจับเวลากับคนจริง ≥3 คน ≤5
      วินาที/คำถาม (owner: build_page.py committer, prio: high)
- [ ] D4: ทำแผนที่กระดาษ (PDF พิมพ์ได้) + phone tree จาก buddy cell ของ D2 + ทดสอบโทรจริง
      อย่างน้อย 1 สาย (owner: committer + founder, prio: medium)
- [ ] ตรวจ claim third-party เพิ่มเติม (Ushahidi 160+ ประเทศ, whitepaper ของ Google/FloodMapp/
      Floodbase ที่ยังไม่อ่าน) หากจะอ้างอิงตัวเลขเหล่านี้ในเอกสารสาธารณะ (owner: worker คนถัดไป,
      prio: low — ไม่บล็อกโจทย์หลัก)
```
