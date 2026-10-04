# Typology "ภูมิทัศน์ + การไหล/การหยุดไหล" (flow-stall typology, ข้อมูลน้อยที่สุด)

**คำสั่งฟาวน์เดอร์ (คำต่อคำ)**: "ทำ typology ให้เห็นภูมิทัศน์ แล้วค่าวัดต่างๆ ทำให้เห็นการไหล และการหยุดไหล
โดยใช้ข้อมูลน้อยที่สุด"

**กติกาที่ยึดตลอดเอกสารนี้ (คำสั่งวันนี้)**: ประตู ≠ ทิศทางการไหล ≠ นิ่ง — สถานะประตู/ปั๊ม, ทิศทางการไหล,
และ "นิ่งหรือไม่นิ่ง" เป็นสามเรื่องต่างกัน อย่าปนกัน. 2-3 การอ่านค่าติดกันพอจะบอกแนวโน้มได้.
ระดับพื้นดิน ≠ ระดับผิวน้ำ. REFUSE เมื่อ datum ไม่ตรงกัน / ข้อมูลเก่าเกิน / Δt > 60 นาที.

**แก้ไขระหว่างงาน (คำต่อคำ, ฟาวน์เดอร์)**: "อย่าลืมว่าไม่มีทางมีข้อมูลพอ แต่ใช้การอนุมานจากข้อมูลที่แข็งแรงเป็นหลัก"
— REFUSED เป็น **ทางเลือกสุดท้าย** ไม่ใช่ค่าเริ่มต้นสำหรับจุดที่ไม่มีเครื่องวัด ต้องมีชั้นการอนุมาน
(inference layer) จากจุดยึด (anchor) ที่แข็งแรงที่สุดก่อนเสมอ — ดูหัวข้อ 4.

รหัสอ้างอิงในเอกสารนี้: `tools/flowmap/flow_stall.py`, `tools/flowmap/render_profile.py`,
`tests/test_flow_stall.py`. ทุกสมการที่ใช้จริงในโค้ดเป็นการ**ประกอบ** (compose) จาก Toledo
PROP-FLOOD-01 กับ PROP-FLOOD-04 ที่ขึ้นทะเบียนแล้ว — **ไม่มีสมการใหม่**ในโค้ดที่รันจริงของงานนี้
(ตัวจัดชั้น F1-F6 ในภาคผนวกท้ายเอกสารเป็นข้อเสนอที่ยังไม่ขึ้นทะเบียน ไม่ถูกเรียกใช้จริง — ดูหัวข้อ 8).

---

## 1. Node kinds / roles

| `kind` (โครงสร้างจริง) | คำอธิบาย |
|---|---|
| `soi_surface` | ผิวซอย/ถนน/สนาม — จุดที่คนอยู่จริง |
| `pond` | บึง/สระ/แก้มลิง |
| `canal_reach` | ช่วงคลองที่ไม่มีโครงสร้างควบคุม |
| `culvert` | ท่อลอด (หน้าตัดจำกัด) |
| `gate` | ประตูระบายน้ำ |
| `pump` | สถานีสูบ |
| `river` | แม่น้ำ |
| `sea` | ทะเล/ปากแม่น้ำ |

นอกจาก `kind` แต่ละ node ยังมี `role` (ศัพท์ typology, สกัดจากข้อเสนอภายนอกที่ฟาวน์เดอร์ส่งมา
2026-09-27, tag `RELAYED-external-proposal -> adopted-as-convention` — เป็น**คำอธิบายตำแหน่งใน
สาย ไม่ใช่การวัด**):

| `role` | ความหมาย |
|---|---|
| `source` | ต้นทาง/จุดกระตุ้น (ฝน/น้ำต้นทางนอกพื้นที่) |
| `local_surface` | ผิวน้ำ/ผิวดินในพื้นที่ (= `soi_surface` ส่วนใหญ่) |
| `storage` | ที่เก็บกักน้ำ (= `pond` ส่วนใหญ่) |
| `connector` | ทางเชื่อมไม่มีควบคุม (= `canal_reach`/`culvert` ส่วนใหญ่) |
| `control` | มีโครงสร้างควบคุม (= `gate`/`pump`) |
| `receiver` | ปลายทางรับน้ำ (= `river`/`sea`) |

Terrain attrs สี่ตัวต่อ node (แต่ละตัวมี `value` + `tag` + `source`, `tag="OPEN"` แปลว่ายังไม่มีการ
ประกาศ — ห้ามเดา):

- `ground_m_msl` — ระดับพื้นดิน/พื้นผิว (เช่น RTSD 2553, ดู §5)
- `bed_m_msl` — ระดับท้องคลอง
- `bank_m_msl` — ระดับสันคลอง
- `control_m_msl` — ระดับควบคุม/เป้าหมายของประตู (BMA `StationDetail`'s `txt_water_control`
  เมื่อมี — ดู `docs/knowledge/BMA_STATION_DETAIL_PROBE.md`)

แต่ละ node ยังพก `readings: list[Reading]` (ชุดค่าที่เก็บสะสมจริง — `value`, `observed_at`,
`datum`, `sensor_status` (`ok`/`faulted`/`unknown`), `tag` ตามบันไดความแข็งแรงในหัวข้อ 3).
**ค่าที่ sensor_status="faulted" ไม่ถูกเชื่อถือเลย** — ตัดออกก่อนคำนวณใด ๆ (`Node.valid_readings()`).

## 2. Edge kinds

`edge_kind` (ศัพท์ typology จากข้อเสนอภายนอกเดียวกัน):

