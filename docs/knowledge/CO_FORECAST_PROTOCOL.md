# CO_FORECAST_PROTOCOL — โปรโตคอลการพยากรณ์ร่วมของคลังนี้

**คำถามผู้ก่อตั้ง (คำต่อคำ, 2026-09-27)**: "ใช้ git readout เรามองหาโปรโตคอลการพยากรณ์ร่วมว่า ทั้งหมดแล้ว
เชื่อมกันไปสู่กรอบมองอะไร" + ตามมาด้วย "ถึงจะแม่นยำและใช้ได้กับทุกสถานที่", "ทำทั้งหมดให้ระดับโลก แต่พอใช้ได้
แม้ข้อมูลไม่ครบ … ขอแค่ข้อมูลจริงแม้เล็กที่สุด", "ระวังข้อมูลขัดแย้งด้วย"

**สถานะไฟล์นี้**: เอกสารสังเคราะห์ (synthesis) จากไฟล์ที่มีอยู่แล้วในคลังนี้ + `toledo-wt-flood06/docs/
proposals/PROP-FLOOD-06.md` (read-only) + `readout_genesis/READOUT_GENESIS_CORE.md` Part VI-A §B.2a
(read-only) — **ไม่ใช่เอกสารเสนอสมการใหม่**, ไม่แก้ไฟล์อื่นใดเลย เป็น worker แยกเขียนไฟล์นี้ไฟล์เดียว

---

## 1. ชื่อกรอบ: "การอ่านค่าร่วม ไม่ใช่การพยากรณ์" (readout-not-truth)

**ทุกตัวเลขในคลังนี้คือ "การอ่านค่าที่จำกัด ณ ช่วงเวลาหนึ่ง" (a finite retained readout) ไม่ใช่ "ความจริงของ
โลก"** — นี่คือกรอบเดียวที่ผูกทุกไฟล์/ทุก worker/ทุก source ในคลังนี้เข้าด้วยกัน ไม่ใช่แค่หลักการทั่วไป
เฉยๆ แต่เป็นเหตุผลเชิงสถาปัตยกรรมที่ readout_genesis Part VI-A §B.2a วางไว้: "A generic conservation
ledger... is architecture, not a physics claim: the machinery reports graph, lineage, tape, currents,
and operator powers for a semantic card to audit against *its own* declared conserved quantity — it
does not, by itself, assert that any particular physical quantity is conserved." เอามาปรับใช้ตรงนี้ —
กราฟ/ทะเบียนของคลังนี้ (`observations`/`documents`/`contradictions`/`readout_log`) คือบัญชี (ledger)
ของ**สิ่งที่อ่านได้จริง** ไม่ใช่คำยืนยันว่าน้ำจะท่วมหรือไม่ท่วม — ทุกเลเยอร์ (§2 ด้านล่าง) มีหน้าที่แค่รักษาบัญชี
นั้นให้ตรวจสอบย้อนกลับได้ ไม่ใช่ตัดสินแทนความจริง

กฎแท็กของคลังนี้เอง (`AGENTS.md` §2) คือการทำให้กรอบนี้บังคับใช้ได้จริงในทุกไฟล์: `VERIFIED` (ตรวจเองแล้ว)
/ `MEASURED` (อ่านจากข้อมูลคลังนี้เอง) / `RELAYED` (จากแหล่งอื่น ยังไม่ตรวจ) / `INSTINCT` (การตัดสินใจ
เชิงวิศวกรรม) / `OPEN` (ยังไม่ยุติ/ขัดแย้งกัน) — **ไม่มี claim ใดในไฟล์ .md ที่ไม่ติดแท็ก**. เหตุผลที่ต้องเป็น
กรอบเดียว ไม่ใช่แค่ระเบียบเอกสาร: `DATA_SYSTEM.md` เขียนไว้ตรงๆ ว่า "หน่วยงานไทยหลายหน่วยงานทำงานแข่งกัน
และข้อมูลไม่สอดคล้องกัน... งานของระบบนี้คือ**แสดงความขัดแย้งนั้นให้เห็น** ไม่ใช่ตัดสินแทนว่าใครถูก" — ถ้าไม่มี
กรอบ readout-not-truth เดียวกำกับทุกชั้น การแสดงความขัดแย้งแบบนี้จะไม่มีวินัยรองรับ (ใครจะตัดสินว่าค่าไหน
"จริงกว่า"?) — คำตอบของคลังนี้คือ: ไม่มีใครตัดสินแทน ทุกค่าคงอยู่พร้อมแท็ก ผู้อ่านตัดสินใจเอง

