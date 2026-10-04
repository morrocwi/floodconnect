# การ์ด: Urban Flood Event Ground-Truth Ledger (implementation, 2026-09-27)

**สถานะไฟล์นี้**: เอกสารประกอบ ledger ใหม่ 3 ไฟล์ (schema+data YAML, tool, tests) — งาน write-new-files-only
(อ่าน `data/observations.sqlite` แบบ read-only, ไม่แก้ไฟล์ tracked อื่น, ไม่ commit, ไม่ build, ไม่มี network
request). สืบเนื่องจาก `docs/knowledge/card_thirdparty_urban_event_layer_and_zoom_2026-09-27.md` §2.1 (GAP
เดียวที่การ์ดรีวิวคืนนั้นพบจริง) และ TODOLIST #50/#81 (`FOUNDER_TASKS_2026-09-27.md`).

---

## 1. Ledger นี้มีไว้ทำอะไร

`data/observations.sqlite`'s `observations`/`contradictions` เดิม เก็บ**ค่าตัวเลขจากเซนเซอร์** (ระดับน้ำ,
ความสูงน้ำบนถนน ฯลฯ) ส่วน `readout_log` เก็บ**tier/mode ต่อ run**. ทั้งสองอันไม่มี field ที่ตอบคำถามง่ายๆ
ตรงๆ ว่า **"เมืองท่วมจริงหรือยัง (สังเกตได้)"** เป็น binary event ต่อหน่วย/โซน — และแยกให้ชัดจาก
**"หน่วยงานประกาศภัยพิบัติหรือยัง"** (ข้อเท็จจริงเชิงกฎ/บริหาร ที่**ไม่เท่ากับ**สิ่งที่สังเกตได้ตรง) เพราะสอง
อย่างนี้เกิดคนละเวลากันเสมอ (ดู `bangkok_citywide_disaster_declared_2026-09-27` — ประกาศ 27 ก.ย. ล่ากว่า
road-telemetry onset จริง ~1 วัน 11 ชม.)

Ledger นี้ตอบคำถามต่อไปนี้ได้โดยตรง (ไม่ต้อง query ข้าม `observations`/`readout_log` เอง):

- **hit / miss / false-alarm / correct-negative ต่อ horizon**: เทียบ `warnings[].issued_at` +
  `warnings[].scope` กับ `t_onset_observed` + `urban_flood_observed` ของ event เดียวกัน
- **lead time ต่อคำเตือน**: `warnings[].lead_time_h` — คำนวณแยกต่อแถว **ไม่เฉลี่ยข้ามคำเตือน** (กฎ
  `CO_FORECAST_PROTOCOL.md` §5 ข้อ 7 — ห้าม average ข้ามหน่วยจนซ่อนหน่วยที่แย่)
- **warning_scope**: `regional_class` (คำเตือนระดับภูมิภาค/หมวดฝนของ TMD) vs `node_specific` (สัญญาณที่
  ระบบนี้เองรู้ค่าจริงต่อหน่วย) — บังคับต่อแถว เพื่อกันการปนสเกลที่การ์ดรีวิวเตือนไว้ (TODO #81/#84: 107ชม.
  ของ TMD ≠ achieved lead ของสัมมากรที่แท้จริง (−9ชม., MISS))

---

## 2. Schema (สรุป — ดูฟิลด์เต็มใน `sources/urban_flood_event_ledger.yaml`'s `fields:` block)

หนึ่งแถว (`events[]` item) = หนึ่ง event, append-only, ไม่เขียนทับ:

```
event_id, unit_scope (city|district|node), unit,
t_onset_observed, t_onset_official,
evidence: [{class, source, detail/value, observed_at_utc, tag}],
urban_flood_observed (true|false|UNCERTAIN),
official_disaster_declared (true|false|OPEN) + declaring_agency,
warnings: [{issuer, issued_at, scope: regional_class|node_specific, text, lead_time_h,
            lead_time_note, tag}],
notes, contradictions: [{description, tag}],
tag  # ต่อแถวทั้งบน event และบน evidence/warning sub-row ทุกอัน
```