| `edge_kind` | ความหมาย |
|---|---|
| `open_gravity` | เชื่อมแบบเปิด ไหลตามแรงโน้มถ่วง ไม่มีโครงสร้างกั้น |
| `constrained_gravity` | ไหลตามแรงโน้มถ่วงแต่ถูกจำกัดหน้าตัด (ท่อ/culvert) |
| `controlled` | มีประตู/ปั๊มควบคุม |
| `backflow_risk` | เสี่ยงน้ำไหลย้อน (ปลายทางสูงกว่าต้นทางได้เมื่อน้ำหนุน) |
| `unknown` | ยังไม่ประกาศ |

Edge หนึ่งเส้นพก `design_direction` (relay, ไม่ใช่การวัด — เหมือน `canal_graph.py`),
`control_structures`, และ (ถ้ามี) `gate_opening_m`/`pumps_on`/`pumps_total` ที่ **วัดจริง**
(เช่น BMA `PumpHistory`) พร้อม tag ความแข็งแรงของแหล่งที่มา.

## 3. บันไดความแข็งแรงของหลักฐาน (evidence-strength ladder)

```
VERIFIED_LIVE (4)  >  VERIFIED_STALE (3)  >  RELAYED (2)  >  COMMUNITY (1)  >  INSTINCT (0)
```

ใช้ตัดสิน `confidence`/`strength` ของทุกผลลัพธ์ (ทั้งที่วัดจริงและที่อนุมาน) — ความมั่นใจของค่าที่
ประกอบจากหลายแหล่งเท่ากับ**ความแข็งแรงของแหล่งที่อ่อนที่สุด**ที่ใช้เสมอ (min, ไม่ใช่ average).

Inference ladder (จากข้อเสนอภายนอก, ผูกกับ field `inference_rung`):

| rung | เมื่อไหร่ |
|---|---|
| `observed` | วัดตรง (PROP-FLOOD-01/04 คำนวณได้จริง จากเครื่องวัดของ node/edge เอง) |
| `strong_inference` | อนุมานจากจุดยึดที่**วัดจริง** (measured anchor) ผ่านกฎในหัวข้อ 4 |
| `weak_inference` | อนุมานจากรายงานชุมชนล้วน ๆ ไม่มีจุดยึดที่วัดจริงเลย |
| `refuse` | ไม่มีจุดยึดใด ๆ เชื่อมถึงได้ในองค์ประกอบที่เชื่อมกัน (connected component) เลย |

## 4. กติกาการอนุมาน (declared consistency rules, INSTINCT-rule — ไม่ใช่สมการ Toledo)

REFUSED คือทางเลือกสุดท้าย (ใช้เมื่อไม่มีจุดยึดใด ๆ เชื่อมถึงเลย). ก่อนถึงจุดนั้น
`tools/flowmap/flow_stall.py::_infer_runs()` พยายามกฎสองข้อนี้กับ "ช่วง" (run) ของ node/edge
ที่ไม่มีข้อมูลตรง ล้อมด้วยจุดยึด (anchor = node ที่มี trend วัดตรงได้):

- **RULE-STALL-01** ("ไม่มีทางลด ทั้งที่ควรลดได้"): ถ้าจุดยึดปลายทางของช่วงนั้น**นิ่งต่อเนื่อง**
  ในหน้าต่างเวลาที่ประกาศ (ดูนิยาม `_is_persistently_stalled()` ด้านล่าง) **และ**
  จำนวนปั๊มที่ทำงานจริง (วัดจริง) บนเส้นเชื่อมในช่วงนั้น = 0 **และ** มีรายงานชุมชนภายในช่วงว่า
  "น้ำยังไม่ลด" → อนุมานว่าทั้งช่วง (node + edge ทุกตัวที่ไม่มีข้อมูลตรง) **นิ่ง (STALLED)**,
  `confidence` = ค่าที่อ่อนที่สุดในสามหลักฐาน (จุดยึด/ปั๊ม/ชุมชน).
- **RULE-DIR-01** ("จุดยึดสองข้างไปทางเดียวกัน"): ถ้าช่วงถูกล้อมด้วยจุดยึดสองจุด (ต้น-ปลาย) และ
  ทั้งคู่มี trend เดียวกัน (ขึ้นทั้งคู่ หรือ ลงทั้งคู่) → อนุมานว่าช่วงกลางเคลื่อนไปทางเดียวกัน,
  `confidence` = ค่าที่อ่อนที่สุดของจุดยึดทั้งสอง. (ข้อจำกัดที่ประกาศไว้: ไม่ตรวจสอบว่ามีโครงสร้าง
  ควบคุมซ่อนอยู่กลางช่วงหรือไม่ — ถ้ามีต้องประกาศเป็น edge_kind=`controlled` แยกเพื่อตัดช่วงให้สั้นลง)
- **RULE-COMMUNITY-01** (weak): ถ้าไม่มีจุดยึดที่วัดจริงเชื่อมถึงเลย แต่มีรายงานชุมชนตรง node นั้น →
  อนุมานแบบอ่อน (`weak_inference`), ไม่ใช่ REFUSED, แต่ก็ไม่ใช่ `strong_inference`.
- ไม่มีข้อไหนใช้ได้เลย → **REFUSED** (`MISSING_INPUT`/`STALE_INPUT`/`DATUM_MISMATCH`/
  `UNDECLARED_EDGE`, เหมือน `canal_graph.py`).

`_is_persistently_stalled(node, ref_iso, persistence_hours, epsilon_m)`: นิ่งต่อเนื่อง = ทุกค่าที่
เชื่อถือได้ (ไม่ faulted) ภายในหน้าต่าง `persistence_hours` อยู่ในช่วง `epsilon_m` เดียวกันทั้งหมด
(max-min <= epsilon). เป็นการต่อยอดวินัยเดียวกับ PROP-FLOOD-01 (เทียบผลต่างที่เก็บจริงกับ epsilon
ที่ประกาศ) แค่ขยายจาก 2 จุดเป็นทั้งหน้าต่าง — **ไม่ใช่สมการใหม่**, tag `INSTINCT-rule`.

