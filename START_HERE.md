# START HERE — เปิดมาแล้วเข้าใจใน 5 นาที

## (1) ปัญหาที่เราแก้

หมู่บ้านสัมมากรและซอยรามคำแหง 53 เสี่ยงน้ำท่วมทุกฤดูฝน แต่ข้อมูลที่ประชาชนเข้าถึงได้กระจัดกระจาย
อยู่คนละหน่วยงาน อัปเดตช้า ขัดแย้งกันเอง และไม่มีใครประกอบให้ดูภาพเดียวได้ทันเวลา FloodConnect
คือเว็บเพจสาธารณะที่ **อ่านค่า (readout)** จากแหล่งข้อมูลทางการหลายแหล่งมาวางไว้จุดเดียว พร้อม
ป้ายบอกความน่าเชื่อถือของแต่ละตัวเลข — ไม่ใช่การพยากรณ์และไม่ใช่การยืนยันความปลอดภัย

## (2) แนวทาง

- **Readout-not-truth**: ทุกตัวเลขคือ "สิ่งที่อ่านได้ ณ เวลาหนึ่ง จากแหล่งหนึ่ง" ไม่ใช่ความจริงสัมบูรณ์
  — ทุกบรรทัดต้องมี **source + time + tag** (`VERIFIED`/`MEASURED`/`RELAYED`/`INSTINCT`/`OPEN`)
- **สมการต้องผ่าน Toledo ก่อนใช้เสมอ** — ห้ามเขียนสูตรน้ำท่วม/คะแนนความเสี่ยงเองลอย ๆ ทุกสมการที่ใช้
  ในโค้ดต้องลงทะเบียนเป็น proposal (เช่น `PROP-FLOOD-03` = water balance, `PROP-FLOOD-04` = edge
  direction) และ **REFUSED เป็นสถานะที่ยอมรับได้** เมื่ออินพุตไม่ครบ (ไม่ fabricate ค่า)
- **เก็บทุกรอบ ไม่ลบ** — `data/observations.sqlite` เป็น append-only, `readout_log` บันทึกทุก run
  เพื่อดูย้อนหลังได้ (ไม่ใช่แค่ค่าปัจจุบัน)
- **Maker ≠ checker** — คนที่เขียน collector/parser ไม่ใช่คนเดียวกับที่อนุมัติปล่อยข้อมูลสู่สาธารณะ

## (3) ระบบทำงานอย่างไร

```
collect.py --all          # เก็บข้อมูลจากทุก source (1 request/URL/run, ไม่มี retry loop)
        ↓
data/observations.sqlite  # เก็บแบบ append-only (observations/documents/contradictions)
        ↓
site/build_data.py        # รันสมการ PROP-FLOOD-01/02 (ขึ้นทะเบียน Toledo main แล้ว) +
                           # PROP-FLOOD-03/04/05a/05b (proposal บน branch proposals/flood-*
                           # ของ toledo ที่ยังไม่ merge) → data.json
        ↓
site/build_page.py        # ประกอบหน้าเว็บจาก data.json (ไฟล์บนเครื่องผู้ใช้เอง)
        ↓
tools/api/export_api.py   # ส่งออก site/dist/api/v1/** จากไฟล์ build ข้างบน
```

**ไม่มีโฮสต์กลาง (project decision 2026-10-04):** GitHub Pages ถูก unpublish แล้วและต้อง
ไม่เปิดอีก — repo สาธารณะนี้ไม่ส่งข้อมูลน้ำท่วมที่คำนวณไว้แล้วให้ใครอ่านได้ — ไฟล์ `site/dist/**`
(รวม `site/dist/api/v1/**`) เป็น build artifact ที่ gitignore ไว้ ผู้ติดตั้งต้องรัน pipeline
ข้างบนบนเครื่อง/network ของตัวเองเสมอ จึงจะมีข้อมูลให้ตอบ

- **Collection cadence**: `collect.py --all` เป็นงานฝั่งผู้เรียก (caller-side) เสมอ — รันบน
  เครื่อง/network/key ของผู้ใช้เอง ไม่มีจังหวะเวลาตายตัว GitHub Actions
  (`.github/workflows/floodconnect.yml`) รันเมื่อ push ไปยัง `main` หรือสั่งรันเอง
  (`workflow_dispatch`) แต่ทำแค่ validate + test + build หน้าเว็บจากไฟล์ที่ commit ไว้แล้ว
  — **ไม่เคยรัน `collect.py`** บน runner ของเรา และ **ไม่มี** private cron/timer ของ repo นี้เอง
  (ดู `docs/DATA_SYSTEM.md`)
