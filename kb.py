#!/usr/bin/env python3
"""kb.py -- a small, stdlib-only query tool for this repo's knowledge base.

Design goal: make this git repo easy for both humans and AI to use. Humans read
`START_HERE.md`; this tool is the query-not-grep counterpart both a human and an
AI can run -- no network, no external dependency, each command finishes in well
under a second.

Commands:
    kb.py find "<term>"      -- case-insensitive search over docs/ + sources/registry.yaml
    kb.py ask Q-XXX-N        -- print a WATER_MANAGER_QUESTION_BANK.md row + docs that
                                 claim (via INDEX.yaml) to answer it
    kb.py status             -- print the question bank's own coverage-count summary and
                                 top-15 "ขาด" (missing) list, verbatim from the bank file
    kb.py sources            -- list sources/registry.yaml entries + last-seen timestamp
                                 from data/observations.sqlite, if that local DB exists
    kb.py history --days N   -- delegates to readout_history.py (readout_log replay)
    kb.py reindex            -- rebuild docs/knowledge/INDEX.yaml from the .md files under
                                 docs/ (never hand-edit INDEX.yaml -- run this instead)

This file intentionally does NOT depend on PyYAML: `docs/knowledge/INDEX.yaml` is written
and read back with a small hand-rolled parser tailored to the exact flat structure this
script itself produces (see `_dump_index`/`_parse_index` below), not a general YAML engine.
`sources/registry.yaml` is read with a line-oriented best-effort scan (see `_scan_registry`),
not a full YAML parser -- good enough to answer "what sources exist / what trust tier /
when last seen", not a substitute for reading the registry itself for anything that matters.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS_DIR = HERE / "docs"
KNOWLEDGE_DIR = DOCS_DIR / "knowledge"
INDEX_PATH = KNOWLEDGE_DIR / "INDEX.yaml"
REGISTRY_PATH = HERE / "sources" / "registry.yaml"
QUESTION_BANK_PATH = KNOWLEDGE_DIR / "WATER_MANAGER_QUESTION_BANK.md"
DB_PATH = HERE / "data" / "observations.sqlite"
READOUT_HISTORY = HERE / "readout_history.py"

from tag_vocabulary import TAG_VOCABULARY as _TAG_VOCABULARY  # noqa: E402 -- single source

TAG_ORDER = list(_TAG_VOCABULARY)

# Heuristic path -> tier mapping (INSTINCT, not a claim about the document's own content).
# First match wins; falls back to "ข้ามระดับ" (cross-level) when nothing matches.
TIER_RULES = [
    (r"docs/knowledge/agencies/", "ชาติ"),
    (r"docs/design/", "สถาปัตยกรรม"),
    (r"docs/ARCHITECTURE", "สถาปัตยกรรม"),
    (r"docs/CAPACITY|docs/DATA_SYSTEM|docs/LESSONS_nodes|docs/METHOD_", "ปฏิบัติการ"),
    (r"card_pathumthani|card_hatyai", "ข้ามระดับ"),
    (r"card_rangsit|card_yucharoen|card_participatory|bma_canal_scada", "เขต-อปท."),
]

BACKTICK_MD_RE = re.compile(r"`([\w./-]+\.md)`")
QID_RE = re.compile(r"Q-[A-Z0-9]+-\d+")


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# reindex
# ---------------------------------------------------------------------------

def _find_md_files() -> list[Path]:
    if not DOCS_DIR.is_dir():
        return []
    out = []
    for root, _dirs, fnames in os.walk(DOCS_DIR):
        for fn in fnames:
            if fn.endswith(".md"):
                out.append(Path(root) / fn)
    return sorted(out)


def _relpath(p: Path) -> str:
    return str(p.relative_to(HERE)).replace(os.sep, "/")


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _classify_tier(relpath: str) -> str:
    for pattern, tier in TIER_RULES:
        if re.search(pattern, relpath):
            return tier
    return "ข้ามระดับ"


def _extract_tags(relpath: str) -> list[str]:
    parts = Path(relpath).parts
    tags = [p for p in parts[:-1] if p != "docs"]
    tags.append(Path(relpath).stem)
    seen = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return seen


def _extract_sources(text: str, self_relpath: str) -> list[str]:
    found = set()
    for m in BACKTICK_MD_RE.finditer(text):
        candidate = m.group(1)
        if candidate == self_relpath:
            continue
        if (HERE / candidate).exists():
            found.add(candidate)
    return sorted(found)


def _dominant_status(text: str) -> str:
    counts = {t: len(re.findall(r"\b" + t + r"\b", text)) for t in TAG_ORDER}
    nonzero = [t for t in TAG_ORDER if counts[t] > 0]
    if not nonzero:
        return "RELAYED"
    if len(nonzero) > 1:
        return "mixed"
    return nonzero[0]


def _git_last_commit_date(relpath: str) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", relpath],
            cwd=HERE, capture_output=True, text=True, timeout=5, check=False,
        )
        d = out.stdout.strip()
        if d:
            return d
    except Exception:
        pass
    return datetime.date.today().isoformat()


def _build_answers_map() -> dict[str, set[str]]:
    if not QUESTION_BANK_PATH.exists():
        return {}
    mapping: dict[str, set[str]] = {}
    for line in _read_text(QUESTION_BANK_PATH).splitlines():
        if not line.strip().startswith("|"):
            continue
        qid_m = QID_RE.search(line)
        if not qid_m:
            continue
        qid = qid_m.group(0)
        for pm in BACKTICK_MD_RE.finditer(line):
            mapping.setdefault(pm.group(1), set()).add(qid)
    return mapping


def _entry_id(relpath: str) -> str:
    if relpath.startswith("docs/"):
        rest = relpath[len("docs/"):]
    else:
        rest = relpath
    if rest.endswith(".md"):
        rest = rest[:-3]
    return rest.replace("/", ".")


def _yaml_str(s: str) -> str:
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(_yaml_str(i) for i in items) + "]"


def _dump_index(entries: list[dict]) -> str:
    lines = [
        "# docs/knowledge/INDEX.yaml -- generated by `python3 kb.py reindex`. DO NOT HAND-EDIT.",
        "# tier/status are best-effort heuristics (INSTINCT), not a certified claim about the",
        "# document's own content -- read the document itself before relying on either field.",
        "",
    ]
    for e in entries:
        lines.append(f"- id: {_yaml_str(e['id'])}")
        lines.append(f"  title: {_yaml_str(e['title'])}")
        lines.append(f"  path: {_yaml_str(e['path'])}")
        lines.append(f"  tier: {_yaml_str(e['tier'])}")
        lines.append(f"  tags: {_yaml_list(e['tags'])}")
        lines.append(f"  sources: {_yaml_list(e['sources'])}")
        lines.append(f"  answers: {_yaml_list(e['answers'])}")
        lines.append(f"  status: {_yaml_str(e['status'])}")
        lines.append(f"  updated: {_yaml_str(e['updated'])}")
    lines.append("")
    return "\n".join(lines)


_ENTRY_RE = re.compile(r'^-\s+id:\s*"(.*)"\s*$')
_FIELD_RE = re.compile(r'^\s+(\w+):\s*(.*)$')
_FLOW_LIST_RE = re.compile(r'^\[(.*)\]$')


def _parse_scalar_or_list(raw: str):
    raw = raw.strip()
    m = _FLOW_LIST_RE.match(raw)
    if m:
        inner = m.group(1).strip()
        if not inner:
            return []
        items = re.findall(r'"((?:[^"\\]|\\.)*)"', inner)
        return [i.replace('\\"', '"').replace("\\\\", "\\") for i in items]
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw


def _parse_index(text: str) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = _ENTRY_RE.match(line)
        if m:
            if current is not None:
                entries.append(current)
            current = {"id": m.group(1)}
            continue
        if current is None:
            continue
        fm = _FIELD_RE.match(line)
        if fm:
            key, val = fm.group(1), fm.group(2)
            current[key] = _parse_scalar_or_list(val)
    if current is not None:
        entries.append(current)
    return entries


def cmd_reindex(_args) -> int:
    answers_map = _build_answers_map()
    entries = []
    for f in _find_md_files():
        relpath = _relpath(f)
        text = _read_text(f)
        entries.append({
            "id": _entry_id(relpath),
            "title": _first_h1(text) or f.stem,
            "path": relpath,
            "tier": _classify_tier(relpath),
            "tags": _extract_tags(relpath),
            "sources": _extract_sources(text, relpath),
            "answers": sorted(answers_map.get(relpath, set())),
            "status": _dominant_status(text),
            "updated": _git_last_commit_date(relpath),
        })
    entries.sort(key=lambda e: e["id"])
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(_dump_index(entries), encoding="utf-8")
    print(f"reindex: wrote {len(entries)} entries to {_relpath(INDEX_PATH)}")
    return 0


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    return _parse_index(_read_text(INDEX_PATH))


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------

def cmd_find(args) -> int:
    term_low = args.term.lower()
    targets: list[Path] = []
    if DOCS_DIR.is_dir():
        for root, _dirs, fnames in os.walk(DOCS_DIR):
            for fn in fnames:
                if fn.endswith((".md", ".yaml", ".yml")):
                    targets.append(Path(root) / fn)
    if REGISTRY_PATH.exists():
        targets.append(REGISTRY_PATH)

    hits = 0
    for f in sorted(set(targets)):
        try:
            lines = _read_text(f).splitlines()
        except Exception:
            continue
        relpath = _relpath(f)
        for i, line in enumerate(lines, start=1):
            if term_low in line.lower():
                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = snippet[:160] + "..."
                print(f"{relpath}:{i}: {snippet}")
                hits += 1
    if hits == 0:
        print(f"(no matches for {args.term!r})")
    return 0


# ---------------------------------------------------------------------------
# ask
# ---------------------------------------------------------------------------

def _find_bank_row(qid: str) -> dict | None:
    if not QUESTION_BANK_PATH.exists():
        return None
    headers: list[str] | None = None
    for line in _read_text(QUESTION_BANK_PATH).splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "#":
            headers = cells
            continue
        if cells[0].startswith("---"):
            continue
        if headers and qid in line:
            n = min(len(headers), len(cells))
            return dict(zip(headers[:n], cells[:n]))
    return None


def cmd_ask(args) -> int:
    qid = args.qid
    row = _find_bank_row(qid)
    if row is None:
        print(f"(question id {qid!r} not found in {_relpath(QUESTION_BANK_PATH)})")
    else:
        print(f"# {qid}")
        for k, v in row.items():
            print(f"{k}: {v}")
    print()
    matches = [e for e in _load_index() if qid in (e.get("answers") or [])]
    if matches:
        print(f"Docs (via INDEX.yaml) claiming to answer {qid}:")
        for e in matches:
            print(f"  - {e.get('path')}  [{e.get('status')}]  {e.get('title')}")
    else:
        print(f"(no docs in INDEX.yaml list {qid} under `answers` -- run "
              f"`floodconnect reindex`, or trust the bank's own status column above)")
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(_args) -> int:
    if not QUESTION_BANK_PATH.exists():
        print(f"({_relpath(QUESTION_BANK_PATH)} not found)")
        return 1
    text = _read_text(QUESTION_BANK_PATH)
    marker = "## สรุปจำนวนคำถามทั้งหมด"
    idx = text.find(marker)
    if idx == -1:
        print("(summary section not found in the question bank -- has its heading changed?)")
        return 1
    print(text[idx:].rstrip())
    return 0


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def _scan_registry() -> list[dict]:
    """Best-effort line scan of sources/registry.yaml's `sources:` and
    `reference_documents:` lists -- not a general YAML parser, see module docstring."""
    if not REGISTRY_PATH.exists():
        return []
    section = None
    records: list[dict] = []
    current: dict | None = None
    id_re = re.compile(r'^\s*-\s*id:\s*(\S+)\s*$')
    th_re = re.compile(r'^\s+th:\s*"([^"]*)')
    trust_re = re.compile(r'^\s*trust_tier:\s*"?([\w_]+)"?\s*$')

    def flush():
        if current is not None:
            records.append(current)

    for line in _read_text(REGISTRY_PATH).splitlines():
        if line.startswith("sources:"):
            section = "sources"
            continue
        if line.startswith("reference_documents:"):
            flush()
            current = None
            section = "reference_documents"
            continue
        m = id_re.match(line)
        if m and section:
            flush()
            current = {"section": section, "id": m.group(1), "label": None, "trust_tier": None}
            continue
        if current is None:
            continue
        m = th_re.match(line)
        if m and current.get("label") is None:
            current["label"] = m.group(1)
            continue
        m = trust_re.match(line)
        if m:
            current["trust_tier"] = m.group(1)
    flush()
    return records


def _last_seen(source_id: str) -> str | None:
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cur = conn.execute(
                "SELECT MAX(fetched_at_utc) FROM observations WHERE source_id = ?",
                (source_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def cmd_sources(_args) -> int:
    records = _scan_registry()
    if not records:
        print(f"(no records found in {_relpath(REGISTRY_PATH)})")
        return 1
    have_db = DB_PATH.exists()
    if not have_db:
        print("(no local data/observations.sqlite -- run `floodconnect answer --at <area>` "
              "without `--offline` (refresh is the default) to populate it; showing "
              "registry only, no last-seen timestamps)")
        print()
    for r in records:
        line = f"[{r['section']}] {r['id']}  trust_tier={r.get('trust_tier')}"
        if r.get("label"):
            line += f"  -- {r['label']}"
        print(line)
        if have_db and r["section"] == "sources":
            seen = _last_seen(r["id"])
            print(f"    last observation fetched_at_utc: {seen or '(none in local DB)'}")
    return 0


# ---------------------------------------------------------------------------
# history (delegates to readout_history.py)
# ---------------------------------------------------------------------------

def cmd_connectors(args) -> int:
    """Connectors health: dry mode (default) lists every wired source
    (collect.COLLECTORS) plus whether tests/contract/fixtures/ has a recorded real
    capture for it -- no network call, no caller cost. --live additionally makes
    ONE request per wired source (via collect.run, same one-GET/no-retry discipline as
    --refresh -- but see the FIX B item 2 note below for the one discipline it does NOT
    share with the sequential --refresh path) and prints ok/fail per source; this also
    runs on the CALLER's own network, never ours.

    FIX B item 2 (2026-10-04, SPEED + visibility): --live used to call `collect.run`
    SEQUENTIALLY with no timeout of its own beyond urllib's internal per-socket-
    operation timeout (collect.REQUEST_TIMEOUT_S=30s/collect.PDF_TIMEOUT_S=300s) and no
    progress output at all until the ENTIRE sweep (every wired collector, 60+ sources)
    finished -- a caller watching this command had no idea whether it was still
    running or stuck. Now wired `parallel=True` (one 20s-bounded thread-pool batch
    instead of 60+ sequential requests -- see collect.run's own docstring for why this
    does NOT carry the sequential path's per-run host circuit breaker) with a streaming
    `on_result` printer, so each source's line appears the moment that source's result
    is ready, not only after the whole batch completes. No TTL cache here (`ttl_s=0`,
    unchanged) -- --live is a human explicitly asking for a real connectivity check of
    every connector, not an answer-path refresh that should ever quietly skip one."""
    sys.path.insert(0, str(HERE))
    import collect as collect_mod
    fixtures_dir = HERE / "tests" / "contract" / "fixtures"
    wired = sorted(collect_mod.COLLECTORS.keys())
    live_results = {}
    if getattr(args, "live", False):
        source_ids = [sid for sid in wired if sid not in collect_mod.DORMANT_NOT_IN_ALL]

        def _progress(res):
            status = "skipped" if res.skipped else ("ok" if res.ok else "FAIL")
            note = f" ({res.note})" if res.note else ""
            print(f"  ...live: {res.source_id:32s} {status}{note}")

        print(f"# connectors --live: fetching {len(source_ids)} source(s) in parallel "
              "(20s per-source budget) -- progress as each one completes:")
        for r in collect_mod.run(source_ids, dry_run=False, parallel=True,
                                  per_source_timeout_s=20,
                                  max_workers=max(8, len(source_ids)),
                                  on_result=_progress):
            live_results[r.source_id] = r
        print()
    n_fixture = 0
    print(f"# connectors health ({'live, one GET each' if args.live else 'dry, no network'})")
    for sid in wired:
        sidecars = sorted(fixtures_dir.glob(f"{sid}_captured.sidecar.json")) if fixtures_dir.exists() else []
        has_fixture = bool(sidecars)
        n_fixture += has_fixture
        line = f"  {sid:32s} fixture={'yes' if has_fixture else 'NO '}"
        if args.live:
            if sid in collect_mod.DORMANT_NOT_IN_ALL:
                line += "  live=skipped (dormant, not in --all set)"
            else:
                r = live_results.get(sid)
                status = "skipped" if (r and r.skipped) else ("ok" if (r and r.ok) else "FAIL")
                line += f"  live={status}"
                if r and r.note:
                    line += f" ({r.note})"
        print(line)
    n_dormant = sum(1 for sid in wired if sid in collect_mod.DORMANT_NOT_IN_ALL)
    print(f"\n{n_fixture}/{len(wired)} wired collectors have a recorded contract fixture "
          f"(MEASURED, counting .sidecar.json files under tests/contract/fixtures/). "
          f"{n_dormant} wired collector(s) are DORMANT_NOT_IN_ALL (host-safety 403, "
          "see sources/registry.yaml) and excluded from --all/--refresh/--live.")
    return 0


def cmd_history(args) -> int:
    if not READOUT_HISTORY.exists():
        print(f"({_relpath(READOUT_HISTORY)} not found)")
        return 1
    cmd = [sys.executable, str(READOUT_HISTORY), "--history", "--days", str(args.days)]
    if args.area:
        cmd += ["--area", args.area]
    if args.kind:
        cmd += ["--kind", args.kind]
    result = subprocess.run(cmd, cwd=HERE, check=False)
    return result.returncode


# ---------------------------------------------------------------------------
# accountability (delegates to tools/kg/accountability.py -- logic lives there, this is
# just a dispatch, per the task's own instruction)
# ---------------------------------------------------------------------------

def cmd_accountability(args) -> int:
    sys.path.insert(0, str(HERE))
    from tools.kg import accountability
    return accountability.run(args.at, args.radius, args.json)


_FORECAST_KNOWN_POINTS = {
    "sammakorn": (13.758235, 100.676084), "ram53": (13.765540125000635, 100.61909460837903),
    "bangkok_east": (13.7734, 100.6813), "c2_nakhonsawan": (15.70, 100.14),
    "c13_chaophraya_dam": (15.15, 100.18), "hatyai": (7.0084, 100.4747),
    "nan": (18.7756, 100.7730), "chiangmai": (18.7883, 98.9853),
}
# fix (2026-10-04): `cmd_forecast`/`_answer_hazard` used to snap a bare
# 'lat,lon' to the NEAREST entry in `_FORECAST_KNOWN_POINTS` with no distance cap at
# all -- MEASURED later: `--at 7.88,98.39` (Phuket, >600km from
# every known point) silently resolved to `hatyai`'s own forecast point (cameras
# 128-197km away reported as if local), and `13.7275,100.7785` (~11km from Sammakorn)
# resolved to `sammakorn`'s point and reported its ACTIVE hazard as this other place's
# own. Beyond this radius a request now gets its own coordinate-derived point_id
# (never written into/read from a named point's cache) and an honest UNKNOWN hazard,
# never a neighbour's data relabelled as local.
_FORECAST_POINT_SNAP_RADIUS_KM = 5.0


def _coordinate_point_id(lat: float, lon: float) -> str:
    """A point_id derived from the coordinates themselves, never a named point --
    guarantees a far-away request's cached rows can never land under (and overwrite)
    a different, named point's own forecast cache."""
    return f"coord_{lat:.3f}_{lon:.3f}"


def _resolve_forecast_point(at: str, lat: float, lon: float) -> "tuple[str, bool]":
    """Resolves (at, lat, lon) to (point_id, within_range). `within_range` is False
    when `at` is not itself a known point id AND the nearest `_FORECAST_KNOWN_POINTS`
    entry is more than `_FORECAST_POINT_SNAP_RADIUS_KM` away -- see the fix note above.
    Shared by `cmd_forecast` and `_answer_hazard` so the two call sites can never
    diverge on this cap."""
    if at in _FORECAST_KNOWN_POINTS:
        return at, True
    import live_water_level as lwl_mod
    nearest_id = min(
        _FORECAST_KNOWN_POINTS,
        key=lambda k: lwl_mod.haversine_km(lat, lon, *_FORECAST_KNOWN_POINTS[k]))
    nearest_km = lwl_mod.haversine_km(lat, lon, *_FORECAST_KNOWN_POINTS[nearest_id])
    if nearest_km <= _FORECAST_POINT_SNAP_RADIUS_KM:
        return nearest_id, True
    return _coordinate_point_id(lat, lon), False


_FORECAST_MODEL_LABEL_TH = {
    "ecmwf_ifs025": "ECMWF", "gfs_seamless": "GFS", "icon_seamless": "ICON",
    "jma_seamless": "JMA", "gem_seamless": "GEM", "meteofrance_seamless": "Météo-France",
    "ukmo_seamless": "UKMO", "knmi_seamless": "KNMI", "cma_grapes_global": "CMA",
    "metno": "MET Norway",
}


# Note: sources/registry.yaml has no `stale_after_s` field for openmeteo_forecast16d
# ("model-dependent, 1h-6h update cycle upstream") or metno_locationforecast ("hourly
# steps") -- this is a repo-local, hand-chosen staleness cutoff for the `answer`/
# `forecast` commands specifically (an engineering default/judgment call, INSTINCT, not a
# value read from the registry and not a derived equation, so Toledo-first does not apply
# to a plain threshold).
#
# FIX (2026-10-03): this used to be its own private 24h-in-seconds
# constant, checked by hand-rolled `(now - issued).total_seconds() > _FORECAST_STALE_
# AFTER_S` arithmetic at both call sites below -- a second, unregistered staleness gate
# living next to `live_water_level.is_fresh`/`max_age_hours_for` (the single freshness
# gate every OTHER reading in this repo is routed through). Kept as the documented
# hours-equivalent default (still 24h, never silently widened) so the two call sites
# below can route through `lwl.is_fresh(..., max_age_hours=_FORECAST_STALE_AFTER_H)`
# instead of re-deriving the same comparison.
_FORECAST_STALE_AFTER_S = 24 * 3600
_FORECAST_STALE_AFTER_H = _FORECAST_STALE_AFTER_S / 3600.0


def _forecast_rows_by_model(
    point_id: str, now_utc: "datetime.datetime | None" = None,
) -> "tuple[dict, str | None, bool | None, str | None, dict]":
    """Shared by `cmd_forecast` and `_answer_hazard` -- read the cached
    openmeteo_forecast16d/metno_locationforecast rows for one point, convert each row's
    `observed_at_utc` to its Asia/Bangkok LOCAL calendar date (reusing
    `readout._local_date` -- never re-derived here, per Toledo/reuse-before-new-object
    discipline), and keep only local dates at or after LOCAL tomorrow.

    Before this fix, `tomorrow = dates[0]` ran over EVERY stored date with no time filter
    at all, keyed on the UTC-day prefix of `observed_at_utc` -- so a row dated days in the
    past (relative to Bangkok local "today") could be handed out as "tomorrow". Measured
    case: Sammakorn CMA row `observed_at_utc=
    2026-09-26T17:00:00+00:00` (Bangkok-local 27 Sep) was returned as "tomorrow" by a run
    five days later, on 2 Oct.

    FIX (2026-10-04, F-forecast-freshness): before this fix, freshness was checked ONCE
    against a single `issued_at` = max(fetched_at_utc) across ALL rows for the point
    (every model, every source, pooled together) -- so one model refreshed moments ago
    could mask another model whose own cache row was days stale: the pooled `issued_at`
    looked fresh, `stale=False` was reported for the WHOLE point, and the stale model's
    rain figures were handed out to `_answer_hazard`/`_classify_forward_hazard` as if they
    were current evidence. There was also no per-source staleness cutoff at all -- every
    row used the same `_FORECAST_STALE_AFTER_H` regardless of `source_id`, even though
    `sources/registry.yaml` already carries a `max_age_hours` per source
    (`lwl.max_age_hours_for`).

    Now every row is individually gated through `lwl.is_fresh(fetched_at_utc, now_utc,
    lwl.max_age_hours_for(source_id))` (the ONE freshness gate, per-source cutoff) BEFORE
    it is added to `by_model` -- a stale row is dropped outright, never averaged in,
    never silently kept to pad another model's date range. A model with NO fresh row left
    is dropped from `by_model` entirely (never returned as an empty/zero reading, which
    would look identical to "really fresh and really zero").

    Returns `(by_model, issued_at, stale, error_or_none, issued_at_by_model)`.
    `by_model` maps `model_name -> {local_date: value_mm}`, built from FRESH rows only,
    already filtered to future local dates only -- an empty dict with no error means
    "nothing ever collected for this point", "every cached row's local date has already
    passed", or "every row that still has a usable local date is stale"; callers do not
    need to tell those apart to answer honestly (all are legitimately OPEN/empty, never a
    guess). `issued_at_by_model` maps `model_name -> that model's own max fetched_at_utc`
    (over its fresh rows only) -- a caller that wants per-model provenance (not just the
    point-level summary) reads this instead of assuming every model shares one timestamp.
    `issued_at` is the max `fetched_at_utc` across the FRESH rows that made it into
    `by_model` (None when no fresh row exists), kept as a point-level summary for callers
    that only want one number. `stale` is True only when no fresh model is left at all
    (`by_model` is empty) despite rows having been read for this point -- a point with at
    least one fresh model is never reported stale at the point level just because another
    model's cache has gone stale; that model is simply absent from `by_model` instead.
    """
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    if not DB_PATH.exists():
        return {}, None, None, ("data/observations.sqlite missing -- " + RUN_REFRESH_ACTION), {}
    try:
        import readout as readout_mod
        import live_water_level as lwl_mod
    except Exception as e:  # pragma: no cover - defensive
        return {}, None, None, f"readout/live_water_level module unavailable: {e}", {}
    today_local = readout_mod._local_date(now_utc.isoformat())
    if today_local is None:  # pragma: no cover - defensive, now_utc is always well-formed
        return {}, None, None, "could not compute local date for now_utc", {}
    tomorrow_local = (
        datetime.date.fromisoformat(today_local) + datetime.timedelta(days=1)
    ).isoformat()
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows = conn.execute(
            """SELECT station_code, observed_at_utc, fetched_at_utc, value, source_id
               FROM observations
               WHERE source_id IN ('openmeteo_forecast16d', 'metno_locationforecast')
               AND station_code LIKE ? AND variable = 'precipitation_forecast_daily_mm'
               ORDER BY observed_at_utc""",
            (f"{point_id}:%",),
        ).fetchall()
    except sqlite3.Error as e:  # pragma: no cover - defensive
        return {}, None, None, f"could not read observations.sqlite: {e}", {}
    if not rows:
        return {}, None, None, None, {}

    now_iso = now_utc.isoformat()
    by_model: dict = {}
    issued_at_by_model: dict = {}
    for station_code, observed_at_utc, fetched_at_utc, value, source_id in rows:
        if value is None:
            continue
        local_date = readout_mod._local_date(observed_at_utc)
        if local_date is None or local_date < tomorrow_local:
            continue  # past (local) or unparseable -- never labelled "tomorrow"
        # FIX (2026-10-04): per-row freshness gate, per-source cutoff -- a stale row is
        # dropped here, before it can enter `by_model` at all (never averaged in, never
        # used to pad a model's date range past what its real refresh covers).
        try:
            max_age_h = lwl_mod.max_age_hours_for(source_id)
            fresh, _age_h = lwl_mod.is_fresh(fetched_at_utc, now_iso, max_age_h)
        except Exception:  # pragma: no cover - defensive, a bad timestamp must not crash
            fresh = False
        if not fresh:
            continue
        model = station_code.split(":", 1)[1]
        by_model.setdefault(model, {})[local_date] = float(value)
        prev = issued_at_by_model.get(model)
        if fetched_at_utc and (prev is None or fetched_at_utc > prev):
            issued_at_by_model[model] = fetched_at_utc

    # A model can end up with no fresh row inside the future-local-date window even
    # though it had rows at all (e.g. only past-dated rows survived the fresh gate) --
    # `by_model.setdefault` above only ever creates an entry when at least one fresh,
    # future-dated row exists, so no extra "drop empty models" pass is needed here.

    issued_at = max(issued_at_by_model.values(), default=None)
    # FIX (2026-10-04): point-level `stale` is True only when NO fresh model is left at
    # all (`by_model` empty) -- never derived from a pooled issued_at that could hide one
    # model's staleness behind another model's fresh refresh (see docstring above).
    stale = not by_model
    return by_model, issued_at, stale, None, issued_at_by_model


def _refresh_forecast_sources(point_id: str, lat: float, lon: float) -> list[dict]:
    """this fix (2026-10-04): `kb.py forecast` used to be read-only (needing a prior
    `collect.py --all`, which fetches the FULL wired-source sweep -- wasteful and
    unexplained for a command that only ever reads 2 sources), unlike `answer`'s
    refresh-by-default. Fetches ONLY the two forecast sources
    (`collect.POINT_FILTERABLE_SOURCES`'s openmeteo/metno pair), scoped to THIS one
    point via `points_by_source` -- one GET per source, no retries, same discipline as
    `_refresh_relevant_sources`."""
    import collect as collect_mod
    source_ids = ["openmeteo_forecast16d", "metno_locationforecast"]
    one_point = {point_id: (lat, lon)}
    points_by_source = {sid: one_point for sid in collect_mod.POINT_FILTERABLE_SOURCES
                         if sid in source_ids}
    results = collect_mod.run(source_ids, dry_run=False, points_by_source=points_by_source)
    return [{"id": r.source_id, "ok": r.ok, "skipped": r.skipped, "note": r.note}
            for r in results]


def cmd_forecast(args) -> int:
    """`kb.py forecast --at lat,lon` -- resolve the nearest cached forecast point (or,
    if `--at` names one of collect.FORECAST7D_POINTS directly, use that point's own
    coords), then print each model's own tomorrow (24h) + 7-day total from
    data/observations.sqlite (source_id openmeteo_forecast16d/metno_locationforecast),
    named never averaged. Sub-basin resolution is via tools/kg/unit_resolver.resolve_unit
    -- read-only, no live fetch for THAT lookup.

    this fix: refreshes the two forecast sources for this point BEFORE reading them,
    by default (same `answer` convention) -- `--offline` opts out and keeps this
    read-only against whatever `data/observations.sqlite` already has (a fresh clone
    with no DB and `--offline` still reports "run collect.py --all first", since there
    is nothing to refresh into)."""
    sys.path.insert(0, str(HERE))
    at = args.at.strip()
    if at in _FORECAST_KNOWN_POINTS:
        lat, lon = _FORECAST_KNOWN_POINTS[at]
    else:
        try:
            lat_s, lon_s = at.split(",")
            lat, lon = float(lat_s), float(lon_s)
        except ValueError:
            print(f"ERROR: --at must be 'lat,lon' or one of {sorted(_FORECAST_KNOWN_POINTS)}",
                  file=sys.stderr)
            return 2
    # fix (2026-10-04): snapping to the nearest declared point used to
    # have no distance cap -- a far-away request silently borrowed, and could overwrite,
    # a named point's own forecast cache. Beyond _FORECAST_POINT_SNAP_RADIUS_KM this now
    # gets its own coordinate-derived point_id instead (see _resolve_forecast_point).
    point_id, within_range = _resolve_forecast_point(at, lat, lon)

    try:
        from tools.kg.unit_resolver import resolve_unit
        unit = resolve_unit(lat, lon)
    except Exception as e:  # pragma: no cover - defensive, unit resolution is a bonus line
        unit = {"sb_code": None, "reason": f"resolver unavailable: {e}", "tag": "OPEN"}

    print(f"จุด: {point_id} ({lat},{lon})"
          + (f" | เนียร์เรสต์จากที่ขอ" if at not in _FORECAST_KNOWN_POINTS else ""))
    if not within_range:
        print(f"ไม่มีจุดพยากรณ์ที่ประกาศไว้ในระยะ {_FORECAST_POINT_SNAP_RADIUS_KM:g} กม. -- "
              "ใช้พิกัดนี้เป็นจุดใหม่ของตัวเอง ไม่ยืมค่าของจุดอื่น (เริ่มต้นว่างเปล่าจนกว่าจะ refresh)")
    # this fix: refresh-by-default (same convention as `kb.py answer`) -- `--offline`
    # opts out. Runs even when `data/observations.sqlite` doesn't exist yet (that is
    # exactly the fresh-clone case this fix targets): `collect_mod.run` creates it.
    if not getattr(args, "offline", False):
        refresh_report = _refresh_forecast_sources(point_id, lat, lon)
        n_skipped = sum(1 for r in refresh_report if r["skipped"])
        n_fail = sum(1 for r in refresh_report if not r["ok"] and not r["skipped"])
        n_ok = len(refresh_report) - n_skipped - n_fail
        print(f"--refresh (ค่าเริ่มต้น): {len(refresh_report)} แหล่ง -- {n_ok} ok, "
              f"{n_skipped} skipped, {n_fail} ล้มเหลว (ใช้ --offline เพื่อข้าม)")
    if unit.get("sb_code"):
        print(f"อยู่ในลุ่มน้ำย่อย: {unit.get('name_th')} ({unit['sb_code']}) "
              f"[{unit.get('tag')}]")
    else:
        print(f"ลุ่มน้ำย่อย: ยังไม่ทราบ ({unit.get('reason')}) [{unit.get('tag', 'OPEN')}]")

    if not DB_PATH.exists() and getattr(args, "offline", False):
        # Refresh is the default (see below); this message only shows for a fresh
        # clone that explicitly opted OUT of it with --offline, so the fix is to drop
        # that flag, not to run the internal `collect.py` script by hand.
        print("ยังไม่มี data/observations.sqlite ในระบบนี้ -- ลองรันใหม่โดยไม่ใส่ `--offline` "
              f"(`floodconnect forecast --at {at}`)")
        return 0
    by_model, issued_at, stale, err, _issued_at_by_model = _forecast_rows_by_model(point_id)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    if not by_model:
        print(f"ยังไม่มีข้อมูลพยากรณ์ 'ในอนาคต' สำหรับจุดนี้ ({point_id}) -- ไม่เคยเก็บเลย "
              "หรือทุกแถวที่มีเป็นวันที่ผ่านไปแล้ว (เทียบเวลาท้องถิ่น กทม.) -- "
              "ลองรันใหม่โดยไม่ใส่ `--offline` (ต้องมี point นี้ใน collect.FORECAST7D_POINTS "
              "หรือพิกัดของคุณเอง)")
        return 0
    if issued_at:
        stale_note = "  [ข้อมูลค้างนาน/stale]" if stale else ""
        print(f"ดึงข้อมูลพยากรณ์ล่าสุดเมื่อ (issued_at, UTC): {issued_at}{stale_note}")
    print(f"\nรายโมเดล ({len(by_model)} โมเดล), พรุ่งนี้ (วันท้องถิ่นถัดไป) + รวม 7 วัน:")
    for model, by_date in sorted(by_model.items()):
        dates = sorted(by_date)
        tomorrow = dates[0]
        total7 = sum(by_date[d] for d in dates[:7])
        label = _FORECAST_MODEL_LABEL_TH.get(model, model)
        tmr_mm = f"{by_date[tomorrow]:.0f} มม."
        print(f"  {label}: พรุ่งนี้ {tmr_mm} · รวม {min(len(dates), 7)} วัน {total7:.0f} มม.")
    return 0


# ---------------------------------------------------------------------------
# answer / compute (added 2026-10-02) -- the minimal AI entrypoint's compute CLI.
# Design: AI.md + this subcommand are the single validated entry for "what's the state here
# and what can I do", replacing any hand-rolled route/forecast logic a caller might otherwise
# improvise. Every sub-answer below REUSES an existing module's function -- none are
# re-derived here (readout.build_readout, accountability.build_result,
# community_dag.find_safe_route, the same DB query cmd_forecast already runs). No new
# equation is introduced, so Toledo-first registration does not apply to this subcommand's
# own code; where a sub-answer's SOURCE module is itself PROPOSAL-tier in the RKG, that is
# surfaced in source_tags as "not yet in Toledo" (H10) rather than silently promoted.
#
# Health status is derived ONLY from the real fetch already recorded in
# data/observations.sqlite (staleness age vs each source's own cutoff) -- there is
# deliberately no separate pre-use probe call here (design M1 fix): adding one would double
# every live upstream fetch and break the one-GET-per-run host rule for rate-limited sources
# (dds.bangkok.go.th / weather.bangkok.go.th). A standalone `kb.py healthcheck` subcommand is
# explicitly OUT of this subcommand's scope -- see AI.md for that gap.
# ---------------------------------------------------------------------------

_ANSWER_AREAS = {
    "sammakorn": {"lat": 13.758235, "lon": 100.676084, "self_help_start": "sammakorn_household_template"},
    "ram53": {"lat": 13.765540125000635, "lon": 100.61909460837903, "self_help_start": "ram53_household_template"},
}

SELF_HELP_DAG_PATH = HERE / "site" / "inputs" / "community" / "self_help_dag.yaml"
REPO_KG_PATH = HERE / "site" / "inputs" / "meta" / "floodconnect_repo_kg.yaml"

# RKG node id -> epistemic_class, read lazily (PyYAML) so kb.py's non-answer commands keep
# their stdlib-only guarantee (module docstring) -- only `answer`/`compute` touches YAML.
_RKG_NODE_FOR_FIELD = {
    "state": "LIVE_DATA_SYSTEM",       # readout.py / live_water_level.py -- epistemic_class LIVE_OBSERVATION
    "next_action": "COMMUNITY_DAG",    # community_dag.py -- epistemic_class POLICY_SCHEMA
}


def _rkg_epistemic_class(node_id: str) -> str | None:
    if not REPO_KG_PATH.exists():
        return None
    try:
        import yaml
    except ImportError:  # pragma: no cover - defensive
        return None
    try:
        doc = yaml.safe_load(_read_text(REPO_KG_PATH)) or {}
    except Exception:  # pragma: no cover - defensive, malformed RKG must not crash `answer`
        return None
    node = (doc.get("nodes") or {}).get(node_id) or {}
    return node.get("epistemic_class")


# Fix (2026-10-04): a bare 'lat,lon' far outside Thailand (e.g. a typo,
# or 999,999) must never fall through to `_answer_state`/`build_readout` and pick up
# city-wide DDS bulletin rows as if they were "near" that point -- see
# `_reject_outside_thailand` below, called once from `build_answer`. Generous box (not a
# precise border), only to catch clearly-wrong input -- never used as a precision check.
THAILAND_BBOX = {"lat_min": 5.0, "lat_max": 21.0, "lon_min": 97.0, "lon_max": 106.0}


def _outside_thailand(lat: float, lon: float) -> bool:
    return not (THAILAND_BBOX["lat_min"] <= lat <= THAILAND_BBOX["lat_max"]
                and THAILAND_BBOX["lon_min"] <= lon <= THAILAND_BBOX["lon_max"])


class _BadAt(ValueError):
    """Raised by `_resolve_area` for a `--at` value that is neither a known area_id nor a
    parseable 'lat,lon' pair (this used to be an
    unhandled ValueError/traceback straight out of `at.split(",")`)."""


def _resolve_area(at: str) -> tuple[str | None, float, float]:
    """'<area_id>' | 'lat,lon' -> (area_id or None, lat, lon). Unknown area ids are an
    ERROR (caller mistyped), but a bare 'lat,lon' with no matching declared area is legal
    -- `next_action` then reports OPEN rather than guessing a self-help DAG start node.
    Raises `_BadAt` (never a raw ValueError/traceback) for anything else, mirroring
    `cmd_forecast`'s own `--at` error handling."""
    at = at.strip()
    if at in _ANSWER_AREAS:
        a = _ANSWER_AREAS[at]
        return at, a["lat"], a["lon"]
    try:
        lat_s, lon_s = at.split(",")
        return None, float(lat_s), float(lon_s)
    except ValueError as e:
        raise _BadAt(
            f"--at must be 'lat,lon' or one of {sorted(_ANSWER_AREAS)}") from e


RUN_REFRESH_ACTION = (
    "run 'floodconnect answer --at <area>' (refresh is the default; do not pass "
    "'--offline') -- every number is computed locally, on your own network, from "
    "your own refresh."
)


_TOP_N_SOURCES_IN_SUMMARY = 3

# Fix (2026-10-03): `_answer_state`'s `evidence` list, uncapped, measured
# ~800+ tokens on a real populated DB (12 drainage rows, each with a Thai station name
# + full ISO timestamp + long float age_h) -- enough on its own to push the default
# (non-verbose) answer over `tests/test_token_budget.py`'s ceiling. `verbose=False`
# keeps at most this many DECIDING rows and this many NOT-used (stale) rows, each
# trimmed to {station, status, age_h (rounded), used_for_decision} -- a representative
# SAMPLE, never a claim of completeness (the exact counts are already in
# `status_counts`/`status_counts_stale`/`stale_count`, which stay uncapped). `verbose
# =True` returns every row with every field, uncapped, same as `notes`.
_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY = 1
_TOP_N_EVIDENCE_STALE_IN_SUMMARY = 0


def _trim_evidence(evidence: list[dict]) -> list[dict]:
    """Non-verbose `evidence`: a small, clearly-partial sample -- see
    `_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY`'s own comment for why this exists and what it
    deliberately drops (unit/source/full observed_at_utc; age_h rounded to 1 decimal).

    FIX (2026-10-04, F-evidence-priority): before this fix, the capped `deciding` sample
    took the first `_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY` decision-driving
    (`used_for_decision=True`) rows in whatever order `full["factors"]["4_การระบาย"]
    ["measured"]` happened to list them -- so a real flood-like/critical reading among
    the decision-driving rows could be silently hidden behind an earlier NORMAL row, with
    the capped summary showing only the unremarkable one. Decision-driving rows are now
    sorted so a flood-like status (the SAME set `_classify_current_local_state` checks,
    via `_flood_like_normal_like_status_words` -- never a second copy of that set) is
    listed first, before the cap trims the list; a caller reading only the capped
    `evidence` sample therefore sees the most alarming decision-driving reading first,
    never a masked one, while `status_counts`/`_classify_current_local_state` (the actual
    GREEN/YELLOW/RED decision) are completely unaffected -- this only changes WHICH rows
    a capped sample shows, never what decided the colour.

    How many STALE (`used_for_decision=False`) rows exist beyond
    `_TOP_N_EVIDENCE_STALE_IN_SUMMARY` is NOT re-stated in this trimmed list itself (it
    would cost real tokens on every JSON answer for a number already available for
    free) -- `_answer_state`'s own `stale_count` (uncapped, computed before this
    function ever runs) already reports it, and `cmd_answer`'s text printer reads that
    same field for its one-line count, never a second copy kept here."""
    flood_like, _normal_like, _critical_like = _flood_like_normal_like_status_words()
    deciding_all = [e for e in evidence if e.get("used_for_decision")]
    deciding_sorted = sorted(
        deciding_all, key=lambda e: 0 if e.get("status") in flood_like else 1)
    deciding = deciding_sorted[:_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY]
    stale = [e for e in evidence if not e.get("used_for_decision")][
        :_TOP_N_EVIDENCE_STALE_IN_SUMMARY]
    out = []
    for e in deciding + stale:
        age_h = e.get("age_h")
        out.append({
            "station": e.get("station"),
            "status": e.get("status"),
            "age_h": round(age_h, 1) if isinstance(age_h, (int, float)) else age_h,
            "used_for_decision": e.get("used_for_decision"),
            "stale": e.get("stale", e.get("used_for_decision") is False),
        })
    return out


def _source_relevance_counts(full: dict) -> dict[str, int]:
    """Counts how many rows in THIS specific area/round's `build_readout` output came
    from each `source_id` (every factor's `measured` + `official_forecast` rows) --
    used only to rank which sources are worth naming in a capped summary, never to
    decide a status or a tag. More rows for this point/radius this check = more
    relevant to THIS answer, not a claim about the source's general importance."""
    counts: dict[str, int] = {}
    for factor in full.get("factors", {}).values():
        for row in list(factor.get("measured", [])) + list(factor.get("official_forecast", [])):
            src = row.get("source")
            if src:
                counts[src] = counts.get(src, 0) + 1
    return counts


def _sources_summary_note(sources_used: list, relevance: dict[str, int]) -> str:
    """The previous version of this function (`_cap_sources_note`)
    capped `readout.py`'s own overall_picture sentence by SEARCHING ITS TEXT for a Thai
    marker string ("แหล่งในรอบนี้: ") and the next ". " -- a silent-failure mode an audit
    exists: if that wording ever changes in `readout.py`, the
    search misses, the cap silently stops firing, and the token budget overflows again with
    NO test failing. This version never reads that note's text at all -- it builds its own
    compact line directly from `build_readout`'s structured `header.sources_used` list (the
    same list `_answer_state` already reads to decide the offline/0-sources fallback), so a
    wording change in `readout.py`'s own note can never break this cap.

    Returns a short line naming every source when there are `_TOP_N_SOURCES_IN_SUMMARY` or
    fewer (no cap needed -- this is the common fresh/small-DB case, where the full list is
    already short), or the top-N by this answer's relevance (`_source_relevance_counts`) plus
    a `--verbose`/`verbose=true` pointer and a count of how many were left out, when there
    are more."""
    names = [s for s in sources_used if s]
    if not names:
        return "ใช้ข้อมูลจาก 0 แหล่งในรอบนี้: (none in store yet)."
    if len(names) <= _TOP_N_SOURCES_IN_SUMMARY:
        return f"ใช้ข้อมูลจาก {len(names)} แหล่งในรอบนี้: {', '.join(names)}."
    ranked = sorted(names, key=lambda n: relevance.get(n, 0), reverse=True)
    top = ranked[:_TOP_N_SOURCES_IN_SUMMARY]
    remaining = len(names) - len(top)
    return (f"ใช้ข้อมูลจาก {len(names)} แหล่งในรอบนี้ (top {len(top)} relevant): "
            f"{', '.join(top)} (+{remaining} more; see --verbose).")


def _answer_state(lat: float, lon: float, radius_km: float = 3.0,
                   as_of_date: str | None = None, verbose: bool = False) -> dict:
    """Current local state -- reuses readout.build_readout (LIVE_DATA_SYSTEM), never
    re-derives its station/canal/pump logic. Returns a COMPACT summary (overall_picture's
    own INSTINCT notes + a status-count line) rather than the full readout object, per the
    design's token-budget fix (H5): the full object was measured elsewhere at ~2,790 tokens
    on its own.

    `as_of_date` is exposed only so tests can pin the staleness reference to a fixed date
    (mirrors `_answer_hazard`'s own `now_utc` parameter) -- production callers leave it
    unset (real `now`), unchanged from before this function grew the parameter.

    `verbose=False` (the default) replaces `overall_picture`'s three Thai sentence notes
    (status counts, STALE count, contradiction count) with the structured fields below
    (`status_counts`, `status_counts_all`, `stale_count`, `contradiction_count`) -- no
    information is dropped, it is only carried as fields instead of prose, which is what
    keeps the token budget under its ceiling on a populated DB (see
    `tests/test_token_budget.py`). The one remaining note is the sources-used line, built
    by `_sources_summary_note` from the top `_TOP_N_SOURCES_IN_SUMMARY` (3) sources by this
    answer's relevance. `verbose=True` returns `notes` unmodified (every sentence,
    uncapped), for a caller that explicitly wants the full prose and accepts the extra
    tokens.

    Also returns `status_counts` -- a plain count, per each fresh
    (non-STALE) row in the drainage factor, of the STATUS WORD the owning agency already
    published for that row (readout.py's own per-row `status` field, e.g. "CRITICAL",
    "NORMAL", "ขัดข้อง") -- no new field is computed from the DB here, this is the exact
    same table `cmd_answer`'s printed footer already summarizes in prose
    (`overall_picture.notes[0]`), just handed back structured so `_answer_next_action` can
    classify `current_local_state` without re-querying the DB or inventing a number.

    Also returns `status_counts_all` (the same per-status
    count, but over EVERY row including STALE ones -- what the dropped notes[0] sentence
    used to say in prose) and `stale_count` (how many drainage rows this check are STALE
    -- what the dropped notes[1] sentence used to say). STALE is still never read as
    evidence of the current state (`status_counts`, used by `_classify_current_local_state`,
    stays fresh-only, unchanged) -- these two new fields only expose the same STALE rows'
    existence and their agency-published status words as numbers, for a caller/human who
    wants the full picture without the prose.

    CAUTION (this, 2026-10-03): `status_counts_all` mixes fresh and STALE rows'
    status words into ONE count with no per-row marker -- a caller reading only this
    field cannot tell a `status_counts_all["CRITICAL"]=1` apart as fresh-and-decided
    vs. STALE-and-not-used (the founder's own exact complaint: an AI reporting a stale
    station's CRITICAL word as if it were current). Kept for backward compatibility with
    existing callers/tests, but a caller that cares about this distinction should read
    `status_counts_stale` (STALE rows only, added below) and/or `evidence` (added below:
    one row per drainage reading with `used_for_decision`), never `status_counts_all`
    alone. `status_counts_stale` is the exact per-status breakdown of the STALE rows
    `status_counts_all` folds in anonymously -- `status_counts_all[k] -
    status_counts.get(k, 0) == status_counts_stale.get(k, 0)` for every status word `k`.

    `evidence` (added): one compact dict per drainage row in this check --
    `{station, value, status, observed_at_utc, age_h, used_for_decision}` --
    `used_for_decision=True` only for the fresh rows `status_counts`/
    `_classify_current_local_state` actually read; every STALE row is still listed, with
    `used_for_decision=False`, so a caller can show/relay EVERY value it has while being
    unable to accidentally claim a stale one decided the colour. `verbose=True` returns
    EVERY row, every field, uncapped. `verbose=False` (the default) returns a SAMPLE
    instead -- at most `_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY` deciding rows plus
    `_TOP_N_EVIDENCE_STALE_IN_SUMMARY` stale ones, each trimmed to
    `{station, status, age_h, used_for_decision}` -- never a claim of completeness
    (`evidence_total_count` always reports the real total; `status_counts`/
    `status_counts_stale` stay the exhaustive, uncapped accounting either way). This
    exists because the full uncapped list alone measured ~800+ tokens on a real
    populated DB -- see `_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY`'s own comment."""
    if not DB_PATH.exists():
        # FIX D (2026-10-04, project decision): this repo ships NO hosted/precomputed
        # reading for anyone to read without computing it themselves -- the previous
        # tracked `site/dist/api/v1/areas/*.json` snapshot fallback is removed. A
        # missing local DB is always an honest UNKNOWN with a refresh action, never a
        # retained figure from some earlier capture.
        return {"tag": "OPEN", "note": "data/observations.sqlite missing -- " + RUN_REFRESH_ACTION,
                "refresh_suggested": True, "next_action": RUN_REFRESH_ACTION}
    try:
        import readout as readout_mod
        import store as store_mod
    except Exception as e:  # pragma: no cover - defensive
        return {"tag": "OPEN", "note": f"readout/store module unavailable: {e}"}
    try:
        # store.connect() (not a bare sqlite3.connect) -- build_readout's row access
        # (row["ts"]) requires sqlite3.Row, which only store.connect() sets.
        conn = store_mod.connect(DB_PATH)
        full = readout_mod.build_readout(conn, lat, lon, radius_km, as_of_date=as_of_date)
    except Exception as e:  # pragma: no cover - defensive, a bad row must not crash `answer`
        return {"tag": "OPEN", "note": f"build_readout failed: {e}"}
    # The DB existing is not the same as the DB having any
    # rows for THIS area/radius -- a `--refresh` that fetched nothing (e.g. offline, every
    # source skipped/failed) leaves `data/observations.sqlite` present but empty, and the
    # previous version never looked at the tracked snapshot again once the file existed,
    # so a failed refresh made the answer WORSE than before the refresh (bare "0 sources"
    # INSTINCT instead of the retained snapshot). Falls back to the exact same offline
    # snapshot path `_answer_state` already used for "file missing", keyed on there being
    # zero sources this check rather than on file existence.
    sources_used = (full.get("header") or {}).get("sources_used") or []
    if not sources_used:
        # No real data at all (zero sources this area/radius) -- an INSTINCT tag
        # here would claim a judgment call was made over data that does not exist.
        # OPEN, never a confident-looking label with nothing behind it, and never a
        # retained snapshot value (FIX D, 2026-10-04 project decision: no hosted/
        # precomputed reading is shipped for anyone to read without their own refresh).
        return {"tag": "OPEN", "note": "0 sources in data/observations.sqlite for this "
                "area/radius this check -- " + RUN_REFRESH_ACTION,
                "refresh_suggested": True, "next_action": RUN_REFRESH_ACTION}
    overall = full.get("overall_picture", {})
    status_counts: dict[str, int] = {}
    status_counts_all: dict[str, int] = {}
    status_counts_stale: dict[str, int] = {}
    evidence: list[dict] = []
    stale_count = 0
    for row in full.get("factors", {}).get("4_การระบาย", {}).get("measured", []):
        st = row.get("status") or "UNKNOWN"
        status_counts_all[st] = status_counts_all.get(st, 0) + 1
        is_stale = row.get("tag") == "STALE"
        # fix: a dds_daily_pdf row carries its own `used_for_decision` (set by
        # readout.build_readout, scoped to whether its station name matched a
        # geolocated station within the radius -- see readout.py's factor-4 dds_canal
        # loop). A row from a geolocated source (thaiwater_canal_waterlevel,
        # bma_pumphistory) has no such field -- it was already radius-filtered by
        # `store.query_observations(near=...)` before it ever reached `measured`, so it
        # defaults to "decide iff fresh", unchanged.
        used = row.get("used_for_decision")
        decides = (not is_stale) if used is None else bool(used)
        evidence.append({
            "station": row.get("station"),
            "value": row.get("value"),
            "unit": row.get("unit"),
            "status": st,
            "source": row.get("source"),
            "observed_at_utc": row.get("observed_at_utc"),
            "age_h": row.get("age_h"),
            "scope_note": row.get("scope_note"),
            "used_for_decision": decides,
            # fix (2026-10-04): explicit, structured flag for WHY a row
            # isn't used -- a `used_for_decision=False` row can be excluded either
            # because it's genuinely too old (`stale=True`) OR because it's fresh but
            # geo-excluded (canal_outer / no coordinate / outside radius, `stale=
            # False`). Before this field existed, both cases were folded into a single
            # "too old" label downstream (`cmd_answer`'s printer) -- MEASURED: 10 fresh
            # (4.8h old) geo-excluded DDS rows were printed under "ค่าที่มีแต่เก่าเกินเกณฑ์"
            # ("values that exist but are too old"), which is simply false for a fresh
            # row.
            "stale": is_stale,
        })
        if is_stale:
            stale_count += 1
            status_counts_stale[st] = status_counts_stale.get(st, 0) + 1
        if not decides:
            continue  # a stale OR not-locally-matched row's status word is not
                       # evidence of the CURRENT state at this point. `status_counts_stale`
                       # intentionally stays AGE-based only (unchanged meaning) -- a
                       # not-locally-matched-but-fresh row is still visible via
                       # `status_counts_all`/`evidence`'s own `scope_note`, it just isn't
                       # double-counted into the "stale" bucket for a reason that isn't
                       # staleness.
        status_counts[st] = status_counts.get(st, 0) + 1
    if verbose:
        notes = overall.get("notes", [])
    else:
        # An earlier check fix: build the one remaining note straight from the structured
        # `sources_used` list (never by re-parsing readout.py's own note text -- see
        # `_sources_summary_note`'s docstring) instead of capping each of
        # `overall.notes` in place; the status/stale/contradiction sentences those notes
        # used to carry are now the structured fields below instead.
        relevance = _source_relevance_counts(full)
        notes = [_sources_summary_note(sources_used, relevance)]
    # `refresh_suggested`: this check's DB is reachable, but no row currently decides
    # `status_counts` for this point. Two distinct causes both set this, since both are
    # fixed the same way (run --refresh / collect):
    #   (a) stale_count > 0 and status_counts empty -- every drainage row within range
    #       aged past STALE_HOURS before any fresh one could decide it (the exact
    #       "data has gone old" case `_classify_current_local_state` turns into
    #       UNKNOWN);
    #   (b) `evidence` itself is empty -- no drainage/water-level row at all exists
    #       within radius (fresh or stale), e.g. a point nothing has ever been
    #       collected for. v0.1.0 only checked (a); a point with ZERO rows in radius
    #       (stale_count==0, status_counts=={}) fell through with refresh_suggested
    #       left False, silently telling the caller nothing more could be done, when a
    #       refresh run could still fetch a station that covers this point.
    # A structured flag (never a notes-text search -- see `_answer_next_action`'s own
    # fix) so a caller/the entrypoint can surface "run --refresh" without re-deriving
    # this reasoning from prose. Unrelated to the fault-only-sensor UNKNOWN case (fresh
    # rows exist, they are just all faults): `status_counts` here still counts a
    # fault-row's own status word (e.g. "ขัดข้อง") as decided, so it is non-empty and
    # this condition stays False -- the fault-vs-UNKNOWN exclusion happens downstream
    # in `_classify_current_local_state`, not here.
    refresh_suggested = not status_counts and (stale_count > 0 or not evidence)
    return {
        "tag": overall.get("tag", "INSTINCT"),
        "notes": notes,
        "contradiction_count": len(full.get("contradictions", [])),
        "missing_count": len(full.get("missing", [])),
        "status_counts": status_counts,
        "status_counts_all": status_counts_all,
        "status_counts_stale": status_counts_stale,
        "evidence": evidence if verbose else _trim_evidence(evidence),
        "evidence_total_count": len(evidence),
        "stale_count": stale_count,
        "refresh_suggested": refresh_suggested,
    }


def _answer_hazard(
    at: str, lat: float, lon: float, now_utc: "datetime.datetime | None" = None,
) -> dict:
    """Forward hazard -- reuses `_forecast_rows_by_model` (the same table/source_ids/
    local-date filter `cmd_forecast` uses), returned as data instead of printed. These are
    third-party (Open-Meteo / MET Norway) model outputs RELAYED as-is: FloodConnect has
    not run its own skill/accuracy evaluation of them, and they are never averaged into
    one number (dual-state rule: this is forward_hazard, kept separate from `state`'s
    current_local_state). `now_utc` is exposed only so tests can pin the clock; production
    callers leave it unset (real `now`).

    Every date returned here is a Bangkok-LOCAL date
    at or after LOCAL tomorrow -- never a date that has already passed. `issued_at` +
    `stale` report when this point's forecast cache was last refreshed, so a caller can
    tell a fresh RELAYED reading from a stale one.

    fix (2026-10-04): a request more than
    `_FORECAST_POINT_SNAP_RADIUS_KM` from every known point is honest UNKNOWN here --
    never silently snapped to, and reported as, a different named place's hazard."""
    point_id, within_range = _resolve_forecast_point(at, lat, lon)
    if not within_range:
        return {"tag": "OPEN", "point_id": point_id, "stale": True,
                "note": f"({lat},{lon}) is more than {_FORECAST_POINT_SNAP_RADIUS_KM:g} km "
                        f"from every point FloodConnect forecasts for -- refusing to "
                        "borrow a different place's hazard; " + RUN_REFRESH_ACTION,
                "next_action": RUN_REFRESH_ACTION}
    # `issued_at_by_model` (per-model provenance) is available from
    # `_forecast_rows_by_model` but deliberately not echoed into the JSON payload below
    # -- it was measured to cost a real token-budget margin for little caller value
    # beyond the already-returned point-level `issued_at` (see
    # tests/test_token_budget.py); a caller that needs it calls
    # `_forecast_rows_by_model` directly.
    by_model, issued_at, stale, err, _issued_at_by_model = _forecast_rows_by_model(point_id, now_utc)
    if err or not by_model:
        # FIX D (2026-10-04, project decision): no cached forecast rows is an honest
        # UNKNOWN with a refresh action -- never a tracked/retained hazard snapshot
        # ("ship no hosted/precomputed reading; the installer computes it themselves").
        if err:
            return {"tag": "OPEN", "point_id": point_id, "stale": True,
                    "note": err, "next_action": RUN_REFRESH_ACTION}
        return {"tag": "OPEN", "point_id": point_id, "stale": True,
                "note": "no cached forecast rows for a future local date -- either nothing "
                        "collected yet for this point, or every cached row's local date "
                        "has already passed -- " + RUN_REFRESH_ACTION,
                "next_action": RUN_REFRESH_ACTION}
    per_model = []
    for model, by_date in sorted(by_model.items()):
        dates = sorted(by_date)
        tomorrow = dates[0]
        window_dates = dates[:7]
        total7 = sum(by_date[d] for d in window_dates)
        per_model.append({
            "model": _FORECAST_MODEL_LABEL_TH.get(model, model),
            "tomorrow_mm": round(by_date[tomorrow], 1),
            "7day_total_mm": round(total7, 1),
            # The real number of distinct future-dated rows this model actually has
            # cached, up to the 7-day cap -- same convention as `cmd_forecast`'s own
            # `min(len(dates), 7)` print (kb.py, "รวม {n} วัน"). `7day_total_mm`'s own
            # key name is kept for backward compatibility with existing callers, but a
            # model with e.g. only 4 cached dates must never be printed as "7 วัน".
            "total_days": len(window_dates),
        })
    return {"tag": "RELAYED", "point_id": point_id, "issued_at": issued_at,
            "stale": bool(stale), "per_model": per_model}


# ---------------------------------------------------------------------------
# F8 (2026-10-04) -- nearest CCTV cameras, VISUAL-CHECK only, NEVER a decision input.
# The hii_analyst_cctv catalog (collect.collect_hii_analyst_cctv) stores one DOCUMENT
# per camera (`store.insert_document`, section="cctv_station"), not an observation row
# -- no numeric reading, just coords + a feed URL, each line formatted
# "{station_id} | {title} | {agency_en} | {province_th} | {lat},{lon} | {cctv_url}".
# This is read-only parsing of that exact string; the write side (collect.py) is out of
# this worker's scope (kb.py/tools/mcp/floodconnect_mcp.py + tests only) and unchanged.
# ---------------------------------------------------------------------------

_CCTV_SOURCE_ID = "hii_analyst_cctv"
_CCTV_SECTION = "cctv_station"
DEFAULT_CCTV_RADIUS_KM = 3.0
_MAX_CCTV_RESULTS = 3


def _parse_cctv_document_text(text: str) -> "dict | None":
    """Reverses `collect.collect_hii_analyst_cctv`'s own pipe-joined document text back
    into `{station_id, title, lat, lon, cctv_url}` -- never re-derives the catalog
    itself. Returns None (never raises, never guesses) for a line that doesn't split
    into exactly the 6 fields that collector writes, or whose `lat,lon` segment isn't
    two parseable floats -- a malformed/legacy row is silently skipped from the nearest-
    camera list, not fabricated into one."""
    parts = text.split(" | ")
    if len(parts) != 6:
        return None
    station_id, title, _agency_en, _province_th, latlon, cctv_url = parts
    try:
        lat_s, lon_s = latlon.split(",")
        lat, lon = float(lat_s), float(lon_s)
    except (ValueError, TypeError):
        return None
    return {"station_id": station_id, "title": title or station_id,
            "lat": lat, "lon": lon, "cctv_url": cctv_url or None}


def _nearest_cctv_cameras(
        lat: float, lon: float, radius_km: float = DEFAULT_CCTV_RADIUS_KM,
        limit: int = _MAX_CCTV_RESULTS) -> list[dict]:
    """Up to `limit` nearest CCTV cameras within `radius_km` of (lat, lon), from the
    hii_analyst_cctv catalog this repo's per-area `--refresh` now also fetches (see
    `collect._refresh_relevant_sources`'s own CCTV carve-out, added alongside this
    function). VISUAL-CHECK ONLY -- a human looking at a camera feed, never a reading
    any `state`/`hazard`/`next_action` classification reads (AI.md rule 5: no SAFE/
    evacuation claim from an unverified visual source).

    Reads ONLY the latest fetched batch for this source (`MAX(fetched_at_utc)`) -- the
    collector has no per-camera dedup across repeated refreshes (each run re-inserts
    every camera as a new document row), so reading every stored row would double-count
    the same camera across refresh runs instead of showing this check's real catalog.

    Returns `[]` (never raises) when `data/observations.sqlite` is missing, the source
    was never fetched, or no camera sits within `radius_km` -- an empty list is a
    legitimate "no camera near this point this check", never promoted into a decision
    signal of any kind."""
    if not DB_PATH.exists():
        return []
    try:
        from live_water_level import haversine_km
    except Exception:  # pragma: no cover - defensive
        return []
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        max_fetched = conn.execute(
            "SELECT MAX(fetched_at_utc) FROM documents WHERE source_id = ? AND section = ?",
            (_CCTV_SOURCE_ID, _CCTV_SECTION),
        ).fetchone()[0]
        if not max_fetched:
            return []
        rows = conn.execute(
            "SELECT text FROM documents WHERE source_id = ? AND section = ? "
            "AND fetched_at_utc = ?",
            (_CCTV_SOURCE_ID, _CCTV_SECTION, max_fetched),
        ).fetchall()
    except sqlite3.Error:  # pragma: no cover - defensive
        return []
    # fix (2026-10-04): MEASURED later -- the nearest
    # `hii_analyst_cctv` camera to either MVP area (Sammakorn, Ram53) is 12-18 km away,
    # so the old `dist_km <= radius_km` filter silently dropped every candidate and F8
    # showed zero cameras for both areas the catalog was built for. Never cap by
    # radius any more -- always return the `limit` NEAREST cameras (even if far),
    # each tagged `within_radius` so a caller still knows whether it is "near" in the
    # original `radius_km` sense; an empty list now means only "catalog has zero
    # parseable camera rows this run", never "none happened to be within N km".
    cameras = []
    for (text,) in rows:
        cam = _parse_cctv_document_text(text)
        if cam is None:
            continue
        dist_km = haversine_km(lat, lon, cam["lat"], cam["lon"])
        cameras.append({"name": cam["title"], "distance_km": round(dist_km, 2),
                         "url": cam["cctv_url"], "within_radius": dist_km <= radius_km})
    cameras.sort(key=lambda c: c["distance_km"])
    return cameras[:limit]


def _answer_cctv(lat: float, lon: float, radius_km: float = DEFAULT_CCTV_RADIUS_KM) -> dict:
    """The `cctv` answer field -- always `kind: "VISUAL-CHECK"`. Deliberately NOT a
    `tag` key: `tag_vocabulary.TAG_VOCABULARY`/`tests/test_tag_vocabulary.py` enforce a
    repo-wide invariant that every dict key literally named `tag` holds one of the five
    floor tokens (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN) -- VISUAL-CHECK is
    deliberately NOT a sixth floor token (it is neither a decision-floor reading nor
    OPEN data, it is an explicit "look yourself, this is not a verdict" carve-out), so
    it is carried under a differently-named key instead of either breaking that
    invariant or being forced into a floor token it doesn't belong in. `cameras` is
    `[]` when none are in range -- never omitted/null on THIS function's own return, so
    a direct caller can tell "checked, none nearby" from "field missing". `build_answer`
    below only adds the top-level `cctv` key to its JSON envelope when `cameras` is
    non-empty (a real token-budget measurement: an always-present `{kind, radius_km,
    cameras: []}` wrapper on every single answer, even the common case with no camera
    in range, pushed `tests/test_token_budget.py`'s populated-DB case over its margin
    for a field that carries zero information in the empty case -- VISUAL-CHECK is
    explicitly never a decision input, so its absence is never mistaken for a decision
    the way a missing `state`/`hazard` would be)."""
    cameras = _nearest_cctv_cameras(lat, lon, radius_km=radius_km)
    return {"kind": "VISUAL-CHECK", "radius_km": radius_km, "cameras": cameras}


# fix support: the two MVP areas' known, already-registered governance DAG
# nodes (docs/knowledge/water_system_dag.mmd) -- NOT a new claim, every id/label here
# is copied verbatim from that file's own node declarations. `district` is the area's
# own district office (lowest-level, first point of contact); `citywide` is BMA's
# drainage authority (always accountable city-wide, regardless of district).
_ACCOUNTABILITY_FALLBACK = {
    "sammakorn": {
        "district": ("AG_DIST_SS", "ผอ.เขตสะพานสูง (ผู้ช่วยผู้อำนวยการ กทม.)"),
    },
    "ram53": {
        # Ram53/Ramkhamhaeng Soi 53 sits on the Bang Kapi/Wang Thonglang border --
        # `AG_DIST_NEIGH` is the governance DAG's own node for exactly this
        # neighbouring-district case ("สำนักงานเขตข้างเคียง (บางกะปิ/ประเวศ/ลาดกระบัง)"),
        # the closest already-registered node rather than inventing a new one.
        "district": ("AG_DIST_NEIGH", "สำนักงานเขตข้างเคียง (บางกะปิ/ประเวศ/ลาดกระบัง)"),
    },
}
_ACCOUNTABILITY_CITYWIDE = ("AG_DDS", "สนน. สำนักการระบายน้ำ + ศูนย์ควบคุมระบบป้องกันน้ำท่วม")


def _accountability_fallback(at: str, refused_text: "str | None" = None,
                              verbose: bool = True) -> "dict | None":
    """Returns a small, explicitly-labelled fallback accountability answer for the two
    MVP areas ONLY (`None` for any other area/bare lat,lon -- caller keeps the real
    OPEN refusal in that case). See `_ACCOUNTABILITY_FALLBACK`'s own comment for why
    this exists (`tools/kg/build_kg.py` currently produces zero geolocated
    `kind="asset"` nodes nationwide, so the real graph lookup refuses everywhere, not
    just outside these two areas). Tagged INSTINCT, never MEASURED/VERIFIED -- this is
    a judgment call reading the governance DAG's own district boundaries, not a
    radius-measured graph answer, and says so in `note`.

    `refused_text` scopes this fallback to the TWO real bugs it addresses -- "no asset
    node within <radius> km" (a graph that DOES exist but has no geolocated asset node
    nearby) AND a fresh clone with no graph file at all yet (`refused_text` naming the
    graph path as "not found or empty" -- `tools/kg/accountability.build_result`'s own
    other early-refusal wording). FIX C (2026-10-04): the missing-file case used to be
    excluded on purpose, which meant the one install path this public tree's own
    README/Quick start actually documents (clone, `pip install`, run `kb.py answer`,
    no `build_kg` step) got the bare OPEN refusal instead of this answer, for both MVP
    areas, every time. Both refused_text shapes name the SAME real gap (zero geolocated
    `kind="asset"` nodes for these two areas), so both fall back the same way; any OTHER
    refusal reason (an unresolvable `--at`, a module import failure) still returns
    `None` and keeps the caller's real OPEN refusal. `None` (caller didn't pass a
    reason) still falls back, for a direct/test caller that wants the fallback
    unconditionally."""
    if refused_text is not None and not (
            "no asset node within" in refused_text
            or "not found or empty" in refused_text):
        return None
    area_id, _lat, _lon = (at, None, None) if at in _ACCOUNTABILITY_FALLBACK else (None, None, None)
    if area_id is None:
        try:
            resolved_area_id, _lat, _lon = _resolve_area(at)
        except _BadAt:
            return None
        area_id = resolved_area_id
    entry = _ACCOUNTABILITY_FALLBACK.get(area_id or "")
    if entry is None:
        return None
    district_id, district_label = entry["district"]
    city_id, city_label = _ACCOUNTABILITY_CITYWIDE
    if verbose:
        note = (f"ไม่มี asset node ที่มีพิกัดในระยะ 3 กม. ในกราฟปัจจุบัน (ช่องว่างที่รู้แล้วของ "
                "tools/kg/build_kg.py, ไม่ใช่เฉพาะพื้นที่นี้) -- คำตอบนี้คือหน่วยงานตามเขต/"
                "สำนักที่ลงทะเบียนไว้แล้วใน docs/knowledge/water_system_dag.mmd "
                f"({district_label}; {city_label}), เป็น INSTINCT (การตัดสินตามเขตการปกครอง) "
                "ไม่ใช่คำตอบที่วัดจากกราฟ/รัศมีจริง")
        # Verbose keeps the internal registry ids too (audit/debug detail) -- the
        # compact default below drops them, see `owner_agencies` comment there.
        owner_agencies = [f"{district_label} ({district_id})", f"{city_label} ({city_id})"]
    else:
        # Token-budget trim (non-verbose default) -- the long "why this is a fallback"
        # prose is a `--verbose` detail, not something a default answer needs to repeat.
        note = "INSTINCT fallback (เขต/สำนักตามทะเบียน, ไม่ใช่ graph lookup) -- see --verbose"
        # FIX C (2026-10-04): a default-mode caller (person or AI) used to get the bare
        # internal registry ids ("AG_DIST_SS", "AG_DDS") here -- not actionable by
        # anyone who doesn't already know this repo's own node-id scheme. The compact
        # answer now carries the same human-readable Thai agency names the `--verbose`
        # note already names, with the ids dropped (the governance DAG
        # (docs/knowledge/water_system_dag.mmd) has no phone field for either node
        # today, so none is added here -- never invent one).
        owner_agencies = [district_label, city_label]
    return {
        "tag": "INSTINCT",
        "basis": "governance_dag_fallback",
        "owner_agencies": owner_agencies,
        "self_help_actions": [],
        "note": note,
    }


def _answer_accountability(at: str, verbose: bool = True) -> dict:
    """Who is responsible / overlapping authority / self-help options -- reuses
    tools.kg.accountability.build_result verbatim (no re-derivation). Compacted to the
    pieces an entrypoint caller needs; each Q-answer already carries its own
    VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN tag inline (not stripped, per the
    floodconnect-agent skill's provenance rule).

    `verbose` defaults to True (unchanged behaviour for every
    direct caller -- the test suite calls this function directly, with no `verbose`
    argument). Only `build_answer` passes its own `verbose` argument through explicitly.
    When `verbose=False`, each `self_help_actions` item keeps `text_th` (the action
    itself) and `cite` (its source -- provenance is never dropped) but loses `id` (an
    internal matching key, not something an entrypoint caller acts on) and `why_matched`
    (the longer audit/debug rationale, same trim `_answer_next_action` already applies
    to its own `why` field) -- this is part of what keeps the real populated-DB answer
    under the token budget."""
    try:
        sys.path.insert(0, str(HERE))
        from tools.kg import accountability
    except Exception as e:  # pragma: no cover - defensive
        return {"tag": "OPEN", "note": f"accountability module unavailable: {e}"}
    full = accountability.build_result(at)
    if "refused" in full:
        return _accountability_fallback(at, full["refused"], verbose=verbose) or {"tag": "OPEN", "refused": full["refused"]}
    # `build_result` has TWO distinct early-refusal
    # shapes, not one -- `resolve_point` failing returns the bare top-level key "Q1"
    # (accountability.py:590, `{"at": at, "Q1": point}`, point carrying "refused"), while
    # every other refusal uses the Thai-named "Q1_ใครรับผิดชอบที่นี่" key this function
    # already read below. Checking only the Thai key let a refused point slip through as
    # if it had answered, with `owner_agencies: []` looking like "no agency in range"
    # instead of "the point itself was refused". Check both.
    early_q1 = full.get("Q1")
    if isinstance(early_q1, dict) and "refused" in early_q1:
        return _accountability_fallback(at, early_q1["refused"], verbose=verbose) or {"tag": "OPEN", "refused": early_q1["refused"]}
    q1 = full.get("Q1_ใครรับผิดชอบที่นี่", {})
    if "refused" in q1:
        # fix (2026-10-04): MEASURED later -- on a fresh
        # clone, `python -m tools.kg.build_kg` produces a real graph with ZERO nodes
        # tagged `kind="asset"` carrying BOTH `lat` and `lon` anywhere nationwide (a
        # pre-existing gap in `tools/kg/build_kg.py`'s own asset-geolocation step, not
        # something this MVP pass can safely re-derive) -- `nearest_assets` therefore
        # always refuses, for every radius, everywhere, not just far from the two MVP
        # areas. `_accountability_fallback` below answers for ONLY the two MVP areas
        # (sammakorn/ram53), from the already-registered governance DAG nodes
        # (docs/knowledge/water_system_dag.mmd), tagged INSTINCT -- a judgment call
        # ("this district/citywide office is accountable here"), never claimed as a
        # radius-measured graph answer. Every other area/bare lat,lon still gets the
        # real OPEN refusal, unchanged.
        return _accountability_fallback(at, q1["refused"], verbose=verbose) or {"tag": "OPEN", "refused": q1["refused"]}
    owners = sorted({c.get("owns_edge", {}).get("agency_id")
                      for c in q1.get("chains", []) if c.get("owns_edge", {}).get("agency_id")})
    q2 = full.get("Q2_อำนาจซ้อนทับ/ต้องร่วมมือ", {})
    q3 = full.get("Q3_กฎหมายหรืออำนาจที่อาจมีปัญหา", {})
    q4 = full.get("Q4_ประชาชนทำอะไรได้เอง", {})
    self_help = q4.get("matched_actions", [])[:3]
    if not verbose:
        self_help = [{k: v for k, v in a.items() if k in ("text_th", "cite")}
                     for a in self_help]
    return {
        # "MEASURED-on-graph" was not one of the five
        # floor tokens (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN) -- use MEASURED, carry
        # the "on a graph, not a live instrument" distinction in a separate `basis` field
        # instead of inventing a sixth tag value.
        "tag": "MEASURED",
        "basis": "graph",
        "owner_agencies": owners,
        "overlap_note": q2.get("note") or q2.get("refused"),
        "law_problem_count": len(q3.get("problems", []) if isinstance(q3.get("problems"), list) else []),
        "self_help_actions": self_help,
    }


# ---------------------------------------------------------------------------
# "What to do next" -- closed
# vocabularies and a fixed hotline list only, never a new equation/threshold. Every
# classification below reuses a vocabulary or constant this repo already registered
# elsewhere; see each function's own docstring for the exact citation.
# ---------------------------------------------------------------------------

# Resident-facing hotline list -- the SAME four numbers+labels `cmd_answer`'s own printed
# footer already uses (below), kept as one constant so both places stay in sync. Labels
# match AI.md's rule-5 wording (1130 routes to MEA/electrical,
# never "DDPM flood").
HOTLINES = (
    {"number": "1669", "label_th": "เหตุฉุกเฉินทางการแพทย์ (สพฉ.)"},
    {"number": "1784", "label_th": "ภัยพิบัติ เกินกำลังพื้นที่ (ปภ.)"},
    {"number": "1555", "label_th": "สายด่วน กทม."},
    {"number": "1130", "label_th": "ไฟฟ้าช็อตจากน้ำท่วม (กฟน./MEA)"},
)

# The one allowed action when current state is UNKNOWN (floodconnect-agent skill rule 2,
# "UNKNOWN is never SAFE" -- AI.md's same rule). Never rephrase this into "ปลอดภัย"/"ปกติ".
# Contains none of the four banned resident-facing words (ไม่ต้อง/ห้าม/ไม่ควร/ผ่อนคลาย).
UNKNOWN_ACTION_TH = (
    "สถานีใกล้จุดนี้ไม่มีข้อมูลสดพอจะสรุปสถานะปัจจุบันในรอบนี้ (ไม่มีเลย หรือเก่ากว่าเกณฑ์ความสด "
    "24 ชม.) การไม่มีข้อมูลไม่ได้แปลว่าปลอดภัย ติดตามประกาศจากหน่วยงานทางการโดยตรง"
)

# The RED action used to ALWAYS render the L5
# survival card's life-safety headline ("น้ำเข้าบ้านแล้ว...") off a bare station-level
# FLOOD_LIKE_STATUS reading, by calling build_l5_survival_card_html({"tier": "L5"}) with a
# FAKED tier -- that headline literally claims water is already inside the resident's
# house, which a canal/pump station reading WATCH/CRITICAL never establishes. This neutral
# line is what `_answer_next_action` emits instead whenever current_local_state is RED but
# the REAL PROP-FLOOD-06 tier engine (tools/backtest/compute_prop_flood_06_sammakorn.py,
# the only place this repo actually computes an L5 tier) did not itself report L5 for this
# point this check. Contains none of the four banned resident-facing words.
STATION_RED_NEUTRAL_ACTION_TH = (
    "สถานีน้ำใกล้จุดนี้รายงานเกินเกณฑ์ปกติ (ระดับสถานีเท่านั้น ไม่ใช่ระดับ L5 ของ "
    "PROP-FLOOD-06) -- ติดตามต่อเนื่อง ดูผู้รับผิดชอบ/เบอร์ฉุกเฉินด้านล่าง"
)

_L5_HTML_LI_RE = re.compile(r"<li>(.*?)</li>", re.S)
_L5_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _l5_survival_steps_plain(build_page_mod) -> list[str]:
    """The RED
    action used to show ONLY `L5_SURVIVAL_HEADLINE_TH` ("...ทำตามนี้" / "...follow these
    steps") with no steps following it at all -- `build_l5_survival_card_html` builds the
    real step list but `_answer_next_action` below discarded it. This strips the tags off
    `build_page._l5_survival_lines_html()`'s OWN already-reviewed numbered-list HTML (the
    exact text the public page itself renders, never a second, separately-maintained
    copy) into one plain string per step, for the JSON `answer` surface which has no HTML
    renderer. Returns [] (never raises) if build_page's function is missing/changes
    shape -- callers must treat an empty list as "no steps available", never silently
    print the bare headline as if steps followed."""
    try:
        html = build_page_mod._l5_survival_lines_html()
    except Exception:  # pragma: no cover - defensive, a bad import must not crash answer
        return []
    items = _L5_HTML_LI_RE.findall(html)
    return [_L5_HTML_TAG_RE.sub("", item).strip() for item in items]


def _flood_like_normal_like_status_words() -> "tuple[set, set, set]":
    """Shared by `_classify_current_local_state` and `_trim_evidence` -- the ONE place
    that builds the closed flood-like/normal-like/critical-like status-word sets, so a
    capped evidence summary can prioritise the SAME statuses the actual
    GREEN/YELLOW/RED classification reads, never a second, possibly-divergent copy of
    this set.

    Reuses readout.py's own `FLOOD_LIKE_STATUS`/`NORMAL_LIKE_STATUS`/
    `CRITICAL_LIKE_STATUS` (English station-status words) plus the two exact BMA DDS
    Thai keys ("ระดับน้ำวิกฤติ"/"ระดับน้ำปกติ") already registered in
    `site/build_data.py`'s `_DDS_STATUS_TH` mapping -- never a new standalone status
    word. Returns `(set(), set(), set())` (never raises) if either module is
    unavailable; callers must treat that as "nothing recognised as
    flood-like/normal-like/critical-like this check", the same fail-open-to-neutral
    behaviour `_classify_current_local_state` already had before this helper was
    factored out.

    `critical_like` is the agency-declared critical/overflow subset (founder ruling
    2026-10-04, verbatim: "WATCH = YELLOW (แนะนำ)") -- it drives RED on its own;
    `flood_like` (the wider set, unchanged) still drives the `_trim_evidence`
    prioritisation and the community-report "agreement" check in readout.py, which
    this ruling does not touch."""
    try:
        import readout as readout_mod
    except Exception:  # pragma: no cover - defensive
        return set(), set(), set()
    dds_status_map: dict = {}
    try:
        if str(HERE / "site") not in sys.path:
            sys.path.insert(0, str(HERE / "site"))
        import build_data as _build_data_mod
        dds_status_map = getattr(_build_data_mod, "_DDS_STATUS_TH", {}) or {}
    except Exception:  # pragma: no cover - defensive, a bad import must not crash answer
        dds_status_map = {}
    # Only the exact keys already registered in build_data._DDS_STATUS_TH -- never a new
    # standalone status word.
    thai_flood_keys = {"ระดับน้ำวิกฤติ"} & set(dds_status_map)
    thai_normal_keys = {"ระดับน้ำปกติ"} & set(dds_status_map)
    flood_like = set(readout_mod.FLOOD_LIKE_STATUS) | thai_flood_keys
    normal_like = set(readout_mod.NORMAL_LIKE_STATUS) | thai_normal_keys
    # The Thai BMA DDS critical key ("ระดับน้ำวิกฤติ") is itself an agency-declared
    # critical reading, so it belongs in critical_like too -- there is no separate Thai
    # "overbank" key published by that source today.
    critical_like = set(getattr(readout_mod, "CRITICAL_LIKE_STATUS", set())) | thai_flood_keys
    return flood_like, normal_like, critical_like


def _classify_current_local_state(state_answer: dict | None) -> str:
    """Map `_answer_state`'s `status_counts` onto community_dag.py's own closed
    CURRENT_LOCAL_STATE vocabulary (GREEN/YELLOW/RED/UNKNOWN -- see community_dag.py's
    "Dual-state rule" block). Reuses readout.py's existing FLOOD_LIKE_STATUS /
    NORMAL_LIKE_STATUS / CRITICAL_LIKE_STATUS sets (each agency's own published status
    word) -- no new status word and no numeric cutoff is introduced here.

    Also:
      - BMA DDS canal bulletins publish the raw Thai words "ระดับน้ำวิกฤติ"/
        "ระดับน้ำปกติ" (critical/normal), which are NEITHER in FLOOD_LIKE_STATUS nor
        NORMAL_LIKE_STATUS (both are English station-status words from a different
        source). These two exact keys are folded into the flood-like/normal-like/
        critical-like sets before classifying (via `_flood_like_normal_like_status_words`,
        the ONE place this set is built -- never re-typed as a second copy here), so a
        real DDS critical reading is never silently lost into YELLOW.
      - `ขัดข้อง` (sensor/equipment fault, `live_water_level.SENSOR_FAULT_STATUS_TH`)
        is EXCLUDED before classifying -- a faulted sensor has no trustworthy reading
        (`level_m` is already None per that module), so counting it as a status word
        would invent evidence. If every fresh row this check is a fault, the state is
        UNKNOWN (no real reading at all), never YELLOW.
      - Founder ruling 2026-10-04 (verbatim: "WATCH = YELLOW (แนะนำ)"): a bare WATCH/
        เฝ้าระวัง station reading alone is no longer enough to drive RED -- RED is now
        reserved for an agency-declared critical/overflow reading (วิกฤต/ล้นตลิ่ง,
        readout.CRITICAL_LIKE_STATUS = {"CRITICAL", "OVERBANK"}, or the DDS Thai
        "ระดับน้ำวิกฤติ" key). WATCH (and any other non-critical, non-normal status word
        the upstream agency publishes) now falls through to YELLOW, same as before for
        the genuinely-mixed/unclear case."""
    counts = (state_answer or {}).get("status_counts") or {}
    if not counts:
        return "UNKNOWN"
    try:
        import live_water_level as lwl_mod
    except Exception:  # pragma: no cover - defensive
        return "UNKNOWN"

    fault_statuses = getattr(lwl_mod, "SENSOR_FAULT_STATUS_TH", set())
    effective = {st: n for st, n in counts.items() if st not in fault_statuses}
    if not effective:
        # every fresh row this check was a sensor/equipment fault -- no trustworthy
        # reading exists, which is UNKNOWN, never a fabricated YELLOW/GREEN.
        return "UNKNOWN"

    _flood_like, normal_like, critical_like = _flood_like_normal_like_status_words()

    if any(st in critical_like for st in effective):
        return "RED"
    if all(st in normal_like for st in effective):
        return "GREEN"
    # Everything else (WATCH/เฝ้าระวัง, plus any other upstream status word that is
    # neither agency-critical nor agency-normal) is YELLOW -- mixed/unclear/watch, never
    # silently folded into GREEN, and never escalated to RED on a non-critical word alone.
    return "YELLOW"


def _classify_forward_hazard(hazard_answer: dict | None) -> str:
    """Map `_answer_hazard`'s output onto community_dag.py's own closed
    FORWARD_HAZARD_STATE vocabulary (ACTIVE/NONE/UNKNOWN). "ACTIVE" is a PRESENCE check
    only (at least one cached model has a non-zero local-tomorrow or 7-day figure) -- not
    a severity cutoff, so no new mm threshold is introduced; a real magnitude-based
    threshold ladder already exists in sources/rain_alert_thresholds_crosswalk.yaml but is
    not wired to any routing/display code yet (OPEN, out of this item's scope) and is
    deliberately NOT reused here as a severity cutoff -- doing so would be inventing a
    binding use for a crosswalk that was built as a reference table, not a decision rule.

    A STALE forecast cache (`hazard_answer["stale"]` is
    True) must never be reported as ACTIVE -- the staleness rule the station rows already
    follow (AI.md rule 2) applies equally to the forecast cache; a stale cache's presence
    check is simply not trustworthy evidence of "active" right now."""
    if not hazard_answer or hazard_answer.get("tag") != "RELAYED":
        return "UNKNOWN"
    if hazard_answer.get("stale"):
        return "UNKNOWN"
    # FIX D (2026-10-04): the `offline_snapshot` ensemble-summary branch this used to
    # have is removed along with the tracked snapshot fallback itself -- `hazard_answer`
    # is now always either `per_model` (live, RELAYED) or OPEN/UNKNOWN, never a retained
    # ensemble shape.
    per_model = hazard_answer.get("per_model") or []
    has_rain = any(
        (m.get("tomorrow_mm") or 0) > 0 or (m.get("7day_total_mm") or 0) > 0
        for m in per_model)
    return "ACTIVE" if has_rain else "NONE"


def _real_pf06_record(area_id: str | None,
                       now_utc: "datetime.datetime | None" = None) -> dict | None:
    """The real PROP-FLOOD-06 compute() record for this point, read from the ONE place
    this repo actually computes it (`tools/backtest/compute_prop_flood_06_sammakorn.py`
    -- never re-derived here). Only "sammakorn" has this unit registered today
    (`raw/backtest/units.yaml`; see that module's own docstring) -- every other area_id
    (including a bare lat,lon) returns None, never a guessed record. Read-only: opens
    its own `mode=ro` connection to `DB_PATH` and always closes it, same discipline as
    `_answer_state`/`cmd_forecast`. Any failure (missing DB, missing units.yaml, import
    error) returns None -- a missing read is OPEN, never fabricated.

    `now_utc`, if given, is passed
    straight through to `compute(now_utc=...)` so a caller pinning `_answer_next_action`
    (and, through it, `_answer_state`'s own `as_of_date`) to a reference time also pins
    THIS read to the same clock -- without it, a pinned `kb` answer still silently
    computed PF06 against the real wall clock, which could disagree with every other
    pinned field in the same answer. `now_utc=None` (the default) is unchanged
    production behaviour: `compute()` falls back to the real wall clock itself.

    `_real_pf06_tier` (below) is the pre-existing tier-only wrapper the test suite
    calls directly; this function exists separately so the withheld-L5
    note (below) can read `input_provenance` without a second DB round-trip."""
    if area_id != "sammakorn" or not DB_PATH.exists():
        return None
    try:
        backtest_dir = str(HERE / "tools" / "backtest")
        if backtest_dir not in sys.path:
            sys.path.insert(0, backtest_dir)
        import compute_prop_flood_06_sammakorn as _pf06_mod
    except Exception:  # pragma: no cover - defensive
        return None
    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        return _pf06_mod.compute(conn=conn, now_utc=now_utc)
    except Exception:  # pragma: no cover - defensive, a bad run must not crash answer
        return None
    finally:
        if conn is not None:
            conn.close()


def _real_pf06_tier(area_id: str | None,
                     now_utc: "datetime.datetime | None" = None) -> str | None:
    """Tier-only wrapper around `_real_pf06_record` (see its docstring) -- kept as its
    own function because existing tests/callers from earlier rounds call it directly
    expecting a bare tier string/None, not the full record."""
    record = _real_pf06_record(area_id, now_utc=now_utc)
    return record.get("tier") if record else None


# Thai labels
# for community_dag.SAFE_NODE_CONTINUITY_FIELDS's 7-field closed vocabulary -- a
# translation layer only, never a new field/threshold. Keys are read from that same
# module's own tuple at call time below (never hard-coded independently of it), so a
# future field added there without a label here falls back to the raw field name
# rather than crashing.
_CONTINUITY_FIELD_TH = {
    "access_state": "ทางเข้า-ออก",
    "power_state": "ไฟฟ้า",
    "backup_power_state": "ไฟฟ้าสำรอง",
    "water_state": "น้ำประปา",
    "comms_state": "การสื่อสาร",
    "medical_capacity_state": "ศักยภาพด้านการแพทย์",
    "occupancy_state": "จำนวนผู้พักพิง",
}


def _continuity_gap_actions(doc: dict) -> tuple[list[dict], list[str]]:
    """`community_dag.report_safe_node_continuity_gaps` (Hat Yai finding F -- a node
    being a hospital/shelter never proves it is ready) is an EXISTING, already-computed
    report this item had not wired into
    `next_action` yet. Reused verbatim, never re-derived -- each gap becomes one "check
    X at safe node Y" action, sorted by node id for a stable order.

    The text used to read "ตรวจสอบความพร้อมของจุดปลอดภัย
    <raw node_id>: ยังไม่มีการรายงานสถานะ access_state, power_state, ..." -- a bare node id
    plus raw English field names, neither of which a resident can act on. Now uses the
    node's own `label_th` (already declared on every node in self_help_dag.yaml, falls
    back to the node id only if a node genuinely has none) and the Thai field labels
    above; the action is still sourced from, and tagged with, the SAME existing
    community_dag.report_safe_node_continuity_gaps() call -- no new rule, only a display
    fix on an existing, already-cited one.

    An `external_safe` node that is
    still a declared PLACEHOLDER (`verified_safe` is not True -- self_help_dag.yaml's own
    "these are placeholders, not claims that a named place is safe" comment) is not a
    real location a resident can go check -- "check readiness of 'External safe point
    #1 -- no real location assigned yet'" is not an action. Returns
    `(actions, notes)`: a placeholder node's gap moves into `notes` (still reported,
    honestly, as an OPEN gap) instead of `actions`; only a gap on a node that IS a real,
    already-surveyed place (any `internal_safe`/`support` node, or an `external_safe`
    node with `verified_safe: true`) becomes an action."""
    try:
        import community_dag
        gaps = community_dag.report_safe_node_continuity_gaps(doc)
    except Exception:  # pragma: no cover - defensive
        return [], []
    nodes = doc.get("nodes") or {}
    actions: list[dict] = []
    notes: list[str] = []
    for node_id in sorted(gaps):
        missing = gaps[node_id]
        node = nodes.get(node_id) or {}
        display_name = node.get("label_th") or node_id
        missing_th = ", ".join(_CONTINUITY_FIELD_TH.get(f, f) for f in missing)
        is_placeholder = (
            node.get("kind") == "external_safe" and node.get("verified_safe") is not True)
        if is_placeholder:
            notes.append(
                f"จุดปลอดภัยภายนอก \"{display_name}\" ยังเป็น placeholder (verified_safe != "
                f"true, ยังไม่กำหนดสถานที่จริง) -- ไม่นับเป็น action ที่ทำได้จริง รายงานเป็น OPEN "
                f"gap เท่านั้น (ยังไม่มีการรายงาน {missing_th})")
            continue
        actions.append({
            "action": f"ตรวจสอบความพร้อมของจุดปลอดภัย \"{display_name}\": ยังไม่มีการรายงาน "
                      f"{missing_th}",
            "source": "community_dag.report_safe_node_continuity_gaps",
            "why": "safe-node continuity report (Hat Yai finding F, card_dual_state_"
                   "reescalation_hatyai_2026-09-28.md) -- a node's kind (hospital/"
                   "shelter) never proves it is actually ready; these fields are "
                   "missing entirely, not merely declared UNKNOWN",
            "tag": "OPEN",
        })
    return actions, notes


def _route_mode_degradation(doc: dict, path: list[str]) -> list[dict]:
    """A safety fix (2026-10-02): display-only reuse of community_dag.MODE_DEGRADATION_
    LADDER/MODE_DEGRADATION_STATES (never re-declared here) -- one entry per consecutive
    edge along `path`, reading that edge's own already-declared `mode_degradation`
    attribute straight from `doc`'s edge list (no new computation). A path step with no
    matching edge record, or an edge that declares no `mode_degradation` at all, reads
    "UNKNOWN" -- per the card's own rule, UNKNOWN is never treated as passable, only
    reported honestly. Does not affect whether a route was found (routing logic is
    untouched, per the card's own "not bound into routing logic this check" note)."""
    try:
        import community_dag
    except Exception:  # pragma: no cover - defensive
        return []
    edges = doc.get("edges") or []
    by_pair = {}
    for e in edges:
        frm, to = e.get("from"), e.get("to")
        if frm is not None and to is not None:
            by_pair[(frm, to)] = e
    out = []
    for frm, to in zip(path, path[1:]):
        edge = by_pair.get((frm, to))
        deg = (edge or {}).get("mode_degradation")
        if deg not in community_dag.MODE_DEGRADATION_STATES:
            deg = "UNKNOWN"
        out.append({"from": frm, "to": to, "mode_degradation": deg})
    return out


def _who_to_call(accountability_answer: dict | None) -> dict:
    """This file's own fixed `HOTLINES` -- no new agency/number is added here.
    FIX C (2026-10-04, token budget): `owner_agencies` used to be repeated here
    verbatim, a byte-for-byte duplicate of `accountability.owner_agencies` at the
    payload's top level (unreferenced by any test, doc or the CLI printer --
    `grep -rn who_to_call` found nothing outside this function and its own call site).
    Once that field held human-readable Thai agency names instead of short internal
    ids (the F2 accountability-fallback fix above), the duplicate cost real budget
    room for no new information -- a caller who wants the owner list already has it at
    `payload['accountability']['owner_agencies']`.

    `hotlines` is now `["<number> <label_th>", ...]` instead of `[{"number":...,
    "label_th":...}, ...]` -- same information (every number+label this file's own
    `HOTLINES` constant carries, unchanged, nothing dropped), no key names repeated 4
    times in every single answer. Still unreferenced by any test/doc (checked above),
    so this shape change is safe."""
    return {"hotlines": [f"{h['number']} {h['label_th']}" for h in HOTLINES]}


def _answer_next_action(
    area_id: str | None,
    *,
    state_answer: dict | None = None,
    hazard_answer: dict | None = None,
    accountability_answer: dict | None = None,
    now_utc: "datetime.datetime | None" = None,
    verbose: bool = True,
    refresh_ran: bool = True,
    raw_at: str | None = None,
) -> dict:
    """Next action / self-help route -- calls community_dag.find_safe_route, the single
    merged route function (design H6: the MCP server's route tool must call this same
    function, never re-implement its own walk). Informational only -- never an evacuation
    order (floodconnect-agent skill rule 5): reports whether a feasible route was FOUND
    under the DAG's own constraints, never SAFE/guaranteed (dsva-redteam non-equivalence
    UNKNOWN != SAFE applies equally to 'route not found').

    The old version only
    ever answered the ROUTE sub-question, never "what do I do next" as a whole. Adds:
      - `dual_state`: current_local_state x forward_hazard (see the two classifiers above).
      - `actions`: 1-3 {action, source, why} dicts. Priority order: (1) the UNKNOWN action
        when current state is UNKNOWN -- always first, never skipped by a later rule; (2)
        for RED, either the L5 survival card headline (ONLY when PROP-FLOOD-06's own real
        tier engine reports L5 for this point this check) or a
        neutral station-level line otherwise; (3) a dual-state reminder when forward_hazard
        is ACTIVE while current state is not RED -- reserved BEFORE self-help items
        (a fixed action order was previously hiding this reminder behind
        pre-season self-help items); (4) self-help actions tools/kg/accountability.py's Q4
        already matched+cited (its ACTION_LIBRARY) -- SKIPPED when current state is RED,
        since ACTION_LIBRARY has no phase/applicability field distinguishing "before the
        rainy season" prep from "during the event" (the gap is
        reported via `notes`, never silently invented), replaced by the safe-node
        continuity-gap report instead; (5) the route result itself. Every source
        module/doc already existed before this item; nothing here derives a new equation
        or threshold.
      - `who_to_call`: see `_who_to_call` above.
      - `notes`: short OPEN-gap / contradiction annotations;
        only present when there is something to say.

    `refresh_ran` (fix, 2026-10-04): whether THIS run's own `build_answer`
    call actually attempted a refresh (`refresh=True`, i.e. `--offline` was NOT passed).
    Before this fix, the UNKNOWN-refresh action text always claimed "refresh already
    ran by default and found nothing fresh" even on an `--offline` run that never
    refreshed at all -- MEASURED later with `--verbose` on an
    `--offline` call. The action text below now says ONE of two true things depending
    on this flag, never both conflated into one sentence that is wrong half the time.

    - `now_utc`, if given, pins BOTH the real PROP-FLOOD-06 tier read
        (`_real_pf06_tier`) and the forecast-reminder/route logic below to the same
        reference time a caller already pinned `state_answer`'s own `as_of_date`
        to -- `now_utc=None` (the default) is unchanged production behaviour (the
        real wall clock, same as always).
      - Every dict in `actions` now carries a `tag` (MEASURED/RELAYED/OPEN) alongside
        its existing `source`/`why` -- taken from what that action actually
        rests on: MEASURED for a real station/tier reading, RELAYED for a third-party
        forecast model, OPEN for "no data"/"no route found"/a continuity gap.
      - Under RED, an ACTIVE forward_hazard now also gets a reminder slot
        (a shortened form of the same non-RED reminder, with the "even though the
        current state is normal" clause dropped since it would be false under RED),
        placed after the L5/neutral action and before the continuity-gap filler.
      - When the RED action is the neutral station-level line because the
        real PF06 engine withheld L5 specifically due to fault-only pump provenance,
        `why` says so explicitly, instead of a generic "tier engine did not report L5".
    The pre-existing top-level keys (`tag`/`found`/`path`/`target`/`score`/`reason`/
    `basis`/`start_node`) are unchanged in shape and meaning -- old callers/tests reading
    only those keys see no behaviour change.

    `verbose` defaults to
    True here (unchanged behaviour for every direct caller -- the test suite calls this
    function directly, with no `verbose` argument, and asserts on each action's `why`/
    `source` fields) -- only `build_answer` passes its own `verbose` argument through
    explicitly. When `verbose=False`, each dict in `actions` keeps `action`/`tag`/`steps`
    (the fields an entrypoint caller actually acts on) but drops `why` (the longer
    English rationale sentence) and `source` (which internal module/doc/rule justified
    the action) -- both meant for audit/debugging, not for deciding what to do next, and
    neither a sensor-reading provenance field (the floodconnect-agent skill's "carry
    provenance through" rule is about state readings, unaffected here) -- this is what
    keeps the real populated-DB answer under the token budget; `verbose=True` returns
    both fields on every action, unchanged."""
    dual_state = {
        "current_local_state": _classify_current_local_state(state_answer),
        "forward_hazard": _classify_forward_hazard(hazard_answer),
    }
    current = dual_state["current_local_state"]
    forward = dual_state["forward_hazard"]
    actions: list[dict] = []
    notes: list[str] = []

    # Structured flag from `_answer_state`/`_answer_hazard` (never a notes-text
    # search -- a prior version only matched when a note happened to contain the
    # literal substring "--refresh", which missed the real populated-DB-gone-stale
    # case entirely: a `state.notes` built from `_sources_summary_note` never
    # contained that string). `hazard.stale` is folded in too -- a stale forecast
    # cache is the same "this data needs a fresh fetch" condition.
    refresh_suggested = bool((state_answer or {}).get("refresh_suggested")) or \
        bool((hazard_answer or {}).get("stale"))

    if current == "UNKNOWN":
        actions.append({
            "action": UNKNOWN_ACTION_TH,
            "source": "AI.md / floodconnect-agent skill rule 2 (UNKNOWN is never "
                      "a verified-safe verdict)",
            "why": "no fresh (non-STALE), non-fault station status near this point this "
                   "round -- absence of data is never evidence of safety",
            "tag": "OPEN",
        })
        if refresh_suggested:
            # Inserted directly after the UNKNOWN action, unconditionally (never
            # behind `len(actions) < 3` -- a later route/self-help item filling the
            # remaining slots must never crowd this one out, since it is the one
            # action that actually explains WHY the answer is UNKNOWN and what a
            # caller can do about it).
            # fix (post-release review 2026-10-04): a bare lat,lon call (area_id is
            # None) used to print the literal placeholder "<area>" in this command
            # hint instead of the caller's own `--at` value -- `raw_at` (the CLI's
            # own `args.at`, passed through by `build_answer`) carries the real
            # value through so the printed command is copy-pasteable as-is.
            area_label = area_id or raw_at or "<area|lat,lon>"
            # FIX (2026-10-03): refresh is now the DEFAULT (this action
            # fires AFTER a refresh attempt already ran, unless the caller passed
            # `--offline`) -- the old wording told a caller to run `--refresh`/pass
            # `refresh=true`, a parameter the MCP tool no longer even has. The real
            # action now is either "you passed --offline, try without it" or "every
            # source is genuinely stale/unreachable even after refresh -- wait and
            # re-check", never a re-ask for something that already ran by default.
            # fix (2026-10-04): this text used to unconditionally claim
            # "refresh already ran by default and found nothing" even when THIS run
            # passed `--offline` (so no refresh ran at all) -- now branches on whether
            # a refresh actually happened this run.
            if refresh_ran:
                action_text = (
                    f"ลองรันใหม่ในอีกสักพัก (`floodconnect answer --at {area_label}`) -- "
                    "refresh เป็น default แล้วและรันไปแล้วรอบนี้ แต่ไม่พบข้อมูลสดเลย")
            else:
                action_text = (
                    f"ลองรันใหม่โดยไม่ใส่ `--offline` (`floodconnect answer --at "
                    f"{area_label}` / MCP offline=false) -- รอบนี้ไม่ได้ refresh เลย "
                    "(ใส่ --offline ไว้)")
            actions.append({
                "action": action_text,
                "source": "state.refresh_suggested / hazard.stale (offline/stale "
                          "cause already reported there)",
                "why": ("state is UNKNOWN because this installation has no fresh live "
                        "data this check, even after the default refresh attempt "
                        "(AI.md 'On-demand refresh') -- refresh fetches on the caller's "
                        "own network/keys, never through us, and can fail silently "
                        "(no network, upstream down) without making the answer itself "
                        "an error") if refresh_ran else
                       ("state is UNKNOWN and this run passed --offline, so no refresh "
                        "was attempted at all -- the caller's own data is simply stale, "
                        "not a failed refresh"),
                "tag": "OPEN",
            })
    elif current == "RED":
        pf06_record = _real_pf06_record(area_id, now_utc=now_utc)
        pf06_tier = pf06_record.get("tier") if pf06_record else None
        card_html = ""
        _build_page_mod = None
        if pf06_tier == "L5":
            try:
                if str(HERE / "site") not in sys.path:
                    sys.path.insert(0, str(HERE / "site"))
                import build_page as _build_page_mod
                card_html = _build_page_mod.build_l5_survival_card_html({"tier": pf06_tier})
            except Exception:  # pragma: no cover - a bad import must not crash answer
                card_html = ""
        if card_html and _build_page_mod is not None:
            # The headline alone ("...ทำตามนี้") with no steps
            # following it is worse than no headline -- always carry the real step list.
            actions.append({
                "action": _build_page_mod.L5_SURVIVAL_HEADLINE_TH,
                "steps": _l5_survival_steps_plain(_build_page_mod),
                "source": "site/build_page.py build_l5_survival_card_html (L5 survival "
                          "card, gated on tools/backtest/compute_prop_flood_06_"
                          "sammakorn.py's real tier output)",
                "why": "PROP-FLOOD-06's own tier engine reports tier=L5 for this point "
                       "this check (not only a station-level flood-like status)",
                "tag": "MEASURED",
            })
        else:
            # Say explicitly WHY L5
            # was withheld when the real cause is fault-only pump provenance (never the
            # generic "did not report L5" when the specific reason is known) -- reads
            # the SAME `input_provenance.pumps_running_count` the engine already
            # produced, never a new check.
            pump_prov = ((pf06_record or {}).get("input_provenance") or {}).get(
                "pumps_running_count") or {}
            withheld_note = ""
            if pf06_tier is not None and pump_prov.get("tag") == "OPEN" \
                    and "sensor fault" in (pump_prov.get("note") or ""):
                withheld_note = (" -- L5 withheld: pump readings this check are sensor "
                                  "faults (ขัดข้อง), not evidence of zero pumps running")
            actions.append({
                "action": STATION_RED_NEUTRAL_ACTION_TH,
                "source": "readout.CRITICAL_LIKE_STATUS / build_data._DDS_STATUS_TH "
                          "(station-level agency-critical status, not a PROP-FLOOD-06 "
                          "tier -- WATCH alone no longer reaches this branch, per "
                          "founder ruling 2026-10-04 'WATCH = YELLOW')",
                "why": ("station-level status, not the L5 tier -- PROP-FLOOD-06's real "
                        "tier engine did not report L5 for this point this check "
                        "(either no L5 unit exists for this area, or it reported a "
                        "lower/OPEN tier)" + withheld_note),
                "tag": "MEASURED" if pf06_tier is not None else "OPEN",
            })

        # The forward-hazard reminder used to
        # be reserved ONLY when current != RED, so an ACTIVE forecast (e.g. the Hat Yai
        # two-peak lesson) silently disappeared from a live RED answer. Added here, a
        # shortened form of the same non-RED reminder below with the "even though the
        # current state is normal" clause dropped (it would be false under RED).
        if forward == "ACTIVE" and len(actions) < 3:
            actions.append({
                "action": "มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก (RELAYED) -- เตรียมเส้นทางสำรอง",
                "source": "floodconnect-agent skill rule 1 (dual-state, always) / "
                          "community_dag.py FORWARD_HAZARD_STATE",
                "why": "forward_hazard=ACTIVE from a cached forecast model even while "
                       "current_local_state=RED -- a life-safety reading right now "
                       "never cancels an active forecast hazard on top of it",
                "tag": "RELAYED",
            })
    elif current == "YELLOW" and "WATCH" in ((state_answer or {}).get("status_counts") or {}):
        # Founder ruling 2026-10-04 ("WATCH = YELLOW (แนะนำ)") moved a bare WATCH
        # station reading off RED and onto YELLOW (see `_classify_current_local_state`
        # above), but left YELLOW's only wording ("สถานะปัจจุบันยังไม่ชัดเจน" -- "current
        # state unclear", added below only when `forward == "ACTIVE"`) saying nothing
        # about WATCH specifically, and said nothing at all when forward is not
        # ACTIVE -- a fresh WATCH reading on a forecast-quiet day would reach the
        # resident as silence, which understates a real agency-published watch-level
        # status. This is a MEASURED action straight off `status_counts` (the same
        # field `_classify_current_local_state` already classified on), not a new
        # status word or threshold.
        actions.append({
            "action": "สถานีน้ำใกล้จุดนี้อยู่ระดับเฝ้าระวัง (WATCH, ระดับสถานีเท่านั้น) -- "
                      "ติดตามต่อเนื่อง / ทำตามประกาศทางการ",
            "source": "state.status_counts (WATCH) / readout.py station-status words -- "
                      "the same field `_classify_current_local_state` reads",
            "why": "status_counts contains WATCH, which `_classify_current_local_state` "
                   "maps to current_local_state=YELLOW (founder ruling 2026-10-04) -- a "
                   "station-level watch reading, never a PROP-FLOOD-06 L5 tier claim",
            "tag": "MEASURED",
        })

    # Reserve a slot for the forward-hazard reminder BEFORE the self-help/route items
    # whenever it is ACTIVE -- except when current state is
    # already RED, where the RED block above already handled it.
    #
    # Life-safety wording fix: this reminder used to say "แม้สถานะปัจจุบันยังปกติ" ("even
    # though the current state is still normal") for EVERY non-RED state, including
    # UNKNOWN and YELLOW -- which told an asker with NO current-state data at all that
    # things were "ปกติ" (normal). That directly contradicts UNKNOWN_ACTION_TH two steps
    # above, is a false normalcy claim for an UNKNOWN reading (floodconnect-agent skill
    # rule 2 / dsva-redteam: UNKNOWN != SAFE), and also mischaracterised YELLOW
    # (mixed/unclear station status) as settled. "ปกติ" is now said only for GREEN,
    # where a real fresh, non-flood-like reading backs it; UNKNOWN gets the same "no
    # current-state data yet" framing as UNKNOWN_ACTION_TH (no new wording invented,
    # same underlying claim); YELLOW gets its own neutral "unclear" wording. Contains
    # none of the four banned resident-facing words (ไม่ต้อง/ห้าม/ไม่ควร/ผ่อนคลาย).
    if forward == "ACTIVE" and current != "RED" and len(actions) < 3:
        if current == "GREEN":
            action_text = ("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก (RELAYED) -- เตรียมเส้นทางสำรองไว้ก่อน "
                           "แม้สถานะปัจจุบันยังปกติ")
            why_text = ("forward_hazard=ACTIVE from a cached forecast model while "
                        "current_local_state=GREEN (fresh, non-flood-like station status) -- "
                        "a calm current reading never cancels an active forecast hazard")
        elif current == "UNKNOWN":
            action_text = ("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก (RELAYED) -- เตรียมเส้นทางสำรองไว้ก่อน "
                           "ยังไม่มีข้อมูลสถานะปัจจุบัน")
            why_text = ("forward_hazard=ACTIVE from a cached forecast model while "
                        "current_local_state=UNKNOWN -- no current-state data was ever "
                        "evidence of safety, and that absence never cancels an active "
                        "forecast hazard either")
        else:  # YELLOW
            action_text = ("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก (RELAYED) -- เตรียมเส้นทางสำรองไว้ก่อน "
                           "สถานะปัจจุบันระดับเฝ้าระวัง/ไม่ชัดเจน")
            why_text = ("forward_hazard=ACTIVE from a cached forecast model while "
                        "current_local_state=YELLOW (a WATCH/เฝ้าระวัง station-level "
                        "reading, or another mixed/unclear station status) -- a "
                        "watch-level or unclear current reading never cancels an "
                        "active forecast hazard")
        actions.append({
            "action": action_text,
            "source": "floodconnect-agent skill rule 1 (dual-state, always) / "
                      "community_dag.py FORWARD_HAZARD_STATE",
            "why": why_text,
            "tag": "RELAYED",
        })

    # The "run --refresh" action for an UNKNOWN current state is now inserted
    # unconditionally right after the UNKNOWN action itself (above, inside the
    # `if current == "UNKNOWN":` block) -- a structured `refresh_suggested` flag,
    # never a notes-text search, and never subject to `len(actions) < 3` crowding by
    # the dual-state reminder/route items below.

    # Load the self-help DAG document once, reused by both find_safe_route (below) and
    # the continuity-gap report -- never re-derived, single load per call.
    doc = None
    doc_error = None
    community_dag = None
    if area_id is not None and SELF_HELP_DAG_PATH.exists():
        try:
            import community_dag
            doc = community_dag.load_document(SELF_HELP_DAG_PATH)
        except Exception as e:  # pragma: no cover - defensive
            doc_error = str(e)

    # find_safe_route is now
    # computed BEFORE the self-help/continuity-gap block below, so the route result
    # itself (found path, or REASON_NO_FEASIBLE_SAFE_ROUTE) can claim one of the up-to-3
    # action slots even under RED -- the old order let continuity-gap items fill every
    # remaining slot first, so "is there a way out" never appeared in `actions` at all
    # during a live RED event, only buried inside the top-level `path`/`found` fields a
    # caller reading just `actions` would never see.
    if area_id is None:
        route_out: dict = {"tag": "OPEN", "note": "no declared self-help DAG start node "
                                                    "for a bare lat,lon -- pass a known "
                                                    "area_id (sammakorn, ram53)"}
    else:
        start_node = _ANSWER_AREAS[area_id]["self_help_start"]
        if doc is None:
            route_out = {"tag": "OPEN",
                         "note": doc_error or f"{_relpath(SELF_HELP_DAG_PATH)} not found"}
        else:
            try:
                result = community_dag.find_safe_route(doc, start_node)
                route_out = result.as_dict()
                # See the matching note in
                # _answer_accountability -- "MEASURED-on-graph" is not one of the five
                # floor tokens; use MEASURED + basis.
                if route_out["found"]:
                    route_out["tag"] = "MEASURED"
                    route_out["basis"] = "graph"
                else:
                    route_out["tag"] = "OPEN"
                route_out["start_node"] = start_node
                # Display-only MODE_DEGRADATION_LADDER readout (card_dual_state_
                # reescalation_hatyai_2026-09-28.md ss3 item 4): that card explicitly
                # says find_safe_route() itself must NOT read this field into its
                # routing decision this check ("ยังไม่ผูกเข้า routing logic ในงานนี้") --
                # it is a readout ladder for DISPLAY first. So this never changes
                # whether the route was found; it only reports each traversed edge's
                # OWN already-declared `mode_degradation` value (UNKNOWN when the edge
                # declares none), reusing community_dag.MODE_DEGRADATION_LADDER's
                # closed vocabulary verbatim, never a new one.
                if route_out.get("found") and route_out.get("path"):
                    route_out["mode_degradation"] = _route_mode_degradation(
                        doc, route_out["path"])
                if len(actions) < 3:
                    if route_out["found"]:
                        actions.append({
                            "action": "เส้นทางที่ตรวจสอบแล้วไปจุดหมายภายนอก: "
                                      + " -> ".join(route_out["path"]),
                            "source": "community_dag.find_safe_route",
                            "why": "feasible path found under this point's declared "
                                   "self-help DAG (field-verified/fresh/capacity-checked "
                                   "edges+nodes only, never a guarantee)",
                            "tag": "MEASURED",
                        })
                    else:
                        # Deliberately neutral: this must never read as a stay-put
                        # order. All 21 self_help_dag.yaml nodes ship as UNKNOWN/not
                        # fresh, so find_safe_route can never succeed on the shipped
                        # data -- give no instruction, point at official channels
                        # instead, and never say "ปลอดภัย" here.
                        actions.append({
                            "action": "ระบบนี้ยังไม่มีข้อมูลเส้นทาง/จุดหมายภายนอกที่ตรวจสอบแล้ว "
                                      "(ทุกจุดยังเป็น UNKNOWN) -- ตัดสินใจตามประกาศหน่วยงานทางการ "
                                      "หรือโทร 1784 / 1555",
                            "source": "community_dag.find_safe_route "
                                      "(no feasible route found)",
                            "why": route_out.get("reason")
                                   or community_dag.REASON_NO_FEASIBLE_SAFE_ROUTE,
                            "tag": "OPEN",
                        })
            except Exception as e:  # pragma: no cover - defensive
                route_out = {"tag": "OPEN", "note": f"find_safe_route failed: {e}"}

    if current == "RED":
        # ACTION_LIBRARY (tools/kg/accountability.py Q4)
        # has no phase/applicability field distinguishing "before the rainy season" prep
        # items from "during the event" actions -- never invent one. Skip that list
        # entirely under RED so a pre-season planning item never fills a life-safety
        # slot; fill remaining slots with the already-computed safe-node continuity
        # report instead (real gap data, not new advice).
        if verbose:
            notes.append(
                "ACTION_LIBRARY (tools/kg/accountability.py) has no phase/applicability "
                "field -- self-help items are not shown while current_local_state=RED, to "
                "avoid a pre-season planning task appearing as a next action during a live "
                "event (OPEN gap, still not fixed here)")
        if doc is not None:
            gap_actions, gap_notes = _continuity_gap_actions(doc)
            if verbose:
                notes.extend(gap_notes)
            elif gap_notes:
                # Both RED-only OPEN gaps (ACTION_LIBRARY skipped, and the
                # placeholder-safe-point count) collapse to ONE combined summary line in
                # default mode -- token-budget discipline (tests/test_token_budget.py);
                # neither gap is dropped, each full explanation is one `--verbose` call
                # away.
                notes.append(
                    f"RED: self-help actions skipped (no phase field); "
                    f"{len(gap_notes)} จุดปลอดภัยภายนอกยังเป็น placeholder "
                    "(ยังไม่กำหนดสถานที่จริง) -- OPEN gaps, ดูรายละเอียดด้วย --verbose")
            elif not verbose:
                notes.append(
                    "RED: self-help actions skipped (ACTION_LIBRARY has no phase field) "
                    "-- OPEN gap, see --verbose")
            for act in gap_actions:
                if len(actions) >= 3:
                    break
                actions.append(act)
        elif not verbose:
            notes.append(
                "RED: self-help actions skipped (ACTION_LIBRARY has no phase field) "
                "-- OPEN gap, see --verbose")
    else:
        for act in (accountability_answer or {}).get("self_help_actions", []):
            if len(actions) >= 3:
                break
            actions.append({
                "action": act.get("text_th"),
                "source": act.get("cite") or "tools/kg/accountability.py ACTION_LIBRARY",
                "why": act.get("why_matched") or "matched by accountability Q4 self-help",
                "tag": "RELAYED",
            })

    # A non-empty contradiction count must
    # reach next_action, not stay silently buried inside `state`'s own payload -- point
    # at both sides without resolving them (the readout itself already carries both
    # rows; this is only a pointer so a caller reading just `next_action` still sees it).
    contradiction_count = (state_answer or {}).get("contradiction_count") or 0
    if contradiction_count > 0:
        if verbose:
            notes.append(
                f"มีข้อมูลขัดแย้งกัน {contradiction_count} รายการระหว่างแหล่งข้อมูลสำหรับจุดนี้ -- "
                "ดู payload['state']/readout contradictions เพื่อดูทั้งสองด้าน (ไม่เลือกข้างใดข้างหนึ่ง)")
        else:
            # The same pointer, shortened -- the count itself
            # already lives in state.contradiction_count (never dropped, see
            # `_answer_state`), so this note's only job in default mode is to say
            # "go look", not to restate the Thai sentence in full every call.
            notes.append(
                f"{contradiction_count} contradiction(s) between sources for this point "
                "-- see state.contradiction_count / readout contradictions (not resolved).")

    out = dict(route_out)
    out["dual_state"] = dual_state
    capped_actions = actions[:3]
    if not verbose:
        # Drop the longer audit/debug `why`/`source` text in
        # default mode (both cite WHICH internal module/doc/rule justified the action,
        # for audit purposes -- never a sensor-reading source, so dropping them here is
        # not the floodconnect-agent skill's "carry provenance through" rule, which is
        # about state readings, not these citations). `action`/`tag`/`steps` (what an
        # entrypoint caller actually acts on) are untouched; nothing here is ever a new
        # claim, only a field removed from the response shape in the default case.
        capped_actions = [{k: v for k, v in act.items() if k not in ("why", "source")}
                           for act in capped_actions]
    out["actions"] = capped_actions
    out["who_to_call"] = _who_to_call(accountability_answer)
    if notes:
        out["notes"] = notes
    return out


def _source_tag(field: str, node_id: "str | None", note: str) -> dict:
    """Build one `source_tags[]` entry. The epistemic_class is READ from the RKG node at
    call time (never hard-coded),
    and a field backed by no RKG node gets `epistemic_class: null` plus a note saying so
    instead of an invented slug (the old code hard-coded "RELAYED" for `hazard` and
    "STATIC_TOPOLOGY/ROLE_OVERLAY" for `accountability` -- neither is a value from
    `epistemic_classes` in site/inputs/meta/floodconnect_repo_kg.yaml, and that
    promised "not yet in Toledo" label was never actually emitted anywhere in the code).
    When the node IS found and its class is PROPOSAL, the label is added here -- this is
    the only place that string is produced now."""
    cls = _rkg_epistemic_class(node_id) if node_id else None
    tag: dict = {"field": field, "epistemic_class": cls, "note": note}
    if node_id and cls is None:
        tag["note"] = note + " -- RKG node lookup failed or the node is missing; treat as OPEN"
    if cls == "PROPOSAL":
        tag["toledo"] = "not yet in Toledo"
    return tag


def _compact_source_tags(source_tags: list[dict]) -> list[dict]:
    """Default-mode (`verbose=False`) shape for `source_tags[]` -- `{field,
    epistemic_class}` only (plus `toledo` when `_source_tag` set it; that flag is a
    distinct AI.md-documented contract, not the long English `note`, so it survives the
    cap). The full `note` explaining WHY a field has no RKG node is audit/debug prose,
    one `--verbose` call away -- never the only place a caller learns a PROPOSAL-tier
    source is unregistered. Token-budget discipline, see tests/test_token_budget.py."""
    compact = []
    for tag in source_tags:
        entry = {"field": tag.get("field"), "epistemic_class": tag.get("epistemic_class")}
        if "toledo" in tag:
            entry["toledo"] = tag["toledo"]
        compact.append(entry)
    return compact


def _compact_hazard_for_display(hazard_answer: dict, cap: int = 3) -> dict:
    """Default-mode (`verbose=False`) shape for the `hazard` field -- caps a live
    `per_model` list (one row per third-party weather model, today 10) to its min/
    median/max by `tomorrow_mm` plus a `+N more` count note, instead of naming every
    model. Classification (`_classify_forward_hazard`) always runs against the FULL,
    uncapped `hazard_answer` this function is called on -- this only shrinks the
    DISPLAYED copy built from it, never the decision input, so capping can never flip
    ACTIVE/NONE. A caller who wants every model's figures reruns with `--verbose`/
    `verbose=true` (the full list is never otherwise reachable -- AI.md's own
    on-demand-refresh model, nothing hidden server-side).

    A model with `tomorrow_mm=None` (no usable figure this check) is excluded from the
    min/median/max selection itself -- `None or 0` previously sorted a missing figure
    as if it measured zero, so an unmeasured model could be shown AS the "min", a false
    reading dressed up as the smallest real one. Such a model is still counted in the
    "+N more" note (and in a separate note when every shown model lacks it, by this
    function's own `tomorrow_mm is None` check, so a caller reading only the capped
    list still learns some models have no figure, rather than it silently vanishing
    into "+N more" with no further explanation)."""
    per_model = hazard_answer.get("per_model")
    if not per_model or len(per_model) <= cap:
        return hazard_answer
    known = [m for m in per_model if m.get("tomorrow_mm") is not None]
    unknown_count = len(per_model) - len(known)
    # Select min/median/max only from models that actually have a tomorrow_mm figure --
    # falls back to the full (possibly all-None) list only when NONE have one, so this
    # never crashes; in that fallback case every "figure" shown is already None, never
    # a fabricated zero.
    pool = known if known else per_model
    ordered = sorted(pool, key=lambda m: m.get("tomorrow_mm") if known else 0)
    mid = ordered[len(ordered) // 2]
    picked = [ordered[0], mid, ordered[-1]]
    # De-duplicate (a short list could repeat the same model as min/median/max).
    seen_models = set()
    deduped = []
    for m in picked:
        if m["model"] not in seen_models:
            deduped.append(m)
            seen_models.add(m["model"])
    # The min/median/max selection above is ranked by `tomorrow_mm` only -- it can
    # hide the model with the single highest multi-day total (`7day_total_mm`), which
    # understates the upper spread for a caller reading only the capped list. Always
    # surface that model too, even when it duplicates none of the min/median/max picks.
    totaled = [m for m in per_model if m.get("7day_total_mm") is not None]
    if totaled:
        highest_total = max(totaled, key=lambda m: m["7day_total_mm"])
        if highest_total["model"] not in seen_models:
            deduped.append(highest_total)
            seen_models.add(highest_total["model"])
    out = dict(hazard_answer)
    out["per_model"] = deduped
    note = (f"min/median/max by tomorrow_mm of {len(per_model)} models shown "
            f"(+{len(per_model) - len(deduped)} more -- see --verbose for every model)")
    if unknown_count:
        note += f"; {unknown_count} model(s) have no tomorrow_mm figure this check"
    out["per_model_note"] = note
    return out


def _refresh_relevant_sources(area_id: str | None = None, verbose: bool = False,
                               all_sources: bool = False,
                               lat: float | None = None,
                               lon: float | None = None) -> list[dict]:
    """On-demand refresh: fetch ONLY the wired collectors, one GET per source, on the
    CALLER's own network/compute/keys -- never a server we run. No scheduler calls
    this. FIX (2026-10-03): this docstring used to say "only runs when a
    caller explicitly passes --refresh" -- stale since the same day's refresh-by-default
    ruling; this now runs on every `cmd_answer`/`build_answer` call UNLESS the caller
    passes `--offline`/`offline=True` (`--refresh` is kept only as a no-op for old
    scripts/muscle memory, since refresh is already the default).

    Added 2026-10-03: two more narrowings on top of the area filter below, found by
    MEASURING what a Sammakorn `--refresh` was actually fetching --
    `collect.CATALOG_ONLY_NOT_IN_REFRESH` (catalog/document-listing sources that feed
    no `state`/`hazard`/`next_action` field at all, e.g. the nationwide CCTV catalog)
    is EXCLUDED unconditionally, `--all`/`--source` are unaffected.

    FIX (2026-10-04, F8/CCTV): `hii_analyst_cctv` is the ONE exception added back to
    this unconditional exclusion below -- it still feeds no `state`/`hazard`/
    `next_action` decision (CATALOG_ONLY_NOT_IN_REFRESH's reasoning for excluding it
    from THOSE fields is unaffected), but `_answer_cctv`'s nearest-camera list (VISUAL-
    CHECK, never a decision input) needs this catalog refreshed per area now, so it is
    re-added after the `CATALOG_ONLY_NOT_IN_REFRESH`/`ANSWER_SOURCES` filtering above.

    Added for v0.1.1 (independent post-release review finding: "no Bangkok DDS sources for
    Chiang Mai"): `lat`/`lon`, if given, additionally narrow the fetch set against
    `collect.SOURCE_BBOX` -- a bbox-scoped source (today: the 5 BMA/dds.bangkok.go.th
    sources) is skipped when the point falls outside its declared bounding box. Unlike
    `AREA_RELEVANT_SOURCES` below (narrows only for a point that resolves to one of
    this repo's NAMED areas), this check runs off the raw coordinate itself, so it also
    catches a bare `--at lat,lon` that resolves to no named area at all -- the case
    `AREA_RELEVANT_SOURCES` alone cannot reach (see `_resolve_area`: an unnamed point's
    `area_id` is `None`, which skipped the `AREA_RELEVANT_SOURCES` block entirely
    before this fix). `lat`/`lon` left `None` (the default; existing direct callers/
    tests that only ever passed named areas) leaves this new check a no-op, unchanged
    behaviour.

    A key-gated source
    whose key is absent from THIS machine's environment is also excluded when
    `verbose=False` (the default) -- skipped quietly, no fetch attempt and no entry in
    the returned report, rather than a guaranteed-to-fail attempt plus a "missing key"
    line on every single refresh; `verbose=True` keeps it in the list so a caller who
    DOES want to see every key-gated gap still can.

    FIX (2026-10-03): the default (`all_sources=False`) fetch set is now
    also intersected against `collect.ANSWER_SOURCES` -- a POSITIVE allowlist of the
    sources that actually feed `state`/`hazard`/the real PROP-FLOOD-06 L-tier engine for
    an area answer (canal/pump/flood-road/dds-daily/dds-tide/dds-flood-report/rain/
    social-listening/the two forecast models/bma_watermap -- see that constant's own
    docstring for the full list and why each one is there). Before this, this
    function's own docstring admitted the fetched set was "still the full wired list" --
    MEASURED: 47 of 72 registry sources survived the old filter for a plain `kb.py
    answer --at sammakorn`, including sources with zero relevance to any served area
    (gdacs_events, noaa_oni, openmeteo_sst, openmeteo_pressure, data_go_th_ckan,
    gistda_portal, ddpm_portal, tmd_main_site, marine_imis, marine_elaws, ...), all paid
    for on the caller's own network on every single default `answer` call. `all_sources
    =True` (wired to `kb.py answer --all` / `--at ... --all`) restores the full sweep
    (same narrowing as before this fix: DORMANT/CATALOG_ONLY/key-gated/
    AREA_RELEVANT_SOURCES only) for a human who explicitly wants it -- `collect.py
    --all`/`--source` are a separate path entirely and are never touched by this flag.

    collect.run() already enforces one-request-per-source and a per-run host circuit
    breaker (stops touching a host after one 403/reset this run; see collect.py's own
    _looks_like_host_block) -- this function adds no retry logic of its own.

    Any source whose collector throws, is unimplemented, or needs a key the caller's
    environment doesn't have comes back with ok=False and a note; a source with no
    fetcher by design or no collector at all comes back skipped=True, ok=False (never
    counted as a real fetch). cmd_answer/cmd_connectors print
    that note and the downstream answer fields for that source stay their existing
    OPEN/stale state -- never silently promoted to a value."""
    sys.path.insert(0, str(HERE))
    import collect as collect_mod
    registry = collect_mod.load_registry()
    source_ids = [sid for sid in registry.keys()
                  if sid not in collect_mod.DORMANT_NOT_IN_ALL
                  and sid not in collect_mod.CATALOG_ONLY_NOT_IN_REFRESH]
    if not all_sources:
        source_ids = [sid for sid in source_ids if sid in collect_mod.ANSWER_SOURCES]
    # FIX (2026-10-04, F8/CCTV): `hii_analyst_cctv` is correctly excluded above via
    # `CATALOG_ONLY_NOT_IN_REFRESH` for every OTHER purpose (a nationwide camera
    # catalog feeds no state/hazard/next_action field) -- but `_answer_cctv`'s nearest-
    # camera list needs exactly this catalog kept fresh per area too. Added back here
    # explicitly (present in the registry, not dormant) regardless of the
    # `all_sources`/`ANSWER_SOURCES` allowlist narrowing above, since CCTV lookup is
    # now part of every default `answer` call, not an opt-in extra.
    if ("hii_analyst_cctv" in registry
            and "hii_analyst_cctv" not in collect_mod.DORMANT_NOT_IN_ALL
            and "hii_analyst_cctv" not in source_ids):
        source_ids = source_ids + ["hii_analyst_cctv"]
    if not verbose:
        source_ids = [sid for sid in source_ids
                      if not collect_mod._missing_api_key_env(sid, registry[sid])]
    # Added 2026-10-03: narrow the per-area fetch list by collect.AREA_RELEVANT_SOURCES -- a
    # source with an explicit area allowlist there is skipped for an area not in it
    # (e.g. rid9_chonburi_rpt, whose basin covers none of this repo's served areas).
    # A source absent from that map is unaffected (still fetched for every area), same
    # default-preserving posture as the POINT_FILTERABLE_SOURCES filter below.
    if area_id:
        source_ids = [sid for sid in source_ids
                      if sid not in collect_mod.AREA_RELEVANT_SOURCES
                      or area_id in collect_mod.AREA_RELEVANT_SOURCES[sid]]
    # Bbox filter (v0.1.1 fix, see this function's own docstring): only applied when a
    # real coordinate is given -- skips a bbox-scoped source whose declared box does
    # not contain (lat, lon). A source absent from `collect.SOURCE_BBOX` is unaffected.
    if lat is not None and lon is not None:
        source_bbox = getattr(collect_mod, "SOURCE_BBOX", {})

        def _in_bbox(sid: str) -> bool:
            box = source_bbox.get(sid)
            if box is None:
                return True
            return (box["lat_min"] <= lat <= box["lat_max"]
                    and box["lon_min"] <= lon <= box["lon_max"])

        source_ids = [sid for sid in source_ids if _in_bbox(sid)]
    points_by_source = None
    if area_id in collect_mod.FORECAST7D_POINTS:
        one_point = {area_id: collect_mod.FORECAST7D_POINTS[area_id]}
        points_by_source = {sid: one_point for sid in collect_mod.POINT_FILTERABLE_SOURCES}
    # FIX B item 1 (2026-10-04, SPEED): `parallel=True` fetches every one of these
    # sources concurrently via `collect.run`'s own thread pool (one request each, no
    # retry, bounded to a 20s per-source wall-clock budget -- see `collect.run`'s own
    # docstring for why a single `wait()` call, not a per-future loop, is what actually
    # keeps the whole batch bounded rather than serialising N*timeout in the worst
    # case). `ttl_s=collect.DEFAULT_TTL_S` (10 min, `FLOODCONNECT_REFRESH_TTL_S` env
    # override) skips the real network call entirely for a source fetched within that
    # window, reusing the already-stored observation -- this is the ONLY place `ttl_s`
    # is wired to a non-zero value; `collect.py --all`/`--source` (a human explicitly
    # asking for a fetch) and every direct test call of `collect.run` default to
    # `ttl_s=0` (cache off) unless they opt in themselves. `--offline`
    # (`refresh=False` in `build_answer`) never reaches this function at all, so it is
    # unaffected.
    # `max_workers` covers every candidate source_id at once (never fewer than the
    # default 8) -- with FEWER worker threads than sources, the thread pool queues the
    # excess and they only start once an earlier one finishes, which can silently push
    # the real wall-clock well past `per_source_timeout_s` (MEASURED: 13 sources against
    # the old default of 8 workers took ~52s, not the ~20s a single wait() call alone
    # would suggest, because 5 sources never even started running until deep into the
    # window). One worker per source removes that queueing tax entirely -- every
    # candidate starts running the moment `run()` submits it.
    results = collect_mod.run(source_ids, dry_run=False, points_by_source=points_by_source,
                               parallel=True, ttl_s=collect_mod.DEFAULT_TTL_S,
                               per_source_timeout_s=20,
                               max_workers=max(8, len(source_ids)))
    return [{"id": r.source_id, "ok": r.ok, "skipped": r.skipped, "note": r.note}
            for r in results]


def _compact_refresh_report(report: list[dict]) -> dict:
    """Collapses the full per-source `_refresh_relevant_sources` report to counts plus
    the ids that actually failed (fix, 2026-10-04): the real default
    path is `refresh=True`, and the full per-source list (13+ entries once
    ANSWER_SOURCES/CCTV are counted) pushed the default `floodconnect answer`/MCP
    payload over the 5,000-token budget on its own -- MEASURED at 5,365/5,408
    tokens for sammakorn/ram53 against a 5,000 ceiling. Never
    applied when `verbose=True` (unchanged -- `test_verbose_answer_names_every_source
    _uncapped` and friends keep reading the full list)."""
    ok = sum(1 for r in report if r.get("ok"))
    skipped = sum(1 for r in report if r.get("skipped"))
    failed_ids = [r["id"] for r in report if not r.get("ok") and not r.get("skipped")]
    return {"total": len(report), "ok": ok, "skipped": skipped, "failed_ids": failed_ids}


def build_answer(at: str, refresh: bool = False, on_refresh_progress=None,
                  verbose: bool = False, all_sources: bool = False) -> dict:
    """The one real implementation behind both `kb.py answer`/`compute` (`cmd_answer`
    below) and the MCP `floodconnect_answer` tool (there
    used to be no MCP equivalent of `--refresh` because this logic lived only inside
    `cmd_answer`, entangled with argparse's `args` namespace and `print()` calls). This
    function does no I/O to stdout -- it returns the exact JSON-shaped payload
    `cmd_answer --json` prints; callers that want the human-readable Thai text format
    stay with `cmd_answer`, unchanged.

    Raises `_BadAt` for an unresolvable `at` (same as `_resolve_area` always has) --
    callers (both `cmd_answer` and the MCP tool) catch this themselves rather than this
    function printing an error and returning an error code (there is no "process exit
    code" concept for an in-process MCP tool call).

    `on_refresh_progress`, if given, is called once with the refresh report dict list
    right after a `refresh=True` fetch completes and before the answer fields are
    computed -- `cmd_answer` uses it to print its CLI progress lines; the MCP tool
    leaves it unset (the report is already in the returned payload's `refresh` key).

    This FUNCTION's own default stays `refresh=False` (unchanged, 2026-10-02) -- tests
    call it directly against a tmp/empty DB and must never touch the network (see
    `tests/test_tag_vocabulary.py`, `tests/test_token_budget.py`). The approved
    refresh-by-default fix (2026-10-03, project decision) lives one layer up, in the two
    real entrypoints: `cmd_answer`'s argparse default and the MCP `floodconnect_answer`/
    `floodconnect_answer_core` wrappers now pass `refresh=True` unless the caller passes
    `--offline`/`offline=True` -- this function itself is unchanged so a direct caller
    (a test, a script) keeps explicit, unsurprising control.

    `verbose=False` (the default) keeps `state.notes` capped to the top sources by this
    answer's relevance (token-budget on a populated DB) -- see
    `_answer_state`/`_sources_summary_note`. `verbose=True` returns the full source list.

    `all_sources=False` (the default, fix) narrows a `refresh=True` fetch
    to `collect.ANSWER_SOURCES` -- see `_refresh_relevant_sources`'s own docstring.
    `all_sources=True` (wired to `kb.py answer --all`) restores the full wired-source
    sweep for a human who explicitly wants it."""
    area_id, lat, lon = _resolve_area(at)
    if _outside_thailand(lat, lon):
        # fix: never let a coordinate outside Thailand (a typo, or a later measurement pass
        # probe like 999,999) reach `_answer_state`/`build_readout` and pick up
        # city-wide DDS bulletin rows as "near" it. Every block is UNKNOWN/OPEN, no
        # colour, no hazard classification, no accountability lookup. Shaped exactly
        # like a normal `build_answer` return (`state`/`hazard`/`accountability`/
        # `next_action.dual_state`) so every caller (CLI `--json`, MCP, `cmd_answer`'s
        # own text printer) reads this the same way as any other answer, not a
        # special-cased shape only this branch produces.
        note = (f"({lat},{lon}) is outside Thailand -- FloodConnect only covers Thai "
                "locations; refusing to guess.")
        unknown_state = {"tag": "OPEN", "note": note}
        unknown_hazard = {"tag": "OPEN", "note": note, "per_model": []}
        unknown_accountability = {"tag": "OPEN", "note": note, "owner_agencies": []}
        unknown_cctv = {"tag": "OPEN", "note": note, "cameras": []}
        next_action_answer = {
            "tag": "OPEN", "found": False, "reason": note,
            "dual_state": {"current_local_state": "UNKNOWN", "forward_hazard": "UNKNOWN"},
            "actions": [{"tag": "OPEN",
                         "action": "ตรวจสอบพิกัด (lat,lon) อีกครั้ง -- FloodConnect "
                                   "รองรับเฉพาะพื้นที่ในประเทศไทย"}],
            "who_to_call": [],
        }
        return {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "at": at, "refresh": None,
            "state": unknown_state,
            "hazard": unknown_hazard,
            "accountability": unknown_accountability,
            "next_action": next_action_answer,
            "source_tags": [],
        }
    refresh_report = None
    if refresh:
        refresh_report = _refresh_relevant_sources(area_id or at, verbose=verbose,
                                                     all_sources=all_sources,
                                                     lat=lat, lon=lon)
        if on_refresh_progress is not None:
            on_refresh_progress(refresh_report)
    state_answer = _answer_state(lat, lon, verbose=verbose)
    hazard_answer = _answer_hazard(area_id or at, lat, lon)
    accountability_answer = _answer_accountability(area_id or at, verbose=verbose)
    cctv_answer = _answer_cctv(lat, lon)
    # Classification and `next_action` always see the FULL `hazard_answer`
    # (`_classify_forward_hazard`/`_answer_next_action` run on the uncapped per_model
    # list below) -- only the payload's own `hazard` field is shrunk for display, so
    # capping can never change what ACTIVE/NONE means.
    next_action_answer = _answer_next_action(
        area_id, state_answer=state_answer, hazard_answer=hazard_answer,
        accountability_answer=accountability_answer, verbose=verbose,
        refresh_ran=refresh, raw_at=at)
    # Finding: the "state" source_tag's epistemic_class
    # (LIVE_DATA_SYSTEM -> "LIVE_OBSERVATION" in the RKG) describes what KIND of system
    # this field structurally comes from, not whether THIS run's own data was actually
    # live -- a retained/offline snapshot run still points at the same live-capable
    # system, it just didn't get fresh data this time (that fact already lives in
    # `state.tag`/`state.notes`). Note it here too so the two don't read as
    # contradictory side by side.
    _state_note = "readout.py / live_water_level.py -- fresh measured/relayed, see inline tags"
    if (state_answer or {}).get("tag") == "OPEN":
        _state_note += (" (this run: UNKNOWN, no live data yet -- "
                         "epistemic_class names the system type, not this run's freshness)")
    source_tags = [
            _source_tag("state", "LIVE_DATA_SYSTEM", _state_note),
            _source_tag("hazard", None,
                        "no RKG node -- third-party weather-model output (Open-Meteo / MET "
                        "Norway, see sources/registry.yaml trust_tier=third_party), not a "
                        "FloodConnect equation; not registered in Toledo and not claimed as such"),
            _source_tag("accountability", None,
                        "no RKG node -- tools/kg/accountability.py reads the NATIONWIDE "
                        "topology/governance KG (output/thailand_water_kg.graphml + "
                        "thailand_water_governance_reference.json), which is not itself a "
                        "floodconnect_repo_kg.yaml node; each Q-answer carries its own tag, "
                        "see full output"),
            _source_tag("next_action", "COMMUNITY_DAG",
                        "community_dag.find_safe_route; FOUND/OPEN only, never a "
                        "guaranteed verdict"),
    ]
    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "at": at,
        "refresh": (refresh_report if (verbose or refresh_report is None)
                    else _compact_refresh_report(refresh_report)),
        "state": state_answer,
        "hazard": hazard_answer if verbose else _compact_hazard_for_display(hazard_answer),
        "accountability": accountability_answer,
        "next_action": next_action_answer,
        "source_tags": source_tags if verbose else _compact_source_tags(source_tags),
    }
    # F8 (2026-10-04): `cctv` carries the full `{kind, radius_km, cameras}` shape when
    # there is at least one camera (token-budget measurement; a full wrapper on every
    # answer cost real margin for little value). this/F8 fix (2026-10-04):
    # the key was previously OMITTED entirely when `cameras` was empty -- MEASURED by
    # a later measurement pass on an offline fresh clone (no DB, no camera catalog
    # fetched yet): the answer had only 3 blocks (state/hazard/accountability/
    # next_action), never the 4th `cctv` block F8's own acceptance criterion requires.
    # A compact `{tag: OPEN, next_action}` (far cheaper than the full wrapper) is
    # emitted instead of omitting the key outright, so every answer always has a
    # `cctv` block, present or honestly OPEN -- never silently missing.
    if cctv_answer.get("cameras"):
        out["cctv"] = cctv_answer
    else:
        out["cctv"] = {"tag": "OPEN", "next_action": RUN_REFRESH_ACTION}
    return out


def cmd_answer(args) -> int:
    sys.path.insert(0, str(HERE))

    def _print_refresh_progress(refresh_report):
        n_skipped = sum(1 for r in refresh_report if r["skipped"])
        n_fail = sum(1 for r in refresh_report if not r["ok"] and not r["skipped"])
        n_ok = len(refresh_report) - n_skipped - n_fail
        if not args.json:
            print(f"--refresh: {len(refresh_report)} wired source(s) this run -- "
                  f"{n_ok} ok, {n_skipped} skipped (no fetcher by design/not "
                  f"implemented), {n_fail} unavailable.")
            for r in refresh_report:
                if not r["ok"] and not r["skipped"]:
                    print(f"  UNKNOWN reason: {r['id']}: {r['note']}")

    # Refresh-by-default (project decision 2026-10-03): `answer`/`compute` now fetches the
    # area-relevant sources on THIS machine's own network/keys every run, same as
    # `--refresh` always did, UNLESS `--offline` is passed. A failed fetch (one source
    # or all of them, e.g. no network) is not fatal -- `_refresh_relevant_sources`
    # already reports ok=False per source and leaves the DB's existing stored rows in
    # place, and every reading (fresh or carried over) still goes through the single
    # freshness gate below before it can decide anything. `--refresh` is still accepted,
    # now a no-op (refresh is already the default) kept only for old scripts/muscle
    # memory; it is an error to pass both `--refresh` and `--offline`.
    if getattr(args, "refresh", False) and getattr(args, "offline", False):
        print("ERROR: --refresh and --offline are mutually exclusive "
              "(refresh is now the default; --offline opts out of it).", file=sys.stderr)
        return 2
    refresh = not getattr(args, "offline", False)
    try:
        payload = build_answer(args.at, refresh=refresh,
                                on_refresh_progress=_print_refresh_progress,
                                verbose=getattr(args, "verbose", False),
                                all_sources=getattr(args, "all_sources", False))
    except _BadAt as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.json:
        import json as _json
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"# floodconnect answer -- {args.at} ({payload['generated_at']})")
    print(f"สถานะปัจจุบัน [{payload['state'].get('tag')}]:")
    for n in payload["state"].get("notes", []):
        print(f"  - {n}")
    # FIX (2026-10-03): print the `evidence` rows that actually decided
    # the colour (station/value/status/observed_at/age_h), plus the STALE ones
    # explicitly marked "not used for the decision" -- a non-verbose answer used to show
    # a bare `ปัจจุบัน=RED`/colour word with no station/value/observed_at behind it at
    # all, which is exactly what let a caller relay a stale station's status word as if
    # it were current (the founder's own complaint this bug report opened with).
    _evidence = payload["state"].get("evidence") or []
    _total_ev = payload["state"].get("evidence_total_count", len(_evidence))

    def _fmt_evidence_line(e: dict) -> str:
        _age = e.get("age_h")
        _age_str = f"{_age:.1f}ชม." if isinstance(_age, (int, float)) else "-"
        # Non-verbose `evidence` rows are trimmed to {station, status, age_h,
        # used_for_decision} (this + token-budget fix, 2026-10-03) -- `value`/
        # `unit`/`source`/`observed_at_utc` only exist on the UNCAPPED `--verbose` rows,
        # so print them only when present rather than a confusing literal "None".
        if "value" in e:
            val = f"{e.get('value')}{e.get('unit') or ''} "
            tail = f" observed_at={e.get('observed_at_utc')} source={e.get('source')}"
        else:
            val, tail = "", ""
        return f"    - {e.get('station')}: {val}[{e.get('status')}] (age={_age_str}){tail}"

    # fix (2026-10-04): a `used_for_decision=False` row is excluded for
    # ONE of two different reasons -- genuinely too old (`stale=True`) OR fresh but
    # geo-excluded (canal_outer / no coordinate / outside radius, `stale=False`).
    # MEASURED later: 10 fresh (4.8h old) geo-excluded DDS rows
    # were printed under a single "ค่าที่มีแต่เก่าเกินเกณฑ์" ("too old") label, which is
    # false for a fresh row. The two reasons now get two separate, honest labels.
    _used = [e for e in _evidence if e.get("used_for_decision")]
    _not_used_stale = [e for e in _evidence
                        if not e.get("used_for_decision") and e.get("stale")]
    _not_used_geo = [e for e in _evidence
                      if not e.get("used_for_decision") and not e.get("stale")]
    if _used:
        print("  หลักฐานที่ใช้ตัดสิน (used_for_decision=true):")
        for e in _used:
            print(_fmt_evidence_line(e))
    if _not_used_stale:
        print("  ค่าที่มีแต่เก่าเกินเกณฑ์ -- ไม่ถูกใช้ตัดสิน (stale=true, used_for_decision=false):")
        for e in _not_used_stale:
            print(_fmt_evidence_line(e) + " -- เก่าเกินเกณฑ์ ไม่ถูกใช้ตัดสิน")
    if _not_used_geo:
        print("  ค่าสดแต่อยู่นอกรัศมี/ไม่มีพิกัดยืนยัน -- ไม่ถูกใช้ตัดสิน (stale=false, "
              "used_for_decision=false):")
        for e in _not_used_geo:
            print(_fmt_evidence_line(e) + " -- นอกรัศมี/ไม่มีพิกัด ไม่ถูกใช้ตัดสิน (ไม่ใช่ค่าเก่า)")
    # FIX (2026-10-04, F-evidence-priority): one line counting STALE rows not used --
    # reuses `state.stale_count` (uncapped, already computed by `_answer_state` before
    # `_trim_evidence` ever runs) rather than re-deriving or re-storing this count a
    # second time inside the capped `evidence` list itself (which would cost real
    # tokens on every JSON answer for a number already available for free). Non-verbose
    # `evidence` never shows a stale row at all (`_TOP_N_EVIDENCE_STALE_IN_SUMMARY=0`),
    # so every stale row this check is, by definition, "not shown" here.
    _stale_count = payload["state"].get("stale_count") or 0
    if _stale_count and not getattr(args, "verbose", False):
        print(f"  (+{_stale_count} ค่าเก่าเกินเกณฑ์ -- ไม่ถูกใช้ตัดสิน ไม่แสดงในสรุปนี้)")
    if _total_ev > len(_evidence):
        print(f"  ({_total_ev} แถวทั้งหมดในการตรวจนี้ -- แสดงตัวอย่าง {len(_evidence)} "
              "แถว, ใช้ --verbose เพื่อดูทั้งหมด)")
    print(f"แนวโน้มฝน (RELAYED, โมเดลภายนอก) จุด {payload['hazard'].get('point_id')}:")
    # Show the forecast cache's own issued_at age (this: "rain forecast lines
    # show no issued_at age") once, before the per-model lines it covers -- every model
    # line below shares the SAME issued_at/stale (see `_forecast_rows_by_model`'s own
    # docstring: one cache refresh covers every model for a point).
    _hz_issued_at = payload["hazard"].get("issued_at")
    if _hz_issued_at:
        try:
            import live_water_level as _lwl_mod
            _now_iso = payload["generated_at"]
            _hz_fresh, _hz_age_h = _lwl_mod.is_fresh(_hz_issued_at, _now_iso,
                                                      _FORECAST_STALE_AFTER_H)
            _hz_age_str = f"{_hz_age_h:.1f}ชม." if _hz_age_h is not None else "-"
        except Exception:
            _hz_age_str = "-"
        print(f"  issued_at={_hz_issued_at} (age={_hz_age_str}, "
              f"stale={bool(payload['hazard'].get('stale'))})")
    # FIX D (2026-10-04): the offline-snapshot ensemble-summary print branch this used
    # to have is removed along with the tracked snapshot fallback -- a hazard answer
    # with no `per_model` is now always OPEN/UNKNOWN, so print its note plainly instead
    # of a retained-snapshot summary that no longer exists.
    if not payload["hazard"].get("per_model"):
        hz = payload["hazard"]
        print(f"  - {hz.get('note') or 'UNKNOWN -- ' + RUN_REFRESH_ACTION}")
    for m in payload["hazard"].get("per_model", []):
        print(f"  - {m['model']}: พรุ่งนี้ {m.get('tomorrow_mm')} มม. / "
              f"รวม {m.get('total_days', 7)} วัน {m.get('7day_total_mm')} มม.")
    acct = payload["accountability"]
    # Finding: "(ไม่พบในรัศมีนี้)" ("not found in this radius") used to
    # be the unconditional fallback whenever owner_agencies was empty -- including when
    # the REAL reason is "no graph built yet" (acct["refused"]/acct["note"], e.g. a fresh
    # install with no output/*.graphml), which reads very differently from "there is
    # nothing here". Show the real reason when one is on record; only fall back to the
    # radius wording when accountability genuinely has none.
    _acct_empty_reason = acct.get("refused") or acct.get("note")
    _acct_owner_text = (", ".join(acct.get("owner_agencies") or [])
                         or (f"ไม่มีคำตอบ -- {_acct_empty_reason}" if _acct_empty_reason
                             else "(ไม่พบในรัศมีนี้)"))
    print(f"ผู้รับผิดชอบ [{acct.get('tag')}]: {_acct_owner_text}")
    na = payload["next_action"]
    if na.get("found"):
        print(f"เส้นทางที่เป็นไปได้ [{na.get('tag')}]: {' -> '.join(na.get('path') or [])}")
    else:
        print(f"เส้นทาง [{na.get('tag')}]: {na.get('reason') or na.get('note')}")
    ds = na.get("dual_state") or {}
    if ds:
        print(f"สถานะคู่ [dual-state]: ปัจจุบัน={ds.get('current_local_state')} / "
              f"แนวโน้ม={ds.get('forward_hazard')}")
    for i, act in enumerate(na.get("actions") or [], 1):
        # Finding: `source` is intentionally dropped from each action
        # in non-verbose mode (see `_answer_next_action`'s own `capped_actions` step,
        # token-budget discipline) -- printing it here always showed a bare "[None]".
        # `tag` (OPEN/MEASURED/RELAYED/...) survives in both modes and is what this line
        # actually means to show.
        print(f"  {i}. [{act.get('tag')}] {act.get('action')}")
    for n in na.get("notes") or []:
        print(f"  หมายเหตุ: {n}")
    # F8 (2026-10-04): nearest CCTV cameras -- VISUAL-CHECK only, printed as a plain
    # reference list, never worded as evidence for any of the lines above.
    cctv = payload.get("cctv") or {}
    cams = cctv.get("cameras") or []
    if cams:
        # fix: cameras are no longer capped at `radius_km` (see
        # `_nearest_cctv_cameras`'s own docstring) -- a camera beyond it is still shown,
        # flagged "(>{radius_km} กม.)" instead of silently vanishing.
        print(f"กล้อง CCTV ที่ใกล้ที่สุด {len(cams)} ตัว [VISUAL-CHECK] "
              "(ดูเองเท่านั้น ไม่ใช่หลักฐานตัดสิน):")
        for c in cams:
            far_note = "" if c.get("within_radius") else f" (>{cctv.get('radius_km')} กม.)"
            print(f"  - {c.get('name')} ({c.get('distance_km')} กม.{far_note}): "
                  f"{c.get('url') or 'ไม่มีลิงก์'}")
    print("\nข้อมูลนี้เป็นข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำสั่งอพยพ "
          "-- เหตุฉุกเฉิน 1669 / ภัยพิบัติ 1784 / กทม. 1555 / กฟน.(ไฟฟ้าช็อตจากน้ำท่วม) 1130")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="kb.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_find = sub.add_parser("find", help="Case-insensitive search over docs/ + registry.yaml")
    p_find.add_argument("term")
    p_find.set_defaults(func=cmd_find)

    p_ask = sub.add_parser("ask", help="Look up a question-bank row + docs that answer it")
    p_ask.add_argument("qid")
    p_ask.set_defaults(func=cmd_ask)

    p_status = sub.add_parser("status", help="Print the question bank's coverage summary")
    p_status.set_defaults(func=cmd_status)

    p_sources = sub.add_parser("sources", help="List registry sources + last-seen timestamp")
    p_sources.set_defaults(func=cmd_sources)

    p_history = sub.add_parser("history", help="Delegate to readout_history.py")
    p_history.add_argument("--days", type=int, default=7)
    p_history.add_argument("--area")
    p_history.add_argument("--kind")
    p_history.set_defaults(func=cmd_history)

    p_reindex = sub.add_parser("reindex", help="Rebuild docs/knowledge/INDEX.yaml")
    p_reindex.set_defaults(func=cmd_reindex)

    p_acct = sub.add_parser(
        "accountability",
        help="Who is responsible here / overlapping authority / problematic law / "
             "self-help actions (see tools/kg/accountability.py)")
    p_acct.add_argument("--at", required=True,
                         help="'lat,lon' | area_id (sammakorn, ram53) | asset_id")
    p_acct.add_argument("--radius", type=float, default=3.0, help="km, default 3.0")
    p_acct.add_argument("--json", action="store_true")
    p_acct.set_defaults(func=cmd_accountability)

    p_forecast = sub.add_parser(
        "forecast",
        help="Per-model rain forecast (tomorrow + 7-day total) for a resolved point")
    p_forecast.add_argument("--at", required=True,
                             help="'lat,lon' or one of collect.FORECAST7D_POINTS "
                                  "(sammakorn, ram53, bangkok_east, c2_nakhonsawan, "
                                  "c13_chaophraya_dam, hatyai, nan, chiangmai)")
    p_forecast.add_argument("--offline", action="store_true",
                             help="Opt OUT of the default live refresh -- read only "
                                  "the stored DB, no network this run.")
    p_forecast.set_defaults(func=cmd_forecast)

    p_answer = sub.add_parser(
        "answer", aliases=["compute"],
        help="Minimal AI-entrypoint compute: state + hazard + accountability + "
             "next_action + source_tags for one area (see AI.md)")
    p_answer.add_argument("--at", required=True,
                           help="area_id (sammakorn, ram53) or 'lat,lon'")
    p_answer.add_argument("--json", action="store_true")
    p_answer.add_argument("--refresh", action="store_true",
                           help="Deprecated/no-op (2026-10-03): refresh is now the "
                                "default behaviour, kept only for old scripts. Fetches "
                                "the area-relevant wired sources on THIS machine's own "
                                "network/keys before computing (one GET per source, no "
                                "retries, no scheduler -- see 'On-demand refresh' in "
                                "AI.md).")
    p_answer.add_argument("--offline", action="store_true",
                           help="Opt OUT of the default live refresh -- use only the "
                                "stored DB (no network this run). Use this when offline "
                                "or to avoid hitting upstream sources.")
    p_answer.add_argument("--verbose", action="store_true",
                           help="Do not cap 'state.notes' source list to the top-N by "
                                "relevance -- print every DB-wide source name. Default "
                                "(omitted) keeps the AI.md token budget on a populated DB.")
    p_answer.add_argument("--all", dest="all_sources", action="store_true",
                           help="Default refresh fetches ONLY collect.ANSWER_SOURCES "
                                "(the sources that actually feed this answer). Pass "
                                "--all to fetch the full wired-source sweep instead. "
                                "No effect with --offline.")
    p_answer.set_defaults(func=cmd_answer)

    p_connectors = sub.add_parser(
        "connectors",
        help="Health of wired upstream connectors: dry=fixture coverage, "
             "--live=one real request per source on the caller's own network")
    p_connectors.add_argument("--live", action="store_true",
                               help="Make one real request per wired source (caller's "
                                    "own network/keys). Default is dry (no network).")
    p_connectors.set_defaults(func=cmd_connectors)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