**Epsilon สองตัว แยกกันโดยเจตนา**:
- `canal_graph.py`'s `DEFAULT_EPSILON_M = 0.02` ม. (INSTINCT) — สำหรับ PROP-FLOOD-04 เทียบ
  ค่า 2 จุดตอนเดียวกัน (sensor-resolution ของ BMA, 2 ทศนิยม).
- `flow_stall.py`'s `DEFAULT_EPSILON_M = 0.03` ม. (**OPEN-convention**, แถบประกาศ 0.02–0.05 ม.,
  สกัดจากข้อเสนอภายนอก) — สำหรับชั้นอนุมานของโมดูลนี้ (persistence window, ความสำคัญของหัวน้ำใน
  head ledger). ทั้งสองไม่แทนกัน — อย่าใช้ค่าใดค่าหนึ่งแทนอีกตัวในโค้ด.

## 4b. ส่วนขยายจาก flood69 KlongMap-proxy probe (RELAYED-via-KlongMap-schema)

`docs/knowledge/card_thirdparty_flood69_peoplesparty_dashboard.md` (probe แยก, third-party
proxy/cache 5 นาทีของ BMA KlongMap เอง — **ไม่ใช่แหล่งวัดของตัวเอง**, `waterStation` payload
ทุกฟิลด์เป็น `null` ในสแนปช็อตที่ probe — **OPEN**, ใช้ได้แค่เป็น gap-filler ของ**โครงสร้าง/
เค้าโครง** ไม่ใช่ระดับน้ำสด) ชี้ 3 field ที่ schema ของเขามีแต่ของเราไม่มี — รับเข้ามาเป็น field
เสริม (ไม่ใช่สมการใหม่):

- **`Edge.flow_direction_state`** (`forward`/`reverse`/`unknown`) — ทิศทาง**ที่ประกาศไว้/ปกติ**
  แยกจาก `direction` ที่วัดจริงจาก ΔH (PROP-FLOOD-04). `EdgeFlowResult.declared_direction` +
  `backflow_flag` เทียบสองค่านี้ — ติดธง **เฉพาะ**เมื่อทั้งคู่รู้ค่าจริงและไม่ตรงกัน (ไม่เดาเมื่อ
  วัดจริงเป็น UNRESOLVED/REFUSED) → นี่คือสัญญาณ**น้ำไหลย้อน** (backflow) แบบ first-class.
