# เหตุการณ์ (Incidents) — 2026-09-27

บันทึกสั้น เพื่อความโปร่งใส ไม่มีชื่อบุคคล ไม่มีชื่อผู้ให้บริการ AI.

## 1. Trailer ระบุที่มา AI พบใน 10 commit ที่ยังไม่ push

การรีวิวก่อนเผยแพร่แบบอิสระ (independent pre-publish review) พบว่า 10 commit ที่ยังไม่ push
มี trailer ระบุที่มา AI ติดอยู่ในข้อความ commit ซึ่งขัดกับกฎห้ามระบุชื่อผู้ให้บริการ AI ใน
artifact ที่ออกจากเครื่อง แก้ไขด้วยการเขียนข้อความ commit ใหม่เฉพาะส่วน message (message-only
rewrite) — เนื้อหาไฟล์ (tree) เหมือนเดิมทุกไบต์ (byte-identical) ไม่มีการเปลี่ยน diff ใดๆ.
HEAD เปลี่ยนจาก `b6110ec` เป็น `c7cdc5d` เพราะ hash เปลี่ยนตามข้อความ commit ที่แก้ ไม่ใช่เพราะ
เนื้อหาเปลี่ยน.

## 2. Worker รีเฟรช 2 ชั่วโมงรัน `collect.py --all` ซ้ำภายใน ~2 นาที

Worker ที่ทำหน้าที่รีเฟรชข้อมูลทุก 2 ชั่วโมงรันคำสั่ง `collect.py --all` สองครั้งภายในเวลา
ห่างกันประมาณ 2 นาที (13:44Z และ 13:46Z) ยิงคำขอไปยังโฮสต์ทั้งหมด ~29 แห่งซ้ำ ขัดกับกฎ
"หนึ่งคำขอต่อหนึ่ง URL ต่อหนึ่งรัน" ใน `AGENTS.md` §2 ตรวจสอบแล้วไม่มี response 403/ถูกแบนจาก
โฮสต์ใด และไม่มีความเสียหายต่อฐานข้อมูล (`data/observations.sqlite` ไม่มีแถวซ้ำผิดปกติ/เสียหาย)
ย้ำกฎเดิมอีกครั้งกับ worker ที่เกี่ยวข้อง ไม่ต้องแก้โค้ดเพิ่มรอบนี้ (root cause เป็นการรันซ้ำจาก
ฝั่ง orchestration ไม่ใช่บั๊กใน `collect.py` เอง).

## 3. ป้าย "ปกติ" ดิบจากหน่วยงานหลุดผ่าน chain-node status โดยไม่ผ่านบันไดระดับปกติ

Chain-node status label แสดงคำว่า "ปกติ" ของหน่วยงานตรงๆ (raw passthrough) โดยไม่ผ่านบันได
เปรียบเทียบระดับปกติ (normal-level ladder) เดียวกับที่ hero section ของหน้าใช้อยู่ ทำให้
สถานะที่แสดงอาจไม่สอดคล้องกับเกณฑ์ภายในของคลังนี้เอง แก้ไขแล้วใน commit `7342960`
("site: chain labels use the same normal-level ladder as the hero").

## 4. WL.BMA.02 แสดง "สูงกว่าปกติ" จากเพดานควบคุมของคนละสถานี คนละตำแหน่ง คนละ datum (P0)

`sources/canal_normal_levels.yaml` มีแถว `basis: official_threshold` (เพดานควบคุม +0.40/+0.50
ม.รทก. จากแผน กทม. 2569 ตาราง ง p.191) ที่ผูกไว้กับ `station_code: WL.BMA.02` แต่พิกัดของแถวนี้
เอง (13.7763, 100.6713) และตัวเลข 0.40/0.50 เป็นของ**สถานีสูบน้ำคลองบ้านม้า 2 / ST.SPS.01**
(สถานีสูบ) ไม่ใช่ของ **WL.BMA.02** (เกจวัดระดับ "จุดวัดคลองบ้านม้า ตอนถนนรามคำแหง" ที่
13.77273, 100.66595 ตาม `docs/knowledge/bma_plan2569_stations.yaml` seq 39) -- สองสถานีห่างกัน
~630 ม. (เกินเกณฑ์ 100 ม. ที่ถือว่าเป็นสถานีเดียวกัน) และเส้นเตือน/วิกฤตของ WL.BMA.02 เอง
(2.14/2.68 ม., จาก bma_watermap) ต่างจากเพดานแผนราว 1.7 ม. สอดคล้องกับการเป็นคนละ datum (ไม่
เคยยืนยัน) ผลคือหน้าเว็บแสดง WL.BMA.02 (ค่าจริง 0.71-0.73 ม.) เป็น "สูงกว่าปกติ" (ABOVE_NORMAL)
ทั้งที่ควรเป็น "ยังไม่มีเกณฑ์ปกติ" (NO_NORMAL_BASIS) -- ตรวจพบโดย orchestrator ด้วย read-only SQL
query โดยตรง (P0)

**แก้ไข**: (1) เปลี่ยน `station_code` ของแถวเดิมจาก `WL.BMA.02` เป็น `ST.SPS.01` (append-only
-- แถวเดิมไม่ถูกลบ, เพิ่มฟิลด์ `applies_to`/`datum`/`station_distance_m` + note แก้ไข) (2) เพิ่ม
บันไดปฏิเสธทั่วไปใน `site/build_data.py.load_canal_normal_levels()` และ
`tools/heromap/sammakorn_map.load_normal_levels()`: แถว `basis: official_threshold` ใดๆ ที่
`station_distance_m` เกิน 100 ม. หรือขาดหาย หรือ `datum` ไม่ยืนยัน (missing/OPEN/unknown) จะถูก
ปฏิเสธเสมอ ไม่ถูกนำไปใช้ (3) บันทึกความขัดแย้งใน
`docs/knowledge/statement_contradictions_2026-09-27.yaml` (`station_vs_plan` list, id
`station_vs_plan:2026-09-27_wl_bma_02_vs_st_sps_01`, datum ยังเป็น OPEN) (4) แก้เทสต์
`tests/test_sammakorn_chain.py` สองรายการที่เคยยืนยันพฤติกรรมผิด (`สูงกว่าปกติ`) ให้ยืนยัน
พฤติกรรมถูก (`ยังไม่มีเกณฑ์ปกติ`) แทน และเพิ่มเทสต์ใหม่
`tests/test_official_threshold_admissibility.py` คุมบันไดปฏิเสธทั่วไป.
