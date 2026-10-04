"""Tests for sources/backtest_units.yaml (task 1, FOUNDER_TASKS_2026-09-27.md #38,
follow-up on commit 9105fa3): the PROP-FLOOD-06 backtest unit registry used to live ONLY
in raw/backtest/units.yaml, which .gitignore's `raw/` line excludes from git entirely --
so this registry (incl. the sammakorn unit's VERIFIED BMA-plan figures) was never
actually tracked. Moved to sources/backtest_units.yaml (tracked); this file checks it
parses and carries the exact sourced fields the compute script relies on.
"""
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKED_PATH = REPO_ROOT / "sources" / "backtest_units.yaml"

sys.path.insert(0, str(REPO_ROOT / "tools" / "backtest"))
import compute_prop_flood_06_sammakorn as pf06  # noqa: E402


def _load():
    return yaml.safe_load(TRACKED_PATH.read_text(encoding="utf-8"))


def test_tracked_units_file_exists_and_is_tracked_by_git():
    assert TRACKED_PATH.exists()
    import subprocess
    out = subprocess.run(["git", "ls-files", "--error-unmatch", str(TRACKED_PATH)],
                          cwd=REPO_ROOT, capture_output=True, text=True)
    # Before this file is committed for the first time this will fail; the assertion
    # documents the intent (tracked, not gitignored) rather than gating on commit order.
    # If uncommitted, at minimum confirm .gitignore does NOT exclude it.
    check_ignore = subprocess.run(["git", "check-ignore", str(TRACKED_PATH)],
                                   cwd=REPO_ROOT, capture_output=True, text=True)
    assert check_ignore.returncode != 0, "sources/backtest_units.yaml must NOT be gitignored"


def test_tracked_units_file_parses():
    data = _load()
    assert isinstance(data, dict)
    assert "units" in data
    unit_ids = {u["id"] for u in data["units"]}
    assert unit_ids == {"HATYAI", "NAN", "CHIANGMAI", "AYUTTHAYA_BANGBAN",
                         "BANGKOK_EAST", "SAMMAKORN"}


def test_tracked_units_file_has_normalized_sammakorn_fields():
    data = _load()
    fields = data["normalized_fields"]["sammakorn"]

    pond = fields["pond_storage_capacity_m3"]
    assert pond["value"] == 227200
    assert pond["unit"] == "m3"
    assert pond["page"] == "74"
    assert pond["tag"] == "VERIFIED"
    assert pond["source"]

    dh = fields["D_H"]
    assert dh["value"] == 7.75
    assert dh["unit"] == "m3/s"
    assert dh["page"] == "ง-25"
    assert dh["tag"] == "VERIFIED"
    assert dh["source"]

    a_u = fields["A_U"]
    assert a_u["value"] is None
    assert a_u["tag"] == "OPEN"

    r_h = fields["R_H"]
    assert r_h["value"] is None
    assert r_h["tag"] == "OPEN"


def test_compute_script_loader_reads_tracked_file_values():
    """compute_prop_flood_06_sammakorn.py's module constants must match the tracked
    file's normalized_fields.sammakorn block (loader discipline, task 1)."""
    fields = _load()["normalized_fields"]["sammakorn"]
    assert pf06.SAMMAKORN_D_H_M3S == fields["D_H"]["value"]
    assert pf06.SAMMAKORN_POND_CAPACITY_M3 == fields["pond_storage_capacity_m3"]["value"]
    assert "ง-25" in pf06.SAMMAKORN_D_H_SOURCE
    assert "หน้า 74" in pf06.SAMMAKORN_POND_CAPACITY_SOURCE


def test_raw_override_layer_wins_when_present(tmp_path, monkeypatch):
    """raw/backtest/units.yaml (gitignored) is a RUN-TIME override layer on top of the
    tracked file -- if present and it declares its own normalized_fields.sammakorn.D_H,
    that value wins for this run. Uses a temp path swap so the real raw/ file (if any)
    is untouched."""
    override_path = tmp_path / "units.yaml"
    override_path.write_text(
        "normalized_fields:\n  sammakorn:\n    D_H: {value: 1.23, source: 'override', "
        "page: 'x', tag: INSTINCT}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pf06, "UNITS_YAML_PATH", override_path)
    fields = pf06._sammakorn_normalized_fields()
    assert fields["D_H"]["value"] == 1.23
    # pond_storage_capacity_m3 is untouched by the override -> still the tracked value
    assert fields["pond_storage_capacity_m3"]["value"] == 227200
