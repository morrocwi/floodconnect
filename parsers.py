#!/usr/bin/env python3
"""
Pure parsers for the newer sources this data system adds on top of live_water_level.py
(thaiwater canal_waterlevel / BMA PumpHistory / KlongMap parsers already live there and
are reused, not duplicated, by collect.py).

Every function here is pure (bytes/str/dict in, list/dict out) -- no network calls, no
file I/O beyond what's explicitly asked for a fixture in a test. Same discipline as
live_water_level.py: a record with no coordinate/value is skipped, never fabricated; a
block of text this pipeline chooses not to force into fields is returned as-is for the
caller to store verbatim in the `documents` table, never silently dropped.

No flood-risk score or formula is computed anywhere in this file (this workspace's
equation discipline) -- every returned value is a relayed/measured reading, nothing
derived.
"""
import datetime
import re

# --- thaiwater flood_road (api-v3.thaiwater.net .../public/flood_road) ------------------
#
# Schema confirmed 2026-09-26 from a real live fetch (262 records, every one agency-tagged
# "Department of Bangkok" i.e. สำนักการระบายน้ำ). `floodroad_value` ranges 0-35.6 across
# the sample (212 records at exactly 0) -- read as a flood-depth reading in cm (0 = dry),
# same telemetry shape as thaiwater_canal_waterlevel's canal_value; `station.floodroad_lat`
# /`floodroad_long` are real coordinates (0 missing in the sample), `floodroad_oldcode`
# mirrors canal_oldcode's "FL.<area>.<n>" scheme.

THAIWATER_FLOOD_ROAD_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road"


def parse_thaiwater_flood_road(data: dict) -> list:
    """
    `api-v3.thaiwater.net .../public/flood_road` JSON -> road-reading dicts.

    Returns [{station_id, road_name_th, floodroad_oldcode, lat, lon, value_cm,
    observed_at (UTC ISO, converted from local Thailand time), district_th, province_th,
    agency, source_url, fetched_at=None}]. A record with no coordinate is skipped, never
    fabricated (same rule as parse_thaiwater_canal_stations).
    """
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("floodroad_lat"), station.get("floodroad_long")
        if lat is None or lon is None:
            continue
        value = rec.get("floodroad_value")
        dt_str = rec.get("floodroad_datetime")
        observed_at = None
        if dt_str:
            try:
                local_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                local_dt = local_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                observed_at = local_dt.astimezone(datetime.timezone.utc).isoformat()
            except ValueError:
                observed_at = None
        geocode = rec.get("geocode") or {}
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        out.append({
            "station_id": str(station.get("id")) if station.get("id") is not None else None,
            "road_name_th": (station.get("floodroad_name") or {}).get("th"),
            "floodroad_oldcode": station.get("floodroad_oldcode"),
            "lat": float(lat),
            "lon": float(lon),
            "value_cm": float(value) if value is not None else None,
            "observed_at": observed_at,
            "district_th": (geocode.get("amphoe_name") or {}).get("th"),
            "province_th": (geocode.get("province_name") or {}).get("th"),
            "agency": agency,
            "source_url": THAIWATER_FLOOD_ROAD_URL,
            "fetched_at": None,
        })
    return out


# --- dds_flood_report (dds.bangkok.go.th/flood_report.php, server-rendered HTML) --------
#
# Two `<table class="blueTable">` blocks confirmed 2026-09-26: the FIRST is a per-district
# summary (รายการที่/พื้นที่เขต/จำนวนรายการ/ความยาวรวม -- 4 columns), the SECOND is the
# per-road detail table this pipeline actually wants (11 columns, see registry.yaml
# dds_flood_report entry). This parser targets the second table specifically by its
# header cell count, not by position, so it survives the page inserting/removing tables.

_HTML_TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
_HTML_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_HTML_TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S | re.I)
_HTML_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)

_FLOOD_ROAD_DETAIL_HEADERS = ["ลำดับที่", "พื้นที่เขต", "ถนน", "บริเวณ", "ความสูง",
                              "ความยาว", "กระทบผิวจราจร", "เวลาท่วม", "เวลาแห้ง",
                              "ระยะเวลาท่วม", "ปริมาณฝนรวม"]


