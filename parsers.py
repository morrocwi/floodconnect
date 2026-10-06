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
import csv
import datetime
import io
import re
import urllib.parse

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


# --- thaiwater rain_24h (api-v3.thaiwater.net .../public/rain_24h) -----------------------
#
# Added 2026-09-26 (fixed: CI had no rain collector at all). Same "data":[...]
# envelope shape as flood_road/canal_waterlevel; confirmed against the existing manual
# snapshot raw/gapfill/rain_24h_1.json (4282 stations, rain_24h in mm, rainfall_datetime
# local Thailand time, station.tele_station_lat/_long real coordinates).

THAIWATER_RAIN_24H_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h"


def parse_thaiwater_rain_24h(data: dict) -> list:
    """
    `api-v3.thaiwater.net .../public/rain_24h` JSON -> rain-reading dicts.

    Returns [{station_id, station_name_th, lat, lon, mm_24h, mm_1h, observed_at (UTC ISO,
    converted from local Thailand time), agency, source_url, fetched_at=None}]. A record
    with no coordinate or no rain_24h value is skipped, never fabricated (same rule as
    parse_thaiwater_flood_road).

    TODO #181 (2026-09-28, confirmed against a live raw/live/thaiwater_rain_24h/*.json
    payload of 4439 records): the live response carries exactly TWO rain fields --
    `rain_1h` and `rain_24h` (no rain_3h/6h/12h anywhere in this API family; `station_type`
    is uniformly "rainfall_24h" across every record checked). Both are rolling windows
    ENDING at the same `rainfall_datetime` timestamp (not independently re-verified against
    thaiwater.net's own API docs -- no such docs page was found -- so the window-end
    convention is RELAYED/assumed from the field names + the existing rain_24h handling
    above, not VERIFIED against a written spec). `rain_1h` is absent on a real fraction of
    records (539/4439 in the checked payload, ~12%) -- MEASURED, not a parsing bug -- so it
    is treated as optional and skipped (mm_1h=None), never fabricated as 0 or copied from
    rain_24h.
    """
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        mm = rec.get("rain_24h")
        if lat is None or lon is None or mm is None:
            continue
        mm_1h = rec.get("rain_1h")
        dt_str = rec.get("rainfall_datetime")
        observed_at = None
        if dt_str:
            try:
                local_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                local_dt = local_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                observed_at = local_dt.astimezone(datetime.timezone.utc).isoformat()
            except ValueError:
                observed_at = None
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        agency_th = ((rec.get("agency") or {}).get("agency_name") or {}).get("th")
        out.append({
            "station_id": str(station.get("id")) if station.get("id") is not None else None,
            "station_name_th": (station.get("tele_station_name") or {}).get("th"),
            "lat": float(lat),
            "lon": float(lon),
            "mm_24h": float(mm),
            "mm_1h": float(mm_1h) if mm_1h is not None else None,
            "observed_at": observed_at,
            "agency": agency,
            "agency_th": agency_th,
            "source_url": THAIWATER_RAIN_24H_URL,
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


# --- Open-Meteo hourly precipitation forecast (open model, third-party) -------------------
#
# Added 2026-09-26 (RAIN FORECAST item): api.open-meteo.com needs no API key and blends
# ECMWF/GFS open models. It is explicitly a THIRD-PARTY forecast product, never a Thai
# government source and never confused with a TMD (กรมอุตุฯ) official forecast -- see
# build_data.py's `load_openmeteo_forecast` and the "third_party" trust_tier in
# sources/registry.yaml. `timezone=Asia/Bangkok` on the request makes every `hourly.time[i]`
# already a Bangkok-local "YYYY-MM-DDTHH:MM" string, so no timezone math happens here.

# forecast_days=5 (2026-09-26, peer-review fix): the drain-timeline chart's 96h horizon
# needs a forecast that actually reaches +96h; forecast_days=3 (~72h) left the last ~24h
# of the chart with no real forecast at all, which build_data.py's build_drain_timeline
# used to silently pad with 0mm. It no longer does that silently -- see
# `drain_timeline["forecast_coverage_hours"]` / the chart's grey "ไม่มีพยากรณ์" band -- but
# requesting the extra 2 days here means most runs won't hit that fallback at all.
OPENMETEO_FORECAST_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=precipitation,precipitation_probability&timezone=Asia%2FBangkok&forecast_days=5"
)


def openmeteo_forecast_url(lat: float, lon: float) -> str:
    return OPENMETEO_FORECAST_URL_TMPL.format(lat=lat, lon=lon)


THAILAND_BBOX = (5.5, 20.6, 97.3, 105.7)  # (lat_min, lat_max, lon_min, lon_max)


def _valid_th_coord(lat, lon) -> bool:
    """Rejects None, (0,0) sentinels, and anything outside a coarse Thailand bounding
    box -- same guard `docs/ASSETS.md` documents for `assets_registry.py`'s HII
    harvesters (a real decimal-place error was found in HII's own `dam_small_tele`
    feed, e.g. lat=118.58928 for a station actually at ~18.6N). Never "corrects" a bad
    coordinate -- only says whether to accept it as-is."""
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if lat == 0 and lon == 0:
        return False
    lat_min, lat_max, lon_min, lon_max = THAILAND_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _th_local_to_utc_iso(dt_str: str, fmt: str = "%Y-%m-%d %H:%M"):
    """Thailand-local ("Y-m-d H:M" or "Y-m-d") -> UTC ISO string, or None if unparsable.
    Same convention as parse_thaiwater_flood_road/parse_thaiwater_rain_24h."""
    if not dt_str:
        return None
    try:
        local_dt = datetime.datetime.strptime(dt_str, fmt)
    except ValueError:
        return None
    local_dt = local_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    return local_dt.astimezone(datetime.timezone.utc).isoformat()


# --- HII nationwide waterlevel (api-v3.thaiwater.net .../public/waterlevel) --------------
#
# Confirmed 2026-09-27 (founder ask "เราได้พิกัด แม่น้ำ เขื่อน... ครบหรือยัง"): 804
# nationwide river/canal telemetry stations, real tele_station_lat/_long. Same envelope
# shape ("data": [...]) as flood_road/rain_24h/canal_waterlevel -- see docs/ASSETS.md's
# HII/RID probe log for the discovery notes (this is the ONLY thaiwater30 service id on
# this host that returned station-level water-level data with coordinates).

THAIWATER_WATERLEVEL_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel"


def _safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_thaiwater_waterlevel(data: dict) -> list:
    """
    `api-v3.thaiwater.net .../public/waterlevel` JSON -> nationwide gauge-reading dicts.

    Returns [{station_id, station_oldcode, station_name_th, lat, lon,
    waterlevel_msl, waterlevel_msl_previous, storage_percent, situation_level,
    diff_wl_bank, diff_wl_bank_text, min_bank, ground_level, critical_level_msl,
    warning_level_m, river_name, sub_basin_id, basin_id, basin_name_th, province_th,
    amphoe_th, tambon_th, agency, agency_shortname, observed_at (UTC ISO),
    source_url}]. A record with no valid coordinate (see `_valid_th_coord`) or no
    `waterlevel_msl` value is skipped, never fabricated -- same rule as every other
    parser in this file. Every added field is read straight off the live payload
    (exact paths MEASURED 2026-10-04: `station.min_bank`, `station.ground_level`,
    `station.critical_level_msl`, top-level `diff_wl_bank`/`diff_wl_bank_text`/
    `storage_percent`/`situation_level` -- NOT nested under `station`) and kept as a
    plain relayed value, never recomputed into a new number here.
    """
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if not _valid_th_coord(lat, lon):
            continue
        wl = rec.get("waterlevel_msl")
        if wl is None:
            continue
        try:
            wl = float(wl)
        except (TypeError, ValueError):
            continue
        storage_pct = _safe_float(rec.get("storage_percent"))
        agency_block = rec.get("agency") or {}
        agency = (agency_block.get("agency_name") or {}).get("en")
        agency_shortname = (agency_block.get("agency_shortname") or {}).get("en")
        basin = rec.get("basin") or {}
        geocode = rec.get("geocode") or {}
        situation_level = rec.get("situation_level")
        try:
            situation_level = int(situation_level) if situation_level is not None else None
        except (TypeError, ValueError):
            situation_level = None
        out.append({
            "station_id": str(station.get("id")) if station.get("id") is not None else None,
            "station_oldcode": station.get("tele_station_oldcode"),
            "station_name_th": (station.get("tele_station_name") or {}).get("th"),
            "lat": float(lat), "lon": float(lon),
            "waterlevel_msl": wl,
            "waterlevel_msl_previous": _safe_float(rec.get("waterlevel_msl_previous")),
            "storage_percent": storage_pct,
            "situation_level": situation_level,
            "diff_wl_bank": _safe_float(rec.get("diff_wl_bank")),
            "diff_wl_bank_text": rec.get("diff_wl_bank_text"),
            "min_bank": _safe_float(station.get("min_bank")),
            "ground_level": _safe_float(station.get("ground_level")),
            "critical_level_msl": _safe_float(station.get("critical_level_msl")),
            "warning_level_m": _safe_float(station.get("warning_level_m")),
            "river_name": rec.get("river_name"),  # top-level, not under station
            "sub_basin_id": station.get("sub_basin_id"),
            "basin_id": basin.get("id"),
            "basin_name_th": (basin.get("basin_name") or {}).get("th"),
            "province_th": (geocode.get("province_name") or {}).get("th"),
            "amphoe_th": (geocode.get("amphoe_name") or {}).get("th"),
            "tambon_th": (geocode.get("tumbon_name") or {}).get("th"),
            "observed_at": _th_local_to_utc_iso(rec.get("waterlevel_datetime")),
            "agency": agency, "agency_shortname": agency_shortname,
            "source_url": THAIWATER_WATERLEVEL_URL,
        })
    return out


# --- HII nationwide dam/reservoir census (api-v3.thaiwater.net dam.json, 4 station types)
#
# Confirmed 2026-09-27 against a real cached payload (`raw/live/hii_dam/*.json`, 989
# records across 4 station types) -- see docs/ASSETS.md's "HII dams and watergates"
# section for the full field-mapping writeup this parser reuses. `dam_hourly`/`dam_daily`
# share one row shape (`dam.dam_lat`/`dam_long`, `dam_date` date-or-datetime string,
# `dam_storage`/`dam_storage_percent`/`dam_inflow`/`dam_released`); `dam_medium` shares
# that same shape (date-only `dam_date`); `dam_small_tele` uses its own field names
# (`dam.tele_station_lat`/`_long`, `smalldam_datetime`, `water_level`/`volume`/
# `percent_storage`). This parser normalises all 4 into one row shape; asset_id join
# scheme is `dam:hii_dam:<dam.id>` (the caller's job, using this row's `dam_id`).

HII_DAM_URL_HINT = "HII dam.json (data.{dam_hourly,dam_daily,dam_medium,dam_small_tele})"


def _hii_dam_datetime_to_utc(dt_str: str):
    if not dt_str:
        return None
    if len(dt_str) == 10:  # "YYYY-MM-DD", date-only -- 00:00 Bangkok local marker
        return _th_local_to_utc_iso(dt_str + " 00:00")
    return _th_local_to_utc_iso(dt_str)


def _mcm_per_day_to_m3s(mcm_per_day):
    """MCM/day -> m3/s: value * 1e6 / 86400. None-safe. Tag this as MEASURED-derived
    (computed from a MEASURED input, not itself an independent reading)."""
    if mcm_per_day is None:
        return None
    try:
        return float(mcm_per_day) * 1e6 / 86400.0
    except (TypeError, ValueError):
        return None


def parse_hii_dam(data: dict) -> list:
    """
    HII `dam.json` payload (`{"data": {"dam_hourly": [...], "dam_daily": [...],
    "dam_medium": [...], "dam_small_tele": [...]}}`) -> one normalised list:
    [{station_type, dam_id, name_th, lat, lon, storage_mcm, storage_pct, inflow_mcm,
    release_mcm, release_m3s_computed, spilled_mcm, level_m, observed_at (UTC ISO),
    agency_en, province_th}]. `release_m3s_computed` = release_mcm * 1e6 / 86400 (MCM/day
    -> m3/s), MEASURED-derived, not itself a fresh reading. `spilled_mcm`/`level_m` are
    only present on dam_hourly/dam_daily/dam_small_tele (dam_medium's payload carries
    neither field -- left None, never fabricated). A record with no valid coordinate is
    skipped, never fabricated (see `_valid_th_coord`).
    """
    out = []
    data = data.get("data") or {}
    for station_type in ("dam_hourly", "dam_daily", "dam_medium"):
        for rec in data.get(station_type, []):
            dam = rec.get("dam") or {}
            lat, lon = dam.get("dam_lat"), dam.get("dam_long")
            if not _valid_th_coord(lat, lon):
                continue
            agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
            geocode = rec.get("geocode") or {}
            release_mcm = rec.get("dam_released")
            out.append({
                "station_type": station_type,
                "dam_id": dam.get("id"),
                "name_th": (dam.get("dam_name") or {}).get("th"),
                "lat": float(lat), "lon": float(lon),
                "storage_mcm": rec.get("dam_storage"),
                "storage_pct": rec.get("dam_storage_percent"),
                "inflow_mcm": rec.get("dam_inflow"),
                "release_mcm": release_mcm,
                "release_m3s_computed": _mcm_per_day_to_m3s(release_mcm),
                "spilled_mcm": rec.get("dam_spilled"),  # dam_medium: field absent -> None
                "level_m": rec.get("dam_level"),        # dam_medium: field absent -> None
                "observed_at": _hii_dam_datetime_to_utc(rec.get("dam_date")),
                "agency_en": agency,
                "province_th": (geocode.get("province_name") or {}).get("th"),
            })
    for rec in data.get("dam_small_tele", []):
        dam = rec.get("dam") or {}
        lat, lon = dam.get("tele_station_lat"), dam.get("tele_station_long")
        if not _valid_th_coord(lat, lon):
            continue
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        geocode = rec.get("geocode") or {}
        release_mcm = dam.get("outflow")
        out.append({
            "station_type": "dam_small_tele",
            "dam_id": dam.get("id"),
            "name_th": (dam.get("smalldam_name") or {}).get("th"),
            "lat": float(lat), "lon": float(lon),
            "storage_mcm": rec.get("volume"),
            "storage_pct": rec.get("percent_storage"),
            "inflow_mcm": (dam.get("inflow")),
            "release_mcm": release_mcm,
            "release_m3s_computed": _mcm_per_day_to_m3s(release_mcm),
            "spilled_mcm": None,  # dam_small_tele payload has no spilled field
            "level_m": rec.get("water_level"),
            "observed_at": _hii_dam_datetime_to_utc(rec.get("smalldam_datetime")),
            "agency_en": agency,
            "province_th": (geocode.get("province_name") or {}).get("th"),
        })
    return out


# --- HII nationwide watergate census (api-v3.thaiwater.net watergate_load.json) ----------
#
# Confirmed 2026-09-27 against a real cached payload (`raw/live/hii_watergate/*.json`,
# 2,315 records) -- see docs/ASSETS.md's "HII dams and watergates" section. Each record's
# `station` sub-object carries the coordinate/name/oldcode; `watergate_in`/`watergate_out`
# are upstream/downstream water levels (m); `floodgate_open`/`pump_on` are boolean-ish
# state fields present on some rows, absent on most (kept as-is, never fabricated as
# false). asset_id join scheme is `gate:hii_watergate:<station.id>`.

def parse_hii_watergate(data: dict) -> list:
    """
    HII `watergate_load.json`'s `watergate_data.data[]` array -> normalised rows:
    [{station_id, name_th, oldcode, lat, lon, level_upstream_m, level_downstream_m,
    gate_open, pump_on, observed_at (UTC ISO), agency_en, province_th}]. A record with
    no valid coordinate, or `station.id == 0` (139 of 2,315 real rows are placeholder/
    incomplete census entries with no name/oldcode/coordinate at all -- see
    docs/ASSETS.md), is skipped, never fabricated.
    """
    out = []
    watergate_data = data.get("watergate_data") or data  # tolerate either envelope
    for rec in watergate_data.get("data", []):
        station = rec.get("station") or {}
        station_id = station.get("id")
        if not station_id:  # 0, None -- placeholder row, see docstring
            continue
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if not _valid_th_coord(lat, lon):
            continue
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        geocode = rec.get("geocode") or {}
        observed_at = (_th_local_to_utc_iso(rec.get("watergate_datetime_in"))
                       or _th_local_to_utc_iso(rec.get("watergate_datetime_out")))
        out.append({
            "station_id": str(station_id),
            "name_th": (station.get("tele_station_name") or {}).get("th"),
            "oldcode": station.get("tele_station_oldcode"),
            "lat": float(lat), "lon": float(lon),
            "level_upstream_m": rec.get("watergate_in"),
            "level_downstream_m": rec.get("watergate_out"),
            "gate_open": rec.get("floodgate_open"),
            "pump_on": rec.get("pump_on"),
            "observed_at": observed_at,
            "agency_en": agency,
            "province_th": (geocode.get("province_name") or {}).get("th"),
        })
    return out


# --- RID large-reservoir summary table (water.rid.go.th/flood/flood/res_table.htm) ------
#
# Confirmed 2026-09-27: 35 named large dams grouped by RID region, but the page publishes
# NO coordinate or numeric reading anywhere (checked by reading the full decoded HTML, not
# assumed -- see docs/ASSETS.md's probe log). This parser therefore only recovers
# region -> dam-name pairs; the caller stores them as documents (a name-only list is not
# an "observation" in this schema's sense -- no value/variable to attach), never as a
# fabricated numeric reading.

_RID_RES_REGION_RE = re.compile(
    r'<p[^>]*>([^<]*ภาค[^<]*)</p>\s*<ul[^>]*>(.*?)</ul>', re.S)
_RID_RES_DAM_NAME_RE = re.compile(r'class="highslide"[^>]*>([^<]+)</a>')


def parse_rid_res_table(html: str) -> list:
    """
    `water.rid.go.th/flood/flood/res_table.htm` HTML -> [{"region_th": str,
    "dam_name_th": str}] for every dam name found under a region heading. Returns []
    if the page structure doesn't match (never guesses).
    """
    out = []
    for region_m in _RID_RES_REGION_RE.finditer(html):
        region_th, block = region_m.groups()
        for name in _RID_RES_DAM_NAME_RE.findall(block):
            out.append({"region_th": region_th.strip(), "dam_name_th": name.strip()})
    return out


# --- EGAT dam water-crisis table (water.egat.co.th/water_crisis.php) --------------------
#
# Confirmed 2026-09-27 (founder-supplied URL, queued item #4 in
# docs/knowledge/FOUNDER_TASKS_2026-09-27.md): a real server-rendered HTML table, one row
# per EGAT-operated dam, 15 data columns after the name (storage level m.รทก., storage
# mcm/%, usable-water mcm/% this year, usable-water mcm/% last year, year-over-year diff
# mcm/%, today's inflow/release mcm, past-week inflow/release mcm, week-over-week change
# mcm, remaining intake capacity mcm) -- column order confirmed against the live page's
# own header cells, not assumed. A region-subheader row (ภาคเหนือ etc.) has every data
# cell empty and is skipped, never stored as a dam with null values.

_EGAT_ROW_RE = re.compile(
    r'<tr>\s*<td[^>]*><p(?:4|20)>([^<]+)</p(?:4|20)></td>(.*?)</tr>', re.S)
_EGAT_CELL_RE = re.compile(r'<p\d+>\s*([^<]*?)\s*</p\d+>')
_EGAT_FIELDS = [
    "storage_level_m", "storage_mcm", "storage_pct", "usable_mcm_this_yr",
    "usable_pct_this_yr", "usable_mcm_last_yr", "usable_pct_last_yr", "yoy_diff_mcm",
    "yoy_diff_pct", "inflow_today_mcm", "release_today_mcm", "inflow_week_mcm",
    "release_week_mcm", "change_week_mcm", "remaining_capacity_mcm",
]


def _egat_num(s):
    s = (s or "").replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_egat_water_crisis(html: str) -> list:
    """
    `water.egat.co.th/water_crisis.php` HTML -> [{"name_th": str, **_EGAT_FIELDS (each
    float or None)}] for every real dam row (a region-subheader row with all-empty cells
    is skipped). No coordinate on this page -- caller joins by name against another
    source's coordinate (e.g. `hii_dam`), never geocodes here.
    """
    out = []
    for m in _EGAT_ROW_RE.finditer(html):
        name_th, rest = m.groups()
        cells = [c.strip() for c in _EGAT_CELL_RE.findall(rest)]
        if not any(c not in ("", "-") for c in cells):
            continue  # region-subheader row, every cell empty
        if len(cells) < len(_EGAT_FIELDS):
            continue
        row = {"name_th": name_th.strip()}
        for field, cell in zip(_EGAT_FIELDS, cells):
            row[field] = _egat_num(cell)
        out.append(row)
    return out


# --- RID region-9 (Chonburi) reservoir report (irrigation.rid.go.th/rid9) ---------------
#
# Confirmed 2026-10-03 (Re-probed 2026-10-03, real GET): `rpt_show.php?dateid=<BE-year><mm><dd>`
# (dateid param alone is sufficient -- `dm`/`dms` only affect a display label, confirmed
# by comparing a full-params fetch against a dateid-only fetch of the same date, same
# table rows) returns a real per-reservoir table, 23 cells per data row: sequence no.,
# name, district, province, capacity, min capacity, then 3 storage columns (historical
# max / 2005-drought-year / current), daily+cumulative rain, 6 inflow columns
# (max/drought-year/current x daily/cumulative), then 6 release columns (domestic,
# agriculture, industry, ecosystem, total, evaporation+seepage). A region-subheader row
# (e.g. "อ่างเก็บน้ำขนาดใหญ่") has exactly 1 cell and is tracked as the row's `category_th`,
# never stored as a reservoir. Basin: Bang Pakong / eastern seaboard (Chonburi, Rayong,
# Chachoengsao, Prachinburi) -- NOT Chao Phraya/Bangkok (see collect.AREA_RELEVANT_SOURCES).

_RID9_TR_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
_RID9_TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
_RID9_TAG_RE = re.compile(r'<[^>]+>')

_RID9_FIELDS = [
    "seq", "name_th", "district_th", "province_th", "capacity_mcm", "min_capacity_mcm",
    "storage_max_mcm", "storage_drought_yr_mcm", "storage_current_mcm",
    "rain_daily_mm", "rain_cum_mm",
    "inflow_max_daily_mcm", "inflow_max_cum_mcm",
    "inflow_drought_yr_daily_mcm", "inflow_drought_yr_cum_mcm",
    "inflow_current_daily_mcm", "inflow_current_cum_mcm",
    "release_domestic_mcm", "release_agri_mcm", "release_industry_mcm",
    "release_ecosystem_mcm", "release_total_mcm", "release_evap_seepage_mcm",
]  # 23 fields total, matching the live table's colspan="23" header


def _rid9_clean(cell: str) -> str:
    text = _RID9_TAG_RE.sub("", cell)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _rid9_num(s: str):
    s = (s or "").replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_rid9_chonburi_rpt(html: str) -> list:
    """
    `irrigation.rid.go.th/rid9/rid9_new/rpt_show.php` HTML -> one dict per reservoir row,
    `{"category_th": str|None, "seq": str, "name_th": str, "district_th": str,
    "province_th": str, **numeric fields (float or None)}`. A row with fewer than 23
    cells, or whose first cell isn't a digit (a region-subheader/header row), is never
    treated as a reservoir -- it only updates the running `category_th` tag applied to
    the rows that follow. Returns [] if the page structure doesn't match (never guesses).
    """
    out = []
    category = None
    for tr_m in _RID9_TR_RE.finditer(html):
        cells_raw = _RID9_TD_RE.findall(tr_m.group(1))
        if not cells_raw:
            continue
        cells = [_rid9_clean(c) for c in cells_raw]
        if len(cells) == 1:
            if cells[0] and ("อ่างเก็บน้ำ" in cells[0]):
                category = cells[0]
            continue
        if len(cells) != len(_RID9_FIELDS) or not cells[0].isdigit():
            continue
        row = {"category_th": category}
        for field, cell in zip(_RID9_FIELDS, cells):
            if field in ("seq", "name_th", "district_th", "province_th"):
                row[field] = cell
            else:
                row[field] = _rid9_num(cell)
        out.append(row)
    return out


# --- Open-Meteo Flood API (GloFAS river discharge, open model, third-party) --------------
#
# api.open-meteo.com/v1/flood -- no API key. Daily river-discharge forecast (m3/s) for a
# fixed lat/lon point (GloFAS global model resolution, not a Thai-agency gauge). Confirmed
# 2026-09-27 with a real sample fetch (see raw/live/openmeteo_flood/*.json).

OPENMETEO_FLOOD_URL_TMPL = (
    "https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}"
    "&daily=river_discharge&timezone=Asia%2FBangkok"
)


def openmeteo_flood_url(lat: float, lon: float) -> str:
    return OPENMETEO_FLOOD_URL_TMPL.format(lat=lat, lon=lon)


def parse_openmeteo_flood(data: dict) -> list:
    """
    Open-Meteo `/v1/flood?daily=river_discharge` JSON -> [{"date": "YYYY-MM-DD",
    "discharge_m3s": float}]. A day missing its discharge value is skipped, never
    fabricated as 0 (same rule as every other parser in this file)."""
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    vals = daily.get("river_discharge") or []
    out = []
    for i, d in enumerate(dates):
        if i >= len(vals) or vals[i] is None:
            continue
        try:
            v = float(vals[i])
        except (TypeError, ValueError):
            continue
        out.append({"date": d, "discharge_m3s": v})
    return out


# --- Open-Meteo Ensemble API (multi-member rain, open model, third-party) ---------------
#
# api.open-meteo.com/v1/ensemble -- no API key. Same hourly envelope as the plain
# forecast API, but `hourly.precipitation_memberNN` carries one series per ensemble
# member alongside the plain `precipitation` (member 0/control run). Confirmed 2026-09-27
# with a real sample fetch (39 members, see raw/live/openmeteo_ensemble/*.json).

OPENMETEO_ENSEMBLE_URL_TMPL = (
    "https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}"
    "&hourly=precipitation&models=icon_seamless&timezone=Asia%2FBangkok&forecast_days=3"
)


def openmeteo_ensemble_url(lat: float, lon: float) -> str:
    return OPENMETEO_ENSEMBLE_URL_TMPL.format(lat=lat, lon=lon)


def parse_openmeteo_ensemble(data: dict) -> list:
    """
    Open-Meteo `/v1/ensemble?hourly=precipitation` JSON -> a list of hourly rows:
    [{"time_local": str, "median_mm": float, "min_mm": float, "max_mm": float,
    "n_members": int}], computed across the control run + every `precipitation_memberNN`
    series present for that hour. An hour with zero readable members is skipped, never
    fabricated."""
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    member_keys = [k for k in hourly.keys()
                   if k == "precipitation" or k.startswith("precipitation_member")]
    out = []
    for i, t in enumerate(times):
        vals = []
        for k in member_keys:
            series = hourly.get(k) or []
            if i < len(series) and series[i] is not None:
                try:
                    vals.append(float(series[i]))
                except (TypeError, ValueError):
                    continue
        if not vals:
            continue
        vals.sort()
        n = len(vals)
        median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        out.append({"time_local": t, "median_mm": round(median, 2),
                     "min_mm": round(min(vals), 2), "max_mm": round(max(vals), 2),
                     "n_members": n})
    return out


# --- Open-Meteo Marine API (sea-level height, open model, third-party) ------------------
#
# api.open-meteo.com/v1/marine -- no API key. Hourly `sea_level_height_msl` (m) for a
# fixed offshore lat/lon point near the Gulf of Thailand bar off Bangkok. Confirmed
# 2026-09-27 with a real sample fetch (see raw/live/openmeteo_marine/*.json).

OPENMETEO_MARINE_URL_TMPL = (
    "https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}"
    "&hourly=sea_level_height_msl&timezone=Asia%2FBangkok"
)


def openmeteo_marine_url(lat: float, lon: float) -> str:
    return OPENMETEO_MARINE_URL_TMPL.format(lat=lat, lon=lon)


def parse_openmeteo_marine(data: dict) -> list:
    """
    Open-Meteo `/v1/marine?hourly=sea_level_height_msl` JSON -> [{"time_local": str,
    "sea_level_m": float}]. A row missing its value is skipped, never fabricated."""
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    vals = hourly.get("sea_level_height_msl") or []
    out = []
    for i, t in enumerate(times):
        if i >= len(vals) or vals[i] is None:
            continue
        try:
            v = float(vals[i])
        except (TypeError, ValueError):
            continue
        out.append({"time_local": t, "sea_level_m": v})
    return out


# --- NASA POWER daily rain (open model/reanalysis, third-party, no key) -----------------
#
# power.larc.nasa.gov/api/temporal/daily/point -- no API key. `PRECTOTCORR` (bias-
# corrected precipitation, mm/day) per calendar day; NASA POWER's own fill value is
# -999.0 for a day not yet processed upstream (the last 1-3 days of any request are
# routinely -999 -- confirmed 2026-09-27, see raw/live/nasa_power/*.json) -- treated as
# missing, never as -999mm or 0mm of rain.

NASA_POWER_URL_TMPL = (
    "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR"
    "&community=AG&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"
)
NASA_POWER_FILL_VALUE = -999.0


def nasa_power_url(lat: float, lon: float, start: str, end: str) -> str:
    return NASA_POWER_URL_TMPL.format(lat=lat, lon=lon, start=start, end=end)


def parse_nasa_power_daily_rain(data: dict) -> list:
    """
    NASA POWER `/api/temporal/daily/point?parameters=PRECTOTCORR` JSON -> [{"date":
    "YYYY-MM-DD", "rain_mm": float}]. A day equal to the feed's own documented fill
    value (`header.fill_value`, -999.0 if absent) is skipped, never stored as a real
    reading (see module note)."""
    fill = ((data.get("header") or {}).get("fill_value")) or NASA_POWER_FILL_VALUE
    series = (((data.get("properties") or {}).get("parameter") or {})
              .get("PRECTOTCORR") or {})
    out = []
    for date_str, v in series.items():
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v == fill:
            continue
        iso = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        out.append({"date": iso, "rain_mm": v})
    return out


def parse_openmeteo_forecast(data: dict) -> list:
    """
    Open-Meteo `/v1/forecast?hourly=precipitation,precipitation_probability` JSON -> a
    list of hourly rows in ascending time order:
    [{"time_local": "YYYY-MM-DDTHH:MM", "mm": float, "prob": int|None}].

    A row missing its precipitation value is skipped, never fabricated as 0 -- same rule
    as every other parser in this file. `prob` (precipitation_probability, %) is optional
    in Open-Meteo's own response and stays None if absent/short.
    """
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    precs = hourly.get("precipitation") or []
    probs = hourly.get("precipitation_probability") or []
    out = []
    for i, t in enumerate(times):
        if i >= len(precs) or precs[i] is None:
            continue
        mm = precs[i]
        try:
            mm = float(mm)
        except (TypeError, ValueError):
            continue
        prob = probs[i] if i < len(probs) else None
        out.append({"time_local": t, "mm": mm, "prob": prob})
    return out


# --- BMA water/PageMap/GoogleMap (bma_watermap) ------------------------------------
#
# Schema confirmed 2026-09-27 via docs/knowledge/BMA_WATER_MAP_PROBE.md's probe run
# (POST weather.bangkok.go.th/water/PageMap/GoogleMap, JSON array, 312 station records
# that run, 52 carrying a non-null watergate01..06 gate-opening height in metres --
# see that doc for the full field list, the founder's "have we connected yet" question,
# and why water_control was null for all 312 records in the probe archive). A pure
# parser first drafted (not wired) as tools/harvest/bma_maplet_draft.py -- superseded by
# this module's version, which this repo's collect.py actually calls; the draft file is
# left in place as a standalone reference/CLI (`python3 tools/harvest/bma_maplet_draft.py
# <path>`), not deleted, since it makes no network calls and duplicates no live wiring.

BMA_WATERMAP_URL = "https://weather.bangkok.go.th/water/PageMap/GoogleMap"
BMA_WATERMAP_GATE_FIELDS = tuple(f"watergate0{i}" for i in range(1, 7))


def _thai_be_datetime_to_iso(s):
    """BMA water/PageMap timestamps are Thai Buddhist-Era strings, 'DD/MM/YYYY HH:MM'
    (e.g. '27/09/2569 16:55'), Bangkok local time (UTC+7, no DST observed in Thailand).
    Returns a UTC ISO-8601 string, or None if unparseable -- never fabricated."""
    if not s:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})$", s.strip())
    if not m:
        return None
    d, mo, y_be, h, mi = (int(g) for g in m.groups())
    y_ce = y_be - 543
    try:
        local = datetime.datetime(y_ce, mo, d, h, mi,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    except ValueError:
        return None
    return local.astimezone(datetime.timezone.utc).isoformat()


def parse_bma_watermap_stations(data: list) -> list:
    """
    `POST weather.bangkok.go.th/water/PageMap/GoogleMap` JSON array -> station dicts.

    Returns one dict per station record that carries a `water_code`:
    {water_code, water_name, water_name_en, lat, lon, wl_in, warning, critical,
    water_control, gates (dict {gate_index 1-6: height_m} for non-null watergateNN
    fields only, empty dict if none), status_th, district_name, observed_at (UTC ISO,
    converted from the record's own site_timestampTH by `_thai_be_datetime_to_iso`),
    source_url, fetched_at=None (caller fills in the actual fetch time)}.

    A record with no `water_code` is skipped (nothing to key an observation by). A
    record whose timestamp does not parse keeps `observed_at=None` -- callers must skip
    inserting an observation for a None observed_at, same discipline as every other
    parser in this file (never fabricate a timestamp).
    """
    out = []
    for rec in data:
        code = rec.get("water_code")
        if not code:
            continue
        gates = {}
        for i, field in enumerate(BMA_WATERMAP_GATE_FIELDS, start=1):
            v = rec.get(field)
            if v is not None:
                gates[i] = v
        out.append({
            "water_code": code,
            "water_name": rec.get("water_name"),
            "water_name_en": rec.get("water_name_en"),
            "lat": rec.get("latitude"),
            "lon": rec.get("longitude"),
            "wl_in": rec.get("wl_in"),
            "warning": rec.get("warning"),
            "critical": rec.get("critical"),
            "water_control": rec.get("water_control"),
            "gates": gates,
            "status_th": rec.get("txtStatus"),
            "district_name": rec.get("district_name"),
            "observed_at": _thai_be_datetime_to_iso(rec.get("site_timestampTH")),
            "source_url": BMA_WATERMAP_URL,
            "fetched_at": None,
        })
    return out


# --- HII public/waterlevel_load (richer per-station shape incl. discharge cms) ----------
#
# api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load -- no API key. Promoted
# from tools/harvest/hii_waterchart_draft.py (draft parser, same fields) into this module
# per docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #1 (2026-09-27):
# the easiest real gauge-based Q_up (upstream inflow, PROP-FLOOD-03's Q_in(k)) source found.
# Requires basin_id + start_date + end_date query params. The 11 basin_code values below
# (6,7,8,9,10,11,12,13,14,15,26) are the ones observed on the Chao Phraya waterchart page
# (same set the draft module used) -- NOT confirmed as covering all ~25 Thailand basins;
# treat basin coverage itself as OPEN (see sources/registry.yaml id hii_waterlevel_load).

HII_WATERLEVEL_LOAD_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load"
HII_WATERLEVEL_LOAD_BASIN_IDS_OBSERVED = "6,7,8,9,10,11,12,13,14,15,26"


def hii_waterlevel_load_url(basin_ids: str, start_date: str, end_date: str) -> str:
    """`start_date`/`end_date` are "YYYY-MM-DD HH:MM" strings, per the live page's own
    query shape (e.g. "2026-09-27 00:00" / "2026-09-27 23:59")."""
    return (
        f"{HII_WATERLEVEL_LOAD_URL}?basin_id={basin_ids}"
        f"&&start_date={urllib.parse.quote(start_date)}"
        f"&&end_date={urllib.parse.quote(end_date)}"
    )


def parse_hii_waterlevel_load(data: dict) -> list:
    """
    HII `public/waterlevel_load` JSON -> flat row list. Keeps this endpoint's extra
    fields (discharge, storage_percent, msl, situation_level, river/basin join,
    cross-section params) rather than narrowing to the plain waterlevel shape -- that
    narrowing would throw away exactly what this endpoint is worth adding for (discharge
    cms, this repo's first real gauge-based Q_up source). A record missing
    `waterlevel_datetime` is skipped (never a guessed timestamp). `discharge` and
    `storage_percent` are parsed to float when present and numeric; a non-numeric/absent
    value is left as None, never coerced to 0.
    """
    records = (data.get("waterlevel_data") or {}).get("data") or []
    rows = []
    for r in records:
        station = r.get("station") or {}
        basin = r.get("basin") or {}
        agency = r.get("agency") or {}
        observed_at = r.get("waterlevel_datetime")
        if not observed_at:
            continue

        def _f(v):
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        rows.append({
            "station_code": station.get("tele_station_oldcode"),
            "station_id": station.get("id"),
            "station_name_th": (station.get("tele_station_name") or {}).get("th"),
            "lat": station.get("tele_station_lat"),
            "lon": station.get("tele_station_long"),
            "observed_at": observed_at,
            "waterlevel_msl": _f(r.get("waterlevel_msl")),
            "waterlevel_m": _f(r.get("waterlevel_m")),
            "discharge_cms": _f(r.get("discharge")),
            "storage_percent": _f(r.get("storage_percent")),
            "situation_level": r.get("situation_level"),
            "station_type": r.get("station_type"),
            "is_key_station": station.get("is_key_station"),
            "left_bank": station.get("left_bank"),
            "right_bank": station.get("right_bank"),
            "min_bank": station.get("min_bank"),
            "ground_level": station.get("ground_level"),
            "warning_level_m": station.get("warning_level_m"),
            "critical_level_m": station.get("critical_level_m"),
            "critical_level_msl": _f(station.get("critical_level_msl")),
            "river_gid": r.get("river_gid"),
            "river_name": r.get("river_name"),
            "basin_id": basin.get("id"),
            "basin_code": basin.get("basin_code"),
            "basin_name_th": (basin.get("basin_name") or {}).get("th"),
            "agency_shortname_en": (agency.get("agency_shortname") or {}).get("en"),
        })
    return rows


# --- Open-Meteo soil moisture (antecedent wetness / S_0 proxy, open model, third-party) --
#
# api.open-meteo.com/v1/forecast?hourly=soil_moisture_0_to_1cm,... -- no API key. Answers
# PROP-FLOOD-03's antecedent-wetness/initial-storage-proxy gap (founder ask, 2026-09-27,
# see docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #4). Volumetric
# water content, m3/m3, three depth layers. This is a MODEL grid-cell estimate, not a
# physical sensor -- tag every row `forecast-inferred` per
# units_datum_crosswalk.yaml's grid_cell_vs_gauge_not_equal rule.

OPENMETEO_SOIL_MOISTURE_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm"
    "&timezone=Asia%2FBangkok&forecast_days=3"
)

