# การ์ดความรู้ — Google Urban Flash Flood + เครื่องมือ resident-facing อื่น (มุมมอง 28 ก.ย. 2569)

**ที่มา**: โพสต์โซเชียลมีเดีย (ชื่อเพจผู้เขียน "Mew Social" — ไม่บันทึกชื่อบุคคลใดๆ ตามกฎคลังนี้) 2 ตอน
อ้างแหล่ง Google Research, Flood Hub help page, AFP/AP, Bangkok Biz News, บวก resident tips
(Flood Hub, DDS, GISTDA "เช็คน้ำ", Traffy Fondue, 1555) — งานนี้ตรวจสอบทุกคำกล่าวอ้างกับแหล่งปฐมภูมิ
เท่าที่ fetch ได้ (งบ ≤8 fetch + อนุมัติเพิ่ม 3 สำหรับตอนที่สองของโพสต์ — ใช้จริง 6 fetch,
2 ครั้งล้มเหลว [403 / TLS cert] ไม่ retry ตามกฎ) แล้ว "ประยุกต์ใช้" อ่านผ่านเลนส์ readout ของคลังนี้
(20 กม.² ของ Google ≫ ขนาดโหนดของเรา → เป็นสัญญาณ Level-0 เท่านั้น ไม่ใช่ node truth)

---

## ส่วน A — ตรวจแต่ละคำกล่าวอ้างจากโพสต์ตอนแรก

### A1. Google Research blog, 12 มี.ค. 2569, "protecting cities with AI...flash floods"

**ลิงก์ที่ตัดทอนมาหาได้แล้ว**: https://research.google/blog/protecting-cities-with-ai-driven-flash-flood-forecasting/

**VERIFIED (fetch โดยตรง, quote ตรงจากหน้า)**:
- วันที่เผยแพร่: "March 12, 2026" — ตรงกับที่โพสต์อ้าง (12 มี.ค. 2569)
- Inputs: "global weather products (NASA IMERG, NOAA CPC)" + real-time forecasts จาก ECMWF และ
  โมเดล AI ของ Google DeepMind, บวก "static geographic, geophysical, and anthropogenic
  attributes, such as urbanization density, topography, and soil absorption rates"
- Target/output: "Given the forecasted weather and local conditions, is a flash flood likely
  to occur in this area in the next 24 hours?" — เป็น**ความน่าจะเป็นแบบ binary/threshold ต่อพื้นที่**
  ไม่ใช่ discharge/water-level แบบสถานีแม่น้ำทั่วไปของ Flood Hub
- Spatial resolution: "20x20 kilometer spatial resolution" (input ทุกตัวถูก area-weighted average
  ลงกริดนี้)
- Lead time: "up to 24 hours in advance"
- ข้อจำกัดที่ระบุตรงในหน้า: (1) พยากรณ์เฉพาะน้ำท่วมที่มาจากสภาพอากาศ **ไม่รวม** เขื่อน/คันกั้นน้ำพัง
  หรือธารน้ำแข็งละลาย (2) เริ่มต้นจำกัดเฉพาะพื้นที่เมือง หรือพื้นที่ที่มีประวัติน้ำท่วมมาก่อน
  (3) บางประเทศ (ระบุตัวอย่างแอฟริกา) ยังขาด ground truth นอกจาก "Groundsource" เอง (4) ทีมงาน
  "actively working" จะลด resolution ให้ hyper-local กว่านี้ในอนาคต (**OPEN** — ยังไม่มี timeline)

**เพิ่มเติมจาก WebSearch (ไม่ได้ fetch หน้าเต็มเอง รอบนี้, RELAYED)**: เทคนิคเบื้องหลังชื่อ
"Groundsource" — ใช้ Gemini อ่านข่าวย้อนหลังหลายสิบปีเพื่อสร้างชุดข้อมูลเหตุการณ์น้ำท่วมในอดีต
(อ้าง 2.6 ล้านเหตุการณ์ยืนยันแล้ว มากกว่า 150 ประเทศ) ใช้ฝึกโมเดล — เกณฑ์พื้นที่เป้าหมายคือความหนาแน่น
ประชากร >100 คน/กม.² (ครอบคลุมกรุงเทพฯ แน่นอน, ความหนาแน่นเฉลี่ย กทม. ~5,300 คน/กม.² — **INSTINCT**
ตัวเลขความหนาแน่นนี้จากความจำทั่วไป ไม่ได้ verify รอบนี้)

