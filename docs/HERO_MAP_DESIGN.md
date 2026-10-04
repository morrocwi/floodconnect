# HERO_MAP_DESIGN.md — "แผนที่น้ำรอบบ้าน" (Sammakorn hero-map schematic)

## Revision 2 (2026-09-27, same task/session)

The orchestrator reviewed the first draft's PNG preview and sent a follow-up revision
(verbatim, relayed): the PNG rasteriser used for that first review (`cairosvg`) has no Thai
font installed, so Thai text showed as tofu boxes in that preview only — re-verify visually
via a real browser engine instead. The layout also "read as a card grid, not a map" — redo
it as a blue canal RING (four bands) around a central village block, closer to
`raw/design/sammakorn_handdrawn_map_founder_2026-09-27.png`, with band labels ON the band,
number pills ON the band, the pond inside the block, 4 pump icons at the drawing's corners
touching their band, and arrow glyphs (→ ← ≈ ?) on the links for measured direction. Keep
everything else (numbers+colour only, strict-normal rule, SSB.08 small/grey, multi-station
band worst-status, 3-chip legend) and raise every text node to ≥12px (was 10.5px on some
sub-lines in the first draft). Target: 360px wide, height ≤~520px, so it fits above the fold
with the layer-0 line below.

**What changed in the code** (`tools/heromap/sammakorn_map.py`):
- Replaced the card-grid `_chip`/`_pump_icon` layout with a ring layout: `RING_X0/Y0/X1/Y1`
  + `BAND_T` (70px band/corner-square thickness) define four band rectangles (north/south
  full-width strips, west/east strips between the corners) around a `VILLAGE_X0..X1,
  Y0..Y1` block — reworked `render_sammakorn_hero_map()`, new `_pill()` (replaces `_chip`),
  new `_corner_pump()` (replaces `_pump_icon`), new `_edge_arrow_symbol()`/`_arrow_link()`
  (replaces the old "?"-only `_dashed_link()`).
- `TEXT_FLOOR = 12` (was 10.5px on some lines) — every `_fit_text` call in the new layout
  uses this or higher; text that would overflow its pill is compressed via `textLength`
  (already the mechanism from the first draft), never shrunk below 12px.
- `VIEW_H` dropped from 600 to 512 (`VIEW_W` unchanged at 360) to meet the "~520px, above
  the fold" target — made possible by the single-row 3-chip legend (was 3 stacked rows) and
  the ring layout's own more compact use of vertical space.
- Two real layout bugs found and fixed WHILE building this revision (not shipped as pre-existing
  known issues — both are recorded here so they aren't reintroduced by a future edit):
  1. **Corner-icon bleed**: a first attempt at "pump icon at the corner" centred the icon
     exactly ON the vertex where the two bands and the village box meet. The icon's own
     2-line label extends outward from its centre, and at that position it bled sideways
     into the neighbouring band's own pill and into the band-title text (confirmed via a
     Playwright screenshot, not by reasoning alone). Fixed by centring each icon in the
     middle of its 70×70 corner SQUARE instead of on the vertex — still visually "touching"
     both bands (the corner square belongs to both), without the collision.
  2. **Village-block z-order clipping**: the west/east band pills are deliberately allowed
     to overlap a few px into the village block's edge (so a long tier word like
     "ยังไม่มีเกณฑ์ปกติ" has room to compress into instead of being cut). The village
     block's own opaque background rect was drawn AFTER those pills in the SVG's paint
     order, so it silently painted over — visually truncating — the overlapping half of the
     pill's text (looked like real character truncation, not a compression artefact — a
     `textLength` compression never drops characters; confirmed by reading the raw SVG
     markup, which showed the full string with a correct `textLength` attribute, before
     finding the actual cause was paint order). Fixed by moving the village block + pond +
     summary-chip drawing to BEFORE the band pills in the function body, so pills always
     paint on top.