SOIL_MOISTURE_FIELDS = (
    "soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm", "soil_moisture_3_to_9cm",
)


def openmeteo_soil_moisture_url(lat: float, lon: float) -> str:
    return OPENMETEO_SOIL_MOISTURE_URL_TMPL.format(lat=lat, lon=lon)


def parse_openmeteo_soil_moisture(data: dict) -> list:
    """
    Open-Meteo soil-moisture hourly JSON -> [{"time_local": str,
    "soil_moisture_0_to_1cm": float|None, "soil_moisture_1_to_3cm": float|None,
    "soil_moisture_3_to_9cm": float|None}]. A row with all three layers missing is
    skipped; a row with at least one readable layer is kept with the others as None
    (never fabricated)."""
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    series = {f: (hourly.get(f) or []) for f in SOIL_MOISTURE_FIELDS}
    out = []
    for i, t in enumerate(times):
        row = {"time_local": t}
        any_value = False
        for f in SOIL_MOISTURE_FIELDS:
            vals = series[f]
            v = vals[i] if i < len(vals) else None
            if v is not None:
                try:
                    v = float(v)
                    any_value = True
                except (TypeError, ValueError):
                    v = None
            row[f] = v
        if any_value:
            out.append(row)
    return out


# --- Open-Meteo Archive API (ERA5 daily precipitation, antecedent-rain proxy) ------------
#
# archive-api.open-meteo.com/v1/archive?daily=precipitation_sum -- no API key. Secondary
# antecedent-wetness proxy alongside soil_moisture above (same founder gap). Historical
# reanalysis, day-boundary caveat applies (see units_datum_crosswalk.yaml
# day_boundary_mismatch -- Open-Meteo's own local-midnight day, not a UTC calendar day).

