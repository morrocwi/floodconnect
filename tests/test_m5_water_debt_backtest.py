"""Tests for tools/backtest/run_m5_water_debt.py (M5 water-debt backtest, EXPERIMENT,
PROP-FLOOD-03/PROP-FLOOD-10 PROPOSAL -- not yet in Toledo). No network."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNNER = REPO_ROOT / "tools" / "backtest" / "run_m5_water_debt.py"
RESULTS = REPO_ROOT / "docs" / "experiments" / "M5_results.jsonl"
EVENT_SET = REPO_ROOT / "docs" / "experiments" / "M5_event_set.yaml"

sys.path.insert(0, str(REPO_ROOT / "tools" / "backtest"))
sys.path.insert(0, str(REPO_ROOT))


def _run_and_capture(out_path: Path) -> str:
    """Run the runner with --out pointed at a tmp_path file -- NEVER at the tracked
    M5_results.jsonl."""
    subprocess.run([sys.executable, str(RUNNER), "--out", str(out_path)], check=True,
                    cwd=REPO_ROOT, capture_output=True, text=True)
    return out_path.read_text(encoding="utf-8")


def test_runner_reproduces_committed_results_byte_for_byte(tmp_path):
    committed = RESULTS.read_text(encoding="utf-8")
    fresh = _run_and_capture(tmp_path / "m5_results_fresh.jsonl")
    assert fresh == committed, "run_m5_water_debt.py must reproduce M5_results.jsonl byte-for-byte"


def test_every_row_is_well_formed_and_real_data_tagged():
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    assert len(rows) > 0
    for r in rows:
        assert r["cell"] in {"HIT", "MISS", "FALSE_ALARM", "CORRECT_NEG", "UNRESOLVED"}
        assert r["obs"] in {"EVENT", "NO_EVENT", "UNRESOLVED"}
        assert r["f_state"] in {"OK", "REFUSED"}
        # no row is ever reported as a resolved OK with a numeric result AND refused
        if r["f_state"] == "REFUSED":
            assert r["S_next_enclosure_m3"] is None
            assert r["reason_codes"]


def test_every_row_refused_missing_input_s0_and_gate_flag_in_this_dataset():
    """MEASURED finding: S0 (initial storage) AND gate_flag are BOTH undeclared/missing
    on every single one of the 219 rows -- gate_flag is never passed by this runner for
    any node, exactly as universal a blocker as S0. This test pins that finding; it
    must be revisited (not silently deleted) the day S0 or gate_flag is ever
    declared/wired for any node."""
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 219
    for r in rows:
        assert r["f_state"] == "REFUSED"
        assert "S0" in r["inputs_missing"]
        assert "gate_flag" in r["inputs_missing"], "gate_flag must be missing on every row -- never declared/wired"
        assert "MISSING_INPUT" in r["reason_codes"]
    assert all(r["cell"] == "UNRESOLVED" for r in rows)


def test_q_out_meas_and_village_inputs_missing_counts_measured():
    """MEASURED: Q_out_meas is missing on 138/219 rows (pinned here to the actual
    measured count), and the two village rows (sammakorn/ram53) additionally lack A,
    c, C_pump, and P on top of S0/gate_flag."""
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    q_out_missing = sum("Q_out_meas" in r["inputs_missing"] for r in rows)
    assert q_out_missing == 138
    village = [r for r in rows if r["node_id"] in ("sammakorn", "ram53")]
    assert len(village) == 2
    for r in village:
        for field in ("A", "c", "C_pump", "P", "S0", "gate_flag"):
            assert field in r["inputs_missing"], f"{field} must be missing for {r['node_id']}"


def test_every_row_carries_toledo_status():
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 219
    assert all(r["toledo_status"] == "PROPOSAL -- not yet in Toledo" for r in rows)


def test_few_events_fires_for_the_real_n_independent_events():
    import yaml
    from score_forward_forecast import N_MIN
    event_set = yaml.safe_load(EVENT_SET.read_text(encoding="utf-8"))
    n_ind = event_set["n_independent_events"]
    assert n_ind == 6
    assert n_ind < N_MIN
    assert event_set["few_events"] is True


def test_few_events_threshold_boundary_logic():
    """Direct unit test of the FEW_EVENTS boundary (n < N_MIN), independent of the
    real dataset's actual count, matching run_m5_water_debt.py's own skill_claim
    construction."""
    from score_forward_forecast import N_MIN

    def skill_claim(n_ind: int) -> dict:
        return ({"state": "REFUSED", "reason": f"FEW_EVENTS (n_ind={n_ind} < N_min={N_MIN})"}
                if n_ind < N_MIN else {"state": "OPEN"})

    assert skill_claim(9)["state"] == "REFUSED"
    assert skill_claim(N_MIN)["state"] == "OPEN"
    assert skill_claim(N_MIN + 1)["state"] == "OPEN"


def test_c_enclosure_bound_declared_and_ordered():
    """c_U's [0.5, 1.0] bound is the one OPEN field this experiment propagates as an
    enclosure rather than refusing -- confirm every row's c_enclosure is the declared
    two-point bound, in sorted order, for the 5 national units (the balance nodes use
    a single declared c value, OPEN, so their enclosure degenerates to one point/None).
    This bound is declared on every row regardless of outcome; it is not exercised by
    any OK row in this dataset (every row REFUSES before the c-dependent arithmetic)."""
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    national = {"HATYAI", "NAN", "CHIANGMAI", "AYUTTHAYA_BANGBAN", "BANGKOK_EAST"}
    for r in rows:
        if r["node_id"] in national:
            assert r["c_enclosure"] == [0.5, 1.0]
            assert r["c_enclosure"] == sorted(r["c_enclosure"])
