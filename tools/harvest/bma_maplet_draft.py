"""
DRAFT parser for the BMA water/PageMap/GoogleMap endpoint (successor to the page the
founder pointed at, weather.bangkok.go.th/water/MapLetLeaf, which now 302-redirects to
weather.bangkok.go.th/water/).

Status: DRAFT ONLY. Not wired into collect.py. Pure functions over an already-archived
JSON sample (raw/live/bma_maplet/pagemap_googlemap.json,
raw/live/bma_maplet/sample_pagemap_googlemap.json) -- this file makes NO network calls
itself, per this workspace's one-request-per-URL / no-retry rule on
weather.bangkok.go.th. See docs/knowledge/BMA_WATER_MAP_PROBE.md for the full readout,
field list, and proposed collector spec (source id `bma_watermap`, not yet registered).

Epistemic tags: values returned by these functions are MEASURED only insofar as the input
JSON itself is an unmodified archived BMA response -- this module performs no inference,
no fabrication, and no unit conversion beyond what BMA's own JSON already encodes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

GATE_FIELDS = tuple(f"watergate0{i}" for i in range(1, 7))

# Fields this draft considers worth carrying into a future observation row.
# See docs/knowledge/BMA_WATER_MAP_PROBE.md section 6 ("Fields to store").
KEEP_FIELDS = (
    "water_code",
    "water_name",
    "water_name_en",
    "latitude",
    "longitude",
    "wl_in",
    "wl_out01",
    "wl_out02",
    "warning",
    "critical",
    "warning_out01",
    "critical_out01",
    "warning_out02",
    "critical_out02",
    "water_control",
    "water_gate_count",
    *GATE_FIELDS,
    "txtStatus",
    "txtStatus_en",
    "colorStatus",
    "site_timestampTH",
    "site_timestampEN",
    "district_id",
    "district_name",
)


def load_raw(path: str | Path) -> list[dict[str, Any]]:
    """Load an archived PageMap/GoogleMap JSON response from disk. No network call."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(
            "expected a JSON array of station records, got "
            f"{type(data).__name__} -- archive may be stale or the endpoint shape changed"
        )
    return data


def parse_pagemap_stations(raw: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Project each raw BMA station record down to the fields this repo would plausibly
    store (see KEEP_FIELDS). Passes values through unchanged -- no rounding, no
    inference, no unit assumptions beyond what BMA's JSON already states (metres for
    water levels and gate heights, per the page's own client-side labels).
    """
    out = []
    for rec in raw:
        row = {k: rec.get(k) for k in KEEP_FIELDS}
        out.append(row)
    return out


def gate_stations(raw: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Return only the stations that carry a non-null gate-opening reading in at least one
    of watergate01..watergate06. This is the MEASURED gate-state subset that
    docs/knowledge/LESSONS_nodes_2026-09-27.md flags as currently INFERRED elsewhere in
    this repo -- see docs/knowledge/BMA_WATER_MAP_PROBE.md section "Gate opening height".
    """
    result = []
    for rec in raw:
        gate_values = {f: rec.get(f) for f in GATE_FIELDS if rec.get(f) is not None}
        if gate_values:
            result.append(
                {
                    "water_code": rec.get("water_code"),
                    "water_name": rec.get("water_name"),
                    "water_name_en": rec.get("water_name_en"),
                    "latitude": rec.get("latitude"),
                    "longitude": rec.get("longitude"),
                    "water_gate_count": rec.get("water_gate_count"),
                    "gates_m": gate_values,
                    "site_timestampTH": rec.get("site_timestampTH"),
                }
            )
    return result


def find_by_water_code(raw: Iterable[dict[str, Any]], water_code: str) -> dict[str, Any] | None:
    """Look up a single station record by its water_code (e.g. 'WL.PWT.04')."""
    for rec in raw:
        if rec.get("water_code") == water_code:
            return rec
    return None


def control_level_coverage(raw: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """
    Answer the founder's specific question: does this endpoint carry a per-canal
    'control'/'back-to-normal' level? Returns a small readout dict rather than a bare
    bool, so a caller can see counts, not just a yes/no. In the 2026-09-27 probe archive,
    water_control was present as a field on every record but null for all of them --
    OPEN, not resolved by this module; re-run against a fresh archive to re-check.
    """
    total = 0
    non_null = []
    for rec in raw:
        total += 1
        if rec.get("water_control") is not None:
            non_null.append(
                {
                    "water_code": rec.get("water_code"),
                    "water_name": rec.get("water_name"),
                    "water_control": rec.get("water_control"),
                }
            )
    return {
        "total_stations": total,
        "water_control_non_null_count": len(non_null),
        "water_control_non_null_stations": non_null,
        "tag": "MEASURED" if total else "OPEN",
    }


def _main(argv: list[str]) -> int:
    """
    Tiny CLI for manual inspection of an archived sample:
        python3 tools/harvest/bma_maplet_draft.py raw/live/bma_maplet/pagemap_googlemap.json
    Prints station count, gate-station count, and the control-level coverage readout.
    Makes no network calls.
    """
    if len(argv) != 2:
        print(f"usage: {argv[0]} <path-to-archived-pagemap-googlemap.json>", file=sys.stderr)
        return 2

    raw = load_raw(argv[1])
    stations = parse_pagemap_stations(raw)
    gates = gate_stations(raw)
    control = control_level_coverage(raw)

    print(f"stations parsed: {len(stations)}")
    print(f"stations with a measured gate reading: {len(gates)}")
    for g in gates[:10]:
        print(f"  {g['water_code']!s:12} {g['water_name']!s:50} gates_m={g['gates_m']}")
    print(
        "water_control coverage: "
        f"{control['water_control_non_null_count']}/{control['total_stations']} "
        f"non-null (tag={control['tag']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