OPENMETEO_ARCHIVE_PRECIP_URL_TMPL = (
    "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
    "&start_date={start_date}&end_date={end_date}&daily=precipitation_sum"
    "&timezone=Asia%2FBangkok"
)


def openmeteo_archive_precip_url(lat: float, lon: float, start_date: str, end_date: str) -> str:
    return OPENMETEO_ARCHIVE_PRECIP_URL_TMPL.format(
        lat=lat, lon=lon, start_date=start_date, end_date=end_date)


def parse_openmeteo_archive_precip(data: dict) -> list:
    """
    Open-Meteo Archive `/v1/archive?daily=precipitation_sum` JSON -> [{"date":
    "YYYY-MM-DD", "precipitation_sum_mm": float}]. A day missing its value is skipped,
    never fabricated as 0."""
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    vals = daily.get("precipitation_sum") or []
    out = []
    for i, d in enumerate(dates):
        if i >= len(vals) or vals[i] is None:
            continue
        try:
            v = float(vals[i])
        except (TypeError, ValueError):
            continue
        out.append({"date": d, "precipitation_sum_mm": v})
    return out


# --- GDACS event list (country-level flood trip-wire, open, no key) ----------------------
#
# www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP -- no API key. The `country=`
# query param does NOT filter server-side (confirmed 2026-09-27, see
# docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #8) -- this parser
# filters client-side on `iso3`/`country`. Country-level granularity only, a trip-wire
# signal for PROP-FLOOD-08's D_critical calibration, never a per-tambon/per-station
# reading.

