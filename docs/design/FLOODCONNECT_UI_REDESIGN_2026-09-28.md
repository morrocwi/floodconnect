# FloodConnect: final redesign spec (หน้าสถานะน้ำท่วมสำหรับชาวบ้าน)

Chair's decision, 2026-09-28. Copied from the design-meeting scratchpad into the repo per
founder direction. See "Implementation status (2026-09-28 build)" at the end of this file
for what this check actually shipped vs. what remains OPEN.

Scope: presentation and layout only. No change to data semantics or computations
(`site/build_data.py`, `tools/*` logic, `data.json` values stay as they are). All work
happens in `site/build_page.py`, `site/index.template.html`, and the render layer of
`tools/heromap/sammakorn_map.py`.

## 0. Decision summary

- **Base: Proposal 2 (Evidence-First).** All three judges ranked it first (8 / 7.5 / 7.5). It is the only one that keeps the heromap ring map at the top.
- **Grafted in:**
  - P1: a fixed 3-line template inside each details section, large call buttons, the honest reading line, the `--watch` token, and one static file per area.
  - P3: the rain picture tile, the readout-tag pill on the hero, a contradiction link that appears only when a contradiction is active, the "หาซอยของฉัน" jump, and the tag gloss.
- **Rejected:**
  - P2's `?area=` query param (a static build cannot read it).
  - P3's "server re-render" and partial `display:none` (same reason).
  - P2's double-nested model list (single level only).
  - P2's ↑/↓ in/out arrows.
  - P3's dots-only mini-map.
  - Every "central value first" rain line from P1 and P3.
- **Founder direction 2026-09-28 (verbatim):** "โมเดลไปรวบไว้ข้างล่างก็ได้นะ เน้นข้อมูลน้อยที่สุด ทำเป็นรูปภาพ ส่วนรายละเอียดให้เอาไว้ท้ายๆ ให้กดแล้วอ่านเข้าใจในสิบวิ". It is implemented as:
  - (a) the per-model list is the second-to-last details section, collapsed;
  - (b) the first screen is pictures plus coloured numbers;
  - (c) every details section follows the 10-second template in §5.

### Facts checked against the current build (VERIFIED, 2026-09-28 06:47 build)

These correct points in the proposals and judge notes:

1. **A trend field does exist.** `areas.<id>.stations_near[].delta_m/prev_value_m/prev_observed_at` and `pumps[].prev_level_m/delta_m` are present, and `build_page.level_trend_html()` already renders ขึ้น / ลง / คงที่ / "ยังบอกไม่ได้" using an ε of 0.02 m and a minimum gap of 0.9 h. Up/down arrows are therefore allowed, but **only** through `level_trend_html()` on each station row. They are never used on the in/out/capacity tiles, and no new trend is derived.
2. **The true worst-case rain is 100.1 mm over 72 h (CMA).** Source: `layer0_public.areas.sammakorn.prop_flood_06.forecast_72h_worst_text_th`, plus a 10-item list already sorted worst-first in `forecast_72h_items_th`. Neither "~17 mm" nor "~39 mm" (single-source/single-day figures) may lead. **No per-model 6 h or 24 h worst field exists**, so the page shows a 72 h worst tile only.
3. **Pump status as sourced.** `pumps[].status_th = "ขัดข้อง"`, `pumps_on = 0` on all 4, `level_m = null`. Relay verbatim. Never upgrade to "หยุดทำงาน", never invent a level.
4. **PROP-FLOOD-08/09/10.** Zero references in `build_page.py`/`build_data.py` and zero `PROP-FLOOD` strings in `dist/floodconnect.html`. Those three live only in `docs/experiments` and `docs/knowledge`. A build-time guard (§9) is meant to keep 08/09/10 out (see status note below on this guard).
5. **Banned words** ไม่ต้อง / ห้าม / ไม่ควร / ผ่อนคลาย: 0 hits. `raw/`, `/home`, `wire`, `LAYER`, `median`/`มัธยฐาน`: 0 hits. Jargon still visible above the divider today: `ST.SPS` (pump-code column, in the always-visible pump table) and `RTSD` — see status note.
6. **Size.** `dist/floodconnect.html` measured at 346,421 B before this check; 337.1 KB after this check's reorder (see status note — still over the 300 KB target).

