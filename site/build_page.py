#!/usr/bin/env python3
"""build_page.py -- inject data.json (TWO areas) into index.template.html -> index.html.

Read-only with respect to the outside world. Renders EVERY table/section SERVER-SIDE for
both areas (so the page communicates everything with JavaScript turned off), by extracting
the single `<!--AREA_TEMPLATE_START--> ... <!--AREA_TEMPLATE_END-->` block from the
template, filling it once per area (with that area's own data + labels + `__AREA__` id
suffix), and concatenating the two renders into the page. Client JS only enhances
(font size, area switching, remembering the viewer's chosen area, staleness re-check
against the viewer's own clock).

Publish-safety invariant enforced here: the OUTPUT file must start with the literal bytes
"<title>" -- no <!DOCTYPE>, <html>, <head>, <body>, or <meta charset/viewport> tags, since
this page is embedded as a fragment, never served as a standalone document. This script
strips any such tags that accidentally end up in the template and asserts the final byte
sequence before writing.

Usage:
    python3 build_page.py
    python3 build_page.py --data other_data.json --template other_template.html --out other.html
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLACEHOLDER = "{{DATA_JSON}}"
AREA_START = "<!--AREA_TEMPLATE_START-->"
AREA_END = "<!--AREA_TEMPLATE_END-->"
AREA_SLOT_RE = re.compile(re.escape(AREA_START) + r"(.*?)" + re.escape(AREA_END), re.DOTALL)

BANGKOK_TZ = datetime.timezone(datetime.timedelta(hours=7))

THAI_DIGITS = {"๐": "0", "๑": "1", "๒": "2", "๓": "3", "๔": "4",
               "๕": "5", "๖": "6", "๗": "7", "๘": "8", "๙": "9"}
THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
               "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

ZONE_META = {
    "red":    {"label": "น้ำเข้าบ้านแล้ว",
               "prep": "ยกของขึ้นสูง ปิดเบรกเกอร์ชั้นล่าง"},
    "orange": {"label": "น้ำเข้าโรงรถ", "prep": "เตรียมกระสอบทราย ย้ายรถให้พ้นน้ำ"},
    "yellow": {"label": "ถนนท่วม", "prep": "ย้ายรถเมื่อถนนเริ่มขัง"},
    "grey":   {"label": "ยังไม่มีรายงาน (ไม่ได้แปลว่าปลอดภัย)", "prep": None},
}

# ---------------------------------------------------------------------------
# Premium icon system (maintainer ruling 2026-09-26): the maintainers asked to raise
# this page to "world-class app" quality -- readable, calm, premium framing --
# benchmarked against Apple Weather / Google weather cards / UK
# check-for-flooding. Emoji render inconsistently across Android/iOS/LINE and
# read as an AI-generated-page tell, so every severity/section icon below is a
# single outline inline-SVG (24px grid, 1.75px stroke, currentColor, no fill)
# instead of an emoji glyph. Emoji are kept ONLY inside the native <option>
# dropdown, which cannot render inline SVG.
ICON_PATHS = {
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "magnifier": '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
    "pump": '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    "wave": '<path d="M2 15c1.5-2 3-2 4.5 0s3 2 4.5 0 3-2 4.5 0 3 2 4.5 0"/><path d="M2 9c1.5-2 3-2 4.5 0s3 2 4.5 0 3-2 4.5 0 3 2 4.5 0"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.07 0l1.41-1.41a5 5 0 0 0-7.07-7.07L10 6"/><path d="M14 11a5 5 0 0 0-7.07 0l-1.41 1.41a5 5 0 0 0 7.07 7.07L14 18"/>',
    "rain": '<path d="M16 13v8"/><path d="M8 13v8"/><path d="M12 15v8"/><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "exit": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "hospital": '<rect x="3" y="3" width="18" height="18" rx="3"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "bolt": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
}


def icon(name, size=24, extra_cls=""):
    """One outline inline-SVG icon, currentColor, from ICON_PATHS. `size` is a
    CSS px class (ic-16/20/24/40); `extra_cls` adds e.g. a dot-colour class."""
    body = ICON_PATHS.get(name, ICON_PATHS["doc"])
    cls = f"ic ic-{size}" + (f" {extra_cls}" if extra_cls else "")
    return (f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" '
            f'fill="none" stroke="currentColor" stroke-width="1.75" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def sec_label(name, text):
    """Section-header content: small icon + uppercase-tracking label text,
    used inside every <h2 class="sec-label"> / <summary> in the template."""
    return f'{icon(name, 20)}<span>{text}</span>'


def tier_dot(zone_key):
    """One 14px inline-SVG dot, coloured via the existing .label-<key> class -- replaces the
    old bare emoji (🔴🟠🟡⚪) severity markers. Never a second icon alongside it."""
    return (f'<svg class="dot label-{zone_key}" viewBox="0 0 10 10" aria-hidden="true">'
            f'<circle cx="5" cy="5" r="5" fill="currentColor"/></svg>')

STATUS_PILL = {
    "NORMAL": ("pill-ok", "ปกติ"), "WATCH": ("pill-warn", "เส้นเตือน"),
    "CRITICAL": ("pill-crit", "เส้นอันตราย"), "OVERBANK": ("pill-over", "ล้นตลิ่ง"),
    "NO_THRESHOLD": ("pill-none", "ไม่มีข้อมูลล่าสุด"),
}

AREA_LABELS = {
    "sammakorn": {
        "dropdown": "หมู่บ้านสัมมากร (รามคำแหง 112)",
        "heading": "หมู่บ้านสัมมากร (รามคำแหง 112)",
        "pin": "หมู่บ้านสัมมากร รามคำแหง 112 เขตสะพานสูง",
        "subtitle": "น้ำสัมมากร (ราม 112) วันนี้",
        "exit_place_word": "หมู่บ้าน",
        "zones_heading": "ซอยไหนต้องระวังอะไร",
        "pump_heading": "บึงและปั๊มในหมู่บ้าน",
        "pump_caption": "ระดับน้ำและปั๊มเดิน/ขัดข้อง 4 สถานีของหมู่บ้าน",
        "canal_north_label": "ฝั่งเหนือ — คลองแสนแสบ",
        "canal_south_label": "ฝั่งใต้ — คลองทับช้าง / ประเวศ / หัวหมาก",
        "pond_word": "บึงในหมู่บ้าน",
    },
    "ram53": {
        "dropdown": "ซอยรามคำแหง 53",
        "heading": "ซอยรามคำแหง 53",
        "pin": "ซอยรามคำแหง 53 เขตวังทองหลาง",
        "subtitle": "น้ำรามคำแหง 53 วันนี้",
        "exit_place_word": "ซอย",
        "zones_heading": "สถานการณ์ในซอย",
        "pump_heading": "สถานีสูบน้ำใกล้ซอย",
        "pump_caption": "ระดับน้ำและปั๊มเดิน/ขัดข้อง 4 สถานีใกล้ซอย",
        "canal_north_label": "ฝั่งเหนือ",
        "canal_south_label": "ฝั่งใต้",
        "pond_word": "ปั๊มริมคลองใกล้ซอย",
    },
}


def normalize_digits(s):
    if not s:
        return s
    return "".join(THAI_DIGITS.get(ch, ch) for ch in s)


def clean_soi_name(s):
    t = normalize_digits(s or "")
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    return t.strip()


def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def to_bkk(iso):
    if not iso:
        return None
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BANGKOK_TZ)
    return dt.astimezone(BANGKOK_TZ)


def fmt_hm(iso):
    dt = to_bkk(iso)
    return dt.strftime("%H:%M") if dt else "--:--"


def hours_ago(iso, now_dt):
    dt = to_bkk(iso)
    if dt is None or now_dt is None:
        return None
    return (now_dt - dt).total_seconds() / 3600.0


def fmt_time_full(iso, now_dt):
    dt = to_bkk(iso)
    if dt is None:
        return "ไม่ทราบเวลา"
    age = hours_ago(iso, now_dt)
    base = f"{dt.strftime('%H:%M')} น. ({dt.day} {THAI_MONTHS[dt.month - 1]}"
    if age is None or age > 24 or age < 0:
        days = round((age or 0) / 24)
        base += f" {dt.year + 543}, {days} วันก่อน)" if days >= 1 else " ข้อมูลเก่า)"
    else:
        base += ")"
    return base


def obs_time_label(iso, now_dt):
    """Short 'ค่าเมื่อ HH:MM' / 'ค่าเมื่อคืน HH:MM' label for the hero's why-list lines."""
    dt = to_bkk(iso)
    if dt is None or now_dt is None:
        return "ไม่มีข้อมูลเวลา"
    hm = dt.strftime("%H:%M")
    if dt.date() == now_dt.date():
        return f"ค่าเมื่อ {hm}"
    if dt.date() == (now_dt - datetime.timedelta(days=1)).date():
        return f"ค่าเมื่อคืน {hm}"
    return f"ค่าเมื่อ {dt.day} {THAI_MONTHS[dt.month - 1]} {hm}"


def thai_hour_phrase(h):
    h = h % 24
    if h == 0:
        return "เที่ยงคืน"
    if 1 <= h <= 5:
        return f"ตี {h}"
    if 6 <= h <= 11:
        return f"{h} โมงเช้า"
    if h == 12:
        return "เที่ยง"
    if h == 13:
        return "บ่ายโมง"
    if h in (14, 15):
        return f"บ่าย {h - 12} โมง"
    if 16 <= h <= 18:
        return f"{h - 12} โมงเย็น"
    return f"{h - 18} ทุ่ม"


def thai_clock_exact(dt):
    if dt is None:
        return "--"
    return thai_hour_phrase(dt.hour) + (f" {dt.minute:02d}" if dt.minute else "")


def thai_hour_window_label(dt, offset_hours):
    if dt is None:
        return "--"
    shifted = dt + datetime.timedelta(hours=offset_hours)
    return thai_hour_phrase(shifted.hour)


def status_pill_html(status):
    cls, label = STATUS_PILL.get(status, STATUS_PILL["NO_THRESHOLD"])
    return f'<span class="pill {cls}" aria-label="สถานะคลอง: {esc(label)}">{esc(label)}</span>'


def status_pill_aged_html(status, observed_at, now_dt):
    h = hours_ago(observed_at, now_dt)
    if h is None or h > 24:
        return '<span class="pill pill-stale">ข้อมูลเก่า ใช้ไม่ได้</span>'
    return status_pill_html(status)


def next_high_water(area):
    tide = area.get("tide") or {}
    highs = tide.get("next_high") or []
    return highs[0] if highs else None


# ---------------- pump wording (item C: same wording everywhere) ----------------

def pump_wording(p, now_dt):
    """Returns (text, kind) where kind in {fail, idle, missing, ok}. Never merges
    ขัดข้อง and ไม่ได้เดิน counts -- callers must count each kind separately."""
    h = hours_ago(p.get("observed_at"), now_dt)
    if p.get("status_th") == "ขัดข้อง":
        return ("กทม. รายงาน 'ขัดข้อง' (ไม่ทราบสาเหตุ: เครื่อง ไฟ หรือสัญญาณ — ตรวจหน้างานได้)", "fail")
    if h is None or h > 2:
        return "ไม่มีข้อมูลล่าสุด", "missing"
    if (p.get("pumps_on") or 0) == 0:
        total = p.get("pumps_total")
        return f"ปั๊มไม่ได้เดิน (0/{total}) — อาจยังไม่เปิดหรือไม่มีข้อมูล", "idle"
    return "ปกติ", "ok"


def pump_counts(pumps, now_dt):
    fail = idle = missing = ok = 0
    for p in pumps:
        _, kind = pump_wording(p, now_dt)
        if kind == "fail":
            fail += 1
        elif kind == "idle":
            idle += 1
        elif kind == "missing":
            missing += 1
        else:
            ok += 1
    return {"fail": fail, "idle": idle, "missing": missing, "ok": ok, "total": len(pumps)}


# ---------------- status word + factors ----------------

def compute_status(area, now_dt, pc):
    near = [s for s in (area.get("stations_near") or []) if s.get("role") in ("north", "south")]
    fresh_near = [s for s in near
                  if (h := hours_ago(s.get("observed_at"), now_dt)) is not None and h <= 24
                  and s.get("status") != "NO_THRESHOLD"]
    fresh_crit = sum(1 for s in fresh_near if s.get("status") in ("CRITICAL", "OVERBANK"))
    upstream = [s for s in (area.get("stations_near") or []) if s.get("role") == "upstream"]
    fresh_up = [s for s in upstream
                if (h := hours_ago(s.get("observed_at"), now_dt)) is not None and h <= 24]
    up_crit = sum(1 for s in fresh_up if s.get("status") in ("CRITICAL", "OVERBANK"))
    all_ok = bool(fresh_near) and all(s.get("status") in ("NORMAL", "WATCH") for s in fresh_near)
    pumps_all_normal = pc["total"] > 0 and pc["fail"] == 0 and pc["idle"] == 0
    rain_mm = (area.get("rain") or {}).get("mm_24h")
    rain_ok = rain_mm is not None and rain_mm < 30
    if pc["fail"] > 0 or fresh_crit >= 2:
        word = "น้ำยังขึ้น"
    elif all_ok and pumps_all_normal and rain_ok:
        word = "น้ำเริ่มลด"
    else:
        word = "ยังบอกไม่ได้ — เตรียมพร้อมไว้ก่อน"
    return {"word": word, "near": near, "fresh_near": fresh_near, "fresh_crit": fresh_crit,
            "upstream": upstream, "fresh_up": fresh_up, "up_crit": up_crit}


