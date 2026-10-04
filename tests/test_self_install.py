"""Real self-install check for the `floodconnect` console script.

Audit finding (an earlier check): `pyproject.toml`'s `py-modules` list did not include
`tag_vocabulary`, even though `kb.py` imports it at module level
(`from tag_vocabulary import TAG_VOCABULARY as _TAG_VOCABULARY`). A real
`pip install -e '.[dev]'` into a fresh venv, run from a cwd outside the repo,
reproduced: `ModuleNotFoundError: No module named 'tag_vocabulary'`. This test
exists so that specific failure mode cannot regress silently -- README.md and
SKILL.md both document this exact command as the self-install entrypoint.

Uses `--system-site-packages` so the venv inherits already-installed
dependencies (pyyaml/requests/networkx/pytest/jsonschema/tiktoken -- the same
set `requirements-ci.txt` installs on a clean CI runner) instead of hitting
the network again; `--no-deps` on the editable install is correct here
because we are testing packaging metadata (which modules ship), not
dependency resolution. This is the "venv-less check" alternative the audit
allowed: no separate interpreter is downloaded, only a lightweight venv
layered on the current one.
"""
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def _observations_db_restored():
    """The installed console script runs as a real subprocess, so an in-process
    monkeypatch of kb.DB_PATH never reaches it -- `kb.py`'s module-level `HERE` always
    resolves to this repo's own `data/observations.sqlite` for an editable install, by
    design (see kb.py:39/45). Snapshot the real, git-ignored DB's bytes (or its
    absence) before the test and restore them after, same pattern as
    tests/test_kb.py's `_index_yaml_restored`, so this test never leaves a real
    recorded-data store changed as a side effect of exercising the install path.

    `store.connect()` runs under `PRAGMA journal_mode=WAL`, so the subprocess above
    also creates/rewrites the `-wal`/`-shm` sidecar files next to the main db file --
    restoring only the main file's bytes and leaving those two behind (or changed)
    still trips tests/conftest.py's session-wide real-data-store guard, so every
    sidecar path next to the main one is snapshotted/restored the same way."""
    path = REPO_ROOT / "data" / "observations.sqlite"
    sidecar_paths = [path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")]
    before = path.read_bytes() if path.exists() else None
    sidecars_before = [(p, p.read_bytes() if p.exists() else None) for p in sidecar_paths]
    try:
        yield path
    finally:
        for p, content in sidecars_before:
            if content is None:
                if p.exists():
                    p.unlink()
            else:
                p.write_bytes(content)
        if before is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(before)


@pytest.mark.skipif(
    shutil.which("python3") is None, reason="no python3 interpreter available"
)
def test_console_script_runs_after_real_pip_install_outside_repo(
    _observations_db_restored,
):
    with tempfile.TemporaryDirectory(prefix="floodconnect-selfinstall-") as tmp:
        tmp_path = Path(tmp)
        venv_dir = tmp_path / "venv"
        outside_cwd = tmp_path / "cwd-outside-repo"
        outside_cwd.mkdir()

        venv.EnvBuilder(system_site_packages=True, with_pip=True).create(venv_dir)
        venv_python = venv_dir / "bin" / "python"
        assert venv_python.exists(), "venv creation did not produce bin/python"

        install = subprocess.run(
            [
                str(venv_python), "-m", "pip", "install",
                "--no-deps", "--no-build-isolation", "-e", str(REPO_ROOT),
            ],
            cwd=str(outside_cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert install.returncode == 0, (
            f"pip install -e (no-deps) failed:\nstdout={install.stdout}\n"
            f"stderr={install.stderr}"
        )

        floodconnect_bin = venv_dir / "bin" / "floodconnect"
        assert floodconnect_bin.exists(), (
            "pip install did not create the `floodconnect` console script "
            f"at {floodconnect_bin}"
        )

        run = subprocess.run(
            # --offline: refresh is now the default (project decision 2026-10-03), but
            # this test's own concern is the installed console script wiring (does it
            # run at all from a cwd outside the repo), never a live network fetch --
            # without --offline this hit real upstream sources from inside the test
            # sandbox (ADDED raw/live/* files, a real regression found by this repo's
            # own session-write guard) and could hang past the 60s timeout below.
            [str(floodconnect_bin), "answer", "--at", "sammakorn", "--offline", "--json"],
            cwd=str(outside_cwd),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, (
            "installed `floodconnect` console script failed from a cwd "
            f"outside the repo:\nstdout={run.stdout}\nstderr={run.stderr}"
        )
        assert "ModuleNotFoundError" not in run.stderr