GDACS_EVENT_LIST_URL_TMPL = (
    "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
    "?country=Thailand&fromdate={fromdate}&todate={todate}"
)


def gdacs_event_list_url(fromdate: str, todate: str) -> str:
    return GDACS_EVENT_LIST_URL_TMPL.format(fromdate=fromdate, todate=todate)


def parse_gdacs_events_thailand(data: dict) -> list:
    """
    GDACS `geteventlist/EVENTS4APP` GeoJSON-like JSON -> Thailand-only flood events,
    client-side filtered on `iso3`/`country` fields (the server's own `country=` query
    param does not filter, confirmed by direct observation -- see this function's module
    docstring). Returns [{"event_id", "event_type", "name", "from_date", "to_date",
    "lat", "lon", "alert_level"}] for records whose eventtype is FL (flood) AND whose
    country/iso3 mentions Thailand -- other event types for Thailand are skipped (this
    repo cares about flood trip-wires only here), never silently included as flood
    events."""
    features = data.get("features") or data.get("result") or []
    if isinstance(data, list):
        features = data
    out = []
    for f in features:
        props = f.get("properties") or f
        country = str(props.get("country") or "")
        iso3 = str(props.get("iso3") or "")
        eventtype = props.get("eventtype")
        if "Thailand" not in country and iso3.upper() != "THA":
            continue
        if eventtype and eventtype != "FL":
            continue
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") if isinstance(geom, dict) else None
        lon, lat = (coords[0], coords[1]) if coords and len(coords) >= 2 else (None, None)
        out.append({
            "event_id": props.get("eventid"),
            "event_type": eventtype,
            "name": props.get("name") or props.get("eventname"),
            "from_date": props.get("fromdate"),
            "to_date": props.get("todate"),
            "lat": lat,
            "lon": lon,
            "alert_level": props.get("alertlevel"),
        })
    return out


