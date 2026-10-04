#!/usr/bin/env python3
"""
Plain-text history reader over the append-only `readout_log` table (see store.py /
site/build_data.py's write_readout_log()) -- this is the tool the founder reads a
water-politics / overall-picture lens through, not a scoring or ranking tool.

Every row in `readout_log` is exactly what one build run observed for one
(area, kind, key): a control-structure burden reading, a canal-graph edge direction, a
per-area pump count, the hero status word, or a rain/tide/forecast/water-balance/BMA
briefing summary. This script only replays those rows back as a compact timeline --
it computes nothing new, scores nothing, and picks no "winner" between runs.

CLI:
    python3 readout_history.py --history --days 7
    python3 readout_history.py --history --days 7 --area sammakorn
    python3 readout_history.py --history --days 7 --kind burden
"""
import argparse
import datetime
from pathlib import Path

import store

HERE = Path(__file__).parent


def _since_utc(days: int, now_utc: datetime.datetime | None = None) -> str:
    now = now_utc if now_utc is not None else datetime.datetime.now(datetime.timezone.utc)
    return (now - datetime.timedelta(days=days)).isoformat()


def _fmt_row(r: dict) -> str:
    bits = [r["run_at_utc"]]
    if r.get("state"):
        bits.append(f"state={r['state']}")
    if r.get("burdened_side"):
        bits.append(f"burdened={r['burdened_side']}")
    if r.get("value_a") is not None or r.get("value_b") is not None:
        bits.append(f"a={r.get('value_a')} b={r.get('value_b')}")
    if r.get("diff_m") is not None:
        bits.append(f"diff={r['diff_m']}")
    if r.get("persistence") is not None:
        bits.append(f"persistence={r['persistence']}")
    return "  " + " | ".join(str(b) for b in bits)


def build_history_text(conn, days: int, area: str | None = None,
                        kind: str | None = None,
                        now_utc: datetime.datetime | None = None) -> str:
    """Returns the plain-text timeline. Pure function of the rows it's given -- no
    scoring, no verdict, just a chronological replay per (area, kind, key).

    now_utc lets a caller (e.g. a test) fix the window's reference instant instead
    of relying on the real wall clock; defaults to the real "now" in production."""
    since = _since_utc(days, now_utc=now_utc)
    rows = store.query_readout_log(conn, area=area, kind=kind, since_utc=since, limit=20000)

    lines = []
    lines.append(f"MEASURED -- readout_log history, last {days} day(s)"
                  + (f", area={area}" if area else "")
                  + (f", kind={kind}" if kind else ""))
    lines.append("(replayed rows only -- no score, no ranking, no verdict)")
    lines.append("")

    if not rows:
        lines.append("(no rows in this window)")
        return "\n".join(lines)

    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r["area"], r["kind"], r["key"]), []).append(r)

    for (area_key, kind_key, key) in sorted(groups.keys()):
        group_rows = groups[(area_key, kind_key, key)]
        lines.append(f"[{area_key}] {kind_key}:{key} ({len(group_rows)} run(s))")
        for r in group_rows:
            lines.append(_fmt_row(r))
        lines.append("")

    # Per-area pump-count-over-time roll-up, called out separately since that's the
    # other explicit ask (pump counts over time, alongside the per-structure timeline).
    pump_groups = {k: v for k, v in groups.items() if k[1] == "pump"}
    if pump_groups:
        lines.append("--- pump counts over time (per area) ---")
        for (area_key, _, key) in sorted(pump_groups.keys()):
            lines.append(f"[{area_key}] {key}")
            for r in pump_groups[(area_key, "pump", key)]:
                extra = r.get("extra_json") or ""
                lines.append(f"  {r['run_at_utc']}  running={r.get('value_a')}"
                              f"/{r.get('value_b')} total  {extra}")
        lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history", action="store_true", required=True,
                     help="Print the readout_log timeline (the only mode this tool has).")
    ap.add_argument("--days", type=int, default=7, help="Look-back window in days.")
    ap.add_argument("--area", help="Filter to one area (e.g. sammakorn, ram53, citywide).")
    ap.add_argument("--kind", help="Filter to one kind (burden/edge/pump/status/rain/"
                                    "tide/balance/briefing).")
    ap.add_argument("--db", help="Override the SQLite DB path.")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else store.DEFAULT_DB_PATH
    conn = store.connect(db_path)
    try:
        print(build_history_text(conn, args.days, area=args.area, kind=args.kind))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