---

## 2. สี่ชั้นของกรอบ

### (a) แหล่ง = ค่าอ่านที่จำกัด (source-as-finite-readout)

ทุก source ใน `sources/registry.yaml` ติด `trust_tier` ของตัวเอง (`official_telemetry` /
`official_report` / `official_shared_inference` / `third_party`) แต่ `DATA_SYSTEM.md` บอกตรงๆ ว่า tier
นี้เป็น **"การตัดสินใจเชิงวิศวกรรม (INSTINCT/Dr-tier) ของโค้ดชุดนี้ ไม่ใช่ใบรับรองจากหน่วยงาน"** — พูดอีกแบบ:
**ไม่มีแหล่งใดมีสิทธิ์ยับยั้งเชิงญาณ (epistemic veto) จากตำแหน่ง/ชื่อหน่วยงานเพียงอย่างเดียว** ตรงตามกฎระดับ
memory ที่ว่าการยืนยันความรู้เป็นแนวราบ (horizontal) เท่านั้น — ไม่มีหน่วยงานใดชนะเพราะเป็น "หน่วยงานรัฐ"
เพียงอย่างเดียว เช่นเดียวกับที่ไม่มี source ใดใน registry นี้ชนะเพราะเป็น `official_telemetry` เพียงอย่างเดียว
— tier บอก**วิธีอ่าน** ไม่ใช่**ใครถูก**

**ตัวอย่างจริงในคลังนี้ (attributed)**: `docs/knowledge/card_opinion_2026-09-27_onetomany_forecast_
communication.md` บันทึกข้อพิพาทระหว่างกรมอุตุนิยมวิทยา (หน่วยงานราชการ) กับเพจพยากรณ์อากาศเอกชนเรื่อง
คำว่า "มหาอุทกภัย" — ทั้งสองฝ่ายอ้าง "แบบจำลองเดียวกัน" (GFS/ECMWF สาธารณะ) ต่างกันที่การตีความ/สื่อสาร
บัตรนี้เขียนไว้เองว่า "บัตรนี้บันทึกข้อกล่าวหา/คำวิจารณ์เหล่านั้น **ในฐานะคำกล่าวอ้างของผู้เขียนบทความเท่านั้น
ไม่ใช่ข้อค้นพบหรือข้อสรุปของทีมนี้**" — ทั้งฝั่งราชการและฝั่งเอกชนถูกเก็บเป็น `RELAYED-OPINION` เท่ากัน ไม่มี
ฝั่งใดถูกยกเว้นการตรวจสอบเพราะเป็นหน่วยงาน หรือถูกด้อยค่าเพราะเป็นเพจเอกชน — นี่คือกรอบ "ไม่มีแหล่งใด
มีสิทธิ์ยับยั้งเชิงญาณ" ที่ใช้งานจริงในเอกสาร ไม่ใช่แค่หลักการลอยๆ

### (b) ความขัดแย้งต้องปรากฏ (contradiction must surface)

`tools/reconcile.py` (docstring ของโมดูลเอง อ้างคำสั่งผู้ก่อตั้งตรงตัว "ระวังข้อมูลขัดแย้งด้วย") คือกลไก
บังคับใช้ของหลักการนี้:

- **ไม่เคย merge หรือเลือกแหล่งใดแหล่งหนึ่งแทนอีกแหล่ง** — แถว `observations` ของทั้งสอง source (เช่น
  `bma_watermap` vs `thaiwater_canal_waterlevel`, join ด้วย station code `WL.xxx.NN` เดียวกัน) คงอยู่
  ตรงตามที่เก็บมาเสมอ โมดูลนี้แค่**อ่าน**แล้ว**เขียนแถวใหม่**เข้า `contradictions`
- **เกณฑ์ขัดแย้ง**: ค่าล่าสุดของสอง source ต่างเวลากันเกิน `DISAGREE_MINUTES = 60` นาที **หรือ** ค่าต่างกัน
  เกิน `DISAGREE_LEVEL_M = 0.05` เมตร → เขียนแถว `contradictions` (append-only, ไม่เคยถูกเขียนทับ)
