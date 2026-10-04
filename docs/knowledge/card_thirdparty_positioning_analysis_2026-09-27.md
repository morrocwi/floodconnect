# Card — third-party positioning/critique analysis of FloodConnect (external assistant, pasted by founder)

**Tag**: RELAYED (external assistant analysis, pasted verbatim by the founder into this
session; not this project's own conclusion) · **บันทึกเข้า**: 2026-09-27 · **founder
instruction (verbatim)**: "สกัดออกมาทำให้โจทย์เราแข็งและครบขึ้น ส่วนที่ยังอ่อนก็ค่อยขาย
ทำโจทย์หลักก่อน"

## คืออะไร

การวิเคราะห์/critique ที่ผลิตโดยผู้ช่วย AI ภายนอก (ไม่ใช่ทีมนี้) วิเคราะห์ตำแหน่งของ
FloodConnect เทียบกับผลิตภัณฑ์ flood-intelligence เชิงพาณิชย์/องค์กรระดับโลก 3 ราย (Google
Flood Hub, FloodMapp, Floodbase) บวก 1 แพลตฟอร์ม humanitarian-crowdsourcing (Ushahidi) —
**เอกสารนี้บันทึกข้อกล่าวอ้าง (claims) ของบุคคลที่สามเกี่ยวกับผลิตภัณฑ์เหล่านั้นเท่านั้น ไม่ใช่
ข้อค้นพบของทีมนี้** ตามกติกา "ข้อกล่าวหาเชิงลบต่อหน่วยงานจากแหล่งเดียว" ที่
`CO_FORECAST_PROTOCOL.md` §6 ข้อ 4 บังคับใช้ (ที่นี่เป็นข้อกล่าวอ้างเชิงบวก/สถิติของบริษัทเอกชน
ไม่ใช่ต่อหน่วยงานรัฐ แต่หลักการเดียวกัน — เก็บเป็นคำกล่าวอ้าง ไม่ใช่ทีมนี้ยืนยันเอง).

## Claims ที่ต้องตรวจ (ก่อนงานนี้ = ยังไม่ verified โดยทีมนี้เลย)

| # | Claim (จากผู้เสนอภายนอก) | ต้องตรวจ | ผลตรวจ (1 WebFetch ต่อรายการ, official page เท่านั้น) |
|---|---|---|---|
| 1 | Google Flood Hub ครอบคลุม "2 พันล้านคน / 150+ ประเทศ" | ต้องตรวจ | **ไม่ยืนยัน** — WebFetch `developers.google.com/flood-forecasting` (2026-09-27): หน้านี้บอกแค่ว่า API ให้เข้าถึง "Google's flood forecasts in [รายชื่อประเทศ]" (มีลิงก์แยก) แต่ไม่ได้ระบุตัวเลข "2 พันล้านคน" หรือ "150+ ประเทศ" ตรงหน้าที่ตรวจ — tag ยังคง **RELAYED, ยังไม่ verified** |
| 2 | Google Flood Hub ให้พยากรณ์แม่น้ำ (riverine) ล่วงหน้า 7 วัน | ต้องตรวจ | **ไม่ยืนยันตัวเลขวัน** — หน้าเดียวกันพูดถึง "real-time riverine flood forecasts" แต่ไม่ระบุ horizon เป็นวันตรง ๆ ในส่วนที่ WebFetch อ่านได้ — tag **RELAYED, ยังไม่ verified** (เทียบกับ `docs/README.md`'s ส่วน "Future integration: Google Flood Forecasting API" ในคลังนี้เองที่เคยเขียนไว้ก่อนหน้าว่า "up to 7-day-ahead riverine forecasts" — คำกล่าวอ้างเดิมของคลังนี้เองก็เป็น RELAYED/Dr-tier ไม่ใช่ VERIFIED เช่นกัน ตาม README.md's ถ้อยคำเดิม) |
| 3 | Google Flood Hub มี "flash-flood API" แยกต่างหาก | ต้องตรวจ | **ไม่พบ** — หน้าที่ตรวจไม่กล่าวถึง flash flood หรือ flash-flood API เลย มีแต่ riverine — claim นี้ **ไม่ได้รับการยืนยัน**, คงเป็น RELAYED จากผู้เสนอภายนอกเท่านั้น |
| 4 | FloodMapp ให้ "flood impact map ความละเอียดถึง ~1 เมตร" | ต้องตรวจ | **ยืนยันบางส่วน** — WebFetch `floodmapp.com` (2026-09-27) พบข้อความจริงบนหน้า: *"High-resolution flood impact maps, down to 1-meter, enable more targeted and efficient resource deployment."* — เป็น**ความละเอียดเชิงพื้นที่ (spatial resolution)** ไม่ใช่ "ความแม่นยำของความลึกน้ำ" ตามที่ claim เดิมสื่อ (accuracy ≠ resolution) — tag **RELAYED-confirmed-wording, แต่ตีความ "accuracy" ผิดจากคำจริงบนหน้า (คำจริงคือ resolution)** |
| 5 | Floodbase ใช้ "satellite intelligence" | ต้องตรวจ | **ไม่พบคำนี้ตรง ๆ** — WebFetch `floodbase.com` (2026-09-27): ไม่พบวลี "satellite intelligence" บนหน้า พบแต่ "satellite imagery", "satellite observation data of floods", และคำอธิบายตัวเอง: *"Grounded in peer-reviewed research that made the cover of Nature, Floodbase fuses satellite imagery, ground sensors, and hydrology to unlock flood observation, prediction, and risk analytics."* — tag **RELAYED, คำที่ผู้เสนอภายนอกใช้ ("satellite intelligence") เป็นการถอดความของเขาเอง ไม่ใช่คำที่ Floodbase ใช้บรรยายตัวเอง** |
| 6 | Ushahidi ใช้งานใน "160+ ประเทศ" | ต้องตรวจ | **ยังไม่ตรวจ** (เกินงบ 3 WebFetch ที่งานนี้กำหนด — เลือกตรวจเฉพาะ Google Flood Hub/FloodMapp/Floodbase ตามที่ระบุไว้ในโจทย์นี้เท่านั้น) — คง **OPEN** |

**สรุปการตรวจ**: จาก 3 หน้าที่ตรวจ (Google Flood Hub, FloodMapp, Floodbase) — **ไม่มี claim
ตัวเลขใดของผู้เสนอภายนอกที่ถูกยืนยันตรงตัวเป๊ะจากหน้าทางการ**: claim #1/#2/#3 (Google)
ไม่พบข้อความสนับสนุนบนหน้าที่ตรวจ; claim #4 (FloodMapp) พบคำจริงแต่คนละความหมาย (resolution
ไม่ใช่ accuracy); claim #5 (Floodbase) พบแนวคิดตรงแต่คำเฉพาะ ("satellite intelligence") เป็น
ของผู้เสนอภายนอกเอง ไม่ใช่คำที่บริษัทใช้ — **ห้ามอ้าง claim เหล่านี้เป็นข้อเท็จจริงยืนยันแล้วใน
เอกสารสาธารณะใดของคลังนี้** จนกว่าจะมีการตรวจเพิ่มเติม (เช่น อ่านหน้าย่อยเฉพาะ/whitepaper
มากกว่าหน้าแรก).