def build_watch_line(area, st, pc, now_dt, forecast):
    """One calm sentence, at most ~20 words -- the single strongest factor only
    (maintainer ruling 2026-09-26: infographic style, fewer words per line)."""
    mag = icon("magnifier", 20)
    hw = next_high_water(area)
    candidates = []
    if pc["fail"] > 0:
        candidates.append((3, f"ปั๊มบึงขัดข้อง {pc['fail']} จุด"))
    if st["up_crit"] > 0:
        candidates.append((2, f"ต้นน้ำเกินเส้นอันตราย {st['up_crit']} จุด"))
    if st["fresh_crit"] > 0:
        candidates.append((2, f"คลองรอบบ้าน {st['fresh_crit']} จุดเกินเส้นอันตราย"))
    if forecast and forecast.get("direction") == "rising":
        candidates.append((1, "ฝนกำลังเพิ่มขึ้น"))
    candidates.sort(key=lambda c: -c[0])
    top_factor = candidates[0][1] if candidates else None

    if not hw:
        text = top_factor or "เฝ้าดูสถานการณ์ต่อไป"
        return f"{mag} ต้องเฝ้าระวัง: {text}"
    hw_dt = to_bkk(hw.get("time"))
    hw_label = f"<strong>{thai_clock_exact(hw_dt)}</strong>"
    if not top_factor:
        return f"{mag} ต้องเฝ้าระวัง: น้ำหนุนสูงสุด {hw_label}"
    win_start = thai_hour_window_label(hw_dt, -2)
    win_end = thai_hour_window_label(hw_dt, 2)
    return (f"{mag} ต้องเฝ้าระวังช่วง <strong>{win_start}–{win_end}</strong> "
            f"— น้ำหนุนสูงสุด {hw_label} และ{top_factor}")


# ---------------- hero "why" list (5 lines, maintainer-mandated bullet format) ----------------

def rain_band_word(mm):
    if mm is None:
        return None
    if mm > 150:
        return "มากผิดปกติ"
    if mm > 90:
        return "มาก"
    if mm >= 30:
        return "ปานกลาง"
    return "น้อย"


DOT_WORD = {"red": "สูง", "amber": "เฝ้าดู", "green": "ปกติ", "grey": "ไม่มีข้อมูลล่าสุด"}


def _tile(icon_name, value_text, label_text, dot, time_text=None, extra_line=None):
    """One infographic tile (maintainer ruling 2026-09-26): 40px icon, big bold
    value, short label, colour dot + one status word. No paragraphs -- an
    icon-grid the eye can scan in one pass. `extra_line` (2026-09-26 red-team
    fix) adds a second small line -- used for pumps merely idle (not failed),
    kept separate from the fail count so idle is never mislabelled as a fault."""
    word = DOT_WORD.get(dot, DOT_WORD["grey"])
    time_html = f'<span class="tile-time">{esc(time_text)}</span>' if time_text else ""
    extra_html = f'<div class="tile-extra">{esc(extra_line)}</div>' if extra_line else ""
    return (
        '<div class="tile">'
        f'{icon(icon_name, 40)}'
        f'<div class="tile-value num">{esc(value_text)}</div>'
        f'<div class="tile-label">{esc(label_text)}</div>'
        f'<div class="tile-status"><span class="why-dot why-dot-{dot}" aria-hidden="true"></span>{word}</div>'
        f'{extra_html}'
        f'{time_html}'
        '</div>'
    )


def build_indicator_tiles(area, st, pc, now_dt, pond_word):
    """2-column infographic tile grid replacing the old row list -- one tile
    per indicator: pump, canal, upstream, rain, tide (maintainer ruling
    2026-09-26: 'more icons, fewer words')."""
    tiles = []

    # 1. ปั๊มบึง
    pumps = area.get("pumps") or []
    total_pumps = len(pumps)
    if total_pumps == 0:
        tiles.append(_tile("pump", "–", "ปั๊มบึง", "grey"))
    else:
        dot = "red" if pc["fail"] > 0 else ("amber" if pc["idle"] > 0 else ("grey" if pc["ok"] == 0 else "green"))
        label = "ขัดข้อง (กทม. รายงาน)" if pc["fail"] > 0 else "ปั๊มบึง"
        newest_pump = max((p.get("observed_at") for p in pumps if p.get("observed_at")), default=None)
        idle_line = f"ไม่ได้เดิน {pc['idle']}" if pc["idle"] > 0 else None
        tiles.append(_tile("pump", f"{pc['fail']}/{total_pumps}", label, dot, obs_time_label(newest_pump, now_dt),
                            extra_line=idle_line))

    # 2. คลองรอบบ้าน
    fresh_near = st["fresh_near"]
    crit = st["fresh_crit"]
    total = len(fresh_near)
    if total == 0:
        tiles.append(_tile("wave", "–", "คลองรอบบ้าน", "grey"))
    else:
        newest = max((s.get("observed_at") for s in fresh_near if s.get("observed_at")), default=None)
        tiles.append(_tile("wave", f"{crit}/{total}", "คลองเกินเส้นอันตราย", "red" if crit > 0 else "green",
                            obs_time_label(newest, now_dt)))

    # 3. น้ำจากต้นทาง
    fresh_up = st["fresh_up"]
    up_crit_stations = [s for s in fresh_up if s.get("status") in ("CRITICAL", "OVERBANK")]
    up_total = len(fresh_up)
    if up_total == 0:
        tiles.append(_tile("link", "–", "ต้นน้ำสูง", "grey"))
    else:
        dot = "red" if up_crit_stations and len(up_crit_stations) >= up_total / 2.0 else \
            ("amber" if up_crit_stations else "green")
        tiles.append(_tile("link", f"{len(up_crit_stations)}/{up_total}", "ต้นน้ำสูง", dot))

    # 4. ฝนตอนนี้ (มม./ชม.) + เส้นรอง 24 ชม.
    rain = area.get("rain")
    if rain and rain.get("mm_24h") is not None:
        mm = rain["mm_24h"]
        mm_1h = rain.get("mm_1h")
        dot = "red" if mm > 90 else ("amber" if mm >= 30 else "green")
        station = rain.get("station")
        dist = rain.get("dist_km")
        value_text = f"{mm_1h:.1f} มม./ชม." if mm_1h is not None else "–"
        label = f"ฝนตอนนี้ ({station} {dist:.1f} กม.)" if station and dist is not None else "ฝนตอนนี้"
        tier = rain.get("tier_word")
        extra = f"24 ชม. {mm:.0f} มม." + (f" ({tier})" if tier else "")
        tiles.append(_tile("rain", value_text, label, dot, extra_line=extra))
    else:
        tiles.append(_tile("rain", "–", "ฝนตอนนี้", "grey"))

    # 5. น้ำหนุน
    hw = next_high_water(area)
    if hw:
        hw_dt = to_bkk(hw.get("time"))
        height = hw.get("height_m")
        h_text = f"{height:+.1f} ม." if height is not None else "–"
        tiles.append(_tile("moon", h_text, f"น้ำหนุน {thai_clock_exact(hw_dt)}", "grey"))
    else:
        tiles.append(_tile("moon", "–", "น้ำหนุน", "grey"))

    return "".join(tiles)


# canal-vs-ground reference station per area (2026-09-26, founder-requested):
# ground class 0-0.5 m MSL, RTSD 2010 topo map, +-0.5 m map-class tolerance.
CANAL_VS_GROUND_STATION = {"sammakorn": "WL.TPK.03", "ram53": "WL.KJN.01"}
GROUND_LEVEL_MSL_M = 0.5


def build_canal_vs_ground_line(area, area_id, now_dt):
    """One hero-list line comparing the back-canal water level to the
    0-0.5 m MSL ground/pond class (RTSD 2010, +-0.5 m map tolerance): if the
    canal already sits above the ground class, water cannot drain into it by
    gravity alone. Falls back to the nearest fresh (<=24h) north/south canal
    station when the named station is missing or stale."""
    stations = area.get("stations_near") or []
    wanted_code = CANAL_VS_GROUND_STATION.get(area_id)
    station = next((s for s in stations if s.get("code") == wanted_code
                     and s.get("value_m") is not None), None)
    if station is None:
        candidates = [s for s in stations
                      if s.get("role") in ("north", "south") and s.get("value_m") is not None
                      and (h := hours_ago(s.get("observed_at"), now_dt)) is not None and h <= 24]
        candidates.sort(key=lambda s: s.get("dist_km") if s.get("dist_km") is not None else 999)
        station = candidates[0] if candidates else None
    if station is None:
        return None
    diff = station["value_m"] - GROUND_LEVEL_MSL_M
    sign = "+" if diff >= 0 else ""
    verdict = "ไหลลงคลองเองได้" if station["value_m"] < 0.3 else "น้ำยังไหลลงคลองเองไม่ได้"
    wave_ic = icon("wave", 20)
    return (f"{wave_ic} คลองหลังบ้าน vs พื้น — คลองสูงกว่าพื้น ~{sign}{diff:.1f} ม. "
            f"(พื้น ชั้นแผนที่ ±0.5 ม., RTSD 2010) → {verdict}")


def build_hours_list(area, st, pc, now_dt, forecast, area_id=None):
    """Up to 5 icon-led lines, each 8 words or fewer (maintainer ruling
    2026-09-26: infographic style; 5th line = canal-vs-ground indicator,
    founder-requested 2026-09-26)."""
    lines = []
    forecast = forecast or {}
    rain_ic = icon("rain", 20)
    moon_ic = icon("moon", 20)
    pump_ic = icon("pump", 20)
    wave_ic = icon("wave", 20)

    # "อีก 3-5 ชั่วโมงข้างหน้า" -- trend_word compares the next-3h sum against the
    # following-3h sum (see build_data.py::_trend_word), read straight from the data
    # rather than re-derived here.
    if forecast.get("available"):
        trend_word = forecast.get("trend_word") or "ฝนยังตกต่อ"
        lines.append(f"{rain_ic} อีก 3–5 ชั่วโมงข้างหน้า: {esc(trend_word)}")
    else:
        lines.append(f"{rain_ic} ยังไม่มีพยากรณ์รายชั่วโมง")

    hw = next_high_water(area)
    if hw:
        hw_dt = to_bkk(hw.get("time"))
        lines.append(f"{moon_ic} น้ำหนุนสูงสุด {thai_clock_exact(hw_dt)}")

    if pc["fail"] > 0:
        lines.append(f"{pump_ic} ปั๊มบึงขัดข้อง {pc['fail']} จุด")
    elif pc["idle"] > 0:
        lines.append(f"{pump_ic} ปั๊มบึงไม่ได้เดิน {pc['idle']} จุด")
    else:
        lines.append(f"{pump_ic} ปั๊มบึงเดินปกติ")

    if len(st["fresh_near"]) > 0:
        lines.append(f"{wave_ic} คลอง {st['fresh_crit']}/{len(st['fresh_near'])} จุดเกินเส้นอันตราย")

    canal_vs_ground = build_canal_vs_ground_line(area, area_id, now_dt)
    if canal_vs_ground:
        lines.append(canal_vs_ground)

    lines = lines[:5]
    return "".join(f'<li><span class="why-text">{ln}</span></li>' for ln in lines)


# ---------------- hero "ตอนนี้: ..." action line (item 9) ----------------

def build_now_line(area):
    """One OPTIONAL-suggestion line for right under the verdict word: the reader decides.
    Never an imperative command, never a permission ("ไม่ต้อง...")."""
    tiers = area.get("tiers") or []
    has_t1 = any(t.get("tier") == "T1" and (t.get("sois") or []) for t in tiers)
    if has_t1:
        prep = ZONE_META["red"]["prep"] or ""
        first_action = prep.split(" · ")[0].strip()
        if first_action:
            return first_action
    return "เตรียมพร้อมไว้ก่อน — ยกของสำคัญขึ้นสูง ชาร์จมือถือ เตรียมไฟฉาย-ยา-น้ำดื่ม"


# ---------------- zones (Sammakorn tiers; ram53 note) ----------------

def build_zones_html(area):
    tiers = area.get("tiers") or []
    if not tiers:
        note = esc(area.get("tiers_note") or "ไม่มีข้อมูลล่าสุด")
        return f'<p class="empty-note">{note}</p>'
    by_tier = {t.get("tier"): (t.get("sois") or []) for t in tiers}
    groups = {"red": by_tier.get("T1", []), "orange": by_tier.get("T2", []),
              "yellow": (by_tier.get("T3", []) or []) + (by_tier.get("T4", []) or []),
              "grey": by_tier.get("T5", [])}

    def card(zone_key, sois, open_by_default=False):
        meta = ZONE_META[zone_key]
        dot = tier_dot(zone_key)
        chips = "".join(f'<span class="zone-chip">{esc(clean_soi_name(s.get("soi")))}</span>' for s in sois) \
            or '<span class="empty-note small">ไม่มีซอยในกลุ่มนี้</span>'
        # short one-line optional action, <=10 words (maintainer ruling 2026-09-26)
        prep_line = f'<p class="prepline">อาจทำได้: {esc(meta["prep"])}</p>' if meta["prep"] else ""
        pill = f'<span class="pill pill-tier-{zone_key}">{len(sois)} ซอย</span>'
        body = (f'<div class="body"><div class="name">{dot}{meta["label"]} {pill}</div>'
                f'<div class="zone-chip-list">{chips}</div>{prep_line}</div>')
        if zone_key == "grey":
            open_attr = " open" if open_by_default else ""
            return (f"<details class=\"tier-card rail-{zone_key}\"{open_attr}>"
                    f"<summary>{dot}{meta['label']} {pill}</summary>"
                    f'<div class="tier-body"><div class="zone-chip-list">{chips}</div></div></details>')
        return f'<div class="tier-card rail-{zone_key}">{body}</div>'

    return (card("red", groups["red"]) + card("orange", groups["orange"])
            + card("yellow", groups["yellow"]) + card("grey", groups["grey"], open_by_default=False))


