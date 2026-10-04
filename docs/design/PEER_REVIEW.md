# FloodConnect — Peer Visual Review

**Reviewer role:** independent peer review, as a senior product designer from a weather or transit app. I did not build the page, and I did not edit any page file.
**Reviewed:** local copy `artifact/floodconnect.html` (119,853 bytes, build stamp "อัปเดต 13:36"), served as `design/wrapped.html` at `127.0.0.1:8123` in headless Chromium.
**Benchmark used:** `design/BENCHMARK.md` (its principles P1–P12). Benchmark statements about outside products are **RELAYED** from that file. I did not re-fetch them. External fetches in this review: 0.
**Tags:** `VERIFIED` = I saw it in a screenshot or read it from the DOM or source. `MEASURED` = I computed it with a script or DOM query. `INSTINCT` = design judgement, not a checked fact.

## Screenshots (all in `design/shots/`)

| File | What |
|---|---|
| `phone-light-fold.png` | 390×844, light theme, first screen |
| `phone-light-full.png` | 390 wide, light theme, full page (4,873 px tall) |
| `phone-light-zones-crop.png` | the zone cards, trend cards and grey bucket |
| `phone-light-pumptable-crop.png` | the pump table and its broken caption |
| `phone-dark-fold.png` | 390×844, dark theme, first screen |
| `phone-dark-full.png` | dark theme, full page |
| `phone-dark-pumptable-crop.png` | dark theme, pump table |
| `1024-light-full.png` | 1024 wide, light theme, full page |
| `1024-light-mid-crop.png` | 1024 wide, zones → trend → pump table |

## Verdict: **SHIP_WITH_FIXES**

The hero concept is right. The verdict word **"น้ำยังขึ้น"** is 43 px (`clamp(2.4rem,6vw,3rem)`, MEASURED) in white on deep navy, and a 70-year-old can read it in under 3 seconds (VERIFIED, `phone-light-fold.png`). Other good points:
- The content is server-rendered, so the zone groups are in the static HTML (VERIFIED).
- The base text is 18 px (MEASURED).
- There is no horizontal scroll at 390 px (MEASURED).
- The page weighs about 23 KB gzipped (MEASURED, `gzip -c | wc -c` = 23,349 B).

A redesign is not needed. What stops it feeling world-class is a set of fixes at the CSS and HTML level:
- **One visible layout bug:** the pump-table caption.
- **One dark-mode inversion:** the hero becomes the brightest thing on the screen.
- **Alarm styling on metadata:** the stale-data ribbon is solid red.
- **The first screen is spent on a disclaimer.**
- **Icons are emoji-based.** This is the main "generated" tell.

## Top 10 issues, ordered by impact

### 1. The pump-table caption collapses to one word per line on phone (VERIFIED + MEASURED)
- **Where:** `phone-light-pumptable-crop.png` and `phone-dark-pumptable-crop.png`.
- **Problem:** The caption "ระดับน้ำและปั๊มเดิน/ปั๊มเสีย 4 สถานีของหมู่บ้าน" renders as a 69 px-wide column of 9 lines. The DOM query gave caption width 69.19 px, `display: table-caption` inside a parent set to `display:block`. The mobile rule turns `table` into `block`, and the caption then shrink-wraps.
- **Why it matters:** It is the most "broken-looking" thing on the page, and it sits in the middle of the scroll.
- **Fix:** In `@media (max-width:480px)`, add `.tablewrap caption{display:block;width:100%;padding:0 0 8px}`. Or delete the caption on mobile, since `.table-lead` ("สถานีสูบในหมู่บ้าน 2 จาก 4 แห่งขัดข้อง") already says it. The same applies to the canal tables inside `<details>`.

