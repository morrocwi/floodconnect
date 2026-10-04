# T7→T0 DATA PLAN — แผนสร้างข้อมูลที่เป็นประโยชน์ช่วง T−7 ถึง T0 ของเหตุการณ์

**คำสั่งผู้ก่อตั้ง (verbatim)**: "วางแผนเพื่อสร้างข้อมูลที่เป็นประโยชน์ในช่วง T7–T0 ของเหตุการณ์"

**สถานะไฟล์นี้**: แผน (proposal), **ไม่ใช่การ implement** — worker นี้เขียนไฟล์ใหม่เท่านั้น ไม่แก้/ไม่ commit
ไฟล์อื่นใด อีก worker เป็นผู้ตัดสินใจ wire เข้า pipeline จริง. ไม่มีสมการใหม่ในไฟล์นี้ (ตาม AGENTS.md §2) —
ทุกอย่างด้านล่างเป็นสถาปัตยกรรมข้อมูล (การเก็บ/การเก็บถาวร/schema) ไม่ใช่การ derive PROP-FLOOD ใหม่.

**สองนาฬิกา (adopt จากบันทึกภายนอก, ดู card คู่กัน)**: `forecast_horizon` (มองเห็นได้ไกลแค่ไหน) กับ
`action_horizon` (หลักฐานพอจะลงมือเมื่อไหร่) — เป็น**ป้ายกำกับ (labels)** ที่แปะทับ tier L0–L5/LR ของ
PROP-FLOOD-06 ที่มีอยู่แล้ว ไม่ใช่ ladder ใหม่:

| Label (จากบันทึกภายนอก) | Tier ที่แมป (PROP-FLOOD-06) | ความหมาย |
|---|---|---|
| PREPARE | L0–L1 | เฝ้าดู, เตรียมของถูก/reversible |
| READY | L1–L2 | มี warning หลายวันซ้อนพื้นที่ → เปิดเครือข่ายมนุษย์ |
| ACTIVATE | L2–L3 | หลักฐาน 24–72 ชม. แข็งขึ้น → ยืนยัน route/safe-node |
| EARLY MOVE | L3–L4 | node ข้างเคียงเสื่อมสภาพจริง (measured) → ย้ายกลุ่มเปราะบางผ่าน route ที่ verified แล้วเท่านั้น |
| RESPONSE | L4–L5/LR | ท่วมจริง → หยุดเดา ใช้ edge ที่ verified/สดเท่านั้น |

**ตัวส่งเสริม (promoter) ผู้สมัครใหม่ — "neighbour node degrading"**: สังเกตจริง (MEASURED-community,
ดู community_reports) ว่ารามคำแหง 53 (สื่อ/social รายงานท่วมถนนตั้งแต่ ~16:00 25 ก.ย. — RELAYED,
ดู `site/inputs/ram53/social_timeline_2026-09-26.md`) เสื่อมสภาพก่อนสัมมากรเข้าบ้านจริง (~04:00 26 ก.ย.,
community_report) ประมาณ **12 ชม.** — นี่คือ**ข้อเสนอ promoter ใหม่ เขียนเป็น proposal note เท่านั้น**
(ยังไม่ implement, ยังไม่แก้ `PROP-FLOOD-06.md`/`flood_outlet_coping.json`): "unit ข้างเคียงที่เชื่อมทาง
น้ำ/ทางถนนเดียวกัน อ่านค่าเสื่อมสภาพ (tier ขึ้น หรือ community-report ท่วมถนน/บ้าน) → promote tier ขั้นต่ำ
ของ unit ปลายน้ำ/เชื่อมต่อขึ้นอย่างน้อย 1 ระดับ, ป้าย `NEIGHBOR_NODE_DEGRADING`, INSTINCT threshold (ยังไม่
สอบเทียบ, ยังไม่มี lead-time distribution ของคู่ node จริงมากกว่า 1 เหตุการณ์)". เก็บไว้ที่นี่เป็นข้อสังเกต
สำหรับ v3/v6 ของ proposal เท่านั้น.

---

## 1. ต่อสเตจ — มีอะไรอยู่แล้ว (a) / ขาดอะไร ทำฟรีได้ยังไง (b)

### T−7 (ราว 7 วันก่อน T0)

