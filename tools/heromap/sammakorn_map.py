#!/usr/bin/env python3
"""tools/heromap/sammakorn_map.py -- classification/normal-level helpers reused
across this repo's water-status code.

Removed 2026-09-28 (founder verbatim: "เอาเฟสนี้ออกจากหน้าสัมมากร ไม่ต้องใช้
แล้ว"): this module used to also render the "สถานะน้ำหมู่บ้าน" simplified hero-map
block (pond tank + canal rows + pump row + action line) wired into the Sammakorn page
by site/build_page.py::build_hero_map_html(). That render wiring, and every pure-HTML/
SVG-building helper it alone used, is retired along with it -- see the removal note
above site/build_page.py's own tile-grid section for what replaced it (the same four
flood drivers now fold into that page's existing .tile-grid instead).

What REMAINS here (reusable, imported by other tests/tools independent of any
rendering): `classify_tier()` / `worst_tier()` -- pure threshold bucketing of numbers
`site/build_data.py` already computed (`warning`/`critical`/`bank`/`value_m`, the same
kind of non-equation classification convention `docs/FLOW_STALL_TYPOLOGY.md` §4 calls
an "INSTINCT-rule", never a derivation); `load_normal_levels()` /
`_official_threshold_row_admissible()` -- loads + admissibility-guards
`sources/canal_normal_levels.yaml`; `pump_tier()` -- one pump station's tier from its
own status/machine counts. No new Toledo equation anywhere in this file.

Project decisions still binding on `classify_tier()`:
  1. "ไม่ปกติ ต้องต่ำกว่าเกณฑ์ปกติหรือเปล่า แค่นี้ยังไม่เรียกปกติ" -- a point is
     coloured "ปกติ" (green) ONLY when its live value is at/below its own
     declared `normal_level_m`. No baseline on record -> can never render
     green; classifies grey "ยังไม่มีเกณฑ์ปกติ" UNLESS it has already breached
     its own warning/critical/bank threshold (breach detection never depends
     on a "normal" baseline existing).
  2. Per-canal-side classification never rests on a single station where more
     than one is available; a station whose reading contradicts its immediate
     neighbours (e.g. WL.SSB.08) is never folded into a band's own colour.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_NORMAL_LEVELS_PATH = os.path.join(REPO_ROOT, "sources", "canal_normal_levels.yaml")

# ---------------------------------------------------------------------------
# tier classification (INSTINCT-rule bucketing, not a Toledo equation -- see
# module docstring)
# ---------------------------------------------------------------------------

TIER_STYLE = {
    "NORMAL":       {"color": "var(--ok)",           "word": "ปกติ"},
    "ABOVE_NORMAL": {"color": "var(--warning-text)",  "word": "สูงกว่าปกติ"},
    "WATCH":        {"color": "var(--warning-text)",  "word": "เตือน"},
    "CRITICAL":     {"color": "var(--alert)",         "word": "วิกฤต"},
    "OVERBANK":     {"color": "var(--alert-strong)",  "word": "ล้นตลิ่ง"},
    "NO_BASELINE":  {"color": "var(--neutral-text)",  "word": "ยังไม่มีเกณฑ์ปกติ"},
    "NO_GAUGE":     {"color": "var(--neutral-text)",  "word": "ไม่มีเครื่องวัด"},
    "OUTLIER":      {"color": "var(--neutral-text)",  "word": "ค่าเดี่ยวขัดกับเพื่อนบ้าน"},
    "NO_DATA":      {"color": "var(--neutral-text)",  "word": "ไม่มีข้อมูล"},
    "FAULT":        {"color": "var(--alert)",         "word": "ขัดข้อง"},
}


def classify_tier(value_m, warning=None, critical=None, bank=None, normal_level_m=None):
    """Bucket one live reading into a tier key + short Thai word.

    Order matters (project decision 2, module docstring): a breach of
    warning/critical/bank is checked FIRST and wins regardless of whether a
    normal-level baseline exists at all -- only once a reading is NOT in
    breach do we ask "is it actually at/below its own normal level" before
    ever calling it green. Returns (tier_key, word).
    """
    if value_m is None:
        return ("NO_DATA", TIER_STYLE["NO_DATA"]["word"])
    if bank is not None and value_m >= bank:
        return ("OVERBANK", TIER_STYLE["OVERBANK"]["word"])
    if critical is not None and value_m >= critical:
        return ("CRITICAL", TIER_STYLE["CRITICAL"]["word"])
    if warning is not None and value_m >= warning:
        return ("WATCH", TIER_STYLE["WATCH"]["word"])
    if normal_level_m is not None:
        if value_m <= normal_level_m:
            return ("NORMAL", TIER_STYLE["NORMAL"]["word"])
        return ("ABOVE_NORMAL", TIER_STYLE["ABOVE_NORMAL"]["word"])
    return ("NO_BASELINE", TIER_STYLE["NO_BASELINE"]["word"])


def worst_tier(tier_keys):
    """Pick the worst of several tier keys, by the same severity ladder the
    rest of the page uses (NORMAL < ABOVE_NORMAL < WATCH < CRITICAL <
    OVERBANK); the grey/no-data tiers never outrank a real breach and never
    get silently promoted to NORMAL."""
    rank = {"NORMAL": 0, "ABOVE_NORMAL": 1, "NO_BASELINE": 1, "NO_GAUGE": 0,
            "NO_DATA": 0, "OUTLIER": 0, "WATCH": 2, "CRITICAL": 3, "OVERBANK": 4,
            "FAULT": 3}
    real = [k for k in tier_keys if k not in ("NO_GAUGE", "NO_DATA", "OUTLIER")]
    pool = real or list(tier_keys)
    return max(pool, key=lambda k: rank.get(k, 0)) if pool else "NO_DATA"


# P0 fix, 2026-09-27 -- same guard as site/build_data.py's
# `_official_threshold_row_admissible()` (do not duplicate the incident, not the
# constant): an `official_threshold` row is only ever applied when it declares a
# same-station distance <= 100 m AND a confirmed (non-OPEN/unknown) datum. See that
# module's comment for the real incident (WL.BMA.02 vs ST.SPS.01, ~630 m apart) this
# guard exists to catch again.
OFFICIAL_THRESHOLD_MAX_DISTANCE_M = 100.0
_DATUM_UNKNOWN_VALUES = {None, "", "OPEN", "open", "unknown", "UNKNOWN", "UNCONFIRMED",
                         "unconfirmed"}


def _official_threshold_row_admissible(row):
    dist = row.get("station_distance_m")
    if dist is None:
        return False
    try:
        if float(dist) > OFFICIAL_THRESHOLD_MAX_DISTANCE_M:
            return False
    except (TypeError, ValueError):
        return False
    return row.get("datum") not in _DATUM_UNKNOWN_VALUES


def load_normal_levels(path=None):
    """Best-effort load of sources/canal_normal_levels.yaml -> {station_code:
    normal_level_m}. Returns {} on any error (missing file, missing PyYAML) --
    callers must treat an absent code as "no baseline", never crash. A
    `basis: official_threshold` row that fails `_official_threshold_row_admissible()`
    (mislocated and/or unconfirmed datum) is skipped -- never applied."""
    path = path or DEFAULT_NORMAL_LEVELS_PATH
    try:
        import yaml  # PyYAML -- optional, same convention as site/build_data.py
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        out = {}
        for row in doc.get("canals") or []:
            code = row.get("station_code")
            lvl = row.get("normal_level_m")
            if code is None or lvl is None:
                continue
            if row.get("basis") == "official_threshold" and not _official_threshold_row_admissible(row):
                continue
            out[code] = lvl
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# station / pump lookups from a data.json-shaped `area` dict
# ---------------------------------------------------------------------------

def pump_tier(p):
    """One pump station's tier + short Thai word. FAULT wins on
    `status_th == "ขัดข้อง"` regardless of the machine counts; otherwise
    reflects running/total machines at that station. `None` -> NO_DATA,
    never an invented running count."""
    if p is None:
        return ("NO_DATA", "ไม่มีข้อมูล")
    if p.get("status_th") == "ขัดข้อง":
        return ("FAULT", "ขัดข้อง")
    on, total = p.get("pumps_on"), p.get("pumps_total")
    if on is None or total is None or total == 0:
        return ("NO_DATA", "ไม่มีข้อมูล")
    if on == total:
        return ("NORMAL", f"เดิน {on}/{total}")
    return ("ABOVE_NORMAL", f"เดิน {on}/{total}")  # "partial" -- amber, not fault