- Neither bug was caught by `tests/test_heromap.py`'s string-presence assertions (both are
  purely geometric/paint-order issues) — they were only caught by actually rendering the SVG
  and looking at it, which is exactly why this revision's request for a real-browser
  screenshot mattered. Recorded as a gap in this check's own test coverage, not solved by
  adding a new geometric test in the time available — the honest fix was to look, not to
  keep asserting.

**Playwright re-render** (real Thai font, Chromium, `python -m playwright`/`playwright.sync_api`,
this environment has `Noto Sans Thai`/`Noto Serif Thai` installed system-wide):
- `site/dist/prototype/sammakorn_hero_map_live_playwright.png`
- `site/dist/prototype/sammakorn_hero_map_synthetic_normal_playwright.png`

Both confirmed visually correct Thai rendering (no tofu), the ring/village/pond/corner-pump
layout, all pills' text fully visible (no clipping), and the single-row 3-chip legend. The
earlier `cairosvg`-rendered `..._preview.png` files are left in place for reference but are
superseded by these two as the ones to actually judge the design against — see §7 below for
the caveat on why they showed tofu.

---

**Status**: PROTOTYPE, not wired into `site/build_data.py` / `site/build_page.py`.
Write-scope for this check: `tools/heromap/__init__.py`, `tools/heromap/sammakorn_map.py`,
`tests/test_heromap.py`, this file, and `site/dist/prototype/*` (gitignored, never
committed). No existing tracked file was edited. The other worker on this branch owns
`build_data.py`/`build_page.py` and is the only committer — this document is written for
them.

## 1. What this is

Founder ask (verbatim, via the orchestrator): "ถ้าเราจะใช้ภาพนี้เป็นภาพใน hero ของ
อาร์ติแฟกต์ ออกแบบใหม่ตามสกิลออกแบบของระบบ แล้วให้แต่ละจุดขึ้นตัวเลขคลองสำคัญทั้งสี่ด้านว่าเต็มหรือ
เขียวแล้ว ดีไหม แบบให้พอดีในมือถือ" — redesign
`raw/design/sammakorn_handdrawn_map_founder_2026-09-27.png` as the public page's hero
image, keep the four-canal-sides + village + pond + pump-station layout, but replace the
hand-drawn art with a data-bound schematic that fits a phone screen and follows the
`floodconnect-design` skill contract.

Three follow-up project decisions arrived mid-task (relayed secondhand; **not**
independently re-confirmed directly with the founder — tag `RELAYED-by-orchestrator`
throughout this document) and are folded into the implementation:

1. **"แสดงแต่ภาพและตัวเลข เขียวหรือแดงตามวิกฤต ส่วนผลวิเคราะห์ให้อยู่ส่วนอื่น"** — the SVG
   returned by `render_sammakorn_hero_map()` carries ONLY the schematic + per-point numbers
   + a status colour + a short status WORD + a 3-item colour-key legend. No interpretive
   sentence, no synthesis line, no "what to do" text anywhere inside the SVG. The live
   layer-0 sentence is returned as a **separate** string by `layer0_caption_th()`, for the
   committer to place in the HTML immediately below the map — never inside the SVG.