**(a) มีอยู่แล้ว**:
- `openmeteo_forecast16d_multimodel` (9 โมเดล deterministic, VERIFIED endpoint, ยังไม่ wire เข้า
  `collect.py`) + `openmeteo_ensemble_daily_precip` (31 สมาชิก GFS-ENS) + `metno_locationforecast`
  (แหล่งอิสระที่ 3 คนละ pipeline) — ครบ ≥7 วัน, ฟรี, ไม่ต้อง key, refresh: **ต่อ run** (ต่อการรัน
  `collect.py --all` แบบ on demand ถ้า wire เข้า, ปัจจุบันยังเป็นสคริปต์ร่าง
  `tools/harvest/forecast7d_draft.py` รันมือ — *(historical note: ก่อน 2026-10-02 แผนนี้สมมติ cron
  30 นาที)*)
- `tmd_7day_text_forecast` (ข้อความ ไม่ใช่ตัวเลข, VERIFIED endpoint, ไทยโดยตรง) — refresh: รายวัน (TMD
  ออกใหม่ทุกวัน แต่เนื้อหาเป็น 7-day outlook ที่ปรับตัวเองทุกวัน)
- `openmeteo_previous_runs` (skill-check, MEASURED-vs-forecast) — ดูว่าโมเดลแม่นแค่ไหนย้อนหลัง, refresh:
  ต่อ run
- `coping_thresholds.yaml` (ค่ารับมือประวัติศาสตร์) — static, ไม่ต้อง refresh บ่อย

**(b) ขาด + วิธีทำฟรี**:
- **TMD 7-day text page ไม่เคยถูกเก็บถาวรรายวัน** ("what was said at T−k" ledger) — ปัจจุบันดึงแล้วอ่านสด
  ไม่เก็บ snapshot วันต่อวัน → เพิ่ม `collect.py` ให้ archive TMD 7-day text page ทุก run ที่
  `raw/live/tmd_7day_text_forecast/<UTC timestamp>.html` (ฟรี, แค่เก็บสิ่งที่ดึงอยู่แล้วให้ไม่หายไป)
- **Per-run snapshot ของทุก forecast model** (ไม่ใช่แค่ log ผลรวม) — ต้องเก็บ raw JSON response ของ
  `openmeteo_forecast16d_multimodel`/`ensemble`/`metno` ทุก run ใต้ `raw/live/forecast7d/<ts>.json`
  เพื่อไม่ให้ hindsight เป็นไปได้ (ย้อนไปดูว่า ณ T−7 โมเดลบอกอะไรจริง ไม่ใช่เดาจาก archive ที่ overwrite แล้ว)
- **Community "node degrading" ก่อนเหตุการณ์** — ไม่มีกลไกรับรายงานชุมชนเชิงรุกที่ T−7 (ตอนนี้เก็บย้อนหลัง
  หลังเหตุการณ์เท่านั้น) — ฟรี: เปิดฟอร์มรับรายงานแบบเดิม (ไม่มีชื่อ, ซอย+สภาพ+เวลา) ตลอดปี ไม่ใช่แค่ตอน
  วิกฤต, ติด timestamp วินาทีจริงที่ระบบรับ (ไม่ใช่แค่ "x ชม.ก่อน")

### T−5

**(a) มีอยู่แล้ว**: เหมือน T−7 (forecast ensemble ยังอยู่ในขอบฟ้า 16 วัน) + `dam` sources (เขื่อนหลัก, ถ้า
wire แล้ว) + rain gauges/canal levels (สถานะปัจจุบัน real-time, MEASURED)

**(b) ขาด**: **safe-node/egress verification ที่ T−5** — ยังไม่มี field เก็บ "เส้นทาง/จุดปลอดภัยถูกยืนยัน
ล่าสุดเมื่อไหร่" (freshness ของ route/safe-node เอง) → เพิ่ม schema แถวเดียว (unit_or_route_id,
verified_at, verified_by_role ไม่ใช่ชื่อ, method) ต่อ route/safe-node — ฟรี (แค่ metadata เพิ่ม ไม่ต้อง
แหล่งข้อมูลใหม่)

### T−3

**(a) มีอยู่แล้ว**: TMD ประกาศ warning ระดับภูมิภาค (ถ้าออกแล้ว) + rain gauges + canal levels vs
normal/critical/bank lines (`sources/registry.yaml`, MEASURED) + GloFAS (upstream, บาง unit) + dam
release ratio (ถ้ามี feed)

**(b) ขาด**: **TMD warning-and-events archive แบบเก็บถาวรของทีมนี้เอง** — ปัจจุบันอ่านหน้าเว็บสด ไม่มี
`raw/live/tmd_warning_archive/` เก็บ HTML ต่อวัน → เพิ่ม collector ใหม่ (1 request/run ตามกติกา BMA-host
เดียวกัน แม้ tmd.go.th ไม่ใช่ BMA host ก็ควรใช้วินัยเดียวกัน), เก็บทุกวันแม้ไม่เปลี่ยน (เพื่อพิสูจน์ภายหลังว่า
"ไม่มีคำเตือนใหม่" ก็เป็นข้อมูลเช่นกัน)

