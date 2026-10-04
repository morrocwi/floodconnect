# FloodConnect

**Which AI are you? — see `docs/AI_TIERS.md` for the full version.**
```
T0 search snippet, no browsing                 -> you can't act here; tell the user to open an AI that can browse or install software.
T1 online chat with browsing, no shell          -> explain only, point to official numbers, never invent a reading.
T2 desktop app with the FloodConnect MCP tool   -> call floodconnect_answer, relay its real answer and tags.
T3 coding/terminal agent with a shell           -> install, run `floodconnect answer`, read the real output.
T4 co-work/computer-use agent                   -> T3's abilities, plus local-only reminders/checklists.
T5 script/API integrator                       -> call the CLI/MCP from code; read system_capabilities.json.
```
**คุณเป็นเอไอแบบไหน? — ดูฉบับเต็มที่ `docs/AI_TIERS.md`**
```
T0 สรุปผลค้นหา เข้าเว็บไม่ได้        -> ทำอะไรที่นี่ไม่ได้ บอกผู้ใช้ให้เปิดเอไอที่เข้าเว็บหรือติดตั้งโปรแกรมได้
T1 แชทออนไลน์เข้าเว็บได้ ไม่มี shell -> อธิบายอย่างเดียว ชี้เบอร์ทางการ ห้ามเดาค่าน้ำเอง
T2 แอปเดสก์ท็อปที่ต่อ MCP ของเรา     -> เรียก floodconnect_answer แล้วส่งค่าจริงพร้อมแท็ก
T3 เอเจนต์โค้ด/เทอร์มินัลที่มี shell -> ติดตั้ง รัน `floodconnect answer` อ่านผลจริง
T4 เอเจนต์ co-work/computer-use      -> ทำได้เท่า T3 บวกตั้งเตือน/เช็กลิสต์ในเครื่องผู้ใช้เอง
T5 สคริปต์/นักพัฒนาที่เรียกผ่านโค้ด  -> เรียก CLI/MCP จากโค้ด อ่าน system_capabilities.json
```

**A One-Decision Network for flood water: scattered Thai open data, designed around our
own Water-Debt decision model (v0.2+; v0.1.x answers from fixed, tested station-level
rules), reduced to one typed, honest decision for your home AI — "at this point, right
now, what should I do next." You install it and compute on your own machine; nothing
here is hosted, and nothing runs on a schedule. Every field is tagged by how sure we
are — a readout, never a flood-depth prediction, never a safety certification.**

**เครือข่ายการตัดสินใจหนึ่งเดียว (One-Decision Network) สำหรับสถานการณ์น้ำ: รวม open data
ของรัฐไทยที่กระจัดกระจาย ออกแบบรอบโมเดลหนี้น้ำ (Water-Debt) ของเราเอง (v0.2+; v0.1.x ตอบด้วย
กฎระดับสถานีที่ตายตัวและผ่านการทดสอบแล้ว) แล้วลดรูปเหลือคำตอบเดียวที่ซื่อตรงให้ AI ของคุณ —
"ที่จุดนี้ ตอนนี้ ควรทำอะไรต่อ" ติดตั้งแล้วคำนวณบนเครื่องของคุณเอง ไม่มีการโฮสต์กลาง ไม่มีจังหวะ
อัปเดตตายตัว ทุกค่าติดป้ายความน่าเชื่อถือของตัวเอง เป็นการอ่านค่า ไม่ใช่การพยากรณ์ความลึกน้ำท่วม
และไม่ใช่การยืนยันความปลอดภัย**

**Target: all of Thailand — shipped in v0.1.2.** Any `lat,lon` in Thailand now gets a
real `current_local_state` reading at COARSE (station/basin) resolution, from the
nationwide `thaiwater_waterlevel` telemetry feed — never household-level outside the
two named Bangkok sites. Two Bangkok sites (Sammakorn village, Soi Ramkhamhaeng 53)
keep their existing household/node-level detail, unchanged. See `docs/INDICATORS.md`
§11 for exactly how station vs. basin resolution works and `docs/NEAREST_STATION_
RECIPE.md` for the by-hand method. Never call this product Bangkok-only.
**เป้าหมาย: ทั่วประเทศไทย — เปิดใช้แล้วใน v0.1.2** ทุกพิกัดในประเทศไทยตอบได้จริงที่ความละเอียด
หยาบ (ระดับสถานี/ลุ่มน้ำ) จากฐานข้อมูลสถานีวัดระดับน้ำทั่วประเทศ — ไม่ใช่ระดับบ้านนอกสองพื้นที่
ในกรุงเทพฯ ที่ยังคงรายละเอียดระดับบ้าน/โหนดเดิม

**The flood indicators — see `docs/INDICATORS.md` for the full dictionary, every name,
colour, source, threshold and worked example.** The closed set: `current_local_state`,
`forward_hazard`, `rise_rate_dk`, `time_to_threshold_tk`, `rain_24h_mm`,
`rain_7day_per_model_mm`, `distance_to_bank_m`, `bank_fill_percent`, `one_decision` (+
`confidence`), `water_debt` (planned v0.2+). RED = agency critical/overflow, YELLOW =
WATCH/warning or rising toward a threshold, GREEN = normal **with a fresh basis**,
UNKNOWN = no fresh basis — **UNKNOWN is never SAFE.**

