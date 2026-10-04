# ดัชนีหน่วยงาน — ระบบนิเวศการจัดการน้ำ/น้ำท่วม (ecosystem ownership map)

สำรวจเมื่อ 2026-09-27, curl (browser UA, 20s timeout, one attempt/URL, ไม่ retry) + Playwright 1 หน้า (acs_flapgate, guest read-only). ที่มา raw: `raw/knowledge/agencies/`. แต่ละแถวมี tag ความน่าเชื่อถือตามการ์ดของแต่ละหน่วยงาน (VERIFIED/RELAYED-GENERAL/OPEN)

| หน่วยงาน | พันธกิจ (1 บรรทัด) | ทรัพย์สินหลัก | ฟีดข้อมูลที่ใช้ได้ (URL) | ระดับ | fetch status | tag |
|---|---|---|---|---|---|---|
| [onwr](onwr.md) | กำหนดนโยบาย/กำกับการบริหารจัดการน้ำทั้งประเทศ | ไม่มี (หน่วยนโยบาย) | ไม่พบ dashboard ที่ยืนยันได้ | ชาติ | OK (200) | VERIFIED (วิสัยทัศน์/พันธกิจ) |
| [rid](rid.md) | ชลประทาน/ควบคุมเขื่อน-คลอง-ประตูระบายน้ำ | เขื่อน/คลอง/ประตู/สถานีสูบ (ไม่ทราบจำนวนรวม) | `water.rid.go.th/flood/...` (daily.pdf, planlow.html, plan_ew.html ฯลฯ — 15+ URL ใหม่) | ชาติ/ภาค (hydro-5=ภาคกลาง ครอบคลุมเจ้าพระยาตอนล่าง) | OK บางส่วน (เว็บหลัก JS-empty, WMSC/water.rid.go.th ใช้ได้) | VERIFIED (เนื้อหา daily/weekly report จริง) |
| [dwr](dwr.md) | ทรัพยากรน้ำผิวดินนอกเขตชลประทาน+น้ำบาดาล | OPEN | ไม่พบ | ชาติ | fetch content-empty (JS shell) | RELAYED-GENERAL |
| [tmd](tmd.md) | พยากรณ์อากาศ/เตือนภัย | เรดาร์ตรวจอากาศ (จำนวน OPEN) | เมนู "การคาดการณ์พื้นที่เสี่ยงภัยน้ำท่วมฉับพลัน" (URL ย่อยยังไม่ยืนยัน) | ชาติ | OK (200) | VERIFIED (รายการเมนู) |
| [hii](hii.md) | คลังข้อมูลน้ำแห่งชาติ/วิจัยสารสนเทศน้ำ | ไม่มี (ระบบข้อมูล) | thaiwater.net (api-v3, **ใช้แล้วใน registry**), waterchart.thaiwater.net (ยังไม่ยืนยัน machine-readable) | ชาติ | OK (200) | VERIFIED (วิสัยทัศน์/พันธกิจ) |
| [gistda](gistda.md) | เทคโนโลยีอวกาศ/ภูมิสารสนเทศ | ไม่มี (ภาพถ่ายดาวเทียม) | disaster.gistda.or.th (ยังไม่แกะ API) | ชาติ | OK (200) | VERIFIED (EN vision) |
| [egat](egat.md) | ผลิตไฟฟ้า/ควบคุมเขื่อนผลิตไฟฟ้าใหญ่ | เขื่อนใหญ่ (ภูมิพล/สิริกิติ์ ฯลฯ — ตัวเลข OPEN) | ไม่พบ (landing page เท่านั้น) | ชาติ | fetch content-empty (interstitial) | RELAYED-GENERAL |
| [ddpm](ddpm.md) | ประกาศเขตภัยพิบัติ/ช่วยเหลือผู้ประสบภัย | ไม่มี (ไม่ควบคุมโครงสร้างพื้นฐาน) | ไม่พบ | ชาติ/จังหวัด | fetch content-empty (JS shell) | RELAYED-GENERAL |
| [moi](moi.md) | ต้นสังกัดโครงสร้างปกครองภูมิภาค | ไม่มี | ไม่พบ | ชาติ/จังหวัด | fetch content-empty (JS shell) | RELAYED-GENERAL |
| [bma_dds](bma_dds.md) | ระบายน้ำ กทม. (สถานีสูบ/ประตู/อุโมงค์) | สถานีสูบ/ประตู/อุโมงค์ (ตัวเลข OPEN) | **ใช้แล้ว 6 ฟีดใน registry** (dds_daily_pdf ฯลฯ) | กทม. | fetch content-empty (JS shell) | RELAYED-GENERAL |
| [bma_saphansung](bma_saphansung.md) | ปกครองเขต/ระบายน้ำระดับพื้นที่ | OPEN | ไม่พบ | เขต | **fetch failed 403** | RELAYED-GENERAL |
| [bma_bangkapi](bma_bangkapi.md) | ปกครองเขต/ระบายน้ำระดับพื้นที่ (ฝั่งตะวันออก กทม.) | OPEN | ไม่พบ | เขต | **fetch failed 403** | RELAYED-GENERAL |
| [mea](mea.md) | จ่ายไฟฟ้า กทม./สมุทรปราการ/นนทบุรี | เครือข่ายไฟฟ้า (ตัวเลข OPEN) | ไม่พบ | กทม.+ปริมณฑล | OK (authority page) | VERIFIED (อำนาจหน้าที่ตามกฎหมาย) |
| [marine](marine.md) | ร่องน้ำ/ท่าเรือ/สิ่งปลูกสร้างล่วงล้ำลำน้ำ | ร่องน้ำ/ท่าเรือ (ตัวเลข OPEN) | imis.md.go.th, gis.md.go.th (ยังไม่แกะ) | ชาติ | OK (200), mandate page 503 | RELAYED-GENERAL |
| [dpt](dpt.md) | ผังเมือง/ควบคุมอาคาร | ไม่มี | ไม่พบ | ชาติ | **fetch failed 000** | RELAYED-GENERAL |
| [doh_exat](doh_exat.md) | ทางหลวง (EXAT ยังไม่สำรวจ) | โครงข่ายถนน (ตัวเลข OPEN) | ไม่พบใหม่ (มี governor_shared_flooded_roads ใน registry อยู่แล้ว) | ชาติ | OK (200) | RELAYED-GENERAL |
| [basin_committee](basin_committee.md) | กลไกนโยบายระดับลุ่มน้ำ (ภายใต้ สทนช.) | ไม่มี | ไม่มี | ลุ่มน้ำ | เหมือน onwr | RELAYED-GENERAL |
| [nesdc_bb](nesdc_bb.md) | งบประมาณ/แผนพัฒนาเศรษฐกิจ | ไม่มี | ไม่มี | ชาติ | **fetch failed (redirect loop)** | RELAYED-GENERAL |
| [acs_flapgate](acs_flapgate.md) | ระบบเอกชน/พันธมิตร แสดงผลประตูระบายน้ำ-ระดับน้ำของโครงการชลประทาน RID (ไม่ใช่ .go.th) | 67 สถานี/29 โครงการชลประทานทั่วประเทศ | `floodgateinfo.acsflapgate.com/floodgate/FloodgateInfo` (POST, no-auth) | ระดับโครงการชลประทาน (ทั่วประเทศ ไม่ครอบคลุม กทม.โดยตรง) | OK (200), Playwright guest-mode verified | VERIFIED (ข้อมูล real-time จริง) |

