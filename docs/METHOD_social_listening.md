# เสียงจากอินเทอร์เน็ต (social listening) — วิธีการ + effectiveness record

**สิ่งนี้ต่างจาก "social listening" ทั่วไปตรงไหน**: ชั้นนี้เก็บ**เฉพาะสามอย่าง**ต่อแถว —
**จุด** (ซอย/สถานที่), **สภาพน้ำที่ตรวจสอบได้** (คำศัพท์ตายตัว:
house/garage/road/pond_overflow/canal_overbank/rising/receding/unknown — **ไม่ใช่ความรู้สึก/sentiment**),
และ **เวลา** — พร้อม `area` และ `publisher_type` (สื่อ vs บุคคล, **ไม่เก็บชื่อคน**เลย). ทุกแถว
**อ่านคู่กับสถานีทางการเสมอ** (ดู `readout.py`'s "เสียงจากอินเทอร์เน็ต (social listening)"
section — ตาราง agreement/disagree/no-overlap ต่อสถานี เป็น lookup ไม่ใช่คะแนน) และชั้นนี้มี
effectiveness record ของตัวเอง (เอกสารนี้ + ตาราง `method_evaluation` ที่เขียนโดย
`python3 social_listening.py --evaluate`) — ไม่ใช่ถือว่ามีประโยชน์เอาไว้ก่อนโดยไม่เช็ค.

โค้ด: `social_listening.py` (`parse_paste`, `parse_google_snapshot`, `search_google` (optional),
`write_rows`, `evaluate_metrics`). Registry: `sources/registry.yaml` → `social_listening_google`,
`social_listening_paste`. ต้นฉบับ 2 ไฟล์ที่ประเมินด้านล่าง อยู่ใน `raw/community/` (gitignored) —
`social_listening_paste_sammakorn_2026-09-26.md`, `social_listening_google_ram53_2026-09-26.md`.

---

## วิธีการที่ใช้จริง วันที่ 26 ก.ย. 2569

1. **สัมมากร**: คนในกลุ่ม Facebook "รวมของดีสัมมากร" โพสต์/คอมเมนต์ 2 กระทู้ → รวบรวม→ตัดชื่อ→
   จัดเป็นตาราง ซอย/จุด | สภาพ | เวลา (≈, นับถอยจากเวลาที่รวบรวม 12:07 น.).
2. **รามคำแหง 53**: Google web search กรอง 24 ชม. (`"รามคำแหง 53" น้ำท่วม` +
   `site:tiktok.com|x.com`, ไม่ล็อกอิน) ตอน ~13:00 น. → 14 ผลลัพธ์สาธารณะ (Facebook/TikTok/
   Instagram + สื่อ JS100/อีจัน/Rodee).

ทั้งสองไฟล์**ไม่มีชื่อบุคคลอยู่แล้วตั้งแต่รวบรวม** — ตรวจซ้ำแล้วก่อนคัดลอกเข้า `raw/community/`.

---

## Effectiveness — วัดจากไฟล์จริง 2 ไฟล์นี้เท่านั้น (ตัวเลขทุกตัว = MEASURED โดยการนับด้วยมือจาก
ไฟล์ หรือ = OPEN ตามที่ระบุ — ไม่มีตัวเลขไหนมาจากความจำ)

### สัมมากร (`social_listening_paste`, กลุ่ม Facebook)

ตัวเลข "ระบบ" แถวล่างมาจากการรันจริงวันนี้: `python3 social_listening.py --import-paste
raw/community/social_listening_paste_sammakorn_2026-09-26.md --at 2026-09-26T12:07:00+07:00`
แล้ว `--evaluate --area sammakorn --date 2026-09-26` (เขียนลง `method_evaluation` table จริง) —
พาร์สได้ **22 แถว** จากส่วน A (ตาราง "จุดที่น้ำเข้าบ้านแล้ว") เท่านั้น ส่วน B ("บึง/ทะเลสาบ") เป็น
bullet list ไม่ใช่ตาราง ผู้แยกวิเคราะห์ (parser) จึงไม่ดึงมาเป็นแถว — **นับด้วยมือเพิ่มอีก 5 รายการ**
จากส่วน B ในแถว "ช่วงเวลา/รายงานแรกสุด" ด้านล่าง (ระบุ tag ต่างกันตามที่มา).