def _strip_html_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_dds_flood_report_html(html: str) -> list:
    """
    BMA `flood_report.php` HTML -> per-road flood-detail row dicts.

    Finds the `<table>` whose header cells (`<th>`, tags/whitespace stripped) start with
    the same 11 column names confirmed 2026-09-26 (see module docstring), then reads every
    `<tr>` in its `<tbody>` (a `<tfoot>` "reported by ..." row is naturally skipped since
    it has one `colspan` cell, not 11). An empty cell (e.g. เวลาแห้ง/ระยะเวลาท่วม for a
    road still flooded at fetch time) becomes None, never a fabricated value.

    Returns [{seq, district_th, road_th, area_detail_th, flood_height_cm, flood_length_m,
    lanes_affected_th, flood_start, flood_end, flood_duration_th, rain_total_mm}]. Returns
    [] if no table with this header shape is found (page structure changed -- caller then
    stores the raw HTML as a document instead of silently reporting zero roads).
    """
    for table_html in _HTML_TABLE_RE.findall(html):
        header_cells = [_strip_html_tags(h) for h in _HTML_TH_RE.findall(table_html)]
        if len(header_cells) < len(_FLOOD_ROAD_DETAIL_HEADERS):
            continue
        if not all(header_cells[i].startswith(_FLOOD_ROAD_DETAIL_HEADERS[i][:4])
                   for i in range(len(_FLOOD_ROAD_DETAIL_HEADERS))):
            continue
        out = []
        for row_html in _HTML_TR_RE.findall(table_html):
            cells = [_strip_html_tags(c) for c in _HTML_TD_RE.findall(row_html)]
            if len(cells) != 11:
                continue  # tfoot's single colspan cell, or a malformed row -- skip, don't guess

            def _num(s):
                s = (s or "").replace(",", "").strip()
                if not s or s == "-":
                    return None
                try:
                    return float(s)
                except ValueError:
                    return None

            def _txt(s):
                s = (s or "").strip()
                return None if not s or s == "-" else s

            out.append({
                "seq": _txt(cells[0]),
                "district_th": _txt(cells[1]),
                "road_th": _txt(cells[2]),
                "area_detail_th": _txt(cells[3]),
                "flood_height_cm": _num(cells[4]),
                "flood_length_m": _num(cells[5]),
                "lanes_affected_th": _txt(cells[6]),
                "flood_start": _txt(cells[7]),
                "flood_end": _txt(cells[8]),
                "flood_duration_th": _txt(cells[9]),
                "rain_total_mm": _num(cells[10]),
            })
        return out
    return []


# --- dds_daily_pdf (dds.bangkok.go.th daily bulletin, via `pdftotext -layout`) ----------
#
# Section layout confirmed 2026-09-26 against a real downloaded issue (ฉบับที่ 269/69,
# 26 ก.ย. 2569) -- see docs/DATA_SYSTEM.md and the parser-spec note in this repo's history
# for the full per-section reasoning. This parser splits the full `pdftotext -layout`
# text on each section's own numbered Thai header (a stable anchor across issues, since
# the bulletin's own template numbers its sections 1-8 every day), then applies a regex
# per section. A section this parser does NOT reduce to fields (weather-forecast prose,
# the salinity table, the free-text incident log, and any Chao Phraya daily row that
# doesn't have the full 10-field layout -- e.g. the report date's own row is routinely
# incomplete, see scout notes) is returned verbatim for the caller to store in the
# `documents` table -- never force-parsed, never silently dropped.

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}

THAI_MONTH_ABBR = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}
_THAI_SHORT_DATE_RE = re.compile(
    r"(\d{1,2})\s*(" + "|".join(re.escape(k) for k in THAI_MONTH_ABBR) + r")\s*(\d{2})")


