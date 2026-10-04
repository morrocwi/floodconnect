"""Urban flood event ground-truth ledger.

Read-only derivation from `thaiwater_flood_road` (BMA flood-road telemetry, see
`sources/registry.yaml`) plus an append-only YAML ledger of REAL events
(`sources/urban_flood_event_ledger.yaml`).

Epistemic discipline (see AGENTS.md §2): every value this module *derives* from
`data/observations.sqlite` is MEASURED. The clustering rule that turns those
values into a binary `urban_flood_observed` call is a judgment call — always
tagged INSTINCT in the ledger, never silently promoted to MEASURED/VERIFIED.
No row in the YAML ledger is ever rewritten or deleted; `append_event()` only
adds new rows and refuses to touch an existing `event_id`.

Toledo-first note: nothing here is a physical equation. This is arithmetic
counting + interval clustering over already-observed road-flood-height
readings, not a PROP-FLOOD-xx candidate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "observations.sqlite"
DEFAULT_LEDGER = REPO_ROOT / "sources" / "urban_flood_event_ledger.yaml"

FLOOD_ROAD_SOURCE_ID = "thaiwater_flood_road"

VALID_TAGS = {"VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN"}
VALID_EVIDENCE_CLASSES = {
    "road_telemetry",
    "canal_overbank",
    "evacuation_shelter",
    "community_reports_consistent",
    "media",
    "satellite",
}
VALID_WARNING_SCOPES = {"regional_class", "node_specific"}


@dataclass(frozen=True)
class Rule:
    """One candidate decision rule for 'urban flooding occurred' from road telemetry.

    tag is always INSTINCT: the rule itself is a calibration choice, not a
    measured fact, however MEASURED the inputs feeding it are.
    """

    threshold_cm: float = 10.0
    min_roads: int = 3
    window_hours: float = 6.0
    name: str = "road_telemetry_district_cluster_v1"
    tag: str = "INSTINCT"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "threshold_cm": self.threshold_cm,
            "min_roads": self.min_roads,
            "window_hours": self.window_hours,
            "tag": self.tag,
        }


CHOSEN_RULE = Rule()

# Grid used for the "alternative rule outcomes" calibration table so the rule
# can be re-picked later without re-deriving from raw SQL by hand.
ALT_THRESHOLDS_CM = (10.0, 20.0, 30.0)
ALT_MIN_ROADS = (2, 3, 5)
ALT_WINDOW_HOURS = 6.0


def _district_code(station_code: str) -> str:
    """BMA flood-road station codes are `FL.<DISTRICT>.<NN>` — the middle
    segment is a district/zone code. Falls back to the raw code if the
    pattern does not match (never fabricate a district)."""
    parts = station_code.split(".")
    if len(parts) == 3 and parts[0] == "FL":
        return parts[1]
    return station_code


def _parse_ts(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def fetch_flood_road_rows(conn: sqlite3.Connection) -> list[tuple[str, str, float, str]]:
    """Read-only fetch of every thaiwater_flood_road row with a non-null value.

    Small table (order of thousands of rows) — loaded fully into memory is
    fine on a ~4GB box; no need for chunking.
    """
    cur = conn.cursor()
    cur.execute(
        """
        select station_code, station_name, value, observed_at_utc
        from observations
        where source_id = ? and value is not null
        order by observed_at_utc
        """,
        (FLOOD_ROAD_SOURCE_ID,),
    )
    return cur.fetchall()


def get_first_fetch_utc(conn: sqlite3.Connection, source_id: str) -> dt.datetime | None:
    """MIN(fetched_at_utc) for a source — the timestamp this collector first
    ever successfully pulled that source. Any observation whose
    observed_at_utc is EARLIER than this collector-first-fetch moment is
    left-censored: the row proves "already true no later than observed_at_utc",
    never a true onset (the source API may hold a value that was already
    non-zero the very first time we asked it). Returns None if the source has
    no rows at all (never fabricate a first-fetch time)."""
    cur = conn.cursor()
    cur.execute(
        "select min(fetched_at_utc) from observations where source_id = ?",
        (source_id,),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return None
    return _parse_ts(row[0])


def _finalize_cluster(
    district: str,
    cluster: list[tuple[dt.datetime, str, float]],
    min_roads: int,
    names: dict[str, str],
    first_fetch_utc: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    roads = sorted({code for _, code, _ in cluster})
    if len(roads) < min_roads:
        return []
    onset = min(t for t, _, _ in cluster)
    offset = max(t for t, _, _ in cluster)
    event: dict[str, Any] = {
        "district": district,
        "onset": onset,
        "offset": offset,
        "roads": roads,
        "road_names": {r: names.get(r, "") for r in roads},
        "n_roads": len(roads),
    }
    if first_fetch_utc is not None:
        event["first_fetch_utc"] = first_fetch_utc
        event["onset_censoring"] = (
            "left_censored" if onset < first_fetch_utc else "observed"
        )
    return [event]


def cluster_events(
    rows: list[tuple[str, str, float, str]],
    threshold_cm: float,
    min_roads: int,
    window_hours: float,
    first_fetch_utc: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """Chain-cluster qualifying road readings (value >= threshold_cm) per
    district: consecutive qualifying readings less than `window_hours` apart
    (in time, across any road in the district) join the same cluster. A
    cluster becomes a candidate event only if it touches >= min_roads
    *distinct* stations.

    When `first_fetch_utc` is given (the collector's own MIN(fetched_at_utc)
    for this source), each returned event also carries `first_fetch_utc` and
    `onset_censoring`: "left_censored" when the cluster's onset predates the
    collector's first-ever fetch of this source (the DB only proves "already
    flooded no later than onset", never a true start time), else "observed".

    Returns candidates sorted by onset time; each dict has:
      district, onset (datetime), offset (datetime), roads (sorted station
      codes), road_names (dict code->name), n_roads[, first_fetch_utc,
      onset_censoring]
    """
    by_district: dict[str, list[tuple[dt.datetime, str, float]]] = {}
    names: dict[str, str] = {}
    for code, name, value, ts in rows:
        names[code] = name
        if value is None or value < threshold_cm:
            continue
        district = _district_code(code)
        by_district.setdefault(district, []).append((_parse_ts(ts), code, value))

    events: list[dict[str, Any]] = []
    window = dt.timedelta(hours=window_hours)
    for district, readings in by_district.items():
        readings.sort(key=lambda r: r[0])
        cluster: list[tuple[dt.datetime, str, float]] = [readings[0]]
        for item in readings[1:]:
            if item[0] - cluster[-1][0] <= window:
                cluster.append(item)
                continue
            events.extend(
                _finalize_cluster(district, cluster, min_roads, names, first_fetch_utc)
            )
            cluster = [item]
        events.extend(
            _finalize_cluster(district, cluster, min_roads, names, first_fetch_utc)
        )

    events.sort(key=lambda e: e["onset"])
    return events


def derive_events_from_flood_road(
    conn: sqlite3.Connection, rule: Rule = CHOSEN_RULE
) -> list[dict[str, Any]]:
    """Scan the whole thaiwater_flood_road history and list candidate
    urban-flood district-events under `rule`. Read-only — never writes.

    Each returned event carries `first_fetch_utc` (this collector's own
    MIN(fetched_at_utc) for thaiwater_flood_road) and `onset_censoring`
    ("left_censored" | "observed"), computed automatically — see
    `cluster_events()`."""
    rows = fetch_flood_road_rows(conn)
    first_fetch_utc = get_first_fetch_utc(conn, FLOOD_ROAD_SOURCE_ID)
    return cluster_events(
        rows, rule.threshold_cm, rule.min_roads, rule.window_hours, first_fetch_utc
    )


def rule_outcome_matrix(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Alternative-rule calibration table: total candidate-event count per
    (threshold_cm, min_roads) combination at the fixed ALT_WINDOW_HOURS, plus
    a per-year breakdown, so the chosen rule can be swapped later without
    re-running SQL by hand."""
    rows = fetch_flood_road_rows(conn)
    out: list[dict[str, Any]] = []
    for threshold_cm in ALT_THRESHOLDS_CM:
        for min_roads in ALT_MIN_ROADS:
            events = cluster_events(rows, threshold_cm, min_roads, ALT_WINDOW_HOURS)
            by_year: dict[int, int] = {}
            for e in events:
                by_year[e["onset"].year] = by_year.get(e["onset"].year, 0) + 1
            out.append(
                {
                    "threshold_cm": threshold_cm,
                    "min_roads": min_roads,
                    "window_hours": ALT_WINDOW_HOURS,
                    "total_events": len(events),
                    "by_year": dict(sorted(by_year.items())),
                    "chosen": (
                        threshold_cm == CHOSEN_RULE.threshold_cm
                        and min_roads == CHOSEN_RULE.min_roads
                        and ALT_WINDOW_HOURS == CHOSEN_RULE.window_hours
                    ),
                }
            )
    return out


