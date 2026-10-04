# การสอบเทียบเกณฑ์ tier ladder ของ PROP-FLOOD-06 กับมาตรฐานสากล + เอกสารไทย

**สั่งงานโดย founder (17:25, 2569-09-27, ตรงตัว)**: "อ่านเอกสารเหล่านี้เพื่อสร้างเกณฑ์ที่เหมาะสมใน
ประเทศไทย และควบกับการจัดการรับมือภัยพิบัติระดับโลกของ WHO และเอกสารชั้นนำทั่วโลก แล้วสร้างเกณฑ์
ที่เข้ากับเราพร้อมกรอบคิดอย่างมีเหตุผล"

**สถานะ**: การสอบเทียบ (calibration), **ไม่ใช่**การยืนยันความถูกต้อง (validation) — ดู §6

**ขอบเขต Toledo**: ไฟล์นี้**ไม่ได้แก้ไข** `PROP-FLOOD-06.md` หรือ `registry/proposals/
flood_outlet_coping.json` — เป็นข้อเสนอ (proposal-for-a-proposal-bump) เท่านั้น การ derive สมการ
ใหม่ใด ๆ **ไม่เกิดขึ้นในไฟล์นี้** ตาม AGENTS.md §2 — ทุกค่าด้านล่างเป็น **ค่าคงที่/อนุสัญญา (convention)**
ที่ใส่เข้าไปในโครงสร้างสมการที่ registered แล้วเท่านั้น ไม่ใช่สมการใหม่

---

## 1. หลักการที่สกัดได้จากมาตรฐานสากล (พร้อม source + tag)

| # | หลักการ | แหล่ง | Tag |
|---|---|---|---|
| P1 | **Impact-based, ไม่ใช่ hazard-based**: ระดับเตือนภัยต้องผูกกับผลกระทบต่อคน/โครงสร้าง ไม่ใช่แค่ค่าฟิสิกส์ดิบ | WMO Guidelines on Multi-hazard Impact-based Forecast and Warning Services — likelihood×impact risk matrix (community.wmo.int checklist, wmo.int) | RELAYED |
| P2 | **People-centred, "end-to-end"**: 4 องค์ประกอบ — risk knowledge, detection/monitoring/forecasting, communication, response capability — ขาดองค์ประกอบใดองค์ประกอบหนึ่งคือ EWS ที่ไม่สมบูรณ์ | UNDRR / Sendai Framework, Early Warnings for All (undrr.org) | RELAYED |
| P3 | **Action verb ต่อระดับ ไม่ใช่แค่ความรุนแรง**: แต่ละระดับต้องบอกว่า "ใครทำอะไร" ไม่ใช่แค่ "แย่แค่ไหน" — Level 3 = กลุ่มเปราะบางอพยพ, Level 4 = ทุกคนอพยพ, Level 5 = ปลอดภัยตัวเองทันที (สายเกินอพยพอย่างปลอดภัย) | Japan 5-level keikai-level system (nippon.com, fetched 2569-09-27) | VERIFIED (fetched, cross-checked ด้วย WebSearch แยก) |
| P4 | **Lead time ต้อง ≥ time-to-act ของกลุ่มที่ช้าที่สุด**: UK EA ให้ Flood Alert ล่วงหน้า 2-12 ชม. (เตรียมตัว) ก่อน Flood Warning ที่ล่วงหน้าสั้นกว่า (30 นาที-2 ชม., ความมั่นใจสูงขึ้น) — สอง stage คนละหน้าที่ ไม่ใช่แค่ระดับความรุนแรงต่างกัน | UK gov.uk "Flood alerts and warnings: what they are and what to do" (fetched 2569-09-27) | VERIFIED (fetched) |
| P5 | **Threshold-based ladder ด้วยเกณฑ์วัดจริง (gauge stage) ไม่ใช่การพยากรณ์ล้วน**: Action/Minor/Moderate/Major ผูกกับระดับน้ำที่วัดได้จริงเทียบ stage ที่ประกาศไว้ล่วงหน้าต่อสถานี | US NWS flood category definitions (forecast.weather.gov/glossary, fetched 2569-09-27) | VERIFIED (fetched, บางส่วน — "action stage" คำนิยามมาจาก WebSearch snippet ไม่ใช่ fetch โดยตรง จึงลดชั้นเป็น RELAYED สำหรับคำนั้นคำเดียว) |
| P6 | **ระดับเดียวชี้ขาด (single dominant level), refusal เป็นคำตอบที่ถูกต้อง**: ทุกมาตรฐานข้างต้นมีระดับเดียวที่ประกาศต่อพื้นที่/สถานี ไม่ใช่หลายหน่วยงานประกาศขัดกัน — ตรงกับ `binding(U)`/`LR` ของ PROP-FLOOD-06 อยู่แล้ว (ยืนยันซ้ำจากมาตรฐานสากล ไม่ใช่หลักการใหม่) | สังเคราะห์จาก P3-P5 ร่วมกัน | INSTINCT (การสังเคราะห์ ไม่ใช่ข้อความตรงจากแหล่งเดียว) |
| P7 | **กลุ่มเปราะบางต้องการเวลามากกว่า และมักต้องพึ่งความช่วยเหลือจากภายนอก ไม่ใช่แค่ "ได้แจ้งเตือนเร็วขึ้น"** | `card_nursing_elderly_flood_preparedness_ubon.md` (วารสารพยาบาล 72(2), 2566) — คำให้สัมภาษณ์ตรง: การขนย้ายของขึ้นที่สูง "อาจไม่ทันการณ์" หากอยู่บ้านลำพัง | RELAYED (จากเอกสารในโปรเจกต์นี้) |
| P8 | **สายบังคับบัญชาที่ยาว/หลายชั้น ทำให้การช่วยเหลือ/การสั่งการไม่ทันเวลา แม้มีแผนระดับชาติ** | `card_research_nakhonsawan_flood_assistance_satisfaction.md` — เหตุการณ์ปี 2554 | RELAYED |
| P9 | **ขีดความสามารถระบบระบายน้ำที่มีอยู่จริง (as-built) มักต่ำกว่าตัวเลขที่แผนแม่บทอ้างถึง** — 58.7 มม./ชม. (=80 มม./วัน) as-built เทียบ 76-100 มม./ชม. เป้าหมายอนาคต | `docs/CAPACITY.md` §1 (VERIFIED ในโปรเจกต์นี้เอง จากแผนปฏิบัติราชการ 2569 สนย.กทม.) | VERIFIED (ของโปรเจกต์เอง, อ้างซ้ำที่นี่) |