### A2. Flood Hub help page — cell 20×20 กม. + ข้อจำกัด

**ลิงก์**: https://support.google.com/flood-hub/answer/16811681?hl=en

**VERIFIED (fetch โดยตรง)**:
- "the probability of a flash flood occurring in a specific region within the next 24 hours"
- "spatial resolution of 20km x 20km"
- ข้อจำกัดตรงตามข้อความ: "can only predict flash floods caused by weather events, not those
  resulting from man-made incidents like dam or levee failures, or glacial melts"; "initially the
  model is limited to either urban areas or areas with some history of flooding in the past"
- หน้านี้ **ไม่มี**ข้อความอธิบายวิธีอ่าน layer สีแดงบนแผนที่ หรือเรื่อง click สถานีวัดน้ำเพื่อดู
  hydrograph โดยตรง (คำถามนั้นตอบไม่ได้จากหน้านี้ — ต้องดูหน้า help อื่นของ Flood Hub, **OPEN**)

**สรุปโพสต์ตอนแรกเรื่องนี้**: ตรงกับแหล่งปฐมภูมิทุกจุดที่ verify ได้ = **VERIFIED**

### A3. AFP/AP, 26 ก.ย. 2569 — ประกาศภัยพิบัติ 50 เขต กทม.

**ลิงก์ที่ verify**: thestar.com.my (ใช้ต้นฉบับ AFP wire) — fetch สำเร็จ

**VERIFIED**:
- บทความให้เครดิต AFP (Agence France-Presse) เป็นสำนักข่าวต้นทาง, และมีเครดิตภาพ "AP Photo/..."
  ควบคู่ — สอดคล้องกับที่โพสต์อ้างว่าเป็นข่าว AFP **และ** AP ทั้งคู่ (AFP = เนื้อข่าว, AP = ภาพประกอบ
  อย่างน้อยในบทความนี้)
- ยืนยันวันที่: "Bangkok authorities declared a flood disaster across the Thai capital on
  Saturday" (26 ก.ย. 2569) — ตรงกับ `docs/knowledge/case_bkk_2569.md` ที่คลังนี้บันทึกไว้แล้ว
  (แถวเดียวกัน, วันเดียวกัน) — **สอดคล้องข้าม 2 แหล่งอิสระ**
- ยืนยันเพิ่ม: "the governor urged residents to move their belongings to higher ground",
  "authorities had transferred 36 bed-ridden people to hospitals" — ตรงกับที่ `case_bkk_2569.md`
  บันทึกไว้แล้วบางส่วน (ตัวเลขคนพักพิง/ผู้ป่วยติดเตียง) แต่ถ้อยคำเจาะจงเรื่อง "ขอให้ย้ายรถ" หรือ
  "ให้ผู้ป่วยใช้เครื่องช่วยหายใจพิจารณาพักโรงพยาบาลชั่วคราว" **ไม่ปรากฏเป็นคำต่อคำ**ในบทความที่ fetch
  ได้รอบนี้ — เป็นการเรียบเรียงทั่วไปกว่าที่โพสต์บรรยาย (**RELAYED-partial**, ไม่ CONTRADICTED เพราะ
  ไม่มีข้อความปฏิเสธ เพียงแต่ไม่มีคำยืนยันตรงคำ — บันทึกตามตำแหน่ง "ผู้ว่าฯ กทม." เท่านั้น ไม่ใส่ชื่อ)

### A4. Bangkok Biz News, 14 มี.ค. 2567 — BMA AI Nowcast

