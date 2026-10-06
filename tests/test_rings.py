"""Tests for `tools/kg/rings.py` (M8 P3) -- the KG neighbourhood extraction behind
the Jev Sandwich model. Reads ONLY the real, committed `output/kg_index/` (no live
network, no graphml load) -- per this project's rule "real data only in tests, never
simulated", every coordinate/id below resolves against the ACTUAL shipped KG.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_rings.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools.kg import rings as rings_mod  # noqa: E402

SAMMAKORN = (13.758235, 100.676084)
AYUTTHAYA_C67 = (14.33, 100.39)
PRACHINBURI_KGT1 = (14.0, 101.37)


def test_sammakorn_z0_resolves_to_its_own_bma_watermap_node():
    r = rings_mod.rings(*SAMMAKORN)
    assert r["z0"] is not None
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.SMK.01"
    assert r["z0"]["km"] < 3.0


def test_sammakorn_z1_carries_the_declared_outlet_to_saen_saep():
    # fix (S3, founder 2026-10-05): the OUTLET row maps to its READABLE M8 twin
    # (gauge:bma_watermap:*) when one exists in this KG, never the unreadable
    # gauge:thaiwater_bma:* node -- see tools/kg/rings.py's `_prefer_readable_twin`.
    r = rings_mod.rings(*SAMMAKORN)
    outlet_rows = [row for row in r["z1"] if row["relation"] == "OUTLET"]
    outlet_ids = {row["id"] for row in outlet_rows}
    assert "gauge:bma_watermap:WL.SSB.08" in outlet_ids
    for row in outlet_rows:
        assert row["contradicts"] is True
        assert row["ref"] == "site/inputs/canals/east_chain.yaml"


def test_sammakorn_z3_sub_basin_inherited_via_outlet_join_when_z0_has_none():
    """SAME_SUBBASIN membership survives `KG_ONLY_MODE` (see that flag's own
    docstring) -- it is a shared-polygon fact, not a guessed station-to-station
    join, and `kb.py`'s own outlet-consistency mechanism reads it."""
    assert rings_mod.KG_ONLY_MODE is True
    r = rings_mod.rings(*SAMMAKORN)
    assert r["z0"]["sb"] is None  # Z0 itself carries no IN_SUBBASIN (pv='b', no DWR archive)
    assert r["z3"]["sub_basin"] == "sub_basin:1002"
    assert r["z3"]["sb_basis"] == "OUTLET_JOIN"
    z3_ids = {row["id"] for row in r["z3"]["stations"]}
    # C.67 (Ayutthaya, real over-bank station used by the acceptance table) is a
    # real member of sub_basin:1002 -- MEASURED against the committed kg_index.
    assert "gauge:thaiwater_waterlevel:C.67" in z3_ids
    for row in r["z3"]["stations"]:
        assert row["relation"] == "SAME_SUBBASIN"


def test_ayutthaya_c67_area_z0_resolves_and_shares_sammakorns_subbasin():
    r = rings_mod.rings(*AYUTTHAYA_C67)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:CPY017"
    assert r["z0"]["sb"] == "sub_basin:1002"


def test_prachinburi_near_kgt1_resolves_to_kgt1():
    r = rings_mod.rings(*PRACHINBURI_KGT1)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:Kgt.1"


def test_no_gauge_within_radius_degrades_to_none_z0_not_a_guess():
    # Mid-ocean -- no gauge anywhere near, same outside-coverage shape every other
    # KG-reading function in this repo already uses (never crashes, never guesses).
    r = rings_mod.rings(7.0, 101.5)
    assert r["z0"] is None
    assert r["z1"] == [] and r["z2"] == []
    assert r["z3"] == {"sub_basin": None, "sb_basis": None, "basin": None,
                        "stations": [], "dams": [], "official": "NOT_WIRED"}