- **ตรงกันก็ต้องโชว์เหมือนกัน**: ถ้าไม่ขัดแย้ง โมดูลไม่เขียนแถว contradiction แต่ผลลัพธ์ยังพก status
  `"AGREE"` ต่อสถานี "เพื่อให้ผู้เรียกแสดงเป็นข้อความเพิ่มความมั่นใจได้" (ตามคำสั่งผู้ก่อตั้ง "ถ้าตรงกันโชว์ด้วย
  เพิ่มความมั่นใจ") — measured ที่ชนะ inferred ไม่ได้แปลว่า inferred หายไป: inferred ยังคงปรากฏ (เช่น
  `governor_shared_flooded_roads` tier `official_shared_inference` ยังอยู่ใน registry เต็ม ไม่ถูกซ่อน
  เพียงเพราะมี telemetry ตรงกว่า)
- **สิ่งที่ยังไม่ reconcile ก็ถูกบันทึกตรงๆ ว่ายังไม่ทำ** ไม่ใช่ถูกข้ามแบบเงียบ — `hii_watergate` ใช้ station
  code scheme คนละแบบ (`gate:hii_watergate:<n>`) ไม่มี cross-walk ที่ verified แล้วไปหา `WL.xxx.NN` —
  docstring บันทึกไว้ตรงๆ ว่า "left OPEN for a future task", ไม่ fuzzy-match เอาเอง
- **burden ledger**: ใครแบกภาระเมื่อสองแหล่งขัดกัน ไม่ใช่หน้าที่ของ reconcile.py ที่จะตัดสิน — เป็นข้อมูล
  เพิ่มให้ผู้อ่าน (เช่น `readout.py`'s "เสียงจากอินเทอร์เน็ต" section ที่อ่าน social listening คู่กับสถานี
  ทางการ ไม่ใช่แทนที่)

### (c) ตัวชี้วัด = ข้อตกลงที่ประกาศ (indicator-as-declared-agreement)

`PROP-FLOOD-01..06` (`toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md`) คือชุดตัวชี้วัดที่ **ประกาศ
ล่วงหน้าไว้ตรงๆ ว่าแต่ละตัวอ่านอะไร** — ไม่ใช่สมการที่ derive มาลอยๆ:

- `R_H(U)` = river/outlet headroom ที่เหลือใน `H` ชั่วโมงข้างหน้า
- `D_H(U)` = drainage clearable volume จากปั๊ม (`0` เมื่อไม่มีปั๊ม — ไม่ใช่การ refuse, คือ `NO_PUMPS_IN_UNIT`)
- `F_H(U)` = forecast inflow volume (ฝน + upstream inflow)
- `S_H(U) := F_H(U) / min(D_H,R_H)` = severity ratio
- `T_act(U)` = ชั่วโมงที่หน่วยจะ "หมดความจุ" — urgency ไม่ใช่แค่ severity
- **Tier ladder L0–L5/LR**: L0 ปกติ, L1 เฝ้าดู, L2 เตรียมตัวได้ยังมีเวลา, L3 ทำตอนนี้ภายในวันนี้, L4
  เร่งด่วนเดี๋ยวนี้, L5 เกินระบบแล้ว, `LR` = REFUSED (ครอบทุกระดับตัวเลข) — เทียบเคียงกับ WMO impact-based
  warning / UNDRR Sendai end-to-end / UK EA Flood Alert-Warning / US NWS Minor-Major-Record / Japan
  keikai-level 5 ใน `TIER_THRESHOLDS_RATIONALE.md` §2 (ไม่มีระบบสากลใดมีแนวคิด `LR`/refusal ตรงๆ —
  เป็นการออกแบบเฉพาะของ PROP-FLOOD-06 เอง)
