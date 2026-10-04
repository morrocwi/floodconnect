"""
tools/harvest/hii_flood_area_ckan.py -- ONE-OFF static harvester (not part of collect.py
--all -- the source dataset is a 17-year historical aggregate, 2005-2021, that does not
change run to run).

Founder gap (2026-09-27, docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_
2026-09-27.md #9): historical flood-frequency baseline for PROP-FLOOD-08's D_critical
calibration. HII (สสน.) CKAN portal `flood-area` dataset: monthly flood-risk frequency
per tambon, 2005-2021 (GISTDA satellite imagery aggregate), licence Creative Commons
Attribution Non-Commercial.

FOUNDER RULING 2026-09-27 (verbatim): "ใช้ได้เพราะอันนี้ไม่ใช่พาณิชย์ อัพขึ้น git ได้เลย"
-- FloodConnect is non-commercial, so this derived data may be committed to git and shown
on the public page. Applied here: `public_page: true`, licence field "CC BY-NC (HII open
data)", an attribution line every page use must render, and a `licence_ruling` field
recording the ruling itself. The RAW CSV download stays under raw/ (gitignored, per this
repo's own .gitignore) -- only the derived per-district YAML below is committed.

This is a FREQUENCY baseline (times flooded per month across 17 years), NOT a per-date
event record -- it does not directly backfill flood_road's daily history. Restricted to
"east side" districts (the ones this repo's own bkk_district_elevation.yaml already
covers as Sammakorn's neighbourhood): หนองจอก, บางกะปิ, มีนบุรี, ลาดกระบัง, บึงกุ่ม,
ประเวศ, คันนายาว, สะพานสูง -- not a nationwide dump (27,024 rows total in the source CSV;
this file keeps only the rows this repo's own area of concern needs).

Usage:
    python3 tools/harvest/hii_flood_area_ckan.py
        -> downloads the CSV ONCE into raw/hii_flood_area/ (gitignored)
        -> writes docs/knowledge/hii_flood_area_2005_2021_east.yaml (committed)
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
RAW_DIR = REPO_ROOT / "raw" / "hii_flood_area"
OUT_PATH = REPO_ROOT / "docs" / "knowledge" / "hii_flood_area_2005_2021_east.yaml"

REQUEST_TIMEOUT_S = 60
GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}

PACKAGE_SHOW_URL = "https://data.hii.or.th/api/3/action/package_show?id=flood-area"
CSV_RESOURCE_URL_FALLBACK = (
    "https://data.hii.or.th/dataset/8b0a19f0-flood-area/resource/download/"
    "monthly-flood-risk-area.csv"
)

# East-side districts this repo already tracks (sources/bkk_district_elevation.yaml,
# Sammakorn's own neighbourhood) -- AMPHOE_T values as they appear in the CSV.
EAST_DISTRICTS_TH = [
    "เขตหนองจอก", "เขตบางกะปิ", "เขตมีนบุรี", "เขตลาดกระบัง",
    "เขตบึงกุ่ม", "เขตประเวศ", "เขตคันนายาว", "เขตสะพานสูง",
]

LICENCE_RULING = ("founder 2026-09-27: non-commercial use OK, commit + public page "
                   "(verbatim: \"ใช้ได้เพราะอันนี้ไม่ใช่พาณิชย์ อัพขึ้น git ได้เลย\")")
ATTRIBUTION_TH = "ที่มา: สถาบันสารสนเทศทรัพยากรน้ำ (สสน.) — data.hii.or.th, CC BY-NC"


def resolve_csv_url() -> str:
    """One GET against package_show to find the actual resource URL -- the exact CSV
    path can change per CKAN revision, so this is read from the package metadata rather
    than hardcoded, with a hardcoded fallback only if package_show itself fails."""
    try:
        req = urllib.request.Request(PACKAGE_SHOW_URL, headers=GENERIC_HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            data = json.loads(resp.read())
        resources = (data.get("result") or {}).get("resources") or []
        for r in resources:
            url = r.get("url") or ""
            if url.lower().endswith(".csv"):
                return url
    except Exception:  # noqa: BLE001 -- fall through to the hardcoded fallback
        pass
    return CSV_RESOURCE_URL_FALLBACK


def download_csv_once(csv_url: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "monthly-flood-risk-area.csv"
    req = urllib.request.Request(csv_url, headers=GENERIC_HEADERS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        status, body = resp.status, resp.read()
    if status != 200:
        raise RuntimeError(f"hii_flood_area_ckan: HTTP {status}")
    out_path.write_bytes(body)
    return out_path


def extract_east_rows(csv_path: Path, districts_th=EAST_DISTRICTS_TH) -> list:
    """Pure function over an already-downloaded CSV path -> a list of row dicts for the
    named districts only. Handles the CSV's own BOM (see its first column header
    starting with ﻿, observed in this check's own sample)."""
    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            amphoe = (r.get("AMPHOE_T") or "").strip()
            if amphoe not in districts_th:
                continue
            try:
                month = int(r["Month"])
                count17 = int(r["COUNT 17 YEAR"])
            except (KeyError, ValueError):
                continue
            rows.append({
                "month": month,
                "geocode": r.get("GEOCODE"),
                "tambon_th": r.get("TAMBON_T"),
                "tambon_en": r.get("TAMBON_E"),
                "amphoe_th": amphoe,
                "amphoe_en": r.get("AMPHOE_E"),
                "province_th": r.get("PROV_T"),
                "count_17_year": count17,
                "criteria_th": r.get("CRITERIA"),
                "risk_th": r.get("RISK"),
            })
    return rows


def build_output(rows: list) -> dict:
    return {
        "_meta": {
            "generated": "2026-09-27",
            "source": "HII (สสน.) CKAN 'flood-area' dataset -- monthly flood-risk area "
                       "frequency, 2005-2021 (GISTDA satellite imagery aggregate)",
            "url": PACKAGE_SHOW_URL,
            "licence": "CC BY-NC (HII open data)",
            "licence_ruling": LICENCE_RULING,
            "attribution_required": ATTRIBUTION_TH,
            "public_page": True,
            "tag": "VERIFIED",
            "kind": "17-year monthly flood-frequency BASELINE, NOT a per-date event "
                    "record -- calibration prior for PROP-FLOOD-08 D_critical, never "
                    "used directly as an urban_event_ledger row.",
            "scope": "east-side districts only (Sammakorn's own neighbourhood per "
                     "sources/bkk_district_elevation.yaml) -- see EAST_DISTRICTS_TH in "
                     "this file's own harvester script for the full list, not a "
                     "nationwide dump.",
            "row_count": len(rows),
        },
        "rows": rows,
    }


def main() -> int:
    csv_url = resolve_csv_url()
    csv_path = download_csv_once(csv_url)
    rows = extract_east_rows(csv_path)
    out = build_output(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Downloaded {csv_path} ; wrote {OUT_PATH} ({len(rows)} row(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
