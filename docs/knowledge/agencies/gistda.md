# GISTDA — สำนักงานพัฒนาเทคโนโลยีอวกาศและภูมิสารสนเทศ (องค์การมหาชน)

- **สังกัด**: องค์การมหาชน ภายใต้กระทรวงการอุดมศึกษา วิทยาศาสตร์ วิจัยและนวัตกรรม (RELAYED-GENERAL)
- **fetch status**: OK (200) — https://www.gistda.or.th/ , https://www.gistda.or.th/about/organizarional-information-about-gistda-corporate-identity-gistda-core-value/ , https://disaster.gistda.or.th/ — ดึงเมื่อ 2026-09-27 (หน้า about เป็นภาษาอังกฤษ — เว็บสลับเป็น EN โดยอัตโนมัติในหน้าที่ดึงได้)

## พันธกิจ (VERIFIED, คำต่อคำจาก gistda.or.th หน้า about, ดึง 2026-09-27, ภาษาอังกฤษตามต้นฉบับ)
> Vision: "To be an organization that brings together the values of space technology and geo-informatics for the greatest benefit of humanity."
> Objective: "Developing geo-informatics and space technology as a non boundary knowledge for the country development"

## อำนาจหน้าที่ตามกฎหมาย
RELAYED-GENERAL: จัดตั้งตาม พ.ร.ก./พ.ร.บ. อวกาศ (เมนู "Royal Decrees" / "Space Act" ปรากฏจริงในหน้าที่ดึงมา แต่ยังไม่ได้เปิดอ่านเนื้อหา) — ทำหน้าที่วิเคราะห์ภาพถ่ายดาวเทียมสำหรับภัยพิบัติ

## โครงสร้างหน่วยย่อยที่เกี่ยวกับน้ำท่วม
OPEN — พบเมนู "Organizational Structure" มี URL แล้วแต่ยังไม่ได้ดึงเนื้อหารายละเอียด

## ทรัพย์สิน/พื้นที่ที่ควบคุม
GISTDA ไม่ควบคุมทรัพย์สินทางน้ำ — เป็นผู้ให้บริการภาพถ่ายดาวเทียมและระบบวิเคราะห์พื้นที่น้ำท่วม (Thailand Ground Receiving Station ตามประวัติที่ระบุในหน้า about — "Thailand Ground Receiving Station was set up as first of its kind in Southeast Asia")

## เครื่องมือข้อมูล (VERIFIED มี URL จริง)
- **disaster.gistda.or.th** — พอร์ทัลติดตามภัยพิบัติของ GISTDA โดยเฉพาะ (fetch สำเร็จ 200, ยังไม่ได้แกะเนื้อหาเชิงลึกในรอบนี้ — น่าจะมีแผนที่น้ำท่วมจากภาพดาวเทียม)

## กระบวนการ
OPEN — ไม่พบขั้นตอนว่า GISTDA ส่งข้อมูลภาพดาวเทียมน้ำท่วมให้หน่วยงานปฏิบัติ (ปภ./สทนช.) อย่างไร ในหน้าที่ดึงมา

## ช่องทางถึงประชาชน
OPEN

## สิ่งที่ FloodConnect ใช้ได้ทันที
**disaster.gistda.or.th ยังไม่มีใน `sources/registry.yaml`** — เป็นฟีดใหม่ที่มีศักยภาพสูง (ภาพดาวเทียมพื้นที่น้ำท่วมระดับประเทศ เสริมกับข้อมูลระดับน้ำจาก thaiwater.net และแผนที่ถนนน้ำท่วมจาก BMA) ควรสำรวจ URL/API ของพอร์ทัลนี้ต่อในรอบถัดไป

## ตำแหน่งสินทรัพย์ที่ดึงได้ (lat/lon)
OPEN — GISTDA ให้บริการภาพถ่ายดาวเทียม (raster) ไม่ใช่ registry ของทรัพย์สินจุด (เขื่อน/ประตู) เอง คาดว่า disaster.gistda.or.th อาจมีชั้นข้อมูล (layer) พื้นที่น้ำท่วมเป็น polygon/raster มากกว่าจุดพิกัดรายทรัพย์สิน — ยังไม่ได้ตรวจ

## OPEN questions
- disaster.gistda.or.th มี API หรือเป็นแผนที่ภาพ (WMS/tile) เท่านั้น
- คาเดนซ์การอัปเดตภาพดาวเทียมน้ำท่วม (รายวัน/ตามเหตุการณ์)
- โครงสร้างหน่วยงานภายในที่รับผิดชอบภัยพิบัติน้ำท่วมโดยตรง