**ลิงก์**: https://www.bangkokbiznews.com/news/news-update/1117716 — fetch สำเร็จ

**VERIFIED**:
- วันที่ตรง: "March 14, 2567 (2024)"
- กทม. ร่วมกับ **Weathernews Inc. (ญี่ปุ่น)** ทำระบบ AI Nowcast อ่านเรดาร์ฝน **2 สถานี: หนองแขม และ
  หนองจอก** เพื่อ "forecast rain accurately 3 hours in advance" — ตรงกับที่โพสต์อ้าง (หนองแขม/หนองจอก,
  3 ชม.)
- ช่องทางดูผล ตามที่บทความระบุ: `https://d3sh0jbs83nmpu.cloudfront.net/`,
  `https://earlywarning.wni.com/`, `https://earlywarning-monitor.wni.com/map/wind`, เพจ Facebook ของ
  สนน./DDS, และ "เว็บไซต์สภาพอากาศเรียลไทม์เฉพาะทางที่กำลังพัฒนา" (ณ วันที่ข่าวออก 2567 — **OPEN**
  ว่าปัจจุบัน 2569 เว็บนั้นสร้างเสร็จหรือยัง, สันนิษฐานว่าคือ dds.bangkok.go.th ปัจจุบัน — ดูส่วน C)
- โพสต์บอกว่า "ดูได้ที่หน้าเว็บป้องกันน้ำท่วมของ DDS" — บทความต้นฉบับ (2567) ไม่ได้พูดถึง
  dds.bangkok.go.th ตรงชื่อนั้น แต่พูดถึงโดเมนของ Weathernews (wni.com) เป็นหลัก — **RELAYED-partial**
  (คลังนี้ไม่ยืนยันได้ว่า dds.bangkok.go.th ปัจจุบันคือหน้าที่โพสต์พูดถึง จนกว่าจะเห็นหน้า DDS
  ที่ embed Weathernews widget จริง — ดู TODO)

---

## ส่วน B — Google's method อ่านผ่านเลนส์ readout ของคลังนี้: บอกอะไรได้/ไม่ได้ที่สเกลสัมมากร/เขต

| หัวข้อ | Google urban flash flood (VERIFIED จาก A1/A2) | ที่สเกลของคลังนี้ (สัมมากร/เขต กทม.) |
|---|---|---|
| หน่วยพื้นที่ | กริด 20×20 กม. (400 กม.²) | เขตสัมมากรอยู่ในเขตบางกะปิ (~12 กม.²) — **เขตทั้งเขตยังเล็กกว่า 1 กริดของ Google เกือบ 30 เท่า** |
| Output | binary probability "flash flood ใน 24 ชม. นี้ไหม" ต่อกริด | คลังนี้มีสัญญาณระดับถนน/คลอง (`thaiwater_flood_road` 243 สถานี, `bma_watermap`) ละเอียดกว่ามาก |
| สิ่งที่ใช้ตัดสินใจได้จาก Google | "ภูมิภาคนี้ (400 กม.²) มีความเสี่ยงน้ำท่วมฉับพลันใน 24 ชม." — เป็น**สัญญาณคัดกรองระดับภาพกว้าง** เท่านั้น | ห้ามใช้แทนสถานะโหนด/ถนนใดถนนหนึ่งในกริดนั้น — 1 กริดครอบคลุมได้หลายสิบเขตแขวง |
| สิ่งที่ตัดสินใจ**ไม่ได้**จาก Google ที่สเกลเรา | ไม่บอกว่าใน 400 กม.² นั้น ซอยไหน/คลองไหนจะท่วมก่อน — ไม่มีความละเอียดระดับถนน | ต้องพึ่งสัญญาณของคลังนี้เอง (flood_road, bma_watermap, community_report) สำหรับความละเอียดนี้ |
| Man-made causes | ไม่รวมเขื่อน/คันกั้นพัง — กทม. เสี่ยงจากประตูระบายน้ำ/สถานีสูบ (ดู `case_bkk_2569.md` §(b) เรื่องสถานีสูบทำงาน 30%) ซึ่ง**อยู่นอกขอบเขตโมเดลนี้โดยสิ้นเชิง** | ทีมนี้ต้องประเมิน man-made bottleneck เอง (`bottlenecks.derived.json`) — Google ช่วยไม่ได้เรื่องนี้ |