### 2. In dark mode the hero turns into a bright sky-blue slab (VERIFIED)
- **Where:** `phone-dark-fold.png`.
- **Problem:** Dark mode sets `--accent: #5AA9D6` with `--on-accent: #08141B`. The banner reuses `--accent`, so it becomes a full-bleed light-blue panel with dark text, the brightest area on a dark phone at night. The white chip borders `rgba(255,255,255,.4)` and the `.watch` tint wash out on it.
- **Why it matters:** It breaks "calm, not alarming" (P3) for anyone checking at 2 a.m., which is when flood checks happen (INSTINCT).
- **Fix:** Add dedicated hero tokens instead of reusing `--accent`:
  ```css
  :root{--hero-bg:#0B3C5D;--on-hero:#FFFFFF}
  /* dark (both the media-query block and [data-theme=dark]) */
  --hero-bg:#10344A; --on-hero:#E9F1F3;
  .banner{background:var(--hero-bg);color:var(--on-hero)}
  ```
  Keep the chip and `.watch` rgba-white overlays as they are, because they then sit on a dark surface again.

### 3. The disclaimer box takes the top of the first screen, above the verdict (VERIFIED)
- **Where:** `phone-light-fold.png`.
- **Problem:** The `.humble-box` runs 4 lines (about 125 px) and pushes the hero to y≈228. The verdict word starts at y≈290.
- **Why it matters:** It contradicts P1 (status first). BENCHMARK.md relays that the UK flood service opens with the status sentence.
- **Fix:** Delete `.humble-box` from the top. The identical sentence is already in the footer (VERIFIED, bottom of `phone-light-full.png`). In the banner's `.note` line, add one muted clause: `ดูจากเครื่องวัดของ กทม. เมื่อ 12:00 · รวบรวมโดยประชาชน ไม่ใช่ประกาศทางการ`. This keeps the honesty requirement at the point of the claim and gives back about 140 px.

### 4. The stale-data ribbon is the loudest element after the hero, and it only describes metadata (VERIFIED)
- **Where:** `phone-light-fold.png`, `1024-light-full.png`.
- **Problem:** `.stale-ribbon` is solid `--alert` red with white bold text: "ข้อมูลบางส่วนเก่า — ดูเวลาท้ายแต่ละบรรทัด". The page's only full-red block is therefore about data age, not flood danger. It also looks like a second headline competing with "น้ำยังขึ้น".
- **Fix:** Make it a quiet caution pill, keeping the age logic as it is:
  ```css
  .stale-ribbon{background:transparent;color:var(--warning-text);border:1.5px solid currentColor;border-radius:999px;font-weight:600;padding:4px 12px}
  ```
  Prefix it with a clock glyph, and move it inside the banner directly under `.note`, so the data age travels with the claim (P6). Reserve solid red for the "น้ำเข้าบ้านแล้ว" tier only (P3).