- **ดูข้อมูลย้อนหลัง**: `python3 readout_history.py --history --days 7 [--area sammakorn]
  [--kind burden]` — อ่าน `readout_log` แบบ replay ตรง ๆ ไม่คำนวณอะไรเพิ่ม ไม่ตัดสินว่ารอบไหนถูกกว่า

## (4) ถามอะไร → เปิดไฟล์ไหน

| คำถาม | เปิดที่ |
|---|---|
| ตอนนี้น้ำเป็นไง | `floodconnect answer --refresh` บนเครื่องตัวเอง (ไม่มีหน้าเว็บโฮสต์กลางแล้ว — local dashboard: ดู `LOCAL_DASHBOARD_LINK.md`, ไม่ port ไปสาธารณะ) หรือ `site/dist/data.json` ที่สร้างเองจาก `--refresh` |
| แนวโน้ม / ประตูน้ำใครรับภาระ | `readout_history.py --history` |
| ความสามารถระบายน้ำของ กทม. | `docs/CAPACITY.md` + `capacity_records` ใน `site/dist/data.json` |
| ใครมีอำนาจ / ต้องถามใคร | `docs/knowledge/POWER_RESOURCE_MAP.md` |
| ปัญหาโครงสร้างจริงของระบบจัดการน้ำไทย | `docs/knowledge/THAI_WATER_GOVERNANCE_MAP.md` หมวด (0) |
| ข้อมูลซ้ำซ้อน/ช่องว่างระหว่างหน่วยงาน | `OVERLAP_REGISTER.md` (กำลังสร้าง) + `WATER_SYSTEM_DAG.md` (กำลังสร้าง) |
| หน่วยงานไหนทำอะไร มีฟีดอะไรบ้าง | `docs/knowledge/agencies/INDEX.md` (กำลังสร้าง) |
| คำถามที่ยังตอบไม่ได้ตอนนี้ | `docs/knowledge/WATER_MANAGER_QUESTION_BANK.md` |
| บทเรียน/สัญญาณนำจากเหตุการณ์จริง | `docs/LESSONS_nodes_2026-09-27.md` (เอกสารภายใน ไม่ได้รวมอยู่ใน public tree นี้) |
| สถาปัตยกรรมระบบเทียบกับศาสตร์สากล | `docs/ARCHITECTURE_world_frameworks.md` |
| งานต่อ (handoff) | `docs/knowledge/HANDOFF_ecosystem_2026-09-27.md` |

## (5) สิ่งที่ทำได้ทันทีถ้าคุณเป็น...

**ชาวบ้าน**
- ดูหน้าเว็บสาธารณะก่อนตัดสินใจอพยพ/ยกของ แต่ **อย่าใช้แทนช่องทางทางการ** (โทร 1669/1555)
- รายงานสภาพน้ำจริงหน้าบ้านผ่านช่องทางที่ทีมประกาศ (ไม่ต้องระบุชื่อ)
- อ่านคำเตือนใน README.md ก่อนแชร์ตัวเลขต่อ — ทุกค่าเป็น readout ไม่ใช่การยืนยัน

**กรรมการหมู่บ้าน**
- เก็บระดับไม้วัดน้ำที่บึง/ท่อลอดถนนเป็นประจำ (ดู `docs/ARCHITECTURE_world_frameworks.md` §5
  ข้อ 1-3) — ข้อมูลนี้มีค่ามากกว่าการเพิ่มแหล่งทางการ
- ประสานขอสถานะประตูที่ยังไม่เผยแพร่จากสำนักการระบายน้ำอย่างเป็นทางการ
- ใช้ `docs/CAPACITY.md` เมื่อคุยกับเจ้าหน้าที่เพื่ออ้างตัวเลขที่ VERIFIED แล้ว ไม่ใช่ข่าวลือ

