#!/usr/bin/env python3
"""watchlist.py -- FloodConnect cross-session WATCHLIST + ROUTER + ALERT_EVENT
(WATCHLIST.md sections 1-9, TRIGGERS.md sections 3-5).

Scope (Part C2 of the M8 split; Part C1 is l0_check.py's fetch+evaluate, which this
module never duplicates): this module takes the per-source result of a single check
(e.g. `l0_check.check(at)`'s reasons/signals/colour_floor/action) and decides what
happens to that point's own cross-session row -- the schema (section 1), the start
level a NEW session must resume at (TRIGGERS section 5 / WATCHLIST section 3's
"start level"), the ACTIVE/COOLING/CLOSED state machine for ONE check (WATCHLIST
section 3's table + invariants), and the emitted `fc.watch_update.v2` block (ops +
alert_events + card + brief, WATCHLIST section 9).

This module makes NO network call of any kind -- it only ever reads/writes the
caller's own local storage (default: gitignored `data/` CSV files, WATCHLIST
section 1/8) or, in AGENT_MCP_STORAGE mode, returns the same ops/archive_bundle for
the caller's own AI to apply through ITS connected storage MCP (never a
FloodConnect-hosted store, per feedback-floodconnect-retain-every-run.md).

Everything the state machine needs from "the agency's own words" (trigger ids,
action, colour_floor) is computed by l0_check.py / the fuller Sandwich (kb.py);
this module never invents a trigger id, a colour or a threshold of its own.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
from pathlib import Path

SCHEMA = "fc.watch.v2"

# WATCHLIST.md section 1.1/4: the one constant this module itself still carries --
# its value and provenance are read FROM TRIGGERS.md section 4, never re-decided
# here (this dict is printed verbatim in every watch_update block, per that file's
# "ต้องพิมพ์ tag ออกมาใน output ทุกครั้งที่ใช้").
N_QUIET = {"value": 2, "src": "TRIGGERS.md §4", "tag": "FC_DEFAULT"}

# WATCHLIST.md section 1.3 -- exact column order, UTF-8 with BOM.
CSV_HEADER = [
    "point_id", "h", "lat", "lon", "area", "iso", "province_th", "kg_anchor",
    "reasons", "signals", "depth", "colour", "first_seen", "last_checked",
    "next_due", "expires", "quiet_streak", "status", "alert_event_ids", "schema",
]
# "required = ทุกคอลัมน์ยกเว้น area,kg_anchor,expires" (section 1.3).
_OPTIONAL_COLUMNS = {"area", "kg_anchor", "expires"}

COLOUR_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
DEPTH_RANK = {"H0": 0, "H1": 1, "H2": 2, "H3": 3}

DEFAULT_STORE_DIR = Path("data")  # gitignored (see .gitignore "data/"), per-user only
WATCHLIST_CSV_NAME = "watchlist.csv"
WATCH_LOG_CSV_NAME = "watch_log.csv"
WATCH_CLOSED_CSV_NAME = "watch_closed.csv"
WATCH_PENDING_JSONL_NAME = "watch_pending.jsonl"

# Trigger-id prefixes this module never auto-clears on a fresh read (WATCHLIST
# section 3 invariants: a kg_gap/contradiction/official-order stays until something
# EXPLICIT resolves it -- a generic "the source came back clean this check" is not
# enough, because none of these three are "the source" in the single-category sense
# the fresh-read clearing rule is about).
_STICKY_REASON_IDS = frozenset({"H3-ORDER", "H3-NOTFETCHED", "H2-CONFLICT", "H2-KGGAP", "GROUND"})


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def h12(point_id: str) -> str:
    """section 1.1 `h`: first 12 hex chars of sha256(point_id) -- used in calendar/
    alert ids INSTEAD OF coordinates (section 7 privacy: ".ics และ alert id ใช้ h
    (hash) แทนพิกัด เพราะ pt: id มีพิกัดอยู่ในตัว")."""
    return hashlib.sha256(point_id.encode("utf-8")).hexdigest()[:12]


def point_id_for(point_cfg: dict) -> str:
    """section 1.1 `point_id`: `kg:<kg_node_id>` when the point has a declared KG
    anchor (its own Z0 gauge node), else `pt:<lat>,<lon>` -- the code formats the
    string (no rounding), it never snaps/guesses a KG node from coordinates."""
    z0 = point_cfg.get("z0")
    if z0:
        return f"kg:gauge:{z0['source_id']}:{z0['code']}"
    return f"pt:{point_cfg['lat']},{point_cfg['lon']}"


def kg_anchor_for(point_cfg: dict) -> str:
    z0 = point_cfg.get("z0")
    return f"gauge:{z0['source_id']}:{z0['code']}" if z0 else ""


def colour_max(*colours: "str | None") -> str:
    """max(official order, CAP colour floor, ground, reading) per WATCHLIST section
    3's colour invariant -- but UNKNOWN is never allowed to stand in for GREEN
    (UNKNOWN != safe): a concrete colour among the arguments always wins over
    UNKNOWN/None; the result is UNKNOWN only when NO argument carries a concrete
    reading (i.e. nothing at all could be determined), never when one source failed
    while another succeeded."""
    concrete = [c for c in colours if c in COLOUR_RANK]
    if not concrete:
        return "UNKNOWN"
    return max(concrete, key=lambda c: COLOUR_RANK[c])


def depth_max(*depths: "str | None") -> str:
    concrete = [d for d in depths if d in DEPTH_RANK]
    return max(concrete, key=lambda d: DEPTH_RANK[d]) if concrete else "H0"


def depth_for_action(action: "str | None") -> str:
    """l0_check.py's `action` field -> the depth that check actually reached.
    "CARD" still reaches H2 per TRIGGERS.md section 0 ("CARD = การ์ดฉุกเฉินก่อน
    แล้ว H2")."""
    return {"CARD": "H2", "DRILL+H2": "H2", "H2": "H2", "H1": "H1"}.get(action or "", "H1")


def _category(reason_id: str) -> str:
    """"L0-CAP-SEV" -> CAP, "Z0-RISE" -> Z0, "H1:Z0-RISE:<node>" -> Z0,
    "RAIN-NOGAUGE" -> RAIN, "FCST-FAIL" -> FCST, "CAP-FAIL" -> CAP. Used only to
    decide whether an id's OWN source category was freshly re-read this check
    (section 3's reasons-removal rule) -- never to join points (that is the KG-only
    rule, a completely different thing)."""
    rid = reason_id.split(":")[-2] if reason_id.count(":") >= 2 else reason_id
    rid = rid.rsplit("@", 1)[0]
    if rid.startswith("L0-"):
        rid = rid[len("L0-"):]
    return rid.split("-", 1)[0]


# ---------------------------------------------------------------------------
# section 1.3: CSV <-> row dict
# ---------------------------------------------------------------------------

def row_to_csv_dict(row: dict) -> dict:
    out = {}
    for col in CSV_HEADER:
        v = row.get(col, "" if col in _OPTIONAL_COLUMNS else None)
        if col in ("reasons", "signals", "alert_event_ids"):
            v = "|".join(v or [])
        elif v is None:
            raise ValueError(f"row missing required column {col!r}: {row!r}")
        out[col] = v
    return out


def csv_dict_to_row(d: dict) -> dict:
    row = dict(d)
    for col in ("reasons", "signals", "alert_event_ids"):
        row[col] = [x for x in (d.get(col) or "").split("|") if x]
    row["lat"] = float(d["lat"])
    row["lon"] = float(d["lon"])
    row["quiet_streak"] = int(d["quiet_streak"])
    return row


def write_watchlist_csv(path: Path, rows: "dict[str, dict]") -> None:
    """Atomic write: temp file + rename (WATCHLIST.md section 8's LOCAL_FS rewrite
    rule -- "เขียนไฟล์ temp แล้ว rename"). Caller must only call this when the
    session's own read was READ_OK (enforced by `WatchStore.flush`, not here)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_HEADER)
    w.writeheader()
    for row in rows.values():
        w.writerow(row_to_csv_dict(row))
    tmp.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))
    tmp.replace(path)


def read_watchlist_csv(path: Path) -> "dict[str, dict]":
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or list(reader.fieldnames) != CSV_HEADER:
        raise ValueError(f"watchlist.csv header mismatch: {reader.fieldnames!r}")
    rows = {}
    for d in reader:
        row = csv_dict_to_row(d)
        rows[row["point_id"]] = row
    return rows


def append_csv_row(path: Path, header: "list[str]", flat_row: dict) -> None:
    """Append-only (section 1.2: watch_log/watch_closed are NEVER pruned/rewritten
    wholesale -- only ever appended to)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        if is_new:
            f.write("﻿")
        w = csv.DictWriter(f, fieldnames=header)
        if is_new:
            w.writeheader()
        w.writerow(flat_row)


# ---------------------------------------------------------------------------
# section 2 step 2 + section 5: read status
# ---------------------------------------------------------------------------

class ReadResult:
    __slots__ = ("status", "rows", "pending")

    def __init__(self, status: str, rows: "dict[str, dict]", pending: "list[dict]"):
        self.status = status  # READ_OK | NO_STORE | UNREAD
        self.rows = rows
        self.pending = pending


def find_closed_row(store_dir: Path, point_id: str) -> "dict | None":
    """Section 3's "ไม่มีแถว (หรืออยู่ใน watch_closed -> REOPEN)": scans
    `watch_closed.csv` (append-only, never large relative to one lookup) for the
    MOST RECENT row with this `point_id`, so a point that closed once and fires
    again is reopened with its history intact, not treated as a brand-new NEW."""
    path = store_dir / WATCH_CLOSED_CSV_NAME
    if not path.exists():
        return None
    try:
        rows = read_watchlist_csv(path)  # header matches CSV_HEADER; dict keyed by
        # point_id already de-duplicates to the LAST row written for each id, since
        # DictReader iterates in file order and this re-keys every match.
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return rows.get(point_id)


def read_store(store_dir: Path = DEFAULT_STORE_DIR) -> ReadResult:
    """WATCHLIST.md section 2 steps 1-2. LOCAL_FS reader: no watchlist.csv AND no
    watch_pending.jsonl at all -> NO_STORE (true first-ever run). A watchlist.csv
    that exists but fails to parse (bad header, truncated row, bad float/int) ->
    UNREAD (section 8: "ห้ามเขียนทับ ... ห้ามลบหรือย้ายแถว"). Otherwise READ_OK,
    merging any carried-over watch_pending ops (section 2 step 3) is the CALLER's
    job once it has rows -- this function only reports what it found."""
    wl_path = store_dir / WATCHLIST_CSV_NAME
    pending_path = store_dir / WATCH_PENDING_JSONL_NAME
    pending = []
    if pending_path.exists():
        try:
            for line in pending_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    pending.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            return ReadResult("UNREAD", {}, [])
    if not wl_path.exists():
        return ReadResult("NO_STORE" if not pending else "READ_OK", {}, pending)
    try:
        rows = read_watchlist_csv(wl_path)
    except (OSError, ValueError, UnicodeDecodeError):
        return ReadResult("UNREAD", {}, pending)
    return ReadResult("READ_OK", rows, pending)


# ---------------------------------------------------------------------------
# TRIGGERS.md section 5 + WATCHLIST.md section 3 "start level": ROUTER
# ---------------------------------------------------------------------------

def start_level(read_status: str, row: "dict | None") -> str:
    """The level a NEW session must resume a given point at, in TRIGGERS.md
    section 5's own exhaustive, ordered form (WATCHLIST.md section 3's shorter
    prose table is the same rule after the ACTIVE/COOLING case split; per that
    file's section 10, where the two ever looked different TRIGGERS.md's wording
    now wins and nothing differs). Order matters -- checked top to bottom:

      1. UNREAD (storage exists but could not be read/parsed this session) -> H2,
         always, regardless of what the (unreadable) row might have said --
         "state หาย != ปลอดภัย; กันการรีเซ็ตเงียบหลัง escalate".
      2. No row for this point at all (first-ever check, or NO_STORE) -> H0 (L0).
      3. reasons carries H3-ORDER or H3-NOTFETCHED -> H3, always, regardless of
         streak -- an unresolved official order/un-fetched H3 source is never
         let the router start shallower than H3.
      4. status == ACTIVE, or quiet_streak < N_QUIET -> H2.
      5. status == COOLING and quiet_streak >= N_QUIET -> H0.

    (4) and (5) are an exhaustive split over status in {ACTIVE, COOLING}: a
    freshly-COOLING row (quiet_streak reset to 0 on entry, WATCHLIST section 3's
    transition table) still starts at H2 for one more check before it is trusted
    down to H0 -- this is intentionally slightly more conservative than WATCHLIST
    section 3's one-line "COOLING -> L0", never less.
    """
    if read_status == "UNREAD":
        return "H2"
    if row is None or read_status == "NO_STORE":
        return "H0"
    reasons = row.get("reasons") or []
    if any(r.split("@", 1)[0] in ("H3-ORDER", "H3-NOTFETCHED") for r in reasons):
        return "H3"
    if row.get("status") == "ACTIVE" or int(row.get("quiet_streak", 0)) < N_QUIET["value"]:
        return "H2"
    return "H0"


# ---------------------------------------------------------------------------
# WATCHLIST.md section 3: reasons merge + event classification
# ---------------------------------------------------------------------------

def merge_reasons(old_reasons: "list[str]", firing_ids: "list[str]", now_iso: str,
                   evaluated_categories: "frozenset[str] | None" = None) -> "list[str]":
    """Each entry is "<ID>@<since>". An id's `since` is preserved across checks
    while it keeps firing; a NEWLY-firing id gets `since = now_iso`. An id that
    stopped firing is DROPPED only when its own category was evaluated (fetched
    successfully, i.e. this check's `firing_ids` could in principle have carried an
    id of that category but did not) for THIS check -- "ID จะถูกลบออกได้เฉพาะเมื่ออ่าน
    แหล่งของมันได้แบบ fresh แล้วเงื่อนไขเป็นเท็จ" (WATCHLIST section 3). Sticky ids
    (H3-ORDER/H3-NOTFETCHED/H2-CONFLICT/H2-KGGAP/GROUND) are NEVER auto-dropped by
    this generic merge -- clearing one of those needs its own explicit evidence
    (an official cancellation, a re-run KG-gap check, ...), out of this function's
    scope by design."""
    if evaluated_categories is None:
        evaluated_categories = frozenset(_category(i) for i in firing_ids) or frozenset({"CAP", "RAIN", "FCST", "Z0"})
    firing_set = set(firing_ids)
    kept: "dict[str, str]" = {}
    for entry in old_reasons:
        rid, _, since = entry.partition("@")
        if rid in firing_set:
            kept[rid] = since  # preserve original since; will be confirmed below
        elif rid in _STICKY_REASON_IDS:
            kept[rid] = since
        elif _category(rid) not in evaluated_categories:
            kept[rid] = since  # not re-evaluated this check -- keep conservatively
        # else: dropped -- category WAS freshly read this check and this id did not fire
    for rid in firing_ids:
        if rid not in kept:
            kept[rid] = now_iso
    return [f"{rid}@{since}" for rid, since in kept.items()]


def classify_event(old_reason_ids: "set[str]", new_reasons: "list[str]",
                    old_colour: "str | None", new_colour: str, action: "str | None") -> str:
    """CARD > WORSEN > FIRE > QUIET (WATCHLIST section 3). `new_reasons` are the
    full "<ID>@<since>" merged list for THIS row after this check."""
    new_ids = {r.split("@", 1)[0] for r in new_reasons}
    if "H3-ORDER" in new_ids or action == "CARD":
        return "CARD"
    # WORSEN means "got worse relative to an ALREADY-firing row" -- a row with no
    # prior reasons at all that starts firing is FIRE (its first occurrence), not
    # WORSEN (nothing to worsen relative to).
    is_new = bool(old_reason_ids) and bool(new_ids - old_reason_ids)
    worsened_colour = (old_colour in COLOUR_RANK and new_colour in COLOUR_RANK
                       and COLOUR_RANK[new_colour] > COLOUR_RANK[old_colour])
    if is_new or worsened_colour:
        return "WORSEN"
    if new_ids:
        return "FIRE"
    return "QUIET"


# ---------------------------------------------------------------------------
# WATCHLIST.md section 6: dedup / alert ids
# ---------------------------------------------------------------------------

def alert_event_id(h: str, reason_id: str, since: str) -> str:
    """section 6: `fc:<h>:<ID>@<since>` -- one id per CONTINUOUS firing span of one
    trigger id, so a daily-repeating CAP-FAIL does not mint a new alert every day
    (idempotent: re-emitting the same id is a no-op for a de-duplicating writer)."""
    return f"fc:{h}:{reason_id}@{since}"


def new_alert_event_ids(h: str, new_reasons: "list[str]", old_alert_ids: "list[str]") -> "list[str]":
    """One alert_event id per entry of `new_reasons` whose id is not already covered
    by an existing alert_event id for the SAME (id, since) span -- "alert_event
    สำหรับ ID ใหม่เท่านั้น" (section 3's ACTIVE|FIRE row)."""
    out = []
    existing = set(old_alert_ids)
    for entry in new_reasons:
        rid, _, since = entry.partition("@")
        aid = alert_event_id(h, rid, since)
        if aid not in existing:
            out.append(aid)
    return out


def ics_vevent(h: str, area: str, colour: str, next_due: str, reason_ids: "list[str]",
                sequence: int, status: "str | None" = None) -> str:
    """WATCHLIST.md section 4's exact VEVENT shape. No `VALARM` (uses the calendar's
    own default), no coordinates/point_id anywhere in the text -- only `h`."""
    lines = [
        "BEGIN:VEVENT",
        f"UID:{h}@fc-watch",
        f"SEQUENCE:{sequence}",
        f"DTSTART;TZID=Asia/Bangkok:{next_due}",
        f"SUMMARY:FloodConnect เช็กจุด {area} ({colour})",
        f"DESCRIPTION:{'|'.join(r.split('@', 1)[0] for r in reason_ids)} · "
        f"เป่ด AI แล้วพิมพ์ \"เช็กน้ำ\"",
    ]
    if status:
        lines.append(f"STATUS:{status}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# WATCHLIST.md section 3: the state machine, ONE check, ONE row
# ---------------------------------------------------------------------------

class CheckInput:
    """What one source-of-truth check (l0_check.check(), or the fuller Sandwich)
    hands this module about ONE point. `official_order_colour`/`cap_colour_floor`
    are kept separate from `reading_colour` precisely so `colour_max` can apply
    WATCHLIST section 3's floor rule without this module ever computing a colour
    from a raw water level itself (that stays the Sandwich/Jev model's job)."""

    def __init__(self, point_id: str, lat: float, lon: float, area: str, iso: str,
                 province_th: str, kg_anchor: str, firing_ids: "list[str]",
                 signals: "list[str]", action: "str | None", reading_colour: "str | None",
                 cap_colour_floor: "str | None" = None, official_order_colour: "str | None" = None,
                 h3_order_active: bool = False, cap_match_active: bool = False,
                 expires: str = "", next_due_candidates: "list[str] | None" = None):
        self.point_id = point_id
        self.lat, self.lon, self.area = lat, lon, area
        self.iso, self.province_th, self.kg_anchor = iso, province_th, kg_anchor
        self.firing_ids = firing_ids
        self.signals = signals
        self.action = action
        self.colour = colour_max(reading_colour, cap_colour_floor, official_order_colour)
        self.depth = depth_for_action(action)
        self.h3_order_active = h3_order_active
        self.cap_match_active = cap_match_active
        self.expires = expires
        self.next_due_candidates = next_due_candidates or []


def _next_due(candidates: "list[str]") -> str:
    """WATCHLIST.md section 4: `min(c > now)`, else `NEXT_SESSION`. Candidates are
    ISO8601 strings; this module never invents one -- the caller passes whatever
    real candidates it has (CAP expires/effective, an ETA)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future = []
    for c in candidates:
        try:
            dt = datetime.datetime.fromisoformat(c.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.astimezone(datetime.timezone.utc) > now:
            future.append((dt, c))
    return min(future)[1] if future else "NEXT_SESSION"


def apply_check(old_row: "dict | None", chk: CheckInput, *, now_iso: "str | None" = None) -> dict:
    """WATCHLIST.md section 3's full table, for ONE point, ONE check. Returns:
        {"row": dict|None,       # the new stored row, or None if nothing to track
         "event": "CARD"|"WORSEN"|"FIRE"|"QUIET",
         "closed": bool,         # True -> caller must append to watch_closed and
                                  #         delete from watchlist (append BEFORE
                                  #         delete; never delete if append fails)
         "reopened": bool,       # True -> old_row came from watch_closed
         "new_alert_event_ids": [str, ...],
         "vevent": str|None, "vevent_sequence": int, "vevent_status": str|None}
    Never raises for "nothing happened" (QUIET with no prior row); the FIRE/
    MISS/STALE invariant ("ไม่มีวันลดระดับ ไม่ปิดแถว และ reset streak") is upheld
    structurally: those always show up as a non-empty `chk.firing_ids`, so `event`
    can never be QUIET while one of them is present.
    """
    now_iso = now_iso or _utcnow_iso()
    old_reasons = (old_row or {}).get("reasons") or []
    old_reason_ids = {r.split("@", 1)[0] for r in old_reasons}
    old_colour = (old_row or {}).get("colour")
    old_status = (old_row or {}).get("status")
    old_alert_ids = (old_row or {}).get("alert_event_ids") or []
    old_streak = int((old_row or {}).get("quiet_streak", 0))
    old_first_seen = (old_row or {}).get("first_seen", now_iso)
    old_expires = (old_row or {}).get("expires", "")

    new_reasons = merge_reasons(old_reasons, chk.firing_ids, now_iso)
    event = classify_event(old_reason_ids, new_reasons, old_colour, chk.colour, chk.action)
    h = h12(chk.point_id)

    def _base_row(status: str, streak: int, first_seen: str, expires: str) -> dict:
        return {
            "point_id": chk.point_id, "h": h, "lat": chk.lat, "lon": chk.lon,
            "area": chk.area, "iso": chk.iso, "province_th": chk.province_th,
            "kg_anchor": chk.kg_anchor, "reasons": new_reasons, "signals": chk.signals,
            "depth": depth_max((old_row or {}).get("depth"), chk.depth),
            "colour": colour_max(old_colour, chk.colour),
            "first_seen": first_seen, "last_checked": now_iso,
            "next_due": _next_due(chk.next_due_candidates), "expires": expires or old_expires,
            "quiet_streak": streak, "status": status,
            "alert_event_ids": list(old_alert_ids), "schema": SCHEMA,
        }

    # section 1.2's watch_log event vocabulary is WIDER than this function's own
    # CARD>WORSEN>FIRE>QUIET decision class: NEW/REOPEN/COOL/CLOSE mark a STATUS
    # TRANSITION, independent of which of the 4 decision classes caused it --
    # `log_event` (not `event`) is what a caller writes into the watch_log row.
    result = {"closed": False, "reopened": False, "vevent": None,
              "vevent_sequence": 0, "vevent_status": None}

    if old_status not in ("ACTIVE", "COOLING"):  # no row, or row came from watch_closed
        if event == "QUIET":
            result.update(row=None, event=event, log_event="QUIET", new_alert_event_ids=[])
            return result
        row = _base_row("ACTIVE", 0, now_iso, chk.expires)
        new_ids = new_alert_event_ids(h, new_reasons, [])
        reopened = old_row is not None  # caller passed a watch_closed row in
        result.update(row=row, event=event, log_event=("REOPEN" if reopened else "NEW"),
                      reopened=reopened, new_alert_event_ids=new_ids, vevent_sequence=0,
                      vevent=ics_vevent(h, chk.area, row["colour"], row["next_due"], new_reasons, 0))
        return result

    if old_status == "ACTIVE":
        if event in ("FIRE", "WORSEN", "CARD"):
            row = _base_row("ACTIVE", 0, old_first_seen, chk.expires)
            new_ids = new_alert_event_ids(h, new_reasons, old_alert_ids)
            row["alert_event_ids"] = old_alert_ids + new_ids
            result.update(row=row, event=event, log_event=event, new_alert_event_ids=new_ids,
                          vevent_sequence=1, vevent=(ics_vevent(h, chk.area, row["colour"], row["next_due"],
                                                                 new_reasons, 1) if new_ids else None))
            return result
        # QUIET
        streak = old_streak + 1
        if streak >= N_QUIET["value"] and not chk.cap_match_active and not chk.h3_order_active:
            row = _base_row("COOLING", 0, old_first_seen, chk.expires)
            result.update(row=row, event=event, log_event="COOL", new_alert_event_ids=[])
            return result
        row = _base_row("ACTIVE", streak, old_first_seen, chk.expires)
        result.update(row=row, event=event, log_event="QUIET", new_alert_event_ids=[])
        return result

    # old_status == "COOLING"
    if event in ("FIRE", "WORSEN", "CARD"):
        row = _base_row("ACTIVE", 0, old_first_seen, chk.expires)
        new_ids = new_alert_event_ids(h, new_reasons, old_alert_ids)
        row["alert_event_ids"] = old_alert_ids + new_ids
        result.update(row=row, event=event, log_event=event, new_alert_event_ids=new_ids, vevent_sequence=1,
                      vevent=(ics_vevent(h, chk.area, row["colour"], row["next_due"], new_reasons, 1)
                              if new_ids else None))
        return result
    # QUIET
    streak = old_streak + 1
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    expires_val = chk.expires or old_expires
    expires_passed = not expires_val or (
        datetime.datetime.fromisoformat(expires_val.replace("Z", "+00:00")).astimezone(
            datetime.timezone.utc) <= now_dt)
    if streak >= N_QUIET["value"] and expires_passed and not chk.h3_order_active:
        # "CLOSED" (not "COOLING") is the row's own stored status from here on --
        # this is the one marker `find_closed_row`/the top-of-function dispatch
        # uses to tell a watch_closed row apart from a live COOLING one, so a
        # later re-fire reopens it (section 3's "REOPEN") instead of being
        # mistaken for an already-COOLING live row.
        row = _base_row("CLOSED", streak, old_first_seen, chk.expires)
        result.update(row=row, event=event, log_event="CLOSE", new_alert_event_ids=[], closed=True,
                      vevent_sequence=2, vevent_status="CANCELLED",
                      vevent=ics_vevent(h, chk.area, row["colour"], "NEXT_SESSION", [], 2, "CANCELLED"))
        return result
    row = _base_row("COOLING", streak, old_first_seen, chk.expires)
    result.update(row=row, event=event, log_event="QUIET", new_alert_event_ids=[])
    return result


# ---------------------------------------------------------------------------
# WATCHLIST.md section 9: the one emitted block + section 8's write ordering
# ---------------------------------------------------------------------------

def build_watch_update(read: ReadResult, point_id: str, applied: dict, card: "str | None",
                        brief: str) -> dict:
    """Assembles the exact `fc.watch_update.v2` shape (WATCHLIST section 9). `ops`
    follows section 8's fixed write order: (1) upsert watchlist, (2) append
    watch_log, (3) calendar, (4) alert_event, (5) move-to-closed. When
    `read.status != "READ_OK"` every op the caller would otherwise emit for (1)/(5)
    is instead downgraded by the caller into a `watch_pending` append (section 8's
    UNREAD rule) -- this function does not downgrade on its own; it only reports
    what `apply_check` decided, so a caller that ignores `read.status` would be
    violating section 8, not this function."""
    ops = []
    row = applied["row"]
    if row is not None:
        ops.append({"op": "upsert", "table": "watchlist", "key": point_id, "row": row})
        ops.append({"op": "append", "table": "watch_log", "row": {
            "point_id": point_id, "checked_at": row["last_checked"],
            "start_level": None, "depth": row["depth"],
            "event": applied.get("log_event", applied["event"]),
            "colour": row["colour"], "reasons": "|".join(row["reasons"]),
            "sources": "|".join(row["signals"]), "quiet_streak": row["quiet_streak"],
            "status": row["status"]}})
        if applied.get("vevent"):
            ops.append({"op": "calendar_upsert", "uid": f"{row['h']}@fc-watch",
                        "ics": applied["vevent"]})
    if applied.get("closed"):
        ops.append({"op": "append", "table": "watch_closed", "row": row})
        ops.append({"op": "delete", "table": "watchlist", "key": point_id,
                    "after": "append ok"})
        ops.append({"op": "calendar_cancel", "uid": f"{row['h']}@fc-watch"})
    return {
        "schema": "fc.watch_update.v2", "generated_at": _utcnow_iso(),
        "read": read.status, "n_quiet": N_QUIET, "ops": ops,
        "alert_events": applied.get("new_alert_event_ids", []),
        "card": card, "brief": brief,
    }


class WatchStore:
    """LOCAL_FS default store (WATCHLIST section 1/8). AGENT_MCP_STORAGE callers
    should use `read_store`/`apply_check`/`build_watch_update` directly and apply
    the returned `ops` through their own connected storage MCP instead of this
    class, per feedback-floodconnect-retain-every-run.md's "ไม่มี FloodConnect
    hosted store" rule -- this class is just the level-1 (shell/MCP-tool, no other
    storage) fallback described in TRIGGERS.md's L0 cheapest-first ladder."""

    def __init__(self, store_dir: Path = DEFAULT_STORE_DIR):
        self.store_dir = Path(store_dir)
        self.read: "ReadResult | None" = None

    def load(self) -> ReadResult:
        self.read = read_store(self.store_dir)
        return self.read

    def check_point(self, point_id: str, chk: CheckInput, card: "str | None",
                     brief: str, *, reopened_from_closed: "dict | None" = None) -> dict:
        """One point, one check, writing LOCAL_FS immediately when the read this
        session was READ_OK; otherwise queues to `watch_pending.jsonl` (section 8's
        UNREAD rule: "ops ทั้งหมดไปอยู่ใน watch_pending") and reports NOT_SAVED only
        if even that append fails."""
        assert self.read is not None, "call load() first"
        old_row = (reopened_from_closed or self.read.rows.get(point_id)
                   or find_closed_row(self.store_dir, point_id))
        applied = apply_check(old_row, chk)
        applied["reopened"] = reopened_from_closed is not None
        wu = build_watch_update(self.read, point_id, applied, card, brief)

        if self.read.status not in ("READ_OK", "NO_STORE"):
            pend_path = self.store_dir / WATCH_PENDING_JSONL_NAME
            try:
                self.store_dir.mkdir(parents=True, exist_ok=True)
                with open(pend_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"base": "UNREAD", "point_id": point_id,
                                        "watch_update": wu}, ensure_ascii=False) + "\n")
                wu["save_status"] = "PENDING_WRITE"
            except OSError:
                wu["save_status"] = "NOT_SAVED"
            return wu

        try:
            if applied["row"] is not None:
                self.read.rows[point_id] = applied["row"]
                if applied.get("closed"):
                    del self.read.rows[point_id]
                write_watchlist_csv(self.store_dir / WATCHLIST_CSV_NAME, self.read.rows)
            for op in wu["ops"]:
                if op["op"] == "append" and op["table"] == "watch_log":
                    append_csv_row(self.store_dir / WATCH_LOG_CSV_NAME,
                                   ["point_id", "checked_at", "start_level", "depth",
                                    "event", "colour", "reasons", "sources",
                                    "quiet_streak", "status"], op["row"])
                elif op["op"] == "append" and op["table"] == "watch_closed":
                    append_csv_row(self.store_dir / WATCH_CLOSED_CSV_NAME, CSV_HEADER,
                                   row_to_csv_dict(op["row"]))
            wu["save_status"] = "SAVED"
        except OSError:
            wu["save_status"] = "NOT_SAVED"
        return wu