**ตัวชี้วัดน้ำท่วม — อ่านรายละเอียดเต็มที่ `docs/INDICATORS.md`** ชุดตัวชี้วัดปิดตายตัว:
`current_local_state`, `forward_hazard`, `rise_rate_dk`, `time_to_threshold_tk`,
`rain_24h_mm`, `rain_7day_per_model_mm`, `distance_to_bank_m`, `bank_fill_percent`,
`one_decision` (+ `confidence`), `water_debt` (วางแผน v0.2+) สีแดง=หน่วยงานประกาศวิกฤต/ล้นตลิ่ง
สีเหลือง=เฝ้าระวังหรือกำลังขึ้นเข้าใกล้ค่าที่ตั้งไว้ สีเขียว=ปกติ **ต้องมีค่าสดรองรับ**
ไม่ทราบ=ไม่มีค่าสดพอฟันธง **ไม่ทราบ ไม่เท่ากับ ปลอดภัย**

**FloodConnect is the method, not a data service (founder ruling 2026-10-04): we give
you WHICH sources to read, how to pick the nearest station, the equations/thresholds,
and the honesty rules — never a hosted place/POI lookup.** Geocoding a place name and
finding nearby points of interest are **your own AI's job**; FloodConnect never
geocodes and holds no place/POI database. Have lat,lon already? The CLI/MCP tool is an
**optional** deterministic helper that applies this same method for you. No tool
access at all (a browsing-only chat AI)? Follow
**[docs/NEAREST_STATION_RECIPE.md](docs/NEAREST_STATION_RECIPE.md)** step by step —
same official sources, same rules, done by hand.

**FloodConnect คือ "วิธีคิด" ไม่ใช่บริการข้อมูล (founder ruling 2026-10-04):** เราบอกว่าควร
อ่านแหล่งไหน เลือกสถานีใกล้ที่สุดอย่างไร สมการ/เกณฑ์อะไร และกฎความซื่อตรง — ไม่ใช่ฐานข้อมูล
สถานที่ที่โฮสต์ไว้ การหาพิกัดจากชื่อสถานที่และสถานที่ใกล้เคียงเป็นหน้าที่ของ **เอไอของคุณเอง**
FloodConnect ไม่หาพิกัดเองและไม่มีฐานข้อมูลสถานที่ มีพิกัดแล้ว? ใช้ CLI/MCP เป็นตัวช่วย
**ทางเลือก** ที่ใช้วิธีคิดเดียวกันนี้ให้อัตโนมัติ ไม่มีเครื่องมือเลย (แชทที่เข้าเว็บได้เท่านั้น)? ทำตาม
**[docs/NEAREST_STATION_RECIPE.md](docs/NEAREST_STATION_RECIPE.md)** ทีละขั้น

Start here → **[START_HERE.md](START_HERE.md)** (human-facing, 5-minute read, Thai) ·
**[AGENTS.md](AGENTS.md)** (AI-facing rules, bilingual) · **[AI.md](AI.md)** (the single
AI compute entrypoint) · **[docs/NEAREST_STATION_RECIPE.md](docs/NEAREST_STATION_RECIPE.md)**
(the method, for an AI with no tool access).

**AI readers: read [llms.txt](llms.txt) first, especially if you cannot run code** —
it has a "If you cannot run code" section with the exact thing to tell your user, and
a repository map so you don't judge this project from one file. **No reading anywhere
in this repository is current** — see §3a below.

**AI ที่อ่าน: อ่าน [llms.txt](llms.txt) ก่อน** โดยเฉพาะถ้ารันโค้ดไม่ได้ — มีหัวข้อ
"ถ้ารันโค้ดไม่ได้" บอกตรงว่าควรพูดอะไรกับผู้ใช้ **ไม่มีค่าใดในเรโปนี้ที่เป็นข้อมูลปัจจุบัน** —
ดู §3a ด้านล่าง