## ตำแหน่งสินทรัพย์ที่ดึงได้ (lat/lon) — สรุปข้ามหน่วยงาน (ตามลำดับความสำคัญของ founder)
| แหล่ง | รูปแบบพิกัด | จำนวนแถวที่ใช้ได้ | stable id | หมายเหตุ |
|---|---|---|---|---|
| **acs_flapgate.com** (`FloodgateInfo` API) | ฝังใน Google Maps iframe string 2 ชั้น: `!2d/!3d` (ศูนย์กลางกลุ่ม, หยาบ) และ `!2z<base64 DMS>` (จุดจริง, ต้อง decode) | **57/67 สถานี** มีพิกัดจุดแม่นยำ (28 จุดต่างจากศูนย์กลางกลุ่มอย่างมีนัยสำคัญ) | มี (`floodgate_id`) | ดีที่สุดในบรรดาที่สำรวจรอบนี้ — แต่เป็นเครือข่ายชลประทานทั่วประเทศ ไม่ใช่ กทม. |
| bma_dds (`bma_klongmap`) | OPEN — ยังไม่เปิด URL จริงใน registry.yaml เพื่อยืนยัน field พิกัด | OPEN | OPEN | อยู่ใน registry แล้ว แต่ scope worker นี้ไม่ครอบคลุมการเปิดตรวจ registry |
| rid (water.rid.go.th) | ไม่มีพิกัดในตัวเอง | 0 | - | ใช้ acs_flapgate แทนสำหรับพิกัดระดับสถานี |
| marine (imis.md.go.th, gis.md.go.th) | OPEN — คาดว่ามี แต่ยังไม่เปิด URL | OPEN | OPEN | ควรสำรวจต่อลำดับแรกในรอบถัดไป |
| hii (waterchart.thaiwater.net) | ไม่พบ (ไม่พบ API เลยในการ grep static bundle) | 0 | - | ต้อง browser network capture จริงจึงจะสรุปได้ |
| onwr/tmd/gistda/egat/ddpm/moi/mea/dpt/doh_exat/basin_committee/nesdc_bb | ไม่พบพิกัดใดๆ ในรอบนี้ | 0 | - | ส่วนใหญ่เป็นหน่วยนโยบาย/ไม่ใช่เจ้าของทรัพย์สินจุด หรือเว็บเป็น JS shell |