- **`Edge.leg_label`/`warning_m`/`critical_m`**: สถานีที่มี 2 ทางออก (out01/out02) ใช้ 1 `Edge`
  ต่อ 1 ขา — threshold เป็นของ edge นั้นเอง ไม่ใช้ชุดเดียวกันข้ามขา (ต่างจาก
  `BMA_STATION_DETAIL_PROBE.md`'s `water_control` เดี่ยวต่อสถานี).
- **`Node.profile_order`**: ลำดับตามคลอง (เหมือน `listRiverMap.profile_order`) —
  `chain_order_from_profile()` เรียงตามนี้ก่อน, node ที่ยังไม่ประกาศ (`OPEN`) ต่อท้ายตามลำดับเดิม
  ไม่สลับแซงตัวที่ประกาศแล้ว.

ทั้งสามอย่างเป็น**ฟิลด์ประกาศ** ไม่ใช่การคำนวณใหม่ — การเทียบ `declared_direction` vs. `direction`
ก็เป็นการเปรียบเทียบตรง ๆ (equality check) ไม่ใช่สูตร.

## 5. การทั่วไป (generalisation) — ใช้ได้กับหน่วยใดก็ตามที่ resolve จาก (lat, lon)

Chain/graph ในโมดูลนี้ไม่ผูกกับสัมมากรโดยตรง — สร้างจากขอบเขต `WATER`/`DRAINS_TO`/`OUTFALL`
ของ knowledge graph (`docs/FLOODCONNECT_TOPOLOGY.md`, `output/thailand_water_kg.graphml`)
รอบพิกัดใดก็ได้: (1) resolve (lat, lon) → district/asset ใกล้ที่สุดผ่าน `assets_registry.py`,
(2) เดินตามขอบ `WATER`/`DRAINS_TO` ในกราฟเพื่อประกาศ node/edge chain (เหมือนที่ maintainer
ประกาศ `site/inputs/canals/east_chain.yaml` ด้วยมือ — งานถัดไปคือ generate อัตโนมัติจากกราฟ),
(3) ผูก terrain attrs จาก `sources/bkk_district_elevation.yaml` (ground, coarse) +
`sources/capacity_ledger.yaml`/`docs/knowledge/BMA_STATION_DETAIL_PROBE.md` (bed/bank/control
เมื่อมี), (4) ผูก readings จาก `data/observations.sqlite` ตาม `station_code`, (5) เรียก
`compute_chain()`. ไม่มีขั้นตอนไหนผูกกับชื่อสถานที่ตายตัว.

## 6. ต้นแบบสัมมากร (Sammakorn prototype) — อ่านผลจริงจากรันนี้ (2026-09-27)

สร้างจาก `data/observations.sqlite` จริง (ไม่ปั้นค่า) ผ่านสายหลัก:
ซอย → บึงที่ 1/2/4 (เซนเซอร์ปั๊ม ST.SPS.01-04 อ่านสถานะ `ขัดข้อง`, `pumps_on=0` จากทั้ง 11 เครื่อง
รวมกัน, MEASURED) → คลองบ้านม้า 2 (ไม่มีเครื่องวัด) → ท่อลอดรามคำแหง (ไม่มีเครื่องวัด) → ST.SPS.01 →
WL.SSB.08 (ชุดข้อมูลจริง) → WL.SSB.07 (ชุดข้อมูลจริง) → พระโขนง (ไม่มีชุดข้อมูลในต้นแบบนี้);
กับแขนงใต้ วังใหญ่บน (ไม่มีเครื่องวัด) → หัวหมาก WL.HMK.01 (ชุดข้อมูลจริง) ต่อจากบึงที่ 4.
บวกตัวอย่างเส้นเชื่อมที่มีข้อมูลครบ: บางชัน WL.SSB.09 → เสรีไทย 24 WL.SSB.08 (ทั้งสองมีเครื่องวัด).

**ผลลัพธ์การรันจริง**: OK (วัดตรง) 2 เส้น, INFERRED (อนุมาน) 2 เส้น, REFUSED 6 เส้น.

**ข้อสังเกตสำคัญ (ตรวจสอบก่อนใช้คำสั่งของฟาวน์เดอร์ตรง ๆ)**: คำสั่งที่ส่งต่อมาระบุ "WL.SSB.08 ปกติ
−0.12 ม. ต่อเนื่อง 30+ ชม." — **ตรวจกับ `data/observations.sqlite` แบบเต็ม (36 แถวใน 30 ชม.
ล่าสุด) แล้ว ข้อมูลจริงไม่สนับสนุนคำกล่าวนี้** (ช่วงค่าจริง −0.67 ถึง 0.80 ม., พิสัย 1.47 ม. — มี
เหตุการณ์จริงเกิดขึ้นในช่วงนั้น) — จึงไม่ใช้ RULE-STALL-01 กับสายหลัก (soi→pond2→banma→culvert→
sps01→ssb08) ทั้งหมดยังคง **REFUSED** อย่างสัตย์จริง ไม่ใช่บั๊ก. ตรงกันข้าม **WL.SSB.07 (พิสัย 0.00 ม.
ตลอด 30 ชม., คงที่ 0.40 ม.) และ WL.HMK.01 (พิสัย 0.03 ม. ตลอด 30 ชม.) นิ่งจริง** — แขนงใต้
(บึงที่ 4 → วังใหญ่บน → หัวหมาก) จึงอนุมาน **STALLED** ได้จริงผ่าน RULE-STALL-01 (จุดยึด=หัวหมาก,
ปั๊ม=0/11 วัดจริง, ชุมชน="ยังไม่ลด" — ข้อความหลังนี้เป็นคำที่ฟาวน์เดอร์ relay มาเอง 13:05,
tag `COMMUNITY`/`RELAYED-by-founder`, ยังไม่ได้ตรวจสอบอิสระเพราะ
`docs/SAMMAKORN_STANDING_WATER_2026-09-27.md` ที่ผู้ร่วมงานอีกคนกำลังเขียนยังไม่มีอยู่ตอนรันนี้).

**next_measurement (อันดับสูงสุด)**: `sps01` และ `pkn01` (แต่ละจุดจะปลด REFUSED ได้ 1 เส้นทันที
เพราะติดกับจุดยึดที่วัดจริงอยู่แล้ว คือ ssb08 และ ssb07 ตามลำดับ) — ไม่ใช่ตัวบึงเองตามที่คาดไว้แต่แรก
เพราะบึงอยู่ห่างจากจุดยึดที่วัดจริง 3-4 ปล้อง (การวัดที่บึงเพียงจุดเดียวยังไม่ปลด edge ใดได้ทันที
จนกว่า soi/banma/culvert จะมีจุดใดจุดหนึ่งวัดด้วย) — เมตริกนี้นับเฉพาะ "ปลดได้ทันทีด้วยการวัดเพิ่ม
1 จุด" ตามที่งานนี้ระบุ ไม่ใช่ศักยภาพสะสมหลายปล้อง (บันทึกไว้เป็นข้อจำกัดที่ประกาศ, ไม่ใช่บั๊ก).

SVG ต้นแบบ: `site/dist/prototype/flow_profile_sammakorn.svg` (สายหลัก),
`site/dist/prototype/flow_profile_sammakorn_south.svg` (แขนงใต้),
`site/dist/prototype/flow_profile_east_example.svg` (ตัวอย่างเส้นเชื่อมข้อมูลครบ).
สร้างจาก script ต้นแบบที่ไม่ได้ commit (scratch, งานนี้เป็น prototype only) — ผู้รับช่วงที่จะ wire
เข้า `build_data.py`/`build_page.py` ต้อง**เขียน builder ใหม่ใน repo จริง** โดยอ่านค่าจาก
`data/observations.sqlite` + `site/inputs/canals/east_chain.yaml` (ขยาย schema ตามหัวข้อ 7).

## 7. ขั้นตอน wiring สำหรับผู้ร่วมงานที่ commit (ไม่ทำในงานนี้)

1. เพิ่ม section ใหม่ใน `site/build_data.py`: `"ภูมิทัศน์และการไหล"` (ชื่อ key ใน `data.json`) —
   เรียก `tools.flowmap.flow_stall.compute_chain()` ด้วย node/edge ที่ประกอบจาก
   `site/inputs/canals/east_chain.yaml` (ขยาย node แต่ละตัวด้วย `ground_m_msl`/`bed_m_msl`/
   `bank_m_msl`/`control_m_msl` เมื่อมีแหล่งจริง) + `canal_by_code`/`bma_pumphistory` ที่มีอยู่แล้ว.