**หมายเหตุ WHO**: WebSearch ไม่พบเอกสาร WHO ที่ระบุตัวเลข lead-time/threshold เชิงปริมาณสำหรับ
อุทกภัยโดยตรง (พบเฉพาะหลักการทั่วไปเรื่อง EMT/eMMT deployment และการดูแลกลุ่มเปราะบางระหว่าง
อพยพ) — เกณฑ์เชิงปริมาณของ WHO/EMT ต่ออุทกภัยยัง **OPEN** ไม่มีตัวเลขที่ตรวจสอบได้มาแปลงเป็นค่าใน
proposal นี้ (ต่างจาก UK/US/Japan ที่ fetch ได้ตัวเลขตรง)

**ISO 22320/22322**: ไม่ได้ WebFetch (เอกสาร ISO ปกติต้องซื้อ/ไม่เปิดสาธารณะเต็มฉบับ) — **OPEN**

---

## 2. ตารางเทียบ ladder ต่างประเทศ/ไทย ↔ L0-L5/LR ของ PROP-FLOOD-06

| ระดับ PROP-FLOOD-06 | ความหมาย | UK EA (3 ระดับ) | US NWS (4 ระดับ) | Japan (5 ระดับ) | DDPM/TMD/BMA (ไทย) |
|---|---|---|---|---|---|
| L0 | ปกติ | (ไม่มีการประกาศ) | ต่ำกว่า Action Stage | Level 1 (เฝ้าระวังทั่วไป, ข่าวสารทั่วไป) | ฝนเล็กน้อย-ปานกลาง (<35 มม./วัน โดยประมาณ, ดูหมายเหตุ TMD ด้านล่าง) |
| L1 | เฝ้าดู | Flood Alert ("เป็นไปได้ เตรียมตัว") | Action Stage | Level 2 (คำแนะนำ, ตรวจสอบเส้นทางอพยพ) | ฝนหนัก (35.1-90 มม./วัน, RELAYED-ยังไม่ verified primary) / เตือนผู้ใหญ่บ้าน (DMR >60 มม./24ชม., ไม่ verified primary) |
| L2 | เตรียมตัวได้ ยังมีเวลา | Flood Alert (ปลายช่วง, ใกล้ Warning) | Minor Flood | Level 2/3 ก้ำกึ่ง | เตือนราษฎรอาจเกิดน้ำป่า (DMR >90 มม./24ชม.) / canal warning_level_m (MEASURED ในโปรเจกต์) |
| L3 | ทำตอนนี้ภายในวันนี้ | Flood Warning ("คาดว่าจะเกิด ต้องทำตอนนี้") | Moderate Flood | Level 3 (กลุ่มเปราะบางอพยพ) | จัดเวรยามเฝ้าระวัง (DMR >100 มม./24ชม.) / rain_24h > 80 มม./วัน (เกินขีดความสามารถ as-built VERIFIED) |
| L4 | เร่งด่วนเดี๋ยวนี้ | Severe Flood Warning ("อันตรายถึงชีวิต ต้องทำทันที") | Major Flood | Level 4 (ทุกคนอพยพ) | เตรียมอพยพ (DMR >150 มม./24ชม.) / canal critical_level_m (MEASURED) |
| L5 | เกินระบบแล้ว | (ไม่มีในโครงสร้าง UK — implied ภายใน Severe) | Record Flooding | Level 5 (ภัยเกิดแล้ว ปลอดภัยตัวเองก่อน) | canal ≥ bank_level_m (MEASURED, ล้นตลิ่งแล้ว) |
| LR | REFUSED | — | — | — | ไม่มี ladder ใดมีแนวคิดนี้ตรง ๆ — เป็นการออกแบบเฉพาะของ PROP-FLOOD-06 เอง (ยืนยัน P6 ว่าไม่มีมาตรฐานใดเทียบได้ 1:1) |

