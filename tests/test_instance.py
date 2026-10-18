import subprocess
import sys
from pathlib import Path

from pluck.adapters.instance import SingleInstance

ROOT = Path(__file__).resolve().parents[1]
CLAIM_AND_HOLD = """
import sys, time
sys.path.insert(0, sys.argv[2])
from PySide6.QtCore import QCoreApplication
from pluck.adapters.instance import SingleInstance
from pathlib import Path
app = QCoreApplication([])
instance = SingleInstance(Path(sys.argv[1]), "pluck")
print(instance.claim(), flush=True)
time.sleep(1.5)
"""


def test_second_instance_hands_over_to_the_first(qt_app, wait_until, tmp_path):
    first = SingleInstance(tmp_path, "pluck")
    activations = []
    first.activated.connect(lambda: activations.append(True))
    assert first.claim() is True
    second = SingleInstance(tmp_path, "pluck")
    assert second.claim() is False
    wait_until(lambda: activations == [True])
    first.release()


def test_stale_socket_does_not_block_a_new_instance(qt_app, tmp_path):
    crashed = SingleInstance(tmp_path, "pluck")
    assert crashed.claim() is True
    crashed.release()
    fresh = SingleInstance(tmp_path, "pluck")
    assert fresh.claim() is True
    fresh.release()


def test_socket_and_lock_stay_private(qt_app, tmp_path):
    directory = tmp_path / "runtime"
    instance = SingleInstance(directory, "pluck")
    assert instance.claim() is True
    assert directory.stat().st_mode & 0o077 == 0
    assert (directory / "pluck.sock").exists()
    instance.release()


def test_simultaneous_launches_elect_a_single_instance(tmp_path):
    launches = [
        subprocess.Popen(
            [sys.executable, "-c", CLAIM_AND_HOLD, str(tmp_path), str(ROOT)],
            stdout=subprocess.PIPE,
            text=True,
        )
        for _ in range(6)
    ]
    results = [launch.communicate(timeout=30)[0].strip() for launch in launches]
    assert sorted(results) == ["False"] * 5 + ["True"]