**สรุปการประยุกต์ใช้ (ไม่ประดิษฐ์เพิ่ม)**: สัญญาณ Google urban flash flood ผูกเข้าระบบซูมของเราได้แค่
**Level 0 (screen ระดับภาพกว้าง, forecast-inferred, RELAYED เสมอ)** ตามที่ `docs/knowledge/
card_thirdparty_google_flood_hub_2026-09-27.md` §4 เคยระบุไว้แล้วสำหรับ river-gauge layer ของ
Flood Hub ทั่วไป — การ์ดนี้ยืนยันว่า urban flash flood layer (คนละโมเดลจาก river gauge, งานนี้เพิ่งไป
fetch หน้า help เฉพาะทางนี้เป็นครั้งแรก) ก็เข้าเงื่อนไขเดียวกัน: **ห้ามใช้แทน node truth**, ใช้เป็น
cross-check เชิงคุณภาพเท่านั้น (โซนที่เราประเมิน L3+ ตรงกับโซน "อันตราย/อันตรายมาก" ของ Google หรือไม่)

---

## ส่วน C — ตรวจ+ประยุกต์ตอนที่สองของโพสต์ (คำสั่ง "สกัดที่เป็นประโยชน์และใช้ฟรีมา")

หลักการของผู้เขียนโพสต์ ("อย่าไว้ใจ AI ตัวเดียว ซูมจากกริดใหญ่ลงมาทีละชั้น") **ตรงกับ**
`docs/knowledge/PROP-FLOOD-10`/`docs/MVP_SCOPE_2026-09-27.md` (zoom level 0–3) และกฎของฟาวน์เดอร์
"อย่าไว้ใจข้อมูลทางเดียว" (`sources/urban_flood_event_ledger.yaml`: `official_disaster_declared`
แยกจาก `urban_flood_observed` เสมอ) — เป็นการยืนยันอิสระของหลักการเดียวกัน ไม่ใช่แหล่งใหม่ที่ต้องเชื่อ

### ตารางสรุป layer (คำขอฟาวน์เดอร์: layer · source · free for residents · ingestible by us · adds what · where it fits)