# --- Open-Meteo pressure (multi-model, hourly, past+forecast) -- storm-track context -----
#
# api.open-meteo.com/v1/forecast?hourly=pressure_msl&models=... -- no API key. Founder
# addition 2026-09-27 ("เอาเลย"): mean-sea-level pressure per model, past_days=7 +
# forecast_days=16, same 9-model list as openmeteo_forecast16d. Data only -- no danger
# threshold derived here (a draft promoter is a separate Toledo task per the founder's own
# instruction). Multi-model hourly response names each model's column
# `pressure_msl_<model>`, confirmed by a live shape check this check.

OPENMETEO_PRESSURE_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=pressure_msl&past_days=7&forecast_days=16&models=" +
    "ecmwf_ifs025,gfs_seamless,icon_seamless,jma_seamless,gem_seamless,"
    "meteofrance_seamless,ukmo_seamless,knmi_seamless,cma_grapes_global"
    + "&timezone=Asia%2FBangkok"
)


def openmeteo_pressure_url(lat: float, lon: float) -> str:
    return OPENMETEO_PRESSURE_URL_TMPL.format(lat=lat, lon=lon)


def parse_openmeteo_pressure_multimodel(data: dict) -> list:
    """
    Open-Meteo hourly `pressure_msl_<model>` (past+forecast) JSON -> one row per
    (model, hour): [{"time_local": str, "model": str, "pressure_msl_hpa": float}]. A
    (model, hour) with a null value is skipped, never fabricated -- same discipline as
    parse_openmeteo_multimodel_daily in tools/harvest/forecast7d_draft.py, applied to an
    hourly multi-model field instead of a daily one."""
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    out = []
    for key, values in hourly.items():
        if not key.startswith("pressure_msl_"):
            continue
        model = key[len("pressure_msl_"):]
        for i, t in enumerate(times):
            v = values[i] if i < len(values) else None
            if v is None:
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            out.append({"time_local": t, "model": model, "pressure_msl_hpa": v})
    return out


# --- Open-Meteo Marine sea-surface temperature (multi-point, one request) ----------------
#
# marine-api.open-meteo.com/v1/marine?hourly=sea_surface_temperature -- no API key.
# Founder addition 2026-09-27 ("เอาเลย เชื่อมเลย"): 3 sea points (upper Gulf of Thailand,
# South China Sea off Vietnam, Andaman Sea) in ONE comma-separated request (Open-Meteo's
# multi-coordinate marine endpoint returns a JSON ARRAY, one object per point, in the SAME
# order as the input lat/lon lists -- confirmed by a live shape check this check, NOT a
# dict keyed by point name).

OPENMETEO_SST_POINTS = {
    "gulf_of_thailand_upper": (13.20, 100.60),
    "south_china_sea_vietnam": (12.00, 110.00),
    "andaman_sea": (9.00, 97.50),
}


def openmeteo_sst_url(points: "dict[str, tuple[float, float]]" = OPENMETEO_SST_POINTS) -> str:
    lats = ",".join(str(lat) for lat, _ in points.values())
    lons = ",".join(str(lon) for _, lon in points.values())
    return (
        f"https://marine-api.open-meteo.com/v1/marine?latitude={lats}&longitude={lons}"
        "&hourly=sea_surface_temperature&past_days=7&forecast_days=3"
        "&timezone=Asia%2FBangkok"
    )


def parse_openmeteo_sst_multipoint(data, point_ids: list) -> dict:
    """
    Open-Meteo Marine multi-coordinate `sea_surface_temperature` JSON (a LIST of per-point
    objects, in request order) -> {point_id: [{"time_local": str, "sst_degc": float}, ...]}.
    `point_ids` must be given in the SAME order the request's lat/lon lists were built in
    (see openmeteo_sst_url) -- this function does not itself know point names, only
    positional order, same as the API's own response. A point whose response is shorter
    than `point_ids` (malformed/partial payload) is simply not present in the output dict,
    never fabricated."""
    if not isinstance(data, list):
        data = [data]
    out = {}
    for i, point_id in enumerate(point_ids):
        if i >= len(data):
            continue
        hourly = (data[i] or {}).get("hourly") or {}
        times = hourly.get("time") or []
        vals = hourly.get("sea_surface_temperature") or []
        rows = []
        for j, t in enumerate(times):
            v = vals[j] if j < len(vals) else None
            if v is None:
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            rows.append({"time_local": t, "sst_degc": v})
        out[point_id] = rows
    return out


# --- NOAA CPC ENSO Oceanic Nino Index (monthly text table, no key) -----------------------
#
# cpc.ncep.noaa.gov/data/indices/oni.ascii.txt -- no API key. Founder addition 2026-09-27.
# Fixed-width-ish whitespace-separated text: header row "SEAS YR TOTAL ANOM" then one row
# per 3-month rolling season since 1950 (SEAS is a 3-letter season code e.g. "JJA", YR is
# the season's ending calendar year, TOTAL is the SST anomaly base value, ANOM is the ONI
# anomaly itself, degC). This parser returns only the LATEST row (most recent season) plus
# keeps the season label -- slow index, fetched at most once/24h by the caller (see
# collect_noaa_oni).

NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


def parse_noaa_oni_latest(text: str) -> "Optional[dict]":
    """Whitespace-split text table -> the LAST parseable data row as
    {"season": str, "year": int, "total_degc": float, "anom_degc": float}, or None if no
    data row was found (never fabricated)."""
    last = None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        season, year, total, anom = parts
        if season.upper() == "SEAS":
            continue
        try:
            year_i = int(year)
            total_f = float(total)
            anom_f = float(anom)
        except ValueError:
            continue
        last = {"season": season, "year": year_i, "total_degc": total_f, "anom_degc": anom_f}
    return last