**เจ้าหน้าที่เขต**
- ดู `docs/knowledge/POWER_RESOURCE_MAP.md` เพื่อยืนยัน/แก้ไขผังอำนาจที่ยังเป็น RELAYED-GENERAL
- ช่วยยืนยันตัวเลขที่ OPEN ใน `docs/CAPACITY.md` (เช่น ความจุปั๊ม ST.SPS, อุโมงค์พระราม 9-รามคำแหง)
- พิจารณาเปิดเผยสถานะประตูมีนบุรี/ประเวศ-ลาดกระบัง ที่ปัจจุบันต้องอนุมานเอง

**นักวิจัย**
- อ่าน `docs/ARCHITECTURE_world_frameworks.md` ก่อนเสนอกรอบ/ตัวชี้วัดใหม่ — เพื่อไม่ให้ซ้ำกับที่มีแล้ว
- ทุกสมการใหม่ต้องผ่าน Toledo-first ตามกฎ §(2) ก่อนนำไปใช้ในโค้ด
- ทบทวน `docs/knowledge/README.md` เพื่อดูว่าเอกสารระดับไหนที่ "ยังไม่มีเอกสาร" และต้องการเพิ่ม

**AI agent ที่มาต่องาน**
- อ่านไฟล์นี้ + `docs/knowledge/HANDOFF_ecosystem_2026-09-27.md` ก่อนแก้โค้ดใด ๆ
- ห้ามเขียนสมการ/คะแนนความเสี่ยงใหม่โดยไม่ผ่าน Toledo (ดู `docs/CAPACITY.md` §7 เป็นตัวอย่างของ
  REFUSED state ที่ถูกต้อง)
- รัน `python3 -m pytest tests/ -q` ให้ผ่านก่อน commit ทุกครั้ง
- ใช้ tag `VERIFIED`/`MEASURED`/`RELAYED`/`INSTINCT`/`OPEN` ทุกครั้งที่เพิ่มเอกสารใหม่

## (6) กฎที่ห้ามละเมิด

- **Wording law**: ห้ามเขียนคำที่สื่อว่าเป็นการพยากรณ์หรือยืนยันความปลอดภัยบนหน้าเว็บสาธารณะ — ทุก
  ตัวเลขต้องมี tag และคำเตือนตามที่ระบุใน README.md
- **ห้ามระบุชื่อบุคคล** ในเอกสาร/ข้อมูลใด ๆ ของโปรเจกต์นี้ (รวมถึงรายงานชาวบ้าน — เก็บแค่ soi/สภาพ/เวลา)
- **ห้ามใส่ชื่อ AI/vendor ใด ๆ** ในผลลัพธ์ที่เผยแพร่ (commit trailer, README, หน้าเว็บ)
- **ห้ามลบ/ตัดข้อมูลเก่าออกจาก `readout_log`** — เก็บทุกรอบเสมอ แม้จะผิดพลาด/REFUSED
- **ห้ามใช้สมการที่ไม่ได้ลงทะเบียนใน Toledo** — ไม่ว่าจะดูเรียบง่ายแค่ไหน

---

## English summary

FloodConnect is a public readout page for flood risk around Sammakorn village and Soi
Ramkhamhaeng 53 in Bangkok. It is **not a forecast system** — every number is a timestamped,
source-tagged reading (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN), pulled from official
agencies (BMA drainage, HII/thaiwater.net, Royal Thai Navy tide tables) plus community
reports, refreshed on demand (push to `main` or a manual workflow run) via GitHub
Actions, with no fixed schedule and no private cron. Any equation
used in the pipeline must be registered through the Toledo reuse pipeline first
(`PROP-FLOOD-01` trend and `PROP-FLOOD-02` time-to-threshold are registered on Toledo
`main`, though `PROP-FLOOD-02` is referenced in planning docs but not yet implemented
anywhere in this repo; `PROP-FLOOD-03` water balance, `PROP-FLOOD-04` edge direction,
`PROP-FLOOD-05a/05b` burden ledger are still proposals on an unmerged Toledo
`proposals/flood-*` branch, not yet registered on `main`) —
REFUSED is a valid, honest
output when required inputs are missing, never a fabricated number. See
`docs/ARCHITECTURE_world_frameworks.md` for how this maps onto SPRC, the EU Floods
Directive-style map stack, WMO/UNDRR early-warning, and Dutch multi-layer safety. See
`docs/knowledge/HANDOFF_ecosystem_2026-09-27.md` for what an incoming agent should do next.
