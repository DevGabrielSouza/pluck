import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT = ROOT / "tools" / "screenshot.py"
SCENARIOS = ("idle", "video", "audio", "playlist", "error", "loading", "settings", "empty")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_scenario_renders_without_qml_warnings(scenario, tmp_path):
    output = tmp_path / f"{scenario}.png"
    result = subprocess.run(
        [sys.executable, str(SCREENSHOT), scenario, str(output), "--wait", "0.8"],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert output.stat().st_size > 0


def test_confirm_dialog_answers_enter_on_the_focused_button():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "qml_dialog_keys.py")],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(ROOT)},
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == "", result.stderr