**ข้อสังเกตสำคัญ**: ทุก ladder สากลที่ตรวจสอบมี **4-5 ระดับ** (UK 3 + "ไม่มีคำเตือน" = 4 ทางปฏิบัติ, US 4,
Japan 5) — สอดคล้องกับโครงสร้าง L0-L4 (5 ระดับ) ของ PROP-FLOOD-06 ที่มีอยู่แล้วในฐานะ **convention
ที่ founder ประกาศไว้ก่อนงานนี้** ไม่ใช่ตัวเลขที่งานนี้เพิ่งกำหนด — งานนี้ยืนยัน (corroborate) จำนวนระดับ
เท่านั้น ไม่ได้เปลี่ยนจำนวนระดับ

---

## 3. ค่า PROPOSED สำหรับ OPEN constants ของ PROP-FLOOD-06 (tag: RELAYED-derived-convention)

**ทุกค่าในหัวข้อนี้ยังเป็น convention — ไม่ใช่ทฤษฎีบทหรือค่าที่พิสูจน์แล้ว** ตามวินัย equation discipline
(§1.1 ของ workspace) — ค่าเหล่านี้ไม่ใช่สมการใหม่ เป็นแค่ตัวเลขที่ใส่ในโครงสร้างที่ registered แล้ว

### 3.1 S_H bands (0.3 / 0.6 / 0.9 / 1.2)

