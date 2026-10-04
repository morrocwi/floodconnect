# FloodConnect

**A flood/canal/pump knowledge-graph readout — the fields any AI assistant can read
directly, tagged by how sure we are, never a forecast and never a safety certification.**

**ระบบ "อ่านค่า" น้ำ/คลอง/ปั๊ม แบบกราฟความรู้ — ไฟล์ที่ผู้ช่วย AI ตัวใดก็เปิดอ่านต่อได้ทันที
ทุกค่าติดป้ายความน่าเชื่อถือ ไม่ใช่การพยากรณ์ และไม่ใช่การยืนยันความปลอดภัย**

Start here → **[START_HERE.md](START_HERE.md)** (human-facing, 5-minute read, Thai) ·
**[AGENTS.md](AGENTS.md)** (AI-facing rules, bilingual) · **[AI.md](AI.md)** (the single
AI compute entrypoint).

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
| **1555** | BMA flood hotline / สายด่วนน้ำท่วม กทม. |
| **1130** | MEA electrical hazard / ไฟฟ้าขัดข้อง-อันตรายจากไฟฟ้าในน้ำ |
| **Traffy Fondue** | Official BMA street-flooding report channel |

---

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

**This is a readout, not a forecast, not a safety certification.** Every number is what
was read from a named source at a named time — never a prediction of what will happen,
never a statement that it is safe to stay or leave.

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
(`kb.py`/`readout.py`/`community_dag.py`), and every network request `answer --refresh`
(the default) makes runs on **your** machine, using **your** network and **your** API
keys (see `sources/registry.yaml`'s `key_env` names) — never ours.

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
themselves (by design -- no hosted access). The first `answer` call honestly returns
`UNKNOWN` with a `next_action` telling you to run `floodconnect answer --refresh` on
your own machine; it never relabels an old or absent reading as current. Run `answer`
(the default already refreshes) when you have network to fetch your own live data.

Clone แรกยังไม่มีข้อมูลสดในเครื่อง (`data/observations.sqlite` ถูก gitignore ไว้) และไม่มีข้อมูลสำเร็จรูป
ที่ไหนให้อ่านด้วย — repo นี้ไม่ส่งข้อมูลน้ำท่วมที่คำนวณไว้แล้วให้ใครอ่านได้โดยไม่รัน pipeline เอง
(ตามหลักการ ไม่มีช่องทางเข้าถึงข้อมูลสำเร็จรูป) คำตอบแรกจะเป็น `UNKNOWN` พร้อม `next_action` บอกให้รัน
`floodconnect answer --refresh` บนเครื่องตัวเอง — ไม่เคยทำให้ข้อมูลเก่า/ไม่มีข้อมูลดูสดกว่าที่เป็นจริง

## 6. Test it with your AI

Point any MCP-capable AI assistant at this repo's MCP server — it runs on your own
machine, not ours:

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
