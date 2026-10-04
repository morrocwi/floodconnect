# วิธีได้มาซึ่งชุดสมการคำนวณน้ำทั้งระบบ — System Equation Set Method (2026-09-27)

**คำสั่งผู้ก่อตั้ง (คำต่อคำ)**: "สร้างวิธีที่จะได้สมการการคำนวณน้ำทั้งระบบ เซ็ตระดับโลกเลย"

**สถานะไฟล์นี้**: เอกสาร *วิธี* (method) — ไม่ใช่การ derive สมการใหม่ ไม่แก้ไฟล์ที่ track อยู่ ไม่ commit
ไม่ build. เขียนโดย กระบวนการคู่ขนาน (worker อื่นกำลังเขียน `docs/knowledge/FORECAST_RISK_SHORTEST_EQUATION_2026-09-27.md`,
`sources/terminology_crosswalk.yaml` และร่าง PROP-FLOOD-08 — load ratio / drawdown time / storage deficit — ณ เวลาที่เขียน
ไฟล์เหล่านั้น**ยังไม่มีในเวิร์กทรี** จึงอ้างถึงเป็น "ดู 08 draft" โดยไม่ทำซ้ำ). ทุกตัวเลขในเอกสารนี้อ่านจากไฟล์ใน repo นี้และ
จาก registry ของ Toledo (read-only) ณ ค่ำ 2026-09-27 — ตัวเลขนับ (counts) เป็น `MEASURED` และ **drift ทุก build** ให้นับใหม่
ก่อนอ้างเป็นค่าปัจจุบัน. แท็ก: `VERIFIED` / `MEASURED` / `RELAYED` / `INSTINCT` / `OPEN` ตาม `AGENTS.md` §2;
`PROPOSAL` ใช้เฉพาะกับสมการที่ยังไม่ขึ้นทะเบียน Toledo (§1.1 ของกติกากลาง) ไม่ใช่แท็กความมั่นใจทั่วไป.