- **Coverage n/7**: เวกเตอร์ `cov(U)` 7 ส่วน (`rain_obs, rain_fcst, canal_level_vs_lines,
  river_flow_vs_cap, dam_release, pumps_state, upstream_inflow`) แต่ละส่วนเป็น `present`/`stale`/`absent`
  — **ทุก readout ต้องแสดง `tier` คู่กับ `mode` และ `coverage` เสมอ ห้ามแสดง `tier` เดี่ยวๆ** (v4 "consumer
  contract, mandatory, not optional") — FloodConnect เขียน copy ไว้แล้วว่า "ระดับ Lk · ข้อมูล n/7 · อิงจาก …"
- **"ข้อมูลเพิ่มไม่เคยลดระดับ"**: v4 พิสูจน์ใน Coq ว่า `promoter_max` เป็น floor ใต้ทุก mode เสมอ (ไม่ใช่แค่
  PARTIAL) — `full_tier_v4_promoter_monotone` (เพิ่ม coverage ไม่เคยลด tier) และ `full_tier_v4_full_ge_
  partial` (FULL ≥ PARTIAL เสมอบน input เดียวกัน) — แก้ปัญหาที่ v3 เคยให้ PARTIAL "แซง" FULL แบบไม่ตั้งใจ
- **PARTIAL mode คือกติกาวิกฤต** (crisis rule): `LR` สงวนไว้เฉพาะเมื่อ `cov(U)` ว่างเปล่าทั้งหมดจริงๆ —
  แค่มี input จริงหนึ่งตัว (เช่น เกจฝนอย่างเดียว) ก็คำนวณ `PARTIAL` ได้แล้ว จาก promoter table (เช่น
  `RAIN_24H_EXCEEDS_DESIGN` fire ที่ `rain_24h_mm > 80` → ขั้นต่ำ `L3`) แทนที่จะ refuse ทั้งหน่วย — ตรงตาม
  คำสั่งผู้ก่อตั้งตรงตัว: "ทำทั้งหมดให้ระดับโลก แต่พอใช้ได้แม้ข้อมูลไม่ครบ... ขอแค่ข้อมูลจริงแม้เล็กที่สุด
  ในบางสถานการณ์ก็ยังดี"

### (d) ความชอบธรรมจาก falsifier เท่านั้น (legitimacy from falsifiers only)

**ไม่มี external validation lever** (peer review/สถาบันรับรอง) ในคลังนี้ — ความชอบธรรมมาจากการ**ทดสอบ
ย้อนหลังกับเหตุการณ์จริงแล้วรายงานว่าล้มเหลวตรงไหน** เท่านั้น ตัวอย่างที่ใช้งานได้จริงคือ backtest v0→v1:

| ตัวชี้วัด | v0 (min literal) | v1 (C_H + PARTIAL) |
|---|---|---|
| REFUSED share | **92.5%** (1550/1676) | **0.9%** (12/1308) |
| Ayutthaya | REFUSED 320/320 (miss ทั้งหมด) | resolve 164/164, miss = **0%**, แต่ false-alarm 51.6% |
| Hit rate (ท่วมจริง) | ต่ำมาก (BANGKOK_EAST 100% miss) | **49.4%** |
| Miss rate | สูง | **50.6%** |
| False-alarm rate | สูง | **11.7%** |

`BACKTEST_PROP_FLOOD_06_v1.md` §9 พูดตรงๆ ว่า: "`C_H(U)` + PARTIAL mode **แก้ falsifier REFUSED ของ v0
ได้จริง** (92.5%→0.9%)... แต่**ไม่ได้แปลว่าระบบเตือนภัยทำงานถูกต้อง**: 3/7 เหตุการณ์จริง (HATYAI×2, NAN)
เตือนช้ากว่าหรือไม่เตือนเลย" — **นี่คือตัวอย่างการทำงานของกรอบเอง**: falsifier รอบแรก (REFUSED 92.5%) ถูกพบ
และแก้ ไม่ใช่ถูกซ่อน; falsifier รอบสอง (lead time ติดลบที่ Hat Yai/Nan, false-alarm 51.6% ที่ Ayutthaya)
ถูกพบและ**รายงานเปิดเผยต่อทันที** ไม่ใช่ถูกปกปิดเพื่อให้ดูเหมือนระบบ "ใช้ได้แล้ว" — การ calibrate ทำ**เฉพาะ
เหตุการณ์ใหม่**เท่านั้น (ห้าม tune ซ้ำบนข้อมูลเดิม §6 ข้อ 5) และรายงาน hit/false-alarm/lead-time เผยแพร่
เสมอ ไม่ปิดบังตัวเลขแย่

---

## 3. git เป็น readout ของเราเอง

Commit/version ของ Toledo proposal คือบันทึก "เชื่ออะไร ณ เวลานั้น" และการ overturn มันคือ falsifier
loop ที่บันทึกไว้ ไม่ใช่ประวัติที่ถูกลบทิ้ง:

- **v1/v2 (ดั้งเดิม)**: `min(D_H(U), R_H(U))` ตรงตัว — self-contradiction: หน่วยไม่มีปั๊ม (`D_H=0`) ชนะ
  `min` เสมอ ทำให้เมืองริมน้ำไม่มีปั๊ม (อยุธยา) ถูก refuse/เป็นศูนย์ทั้งที่ `R_H` มีค่าจริง
- **v2 (independent review รอบ 1)**: แก้ Coq band-edge, ทำ tier-ladder เป็น total function เดียว, ลบ
  `ZERO_CAPACITY_NONZERO_INFLOW` (กลายเป็น tier `L5` แทน refusal), ประกาศ default ของการ resolve หน่วย
  จาก (lat,lon) (CRS, nearest-k gauge, staleness window)
- **v3 (falsifier backtest v0 พบว่า 92.5% REFUSED)**: เพิ่ม `C_H(U)` case split (แก้ no-pump contradiction)
  + PARTIAL mode (promoter table แทนการ refuse ทั้งหน่วยเมื่อขาด input บางตัว)
- **v4 (independent review รอบ 2 พบ MUST-FIX 2 ข้อ)**: promoter เป็น floor ใต้ทุก mode (ไม่ใช่แค่
  PARTIAL) + พิสูจน์ monotonicity ใน Coq + เปลี่ยน return type เป็น `readout` record บังคับ (`tier` +
  `mode` + `coverage` ผูกกันเสมอ ห้ามแยก)
- **v5 (ยังไม่พบในคลังนี้ ณ เวลาที่เขียนไฟล์นี้)**: `BACKTEST_PROP_FLOOD_06_v1.md` เองระบุว่า "ไม่พบ v4 ที่
  HEAD" ตอนรันงาน แล้วภายหลัง v4 ถูกเพิ่มเข้ามาจริง (independent review รอบ 2) — ประวัตินี้เองคือหลักฐาน
  ว่า commit เป็น readout: ผู้ที่เขียน backtest v1 บันทึกตรงๆ ว่าตนอ้างอิง version ไหน แทนที่จะเดา rule
  ของ version ถัดไปเอง

**กติกา commit-after-every-phase**: ทุก phase งานที่จบแล้วต้อง commit (ไม่ต้อง push) ทันที ไม่รอสะสม — ถ้า
session ล้มระหว่างทาง ประวัติของ readout จะขาดหายไปเฉพาะ phase ที่ยังไม่ commit เท่านั้น ไม่ใช่ทั้งหมด นี่
คือเหตุผลเดียวกับที่ `data/observations.sqlite` เป็น append-only: git log ของ proposal คือ ledger เดียวกัน
ในรูปแบบอื่น — ทั้งคู่มีหน้าที่รักษา "เชื่ออะไร ณ เวลาไหน" ให้ตรวจสอบย้อนกลับได้ ไม่ใช่แค่ backup

---

## 4. กติกาสำหรับแหล่งใหม่ทุกแหล่ง (checklist)

1. **Census row**: เพิ่มแถวใน `sources/registry.yaml` ก่อนโค้ดใดๆ (id, agency.th/en, url, method,
   cadence, format, auth, licence_status, trust_tier ∈ 4 ค่าที่กำหนด, host_rule.max_requests_per_run,
   last_status, variables) — ตาม `tests/test_registry.py` เช็คครบ
2. **One request per URL (per run)**: `collect.py` ห้าม retry loop; BMA host (`weather.bangkok.go.th`,
   `dds.bangkok.go.th`) 403/reset → หยุดแตะ host นั้นทั้ง run (ไม่ใช่แค่ URL เดิม)
3. **Archive raw**: snapshot ดิบเก็บใต้ `raw/live/<source_id>/<UTC timestamp>.<ext>` เสมอ (gitignored
   แต่ทำซ้ำได้)
4. **Tag**: ทุกค่าที่ store ต้องรู้ trust_tier ของตัวเอง — ไม่มีค่าที่ "ไม่มีที่มา"
5. **Join key**: ประกาศ join key ตรงๆ (เช่น station code `WL.xxx.NN`) — ห้าม fuzzy-match แบบเงียบ ถ้ายัง
   ไม่มี cross-walk ที่ verified แล้ว ให้บันทึกเป็น OPEN แทนการเดา
6. **Reconcile against overlapping sources**: ถ้า source ใหม่วัดตัวแปรเดียวกับ source เดิม (variable +
   join key ตรงกัน) ต้องเดินผ่าน `reconcile.py`-style logic (เกณฑ์ `DISAGREE_MINUTES`/`DISAGREE_LEVEL_M`
   หรือเกณฑ์ที่เทียบเท่าสำหรับตัวแปรนั้น)
7. **Contradiction rows**: เขียนแถว `contradictions` เมื่อขัดกัน — append-only, ไม่เขียนทับ, ไม่ resolve แทน
8. **readout_log ต่อ run**: ทุกตัวเลขที่ต้องเทียบข้ามเวลาต้องเขียนแถว `readout_log` — ไม่งั้น
   `readout_history.py` มองไม่เห็น
9. **Never prune**: ไม่มีการลบ/เขียนทับข้อมูลเก่าเพื่อความสวยงาม แม้จะขัดแย้งกันเอง (เช่น 195 vs 200 ปั๊ม)
10. **Licence noted**: `licence_status.text`/`unresolved` ต้องระบุ ไม่ปล่อยว่าง
11. **No personal data**: ไม่เก็บชื่อคนในรายงานชุมชน (soi + สภาพ + เวลา เท่านั้น)

---

## 5. กติกาสำหรับหน่วยพื้นที่ใหม่ทุกจุด (lat, lon)

ตามที่ PROP-FLOOD-06 §8 ระบุไว้ ลำดับการ resolve หน่วย `U` จากพิกัดใดๆ ในประเทศไทย:

1. **Resolve sub-basin**: หา polygon ลุ่มน้ำย่อยที่ครอบพิกัดนั้น (DWR/basin polygon) — ถ้ามีแค่ node
   ลุ่มน้ำ 22 ลุ่มโดยไม่มี polygon → `REFUSED (UNIT_POLYGON_MISSING)` เว้นแต่ประกาศ fallback รัศมี `r`
   วงกลมชัดเจน (INSTINCT, ระบุ `r` เสมอ ไม่แทนแบบเงียบ)
2. **Upstream gauges + travel time**: เดินตามเส้น WATER edge จาก reach/canal node ที่ใกล้ที่สุดเพื่อหา
   outlet ปลายน้ำ (HydroRIVERS, RELAYED)
3. **Pumps/outlets/capacities**: หา `pump_station` asset ในพื้นที่, สถานะ running ล่าสุด (ไม่มีปั๊ม =
   `NO_PUMPS_IN_UNIT` valid case ไม่ใช่ error); `Q_cap,o` จาก capacity ledger ถ้ามี ไม่งั้น
   `REFUSED (OUTLET_CAPACITY_UNKNOWN)`
4. **Rain gauges + ensemble**: เกจทางการในพื้นที่ (หรือ nearest-k=3 ภายใน 10km, ระบุชัด) + forecast
   ensemble ที่พิกัดนั้น; ไม่มี → `REFUSED (NO_GAUGE_IN_UNIT)`
5. **PARTIAL จนกว่าจะ calibrate**: หน่วยใหม่เริ่มที่ PARTIAL mode เสมอจนกว่าจะมีเหตุการณ์จริงมา calibrate
   — ห้ามประกาศ FULL mode ก่อนมีข้อมูลครบตามนิยาม
6. **Calibrate บนเหตุการณ์จริงครั้งแรก**: ปรับ threshold/convention เฉพาะเมื่อมีเหตุการณ์ใหม่จริงเกิดขึ้น
   (ไม่ tune ซ้ำบนข้อมูลเดิมที่เคย tune ไปแล้ว)
7. **Publish per-unit hit/FA/lead**: ทุกหน่วยต้องมีตัวเลข hit rate / false-alarm rate / lead time ของ
   ตัวเองเผยแพร่แยกต่อหน่วย (ไม่รวมยอดข้ามหน่วยจนซ่อนหน่วยที่แย่ — ดู §6 ข้อ averaging)

---

## 6. สิ่งที่กรอบนี้ห้าม

1. **Averaging away disagreement** — ห้ามเฉลี่ยค่าจากสองแหล่งที่ขัดกันเพื่อให้ได้ตัวเลขเดียวที่ "ดูสวย"
   ต้องเก็บทั้งคู่ + เขียนแถว contradiction
2. **แสดง tier โดยไม่มี coverage** — ห้ามแสดง `tier: Lk` เดี่ยวๆ โดยไม่แปะ `mode` + `coverage n/7` (v4
   consumer contract, mandatory)
3. **อ้างความแม่นยำจากความจำ** — ห้ามพูดว่า "ระบบนี้แม่นยำ/ใช้ได้" โดยไม่รัน backtest หรือไม่ระบุว่าเป็น
   INSTINCT/RELAYED
4. **ข้อกล่าวหาเชิงลบต่อหน่วยงานจากแหล่งเดียว** — ห้ามเขียน claim เชิงลบที่ยังไม่ยืนยันเกี่ยวกับหน่วยงาน/
   บุคคลด้วยน้ำเสียงของทีมนี้เองจากแหล่งเดียว (ดูตัวอย่าง `card_opinion..._onetomany...md` ที่เก็บทุกฝ่าย
   เป็น "คำกล่าวอ้างของผู้เขียน" เท่านั้น)
5. **Tune threshold ซ้ำบนข้อมูลเดิม** — calibration ทำได้เฉพาะเหตุการณ์ใหม่ ห้าม re-tune บนชุดข้อมูลที่
   เคยใช้ปรับ threshold ไปแล้ว (จะกลายเป็น overfitting ที่ดูเหมือน validation)
6. **Geocoding/snapping โดยไม่ติดแท็ก INSTINCT + ขอ founder OK** — การจับคู่พิกัด/สถานีแบบเดา (fuzzy) ต้อง
   ประกาศชัดว่าเป็น INSTINCT และรอการอนุมัติ ไม่ทำเงียบๆ

---

## 7. OPEN questions ของกรอบนี้เอง

1. **Lagging gauges**: X.44 (หาดใหญ่) discharge ที่วัดได้ต่ำสุดพอดีช่วงวิกฤตจริง — ไม่สะท้อนเหตุการณ์
   (`BACKTEST_PROP_FLOOD_06_v1.md` §4/§8 ข้อ 2) — INSTINCT ที่ยังไม่ยืนยัน: อยู่ปลายจุดผันน้ำเข้าคลอง ร.1
2. **X.44 ไม่ track หาดใหญ่**: ผลคือ PROP-FLOOD-06 ไม่เคยเตือนทันเวลาที่หาดใหญ่ทั้ง 2553/2565 — falsifier
   เชิงข้อมูล หนักกว่า falsifier เชิง REFUSED เดิม ยังไม่มีทางแก้ในคลังนี้
3. **Control level เป็น null ใน PageMap แต่ปรากฏใน StationDetail**: `BMA_STATION_DETAIL_PROBE.md` พบ
   `water_control` อ่านได้จริงที่ StationDetail แต่ `BMA_WATER_MAP_PROBE.md` (endpoint คนละตัว) เป็น null
   ทุกสถานี — ยังไม่ reconcile สอง endpoint นี้เข้าด้วยกัน
4. **hii_watergate ยังไม่ reconcile**: station-code scheme ต่างจาก `WL.xxx.NN` — `reconcile.py` เขียนไว้
   ตรงๆ ว่า "left OPEN for a future task" ไม่ fuzzy-match
5. **PARTIAL mode ไม่เคยถูกทดสอบกับ canal/pump promoter จริง** — BANGKOK_EAST มี canal/pump feed จริง
   resolve เป็น FULL เสมอ ไม่เคยเข้า PARTIAL — ส่วนของ promoter table ที่ออกแบบมาสำหรับ PARTIAL
   (`CANAL_AT_*`, `PUMPS_ZERO_RUNNING_*`) ยังไม่ผ่านการทดสอบจริงในโหมดนั้นเลย
6. **`DAM_RELEASE_ABOVE_SPILL_THRESHOLD` และ `VULNERABLE_UNIT_PROMOTION`** ยังไม่มี feed ข้อมูลใดใน
   คลังนี้ — ไม่ได้ falsify หรือ verify เลย
7. **S_H ไม่แยกวันท่วม/ไม่ท่วมได้เลยที่ HATYAI/NAN/CHIANGMAI** (§6 ของ backtest v1) — ปัญหาอยู่ที่การ resolve
   ตัวเลขต้นทาง (ERA5 ต่ำกว่าฝนจริง, discharge ไม่สะท้อนวิกฤต) ไม่ใช่ตำแหน่ง threshold — ยังไม่มีทางแก้

---

*ไฟล์นี้เป็นการสังเคราะห์จากเอกสารที่มีอยู่แล้วในคลังนี้และ read-only จาก toledo-wt-flood06 +
readout_genesis — ไม่ใช่ proposal ใหม่ ไม่แก้ไฟล์ต้นทางใดๆ*