# --------------------------------------------------------------------------
# Ledger I/O — append-only
# --------------------------------------------------------------------------


def _empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ledger_kind": "urban_flood_event_ledger",
        "append_only": True,
        "decision_rule": {"chosen": CHOSEN_RULE.as_dict()},
        "events": [],
    }


def load_ledger(path: Path = DEFAULT_LEDGER) -> dict[str, Any]:
    if not path.exists():
        return _empty_ledger()
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("events", [])
    return data


def validate_event(event: dict[str, Any]) -> None:
    """Raises ValueError on a malformed event row. Checked before every
    append — never silently accepted."""
    required = ["event_id", "unit_scope", "urban_flood_observed", "tag"]
    missing = [k for k in required if k not in event]
    if missing:
        raise ValueError(f"event missing required field(s): {missing}")

    if event["unit_scope"] not in {"city", "district", "node"}:
        raise ValueError(f"unit_scope must be city|district|node, got {event['unit_scope']!r}")

    if event["tag"] not in VALID_TAGS:
        raise ValueError(f"tag must be one of {sorted(VALID_TAGS)}, got {event['tag']!r}")

    ufo = event["urban_flood_observed"]
    if ufo not in (True, False, "UNCERTAIN"):
        raise ValueError(
            f"urban_flood_observed must be true/false/UNCERTAIN, got {ufo!r}"
        )

    odd = event.get("official_disaster_declared", "OPEN")
    if odd not in (True, False, "OPEN"):
        raise ValueError(
            f"official_disaster_declared must be true/false/OPEN, got {odd!r}"
        )

    for ev in event.get("evidence", []):
        if "class" not in ev:
            raise ValueError(f"evidence row missing 'class': {ev}")
        if ev["class"] not in VALID_EVIDENCE_CLASSES:
            raise ValueError(
                f"evidence class must be one of {sorted(VALID_EVIDENCE_CLASSES)}, "
                f"got {ev['class']!r}"
            )
        if "tag" not in ev or ev["tag"] not in VALID_TAGS:
            raise ValueError(f"evidence row must carry a valid tag: {ev}")

    for w in event.get("warnings", []):
        if "scope" not in w or w["scope"] not in VALID_WARNING_SCOPES:
            raise ValueError(
                f"warning row must carry scope in {sorted(VALID_WARNING_SCOPES)}: {w}"
            )
        if "tag" not in w or w["tag"] not in VALID_TAGS:
            raise ValueError(f"warning row must carry a valid tag: {w}")


