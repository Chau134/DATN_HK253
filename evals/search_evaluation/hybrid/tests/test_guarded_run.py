import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/19_guarded_run.py"


@pytest.mark.parametrize("code,state", [
    ("print('checkpoint', flush=True)", "completed"),
    ("raise RuntimeError('test failure')", "failed"),
    ("import time; print('checkpoint', flush=True); time.sleep(30)", "timed_out"),
])
def test_supervisor_persists_exit_and_bounds_hung_child(tmp_path, code, state):
    child = tmp_path / "child.py"
    child.write_text(code, encoding="utf-8")
    output = tmp_path / "run"
    subprocess.run([sys.executable, str(SCRIPT), "--output", str(output), "--timeout", "1", str(child)], check=True, timeout=15)
    status = json.loads((output / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == state
    assert "finished_at" in status
    assert (output / "progress.log").read_text(encoding="utf-8")