### T−2

**(a) มีอยู่แล้ว**: เหมือน T−3 + `bma_station_detail`/`bma_watermap` (canal level, pump running state
รายสถานี) + BMA preparedness announcements (ถ้าเก็บ, ปัจจุบันเป็น RELAYED จากข่าว ไม่ใช่ collector)

**(b) ขาด**: **BMA/เขต official preparedness order เป็น source ใน registry** — ตอนนี้ทราบผ่านข่าว
(RELAYED) เท่านั้น ไม่มี collector ต่อประกาศราชการโดยตรง → ฟรี: เพิ่ม reference_documents entry ต่อ
ประกาศเขต/กทม. ที่พบ (URL + วันที่ดึง) เป็น static card แบบ `docs/knowledge/*.md` เดิม (ไม่ต้องมี API)

### T−1

**(a) มีอยู่แล้ว**: ทุกอย่างของ T−2 ปรับ frequency ถี่ขึ้น (real-time gauges) + community "node
degrading" ของ unit ข้างเคียง (เช่น กรณีนี้ ราม 53 ก่อนสัมมากร — แต่**เก็บย้อนหลังหลังเหตุการณ์เท่านั้น
ในเคสนี้จริง** ไม่ใช่ real-time ตอนนั้น)

**(b) ขาด**: **real-time neighbour-node monitoring** — ไม่มีกลไก "จับตา unit ข้างเคียงที่เชื่อมทางน้ำ/
ถนนเดียวกัน" อัตโนมัติ (ตอนนี้ทำได้แค่ social listening ย้อนหลังผ่าน Playwright ที่ `site/inputs/ram53/`)
→ ฟรี: ทำ social-listening query เดิมให้รันเป็น cron/run ปกติ (ไม่ใช่ ad-hoc ครั้งเดียวหลังเหตุการณ์),
เก็บผลทุก run แม้ผลว่าง (เพื่อพิสูจน์ว่าไม่มีสัญญาณ ก็เป็นแถวข้อมูล ไม่ใช่ความเงียบที่ตีความไม่ได้)

### T−12h

**(a) มีอยู่แล้ว**: gauge/canal real-time (on demand, caller-side -- *(historical note: ก่อน
2026-10-02 เคยเป็น cadence 30 นาทีผ่าน GitHub Actions; ก่อน 2026-10-03 GitHub Actions เองเคยรัน
`collect.py --all` บน runner ของเรา -- เอาออกแล้ว, ตอนนี้ต้องรันบนเครื่อง/network/key ของผู้เรียก
เอง)*) + community reports (ถ้า
มีคนโพสต์แล้ว ระบบเก็บได้)

**(b) ขาด**: **"node degrading" ของ neighbour unit เป็น field มาตรฐานใน readout_log** — ปัจจุบันไม่มี
column ที่บอกว่า unit ข้างเคียงคนไหนเสื่อมสภาพก่อนกี่ชั่วโมง (ต้องขุดจาก social/community เอง) → เพิ่ม
`neighbor_node_id` + `neighbor_tier_at_read_time` ใน readout_log schema (ดู §2 ด้านล่าง)

### T0

**(a) มีอยู่แล้ว**: community reports "เข้าบ้านแล้ว" (MEASURED-community, ซอย+เวลา+สภาพ), canal/pump
station จริง (measured), tide (ถ้ามี feed)

**(b) ขาด**: **timestamp T0 ที่ประกาศชัดเจนต่อ event** — ปัจจุบัน T0 ถูกอนุมานจาก community report ("ตี 4"
เป็นช่วง ±1 ชม. ไม่ใช่วินาทีจริง) → ต้องประกาศ convention ชัดว่า T0 ของ event หนึ่งคือ "เวลาที่ community
report แรกที่ tag `เข้าบ้าน` (ไม่ใช่แค่ถนน/โรงรถ) มาถึง" — เป็น INSTINCT convention ที่ต้องประกาศไว้ล่วงหน้า
ไม่ใช่เลือกทีหลังให้ตัวเลข lead time สวย

### T+1 (หลังเหตุการณ์)

**(a) มีอยู่แล้ว**: community reports ต่อเนื่อง (ระดับน้ำ, ทางออก, การช่วยเหลือ) + canal/pump status