**ข้อเสนอ: คงค่าเดิมตามที่ founder ประกาศไว้ในการ derive proposal ครั้งแรก — ไม่มีมาตรฐานสากลใดให้
ตัวเลข ratio F/min(D,R) ที่ตรงกันเป๊ะ (ทุกมาตรฐานสากลใช้ gauge-stage หรือ likelihood×impact matrix
เชิงคุณภาพ ไม่ใช่ ratio เชิงปริมาณแบบนี้)** — เหตุผลที่คงไว้: (1) จำนวน 5 bands สอดคล้องกับจำนวน
ระดับสากล (§2), (2) ช่วงห่างเท่ากัน (0.3 ทุกขั้น) เป็นโครงสร้างที่ตรวจสอบ/อธิบายง่ายที่สุดเมื่อไม่มีข้อมูล
เชิงประจักษ์มายืนยันจุดตัดที่แม่นยำกว่านี้ (Occam's razor สำหรับ convention, ไม่ใช่ข้อเท็จจริง)

**สิ่งที่จะเปลี่ยนค่านี้**: การพบว่าเหตุการณ์จริงหลายครั้งอ่าน S_H ต่ำกว่า 0.9 แต่กลับท่วมจริง (หรือสูงกว่า
1.2 แต่ไม่ท่วม) ตาม falsifier ที่ PROP-FLOOD-06 กำหนดไว้แล้ว — ยังไม่มีข้อมูล readout_log พอที่จะทดสอบ
ในตอนนี้ (OPEN, ดู §6)

### 3.2 T_act bands (6h / 24h / 48h)

**ข้อเสนอ: คงค่าเดิม พร้อมกฎเสริม (promotion rule) จาก P7**:
- เหตุผลคงค่า: 6h อยู่ในช่วงเดียวกับ UK EA Severe Warning (ไม่มี lead time คงที่ = "เดี๋ยวนี้") และ Japan
  Level 4 (ต้องอพยพก่อนสถานการณ์แย่ลง); 24h ตรงกับช่วง Japan Level 2→3 (ตรวจสอบเส้นทาง →
  เริ่มอพยพกลุ่มเปราะบาง); 48h ให้ margin สำหรับ "เตรียมตัวได้ ยังมีเวลา" ซึ่งตรงกับที่ UK EA Flood Alert
  ให้ล่วงหน้าได้ถึง 12 ชม. บวก margin เพิ่มสำหรับกลุ่มเปราะบางตาม P7 (การ์ดพยาบาลผู้สูงอายุระบุตรงว่า
  ต้องพึ่งคนอื่นช่วยขนของ/อพยพ ซึ่งใช้เวลามากกว่าคนทั่วไป)
- **กฎเสริมใหม่ (ไม่เปลี่ยนตัวเลข bands, เพิ่มกฎ promotion)**: ถ้าหน่วย `U` มีการประกาศ (declared) ว่ามี
  ประชากรกลุ่มเปราะบาง (ผู้สูงอายุอยู่คนเดียว/ผู้พิการ/ผู้ป่วยติดเตียง) ในสัดส่วนสูง และ `T_act(U) ≤ 48h`
  ให้ปรับ tier ขึ้นอย่างน้อย 1 ระดับจากที่ ratio S_H bands คำนวณได้ตรง ๆ (เหตุผล: P7 — เวลาที่ต้องใช้ใน
  การอพยพจริงยาวกว่าที่สูตรมาตรฐานสมมติ) — **นี่คือ INSTINCT ไม่ใช่ VERIFIED**: ไม่มีตัวเลขจากเอกสารว่า
  "เท่าไหร่ถึงพอ" มีแค่หลักฐานเชิงคุณภาพว่า "นานกว่า"

**สิ่งที่จะเปลี่ยนค่านี้**: ตัวเลขเวลาจริงที่วัดได้จากเหตุการณ์จริงว่ากลุ่มเปราะบางในหมู่บ้านสัมมากรใช้เวลา
เท่าไหร่จริงในการอพยพ/ขนของ (ยังไม่มีข้อมูลนี้ในโปรเจกต์)

### 3.3 Horizon H

**ข้อเสนอ: H = 48 ชั่วโมง เป็นค่า default สำหรับหน่วยระดับหมู่บ้าน/เขตเมือง (เช่น สัมมากร)**, เปิดทาง
เลือก H ยาวกว่า (เช่น 120 ชั่วโมง/5 วัน) สำหรับหน่วยระดับลุ่มน้ำ/ต้นน้ำ — เหตุผล: (1) 48h ตรงกับ T_act
band บนสุดที่มีอยู่แล้ว (ถ้า T_act ไม่มีทางเกิน H ก็ควรตั้ง H ≥ T_act band สูงสุด มิฉะนั้น T_act จะรายงาน
">H" ทั้งที่ยังอยู่ใน L1 อยู่), (2) Japan Level 1 ("ข้อมูลล่วงหน้าได้ถึง 5 วัน") ให้บรรทัดฐานว่าการพยากรณ์
ระดับลุ่มน้ำ/อุตุนิยมวิทยาระยะไกลมีความน่าเชื่อถือลดลงเมื่อเกิน 48-72 ชั่วโมง จึงไม่ควรใช้ H ยาวกว่านั้น
สำหรับหน่วยที่ dominant term คือ rainfall-runoff ในพื้นที่ (สัมมากร/กทม.) — ค่านี้ **ยังไม่มีตัวเลขสากล
ที่ตรงกัน 1:1** จึงเป็น INSTINCT ผสม P1/P3

**สิ่งที่จะเปลี่ยนค่านี้**: ความแม่นยำจริงของ ensemble rain forecast ที่ใช้ (Open-Meteo) เมื่อวัด lead
time เทียบผลจริงในโปรเจกต์นี้เอง (ยังไม่ได้วัด)

### 3.4 Runoff coefficient c_U bounds

**ข้อเสนอ: คงช่วง [0.5, 1] ตามที่ proposal ประกาศไว้แล้ว แต่เพิ่ม point-estimate แนะนำตาม land-use
tag (ไม่ใช่การลบขอบเขต [0.5,1], เป็นการเพิ่มค่ากลางแนะนำเมื่อไม่มีการวัดจริง)**:
- พื้นที่เมืองหนาแน่นสูง (CBD/ถนน/อาคารต่อเนื่อง): แนะนำ `c ≈ 0.85-0.9` — อ้างอิงทิศทางจาก
  `card_research_ku_bangkhen_urban_runoff_2018.md`: พื้นผิวไม่พรุนน้ำเพิ่มจากร้อยละ 55 เป็น 65 ในรอบ
  7 ปี (แนวโน้ม ไม่ใช่ตัวเลข runoff coefficient ตรง ๆ)
- พื้นที่เมืองผสมสวน/หมู่บ้านจัดสรร (เช่น สัมมากร): แนะนำ `c ≈ 0.6-0.7` (กึ่งกลางของช่วง [0.5,1], ไม่มี
  หลักฐานตรงให้ปรับสูง/ต่ำกว่ากึ่งกลาง)
- พื้นที่เกษตร/พื้นที่สีเขียว: แนะนำใช้ขอบล่าง `c ≈ 0.5` ตามที่ proposal กำหนดไว้แล้ว (ไม่มีหลักฐานใหม่ให้
  ปรับ)
- **ข้อควรระวังที่ตรวจพบและต้องบันทึกไว้**: ค่า Manning's coefficient ในการ์ด Chanthaburi (0.0678
  สำหรับพื้นที่ชุมชนหนาแน่นปานกลาง, 0.368 สำหรับพื้นที่สีเขียว) **เป็นคนละนิยามกับ runoff coefficient
  `c_U`** ของ PROP-FLOOD-06 (Manning's N ใช้ในสมการความเร็วการไหลในท่อ/ผิวดิน ไม่ใช่สัดส่วนน้ำฝนที่
  กลายเป็น runoff) — **ห้ามแทนค่าโดยตรง**, บันทึกไว้ในการ์ดเอกสารนั้นแล้วเช่นกัน