| ตัวชี้วัด | ค่า | tag |
|---|---|---|
| แถวที่ระบบพาร์สได้ (ส่วน A, ตาราง; area="sammakorn" ระบุตรงจาก caller) | **22** จาก `social_listening_paste` + **1** จาก `social_listening_google` (แถว JS100 ที่พูดถึง "สัมมากร" ตรง ๆ) = **23** (`rows_total` ใน `method_evaluation`) | MEASURED (รันจริง) |
| แถวที่นับด้วยมือเพิ่ม (ส่วน B, บึง/ทะเลสาบ, ไม่ใช่รูปตาราง) | **5** | MEASURED (อ่านไฟล์ด้วยตา) |
| ช่วงเวลาที่ครอบคลุม (ส่วน A) | ตี 4 (04:00) ถึง 11:30 → **≈7.5 ชั่วโมง** | MEASURED (`earliest_report_utc`/`latest_report_utc` จากระบบ) |
| รายงานแรกสุด | ซอย 50 เข้าบ้าน **04:00** 26 ก.ย. | MEASURED |
| สัญญาณทางการแรกสุดที่เทียบได้ | `WL.HMK.01` (ค.หัวหมาก) เข้า **CRITICAL** และ `WL.SSB.07` (ค.แสนแสบ-สนข.บางกะปิ) เข้า **WATCH** พร้อมกันที่ **2026-09-25T13:05:00Z = 20:05 น. เวลาไทย 25 ก.ย.** | MEASURED (query ตรงจาก `data/observations.sqlite` ของ repo นี้เอง วันนี้ — ไม่ใช่จากความจำ) |
| ผลเทียบ | สถานีทางการเข้าโซน WATCH/CRITICAL **ก่อน**รายงานแรกในกลุ่ม (ซอย 50, บ้านจริง) ประมาณ **8 ชั่วโมง** | MEASURED (คำนวณจาก 2 บรรทัดข้างบน) |
| สัดส่วนที่มีซอย/จุดระบุ (`share_with_soi_point`) | **0.957** (22/23 -- หนึ่งแถวไม่มีเลขซอยให้ regex จับ) | MEASURED (ระบบ, `method_evaluation`) |
| สัดส่วนที่มีตัวเลขความลึก (`share_with_depth_number`) | **0.087** (2/23: ซอย 48 = 9.5 ซม., ซอย 48/3 = 30 ซม.) | MEASURED (ระบบ) |
| สัดส่วนจากสื่อ vs บุคคล (`share_from_media`/`share_from_individuals`) | **0.043 สื่อ / 0.957 บุคคล** -- ดูหมายเหตุ (ไม่ใช่ 0% ตามที่คาดจากกลุ่มปิด เพราะ metric นี้รวมข้าม 2 แหล่ง) | MEASURED (ระบบ) |
| ความขัดแย้งกับข้อมูลทางการ | ชุมชนรายงาน "บึงที่ 4 เครื่องสูบ 0/2" (นัยว่าเสีย) แต่ `bma_pumphistory` (ST.SPS.02, "สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่") แสดง status_th = **"ปกติ"** แม้ pumps_on=0/2 — แปลว่า BMA เองไม่ได้ถือว่า 0 เครื่องเปิดคือ "ขัดข้อง" เสมอไป (อาจไม่จำเป็นต้องเปิดตอนนั้น) — **ไม่ resolve ว่าใครถูก**, แสดงไว้เป็นตัวอย่างว่าวิธีนี้จับความขัดแย้งได้จริง | MEASURED (query ตรงจาก DB วันนี้) |
| ยืนยันตรงกัน | ST.SPS.01 ("สถานีสูบน้ำคลองบ้านม้า 2") status_th = **"ขัดข้อง"**, pumps_on=0/4 — ตรงกับที่ชุมชนรายงาน ("สถานีสูบคลองบ้านม้า 2 ขัดข้อง 0/4") | MEASURED |