---

## 1. Section order (ลำดับหน้า)

```
[A] Top bar ─ ชื่อ + ลิงก์เลือกพื้นที่ (<a>) + A−/A+
[B] HERO ─ แถบสถานะ (คำสี + เวลาอ่าน + ป้าย) → แผนที่วงแหวน heromap (ปั๊ม 4 ตัว, ตัวเลขสี) → แถบคำอธิบายสี
[C] ภาพ 3 ช่อง ─ ปั๊ม | ฝน 72 ชม. แย่สุด | คลองรอบบ้าน
[D] ข้อเท็จจริงตัดสิน (ปั๊ม) + ลิงก์ "ดูข้อมูลที่ขัดกัน" (เฉพาะเมื่อมี)
[E] บรรทัดทำอะไรได้ตอนนี้ + ปุ่มโทร 1555 / 1669
──────────── (จบหน้าจอแรก)
[F] ซอยของฉัน ─ ชิป ≤6 ซอยที่หนักสุด + ปุ่ม "ดูทั้งหมด N ซอย" + "หาซอยของฉัน"
[G] สิ่งที่ทำได้ ─ 6 ข้อ มีไอคอน (ข้อความเดิม)
[H] ตัวคั่น "ข้อมูลละเอียด — แตะเพื่อเปิดดู · แต่ละหัวข้ออ่านจบใน 10 วินาที"
 D1 ปั๊มบึงในหมู่บ้าน
 D2 ระดับน้ำคลองรอบบ้าน
 D3 น้ำเข้า · น้ำออก · รับมือได้
 D4 ซอยทั้งหมด
 D5 ถ้าต้องการความช่วยเหลือ
 D6 ทางออกจากพื้นที่ + ถนนที่น้ำท่วม
 D7 ทางการบอกอะไร (ผู้ว่าฯ / สำนักการระบายน้ำ)
 D8 ข้อมูลที่ขัดกัน (เทียบแหล่ง)
 D9 ทางน้ำไหล (กราฟคลอง)
 D10 สายการไหลหลักถึงสัมมากร
 D11 ผลที่วัดได้ที่ประตูน้ำ
 D12 เสียงจากอินเทอร์เน็ต (ยังไม่ยืนยัน)
 D13 น้ำขึ้นน้ำลง
 D14 พยากรณ์ฝนแยกทีละแบบจำลอง  ← founder: "โมเดลไปรวบไว้ข้างล่าง"
 D15 สมดุลน้ำ (สูตรเป็นข้อเสนอ ยังไม่ผ่านการตรวจ) ← สุดท้ายเสมอ
[Z] Footer ─ แหล่งข้อมูล + คำชี้แจง
```

Every D-section is a sibling `<details>`, one level deep only.

---

## 2. First screen at 360 px (หน้าจอแรก)

- **Budget:** 360 × 740 CSS px viewport, about 640 px usable. [A] through [C] must be fully visible without scrolling. [D] and [E] must finish within the first 800 px of the document.
- **Text budget:** at most about 250 Thai characters of prose above [F].
- **Excluded from the first screen:** tables, model names, station codes, datum/accuracy caveats, and paragraphs.

**ram53** has no heromap (`build_hero_map_html` returns "" for areas other than sammakorn). Its [B] becomes a coloured-number list: one row per `stations_near` + `pumps` item, worst tier first, each row = dot + name + value + word + tag. No prose.

---

## 3-11. Components, tags, wording, type scale, a11y, size budget, acceptance checklist