**(b) ขาด**: **ผลลัพธ์เชิงปริมาณต่อครัวเรือน** (เวลาที่ถึงกลุ่มเปราะบางจริง, จำนวนคำขอที่จับคู่สำเร็จ) — ตรง
กับ metric "human outcome" ที่บันทึกภายนอกเสนอ, ยังไม่มี schema เก็บเลย ในคลังนี้ → ต้องออกแบบใหม่ (นอก
ขอบเขตไฟล์นี้ ระบุเป็น OPEN §7)

---

## 2. EVENT LEDGER schema (append-only, retained)

**หลักการ**: ทุกแถวเขียนครั้งเดียว ไม่เขียนทับ — backtest ในอนาคตอ่านเฉพาะแถวที่ `run_time ≤ T−k` ของ
เหตุการณ์นั้น เพื่อไม่ให้ hindsight เป็นไปได้ (ตรงกับกฎ "anti-leakage" ที่บันทึกภายนอกประกาศเอง และตรงกับ
`readout_log`/`never prune` ที่มีอยู่แล้วใน AGENTS.md §2).

```yaml
event_ledger:
  event_id: string        # เช่น "sammakorn_2026-09-26"
  unit: string             # unit id ตาม PROP-FLOOD-06 (เช่น "sammakorn", "ram53")
  T0_definition:
    convention: string     # เช่น "first community report tagged เข้าบ้าน"
    T0_value: timestamp    # ISO8601 UTC, ประกาศครั้งเดียว ไม่แก้ย้อนหลัง
    tag: "INSTINCT"         # การเลือก convention เอง ไม่ใช่ข้อเท็จจริงที่วัดได้ตรง
  rows:                     # แถวเดียวต่อ (run_time, source) — append-only, ไม่เขียนทับ
    - run_time: timestamp   # เวลาที่ระบบ "รู้" ค่านี้จริง (ไม่ใช่เวลาที่เหตุการณ์เกิด)
      horizon_to_T0_h: number   # T0_value - run_time เป็นชั่วโมง (ลบ = ก่อน T0, บวก = หลัง T0)
      source: string        # id ตาม sources/registry.yaml, หรือ "community_report", หรือ
                              # "neighbor_node:<unit_id>"
      value: any             # ตัวเลข/ข้อความดิบที่อ่านได้ ณ เวลานั้น
      tier: string           # L0-L5/LR ที่คำนวณได้ ณ run_time นั้น (ถ้ามี pipeline คำนวณ)
      action_label: string   # PREPARE/READY/ACTIVATE/EARLY_MOVE/RESPONSE (ป้าย, ไม่ใช่ tier ใหม่)
      tag: string             # VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN ต่อแถว (บังคับ)
```

**กติกาบังคับ**: `run_time` ต้องเป็นเวลาที่ระบบเก็บค่าจริง (ไม่ใช่เวลาของเหตุการณ์ในค่านั้น) — นี่คือกลไก
เดียวที่ทำให้ query `WHERE run_time <= T0 - k` ที่ §4/§5 ต้องการ เป็นไปได้จริงโดยไม่ต้องเดา. ไม่มีแถวใดถูก
ลบ/เขียนทับแม้ค่าในแถวจะขัดแย้งกับแถวหลัง (เหมือน `contradictions` เดิม).

---

## 3. Acceptance test — เหตุการณ์ 24-26 ก.ย. 2569 สร้างจากอะไรได้จริงตอนนี้

**ตรวจแล้ว (MEASURED, ตอนเขียนไฟล์นี้)**: raw snapshot จริงที่เก็บถาวรใน `raw/live/` เริ่มที่
**2026-09-26T04:01:59Z** (`raw/live/thaiwater_bma/2026-09-26T040159Z_canal_waterlevel.json`) — **ไม่มี
snapshot ดิบที่เก็บถาวรจริงก่อนเวลานี้** ในคลังนี้ (ต่างจากตัวเลขที่ระบุไว้ในโจทย์งานนี้ว่า "ตั้งแต่ 26 ก.ย.
14:45" — ตรวจแล้วพบว่าจุดเริ่มจริงคือ ~04:01 UTC เช้าวันเดียวกัน, ไม่ใช่ 14:45; ทั้งสองตัวเลขอยู่ใน "26 ก.ย."
เดียวกัน ต่างกันแค่ชั่วโมง — บันทึกความต่างนี้ตรงๆ แทนการเลือกใช้ตัวเลขใดตัวเลขหนึ่งแบบเงียบๆ).

**สร้างได้ตรง (honest, จาก archive จริง)**:
- แถว `run_time` ตั้งแต่ 2026-09-26T04:01Z เป็นต้นไป (canal water level, pump/floodgate, flood_road) —
  คือช่วง **T−0 ถึง T+ เท่านั้น** (สัมมากรเข้าบ้านแล้วตี 4 ตามคำนิยาม T0 ข้างบน — snapshot แรกมาถึงพร้อมๆ
  หรือหลัง T0 เล็กน้อย ไม่ใช่ก่อน)
