#!/usr/bin/env python3
"""
Append-only SQLite store for the Sammakorn live flood-context data system.

`data/observations.sqlite` is gitignored (see .gitignore's `raw/` + this file's own
directory convention -- the DB itself is a local cache/ledger, not a deposited artifact).

Three tables, per the design fixed by the orchestrator:

- `observations` -- one row per (source, station, variable, timestamp) reading. Append-
  only: a unique index on (source_id, station_code, variable, observed_at_utc) means a
  re-collect of the same instant is a no-op (INSERT OR IGNORE), never an overwrite of an
  already-recorded reading -- this pipeline does not rewrite history.
- `documents` -- raw/semi-structured text this pipeline chose NOT to force into fields
  (prose sections of the DDS daily PDF, HTML sections that don't fit a clean row shape).
  Never silently dropped -- if it wasn't parsed into a field, it lives here verbatim.
- `contradictions` -- explicit rows for two sources disagreeing about the same topic at
  (about) the same time. Never auto-resolved; `readout.py` lists these, never picks a
  winner.

No flood-risk score or formula is computed or stored anywhere in this module (see this
workspace's equation-discipline rule) -- every stored value is a relayed/measured
reading, tagged with its own trust_tier, nothing derived.
"""
import csv
import datetime
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_DB_PATH = HERE / "data" / "observations.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    station_code TEXT,
    station_name TEXT,
    lat REAL,
    lon REAL,
    variable TEXT NOT NULL,
    value REAL,
    unit TEXT,
    observed_at_utc TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL,
    warning REAL,
    critical REAL,
    bank REAL,
    status TEXT,
    trust_tier TEXT NOT NULL,
    provenance_json TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL,
    path TEXT,
    sha256 TEXT,
    section TEXT,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS method_evaluation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT NOT NULL,
    date TEXT NOT NULL,
    metric TEXT NOT NULL,
    value TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at_utc TEXT NOT NULL,
    topic TEXT NOT NULL,
    source_a TEXT NOT NULL,
    value_a TEXT,
    observed_a_utc TEXT,
    source_b TEXT NOT NULL,
    value_b TEXT,
    observed_b_utc TEXT,
    note TEXT
);
"""

# The identity indexes are created/repaired explicitly in `connect()` rather than inline
# in SCHEMA above, so an already-existing sqlite file created before this fix (which used
# a plain `station_code` unique key) gets migrated in place instead of silently keeping a
# stale index. `COALESCE(station_code, station_name, '')` closes a real dedupe hole: many
# rows (e.g. dds_daily_pdf rain/canal rows) carry `station_code=None` by design, and SQLite
# treats every NULL as distinct in a UNIQUE index, so two NULLs never collide -- a re-collect
# of the same instant silently inserted duplicate rows for exactly those sources.
_OBSERVATIONS_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_observations_identity_v2
    ON observations(source_id, COALESCE(station_code, station_name, ''), variable,
                     observed_at_utc)
"""
# Contradiction rows are re-derived every `readout.py` run (it re-inserts the same
# comparison every time it runs), so without an identity key each run doubled the table.
# Identity = the same topic comparing the same two dated observations from the same two
# sources.
_CONTRADICTIONS_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_contradictions_identity
    ON contradictions(topic, source_a, COALESCE(observed_a_utc, ''),
                       source_b, COALESCE(observed_b_utc, ''))
