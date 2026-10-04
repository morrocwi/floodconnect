# ระบบข้อมูลน้ำท่วมสด สำหรับหมู่บ้านสัมมากร (Sammakorn live flood-context data system)

**อ่านก่อน**: เอกสารนี้อธิบาย "ระบบเก็บ+อ่านข้อมูล" ไม่ใช่ "ระบบพยากรณ์น้ำท่วม" — ไม่มีสูตร
หรือคะแนนความเสี่ยง (risk score) อยู่ในโค้ดชุดนี้เลย ทุกตัวเลขที่ readout.py แสดง คือค่าที่
relay/วัดมาตรง ๆ จากหน่วยงานต้นทาง พร้อม tag บอกชั้นความน่าเชื่อถือ (ดูหัวข้อ "Trust tier" ด้านล่าง).
เหตุผล: หน่วยงานไทยหลายหน่วยงานทำงานแข่งกันและข้อมูลไม่สอดคล้องกัน (project ruling) — งานของระบบนี้
คือ**แสดงความขัดแย้งนั้นให้เห็น** ไม่ใช่ตัดสินแทนว่าใครถูก.

## แผนภาพ pipeline

```
sources/registry.yaml  (นิยาม source ทุกตัว: agency, url, method, trust_tier, host_rule)
        |
        v
collect.py --all | --source ID       (1 request ต่อ URL ต่อ 1 run, ไม่มี retry loop)
        |  - reuse fetch/parse จาก live_water_level.py (thaiwater canal, PumpHistory, KlongMap)
        |  - parsers ใหม่ใน parsers.py (flood_road, flood_report HTML, DDS daily PDF, tide PDF)
        v
raw/live/<source_id>/<UTC timestamp>.<ext>   (raw snapshot, gitignored, ทำซ้ำได้ --
        note: this naming applies to sources collect.py itself fetches, e.g.
        raw/live/thaiwater_flood_road/, raw/live/dds_nowcast_gif/; the reused
        live_water_level.py fetchers still cache under THEIR OWN older dir names,
        e.g. raw/live/thaiwater_bma/, raw/live/pumphistory/ -- not <source_id>)
        |
        v
store.py  ->  data/observations.sqlite  (gitignored)
        observations  -- ข้อมูลเป็นแถว ๆ, append-only, unique index กันเขียนซ้ำ
        documents     -- ข้อความดิบที่ไม่ได้ถูกแปลงเป็น field (เช่น พยากรณ์อากาศแบบร้อยแก้ว)
        contradictions -- แถวขัดแย้งระหว่างแหล่ง (ไม่ resolve ให้)
        |
        v
readout.py --centre LAT LON [--radius-km 5] [--date YYYY-MM-DD]
        |
        v
output/sammakorn_readout_<UTC date>.md   +   .json
```

## Trust tier (ชั้นความน่าเชื่อถือ) -- คำศัพท์คงที่

| Tier | ความหมาย | ตัวอย่างใน registry นี้ |
|---|---|---|
| `official_telemetry` | หน่วยงานวัดเอง เป็นเซนเซอร์/เครื่องมือ ไม่ผ่านคนคอมไพล์ | thaiwater_canal_waterlevel, thaiwater_flood_road, thaiwater_waterlevel, hii_dam, hii_watergate, bma_pumphistory, bma_klongmap |
| `official_report` | หน่วยงานรวบรวม/ออกรายงานเอง (อาจรวม telemetry + คำบรรยาย/พยากรณ์) | dds_daily_pdf, dds_flood_report, dds_tide_pdf, dds_nowcast_gif, rid_res_table, egat_water_crisis |
| `official_shared_inference` | หน่วยงานอนุมานจากสัญญาณของบุคคลที่สาม (เช่น อ่านสีจราจรจาก Google Maps) แล้วแชร์ต่อ | governor_shared_flooded_roads |
| `third_party` | ไม่ใช่หน่วยงานรัฐ (แบบจำลอง/reanalysis เปิด ไม่มี key) | openmeteo_forecast, openmeteo_flood, openmeteo_ensemble, openmeteo_marine, openmeteo_multimodel, nasa_power |