def thai_short_date_to_iso(s: str):
    """
    "20 ก.ย. 69" (day, Thai month abbreviation, 2-digit Buddhist-Era year) -> "2026-09-20"
    (Gregorian ISO date), or None if unrecognized.

    2-digit BE year handling (Dr-tier judgment, not a general calendar library): this
    bulletin only ever prints the last two digits of the Buddhist Era year, so this
    assumes the 2500s (`2500 + yy`) -- correct for any date in 2023-2099 CE (BE 2566-2642)
    and therefore correct for this pipeline's actual operating window. Do not reuse this
    assumption blindly decades from now.
    """
    m = _THAI_SHORT_DATE_RE.search(s or "")
    if not m:
        return None
    day, month_abbr, yy = m.groups()
    year_ce = 2500 + int(yy) - 543
    try:
        return datetime.date(year_ce, THAI_MONTH_ABBR[month_abbr], int(day)).isoformat()
    except ValueError:
        return None


# NOTE on Thai text corruption: this bulletin's PDF embeds a custom-encoded font that
# `pdftotext` extracts with SOME tone marks/subscript vowels (mai tho, mai ek, thanthakhat
# etc.) remapped to Unicode Private-Use-Area codepoints (U+F700-U+F8FF) instead of their
# real Thai codepoints -- confirmed 2026-09-26 (e.g. "ป้องกัน" extracts as "ป" + U+F706 +
# "องกัน"). Section anchors below are therefore deliberately truncated to end BEFORE the
# first character known to land in a PUA cell for that heading, so they still match by
# `str.find`. Captured field text (station/road names etc.) is passed through verbatim,
# PUA characters included -- this is a relayed, not-cleaned extraction artifact, never
# silently "corrected" (that would be guessing at the intended glyph, i.e. fabrication).
_SECTION_ANCHORS = [
    ("weather_forecast", "1. ลักษณะอากาศทั่วไป"),
    ("rainfall", "2. ปริมาณฝนในพื้นที่กรุงเทพมหานคร"),
    ("canal_outer", "3. ระดับน้ำพื้นที่ กทม. ภายนอก"),
    ("canal_inner", "4. ระดับน้ำพื้นที่ กทม. ภายใน"),
    ("chaophraya_flow_tide", "5. ปริมาณน้ำผ"),
    ("reservoirs", "6. ปริมาณน้ำในเขื่อน"),
    ("tide_dedicated", "7. ระดับน้ำทะเลหนุน"),
    ("salinity", "8. สถานการณคาความเค็ม"),
    ("narrative_log", "สรุปเหตุการณ"),
]

_HEADER_RE = re.compile(
    r"ประจำวัน\S*ที่\s*(\d{1,2})\s*(\S+)\s*(\d{4})\s*\(ฉบับที่\s*([\d/]+)\)")
_RAIN_ROW_RE = re.compile(r"^\s*(\d+)\s+จุดวัด\s+(.+?)\s{2,}([\d,]+\.\d+)\s*$")
_RAIN_REF_ROW_RE = re.compile(r"^\s*จุดวัด\s+(.+?)\s{2,}([\d,]+\.\d+)\s*$")
_CANAL_ROW_RE = re.compile(
    r"^(\d+)\.\s+(.+?)\s{2,}([+-]?\d+\.\d{2})\s+([+-]?\d+\.\d{2})\s+([+-]?\d+\.\d{2})\s+(\S.*?)\s*$")
# Built from THAI_MONTH_ABBR (all 12 abbreviations), not hard-coded to any one month --
# an earlier version hard-coded "ก.ย." (September) only, so from about 1 Oct every Chao
# Phraya/reservoir row silently dropped into `documents` with no warning (verified with a
# "ต.ค." row). `_THAI_MONTH_DATE_FRAGMENT` matches "<day> <abbrev> <2-digit BE year>" for
# any month.
_THAI_MONTH_DATE_FRAGMENT = (r"\d{1,2}\s*(?:" +
                              "|".join(re.escape(k) for k in THAI_MONTH_ABBR) + r")\s*\d{2}")