# ---------------- pumps ----------------

def build_pump_rows(area, now_dt):
    pumps = area.get("pumps") or []
    rows = []
    for p in pumps:
        text, kind = pump_wording(p, now_dt)
        cls = "stat-fail" if kind in ("fail", "idle", "missing") else "stat-ok"
        if kind in ("fail", "missing"):
            level = "ไม่มีข้อมูลล่าสุด"
        elif p.get("level_m") is None:
            level = "ไม่มีข้อมูลล่าสุด"
        else:
            level = f"{p['level_m']:.2f} ม."
        pond_name = esc(p.get("pond_name") or p.get("name"))
        rows.append(
            "<tr>"
            f'<td data-label="บึง / สถานี"><span class="nw">{pond_name}</span>'
            f'<small class="code">{esc(p.get("code"))}</small></td>'
            f'<td class="num" data-label="ระดับน้ำ">{esc(level)}</td>'
            f'<td class="num" data-label="ปั๊มเดิน">{esc(p.get("pumps_on"))}/{esc(p.get("pumps_total"))}</td>'
            f'<td class="{cls}" data-label="สถานะ">{esc(text)}</td>'
            f'<td data-label="เวลา">{fmt_time_full(p.get("observed_at"), now_dt)}</td>'
            "</tr>"
        )
    rows_html = "".join(rows) or '<tr><td colspan="5" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'
    pc = pump_counts(pumps, now_dt)
    bits = []
    if pc["fail"]:
        bits.append(f"ขัดข้อง {pc['fail']}")
    if pc["idle"]:
        bits.append(f"ไม่ได้เดิน {pc['idle']}")
    lead = (f"จาก {len(pumps)} สถานี: " + ", ".join(bits)) if bits else \
        (f"ปกติทั้ง {len(pumps)} สถานี" if pumps else "")
    return rows_html, lead


# ---------------- canals ----------------

def canal_row_html(s, now_dt):
    # Short per-station threshold numbers only (no long "เกณฑ์ (ม. เทียบระดับน้ำในคลอง):"
    # label repeated on every row -- that explanation now lives ONCE as a .table-lead note
    # above the table). Combined with the observed-time label into one small grey meta
    # line, matching the pump/pond card's line-4 pattern.
    thresh = []
    if s.get("warning") is not None:
        thresh.append(f"เตือน {s['warning']:.2f}")
    if s.get("critical") is not None:
        thresh.append(f"อันตราย {s['critical']:.2f}")
    if s.get("bank") is not None:
        thresh.append(f"ตลิ่ง {s['bank']:.2f}")
    thresh_short = " · ".join(thresh)
    time_label = obs_time_label(s.get("observed_at"), now_dt)
    meta_line = f"{thresh_short} · {time_label}" if thresh_short else time_label
    value = "–" if s.get("value_m") is None else f"{s['value_m']:.2f} ม."
    return (
        "<tr>"
        f'<td data-label="สถานี">{esc(s.get("name"))}<br><span class="small">{esc(s.get("code"))} · ห่าง '
        f'{s.get("dist_km", 0):.1f} กม.</span></td>'
        f'<td class="num" data-label="ระดับน้ำ">{esc(value)}</td>'
        f'<td data-label="สถานะ">{status_pill_aged_html(s.get("status"), s.get("observed_at"), now_dt)}</td>'
        f'<td data-label="เกณฑ์ / เวลา">{esc(meta_line)}</td>'
        "</tr>"
    )


def build_canal_rows(area, now_dt):
    stations = [s for s in (area.get("stations_near") or [])
                if s.get("role") in ("north", "south") and (s.get("dist_km") or 0) <= 5]
    fresh, stale = [], []
    for s in stations:
        h = hours_ago(s.get("observed_at"), now_dt)
        (fresh if (h is not None and h <= 24) else stale).append(s)
    north = [s for s in fresh if s.get("role") == "north"]
    south = [s for s in fresh if s.get("role") == "south"]
    empty = '<tr><td colspan="4" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'
    north_html = "".join(canal_row_html(s, now_dt) for s in north) or empty
    south_html = "".join(canal_row_html(s, now_dt) for s in south) or empty
    stale_html = "".join(canal_row_html(s, now_dt) for s in stale) or \
        '<tr><td colspan="4" class="empty-note">ไม่มี</td></tr>'

    upstream = [s for s in (area.get("stations_near") or []) if s.get("role") == "upstream"]
    upstream_html = "".join(canal_row_html(s, now_dt) for s in upstream) or \
        '<tr><td colspan="4" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'
    return north_html, south_html, stale_html, upstream_html


# ---------------- forecast (rain 24h + rain forecast strip + tide + DDS) ----------------

def build_forecast_fragments(area, now_dt_local, forecast, rain_forecast_area_note):
    rain = area.get("rain")
    capacity = area.get("capacity") or {}
    if rain:
        mm_1h = rain.get("mm_1h")
        mm_24h = rain.get("mm_24h")
        now_rate = f"{mm_1h:.1f}" if mm_1h is not None else "–"
        rain_text = (
            f'ฝนตอนนี้ <span class="num">{now_rate}</span> มม./ชม. '
            f'<span class="small">({esc(rain.get("station"))} {rain.get("dist_km", 0):.1f} กม.)</span><br>'
            f'24 ชม. <span class="num">{(mm_24h or 0):.1f}</span> มม.'
            f'{" (" + esc(rain.get("tier_word")) + ")" if rain.get("tier_word") else ""} — '
            f'อ่านเมื่อ {fmt_time_full(rain.get("observed_at"), now_dt_local)} · {esc(rain.get("agency_th"))}'
        )
        if capacity.get("today_mm") is not None and capacity.get("today_ratio") is not None:
            rain_text += (
                f'<br><span class="small">ระบบ กทม. ออกแบบรับได้ ~'
                f'{capacity["mm_per_day"]:.0f} มม./วัน — วันนี้ตกแล้ว '
                f'{capacity["today_mm"]:.0f} มม. ({capacity["today_ratio"]:.1f} เท่า) — '
                f'{esc(capacity.get("source_th"))}</span>'
            )
    else:
        rain_text = "ไม่มีข้อมูลล่าสุด"

    forecast = forecast or {}
    rain_ic = icon("rain", 20)
    if forecast.get("available"):
        note = f' <span class="small">({esc(rain_forecast_area_note)})</span>' if rain_forecast_area_note else ""
        trend_word = forecast.get("trend_word") or "ฝนยังตกต่อ"
        fc_text = f"{rain_ic} {esc(trend_word)}"
        fc_text += (f'{note} <span class="small">— {esc(forecast.get("source"))}, '
                    f'ไม่ใช่ของหน่วยงานรัฐไทย</span>')
        next6h = forecast.get("next6h_mm")
        next24h = forecast.get("next24h_mm")
        tomorrow = forecast.get("h24_48_mm")
        dry_start = forecast.get("first_dry_6h_start")
        add_html = '<br><span class="small">ฝนที่จะเติมอีก (แบบจำลองเปิด Open-Meteo, ไม่ใช่กรมอุตุฯ): '
        if next6h is None:
            add_html += "ไม่มีข้อมูล"
        else:
            add_html += f'อีก 6 ชม. {next6h:.0f} มม.'
            if next24h is not None:
                add_html += f' · 24 ชม. {next24h:.0f} มม.'
            if tomorrow is not None:
                add_html += f' · พรุ่งนี้ {tomorrow:.0f} มม.'
            add_html += (f' · ช่วงแห้ง 6 ชม. แรกเริ่ม {esc(dry_start)} น.' if dry_start
                         else ' · ยังไม่พบช่วงแห้ง 6 ชม. ติดต่อกันใน 72 ชม.นี้')
        add_html += "</span>"
        fc_text += add_html
        if capacity.get("total_with_forecast_mm") is not None:
            fc_text += (
                f'<br><span class="small">ฝนที่ตกแล้ว + ที่จะเติม 24 ชม. = '
                f'{capacity["total_with_forecast_mm"]:.0f} มม. เทียบขีด '
                f'{capacity["mm_per_day"]:.0f} มม./วัน = {capacity["total_with_forecast_ratio"]:.1f} เท่า '
                '(ผลรวม+อัตราส่วนจากตัวเลขที่ประกาศไว้ ไม่ใช่แบบจำลอง)</span>'
            )
    else:
        note = f' ({esc(rain_forecast_area_note)})' if rain_forecast_area_note else ""
        fc_text = f'{esc(forecast.get("status") or "ยังไม่มีพยากรณ์ฝนรายชั่วโมง — ดูเรดาร์ กทม.")}{note}'

    tide = area.get("tide") or {}
    hw = next_high_water(area)
    if hw:
        hw_dt = to_bkk(hw.get("time"))
        tide_next = (f'น้ำขึ้นสูงสุดรอบถัดไป: <strong>{thai_clock_exact(hw_dt)} '
                     f'({hw_dt.strftime("%H:%M")} น.)</strong> ระดับ '
                     f'<span class="num">{(hw.get("height_m") or 0):.2f}</span> ม.')
    else:
        tide_next = "ไม่มีข้อมูลล่าสุด"
    station_th = tide.get("station_th") or "กรมอุทกศาสตร์ กองทัพเรือ"
    tide_basis = (f"พยากรณ์ทางดาราศาสตร์จาก{esc(station_th)} เท่านั้น ไม่รวมน้ำเหนือ/ฝน "
                  "วัดจากระดับทะเลปานกลาง (MSL) — เทียบกับตัวเลขคลองไม่ได้ ใช้คนละมาตรฐาน")

    def tide_rows_html(days):
        rows = []
        for day in days:
            events = day.get("events") or []
            for i, ev in enumerate(events):
                date_cell = (f'<td rowspan="{len(events)}" data-label="วันที่">{esc(day.get("date"))}</td>'
                             if i == 0 else '<td data-label="วันที่"></td>')
                rows.append("<tr>" + date_cell +
                            f'<td data-label="เหตุการณ์">{"น้ำขึ้น" if ev.get("kind")=="HW" else "น้ำลง"}</td>'
                            f'<td class="num" data-label="เวลา">{esc(ev.get("t"))} น.</td>'
                            f'<td class="num" data-label="ระดับ (ม.)">{(ev.get("h") or 0):.2f}</td></tr>')
        return "".join(rows)

    week = tide.get("week") or []
    tide_week_rows = tide_rows_html(week[:2]) or '<tr><td colspan="4" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'
    tide_week_more_rows = tide_rows_html(week[2:]) or '<tr><td colspan="4" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'

    quotes = area.get("dds_quotes") or []
    dds_html = "".join(f"<li>{esc(q.get('text'))}</li>" for q in quotes)

    return rain_text, fc_text, tide_next, tide_basis, tide_week_rows, tide_week_more_rows, dds_html


# ---------------- exits / flood roads ----------------

def build_exit_rows(area):
    exits = area.get("exits") or []
    rows = []
    for e in exits:
        if e.get("is_community_report"):
            bits = ["ชาวบ้านรายงาน"]
            if e.get("report_date_th"):
                bits.append(esc(e["report_date_th"]))
            if e.get("report_time_th"):
                bits.append(esc(e["report_time_th"]) + " น.")
            body = f'{esc(e.get("status_from_reports"))} <span class="small">({" ".join(bits)})</span>'
        else:
            body = f'<span class="empty-note">{esc(e.get("status_from_reports"))}</span>'
        rows.append(f'<tr><td data-label="เส้นทาง">{esc(e.get("name"))}</td>'
                    f'<td data-label="รายงานล่าสุด">{body}</td></tr>')
    return "".join(rows) or '<tr><td colspan="2" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'


def build_floodroad_rows(area, now_dt):
    roads = [r for r in (area.get("flood_roads") or []) if (r.get("depth_cm") or 0) > 0]
    rows = []
    for r in roads:
        h = hours_ago(r.get("observed_at"), now_dt)
        old_tag = ' <span class="small">(ข้อมูลเก่า)</span>' if (h is None or h > 24) else ""
        rows.append(f'<tr><td data-label="ถนน">{esc(r.get("name"))}{old_tag}</td>'
                    f'<td class="num" data-label="ระดับน้ำ">{(r.get("depth_cm") or 0):.0f} ซม.</td>'
                    f'<td data-label="ห่างจากพื้นที่">{(r.get("dist_km") or 0):.1f} กม.</td>'
                    f'<td data-label="เวลารายงาน">{fmt_time_full(r.get("observed_at"), now_dt)}</td></tr>')
    return "".join(rows) or \
        '<tr><td colspan="4" class="empty-note">ไม่มีรายงานถนนน้ำท่วมใกล้เคียง (0 ซม. ไม่แสดง)</td></tr>'


def build_community_rows(area):
    rows = [f'<tr><td class="num" data-label="เวลา">{esc(r.get("time"))}</td>'
            f'<td data-label="จุด">{esc(clean_soi_name(r.get("place")))}</td>'
            f'<td data-label="สภาพที่รายงาน">{esc(r.get("state") or "-")}</td></tr>'
            for r in (area.get("community") or [])]
    return "".join(rows) or '<tr><td colspan="3" class="empty-note">ยังไม่มีรายงานในชุดข้อมูลนี้</td></tr>'


def build_nearby_community_rows(area):
    """คลองจั่น/บางกะปิ 'nearby area' note (2026-09-26) -- sammakorn only; ram53 already
    folds the full set into its own community rows since คลองจั่น is on its own canal
    chain, so this returns "" (hidden) there."""
    rows = area.get("nearby_community") or []
    if not rows:
        return "", " hidden"
    html = "".join(f'<tr><td class="num" data-label="เวลา">{esc(r.get("time"))}</td>'
                   f'<td data-label="จุด">{esc(clean_soi_name(r.get("place")))}</td>'
                   f'<td data-label="สภาพที่รายงาน">{esc(r.get("state") or "-")}</td></tr>'
                   for r in rows)
    return html, ""


