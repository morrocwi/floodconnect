# Table-of-tables — แผนปฏิบัติการป้องกันและแก้ไขปัญหาน้ำท่วม กทม. ประจำปี 2569 (สนน.)

**Tag**: VERIFIED (index built from the `pdftotext -layout` text layer of the 322-page PDF, every page scanned for table signals; page numbers are PDF pages, printed labels in brackets) · **บันทึกเข้า**: 2569-09-27 · **Scope**: new file, not committed as part of this change.

Founder instruction (verbatim): "นายต้องสกัดตารางสำคัญต่างๆ ออกมาให้หมด เพื่อเติม typology เราให้แข็งแกร่ง". This index is the completeness ledger for that instruction: every table found, its class, and whether its rows now sit in a `docs/knowledge/bma_plan2569_<class>.yaml`.

Status legend: **extracted** = rows in a YAML with page + raw line · **hand** = transcribed by the worker from the text layer (small table) · **garbled** = text layer unusable, page image needed (not rendered this check, RAM-boxed) · **skipped** = not a physical/operational-object table (reason given).

| # | Table (title as printed / paraphrase) | PDF pages (printed) | Rows | Asset class | Status → file |
|---|---|---|---|---|---|
| T01 | คำสั่ง กทม. ที่ __/2569 จัดตั้งศูนย์อำนวยการฯ — องค์ประกอบ 15 ตำแหน่ง + อำนาจหน้าที่ 2.1-2.5 | 4-5 | 15+5 | command | hand → card §3 |
| T02 | ภารกิจหน้าที่ตามแผนปฏิบัติการ (11 หน่วยงาน) | 6 | 11 | command/responsibility | hand → card §3 |
| T03 | คำสั่ง สนน. ที่ __/2568 ศูนย์ปฏิบัติการฯ — ผู้อำนวยการ/ฝ่ายปฏิบัติการ 30 ตำแหน่ง/ฝ่ายตรวจสอบ 20/ฝ่ายเลขานุการ 10 | 7-11 | ~60 | command | hand (roles only) → card §3 |
| T04 | ตารางปริมาณฝนสะสมและความเข้มฝน (IDF, คาบ 2/5/7/10/12 ปี × 10 ช่วงเวลา) | 18 (1-2) | 5×10 | design threshold | hand → `bma_plan2569_assets.yaml: design_storm_table_p18` |
| T05 | ระดับน้ำสูงสุดที่ปากคลองตลาด รายปี (12 ปี) | 19 (1-3) | 12 | river threshold | hand → `coping_thresholds_additions_bma_plan2569.yaml` |
| T06 | ระดับน้ำสูงสุด 2554 vs คันกั้นน้ำเดิม/หลัง 2554 (4 ช่วง) | 19 (1-3) | 4 | levee | hand → `bma_plan2569_assets.yaml: levees_and_flood_walls` |
| T07 | §5.1 ช่วงปฏิบัติการ 3 ช่วง (ฝน/ระดับเจ้าพระยา/C.29B) | 22 (1-6) | 3 | operating threshold | hand → `coping_thresholds_additions_bma_plan2569.yaml` + card §1 |
| T08 | §5.2.1 กำหนดการเตรียมการ (Gantt ต.ค.68-ก.ย.69) | 23 (1-7) | 6 | schedule | hand → card §3 (dates only) |
| T09 | ระบบพื้นที่ปิดล้อมย่อยบริหารจัดการน้ำท่วม (Sub Polder) 38 พื้นที่ + ตร.กม. | 24-25 (1-8/1-9) | 38 | sub_polder | extracted → `bma_plan2569_assets.yaml: sub_polders_38_p24_25` |
| T10 | §5.3.1 กำหนดการเตรียมการน้ำหนุน (Gantt) | 28 (1-12) | 8 | schedule | hand → card §3 |
| T11 | แผนซ่อมบำรุงรักษาระบบควบคุมน้ำ (Gantt) | 37 (1-21) | 4 | schedule | skipped (no object rows) |
| T12 | แผนการติดตั้งและสนับสนุนเครื่องสูบน้ำ (สนน./สนข. × ตะวันออก/ตะวันตก) | 38 (1-22) | 5 | equipment summary | hand → `bma_plan2569_assets.yaml: pump_installation_summary_p38` |
| T13 | การจัดสรรงบประมาณ 2569 สนน. | 42 (1-26) | 5 | budget | hand → `bma_plan2569_assets.yaml: budget_2569_p42` |
| T14 | โครงการสำคัญ 2569 (7 งาน) | 49-52 (2-1..2-4) | 124 | project | extracted → `bma_plan2569_assets.yaml: key_projects_2569_p49_52` |
| T15 | คันกั้นน้ำพระราชดำริ ด้านตะวันออก (แนว/ระดับ/ความยาว/ทำนบ 5 แห่ง) | 55-56 (ก-1/ก-2) | 7 | levee | hand → assets: levees |
| T16 | แนวป้องกันน้ำท่วมริมแม่น้ำ/คลอง — ความยาว, ระดับ, ฟันหลอ 32 แห่ง | 59 (ก-5) | 12 | levee/flood wall | hand → assets: levees |
| T17 | พื้นที่ป้องกัน 3 พื้นที่ (650/450/468 ตร.กม.) | 60 (ก-6) | 3 | protected area | hand → assets: protected_areas_p60 |
| T18 | ระบบระบายน้ำ: จำนวนคลอง/ท่อ/สถานีสูบ/ปตร./บ่อสูบ + ขีดความสามารถรวม (ลบ.ม./วิ) | 63-64 (ก-9/ก-10) | ~15 | system counts | hand → assets: system_counts_p63 |
| T19 | อุโมงค์ระบายน้ำ 5 แห่งเปิดใช้ + 8 แห่งเพิ่มเติม (ความจุ/เส้นผ่านศูนย์กลาง/ความยาว/พื้นที่) | 64-75 (ก-10..ก-21) | 15 | tunnel | hand → assets: tunnels |
| T20 | อาคารรับน้ำอุโมงค์หนองบอน 8 จุด (ลบ.ม./วิ) | 68 (ก-14) | 8 | intake | hand → assets: tunnels[4].intakes_p68 |
| T21 | Pipe Jacking 12 โครงการเสร็จ + 2 โครงการ (งบ) | 77 (ก-23) | 14 | project | hand (partial; budgets cut in text layer) → assets: pipe_jacking_p77 — **garbled cells** |
| T22 | แก้มลิงที่จัดหาแล้ว 38 แห่ง (ลำดับ/ชื่อ/ปริมาตร) | 78-80 (ก-24..ก-26) | 38 | pond | extracted → `bma_plan2569_retention_ponds.yaml: capacity_list_appendix_ko` |
| T23 | แก้มลิงกำลังก่อสร้าง 4 / ปรับปรุง 4 / จัดหาเพิ่ม 20 (ใน/นอกคันพระราชดำริ) | 80-81 (ก-26/ก-27) | 28 | pond | extracted (19 of 28 rows parsed; 9 rows whose name wraps or has no seq not parsed — see YAML `section` counts) → same file |
| T24 | ภารกิจเปิดทางน้ำไหล/รักษาความสะอาดคูคลอง กลุ่มงานบำรุงรักษาคลอง 1-4 (กว้าง/ยาว/ระดับขุดลอก/เขต/พิกัด) | 93-112 (ข-1..ข-20) | 269 | canal reach | extracted → `bma_plan2569_canal_dimensions.yaml` |
| T25 | ภารกิจรักษาความสะอาดบึงรับน้ำ (ปริมาตร/พื้นที่/ระดับ/พิกัด) | 98-99, 103, 107 (ข-6/7, ข-11, ข-15) | 17 | pond | extracted (15 full, 2 low-confidence) → retention_ponds: ponds_with_coordinates_appendix_kho |
| T26 | จุดเสี่ยงน้ำท่วมถนนสายหลัก ถอดบทเรียน 2568, 216 จุด (พิกัด) | 117-123 (ค-1..ค-7) | 216 | flood_prone_point | extracted 214 → `bma_plan2569_flood_risk_points.yaml` (seq 196, 206 not parsed: `เขตบางกอกใหญ่ 196 ถนนเพชรเกษม ช่วงซอยอุดมศรี 100.48225 13.72875`; `เขตบางขุนเทียน 206 ถนนบางกระดี่ ช่วงซอยบางกระดี่ 3 - 9 100.40027 13.62771`) |
| T27 | แผนที่จุดเสี่ยง/ระบบท่อระบายน้ำ (UTM grid maps) | 126-163 (ค-10..ค-47) | — | map | **garbled** (map images; text layer is grid labels only) — skipped |
| T28 | สรุปอัตราการสูบน้ำ/จำนวนเครื่อง/ปตร./สถานี รายกลุ่มงาน (ธ.ค. 2568) + ริมแม่น้ำ | 169 (ง-3) | 9+5 | system counts | hand → `bma_plan2569_control_structures.yaml: meta.summary_p169` |
| T29 | แผนการควบคุมระดับน้ำ — อาคารบังคับน้ำ (กำลังสูบ/จำนวนเครื่อง/เตือนภัย/วิกฤติ/แผน ก ข ค/พิกัด/โทร) 6 กลุ่มงาน | 170-208 (ง-4..ง-42) | 451 | pump_station / gate / intake / dam | extracted → `bma_plan2569_control_structures.yaml` (all 451 rows with raw_block; parse confidence per row; 60 east rows hand-checked) + thresholds → `bma_plan2569_canal_thresholds.yaml` (406) |
| T30 | สรุปแผนติดตั้งเครื่องสูบน้ำ กองเครื่องจักรกล (12 หน่วย) | 211 (จ-1) | 13 | equipment summary | hand → `bma_plan2569_pump_install_plan.yaml: meta.summary_p211` |
| T31 | จำนวนเครื่องสูบน้ำไฟฟ้า/เครื่องยนต์/เครื่องผลักดันน้ำ (ขนาด/กำลัง/จำนวน) | 212 (จ-2) | 21 | equipment inventory | hand → pump_install_plan: meta.inventory_p212 |
| T32 | แผนการติดตั้งเครื่องสูบน้ำชนิดไฟฟ้า 2569 (สถานที่/ขนาด/กำลัง/จำนวน/พิกัด) | 213-238 (จ-3..จ-28) | 573 | pump_pit / mobile pump point | extracted → `bma_plan2569_pump_install_plan.yaml` (538 with coords; 35 district-office allocation rows without) |
| T33 | ศูนย์ควบคุมระบบป้องกันน้ำท่วม — จำนวนสถานีเครือข่าย 8 ระบบ + ช่องทางเผยแพร่ + สายด่วน | 241-242 (ฉ-1/ฉ-2) | 12 | telemetry summary | hand → assets: telemetry_counts_p241 |
| T34 | สถานีเครือข่ายอัตโนมัติ 8 ระบบ (รหัส/ชื่อ/พิกัด/เขต): เรดาร์ 2, ฝน 130, น้ำท่วมถนน 240, อุโมงค์ 8, ระดับน้ำ 310, อัตราการไหล 55, บ่อสูบ 170, SCADA 100 | 244-268 (ฉ-4..ฉ-28) | 1,015 | gauge / sensor / station | extracted 1,012 → `bma_plan2569_stations.yaml` (3 rows not parsed: FL 1, WL 2 — wrapped lines) |
| T35 | (ฉ-29..ฉ-34) หน้าว่าง/ภาพ | 269-274 | — | — | skipped (no text) |
| T36 | ตารางน้ำขึ้นเต็มที่-น้ำลงเต็มที่ กรมอุทกศาสตร์ สถานี กองบัญชาการกองทัพเรือ ม.ค.-ธ.ค. 2569 | 275-286 (ฉ-35..ฉ-46) | 12×31 | tide boundary condition | skipped this check (predicted tides, not objects; repo already ingests `dds_tide_pdf`) — **cross-check TODO #60** |
| T37 | แผนที่อากาศ/คำศัพท์/พายุหมุนเขตร้อน 2568 (ตารางที่ 1-2 พายุ) | 287-298 (ฉ-47..ฉ-58) | 2 tables | event history | skipped (narrative/history; no BKK object rows) |
| T38 | ตารางที่ 1 โรงควบคุมคุณภาพน้ำ 9 แห่ง (พิกัด) + โครงการบำบัดน้ำเสีย | 306-309 (ช-6..ช-9) | 9+4 | wastewater plant | skipped (water-quality, not flood); 13 coord lines available if a `wwtp` class is ever wanted |
| T39 | นามเรียกขานวิทยุสื่อสาร สนน. (45 ตำแหน่ง) | 315 (ซ-1) | 45 | command (radio) | hand, roles only (no personal names per repo rule) → card §3 |
| T40 | หมายเลขโทรศัพท์ประสานงาน (สนน. รายตำแหน่ง / สนข. ฝ่ายโยธา 50 เขต / หน่วยงานภายนอก) | 316-320 (ซ-2..ซ-6) | ~120 | contact | hand, unit-level numbers only → card §3 |

## Coverage summary

- Tables found: 40 (T01-T40). Extracted or hand-transcribed: 33. Skipped with reason: 5 (T11, T27, T35, T36, T37, T38 → 6 incl. garbled T27). Partially garbled: T21 (budgets), T23 (9 wrapped rows), T25 (2 rows), T26 (2 rows), T34 (3 rows), T29 (parse_confidence `low` rows carry raw_block for re-reading).
- Rows delivered with coordinates: stations 1,012 · control structures 451 · pump-install points 538 · canal reaches 269 · ponds 17 · flood-risk points 214 → **2,501 georeferenced rows**.
- Pages rendered as images this check: **0** (RAM-boxed; every unreadable cell is named above so the next worker can `pdftoppm -r 110 -f N -l N` exactly those pages: 77, 80-81, 107, 121-123, and the `parse_confidence: low` pages listed inside `bma_plan2569_control_structures.yaml`).