_CHAOPHRAYA_DATE_RE = re.compile(r"^(" + _THAI_MONTH_DATE_FRAGMENT + r")\s+(.*\S)\s*$")
_RESERVOIR_ROW_RE = re.compile(
    r"^(\d+)\.\s+(\S+)\s+([\d,]+)\s+([\d,]+\.\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"([+-][\d.]+)\s+(" + _THAI_MONTH_DATE_FRAGMENT + r")\s*$")
_TIDE7_ROW_RE = re.compile(
    r"^\s*(ขึ้นเต็มที่|ลงเต็มที่)\s+(\d{2}\.\d{2})\s+([+-]?\d+\.\d{2})\s+"
    r"(\d{2}\.\d{2})\s+([+-]?\d+\.\d{2})\s*$")

_CHAOPHRAYA_FIELDS = [
    "qmax_nakhonsawan_cms", "qmax_chaophraya_dam_cms", "qmax_rama6_dam_cms",
    "qmax_samkhok_cms", "tide_paklongtalat_time", "tide_paklongtalat_level_m",
    "tide_bangna_time", "tide_bangna_level_m", "tide_base_time", "tide_base_level_m",
]


def _split_sections(text: str) -> dict:
    """Splits `text` on `_SECTION_ANCHORS`, in the order they're declared (each anchor is
    searched for starting after the previous one's position, so a header word that also
    appears earlier in prose doesn't cut the text early). Returns {key: block_text}, plus
    a "header" key for everything before the first anchor."""
    positions = []
    cursor = 0
    for key, anchor in _SECTION_ANCHORS:
        idx = text.find(anchor, cursor)
        if idx == -1:
            continue
        positions.append((idx, key))
        cursor = idx + len(anchor)
    positions.sort()
    blocks = {}
    if positions:
        blocks["header"] = text[:positions[0][0]]
    else:
        blocks["header"] = text
    for i, (idx, key) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        blocks[key] = text[idx:end]
    return blocks


def parse_dds_daily_pdf_text(text: str) -> dict:
    """
    Full `pdftotext -layout` text of one DDS daily bulletin -> a structured dict:

    {
      "header": {"day": int, "month_th": str, "year_be": int, "year_ce": int,
                 "issue_no": str} or None if the header line wasn't recognized,
      "rain_stations": [{"rank": int|None, "location_th": str, "rain_mm": float}],
      "canal_outer": [{"idx": int, "name_th": str, "critical_m": float,
                        "yesterday_max_m": float, "today_0700_m": float,
                        "status_th": str}],
      "canal_inner": [... same shape as canal_outer ...],
      "chaophraya_rows": [{"date_th": str, <10 _CHAOPHRAYA_FIELDS keys>}] -- only for
          rows with the full 10-field layout,
      "chaophraya_partial": [{"date_th": str, "raw_line": str}] -- a dated row that did
          NOT have the full layout (e.g. the report date's own row is routinely
          incomplete -- see module docstring); never guessed into fields,
      "reservoirs": [{"idx": int, "name_th": str, "capacity_mcm": float,
                       "storage_mcm": float, "storage_pct": float,
                       "inflow_mcm_day": float, "outflow_mcm_day": float,
                       "net_change_mcm_day": float, "as_of_date_th": str}],
      "tide_dedicated": [{"kind_th": "ขึ้นเต็มที่"|"ลงเต็มที่", "am_time": str,
                           "am_level_m": float, "pm_time": str, "pm_level_m": float}],
      "documents": [{"section": str, "text": str}] -- every section this function does
          NOT reduce to fields, verbatim (weather_forecast, salinity, narrative_log),
          PLUS one entry per chaophraya_flow_tide/reservoirs/etc. block's own header/
          footnote lines that didn't match a row regex (never silently dropped).
    }
    """
    blocks = _split_sections(text)
    result = {
        "header": None, "rain_stations": [], "canal_outer": [], "canal_inner": [],
        "chaophraya_rows": [], "chaophraya_partial": [], "reservoirs": [],
        "tide_dedicated": [], "documents": [],
    }

    m = _HEADER_RE.search(blocks.get("header", ""))
    if m:
        day, month_th, year_be, issue_no = m.groups()
        year_be = int(year_be)
        result["header"] = {
            "day": int(day), "month_th": month_th, "year_be": year_be,
            "year_ce": year_be - 543, "issue_no": issue_no,
        }
    if blocks.get("header"):
        # Stored unconditionally (not only when the header regex fails to match) so a
        # layout change that makes NONE of `_SECTION_ANCHORS` match (the whole PDF then
        # lands in "header") can never come back as 0 observations, 0 documents, ok=True
        # -- a silent drop that used to look identical to "the bulletin genuinely had
        # nothing new in it." The caller can tell the two cases apart: this document plus
        # `result["header"] is None` means the layout wasn't recognized at all.
        result["documents"].append({"section": "header", "text": blocks["header"]})

    for doc_key in ("weather_forecast", "salinity", "narrative_log"):
        if blocks.get(doc_key):
            result["documents"].append({"section": doc_key, "text": blocks[doc_key]})

    rain_block = blocks.get("rainfall", "")
    unmatched = []
    for line in rain_block.splitlines():
        if not line.strip() or "จุดวัด" not in line:
            continue
        m = _RAIN_ROW_RE.match(line)
        if m:
            rank, loc, mm = m.groups()
            result["rain_stations"].append({
                "rank": int(rank), "location_th": loc.strip(),
                "rain_mm": float(mm.replace(",", "")),
            })
            continue
        m = _RAIN_REF_ROW_RE.match(line)
        if m:
            loc, mm = m.groups()
            result["rain_stations"].append({
                "rank": None, "location_th": loc.strip(),
                "rain_mm": float(mm.replace(",", "")),
            })
            continue
        unmatched.append(line)
    if unmatched:
        result["documents"].append({"section": "rainfall_unmatched",
                                     "text": "\n".join(unmatched)})

    for key in ("canal_outer", "canal_inner"):
        unmatched = []
        for line in blocks.get(key, "").splitlines():
            if not line.strip():
                continue
            m = _CANAL_ROW_RE.match(line)
            if m:
                idx, name, critical, ymax, today, status = m.groups()
                (result[key]).append({
                    "idx": int(idx), "name_th": name.strip(),
                    "critical_m": float(critical), "yesterday_max_m": float(ymax),
                    "today_0700_m": float(today), "status_th": status.strip(),
                })
            elif "จุดวัด" not in line and key.split("_")[-1] not in line:
                unmatched.append(line)
        if unmatched:
            result["documents"].append({"section": f"{key}_unmatched",
                                         "text": "\n".join(unmatched)})

    cp_block = blocks.get("chaophraya_flow_tide", "")
    cp_unmatched = []
    for line in cp_block.splitlines():
        if not line.strip():
            continue
        m = _CHAOPHRAYA_DATE_RE.match(line)
        if not m:
            cp_unmatched.append(line)
            continue
        date_th, rest = m.groups()
        tokens = re.split(r"\s{2,}", rest.strip())
        if len(tokens) == len(_CHAOPHRAYA_FIELDS):
            row = {"date_th": date_th.strip()}
            for field, tok in zip(_CHAOPHRAYA_FIELDS, tokens):
                # Per-token, with a None fallback -- a "-" (no reading that field, seen on
                # a real full 10-token row) used to hit float()'s ValueError and abort the
                # WHOLE bulletin (every section, not just this row). None is a missing
                # value, never fabricated as 0.
                if field.endswith("_cms") or field.endswith("_level_m"):
                    tok_clean = (tok or "").replace(",", "").strip()
                    try:
                        row[field] = float(tok_clean) if tok_clean and tok_clean != "-" else None
                    except ValueError:
                        row[field] = None
                else:
                    row[field] = tok
            result["chaophraya_rows"].append(row)
        else:
            result["chaophraya_partial"].append({"date_th": date_th.strip(), "raw_line": line})
    if cp_unmatched:
        result["documents"].append({"section": "chaophraya_flow_tide_header_notes",
                                     "text": "\n".join(cp_unmatched)})

    res_unmatched = []
    for line in blocks.get("reservoirs", "").splitlines():
        if not line.strip():
            continue
        m = _RESERVOIR_ROW_RE.match(line)
        if m:
            idx, name, cap, store, pct, inflow, outflow, net, as_of = m.groups()
            result["reservoirs"].append({
                "idx": int(idx), "name_th": name.strip(),
                "capacity_mcm": float(cap.replace(",", "")),
                "storage_mcm": float(store.replace(",", "")),
                "storage_pct": float(pct), "inflow_mcm_day": float(inflow),
                "outflow_mcm_day": float(outflow), "net_change_mcm_day": float(net),
                "as_of_date_th": as_of.strip(),
            })
        else:
            res_unmatched.append(line)
    if res_unmatched:
        result["documents"].append({"section": "reservoirs_header_notes",
                                     "text": "\n".join(res_unmatched)})

    tide_unmatched = []
    for line in blocks.get("tide_dedicated", "").splitlines():
        if not line.strip():
            continue
        m = _TIDE7_ROW_RE.match(line)
        if m:
            kind, am_t, am_l, pm_t, pm_l = m.groups()
            result["tide_dedicated"].append({
                "kind_th": kind, "am_time": am_t, "am_level_m": float(am_l),
                "pm_time": pm_t, "pm_level_m": float(pm_l),
            })
        else:
            tide_unmatched.append(line)
    if tide_unmatched:
        result["documents"].append({"section": "tide_dedicated_header_notes",
                                     "text": "\n".join(tide_unmatched)})

    return result


# --- dds_tide_pdf (Navy Hydrographic Dept yearly monthly tide table) --------------------

_ENGLISH_MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}
_TIDE_MONTH_HEADER_RE = re.compile(
    r"(" + "|".join(_ENGLISH_MONTHS) + r")\s+(\d{4})\s*$")
