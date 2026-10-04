# สสน. — สถาบันสารสนเทศทรัพยากรน้ำ (องค์การมหาชน) (HII)

- **สังกัด**: องค์การมหาชน ภายใต้กระทรวงการอุดมศึกษา วิทยาศาสตร์ วิจัยและนวัตกรรม (RELAYED-GENERAL)
- **fetch status**: OK (200) — https://www.hii.or.th/ , หน้าวิสัยทัศน์/พันธกิจ (URL มี Thai percent-encoding, ดูไฟล์ raw), https://www.thaiwater.net/ — ดึงเมื่อ 2026-09-27

## พันธกิจ (VERIFIED, คำต่อคำจาก hii.or.th หน้า "วิสัยทัศน์ พันธกิจ", ดึง 2026-09-27)
วิสัยทัศน์:
> "เป็นคลังข้อมูลและคลังความรู้ที่ทันสมัย เพื่อสนับสนุนให้ประเทศไทยเกิดการบริหารจัดการน้ำอย่างมีประสิทธิภาพ และถ่ายทอดขยายผลการใช้งานโดยสร้างและพัฒนาเครือข่าย"

พันธกิจ (2 ข้อแรกที่ดึงได้):
> "1. วิจัยและพัฒนาเทคโนโลยีและนวัตกรรม ด้านสารสนเทศทรัพยากรน้ำ และการเพิ่มประสิทธิภาพคลังข้อมูลน้ำแห่งชาติ"
> "2. บูรณาการข้อมูล และให้บริการระบบคลังข้อมูลน้ำแห่งชาติ เพื่อสนับสนุนการพัฒนาและบริหารจัดการน้ำของประเทศ"

## อำนาจหน้าที่ตามกฎหมาย
RELAYED-GENERAL: HII เป็นผู้ดูแล "คลังข้อมูลน้ำแห่งชาติ" (National Hydroinformatics Data Center) และพอร์ทัล thaiwater.net — ไม่พบข้อความกฎหมายจัดตั้งคำต่อคำในรอบดึงนี้ (มีเมนู "กฎหมาย ระเบียบ ข้อบังคับ" และ hydrolaw.thaiwater.net แต่ยังไม่ได้เปิด)

## โครงสร้างหน่วยย่อยที่เกี่ยวกับน้ำท่วม
OPEN — เมนู "โครงสร้างองค์กร" มี URL แล้วแต่ยังไม่ได้ดึงเนื้อหา

## ทรัพย์สิน/พื้นที่ที่ควบคุม
HII ไม่ได้ควบคุมทรัพย์สินกายภาพ (เขื่อน/คลอง) — เป็นผู้ดูแล "คลังข้อมูลน้ำแห่งชาติ" (ระบบข้อมูล ไม่ใช่โครงสร้างพื้นฐาน)

## เครื่องมือข้อมูล (VERIFIED มี URL จริง)
- **thaiwater.net** — พอร์ทัลข้อมูลน้ำแห่งชาติ, เป็นแหล่งที่มาของฟีดที่ `sources/registry.yaml` ใช้อยู่แล้ว (thaiwater_canal_waterlevel, thaiwater_flood_road, thaiwater_rain_24h ผ่าน api-v3.thaiwater.net)
- **hydrolaw.thaiwater.net** — ระบบกฎหมายด้านบริหารจัดการน้ำ

## กระบวนการ
OPEN — HII เป็นผู้ให้ข้อมูล ไม่ใช่ผู้สั่งการปฏิบัติการ (ตามพันธกิจที่ระบุ "วิจัย/บูรณาการข้อมูล")

## ช่องทางถึงประชาชน
thaiwater.net เป็นช่องทางสาธารณะหลัก (VERIFIED มีอยู่จริง, ใช้งานแล้วโดย FloodConnect)