## ฟีดใหม่ที่ควรต่อเข้า FloodConnect (เรียงตามความสำคัญ — มีพิกัดขึ้นก่อนตามลำดับความสำคัญของ founder)
1. **`floodgateinfo.acsflapgate.com/floodgate/FloodgateInfo`** (JSON, POST, no-auth) — 67 สถานี, 57 มีพิกัดแม่นยำ, ค่าระดับน้ำ/อัตราการไหล real-time — **machine-readable เต็มรูปแบบ**, แต่ต้องยืนยันเจ้าของ/สิทธิ์ใช้ข้อมูลก่อน (ไม่ใช่โดเมนราชการ)
2. **RID — `water.rid.go.th/flood/plan_new/planlow.html`** (HTML) และ **`plan_ew.html`** (HTML) — ผังน้ำเจ้าพระยาตอนล่าง/ฝั่งตะวันออก-ตะวันตก แบบรายวัน ตอบคำถาม "น้ำเหนือถึงกรุงเทพฯ ฝั่งไหนแล้ว" โดยตรง ไม่มีพิกัดในตัวแต่เป็น HTML ที่ parse ได้
3. **RID — `water.rid.go.th/flood/flood/daily.pdf`** (PDF, 14 หน้า, รายวัน) — รายงานทางการฉบับเต็ม ต้อง parse PDF
4. **TMD — "การคาดการณ์พื้นที่เสี่ยงภัยน้ำท่วมฉับพลัน"** (URL ย่อยยังไม่ยืนยัน) — พยากรณ์เตือนภัยล่วงหน้า ต่างจากข้อมูลระดับน้ำปัจจุบันที่มีอยู่แล้ว
5. **GISTDA — `disaster.gistda.or.th`** — ภาพถ่ายดาวเทียมพื้นที่น้ำท่วมระดับประเทศ (รูปแบบยังไม่ยืนยัน: API/WMS/tile)
6. **Marine — `imis.md.go.th` / `gis.md.go.th`** — ระบบ GIS โครงสร้างพื้นฐานทางน้ำ อาจมีพิกัดร่องน้ำ/สถานีวัดระดับน้ำ (ยังไม่แกะ)
7. waterchart.thaiwater.net — **ไม่แนะนำให้จัดลำดับสูง** จนกว่าจะยืนยัน machine-readable ด้วย browser capture จริง (รอบนี้ grep static bundle ไม่พบ API)