def build_hospital_rows(area):
    rows = []
    for h in area.get("hospitals") or []:
        phone = h.get("phone")
        phone_html = f'<a href="tel:{esc((phone or "").replace(" ", ""))}">{esc(phone)}</a>' if phone else "-"
        rows.append(f'<tr><td data-label="โรงพยาบาล">{esc(h.get("name"))}</td>'
                    f'<td class="num" data-label="ระยะทาง">{(h.get("dist_km") or 0):.1f} กม.</td>'
                    f'<td data-label="โทร">{phone_html}</td></tr>')
    return "".join(rows) or '<tr><td colspan="3" class="empty-note">ไม่มีข้อมูลล่าสุด</td></tr>'


def build_sources_list(sources, now_dt):
    dot = icon("doc", 16)
    items = []
    for s in sources or []:
        link = (f' — <a href="{esc(s.get("url"))}" target="_blank" rel="noopener">ลิงก์ต้นทาง</a>'
                if s.get("url") else "")
        items.append(f"<li>{dot}<strong>{esc(s.get('agency_th'))}</strong> · อ่านเมื่อ "
                     f"{fmt_time_full(s.get('fetched_at'), now_dt)}{link}</li>")
    return "".join(items)


# ---------------- worsen / better two-sided cards (short bullets, icon-led) --------------

def build_worsen_better_html(area, st, pc, now_dt, forecast):
    """Two calm cards, condition bullets straight from the data -- never a
    verdict, just the signals a reader can check themselves."""
    worse, better = [], []
    hw = next_high_water(area)
    rain = area.get("rain") or {}
    mm = rain.get("mm_24h")
    forecast = forecast or {}

    if hw:
        hw_dt = to_bkk(hw.get("time"))
        height = hw.get("height_m")
        h_text = f" ({height:+.1f} ม.)" if height is not None else ""
        worse.append((icon("moon", 20), f"น้ำหนุนสูงสุด {thai_clock_exact(hw_dt)}{h_text}"))
    if mm is not None and mm >= 30:
        worse.append((icon("rain", 20), f"ฝนสะสม {mm:.0f} มม. ใน 24 ชม."))
    if pc["fail"] + pc["idle"] > 0:
        worse.append((icon("pump", 20), f"ปั๊มบึงมีปัญหา {pc['fail'] + pc['idle']} จุด"))
    if st["fresh_crit"] > 0:
        worse.append((icon("wave", 20), f"คลองเกินเส้นอันตราย {st['fresh_crit']} จุด"))
    if forecast.get("direction") == "rising":
        worse.append((icon("rain", 20), "ฝนตามพยากรณ์กำลังเพิ่มขึ้น"))
    if not worse:
        worse.append((icon("clock", 20), "ยังไม่มีสัญญาณแย่ลงชัดเจนตอนนี้"))

    tide = area.get("tide") or {}
    highs = tide.get("next_high") or []
    if len(highs) >= 2:
        h0, h1 = highs[0].get("height_m"), highs[1].get("height_m")
        if h0 is not None and h1 is not None and h1 < h0:
            better.append((icon("moon", 20), "น้ำหนุนรอบถัดไปต่ำกว่ารอบนี้"))
    if forecast.get("direction") == "falling":
        better.append((icon("rain", 20), "ฝนตามพยากรณ์กำลังเบาลง"))
    if pc["total"] > 0 and pc["fail"] == 0 and pc["idle"] == 0:
        better.append((icon("pump", 20), "ปั๊มบึงเดินปกติทุกจุด"))
    if st["fresh_near"] and st["fresh_crit"] == 0:
        better.append((icon("wave", 20), "คลองรอบบ้านอยู่ในเกณฑ์ปกติ"))
    if not better:
        better.append((icon("clock", 20), "ยังไม่มีสัญญาณดีขึ้นชัดเจนตอนนี้"))

    def bullets_html(rows):
        return "".join(f"<li>{ic}<span>{text}</span></li>" for ic, text in rows)

    return (
        '<div class="wb-grid">'
        '<div class="wb-card worse"><h3>สัญญาณว่าอาจแย่ลง</h3>'
        f'<ul class="wb-list">{bullets_html(worse)}</ul></div>'
        '<div class="wb-card better"><h3>สัญญาณว่าอาจดีขึ้น (ยังคงระวังต่อ)</h3>'
        f'<ul class="wb-list">{bullets_html(better)}</ul>'
        '<p class="action">แม้สัญญาณดีขึ้น ให้เก็บของที่ยกไว้ต่อจนน้ำในซอยลงหมด</p></div>'
        '</div>'
    )


# ---------------- optional advice section (5 short suggestions) --------------

# SAFETY_FACT (2026-09-26, maintainer-requested after the คลองจั่น electrocution death):
# stated as a FACT, never a command -- never "ไม่ต้อง/ห้าม/ไม่ควร".
SAFETY_FACT = ("⚠ วันนี้มีผู้เสียชีวิตจากไฟฟ้าดูดในน้ำท่วมที่แฟลตคลองจั่น (ข่าว 26 ก.ย.) "
               "— ไฟฟ้ากับน้ำท่วมอันตรายถึงชีวิต")

ADVICE_ITEMS = [
    # Moved to first place 2026-09-26 (same incident) -- an optional suggestion, not a
    # command ("เลี่ยง", not "ห้าม/ไม่ควร").
    ("bolt", "ปิดเบรกเกอร์ชั้นล่าง และเลี่ยงน้ำใกล้เสาไฟ/ปลั๊ก/รถที่จมน้ำ"),
    ("pump", "ยกของสำคัญขึ้นที่สูง"),
    ("phone", "ชาร์จมือถือ เตรียมไฟฉาย"),
    ("exit", "จอดรถในจุดที่น้ำไม่ถึง"),
    ("hospital", "เตรียมยาประจำตัว 3–5 วัน"),
    ("doc", "ติดตามป้ายเตือนก่อนออกจากบ้าน"),
]


def build_advice_html():
    items = "".join(f'<li>{icon(ic, 20)}<span>{esc(text)}</span></li>' for ic, text in ADVICE_ITEMS)
    return f'<ul class="advice-list">{items}</ul>'


# ---------------- water balance (Toledo PROP-FLOOD-03, proposal, PR #60 pending) --------

_TAG_LABEL_TH = {"VERIFIED": "ยืนยันแล้ว", "MEASURED": "วัดจากไฟล์ข้อมูล", "RELAYED": "ข่าว/บุคคลที่สาม",
                 "OPEN": "ยังไม่มีคำตอบ", "official_report": "ทางการแถลง"}


def _tag_pill(tag):
    label = _TAG_LABEL_TH.get(tag, tag or "")
    cls = (tag or "").lower()
    return f'<span class="tag-pill tag-{esc(cls)}">{esc(label)}</span>'


def build_capacity_mini_table(records):
    """'ขีดความสามารถ กทม.' mini-table -- VERIFIED/MEASURED rows first, RELAYED/OPEN
    marked clearly. `records` is data.json's `capacity_records` (bma_capacity.json's own
    curated list, unchanged)."""
    if not records:
        return '<p class="small">ไม่มีข้อมูลขีดความสามารถ กทม. ที่โหลดได้</p>'
    order = {"VERIFIED": 0, "MEASURED": 1, "RELAYED": 2, "OPEN": 3}
    rows = sorted(records, key=lambda r: order.get(r.get("tag"), 9))
    # Size-budget fix 2026-09-26: capped at 16 rows (VERIFIED/MEASURED always included
    # first by the sort above) -- the full 32-row list lives in docs/CAPACITY.md and in
    # the standalone dist/data.json; this mini-table is a summary, not the record.
    shown, rest = rows[:10], rows[10:]
    out = ['<table class="mini-capacity-table"><thead><tr><th>รายการ</th><th>ค่า</th>'
           '<th>สถานะ</th></tr></thead><tbody>']
    for r in shown:
        value = r.get("value")
        unit = r.get("unit") or ""
        val_text = "ไม่พบ/OPEN" if value is None else f"{value} {esc(unit)}"
        out.append(f'<tr><td>{esc(r.get("key"))}</td>'
                    f'<td>{val_text}</td><td>{_tag_pill(r.get("tag"))}</td></tr>')
    out.append("</tbody></table>")
    if rest:
        out.append(f'<p class="small">อีก {len(rest)} รายการ (ส่วนใหญ่ RELAYED/OPEN) — '
                    f'ดู <code>docs/CAPACITY.md</code></p>')
    return "".join(out)


def build_bangkok_east_html(bangkok_east):
    """Bangkok-wide/east-zone upper-bound block -- maintainer decision 2026-09-26: shown
    ABOVE the village-level blocks. Plain arithmetic on declared inputs (A, C_pump, and
    the BMA's own 26 ก.ย. 13:00 briefing V/Q), never a hydraulic model -- every number
    here says so next to itself."""
    if not bangkok_east or not bangkok_east.get("available"):
        return '<p class="small">ยังไม่มีข้อมูลภาพรวมกรุงเทพฯ/โซนตะวันออก</p>'

    parts = ['<div class="fcard waterbalance-city">',
             '<h3>ภาพรวมกรุงเทพฯ / โซนตะวันออก (คำนวณจากตัวเลขที่ประกาศแล้วเท่านั้น)</h3>']

    ba = bangkok_east.get("briefing_arithmetic")
    if ba:
        days_range = ba.get("days_range_with_forecast_rain") or [ba.get("days_if_no_new_rain")]
        low, high = days_range[0], days_range[-1]
        range_text = f"{low:.1f}" if low == high else f"{low:.1f}–{high:.1f}"
        parts.append(
            '<p><strong>เวลาที่คาดว่าจะระบายน้ำค้างหมด</strong> (จากตัวเลขที่ กทม. แถลงเอง 13:00): '
            f'{ba["backlog_volume_m3"]:,.0f} ลบ.ม. ÷ ({ba["pumping_capacity_m3s"]:,.0f} ลบ.ม./วิ × 3,600) '
            f'= {ba["outflow_per_hour_m3"]:,.0f} ลบ.ม./ชม. ≈ '
            f'<span class="num">{ba["hours_if_no_new_rain"]:.0f} ชม. (≈{ba["days_if_no_new_rain"]:.1f} วัน)</span> '
            f'ถ้าฝนหยุดและสูบเต็มกำลัง — ตรงกับที่ กทม. แถลง {esc(ba.get("briefing_stated_days"))} '
            f'{_tag_pill("official_report")}</p>'
            f'<p class="small">รวมฝนที่ยังจะตกอีก (Open-Meteo คาด 24 ชม. ข้างหน้า, third-party, upper bound): '
            f'ช่วงเวลา {esc(range_text)} วัน — {esc(ba.get("caveat_th"))}</p>'
        )

    a_km2 = bangkok_east.get("area_km2")
    c_pump = bangkok_east.get("c_pump_m3s")
    parts.append(
        f'<p class="small">พื้นที่ที่ใช้คำนวณ: {a_km2:,.1f} ตร.กม. {_tag_pill(bangkok_east.get("area_tag"))} '
        f'(ยังไม่มีตัวเลขพื้นที่รับน้ำเฉพาะโซนตะวันออก จึงใช้พื้นที่กรุงเทพฯ ทั้งหมดแทน — เป็น upper bound '
        f'ที่กว้างกว่าโซนจริง) · กำลังสูบที่มีแหล่งอ้างอิงรวม {c_pump:,.0f} ลบ.ม./วินาที '
        f'(พระโขนง 155 {_tag_pill("MEASURED")}, อุโมงค์พระโขนง 60 {_tag_pill("MEASURED")}, '
        f'บึงหนองบอน 60 {_tag_pill("RELAYED")}, แสนแสบ-ลาดพร้าว 60 {_tag_pill("RELAYED")}) '
        f'เทียบกำลังสูบรวมทั้งเมืองที่รายงาน 1,200-1,300 ลบ.ม./วินาที {_tag_pill("RELAYED")}</p>'
    )

    rain_now_vol = bangkok_east.get("rain_now_volume_million_m3")
    outflow_hr = bangkok_east.get("outflow_capacity_per_hour_million_m3")
    if rain_now_vol is not None and outflow_hr is not None:
        ratio = bangkok_east.get("ratio_rain_now_vs_outflow_per_hour")
        parts.append(
            f'<p>ฝนที่ตกลงบนพื้นที่ต่อชั่วโมง ≈ <span class="num">{rain_now_vol:.2f}</span> ล้าน ลบ.ม. '
            f'เทียบสูบออกได้สูงสุด ≈ <span class="num">{outflow_hr:.2f}</span> ล้าน ลบ.ม./ชม. '
            f'({esc(bangkok_east.get("rain_source_note_th"))})'
            f'{f" — อัตราส่วน {ratio:.1f} เท่า" if ratio is not None else ""}</p>'
        )
    parts.append('<p class="small"><em>สัดส่วนไหลบ่า (c) และน้ำเก็บเริ่มต้น (S0) ยังไม่ได้ประกาศ '
                 '— นี่คือการเทียบตัวเลขต้นน้ำ/ปลายน้ำ (upper bound) ไม่ใช่ผลลัพธ์สมการสมดุลน้ำที่แท้จริง</em></p>')
    next_step = bangkok_east.get("next_step_th")
    if next_step:
        parts.append(f'<p class="small">ขั้นต่อไป: {esc(next_step)}</p>')
    parts.append("</div>")
    return "".join(parts)


