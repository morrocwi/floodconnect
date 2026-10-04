# Worked example — the Sammakorn incident, reproduced

## The incident

An external AI assistant tried a Sammakorn readout at 19:25 and reported:

> "receiving canal = UNKNOWN"

This was wrong. FloodConnect had fresh `WL.BMA.02` / `WL.SSB.*` readings at
that moment — the assistant simply had no channel into the data. This is the
failure `floodconnect_get_station` (MCP) / the local export file you build
yourself (`site/dist/api/v1/areas/sammakorn.json`, after running
`site/build_data.py` + `tools/api/export_api.py` on your own machine — there is
no hosted endpoint) exists to close.

## Snapshot 1 — station is fresh

Suppose `floodconnect_get_station("WL.SSB.08")` (or the equivalent
`canals[]` entry in `areas/sammakorn.json`) returns:

```json
{
  "found": true,
  "area_id": "sammakorn",
  "station": {
    "station_code": "WL.SSB.08",
    "level_m": 0.42,
    "trend": "rising",
    "staleness": {
      "observed_at": "2026-09-28T04:55:00+00:00",
      "fetched_at": "2026-09-28T05:00:00+00:00",
      "age_class": "fresh",
      "tag": "MEASURED"
    }
  }
}
```

**Correct answer:**

> ระดับน้ำคลองที่สถานี WL.SSB.08 อยู่ที่ 0.42 ม. (แนวโน้มขึ้น) — แหล่งข้อมูล:
> thaiwater_canal_waterlevel, อ่านค่าเมื่อ 2026-09-28T04:55:00+00:00
> (tag: MEASURED, fresh)

**NOT** "unknown" / "ไม่ทราบ" — the field's `age_class` is `fresh` and its
`tag` is `MEASURED`; nothing here justifies UNKNOWN.

## Snapshot 2 — same station, now aged past the freshness cutoff

Same station code, later query, same value but now old:

```json
{
  "found": true,
  "area_id": "sammakorn",
  "station": {
    "station_code": "WL.SSB.08",
    "level_m": 0.42,
    "staleness": {
      "observed_at": "2026-09-26T20:00:00+00:00",
      "fetched_at": "2026-09-28T05:00:00+00:00",
      "age_class": "stale",
      "tag": "MEASURED"
    }
  }
}
```

**Correct answer:**

> ค่าล่าสุดที่มีคือ 0.42 ม. แต่อ่านเมื่อ 2026-09-26T20:00:00+00:00 — เก่ากว่า
> เกณฑ์ความสดที่ระบบนี้ใช้ ถือเป็นข้อมูลไม่ทราบสถานะปัจจุบัน จนกว่าจะมีค่าที่สดกว่านี้

This demonstrates the freshness rule is **reused** (the `age_class` the API
already computed, from `site/build_data.py`'s own cutoff), not something this
skill invents on its own — the skill never applies its own separate "is this
old" judgment call on top of the field.

## Why this matters for the acceptance test

Any external AI following this skill against a live `WL.SSB.08`/`WL.BMA.02`
reading that is genuinely fresh must answer with the value + source +
observed_at + tag — never "UNKNOWN" — and must downgrade to "stale/unknown
for current decision-making" only when `age_class` says so, never on its own
guess about how old is "too old."
