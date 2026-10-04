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

-- Append-only per-run readout log (project decision 2026-09-27): site/build_data.py's
-- per-build data.json is overwritten every run, which meant the burden ledger, canal-
-- graph edge directions, pump counts, hero status word, rain/tide/forecast summary, BMA
-- briefing fields and water-balance numbers were all lost after each build -- nothing to
-- read a water-politics/overall-picture lens through later. This table gets ONE row per
-- (run_at_utc, area, kind, key) -- re-running a build for the SAME data timestamp is a
-- no-op (INSERT OR IGNORE on the identity index below), never a duplicate or an
-- overwrite of an earlier run's row. `kind` in
-- {'burden','edge','pump','status','rain','tide','balance','briefing'}; `key` is the
-- structure id (e.g. ssb10), edge id, or a per-area label (e.g. sammakorn_pumps).
CREATE TABLE IF NOT EXISTS readout_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at_utc TEXT NOT NULL,
    area TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    state TEXT,
    burdened_side TEXT,
    value_a REAL,
    value_b REAL,
    diff_m REAL,
    persistence INTEGER,
    extra_json TEXT
);

-- Human-experience layer (founder ask 2026-09-27: "สกัดประสบการณ์มนุษย์เข้าไปในระบบต่างๆ ทั้งด้าน
-- กรอบเลนส์การเมือง ปรัชญา เชิงโครงสร้าง ระบบ จริยธรรม") -- one row per anonymised, paraphrased
-- account (social post/comment/interview/paste), never a verified fact. `id` is the card's own
-- front-matter id (e.g. exp_2026-09-26_donmueang_mobility) and is the primary key -- a card
-- edited and re-`add`ed replaces its own row (see insert_experience), it never piles up
-- duplicates. `tag` is expected to always be the literal string 'RELAYED-EXPERIENCE' (enforced
-- by the card schema in docs/knowledge/experience/README.md, not by a DB constraint here, so an
-- old/foreign row shape does not hard-fail this table). `*_json` columns hold list/dict fields
-- serialised with json.dumps; `path` is the source card file's path, for traceability back to
-- the full body text (the DB row itself only holds the front-matter fields).
CREATE TABLE IF NOT EXISTS experience_log (
    id TEXT PRIMARY KEY,
    date_event TEXT,
    date_collected TEXT,
    role TEXT,
    place TEXT,
    node_ids_json TEXT,
    tag TEXT,
    measurables_json TEXT,
    politics TEXT,
    philosophy TEXT,
    structure TEXT,
    system TEXT,
    ethics TEXT,
    dag_gaps_json TEXT,
    ews_element TEXT,
    sprc TEXT,
    proposed_indicators_json TEXT,
    future_signal TEXT,
    path TEXT
);
"""

_READOUT_LOG_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_readout_log_identity
    ON readout_log(run_at_utc, area, kind, "key")
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
    conn.execute(_READOUT_LOG_INDEX_SQL)
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


def insert_readout_log(conn: sqlite3.Connection, *, run_at_utc, area, kind, key,
                        state=None, burdened_side=None, value_a=None, value_b=None,
                        diff_m=None, persistence=None, extra=None) -> bool:
    """INSERT OR IGNORE on (run_at_utc, area, kind, key) -- append-only, same posture as
    `insert_observation`. Returns True if a new row was inserted, False if this exact
    (run, area, kind, key) was already logged (re-running a build for the same data
    timestamp is a no-op, never a duplicate). `extra` is any JSON-serialisable dict,
    stored as `extra_json` for fields that don't have their own column."""
    extra_json = json.dumps(extra, ensure_ascii=False) if extra is not None else None
    cur = conn.execute(
        """INSERT OR IGNORE INTO readout_log
               (run_at_utc, area, kind, "key", state, burdened_side, value_a, value_b,
                diff_m, persistence, extra_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_at_utc, area, kind, key, state, burdened_side, value_a, value_b, diff_m,
         persistence, extra_json),
    )
    conn.commit()
    return cur.rowcount > 0


def query_readout_log(conn: sqlite3.Connection, *, area=None, kind=None, key=None,
                       since_utc=None, limit=5000) -> list:
    sql = 'SELECT * FROM readout_log WHERE 1=1'
    args = []
    if area:
        sql += " AND area = ?"
        args.append(area)
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    if key:
        sql += ' AND "key" = ?'
        args.append(key)
    if since_utc:
        sql += " AND run_at_utc >= ?"
        args.append(since_utc)
    sql += " ORDER BY run_at_utc, area, kind, \"key\" LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


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


# --- Assets registry (append-only addition) ---------------------------------------
#
# Physical flood-management asset registry (gauges, pump stations, gates, tunnels,
# dams, culverts, ponds, control centres) with an official-source-provable coordinate
# wherever one exists. Kept in its OWN schema block/functions, never touching the
# tables/functions above, per this check's append-only constraint.
#
# `assets` -- one row per asset_id (our stable id "class:source:code"), upserted in
# place (INSERT ... ON CONFLICT DO UPDATE) -- never deleted, never overwritten to a
# worse tag; `last_verified` moves forward each successful (re-)harvest.
# `assets_log` -- append-only per-verification history (one row per asset_id +
# verified_at_utc), so an asset's coordinate/tag history over time is never lost even
# though the `assets` row itself is a single current-state upsert.

ASSETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    class TEXT NOT NULL,
    name_th TEXT,
    source_code TEXT,
    lat REAL,
    lon REAL,
    coord_source TEXT,
    coord_source_type TEXT,
    owner TEXT,
    owner_source TEXT,
    pumps_total INTEGER,
    capacity_m3s REAL,
    capacity_m3s_suspect_count REAL,
    warning_level REAL,
    critical_level REAL,
    bank REAL,
    first_seen TEXT NOT NULL,
    last_verified TEXT NOT NULL,
    tag TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS assets_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    verified_at_utc TEXT NOT NULL,
    lat REAL,
    lon REAL,
    tag TEXT,
    coord_source TEXT,
    note TEXT
);
"""

_ASSETS_LOG_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_log_identity
    ON assets_log(asset_id, verified_at_utc)
"""


def ensure_assets_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: creates the `assets`/`assets_log` tables (and their identity index)
    if they don't already exist. Safe to call on every run; never touches the tables
    defined in SCHEMA above.

    `CREATE TABLE IF NOT EXISTS` does not add a column to an already-existing table --
    an `assets` table created before `capacity_m3s_suspect_count` existed (TODO #51,
    2026-09-27: `capacity_m3s` was found to hold a raw PUMP COUNT rather than m3/s for
    91 stations, per the bma_plan2569 plan cross-check) needs that column added in
    place. Never touches or resets `capacity_m3s`/`capacity_m3s_suspect_count` values
    already on record -- upsert_asset()'s own UPDATE list still does not mention
    `capacity_m3s_suspect_count`, so a future harvest re-run can never silently wipe a
    correction made here."""
    conn.executescript(ASSETS_SCHEMA)
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(assets)").fetchall()}
    if "capacity_m3s_suspect_count" not in existing_cols:
        conn.execute("ALTER TABLE assets ADD COLUMN capacity_m3s_suspect_count REAL")
    conn.execute(_ASSETS_LOG_INDEX_SQL)
    conn.commit()


def upsert_asset(conn: sqlite3.Connection, *, asset_id, klass, tag, name_th=None,
                  source_code=None, lat=None, lon=None, coord_source=None,
                  coord_source_type=None, owner=None, owner_source=None,
                  pumps_total=None, capacity_m3s=None, warning_level=None,
                  critical_level=None, bank=None, notes=None,
                  verified_at_utc=None) -> bool:
    """Insert a new asset row, or update the existing one in place by `asset_id` --
    never deletes a row. `first_seen` is preserved across updates (set once, on first
    insert). Also appends one row to `assets_log` for this verification instant
    (INSERT OR IGNORE on (asset_id, verified_at_utc), so re-running a harvest within
    the same instant/tick is a no-op there, not a duplicate).

    Returns True if this asset_id is new (first time seen), False if it already
    existed and this call just refreshed it.
    """
    verified_at_utc = verified_at_utc or _utcnow()
    existing = conn.execute(
        "SELECT first_seen FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    first_seen = existing["first_seen"] if existing else verified_at_utc
    conn.execute(
        """INSERT INTO assets
           (asset_id, class, name_th, source_code, lat, lon, coord_source,
            coord_source_type, owner, owner_source, pumps_total, capacity_m3s,
            warning_level, critical_level, bank, first_seen, last_verified, tag, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(asset_id) DO UPDATE SET
               class=excluded.class, name_th=excluded.name_th,
               source_code=excluded.source_code, lat=excluded.lat, lon=excluded.lon,
               coord_source=excluded.coord_source,
               coord_source_type=excluded.coord_source_type, owner=excluded.owner,
               owner_source=excluded.owner_source, pumps_total=excluded.pumps_total,
               capacity_m3s=excluded.capacity_m3s, warning_level=excluded.warning_level,
               critical_level=excluded.critical_level, bank=excluded.bank,
               last_verified=excluded.last_verified, tag=excluded.tag,
               notes=excluded.notes""",
        (asset_id, klass, name_th, source_code, lat, lon, coord_source,
         coord_source_type, owner, owner_source, pumps_total, capacity_m3s,
         warning_level, critical_level, bank, first_seen, verified_at_utc, tag, notes),
    )
    conn.execute(
        """INSERT OR IGNORE INTO assets_log
           (asset_id, verified_at_utc, lat, lon, tag, coord_source, note)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (asset_id, verified_at_utc, lat, lon, tag, coord_source, notes),
    )
    conn.commit()
    return existing is None


def query_assets(conn: sqlite3.Connection, *, klass=None, tag=None, owner=None) -> list:
    sql = "SELECT * FROM assets WHERE 1=1"
    args = []
    if klass is not None:
        sql += " AND class = ?"
        args.append(klass)
    if tag is not None:
        sql += " AND tag = ?"
        args.append(tag)
    if owner is not None:
        sql += " AND owner = ?"
        args.append(owner)
    sql += " ORDER BY class, asset_id"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def query_assets_log(conn: sqlite3.Connection, *, asset_id=None, limit=200) -> list:
    sql = "SELECT * FROM assets_log WHERE 1=1"
    args = []
    if asset_id is not None:
        sql += " AND asset_id = ?"
        args.append(asset_id)
    sql += " ORDER BY verified_at_utc DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


# ---------------------------------------------------------------------------------------
# Human-experience layer (docs/knowledge/experience/) -- see the CREATE TABLE comment
# above for the "why" of this table. `insert_experience`/`query_experience` are the only
# writers/readers of `experience_log`; `experience_log.py` (root CLI) is the only caller.
# ---------------------------------------------------------------------------------------

def insert_experience(conn: sqlite3.Connection, *, id, date_event=None, date_collected=None,
                       role=None, place=None, node_ids=None, tag="RELAYED-EXPERIENCE",
                       measurables=None, politics=None, philosophy=None, structure=None,
                       system=None, ethics=None, dag_gaps=None, ews_element=None, sprc=None,
                       proposed_indicators=None, future_signal=None, path=None) -> None:
    """INSERT OR REPLACE keyed on `id` (the card's own front-matter id) -- re-`add`ing the
    same card (e.g. after an edit) replaces that one card's row in place; it never
    accumulates duplicate rows for the same card, and never touches any other card's row.
    List/dict fields are stored as JSON text via `*_json` columns."""
    conn.execute(
        """INSERT OR REPLACE INTO experience_log
           (id, date_event, date_collected, role, place, node_ids_json, tag,
            measurables_json, politics, philosophy, structure, system, ethics,
            dag_gaps_json, ews_element, sprc, proposed_indicators_json, future_signal, path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (id, date_event, date_collected, role, place,
         json.dumps(node_ids if node_ids is not None else [], ensure_ascii=False),
         tag,
         json.dumps(measurables if measurables is not None else [], ensure_ascii=False),
         politics, philosophy, structure, system, ethics,
         json.dumps(dag_gaps if dag_gaps is not None else [], ensure_ascii=False),
         None if ews_element is None else str(ews_element),
         sprc,
         json.dumps(proposed_indicators if proposed_indicators is not None else [],
                     ensure_ascii=False),
         future_signal, path),
    )
    conn.commit()


def query_experience(conn: sqlite3.Connection, term: str = None, *, id=None,
                      role=None, limit=500) -> list:
    """`term` does a case-insensitive substring search across every text field (id, place,
    role, the five lens fields, future_signal) -- this is the `find <term>` CLI verb.
    Passing no filters at all returns every row (the `list` CLI verb)."""
    sql = "SELECT * FROM experience_log WHERE 1=1"
    args = []
    if id is not None:
        sql += " AND id = ?"
        args.append(id)
    if role is not None:
        sql += " AND role = ?"
        args.append(role)
    if term:
        sql += """ AND (
            id LIKE ? OR place LIKE ? OR role LIKE ? OR politics LIKE ? OR
            philosophy LIKE ? OR structure LIKE ? OR system LIKE ? OR ethics LIKE ? OR
            future_signal LIKE ? OR measurables_json LIKE ? OR
            proposed_indicators_json LIKE ?
        )"""
        needle = f"%{term}%"
        args.extend([needle] * 11)
    sql += " ORDER BY date_event, id LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]
