# FloodConnect — Design Benchmark & Principles

**ขอบเขต:** เอกสารนี้เป็นการรีวิว "หน้าตา" (design/UX) เท่านั้น — ไม่แตะไฟล์หน้าเว็บ (`floodconnect.html` / `index.html` / `build_page.py` เป็นของทีมอื่น). เขียนไว้ที่ `design/BENCHMARK.md` นี้ และสกัดเป็นแนวทางที่ใช้ซ้ำได้สำหรับงานถัดไป.

**Tag ที่ใช้:** `VERIFIED` = เปิดหน้าเว็บนั้นเองแล้วอ่านจริง (WebFetch) · `RELAYED` = จากผลค้นเว็บ/แหล่งรอง ไม่ได้เปิดต้นทางเอง (WebSearch) · `MEASURED` = คำนวณเอง (เช่น contrast ratio) · `INSTINCT` = ความเห็น/การตีความ ไม่ใช่ข้อเท็จจริงที่ตรวจแล้ว.

---

## สรุปภาษาไทย

**หน้า FloodConnect ปัจจุบัน (อ่านจาก `floodconnect.html` จริง — VERIFIED) แข็งแรงกว่าที่คาดในหลายจุดอยู่แล้ว:**
แบนเนอร์สถานะเป็นสิ่งแรกที่เห็น (แต่ก่อนหน้านั้นมีกล่อง "humble disclaimer" คั่นอยู่ — ดูข้อ 1 ด้านล่าง), มีปุ่ม A+/A− ปรับขนาดตัวอักษร, ปุ่ม/แถวแตะขั้นต่ำ 48px, รองรับ dark mode, ตารางพับเป็นการ์ดบนจอมือถือ, และมีระบบ "ข้อมูลเก่า" (stale pill) ที่ตรวจสอบอายุข้อมูลจริงตอนเปิดหน้า — ซึ่งเข้มงวดกว่าเว็บ/แอปเทียบเคียงส่วนใหญ่ที่ลองดู. สีของแบนเนอร์หลักเป็นน้ำเงินเข้ม (ไม่ใช่แดงเถือก) ตลอดเวลาแม้สถานการณ์แย่ — ตรงกับหลัก "สงบแต่จริงจัง" (calm not alarming) ของแนวทาง USWDS ที่เตือนว่าสีแดง/ส้มจัดจ้านทำให้คนตื่นตระหนกเกินจำเป็น.

**จุดที่ปรับได้ให้เร็วขึ้น/เป็นมืออาชีพขึ้น เทียบกับ 8 ผลิตภัณฑ์ตลาดเดียวกัน** (thaiwater.net, BMA DDS, Google weather alert, Apple Weather, Windy, Yahoo!防災速報, UK Environment Agency check-for-flooding, Taiwan CWA, บวก FEMA app และ USWDS pattern เป็นข้อมูลเสริม): กล่องคำเตือน/disclaimer ไม่ควรมาก่อนคำตอบหลัก (UK gov.uk ให้คำตอบสถานะเป็นประโยคแรกเสมอ แม้ตอนไม่มีอะไรเกิดขึ้น), ระดับสี/ความรุนแรงควรผูกกับตัวเลขเกณฑ์เสมอไม่ใช่แค่คำ (Taiwan CWA ใช้ mm/ชม.ชัดเจนทุกระดับ), และหน้าเว็บที่พึ่ง JavaScript/แผนที่หนักๆ (thaiwater.net, Windy) กลับอ่านเนื้อหาไม่ได้เลยถ้าไม่รัน JS เต็มรูปแบบ — ตรงข้ามกับแนวทางที่ FloodConnect ทำถูกอยู่แล้ว (เนื้อหาฝังในหน้า HTML ตั้งแต่ build ไม่ต้องรอ JS โหลดเสร็จ).

**สี (token) ปัจจุบันของหน้านี้ผ่านมาตรฐาน 4.5:1 ทุกคู่ที่ตรวจ** (คำนวณจริง — MEASURED, ดูตารางท้ายเอกสาร) ทั้งโหมดสว่างและมืด จึงไม่แนะนำให้เปลี่ยนจานสีทั้งชุด — ให้ "รักษาไว้" เป็นฐาน และใช้เป็น token suggestion ในสกิลต่อไป.

หลักการที่กลั่นได้ 12 ข้อ และ token suggestion อยู่ในภาษาอังกฤษด้านล่าง (เพื่อให้ตรงกับไฟล์สกิลที่จะเรียกใช้ซ้ำในงานเขียนโค้ด) — ไม่มีชื่อผู้ให้บริการ AI ใดๆ ปรากฏในเอกสารนี้หรือในสกิล ตามข้อกำหนด.