## ส่วนที่มีประโยชน์ (สกัดมาใช้ใน positioning ของเราเอง, ไม่ใช่คำยืนยันของบุคคลที่สาม)

ส่วนนี้เป็น**เฟรมมิ่ง/แนวคิด** ที่ผู้เสนอภายนอกให้มา ไม่ใช่ข้อเท็จจริงเชิงตัวเลขที่ต้องตรวจ —
รับมาเป็นแนวคิด (tag `INSTINCT` ของทีมนี้เอง ที่ยอมรับแนวคิดนี้ว่าเข้ากับสิ่งที่มีอยู่แล้วใน
คลังจริง):

1. **Positioning**: FloodConnect ไม่ใช่ "FloodMapp ราคาถูกกว่า" — มันเป็นชั้นที่อยู่**ใต้**
   ผลิตภัณฑ์ flood-intelligence เหล่านั้น: "Local Evidence + Human Action Infrastructure"
   (ดูรายละเอียดเต็มใน `docs/PROBLEM_STATEMENT_AND_POSITIONING.md`).
2. **คำถามหลักที่เราเป็นเจ้าของ**: "เมื่อรู้ทั้งหมดนี้แล้ว คนธรรมดาจะจัดตัวเองอย่างไร เพื่อเดินจาก
   node ที่ไม่ปลอดภัยไป node ที่ปลอดภัยกว่า โดยไม่สร้างความมั่นใจปลอม" — ตรงกับสิ่งที่คลังนี้
   ทำอยู่แล้วจริง (`REFUSED` เป็น first-class outcome, `UNKNOWN`≠`SAFE`).
3. **ผลิตภัณฑ์ภายนอกทั้ง 3 ตัวควรเป็น INPUT ของเรา ไม่ใช่คู่แข่ง** — Google Flood Hub (เมื่อมี
   API access), FloodMapp/Floodbase (แนวคิด satellite/inundation — ยังไม่ต่อจริง) ป้อนเข้าชั้น
   epistemic ของเราแล้วค่อยส่งต่อ community DAG.
4. **สิ่งที่ critique ชี้ว่ายังอ่อน** (4 must-do) ถูกแปลเป็นแผนงานที่ระบุใน
   `docs/PROBLEM_STATEMENT_AND_POSITIONING.md` ส่วน (d).

## ข้อจำกัดของการ์ดนี้

- ตรวจแค่หน้าแรก/หน้าหลักของแต่ละผลิตภัณฑ์ (1 WebFetch ต่อราย, ตามงบที่กำหนด) — ไม่ได้อ่าน
  whitepaper/หน้าย่อย/เอกสารทางเทคนิคแยก อาจมีตัวเลขที่ claim ทั้งหมดถูกยืนยันอยู่ที่หน้าอื่นซึ่ง
  ไม่ได้ตรวจในงานนี้ — คงเป็น **OPEN สำหรับหน้าที่ยังไม่ได้อ่าน**
- ไม่มีการติดต่อบริษัทเหล่านี้โดยตรง ไม่มีการยืนยันผ่านช่องทางอื่นนอกจากหน้าเว็บสาธารณะ
- ไม่มีชื่อบุคคล/พนักงานของบริษัทเหล่านี้ในไฟล์นี้