def build_archive_bundle(read: ReadResult) -> dict:
    """What an AGENT_MCP_STORAGE caller's own AI writes through ITS connected
    storage MCP (Drive/Sheet/DB) instead of this module touching any file --
    feedback-floodconnect-retain-every-run.md's "ถ้าเป็นเซสชั่นออนไลน์ก็ให้บันทึก
    ไว้ใน google drive หรืออื่นๆ ที่ผู้ใช้เชื่อม mcp ไว้"."""
    return {"schema": "fc.watch_archive_bundle.v1", "generated_at": _utcnow_iso(),
            "csv_header": CSV_HEADER, "rows": list(read.rows.values())}


# ---------------------------------------------------------------------------
# CLI glue: one point, one l0_check.check() call, one watch_update block
# ---------------------------------------------------------------------------

def _check_input_from_l0(at: str, l0_result: dict, point_cfg: dict) -> CheckInput:
    """Builds the `CheckInput` this module needs out of l0_check.check()'s own
    return shape (its `reasons`/`signals`/`action`/`colour_floor` fields) -- the
    one place that couples this module to l0_check.py's concrete output, so a
    future second check source (the fuller H2 Sandwich) only needs its own small
    adapter next to this one, never a change inside `apply_check` itself."""
    point_id = point_id_for(point_cfg)
    h3_order_active = "H3-ORDER" in l0_result.get("reasons", [])
    cap_match_active = any(r in l0_result.get("reasons", [])
                            for r in ("CAP-SEV", "CAP-ANY", "CAP-AREA?", "CAP-NEXT"))
    return CheckInput(
        point_id=point_id, lat=point_cfg["lat"], lon=point_cfg["lon"],
        area=point_cfg.get("province_th") or "", iso=point_cfg.get("iso") or "",
        province_th=point_cfg.get("province_th") or "", kg_anchor=kg_anchor_for(point_cfg),
        firing_ids=list(l0_result.get("reasons", [])), signals=list(l0_result.get("signals", [])),
        action=l0_result.get("action"),
        # l0_check.py does not itself read a ground/Jev colour (that is the fuller
        # Sandwich's job, out of this M8 part's scope) -- GREEN is used ONLY when
        # l0 came back QUIET (no reasons at all); an ESCALATE with no concrete
        # colour source yet stays UNKNOWN rather than defaulting to GREEN, so a
        # caller never prints "normal" off of a trigger it cannot yet colour.
        reading_colour=("GREEN" if l0_result.get("flag") == "QUIET" else None),
        cap_colour_floor=l0_result.get("colour_floor"),
        h3_order_active=h3_order_active, cap_match_active=cap_match_active,
    )