# --- RID reservoir web-app `api/dams` (app.rid.go.th/reservoir) -------------------------
#
# Confirmed 2026-10-03 (real POST, `{"date": "<YYYY-MM-DD>"}`, no auth): returns a real
# JSON payload keyed by `regions` (เหนือ/ตะวันออกเฉียงเหนือ/กลาง/ตะวันตก/ตะวันออก/ใต้), each
# holding a `dams` list. Includes เขื่อนภูมิพล, เขื่อนสิริกิติ์ (region เหนือ) and
# เขื่อนป่าสักชลสิทธิ์ (region กลาง) -- the Chao Phraya-basin feeder dams whose release
# decisions are directly Bangkok-relevant. `DMD_QUse` is the dam's CURRENT storage
# (MCM, not a capacity field);
# `DAM_QMax` is the dam's maximum/gross capacity. Numeric fields arrive as strings
# (`"9510.00"`) or the literal placeholder `" - "` for a missing reading -- never
# fabricated, left None. This source field-overlaps `hii_dam` (storage/inflow/release for
# the same large-dam set, from HII's telemetry instead of RID's own reservoir app) -- kept
# as a cross-check source, never a silent duplicate: both are wired, `source_id` differs,
# and a consumer that wants one authoritative reading picks per its own trust-tier policy,
# this layer does not resolve it for them.

_RID_DAMS_NUM_FIELDS = {
    "DAM_QMax": "capacity_mcm",
    "DAM_QStore": "storage_norm_mcm",
    "DAM_QUsage": "usable_capacity_mcm",
    "DUL_Useless": "dead_storage_mcm",
    "DMD_QUse": "storage_current_mcm",
    "PERCENT_DMD_QUse": "storage_pct",
    "DMD_Inflow": "inflow_daily_mcm",
    "SUM_Inflow": "inflow_cum_mcm",
    "DMD_Outflow": "release_daily_mcm",
    "SUM_Outflow": "release_cum_mcm",
}


def _rid_dams_num(s) -> "float | None":
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_rid_app_reservoir(data: dict) -> list:
    """`api/dams` JSON (see module comment above) -> one row per dam:
    [{dam_id, name_th, region_th, lat, lon, date, capacity_mcm, storage_norm_mcm,
    usable_capacity_mcm, dead_storage_mcm, storage_current_mcm, storage_pct,
    inflow_daily_mcm, inflow_cum_mcm, release_daily_mcm, release_cum_mcm}]. A dam with no
    coordinate pair is still returned (coordinate presence checked by the caller, same
    posture as `parse_rid9_chonburi_rpt` for dams with no coordinate at all) -- this
    endpoint DOES carry `DAM_Lat`/`DAM_Lon` for every dam seen on the real capture, unlike
    `rid_res_table`."""
    out = []
    for region in data.get("regions", []):
        region_th = region.get("region_name")
        for dam in region.get("dams", []):
            row = {
                "dam_id": dam.get("DAM_ID"),
                "name_th": dam.get("DAM_Name"),
                "region_th": region_th,
                "lat": dam.get("DAM_Lat"),
                "lon": dam.get("DAM_Lon"),
                "date": dam.get("DMD_Date"),
            }
            for src_field, out_field in _RID_DAMS_NUM_FIELDS.items():
                row[out_field] = _rid_dams_num(dam.get(src_field))
            out.append(row)
    return out


# --- HII analyst CCTV station catalog (api-v3.thaiwater.net .../analyst/cctv) ----------
#
# Confirmed 2026-10-03 from a real live fetch (200, JSON): each record is a camera/station
# with a coordinate and a `cctv_url` (the actual video/image feed, owned by whichever
# agency installed that specific camera -- DWR/EGAT/RID per record, not HII itself). No
# water-level/discharge numeric reading lives on this endpoint -- it is an asset
# (camera-station) catalog, same shape as `parse_hii_watergate`'s station list, not a
# telemetry value. Stored as documents (one per camera), never as a fabricated
# observation row, same discipline as `parse_rid_res_table`.

def parse_hii_analyst_cctv(data: dict) -> list:
    """`analyst/cctv` JSON (`{"result": "OK", "data": [...]}`) -> normalised camera rows:
    [{station_id, title, lat, lon, basin_name_th, province_th, agency_en, cctv_url,
    is_active}]. A record with no valid coordinate or no station id is skipped, never
    fabricated (see `_valid_th_coord`)."""
    out = []
    for rec in data.get("data", []) or []:
        station_id = rec.get("id")
        if not station_id:
            continue
        lat, lon = rec.get("lat"), rec.get("long")
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        if not _valid_th_coord(lat_f, lon_f):
            continue
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        geocode = rec.get("geocode") or {}
        out.append({
            "station_id": str(station_id),
            "title": rec.get("title"),
            "lat": lat_f, "lon": lon_f,
            "basin_name_th": (rec.get("basin_name") or {}).get("th"),
            "province_th": (geocode.get("province_name") or {}).get("th"),
            "agency_en": agency,
            "cctv_url": rec.get("cctv_url"),
            "is_active": rec.get("is_active"),
        })
    return out


# --- BMA Pak Khlong river daily max water level CSV (data.bangkok.go.th CKAN resource) --
#
# Confirmed 2026-10-03 from a real live fetch (200, text/csv, 3,692 bytes): a single-
# station daily series, header `DATE,MAX_WATER_LEVEL`, no coordinate on the CSV itself
# (the dataset page names the station "แม่น้ำเจ้าพระยา-ปากคลอง", Pak Khlong on the Chao
# Phraya -- the coordinate below is this check's own lookup of that named point, tagged
# RELAYED in the registry entry, not re-measured here).

def parse_bma_pak_khlong_csv(text: str) -> list:
    """`DATE,MAX_WATER_LEVEL` CSV text -> [{date, max_water_level_m}]. A row whose value
    doesn't parse as a float is skipped, never fabricated."""
    out = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return out
    header = [h.strip().upper() for h in lines[0].split(",")]
    if header[:2] != ["DATE", "MAX_WATER_LEVEL"]:
        return out  # unexpected shape -- caller treats this as "0 rows", never guesses
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date_s, value_s = parts[0].strip(), parts[1].strip()
        try:
            value = float(value_s)
        except ValueError:
            continue
        out.append({"date": date_s, "max_water_level_m": value})
    return out


# --- data.bangkok.go.th CKAN catalog search (BMA open-data portal) --------------------
#
# Confirmed 2026-10-03 from a real live fetch (200, JSON): a standard CKAN
# `package_search` response -- a dataset-metadata catalog, not a telemetry reading in
# itself. Stored as one document per matched dataset (id/title/resource count/url), so a
# human/future collector can see what BMA has published without this check guessing a
# per-dataset parser for every entry.

def parse_bangkok_ckan_catalog(data: dict) -> list:
    """CKAN `package_search` JSON -> [{dataset_id, title_th, organization, num_resources,
    resource_urls}]. Returns [] if `success` is falsy, never fabricates a dataset."""
    out = []
    if not data.get("success"):
        return out
    for pkg in (data.get("result") or {}).get("results", []) or []:
        out.append({
            "dataset_id": pkg.get("id") or pkg.get("name"),
            "title_th": pkg.get("title"),
            "organization": (pkg.get("organization") or {}).get("title"),
            "num_resources": pkg.get("num_resources"),
            "resource_urls": [r.get("url") for r in pkg.get("resources", []) if r.get("url")],
        })
    return out


def _parse_bangkok_lat(raw) -> float | None:
    """Return a float only when it falls in Thailand's plausible latitude envelope
    (5-20 N) -- this open-data CSV mixes real coordinates with garbage (a
    phone-number-shaped string, e.g. "0-2541-1933", was observed in a `lat` cell on a
    real 2026-10-03 capture). Anything outside that envelope, or that doesn't parse as
    a float at all, is treated as missing, never coerced or guessed."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if 5.0 < v < 20.0 else None


def _parse_bangkok_lon(raw) -> float | None:
    """Same discipline as `_parse_bangkok_lat` for longitude (95-105 E)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if 95.0 < v < 105.0 else None


def _parse_bangkok_number(raw):
    """Best-effort float for a threshold/count cell that is frequently a composite
    Thai-language note instead of a plain number (e.g. "35(3)+10(5)") on this open-data
    CSV. Returns the float when the cell parses cleanly, otherwise the original
    stripped string verbatim (for provenance), never a fabricated number."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return s


def parse_bangkok_floodgate_locations(text: str) -> list:
    """data.bangkok.go.th Open Data `floodgate.csv` -> [{id, name_th, type_th, district,
    lat, lon, gate_opening_height_m, water_control, critical, warning}]. Real capture
    (2026-10-03) has quoted multi-line Thai-text cells, so this uses the stdlib `csv`
    module (not a naive line-split) -- a naive split overcounts/undercounts rows the
    moment a cell contains an embedded newline. A row with no valid lat/lon
    (see `_parse_bangkok_lat`/`_parse_bangkok_lon`) is skipped, never geocoded or
    guessed. Threshold
    cells that aren't a plain number are kept as the original string (see
    `_parse_bangkok_number`) -- this is static reference/design data, not a live
    reading, so no value here is ever a telemetry observation."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        lat = _parse_bangkok_lat(row.get("lat"))
        lon = _parse_bangkok_lon(row.get("long"))
        if lat is None or lon is None:
            continue
        out.append({
            "id": (row.get("id") or "").strip(),
            "name_th": (row.get("name") or "").strip(),
            "type_th": (row.get("type") or "").strip(),
            "district": (row.get("district") or "").strip(),
            "lat": lat,
            "lon": lon,
            "gate_opening_height_m": _parse_bangkok_number(row.get("gate")),
            "water_control": _parse_bangkok_number(row.get("water_control")),
            "critical": _parse_bangkok_number(row.get("critical")),
            "warning": _parse_bangkok_number(row.get("warning")),
        })
    return out