| Layer | Source | Free ต่อ resident? | Ingestible โดยเราตอนนี้? | เพิ่มอะไรจากที่มีอยู่แล้ว | เข้า zoom level ไหน / การ์ดหน้าเว็บ |
|---|---|---|---|---|---|
| L1 (24 ชม.) | Google Flood Hub — river gauge layer + urban flash flood layer, https://sites.research.google/floods/ | **ใช่** — ไม่ต้อง key, ไม่ต้อง login (VERIFIED จาก card เดิม + A1/A2) | **ไม่** — Flood Forecasting API ต้อง request access (waitlist/pilot, บันทึกไว้แล้วใน `docs/knowledge/GLOBAL_FREE_HAZARD_APIS.md`) — คงสถานะ "not wired" | คัดกรองภาพกว้างระดับภูมิภาค/แม่น้ำสายหลัก ที่เราไม่มี (เราไม่มี river-basin-wide screen) | zoom **Level 0** เท่านั้น (cross-check เชิงคุณภาพ, RELAYED เสมอ) — การ์ดหน้าเว็บ "ชั้นเตือน 24 ชม." ใส่เป็น**ลิงก์ออก**ไปยัง sites.research.google/floods/ ให้ resident เช็คเอง ไม่ embed ข้อมูลตัวเลขของ Google เข้ามาเป็นของเรา |
| L2 (3 ชม.) | BMA AI Nowcast (Weathernews Japan) อ่านเรดาร์หนองแขม/หนองจอก | **น่าจะใช่** — ตามข่าว 2567 ดูผ่านเว็บ Weathernews/เพจ Facebook DDS ไม่ต้อง login ที่ระบุ (VERIFIED บางส่วน A4) — แต่**ไม่ยืนยันได้ว่าปัจจุบัน 2569 embed อยู่ที่ dds.bangkok.go.th หน้าไหนตรงๆ** (OPEN) | **ไม่ชัด** — คลังนี้มี `dds_nowcast_gif` (`sources/registry.yaml` id `dds_nowcast_gif`, url `dds.bangkok.go.th/Line_data/picture/radar_rain.gif`) ลงทะเบียนแล้วแต่ "ยังไม่ได้ fetch จริง" (`last_status.http: null`) — **ไม่รู้ว่าภาพเรดาร์นี้คือผลผลิตของ Weathernews AI Nowcast ตัวเดียวกับที่ข่าวพูดถึงหรือคนละอัน** (OPEN, ต้องเทียบภาพ) | ถ้าใช่ตัวเดียวกัน: เพิ่ม nowcast เชิงภาพ (การเคลื่อนตัวของกลุ่มฝน 3 ชม.) ที่เราไม่มี — ตอนนี้เรามีแค่ `rain_24h`/`rain_1h` (ค่าจุด, ไม่ใช่ nowcast เชิงพื้นที่) | zoom **Level 0–1** (ภาพเรดาร์กว้างกว่าจุดสถานี) — การ์ดหน้าเว็บ "ชั้นเตือน 3 ชม." ใส่เป็นลิงก์ออกไปหน้า DDS โดยตรง (ไม่ scrape ภาพเข้ามาแสดงเป็นข้อมูลของเราเอง จนกว่าจะยืนยันตัวตนภาพนี้กับ AGENTS.md) |
| L3 (ตอนนี้) | DDS จุดน้ำท่วมถนนหลัก (`dds_daily_pdf`, `dds_flood_report`, `dds_tide_pdf` — ทั้งหมดลงทะเบียนแล้ว, VERIFIED http 200 ณ 2026-09-26 ตาม registry) | **ใช่** — หน้าเว็บสาธารณะไม่ต้อง key | **ใช่ อยู่แล้ว** — คลังนี้เก็บอยู่แล้ว (เป็นแหล่งของเราเอง ไม่ใช่ของใหม่จากโพสต์นี้) | ไม่เพิ่มอะไรใหม่ — โพสต์แค่ยืนยันว่า resident รู้จักแหล่งเดียวกับที่เราเก็บอยู่แล้ว | zoom Level 2 (มีอยู่แล้ว) |
| L3 (ตอนนี้) | GISTDA "เช็คน้ำ" — แอป, ใช้ AI+ภาพดาวเทียม+CCTV, อ้างกริด **1 กม.²** (400 เท่าเล็กกว่า 20 กม.² ของ Google — เลขนี้เป็น**คำกล่าวอ้างของผู้ให้บริการเอง**, คลังนี้ไม่ verify ตัวเลข "400×" ด้วยตัวเอง รอบนี้ เพราะ fetch หน้า gistda.or.th ล้มเหลว TLS cert error ไม่ retry) | **ใช่** — แอปฟรี ทั้ง iOS/Android (RELAYED จาก WebSearch, ไม่ fetch หน้าแอปสโตร์เอง) | **ไม่ทราบ** — probe หน้า gistda.or.th ที่บรรยายแอปนี้ล้มเหลว (TLS cert, ตามกฎไม่ retry) — **ยังตอบไม่ได้ว่ามี public JSON/WMS endpoint หรือเป็น UI แอปปิดเท่านั้น** (OPEN, ต้อง probe รอบหน้าด้วยเครื่องมือ/certificate ต่างออกไป, ห้าม scrape UI) | ถ้ามี endpoint จริง: กริด 1 กม.² ละเอียดกว่า `thaiwater_flood_road`/`bma_watermap` เชิงพื้นที่ (แต่จุดของเราละเอียดกว่าเชิง sensor จริง ไม่ใช่ grid ประมาณ) + CCTV ความลึกน้ำจากภาพ (model-inferred, ไม่ใช่ sensor วัดจริง) | ถ้าเข้าได้: zoom **Level 1–2** (เสริม, ไม่ทดแทน) — การ์ดหน้าเว็บใส่เป็นลิงก์ออกไปที่แอป ไม่ embed ตัวเลข "กริด 1 กม.²" เป็นค่าของเราเอง |
| L4 (รายงานเอง) | Traffy Fondue (LINE @TraffyFondue) + สายด่วน 1555 | **ใช่** — ช่องทางราชการฟรี ไม่ต้อง key | ไม่เกี่ยวกับ ingest (เป็นช่องทาง**ออก**จาก resident ไปหน่วยงาน ไม่ใช่แหล่งข้อมูล**เข้า**คลังนี้) | คลังนี้มี `community_report` (ของโครงการเอง, ผ่านช่องทางภายใน) อยู่แล้ว — Traffy Fondue/1555 เป็นช่องทาง**คู่ขนาน**ของภาครัฐ ไม่ใช่สิ่งที่เราแทนที่หรือดึงเข้ามา | zoom Level 3 + resident card "รายงานเอง" (ลิงก์ออกเท่านั้น) |