def build_village_waterbalance_html(water_balance, labels):
    """This area's own PROP-FLOOD-03 ledger status -- REFUSED with reason codes today
    (village-level catchment/pump-capacity are not declared), never a guessed number."""
    if not water_balance:
        return ""
    status = water_balance.get("status")
    present = water_balance.get("inputs_present") or []
    missing = water_balance.get("inputs_missing") or []
    reasons = water_balance.get("reason_codes") or []

    field_th = {"A": "พื้นที่รับน้ำ", "c": "สัดส่วนไหลบ่า", "C_pump": "กำลังปั๊ม",
                "S0": "น้ำเริ่มต้นในบึง", "P": "ฝนตอนนี้", "tau": "ช่วงเวลาต่อรอบ",
                "gate_flag": "สถานะประตูน้ำ", "Q_out_meas": "อัตราสูบออกจริง"}

    def field_word(f):
        return field_th.get(f, f)

    present_html = "".join(f'<li class="ok">✔ {esc(field_word(f))}</li>' for f in present) or "<li>—</li>"
    missing_words = [field_word(f) for f in missing]
    missing_html = "".join(f'<li class="missing">✘ {esc(field_word(f))}</li>' for f in missing) or "<li>—</li>"

    if status == "REFUSED":
        sentence = f'ยังคำนวณไม่ได้ — ระบบปฏิเสธเพราะขาด: {esc(", ".join(missing_words) or "ไม่ทราบ")}'
    else:
        sentence = f'คำนวณได้: น้ำสะสม {esc(water_balance.get("S_next"))} ลบ.ม. (แนวโน้ม {esc(water_balance.get("trend"))})'

    return (
        f'<div class="fcard waterbalance-village">'
        f'<h3>{esc(labels.get("heading") or "")} (หน่วยย่อย)</h3>'
        f'<div class="wb-inputs-grid"><ul class="wb-inputs-present">{present_html}</ul>'
        f'<ul class="wb-inputs-missing">{missing_html}</ul></div>'
        f'<p class="wb-refused-sentence"><strong>{esc(sentence)}</strong></p>'
        f'<p class="small">รหัสเหตุผล: {esc(", ".join(reasons) or "—")} '
        f'(สูตรที่ลงทะเบียน PROP-FLOOD-03, ยังเป็นข้อเสนอ, PR #60 รอตรวจ)</p>'
        f'</div>'
    )


_SCENARIO_COLOR = {"c0": "#1e8f4e", "c50": "#d98c0f", "c100": "#c0392b", "d_jma": "#8e2411"}
_SCENARIO_DASH = {"d_jma": "3,2"}
_HALF_DAY_TH = [(0, 5, "เช้ามืด"), (6, 11, "เช้า"), (12, 16, "บ่าย"), (17, 19, "เย็น"), (20, 23, "คืน")]


def _half_day_word(hour):
    for lo, hi, word in _HALF_DAY_TH:
        if lo <= hour <= hi:
            return word
    return ""


def _fmt_end_time_th(iso, now_dt):
    """Rounded to a half-day per peer review 2026-09-26 -- exact hours stay in the JSON
    (end_time_utc), only the legend/table text is rounded."""
    if not iso:
        return "ยังไม่พ้นน้ำในช่วงที่คำนวณ"
    dt = to_bkk(iso)
    if dt is None:
        return "ไม่ทราบ"
    return f"{_half_day_word(dt.hour)} {dt.day} {THAI_MONTHS[dt.month - 1]}"


def _tide_windows(area):
    """±2h shaded windows around each declared next-high-water time -- 'น้ำหนุน — สูบออกได้ช้าลง'."""
    tide = (area or {}).get("tide") or {}
    highs = tide.get("next_high") or []
    windows = []
    for h in highs:
        dt = to_bkk(h.get("time"))
        if dt is None:
            continue
        windows.append((dt - datetime.timedelta(hours=2), dt + datetime.timedelta(hours=2)))
    return windows


def _svg_chart_frame(W, H, PAD_L, PAD_R, PAD_T, PAD_B, n, t0, now_dt, tide_windows,
                      forecast_coverage_hours=None):
    """Shared frame pieces: day gridlines/x-labels, 'now' marker, tide-window shading,
    and a grey unforecast band -- used by both the Bangkok and village panels so they
    stay visually aligned on the same x-axis."""
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    parts = []

    def x_of(h):
        return PAD_L + (h / n) * plot_w if n else PAD_L

    # grey "no forecast beyond here" band (peer-review fix -- never silently draw
    # padding-zero hours as if they were real forecast)
    if forecast_coverage_hours is not None and forecast_coverage_hours < n:
        gx = x_of(forecast_coverage_hours)
        parts.append(f'<rect x="{gx:.0f}" y="{PAD_T}" width="{(W - PAD_R - gx):.0f}" '
                     f'height="{plot_h}" fill="#d9dde2" opacity="0.5"/>')
        parts.append(f'<text x="{gx + 4:.0f}" y="{PAD_T + 11}" font-size="8" fill="#5b6472">'
                     f'ไม่มีพยากรณ์ — สมมติฝน 0</text>')

    # tide (high-water ±2h) shading
    for i, (w0, w1) in enumerate(tide_windows or []):
        h0 = (w0 - t0).total_seconds() / 3600.0 if t0 else None
        h1 = (w1 - t0).total_seconds() / 3600.0 if t0 else None
        if h0 is None or h1 is None or h1 < 0 or h0 > n:
            continue
        h0c, h1c = max(h0, 0), min(h1, n)
        x0, x1 = x_of(h0c), x_of(h1c)
        parts.append(f'<rect x="{x0:.0f}" y="{PAD_T}" width="{max(x1 - x0, 1):.0f}" '
                     f'height="{plot_h}" fill="#b39ddb" opacity="0.22"/>')
        if i == 0:
            parts.append(f'<text x="{x0 + 2:.0f}" y="{PAD_T + 22}" font-size="8" '
                         f'fill="#6a4fa0">น้ำหนุน — สูบออกได้ช้าลง</text>')

    # day gridlines + x labels
    for h in range(0, n + 1, 48):
        x = x_of(h)
        parts.append(f'<line x1="{x:.0f}" y1="{PAD_T}" x2="{x:.0f}" y2="{PAD_T + plot_h}" '
                     f'stroke="#d8dee6" stroke-width="1" stroke-dasharray="2,2"/>')
        label = f"+{h}ชม."
        if t0:
            dt_h = t0 + datetime.timedelta(hours=h)
            label = f"{_half_day_word(dt_h.hour)} {dt_h.day}/{dt_h.month}"
        parts.append(f'<text x="{x:.0f}" y="{H - 10}" font-size="8.5" fill="#5b6472" '
                     f'text-anchor="middle">{esc(label)}</text>')

    # "ตอนนี้" (now) marker at h=0
    x_now = x_of(0)
    parts.append(f'<line x1="{x_now:.0f}" y1="{PAD_T}" x2="{x_now:.0f}" y2="{PAD_T + plot_h}" '
                 f'stroke="#333" stroke-width="1.4"/>')
    parts.append(f'<text x="{x_now + 3:.0f}" y="{PAD_T + 10}" font-size="8.5" fill="#333">ตอนนี้</text>')

    return parts, x_of, plot_w, plot_h


def build_drain_timeline_svg(drain_timeline, now_dt, tide_windows=None):
    """Bangkok-wide panel: 3 scenarios sweeping the undeclared runoff fraction c in
    {0, 0.5, 1}, rain bars, day gridlines, now-marker, tide shading, grey unforecast
    band, and a shaded c=0..c=1 uncertainty band. Hand-written inline SVG (no
    matplotlib in the shipped page -- keeps the page well under the 300KB/artifact
    contract; a matplotlib rendering of this same chart ran ~140KB, mostly font-path
    bloat for Thai glyphs)."""
    if not drain_timeline:
        return '<p class="small">ยังไม่มีข้อมูลพยากรณ์ฝนพอสำหรับกราฟ</p>'

    W, H = 640, 280
    PAD_L, PAD_R, PAD_T, PAD_B = 56, 46, 18, 34
    scenarios = drain_timeline["scenarios"]
    n = drain_timeline["horizon_hours"]
    v_max = max(max(s["values_m3"]) for s in scenarios.values()) or 1.0
    v_max_m = v_max / 1_000_000.0
    plot_h = H - PAD_T - PAD_B

    def y_of(v_m3):
        v_m = v_m3 / 1_000_000.0
        frac = v_m / v_max_m if v_max_m else 0
        return PAD_T + plot_h - frac * plot_h

    t0 = to_bkk(drain_timeline.get("generated_at_utc"))
    frame_parts, x_of, plot_w, _ = _svg_chart_frame(
        W, H, PAD_L, PAD_R, PAD_T, PAD_B, n, t0, now_dt, tide_windows,
        forecast_coverage_hours=drain_timeline.get("forecast_coverage_hours"))

    rain = drain_timeline.get("rain_mm_hourly") or []
    rain_max = (max(rain) if rain else 1.0) or 1.0

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="กราฟเวลาระบายน้ำค้าง สามสถานการณ์" '
             f'xmlns="http://www.w3.org/2000/svg" class="drain-timeline-svg">']

    # rain bars (behind everything) -- rendered every RENDER_STRIDE hours to keep SVG
    # size well under the artifact-contract budget (a bar per literal hour over a 96h
    # horizon roughly doubled this chart's byte size for no visible gain at this width).
    RENDER_STRIDE = 4 if n > 48 else 1
    if rain:
        bar_w = max(plot_w / max(n, 1) * 0.7 * RENDER_STRIDE, 1)
        for h in range(0, n, RENDER_STRIDE):
            mm = rain[h] if h < len(rain) else 0
            if mm <= 0:
                continue
            bh = (mm / rain_max) * (plot_h * 0.3)
            bx = x_of(h)
            by = PAD_T + plot_h - bh
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_w:.0f}" height="{bh:.0f}" '
                         f'fill="#8ec9ee" opacity="0.5"/>')

    parts.extend(frame_parts)

    # y-axis labels (million m^3)
    for frac in (0, 0.5, 1.0):
        y = PAD_T + plot_h - frac * plot_h
        val = frac * v_max_m
        parts.append(f'<line x1="{PAD_L}" y1="{y:.0f}" x2="{W - PAD_R}" y2="{y:.0f}" '
                     f'stroke="#eef1f4" stroke-width="1"/>')
        parts.append(f'<text x="{PAD_L - 6}" y="{y + 3:.0f}" font-size="9" fill="#5b6472" '
                     f'text-anchor="end">{val:.0f}</text>')
    parts.append(f'<text x="12" y="{PAD_T + 8}" font-size="9" fill="#5b6472">ล้าน ลบ.ม.</text>')

    # c=0..c=1 uncertainty band (shaded fill between the two extreme scenarios) --
    # sampled every RENDER_STRIDE hours (see rain-bar comment above)
    idxs = sorted(set(list(range(0, n + 1, RENDER_STRIDE)) + [n]))
    c0, c100 = scenarios.get("c0"), scenarios.get("c100")
    if c0 and c100:
        top_pts = [(x_of(h), y_of(c100["values_m3"][h])) for h in idxs]
        bot_pts = [(x_of(h), y_of(c0["values_m3"][h])) for h in idxs]
        path_pts = top_pts + list(reversed(bot_pts))
        path = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in path_pts) + " Z"
        parts.append(f'<path d="{path}" fill="#c0392b" opacity="0.08"/>')

    # scenario lines (d_jma drawn thin+dashed per peer review, others solid)
    for key, s in scenarios.items():
        color = _SCENARIO_COLOR.get(key, "#333")
        dash = _SCENARIO_DASH.get(key)
        width = 1.4 if key == "d_jma" else 2.2
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        pts = " ".join(f"{x_of(h):.0f},{y_of(s['values_m3'][h]):.0f}" for h in idxs)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                     f'stroke-width="{width}"{dash_attr}/>')

    parts.append("</svg>")

    legend_rows = []
    for key, _, label_th in DRAIN_TIMELINE_SCENARIOS_LABELS:
        s = scenarios.get(key)
        if not s:
            continue
        color = _SCENARIO_COLOR.get(key, "#333")
        legend_rows.append(
            f'<li><span class="legend-swatch" style="background:{color}"></span>'
            f'{esc(label_th)} — {esc(_fmt_end_time_th(s.get("end_time_utc"), now_dt))}</li>'
        )

    return (
        '<div class="drain-timeline">'
        + "".join(parts)
        + f'<ul class="drain-legend">{"".join(legend_rows)}</ul>'
        + f'<p class="small drain-footnote">{esc(drain_timeline.get("footnote_th"))}</p>'
        + '</div>'
    )


DRAIN_TIMELINE_SCENARIOS_LABELS = [("c0", 0.0, "ฝนหยุด (c=0)"), ("c50", 0.5, "สมมติ (c=0.5)"),
                                    ("c100", 1.0, "ขอบบน (c=1)"),
                                    ("d_jma", 0.5, "แบบจำลองที่ฝนมากที่สุด (JMA, c=0.5)")]

_PUMP_SCENARIO_STYLE = {
    "pump0": {"color": "#c0392b", "dash": ""},
    "pump2": {"color": "#d98c0f", "dash": "5,3"},
    "pump2_gravity": {"color": "#1e8f4e", "dash": "2,2"},
}