**หมายเหตุ `share_from_media` ของสัมมากร (ตรวจสอบจริงจาก DB แล้ว ไม่ใช่การเดา)**:
`evaluate_metrics()` รวมแถวจาก**ทั้งสองแหล่ง** (`social_listening_paste` +
`social_listening_google`) ที่มี `area == "sammakorn"` ไม่ใช่แค่แหล่งกลุ่มปิด — แถว media 1 แถว
นั้นคือผลลัพธ์ Google จริงของ "Facebook JS100 -- สัมมากร รามคำแหง 112" (แหล่ง
`social_listening_google`, ไม่ใช่กลุ่ม Facebook ปิด) ที่ `_guess_area()` จับคำว่า "สัมมากร" ได้ถูก
ต้อง ⇒ **ระบบทำงานตามที่ออกแบบ** (สื่อรายงานถึงสัมมากรจริงจาก timeline ราม 53).

**Incident ที่พบระหว่างพัฒนา (แก้แล้ว ก่อน commit)**: เวอร์ชันแรกของ `parse_paste()` ใช้
`_guess_area()` เดาพื้นที่จากข้อความในแถวเหมือน `parse_google_snapshot()` — ทดสอบจริงพบว่าแถว
กลุ่มปิดสัมมากร "ซอย G14 / ถนนเมน ราม 110" ถูกเดาเป็น `"ram53"` แทน `"sammakorn"` เพียงเพราะ
ข้อความมีคำว่า "ราม 110" ทั้งที่มาจากกลุ่มสัมมากรเอง 100% — **ข้อจำกัดจริงของการเดาพื้นที่จาก
ข้อความอย่างเดียว เมื่อรู้แหล่งที่มาแน่นอนอยู่แล้ว**. แก้แล้ว: `parse_paste(text, pasted_at,
area=...)` รับ `area` ตรงจากผู้เรียก (ค่าเริ่มต้น `"sammakorn"`) แทนการเดา -- ตัวเลขในตารางข้างบน
เป็นค่าหลังแก้ (23 = 22 paste ที่ area ถูกต้องแล้ว + 1 google JS100). `parse_google_snapshot()`
ยังเดาต่อไปตามเดิม เพราะแหล่งนั้นเป็นผลค้นหาข้ามพื้นที่จริง ๆ ไม่รู้แหล่งที่มาแน่นอนล่วงหน้า.

### รามคำแหง 53 (`social_listening_google`)