**Toledo lookup ที่รันจริงในงานนี้ (VERIFIED)**: `toledo_mcp.cli check --formula "<network-coupling statement>"` (จาก `mcp/`
ของ Toledo worktree) → `verdict: NOT_REGISTERED, candidates: []`. อ่าน statement เต็มของ `registry/proposals/flood_*.json`
(PROP-FLOOD-01/02/03/05a/05b/06/07) และ `registry/CANONICAL.json` (1,344 objects; scan คำสำคัญ conservation/ledger/
Laplacian/junction/routing ได้ 64 hits, อ่านตัวที่เกี่ยว: `weld/M.01.v1`, `weld/S.22.v1`, `EQ-001/C.01.v1`, `EQ-001/C.02.v1`).
PROP-FLOOD-04 ยังไม่อยู่ใน registry (PR #61 pending) — อ่าน statement จาก `canal_graph.py` docstring แทน.

---

## 0. คำตอบสั้น (≤ 10 บรรทัด)

1. **ชุดสมการทั้งระบบไม่ใช่สมการใหม่หนึ่งก้อน แต่คือการ "ประกอบ" object ที่ขึ้นทะเบียนแล้ว 7 ตัว (01–07) ลงบนกราฟจำกัด (finite graph)
   ของ object class 14 ชนิด + edge 6 ชนิด** ที่ประกาศจากทะเบียนจริงที่เรามีแล้ว (แผน สนน. 2569: 38 sub-polder, 451 อาคารบังคับน้ำ,
   269 ช่วงคลอง, 1,012 สถานี, 214 จุดเสี่ยง; KG 25,463 node) — §1–§2.
2. **สิ่งที่ยังขาดจริงในระดับสมการมีชิ้นเดียว**: กติกา *เชื่อมโหนด* (network coupling — "หนึ่ง edge หนึ่งตัวเลข" ที่ปรากฏเป็น
   Q_out ของต้นทางและ Q_in ของปลายทางพร้อมกัน, ขอบเขตด้วย capacity, ทิศทางต้องสอดคล้อง 04, junction ไม่มีที่เก็บ ⇒ เข้า = ออก,
   outfall ผูกกับระดับแม่น้ำ/น้ำทะเล) — อ่าน statement ของ 03/04/05/06 แล้วยืนยันว่า**ไม่มี object ใดกล่าวถึง**; Toledo check =
   NOT_REGISTERED → เสนอเป็น **PROP-FLOOD-09 candidate, NEW DERIVATION / PROPOSAL — not yet in Toledo** (§2.3).
3. **พารามิเตอร์ที่ต้อง "วัด" จากเหตุการณ์จริง ไม่ใช่ประกาศ**: c, A, η, cap_e, τ_e (รวม lag หนองจอก→พระโขนง) — แต่ละตัวมี
   ขั้นตอน/จำนวนเหตุการณ์ขั้นต่ำ/ตัวหักล้าง (§3); การทดลอง τ_e ครั้งแรกเริ่มได้คืนนี้จาก recession front ที่เห็นจริง (SSB.01/03 ลด,
   07/09/10/12 นิ่ง).
4. **ชั้นคุณภาพข้อมูล** (anchor rule, datum, day boundary, contradiction ledger, coverage vector) และกติกาการแพร่ของ PARTIAL/REFUSED
   ในกราฟ ตัดสินแล้ว: REFUSED ต้นน้ำ ⇒ ปลายน้ำ *ไม่ REFUSED ตาม* แต่ Q_in ของมัน = ABSENT และโหนดปลายน้ำเป็น PARTIAL ด้วย
   anchor ของตัวเอง; REFUSED เฉพาะเมื่อ input ทุกตัวของมันเอง ABSENT (§4).
5. **ความชอบธรรมมาจาก backtest ≥ 100 event-day + falsifier ที่ประกาศล่วงหน้าเท่านั้น** (§5) — ไม่มี external validation lever.

---

## 1. Object model — ชุดคลาสจำกัด (finite class set), state ขั้นต่ำ, input ขั้นต่ำ, ทะเบียนที่มี / ที่ขาด

**หลักการ (founder mapping)**: node = พื้นที่/sub-polder ที่มี *งบน้ำ* (storage balance) ของตัวเอง; "ความสามารถจ่าย" (ability to
pay) = อัตราระบาย `Q_out` (m³/s) ของโหนดนั้น; เมือง = ผลรวมของ `Q_out` ที่ทุก outfall. ทุก class ต้องประกาศ **state vector ขั้นต่ำ**
(สิ่งที่สมการต้องรู้เพื่อ step ได้) และ **measured input ขั้นต่ำ** (สิ่งที่ต้องอ่านได้จริงจากแหล่งใด แหล่งหนึ่ง) — ถ้าอ่านไม่ได้ ⇒
REFUSED/PARTIAL ตามชั้น §4 ไม่ใช่ค่า default.

### 1.1 Node classes (14)

| # | class | state vector ขั้นต่ำ (ต่อ tick τ) | measured input ขั้นต่ำ | ทะเบียน/ตารางที่ให้ (ไฟล์ · KG class) | มีแล้ว (MEASURED นับจากไฟล์) | ขาด (OPEN) |
|---|---|---|---|---|---|---|
| N1 | `sub_polder` / drainage unit (พื้นที่ปิดล้อมย่อย) | `S_b(k)` (m³), `A_b`, `c_b`, รายชื่อ outlet/pump ที่ผูก | ฝน `P(k)` ที่เกจในพื้นที่, `Q_out` จาก pump/gate ที่ผูก | `bma_plan2569_assets.yaml: sub_polders_38_p24_25` (38 พื้นที่ + ตร.กม.), `protected_areas_p60` (3: 650/450/468 ตร.กม.), `sources/dwr_subbasins.yaml` (359 sub-basin, licence OPEN, ใช้ภายใน), `sources/backtest_units.yaml` (6 units) · KG `district` 50, `sub_basin` 359 | 38 sub-polder มี **พื้นที่** ครบ; 359 sub-basin มี polygon; 6 unit มี tuple ⟨A,O,P,c⟩ บางส่วน | **polygon ของ 38 sub-polder = 0** (แผนให้แต่ตร.กม.), `A_U` เป็น INSTINCT radius 5/6 unit + sammakorn OPEN, `c_U` OPEN **6/6**, `S_b(0)` OPEN ทุกโหนด |
| N2 | `pond` / retention (แก้มลิง/บึง) | `S(k)`, ระดับ `h(k)`, stage–storage `S(h)` | ระดับบึง (WL.xxx), สถานะปั๊มที่บึง | `bma_plan2569_retention_ponds.yaml` (`capacity_list_appendix_ko` 57 แถว; 17 บึงมีพิกัด/ปริมาตร/พื้นที่/ระดับขุดลอก), `sammakorn_unit_from_bma_plan2569.yaml` (บึงสัมมากร 227,200 m³ VERIFIED p79) · KG `retention_basin` 14, `pond` 1 | 57 ปริมาตร VERIFIED, 17 พิกัด VERIFIED, บึงสัมมากร = แก้มลิง #25 ทางการ; เกจบึง 1 จุด (WL.SMK.01, เริ่ม 27 ก.ย. 10:15Z) | **stage–storage curve 0/57**, `S(0)` 0/57, เกจระดับบึง 1/57 |
| N3 | `canal_reach` (ช่วงคลอง) | `h_u(k), h_v(k)` ปลายทั้งสอง (datum เดียวกัน), `cap_e` | ระดับ 2 ปลาย (WL), ระดับขุดลอก/สัน | `bma_plan2569_canal_dimensions.yaml` (269 ช่วง: กว้าง/ยาว/ระดับขุดลอก ม.รทก./เขต/พิกัด; คลองสำคัญ 44), `site/inputs/canals/east_chain.yaml` (18 node ประกาศมือ) · KG `canal` 190 (Wikipedia), `canal_node` 8,690 (OSM) | 269 มิติ VERIFIED; ระดับท้องคลอง (dredge level) ใช้เป็น `bed_m_msl` proxy 269 ช่วง | **design/conveyance capacity m³/s = 0/269** (แผนไม่ระบุ — ยืนยัน `led:bkk_east_canals_summary` OPEN), เกจ 2 ปลายครบเฉพาะสายแสนแสบ/ประเวศ/หัวหมาก |
| N4 | `junction` (จุดบรรจบ, ไม่มีที่เก็บ) | ไม่มี state; constraint Σin = Σout ต่อ tick | edge flow ทุกเส้นที่เข้า/ออก (ผ่าน 09) | `east_multi_outlet_network_draft.yaml` (`AS_HOKWA` เป็น junction 2 แขน, proposal), KG `drain_junction` 1,077 (ชื่อถนน ไม่มีพิกัด), OSM junction ~8,600 | โครงสร้างชื่อ 1,077 | **รายการ junction ที่ประกาศว่า storage ≡ 0 = 0**, flow telemetry 0 |
| N5 | `gate` (ปตร./ทำนบ) | `g_c(k)` ∈ {OPEN, CLOSED, PUMPING}, `h_A, h_B`, ระดับ เตือน/วิกฤติ/แผน ก ข ค | สถานะประตูประกาศ, ระดับ 2 ด้าน (canal_in/canal_out) | `bma_plan2569_control_structures.yaml` (451 แถว, 201 ปตร. ตรง asset เดิมภายใน 60 ม. + 24 ใหม่), `bma_plan2569_canal_thresholds.yaml` (406 แถว ม.รทก.), `inter_agency_agreements_5_3_4` (7 ข้อตกลง RID–BMA: หกวา/คลอง 13, แสนแสบ/หนองจอก, ประเวศ/พระองค์ฯ, เปรมใต้) · KG `gate` 2,279 (HII watergate 2,315 ทั่วประเทศ) | 451 พิกัด+เกณฑ์ VERIFIED; `gate_opening_m` บางสถานีจาก `bma_watermap`; `hii_watergate` ให้ระดับเหนือ/ใต้ | **`g_c(t)` ทางการที่เผยแพร่ = 0 สถานี** (ยัง *inferred*, `LESSONS_nodes` §A), hii_watergate ยังไม่ crosswalk กับ WL.xxx.NN |
| N6 | `pump_station` (สถานีสูบ) | `P_run(k)` (m³/s), `pumps_on/total`, rated ต่อเครื่อง, `η` | `pumps_on`, สถานะ "ขัดข้อง", ระดับหน้า/หลังสถานี | `bma_plan2569_control_structures.yaml` (199 ตรง asset เดิม + 9 ใหม่; กำลังสูบเติมค่าที่เดิม null **139 แถว**; ขัดแย้ง 104 แถว — 91 แถวค่าเดิมเรา = *จำนวนเครื่อง* ไม่ใช่ m³/s), `sources/registry.yaml: bma_pumphistory` · KG `pump_station` 297 | rated capacity ครบฝั่งตะวันออก (60.20 m³/s, 46 เครื่อง); ST.SPS.01–04 (7.75 m³/s) ผูกสัมมากร | **η (จริง/rated) วัดแล้ว = 0 สถานี**; ST.SPS.01–04 "ขัดข้อง" 39/39 แถว (27 ชม.+); running count นอกสายแสนแสบส่วนใหญ่ absent |
| N6b | `pump_pit` / mobile pump point (บ่อสูบ/จุดติดตั้ง) | rated, จำนวน, พิกัด | สถานะติดตั้ง/เดินเครื่อง | `bma_plan2569_pump_install_plan.yaml` (573 แถว, 538 พิกัด; 567 จุด 1,379 เครื่อง 947.72 m³/s) · KG `pump_pit` **0** | 538 พิกัด VERIFIED | class ใหม่ทั้งชุด, live state 0 |
| N7 | `tunnel` (อุโมงค์) | `Q_tunnel(k)`, intake states | ระดับ TN 8 สถานี, running | `bma_plan2569_assets.yaml: tunnels` (15: 5 เปิดใช้ 30/45/60/60/60 + 8 เพิ่ม + 2 ยอดรวม 255/370), `sources/capacity_ledger.yaml` tunnel 14 แถว · KG `tunnel` 13 (OPEN) | rated 5 อุโมงค์ตรงกัน ledger↔แผน | live flow 0; รายการ SpringNews (สุขุมวิท 26/36/42, พญาไท) ไม่อยู่ในแผน → class OPEN |
| N8 | `outfall` (จุดออก → แม่น้ำ/ทะเล) | `Q_cap,o`, `Q_o,now(k)`, `g(k)` derating, `gravity_threshold` | flow ที่จุดออก, ระดับแม่น้ำ/น้ำทะเลด้านนอก | `sources/capacity_ledger.yaml` outfall **11 แถว** (chao_phraya_boundary, phra_khanong [49/155/173 **CONTRADICTED**], bang_sue, makkasan, nongbon, east_seaside_rid OPEN, tide_boundary, thachin, bangpakong, mun_chi, hatyai), `east_multi_outlet_network_draft.yaml` outlet 4 node · KG edge `OUTFALL` | 11 แถว, 5 มีตัวเลข rated; เพดานลงเจ้าพระยา 1,276.49 m³/s (D น.13) แยกจากกำลังสูบรวม 2,510.24 | **`gravity_threshold` OPEN ทุกแถว**, `Q_o,now` 0 (ไม่มี flow telemetry ที่เผยแพร่ แม้แผนระบุ FW 55 สถานี), utilisation OPEN 6/8 |
| N9 | `river_reach` (ช่วงแม่น้ำ) | `h(k)` MSL, `Q(k)`, bankfull/capacity | ระดับ+discharge จากโทรมาตร RID/HII | `thaiwater_waterlevel` (C.2/C.13/C.29 ฯลฯ), `sources/capacity_ledger.yaml` river_reach 9 แถว, แผน p19 (2,500–3,500 m³/s ไม่ล้นตลิ่ง; C.29B วิกฤติ ≤3,500), ระดับปากคลองตลาด 12 ปี · KG `river_reach` 2,250 (HydroRIVERS RELAYED) | reach หลักเจ้าพระยามีเกณฑ์ครบ; ระดับ MSL live | capacity ของ reach นอกเจ้าพระยา OPEN (น่าน/ปิง/อู่ตะเภา = OUTLET_CAPACITY_UNKNOWN ใน backtest) |
| N10 | `dam` (อ่างเก็บน้ำ) | storage %, inflow, release `R(k)` | ตาราง กฟผ./RID/HII | `hii_dam` (989 เขื่อน), `egat_water_crisis`, `rid_res_table` · KG `dam` 86, `reservoir_medium` 862, `reservoir_small` 60 | storage/release ระดับวัน | **lag ปล่อยเขื่อน→ กทม. OPEN ทุกเขื่อน** (`NATIONWIDE_HIERARCHY` OPEN 2) |
| N11 | `rain_gauge` (เกจฝน) | `P(k)` mm ต่อหน้าต่างที่ประกาศ | ฝน 24 ชม./รายชั่วโมง | `thaiwater_rain_24h`, `dds_daily_pdf`, แผน RF 130 สถานี (BKK) · KG `rain_gauge` 4,428 | พิกัด 4,428 VERIFIED; 24 ชม. live | **อนุกรมรายชั่วโมงที่เก็บถาวรของทีมเอง = เริ่ม 26 ก.ย. เท่านั้น**; coped_max/danger_min OPEN |
| N12 | `forecast_grid_cell` (เซลล์พยากรณ์) | ค่าต่อโมเดล/สมาชิก ต่อ horizon (ไม่เฉลี่ย) | forecast JSON ต่อ run | `sources/registry.yaml` third_party 10 แหล่ง (multimodel 9 โมเดล, ensemble 31–39 สมาชิก, 16d, previous_runs, GloFAS, marine, NASA POWER, MET Norway) | endpoint VERIFIED; skill-check ย้อนหลังใช้ได้จริง (7-day backtest) | **raw snapshot ต่อ run ยังไม่เก็บครบ** (`T7_T0_DATA_PLAN` §1b); point-vs-cell ratio OPEN (1 คู่: 13–53 vs 203 mm) |
| N13 | `community_report` (รายงานชุมชน) | `M(k)` ∈ {BACKFLOW, RISING, STEADY, FALLING, ABSENT}, ซอย+สภาพ+เวลา | ข้อความ + timestamp ที่ระบบรับจริง | `social_listening_google/paste`, `site/inputs/community/*`, ตาราง `experience_log` | T0 สัมมากร (INSTINCT convention) 1 เหตุการณ์ | **capture สด = 0** (achieved lead EARLY_MOVE = −9h), T0 convention ประกาศแค่ 1 unit |
| N14 | `level_gauge` (เกจระดับ — anchor object ที่ผูกกับ N2/N3/N5/N9) | `h(k)`, `ε`, datum, staleness, `suspect` flag | ค่าอ่าน + เวลา | `bma_plan2569_stations.yaml` (1,012: WL 308, FL 239, PH 170, ST 100, FW 55, TN 8, RF 130, radar 2), `data/observations.sqlite` (150,437 แถว, 9,542 station code ทั่วประเทศ, readout_log 1,621, contradictions 96) | รหัสตรง `bma_watermap` 306; **706 รหัสใหม่** (FL/PH/ST/FW/TN แทบไม่มีในระบบ) | datum ต่อสถานีส่วนใหญ่ OPEN (WL.BMA.02: เตือน 2.14 vs แผน +0.40 — คนละ datum?), พิกัดต่างเกิน 100 ม. 4 รหัส |

### 1.2 Edge classes (6)

| # | edge kind | state ขั้นต่ำ | measured input ขั้นต่ำ | ที่มีแล้ว | ที่ขาด |
|---|---|---|---|---|---|
| E1 | `conveyance` (คลอง/ท่อ เชื่อมสองโหนด, ไม่มีโครงสร้าง) | `Q_e(k)`, `cap_e`, `τ_e` (travel time), `design_direction` | `Δ_e = h_u − h_v` (04) | east_chain edges (18 node), KG `WATER` (HydroRIVERS+OSM+Wikipedia 72 resolved), `DRAINS_TO` 7,149 (ท่อ กทม.) | `cap_e` ≈ 0 ที่ประกาศ, `τ_e` **0 วัดจริง**, ทิศทางวัดได้เฉพาะคู่ที่มีเกจ 2 ปลาย |
| E2 | `gate_controlled` | + `g_c(k)` | สถานะประตู + ระดับ 2 ด้าน | 451 อาคาร (thresholds 406) | `g_c` ทางการ 0 |
| E3 | `pumped` | + `P_run(k)`, `η` | pumps_on | 199+9 สถานี, ST.SPS.01–04 | η 0, running ส่วนใหญ่ absent |
| E4 | `gravity` (ออกสู่แม่น้ำ/ทะเลด้วยแรงโน้มถ่วง) | + `gravity_threshold`, `g(k)` | ระดับด้านนอก (แม่น้ำ/น้ำทะเล) | `dds_tide_pdf`, `openmeteo_marine`, แผน T36 ตารางน้ำขึ้นลง 2569 (skipped, TODO #60) | threshold OPEN ทุกแถว |
| E5 | `diversion` (ผันน้ำ) | + สัดส่วนผัน/กติกาผู้ควบคุม | ตัวเลขผันจริง | C.13 → ชัยนาท-ป่าสัก/ระพีพัฒน์ (`AS_DIVERT_CNPS`), หกวา 2 แขน (36 m³/s VERIFIED plan50) | สัดส่วนจริงต่อรอบ OPEN (`NATIONWIDE_HIERARCHY` OPEN 4) |
| E6 | `backwater_coupled` (ปลายทางสูงกว่าต้นทางได้) | + `backwater_risk`, stage ปลายทาง | ระดับปลายทาง vs ต้นทาง | flag `backwater_risk: OPEN` ทุก edge ใน draft (14 edges) | ค่าวัดการแพร่ backwater = 0 |

**นับรวม (MEASURED)**: node class 14 (+1 sub-class) — มี "โครงสร้าง+พิกัด" ครบพอประกาศกราฟใน 12 class; **ขาดค่าที่สมการต้องใช้จริง
ใน 5 กลุ่ม**: (i) stage–storage ของบึง 0/57, (ii) conveyance capacity 0/269, (iii) สถานะประตูทางการ 0/451, (iv) η 0/208 สถานีสูบ,
(v) τ_e 0 edge. ห้าอย่างนี้คือสิ่งที่ §3 ต้อง "วัด" — ไม่ใช่สิ่งที่ต้อง "คิดสูตร".

---

## 2. Law layer — Toledo-first: object ที่ใช้ต่อ class และ statement การนำกลับมาใช้ (reuse) ที่แน่ชัด

**กติกา**: object ที่มีอยู่ → อ้าง code, ใช้ statement เดิม, เพิ่ม *occurrence* — ไม่มี twin/ไม่ตั้งชื่อใหม่; equivalence ที่ยอมรับ =
renaming / positive scale / constant substitution เท่านั้น. code ทุกตัวด้านล่างเป็น `weld/M.??.v1` **status unverified, tier Dr,
PROPOSAL** ใน `registry/proposals/` (01/02/03/05a/05b/06/07) และ 04 = PR #61 pending — **ไม่มีตัวใดเป็น Toledo theorem**;
อ้างเป็น "PROP-FLOOD-xx (proposal, unverified)" เท่านั้น.

### 2.1 ตาราง class → object → reuse statement

| class / edge | object ที่ใช้ | reuse statement (ไม่ derive ใหม่) |
|---|---|---|
| N1 sub_polder, N2 pond | **PROP-FLOOD-03** `S_b(k+1) := S_b(k) + P(k)·A_b·c_b + Q_in(k)·τ − Q_out(k)·τ` บน ℚ; `Q_out := 0` ถ้า gate CLOSED, มิฉะนั้น `min(Q_out_meas, C_pump,b)`; REFUSED ∈ {MISSING_INPUT, STALE_INPUT, UNDECLARED_AREA, UNDECLARED_EDGE, NEGATIVE_STORAGE} | **renaming**: b := sub-polder id (38 ของแผน) หรือ pond id; `A_b` := ตร.กม. × 10⁶ (**positive scale**), `C_pump,b` := Σ rated ของสถานีที่ผูก (constant substitution จาก `control_structures`); founder mapping "ability to pay" = `Q_out(k)` ของ 03 ตรงตัว. บึง: `S(h)` stage–storage เป็น *declared relation* ที่ 03 บอกเองว่า OPEN — ไม่ใส่สูตรแทน |
| N3 canal_reach, E1–E6 (ทิศทาง) | **PROP-FLOOD-04** `Δ_e(t) := h_u − h_v` (datum เดียว); FORWARD ถ้า > ε, REVERSE ถ้า < −ε, UNRESOLVED ถ้า ≤ ε; CONTROLLED ถ้าปลายเป็นประตูที่ out > in เกิน ε; REFUSED ∈ {MISSING_INPUT, STALE_INPUT, DATUM_MISMATCH, UNDECLARED_EDGE} | **renaming** ของ (u,v) เป็นทุก edge ที่มีเกจ 2 ปลาย; ε = 0.02 ม. (INSTINCT, `east_chain.yaml`) — ขอ 04 ให้ **ทิศทาง** เท่านั้น ไม่ให้ขนาด; datum rule §4.2 บังคับก่อนเรียก |
| N5 gate, N6 pump (ฝั่งใดแบก) | **PROP-FLOOD-05a** `a_c(t) := h_A − h_B` ภายใต้ `g_c ∈ {OPEN, CLOSED, PUMPING}`; HIGHER_SIDE/LOWER_SIDE (=BURDENED/RELIEVED) เฉพาะ non-OPEN; `P_c(k)` persistence; **05b** `net(Z,t) = (R−B, ΣP_rel − ΣP_bur)`, dense rank, NO_ORDER/NOT_EVALUABLE | **renaming**: c := แถวใน `control_structures` (451), ζ(c, side) := sub-polder ที่แต่ละด้านสังกัด (ประกาศจาก 38 sub-polder + inter-agency agreements 7 ข้อ: หกวา/คลอง 13 นอก ≤ +1.70 ใน ≤ +0.80 ฯลฯ) — 05 อ่าน *ภาระ* ไม่ใช่ flow; ห้ามใช้แทน 09 |
| N1/N8 (รับมือได้, tier, PARTIAL) | **PROP-FLOOD-06 v6.1** `R_H(U) = Σ_o max(0, Q_cap,o − Q_o,now)·H·3600`, `D_H(U) = Σ_t Σ_p P_run,p·3600·g_U(t)`, `F_H(U) = c_U·A_U·Σ rain + Σ Q_in,up·3600`, `S_H = F_H / min(D_H, R_H)` (+ `C_H` case split), tier L0–L5/LR, promoter floor, `cov6` 10 องค์ประกอบ ×{present, inferred, absent}, hysteresis p/q, `τ_up` + `T_act_upstream`, multi_model_scenarios (worst_case first), `calibration_procedure`, LAYER 0 headline | **U := เมือง (กทม.) ⇒ R_H รวมทุก outfall = founder's "เมือง = Σ Q_out ที่ทุก outfall" ตรงกับ Σ_o ของ 06 โดย renaming O_U := 11 outfall ของ ledger**; U := sub-polder ⇒ 38 instance; `g_U(t)` derating เมื่อระดับแม่น้ำ/น้ำทะเล > `gravity_threshold` (declared, OPEN ตอนนี้ ⇒ DERATING_UNDECLARED เฉพาะ term) |
| E1–E6 (สถานะการไหล) | **PROP-FLOOD-07** classifier F1–F6 บน (D จาก 04, T จาก 01, C = control state, M = community); REFUSED เฉพาะ D=T=C=M=ABSENT; F6 พก `ruled_out`; RULE-STALL-01 / RULE-DIR-01 (INSTINCT-rule) ให้ Inferred + anchor ids + min-confidence | **ใช้ตรงตัวต่อ edge**; ไม่มี arithmetic เพิ่ม |
| N2/N3/N9 (เวลาถึงเกณฑ์) | **PROP-FLOOD-02** `T_k := (θ − h(t))·k / Δ_k(t)` เฉพาะ `Δ_k > ε` และ `h < θ`; REFUSED ∈ {UNRESOLVED, NOT_APPLICABLE} (non-value) | **renaming**: θ := เตือน/วิกฤติ/แผน ก ข ค ของสถานีจาก `canal_thresholds` (406 แถว, constant substitution); **หมายเหตุ**: `AGENTS.md` §8 บันทึกว่า 02 ยังไม่ implement ที่ไหน — โมดูลใหม่ต้องเรียก 02 ตรง ไม่ทำเลขเอง (ต่างจาก `tools/layer0` ที่ทำ inline และติดป้าย PROPOSAL-derived) |
| ทุก class (แนวโน้ม) | **PROP-FLOOD-01** `Δ_k(t) := h(t) − h(t−k)`; RISING/FALLING/FLAT/NO_READOUT ต่อ ε | ตรงตัว; หน้าต่าง persistence (`_is_persistently_stalled`) = ส่วนขยายที่ 07 รับรองแล้วว่า "ไม่ใช่สมการใหม่" |
| N12 forecast, N10 dam, N14 gauge (หลายแหล่ง) | **06 v6.1 `multi_model_scenarios`** worst_case / best_case / majority_band / disagreement_flag | ใช้กับ *ทุก* input หลายแหล่ง (ฝน, ปล่อยเขื่อน กฟผ. vs HII, ระดับ สนน. vs HII) — ห้ามเฉลี่ย |
| N1/N2 (load ratio, drawdown time, storage deficit) | **ดู 08 draft** (กระบวนการคู่ขนาน) | ไม่ทำซ้ำในไฟล์นี้; เมื่อ 08 มี code ให้ตาราง §2.1 เพิ่มแถว occurrence ไม่ใช่ twin |

**สิ่งที่ตารางนี้ยืนยัน**: object 01–07 ครอบคลุม *ภายในโหนด* (งบน้ำ, แนวโน้ม, เวลาถึงเกณฑ์), *บน edge* (ทิศทาง, สถานะไหล), *ที่โครงสร้าง*
(ภาระ), และ *ระดับ unit* (รับมือได้/tier/coverage). สิ่งที่ยังไม่มี object รองรับคือ **ข้อความที่พูดถึงหลายโหนดพร้อมกันผ่าน edge เดียวกัน**.

### 2.2 กติกาเชื่อมโหนด (network coupling) — แสดงได้จาก 03+04+05(+06) หรือไม่? — **ไม่ได้** (อ่าน statement แล้ว)

อ่าน statement เต็มแล้ว (registry JSON + docstring 04):

- **03** นิยาม `Q_in(k)` เป็น "sum over *declared graph edges into b*" และ `Q_out(k)` จาก `gate_flag`/`Q_out_meas`/`C_pump,b` — ทั้งสองเป็น
  **input ที่ประกาศให้โหนด b โดยอิสระ**; 03 **ไม่ได้กล่าว**ว่าตัวเลขที่ออกจาก u ต้องเป็นตัวเลขเดียวกับที่เข้า v (edge-flow identity),
  ไม่มีขอบเขต capacity ของ edge, และ claim_boundary ของ 03 เองพูดว่า "no routing time between b and its neighbours is modelled".
- **04** ให้ *เครื่องหมาย/ทิศทาง* ของ `Δ_e` เท่านั้น — "says nothing about flow speed/volume" (claim_boundary) — จึงผูกขนาด `Q_e` กับทิศทางไม่ได้.
- **05a/05b** อ่าน *ภาระ* (level asymmetry ภายใต้ control state) และ *ลำดับโซน* — claim_boundary: "No hydraulic flow-rate, discharge, or
  volume estimate is asserted".
- **06** ให้ headroom/drainage/inflow ระดับ *unit* และ `τ_up` จาก upstream gauge → unit; ไม่ให้ balance ที่ junction และไม่ผูก edge สองปลาย.

**Toledo lookup**: `toledo_mcp.cli check --formula …` → `NOT_REGISTERED`, ไม่มี candidate. **Canonical neighbours ที่อ่านแล้วและ *ไม่ใช่*
match**: `weld/M.01.v1` / `weld/S.22.v1` (discrete forced-Laplacian stepper `s[n+1] = s[n] + dt(−A s[n] + J)`, Th_coqc/Definition) —
เป็นการแพร่ *เชิงเส้น* บนกราฟ; edge flow ของเรา *อิ่มตัว* (bounded by `cap_e`) และ *สลับด้วยประตู/ปั๊ม* จึงไม่ใช่ renaming/scale/constant ของมัน
(ถ้าอ้างเป็น parent จะเป็น DRIFT); `EQ-001/C.01.v1` RT-LEDGER-001 ("declared closed boundary preserves ledger ⇒ A(n1−n0)=0", untagged)
เป็นหลักการ ledger ปิดขอบเขต — ใช้เป็น **Genesis/lineage compatibility** ร่วมกับ `readout_genesis` Part VI-A §B.2a "generic conservation
ledger" `C(𝔖_{n+1}) − C(𝔖_n) = J_in − J_out + J_created − J_obstructed [Dr]` ("architecture, not a physics claim") — ไม่ใช่ parent เชิงสมการ.

**ผลตัดสิน**: ต้องมี **PROP-FLOOD-09 candidate** — ชิ้นเล็กที่สุดที่ขาดคือ *identity + bound + consistency + boundary* 4 ข้อ ไม่ใช่โมเดล
การไหลใหม่.

### 2.3 PROP-FLOOD-09 candidate — NEW DERIVATION / PROPOSAL — not yet in Toledo (ห้ามใช้ในโค้ด/หน้าเว็บจนกว่าจะขึ้นทะเบียน)

**สถานะหลังค้น Toledo (ดู TOLEDO_HYDRAULICS_DIFFUSION_ZOOM_REUSE_2026-09-27)**: 09 เป็นการประกอบจากของที่
ลงทะเบียนแล้ว 4 ใน 5 ข้อ — delta จริงมีข้อเดียวคือ (i) ค่า edge เดียวลงบัญชีสอง node พร้อม delay เต็มหน่วยที่
ประกาศ; §2.2 เดิมค้นไม่ครบ (ไม่ได้ค้น D/, A2/, Z/, R/ และ EQ-001/C.*)

```
Declared finite graph G = (N, E), tick τ, all values on Q.
For every edge e = (u, v) in E, ONE Q-valued edge flow Q_e(k) (positive = u -> v) such that
  (i)   identity:   Q_e(k) is the SAME value appearing in Q_out,u(k) (as a summand) and in Q_in,v(k + d_e)
                     (as a summand), d_e := tau_e / tau in N a DECLARED integer delay (0 if undeclared -> flag TAU_UNDECLARED,
                     not a fabricated lag; tau_e is the per-edge renaming of PROP-FLOOD-06's tau_up);
  (ii)  bound:      |Q_e(k)| <= cap_e  (declared conveyance; absent -> REFUSED CAPACITY_UNDECLARED for this edge only);
                     for edge_kind pumped/gate_controlled, Q_e(k) follows PROP-FLOOD-03's own Q_out rule
                     (0 if CLOSED, min(Q_meas, C_pump) otherwise) -- cited, not restated;
  (iii) consistency: sign(Q_e(k)) must agree with PROP-FLOOD-04's readout on e at k:
                     FORWARD -> Q_e >= 0, REVERSE -> Q_e <= 0, UNRESOLVED -> Q_e is UNRESOLVED (edge contributes ABSENT to
                     both endpoints -> PARTIAL, never 0), REFUSED(04) -> ABSENT likewise; a MEASURED Q_e whose sign
                     contradicts 04 is a CONTRADICTION row, not a resolution;
  (iv)  junction:   a node declared storage-free (S == 0) is a PROP-FLOOD-03 node with S_b(k) = 0 for all k, so
                     sum_in Q_e(k) - sum_out Q_e(k) != 0 beyond declared resolution eps_Q is exactly 03's NEGATIVE_STORAGE /
                     bookkeeping refusal -- no new arithmetic;
  (v)   boundary:   an outfall edge (u -> river/sea) has cap_e(k) := max(0, Q_cap,o - Q_o,now(k)) * g(k) with g(k) from
                     PROP-FLOOD-06's declared gravity_threshold derating -- cited; stage h_river(k)/h_tide(k) is a DECLARED
                     boundary readout (RID/HII/Hydrographic table), never solved for.
Readout per node: PROP-FLOOD-03 step with Q_in/Q_out assembled by (i)-(v); per edge: (Q_e or ABSENT, 04 direction, 07 class).
Refusal (total, precedence): UNDECLARED_EDGE -> CAPACITY_UNDECLARED -> DATUM_MISMATCH (from 04) -> BOUNDARY_STAGE_MISSING
-> PARTIAL(ABSENT edges listed) ; REFUSED for a node only when every incident edge and every own input is ABSENT.
Parents: delta_R (instance_of), PROP-FLOOD-03 (per-node ledger, reused verbatim), PROP-FLOOD-04 (direction, reads),
PROP-FLOOD-06 (outlet headroom/derating/tau_up, reads), PROP-FLOOD-07 (edge class + inferred_value wrapper, reads).
Compatibility (not parents): EQ-001/C.01.v1 RT-LEDGER-001; readout_genesis VI-A B.2a generic conservation ledger [Dr].
Claim boundary: no momentum, no Saint-Venant, no rating curve, no continuum limit; Q_e is a declared-or-measured tick value
(m^3/s over one tau), the network is a bookkeeping constraint over declared readouts, not a hydraulic solve.
Falsifier: with EVERY incident Q_e MEASURED (flow telemetry) at a declared storage-free junction, a persistent imbalance
> eps_Q across >= 3 independent events retires (iv) for that junction class (a hidden storage/undeclared edge is then the
first suspect, recorded as UNDECLARED_EDGE candidate); a MEASURED Q_e repeatedly contradicting 04's sign retires (iii)'s
use of that gauge pair (datum/gauge suspect first).
Status: HOLD until (a) PROP-FLOOD-04 (PR #61) lands in its registered form, (b) 08 draft is read so 09 does not duplicate
its storage-deficit/drawdown terms, (c) founder decision D1 (Sec.6).
```

**ทำไมสองบรรทัด**: 03 ทำงบน้ำ *ทีละโหนด* ด้วย Q_in/Q_out ที่ประกาศแยกกัน จึงไม่มีอะไรบังคับว่าน้ำที่ออกจากบึงสัมมากรคือน้ำที่เข้าคลองบ้านม้า 2
(ไม่มี identity/bound/junction constraint ในทั้ง 03, 04, 05, 06); 04/05 ให้ทิศทางและภาระแต่ "ไม่ยืนยันปริมาณ" ตาม claim_boundary ของตัวเอง —
ช่องว่างนี้จึงเป็น object ใหม่จริง (Toledo check = NOT_REGISTERED) และเล็กพอที่จะเป็น delta 5 ข้อบน parent เดิม.

---

## 3. Calibration protocol — วัดพารามิเตอร์จากเหตุการณ์จริง (world-class แต่ซื่อสัตย์)

**กติการ่วม**: (1) ทุกตัวประมาณ (estimator) เป็น *ขั้นตอน* บน object ที่ขึ้นทะเบียนแล้ว — การ "แก้สมการ 03 หา c" คือการจัดรูป (rearrangement)
ของ 03 ไม่ใช่สมการใหม่ แต่ต้องอ้าง 03 ทุกครั้ง; (2) ผลเป็น **ช่วง [min, max] ต่อเหตุการณ์ + worst case ก่อน** ไม่ใช่ค่าเฉลี่ย (06 v6.1 multi_model
discipline ใช้กับ *พารามิเตอร์* ด้วย); (3) จำนวนเหตุการณ์ขั้นต่ำ **ประกาศล่วงหน้าที่นี่** (INSTINCT convention, founder ตัดสิน D4) ไม่เลือกหลังเห็นผล;
(4) บันทึกแบบ append-only (version list) ใน `calibration` block ตาม 06 `calibration_procedure`; (5) ข้อมูลอ่านจาก ledger ที่มีอยู่แล้ว —
`raw/live/<source>/<ts>`, `data/observations.sqlite` (`observations`/`readout_log`/`contradictions`/`experience_log`), `raw/backtest/*`,
`raw/backtests/*.jsonl`, `raw/tier_runs/*.json` — ไม่มี ledger ใหม่นอกจาก `event_ledger` ที่ `T7_T0_DATA_PLAN.md` §2 เสนอไว้แล้ว.

| พารามิเตอร์ | ข้อมูลที่ต้องมี (ทั้งหมด MEASURED ในหน้าต่างเดียวกัน) | ตัวประมาณ (ขั้นตอน) | เหตุการณ์ขั้นต่ำ (ประกาศ) | ตัวหักล้าง (falsifier) | OPEN จนกว่า |
|---|---|---|---|---|---|
| **c** (runoff coefficient) ต่อ sub-polder/บึง | ฝนรายชั่วโมงที่เกจในพื้นที่; ระดับบึง `h(k)` + stage–storage `S(h)`; `Q_out` = pumps_on × rated × η ต่อชั่วโมง; `Q_in` ทุก edge ที่ประกาศ (หรือ ABSENT ⇒ ข้ามชั่วโมงนั้น) | จัดรูป 03 ต่อชั่วโมงที่ *ปิดงบได้* (ทุก term MEASURED): `c_k = (S(k+1) − S(k) − Q_in·τ + Q_out·τ) / (P(k)·A)`; รายงาน `[min c_k, max c_k]` ต่อเหตุการณ์ และ **ช่วงรวมข้ามเหตุการณ์ = ครอบทุกช่วง** (ไม่เฉลี่ย); ถ้า `P(k)=0` ⇒ ไม่นิยาม (ใช้ชั่วโมงนั้นวัด η แทน) | **5 เหตุการณ์ฝน** ที่ปิดงบได้ ≥ 6 ชม. ต่อเหตุการณ์ | `c_k` ∉ [0, 1] ในเหตุการณ์ใด ⇒ 03 REFUSED NEGATIVE_STORAGE-class; สงสัยตามลำดับ A → S(h) → η → เกจ; ถ้า ≥ 3 unit ที่ input ครบยังนอกช่วง ⇒ scalar-c ของ 03 ใช้ไม่ได้กับ class นั้น (ต้อง PROPOSAL ใหม่ ไม่ปรับค่าเงียบ) | stage–storage ของบึง (0/57) + A polygon; ตอนนี้ c = `[0.5, 1]` bound pair ตาม 06 (ไม่ใช่ค่าเดียว) |
| **A** (พื้นที่รับน้ำ) ต่อ unit | polygon ทางการ: 38 sub-polder (ตร.กม. มี, geometry ขาด), DWR sub-basin 359 (licence OPEN — ใช้ภายใน), เขตหมู่บ้าน (นิติบุคคล) | **ไม่ประมาณ — ประกาศจาก polygon** (tag ตามแหล่ง); cross-check: ผลคูณ `c·A` จากการจัดรูป 03 ต้องให้ `c ∈ [0,1]` เมื่อใช้ A ที่ประกาศ | 1 polygon ทางการ + **3 เหตุการณ์** cross-check | implied `c > 1` ที่ A ที่ประกาศ ⇒ A เล็กเกิน/มีน้ำเข้าจาก edge ที่ไม่ประกาศ (UNDECLARED_EDGE candidate) | ขอ geometry 38 sub-polder จาก สนน. หรือ digitise แผนที่ ค (garbled, ต้อง render หน้า 126–163) |
| **η** (effective / rated) ต่อสถานีสูบ | ช่วง "สูบอย่างเดียว": ฝน = 0, ประตูเข้าปิด/`Q_in` ABSENT-ไม่นับ, pumps_on คงที่ ≥ 1 ชม.; `S(h)` ของบึงหน้าสถานี | `η = (S(k) − S(k+1)) / (Σ_p rated_p · pumps_on · τ)` ต่อช่วง; ช่วง [min, max] ต่อสถานี; แถว "ขัดข้อง" ⇒ η **ไม่นิยาม** (REFUSED ไม่ใช่ 0) | **3 ช่วง drawdown** ต่อสถานี (ต่างวัน) | `η > 1.05` ⇒ rated ที่ประกาศต่ำเกินหรือมีทางออกอื่น ⇒ re-tag rated (ตาม 06 falsifier "observed flow exceeding declared Q_cap") ไม่ปัดขึ้นเงียบ | stage–storage; สถานะ pumps_on ของสถานีนอกสายแสนแสบ |
| **cap_e** (conveyance limit) ต่อ edge | flow telemetry ที่ปลาย edge (แผนระบุ FW 55 สถานี — ไม่เผยแพร่, TODO #41) **หรือ** เหตุการณ์ที่ 07 อ่าน F3 (blocked: `Δ_e > ε` แต่ปลายไม่ลด) | ถ้ามี flow: `cap_e ≥ max sustained Q_e` ที่เคยวัด (ขอบล่างของ cap); ถ้าไม่มี: **ไม่ประมาณ** — บันทึกเฉพาะ "F3 observed at Δ_e = x" เป็น *หลักฐานเชิงคุณภาพ*ว่า edge อิ่มตัว; **ห้าม** ใช้ Manning/Chezy จากมิติคลอง (ไม่อยู่ใน Toledo) | 3 เหตุการณ์ที่มี flow วัดจริง | ค่าที่วัดเกิน cap_e ที่ประกาศ ⇒ re-tag cap_e | flow telemetry (0 วันนี้) — **cap_e OPEN ทั้งกราฟ** จนกว่าจะมี; 09 (ii) จึงเป็น CAPACITY_UNDECLARED เกือบทุก edge ตอนนี้ (ซื่อสัตย์) |
| **τ_e** (travel time) ต่อ edge — รวม lag หนองจอก→พระโขนง | อนุกรมระดับ 2 ปลาย (หรือหลายสถานีตามสาย) ที่ cadence ≤ 30 นาที บน datum เดียวกัน (หรือใช้แต่ *เครื่องหมายแนวโน้ม* ซึ่งไม่ต้องการ datum เดียวกัน) | **Recession/rise-front method**: ต่อสถานี s หา tick แรก `t_flip(s)` ที่ PROP-FLOOD-01 เปลี่ยนจาก FLAT/RISING → FALLING (หรือ FLAT/FALLING → RISING) และ *คงอยู่* ตามหน้าต่าง persistence ของ `flow_stall.py`; `lag(u→v) := t_flip(v) − t_flip(u)` (retained difference ของ tick index — instance ของ δ_R, ไม่มีเลขใหม่); ระบุทิศทางของ front แยกกัน: **drawdown front** (ปลายน้ำลดก่อน ⇒ แพร่ย้อนขึ้นต้นน้ำ) กับ **flood-wave front** (ต้นน้ำขึ้นก่อน) — เก็บเป็นสองตารางไม่รวม | **3 recession + 3 rise** ต่อคู่สถานี | เครื่องหมาย lag สลับกันข้ามเหตุการณ์ หรือ `|lag| < cadence` ⇒ UNRESOLVED (ไม่ประกาศ τ_e); lag ที่ประกาศแล้วทำให้ 09 (i) ปิดงบไม่ได้ ⇒ ถอน τ_e | rise event ที่จับได้ตั้งแต่ต้น (25 ก.ย. ค่าแรกสุด 13:05Z ทุกสถานีสูงแล้ว — ไม่มี rise flip ในคลัง) |
| **gravity_threshold / g(k)** ต่อ outfall | ระดับด้านนอก (แม่น้ำ/น้ำทะเล) + `gate_opening_m` หรือ pumps_on ที่ outfall | อ่านค่าประกาศจาก 406 แถว (แผน ก ข ค/เตือน/วิกฤติ ด้านนอก) เป็นค่าตั้งต้น (VERIFIED-declared); *วัด*: ระดับด้านนอกที่ `gate_opening_m → 0` / pumps_on เริ่ม > 0 ต่อรอบน้ำขึ้น | **5 รอบน้ำขึ้น** | ประตูปิดที่ระดับต่ำกว่าค่าประกาศซ้ำ ⇒ ค่าประกาศ stale ⇒ OPEN | `gate_opening_m` มีบางสถานี; ตารางน้ำขึ้นลง T36 ยังไม่ ingest (TODO #60) |
| **point-vs-cell ratio** (เตือน ไม่ใช่ตัวแก้) | ฝนเกจ 24 ชม. vs ค่าเซลล์ต่อโมเดล ต่อ horizon | อัตราส่วนต่อ (วัน, โมเดล) — เก็บทุกค่า ไม่เฉลี่ย; ใช้เป็น `disagreement_flag` เท่านั้น (06 v6.1) | 10 วันฝน | — (ไม่ใช่สมการ จึงไม่มีสิ่งให้หักล้าง นอกจากการอ้างว่าเป็น "ตัวคูณแก้") | มี 1 คู่ (13–53 vs 203 mm) |
| **band edges / promoter thresholds** ต่อ unit | ground-truth events + tier trajectory | **06 `calibration_procedure` ตรงตัว**: grid ที่ประกาศล่วงหน้า (S_H {0.1…2.0}, rain {40…150}), maximise hits ภายใต้ FA ceiling ที่ประกาศ, บันทึก `calibrated: yes(n, hit, FA, median_lead)` | ตาม 06 (ยังไม่มี unit ใด calibrated) | ตาม 06 | founder อนุมัติ grid/FA ceiling ต่อ unit (D3) |

### 3.1 การทดลอง τ_e ครั้งแรก — recession front ที่เห็นจริงคืนนี้ (MEASURED, จาก `statement_contradictions_2026-09-27.yaml` + sqlite)

หน้าต่าง 2026-09-27 07:00–13:00Z (14 ค่าอ่านต่อสถานี, cadence ≈ 25 นาที), ε ตาม 04 = 0.02 ม., หน้าต่าง persistence ตาม `flow_stall.py` ε = 0.03 ม.:

| สถานี (ต้นน้ำ → ปลายน้ำ ตามสาย) | ค่าแรก → ค่าท้าย (ม.) | max − min | อ่านตาม 01 | `t_flip` (FALLING แบบคงอยู่) |
|---|---|---|---|---|
| WL.SSB.12 หนองจอก | 1.22 → 1.23 | 0.02 | FLAT | ยังไม่เกิด (≥ 13:00Z) |
| WL.SSB.10 ปตร.มีนบุรี | 1.02 → 1.01 | 0.01 | FLAT | ยังไม่เกิด |
| WL.SSB.09 ปตร.บางชัน | 0.95 → 0.94 | 0.01 | FLAT | ยังไม่เกิด |
| WL.SSB.07 บางกะปิ | 0.40 → 0.40 | 0.00 | FLAT | ยังไม่เกิด |
| WL.SSB.06 เจ้าคุณสิงห์ | 0.52 → 0.47 | 0.06 | UNRESOLVED (สัญญาณรบกวน ±0.05 > ε_persist) | ไม่ตัดสิน |
| WL.SSB.04 คลองตัน | 0.32 → 0.26 | 0.06 | FALLING (Δ = −0.06 < −ε) | ภายในหน้าต่าง (≤ 07:00Z–13:00Z) |
| WL.SSB.03 อโศก | 0.34 → 0.23 | 0.11 | FALLING | ภายในหน้าต่าง |
| WL.SSB.01 โบ๊เบ๊ | −0.09 → −0.14 | 0.07 | FALLING | ภายในหน้าต่าง |
| WL.SSB.08 เสรีไทย 24 | — | — | **EXCLUDED (SUSPECT, §4.1)** | — |

**อ่านผล (MEASURED + INSTINCT ระบุชัด)**: front ที่เห็นเป็น **drawdown front จากปลายน้ำ** (01/03/04 ลดก่อน ขณะ 07/09/10/12 นิ่ง) —
สอดคล้องกับกลไก "ลดระดับที่จุดออกแล้วแพร่ย้อนขึ้น" (INSTINCT, ยังไม่ผูกกับปริมาณ) และ**ขัด**กับคำแถลงทางการ "แสนแสบเริ่มลด" สำหรับช่วง
บางกะปิ–หนองจอก (contradiction row เก็บไว้แล้ว, ไม่ตัดสิน). **ตัวเลขที่ได้จริงคืนนี้ = ขอบล่างของ lag เท่านั้น**: `lag(SSB.03 → SSB.07) ≥ 6 h`
ณ 13:00Z (MEASURED lower bound) — ไม่ใช่ค่า τ_e. ขั้นตอนต่อ (ไม่ต้องรอ): บันทึก `t_flip` ของ 07/09/10/12 เมื่อเกิด ลง `readout_log`
kind `recession_front` (แถวใหม่ต่อสถานีต่อ flip) แล้วคำนวณ lag matrix ต่อคู่; ทำซ้ำอีก 2 recession + จับ rise front ในเหตุการณ์ฝนถัดไป
ก่อนประกาศ τ_e ใด ๆ. **lag หนองจอก→พระโขนง** (flood-wave) ยัง **OPEN** — คลังไม่มี rise flip ที่จับได้ตั้งแต่ต้น และ WL.PKN.01 ไม่อยู่ในชุด
ที่ตรวจคืนนี้.

---

## 4. Data-quality layer — ก่อนตัวเลขใดจะเข้าสมการ

### 4.1 Anchor rule (เซนเซอร์เป็น anchor ได้ต่อเมื่อสอดคล้องกับเพื่อนบ้าน + สมการการไหล)

`neighbour_consistency_check()`/`SAENSAEB_NEIGHBOUR_ORDER` (`site/build_data.py`) + 04: สถานีเดี่ยวเป็น **SUSPECT** และ**ห้ามใช้เป็น anchor**
(สำหรับ 01/02/04/07/RULE-STALL/DIR และ 09) เมื่อ (a) ขัดกับเพื่อนบ้าน ≥ 2 สถานีบนสายเดียวกัน **และ/หรือ** (b) ขัดกับภาพการไหลที่ 03/04 บอก
(เช่น แกว่ง −0.67 ↔ +0.80 ม. ในไม่กี่ชั่วโมงขณะเพื่อนบ้านราบ). ค่ายัง**อยู่ในทะเบียน** (never prune) พร้อม `suspect: true` และแถว contradiction;
SUSPECT ⇒ coverage component ของโหนดนั้น = ABSENT (ไม่ใช่ present) จนกว่าจะพ้นเกณฑ์ ≥ 2 ชม. ต่อเนื่อง. กรณีจริง: WL.SSB.08 SUSPECT ตั้งแต่ค่าแรกสุด
(T−7h55m) ตลอดทุกจุดที่ตรวจ. **ทั่วไป**: ใช้ได้ทุกสาย/ทุกจังหวัดที่มีสถานี ≥ 3 บนสายเดียว (ต้องประกาศ `profile_order`); สาย 2 สถานี ⇒ ตรวจได้เฉพาะ (b).

### 4.2 Datum rule (`sources/units_datum_crosswalk.yaml`)

`never_mix_msl_and_local`: ห้ามลบ/รวมระดับ MSL (ม.รทก.) กับระดับ staff-gauge ท้องถิ่น ⇒ 04/05/09 REFUSED `DATUM_MISMATCH`; ระดับทุกค่าต้องพก
datum tag; `grid_cell_vs_gauge_not_equal`; `never_add_intensity_to_accumulation`; `never_sum_ensemble_members`. กรณีเปิด: WL.BMA.02 เตือน/วิกฤติ
2.14/2.68 ในระบบเรา vs +0.40/+0.50 ที่สถานีสูบคลองบ้านม้า 2 ในแผน ⇒ **OPEN datum** — จนกว่าจะยุติ 04 บนคู่ (WL.SMK.01, WL.BMA.02) ให้ได้เฉพาะ
*แนวโน้ม* (01) ไม่ให้ทิศทาง. ระดับพื้นดิน ≠ ระดับผิวน้ำ (`ground_m_msl` แยกจาก reading เสมอ).

### 4.3 Day-boundary rule

`always_convert_to_utc_before_windowing`: แปลงเป็น UTC ก่อนตัดหน้าต่าง 24 ชม.; ฝน TMD 07:00 ICT vs โมเดล 00:00 UTC ต่างกัน 7 ชม. — ห้ามเทียบ
"รายวัน" ตรง ๆ; `T0` ของเหตุการณ์ประกาศครั้งเดียว (ISO UTC) ไม่แก้ย้อนหลัง; `run_time` = เวลาที่ระบบ *รู้* ค่า ไม่ใช่เวลาที่เหตุการณ์เกิด (anti-leakage).

### 4.4 Contradiction ledger (เก็บ ไม่ resolve)

สามชั้นที่มีอยู่แล้ว: (1) `tools/reconcile.py` — สองแหล่ง สถานีเดียวกัน ต่างเวลา > 60 นาที หรือต่างค่า > 0.05 ม. ⇒ แถว `contradictions` (96 แถว
ณ วันนี้); (2) `statement_vs_gauge` (คำแถลง vs เกจ); (3) `document_vs_document` (49/155/173 พระโขนง). กติกาใน 09: `Q_e` ที่วัดได้ขัดเครื่องหมาย 04
⇒ แถวใหม่ class `flow_vs_direction`; งบน้ำไม่ปิดที่ junction ⇒ `junction_imbalance` — ทั้งคู่เก็บ ไม่ปรับค่าให้ปิด.

### 4.5 Coverage vector ต่อโหนด

ใช้ `cov6` ของ 06 (10 องค์ประกอบ × {present, inferred, absent}) ต่อ *unit* และขยายด้วย renaming เป็น **ต่อโหนด** โดยเพิ่มองค์ประกอบ edge:
`{h_self, h_neighbours(≥2), gate_state, pumps_state, rain_obs, rain_fcst, stage_storage, edge_flows(all incident), boundary_stage, community}`;
`confidence` = **min** ของ rung ทุกองค์ประกอบที่ inferred (07 `strength_min`) — ไม่เฉลี่ย; readout ทุกตัวต้องแสดง `tier · mode · coverage n/N`
คู่กันเสมอ (06 v4 consumer contract).

### 4.6 การแพร่ของ PARTIAL / REFUSED ในกราฟ (ตัดสินแล้ว, fail-closed)

- **REFUSED ที่โหนด u ต้นน้ำ** ⇒ ทุก edge ออกจาก u มี `Q_e = ABSENT` ⇒ ที่ปลายน้ำ v term `Q_in` จาก edge นั้น = ABSENT (ไม่ใช่ 0) ⇒ v เป็น **PARTIAL**
  ถ้า v มี anchor ของตัวเองอย่างน้อยหนึ่ง (ระดับ/ปั๊ม/ชุมชน) — รายงานพร้อมรายชื่อ edge ที่ ABSENT และเหตุผลต้นทาง (`upstream_refused: u, reason`);
  v **REFUSED เฉพาะเมื่อ input ทุกตัวของ v เอง ABSENT ด้วย** (กติกาเดียวกับ 07: REFUSED iff D=T=C=M=ABSENT). นี่คือ fail-closed (ไม่มีเลขถูกกุ)
  แต่ไม่ fail-silent (ปลายน้ำยังรายงานสิ่งที่ตัวเองอ่านได้).
- **ABSENT อาจถูกยกเป็น Inferred** ผ่าน RULE-STALL-01/RULE-DIR-01 เท่านั้น (07) โดยต้องระบุ anchor ids และ confidence = rung ต่ำสุด; inferred นับใน
  coverage ที่ rank ต่ำกว่า present; ห้าม inferred ป้อนเข้าการจัดรูปหา c/η (§3) — calibration ใช้ present เท่านั้น.
- **STALE** ⇒ นับเป็น ABSENT สำหรับการปิดงบ แต่แสดงค่า+อายุ; **SUSPECT** ⇒ ABSENT สำหรับ anchor ทุกกติกา.
- **ทิศทางแพร่ตาม edge ที่ประกาศเท่านั้น** — ไม่มีการแพร่ตามระยะทาง/พิกัด (ไม่ geocode/snap เงียบ ๆ, ตาม `CO_FORECAST_PROTOCOL` §6 ข้อ 6).
- **หน่วยที่ยังไม่ calibrate เริ่มที่ PARTIAL เสมอ** (06 §8) — FULL ประกาศได้เมื่อ input ครบตามนิยามและผ่าน backtest ของ unit นั้นเอง.

---

## 5. Validation — backtest ≥ 100 event-day, ตัวชี้วัดที่ไม่เฉลี่ย, ตัวหักล้างที่ปลดสมการได้

### 5.1 แคตตาล็อกเหตุการณ์ (มีแล้ว + เพิ่ม)

`tools/backtest/run_backtest.py: EVENTS` (MEASURED นับจากหน้าต่างวันที่): HATYAI 2553 (22 วัน, ท่วม 31 ต.ค.–3 พ.ย.), HATYAI 2565 (21 วัน,
หน้าต่างท่วม INSTINCT), HATYAI ไม่ท่วม 4 หน้าต่าง (40 วัน); NAN 2567 (17 + 10 ไม่ท่วม); CHIANGMAI 2567 สองพัลส์ (16 + 10); AYUTTHAYA_BANGBAN 2554
(31 + 10); BANGKOK_EAST 2554 (22) + 2569 (8) + ไม่ท่วม (10) ⇒ **≈ 217 unit-day** (ผ่าน ≥ 100). เพิ่มในรอบถัดไป: **Sammakorn 2569-09**
(7 วันจริง, `docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md`, ledger 24 แถว), **Hat Yai 2568 (พ.ย. 2568)** — ขณะนี้มีเฉพาะ
red-team ของบุคคลที่สาม (RELAYED, 10 claims: VERIFIED 1 เป๊ะ, RELAYED 5, CONTRADICTED 1, OPEN 3) และ *ไม่มี archive ของทีมเอง* → เป็น event-day
ได้ต่อเมื่อดึง X.44/X.90/X.173A/X.174 ย้อนหลัง พ.ย. 2568 จาก HII เข้า `raw/backtest/hii_history/` และประกาศ bank line ที่ verified ก่อน;
**Rangsit 2561** — การ์ดเป็นบทความบรรยาย *แผน* (RELAYED) ไม่มีอนุกรมเกจ ⇒ **ยังเป็น event-day ไม่ได้** (บันทึกตรง ๆ); **2554 กทม. ตะวันออก** มีอยู่แล้ว
(BANGKOK_EAST_2011). ทุกเหตุการณ์ต้องมี `T0_definition` ประกาศล่วงหน้า และแถว `event_ledger` อ่านเฉพาะ `run_time ≤ T0 − k`.

### 5.2 ตัวชี้วัด (respect "no averaging")

| ตัวชี้วัด | รูปแบบ | ห้าม |
|---|---|---|
| Lead time ต่อเหตุการณ์ ต่อ action_label | `T0 − run_time แรกที่ถึง label` (ชั่วโมง, ลบ = MISS) — ตาราง event × label | เฉลี่ยข้ามเหตุการณ์/unit |
| Tier trajectory ต่อเหตุการณ์ | รายชั่วโมง L0–L5/LR + mode + coverage n/N + scenario (worst/majority) — เส้นเดียวต่อเหตุการณ์ | รายงาน tier เดี่ยวไม่มี coverage |
| False-alarm ledger | หนึ่งแถวต่อ FA: (unit, วัน, tier, promoter/term ที่ยิง, scenario, สาเหตุที่วินิจฉัยได้) | อัตราเดียวข้าม unit |
| Hit / Miss / FA ต่อ unit | ตารางแยก unit (06 §8 ข้อ 7) | pool |
| Closure residual ต่อโหนด (03/09) | `r_b(k) = S(k+1) − [S(k) + …]` ต่อชั่วโมงที่ input ครบ; รายงาน `[min, max]` และจำนวนชั่วโมงที่ปิดได้/ทั้งหมด | ค่าเดียว |
| Contradiction count ต่อเหตุการณ์ | จำนวนแถว contradictions ใหม่ + class | resolve เพื่อลดจำนวน |
| Lag matrix (τ_e) | ต่อคู่สถานี ต่อเหตุการณ์ ต่อชนิด front | เฉลี่ยข้าม front ชนิดต่างกัน |

### 5.3 ตัวหักล้างที่ปลด (retire) สมการ/กติกา — ประกาศล่วงหน้า

1. **03 (งบน้ำ)**: residual `r_b` เกิน `ε_S` ที่ประกาศอย่างเป็นระบบเมื่อ input *ทุกตัว* MEASURED ใน ≥ 3 เหตุการณ์ ⇒ ลำดับสงสัย A → S(h) → η → เกจ;
   ถ้ายังคง ⇒ scalar-c ของ 03 ใช้ไม่ได้กับ class นั้น → PROPOSAL ใหม่ (ห้ามเพิ่ม term เงียบ ๆ).
2. **04/07**: edge จัดเป็น F1/F2 แล้วยืนยันภายหลังว่าไม่ระบาย (หรือ F3/F4 แล้วพบไหลอิสระ) ⇒ ปลดตาราง case ของ 07 สำหรับชุด input นั้น (falsifier ของ 07 เอง);
   RULE-STALL/DIR ที่ inferred แล้วค่าวัดภายหลังขัด ⇒ ปลด rule นั้นสำหรับ run นั้น.
3. **06**: OK (< 0.5) ที่หลาย unit ท่วมจริง / CRITICAL (> 1) ไม่ท่วม ⇒ ปลดการสอบเทียบ tier (ไม่ใช่เลขคณิต); `Q_o,now` เกิน `Q_cap,o` ⇒ re-tag ค่าคงที่.
4. **09 candidate**: junction ที่ทุก edge วัดได้ยังไม่ปิดงบ > `ε_Q` ใน ≥ 3 เหตุการณ์ ⇒ ปลด (iv) สำหรับ class นั้น (สงสัย edge ที่ไม่ประกาศก่อน);
   `Q_e` วัดได้ขัดเครื่องหมาย 04 ซ้ำ ⇒ ปลดคู่เกจนั้นจาก (iii) (datum/เกจต้องสงสัยก่อน).
5. **02**: `T_k` ให้ lead ผิดเครื่องหมายซ้ำที่สถานีเดียวกัน ⇒ ปลด θ ที่ประกาศ (เกณฑ์ stale) ก่อนปลดสมการ.
6. **anchor rule**: สถานีที่ตั้ง SUSPECT แล้วภายหลังพบคำอธิบายเชิงกลไก (ประตูเฉพาะจุดเปิด-ปิดเร็วจริง) ⇒ คืนสถานะ anchor + บันทึกว่ากติกา (a)/(b) ยิงผิดเพราะอะไร.

---

## 6. Roadmap — จากคืนนี้ถึงชุดสมการเต็ม (เรียงลำดับ, ไฟล์/ID ที่แต่ละขั้นให้)

| ขั้น | งาน | ผลลัพธ์ที่เป็นไฟล์/ID | ต้องมีก่อน |
|---|---|---|---|
| R1 | ยืนยันสถานะ Toledo ของ 03 (PR #60) และ **04 (PR #61)** — 09 อ้าง 04 เป็น parent จึงต้องรู้รูปที่ลงทะเบียนจริง | บันทึกสถานะใน `AGENTS.md` §8 (committer) | — |
| R2 | อ่าน **08 draft** (กระบวนการคู่ขนาน) เมื่อไฟล์มา; ตัด term ที่ซ้อน (storage deficit/drawdown) ออกจากร่าง 09 | หมายเหตุ "see 08 draft" ใน §2.3 ที่นี่ + occurrence row | 08 draft มีอยู่ |
| R3 | เปิด **PROP-FLOOD-09 PROPOSAL** ใน Toledo หลัง founder D1: statement §2.3, parents, refusal codes, Coq skeleton (total readout, refusal precedence) | `registry/proposals/flood_network_ledger.json`, `docs/proposals/PROP-FLOOD-09.md`, `coq/canonical/PROP_FLOOD_09_network_ledger.v` (ใน Toledo repo, ผ่าน PR + `CLAY_GOVERNANCE_ACK.json`) | R1, R2, D1 |
| R4 | **ประกาศกราฟตะวันออกทั้งสาย** หนองจอก→แสนแสบ/ประเวศ→พระโขนง/อุโมงค์→เจ้าพระยา และแขนหกวา→คลอง 13→บางปะกง จากทะเบียนที่มี (38 sub-polder, 451 อาคาร, 269 ช่วง, 11 outfall, draft 19 node/14 edge) — ทุก edge พก `kind`, `cap_e: OPEN`, `tau_e: OPEN`, `controller`, `backwater_risk: OPEN`, `datum` | `site/inputs/network/east_network.yaml` (ใหม่) + `tests/test_network_declaration.py` (ทุก node id resolve ใน KG/asset; ไม่มี fuzzy) | D5 (granularity) |
| R5 | ledger kinds ใหม่ใน `readout_log` (ไม่แก้ schema — ใช้คอลัมน์ `kind/key/extra_json` เดิม): `edge_flow`, `node_balance`, `closure_residual`, `recession_front`, `junction_imbalance`; `event_ledger` ตาม `T7_T0_DATA_PLAN.md` §2 | `tools/network/ledger_kinds.py` (ค่าคงที่+writer) | — |
| R6 | โมดูล 09 (additive, ไม่แก้ของเดิม): ประกอบ `water_balance.step()` + `canal_graph.edge_direction()` + `prop_flood_06_v5/v6` verbatim; PARTIAL/REFUSED propagation §4.6; **ห้ามใช้บนหน้าเว็บสาธารณะ** จนกว่า 09 ขึ้นทะเบียน (ใช้ใน backtest/ทดลองเท่านั้น, ป้าย PROPOSAL) | `tools/network/network_ledger.py`, `tests/test_network_ledger.py` (synthetic 4-node + junction + outfall) | R3 (หรือรันแบบ PROPOSAL-only) |
| R7 | โมดูลสอบเทียบ §3: `recession_front.py` (t_flip/lag matrix), `c_inversion.py` (จัดรูป 03, present-only), `eta_drawdown.py`, `anchor_rule.py` (generalise `neighbour_consistency_check` ให้ทุกสายที่มี profile_order) | `tools/calib/*.py`, `tests/test_calib_*.py`, ผลลง `raw/calibration/<unit>/<UTC>.json` (append-only) | R5 |
| R8 | ข้อมูลที่ต้องได้เพิ่ม (ไม่มีทางลัด): stage–storage บึงสัมมากร (นิติบุคคล/สนน.), geometry 38 sub-polder (render แผนที่ ค p126–163 หรือขอ GIS), FW flow telemetry probe (TODO #41, 1 request/URL), TMD/ONWR warning archive + raw forecast ต่อ run (T7 §1b), ตารางน้ำขึ้นลง T36 (TODO #60), HII history พ.ย. 2568 สำหรับ Hat Yai | `sources/registry.yaml` แถวใหม่ + collector + fixture; `docs/knowledge/card_*` ต่อเอกสาร | ตามลำดับความสำคัญ R8a stage–storage > R8b FW > R8c archive |
| R9 | backtest v3: แคตตาล็อก ≥ 100 event-day + Sammakorn 2569 + Hat Yai 2568 (เมื่อมี archive); ตัวชี้วัด §5.2 ต่อเหตุการณ์; anti-leakage บน `event_ledger` | `tools/backtest/run_backtest_v3.py`, `docs/BACKTEST_PROP_FLOOD_06_v3.md`, `raw/backtest/results_v3.jsonl` | R5–R7 |
| R10 | Maker ≠ checker: review อิสระของ 09 statement + โมดูล + backtest ก่อน PR/publish ใด ๆ (independent reviewer, maker ≠ checker; leak scan) | `docs/knowledge/REVIEW_PROP_FLOOD_09_r1.md` | R3, R6, R9 |

**คำตัดสินที่ต้องขอจาก founder**: **D1** เปิด PROP-FLOOD-09 เป็น PROPOSAL ใน Toledo ตาม §2.3 หรือ HOLD; **D2** ประกาศ `T0_definition` convention
สำหรับ unit อื่นนอกสัมมากร/ราม 53; **D3** grid + FA ceiling ต่อ unit สำหรับ 06 `calibration_procedure`; **D4** จำนวนเหตุการณ์ขั้นต่ำ §3 (5/3/3/3+3/5/10)
รับเป็น declared convention; **D5** granularity ของโหนด กทม. = 38 sub-polder (แผน) ไม่ใช่ 50 เขต; **D6** ใช้ polygon DWR ภายในต่อไปหรือหยุดจน licence ยุติ;
**D7** ยืนยันกรรมสิทธิ์/ผู้ปฏิบัติการปั๊ม ST.SPS.01–04 กับนิติบุคคล/สนน. (C1 ค้างอยู่).

### TODOLIST (ต่อจาก `docs/knowledge/FOUNDER_TASKS_2026-09-27.md`, เริ่ม #91, รูปแบบ 5 คอลัมน์เดิม — **เดิมเขียนเป็น #70-84 ในไฟล์นี้ ก่อนพบว่าชนกับ #80-84 ที่มีอยู่แล้วใน FOUNDER_TASKS จากการ์ด urban-event/zoom review; renumber เป็น #91-105 ที่นี่เท่านั้น เนื้อหาไม่เปลี่ยน**)

| # | Mismatch | Fix | Owner | Prio |
|---|---|---|---|---|
| 91 | ไม่มี object ใดใน 03/04/05/06 กล่าวถึง edge-flow identity / capacity bound / junction constraint / outfall boundary; Toledo check = NOT_REGISTERED | founder D1 → เปิด PROP-FLOOD-09 PROPOSAL ตาม §2.3 (หลัง 04 PR #61 ลงและอ่าน 08 draft) — ห้ามใช้ในโค้ด/หน้าเว็บก่อนขึ้นทะเบียน | founder+committer | high |
| 92 | กราฟตะวันออกทั้งสายยังกระจายใน 4 ไฟล์ (east_chain 18 node, draft 19/14, ledger 11 outfall, แผน 451/269/38) ไม่มี declaration เดียว | สร้าง `site/inputs/network/east_network.yaml` (R4) + test id-resolve; ทุก edge พก kind/cap_e/tau_e/controller/backwater_risk/datum (OPEN ได้ ห้ามเดา) | committer | high |
| 93 | `readout_log` ไม่มี kind สำหรับ edge_flow/closure_residual/recession_front → lag/closure ที่วัดคืนนี้จะหายไป | เพิ่ม kinds (R5) และเขียนแถว `recession_front` ทันทีที่ 07/09/10/12 flip | committer | high |
| 94 | τ_e ทุก edge = 0 วัดจริง; คืนนี้ได้แค่ขอบล่าง lag(SSB.03→SSB.07) ≥ 6 h | `tools/calib/recession_front.py` (R7) รันทุก run; ประกาศ τ_e ต่อคู่หลัง 3 recession + 3 rise เท่านั้น | committer | high |
| 95 | stage–storage ของบึง 0/57 ⇒ c, η, S(0) วัดไม่ได้เลย (03 REFUSED ทุกโหนดบึง) | ขอ curve/แบบบึงสัมมากรจากนิติบุคคล + สนน. (บ่อสูบ/ปตร. ที่ กทม. สร้างตาม p83); ระหว่างรอ: บันทึกระดับ WL.SMK.01 ต่อเนื่องเพื่อใช้เมื่อได้ curve | founder+committer | high |
| 96 | conveyance capacity 0/269 ช่วงคลอง; ไม่มี flow telemetry แม้แผนระบุ FW 55 สถานี | probe endpoint FW (TODO #41, 1 request/URL/run); ถ้าไม่มี บันทึก "มีเซ็นเซอร์ ไม่เผยแพร่" และคง `cap_e: OPEN` (ห้าม Manning) | committer | high |
| 97 | c_U OPEN 6/6 unit; A_U เป็น radius INSTINCT 5/6 | R8 geometry 38 sub-polder + `c_inversion.py` present-only หลังมี stage–storage; ประกาศ min events (D4) | committer | medium |
| 98 | สถานะประตูทางการ 0/451 (inferred เท่านั้น) ⇒ 05a/09 (ii) ทำงานได้เฉพาะ `gate_opening_m` บางสถานี | ลงทะเบียน `g_c` จาก `bma_watermap.gate_opening_m` เป็น declared state (0 = CLOSED, >0 = OPEN, tag MEASURED) เฉพาะสถานีที่มีฟิลด์; ที่เหลือ CONTROL_STATE_MISSING | committer | medium |
| 99 | Hat Yai 2568 ยังเป็น RELAYED red-team ล้วน (ไม่มี archive ทีมเอง, X.174 ไม่รู้จัก, bank line X.44 ว่าง) ⇒ ยังเข้าแคตตาล็อก ≥100 event-day ไม่ได้ | ดึง HII history X.44/X.90/X.173A/X.174 พ.ย. 2568 → `raw/backtest/hii_history/`; ประกาศ bank line จากเอกสาร RID ก่อนใช้ | committer | medium |
| 100 | Rangsit 2561 มีแค่การ์ดบรรยายแผน — ไม่มีอนุกรมเกจ | หาเกจ RID/ปทุมธานี (คลองรังสิต/ปตร.จุฬาลงกรณ์) ปี 2554–2561; ถ้าไม่มี บันทึกว่า "ไม่เป็น event-day" ตรง ๆ | committer | low |
| 101 | PARTIAL/REFUSED propagation §4.6 ยังไม่มีในโค้ดใด (flow_stall/layer0 ทำระดับ chain/unit ไม่ใช่กราฟ) | implement ใน `network_ledger.py` (R6) + test "upstream REFUSED ⇒ downstream PARTIAL with anchor, REFUSED iff all own inputs absent" | committer | medium |
| 102 | anchor rule ผูกกับ `SAENSAEB_NEIGHBOUR_ORDER` สายเดียว | generalise เป็น `tools/calib/anchor_rule.py` อ่าน `profile_order` จาก network yaml; ใช้ได้ทุกสายที่มี ≥3 สถานี | committer | medium |
| 103 | datum ต่อสถานีส่วนใหญ่ OPEN (WL.BMA.02 2.14 vs +0.40) ⇒ 04 บนคู่ SMK.01/BMA.02 REFUSED | เติม `datums` ใน `units_datum_crosswalk.yaml` จาก `bma_station_detail` (left/right/bed bank ม.รทก.) ทีละสถานี (1 request/run) | committer | medium |
| 104 | ตารางน้ำขึ้นลง T36 (12×31) ยังไม่ ingest ⇒ `gravity_threshold`/g(k) ไม่มี boundary stage ล่วงหน้า | ingest T36 เป็น boundary series (RELAYED-กรมอุทกศาสตร์) + cross-check `dds_tide_pdf` (TODO #60) | committer | medium |
| 105 | ไม่มี review อิสระของ §2.3/§4.6 (maker=checker) | reviewer คนละ agent อ่าน statement 09 เทียบ 03/04/05/06 อีกครั้ง + leak scan ก่อน PR (R10) | reviewer | high |

---

## 7. Boundary statement — สิ่งที่วิธีนี้ *ตั้งใจไม่ทำ* และทำไมนั่นคือทางเลือกระดับโลกสำหรับระบบ readout-first

วิธีนี้**ไม่ทำ**แบบจำลองอุทกพลศาสตร์ 2 มิติ ไม่แก้สมการ Saint-Venant/Navier–Stokes ไม่ใช้ rating curve หรือสูตร Manning จากมิติคลอง ไม่ใส่ค่า
c/η/τ_e/cap_e ที่ "สมเหตุสมผล" เข้าไปเพื่อให้ตัวเลขออก และไม่ take limit ใด ๆ (τ→0, พื้นที่→จุด) — ทุกอย่างเป็น tick จำกัด τ บน ℚ กับ object ที่
ขึ้นทะเบียนแล้ว. เหตุผลไม่ใช่ว่าแบบจำลองต่อเนื่องไร้ค่า แต่เพราะ**ข้อมูลที่ระบบนี้อ่านได้จริง**คือระดับน้ำที่ 2 ทศนิยมทุก 15–30 นาที จากสถานีที่ยังไม่รู้ datum
ครบ, สถานะประตูที่ยังไม่เผยแพร่, ปั๊มที่รายงาน "ขัดข้อง" 39/39 แถว, ความจุคลองที่แผนทางการเองไม่ระบุ, และ flow telemetry ที่มีเซ็นเซอร์แต่ไม่เผยแพร่ —
แบบจำลองต่อเนื่องบน input ชุดนี้จะให้ตัวเลขที่ *ดูแม่น* แต่พารามิเตอร์ครึ่งหนึ่งถูกกุขึ้น และผู้อ่านแยกไม่ได้ว่าส่วนไหนวัด ส่วนไหนสมมติ. ระบบ readout-first
เลือกกลับด้าน: ทุกตัวเลขบนหน้ากระดาษต้องสาวกลับไปถึงค่าอ่านจริง + object ที่อ้างได้ + แท็ก และเมื่อสาวไม่ถึงต้องออกมาเป็น PARTIAL/REFUSED ที่บอกว่า
ขาดอะไร — "ระดับโลก" ในที่นี้จึงวัดจาก *ความสามารถบอกว่าตัวเองไม่รู้อะไร* (coverage n/N, contradiction ledger, falsifier ที่ประกาศก่อน) ไม่ใช่จาก
ความละเอียดของกริด.

ผลข้างเคียงที่จงใจรับ: (1) ระบบนี้จะ **ไม่ให้ระดับน้ำที่หน้าบ้านเป็นเซนติเมตร** จากการคำนวณ — ให้ได้เฉพาะระดับที่เกจอ่านจริง, แนวโน้ม, ทิศทางบน edge ที่มีเกจ
2 ปลาย, เวลาถึงเกณฑ์เมื่อแนวโน้มขึ้นจริง, และงบน้ำ/ภาระ/ความสามารถรับมือระดับโหนดเมื่อ input ปิดได้; (2) พารามิเตอร์ทุกตัวได้มาจากเหตุการณ์จริงตาม §3
เท่านั้น — ช้ากว่าการใส่ค่าจากตำรา แต่ทุกค่ามีจำนวนเหตุการณ์ ช่วง [min, max] และตัวหักล้างติดมาด้วย; (3) ความชอบธรรมของชุดสมการมาจากการยืนอยู่ได้ต่อหน้า
เหตุการณ์จริง ≥ 100 event-day (หาดใหญ่ 2553/2565/2568, น่าน 2567, เชียงใหม่ 2567, อยุธยา 2554, กทม. 2554/2569, สัมมากร 2569) โดยรายงาน
ความล้มเหลวทุกครั้งเปิดเผย (เช่น achieved lead −9h ของสัมมากร, X.44 ไม่เคยเตือนทันที่หาดใหญ่) — ไม่ใช่จากใครรับรอง. นี่คือสิ่งที่ทำให้วิธีเดียวกัน
ใช้ได้กับทุก lat/lon ในประเทศ: มันไม่ต้องการแบบจำลองเฉพาะพื้นที่ ต้องการเพียงทะเบียน object ที่ประกาศได้ + เกจที่อ่านได้ + ความซื่อสัตย์ที่จะพูดว่า
"ยังไม่มี".

---

*ไฟล์นี้ไม่มีชื่อบุคคล ไม่มี path เครื่อง ไม่มีชื่อ AI/vendor; path ทั้งหมดเป็น path ภายใน repo หรือ repo Toledo.*