def build_village_panel_svg(sammakorn_rough, now_dt, tide_windows=None):
    """Village (สัมมากร) panel: average excess-depth-above-pond-capacity per pump
    scenario (cm), a shaded band for the no-pump scenario reflecting the 1.5-4.6 km^2
    sub-area uncertainty, rain bars scaled to this panel's own forecast max, and the
    same now-marker/tide-shading frame as the Bangkok panel above it."""
    if not sammakorn_rough:
        return '<p class="small">ยังไม่มีข้อมูลประมาณหยาบสำหรับสัมมากร</p>'

    W, H = 640, 260
    PAD_L, PAD_R, PAD_T, PAD_B = 56, 46, 18, 34
    n = sammakorn_rough["horizon_hours"]
    scenarios = sammakorn_rough["scenarios"]
    band = sammakorn_rough.get("pump0_depth_band")
    all_vals = [v for s in scenarios.values() for v in s["values_cm"]]
    if band:
        all_vals += band["depth_high_cm"] + band["depth_low_cm"]
    v_max = max(all_vals) if all_vals else 1.0
    v_max = max(v_max, 1.0)
    plot_h = H - PAD_T - PAD_B

    def y_of(cm):
        frac = cm / v_max if v_max else 0
        return PAD_T + plot_h - frac * plot_h

    t0 = now_dt
    frame_parts, x_of, plot_w, _ = _svg_chart_frame(
        W, H, PAD_L, PAD_R, PAD_T, PAD_B, n, t0, now_dt, tide_windows,
        forecast_coverage_hours=sammakorn_rough.get("forecast_coverage_hours"))

    rain = sammakorn_rough.get("rain_mm_hourly") or []
    rain_max = (1.5 * max(rain)) if rain else 1.0
    rain_max = rain_max or 1.0

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" '
             f'aria-label="กราฟความลึกน้ำเฉลี่ยเหนือความจุบึงสัมมากร ประมาณหยาบ" '
             f'xmlns="http://www.w3.org/2000/svg" class="village-panel-svg">']

    RENDER_STRIDE = 4 if n > 48 else 1
    if rain:
        bar_w = max(plot_w / max(n, 1) * 0.7 * RENDER_STRIDE, 1)
        for h in range(0, n, RENDER_STRIDE):
            mm = rain[h] if h < len(rain) else 0
            if mm <= 0:
                continue
            bh = (mm / rain_max) * (plot_h * 0.3)
            bx = x_of(h)
            by = PAD_T + plot_h - bh
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_w:.0f}" height="{bh:.0f}" '
                         f'fill="#8ec9ee" opacity="0.5"/>')

    parts.extend(frame_parts)

    for frac in (0, 0.5, 1.0):
        y = PAD_T + plot_h - frac * plot_h
        val = frac * v_max
        parts.append(f'<line x1="{PAD_L}" y1="{y:.0f}" x2="{W - PAD_R}" y2="{y:.0f}" '
                     f'stroke="#eef1f4" stroke-width="1"/>')
        parts.append(f'<text x="{PAD_L - 6}" y="{y + 3:.0f}" font-size="9" fill="#5b6472" '
                     f'text-anchor="end">{val:.0f}</text>')
    parts.append(f'<text x="12" y="{PAD_T + 8}" font-size="9" fill="#5b6472">ซม. (เฉลี่ย)</text>')

    idxs = sorted(set(list(range(0, n + 1, RENDER_STRIDE)) + [n]))
    if band:
        top_pts = [(x_of(h), y_of(band["depth_high_cm"][h])) for h in idxs]
        bot_pts = [(x_of(h), y_of(band["depth_low_cm"][h])) for h in idxs]
        path_pts = top_pts + list(reversed(bot_pts))
        path = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in path_pts) + " Z"
        parts.append(f'<path d="{path}" fill="#c0392b" opacity="0.12"/>')

    for key, s in scenarios.items():
        style = _PUMP_SCENARIO_STYLE.get(key, {"color": "#333", "dash": ""})
        pts = " ".join(f"{x_of(h):.0f},{y_of(s['values_cm'][h]):.0f}" for h in idxs)
        dash_attr = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{style["color"]}" '
                     f'stroke-width="2.2"{dash_attr}/>')

    # annotate the no-pump plateau
    pump0 = scenarios.get("pump0")
    if pump0 and pump0["values_cm"]:
        last_h = len(pump0["values_cm"]) - 1
        ax, ay = x_of(last_h * 0.6), y_of(pump0["values_cm"][int(last_h * 0.6)])
        parts.append(f'<text x="{ax:.0f}" y="{(ay - 8):.0f}" font-size="9" fill="#c0392b" '
                     f'text-anchor="middle">ไม่ลดเอง — ต้องปั๊ม</text>')

    parts.append("</svg>")

    legend_rows = []
    labels_th = {"pump0": "ปั๊มไม่เดิน (ปัจจุบัน)", "pump2": "ปั๊ม 2 ลบ.ม./วิ",
                 "pump2_gravity": "ปั๊ม 2 + แรงโน้มถ่วง 1 หลัง กทม.ระบายหมด"}
    for key in ("pump0", "pump2", "pump2_gravity"):
        s = scenarios.get(key)
        if not s:
            continue
        style = _PUMP_SCENARIO_STYLE.get(key, {"color": "#333"})
        legend_rows.append(f'<li><span class="legend-swatch" style="background:{style["color"]}">'
                           f'</span>{esc(s.get("label_th") or labels_th.get(key, key))}</li>')

    band_low = band["depth_low_cm"][-1] if band else None
    band_high = band["depth_high_cm"][-1] if band else None
    range_note = (f'ช่วงความไม่แน่นอนของพื้นที่ (1.5-4.6 ตร.กม.) ให้ความลึกเฉลี่ย '
                  f'≈ {band_low:.0f}-{band_high:.0f} ซม. — ซอยต่ำสุดลึกกว่าค่าเฉลี่ยหลายเท่า '
                  f'(รายงานวันนี้ 30 ซม.)') if band_low is not None else ""

    return (
        '<div class="village-panel">'
        + "".join(parts)
        + f'<ul class="drain-legend">{"".join(legend_rows)}</ul>'
        + (f'<p class="small">{esc(range_note)}</p>' if range_note else "")
        + f'<p class="small">{esc(sammakorn_rough.get("caption_th"))}</p>'
        + f'<p class="small"><strong>{esc(sammakorn_rough.get("decisive_factor_th"))}</strong> '
        + f'{_tag_pill("INSTINCT")}</p>'
        + '</div>'
    )


_THAI_MONTH_SHORT = {9: "ก.ย.", 10: "ต.ค."}


def build_daily_rain_table_html(compare, briefing=None):
    """'ฝน 7 วันข้างหน้า (6 แบบจำลอง)' table -- daily median(min-max) mm straight from
    forecast_7day_compare.json (never recomputed, per FORECAST_SPEC.md item 2), plus the
    model-disagreement flags and the TMD 24h official text (labelled official_forecast)
    /ONWR-HII OPEN gap, surfaced plainly rather than hidden. `briefing` (optional) is the
    build_briefing_summary() dict -- when it carries a `tmd_forecast_note_th` (TMD's own
    outlook relayed via the 26 ก.ย. 16:15 BMA/PM briefing: rain easing from 27 ก.ย.), that
    line is shown right next to this table, tagged official_report, never merged into the
    models' own median/min/max numbers above."""
    if not compare:
        return ""
    daily = compare.get("daily_open_meteo_mm") or {}
    rows = []
    for date_str, d in sorted(daily.items()):
        y, m, day = date_str.split("-")
        label = f"{int(day)} {_THAI_MONTH_SHORT.get(int(m), m)}"
        med, lo, hi = d.get("median"), d.get("min"), d.get("max")
        note = " ← ฝนเบา" if (med is not None and med < 6) else ""
        rows.append(f'<tr><td>{esc(label)}</td>'
                    f'<td>{med:.0f} ({lo:.0f}-{hi:.0f}){esc(note)}</td></tr>')
    table_html = ('<div class="tablewrap"><table class="daily-rain-table">'
                  '<thead><tr><th>วัน</th><th>ฝนคาดการณ์ มม./วัน มัธยฐาน (ต่ำสุด-สูงสุด)</th></tr></thead>'
                  f'<tbody>{"".join(rows)}</tbody></table></div>')

    flags = compare.get("flags") or {}
    flag_lines = []
    for f in (flags.get("model_disagreement") or []) + (flags.get("heavy_burst_gt_50mm_after_today") or []):
        flag_lines.append(f'<p class="small flag-line">⚠ {esc(f)}</p>')

    tmd = (compare.get("sources") or {}).get("tmd") or {}
    tmd_html = ""
    if tmd:
        tmd_html = (f'<p class="small">{_tag_pill("official_report")} กรมอุตุฯ 24 ชม.: '
                    f'{esc(tmd.get("content"))} — ยังไม่มีพยากรณ์ 7 วันเป็นตัวเลขจากหน่วยงานรัฐที่ดึงได้</p>')

    briefing_tmd_note = (briefing or {}).get("tmd_forecast_note_th")
    briefing_tmd_html = ""
    if briefing_tmd_note:
        briefing_tmd_html = (
            f'<p class="small">{_tag_pill("official_report")} กทม. แถลง 16:15 (อ้างอิงกรมอุตุฯ): '
            f'{esc(briefing_tmd_note)} — สอดคล้องกับตัวเลขมัธยฐานของแบบจำลองข้างต้นที่ลดลง '
            f'27-29 ก.ย.</p>'
        )

    return (
        '<div class="fcard daily-rain-card">'
        '<h3>ฝน 7 วันข้างหน้า (6 แบบจำลอง)</h3>'
        + table_html
        + "".join(sorted(set(flag_lines)))
        + tmd_html
        + briefing_tmd_html
        + '</div>'
    )


def build_combined_chart_html(drain_timeline, sammakorn_rough, now_dt, tide_windows,
                               include_village_panel, forecast_7day_compare=None,
                               briefing=None):
    coverage = (drain_timeline or {}).get("forecast_coverage_hours")
    horizon = (drain_timeline or {}).get("horizon_hours")
    gap_note = (f"ฝนหลังชั่วโมงที่ {coverage} ยังไม่รวม (พื้นที่สีเทาในกราฟ) · "
                if (coverage is not None and horizon is not None and coverage < horizon) else "")
    caveat = (f'<p class="waterbalance-caveat"><strong>คำเตือนก่อนดูกราฟ:</strong> '
              f'ประมาณหยาบ ๆ ไม่ใช่พยากรณ์ทางการ · {gap_note}'
              'ไม่รวมน้ำจากจังหวัดรอบ · '
              'การสูบจริงลดลงช่วงน้ำหนุน (พื้นที่สีม่วงในกราฟ)</p>')
    top = ('<div class="fcard drain-timeline-card">'
           '<h3>เส้นเวลาระบายน้ำค้าง — กรุงเทพฯ/โซนตะวันออก (4 สถานการณ์)</h3>'
           + build_drain_timeline_svg(drain_timeline, now_dt, tide_windows)
           + '</div>'
           + build_daily_rain_table_html(forecast_7day_compare, briefing=briefing))
    if not include_village_panel:
        return caveat + top
    bottom = ('<div class="fcard village-panel-card">'
              '<h3>สัมมากร — ความลึกน้ำเฉลี่ยเหนือความจุบึง (ประมาณหยาบ ๆ ทุกตัวแปรติดป้าย)</h3>'
              + build_village_panel_svg(sammakorn_rough, now_dt, tide_windows)
              + '</div>')
    return caveat + top + bottom


def build_waterbalance_section_html(area_id, water_balance, bangkok_east, capacity_records,
                                     labels, drain_timeline=None, now_dt=None,
                                     sammakorn_rough=None, tide_windows=None,
                                     forecast_7day_compare=None, briefing=None):
    # Size budget fix 2026-09-26: the Bangkok-wide chart/arithmetic/capacity table are
    # IDENTICAL regardless of which area tab is open (they are city-wide, not
    # area-specific) -- rendering them once per area doubled the page past the 300KB
    # artifact-contract budget. They now render ONLY inside the sammakorn block (which is
    # also the block carrying the village-level chart panel); the ram53 block gets a
    # short pointer instead of a byte-for-byte duplicate.
    if area_id != "sammakorn":
        pointer = ('<p class="small">ภาพรวมกรุงเทพฯ/โซนตะวันออก, กราฟเส้นเวลาระบายน้ำ, '
                   'ฝน 7 วันข้างหน้า และตารางขีดความสามารถ กทม. เป็นข้อมูลระดับเมืองเดียวกันทั้งสองพื้นที่ '
                   '— ดูที่แท็บ "หมู่บ้านสัมมากร" ด้านบน</p>')
        return pointer + build_village_waterbalance_html(water_balance, labels)

    chart_html = build_combined_chart_html(drain_timeline, sammakorn_rough, now_dt,
                                            tide_windows, include_village_panel=True,
                                            forecast_7day_compare=forecast_7day_compare,
                                            briefing=briefing)
    return (
        build_bangkok_east_html(bangkok_east)
        + chart_html
        + build_village_waterbalance_html(water_balance, labels)
        + '<div class="fcard capacity-mini">'
        + '<h3>ขีดความสามารถ กทม. (สรุปย่อ)</h3>'
        + build_capacity_mini_table(capacity_records)
        + f'<p class="small">รายละเอียดเต็ม: <code>docs/CAPACITY.md</code></p></div>'
    )


# ---------------- BMA governor briefing 2026-09-26 13:00 (official_report) --------------

def build_briefing_hero_html(briefing):
    if not briefing:
        return "", " hidden"
    return f'<p class="briefing-hero">{esc(briefing.get("hero_line_th"))}</p>', ""


def build_forecast_briefing_line(briefing):
    if not briefing or not briefing.get("weather_system_note_th"):
        return ""
    return (f'<p class="small">{icon("doc", 16)} กทม. แถลง: '
            f'{esc(briefing.get("weather_system_note_th"))}</p>')