**สิ่งที่จะเปลี่ยนค่านี้**: การวัด imperviousness ratio จริงของพื้นที่สัมมากร/รามคำแหง 53 ด้วย GIS/land-
cover classification (ยังไม่มีในโปรเจกต์นี้ — เป็นช่องว่างที่ควรเติมก่อนใช้ค่า point-estimate นี้จริงจัง)

### 3.5 Tide/gravity derating factor g_U(t)

**ข้อเสนอ: เปลี่ยนจาก "ค่าคงที่ OPEN default = 1" เป็น "กฎโครงสร้าง 2 สถานะ" (ยังไม่ใช่ตัวเลขสุดท้าย)**:
- เมื่อระดับน้ำทะเล **ต่ำกว่า** ระดับน้ำในคลอง (ประตูเปิด, แรงโน้มถ่วงระบายได้): `g_U(t) = 1` (คงเดิม)
- เมื่อระดับน้ำทะเล **สูงกว่าหรือเท่ากับ** ระดับน้ำในคลอง (ประตูปิด ตามกลไกที่
  `card_academic_kaemling_retarding_basin_development.md` อธิบาย): การระบายด้วยแรงโน้มถ่วง = 0
  ทั้งหมด ต้องพึ่งปั๊มล้วน ๆ — เสนอ `g_U(t) = 0` เฉพาะ**เทอมแรงโน้มถ่วง** (ไม่ใช่ทั้ง D_H เพราะปั๊มยังทำงาน
  ได้ตามปกติ — ต้องแยกเทอม gravity-outflow ออกจากเทอม pump-outflow ใน D_H ถ้าจะใช้กฎนี้จริงจัง ซึ่ง
  เป็นการเปลี่ยนโครงสร้างสมการเล็กน้อย **เกินขอบเขตของไฟล์นี้ที่ห้าม derive สมการใหม่** — จึงเสนอไว้เป็น
  "ข้อสังเกตสำหรับการพิจารณา v3" ไม่ใช่ค่าที่ใส่ใน thresholds_v2 JSON ด้านล่าง)