### ข้อควรระวัง (บังคับใส่ตามคำสั่งฟาวน์เดอร์)

- ตัวเลขความละเอียด (1 กม.² ของ GISTDA เทียบ 20 กม.² ของ Google, อ้าง "400 เท่า") เป็น**คำกล่าวอ้างของ
  ผู้ให้บริการแต่ละราย** — คลังนี้ไม่ได้วัด/ทวนสอบตัวเลขทั้งสองด้วยตัวเอง เกินกว่าที่ fetch ได้ในการ์ดนี้
  (Google: VERIFIED จาก help page เอง; GISTDA: RELAYED จาก WebSearch เท่านั้น, primary fetch ล้มเหลว)
- ความลึกน้ำจาก CCTV (ทั้งของ GISTDA และ `hii` `analyst/cctv` ที่คลังนี้เห็นแล้วแต่ "ยังไม่ได้เชื่อม" —
  ดู `docs/knowledge/card_api_2026-09-27_hii_waterchart_basin.md`) เป็น**ค่าประเมินจากโมเดล/ภาพ**
  (model-inferred) ไม่ใช่ sensor วัดระดับน้ำโดยตรง — ห้ามปนกับ `value_cm` ของ `thaiwater_flood_road`
  ที่เป็น sensor จริง
- Flood Hub urban flash flood cell (20×20 กม.) หยาบกว่าหน่วยวิเคราะห์ของคลังนี้ทุกหน่วย (เขต/โหนด/ถนน)
  หลายสิบเท่า — เข้าระบบนี้เป็น **forecast-inferred / RELAYED signal เสมอ ไม่ใช่ node truth** (ย้ำซ้ำ
  จากส่วน B)
- ทุกแถวข้างต้นที่ tag OPEN ยังไม่ได้ยืนยัน — ห้ามนำไปเขียนบนหน้าเว็บเป็นข้อเท็จจริงจนกว่าจะปิด TODO

---

## ส่วน D — Leak scan (ก่อนส่งมอบ)

- ไม่มี local username/path เครื่องนี้ในไฟล์ (ตรวจด้วยตาก่อนเขียน — ไม่มี `/home/`, ไม่มี session id)
- ชื่อบุคคล: ตรวจแล้ว — ไม่มีชื่อเฉพาะบุคคลใดถูกบันทึก (ผู้ว่าฯ กทม., ผู้เชี่ยวชาญ ฯลฯ ใช้ตำแหน่งเท่านั้น
  ตามที่ `case_bkk_2569.md` ทำไว้แล้ว, ชื่อเพจโพสต์ต้นทาง "Mew Social" ไม่ใช่ชื่อบุคคล แต่ก็ไม่ได้ขยาย
  ต่อเป็นชื่อบุคคลใดๆ)