2. เพิ่ม attribute ใหม่ในกราฟความรู้ (KG, `output/thailand_water_kg.graphml`): แต่ละ
   `canal_node`/`asset` ผูก `ground_m_msl`/`bed_m_msl`/`bank_m_msl`/`control_m_msl` (attrs ใหม่,
   ค่า default `None`/`tag=OPEN`) เพื่อให้ `classify_landscape_type()`/renderer เดินตามกราฟจริง
   แทนที่จะพึ่งพา `east_chain.yaml` ที่ประกาศมือเพียงไฟล์เดียว.
3. เรียก `tools.flowmap.render_profile.render_profile_svg()` จาก `build_page.py` แทนการ generate
   SVG แยก, สลับ literal hex ในหัวไฟล์ `render_profile.py` เป็น `var(--ok)`/`var(--warning-text)`/
   `var(--alert)`/`var(--accent-2)`/`var(--border)`/`var(--bg)`/`var(--surface)`/`var(--text)`
   จริง (ตอนนี้เป็น literal hex เพราะ SVG ต้นแบบนี้ยืนอิสระ ไม่อยู่ใน cascade ของหน้าเว็บ).
4. **Maker ≠ checker**: ก่อน publish ต้องผ่าน adversarial review (leak scan + tier fidelity)
   เหมือนทุก publish อื่นของ repo นี้ (maker ≠ checker, leak scan ก่อน publish).

## 8. ภาคผนวก — ตัวจัดชั้น F1-F6 (candidate PROP-FLOOD-07, **ยังไม่ขึ้นทะเบียน, ไม่ถูกเรียกใช้จริง**)

ฟาวน์เดอร์ส่งข้อเสนอจากผู้ช่วยภายนอกมาให้ "สกัดเฉพาะที่มีประโยชน์ออกมาเสริมระดับสมการเรา" — หัวข้อ 1-6
ด้านบนเป็นส่วนที่รับมาแล้ว (คำศัพท์/vocabulary เท่านั้น, ไม่ใช่สมการ). ส่วนนี้คือสูตรจัดชั้นที่ผู้เสนอ
เรียกว่า F1-F6 — **ยังไม่ผ่าน Toledo, ห้ามอ้างเป็นทฤษฎีบท, ห้ามใช้กับหน้าเว็บสาธารณะจนกว่าจะขึ้น
ทะเบียนสำเร็จ**. งานนี้เพียงร่างข้อความผู้สมัคร (candidate statement) ไว้ให้ทีม Toledo ไปขึ้นทะเบียน
ต่อ — ไม่ได้ขึ้นทะเบียนเอง, ไม่ได้เขียนโค้ดเรียกใช้จริงที่ไหนเลยในงานนี้.

**ผู้ปกครอง (parents)**: PROP-FLOOD-01 (lag-k trend), PROP-FLOOD-04 (edge_direction),
PROP-FLOOD-05a (burden ledger — ใช้เฉพาะกรณีต้องอ้างฝั่งที่แบกรับภาระ).

**Inputs (ประกาศ)**:
- `ΔH1` := ผลต่างระดับผิวน้ำ (จาก PROP-FLOOD-04) บนเส้นเชื่อม บึง/บ้านม้า 2 → แสนแสบ
  ("ออกจากหมู่บ้านได้ไหม")
- `ΔH2` := ผลต่างระดับผิวน้ำ บนเส้นเชื่อม ผิวซอย → บึง ("น้ำจากซอยลงบึงได้ไหม")
- `ε` := แถบ noise ที่ประกาศ (ตกลงกันที่ 0.02–0.05 ม., **OPEN-convention** — ยังไม่ใช่ค่าวัด
  ความแม่นยำเซนเซอร์จริงจากผู้ผลิต)
- สถานะโครงสร้างควบคุม (ปั๊ม/ประตู, MEASURED เมื่อมี, รวมสถานะ fault)
- รายงานน้ำไหลย้อน/ล้นบึงจากชุมชน (COMMUNITY)
- ธง datum-mismatch / staleness / conflict (จาก PROP-FLOOD-04/reconcile.py)

**Outputs (F1-F6)**: F1 ไหลอิสระ (free drainage) · F2 ล่าช้า (delayed) · F3 ติดขัด
(blocked — `ΔH>ε` แต่ไม่มีการลดลงต่อเนื่อง → บ่งชี้โครงสร้าง ไม่ใช่ตัวน้ำเอง) · F4 น้ำหนุน/ย้อน
(tailwater/backwater — `ΔH<=0`) · F5 ล้นภายใน (internal surcharge — มีรายงานไหลย้อน/บึงล้น) ·
**F6 ไม่ทราบแต่มีขอบเขต (unknown-but-bounded)** — สถานะที่พบบ่อยที่สุดตามความสัตย์จริง, ต้องแสดง
รายการ **สิ่งที่ตัดออกได้แล้ว** และ **สิ่งที่ยังเหลือเป็นไปได้** เสมอ ไม่ใช่แค่เครื่องหมาย "?" เฉย ๆ.

**Refusal**: ข้อมูลเก่าเกิน/ขัดแย้งกันเอง → **F6** (ไม่ใช่ REFUSED เฉย ๆ — ต่างจาก PROP-FLOOD-04
ที่ REFUSED เป็น first-class outcome; F6 ยังต้องพกรายการที่ตัดออกได้).