- สำหรับ v2 (ไม่เปลี่ยนโครงสร้างสมการ): **คง g_U(t) = 1 เป็น default ต่อไป แต่ต้อง flag ชัดว่าเป็น
  known-wrong-when-gate-closed** ตามที่ proposal เดิมเขียนไว้แล้ว ("OPEN default 1, flagged")

**สิ่งที่จะเปลี่ยนค่านี้**: ข้อมูลตารางน้ำขึ้นน้ำลงจริงจากสถานีวัดระดับน้ำทะเลที่ใกล้จุดออกของสัมมากร +
บันทึกสถานะประตูระบายจริง (ยังไม่มีในโปรเจกต์)

### 3.6 L5 pre-check

**ข้อเสนอ: ผูก "level ที่เกินเกณฑ์แล้ว" เข้ากับเส้น critical/bank ที่มีอยู่แล้วในฟีดจริง** (ไม่ใช่ตัวเลข
ใหม่ — ใช้ค่าที่ MEASURED อยู่แล้วใน `sources/registry.yaml` — `canal_critical_m`, `bank_level_m`):
- `L5` เมื่อ `canal_water_level_m ≥ bank_level_m` (ล้นตลิ่งแล้ว — ตรงกับนิยาม "capacity already 0" ของ
  proposal เดิม เพราะเมื่อล้นตลิ่ง ความจุที่เหลือ = 0 โดยนิยาม) **หรือ** ปั๊มที่ประกาศไว้ทั้งหมดในหน่วยไม่
  ทำงาน (`NOT running`, จาก readout สด) **ขณะที่** `canal_water_level_m ≥ canal_critical_m`
- เหตุผล: ใช้เส้นที่มีอยู่แล้วในฟีดจริง (ไม่ใช่การประดิษฐ์ threshold ใหม่) ตรงตามหลักการ P5 (threshold-
  based ladder ผูกกับ gauge stage ที่ประกาศไว้ล่วงหน้า, แบบเดียวกับ US NWS)

**สิ่งที่จะเปลี่ยนค่านี้**: ถ้าพบว่าเส้น `bank_level_m` ในฟีด กทม. ไม่ตรงกับตำแหน่งจริงของคันกั้นน้ำที่
สัมมากร (ยังไม่ได้ ground-truth เทียบภาคสนาม)

---

## 4. ตัวกระตุ้น (trigger) เฉพาะไทย เพิ่มเติมสำหรับ promote tier (พร้อมแหล่งที่มา)

ตามหลักการ "higher of the two governs" ที่ proposal ใช้อยู่แล้วระหว่าง S_H และ T_act — เสนอให้ trigger
เหล่านี้ทำหน้าที่เป็น **ตัวที่สาม** ในการเทียบ (promote tier ขึ้น ไม่เคยลดระดับที่คำนวณได้จากสูตรเดิม):

1. **ฝนสะสม 24 ชม. เทียบเกณฑ์ออกแบบ 80 มม./วัน (VERIFIED, `docs/CAPACITY.md` §1)**: ถ้า
   `rain_24h(U) > 80` มม. → promote tier ขั้นต่ำเป็น **L3** ทันที (เหตุผล: ปริมาณฝนเกินขีดความสามารถ
   as-built ของระบบระบายน้ำ กทม. ตามเอกสารทางการที่ verified แล้วในโปรเจกต์นี้ — ไม่ต้องรอผลลัพธ์
   ratio S_H เพราะ input หนึ่งตัวเกิน design assumption ไปแล้ว)
2. **Canal critical line (MEASURED, `sources/registry.yaml` `canal_critical_m`)**: ถ้า
   `canal_water_level_m ≥ canal_critical_m` → promote tier ขั้นต่ำเป็น **L4** (เหตุผล: เส้นนี้เป็นเส้นที่
   กทม. ประกาศเองว่า "วิกฤต" — ใช้ตรรกะเดียวกับ P5, เชื่อ gauge ที่หน่วยงานประกาศไว้ล่วงหน้า)