See the design-meeting scratchpad transcript (chair's decision record, 2026-09-28) for
the full component table (§3), readout-tag rules (§4), the 10-second details template
(§5), exact Thai wording (§6), type/colour/dark-mode tokens (§7), accessibility rules
(§8), the size-budget levers (§9) and the full acceptance checklist (§10). This repo file
is the durable copy the founder asked for; the sections above (§0-§2) are reproduced in
full because they set the ordering contract this build implements and tests against.

---

## Implementation status (2026-09-28 build, branch `feat/redesign-v2`)

**Shipped in this check** (VERIFIED against `site/dist/floodconnect.html` after
`python3 site/build_data.py && python3 site/build_page.py`):

- The per-model 72h rain forecast list (`forecast_72h_items_th`) and the dev-jargon
  engine note ("คำนวณด้วยสมการรุ่น ...") were removed from the top-of-page LAYER 0
  block and now render ONLY in a new collapsed `<details>` section (D14,
  `build_layer0_model_list_html()`), placed immediately before the water-balance
  section (D15), which stays last. Worst-first order is preserved verbatim from
  `build_data.py` — this check never re-sorts or re-derives rain figures.
- The LAYER 0 in/out/capacity summary block, previously the first thing after the
  hero map, now sits inside its own collapsed `<details id="layer0-details-*">`
  (D3), inside the "ข้อมูลละเอียด" details cluster rather than always-visible.
  It keeps only the single worst-case 72h summary sentence, never the per-model
  breakdown.
- The "ข้อมูลละเอียด" divider heading now reads "ข้อมูลละเอียด — แตะเพื่อเปิดดู ·
  แต่ละหัวข้ออ่านจบใน 10 วินาที" per §H, with minimal `.dsec-h`/`.dsec-peek`/
  `.dsec-headline` CSS for a peek-summary + headline-sentence pattern on the new D14
  section.
- 706 pre-existing tests still pass unchanged; 10 new tests
  (`tests/test_redesign_2026_09_28.py`) assert the new order and the founder rules
  (no per-model list or jargon above the fold, worst-first preserved, D14 sits right
  before D15, no `<details open>`).
- Gate grep on the rebuilt page: resident-facing word bans, dev-jargon terms ("LAYER 0",
  "wire", "median"), AI/vendor names, and the local path marker all
  0 hits; `PROP-FLOOD-08/09/10` 0 hits; `วัดจริง` present; 4 pump glyphs
  (`aria-label="ปั๊ม "` × 4); `WL.SSB.08` still shown grey/suspect with the neighbour
  band; `WL.BMA.02` still referenced per existing (pre-redesign) data/prose.

**OPEN / not done in this check** (INSTINCT — these are real gaps against the full
spec above, left for a follow-up pass rather than claimed done):

- §1's full first-screen redesign (picture tiles [C], decisive-fact line [D],
  contradiction link, zone chips [F]) was **not** rebuilt from scratch — the
  existing v2 template's hero/banner/tile-grid/advice sections were left as they
  were before this check, since they already satisfied several founder rules (hero
  map first, no averaged headline, tags on L0 items) and a full rewrite was out of
  scope for this check's time budget.
- §9.1 (one static page per area, `floodconnect-sammakorn.html` /
  `floodconnect-ram53.html`) was **not** implemented. The page is still a single
  combined file with both areas and a `<select>` toggle. Measured page size after
  this check: 337.1 KB — still over the 300 KB budget (it was 346.4 KB before this
  check; the reorder alone did not remove enough bytes, since content was relocated,
  not deleted).
- §9.7's build-time size/banned-word guard (fail the build itself, not just report a
  warning) was **not** added to `build_page.py`'s `main()`. `main()` still only
  prints a `WARNING` when the page exceeds 300 KB and does not grep for banned
  strings at build time.
- `ST.SPS` pump codes and `RTSD` still appear above the "ข้อมูลละเอียด" divider,
  inside the always-visible pump table (D1's table is not itself behind a
  `<details>` in the current template) — moving that table behind a details toggle
  was judged out of scope for this check.
- Readout-tag pills on every rendered number (§4), the type-scale/contrast token
  work (§7, incl. the new `--watch` token), and the full accessibility checklist
  (§8) were not audited or built out in this check.