---

## Method (English)

Founder brief: *"world-class design that emphasises SPEED (instant comprehension, fast load, calm not alarming) yet professional, benchmarked against apps in the same market."*

Scope: page-design review of the FloodConnect artifact (local copy read directly — VERIFIED), benchmarked against products in the same market (public disaster/flood/weather/transit-status apps and pages). No page files were edited. WebFetch/WebSearch only, ≤25 fetches used (17 used: 11 WebSearch + 6 WebFetch). No screenshots taken (not needed per task).

## Reference products reviewed

| # | Product | Market | Access | Tag |
|---|---|---|---|---|
| 1 | thaiwater.net (สสน. / HII) — the source FloodConnect already cites | TH national water data portal | WebFetch (SPA — content not renderable without full JS) + WebSearch | RELAYED / VERIFIED-that-it-didn't-render |
| 2 | BMA DDS (dds.bangkok.go.th) — the source FloodConnect already cites for daily reports | BKK municipal drainage bureau | WebFetch | VERIFIED (partial — landing page is a portal gate) |
| 3 | Google Search weather/alert card | Global consumer weather | WebSearch | RELAYED |
| 4 | Apple Weather severe-weather banner | Global consumer weather (iOS) | WebSearch | RELAYED |
| 5 | Windy.com | Global consumer weather/wind map | WebFetch + WebSearch | RELAYED |
| 6 | Yahoo! Japan 防災速報 (disaster alert) | JP consumer disaster alert | WebFetch (color-system page) + WebSearch | VERIFIED (levels) / OPEN (exact hex not published) |
| 7 | UK Environment Agency — check-for-flooding.service.gov.uk | UK govt flood warning | WebFetch (2 pages) | VERIFIED |
| 8 | Taiwan CWA (Central Weather Administration) heavy-rain warning page | TW govt weather warning | WebFetch | VERIFIED |
| + | FEMA app (US) — supporting reference | US govt emergency app | WebSearch | RELAYED |
| + | USWDS Alert / Site-alert design pattern — supporting reference (design-system doc, not a product, but directly on-topic: "calm not alarming" governance) | US govt design system | WebSearch | RELAYED |

Note on NHK: WebSearch for the specific NHK disaster page returned no independent NHK-specific results beyond the Yahoo!防災速報 material (both queried together); NHK's own page design is therefore **OPEN** — not claimed here, only Yahoo!'s documented color-system page is used.

## Per-product findings

**1. thaiwater.net / ThaiWater** (RELAYED for the described color system; VERIFIED that the page did not render as text — it is a JS-driven SPA dashboard). Color system: green/orange/red risk tiers on rainfall/water-level/reservoir data (RELAYED, exact hex not published). Speed practice: **no readable no-JS fallback** — WebFetch returned only page title, meaning a slow/blocked connection likely shows a blank shell. This is the same upstream FloodConnect already cites as a source, so FloodConnect's own static rendering is a deliberate improvement over its own source's delivery method.

**2. BMA DDS (dds.bangkok.go.th)** (VERIFIED, partial). First thing shown is not status data — it's a bureau-name banner + an "เข้าสู่เว็บไซต์" (Enter Website) gate button. Hero pattern: **portal, not status** — an extra click before any flood number. FloodConnect already avoids this by skipping straight to a status word.

**3. Google weather alert card** (RELAYED). Hero pattern: a short colored hazard name (e.g. "Excessive Heat Warning") in red, with an "ALERT" badge + icon near the top; issuing agency (National Weather Service) and issue time shown at the bottom, after the headline, not before it.

**4. Apple Weather severe-weather banner** (RELAYED). Hero pattern: colored banner near the top of the forecast screen, hazard title only, tap-through for affected area / start–end time / hazards / safety guidance. Multiple concurrent alerts stack as separate cards rather than merging into one paragraph. Source agency always shown.

**5. Windy.com** (RELAYED + one direct fetch). Primary experience is a heavy interactive map; WebFetch could not confirm any lightweight/no-JS path. Treated here as a **counter-example**: powerful for exploration, but not optimized for "instant comprehension in under a second" — the opposite end of the speed spectrum from what the founder brief asks for.