def append_event(event: dict[str, Any], path: Path = DEFAULT_LEDGER) -> None:
    """Append one event row to the ledger. Never rewrites or removes an
    existing row — refuses (ValueError) if event_id already exists."""
    validate_event(event)
    data = load_ledger(path)
    existing_ids = {e.get("event_id") for e in data.get("events", [])}
    if event["event_id"] in existing_ids:
        raise ValueError(
            f"event_id {event['event_id']!r} already exists — ledger is append-only, "
            "never overwrite an existing row"
        )
    data.setdefault("events", []).append(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _fmt_event_line(e: dict[str, Any]) -> str:
    return (
        f"{e['district']:>4}  onset={e['onset'].isoformat()}  "
        f"offset={e['offset'].isoformat()}  n_roads={e['n_roads']}  "
        f"roads={','.join(e['roads'][:5])}{'...' if e['n_roads'] > 5 else ''}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="derive candidate urban-flood district-events under the chosen rule",
    )
    parser.add_argument(
        "--event",
        metavar="YYYY-MM-DD",
        help="show candidate events whose onset date matches this UTC date",
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="print the alternative-rule calibration matrix",
    )
    args = parser.parse_args(argv)

    if not (args.list_candidates or args.event or args.matrix):
        parser.print_help()
        return 1

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        if args.matrix:
            for row in rule_outcome_matrix(conn):
                marker = " <-- chosen" if row["chosen"] else ""
                print(
                    f"threshold={row['threshold_cm']}cm min_roads={row['min_roads']} "
                    f"window={row['window_hours']}h -> total={row['total_events']} "
                    f"by_year={row['by_year']}{marker}"
                )
        if args.list_candidates:
            events = derive_events_from_flood_road(conn)
            print(f"# {len(events)} candidate events under rule {CHOSEN_RULE.as_dict()}")
            for e in events:
                print(_fmt_event_line(e))
        if args.event:
            target = dt.date.fromisoformat(args.event)
            events = derive_events_from_flood_road(conn)
            matches = [e for e in events if e["onset"].date() == target]
            print(f"# {len(matches)} candidate event(s) with onset date {target}")
            for e in matches:
                print(_fmt_event_line(e))
                for code in e["roads"]:
                    print(f"    {code}  {e['road_names'][code]}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