def build_help_briefing_html(briefing):
    if not briefing:
        return ""
    parts = ['<div class="fcard briefing-help">']
    hotlines = briefing.get("hotlines") or []
    if hotlines:
        parts.append(f'<p><strong>สายด่วน:</strong> {esc(", ".join(hotlines))}</p>')
    shelters = briefing.get("shelters") or {}
    if shelters:
        parts.append(f'<p><strong>ศูนย์พักพิง:</strong> {shelters.get("count")} แห่ง '
                      f'(รองรับ {shelters.get("capacity"):,} คน, ใช้แล้ว {shelters.get("in_use")} คน)</p>')
    households = briefing.get("households_affected_initial_survey")
    if households:
        parts.append(f'<p><strong>ครัวเรือนที่ได้รับผลกระทบ (สำรวจเบื้องต้น):</strong> '
                      f'ประมาณ {households:,} ครัวเรือน</p>')
    health_support = briefing.get("health_support_ready")
    if health_support:
        parts.append(f'<p><strong>หน่วยแพทย์พร้อม:</strong> {esc(health_support)}</p>')
    dispatch_support = briefing.get("disaster_response_support")
    if dispatch_support:
        parts.append(f'<p><strong>กำลังสนับสนุน:</strong> {esc(dispatch_support)}</p>')
    parking = briefing.get("temporary_parking") or []
    if parking:
        parts.append(f'<p><strong>จุดจอดรถชั่วคราว:</strong> {esc(", ".join(parking))}</p>')
    monday = briefing.get("monday_note_th")
    if monday:
        parts.append(f'<p><strong>วันจันทร์ 28 ก.ย.:</strong> {esc(monday)}</p>')
    parts.append(f'<p class="small">{_tag_pill("official_report")} จากแถลงผู้ว่าฯ 26 ก.ย. 2569 13:00</p>')
    parts.append("</div>")
    return "".join(parts)


# ---------------- canal graph (Toledo PROP-FLOOD-04, proposal) --------------------------
#
# Fixed schematic layout for the declared east-chain graph (site/inputs/canals/east_chain.yaml)
# -- a small, hand-declared set of named nodes, not a generic force-directed layout. Positions
# are a readable diagram, not a geographic projection (same "schematic, not a map" posture the
# repo's own README_bangkok_canals.md uses for KlongMap).
_CG_BOX_W, _CG_BOX_H = 132, 44
_CG_NODE_POS = {
    "ssb10": (10, 10), "ssb09": (170, 10), "ssb08": (330, 10),
    "ssb07": (490, 10), "ssb04": (650, 10), "pkn01": (810, 10),
    "banma": (10, 130), "sammakorn_pond": (170, 130), "wangyai": (330, 130),
    "tpk03": (490, 130), "pwt03": (650, 130), "pwt04": (810, 130),
    "ladkrabang": (650, 250), "south_outlet": (810, 250),
    "hmk01": (10, 250), "lbk03": (150, 250), "kjn01": (290, 250), "ram53_canal": (430, 250),
}
_CG_STATUS_COLOR = {
    "NORMAL": "#2E7D32", "WATCH": "#D68910", "CRITICAL": "#C0392B", "OVERBANK": "#8E2A1F",
    "NO_GAUGE": "#8A9AA0", "NO_DATA": "#8A9AA0", "NO_THRESHOLD": "#8A9AA0",
}
_CG_HIGHLIGHT_NODE = "sammakorn_pond"


def _cg_inset(x1, y1, x2, y2, inset=70):
    import math
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    return (round(x1 + ux * inset, 1), round(y1 + uy * inset, 1),
            round(x2 - ux * inset, 1), round(y2 - uy * inset, 1))


def build_canal_graph_synthesis_th(canal_graph):
    """One line, generated ONLY from today's edge/node readouts (never a forecast) --
    the maintainer's own example shape: which measured reaches are flowing which way,
    which gates are locked, which reaches have no gauge at all."""
    if not canal_graph or not canal_graph.get("available"):
        return "ยังไม่มีข้อมูลผังคลองวันนี้"
    nodes = canal_graph.get("nodes") or {}
    edges = canal_graph.get("edges") or []
    parts = []

    measured = []
    for e in edges:
        if e["status"] == "OK" and e["direction"] in ("FORWARD", "REVERSE"):
            u_label = (nodes.get(e["u"]) or {}).get("label_th") or e["u"]
            v_label = (nodes.get(e["v"]) or {}).get("label_th") or e["v"]
            measured.append(f"{u_label}→{v_label}" if e["direction"] == "FORWARD"
                             else f"{v_label}→{u_label}")
    if measured:
        parts.append("น้ำวัดได้จริงตอนนี้: " + " · ".join(measured))

    locked_labels = sorted({
        (nodes.get(e["locked_node"]) or {}).get("label_th") or e["locked_node"]
        for e in edges if e["status"] == "CONTROLLED" and e.get("locked_node")
    })
    if locked_labels:
        parts.append("ประตูล็อก/ปิดกั้นอยู่: " + ", ".join(locked_labels))

    ungauged = sorted({
        n.get("label_th") or nid for nid, n in nodes.items() if n.get("status") == "NO_GAUGE"
    })
    if ungauged:
        parts.append(", ".join(ungauged) + " ไม่มีเครื่องวัด")

    return " · ".join(parts) if parts else "วันนี้ยังไม่มีทิศทางที่ยืนยันได้จากเครื่องวัดจริง"