| ตัวชี้วัด | ค่า | tag |
|---|---|---|
| แถวทั้งหมดที่ Google เห็น (ไม่แยกพื้นที่) | **14** (นับด้วยมือจากไฟล์) | MEASURED |
| แถวที่ระบบนับเป็น "ram53" ใน `method_evaluation` (`rows_total`) | **13** (แถว JS100 ถูกจัดเป็น "sammakorn" แทน เพราะพูดถึงสัมมากรตรง ๆ -- ดูตารางสัมมากรด้านบน) | MEASURED (ระบบ) |
| แถวที่ใช้ได้ (มีเวลา ± ประมาณได้) | 12/14 (2 แถวสุดท้ายไม่มีเวลาที่ชัด) | MEASURED (นับด้วยมือ) |
| ช่วงเวลาที่ครอบคลุม | 25 ก.ย. ~16:00 ถึง 26 ก.ย. ~12:50 ≈ **21 ชั่วโมง** | MEASURED |
| รายงานแรกสุด | 25 ก.ย. ~16:00 (Facebook เพจ, "น้ำท่วมขังบนถนน") | MEASURED (นับจากไฟล์เอง) |
| ค่าความลึกสูงสุดที่รายงาน | **70–80 ซม.** (หน้า ม.ราม, 00:45 น. 26 ก.ย.) | RELAYED (ตัวเลขจากโพสต์ ไม่ใช่ค่าที่วัดโดยเครื่องมือ) |
| สัดส่วนที่มีซอย/จุดระบุ (`share_with_soi_point`, ระบบ) | **0.154** (2/13 -- ระบบจับคำว่า "ซอย" ตรง ๆ เท่านั้น ไม่รวม "หน้า ม.ราม"/"ราม 59" ที่ไม่มีคำว่า "ซอย") | MEASURED (ระบบ) |
| สัดส่วนที่มีจุดเฉพาะ ตามเกณฑ์กว้างกว่า (มีคน)ด้วยมือ (หน้า ม.ราม, ราม 59, ปากซอย ราม 53) | 4/13 ≈ 31% | MEASURED (นับด้วยมือ, เกณฑ์กว้างกว่า `share_with_soi_point`) |
| สัดส่วนที่มีตัวเลขความลึก (`share_with_depth_number`, ระบบ) | **0.077** (1/13) | MEASURED (ระบบ) |
| สัดส่วนจากสื่อ vs บุคคล (`share_from_media`/`share_from_individuals`, ระบบ) | **0.154 สื่อ / 0.846 บุคคล** (2/13 สื่อ: อีจัน, Rodee -- JS100 ย้ายไปนับใน "sammakorn") | MEASURED (ระบบ) |
| median Google-index latency | ไฟล์เองระบุ "ช้า 1–3 ชม." ในหัวข้อ "ข้อจำกัด" — **ไม่มีค่าที่วัดได้จริง** (ไม่มี timestamp การ index จริงเทียบกับเวลาโพสต์จริง) | **OPEN** (relay จากคำอธิบายไฟล์เอง ไม่ใช่ตัวเลขที่ยืนยันแล้ว) |
| ผลเทียบกับทางการ | ไม่มีสถานีทางการที่รู้พิกัดแน่นอนสำหรับ "ราม 53" ในรายการ `SAMMAKORN_NODES` ของ `readout.py` ตอนนี้ — เทียบตรงไม่ได้ในรอบนี้ | **OPEN** |

### สิ่งที่วิธีนี้ **ให้ไม่ได้** (ต้องพูดตรงๆ ไม่ใช่ blanket gag)

- **พิกัด (lat/lon) ของแต่ละจุด** — มีแค่ชื่อซอย/สถานที่เป็นข้อความ ต้อง geocode ด้วยมือ/แยกต่างหาก
  ก่อนจะ join แบบ "ภายใน N km" ได้จริง (ตอนนี้ readout.py's agreement section ใช้เวลาที่ใกล้ที่สุด
  ไม่ใช่ระยะทาง สำหรับพื้นที่ที่ไม่มีพิกัด).
- **ความลึกที่สอบเทียบแล้ว (calibrated depth)** — ตัวเลข "ซม." ในโพสต์เป็นค่าที่ผู้โพสต์กะเอง ไม่ผ่าน
  เครื่องมือวัด ไม่เทียบกับระดับอ้างอิงเดียวกันทั้งพื้นที่ (person A's "ถึงต้นขา" ≠ person B's "30 ซม."
  ในหน่วยเดียวกันจริง).
- **กลุ่มปิด** — Google เห็นเฉพาะโพสต์สาธารณะ; กลุ่ม Facebook ปิดต้องมีคนใน "วาง" ให้เท่านั้น (มาจาก
  `social_listening_paste`, ไม่ใช่ระบบดึงเอง) — coverage ของทั้งสองแหล่งจึงไม่ใช่ภาพเต็มของพื้นที่.

---

## English summary

This is a data-collection layer, not a forecast or a score. `social_listening.py` extracts three
verifiable fields per row — place, water state (a fixed vocabulary, never sentiment), time — plus
`area` and `publisher_type` (media vs individual; no personal names are ever stored). Two registry
sources feed it: `social_listening_google` (a saved Google search snapshot filtered to the last
24h) and `social_listening_paste` (maintainer-pasted community-group text). Effectiveness numbers
above were counted directly from the two source files and, where possible, cross-checked live
against this repo's own `data/observations.sqlite` (e.g. official WATCH/CRITICAL station timestamps,
pump station status) — every number is tagged MEASURED, RELAYED, or OPEN, never stated as settled
fact from memory. What this method structurally cannot give: coordinates, calibrated depth, or
visibility into closed groups it wasn't handed text from.