_TIDE_DAY_ROW_RE = re.compile(
    r"^\s*(\d{1,2})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$")

_TIDE_DAY_FIELDS = ["hw_am_time", "hw_am_level_m", "lw_am_time", "lw_am_level_m",
                    "hw_pm_time", "hw_pm_level_m", "lw_pm_time", "lw_pm_level_m"]


def _tide_token(field: str, tok: str):
    if tok == "-":
        return None
    if field.endswith("_level_m"):
        try:
            return float(tok)
        except ValueError:
            return None
    return tok  # time fields stay as the raw "HHMM"-style string BMA/Navy print


def parse_tide_table_text(text: str) -> list:
    """
    `pdftotext -layout` text of the Navy Hydrographic Dept's yearly monthly tide-table
    PDF -> a list of monthly blocks: [{"year": int, "month": int,
    "station_th": "กองบัญชาการกองทัพเรือ", "days": [{"day": int, **_TIDE_DAY_FIELDS}]}].

    Confirmed 2026-09-26 against a real 12-page/12-month PDF (station: Royal Thai Navy
    HQ). Each day has up to 2 high-water + 2 low-water time+level entries (AM/PM); the
    source prints "-" for a half-day with no such extreme -- parsed as None here, never
    fabricated as 0.0. A page/block whose month/year header isn't found is skipped (not
    guessed) -- callers can compare `len(result)` against the PDF's own page count if
    they want to detect that.
    """
    out = []
    current = None
    for line in text.splitlines():
        m = _TIDE_MONTH_HEADER_RE.search(line.strip())
        if m:
            month_name, year = m.groups()
            current = {"year": int(year), "month": _ENGLISH_MONTHS[month_name],
                       "station_th": "กองบัญชาการกองทัพเรือ", "days": []}
            out.append(current)
            continue
        if current is None:
            continue
        m = _TIDE_DAY_ROW_RE.match(line)
        if not m:
            continue
        day_s, *tokens = m.groups()
        day = int(day_s)
        if not (1 <= day <= 31):
            continue
        row = {"day": day}
        for field, tok in zip(_TIDE_DAY_FIELDS, tokens):
            row[field] = _tide_token(field, tok)
        current["days"].append(row)
    return out