### 5. Emoji used as the severity icon system (VERIFIED)
- **Where:** `phone-light-zones-crop.png`, `1024-light-mid-crop.png`.
- **Problem:** The page uses 📍 🔎 🔴 🟠 🟡 ⚪ 🟢 as the tier markers and as hero decoration.
- **Why it matters:**
  - Emoji render differently on Android, iOS, LINE's in-app browser and Windows. That makes them inconsistent in size, weight and colour (INSTINCT, but well known).
  - They are the single strongest "AI-generated page" tell here (INSTINCT).
  - On the grey bucket they double up with the CSS swatch (see #6).
- **Fix:** Replace them with one 14 px inline-SVG dot component that uses the same token as the card stripe:
  ```html
  <svg class="dot" viewBox="0 0 10 10" aria-hidden="true"><circle cx="5" cy="5" r="5" fill="currentColor"/></svg>
  ```
  Use `.dot{width:.8em;height:.8em;vertical-align:-.05em;margin-right:.35em}` with `class="label-red"` and so on for the colour. Drop 📍 and 🔎 entirely. The place name and "ต้องเฝ้าระวัง:" already carry the meaning.

### 6. Tier colours are inconsistent between stripe, emoji and meaning (VERIFIED)
- **Where:** `phone-light-zones-crop.png`, `1024-light-mid-crop.png`.
- **Problem:**
  - The "ถนนท่วม" tier has a **teal** stripe (`.stripe-yellow{background:var(--accent-2)}`) next to a **yellow** 🟡.
  - The grey bucket summary shows a grey CSS square **and** ⚪, two icons for one state.
  - Teal is also the brand's second accent, used for the `+` disclosure glyph. So "road flooded" and "tap to expand" share a colour.
- **Fix:**
  - Give the tier ladder its own 4 tokens and use them for the stripe, dot and label alike, never the brand accents. For light: `--tier-3:#C0392B; --tier-2:#D98A1F; --tier-1:#C9A227` (text variant `#7A5F00`), `--tier-0:#8A9AA0`. For dark: `#FF7A68 / #F5BB4E / #E6C95A / #9AACB2`.
  - Remove the inline-styled `<span class="stripe stripe-grey" style="width:1em;...">` from the grey `<summary>`, or remove the ⚪, so only one icon remains.
  - Run a contrast check on `--tier-1` text before shipping.

### 7. Pump cards on phone are tall, cramped key–value grids that break Thai names mid-word (VERIFIED)
- **Where:** `phone-light-pumptable-crop.png`.
- **Problem:**
  - The label column is fixed at `flex:0 0 42%`, which leaves about 150 px for values. "บึงรับน้ำสัมมากร 4" wraps as "สัมมา / กร", which is not a dictionary break, so ICU splits it.
  - The station code "ST.SPS.02" floats as a third column.
  - "ปั๊มเดิน 0/2" next to "สถานะ ปกติ" reads as a contradiction to a lay reader (INSTINCT; it may be correct data).
  - The 4 cards × about 230 px make roughly 950 px of scroll for 4 facts.
- **Fix:** Make it a compact status row per station. The first cell becomes the card title, and the rest become an inline meta line:
  ```css
  .tablewrap tbody td:first-child{display:block;font-weight:700;font-size:1.05rem;padding-bottom:2px}
  .tablewrap tbody td:first-child::before{display:none}
  .tablewrap tbody td::before{flex:0 0 7.5em;max-width:7.5em}
  ```
  - Wrap place names in `<span class="nw">` with `.nw{white-space:nowrap}`.
  - Move the code to a second muted line: `<small class="code">ST.SPS.02</small>`.
  - Put the status pill right-aligned on the title row.
  - Change the status copy to say why: "ปกติ (น้ำต่ำ ไม่ต้องเปิดปั๊ม)" instead of a bare "ปกติ".
  - Target: 4 stations in 1 screen or less.

### 8. The hotline is not tappable, and tel links are 26 px tall (VERIFIED + MEASURED)
- **Problem:**
  - "1555" is a `<span class="hotline num">` in the footer and in the collapsed help section. It is not a `tel:` link (VERIFIED, source lines 440/462).
  - The other phone links (`0 2722 2500`, `0 2374 0200`, `02 734 0000`) measure 91×26 px. The "ลิงก์ต้นทาง" links measure 76×34 px (MEASURED).
  - Both fall below the page's own 48 px rule (P9), for users with shaky hands.
- **Why it matters:** BENCHMARK.md relays that the UK flood service puts Floodline next to the status.
- **Fix:** Add one 48 px call button at the end of the banner:
  ```html
  <a class="callbtn" href="tel:1555">โทร 1555 แจ้งน้ำท่วม กทม.</a>
  ```
  ```css
  .callbtn{display:flex;align-items:center;justify-content:center;min-height:48px;border-radius:10px;background:var(--surface);color:var(--hero-bg);font-weight:700;text-decoration:none;margin-top:12px}
  ```
  Also give all `a[href^="tel:"]` and source links `display:inline-flex;min-height:44px;align-items:center;padding-inline:4px`.

### 9. The hero states the situation but not what to do now (VERIFIED)
- **Where:** `phone-light-fold.png`.
- **Problem:** The hero gives the word, a 4-line bold `.watch` paragraph (17.6 px, all bold), and 3 chips. The only reassurance or action line ("ยังไม่ต้องยกของเพิ่ม รอดูอีก 1 ชม.") sits at the bottom of the trend card, about 1,800 px down.
- **Why it matters:** An all-bold block reads as shouting and slows scanning (INSTINCT). BENCHMARK.md relays the FEMA and USWDS guidance: clear, immediate instruction.
- **Fix:**
  - Set `.banner .watch{font-weight:500}` and bold only the lead "ต้องเฝ้าระวัง: ช่วง 5 โมงเย็น–3 ทุ่ม" via `<strong>`.
  - Add one 20 px action line directly under the word: `<p class="now">ตอนนี้: ยังไม่ต้องยกของเพิ่ม · ดูอีกครั้ง 1 ชม.</p>`, generated from the same value as the trend card.
  - On phone, make the 3 chips a 3-up stat row (big number, small label) instead of 3 stacked pills:
    ```css
    .chips{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
    .chip b{display:block;font-size:1.4rem}
    ```
    For example: "2/4 ปั๊มเสีย" · "9/11 คลองเกินเส้น" · "197 มม. ฝน 24 ชม.".

### 10. Speed: render-blocking Google Fonts with 2 families and 6 weights (VERIFIED + MEASURED)
- **Problem:** The head loads `Noto Sans Thai:400;500;600;700` plus `Kanit:600;700` through a blocking `<link rel=stylesheet>`. `document.fonts` showed 8 loaded faces (MEASURED). `display=swap` is set, which is good, but the CSS request itself still blocks the first render. That costs a round trip on a congested flood-day 3G/4G link (P11). Kanit only styles the h1, the place name and the verdict word.
- **Fix:**
  - Drop Kanit and use Noto Sans Thai 700 for display.
  - Request only `wght@400;700`, since the 500 and 600 uses can become 400 and 700.
  - Load it non-blocking:
    ```html
    <link rel="preload" as="style" href="…&display=swap" onload="this.rel='stylesheet'">
    ```
    plus `<noscript>` for the plain link.
  - Keep the fallback stack (`Sarabun, system-ui…`). Thai system fonts exist on every target phone, so first paint is immediately readable.
- **Expected effect (INSTINCT):** one fewer blocking request and about 4 fewer font files.

## Lower-priority notes (not in the top 10)
- **1024 px:** the banner uses `margin-inline: calc(var(--gutter) * -1)`, so it overhangs the card column by 16 px on each side (VERIFIED, `1024-light-full.png`). Add `@media (min-width:600px){.banner{margin-inline:0;border-radius:12px}}`.
- **Section dividers:** there are 3 px `--border` rules above every h2 plus separate hr-like rules, which gives double lines between sections (VERIFIED). Use one 1 px rule or whitespace only (32 px rhythm).
- **Trend-card headers:** "อาจแย่ลงเมื่อ... → เตรียมรับมือ" uses an ellipsis-plus-arrow construction that reads like a template (INSTINCT). Try "ถ้าเกิดสิ่งเหล่านี้ ให้เตรียมรับมือ".
- **Sources footer:** it repeats "สำนักการระบายน้ำ กรุงเทพมหานคร" 4 times. Group it by agency with sub-bullets.
- **Favicon:** the only console error was a 404 on `/favicon.ico`, caused by the local wrapper and not the page (VERIFIED). The artifact host supplies an icon, so no action is needed.

## What to keep (do not regress)
- The verdict word as the visual hero: 43 px, display weight, on a calm navy (not red) banner in light mode. This matches P1 and P3 (VERIFIED).
- Colour and word always paired on tiers ("น้ำเข้าบ้านแล้ว (5 ซอย)", "ถนนท่วม (14 ซอย)"), and the count stated in every tier title (VERIFIED).
- The grey bucket is labelled "ยังไม่มีรายงาน (ไม่ได้แปลว่าปลอดภัย)", an explicit unknown rather than a false calm. This is excellent (P5).
- Each tier card ends with one short imperative prep line ("เตรียมกระสอบ · ย้ายรถเมื่อบึงล้น").
- 18 px base, rem-based type, A−/A+ controls at 48×48 px, and no horizontal scroll at 390 px (MEASURED).
- Server-rendered content with JS as enhancement only, and about 23 KB gzipped for the whole page including data (MEASURED).
- The stale-age logic itself. Only its styling changes (#4).
- Long secondary sections (canals, official forecast, exits, internet voices, help) collapsed into `<details>` with 48 px summaries. This keeps the phone scroll honest.
- The trend section's two-sided framing ("อาจแย่ลงเมื่อ / อาจดีขึ้นเมื่อ"), which is calm and non-fatalistic.
- The desktop layout, a single centred column of about 640 px. It is correct for this content, so do not add a sidebar.