def parse_bangkok_pump_stations(text: str) -> list:
    """data.bangkok.go.th Open Data pump-station-and-floodgate physical-data CSV ->
    [{id, name_th, type_th, district, lat, lon, gate_count, pump_count, total_capacity,
    water_control, critical, warning}]. Same `csv`-module/coordinate-validation/
    best-effort-number discipline as `parse_bangkok_floodgate_locations` -- see that
    function's docstring; a composite capacity cell (e.g. "35(3)+10(5)") is kept as a
    string, never summed or guessed into a single number."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        lat = _parse_bangkok_lat(row.get("gp_lat"))
        lon = _parse_bangkok_lon(row.get("gp_long"))
        if lat is None or lon is None:
            continue
        out.append({
            "id": (row.get("gp_id") or "").strip(),
            "name_th": (row.get("gp_name") or "").strip(),
            "type_th": (row.get("gp_type") or "").strip(),
            "district": (row.get("district") or "").strip(),
            "lat": lat,
            "lon": lon,
            "gate_count": _parse_bangkok_number(row.get("gp_gate")),
            "pump_count": _parse_bangkok_number(row.get("gp_pump")),
            "total_capacity": _parse_bangkok_number(row.get("gp_total_capacity")),
            "water_control": _parse_bangkok_number(row.get("gp_water_control")),
            "critical": _parse_bangkok_number(row.get("gp_critical")),
            "warning": _parse_bangkok_number(row.get("gp_warning")),
        })
    return out


def parse_rid_app_alert(data: dict) -> list:
    """`api/alert` JSON -> a flat list of alert rows (each tagged `kind`: "Dam" or
    "Reservoir"), or an empty list on a real capture with no active alert (`{"Dam":[],
    "Reservoir":[]}` on 2026-10-03 -- an empty list here means "no alert observed at
    capture time", never "alerting is broken"; see collect.collect_rid_app_reservoir for
    how that distinction is carried into the stored note)."""
    out = []
    for kind in ("Dam", "Reservoir"):
        for item in data.get(kind, []) or []:
            row = dict(item)
            row["kind"] = kind
            out.append(row)
    return out


# --- GOV9 pass (2026-10-03): 4 reachable-but-unwired CSV sources + 2 reachable-but-
# unwired JSON API sources, wired to close the api_census.yaml "plain reachable, not
# wired" backlog (see sources/api_census.yaml census_date 2026-10-03). Every parser here
# follows the same discipline as the rest of this file: a row with no usable coordinate/
# value is skipped, never fabricated; nothing here computes a flood-risk score.

def parse_hii_mou_station_metadata_csv(text: str) -> list:
    """HII watershed-forest (MOU) telemetry station metadata CSV ->
    [{station_code, station_name, lat, lon, basin, province, station_type}]. Nationwide
    reference catalog, not a live reading -- `collect_hii_mou_station_metadata` stores
    one document per station, never an `observations` row (no `value`/`observed_at` of
    its own)."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("Station_Code") or "").strip()
        if not code:
            continue
        try:
            lat = float(row.get("Latitude", "").strip())
            lon = float(row.get("Longitude", "").strip())
        except (ValueError, AttributeError):
            lat = lon = None
        out.append({
            "station_code": code,
            "station_name": (row.get("Station_Name") or "").strip(),
            "lat": lat,
            "lon": lon,
            "basin": (row.get("Basin_Name") or "").strip(),
            "province": (row.get("Province_Name") or "").strip(),
            "station_type": (row.get("Station_Type_Name") or "").strip(),
        })
    return out


def parse_dnp_yom_telemetry_csv(text: str) -> list:
    """DNP Yom-basin telemetry station list CSV (Thai headers) ->
    [{station_code, station_name, tambon, amphoe, province, station_type, utm_zone, x, y,
    status_th}]. Station-siting reference for Phayao-province stations, OUTSIDE this
    repo's current Sammakorn/Ram53/bangkok_east area scope (see
    collect.AREA_RELEVANT_SOURCES) -- several sample rows carry status_th
    'ไม่มีการอัปเดตข้อมูลแล้ว (offline)', kept verbatim, never dropped or translated into
    a different status."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("รหัสสถานี") or "").strip()
        if not code:
            continue
        try:
            x = float(row.get("X", "").strip())
            y = float(row.get("Y", "").strip())
        except (ValueError, AttributeError):
            x = y = None
        out.append({
            "station_code": code,
            "station_name": (row.get("ชื่อสถานี") or "").strip(),
            "tambon": (row.get("ตำบล") or "").strip(),
            "amphoe": (row.get("อำเภอ") or "").strip(),
            "province": (row.get("จังหวัด") or "").strip(),
            "station_type": (row.get("ประเภท") or "").strip(),
            "utm_zone": (row.get("UTM Zone") or "").strip(),
            "utm_x": x,
            "utm_y": y,
            "status_th": (row.get("สถานะ") or "").strip(),
        })
    return out


def parse_pcd_mwqi_csv(text: str) -> list:
    """PCD marine water-quality-index-by-station CSV (Thai headers) ->
    [{year_be, province, station_name, station_code, mwqi_class_th, mwqi_value}]. A row
    whose MWQI cell doesn't parse as an int is skipped, never fabricated (a handful of
    rows in this dataset carry a blank/'-' value for a station not sampled that year)."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("รหัสสถานี") or "").strip()
        year = (row.get("ปี ") or row.get("ปี") or "").strip()
        if not code or not year:
            continue
        try:
            mwqi = int((row.get("MWQI") or "").strip())
        except ValueError:
            continue
        out.append({
            "year_be": year,
            "province": (row.get("จังหวัด") or "").strip(),
            "station_name": (row.get("ชื่อสถานี") or "").strip(),
            "station_code": code,
            "mwqi_class_th": (row.get("เกณฑ์คุณภาพน้ำทะเล") or "").strip(),
            "mwqi_value": mwqi,
        })
    return out


def parse_dmcr_marine_acidification_csv(text: str) -> list:
    """DMCR marine-acidification mooring CSV -> [{mooring_name, lat, lon, observed_at_utc,
    temp_c, salinity_psu, ph_tot}]. `DATE_UTC`+`TIME_UTC` are combined into one ISO
    timestamp; a row with an unparseable timestamp or temp/pH is skipped, never
    fabricated. Column names vary in trailing-space style across this real CSV (e.g.
    `CTDSAL ` with a trailing space) -- headers are stripped before lookup."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        row = {(k or "").strip(): v for k, v in row.items()}
        name = (row.get("MOORING_NAME") or "").strip()
        date_s = (row.get("DATE_UTC") or "").strip()
        time_s = (row.get("TIME_UTC") or "").strip()
        if not name or not date_s or not time_s:
            continue
        try:
            observed_at = f"{date_s}T{time_s}:00+00:00"
            datetime.datetime.fromisoformat(observed_at)
        except ValueError:
            continue
        try:
            lat = float(row.get("LATITUDE", "").strip())
            lon = float(row.get("LONGITUDE", "").strip())
        except (ValueError, AttributeError):
            lat = lon = None
        try:
            temp_c = float(row.get("CTDTMP", "").strip())
        except (ValueError, AttributeError):
            temp_c = None
        try:
            salinity = float(row.get("CTDSAL", "").strip())
        except (ValueError, AttributeError):
            salinity = None
        try:
            ph_tot = float(row.get("PH_TOT", "").strip())
        except (ValueError, AttributeError):
            ph_tot = None
        out.append({
            "mooring_name": name,
            "lat": lat,
            "lon": lon,
            "observed_at_utc": observed_at,
            "temp_c": temp_c,
            "salinity_psu": salinity,
            "ph_tot": ph_tot,
        })
    return out


def _dms_to_decimal(dms) -> "float | None":
    """[deg, min, sec] -> decimal degrees. Returns None on any non-3-element or
    non-numeric input, never a guessed value."""
    if not isinstance(dms, (list, tuple)) or len(dms) != 3:
        return None
    try:
        deg, mn, sec = (float(x) for x in dms)
    except (TypeError, ValueError):
        return None
    return deg + mn / 60.0 + sec / 3600.0


def parse_royalrain_operations(data: dict) -> list:
    """Royal Rainmaking Dept `dailyoperationsequenceinfo` JSON ->
    [{operation_date, center_name, unit_name, is_operation, memo, track_count, lat, lon}].
    `lat`/`lon` are the first mission track's start point (DMS->decimal), nationwide
    cloud-seeding flight operations -- NOT a canal/flood telemetry reading, OUTSIDE this
    repo's current area scope (see collect.AREA_RELEVANT_SOURCES). A record with no
    `missions` carries lat=lon=None, never a fabricated coordinate."""
    out = []
    for rec in data.get("data") or []:
        lat = lon = None
        track_count = 0
        for mission in rec.get("missions") or []:
            for track in mission.get("tracks") or []:
                track_count += 1
                if lat is None:
                    start = track.get("trackStart") or {}
                    lat = _dms_to_decimal(start.get("latitude"))
                    lon = _dms_to_decimal(start.get("longitude"))
        out.append({
            "operation_date": rec.get("operationDate"),
            "center_name": rec.get("operationCenterName"),
            "unit_name": rec.get("operationUnitName"),
            "is_operation": rec.get("isOperation") == "Y",
            "memo": (rec.get("operationMemo") or "").strip(),
            "track_count": track_count,
            "lat": lat,
            "lon": lon,
        })
    return out


def parse_royalrain_agriculture_rainfall(data: dict) -> list:
    """Royal Rainmaking Dept `summaryagricultureareainfo` JSON ->
    [{operation_date, center_name, unit_name, is_rainy_on_target_area, rain_quantity_th,
    province_count}]. No coordinate field exists in this real payload (province/district
    name/code only) -- `has_coords` is NOT claimed for this source, correcting the
    api_census.yaml row's earlier RELAYED/unconfirmed `has_coords: True` guess."""
    out = []
    for rec in data.get("data") or []:
        provinces = rec.get("agricultureAreaProvice") or []
        out.append({
            "operation_date": rec.get("operationDate"),
            "center_name": rec.get("operationCenterName"),
            "unit_name": rec.get("operationUnitName"),
            "is_rainy_on_target_area": bool(rec.get("isRainyOnTargetArea")),
            "rain_quantity_th": (rec.get("rainQuantity") or "").strip(),
            "province_count": len(provinces),
        })
    return out