## หน้าที่ซ้อนกันที่เห็นจากพันธกิจเอง (agency mission-text overlaps)
1. **onwr vs rid/egat/dwr — "ใครสั่งเปิด/ปิดเขื่อน"**: พันธกิจ สทนช. ระบุ "กำกับ ติดตาม ประเมินผลการบริหารจัดการทรัพยากรน้ำของประเทศ" (onwr.go.th, VERIFIED) ซึ่งครอบคลุมน้ำทั้งหมดรวมถึงเขื่อนของ กฟผ. และกรมชลประทาน แต่ทั้ง กฟผ. และกรมชลประทานเป็นเจ้าของทรัพย์สินจริงที่ต้องเป็นผู้ปฏิบัติสั่งเปิด-ปิด — **ไม่มีหน้าใดในทั้งสามหน่วยงานที่ระบุคำต่อคำว่าใครลงนามอนุมัติขั้นสุดท้าย** เป็นจุดคลุมเครือเชิงพันธกิจที่ต้องสอบถามเพิ่ม
2. **ddpm vs moi — "ใครประกาศเขตภัยพิบัติ"**: ทั้งสองหน่วยงานเป็น JS shell ในรอบนี้จึงไม่สามารถเทียบข้อความพันธกิจได้โดยตรง (OPEN — ยังไม่พบข้อความคำต่อคำจากทั้งคู่เพื่อเทียบซ้อนทับ)
3. **rid vs acs_flapgate — ภาพรวมเดียวกันคนละแหล่ง**: กรมชลประทานมีทั้งเว็บทางการ (water.rid.go.th) และระบบพันธมิตรเอกชน (acsflapgate.com) ที่รายงานระดับน้ำของ "โครงการชลประทาน" เดียวกัน (ชื่อกลุ่มตรงกันคำต่อคำ เช่น "โครงการชลประทานสงขลา") — เป็นข้อมูล**ซ้ำแหล่งแต่คนละช่องทาง** ไม่ใช่ความขัดแย้งเชิงอำนาจหน้าที่ แต่ทีมพัฒนาต้องตัดสินใจว่าจะใช้ฟีดไหนเป็นหลัก

## OPEN questions เชิงระบบ (ไม่ผูกกับหน่วยงานเดียว)
- ใครลงนามอนุมัติขั้นสุดท้ายในการระบายน้ำเขื่อนใหญ่ (ภูมิพล/สิริกิติ์) — สทนช. กำหนดนโยบาย, กฟผ.เป็นเจ้าของ, กรมชลประทานเป็นผู้บริหารจัดการน้ำในแม่น้ำ — สายบังคับบัญชาจริงยังไม่ verified จากหน้าเว็บใดเลย
- เจ้าของ/สิทธิ์ใช้ข้อมูลของ acsflapgate.com (โดเมนเอกชน) ก่อนนำเข้าระบบ FloodConnect จริง
- อีก 6 หน่วยงาน (rid เว็บหลัก, dwr, ddpm, moi, bma_dds, dpt) เป็น JS-only shell หรือเชื่อมต่อไม่ได้ทั้งหมด — ต้องใช้ Playwright ในรอบที่ RAM มีเพียงพอ หรือหา sitemap/API เอกสารแทน