3. **เกณฑ์ฝนสะสม/ดินถล่มของกรมทรัพยากรธรณี (DMR)** — **RELAYED, ยังไม่ verified จากเอกสารต้นทาง
   โดยตรง** (WebFetch เอกสาร PDF ต้นทางไม่สำเร็จ — เป็น binary parse ไม่ได้ ตัวเลขด้านล่างมาจากการ
   สังเคราะห์ผลค้นเว็บเท่านั้น ต้องยืนยันซ้ำก่อนใช้งานจริง): `>60` มม./24ชม. เตือนผู้ใหญ่บ้าน, `>90`
   มม./24ชม. เตือนราษฎรเรื่องน้ำป่า, `>100` มม./24ชม. จัดเวรยาม, `>150` มม./24ชม. เตรียมอพยพ — ถ้า
   ยืนยันตัวเลขนี้ได้จริงในอนาคต เสนอใช้เป็นตัวกระตุ้น **เฉพาะหน่วยที่มีความเสี่ยงดินถล่มร่วม** (ต้นน้ำ/
   พื้นที่ลาดชัน ไม่ใช่สัมมากรซึ่งเป็นที่ราบ): `rain_24h ≥ 100` → ขั้นต่ำ L3, `rain_24h ≥ 150` → ขั้นต่ำ L4
   — **นี่คือ trigger คนละ hazard channel (ดินถล่ม) ไม่ใช่ส่วนหนึ่งของ S_H ratio** จึงเสนอเป็น "ตัว
   promote คู่ขนาน" เหมือนข้อ 1-2 ไม่ใช่การแก้สูตร S_H

---

## 5. Draft JSON block `thresholds_v2` (สำหรับ paste เข้า proposal ในการ bump .v2 — ไม่ได้แก้ไฟล์ proposal ในงานนี้)

```json
{
  "thresholds_v2": {
    "provenance": "docs/knowledge/TIER_THRESHOLDS_RATIONALE.md, calibration pass 2026-09-27, tag RELAYED-derived-convention unless noted",
    "S_H_bands": { "L1": 0.3, "L2": 0.6, "L3": 0.9, "L4": 1.2, "unchanged_from_v1": true },
    "T_act_bands_hours": { "L4": 6, "L3": 24, "L2": 48, "unchanged_from_v1": true,
      "vulnerable_population_promotion_rule": "if unit declares high share of vulnerable residents AND T_act <= 48h, promote tier by >=1 level (INSTINCT, source: card_nursing_elderly_flood_preparedness_ubon.md)" },
    "horizon_H_hours": { "default_urban_or_village_unit": 48, "option_basin_or_upstream_unit": 120,
      "rationale": "INSTINCT, no 1:1 international standard; loosely anchored to Japan level-1 5-day outlook ceiling and to T_act's own top band" },
    "runoff_coefficient_c_U": {
      "declared_bound_pair_unchanged": [0.5, 1],
      "point_estimate_suggestions": {
        "dense_urban_CBD": 0.875,
        "mixed_village_e.g._sammakorn": 0.65,
        "agricultural_green": 0.5
      },
      "caveat": "point estimates are directional (KU Bangkhen impervious-surface trend 55%->65%), NOT a measured c_U for any specific node"
    },
    "tide_gravity_derating_g_U_t": {
      "v2_kept_as": 1,
      "flag": "known-wrong-when-outlet-gate-closed",
      "structural_note_for_v3_only": "gate-state binary rule (g=1 open / g=0 gravity-term only when closed) requires splitting D_H into gravity-outflow + pump-outflow terms -- out of scope for a v2 constant-only bump"
    },
    "L5_pre_check": {
      "rule": "canal_water_level_m >= bank_level_m OR (all declared pumps not running AND canal_water_level_m >= canal_critical_m)",
      "source": "sources/registry.yaml canal feed fields, already MEASURED"
    },
    "thai_specific_extra_promoters": [
      { "id": "RAIN_24H_EXCEEDS_BMA_DESIGN", "condition": "rain_24h_mm > 80", "min_tier": "L3",
        "source": "docs/CAPACITY.md §1, VERIFIED" },
      { "id": "CANAL_AT_CRITICAL_LINE", "condition": "canal_water_level_m >= canal_critical_m", "min_tier": "L4",
        "source": "sources/registry.yaml, MEASURED" },
      { "id": "DMR_LANDSLIDE_RAIN_100MM", "condition": "rain_24h_mm >= 100 AND unit.landslide_risk == true",
        "min_tier": "L3", "source": "RELAYED, NOT YET VERIFIED AGAINST DMR PRIMARY DOCUMENT" },
      { "id": "DMR_LANDSLIDE_RAIN_150MM", "condition": "rain_24h_mm >= 150 AND unit.landslide_risk == true",
        "min_tier": "L4", "source": "RELAYED, NOT YET VERIFIED AGAINST DMR PRIMARY DOCUMENT" }
    ]
  }
}
```

