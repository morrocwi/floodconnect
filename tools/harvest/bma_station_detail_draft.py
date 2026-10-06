"""
DRAFT parser for the BMA weather.bangkok.go.th/water/StationDetail?id={water_id} page and
its sibling read-only endpoints (CreateCrossection, WaterHistory). See
docs/knowledge/BMA_STATION_DETAIL_PROBE.md for the full readout, endpoint table, and
proposed collector spec (source id `bma_station_thresholds`, not yet registered).

Status: DRAFT ONLY. Not wired into collect.py. Pure functions over already-archived HTML
samples (raw/live/bma_station_detail/*.html) -- this module makes NO network calls itself,
per this workspace's one-request-per-URL / no-retry rule on weather.bangkok.go.th.

Epistemic tags: values returned by these functions are MEASURED only insofar as the input
HTML itself is an unmodified archived BMA response -- this module performs no inference, no
fabrication, and no unit conversion beyond what BMA's own page already encodes (metres,
per the page's own labels "ม. รทก.").

Scope note: this module is READ-ONLY by design. It has no function for
`/water/StationDetail/Login` or `/water/StationDetail/UpdateStationinfo` (the write path) --
those are out of scope for a collector and are not to be called from any future wiring of
this draft either.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# The admin-edit-form input ids this page renders with the station's current values already
# filled in (readable via a plain unauthenticated GET -- only *writing* them back via
# /water/StationDetail/UpdateStationinfo requires the login session). See
# docs/knowledge/BMA_STATION_DETAIL_PROBE.md section 2's endpoint table.
FIELD_IDS = (
    "txt_water_code",
    "txt_water_name",
    "txt_water_shortname",
    "txt_left_bank",
    "txt_right_bank",
    "txt_bed_bank",
    "txt_water_control",
    "txt_warning",
    "txt_critical",
    "txt_warning_out01",
    "txt_critical_out01",
    "txt_warning_out02",
    "txt_critical_out02",
)

_FIELD_RE = re.compile(r'id="(txt_\w+)"[^>]*value="([^"]*)"')
_TITLE_H3_RE = re.compile(
    r'id="station_name_display"[^>]*>\s*(.*?)\s*</h3>', re.DOTALL
)


def load_html(path: str | Path) -> str:
    """Load an archived StationDetail (or WaterHistory) HTML page from disk. No network call."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def parse_station_detail_fields(html: str) -> dict[str, str | None]:
    """
    Extract the admin-edit-form field values BMA already renders unauthenticated on a
    StationDetail page -- this is where `water_control` (the founder's "control/normal
    level" question) actually lives; PageMap/GoogleMap exposes the same-named field but
    null for every station (see docs/knowledge/BMA_WATER_MAP_PROBE.md).

    A missing field or a literal "-" placeholder (BMA's own "not applicable" marker, seen
    on e.g. txt_warning_out02 for single-outer-canal stations) is returned as None -- never
    fabricated as 0 or empty string, per this repo's never-fabricate-a-number rule.
    """
    found = dict(_FIELD_RE.findall(html))
    out: dict[str, str | None] = {}
    for field_id in FIELD_IDS:
        value = found.get(field_id)
        if value is None or value.strip() in ("", "-"):
            out[field_id] = None
        else:
            out[field_id] = value.strip()
    return out


def water_control_value(html: str) -> dict[str, Any]:
    """
    Answer the founder's specific question for one archived StationDetail sample: does this
    page carry a populated control/target ("ระดับน้ำควบคุม") level for this station? Returns
    a small readout dict (value + tag) rather than a bare number, so a caller never has to
    re-derive whether the value was actually present vs. defaulted.
    """
    fields = parse_station_detail_fields(html)
    raw = fields.get("txt_water_control")
    if raw is None:
        return {"water_control": None, "tag": "OPEN"}
    try:
        return {"water_control": float(raw), "tag": "MEASURED"}
    except ValueError:
        return {"water_control": None, "tag": "OPEN"}


def parse_station_name(html: str) -> str | None:
    """Extract the human-readable station display name (river + station), if present."""
    m = _TITLE_H3_RE.search(html)
    if not m:
        return None
    # Collapse internal whitespace; the source HTML has irregular indentation here.
    return re.sub(r"\s+", " ", m.group(1)).strip() or None