**กฎ 1-6 (ผู้เสนอ, ยังไม่ตรวจ)**: (1) `ΔH>ε` และมีการลดลงต่อเนื่อง → candidate F1/F2; (2)
`ΔH>ε` แต่ไม่มีการลดลง → candidate F3 (บล็อก); (3) `ΔH<=0` → candidate F4; (4) มีรายงานไหลย้อน →
เพิ่มน้ำหนักให้ F5; (5) **ปั๊ม/ประตูขัดข้อง (fault) → ให้บอกว่า "ความล้มเหลวของโครงสร้างอาจครอบงำ
สถานการณ์" ห้ามพูดว่า "ตามทฤษฎีน้ำไหลได้"**; (6) ข้อมูลเก่า/ขัดแย้งกัน → F6 เสมอ ไม่ใช่ REFUSED.

**ไม่รับ**: ตัวเลขตัวอย่าง `+0.83`/`−0.11` = `0.94` ที่แนบมาในข้อเสนอเดิม — เป็นตัวเลขสมมติ ไม่มี
แหล่ง/datum ที่ตรวจสอบได้ ไม่ถูกใช้ที่ไหนในเอกสารหรือโค้ดนี้เลย. การอ้างว่าสัมมากรเป็น "ประเภท 3+6"
ก็ไม่รับเป็นข้อสรุปสำเร็จรูป — `classify_landscape_type()` ในโค้ดจริงคำนวณจากจุดยึดของการรันนั้น ๆ
เสมอ และคืนค่าพร้อม `inferred=True` + รายชื่อจุดยึดทุกครั้ง (ดูหัวข้อ 6: ผลจริงจากรันนี้ได้ประเภท 6).