def apply_watch_from_l0_result(at: str, l0_result: dict,
                                store_dir: "Path | None" = None) -> dict:
    """Same WATCHLIST state machine + LOCAL_FS write as `run_watch` below, but takes
    an ALREADY-COMPUTED `l0_check.check(at)` result instead of fetching one itself --
    this is what lets a caller that already paid for the one `check()` network round
    (`kb.py check`/`kb.py answer`) wire every trigger straight into a
    `watch_update`/`alert_event` write WITHOUT a second, duplicate set of live GETs.
    `run_watch` (the standalone `kb.py watch` entrypoint) is now a thin wrapper that
    fetches its own `l0_result` and calls this function -- no behaviour changed for
    that existing caller, this is a pure split for reuse."""
    import l0_check
    _, point_cfg = l0_check._resolve_point(at)  # l0_check's own "point_id" here is
    # just the bare area key ("sammakorn") -- NEVER this module's `point_id`
    # (section 1.1's `kg:<node>`/`pt:<lat,lon>` form), so it is discarded; the
    # watchlist row key is always `chk.point_id` below.
    chk = _check_input_from_l0(at, l0_result, point_cfg)
    card = l0_result["line"] if l0_result.get("action") == "CARD" else None
    brief = f"{chk.area or at} {l0_result['line']}"
    # `store_dir=None` (the default) resolves the CURRENT `DEFAULT_STORE_DIR` at
    # CALL time, not at function-definition time -- a `Path` default argument is
    # evaluated once, at import, so a caller monkeypatching the module constant
    # (every other caller uses the real `data/` dir unchanged) would otherwise be
    # silently ignored.
    store = WatchStore(store_dir if store_dir is not None else DEFAULT_STORE_DIR)
    store.load()
    wu = store.check_point(chk.point_id, chk, card, brief)
    wu["at"] = at
    wu["point_id"] = chk.point_id
    # The row just written this call -- so the NEXT session's own read will come
    # back READ_OK (assuming this write succeeded); only a failed write keeps the
    # caution this session already read.
    next_read_status = "READ_OK" if wu.get("save_status") == "SAVED" else store.read.status
    wu["start_level_next_session"] = start_level(
        next_read_status, store.read.rows.get(chk.point_id))
    return wu


def run_watch(at: str, store_dir: Path = DEFAULT_STORE_DIR) -> dict:
    """The level-1 (shell/MCP-tool) entrypoint: runs `l0_check.check(at)` (the ONLY
    network/fetch this whole call makes -- this module itself never calls a
    third-party service), then the WATCHLIST state machine, then writes LOCAL_FS
    and returns the `fc.watch_update.v2` block. `kb.py watch --at <point>` and the
    `floodconnect_watch` MCP tool both call this one function."""
    import l0_check
    l0_result = l0_check.check(at)
    return apply_watch_from_l0_result(at, l0_result, store_dir=store_dir)


def cmd_watch(args) -> int:
    result = run_watch(args.at)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(result.get("card") or result.get("brief"))
        print(f"save: {result.get('save_status')}")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", required=True, help="area_id (sammakorn, ram53) or 'lat,lon'")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    return cmd_watch(args)


if __name__ == "__main__":
    import sys
    sys.exit(main())
