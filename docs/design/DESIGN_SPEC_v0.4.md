# FloodConnect — Design Spec v0.4 (fixer-ready change list)

**Do not touch page files from this document — it is instructions for the worker who owns
`artifact/floodconnect.html` / `build_page.py`, written by an independent design-review task.**
Source: `PEER_REVIEW.md` (peer visual review, SHIP_WITH_FIXES) + `BENCHMARK.md` (P1–P12) +
the project's design-token baseline. All items are CSS/markup-order
only — no content redesign, no new sections. Apply in this order (impact-ranked); each is
independent and reversible. Evidence tags per item follow PEER_REVIEW.md's own tagging
(VERIFIED = seen in DOM/screenshot, MEASURED = computed, INSTINCT = judgement call, RELAYED =
from BENCHMARK.md, not re-checked here).

1. **Pump-table caption breaks to 1 word/line on phone** (VERIFIED+MEASURED, caption width 69px).
   Add inside the existing `@media (max-width:480px)` block:
   `.tablewrap caption{display:block;width:100%;padding:0 0 8px}` — same rule for canal tables in `<details>`.

2. **Dark-mode hero becomes the brightest element on screen** (VERIFIED — reuses `--accent`).
   Add hero-only tokens: light `--hero-bg:#0B3C5D;--on-hero:#FFFFFF`, dark `--hero-bg:#10344A;--on-hero:#E9F1F3`.
   Repoint `.banner{background:var(--hero-bg);color:var(--on-hero)}`; leave chip/`.watch` rgba-white overlays as-is.

3. **Disclaimer sits above the verdict word, ~140px of the first screen** (VERIFIED, contradicts P1).
   Delete `.humble-box` from the top; fold its sentence into the banner `.note` as a muted clause:
   "ดูจากเครื่องวัดของ กทม. เมื่อ 12:00 · รวบรวมโดยประชาชน ไม่ใช่ประกาศทางการ".

4. **Stale-data ribbon is solid alarm-red — the loudest non-hero element, but it's only metadata** (VERIFIED, breaks P3).
   `.stale-ribbon{background:transparent;color:var(--warning-text);border:1.5px solid currentColor;border-radius:999px;font-weight:600;padding:4px 12px}`.
   Move its markup inside the banner, directly under `.note`, so age travels with the claim (P6).

5. **Emoji (📍🔎🔴🟠🟡⚪🟢) are the severity icon system — the strongest "generated" tell** (INSTINCT+VERIFIED).
   Replace with one inline-SVG dot: `<svg class="dot" viewBox="0 0 10 10" aria-hidden="true"><circle cx="5" cy="5" r="5" fill="currentColor"/></svg>`.
   `.dot{width:.8em;height:.8em;vertical-align:-.05em;margin-right:.35em}`, coloured via the existing `.label-red/.label-orange/…` classes; drop 📍/🔎 entirely.

6. **Tier colour is inconsistent across stripe/emoji/meaning** (VERIFIED — e.g. teal stripe next to a yellow 🟡).
   Add dedicated tier tokens, used only for stripe+dot+label (never brand `--accent`/`--accent-2`):
   light `--tier-3:#C0392B;--tier-2:#D98A1F;--tier-1:#C9A227(text #7A5F00);--tier-0:#8A9AA0`; dark `#FF7A68/#F5BB4E/#E6C95A/#9AACB2`. Remove the duplicate grey-square+⚪ on the grey `<summary>` (keep one icon). MEASURE contrast on `--tier-1` text before shipping.

7. **Pump cards are tall, cramped key–value grids; Thai names break mid-word; ~950px scroll for 4 facts** (VERIFIED).
   `.tablewrap tbody td:first-child{display:block;font-weight:700;font-size:1.05rem;padding-bottom:2px}`; hide its `::before` label.
   Move station code to `<small class="code">ST.SPS.02</small>`; wrap place names in `.nw{white-space:nowrap}`; right-align the status pill on the title row.

8. **Hotline "1555" is not tappable; tel links measure 26–34px tall, below the page's own 48px rule** (VERIFIED+MEASURED, source lines ~440/462).
   Add one 48px call button at the end of the banner: `<a class="callbtn" href="tel:1555">โทร 1555 แจ้งน้ำท่วม กทม.</a>` with `.callbtn{display:flex;align-items:center;justify-content:center;min-height:48px;border-radius:10px;background:var(--surface);color:var(--hero-bg);font-weight:700;text-decoration:none;margin-top:12px}`.
   Give every `a[href^="tel:"]` and source link `display:inline-flex;min-height:44px;align-items:center;padding-inline:4px`.

9. **Hero has no visible "what to do now" line; the only reassurance sits ~1,800px down** (VERIFIED, contradicts P8).
   `.banner .watch{font-weight:500}` (bold only the lead clause via `<strong>`, not the whole paragraph).
   Add `<p class="now">ตอนนี้: ยังไม่ต้องยกของเพิ่ม · ดูอีกครั้ง 1 ชม.</p>` directly under the verdict word, sourced from the same value already driving the trend card.

10. **The 3 hero chips stack as 3 separate pills, wasting fold space** (INSTINCT — layout only, keep the 3 values).
    `.chips{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}` and `.chip b{display:block;font-size:1.4rem}` for a 3-up stat row (e.g. "2/4 ปั๊มเสีย" · "9/11 คลองเกินเส้น" · "197 มม. ฝน 24 ชม.").

11. **Render-blocking Google Fonts: 2 families, 6 weights, 8 loaded faces** (VERIFIED+MEASURED — costs a blocking round trip on 3G/4G).
    Drop the Kanit family; request Noto Sans Thai only at `wght@400;700` (400/700 cover the 500/600 uses).
    Load non-blocking: `<link rel="preload" as="style" href="…&display=swap" onload="this.rel='stylesheet'">` + `<noscript>` fallback; keep the `Sarabun, system-ui` stack.

12. **Desktop banner overhangs the card column by 16px each side at 1024px** (VERIFIED, `margin-inline: calc(var(--gutter) * -1)`).
    `@media (min-width:600px){.banner{margin-inline:0;border-radius:12px}}`.

13. **Double section-divider lines above every h2** (VERIFIED — a `--border` rule plus a separate hr-like rule).
    Keep one 1px `--border` rule, or drop it and rely on the existing 32px whitespace rhythm — not both.

## Do not regress (already correct — see `PEER_REVIEW.md` §"What to keep")
Verdict word as visual hero at 43px display weight on calm navy (not red); colour+word always
paired per tier with counts in the title; explicit "ยังไม่มีรายงาน (ไม่ได้แปลว่าปลอดภัย)" grey
bucket; per-tier imperative prep line; 18px base / rem type / 48px A−/A+ controls / no horizontal
scroll at 390px; server-rendered content (~23KB gzipped) with JS as enhancement only; `<details>`
collapse for long secondary sections; the two-sided trend framing; the single ~640px desktop
column (no sidebar).

## Provenance / no-attribution note
Produced as part of an internal design-review task; do not add any AI/vendor name to this
document or to anything built from it.