2026-09-27 (founder ask "ต่อให้เสร็จเฉพาะของฟรี แน่นอน ก่อน"): 9 new registry-driven
`collect.py` collectors added on top of the above -- nationwide Thai government feeds
(`thaiwater_waterlevel`, `hii_dam`, `hii_watergate`, `rid_res_table`, `egat_water_crisis`)
and free global no-key forecast/reanalysis feeds (`openmeteo_flood` -- GloFAS river
discharge for the upstream Chao Phraya chain, `openmeteo_ensemble` -- multi-member rain,
`openmeteo_marine` -- Gulf of Thailand sea level, `nasa_power` -- daily bias-corrected
rain, `openmeteo_multimodel` -- the 6-model feed `site/build_data.py`'s drain-timeline
chart already reads from `raw/forecast/openmeteo_<model>.json`, now produced by a real
collector instead of a 2026-09-26 manual one-off). `rid_res_table` has no coordinate or
numeric reading on its page -- stored as `documents` rows (region + dam name), never a
fabricated observation. See `sources/registry.yaml` for full per-source detail.

Tier เป็น**การตัดสินใจเชิงวิศวกรรม (INSTINCT/Dr-tier)** ของโค้ดชุดนี้ ไม่ใช่ใบรับรองจากหน่วยงาน —
ดูรายละเอียด/เหตุผลของแต่ละ source ที่ `sources/registry.yaml`.

## กติกาความปลอดภัยของ host (Host-safety rule)

