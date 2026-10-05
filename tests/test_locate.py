"""Tests for tools/kg/locate.py against the real committed output/kg_index/
(M4 acceptance points A2). Skipped (not failed) when the index is absent."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools.kg.locate import KGIndexMissing, locate  # noqa: E402

KG_INDEX_DIR = HERE / "output" / "kg_index"

pytestmark = pytest.mark.skipif(
    not (KG_INDEX_DIR / "index.json").exists(),
    reason="output/kg_index/ absent in this checkout",
)

ACCEPTANCE_POINTS = {
    "pathum": (14.0208, 100.5343),
    "chiang_mai": (18.79, 98.98),
    "sai_buri": (6.70, 101.62),
    "ubon": (15.24, 104.85),
    "sammakorn": (13.7656, 100.6478),
    "sammakorn_kb_py": (13.758235, 100.676084),
}


@pytest.mark.parametrize("name,point", ACCEPTANCE_POINTS.items())
def test_acceptance_points_resolve_under_budget_and_time(name, point):
    lat, lon = point
    t0 = time.time()
    result = locate(lat, lon)
    dt = time.time() - t0
    text = json.dumps(result, ensure_ascii=False)
    assert len(text) <= 6000, f"{name}: locate output is {len(text)} chars, over the 6,000 cap"
    assert dt < 3.0, f"{name}: locate took {dt:.3f}s, over the 3s budget"
    assert "kg_anchor" in result
    assert result["kg_anchor"].get("kg_sha256")
    # Either resolved to one province or handed back candidates -- never silent.
    assert result.get("province") or result.get("cand")


def test_pathum_point_with_no_province_returns_candidates_including_12_and_13():
    result = locate(14.0208, 100.5343)
    assert result["province"] is None
    assert result["method"] == "cand"
    codes = {c["code"] for c in result["cand"]}
    assert "12" in codes and "13" in codes, (
        f"expected both Nonthaburi (12) and Pathum Thani (13) among candidates, got {codes}"
    )
    assert len(result["cand"]) <= 3


@pytest.mark.parametrize("province_arg", ["13", "ปทุมธานี"])
def test_pathum_point_with_explicit_province_resolves_as_caller(province_arg):
    result = locate(14.0208, 100.5343, province=province_arg)
    assert result["method"] == "caller"
    assert result["province"] == "13"
    assert result["kg_anchor"]["province"] == "13"
    assert "cand" not in result["kg_anchor"]


def test_unknown_province_name_returns_error_with_candidates_never_a_guess():
    result = locate(14.0208, 100.5343, province="Nowhereland")
    assert result.get("error") == "province not recognised"
    assert result.get("cand")
    assert "province" not in result or result["province"] is None


def test_sammakorn_slice_10_asset_among_nearest():
    lat, lon = ACCEPTANCE_POINTS["sammakorn"]
    result = locate(lat, lon)
    assert result["nearest_assets"], "no nearest_assets returned for Sammakorn"
    # Sammakorn is firmly inside Bangkok (province 10).
    assert result["province"] == "10" or "10" in [c["code"] for c in result.get("cand", [])]


def test_kg_index_missing_raises(tmp_path):
    with pytest.raises(KGIndexMissing):
        locate(13.0, 100.0, index_dir=str(tmp_path))


def test_pathum_cand_mode_never_names_one_provinces_governor_as_the_answer():
    """HIGH fix regression: a 5-nearest-asset vote previously put this exact
    point's `agencies` field under Nonthaburi alone (the pitfall the M4 spec
    names by name), which an AI would relay as "who is responsible" for a
    point that could just as well be Pathum Thani."""
    result = locate(14.0208, 100.5343)
    assert result["method"] == "cand"
    assert result["province"] is None
    codes = {c["code"] for c in result["cand"]}
    assert "12" in codes and "13" in codes
    # agencies must be keyed per candidate code, never a single flat list
    # that silently picks one candidate's answer for the whole point.
    assert isinstance(result["agencies"], dict)
    assert set(result["agencies"]) == codes
    # Every candidate's own agency ids are present and distinct where the
    # provinces differ (Pathum's governor is not Nonthaburi's governor).
    ntb_ids = {a["id"] for a in result["agencies"]["12"]}
    ptt_ids = {a["id"] for a in result["agencies"]["13"]}
    assert "AG_PROV_GOV_NTB" in ntb_ids
    assert "AG_PROV_GOV_PTT" in ptt_ids
    assert "AG_PROV_GOV_NTB" not in ptt_ids
    assert "AG_PROV_GOV_PTT" not in ntb_ids


def test_cand_entries_and_kg_anchor_are_tagged_relayed():
    result = locate(14.0208, 100.5343)
    assert result["method"] == "cand"
    for c in result["cand"]:
        assert c["tag"] == "RELAYED"
    assert result["kg_anchor"]["province_tag"] == "RELAYED"


def test_known_gaps_keyed_per_candidate_code_not_truncated_to_first_two():
    result = locate(14.0208, 100.5343)
    assert result["method"] == "cand"
    codes = {c["code"] for c in result["cand"]}
    assert isinstance(result["known_gaps"], dict)
    assert set(result["known_gaps"]) == codes


def test_english_province_name_resolves_pathum_thani():
    result = locate(14.0208, 100.5343, province="Pathum Thani")
    assert result["method"] == "caller"
    assert result["province"] == "13"


def test_stations_exclude_rain_only_gauges():
    result = locate(14.0208, 100.5343)
    for s in result["stations"]:
        assert not s["id"].startswith("gauge:thaiwater_rain:"), (
            f"a rainfall-only gauge {s['id']!r} was returned as a 'station'"
        )