`evidence[].class` ∈ `road_telemetry | canal_overbank | evacuation_shelter |
community_reports_consistent | media | satellite` ตามที่การ์ดรีวิวเสนอ §2.1 ทุกตัว.

---

## 3. กฎตัดสิน "เกิดน้ำท่วมเมืองจริง" จากข้อมูลถนน (`decision_rule`)

**เลือกใช้ (INSTINCT — รอ founder ปรับ)**: `threshold_cm=10, min_roads=3, window_hours=6` —
`urban_flood_observed=true` เมื่อมี **≥3 ถนนต่างจุด** ในโซนถนนเดียวกันของ BMA (ส่วนกลางของ station_code
เช่น `FL.BKP.04` → โซน `BKP`) รายงานค่า **≥10 ซม.** ภายใน **6 ชม.**ของกันและกัน (chain-cluster).

**ทางเลือกอื่น (คำนวณจาก DB จริงทั้งหมด, ไม่ใช่ประมาณ)** — ดู `decision_rule.alternatives_matrix` เต็มใน
YAML:

| threshold_cm | min_roads | window_hours | total events (2026) |
|---|---|---|---|
| 10 | 2 | 6 | 32 |
| **10** | **3** | **6** | **25 (เลือก)** |
| 10 | 5 | 6 | 13 |
| 20 | 2 | 6 | 23 |
| 20 | 3 | 6 | 16 |
| 20 | 5 | 6 | 11 |
| 30 | 2 | 6 | 4 |
| 30 | 3/5 | 6 | 0 |

เหตุผลที่เลือก min_roads=3/threshold=10cm: ให้จำนวน event ที่ดูสมเหตุสมผล ไม่ยุบเหลือเกือบศูนย์ (min_roads=5)
และไม่ระเบิดเป็น noise ระดับถนนเดียว (min_roads=2). **ยังไม่ผ่านการสอบเทียบจาก founder** — เปลี่ยนกฎได้ทันที
โดยรัน `python3 tools/backtest/urban_event_ledger.py --matrix` (ไม่ต้อง re-derive SQL เอง).

---

## 4. จำนวน candidate events 2019–2026 แยกตามปี

**MEASURED (ตรวจจาก DB จริง, 2026-09-27)**: source `thaiwater_flood_road` มี **7,699 แถวทั้งหมด**
(2019-01-30 .. 2026-09-27) แต่มีเพียง **10 แถว** ที่อยู่นอกปี 2026 (2019×1, 2021×2, 2022×2, 2023×2,
2025×2 — ทุกแถว value=0) — เป็น**การ probe/test fetch แยกเดี่ยว ไม่ใช่ archive ประวัติศาสตร์จริง**.
**7,689 จาก 7,699 แถว (99.87%)** อยู่ในปี 2026 เท่านั้น. ดังนั้น candidate events ทุกรายการภายใต้กฎข้างบน
**อยู่ในปี 2026 ล้วน (25 events)** — **นี่คือช่องว่างที่วัดได้ของแหล่งข้อมูลนี้เอง ไม่ใช่การอ้างว่ากรุงเทพฯ
ไม่เคยน้ำท่วมถนนช่วง 2019–2025** (case card 2554/2565/2567×2 ด้านล่างครอบคลุมช่วงนั้นบางส่วนแบบ RELAYED
ระดับเมือง ไม่ใช่ระดับถนน).

จำนวน candidate district-events ตามปี (กฎที่เลือก, threshold=10cm, min_roads=3, window=6h):

| ปี | จำนวน |
|---|---|
| 2019–2025 | 0 (ไม่มี archive ถนนช่วงนี้ในคลังนี้) |
| **2026** | **25** |

---

## 5. เหตุการณ์ 24-26 ก.ย. 2569 — onset ต่อถนน (ของเราเอง) vs เวลา RELAYED