## waterchart.thaiwater.net — "แผนที่ผังน้ำประเทศไทย, คลังข้อมูลน้ำแห่งชาติ" (สำรวจเพิ่มตามคำขอ founder)
- **fetch status**: https://waterchart.thaiwater.net/ ตอบ 200 แต่ DNS ของโดเมนนี้ (27.131.148.79) มี TLS chain ที่ตรวจสอบไม่ผ่าน (curl `ssl_verify_result 20` — chain ไม่สมบูรณ์/ไม่น่าเชื่อถือ) → ต้องดึงด้วย `curl -k` เสมอ **OPEN security remark**: หน่วยงานรัฐใช้ TLS chain ที่ตรวจสอบไม่ผ่านสำหรับพอร์ทัลสาธารณะ ควรแจ้งเตือนก่อนนำไปใช้งานจริง
- โครงสร้างหน้า: เว็บแอป Next.js แบบ **static export** (`__NEXT_DATA__` ระบุ `"nextExport":true, "pageProps":{}` — ไม่มีข้อมูลฝังตอน build) หน้า HTML ดิบมีแค่ 16KB, เนื้อหาที่มองเห็นได้มีเพียงหัวข้อ "แผนที่ผังน้ำประเทศไทย" / "คลังข้อมูลน้ำแห่งชาติ"
- **การตรวจสอบ 1 รอบ (VERIFIED, ดึงเมื่อ 2026-09-27)**: ดึง `/_next/static/chunks/pages/index-dc9f53418ae4907f.js` + 3 shared chunks (`219-...js`, `611-...js`, `814-...js`) มา grep หา `fetch(`/`axios(`/`api`/`.json`/`baseURL`/`NEXT_PUBLIC` — **ไม่พบ endpoint API หรือ fetch call ใดๆ ในทั้ง 4 ไฟล์เลย** พบเพียง string UI เช่น `"basin"`/`"Basin"` (ตัวเลือกลุ่มน้ำ) และ class name `Home_mapContent`
- **สรุปสถานะ machine-readable**: **ยังสรุปไม่ได้จากการ grep static bundle เพียงอย่างเดียว (OPEN)** — เป็นไปได้ 2 ทาง: (ก) หน้านี้เป็นเพียงหน้า splash ที่ลิงก์ไปหน้าเนื้อหาอื่นซึ่งมี JS chunk คนละไฟล์ที่ยังไม่ได้ดึง หรือ (ข) ผังน้ำจริงเป็นภาพ/แผนที่แบบ static (ไม่มี live API) — **เนื่องจากไม่พบ fetch/axios/api string ใดๆ ในบันเดิลไคลเอนต์ที่ตรวจ จึงเอนไปทาง "ไม่ใช่ JSON API ที่เข้าถึงได้ตรงๆ" มากกว่า** ต้องรัน browser จริง (Playwright, สังเกต network request) เพื่อยืนยันขาดไม่ได้ — ไม่ได้ทำในรอบนี้เพราะ RAM จำกัดและ scope คำขอกำหนดไว้ที่ 1 pass แบบ static grep เท่านั้น
- ไม่ได้ทำการ fetch endpoint ใดเพิ่มเติม เพราะไม่พบ URL ที่ "promising" จากการ grep เลย (0 candidates)
- ไฟล์ raw ทั้งหมดเก็บที่ `raw/knowledge/agencies/hii/` (waterchart_index.html + 4 ไฟล์ .js)

## ตำแหน่งสินทรัพย์ที่ดึงได้ (lat/lon)
- **thaiwater.net (api-v3)**: ยังไม่ตรวจสอบว่า endpoint ที่ใช้อยู่ใน registry.yaml (canal_waterlevel, flood_road, rain_24h) มี field lat/lon ต่อสถานีหรือไม่ (OPEN — ต้องเปิด response จริง)
- **waterchart.thaiwater.net**: ไม่พบพิกัดใดๆ เพราะไม่พบ API/ข้อมูลเชิงกลไกเลยในรอบนี้ (ดูด้านบน)

## สิ่งที่ FloodConnect ใช้ได้ทันที
ฟีดจาก thaiwater.net (api-v3) **ถูกใช้แล้ว** ใน registry.yaml (3 ฟีด: canal_waterlevel, flood_road, rain_24h) — เป็นหน่วยงานที่ FloodConnect เชื่อมต่อได้ดีที่สุดในบรรดา 19 หน่วยงานนี้แล้ว ควรสำรวจ endpoint อื่นของ api-v3.thaiwater.net ที่ยังไม่ได้ใช้ (เช่น ระดับน้ำเขื่อน, สถานีโทรมาตร, พิกัดสถานี) เป็นลำดับถัดไป **waterchart.thaiwater.net ยังไม่พร้อมนำเข้าใช้งาน** — ไม่พบ machine-readable data ในรอบตรวจนี้ ไม่ควรจัดอันดับสูงจนกว่าจะยืนยันด้วย browser network capture จริง

## OPEN questions
- endpoint อื่นของ api-v3.thaiwater.net ที่ FloodConnect ยังไม่ได้ใช้มีอะไรบ้าง (ต้องดู API docs) และมี field พิกัดหรือไม่
- โครงสร้างหน่วยย่อยและกฎหมายจัดตั้งคำต่อคำ
- waterchart.thaiwater.net โหลดข้อมูลผังน้ำจริงมาจากไหน (ต้องใช้ browser network capture ยืนยัน)
- ทำไม TLS chain ของ waterchart.thaiwater.net ตรวจสอบไม่ผ่าน — misconfiguration หรือ self-signed/internal CA