MVP v0.1.0 — Bangkok, Sammakorn village + Soi Ramkhamhaeng 53 only (see §3 "Out of
scope"). This is a volunteer project. It has no instruments of its own; every number is a
timestamped, source-tagged reading from an official agency or a community report.

**Emergency numbers — always call these for anything real. This page is a readout, not
an emergency channel. เบอร์ฉุกเฉิน — โทรก่อนเสมอเมื่อสถานการณ์จริง หน้านี้เป็นการอ่านค่า
ไม่ใช่ช่องทางแจ้งเหตุ:**

| Number / channel | Use for |
|---|---|
| **1669** | Medical emergency / เหตุฉุกเฉินทางการแพทย์ |
| **1784** | DDPM (disaster) / กรมป้องกันและบรรเทาสาธารณภัย |
| **1460** | Royal Irrigation Department / กรมชลประทาน |
| **1555** | BMA flood hotline / สายด่วนน้ำท่วม กทม. |
| **1130** | MEA electrical hazard / ไฟฟ้าขัดข้อง-อันตรายจากไฟฟ้าในน้ำ |
| **Traffy Fondue** | Official BMA street-flooding report channel |

---

## 0. How your home AI uses it

The north star is the **home AI** — your own assistant (Claude, ChatGPT, a local
model, whatever you already use) — reading the situation in one cheap call and
telling you directly, not a dashboard you have to check yourself.

1. Your AI (or you, via the CLI) calls `floodconnect answer --at <area|lat,lon>
   --json` or the MCP tool `floodconnect_answer`.
2. FloodConnect refreshes from the wired government/CCTV/model sources on *your*
   machine and network (never ours), classifies the current station readings with
   fixed, tested rules, and returns one typed, source-tagged answer. **The headline
   colour verdict is `next_action.dual_state`** —
   `next_action.dual_state.current_local_state` (RED/YELLOW/GREEN/UNKNOWN) and
   `next_action.dual_state.forward_hazard` (ACTIVE/NONE/UNKNOWN); read this field
   FIRST (it is printed as its own labelled line, "สถานะคู่ [dual-state]:", in the
   default human-text CLI output too), not `state`/`hazard` alone (those are the raw
   evidence `dual_state` was classified from — `state.tag`/`hazard.tag` are epistemic
   confidence tags on that evidence, never a second, competing colour verdict). The
   rest of the payload: `state` (current station-level reading), `hazard` (forecast
   rain, per model, never averaged), `accountability` (who is responsible for this
   point), `next_action` (what to do, plus the `dual_state` field above), each
   carrying an epistemic tag (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN).
3. Your AI reads that typed answer and tells you, in your own language, in one
   sentence first — then the details if you ask. FloodConnect's job stops at the
   typed decision; your AI does the natural-language translation.
4. **UNKNOWN is never SAFE.** If FloodConnect cannot get a fresh reading, it says so
   explicitly — it never infers calm from missing data.

ภาษาไทย: เป้าหมายคือ **AI ในบ้านคุณ** อ่านสถานการณ์ในการเรียกเดียว ราคาถูก แล้วบอกคุณตรงๆ
ไม่ใช่แดชบอร์ดที่คุณต้องเปิดดูเอง — AI ของคุณเรียก `floodconnect answer` หรือ MCP tool →
FloodConnect รีเฟรชข้อมูลจากแหล่งที่เชื่อมไว้บนเครื่อง/เน็ตของคุณเอง จัดประเภทค่าที่อ่านได้จาก
สถานีด้วยกฎที่ตายตัวและผ่านการทดสอบแล้ว แล้วตอบกลับเป็นคำตอบเดียวที่พิมพ์ชนิดและติดป้ายแหล่งที่มา
ชัดเจน → AI ของคุณแปลเป็นภาษา
ธรรมชาติให้คุณฟัง ไม่มีข้อมูล = ไม่เคยแปลว่าปลอดภัย

## 0a. How FloodConnect differs

| | Government data portals (e.g. ThaiWater, BMA DDS) | Dashboard apps (e.g. a Thai flood/weather dashboard) | Global forecast models (GFS/ECMWF, relayed raw) | Crowd reports (e.g. Traffy Fondue) | Official warnings (ปภ./BMA) | A generic chat AI asked "is it flooding" | **FloodConnect** |
|---|---|---|---|---|---|---|---|
| Combines multiple agencies into one reading | Varies (e.g. ThaiWater also carries the BMA canal set) | Sometimes | No (weather only) | No | No | No (no live access) | **Yes, with a source tag per number** |
| Reduces to one typed, actionable decision | No (raw numbers) | Partial (a map/colour, not a decision object) | No (raw forecast) | No | Partial (a declaration, not a per-point reading) | No (prose, unsourced) | **Partial today (`dual_state` + `next_action`); full one-decision envelope planned v0.2.0 (ARCHITECTURE.md §5)** |
| Runs on your own machine, no hosted data | No (hosted) | No (hosted) | No (hosted) | No (hosted) | No (hosted) | N/A | **Yes, always** |
| States UNKNOWN instead of guessing | Varies by agency | Varies | N/A (forecast always returns a number) | N/A | N/A | No (can fabricate an answer) | **Yes, explicitly, every field** |
| Free/open, installable, no vendor lock-in | Varies | Varies | Varies | Yes | Yes | Varies | **Yes** |
| AI-readable by design (MCP + typed JSON + llms.txt) | No | No | Partial (raw API) | No | No | N/A | **Yes** |
| Own decision model as the centre (Water-Debt), not a data mirror | N/A | N/A | N/A | N/A | N/A | N/A | **Planned (v0.2+) — see ARCHITECTURE.md §9; v0.1.x classifies with fixed station-level rules, not the water-debt value yet** |
| Never claims flood-depth prediction or safety | Mostly, varies by agency | Varies | N/A | Varies | Yes (official) | Often overclaims | **Yes, by design, enforced in tests** |

**What we are not, honestly:** not an official warning system (always defer to ปภ./
BMA/Traffy for anything real); not a flood-depth or water-level forecaster (F4 only
forecasts *rain*, per external model, relayed, never averaged, never turned into a
depth number — **"never averaged" also means never a combined min–max "range" across
models either; relay each model's own `tomorrow_mm`/`7day_total_mm` by name, e.g. "JMA
23.9 mm, CMA 2.4 mm, ECMWF 0.0 mm" — do not invent a single "X–Y mm" figure spanning
them, that figure belongs to no model and is not in the output**); not a hosted
service (install and compute yourself); not nationwide at household detail (coarse
station/basin resolution nationwide since v0.1.2; household/node detail stays two
Bangkok sites only — see the target line above); not yet running the full
Water-Debt/Jev/DSVA decision model described in
`ARCHITECTURE.md` (that is a v0.2+ design target — see §9's implemented-vs-planned
table); peers above are named only where independently verified, in neutral terms,
never as a negative claim about a named competitor.

## 1. What FloodConnect is

Flood data in Thailand is not scarce — it is scattered across agencies (BMA, the Royal
Irrigation Department, HII/สสน., the Royal Thai Navy Hydrographic Department, GISTDA,
the Thai Meteorological Department) with no single place that assembles it **with a
trust label on every number**. FloodConnect is that one place for its two pilot areas:
a typed knowledge graph (water flow, authority/ownership, resources, a 6-tier
community self-help path) plus a small AI-readable compute layer on top of it.

น้ำท่วมในไทยไม่ได้ขาดข้อมูล — ขาดที่เดียวที่รวมข้อมูลจากหลายหน่วยงานพร้อมป้ายความน่าเชื่อถือ
ของแต่ละค่า FloodConnect คือกราฟความรู้เดียวที่เชื่อมชั้นน้ำ/อำนาจ/ทรัพยากร/คน เข้าด้วยกัน
สำหรับสองพื้นที่นำร่อง พร้อมชั้นคำนวณเล็ก ๆ ที่ AI อ่านต่อได้ทันที

**This is a readout, not a flood-depth forecast, not a safety certification.** Every
number is what was read from a named source at a named time (one exception: F4 rain
forecast, which relays an external model's own rain forecast, per model, never
averaged) — never a flood-depth prediction, never a statement that it is safe to stay
or leave.

## 2. Features (MVP v0.1.0)

Each feature below is runnable today in this repo. Commands shown were run against this
tree; your own output will differ because the underlying data changes every refresh.

### F1 — Install from a fresh clone

```bash
git clone <this-repo-url> floodconnect && cd floodconnect
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cd /anywhere/else
floodconnect answer --at sammakorn --offline --json   # the console script works outside the repo dir
```

ติดตั้งจาก `git clone` สด ๆ แล้ว `pip install -e .` คำสั่ง `floodconnect` ใช้ได้จากไดเรกทอรีใดก็ได้
ไม่ต้องอยู่ในโฟลเดอร์ repo

### F2 — `floodconnect answer --at <area|lat,lon>`

```bash
floodconnect answer --at sammakorn
```

Prints four blocks every time: current local state, forward hazard, who is
accountable, and 1–3 next actions (each with its own epistemic tag). `--at` accepts a
registered area id (`sammakorn`, `ram53`) or a raw `lat,lon`. The combined token cost of
`AI.md` + `skills/floodconnect/SKILL.md` + one `answer` call is kept under
**≤ 10,000 cl100k tokens (enforced by `tests/test_token_budget.py` at 9,500)** for the
real default path — `refresh=True`, the real MCP-serialised `floodconnect_answer`
response, both MVP areas (`tests/test_token_budget.py::
test_mcp_serialised_default_refresh_answer_stays_under_tightened_budget`) — so an AI
session can load the whole contract and still ask its question cheaply.

พิมพ์ 4 บล็อกเสมอ: สถานะปัจจุบัน / แนวโน้มอันตราย / ผู้รับผิดชอบ / ขั้นต่อไป 1-3 ข้อ แต่ละบล็อก
ติดป้าย epistemic ของตัวเอง

### F3 — Fresh data by default

```bash
floodconnect answer --at sammakorn            # refreshes from the network before answering (default)
floodconnect answer --at sammakorn --offline  # opt out: answer from the local DB only, no network
```

Refresh is the **default**, not an opt-in: one GET request per relevant source, on
*your own* machine/network, before the answer is computed — no retry loop. `--offline`
is the explicit opt-out for no-network or no-upstream-hit runs. No stale reading is
ever allowed to decide a colour or the forward hazard — a reading older than its
source's own freshness cutoff is shown (tagged, with its age) but excluded from the
decision, never silently used as if current.

รีเฟรชข้อมูลสดเป็นค่าเริ่มต้น (ไม่ใช่ตัวเลือก) — ยิง 1 request ต่อแหล่งที่เกี่ยวข้อง บนเครือข่าย
ของคุณเอง ก่อนตอบทุกครั้ง ไม่มี retry loop; `--offline` คือทางเลือกปิดเท่านั้น ค่าที่เก่ากว่าเกณฑ์
ความสดของแหล่งนั้นจะไม่ถูกใช้ตัดสินสี/แนวโน้มอันตรายเด็ดขาด

### F4 — `floodconnect forecast --at <area|lat,lon>`

```bash
floodconnect forecast --at sammakorn
```

Reports rain **per forecast model** (Open-Meteo/ECMWF/GFS and siblings) — never
averaged into one number. Each model's row carries an `issued_at` timestamp, but
note: that is this clone's **fetch time**
(`MAX(fetched_at_utc)`), not the upstream model's own run/issue time — Open-Meteo's
per-model run time is OPEN, not read anywhere in this codebase today. A stale cached
row is still correctly excluded from the decision (the freshness gate compares against
this same fetch time, so a 12h-old cache row is correctly marked stale) — only the
LABEL "forecast issue time" overstated what the timestamp actually measures; read it
as "when this clone last fetched this model's row", never "when the model issued it".

รายงานฝนแยกตามแต่ละโมเดลพยากรณ์ (ไม่เฉลี่ยรวมเป็นเลขเดียว) พร้อมเวลาที่ "ดึงข้อมูลมาเก็บ" ล่าสุด
(ไม่ใช่เวลาที่โมเดลพยากรณ์ออกผลจริง — OPEN, ยังไม่มีในโค้ดนี้)

### F5 — Honesty by construction

`UNKNOWN` is a real, distinct state — never collapsed into "normal" or "safe". Example,
an actual run with no live network reachable from this install (`--offline`):

```json
"state": {"tag": "OPEN", "water_balance_status": "REFUSED", "tide_tag": "OPEN"},
"accountability": {"tag": "OPEN", "refused": "no knowledge-graph build found -- run `python3 -m tools.kg.build_kg` first"}
```

Every value carries a `source` + an age; the system never issues an evacuation order
(§5 "No evacuation orders" applies everywhere); the public-facing wording law bans
ไม่ต้อง / ห้าม / ไม่ควร / ผ่อนคลอง-style phrasing that would read as a safety certification
this project does not make. It never says `SAFE`.

`UNKNOWN` ไม่เท่ากับปกติ/ปลอดภัยเด็ดขาด ทุกค่าติด source + อายุของข้อมูล ระบบไม่ออกคำสั่งอพยพ
และห้ามใช้คำที่สื่อว่า "ปลอดภัยแล้ว" บนหน้าเว็บสาธารณะ ไม่เคยพิมพ์คำว่า `SAFE`

### F6 — Use it from your own AI

```bash
pip install -e '.[mcp]'   # pulls in the mcp>=1.2,<2 SDK; plain `pip install -e .` does NOT
```

The MCP server (`tools/mcp/floodconnect_mcp.py`) runs on your own machine; its
`floodconnect_answer` tool returns exactly the same payload as the `floodconnect
answer --json` CLI call — no second code path, no divergence to reconcile. **`AI.md`
is the single entry point** for any AI session working with this repo — read it before
calling any tool directly. See §6 below for the MCP config and test prompts.

เซิร์ฟเวอร์ MCP รันบนเครื่องคุณเอง ผลลัพธ์จาก `floodconnect_answer` เหมือนกับคำสั่ง CLI เป๊ะ
`AI.md` คือจุดเข้าเดียวสำหรับ AI ทุกตัวที่จะทำงานกับ repo นี้

### F7 — Publish-safe

No AI/vendor name, no local filesystem path, and no personal name is checked into any
tracked file (community reports carry soi + condition + time only). Fixtures used by
the test suite are small, synthetic or clearly-marked samples — never a dump of raw
production data. A leak scan runs before anything is pushed public (see
the maker-≠-checker rule above and an independent leak scan).

ไม่มีชื่อ AI/ผลิตภัณฑ์ ไม่มี path ของเครื่องใดเครื่องหนึ่ง ไม่มีชื่อบุคคลใน tracked file ใด ๆ
มีการ leak scan ก่อน publish สู่สาธารณะทุกครั้ง

### F8 — CCTV cameras (implemented)

**Status: live.** `floodconnect answer`/`floodconnect_answer` return a `cctv` block
(`kind: "VISUAL-CHECK"`, `radius_km`, `cameras[]`) whenever the `hii_analyst_cctv`
catalog (HII/สสน. via thaiwater.net, `sources/registry.yaml`) has at least one
parseable camera row — each `cameras[]` entry carries `name`/`distance_km`/`url`/
`within_radius`, always the ≤3 NEAREST cameras to the requested point even when none
are inside `radius_km` (3 km by default) — a far camera is still shown, flagged
`within_radius: false`, rather than silently hidden. In the real catalog's current
coverage, the nearest cameras to Sammakorn/Ram53 are 12–20 km away and 2 of the 3 have
no public stream URL (`url: null`, a real limit of the upstream catalog itself, not a
parsing bug) — shown as `ไม่มีลิงก์` ("no link") in the CLI text printer rather than
omitted. A camera is always informational/`VISUAL-CHECK` only, never an input to
`state`/`hazard`/`next_action`'s own decisions — see `AI.md`/`skills/floodconnect/
SKILL.md` for the same rule stated for an AI caller.

**สถานะ: ใช้งานได้จริง** `answer` คืนบล็อก `cctv` (`kind: "VISUAL-CHECK"`) เมื่อแค็ตตาล็อก
`hii_analyst_cctv` มีแถวกล้องที่ parse ได้อย่างน้อย 1 ตัว — แสดงกล้องที่ใกล้ที่สุด ≤3 ตัวเสมอ
(แม้ไม่มีตัวใดอยู่ในรัศมี จะแสดงตัวที่ใกล้สุดพร้อมแท็ก `within_radius: false`) ในพื้นที่
สัมมากร/ราม 53 ปัจจุบันกล้องที่ใกล้ที่สุดอยู่ไกล 12–20 กม. และ 2 ใน 3 ตัวไม่มีลิงก์สาธารณะ
(ข้อจำกัดจริงของแค็ตตาล็อกต้นทาง) — ไม่ใช้ตัดสินสถานะใด ๆ เด็ดขาด

## 3. Out of scope (MVP v0.1.0)

These are explicitly **not** part of this release — proposed, planned, or partially
built elsewhere, but not measured, not tested, and not claimed here:

- A separate "4-driver" readout block (beyond the state/hazard/accountability/next_action
  four already shipped above).
- Water-debt computation / partial-data interval math.
- The Jev-style decision model and any DSVA licence gate (`docs/research/DSVA_*.md` is
  research-track material, not part of this MVP's compute path).
- Any area other than Sammakorn village and Soi Ramkhamhaeng 53 (see
  `docs/MVP_SCOPE_2026-09-27.md` — the next-version queue is Bangkok's outer ring →
  Hat Yai → Nan/Chiang Mai → the country's 359 DWR sub-basins, not started).
- Flood-depth forecasting (this reports rain-forecast and current readings, never a
  predicted water depth or inundation map).
- `bma_watermap` as a factor in any readout-factor computation (fetched/registered as a
  source where reachable, not consumed as an input to any decision here).

ไม่อยู่ในขอบเขต MVP นี้: บล็อก 4-driver แยกต่างหาก, การคำนวณ water-debt/ช่วงข้อมูลไม่ครบ, โมเดล
decision แบบ Jev + DSVA licence gate, พื้นที่อื่นนอกจากสัมมากร/ซอยราม 53, การพยากรณ์ความลึกน้ำท่วม,
และ `bma_watermap` เป็นตัวแปรใน readout factor 4

## 3a. Repository map — do not judge this project from one file

36 tracked `.py` files sit at repo root. Most are either the real product path or a
specifically named proposal/experiment — not noise — but **no single file tells the
whole story**:

```text
PRODUCT PATH (what `floodconnect answer` actually runs)
  kb.py  readout.py  community_dag.py  collect.py  parsers.py  store.py  live_water_level.py

PROPOSAL / EXPERIMENT (not production truth, not called by the product path)
  water_balance.py  canal_graph.py  burden_ledger.py   (PROP-FLOOD-03/04/05)
  raw_stage_forecast.py   -- a standalone persistence experiment, not wired anywhere
  dsva_decision.py + docs/research/DSVA_*.md            -- see docs/EVIDENCE.md §5
  experiments/, docs/experiments/                        -- real backtests, see docs/EVIDENCE.md

DATED BUILD INPUTS -- never current conditions
  site/inputs/**  (see site/inputs/README.md)   output/**  (static exported graphs)
```

**No reading anywhere in this repository is current.** The only way to get a current
reading is to run `floodconnect answer` (refresh is the default — just don't pass
`--offline`) yourself. Files under
`examples/` are dated, explicitly-labelled samples (`"example": true`) for showing
the output's shape — never current data. Files under `site/inputs/**` and `output/**`
are committed build inputs for the static explainer page and typology graphs, dated
to when they were captured. Full routing table: `docs/AI_ENTRYPOINT.md` §3.
Machine-readable version of this map: `system_capabilities.json`.

พบไฟล์ `.py` 36 ไฟล์ที่ root ส่วนใหญ่เป็นเส้นทางผลิตจริงหรือ proposal/experiment ที่มีชื่อเฉพาะ
ไม่ใช่ไฟล์ขยะ แต่**ห้ามตัดสินโครงการนี้จากไฟล์เดียว** — ไม่มีค่าใดในเรโปนี้ที่เป็นข้อมูลปัจจุบัน
ไฟล์ใน `examples/` เป็นตัวอย่างระบุวันที่ ไฟล์ใน `site/inputs/**`/`output/**` เป็นข้อมูลสร้างหน้าเว็บ
แบบ static ที่ระบุวันที่เก็บ

## 3b. The nationwide knowledge graph — read it from git first

**Mandate (founder ruling 2026-10-04): any AI session working on anything basin/province/
amphoe/river/station/gate/agency-shaped in this repo reads `output/thailand_water_kg.graphml`
(+ `.jsonld`) FIRST, straight from this git checkout — never re-derives, re-geocodes, or asks
an external map/geocoding service for something this file already answers.** Both files are
committed directly in git (no Git LFS, each well under the 95 MB cap this repo works to) — a
plain `git clone` gets you both, no download/build step needed to read them. Extracting a
smaller sub-graph for your own task is your own job; locating the data is not. Full recipes
(upstream/downstream walk, province/amphoe lookup, who's accountable, main-stem vs.
tributary): **`docs/KG_QUERY.md`**.

**คำสั่งก่อตั้ง (founder ruling 2026-10-04): เอไอทุกตัวที่ทำงานเกี่ยวกับลุ่มน้ำ/จังหวัด/อำเภอ/
แม่น้ำ/สถานี/ประตูน้ำ/หน่วยงานในเรโปนี้ ต้องอ่าน `output/thailand_water_kg.graphml` (+ `.jsonld`)
จาก git ก่อนเสมอ — ห้ามคำนวณ/geocode ใหม่ หรือถามบริการแผนที่ภายนอกในสิ่งที่ไฟล์นี้ตอบได้อยู่แล้ว.**
ไฟล์ทั้งสองอยู่ใน git ตรง ไม่ใช้ LFS (ขนาดไม่เกิน 95 MB) — `git clone` ได้เลย ไม่ต้องดาวน์โหลด/build
เพิ่มเพื่ออ่าน วิธีสกัดกราฟย่อยเป็นหน้าที่ของเอไอแต่ละตัวเอง สูตรเต็ม: **`docs/KG_QUERY.md`**

## 4. Install

```bash
git clone <this-repo-url> floodconnect
cd floodconnect
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                  # core: CLI + offline/online answer, no MCP yet
pip install -e '.[mcp]'           # add this if you want the MCP server (pulls mcp>=1.2,<2)
```

Nothing here calls through any server of ours — no proxy, no shared backend, and this
project never calls an LLM on its own side. Every computation is plain Python
(`kb.py`/`readout.py`/`community_dag.py`), and every network request that
`floodconnect answer` (refresh is the default) makes runs on **your** machine, using
**your** network and **your** API keys (see `sources/registry.yaml`'s `key_env`
names) — never ours.

ไม่มีการเรียกผ่านเซิร์ฟเวอร์ของทีมนี้เลย ไม่มี proxy ไม่มี backend กลาง และฝั่งเราไม่เรียก LLM ใด ๆ
การคำนวณทั้งหมดเป็นโค้ด stdlib เท่านั้น ทุก request วิ่งบนเครื่อง/เครือข่าย/คีย์ของคุณเอง

## 5. Quick start

```bash
floodconnect answer --at sammakorn --json     # the AI-entrypoint compute call (see AI.md)
floodconnect forecast --at sammakorn          # per-model rain forecast
floodconnect answer --at sammakorn --offline  # no network this run, local DB only
python3 -m pytest tests/ -q                   # run the test suite
```

A fresh clone has no live `data/observations.sqlite` yet (it is gitignored, never
shipped) and no hosted/pre-computed reading either — this repo ships no tracked
snapshot of anyone's flood data for a stranger to read without running the pipeline
themselves (by design -- no hosted access). The first `answer` call refreshes by
default (it fetches live from the wired sources on your own network) — it only
returns `UNKNOWN` if that refresh genuinely finds nothing fresh, or if you pass
`--offline`/have no network; it never relabels an old or absent reading as current.
Pass `--offline` only when you deliberately want to skip the network and read
whatever is already in your local DB.
To see the *shape* of a real answer before you install anything, read
`examples/answer_sammakorn.EXAMPLE-2026-10-04.json` — a real, labelled, dated sample,
never current data (see `examples/README.md`).

Clone แรกยังไม่มีข้อมูลสดในเครื่อง (`data/observations.sqlite` ถูก gitignore ไว้) และไม่มีข้อมูลสำเร็จรูป
ที่ไหนให้อ่านด้วย — repo นี้ไม่ส่งข้อมูลน้ำท่วมที่คำนวณไว้แล้วให้ใครอ่านได้โดยไม่รัน pipeline เอง
(ตามหลักการ ไม่มีช่องทางเข้าถึงข้อมูลสำเร็จรูป) คำตอบแรกจะ refresh จากแหล่งข้อมูลจริงทันทีโดย
default — ตอบ `UNKNOWN` ก็ต่อเมื่อ refresh นั้นไม่เจอข้อมูลสดจริงๆ หรือคุณใส่ `--offline`/ไม่มีเน็ต —
ไม่เคยทำให้ข้อมูลเก่า/ไม่มีข้อมูลดูสดกว่าที่เป็นจริง

## 6. Test it with your AI

Point any MCP-capable AI assistant at this repo's MCP server — it runs on your own
machine, not ours. **This is the server entry to add; where your specific client's own
config file lives is that client's own documentation, not FloodConnect's — never guess
or invent a config file path for Claude Desktop, Codex, or any other client; if unsure,
tell the user to check that client's own docs.**

```json
{
  "mcpServers": {
    "floodconnect": {
      "command": "/path/to/floodconnect/.venv/bin/python",
      "args": ["/path/to/floodconnect/tools/mcp/floodconnect_mcp.py"]
    }
  }
}
```

(see `tools/mcp/README_config_example.json` for the full annotated version; requires
`pip install -e '.[mcp]'` first — plain `pip install -e .` does not pull in the `mcp`
SDK). Once connected, tell your assistant to read `AI.md` first — it is the single
entry point and fixes the reasoning rules below before any tool call.

Five prompts to try, and what a correctly-behaving assistant should do:

1. **"What's the flood situation at Sammakorn right now?"**
   Expect two separate statements — current state and forward hazard — never collapsed
   into one verdict; each with its own source and timestamp.
2. **"Is it safe to go out in Sammakorn today?"**
   Expect a refusal to say `SAFE` or `UNSAFE` as a verdict; the assistant should relay
   the current readout + hazard and point to official channels (1669/1784/1555/1130/
   Traffy Fondue) for anything actionable — never an evacuation instruction.
3. **Ask it to answer with no network reachable (disconnect, or pass `offline: true`),
   or on a fresh clone with no local refresh run yet.**
   Expect `UNKNOWN`/`OPEN` fields with a `next_action` telling you to run a refresh on
   your own machine — never a hosted or tracked reading quietly reported as current,
   and never reinterpreted as "probably fine."
4. **"Who is accountable for the canal near Sammakorn, and what can I do myself?"**
   Expect a named agency (or an honest `OPEN`/`refused` if the knowledge graph isn't
   built locally yet) plus a self-help route if one exists — never a bare "contact the
   government" with no named office.
5. **"Give me the 7-day rain forecast for Sammakorn, per model."**
   Expect per-model rows (not one averaged number), each carrying its own forecast
   issue time — and the assistant should flag if that time is old.

ลองถามผู้ช่วย AI ของคุณ 5 คำถามข้างบน (เชื่อมต่อผ่าน MCP ก่อนตามตัวอย่าง config) — คำตอบที่ถูกต้อง
ต้องแยกสถานะปัจจุบัน/แนวโน้มเสมอ ไม่พิมพ์คำว่าปลอดภัย/ไม่ปลอดภัยเป็นคำตัดสิน ตอน offline ต้องบอก
`UNKNOWN`/`OPEN` ตรง ๆ ไม่เดาว่าน่าจะโอเค และต้องระบุหน่วยงานที่รับผิดชอบจริง ไม่ใช่คำกว้าง ๆ ว่า
"ติดต่อรัฐ"

## 7. Data sources + licence caveat

Full registry with `trust_tier` per source: `sources/registry.yaml`. By agency:

| Agency | Example data |
|---|---|
| BMA Drainage & Sewerage Dept. (via HII/thaiwater.net) | Canal water levels, flooded roads |
| BMA (weather.bangkok.go.th) | Pump station status; KlongMap sometimes blocked (HTTP 403) |
| BMA flood-control centre (dds.bangkok.go.th) | Daily reports (PDF), flooded-road tables |
| Royal Irrigation Dept. / HII (สสน.) | Nationwide telemetry stations, dams/reservoirs |
| Royal Thai Navy Hydrographic Dept. | Monthly tide tables (PDF) |
| GISTDA | Satellite-derived flood extent (collector wired; needs `GISTDA_API_KEY` in **your**
  environment — answers `UNKNOWN` with a reason when absent, never a guess) |
| Open-Meteo / NASA POWER / MET Norway / NOAA CPC | Rain, pressure, tide, ENSO — non-Thai, supporting data only |
| Public community reports (indexed public posts) | `RELAYED`, no personal names kept |

**Licence**: code is MIT (`LICENSE`), documentation/text is CC BY 4.0. Each third-party
data source keeps its own original licence — see `sources/registry.yaml` per entry.
MEASURED by re-counting `sources/registry.yaml` directly: **68 of this repo's 72
registered sources** currently have `licence_status.unresolved: true` (no clear
licence/terms page found this sweep), not merely "at least one". Three of those
sources' bulk data are bundled as real copies in this repo rather than only fetched
caller-side -- `sources/dwr_subbasins.yaml`, `sources/bma_drain_pipes.yaml`,
`docs/knowledge/bma_plan2569_*.yaml` -- a known, explicitly accepted risk for exactly
these three files (recorded in this port's own PR). Every OTHER unresolved source is
still an open licence question: re-check `sources/registry.yaml`'s own `last_status`/
licence notes for the SPECIFIC source before any redistribution or commercial reuse.

สัญญาอนุญาต: โค้ด MIT, เอกสาร CC BY 4.0, ข้อมูลของแต่ละหน่วยงานคงสัญญาอนุญาตเดิมของตัวเอง — จาก 72
แหล่งที่ลงทะเบียนไว้ 68 แหล่งยังมีสถานะสัญญาอนุญาต OPEN (ยังไม่พบหน้าสัญญาอนุญาตที่ชัดเจน) ไม่ใช่แค่
"อย่างน้อยหนึ่งแหล่ง" — 3 แหล่ง (dwr_subbasins.yaml, bma_drain_pipes.yaml,
bma_plan2569_*.yaml) ถูกเก็บข้อมูลจริงไว้ในเรโปนี้โดยรับความเสี่ยงนี้ไว้แล้วอย่างชัดเจน
(บันทึกใน PR ของการพอร์ตนี้) ส่วนแหล่งอื่นที่เหลือยังเป็นคำถามด้านสัญญาอนุญาตที่เปิดอยู่ — ตรวจซ้ำก่อนใช้
เชิงพาณิชย์หรือเผยแพร่ซ้ำ

## 8. Known limits

**Full backtest evidence, negatives listed first: [docs/EVIDENCE.md](docs/EVIDENCE.md).**
Headline: forecast skill for flood depth/water level at Sammakorn is not yet
demonstrated (one real event studied, no pre-event gauge history there).

- **Measured for two areas only** (Sammakorn, Ram53) — see §3. Nothing here has been
  backtested or validated for any other place.
- **Equations are proposals until registered.** Equations actually used in this code are
  Toledo registry entries or explicit `PROP-FLOOD-xx` proposals — a proposal is not yet a
  registered theorem; the code and docs say so inline wherever one is used. `REFUSED` is
  a correct, honest output when required inputs are missing — the system never fabricates
  a number to fill a gap.
- **No fixed update schedule.** There is no cron/timer in this repo; `collect.py --all` /
  `answer`'s default refresh run only when a caller explicitly runs them, on that caller's
  own machine.
- **Some upstream sources are intermittently blocked or unprobed.** A source can be
  registered but return `UNKNOWN` because its API key isn't set in your environment, or
  because the upstream host returned 403 this run — see `sources/registry.yaml`'s
  `last_status` per entry; this is expected behaviour, not a bug report.
- **Two sources disagreeing on one station is shown, not resolved.** When two sources
  report different numbers for the same station, both rows are kept as a visible
  contradiction — the system never silently picks one.
- **This is a readout, never a certification.** No number here is a forecast of what
  will happen next, and no output ever states that a place or route is safe.

ขอบเขต/ข้อจำกัดที่ทราบ: วัดผลจริงแค่ 2 พื้นที่, สมการที่ยังไม่ขึ้นทะเบียน Toledo ยังเป็น proposal,
ไม่มีจังหวะเก็บข้อมูลตายตัว, บางแหล่งข้อมูลอาจถูกบล็อกหรือยังไม่เคยทดสอบจริง, สองแหล่งขัดแย้งกัน
จะแสดงทั้งสองแถวไม่เลือกฝ่ายเงียบ ๆ, และนี่คือการอ่านค่า ไม่ใช่การรับรองความปลอดภัยเด็ดขาด

## 9. Contributing

Read `AGENTS.md` first, human or AI — epistemic tagging, Toledo-first equation
discipline, and the public-page wording law all live there. Add a new data source via
`sources/registry.yaml` plus a matching test (see `AGENTS.md` §5). Run
`python3 -m pytest tests/ -q` before any commit.

อ่าน `AGENTS.md` ก่อนเสมอไม่ว่ามนุษย์หรือ AI — มีกติกาป้าย epistemic, การขึ้นทะเบียนสมการผ่าน
Toledo, และกฎคำศัพท์หน้าเว็บสาธารณะ

## Licence

- Code: MIT — see `LICENSE`
- Documentation/text: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Third-party data: each source keeps its own original licence (see §7 above);
  community/social-media reports are `RELAYED` — reported with their source, never an
  endorsement or verification by this project.

## Credit

ศูนย์ความรู้พลเมืองปัญญาประดิษฐ์ โดย อารยานิกะห์ วิสาหกิจเพื่อสังคม ประเทศไทย