**ของเราเอง (MEASURED, `thaiwater_flood_road`)**: ถนนที่ถึง ≥10cm เร็วที่สุดในฐานข้อมูลทั้งหมด (ไม่ใช่แค่
เหตุการณ์นี้) คือ 2 ถนนที่ **2026-09-25T13:00:00Z (20:00 น. ไทย)** — `FL.LKB.03` (ถ.หลวงแพ่ง ช่วงโลตัส
ลาดกระบัง, 20cm) และ `FL.WTL.09` (ถ.ลาดพร้าว ช่วง ซ.89, 10cm). อีก 5 นาทีถัดมา (**13:05Z / 20:05 น.**)
เกิด burst ใหญ่ครอบคลุมหลายโซน รวมโซน **BKP (บางกะปิ)** ซึ่งเป็นโซนของสัมมากร/รามคำแหง — **8 ถนนถึง
≥10cm พร้อมกัน**: 10 ถนนแรกสุด (เรียงตามเวลา, MEASURED):

| ลำดับ | station_code | ถนน | เวลา (UTC) |
|---|---|---|---|
| 1 | FL.LKB.03 | ถ.หลวงแพ่ง ช่วงโลตัสลาดกระบัง | 13:00:00Z |
| 2 | FL.WTL.09 | ถ.ลาดพร้าว ช่วง ซ.89 | 13:00:00Z |
| 3 | FL.BBN.06 | ถ.บางขุนเทียน ตรงข้าม ซ.10 | 13:05:00Z |
| 4 | FL.BKA.03 | ถ.รามอินทรา ช่วง ซ.5 | 13:05:00Z |
| 5 | FL.BKA.06 | ถ.เทพรักษ์ ช่วงบิ๊กซีสะพานใหม่ | 13:05:00Z |
| 6 | FL.BKA.08 | ถ.แจ้งวัฒนะ หน้า ม.ราชภัฏพระนคร | 13:05:00Z |
| 7 | FL.BKE.06 | ถ.หมู่บ้านเศรษฐกิจ ช่วง ซ.5 | 13:05:00Z |
| 8 | FL.BKM.06 | ถ.นวมินทร์ ช่วง ซ.38 | 13:05:00Z |
| 9 | **FL.BKP.03** | **ถ.นวมินทร์ ช่วงแยกบางกะปิ** | **13:05:00Z** |
| 10 | **FL.BKP.04** | **ถ.รามคำแหง ตรงข้าม ซ.53** | **13:05:00Z** |

(รามคำแหง 43 = `FL.BKP.05` เข้าเงื่อนไขที่ 13:05:00Z เช่นกัน, ไม่ติดใน top-10 เพราะเรียงตามเวลาเท่ากันหลายแถว)

**เทียบกับเวลาที่ third-party paste อ้างว่าเป็น BMA-record onset (RELAYED, ยังไม่ระบุ ICT/UTC หรือวันที่
ชัดเจนในไฟล์นั้น)**: **14:45 และ 15:55**. ไม่ว่าตีความเป็น ICT วันที่ 25 (จะเร็วกว่าของเราเองราว 5-6 ชม.)
หรือวันที่ 26 (จะช้ากว่าราว 1 วัน) — **ต่างจาก onset ของเราเอง (13:05Z = 20:05 น. ไทย 25 ก.ย.) เกิน 1
ชม.ทั้งสองกรณี** → บันทึกเป็น **contradiction row ใน `bkp_bangkapi_2026-09-25`, tag OPEN** (ไม่ merge,
ไม่เลือกใช้ตัวเลขใดตัวเลขหนึ่งแทนอีกตัว).

**Sammakorn (ซอย 50, node-specific)**: T0 = community report แรกที่ tag "เข้าบ้าน" = **2026-09-25T21:00:00Z
(04:00 น. 26 ก.ย.)** — ตรงกับ `raw/backtests/sammakorn_7day_real_2026-09-27.jsonl` 100%. คำเตือนที่ระบบนี้
เองรู้ค่าจริงก่อน T0 คือ canal-waterlevel signal ที่ T−7.92h (13:05Z 25 ก.ย., ตรงกับ onset ของ BKP road
cluster พอดี) — **แต่ไม่มี threshold ที่ขึ้นทะเบียนแล้วยกระดับเป็น action_label ณ ตอนนั้น (tier = OPEN)**;
achieved EARLY_MOVE lead ที่แท้จริงของสัมมากรคือ **−9ชม. (MISS)** ตาม
`docs/experiments/2026-09-27-sammakorn-7day-backtest-REAL.md` §5 — คนละตัวเลขกับ TMD regional lead 107ชม.
เสมอ (ไม่เคยปนกัน, ดู `warning_scope` ด้านบน).

