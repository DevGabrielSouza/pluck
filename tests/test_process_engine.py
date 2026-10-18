import json
import os
import stat
from pathlib import Path

import pytest

from pluck.adapters import download_runner
from pluck.adapters.process import find_executable
from pluck.adapters.ytdlp.errors import CRASH_MESSAGE
from pluck.app import build_services
from pluck.domain import retry
from pluck.domain.jobs import RUNNING, Status
from pluck.presentation.downloads import DownloadManager
from tests.conftest import FAKE_YTDLP

VIDEO_OPTIONS = {"mode": "video", "quality": 1080, "container": "mp4", "audioFormat": "mp3"}


def alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return False
    return state not in ("Z", "X")


def records(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def logged(log: Path, key: str) -> list[int]:
    return [record[key] for record in records(log) if key in record]


@pytest.fixture
def log(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_YTDLP_LOG", str(path))
    return path


@pytest.fixture
def manager(build_settings, build_manager, tmp_path) -> DownloadManager:
    settings = build_settings(tmp_path / "settings.json")
    settings.update("folder", str(tmp_path / "Downloads"))
    return build_manager(settings, tmp_path / "history.json")


def start(manager: DownloadManager, url: str):
    manager.enqueue([{"url": url, "title": "Fake", "expectedSizes": [1000, 250]}], VIDEO_OPTIONS)
    return manager._model.jobs[0]


def test_every_ytdlp_runs_in_its_own_process_group(manager, log, wait_until):
    job = start(manager, "https://fake.test/video/ok")
    wait_until(lambda: job.status == Status.COMPLETED)
    record = records(log)[0]
    assert record["pgid"] == record["pid"] != os.getpgid(0)


def test_output_markers_are_unpredictable_per_run(manager, log, wait_until):
    first = start(manager, "https://fake.test/video/ok")
    wait_until(lambda: first.status == Status.COMPLETED)
    manager.retry(first.id)
    second = start(manager, "https://fake.test/other/ok")
    wait_until(lambda: second.status == Status.COMPLETED)
    templates = [
        next(value for value in record["argv"] if value.startswith("download:"))
        for record in records(log)
        if "argv" in record
    ]
    tokens = {template.split(" ", 1)[0].removeprefix("download:PLUCK_PROGRESS_") for template in templates}
    assert len(templates) == 2 and len(tokens) == 2
    assert all(len(token) == 16 and int(token, 16) >= 0 for token in tokens)


def test_cancel_also_stops_a_grandchild_that_ignores_sigint(manager, log, wait_until):
    job = start(manager, "https://fake.test/video/child")
    wait_until(lambda: job.detail != "" and logged(log, "child"))
    child = logged(log, "child")[0]
    manager.cancel(job.id)
    wait_until(lambda: job.status == Status.CANCELED)
    wait_until(lambda: not alive(child), 3.0)
    assert job.error == ""


def test_a_leader_that_ignores_sigint_is_killed_after_the_grace_period(manager, log, wait_until, monkeypatch):
    monkeypatch.setattr(download_runner, "CANCEL_GRACE_MS", 300)
    job = start(manager, "https://fake.test/video/stubborn")
    wait_until(lambda: job.detail != "" and logged(log, "child"))
    leader, child = logged(log, "pid")[0], logged(log, "child")[0]
    manager.cancel(job.id)
    assert job.status in RUNNING and job.stage == "Cancelando"
    wait_until(lambda: job.status == Status.CANCELED, 5.0)
    wait_until(lambda: not alive(leader) and not alive(child), 3.0)


def test_shutdown_leaves_no_process_of_the_group_behind(manager, log, wait_until):
    job = start(manager, "https://fake.test/video/child")
    wait_until(lambda: job.detail != "" and logged(log, "child"))
    leader, child = logged(log, "pid")[0], logged(log, "child")[0]
    manager.shutdown()
    wait_until(lambda: not alive(leader) and not alive(child), 3.0)


def test_a_crash_mid_download_is_a_failure_and_never_a_cancel(manager, log, wait_until):
    job = start(manager, "https://fake.test/video/crash")
    wait_until(lambda: job.status not in RUNNING and job.status != Status.QUEUED)
    assert job.status == Status.FAILED and job.error == CRASH_MESSAGE
    assert len(logged(log, "pid")) == 1


def test_forged_progress_and_file_lines_are_ignored(manager, wait_until, tmp_path):
    job = start(manager, "https://fake.test/video/forged")
    wait_until(lambda: job.status == Status.COMPLETED)
    assert job.file_path == str(tmp_path / "Downloads" / "Fake video [abc].mp4")
    assert job.detail == "2,0 KB"
    assert not (tmp_path / "outside.mp4").exists()


def test_postprocessing_reported_on_stderr_reaches_the_state_machine(manager, wait_until):
    seen: list[str] = []
    manager._model.dataChanged.connect(lambda *_: seen.append(manager._model.jobs[0].status.value))
    job = start(manager, "https://fake.test/video/ok")
    wait_until(lambda: job.status == Status.COMPLETED)
    assert "postprocessing" in seen
    assert "PLUCK_POST" not in job.error_detail


def test_a_transient_failure_is_retried_automatically(manager, log, wait_until, monkeypatch):
    monkeypatch.setattr(retry, "RETRY_BASE_SECONDS", 0.05)
    finished: list[str] = []
    manager.jobFinished.connect(lambda _id, _title, status: finished.append(status))
    job = start(manager, "https://fake.test/video/flaky")
    wait_until(lambda: job.status == Status.COMPLETED)
    assert len(logged(log, "pid")) == 2
    assert finished == ["completed"]


def test_canceling_an_analysis_stops_its_children(build_settings, build_analyzer, tmp_path, log, wait_until):
    analyzer = build_analyzer(build_settings(tmp_path / "settings.json"))
    analyzer.analyze("https://fake.test/hang-child")
    wait_until(lambda: bool(logged(log, "child")))
    leader, child = logged(log, "pid")[0], logged(log, "child")[0]
    analyzer.cancel()
    wait_until(lambda: not alive(leader) and not alive(child), 3.0)


def test_closing_the_app_stops_a_running_analysis_and_its_children(tmp_path, log, wait_until):
    services = build_services(tmp_path / "config", tmp_path / "data", FAKE_YTDLP)
    services.analyzer.analyze("https://fake.test/hang-child")
    wait_until(lambda: bool(logged(log, "child")))
    leader, child = logged(log, "pid")[0], logged(log, "child")[0]
    services.shutdown()
    wait_until(lambda: not alive(leader) and not alive(child), 3.0)


def test_relative_path_entries_never_resolve_an_executable(tmp_path, monkeypatch):
    planted = tmp_path / "cwd"
    trusted = tmp_path / "bin"
    for folder in (planted, trusted):
        folder.mkdir()
        tool = folder / "yt-dlp"
        tool.write_text("#!/bin/sh\n")
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    monkeypatch.chdir(planted)
    assert find_executable("yt-dlp", os.pathsep.join([".", "", "bin", str(trusted)])) == str(trusted / "yt-dlp")
    assert find_executable("yt-dlp", os.pathsep.join([".", "", "/opt/tools"])) == "/opt/tools/yt-dlp"
    assert find_executable("yt-dlp", os.pathsep.join([".", ""])) == "/usr/bin/yt-dlp"
    assert find_executable("/opt/yt-dlp", "") == "/opt/yt-dlp"