def build_canal_graph_svg(canal_graph):
    """Inline SVG 'ผังคลอง' flow diagram: boxes = declared nodes (name + level m + status
    colour), arrows = edges coloured by readout (blue solid = measured direction, grey
    dashed = unresolved/refused/no gauge, orange = controlled/locked, with a lock glyph).
    An edge whose design_direction is declared but not measured gets a thin grey outline
    arrow instead of a solid one -- never presented the same as a live reading."""
    if not canal_graph or not canal_graph.get("available"):
        return ""
    nodes = canal_graph.get("nodes") or {}
    edges = canal_graph.get("edges") or []

    max_x = max((p[0] for p in _CG_NODE_POS.values()), default=0) + _CG_BOX_W + 10
    max_y = max((p[1] for p in _CG_NODE_POS.values()), default=0) + _CG_BOX_H + 10

    parts = [
        f'<svg class="canal-graph-svg" viewBox="0 0 {max_x} {max_y}" '
        f'role="img" aria-label="ผังคลอง น้ำไหลจากไหนไปไหนตอนนี้">',
        '<defs>'
        '<marker id="cgArrB" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L8,4L0,8Z" fill="#1F7A8C"/></marker>'
        '<marker id="cgArrO" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L8,4L0,8Z" fill="#D68910"/></marker>'
        '<marker id="cgArrG" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0L8,4L0,8Z" fill="#8A9AA0"/></marker>'
        '</defs>'
    ]

    # -- edges first, so node boxes drawn after sit visually on top of the line ends --
    for e in edges:
        u_id, v_id = e["u"], e["v"]
        if u_id not in _CG_NODE_POS or v_id not in _CG_NODE_POS:
            continue
        ux, uy = _CG_NODE_POS[u_id]
        vx, vy = _CG_NODE_POS[v_id]
        ucx, ucy = ux + _CG_BOX_W / 2, uy + _CG_BOX_H / 2
        vcx, vcy = vx + _CG_BOX_W / 2, vy + _CG_BOX_H / 2
        x1, y1, x2, y2 = _cg_inset(ucx, ucy, vcx, vcy)

        status, direction = e["status"], e.get("direction")
        design_dir = e.get("design_direction") or "unknown"
        reverse_arrow = (direction == "REVERSE") or (direction is None and design_dir == "v_to_u")

        if status == "OK" and direction in ("FORWARD", "REVERSE"):
            cls, marker = "cg-edge-measured", "cgArrB"
        elif status == "CONTROLLED":
            cls, marker = "cg-edge-controlled", "cgArrO"
        else:
            cls, marker = "cg-edge-design" if design_dir != "unknown" else "cg-edge-unknown", "cgArrG"

        if reverse_arrow:
            x1, y1, x2, y2 = x2, y2, x1, y1
        marker_attr = "" if design_dir == "unknown" and status not in ("OK", "CONTROLLED") else f' marker-end="url(#{marker})"'
        parts.append(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{marker_attr}/>')
        if status == "CONTROLLED":
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            parts.append(f'<text class="cg-lock" x="{mx}" y="{my - 6}" text-anchor="middle">🔒</text>')

    # -- node boxes on top --
    for nid, n in nodes.items():
        if nid not in _CG_NODE_POS:
            continue
        x, y = _CG_NODE_POS[nid]
        color = _CG_STATUS_COLOR.get(n.get("status"), "#8A9AA0")
        label = esc(n.get("label_th") or nid)
        value = n.get("value_m")
        value_txt = f"{value:.2f} ม." if isinstance(value, (int, float)) else "ไม่มีเครื่องวัด"
        highlight = ' class="cg-node cg-node-hi"' if nid == _CG_HIGHLIGHT_NODE else ' class="cg-node"'
        parts.append(
            f'<g{highlight}>'
            f'<rect x="{x}" y="{y}" width="{_CG_BOX_W}" height="{_CG_BOX_H}" rx="6" '
            f'fill="var(--surface)" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x + _CG_BOX_W / 2}" y="{y + 17}" text-anchor="middle" class="cg-node-label">{label}</text>'
            f'<text x="{x + _CG_BOX_W / 2}" y="{y + 33}" text-anchor="middle" class="cg-node-value" fill="{color}">{esc(value_txt)}</text>'
            f'</g>'
        )

    parts.append('</svg>')
    return "".join(parts)


def build_canal_graph_section_html(canal_graph):
    """'ผังคลอง — น้ำไหลจากไหนไปไหน (ตอนนี้)' -- synthesis line always visible, full
    diagram inside a <details> that is collapsed by default (same convention as every
    other <details> in this template)."""
    if not canal_graph or not canal_graph.get("available"):
        return ""
    synthesis = esc(build_canal_graph_synthesis_th(canal_graph))
    svg = build_canal_graph_svg(canal_graph)
    legend = (
        '<p class="cg-legend small">'
        '<span class="cg-legend-item"><span class="cg-swatch cg-swatch-blue"></span>ทิศทางวัดได้จริง</span> '
        '<span class="cg-legend-item"><span class="cg-swatch cg-swatch-orange"></span>ประตูล็อก/ปิดกั้น</span> '
        '<span class="cg-legend-item"><span class="cg-swatch cg-swatch-grey"></span>ไม่มีเครื่องวัด/ไม่ยืนยัน</span>'
        '</p>'
    )
    return (
        '<section class="canal-graph-wrap" aria-label="ผังคลองน้ำไหลจากไหนไปไหน">'
        f'<p class="cg-synthesis">{synthesis}</p>'
        '<details id="canal-graph-details">'
        '<summary><span>ผังคลอง — น้ำไหลจากไหนไปไหน (ตอนนี้)</span></summary>'
        + legend + svg +
        '<p class="small">ทิศทางมาจากการเทียบระดับน้ำสองจุดจริง (readout) — เส้นบาง/เทาคือคลองที่ยังไม่มี'
        'เครื่องวัดครบสองฝั่ง แสดงแค่ทิศทางที่ออกแบบไว้ (relay, ไม่ใช่การวัด)</p>'
        '</details></section>'
    )


# ---------------- one area's full fragment map ----------------

def build_area_fragments(area_id, area, now_dt, forecast, bangkok_east=None, briefing=None,
                          capacity_records=None, drain_timeline=None, sammakorn_rough=None,
                          forecast_7day_compare=None, canal_graph=None):
    labels = AREA_LABELS[area_id]
    pumps = area.get("pumps") or []
    pc = pump_counts(pumps, now_dt)
    st = compute_status(area, now_dt, pc)

    rain_forecast_note = area.get("rain_forecast_area_note")
    watch_line = build_watch_line(area, st, pc, now_dt, forecast)
    indicator_tiles = build_indicator_tiles(area, st, pc, now_dt, labels["pond_word"])
    hours_list = build_hours_list(area, st, pc, now_dt, forecast, area_id=area_id)
    wb_html = build_worsen_better_html(area, st, pc, now_dt, forecast)
    advice_html = build_advice_html()

    staleness = area.get("staleness") or {}
    newest = staleness.get("newest_official_obs")
    status_note = f"ดูจากเครื่องวัดของ กทม. เมื่อ {fmt_hm(newest)}" if newest else "ยังไม่มีเวลาที่อ่านค่าล่าสุด"
    status_note += " · รวบรวมโดยประชาชน ไม่ใช่ประกาศทางการ"
    now_line = build_now_line(area)

    # Red-team fix MEDIUM-5 (2026-09-26): this used to compute its own "any row older
    # than 2h" check, treating a row with NO observed_at at all (a reference-only row
    # such as BKK013/BKK015, which never carries a live timestamp) the same as a row
    # that IS live but stale -- so the banner was pinned on permanently regardless of how
    # fresh the real data was. It now reuses the same `staleness` dict build_data.py
    # already computed (which correctly excludes null-observed_at rows and keys off the
    # newest live official observation), so the page and data.json can never disagree.
    stale_ribbon_hidden = "" if staleness.get("banner") else " hidden"
    # LOW-6: on total failure (no live official observation at all -- not merely an old
    # one), say so plainly instead of the "some data is old" wording, which implies fresh
    # data exists somewhere on the page.
    stale_ribbon_text = ("ไม่มีข้อมูลล่าสุดจากหน่วยงาน — เตรียมพร้อมไว้ก่อน"
                          if not staleness.get("newest_official_obs")
                          else "ข้อมูลบางส่วนเก่า — ดูเวลาท้ายแต่ละบรรทัด")

    zones_html = build_zones_html(area)
    pump_rows_html, pump_lead = build_pump_rows(area, now_dt)
    canal_north, canal_south, canal_stale, canal_upstream = build_canal_rows(area, now_dt)
    rain_text, fc_text, tide_next, tide_basis, tide_week_rows, tide_week_more_rows, dds_html = \
        build_forecast_fragments(area, now_dt, forecast, rain_forecast_note)
    exit_rows = build_exit_rows(area)
    floodroad_rows = build_floodroad_rows(area, now_dt)
    community_rows = build_community_rows(area)
    nearby_community_rows, nearby_community_hidden = build_nearby_community_rows(area)
    hospital_rows = build_hospital_rows(area)

    tide_windows = _tide_windows(area)
    waterbalance_section_html = build_waterbalance_section_html(
        area_id, area.get("water_balance"), bangkok_east, capacity_records, labels,
        drain_timeline=drain_timeline, now_dt=now_dt, sammakorn_rough=sammakorn_rough,
        tide_windows=tide_windows, forecast_7day_compare=forecast_7day_compare,
        briefing=briefing)
    briefing_hero_html, briefing_hero_hidden = build_briefing_hero_html(briefing)
    briefing_forecast_line = build_forecast_briefing_line(briefing)
    # Identical between areas (city-wide briefing) -- render once (sammakorn/default
    # tab) to stay under the page size budget, same reasoning as the water-balance chart.
    briefing_help_html = build_help_briefing_html(briefing) if area_id == "sammakorn" else ""
    fc_text = fc_text + briefing_forecast_line

    # Identical between areas (both share nodes on the same declared east-chain graph,
    # e.g. ssb07) -- render the full diagram once (sammakorn tab) for the size budget,
    # same reasoning as the water-balance chart/bangkok_east block above; ram53 gets a
    # short pointer with its own always-visible synthesis line (never a silent drop).
    if area_id == "sammakorn":
        canal_graph_section_html = build_canal_graph_section_html(canal_graph)
    else:
        synthesis = esc(build_canal_graph_synthesis_th(canal_graph))
        canal_graph_section_html = (
            '<section class="canal-graph-wrap" aria-label="ผังคลองน้ำไหลจากไหนไปไหน">'
            f'<p class="cg-synthesis">{synthesis}</p>'
            '<p class="small">ผังคลองแบบเต็ม (โซนตะวันออกร่วมกันทั้งสองพื้นที่) — '
            'ดูที่แท็บ "หมู่บ้านสัมมากร" ด้านบน</p></section>'
        ) if canal_graph and canal_graph.get("available") else ""

    return {
        "{{PLACE_PIN}}": icon("pin", 16) + f'<span>{esc(labels["pin"])}</span>',
        "{{HEADING_LABEL}}": esc(labels["heading"]),
        "{{STATUS_WORD}}": esc(st["word"]),
        "{{NOW_LINE}}": esc(now_line),
        "{{SAFETY_FACT}}": esc(SAFETY_FACT),
        "{{STATUS_WATCH}}": watch_line,  # already HTML (has <strong> + icon)
        "{{WHY_LIST}}": indicator_tiles,
        "{{CANAL_GRAPH_SECTION_HTML}}": canal_graph_section_html,
        "{{HOURS_LIST}}": hours_list,
        "{{STATUS_NOTE}}": esc(status_note),
        "{{STALE_RIBBON_HIDDEN}}": stale_ribbon_hidden,
        "{{STALE_RIBBON_TEXT}}": esc(stale_ribbon_text),
        "{{WB_HTML}}": wb_html,
        "{{ADVICE_HTML}}": advice_html,
        "{{ZONES_HEADING}}": sec_label("wave", esc(labels["zones_heading"])),
        "{{ZONES_HTML}}": zones_html,
        "{{PUMP_HEADING}}": sec_label("pump", esc(labels["pump_heading"])),
        "{{PUMP_CAPTION}}": esc(labels["pump_caption"]),
        "{{PUMP_LEAD}}": esc(pump_lead),
        "{{PUMP_ROWS}}": pump_rows_html,
        "{{CANAL_NORTH_LABEL}}": esc(labels["canal_north_label"]),
        "{{CANAL_SOUTH_LABEL}}": esc(labels["canal_south_label"]),
        "{{CANAL_NORTH_ROWS}}": canal_north,
        "{{CANAL_SOUTH_ROWS}}": canal_south,
        "{{CANAL_UPSTREAM_ROWS}}": canal_upstream,
        "{{CANAL_STALE_ROWS}}": canal_stale,
        "{{RAIN_TEXT}}": rain_text,
        "{{RAIN_FORECAST_LINE}}": fc_text,
        "{{TIDE_NEXT}}": tide_next,
        "{{TIDE_BASIS}}": tide_basis,
        "{{TIDE_WEEK_ROWS}}": tide_week_rows,
        "{{TIDE_WEEK_MORE_ROWS}}": tide_week_more_rows,
        "{{DDS_QUOTES_HTML}}": dds_html,
        "{{EXIT_PLACE_WORD}}": esc(labels["exit_place_word"]),
        "{{EXIT_ROWS}}": exit_rows,
        "{{FLOODROAD_ROWS}}": floodroad_rows,
        "{{COMMUNITY_COL2_LABEL}}": esc(area.get("community_label") or "จุด"),
        "{{COMMUNITY_ROWS}}": community_rows,
        "{{NEARBY_COMMUNITY_ROWS}}": nearby_community_rows,
        "{{NEARBY_COMMUNITY_HIDDEN}}": nearby_community_hidden,
        "{{NEARBY_COMMUNITY_LABEL}}": esc(area.get("nearby_community_label") or ""),
        "{{HOSPITAL_ROWS}}": hospital_rows,
        "{{WATERBALANCE_SECTION_HTML}}": waterbalance_section_html,
        "{{BRIEFING_HERO_HTML}}": briefing_hero_html,
        "{{BRIEFING_HERO_HIDDEN}}": briefing_hero_hidden,
        "{{BRIEFING_HELP_HTML}}": briefing_help_html,
    }


def render_area_block(area_template, area_id, area, now_dt, forecast, hidden,
                       bangkok_east=None, briefing=None, capacity_records=None,
                       drain_timeline=None, sammakorn_rough=None, forecast_7day_compare=None,
                       canal_graph=None):
    block = area_template
    fragments = build_area_fragments(area_id, area, now_dt, forecast,
                                      bangkok_east=bangkok_east, briefing=briefing,
                                      capacity_records=capacity_records,
                                      drain_timeline=drain_timeline,
                                      sammakorn_rough=sammakorn_rough,
                                      forecast_7day_compare=forecast_7day_compare,
                                      canal_graph=canal_graph)
    for placeholder, value in fragments.items():
        block = block.replace(placeholder, value)
    block = block.replace("{{AREA_HIDDEN}}", " hidden" if hidden else "")
    block = block.replace("__AREA__", area_id)
    return block


# ---------------- top-level assembly ----------------

def strip_disallowed_wrapper_tags(html_text: str) -> str:
    """Publish-safety net: this page is a fragment (starts with <title>, no <!DOCTYPE>,
    <html>, <head>, <body>, or <meta charset/viewport>). Strip any such tags if they ever
    end up in the template so a future template edit cannot silently break the contract."""
    html_text = re.sub(r"<!DOCTYPE[^>]*>", "", html_text, flags=re.IGNORECASE)
    for tag in ("html", "head", "body"):
        html_text = re.sub(rf"</?{tag}[^>]*>", "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'<meta[^>]+charset=[^>]*>', "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'<meta\s+name=["\']viewport["\'][^>]*>', "", html_text, flags=re.IGNORECASE)
    return html_text.strip()


def wrap_full_document(fragment: str) -> str:
    """Wrap the <title>-first Artifact-contract fragment in a full HTML document (doctype,
    head with charset/viewport meta, lang="th", body) for GitHub Pages, which needs a
    standalone document rather than an embeddable fragment."""
    m = re.match(r"(<title>.*?</title>)(.*)", fragment, flags=re.DOTALL)
    if m:
        title_tag, rest = m.group(1), m.group(2)
    else:
        title_tag, rest = "<title>FloodConnect</title>", fragment
    return (
        "<!DOCTYPE html>\n"
        '<html lang="th">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"{title_tag}\n"
        "</head>\n"
        "<body>\n"
        f"{rest.strip()}\n"
        "</body>\n"
        "</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(HERE / "dist" / "data.json"))
    ap.add_argument("--template", default=str(HERE / "index.template.html"))
    ap.add_argument("--out", default=str(HERE / "dist" / "floodconnect.html"),
                     help="Artifact-contract fragment file (starts with <title>).")
    ap.add_argument("--out-full", default=str(HERE / "dist" / "index.html"),
                     help="Full HTML document (doctype/head/body) for GitHub Pages.")
    args = ap.parse_args()

    data_path = Path(args.data)
    template_path = Path(args.template)
    out_path = Path(args.out)
    out_full_path = Path(args.out_full)

    if not data_path.exists():
        print(f"ERROR: data file not found: {data_path}", file=sys.stderr)
        return 1
    if not template_path.exists():
        print(f"ERROR: template file not found: {template_path}", file=sys.stderr)
        return 1

    try:
        parsed = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {data_path} is not valid JSON: {e}", file=sys.stderr)
        return 1

    # Size budget fix 2026-09-26: everything in this page is already server-rendered
    # into HTML (the water-balance chart, capacity table, daily rain table etc.) --
    # the embedded <script id="data"> JSON only needs to carry what client JS actually
    # reads (recheckStaleness() reads `areas[*].stations_near`/`.pumps` observed_at
    # only, per index.template.html). Bulky fields that exist purely for build-time
    # HTML rendering are dropped from the EMBEDDED copy only; the standalone
    # dist/data.json written separately still has everything, unabridged.
    embed_parsed = dict(parsed)
    for _k in ("capacity_records", "drain_timeline", "sammakorn_rough", "forecast_7day_compare",
               "canal_graph"):
        embed_parsed.pop(_k, None)
    json_text = json.dumps(embed_parsed, ensure_ascii=False, separators=(",", ":"))
    json_text = json_text.replace("</script", "<\\/script")

    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        print(f"ERROR: placeholder {PLACEHOLDER!r} not found in {template_path}", file=sys.stderr)
        return 1
    if template.count(PLACEHOLDER) != 1:
        print(f"ERROR: placeholder {PLACEHOLDER!r} must appear exactly once", file=sys.stderr)
        return 1

    m = AREA_SLOT_RE.search(template)
    if not m:
        print("ERROR: AREA_TEMPLATE_START/END markers not found", file=sys.stderr)
        return 1
    area_template = m.group(1)

    now_dt = to_bkk(parsed.get("generated_at_bkk")) or datetime.datetime.now(BANGKOK_TZ)
    top_forecast = parsed.get("forecast")
    areas = parsed.get("areas") or {}
    default_area = parsed.get("default_area") or "sammakorn"
    bangkok_east = parsed.get("bangkok_east_water_balance")
    briefing = parsed.get("bma_briefing")
    capacity_records = parsed.get("capacity_records") or []
    drain_timeline = parsed.get("drain_timeline")
    sammakorn_rough = parsed.get("sammakorn_rough")
    forecast_7day_compare = parsed.get("forecast_7day_compare")
    canal_graph = parsed.get("canal_graph")

    static_ok = True
    try:
        blocks = []
        for area_id in ("sammakorn", "ram53"):
            area = areas.get(area_id)
            if area is None:
                continue
            # Each area now carries its OWN Open-Meteo forecast (own lat/lon) -- fall
            # back to the top-level (sammakorn's) forecast only if an area is missing it.
            area_forecast = area.get("forecast") or top_forecast
            blocks.append(render_area_block(area_template, area_id, area, now_dt, area_forecast,
                                             hidden=(area_id != default_area),
                                             bangkok_east=bangkok_east, briefing=briefing,
                                             capacity_records=capacity_records,
                                             drain_timeline=drain_timeline,
                                             sammakorn_rough=sammakorn_rough,
                                             forecast_7day_compare=forecast_7day_compare,
                                             canal_graph=canal_graph))
        area_sections_html = "".join(blocks)

        asof = fmt_hm(parsed.get("generated_at_bkk"))
        active_subtitle = f'{esc(AREA_LABELS[default_area]["subtitle"])} · อัปเดต {esc(asof)}'

        all_sources = parsed.get("all_sources") or []
        sources_list = build_sources_list(all_sources, now_dt)
        forecast_caveat_th = parsed.get("forecast_caveat_th")
        if forecast_caveat_th:
            sources_list += f'<li>{icon("doc", 16)}<span class="small">{esc(forecast_caveat_th)}</span></li>'
    except Exception as e:  # fail-soft: never crash with zero output
        print(f"WARNING: static server-side render failed ({e}); page will be degraded", file=sys.stderr)
        area_sections_html = ""
        active_subtitle = "FloodConnect"
        sources_list = ""
        static_ok = False

    def _area_slot_repl(_match, html=area_sections_html):
        return html

    template = AREA_SLOT_RE.sub(_area_slot_repl, template, count=1)
    template = template.replace("{{ACTIVE_SUBTITLE}}", active_subtitle)
    template = template.replace("{{SOURCES_LIST}}", sources_list)
    template = template.replace(PLACEHOLDER, json_text)

    # Any placeholder left unfilled must not leak into the shipped page as a literal string.
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", template)
    for ph in set(leftover):
        template = template.replace(ph, "")

    template = strip_disallowed_wrapper_tags(template)
    if not template.startswith("<title>"):
        print("ERROR: rendered page does not start with '<title>' -- publish-safety contract broken",
              file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB) from {data_path.name} + {template_path.name}; "
          f"static_ok={static_ok}")
    if size_kb > 300:
        print("WARNING: page exceeds the 300 KB budget", file=sys.stderr)

    full_doc = wrap_full_document(template)
    out_full_path.parent.mkdir(parents=True, exist_ok=True)
    out_full_path.write_text(full_doc, encoding="utf-8")
    print(f"wrote {out_full_path} ({out_full_path.stat().st_size / 1024:.1f} KB, full document)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
