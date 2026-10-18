import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pluck.adapters.download_runner import QtDownloadRunner
from pluck.adapters.media_probe import YtDlpMediaProbe
from pluck.adapters.storage import JsonFile
from pluck.adapters.ytdlp.commands import OutputMarkers, build_analyze_command, build_download_command, output_template
from pluck.domain.options import DEFAULT_FILENAME_TEMPLATE, DownloadOptions, Preferences
from pluck.presentation.analyzer import Analyzer
from pluck.presentation.downloads import DownloadManager
from pluck.presentation.settings import Settings

PLANTED_CONFIG = "--print-traffic\n--exec 'touch {marker}'\n"


def option_value(command: list[str], option: str) -> list[str]:
    return [command[index + 1] for index, value in enumerate(command) if value == option]


def test_download_command_never_points_home_at_the_download_folder(tmp_path):
    folder = tmp_path / "Downloads"
    command = build_download_command(
        "yt-dlp",
        "https://example.com/v",
        DownloadOptions(),
        Preferences(folder=str(folder)),
        "/private/home",
        OutputMarkers.generate(),
    )
    assert option_value(command, "-P") == ["home:/private/home"]
    assert option_value(command, "-o") == [f"{folder}/{DEFAULT_FILENAME_TEMPLATE}"]


def test_analyze_command_uses_the_private_home():
    command = build_analyze_command("yt-dlp", "https://example.com/v", False, "", "/private/home")
    assert option_value(command, "-P") == ["home:/private/home"]


def test_percent_in_folder_is_not_a_template_field():
    assert output_template("/home/a/100% music", "%(title)s.%(ext)s") == "/home/a/100%% music/%(title)s.%(ext)s"


@pytest.mark.parametrize(
    "template",
    ["/etc/cron.d/%(id)s", "~/.bashrc", "../%(title)s.%(ext)s", "a/../../%(id)s", "%(title)s\n.%(ext)s", "", "   "],
)
def test_unsafe_templates_fall_back_to_the_default(template):
    assert output_template("/srv/out", template) == f"/srv/out/{DEFAULT_FILENAME_TEMPLATE}"


def test_subfolders_inside_the_download_folder_are_allowed():
    assert output_template("/srv/out", "%(channel)s/%(title)s.%(ext)s") == "/srv/out/%(channel)s/%(title)s.%(ext)s"


def test_relative_download_folder_is_rejected():
    with pytest.raises(ValueError):
        output_template("Downloads", DEFAULT_FILENAME_TEMPLATE)


def invocations(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_every_ytdlp_process_runs_inside_the_private_home(tmp_path, runtime, wait_until, monkeypatch):
    log = tmp_path / "invocations.jsonl"
    monkeypatch.setenv("FAKE_YTDLP_LOG", str(log))
    settings = Settings(JsonFile(tmp_path / "settings.json"))
    settings.update("folder", str(tmp_path / "out"))
    analyzer = Analyzer(settings, YtDlpMediaProbe(runtime))
    analyzer.analyze("https://www.youtube.com/watch?v=fOT0BUpITw8")
    wait_until(lambda: analyzer.state == "ready")
    manager = DownloadManager(settings, JsonFile(tmp_path / "history.json"), QtDownloadRunner(runtime))
    manager.enqueue([{"url": "https://fake.test/video/ok", "title": "t"}], {"mode": "video"})
    wait_until(lambda: manager.completedCount == 1)
    calls = invocations(log)
    assert len(calls) == 2
    assert {call["cwd"] for call in calls} == {str(runtime.home)}
    manager.shutdown()


def test_invalid_folder_fails_the_job_instead_of_crashing(tmp_path, runtime, wait_until):
    settings = Settings(JsonFile(tmp_path / "settings.json"))
    settings.update("maxConcurrent", 1)
    manager = DownloadManager(settings, JsonFile(tmp_path / "history.json"), QtDownloadRunner(runtime))
    manager.enqueue([{"url": "https://fake.test/video/slow", "title": "blocker"}], {"mode": "video"})
    manager.enqueue([{"url": "https://fake.test/video/ok", "title": "t"}], {"mode": "video"})
    queued = next(job for job in manager._model.jobs if job.title == "t")
    queued.preferences = Preferences(folder="relative/dir")
    blocker = next(job for job in manager._model.jobs if job.title == "blocker")
    manager.cancel(blocker.id)
    wait_until(lambda: queued.status.value == "failed")
    assert "pasta de destino" in queued.error
    manager.shutdown()


def test_invalid_folder_does_not_start_the_next_job_twice(tmp_path, runtime, wait_until, capfd):
    settings = Settings(JsonFile(tmp_path / "settings.json"))
    settings.update("maxConcurrent", 1)
    manager = DownloadManager(settings, JsonFile(tmp_path / "history.json"), QtDownloadRunner(runtime))
    manager.enqueue([{"url": "https://fake.test/video/slow", "title": "blocker"}], {"mode": "video"})
    manager.enqueue([{"url": "https://fake.test/other/slow", "title": "invalid"}], {"mode": "audio"})
    manager.enqueue([{"url": "https://fake.test/video/ok", "title": "next"}], {"mode": "video"})
    invalid = next(job for job in manager._model.jobs if job.title == "invalid")
    invalid.preferences = Preferences(folder="relative/dir")
    settings.update("maxConcurrent", 3)
    following = next(job for job in manager._model.jobs if job.title == "next")
    assert invalid.status.value == "failed"
    assert following.status.value != "queued"
    assert manager.runningCount == 2
    wait_until(lambda: following.status.value == "completed")
    manager.shutdown()
    assert "Traceback" not in capfd.readouterr().err


ytdlp = shutil.which("yt-dlp") or ""


def run_ytdlp_verbose(command: list[str], cwd: Path) -> str:
    verbose = [command[0], "-v", "--simulate", "--socket-timeout", "1", *command[1:]]
    result = subprocess.run(verbose, cwd=cwd, capture_output=True, text=True, timeout=60)
    return result.stderr


@pytest.mark.integration
@pytest.mark.skipif(not ytdlp, reason="yt-dlp is not installed")
def test_real_ytdlp_ignores_a_config_planted_in_the_download_folder(tmp_path):
    folder = tmp_path / "Downloads"
    home = tmp_path / "home"
    folder.mkdir()
    home.mkdir()
    marker = tmp_path / "pwned"
    (folder / "yt-dlp.conf").write_text(PLANTED_CONFIG.format(marker=marker))
    command = build_download_command(
        ytdlp,
        "https://invalid.invalid/v",
        DownloadOptions(),
        Preferences(folder=str(folder)),
        str(home),
        OutputMarkers.generate(),
    )
    stderr = run_ytdlp_verbose(command, home)
    assert "Command-line config" in stderr
    assert str(folder / "yt-dlp.conf") not in stderr
    assert not marker.exists()


@pytest.mark.integration
@pytest.mark.skipif(not ytdlp, reason="yt-dlp is not installed")
def test_real_ytdlp_would_load_it_if_the_folder_were_the_home(tmp_path):
    folder = tmp_path / "Downloads"
    folder.mkdir()
    (folder / "yt-dlp.conf").write_text("--print-traffic\n")
    stderr = run_ytdlp_verbose([ytdlp, "-P", str(folder), "--", "https://invalid.invalid/v"], tmp_path)
    assert str(folder / "yt-dlp.conf") in stderr