---

## 6. OPEN list + คำเตือนความซื่อสัตย์

**นี่คือการสอบเทียบ (calibration) ไม่ใช่การยืนยัน (validation)** — ทุกค่าใน §3-5 เป็น convention ที่
สังเคราะห์จากหลักการสากล + เอกสารที่มี ไม่ใช่ตัวเลขที่พิสูจน์แล้วว่าถูกต้องสำหรับสัมมากร/กทม. การ
validation จริงต้องใช้ **falsifier loop** ที่ PROP-FLOOD-06 กำหนดไว้แล้ว: เทียบ tier ที่คำนวณได้กับผล
ท่วมจริงซ้ำ ๆ หลายเหตุการณ์ (readout_log ของโปรเจกต์นี้เอง เมื่อสะสมพอ, หรือย้อนดูเหตุการณ์ 2554/2568-
2569 ที่การ์ด `case_*.md` เก็บไว้แล้ว) — **ยังไม่ได้ทำ falsifier loop นี้ในงานนี้**

**OPEN รายการ**:
1. ตัวเลขทั้งหมดใน §3 (S_H bands, T_act bands, H, c_U point estimates, g_U(t)) — ยังไม่ validate กับ
   เหตุการณ์จริง
2. เกณฑ์ DMR (60/90/100/150 มม./24ชม.) — RELAYED จากผลค้นเว็บสังเคราะห์ ไม่ใช่จาก fetch เอกสาร
   ต้นทางโดยตรง (PDF ต้นทาง 2 ไฟล์ที่ลองดึงเป็น binary parse ไม่ได้) — **ต้องยืนยันซ้ำก่อนใช้จริง**
3. TMD สีเตือนภัย/เกณฑ์ปริมาณฝนอย่างเป็นทางการ — WebFetch เว็บ tmd.go.th ล้มเหลว (certificate error)
   ตัวเลข "ฝนหนัก 35.1-90 มม." มาจาก WebSearch snippet เท่านั้น
4. WHO เกณฑ์เชิงปริมาณสำหรับ lead-time/threshold ต่ออุทกภัยโดยเฉพาะ — ไม่พบตัวเลขที่ตรวจสอบได้
5. ISO 22320/22322 — ไม่ได้เข้าถึงเนื้อหา (ปกติเป็นเอกสารซื้อ)
6. gate-state ของประตูระบายน้ำจริงที่จุดออกสัมมากร (เปิด/ปิดตามระดับน้ำทะเล) — ไม่มีข้อมูลจริงในโปรเจกต์
   ตอนนี้ (ตรงกับ known OPEN item "Gate states ... currently inferred" ใน `AGENTS.md` §8)
7. imperviousness ratio ที่วัดจริงของพื้นที่สัมมากร/รามคำแหง 53 (ใช้ค่า point-estimate เชิงเปรียบเทียบ
   จากพื้นที่อื่นแทน)

**คำเตือนสุดท้าย**: ค่าเหล่านี้จะถูกใช้โดย FloodConnect เพื่อสื่อสารกับสาธารณะ — การนำ convention ที่ยัง
ไม่ validate ไปแสดงผลราวกับเป็นข้อเท็จจริงที่พิสูจน์แล้วคือการถดถอยของ epistemic floor ของโปรเจกต์นี้
(ตาม AGENTS.md §1) — ต้องแสดง tag `RELAYED-derived-convention` กำกับไว้เสมอเมื่อ implement จริง
ไม่ใช่แสดงเป็นตัวเลข "ถูกต้อง" เฉย ๆ