def test_ait00x_code_family_join_is_removed_entirely_under_kg_only_mode(monkeypatch):
    """Founder ruling 2026-10-06 (KG-only, no guessing -- supersedes the narrower
    same-canal refinement this test used to check): thaiwater's "AIT" code family
    is a bare agency code-prefix guess, never a declared KG edge -- under
    `KG_ONLY_MODE` it must not join AIT001 to AIT002/AIT003 AT ALL, not merely be
    relabelled SAME_CODE_FAMILY. AIT002 is on แม่น้ำเลย (Loei, ~471 km away),
    AIT003 on ห้วยน้ำฮวย -- neither may appear in AIT001's rings any more."""
    assert rings_mod.KG_ONLY_MODE is True
    real_river_name_cache = rings_mod._river_name_cache
    fixture = {
        "gauge:thaiwater_waterlevel:AIT001": "คลองแสนแสบ",
        "gauge:thaiwater_waterlevel:AIT002": "แม่น้ำเลย",
        "gauge:thaiwater_waterlevel:AIT003": "ห้วยน้ำฮวย",
    }

    def _fake_river_name_cache(index_dir):
        base = dict(real_river_name_cache(index_dir))
        base.update(fixture)
        return base

    monkeypatch.setattr(rings_mod, "_river_name_cache", _fake_river_name_cache)
    r = rings_mod.rings(13.74325, 100.56216)  # AIT001's own real committed coordinates
    assert r["z0"] is not None
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:AIT001"
    joined_ids = {row["id"] for row in (r["z1"] + r["z2"])}
    assert "gauge:thaiwater_waterlevel:AIT002" not in joined_ids
    assert "gauge:thaiwater_waterlevel:AIT003" not in joined_ids
    for row in r["z1"] + r["z2"]:
        assert row.get("basis") == "declared", row
    for row in r["z3"]["stations"]:
        assert row.get("basis") == "declared" or row.get("relation") == "SAME_SUBBASIN", row


def test_bbd04_code_family_join_is_removed_entirely_under_kg_only_mode(monkeypatch):
    """Founder ruling 2026-10-06 (KG-only): BBD04 (แม่น้ำปิง, Tak) must not be
    joined to BBD05/BBD09/BBD10 at all any more, declared-name-disagreement or
    not -- a bare code-prefix guess is dropped outright under `KG_ONLY_MODE`,
    never merely refused-but-attempted."""
    assert rings_mod.KG_ONLY_MODE is True
    real_river_name_cache = rings_mod._river_name_cache
    fixture = {
        "gauge:thaiwater_waterlevel:BBD04": "แม่น้ำปิง",
        "gauge:thaiwater_waterlevel:BBD05": "ห้วยแม่ท้อ",
        "gauge:thaiwater_waterlevel:BBD09": "แม่น้ำวัง",
        "gauge:thaiwater_waterlevel:BBD10": "แม่น้ำวัง",
    }

    def _fake_river_name_cache(index_dir):
        base = dict(real_river_name_cache(index_dir))
        base.update(fixture)
        return base

    monkeypatch.setattr(rings_mod, "_river_name_cache", _fake_river_name_cache)
    r = rings_mod.rings(16.8567, 99.12529)  # BBD04's own real committed coordinates
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:BBD04"
    joined_ids = {row["id"] for row in (r["z1"] + r["z2"])}
    for code in ("BBD05", "BBD09", "BBD10"):
        assert f"gauge:thaiwater_waterlevel:{code}" not in joined_ids


def test_ray002_is_never_joined_to_distant_same_name_canal_stations():
    """fix (founder ruling 2026-10-06): the verbatim canal-name join used to join
    RAY002 (Rayong) to X.77 (745 km away, Rayong) and X.276 (594 km) just
    because they share a คลองใหญ่ name token. Under `KG_ONLY_MODE` that join
    (basis NAME_JOIN, never declared) must not reach the ring at all."""
    assert rings_mod.KG_ONLY_MODE is True
    r = rings_mod.rings(12.84919, 101.30135)  # RAY002's own real committed coordinates
    assert r["z0"] is not None
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:RAY002"
    joined_ids = {row["id"] for row in (r["z1"] + r["z2"])}
    assert "gauge:thaiwater_waterlevel:X.77" not in joined_ids
    assert "gauge:thaiwater_waterlevel:X.276" not in joined_ids
    for row in r["z1"] + r["z2"]:
        assert row.get("basis") == "declared", row
    for row in r["z3"]["stations"]:
        assert row.get("basis") == "declared" or row.get("relation") == "SAME_SUBBASIN", row


def test_kiz003_is_never_joined_to_distant_same_name_canal_stations():
    """fix (founder ruling 2026-10-06): the verbatim canal-name join used to join
    KIZ003/Kgt.14A (ห้วยยาง) to TON001, 111 km away in a different basin. Under
    `KG_ONLY_MODE` that join must not reach the ring at all."""
    assert rings_mod.KG_ONLY_MODE is True
    r = rings_mod.rings(14.13641, 101.85747)  # KIZ003's own real committed coordinates
    assert r["z0"] is not None
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:KIZ003"
    joined_ids = {row["id"] for row in (r["z1"] + r["z2"])}
    assert "gauge:thaiwater_waterlevel:TON001" not in joined_ids
    for row in r["z1"] + r["z2"]:
        assert row.get("basis") == "declared", row
    for row in r["z3"]["stations"]:
        assert row.get("basis") == "declared" or row.get("relation") == "SAME_SUBBASIN", row