- community reports 26/27 ก.ย. (ไฟล์ `site/inputs/community/*.md`) — MEASURED-community, ครอบคลุม
  T0 ถึง T+1 ของสัมมากรเอง
- `site/inputs/ram53/social_timeline_2026-09-26.md` (RELAYED, ค้น 26 ก.ย. ~13:00 ย้อนหลัง 24 ชม.) — ให้
  หลักฐาน "ราม 53 เริ่มท่วมถนน ~16:00 25 ก.ย." แต่เป็น**การค้นย้อนหลัง**ในวันที่ 26 (หลัง T0 ของสัมมากรแล้ว)
  ไม่ใช่ social-listening ที่รันสด ณ เวลานั้นจริง — ใช้ตรวจสอบ lead-time เชิง**อนุมานย้อนหลัง**ได้ (บันทึกไว้
  ชัดว่าเป็น retrospective ไม่ใช่ real-time capture)

**ต้องการ collector ใหม่ก่อนสร้างได้ (missing)**:
- แถวช่วง T−7 ถึง T−1 ของเหตุการณ์นี้เอง (19–25 ก.ย.) — **ไม่มี raw snapshot ที่เก็บถาวรของทีมนี้เองในช่วง
  นี้เลย** ในคลังนี้ (`raw/live` เริ่ม 26 ก.ย. เท่านั้น) — สิ่งที่มีคือ TMD-citation ที่บันทึกภายนอกอ้างถึง
  (RELAYED, ไม่ใช่ archive ของทีมนี้ — ดู card คู่กัน §"การตรวจสอบ")
- `neighbor_node_id`/`horizon_to_T0_h` ต่อ ram53↔sammakorn — คำนวณได้ย้อนหลังจากไทม์ไลน์ social ข้างบน
  (16:00 25 ก.ย. → 04:00 26 ก.ย. = **~12 ชม.**) แต่**ยังไม่มีแถวใน readout_log จริงที่เขียนไว้ ณ เวลานั้น**
  — เป็นการคำนวณย้อนหลังตอนนี้เท่านั้น (tag: MEASURED-post-hoc, ไม่ใช่ real-time lead)

---

## 4. Falsifier

**หลังทุกเหตุการณ์**: คำนวณ **achieved lead time ต่อ action_label** = `T0_value − (run_time แรกที่
action_label นั้นถูกยกระดับถึงในแถว event_ledger จริง)`. เปรียบเทียบกับ target lead-time ที่บันทึกภายนอก
เสนอไว้ (เช่น READY ควรมาก่อน T0 หลายวัน, EARLY MOVE ควรมาก่อน T0 หลักชั่วโมง). รายงานเป็นตาราง
per-event, ไม่เฉลี่ยข้ามเหตุการณ์ (ตรงกับกฎ §5 ข้อ 7 ของ `CO_FORECAST_PROTOCOL.md` — ห้าม average ข้าม
หน่วยจนซ่อนหน่วยที่แย่). ถ้า achieved lead time < 0 (action_label มาหลัง T0) ให้รายงานตรงๆ ว่าเป็น
**miss ของ action_label นั้น** ไม่ใช่ปัดเป็น "ใกล้เคียง".

---

## 5. OPEN

1. Collector ใหม่ทั้งหมดใน §1(b) ยังไม่ implement — เป็นแผนเท่านั้น (ตาม scope ของไฟล์นี้)
2. `neighbor_node_id` field ใน readout_log schema (§2) ยังไม่ wire เข้า `store.py` จริง
3. T0_definition convention (§2) ยังไม่ประกาศเป็นทางการสำหรับหน่วยอื่นนอกจากสัมมากร/ราม53
4. Promoter "neighbour node degrading" (คำนำ) ยังไม่มี threshold ที่สอบเทียบ — เสนอเป็น proposal note
   สำหรับ PROP-FLOOD-06 เท่านั้น
5. Human-outcome metric schema (T+1, §1) — นอกขอบเขตไฟล์นี้ทั้งหมด
6. ความต่างระหว่างเวลา "14:45" ในโจทย์กับ "04:01Z" ที่ตรวจพบจริง — ยังไม่สืบต่อว่าตัวเลขไหนอ้างอิงถึงอะไร
   แน่ชัด (อาจเป็นคนละ timezone/คนละ run ที่ต่างเวลากัน) — บันทึกไว้เป็นข้อขัดแย้งที่ยังไม่ reconcile