---

## 5b. การตัดซ้าย (left-censoring) — แก้ไข 2026-09-27 หลัง independent worker พบ

**สืบเนื่อง (VERIFIED, re-run SQL ตัวเองก่อนแก้)**: `data/observations.sqlite`, `min(fetched_at_utc)`
ต่อ source: `thaiwater_flood_road` = **2026-09-26T08:25:26.071750Z** (collector ของเราดึงครั้งแรก),
`thaiwater_canal_waterlevel` = **2026-09-26T07:51:01.583905Z**. เหตุการณ์ที่ `t_onset_observed`
**ก่อน** เวลาดึงครั้งแรกของ source นั้น — คือ**ตัดซ้าย (left-censored)**: DB ของเรายืนยันได้แค่ **"ท่วมแล้ว
ไม่ช้ากว่า" onset ที่บันทึกไว้** ไม่ใช่เวลาที่เริ่มท่วมจริง (API อาจคืนค่าย้อนหลังที่ไม่ใช่ศูนย์ตั้งแต่แถวแรกที่เราถาม).

**ผลตรวจ (MEASURED)**: **9 จาก 32 event** ในไฟล์นี้ถูกแฟล็ก `onset_censoring: left_censored` +
`first_fetch_utc` (ค่า `thaiwater_flood_road`'s first-fetch ด้านบน) — ทั้งหมดเป็น district-event ที่
`t_onset_observed` ก่อน 2026-09-26T08:25:26Z: `bkp_bangkapi_2026-09-25`, `lkb_2026-09-25_1300`,
`wtl_2026-09-25_1300`, `bka_2026-09-25_1305`, `bkm_2026-09-25_1305`, `lpw_2026-09-25_1305`,
`pwt_2026-09-25_1305`, `slg_2026-09-25_1305`, `bkp_2026-09-26_0645` (06:45Z 26 ก.ย. ก็ยังก่อน first
fetch 08:25Z วันเดียวกัน — ตัดซ้ายเช่นกัน). อีก 16 district-event ที่ onset หลัง 08:25:26Z (26–27 ก.ย.)
เป็น `onset_censoring: observed` — genuine onset, ไม่ตัดซ้าย.

`sammakorn_2026-09-26`'s canal-waterlevel evidence (T−7.92h, observed_at_utc 2026-09-25T13:05:00Z) ก็
ตัดซ้ายแยกต่างหากเทียบกับ `thaiwater_canal_waterlevel`'s first fetch (07:51:01Z 26 ก.ย.) — แฟล็กเป็น
`onset_censoring_canal_signal: left_censored` + `first_fetch_utc_canal` บนแถว event, และบนแถว evidence/
warning ย่อยที่เกี่ยวข้องเอง (ตัวเดียวกับที่ `bkp_bangkapi_2026-09-25` อ้างถึงในคำเตือน node-specific).

**Contradiction row ของ `bkp_bangkapi_2026-09-25` เปลี่ยนสถานะ** (แก้ไข ไม่ลบแถว): เพิ่มฟิลด์ `status:
compatible_left_censored` + `note` — เพราะ onset ของเราเองเป็นแค่ **ขอบบน** (ไม่ช้ากว่า 13:05Z) ไม่ใช่เวลา
เริ่มจริง เวลา BMA-record ของ third-party (14:45/15:55 ICT) ถ้าตีความเป็น ICT วันที่ 25 จะ**เร็วกว่า**ขอบบน
ของเรา ซึ่ง**ไม่ขัดแย้งกัน**ในทางตรรกะ (สอดคล้องกับความเป็นไปได้ที่ท่วมเริ่มก่อน 13:05Z จริง) — แต่ยังไม่ยืนยัน
timezone/วันที่ของตัวเลข BMA ชัดเจน จึงยังเก็บเป็น contradiction row (`tag: OPEN`) ไม่ตัดทิ้งและไม่เลือกใช้
ตัวเลขใดแทนอีกตัว.

**Placeholder ที่น่าสงสัย (SUSPECT, OPEN)**: สถานีที่ชื่อลงท้าย `*` ให้ค่า **20.0 ซม.** คงที่ซ้ำหลายจุด/เวลา —
`884` แถวทั้งหมดมีค่า `value == 20.0` เป๊ะ, `883` ใน 884 แถวนั้นอยู่บนสถานีที่ `station_name` ลงท้ายด้วย ` *`
(อีก 1 แถวไม่ใช่สถานีลงท้าย `*`). ค่าคงที่ซ้ำขนาดนี้เข้ากับ "รหัสหมวด/placeholder" ของ API ต้นทางมากกว่าการวัด
อิสระ 883 ครั้งที่บังเอิญได้ค่าเดียวกันเป๊ะ — บันทึกเป็น `data_quality_flags.flat_20cm_placeholder_suspect`
ในไฟล์ YAML (tag `OPEN`, `candidate_status: SUSPECT_placeholder`) **ไม่ตัดออกจาก decision rule** (ยังนับ
รวมใน cluster เดิม, ห้ามลบทิ้งเพื่อความสะอาด).

**ผลต่อ TODO #87 (calibration)**: founder ที่จะสอบเทียบ `decision_rule` ควรอ่านทั้งสองแฟล็กนี้ก่อน — event ที่
ตัดซ้ายอาจมี onset จริงเร็วกว่าที่บันทึก (โน้มเอียงให้ lead-time ที่รายงานเป็น**ขอบบน**ของ lead จริง ไม่ใช่ค่ากลาง)
และค่า 20.0 ซ้ำอาจดันจำนวน event ให้สูงกว่าที่ควรถ้าเป็น placeholder จริงมากกว่าค่าวัด.

---

## 6. TODOLIST — แถวใหม่ #86 เป็นต้นไป (5 คอลัมน์)

| # | ปัญหา/ช่องว่าง | สิ่งที่ต้องทำ | owner | priority |
|---|---|---|---|---|
| 86 | GAP §2.1 ของการ์ดรีวิว (binary urban-event ground-truth ledger) — **ปิดแล้ว** ในรอบนี้ ด้วย `sources/urban_flood_event_ledger.yaml` (YAML append-only แทน sqlite table ใหม่ ตามที่เสนอไว้ — ยังไม่ wire เข้า `store.py`/`data/observations.sqlite` จริง) | ถ้าจะให้ collector สด (`collect.py`) เขียนแถวใหม่อัตโนมัติ ต้อง wire `append_event()` เข้า pipeline จริง (ตอนนี้เป็น manual/backtest tool เท่านั้น) | committer | medium |
| 87 | Decision rule (`threshold_cm=10, min_roads=3, window_hours=6`) เป็น INSTINCT ล้วน ยังไม่ผ่านการสอบเทียบจาก founder | founder ทบทวน `decision_rule.alternatives_matrix` ใน YAML แล้วยืนยัน/ปรับค่า | founder | high |
| 88 | เวลา BMA-record onset 14:45/15:55 ที่ third-party paste อ้างถึง ยังไม่ระบุ ICT/UTC/วันที่ชัดเจน — ขัดกับ onset ของเราเอง (13:05Z 25 ก.ย.) เกิน 1 ชม. ทั้งสองการตีความ | สืบต้นทางไฟล์ paste เดิม (`external_urban_event_and_zoom_pastes_2026-09-27.md`, อยู่ใน scratchpad ของ session อื่น ไม่ใช่ไฟล์ในคลังนี้) หา timezone/วันที่ชัดเจน แล้วอัปเดต contradiction row (ห้ามแก้ย้อนหลัง เพิ่มแถวใหม่แทน) | committer | medium |
| 89 | Ledger ยังไม่มีแถวปี 2019–2025 ระดับถนน เพราะ `thaiwater_flood_road` เองไม่มี archive ช่วงนั้น (มีแค่ 10 แถว probe, value=0 ทั้งหมด) | ถ้าต้องการ historical district-level ground-truth ช่วง 2019–2025 ต้องหา archive ภายนอก (news/RID/BMA) แล้วเพิ่มเป็นแถว RELAYED ใหม่ — นอกขอบเขตงานนี้ | committer | low |
| 90 | `bangkok_citywide_disaster_declared_2026-09-27`'s `declaring_agency` ระบุกว้างแค่ "กรุงเทพมหานคร" — ยังไม่ระบุคำสั่ง/ประกาศฉบับที่แน่ชัด | สืบเอกสารประกาศจริงจาก กทม. (นอก pptvhd36.com ที่เป็นข่าว) เพื่อยกระดับจาก RELAYED เป็น VERIFIED | committer | low |

---

## 7. ไฟล์ที่เขียน

- `sources/urban_flood_event_ledger.yaml` — schema + decision rule + alternatives matrix + 32
  event rows (3 headline: `bkp_bangkapi_2026-09-25`, `sammakorn_2026-09-26`,
  `bangkok_citywide_disaster_declared_2026-09-27`; 24 candidate district-rows จากกฎ; 5 historical
  case-card rows: 2554, เชียงใหม่ 2567, หาดใหญ่ 2553, หาดใหญ่ 2565, น่าน 2567)
- `tools/backtest/urban_event_ledger.py` — `derive_events_from_flood_road()`,
  `cluster_events()`, `rule_outcome_matrix()`, `append_event()` (append-only, refuses duplicate
  `event_id`, validates schema before writing), CLI `--list-candidates` / `--event YYYY-MM-DD` /
  `--matrix`
- `tests/test_urban_event_ledger.py` — 21 tests (schema validation, append-only guarantee,
  synthetic 3-road decision-rule fixture, district-code parsing, window-clustering boundary, and a
  DB-gated test on the real 25 Sep 2569 BKP onset — skips gracefully if
  `data/observations.sqlite` is absent)
- `docs/knowledge/URBAN_FLOOD_EVENT_LEDGER_2026-09-27.md` — this file

**Leak scan (ของไฟล์ที่เขียนในงานนี้ทั้งหมด)**: ไม่มีชื่อบุคคล, ไม่มี local absolute path,
ไม่มี local username, ไม่มีชื่อ AI/vendor — ตรวจด้วย leak-pattern scanner ของ repo ก่อนส่งมอบ (ดู §8).

---

## 8. Leak-scan check (บันทึกไว้ ไม่ใช่ผลลัพธ์ที่หลุดมา)

ตรวจด้วย leak-pattern scanner ของ repo ข้ามทั้ง 4 ไฟล์ของงานนี้
(`sources/urban_flood_event_ledger.yaml`, `tools/backtest/urban_event_ledger.py`,
`tests/test_urban_event_ledger.py`, `docs/knowledge/URBAN_FLOOD_EVENT_LEDGER_2026-09-27.md`) —
ตรวจหา local username, local absolute path, และชื่อ AI/vendor โดยไม่ต้องเขียน pattern
เป็นคำตรงๆ ไว้ในไฟล์นี้เอง (เลี่ยงปัญหาที่เอกสาร "บันทึกการตรวจ" กลายเป็นตัวอย่างของสิ่งที่มันตรวจเอง).

ผลตรวจ (2026-09-27): grep ตรงพบ 1 match — บรรทัด command ของ grep pattern เองในไฟล์นี้ (§8
ด้านบน ตอนนั้นยังเขียน pattern ตรงๆ ในไฟล์ ซึ่งแก้ไปแล้วด้านบน). ไม่พบชื่อบุคคล (คำว่า
"นายกฯ"/"ผู้ว่าฯ" ในแถว historical case-card เป็นตำแหน่งเท่านั้น ไม่ใช่ชื่อบุคคล ตามรูปแบบการ์ด
case_* อื่นในคลังนี้) ไม่พบ local absolute path/username ในไฟล์ทั้ง 4.

ตรวจซ้ำ (2026-10-03) ด้วยสแกนเนอร์ leak-pattern ของ repo (ไม่เขียนชื่อไฟล์/ชื่อเครื่องมือตรงๆ
ไว้ที่นี่ — ดูเหตุผลใน §8 ด้านบน): 0 finding บนไฟล์ทั้ง 4 ของงานนี้.