def test_wl_bbu01_never_joins_thaiwater_bbu_family_across_agencies(monkeypatch):
    """BMA's WL.BBU.01 (คลองบางบัว, Bangkok)
    must never be joined with plain thaiwater's BBU01/BBU02 (แม่น้ำปิง, 453+ km
    away) just because both reduce to the bare "BBU" letters once each agency's
    own sensor-type prefix is stripped -- never join across agencies on a code
    prefix."""
    real_river_name_cache = rings_mod._river_name_cache
    fixture = {
        "gauge:thaiwater_waterlevel:BBU01": "แม่น้ำปิง",
        "gauge:thaiwater_waterlevel:BBU02": "แม่น้ำปิง",
        "gauge:thaiwater_waterlevel:BBU04": "ห้วยแม่ตื่น",
    }

    def _fake_river_name_cache(index_dir):
        base = dict(real_river_name_cache(index_dir))
        base.update(fixture)
        return base

    monkeypatch.setattr(rings_mod, "_river_name_cache", _fake_river_name_cache)
    r = rings_mod.rings(13.85806, 100.58656)  # WL.BBU.01's own real committed coordinates
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.BBU.01"
    joined_ids = {row["id"] for row in (r["z1"] + r["z2"])}
    assert "gauge:thaiwater_waterlevel:BBU01" not in joined_ids
    assert "gauge:thaiwater_waterlevel:BBU02" not in joined_ids
    assert "gauge:thaiwater_waterlevel:BBU04" not in joined_ids


def test_y64_same_reach_as_n5a_is_removed_entirely_under_kg_only_mode(monkeypatch):
    """Founder ruling 2026-10-06 (KG-only, no guessing -- supersedes the
    river-name-mismatch demotion this test used to check): a reach-snap pair is
    `basis="DERIVED-snap"` (the geometric ON_REACH placement, never a declared
    edge) -- under `KG_ONLY_MODE`, Y.64's reach-snap neighbour N.5A must not
    appear in the ring at all any more, agreeing river names or not."""
    assert rings_mod.KG_ONLY_MODE is True
    real_river_name_cache = rings_mod._river_name_cache
    fixture = {
        "gauge:thaiwater_waterlevel:Y.64": "แม่น้ำยม",
        "gauge:thaiwater_waterlevel:N.5A": "แม่น้ำน่าน",
    }

    def _fake_river_name_cache(index_dir):
        base = dict(real_river_name_cache(index_dir))
        base.update(fixture)
        return base

    monkeypatch.setattr(rings_mod, "_river_name_cache", _fake_river_name_cache)
    r = rings_mod.rings(16.76212, 100.1212)  # Y.64's own real committed coordinates
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:Y.64"
    n5a_rows = [row for row in r["z1"] if row["id"] == "gauge:thaiwater_waterlevel:N.5A"]
    assert n5a_rows == []
    for row in r["z1"] + r["z2"]:
        assert row.get("basis") == "declared", row
    for row in r["z3"]["stations"]:
        assert row.get("basis") == "declared" or row.get("relation") == "SAME_SUBBASIN", row


def test_canal_code_guess_matches_declared_naming_pattern():
    assert rings_mod._canal_code_guess("canalchain:ssb08") == "WL.SSB.08"
    assert rings_mod._canal_code_guess("canalchain:sammakorn_pond") is None
    assert rings_mod._canal_code_guess("canalchain:banma") is None


def test_bbn01_same_station_tie_resolves_to_readable_m8_twin():
    """Regression (MEASURED 2026-10-05): WL.BBN.01's
    gauge:bma_watermap:/gauge:thaiwater_bma: twins sit at the IDENTICAL declared
    lat/lon (13.67055,100.42713), so they tie on distance. Before the fix, dict-
    iteration order let the unreadable gauge:thaiwater_bma: twin win 215/311 such
    ties; it must always resolve to the readable gauge:bma_watermap: node instead."""
    r = rings_mod.rings(13.67055, 100.42713)
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.BBN.01"
    assert r["z0"]["km"] < 0.01


def test_rings_result_is_json_serializable():
    import json
    r = rings_mod.rings(*SAMMAKORN)
    json.dumps(r, ensure_ascii=False)  # must not raise
