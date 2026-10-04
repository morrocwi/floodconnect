# กรมทรัพยากรน้ำ (DWR)

- **สังกัด**: กระทรวงทรัพยากรธรรมชาติและสิ่งแวดล้อม (RELAYED-GENERAL)
- **fetch status**: https://www.dwr.go.th/ ตอบ 200 แต่เป็น JS-only SPA shell (0 anchor tags ในหน้า HTML ดิบ) → "fetch content-empty (JS-only shell)". ลอง https://www.dwr.go.th/about-dwr และ https://www.dwr.go.th/webapp/water/?p=1 ได้ 404 ทั้งคู่ — ไม่ retry ตามกติกา one-attempt

## พันธกิจ
RELAYED-GENERAL: DWR ดูแลทรัพยากรน้ำผิวดินนอกเขตชลประทาน (แม่น้ำ ลำคลองสายรอง) และน้ำบาดาลบางส่วน ประสานกับ สทนช. ในระดับนโยบาย — ไม่ได้ยืนยันจากหน้าเว็บทางการในรอบนี้

## อำนาจหน้าที่ตามกฎหมาย
OPEN — ไม่พบเนื้อหาจากการดึงรอบนี้

## โครงสร้างหน่วยย่อยที่เกี่ยวกับน้ำท่วม
OPEN

## ทรัพย์สิน/พื้นที่ที่ควบคุม
OPEN

## เครื่องมือข้อมูล
OPEN — ไม่พบ URL API/dashboard ในรอบนี้

## กระบวนการ
OPEN

## ช่องทางถึงประชาชน
OPEN

## สิ่งที่ FloodConnect ใช้ได้ทันที
ไม่พบฟีดจาก dwr.go.th ใน `sources/registry.yaml` ปัจจุบัน และไม่พบ URL ใหม่ในรอบนี้ (fetch content-empty)

## ตำแหน่งสินทรัพย์ที่ดึงได้ (lat/lon)
OPEN — ไม่พบข้อมูลใดๆ (JS shell)

## OPEN questions
- ต้องหา URL เนื้อหาจริงของเว็บ DWR (เมนูเรนเดอร์ด้วย JS ทั้งหมด) — อาจต้องใช้ sitemap.xml หรือ Google cache แทน Playwright (RAM จำกัดรอบนี้)
- พันธกิจ/อำนาจหน้าที่/โครงสร้างหน่วยย่อยที่เกี่ยวกับน้ำท่วม