- ไม่มี API key ใดถูกใช้หรือบันทึกในไฟล์นี้ (ทุก fetch เป็น public page, ไม่มี key ในคำขอ)
- ไม่มีการ commit/build/collect.py รันในงานนี้ — ไฟล์ใหม่ 2 ไฟล์เท่านั้น (รายการด้านล่าง)

---

## ส่วน E — TODO (5 คอลัมน์: id, คำถาม/งาน, ใครตอบได้, เงื่อนไขปิด, priority)

| id | คำถาม/งาน | ใครตอบได้ | เงื่อนไขปิด | priority |
|---|---|---|---|---|
| TODO-GFH-01 | เทียบภาพ `dds_nowcast_gif` (radar_rain.gif) กับสิ่งที่ข่าว Weathernews/BMA AI Nowcast อธิบาย — เป็นผลผลิตเดียวกันหรือคนละระบบ | worker คนถัดไป, fetch ภาพจริง 1 ครั้ง + เทียบคำอธิบาย wni.com | ยืนยันได้ว่าใช่/ไม่ใช่ระบบเดียวกัน พร้อมอ้างอิงภาพ+ข้อความ | MVP |
| TODO-GFH-02 | หา public JSON/WMS/API endpoint ของ GISTDA "เช็คน้ำ" (ไม่ใช่แค่หน้าข่าวประชาสัมพันธ์) — probe คนละ TLS chain/เครื่องมือจาก workaround นี้ | worker คนถัดไป, ใช้ curl -k หรือเครื่องมืออื่นนอก WebFetch (ระวังไม่ scrape UI) | พบ endpoint สาธารณะจริง หรือสรุปว่าไม่มี (ปิด OPEN เป็น VERIFIED-negative) | next-version |
| TODO-GFH-03 | ยืนยันว่า Flood Forecasting API (Google) ยังอยู่สถานะ waitlist/pilot หรือเปิดกว้างขึ้นแล้ว ณ 2569 | worker คนถัดไป, เช็คหน้า developers.google.com/flood-forecasting หรือหน้า access-request | ยืนยันสถานะปัจจุบัน พร้อมวันที่ตรวจ | next-version |
| TODO-GFH-04 | ตรวจว่า `hii` `analyst/cctv` (106 กล้อง, ยังไม่เชื่อม ตาม `card_api_2026-09-27_hii_waterchart_basin.md`) มีกล้องในรัศมีสัมมากร/บางกะปิ หรือไม่ ก่อนตัดสินใจเชื่อม | worker คนถัดไป | รายชื่อกล้อง+พิกัด ที่อยู่ใน scope MVP (สัมมากร/กทม.) หรือสรุปว่าไม่มี | MVP (เพราะ MVP scope = สัมมากร+กทม.) |
| TODO-GFH-05 | ออกแบบ "resident card" ส่วนหน้าเว็บ (ชั้นเตือน 24 ชม./3 ชม./ตอนนี้/รายงานเอง) เป็น draft UI — งานนี้ห้าม implement, ส่งต่อให้ design workflow ที่กำลังจะแตะ site/ | ทีม design (site/ workflow ที่ระบุใน mission ของ repo นี้) | draft ผ่าน review, ไม่ embed ตัวเลขบุคคลที่สามเป็นค่าของเราเอง (ตามส่วน C ข้อควรระวัง) | MVP |

---

## ไฟล์ที่เขียนในงานนี้

- `docs/knowledge/card_thirdparty_google_urban_flash_flood_2026-09-28.md` (ไฟล์นี้)
- `docs/knowledge/api_census_additions_google_floodhub_2026-09-28.yaml` (บันทึก candidate source
  ใหม่ที่ยังไม่เชื่อม — list-only ตามคำสั่ง ไม่แก้ `sources/registry.yaml` จริง)

ไม่มีไฟล์ tracked ใดถูกแก้ไข ไม่มี commit ไม่มี build ไม่มีการรัน `collect.py` ในงานนี้.