2. **"ไม่ปกติ ต้องต่ำกว่าเกณฑ์ปกติหรือเปล่า แค่นี้ยังไม่เรียกปกติ"** — a point renders green
   ("ปกติ") only when its live value is at/below its own declared `normal_level_m`
   (`sources/canal_normal_levels.yaml`, dry-season-median basis, tag `MEASURED-history` per
   that file's own header). No `normal_level_m` on record → the point can never render
   green; it renders grey "ยังไม่มีเกณฑ์ปกติ" **unless** it has already breached its own
   warning/critical/bank threshold, which still renders เตือน/วิกฤต/ล้นตลิ่ง regardless of
   baseline availability (breach detection never depends on having a "normal" to compare
   against). See `classify_tier()` in `tools/heromap/sammakorn_map.py`.
3. **"ในภาพหมู่บ้านก็ให้มีปั๊มด้วยว่าทำงานครบสี่ตัวหรือไม่"** — all four village pump
   stations render as icons with live running-count state, plus one village-level summary
   chip ("ปั๊ม x/4 · a/b เครื่อง").

A fourth, earlier note (data rule, also relayed): a canal side must never be coloured from
a single station where more than one is available, and a station whose reading contradicts
its immediate neighbours renders small/grey as a flagged outlier instead of being folded
into the side's colour.

No new Toledo equation anywhere in this module: `classify_tier()` is a pure threshold
bucketing of numbers `site/build_data.py` already computes and places on
`warning`/`critical`/`bank`/`value_m` — the same kind of non-equation classification
`docs/FLOW_STALL_TYPOLOGY.md` §4 calls an "INSTINCT-rule", never a derivation.

## 2. Data binding (what the pure function reads, from data.json's own shape)

| Map element | Source | Notes |
|---|---|---|
| North band: บางกะปิ (SSB.07), บางชัน (SSB.09) | `areas.sammakorn.stations_near[code=WL.SSB.07\|WL.SSB.09]` | Both have a `normal_level_m` on record (`sources/canal_normal_levels.yaml`: −0.36, −0.38). Band shown = worst of the two. |
| North outlier: เสรีไทย 24 (SSB.08) | `stations_near[code=WL.SSB.08]` | Rendered small/grey, tier forced to `OUTLIER` ("ค่าเดี่ยวขัดกับเพื่อนบ้าน"), never folded into the north band's own colour, per the coordinator's data rule. No `normal_level_m` on record for this code either. |
| West: บ้านม้า 2 (BMA.02) | `sammakorn_chain.nodes.banma2` | No `normal_level_m` on record for `WL.BMA.02` → **can never render green** even though its own chain-declared warning/critical (2.14/2.68 m) are nowhere near breached at the live 0.70 m reading (project decision 2 above overrides the "own-scale ปกติ" reading the coordinator's earlier message suggested). |
| East: คลองสะพานสูง | *(no station found)* | Checked: no `stations_near` entry whose name contains "สะพานสูง". Rendered `NO_GAUGE` grey "ไม่มีเครื่องวัด" — never invented. |
| Pond: บึงสัมมากร (SMK.01) | `sammakorn_chain.nodes.pond` | No `normal_level_m` on record for `WL.SMK.01` either; at the live 0.82 m reading it breaches its own critical (0.44 m) anyway → วิกฤต regardless. |
| South: คลองวังใหญ่บน | *(no station found)* | Grey `NO_GAUGE`. Nearest measured neighbours หัวหมาก (`WL.HMK.01`) and คลองจิก (`WL.KJG.01`) shown as separate "ใกล้เคียง" chips, per the coordinator's data rule — never substituted in as if they were the canal itself. |
| Pump stations ×4 | `areas.sammakorn.pumps` | See §3, "known mismatch" — bound by **name/pond_name text**, not by `ST.SPS.0x` code. |
| Village pump summary chip | derived from the same 4 pumps | `ปั๊ม {stations at full run}/4 · {machines on}/{machines total} เครื่อง`. |
| Bottom caption (kept OUT of the SVG) | `layer0_public.areas.sammakorn.out_vs_in_th` + `.in_vs_capacity_th` | `layer0_caption_th()`. Never hardcoded — e.g. today it reads "ระบายไม่ทัน · ยังไม่เกินความสามารถรับมือ", never a fixed "เต็มทุกด้าน" string. |
| Flow-direction glyphs | `sammakorn_chain.edges[*].status`/`.direction` | PROP-FLOOD-04 output only. Every edge in the live `sammakorn_chain` currently resolves `REFUSED`/`unknown` → every connector renders the dashed-grey "?" glyph, never a fabricated arrow. |

## 3. Known mismatch — pump code vs. drawn position (OPEN, needs the data owner)

Two different retellings of "which `ST.SPS.0x` code sits at which drawn corner" were given
to this check, and **neither matches this check's own read of `site/dist/data.json` on
2026-09-27**:

- The original task prompt's mapping: `ST.SPS.01` บ้านม้า 2 (NW), `ST.SPS.04` บึงที่ 4 (SW),
  `ST.SPS.02/03` บึงที่ 1/2 (E/centre).
- The coordinator's follow-up mapping: `ST.SPS.01` บ้านม้า 2 (NW), `ST.SPS.02` บึงที่ 2,
  `ST.SPS.03` บึงที่ 1 (E), `ST.SPS.04` บึงที่ 4 (SW).
- Revision 2's own layout (per the founder's "4 pump icons at the drawing's corners"
  instruction) places all four at the four corners: NW=บ้านม้า 2, NE=บึงที่ 2, SW=บึงที่ 4,
  SE=บึงที่ 1. The hand-drawn reference image itself only draws 3 pump icons (no drawn
  position for บึงที่ 2) — NE was a judgment call to give all 4 real stations a
  corner, not something the drawing itself specifies. Flag this specific placement (NE for
  บึงที่ 2) for founder confirmation too, separately from the code↔pond mapping question
  below.
- **What `data.json` actually contains** (`areas.sammakorn.pumps`, checked directly):
  `ST.SPS.01` = "สถานีสูบน้ำคลองบ้านม้า 2" (`pond_name: null`); `ST.SPS.02` = "สถานีสูบน้ำบึงที่ 4
  ตอนคลองวัดใหญ่" (`pond_name: บึงรับน้ำสัมมากร 4`); `ST.SPS.03` = "สถานีสูบน้ำบึงที่ 2 ตอนคลอง
  บ้านม้า 2" (`pond_name: บึงรับน้ำสัมมากร 2`); `ST.SPS.04` = "สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง"
  (`pond_name: บึงรับน้ำสัมมากร 1`).

None of the three lists agree on the code↔pond mapping past `ST.SPS.01`. **This module
binds by pond/place NAME TEXT, never by the `ST.SPS.0x` code** (`_find_pump_no_pond()` /
`_find_pump_by_pond_number()`), so the map stays correct regardless of which retelling (or
future BMA renumbering) turns out to be right — and it deliberately shows only the plain
Thai place word on the map ("บึงที่ 4", not "ST.SPS.04 บึงที่ 4") to avoid asserting a
code↔position claim this check could not verify. **Flag for the founder/data owner**: please
confirm the true code↔pond mapping once, so a future pass can safely show the code too.

A first draft of this module DID bind by a naive substring match on the full station
`name` field ("คลองบ้านม้า" as the NW test) and got this wrong silently: `ST.SPS.03`'s own
name also contains the text "คลองบ้านม้า 2" (it is the outfall canal name embedded in a
"บึงที่ 2" station's full name), so the naive matcher picked the wrong station and the
village summary chip under-counted total pump machines by one (10 instead of 11). Fixed
by matching on `pond_name is None` (unique to the true NW pump) and on the pond name's own
trailing number for the other three — recorded here so the same mistake isn't repeated.

## 4. Wiring steps for the committing worker (not done in this check)

1. Add `tools/heromap/` to whatever import path `site/build_data.py`/`build_page.py` use
   (both already live under `site/`; a `sys.path` entry for the repo root, or a relative
   package import, whichever this repo's existing convention is — check how
   `tools/flowmap`/`tools/kg` are imported elsewhere first, e.g. `docs/FLOW_STALL_TYPOLOGY.md`
   §7 point 3 for the sibling flowmap module's own wiring note).
2. In `site/build_data.py`, after `sammakorn_chain` and `layer0_public` are computed, call
   `tools.heromap.sammakorn_map.render_sammakorn_hero_map(area, chain=sammakorn_chain,
   normal_levels=tools.heromap.sammakorn_map.load_normal_levels())` once per build and place
   the returned SVG string under a new `data.json` key (e.g. `hero_map_svg`) — OR call it
   directly from `build_page.py` at render time (either is fine; this check took no side on
   that, since it doesn't touch either file).
3. In `site/build_page.py`'s hero section (the same call site that currently prints the
   `raw/design/...png` reference art, or the top of `build_area_fragments()`/the hero
   template block), inject the SVG string, THEN separately call `layer0_caption_th(
   data["layer0_public"]["areas"]["sammakorn"])` and render that string as its own
   paragraph immediately below the map markup — never inside the SVG (project decision 1).
4. CSS: no new custom properties are needed — every colour in the SVG is a `var(--...)`
   token already declared in `site/index.template.html`'s `:root`/dark-mode blocks (`--ok`,
   `--warning-text`, `--alert`, `--alert-strong`, `--neutral-text`, `--surface`,
   `--surface-2`, `--border`, `--text`, `--text-muted`, `--accent-2`, `--bg`). Optionally add
   a `.hero-map-wrap { max-width: 360px; margin: 0 auto; }` wrapper class so the SVG's own
   `width="100%"` scales down cleanly inside the existing hero card.
5. **Maker ≠ checker** (per `AGENTS.md` §2): before this
   goes live, an independent reviewer (not the author, not the committer) must re-run the
   §5 checklist below against the actual wired page, not just this prototype's standalone
   SVG — a live page can introduce new collisions the standalone prototype didn't have
   (e.g. the existing hero card's own padding/font-size overrides).
6. Confirm the pump code↔position mismatch in §3 with the founder/data owner before ever
   printing an `ST.SPS.0x` code on the public page next to a position claim.

## 5. Independent design check (against the `floodconnect-design` skill's 12 rules)

Checked directly against the live-data prototype (`site/dist/prototype/hero_map_live.html`,
`sammakorn_hero_map_live.svg`) and the synthetic one
(`hero_map_synthetic_normal.html`). Each item tagged genuine defect / accepted trade-off
(INSTINCT) / pass.

1. **Status word first, no disclaimer above it** — N/A to this component as scoped: per
   project decision 1, this map is now explicitly NOT where the top-line hazard/status word
   lives (that's the existing hero card above it); the map's own first visible content is
   the north-band label + two chips, which is correct for what THIS component's job is.
   **Accepted trade-off**, not a violation of rule 1's intent (the surrounding page still
   needs its top-line status word above everything, unchanged, outside this component's
   scope).
2. **Colour never carries severity alone** — **PASS**. Every chip/pond/pump has a status
   WORD (ปกติ/สูงกว่าปกติ/เตือน/วิกฤต/ล้นตลิ่ง/ยังไม่มีเกณฑ์ปกติ/ไม่มีเครื่องวัด/ไม่มีข้อมูล/
   ขัดข้อง) next to its colour, not colour alone.
3. **Calm palette, alarm colour only as accents** — **PASS**. `--alert`/`--alert-strong`
   are used only as a 2px chip stroke + a 4px top accent stripe, never a full-bleed fill;
   matches the same convention `build_canal_graph_svg()` already uses elsewhere on this page.
4. **Every tier resolves to a number** — **PASS** for every bound station; **genuine gap**
   for the two truly-ungauged canals (คลองสะพานสูง, คลองวังใหญ่บน) and for stations without a
   `normal_level_m` — those show the tier WORD but the "what number would count as ปกติ" is
   not shown on the map (it exists in `sources/canal_normal_levels.yaml` for the stations
   that have one, but this map doesn't print the threshold value itself, only the tier
   name). **Recorded as a follow-up**, not fixed in this check — the founder's own rule 1
   ("only picture + numbers, no analysis") argues against adding more explanatory text here
   anyway; a future per-station detail view is the more likely right place for the
   threshold number itself.
5. **Calm case stated explicitly, never blank** — **PASS**. Every unbound point renders an
   explicit grey word ("ไม่มีเครื่องวัด" / "ยังไม่มีเกณฑ์ปกติ" / "ไม่มีข้อมูล") rather than an
   empty cell.
6. **Timestamp travels with every number** — **genuine gap, not fixed in this check**. The
   prototype's `_chip`/`_pump_icon` do not render a per-point "ค่าเมื่อ HH:MM" timestamp (the
   task's own instruction listed "value + unit, status pill, trend arrow, **time**" as the
   per-point content). This was DESCOPED under project decision 1 ("only picture + numbers")
   arriving mid-task, which reads as being in tension with the original per-point spec —
   flagged here rather than silently dropped. If the founder wants the time back on the
   map itself (not just the surrounding page's existing staleness handling), add one more
   `_fit_text` line per chip reading `obs_time_label()`-equivalent output; the data already
   carries `observed_at` on every station.
7. **Server-rendered, no client JS dependency** — **PASS**. `render_sammakorn_hero_map()` is
   a pure function returning a plain inline `<svg>` string with zero `<script>`/JS.
8. **"What to do" near the status it responds to** — **N/A by project decision 1**: this
   component intentionally carries no guidance text at all now; guidance lives in the
   existing hero card's own advice section, unchanged.
9. **Typography floor (skill's general rule: 16px min, 18–20px preferred)** — **genuine,
   documented deviation, narrowed in revision 2**: every text node in the ring layout is now
   ≥12px (`TEXT_FLOOR = 12` in `sammakorn_map.py`, enforced by
   `test_no_font_size_below_12px`) — the first draft's 10.5px pump/sub-label lines were
   raised to 12px per the founder's explicit revision instruction, with text shortened/
   compressed via `_fit_text`'s `textLength` mechanism rather than shrunk further. 12–15px
   is still below the skill's GENERAL 16px body-text floor — the same accepted trade-off
   `site/build_page.py`'s own `build_canal_graph_svg()` component already ships today (its
   `.cg-node-label` is 12px) — a dense multi-point diagram at 360px width cannot fit real
   per-point numbers at 16px+ without either a much taller SVG or fewer points shown per
   side. The task's own explicit instruction ("≥12px for all value/label text") is now met
   everywhere, closing the founder-sign-off flag the first draft raised on this item.
10. **48×48px tap targets** — **N/A**: nothing in the returned SVG is interactive (no
    `<a>`/button/pointer handler) — it is a static status graphic, same as the existing
    `canal-graph-svg`. If the committer wraps it in a `<details>` toggle, that toggle
    element already meets 48px elsewhere in this template's existing pattern.
11. **Tables collapse to single-column cards under ~480px** — **N/A**: this component has
    no `<table>`; it's already laid out for a 360px viewBox from the start.
12. **One file, minimal external requests** — **PASS**. No external font/script/stylesheet
    request; the SVG is inline, referencing only the page's own existing `var(--...)` tokens.

**Anti-pattern scan**: no full-bleed alarm-red background (checked: `--alert`/
`--alert-strong` only ever appear as `stroke`/small `fill` accents); no emoji anywhere (a
small inline pump glyph + text-anchor circles only); not "cards everywhere" run amok — chips
are used because each one IS a genuinely separate measured point, matching the skill's own
carve-out; no stock gradient/shield art; no ellipsis-arrow copy (there is no copy at all
inside the SVG, per project decision 1).

## 6. Tests (`tests/test_heromap.py`, 28 cases, all passing at hand-off)

Covers: `classify_tier()`'s breach-first/no-baseline-stays-grey logic (the founder-ruling-2
behaviour, both directions); `worst_tier()`; rendering with a completely empty area (no
crash, nothing green); a missing pump showing `0/0` rather than an invented count; the
north-band worst-of-two-stations + flagged-outlier behaviour on realistic fixture data; the
pond bound from a `sammakorn_chain` node; pump partial/fault/ok state counting against a
4-pump fixture; a scan across rendered SVGs for the four AGENTS.md-forbidden public-page
words, for a local path or AI-vendor name, and for any text node long enough to look like a
sentence rather than a label (project decision 1's "no analysis" check, approximated); a
12px font-size floor check; `layer0_caption_th()`'s "never baked into the SVG, never
hardcoded, None when data is absent" behaviour; and (revision 2) all four band labels
present, the village name present, `_edge_arrow_symbol()`'s 4-case mapping (`→`/`←`/`≈`/`?`)
and that no OTHER arrow-like glyph ever appears, all four corner pumps rendering even when
unbound, and the `VIEW_W`/`VIEW_H` bounds (360×≤520).

`python3 -m pytest tests/test_heromap.py -q` → **28 passed** (run 2026-09-27, this check,
after revision 2). This check did not re-run the repo's full `tests/` suite (500+ cases as of
`AGENTS.md`'s own snapshot) — per `AGENTS.md` §3 / the "no repeated full-arc audits"
convention, that full run belongs to whoever commits this, once, right before merge; this
worker never touched an existing tracked file so there is nothing else in the suite this
change could have broken.

**Coverage gap, stated honestly**: neither of the two real layout bugs found while building
revision 2 (§ "Revision 2" above — corner-icon bleed, village-block z-order clipping) was
caught by any assertion in this test file; both are geometric/paint-order defects that a
string-presence test cannot see. They were only caught by actually rendering the SVG in a
browser and looking at it. No new geometric/visual-regression test was added in the time
available to close this gap — recording it here rather than implying the test suite would
catch a similar bug next time.

## 7. Prototype files (gitignored, `site/dist/` — never committed)

- `site/dist/prototype/sammakorn_hero_map_live.svg` — rendered from the actual
  `site/dist/data.json` on disk at hand-off time.
- `site/dist/prototype/sammakorn_hero_map_synthetic_normal.svg` — a synthetic "everything at
  or below its own normal level, all 4 pump stations running full" case, built to exercise
  the all-green path. Note: WL.HMK.01/WL.KJG.01 still render grey even in this "all normal"
  synthetic case, because neither has a `normal_level_m` on record — that is project decision
  2 working as intended (no baseline ⇒ never green), not a bug in the synthetic fixture.
- `hero_map_live.html` / `hero_map_synthetic_normal.html` — minimal standalone viewer pages
  (own `<!doctype html>`, a light+dark token stylesheet copied from
  `site/index.template.html`'s `:root` blocks, and the caption rendered below the map) for
  visually checking the two SVGs outside the real page template.
- `sammakorn_hero_map_live_preview.png` / `..._synthetic_normal_preview.png` — the FIRST
  draft's PNG renders via `cairosvg`. **Superseded, kept only for the record**: the
  `cairosvg` renderer available in this environment has no Thai-script font installed, so
  Thai text showed as tofu-boxes/hex-glyphs in these two PNGs only — a limitation of that
  one local raster tool, not of the SVG markup itself (the raw SVG text/attribute values are
  correct UTF-8 Thai strings throughout). Do not judge the design against these two files.
- **`site/dist/prototype/sammakorn_hero_map_live_playwright.png`** and
  **`site/dist/prototype/sammakorn_hero_map_synthetic_normal_playwright.png`** — the
  authoritative visual check for revision 2, rendered via `playwright.sync_api` +
  headless Chromium (`chromium.launch(args=["--no-sandbox", "--disable-gpu",
  "--disable-dev-shm-usage"])` — the default launch failed with a screenshot protocol error
  in this sandboxed environment; these three args fixed it) against
  `hero_map_live.html`/`hero_map_synthetic_normal.html` at a 390px-wide viewport. This
  environment has `Noto Sans Thai`/`Noto Serif Thai` installed system-wide
  (`fc-list | grep -i thai`), so these two PNGs show real, correctly-shaped Thai text — use
  these two, not the `cairosvg` ones, to judge the design.