"""

# One row per (area, date, metric) -- re-running `social_listening.py --evaluate` updates
# the same row in place (ON CONFLICT DO UPDATE below) rather than piling up duplicate
# snapshots every run.
_METHOD_EVALUATION_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_method_evaluation_identity
    ON method_evaluation(area, date, metric)
"""


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # `CREATE TABLE IF NOT EXISTS` above does not add columns to an already-existing table
    # -- an sqlite file created before this fix has a `contradictions` table with no
    # observed_a_utc/observed_b_utc columns at all, so creating the new identity index
    # against them would fail with "no such column". Add them in place if missing.
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(contradictions)").fetchall()}
    for col in ("observed_a_utc", "observed_b_utc"):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE contradictions ADD COLUMN {col} TEXT")
    # Drop the old (pre-fix) plain station_code unique index if an existing DB file still
    # has it -- it would otherwise coexist with the new one and still let NULL-station-code
    # duplicates through undetected via the old index's own NULL-is-distinct behaviour.
    conn.execute("DROP INDEX IF EXISTS ux_observations_identity")
    conn.execute(_OBSERVATIONS_INDEX_SQL)
    conn.execute(_METHOD_EVALUATION_INDEX_SQL)
    try:
        conn.execute(_CONTRADICTIONS_INDEX_SQL)
    except sqlite3.IntegrityError:
        # An existing DB file predating this fix can already hold duplicate contradiction
        # rows (the exact bug this index closes -- every readout.py run used to re-insert
        # the same comparison). Keep the earliest row per identity group, drop the rest,
        # then retry -- a one-time cleanup, not something that runs again once the index
        # exists (INSERT OR IGNORE keeps it from recurring).
        conn.execute("""
            DELETE FROM contradictions WHERE id NOT IN (
                SELECT MIN(id) FROM contradictions
                GROUP BY topic, source_a, COALESCE(observed_a_utc, ''),
                         source_b, COALESCE(observed_b_utc, '')
            )
        """)
        conn.execute(_CONTRADICTIONS_INDEX_SQL)
    conn.commit()
    return conn


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def insert_observation(conn: sqlite3.Connection, *, source_id, variable, observed_at_utc,
                        fetched_at_utc, trust_tier, station_code=None, station_name=None,
                        lat=None, lon=None, value=None, unit=None, warning=None,
                        critical=None, bank=None, status=None, provenance=None) -> bool:
    """
    INSERT OR IGNORE on the (source_id, station_code, variable, observed_at_utc) unique
    index -- append-only, never overwrites an already-recorded reading. Returns True if a
    new row was actually inserted, False if it was already present (a no-op re-collect).
    """
    cur = conn.execute(
        """INSERT OR IGNORE INTO observations
           (source_id, station_code, station_name, lat, lon, variable, value, unit,
            observed_at_utc, fetched_at_utc, warning, critical, bank, status,
            trust_tier, provenance_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_id, station_code, station_name, lat, lon, variable, value, unit,
         observed_at_utc, fetched_at_utc, warning, critical, bank, status, trust_tier,
         json.dumps(provenance, ensure_ascii=False) if provenance is not None else None),
    )
    conn.commit()
    return cur.rowcount > 0


def insert_document(conn: sqlite3.Connection, *, source_id, fetched_at_utc, text,
                     path=None, sha256=None, section=None) -> int:
    cur = conn.execute(
        """INSERT INTO documents (source_id, fetched_at_utc, path, sha256, section, text)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (source_id, fetched_at_utc, path, sha256, section, text),
    )
    conn.commit()
    return cur.lastrowid