def parse_hii_reservoir_metadata_csv(text: str) -> list:
    """HII small-reservoir metadata CSV (reservoir_metadata.csv, sibling resource of the
    hii_reservoir_elevation_capacity_curve CKAN dataset) ->
    [{reservoir_code, reservoir_name, subdistrict, district, province, lat, lon,
    old_capacity_mcm, updated_capacity_mcm, survey_date}]. A static survey catalog, not
    a live reading -- `CODE`/`ID` are both blank on several real rows (the survey
    predates code assignment); `reservoir_code` falls back to the row's own `No.` so no
    row is dropped for a missing code."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        name = (row.get("Water Resources Name") or "").strip()
        if not name:
            continue
        code = (row.get("CODE") or "").strip() or (row.get("No.") or "").strip()
        try:
            lat = float((row.get("latitude") or "").strip())
            lon = float((row.get("longitude") or "").strip())
        except (ValueError, AttributeError):
            lat = lon = None

        def _mcm(key):
            raw = (row.get(key) or "").strip()
            if not raw:
                return None
            try:
                return float(raw.replace(",", ""))
            except ValueError:
                return None

        out.append({
            "reservoir_code": code,
            "reservoir_name": name,
            "subdistrict": (row.get("Subdistrict") or "").strip(),
            "district": (row.get("District") or "").strip(),
            "province": (row.get("Province") or "").strip(),
            "lat": lat,
            "lon": lon,
            "old_capacity_mcm": _mcm("old capacity (million cubic meters)"),
            "updated_capacity_mcm": _mcm("Updated capacity (million cubic meters)"),
            "survey_date": (row.get("Survey date") or "").strip(),
        })
    return out


_PCD_THAI_MONTH_ABBREV = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}


def _parse_pcd_date(date_raw: str):
    """This CSV mixes two date spellings for what is, by construction, the same real
    calendar year within one dataset: "10 Mar 25" (English month abbrev, Gregorian
    2-digit year, 2025) and "15 ก.ค. 68" (Thai month abbrev, Buddhist-era 2-digit year,
    2568 -- also 2025 CE). Returns a naive `datetime.date` or None, never guesses a
    year when the month token matches neither vocabulary."""
    parts = date_raw.split()
    if len(parts) != 3:
        return None
    day_raw, month_raw, year_raw = parts
    try:
        day = int(day_raw)
        year2 = int(year_raw)
    except ValueError:
        return None
    if month_raw in _PCD_THAI_MONTH_ABBREV:
        month = _PCD_THAI_MONTH_ABBREV[month_raw]
        year_ce = (2500 + year2) - 543
    else:
        try:
            month = datetime.datetime.strptime(month_raw, "%b").month
        except ValueError:
            return None
        year_ce = 2000 + year2
    try:
        return datetime.date(year_ce, month, day)
    except ValueError:
        return None


def parse_pcd_coastal_marine_quality_csv(text: str) -> list:
    """PCD coastal/marine water-quality monitoring-round CSV (one of the dataset's
    per-round resource files) -> [{station_id, station_name, province, observed_at_utc,
    ph}]. `Date` is a short-year day-month-year string, mixing an English-month-abbrev/
    Gregorian-year spelling and a Thai-month-abbrev/Buddhist-era-year spelling within
    the same file (see `_parse_pcd_date`) -- both resolve to the same real year.
    Anchored to local noon (Asia/Bangkok, UTC+7) rather than midnight, since the real
    `Time` column already carries a separate per-row sampling time this parser does not
    need to merge in. A row with an unparseable/empty `pH` cell is still returned with
    `ph: None`, never dropped, since station/date identity is still real data."""
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        station_id = (row.get("Station ID") or "").strip()
        if not station_id:
            continue
        date_raw = (row.get("Date") or "").strip()
        d = _parse_pcd_date(date_raw)
        if d is not None:
            observed_at = datetime.datetime(
                d.year, d.month, d.day, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
        else:
            observed_at = None
        ph_raw = (row.get("pH") or "").strip()
        try:
            ph = float(ph_raw) if ph_raw else None
        except ValueError:
            ph = None
        out.append({
            "station_id": station_id,
            "station_name": (row.get("Station Name") or "").strip(),
            "province": (row.get("Province") or "").strip(),
            "observed_at_utc": observed_at,
            "ph": ph,
        })
    return out


# --- BMA StationDetail inline history series (weather.bangkok.go.th/water/StationDetail) --
#
# Fix (FloodConnect M8, 2026-10-05, blocking finding #2): the page's inline Highcharts
# `Date.UTC(Y, M0, D, h, m, s)` literal already needs M0+1 (confirmed: BMA's own month
# index is 0-based JS-style, e.g. M0=8 for September) -- `tools/harvest/
# bma_station_detail_draft.parse_history_series` already does that part correctly. What
# it does NOT do is correct the clock: BMA bakes Bangkok LOCAL wall-clock time into this
# literal, not UTC, even though the function name says `.UTC` and the page's own call is
# literally `Date.UTC(...)` -- the page's timestamps are simply mislabelled, confirmed by
# cross-checking a real sample against the same station's watermap `site_timestampTH`
# for the same instant (both local, both agreeing once the 7h offset is applied).
# Un-fixed, every stored `station_level_history_m` row this repo has collected so far is
# 7 hours off (see tests/test_bma_station_detail.py's old pin, corrected alongside this
# function).
_BMA_STATION_SERIES_RE = re.compile(
    r"Date\.UTC\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\),\s*([\-\d\.]+)"
)
BMA_LOCAL_UTC_OFFSET = datetime.timedelta(hours=7)


def parse_bma_station_series(html: str, wl_in_now: "float | None" = None,
                              observed_at_now: "str | None" = None) -> dict:
    """Parse the inline Highcharts water-level series baked into a BMA StationDetail
    page -- there is no separate JSON endpoint for this (docs/knowledge/
    BMA_STATION_DETAIL_PROBE.md section 2).

    Each `Date.UTC(Y, M0, D, h, m, s)` literal is Bangkok LOCAL time with a 0-based month
    (BMA's own convention) -- this function adds 1 to the month, builds a naive local
    datetime, then subtracts `BMA_LOCAL_UTC_OFFSET` (7h) to get the real UTC instant,
    emitted as `t_utc` (ISO, `Z` suffix). `v` is the station's raw metre reading, verbatim.

    One archived sample (id51/WL.SSB.12) concatenates TWO runs back to back (inner+outer
    canal) covering the same ~2-day window -- this function splits wherever the
    timestamp goes backwards (a real run boundary, never inferred from point count) and
    returns every run found in `runs` (list of point-lists), picking `chosen_run` (an
    index into `runs`, or None) as follows:
      - exactly one run -> chosen_run = 0, status "OK" (or "SPARSE_SERIES" if that run
        has fewer than 2 points -- too few to compute a trend/lag at all);
      - zero runs (no Date.UTC literal matched at all, e.g. the real empty-series case
        this repo has seen for WL.SSB.13/id 312) -> chosen_run = None, status "EMPTY";
      - more than one run: if `wl_in_now`/`observed_at_now` are given, the run whose
        last point before-or-at `observed_at_now` equals `wl_in_now` (within 0.005 m,
        BMA's own 2-decimal publication resolution) is chosen; if none or more than one
        run matches -> chosen_run = None, status "AMBIGUOUS" (the trend from an
        ambiguous split is UNKNOWN, never guessed); without both of those two
        disambiguating args, multiple runs are also AMBIGUOUS (this function never
        silently assumes "the last run is the real one").

    Returns {"points": [{"t_utc", "v"}, ...] (ALL points, every run, in page order --
    unsplit, for a caller that wants the raw series regardless), "step_s": int|None (the
    modal gap between consecutive points within the chosen run, seconds; None if
    `chosen_run` is None or has <2 points), "runs": [[{"t_utc","v"}, ...], ...],
    "chosen_run": int|None, "status": "OK"|"EMPTY"|"SPARSE_SERIES"|"AMBIGUOUS"}."""
    points = []
    for y, mo, d, h, mi, s, v in _BMA_STATION_SERIES_RE.findall(html):
        local_naive = datetime.datetime(int(y), int(mo) + 1, int(d), int(h), int(mi), int(s))
        utc_dt = local_naive - BMA_LOCAL_UTC_OFFSET
        try:
            value = float(v)
        except ValueError:
            continue
        points.append({"t_utc": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "v": value,
                        "_local": local_naive})

    if not points:
        return {"points": [], "step_s": None, "runs": [], "chosen_run": None, "status": "EMPTY"}

    runs: list = [[]]
    prev_local = None
    for p in points:
        if prev_local is not None and p["_local"] < prev_local:
            runs.append([])
        runs[-1].append({"t_utc": p["t_utc"], "v": p["v"]})
        prev_local = p["_local"]

    all_points = [{"t_utc": p["t_utc"], "v": p["v"]} for p in points]

    def _step_s(run):
        if len(run) < 2:
            return None
        gaps = []
        for i in range(1, min(len(run), 6)):
            t0 = datetime.datetime.strptime(run[i - 1]["t_utc"], "%Y-%m-%dT%H:%M:%SZ")
            t1 = datetime.datetime.strptime(run[i]["t_utc"], "%Y-%m-%dT%H:%M:%SZ")
            gaps.append((t1 - t0).total_seconds())
        return max(set(gaps), key=gaps.count) if gaps else None

    if len(runs) == 1:
        run = runs[0]
        if len(run) < 2:
            return {"points": all_points, "step_s": None, "runs": runs, "chosen_run": 0,
                    "status": "SPARSE_SERIES"}
        return {"points": all_points, "step_s": _step_s(run), "runs": runs, "chosen_run": 0,
                "status": "OK"}

    if wl_in_now is None or observed_at_now is None:
        return {"points": all_points, "step_s": None, "runs": runs, "chosen_run": None,
                "status": "AMBIGUOUS"}
    matches = []
    for idx, run in enumerate(runs):
        candidates = [p for p in run if p["t_utc"] <= observed_at_now]
        if not candidates:
            continue
        last = candidates[-1]
        if abs(last["v"] - wl_in_now) <= 0.005:
            matches.append(idx)
    if len(matches) != 1:
        return {"points": all_points, "step_s": None, "runs": runs, "chosen_run": None,
                "status": "AMBIGUOUS"}
    chosen = matches[0]
    run = runs[chosen]
    if len(run) < 2:
        return {"points": all_points, "step_s": None, "runs": runs, "chosen_run": chosen,
                "status": "SPARSE_SERIES"}
    return {"points": all_points, "step_s": _step_s(run), "runs": runs, "chosen_run": chosen,
            "status": "OK"}
