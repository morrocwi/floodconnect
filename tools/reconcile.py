#!/usr/bin/env python3
"""
Cross-source station reconciliation (build 4, 2026-09-27 -- founder rule, verbatim:
"ระวังข้อมูลขัดแย้งด้วย" / "watch out for conflicting data too", issued alongside the
bma_watermap collector because it overlaps thaiwater_canal_waterlevel on the same
'WL.xxx.NN' station-code scheme).

**Never merges or silently prefers one source.** Both `observations` rows for a station
stay exactly as collected -- this module only READS them and WRITES `contradictions`
rows (via `store.insert_contradiction`, itself append-only / never overwritten) when two
sources' LATEST readings for the same station disagree:
  - their timestamps are more than `DISAGREE_MINUTES` (60) apart, OR
  - their values differ by more than `DISAGREE_LEVEL_M` (0.05 m)
When they agree, no contradiction row is written, but this module's return value still
carries the "2 sources agree" fact per station (status "AGREE") so a caller can render it
as a confidence-raising note, per the founder's own instruction ("ถ้าตรงกันโชว์ด้วย เพิ่ม
ความมั่นใจ").

**Reconciled here**: `bma_watermap` vs `thaiwater_canal_waterlevel`, both `variable=
canal_water_level_m`, joined by the IDENTICAL `WL.xxx.NN` station_code (this repo's own
scheme, no cross-walk needed -- confirmed directly against a live pull, see
docs/knowledge/BMA_WATER_MAP_PROBE.md).

**NOT reconciled here (documented, not silently skipped)**: `hii_watergate` uses a
completely different station-code scheme (`gate:hii_watergate:<n>`) with no already-
verified cross-walk to `WL.xxx.NN` anywhere in this repo. Reconciling it would require a
new name/geometry cross-walk this module does not build (never fuzzy-matched, per this
repo's discipline) -- left OPEN for a future task.
"""
from __future__ import annotations

import datetime

import store

DISAGREE_MINUTES = 60.0
DISAGREE_LEVEL_M = 0.05

SOURCE_A = "bma_watermap"
SOURCE_B = "thaiwater_canal_waterlevel"
VARIABLE = "canal_water_level_m"

STATUS_AGREE = "AGREE"
STATUS_DISAGREE = "DISAGREE"
STATUS_ONE_SIDED = "ONE_SIDED"  # only one of the two sources has a reading for this station
STATUS_NO_DATA = "NO_DATA"  # neither source has a reading for this station


def _latest_reading(conn, source_id: str, station_code: str, variable: str = VARIABLE):
    row = conn.execute(
        "SELECT value, observed_at_utc FROM observations "
        "WHERE source_id = ? AND station_code = ? AND variable = ? "
        "ORDER BY observed_at_utc DESC LIMIT 1",
        (source_id, station_code, variable),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    value, observed_at = row
    return {"value": value, "observed_at": observed_at}


def _minutes_apart(iso_a: str, iso_b: str) -> float | None:
    try:
        a = datetime.datetime.fromisoformat(iso_a)
        b = datetime.datetime.fromisoformat(iso_b)
    except (TypeError, ValueError):
        return None
    return abs((a - b).total_seconds()) / 60.0


def reconcile_canal_water_level(conn, station_codes) -> dict:
    """Runs the bma_watermap vs thaiwater_canal_waterlevel comparison for every station
    code given (typically this repo's own tracked canal_by_code keys). `conn` must be a
    WRITABLE connection (store.connect(...), not a read-only mode=ro one) -- this
    function calls store.insert_contradiction() for every disagreement found.

    Returns {"stations": {code: {"status", "a", "b", "delta_m", "minutes_apart"}},
    "summary": {"agree": n, "disagree": n, "one_sided": n, "no_data": n}}. Never raises
    on a missing/malformed reading -- that station is simply reported NO_DATA/ONE_SIDED.
    """
    stations = {}
    n_agree = n_disagree = n_one_sided = n_no_data = 0
    for code in station_codes:
        a = _latest_reading(conn, SOURCE_A, code)
        b = _latest_reading(conn, SOURCE_B, code)
        if a is None and b is None:
            stations[code] = {"status": STATUS_NO_DATA, "a": None, "b": None,
                               "delta_m": None, "minutes_apart": None}
            n_no_data += 1
            continue
        if a is None or b is None:
            stations[code] = {"status": STATUS_ONE_SIDED, "a": a, "b": b,
                               "delta_m": None, "minutes_apart": None}
            n_one_sided += 1
            continue
        delta = abs(a["value"] - b["value"])
        minutes = _minutes_apart(a["observed_at"], b["observed_at"])
        disagree = minutes is None or minutes > DISAGREE_MINUTES or delta > DISAGREE_LEVEL_M
        if disagree:
            store.insert_contradiction(
                conn, observed_at_utc=a["observed_at"],
                topic=f"canal_water_level_m:{code}", source_a=SOURCE_A,
                value_a=a["value"], observed_a_utc=a["observed_at"], source_b=SOURCE_B,
                value_b=b["value"], observed_b_utc=b["observed_at"],
                note=(f"delta={delta:.3f}m, "
                      f"{('%.0f' % minutes) if minutes is not None else 'unknown'} min "
                      "apart -- never auto-resolved, both readings kept in observations"))
            stations[code] = {"status": STATUS_DISAGREE, "a": a, "b": b,
                               "delta_m": delta, "minutes_apart": minutes}
            n_disagree += 1
        else:
            stations[code] = {"status": STATUS_AGREE, "a": a, "b": b,
                               "delta_m": delta, "minutes_apart": minutes}
            n_agree += 1
    return {
        "stations": stations,
        "summary": {"agree": n_agree, "disagree": n_disagree,
                    "one_sided": n_one_sided, "no_data": n_no_data},
    }