**สถานะ**: `NEW DERIVATION / PROPOSAL`, ไม่ใช่ทฤษฎีบท Toledo. ผู้ที่จะเปิด Toledo PR ต้องอ่าน
`toledo/EQUATION_SOURCE_POLICY.md` ก่อน แล้วเทียบ equivalence กับ registry/CANONICAL.json +
registry/proposals/*.json ตามลำดับ Toledo-first (ไม่ใช่งานของ worker นี้).

## 9. Tests

`tests/test_flow_stall.py` — สาย 4 node สังเคราะห์ (a→b→c→d): (1) 2 การอ่านค่าให้ทิศทางได้จริง
(PROP-FLOOD-04 ผ่าน `canal_graph.edge_direction()` ตรง ๆ); (2) เซนเซอร์ fault → REFUSED ไม่มีการ
ปั้นค่า; (3) ตรวจจับ "นิ่ง" (STALLED) และ "ขึ้น" (MOVING_UP) ผ่านค่าย้อนหลัง; (4)+(5) ชั้นอนุมาน:
RULE-STALL-01 ยิงเมื่อจุดยึดนิ่งจริง+ปั๊ม 0+รายงานชุมชนครบ, RULE-DIR-01 ยิงเมื่อจุดยึดสองข้างไปทาง
เดียวกัน; (6) ไม่มีจุดยึดเลย → REFUSED จริง ไม่ใช่ค่าเดา; (7) next_measurement แนะนำ node ที่ถูกต้อง;
(8) `classify_landscape_type()` ติด `inferred=True` เสมอ.

## 10. ส่วนขยาย typology: agency/resource/warning_channel/sensor (2026-09-28)

**คำสั่งฟาวน์เดอร์ (คำต่อคำ)**: "ทำให้เชื่อมกันหละ" — แปลงข้อเสนอ `FLOW_STALL_TYPOLOGY_EXTENSION_
PROPOSAL_2026-09-28.md` (proposal-only ตอนนั้น) เป็นกราฟที่เชื่อมกันจริงในคลังนี้ (ไม่ใช่แค่เอกสาร).
ไม่แทนที่หัวข้อ 1-9 ด้านบน — **เพิ่มชั้น** (layer) บน node/edge เดิม ตามหลักการ §0 ของข้อเสนอเดิม.

**Node kind ใหม่ 3 ตัว** (บวก `sensor` เสริม, ไม่บังคับ — แยกจาก `Node.readings` เดิมซึ่งไม่ถูกแตะ):

| `kind` | `layer` | คำอธิบาย |
|---|---|---|
| `agency` | `power`/`civil` | หน่วยงาน/ตำแหน่งที่ถืออำนาจ/ข้อมูล — `agency_class` แยกภาครัฐ (`state`)
  จากภาคประชาชน (`juristic_village`/`volunteer_informal`/`local_shop`/`online_community_group`/
  `media_radio`/`foundation`) |
| `resource` | `resource` | ทรัพยากรตอบสนอง (รถ/เรือ/อาหาร/ทีมแพทย์/จุดรับบริจาค) |
| `warning_channel` | `power` | ช่องทางออกคำเตือน แยกจากตัวหน่วยงานผู้ออก (CAP 1.2 sender ≠ channel) |
| `sensor` (เสริม) | `water` | ผู้เป็นเจ้าของ/มองเห็นเซนเซอร์จุดหนึ่ง แยกจาก node ทางน้ำที่มันติดตั้งอยู่ |

**Edge kind ใหม่ 6 ตัว** (closed vocabulary, ปิดคำศัพท์ — `owned_by`/`operates`/`decides`/`warns`/
`supplies`/`reports_to`) ผูกเข้ากับ `flows_to` เดิม (คือ `open_gravity`/`constrained_gravity`/
`controlled`/`backflow_risk`/`unknown` ของหัวข้อ 2 เมื่อสร้างเป็นกราฟจริง — `tools/typology/
build_graph.py` เก็บทุกเส้นทางน้ำเป็น `kind=flows_to` เดียว พก `design_direction`/`control_
structures` เดิมของ east_chain.yaml ไว้ครบ ไม่ทิ้งข้อมูล):

| `edge_kind` | `from_kind → to_kind` | cardinality |
|---|---|---|
| `owned_by` | `sensor \| gate \| pump → agency` | many→1 (exactly-one, บังคับ) |
| `operates` | `agency → gate \| pump` | many→many |
| `decides` | `agency → gate \| pump` **เท่านั้น** | many→many |
| `warns` | `agency → warning_channel → soi_surface` (2-hop เสมอ) | 1→many→many |
| `supplies` | `resource → soi_surface \| node` | many→many |
| `reports_to` | `soi_surface \| community-agency → node \| soi_surface` | many→many |

**แก้ไขตามรีวิวอิสระ 2026-09-28 (ก่อน build จริง)**:
1. `decides` **ไม่ชี้ไปที่ `edge` อีกต่อไป** — ข้อเสนอฉบับแรกอนุญาต `agency → gate|pump|edge`; ตัด
   `edge` ออก. ภาระ (`BURDENED`/`RELIEVED`, PROP-FLOOD-05a/05b) ยังอยู่ที่ attribute เดิมบน edge น้ำ
   ผ่านประตูเหมือนเดิม ไม่ใช่ edge kind ใหม่ และไม่ใช่เป้าหมายของ `decides` (`tools/typology/
   validate.py::rule_decides_target_kind()` บังคับเป็น schema error ถ้าละเมิด).
2. จำนวนปั๊มสัมมากร: ข้อเสนอเดิมปนกัน "0/11" (ติด MEASURED) กับ "0/4" — คลังนี้เองบันทึกไว้แล้วว่า
   เป็นความขัดแย้งที่ยังเปิดอยู่ (`docs/LAYER0_IN_OUT_CAPACITY.md` §7, `FOUNDER_TASKS_2026-09-27.md`
   "OPEN conflicts"). โมเดลเป็น **4 สถานี** (`ST.SPS.01-04`, ทั้งหมด "ขัดข้อง") แต่ละสถานีพก machine
   count ของตัวเองแยกจากกัน (`typology/nodes/sensors.yaml`'s `aggregate_readouts`) — ทุกที่เขียนว่า
   **"สถานี 4/4 ขัดข้อง · เครื่อง 0/11 เดิน"** เสมอ ไม่ใช่ "0/11" เดี่ยว ๆ, ความต่างระดับสถานี/เครื่อง
   ติด tag `OPEN` อ้างอิงหมายเหตุข้างต้น.

**id scheme** (§4a ของข้อเสนอเดิม, reuse-first): water node `WL.<CODE>`/`ST.<CODE>` (จาก
`site/inputs/canals/east_chain.yaml` + `site/build_data.py`'s `SAMMAKORN_CHAIN_NODES` สำหรับ
`WL.SMK.01`/`WL.BMA.02` ที่ east_chain.yaml เองประกาศ `canal_oldcode: null` — สอง coding นี้อ้างถึง
โครงสร้างจริงเดียวกัน, เก็บเป็น `east_chain_key_alias` แทนการเลือกทิ้งอันใดอันหนึ่ง); `agency`
`AG_<SHORT_CODE>` (**reuse ตรงจาก `docs/knowledge/water_system_dag.mmd` เสมอเมื่อมีอยู่แล้ว** — ตรวจ
จริงแล้วพบว่า `AG_MEA`/`AG_ESTATE` มีอยู่แล้ว ต่างจากที่ข้อเสนอเดิมอ้างว่า "หายไป" ทั้งคู่ — ดู
`typology/nodes/agencies.yaml`); `sensor` `SENSOR.<water code>`; `resource`
`RES.<TYPE>.<OWNER>.<seq>`; `warning_channel` `WCH.<NAME_SLUG>`; `soi`/zone `SOI.<AREA>.<slug>`
(convention เดียวกับ `social_listening.py::_extract_soi()`).

**ไฟล์**:
- `typology/nodes/{agencies,resources,warning_channels,sensors}.yaml` — registry มือ, ทุกแถวมี
  `id`/`kind`/`layer`/`label_th`/`tag`/`source`.
- `typology/edges/{owned_by,operates,decides,warns,supplies,reports_to}.yaml` — registry มือ, ทุก
  แถวมี `from`/`to`/`tag`/`source`; `to`/`from: "OPEN"` = ยังไม่ยืนยัน (ห้ามเดา, ไม่ใช่การละเว้น).
- `tools/typology/build_graph.py` — ประกอบกราฟ water layer (east_chain.yaml, แทรก `pump` node
  จาก `control_structures`) + registry เข้าด้วยกันเป็น `networkx.MultiDiGraph` เดียว, เขียน
  `output/typology_graph.json` (โหนดลิงก์ทุกชั้น) + `output/typology_sammakorn_subgraph.json`
  (สายสัมมากรทำงานจริง ± 2 hop). **แก้ 2026-09-28 หลังรีวิวอิสระพบว่าสายเดิม (ปั๊มต่อกันเป็นชุด,
  ไม่มีเส้นเชื่อมสายสัมมากรกับสายแสนแสบเลย) ไม่ตรงกับที่ build จริง** — สายเหนือ (ทางออกจริงสู่แสนแสบ)
  อ่านตรงจาก `site/build_data.py`'s `SAMMAKORN_CHAIN_EDGES` (ไม่ใช่เดาจากพิกัด, ดู
  `docs/TYPOLOGY_GRAPH.md` "Sammakorn worked chain" สำหรับสายเต็ม+วิธี reproduce).
- `tools/typology/validate.py` — ตรวจกติกาการเชื่อม §4c ของข้อเสนอเดิม: ไม่มี node ลอย, `sensor`
  มี `owned_by` เท่ากับ 1 เส้นเสมอ, `gate`/`pump` มี `operates`+`decides` อย่างน้อย 1 เส้น (หรือรายงาน
  เป็นช่องว่าง OPEN — ไม่ fail), ทุก zone ถึง sink ผ่าน `flows_to`, ทุก `warns` มี `instruction`
  ไม่ว่างเปล่า, ทุก claim edge ติด tag — **exit non-zero เฉพาะ schema error จริง ไม่ใช่ OPEN link**
  (OPEN link คือช่องว่างเชิงโครงสร้างที่ส่วนขยายนี้มีไว้เพื่อ "แสดง" ไม่ใช่ความล้มเหลวที่ต้องซ่อน).
- `tests/test_typology_build_graph.py`, `tests/test_typology_sammakorn_chain.py` — ข้อมูลจริงจาก
  คลังนี้เท่านั้น (ไม่มีข้อมูลจำลอง), ยืนยันสาย ซอย → `WL.SMK.01` → `ST.SPS.01-04` → `WL.BMA.02` →
  `WL.SSB.*` → `WL.PKN.01` (พระโขนง) → `river:chao_phraya` เชื่อมกันจริงผ่าน `flows_to`, และช่องว่าง
  ที่รู้อยู่แล้ว (ผู้ควบคุมปั๊ม, `AG_MEA` ↔ ซ.17/18) ถูก**รายงาน**ไม่ใช่ถูกปิดบัง.

รายละเอียด id scheme/edge vocabulary/มาตรฐานสากล crosswalk (RELAYED ทั้งหมด) เพิ่มเติม: ดู
`docs/TYPOLOGY_GRAPH.md`. ปัญหาเชิงโครงสร้างที่ส่วนขยายนี้ตอบ: ดู
`docs/knowledge/STRUCTURAL_ISSUES_2026-09-28.md` + `docs/knowledge/structural_issues_2026-09-28.yaml`.

**ข้อจำกัด**: ไม่มีสมการใหม่ในส่วนนี้ (อ้างเฉพาะรหัส PROP-FLOOD ที่ลง Toledo แล้ว) — ไม่มีการแก้ไข
`site/` (ไม่มีการเปลี่ยนหน้าเว็บสาธารณะในรอบนี้). `resource`/`warning_channel` เป็นชั้นข้อมูลใหม่จริง
(ไม่เคยมีมาก่อนในคลังนี้) — ตัวอย่างเกือบทั้งหมดเป็น RELAYED จากข่าว/โพสต์ ไม่มี collector อัตโนมัติ.

**เติมเพิ่ม 2026-09-28 (TDRI 3 บทความ, RELAYED, สกัดเฉพาะที่ขาด)**: `phase`
(normal/pre_event/incident/post_event) บน warning_channel/resource/decides/warns/supplies,
`capability_*` checklist 6 ข้อ (C3) บน agency node แบบ command, `permanence`/`level` (basin
tier ใหม่, `AG_BASIN_CMT`/`AG_REGCOM`), `infra_class` (grey/green_blue/soft) บน water/resource
node, `datum`/`area`/`lead_time` บน warns edge (คุณภาพคำเตือน) — รายละเอียดเต็มดู
`docs/TYPOLOGY_GRAPH.md` "TDRI extension". ไม่มีการวิจารณ์บุคคลที่มีชื่อใดจากบทความต้นทางถูกนำเข้า
กราฟ; หาดใหญ่เป็น next-version scope, บันทึกเป็นบทเรียนข้ามกรณีแถวเดียว
(`docs/knowledge/structural_issues_2026-09-28.yaml` `ISSUE-LESSON-HATYAI`).

**เติมเพิ่ม 2026-09-28 (Environman FB post, RELAYED, เครือข่าย node เท่านั้น ไม่มีตัวเลข)**:
จุดบรรจบลาดพร้าว-แสนแสบ, อุโมงค์พระราม9/สถานีสูบพระโขนง (reuse id จาก
`sources/capacity_ledger.yaml`), `drains_after` (ลำดับการปล่อยน้ำ tributary), `condition`
(OPEN, ขยะอุดตันสถานีสูบ), north-axis stub (คลองเปรมประชากร) — รายละเอียดเต็มดู
`docs/TYPOLOGY_GRAPH.md` "Environman extension + completeness pass". Completeness pass
เดียวกันปิดช่องว่าง orphan/owned_by หลายจุดด้วยแหล่งที่มีอยู่แล้วในคลังนี้เอง
(`sources/owner_agency_crosswalk.yaml`, `docs/CAPACITY.md` §2).

## 11. INTAKE_STARVED (เพิ่ม 2026-09-28, ปากคลองบางตลาด field report, RELAYED-field)

State ใหม่ แยกจาก RULE-STALL-01: ปั๊ม/จุดสูบ idle หรือ derated เพราะระดับน้ำฝั่งรับ (forebay) ต่ำ
เกินไป **ทั้งที่พื้นที่ต้นน้ำยังท่วมอยู่** (RULE-STALL-01 พูดถึงจุดยึดปลายทางที่นิ่ง — คนละกลไก).
บันทึกเป็น attribute บน node ประเภท pump/tunnel: `stall_state: INTAKE_STARVED` +
`stall_cause_confirmed`/`stall_cause_checklist_pending` จาก checklist ปิด 4 ข้อ (ลำดับตรวจ ไม่ใช่
สูตร): สิ่งกีดขวางต้นน้ำ (ขยะ/ผักตบชวา) → สถานีสูบ relay ล้มเหลว → สถานะประตูน้ำ → ท่อ/culvert ตีบ.
ตัวอย่างจริง: `ST.BANGTALAD.01` (ดู `docs/knowledge/card_paakklongbangtalad_intake_starved_
2569.md`, เชื่อมกับ `ISSUE-INFRA-02`/`ISSUE-INFRA-03`).