def insert_contradiction(conn: sqlite3.Connection, *, observed_at_utc, topic, source_a,
                          value_a, source_b, value_b, note=None, observed_a_utc=None,
                          observed_b_utc=None) -> int:
    """Never resolves the disagreement -- both values are recorded side by side, for a
    human/readout to weigh, per this workspace's "never silently resolved" rule.

    INSERT OR IGNORE on (topic, source_a, observed_a_utc, source_b, observed_b_utc) --
    the same underlying comparison re-derived by a later `readout.py` run is a no-op, not
    a duplicate row. `observed_a_utc`/`observed_b_utc` are optional for backward
    compatibility with older call sites that only ever had one `observed_at_utc` (the
    run's own generation time); passing them lets two runs of the same comparison collide
    on identity instead of piling up.
    """
    cur = conn.execute(
        """INSERT OR IGNORE INTO contradictions
           (observed_at_utc, topic, source_a, value_a, observed_a_utc, source_b, value_b,
            observed_b_utc, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (observed_at_utc, topic, source_a, str(value_a), observed_a_utc, source_b,
         str(value_b), observed_b_utc, note),
    )
    conn.commit()
    return cur.lastrowid


def insert_method_evaluation(conn: sqlite3.Connection, *, area, date, metric, value,
                              note=None) -> None:
    """Upserts one (area, date, metric) row -- a re-run of `social_listening.py
    --evaluate` updates the same snapshot instead of accumulating duplicates, since this
    table holds a computed effectiveness reading, not a raw append-only observation."""
    conn.execute(
        """INSERT INTO method_evaluation (area, date, metric, value, note)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(area, date, metric) DO UPDATE SET value=excluded.value,
               note=excluded.note""",
        (area, date, metric, None if value is None else str(value), note),
    )
    conn.commit()


def query_method_evaluation(conn: sqlite3.Connection, *, area=None, date=None) -> list:
    sql = "SELECT * FROM method_evaluation WHERE 1=1"
    args = []
    if area:
        sql += " AND area = ?"
        args.append(area)
    if date:
        sql += " AND date = ?"
        args.append(date)
    sql += " ORDER BY area, date, metric"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def query_observations(conn: sqlite3.Connection, *, source_id=None, station_code=None,
                        variable=None, since_utc=None, near=None, limit=1000) -> list:
    """
    `near` optionally = (lat, lon, radius_km) for a haversine filter applied in Python
    (SQLite has no built-in haversine; the observations table is small enough that this
    is a plain full scan + filter, not a spatial index -- fine at this data volume).
    """
    sql = "SELECT * FROM observations WHERE 1=1"
    args = []
    if source_id:
        sql += " AND source_id = ?"
        args.append(source_id)
    if station_code:
        sql += " AND station_code = ?"
        args.append(station_code)
    if variable:
        sql += " AND variable = ?"
        args.append(variable)
    if since_utc:
        sql += " AND observed_at_utc >= ?"
        args.append(since_utc)
    sql += " ORDER BY observed_at_utc DESC LIMIT ?"
    args.append(limit)
    rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    if near:
        from live_water_level import haversine_km
        lat0, lon0, radius_km = near
        rows = [r for r in rows if r.get("lat") is not None and r.get("lon") is not None
                and haversine_km(lat0, lon0, r["lat"], r["lon"]) <= radius_km]
    return rows


def query_documents(conn: sqlite3.Connection, *, source_id=None, section=None,
                     since_utc=None, limit=200) -> list:
    sql = "SELECT * FROM documents WHERE 1=1"
    args = []
    if source_id:
        sql += " AND source_id = ?"
        args.append(source_id)
    if section:
        sql += " AND section = ?"
        args.append(section)
    if since_utc:
        sql += " AND fetched_at_utc >= ?"
        args.append(since_utc)
    sql += " ORDER BY fetched_at_utc DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def query_contradictions(conn: sqlite3.Connection, *, since_utc=None, limit=200) -> list:
    sql = "SELECT * FROM contradictions WHERE 1=1"
    args = []
    if since_utc:
        sql += " AND observed_at_utc >= ?"
        args.append(since_utc)
    sql += " ORDER BY observed_at_utc DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def export_csv_last_24h(conn: sqlite3.Connection, out_path: Path) -> int:
    """Writes every observation with fetched_at_utc within the last 24h to `out_path`.
    Returns the row count written."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(hours=24)).isoformat()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM observations WHERE fetched_at_utc >= ? ORDER BY observed_at_utc",
        (cutoff,)).fetchall()]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "source_id", "station_code", "station_name", "lat", "lon",
                  "variable", "value", "unit", "observed_at_utc", "fetched_at_utc",
                  "warning", "critical", "bank", "status", "trust_tier",
                  "provenance_json"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB_PATH))
    ap.add_argument("--export-csv", metavar="OUT_CSV",
                     help="Export the last 24h of observations to a CSV file.")
    args = ap.parse_args()
    conn = connect(Path(args.db))
    if args.export_csv:
        n = export_csv_last_24h(conn, Path(args.export_csv))
        print(f"wrote {n} observation(s) from the last 24h to {args.export_csv}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