**6. Yahoo! Japan 防災速報** (VERIFIED for the level structure). Every hazard type has its own named tier ladder (e.g. river flooding has 3 numbered levels, heat stress has 4 named levels, tsunami has 3 named tiers) — color is layered *per hazard category*, never a single universal red/yellow/green across all hazards. Exact hex values are **OPEN** (Yahoo's own page describes color-coding but does not publish the palette).

**7. UK Environment Agency — check-for-flooding.service.gov.uk** (VERIFIED, 2 pages fetched directly). Hero pattern: when nothing is happening, the page still states it explicitly — **"No flood alerts or warnings"**, 4 words, as a heading — rather than an empty page or a generic disclaimer. Severity ladder, always color **and** words paired: Flood Alert (yellow — "flooding is possible, be prepared"), Flood Warning (amber — "flooding is expected, immediate action required"), Severe Flood Warning (red — "danger to life, you must act now"). "What to do" is *not* inline on the alert page — it links out to separate step-by-step guidance pages. Floodline phone number is prominently placed near the status, not buried in a footer.

**8. Taiwan CWA heavy-rain warning page** (VERIFIED, direct fetch). Severity is defined by an exact rainfall threshold at every tier, not just an adjective: Heavy Rain (>80 mm/24h or >40 mm/h) → Extremely Heavy Rain (>200 mm/24h or >100 mm/3h) → Torrential Rain (>350 mm/24h or >200 mm/3h) → Extremely Torrential Rain (>500 mm/24h). Page order: warning + issue time first, then affected-area tabs, then a map, then technical definitions **last** — the actionable summary always comes before the map/technical detail, never after.

**+ FEMA app** (RELAYED). Explicit design goal quoted in a secondary source: *"users need clear, immediate instruction: where to go, what to do, and whether the warning applies to your neighborhood."* Alerts are scoped to the user's own location, not a whole city/region.

**+ USWDS Alert / Site-alert pattern** (RELAYED, design-system documentation, included because it is directly on-topic guidance rather than a product). Two points map straight onto the founder's brief: (a) write alert text in **plain, concise, human-readable language**, telling the user exactly what to do; (b) **"avoid overwhelming use of color... bright red/orange can produce strong negative emotional reactions such as fear or panic"** — i.e. "calm not alarming" is itself a named, government-grade design requirement, not just a nice-to-have.

**+ Accessible typography for older readers** (RELAYED, multiple accessibility references, cross-checked against 3+ independent sources so treated as reasonably solid even though not a single authoritative citation): 16px is the accepted floor for body text; 18–20px is recommended for content-heavy pages read by older audiences; 1.5–1.75 line-height; text must remain usable at 200% browser zoom; normal text needs ≥4.5:1 contrast, large text ≥3:1.

## FloodConnect's current state — what already matches world-class practice (VERIFIED by reading the file)

- Status word + place name is the visual hero of the page (`banner-word`, `banner-place`), matching Apple/Google's "hazard name first" pattern.
- Color and words are always paired (emoji + Thai label on every tier chip and pill) — never color alone. Matches Yahoo!'s per-category labeling and general a11y practice.
- Banner background stays a calm dark blue (`--accent`) regardless of severity, rather than switching to alarm-red — this is *already* the USWDS "avoid overwhelming red/orange" guidance in practice, done correctly.
- 48px minimum tap targets on buttons and summary rows; A+/A− font-size control that scales the real root font (rem-based) — matches the accessible-typography findings above.
- Content is inline in the built HTML (server/build-time rendered), with JS only for progressive enhancements (view-time relative ages, font scaling) — this is the opposite of thaiwater.net's and Windy's JS-dependent delivery, and is a genuine speed advantage already in place.
- A stale-data pill computed against the *viewer's* clock at view time, not build time — stricter than every benchmarked government page reviewed here, none of which appeared to re-check staleness live in the fetched excerpts.
- Mobile table→card fallback with `data-label` per cell — avoids horizontal scrolling on phones, which none of the benchmarked sources documented explicitly.

## Where it diverges from the benchmark pattern (findings, not yet fixed — page files not touched)

1. **Hero not truly first.** The `humble-box` disclaimer paragraph sits between the page title and the status banner. Every benchmarked hero (UK gov.uk's "No flood alerts or warnings", Apple's colored banner, Google's alert card) puts the status/hazard-name line before any caveat text. INSTINCT: moving the disclaimer to below the banner (or into the footer, where the fuller version already lives) would shave a beat off comprehension time without losing the epistemic-honesty requirement.
2. **No single quantified threshold line in the hero.** Taiwan CWA and the canal tables both state an exact number (mm/h, meters) at the point of the claim. The banner's `banner-word` is a qualitative phrase ("น้ำยังขึ้น") — the quantified numbers appear later in chips/tables. INSTINCT, low priority: this is a defensible trade-off (plain-language-first, per USWDS) rather than a clear defect.
3. **"What to do" is distributed across multiple `details` blocks** rather than one linked/highlighted action list near the top the way FEMA's stated design goal and UK gov.uk's link-out pattern do. The `prepline` inside each zone tier card is good, but a reader whose own ซอย is in the "ยังไม่มีรายงาน" (grey, 77 ซอย) bucket has to open a `<details>` to find out there's no separate "what to do if unknown" guidance visible without expanding.

## Contrast measurements (MEASURED — computed directly, WCAG relative-luminance formula)

| Pair | Ratio | Passes 4.5:1 |
|---|---|---|
| light text / bg | 15.47:1 | yes |
| light text-muted / bg | 6.23:1 | yes |
| light alert / surface | 5.44:1 | yes |
| light warning-text / surface | 5.38:1 | yes |
| light ok / surface | 5.13:1 | yes |
| light on-accent / accent (banner) | 11.55:1 | yes |
| light accent-2 / surface | 4.98:1 | yes |
| dark text / bg | 16.01:1 | yes |
| dark text-muted / bg | 8.73:1 | yes |
| dark alert / bg | 7.19:1 | yes |
| dark warning-text / bg | 10.56:1 | yes |
| dark ok / bg | 9.51:1 | yes |
| dark on-accent / accent (banner, dark) | 7.18:1 | yes |

Conclusion: the existing FloodConnect token set already clears 4.5:1 everywhere checked, in both themes. No palette replacement is warranted; the token suggestion below **restates the existing palette** as the reusable design-system baseline rather than proposing a new one.

## 12 distilled principles for FloodConnect-family pages

1. Status/hazard word is the first thing a reader sees — no disclaimer, logo, or navigation may sit above it.
2. Pair color with a word every time; never let color alone carry the severity meaning (screen readers, color-blind readers, low-contrast phone screens in sunlight).
3. Keep the "calm" palette even at the worst severity — reserve pure alarm-red for small accents (stripes, pills, one ribbon), never as a full-bleed background; USWDS names this explicitly as preventing panic-driven bad decisions.
4. Every severity tier needs a named, quantified threshold behind it somewhere on the page (mm/h, meters, % of stations) — plain language in the hero, the number one tap away.
5. State the calm case explicitly too ("no active warning" / "ยังไม่มีรายงาน") — never leave a state blank; a blank state reads as "no data" when it should read as "confirmed calm."
6. Timestamp and source agency travel with every number, not just once in a footer; compute "how old is this" against the viewer's own clock at view time, not the build time.
7. Render content at build/server time and ship it inline; use JS only for progressive enhancement (font size, live age). A page that only works after a heavy JS bundle finishes is a speed and resilience failure, not a feature.
8. "What to do" is short, imperative, and near the status it responds to — not several taps away in a generic details block; the reader whose own street has no report yet still needs one visible line of guidance.
9. 48px minimum tap targets, 16px absolute floor for body text with an easy way to go to 18–20px, 1.5+ line-height — non-negotiable for elderly/low-vision readers, who are named stakeholders here.
10. Keep tables collapsible to labeled single-column cards below ~480px; never force horizontal scrolling on a phone.
11. One page load, one file, minimal external requests (fonts only) — every added network call is a chance to be the one thing that fails on a congested flood-day mobile network.
12. Never let a stale reading impersonate a fresh one — a status pill's color must depend on the reading's age as well as its value, exactly as FloodConnect's own `statusPillAged` already does; keep this pattern for any new panel.

## Token suggestion (restating the current, already-passing palette)

Palette (6 hex, light mode base + semantic):
- `--bg` `#F5F7F8` (page background)
- `--surface` `#FFFFFF` (cards)
- `--text` `#10202B` (body text — 15.47:1 on bg)
- `--accent` `#0B3C5D` (calm banner / brand — 11.55:1 for white text on it)
- `--alert` `#C0392B` (critical stripe/pill only, never full-bleed — 5.44:1 on white)
- `--ok` `#2E7D32` (normal/reassurance — 5.13:1 on white)

Dark-mode equivalents already defined and MEASURED ≥7:1 across the board (`#0A161D` bg / `#E9F1F3` text / `#5AA9D6` accent / `#FF7A68` alert / `#74CE82` ok) — keep as-is.

Type scale: 1.125rem (18px) body floor, 1.6 line-height; h1 ~1.6rem/700; h2 ~1.2rem/700; small/meta text 1rem floor (never below 16px, matching the accessible-typography findings above) — this already matches the current stylesheet; no change needed.

Spacing rhythm: 16px gutter, 8/10/12/14/16/20px internal paddings already in use — keep the existing 4–8px step scale rather than introducing a new one.

Tap sizes: 48×48px minimum for any interactive control (already implemented for the A+/A− buttons and `<summary>` rows) — extend the same 48px floor to any new interactive element (e.g. a future "call hotline" button).