def parse_history_series(html: str) -> list[dict[str, Any]]:
    """
    Extract the inline Highcharts water-level series baked directly into a StationDetail
    page's <script> block (there is no separate JSON endpoint for this -- see
    docs/knowledge/BMA_STATION_DETAIL_PROBE.md section 2). Returns a list of
    {"timestamp_utc": "...", "value": float} rows in the order BMA emitted them, EVERY
    point/run concatenated (unsplit) -- same shape this function has always returned, so
    `collect.collect_bma_station_detail` (which stores these as-is with
    `provenance.series_split="unresolved"`) needs no change.

    FIX (FloodConnect M8, 2026-10-05, blocking finding #2): this function now delegates
    to `parsers.parse_bma_station_series`, which corrects a 7-hour bug this function
    used to carry -- the raw `Date.UTC(...)` literal is Bangkok LOCAL time, not UTC,
    even though the page labels it `.UTC` and this function used to pass that label
    straight through with only the month fixed (+1). Every `station_level_history_m`
    row collected before this fix is 7h wrong in the DB (append-only, not rewritten --
    see `live_water_level.py`'s own note on the same append-only discipline for a
    different bug). The month-index fix (BMA's 0-based month) is unchanged.

    Caution (documented, not fixed here): in the one archived sample this repo has seen
    (id51/WL.SSB.12), the raw point list actually concatenates TWO runs covering the same
    2-day window back to back (e.g. an inner-canal series followed by an outer-canal
    series) rather than one clean series. `parse_bma_station_series` now detects and
    splits these runs (a backwards timestamp jump is the split point), but this function
    keeps returning every point from every run concatenated, in page order -- splitting/
    labelling which run is which canal is still OPEN, left to whoever wires that in.
    """
    import parsers
    result = parsers.parse_bma_station_series(html)
    return [{"timestamp_utc": p["t_utc"], "value": p["v"]} for p in result["points"]]


def find_history_rows(html: str) -> list[dict[str, Any]]:
    """
    Extract the WaterHistory search-result table rows, if any (columns: water_code, river,
    station, timestamp, wl_in, wl_out01, wl_out02). In this probe's one archived POST
    sample (dry-season Feb-Mar 2569 request for station 51) this table came back empty --
    this function returns an empty list in that case, which is the honest, MEASURED
    result, not a parsing failure. See docs/knowledge/BMA_STATION_DETAIL_PROBE.md section 3
    for the open hypotheses on why.
    """
    body_match = re.search(
        r'<tbody id="waterhistorybody">(.*?)</tbody>', html, re.DOTALL
    )
    if not body_match:
        return []
    body = body_match.group(1)
    rows = []
    for row_match in re.finditer(r"<tr>(.*?)</tr>", body, re.DOTALL):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_match.group(1), re.DOTALL)
        if len(cells) < 7:
            continue
        rows.append(
            {
                "water_code": cells[0].strip(),
                "river_name": cells[1].strip(),
                "station_name": cells[2].strip(),
                "timestamp": cells[3].strip(),
                "wl_in": cells[4].strip(),
                "wl_out01": cells[5].strip(),
                "wl_out02": cells[6].strip(),
            }
        )
    return rows


def _main(argv: list[str]) -> int:
    """
    Tiny CLI for manual inspection of an archived sample:
        python3 tools/harvest/bma_station_detail_draft.py \
            raw/live/bma_station_detail/stationdetail_id51.html
    Prints the station's admin-form fields, the water_control readout, the history-series
    point count, and (if the file is a WaterHistory response instead) the result-row count.
    Makes no network calls.
    """
    if len(argv) != 2:
        print(f"usage: {argv[0]} <path-to-archived-html>", file=sys.stderr)
        return 2

    html = load_html(argv[1])
    name = parse_station_name(html)
    fields = parse_station_detail_fields(html)
    control = water_control_value(html)
    series = parse_history_series(html)
    history_rows = find_history_rows(html)

    print(f"station name: {name!r}")
    print("admin-form fields:")
    for k, v in fields.items():
        print(f"  {k} = {v}")
    print(
        f"water_control readout: value={control['water_control']} tag={control['tag']}"
    )
    print(f"inline history series points: {len(series)}")
    print(f"WaterHistory result-table rows: {len(history_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