`weather.bangkok.go.th` และ `dds.bangkok.go.th` เป็น "BMA host" ตามกติกาความปลอดภัยของ workspace นี้:
**ไม่เกิน 1 request ต่อ URL ต่อการรัน 1 ครั้ง (run) งดใช้ retry loop และถ้าเจอ 403/reset ให้หยุดแตะ
host นั้นทันที (ทุก source ที่เหลือบน host เดียวกันในรอบนั้น ไม่ใช่แค่ URL เดิม)**. `collect.py`
ทำตามนี้ทุก source (ดู `sources/registry.yaml`'s `host_rule` ต่อ source) ผ่าน per-host circuit
breaker ใน `run()` (`collect._looks_like_host_block` + `tripped_hosts`) และไม่มี retry-loop
ที่ไหนในไฟล์นี้เลย. `bma_klongmap` (403 ยืนยันแล้ว 2026-09-26) ถูกตัดออกจาก `--all` โดยเฉพาะ
(`collect.DORMANT_NOT_IN_ALL`) จนกว่าคนจะสั่ง `--source bma_klongmap` เองเพื่อเช็คซ้ำ.
`api-v3.thaiwater.net` (HII/สสน.) ไม่ใช่ BMA host แต่ก็ถูกจำกัดไว้ที่ 1 GET ต่อ run เหมือนกัน
(นิสัยเดียวกันทั้งระบบ).

สำหรับ PDF สองไฟล์ (`dds_daily_pdf`, `dds_tide_pdf`): `collect.py` ทำ **GET เดียว ไม่มี HEAD ก่อน**
(เวอร์ชันก่อนหน้าทำ HEAD-then-conditional-GET ซึ่งกลายเป็น 2 requests ต่อ URL เดียวในบาง run --
ขัดกับกติกา "ไม่เกิน 1 request ต่อ URL ต่อ run" -- แก้เป็น GET เดียวเสมอแทน). `--from-file <path>`
ข้าม GET ไปเลย เอาไฟล์ที่มีอยู่แล้วมาแปลง -- ใช้เมื่อมีการรันแยกต่างหากดาวน์โหลดไฟล์เดียวกันไว้แล้ววันนั้น.

## วิธีเพิ่ม source ใหม่

1. เพิ่มรายการใน `sources/registry.yaml` (ทุก field ที่ `tests/test_registry.py` เช็ค: id,
   agency.th/en, url, method, cadence, format, auth, licence_status.text/unresolved, trust_tier
   (ต้องอยู่ใน 4 ค่าที่กำหนดไว้), host_rule.max_requests_per_run, last_status, variables).
2. ถ้ามี fetch/parse logic อยู่แล้วใน `live_water_level.py` (เช่น pattern ของ thaiwater/BMA)
   ให้ reuse ผ่าน import -- **ต้องไม่ copy โค้ดซ้ำ**.
3. ถ้าเป็น parser ใหม่จริง ๆ เขียนเป็น**pure function**ใน `parsers.py` (input เป็น bytes/str/dict,
   output เป็น list/dict, ไม่มี network call ในนั้น) แล้วเขียน unit test ด้วย fixture ที่ตัดทอนจาก
   ข้อมูลจริง (public fields เท่านั้น) ใน `tests/fixtures/`.
4. เขียนฟังก์ชัน `collect_<source_id>(conn, dry_run=False, ...)` ใน `collect.py`, ใช้
   `store.insert_observation` (สำหรับข้อมูลที่ parse เป็น field ได้) หรือ
   `store.insert_document` (สำหรับข้อความที่ยังไม่ parse) -- **ต้องไม่เขียน flood-risk score/formula
   ที่ไหนเลย** (ดูกฎ equation discipline ของ workspace นี้).
5. เพิ่มเข้า `COLLECTORS` dict ใน `collect.py`.
6. รัน `python3 -m pytest tests/ -q` ให้ผ่านทั้งหมดก่อน commit.

## การรันประจำวันเป็นอย่างไร (และสิ่งที่ยังไม่มี)

**ระบบนี้ยังไม่มี timer/cron ใด ๆ ที่รันเอง.** การรันทุกครั้งเป็น manual:

```bash
python3 collect.py --all          # เก็บข้อมูลรอบเดียว (1 request ต่อ URL)
python3 readout.py --centre 13.758235 100.676084
```

**GitHub Actions (`.github/workflows/floodconnect.yml`) ไม่ได้รัน `collect.py` เอง** --
workflow นี้ทำแค่ validate + test + build หน้าเว็บสาธารณะจาก **tracked inputs เท่านั้น**
(`site/inputs/**`, `sources/*.yaml`, และไฟล์อื่นที่ commit ไว้) เกิดขึ้น on demand เท่านั้น
เมื่อ push ไปยัง `main` หรือสั่งรันเอง (`workflow_dispatch`) ไม่มี schedule/cron ตามเวลา และไม่มี
private cron/systemd timer ของ repo นี้โดยเฉพาะ. runner สดใหม่ไม่มี `data/`/`raw/` (gitignored)
ดังนั้นหน้าเว็บที่ build ได้จะอยู่ในสถานะ no-current-data/staleness จนกว่าจะมีคน refresh ฝั่งผู้เรียก
(caller-side) เอง -- รันบนเครื่อง/network/key ของผู้ใช้เอง ไม่ใช่บน runner ของเรา. ส่วน
`site/dist/api/v1/**` **ไม่ถูก track ในคลังนี้เลย** (gitignored) -- เป็น local export ที่ต้องรัน
`site/build_data.py` แล้ว `tools/api/export_api.py` เองก่อนจึงจะมีไฟล์ (ruling 2026-10-04:
no-hosted-access; ก่อนหน้านี้เอกสารรุ่นนี้เคยเขียนว่าเป็น "tracked snapshot ที่ build นี้ upload
ติดไปกับหน้าเว็บ" -- ถ้อยคำนั้นเก่าแล้วและผิดตั้งแต่ snapshot ถูกถอดออกจาก main; ไม่มี snapshot
สำเร็จรูปในคลังนี้อีกต่อไป).

## เสียงจากอินเทอร์เน็ต (social listening)

ชั้นข้อมูลเพิ่มเติม (ไม่ใช่ telemetry/report ทางการ): `social_listening.py` (+ registry
sources `social_listening_google`, `social_listening_paste`) เก็บ place + water-state +
time จากโพสต์สาธารณะ/ข้อความที่แชร์ในกลุ่ม — **ไม่เก็บชื่อคน** และอ่านคู่กับสถานีทางการเสมอ
(ดูตาราง agreement ใน `readout.py`'s "เสียงจากอินเทอร์เน็ต" section). วิธีการ + effectiveness
record เต็ม ๆ (ตัวเลขที่วัดได้จริง, ข้อจำกัด) อยู่ที่ `docs/METHOD_social_listening.md`.

## PDF ของ DDS: หมายเหตุเรื่อง encoding

PDF bulletin รายวันของ DDS (`dds_daily_pdf`) ใช้ font ที่ฝัง custom encoding -- `pdftotext`
ดึงตัวอักษรบางตัว (สระ/วรรณยุกต์บางตัว เช่น ไม้โท ไม้เอก ทัณฑฆาต) ออกมาเป็น Unicode Private Use
Area (U+F700-U+F8FF) แทนที่จะเป็นรหัสไทยจริง -- ยืนยันแล้ว 2026-09-26 (เช่น "ป้องกัน" ถูกดึงออกมา
เป็น "ป" + U+F706 + "องกัน"). `parsers.py` **ไม่พยายามเดา/แก้ตัวอักษรเหล่านี้** (นั่นจะเป็นการ
fabricate ตัวอักษรที่ไม่รู้แน่ชัด) -- Section anchor ถูกออกแบบให้ตัดก่อนจุดที่มีปัญหา ส่วนข้อความที่
capture มา (ชื่อคลอง/ชื่อสถานี) จะมีตัวอักษร PUA เหล่านี้ติดมาตรง ๆ ตามที่สกัดได้จริง.

---

## English summary

This is a data COLLECTION + READOUT system, not a forecast system -- no flood-risk formula
or score exists anywhere in this code. `sources/registry.yaml` declares every source with a
`trust_tier` (official_telemetry / official_report / official_shared_inference /
third_party) and a `host_rule` (max 1 request per URL per run on BMA hosts, no retries).
`collect.py` fetches each source once per run (reusing `live_water_level.py`'s existing
thaiwater/BMA PumpHistory/KlongMap fetch+parse, and new parsers in `parsers.py` for
flood_road, the DDS flood-report HTML table, the DDS daily PDF, and the monthly tide-table
PDF), caches the raw snapshot under `raw/live/<source>/`, and writes normalised rows into
`data/observations.sqlite` (`observations` / `documents` / `contradictions` tables,
append-only). `readout.py --centre LAT LON` renders a Markdown+JSON snapshot with a MEASURED
/ OFFICIAL FORECAST / MISSING row for each of the four factors (rain, northern Chao Phraya
inflow, tide surge, drainage), a fixed list of Sammakorn's own nearby stations/pumps, and an
explicit, never-auto-resolved cross-source contradictions section. There is NO cron/timer
here -- GitHub Actions in `.github/workflows/floodconnect.yml` runs on demand only, triggered
by a push to `main` or a manual `workflow_dispatch`, with no fixed schedule, and it never
calls `collect.py` itself: it only validates, tests, and rebuilds the public page from the
repo's own committed snapshot. Running `collect.py` to fetch fresh upstream data is always
caller-side -- on the caller's own machine, network and keys.

## Thai flood warning actor typology (pointer)

Note (2026-10-02): `trust_tier` (how an item was produced) and
actor/product role (what the publisher is playing, what kind of claim the item is) are
two different questions. The canonical role graph is `OBSERVE -> INTERPRET_SECTOR ->
INTEGRATE -> PUBLIC_WARN -> LOCAL_WARN_AND_ACT` (not an exclusive chain of command --
several Thai agencies act in parallel across hazard domains). Machine-readable typology:
`site/inputs/governance/flood_warning_actor_typology.yaml`. Human-readable crosswalk:
`docs/THAI_FLOOD_WARNING_ACTOR_TYPOLOGY.md`. Contradictions must compare like-with-like
across these layers -- a severe-weather warning and a canal gauge reading can both be
correct at once because they describe different layers of the system.
