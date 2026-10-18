import json
import os
from pathlib import Path

import pytest

from pluck.adapters.media_probe import YtDlpMediaProbe
from pluck.adapters.process import YtDlpRuntime
from pluck.adapters.storage import JsonFile
from pluck.domain.jobs import RUNNING, DownloadJob, Status
from pluck.domain.options import VIDEO, DownloadOptions, Preferences
from pluck.presentation.analyzer import Analyzer
from pluck.presentation.downloads import DownloadManager
from pluck.presentation.settings import Settings


@pytest.fixture
def settings(tmp_path: Path, qt_app) -> Settings:
    instance = Settings(JsonFile(tmp_path / "settings.json"))
    instance.update("folder", str(tmp_path / "out"))
    return instance


@pytest.fixture
def make_manager(build_manager):
    def build(settings: Settings, tmp_path: Path) -> DownloadManager:
        return build_manager(settings, tmp_path / "history.json")

    return build


def entry(url: str, title: str = "Fake") -> dict:
    return {"url": url, "title": title, "expectedSizes": [1000, 250]}


VIDEO_OPTIONS = {"mode": "video", "quality": 1080, "container": "mp4", "audioFormat": "mp3"}


def statuses(manager: DownloadManager) -> list[str]:
    return [job.status.value for job in manager._model.jobs]


def test_successful_download_reports_file_and_counts(make_manager, settings, tmp_path, wait_until):
    manager = make_manager(settings, tmp_path)
    finished = []
    manager.jobFinished.connect(lambda job_id, title, status: finished.append(status))
    assert manager.enqueue([entry("https://fake.test/video/ok")], VIDEO_OPTIONS) == 1
    wait_until(lambda: finished == ["completed"])
    job = manager._model.jobs[0]
    assert job.status == Status.COMPLETED
    assert job.progress == 1.0
    assert job.file_path.endswith("Fake video [abc].mp4")
    assert job.detail == "2,0 KB"
    assert manager.completedCount == 1 and manager.pendingCount == 0


def test_failure_maps_error_and_keeps_stderr_detail(make_manager, settings, tmp_path, wait_until):
    manager = make_manager(settings, tmp_path)
    manager.enqueue([entry("https://fake.test/video/fail")], VIDEO_OPTIONS)
    wait_until(lambda: statuses(manager) == ["failed"])
    job = manager._model.jobs[0]
    assert job.error == "Vídeo privado."
    assert "WARNING: something odd" in job.error_detail
    assert manager.failedCount == 1


def test_cancel_running_download(make_manager, settings, tmp_path, wait_until):
    manager = make_manager(settings, tmp_path)
    manager.enqueue([entry("https://fake.test/video/slow")], VIDEO_OPTIONS)
    job = manager._model.jobs[0]
    wait_until(lambda: job.detail != "")
    manager.cancel(job.id)
    wait_until(lambda: job.status == Status.CANCELED)
    manager.retry(job.id)
    assert job.status in (Status.QUEUED, Status.RESOLVING)
    manager.cancel(job.id)
    wait_until(lambda: job.status == Status.CANCELED)


def test_concurrency_limit_and_duplicate_urls(make_manager, settings, tmp_path, wait_until):
    settings.update("maxConcurrent", 1)
    manager = make_manager(settings, tmp_path)
    first, second = entry("https://fake.test/a/slow"), entry("https://fake.test/b/slow")
    added = manager.enqueue([first, second, first], VIDEO_OPTIONS)
    assert added == 2
    assert manager.enqueue([entry("https://fake.test/a/slow")], {**VIDEO_OPTIONS, "mode": "audio"}) == 1
    assert manager.runningCount == 1 and manager.queuedCount == 2
    first_running = next(job for job in manager._model.jobs if job.status in RUNNING)
    assert first_running.url == "https://fake.test/a/slow"
    for job in list(manager._model.jobs):
        manager.cancel(job.id)
    wait_until(lambda: manager.pendingCount == 0)


def test_history_round_trip_marks_unfinished_as_interrupted(make_manager, settings, tmp_path):
    manager = make_manager(settings, tmp_path)
    folder = Preferences(folder="/f")
    running = DownloadJob(url="u1", title="t1", options=DownloadOptions(VIDEO, 720, "mkv"), preferences=folder)
    running.status = Status.DOWNLOADING
    done = DownloadJob(url="u2", title="t2", options=DownloadOptions(), preferences=folder, status=Status.COMPLETED)
    manager._model.reset_with([running, done])
    manager.save()
    stored = json.loads((tmp_path / "history.json").read_text())
    assert stored["version"] == 2 and len(stored["jobs"]) == 2

    reloaded = make_manager(settings, tmp_path)
    assert statuses(reloaded) == ["interrupted", "completed"]
    assert reloaded.startupInterrupted == 1
    assert reloaded._model.jobs[0].options == DownloadOptions(VIDEO, 720, "mkv")


def test_corrupted_history_is_ignored(make_manager, settings, tmp_path):
    (tmp_path / "history.json").write_text("{not json")
    assert make_manager(settings, tmp_path).totalCount == 0


def test_filter_view_tracks_status_changes(make_manager, settings, tmp_path, wait_until):
    manager = make_manager(settings, tmp_path)
    view = manager.view
    view.setProperty("group", "failed")
    manager.enqueue([entry("https://fake.test/video/fail")], VIDEO_OPTIONS)
    assert view.rowCount() == 0
    wait_until(lambda: view.rowCount() == 1)
    view.setProperty("group", "completed")
    assert view.rowCount() == 0


def test_settings_sanitize_and_persist(tmp_path, qt_app):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"maxConcurrent": 99, "defaultMode": "hologram", "folder": "", "subtitles": "yes"}))
    settings = Settings(JsonFile(path))
    assert settings.value("maxConcurrent") == 6
    assert settings.value("defaultMode") == "video"
    assert settings.value("folder") != ""
    assert settings.value("subtitles") is False
    settings.update("cookiesBrowser", "firefox")
    settings.save()
    assert Settings(JsonFile(path)).value("cookiesBrowser") == "firefox"


def test_analyzer_reads_video_and_playlist(settings, runtime, wait_until):
    analyzer = Analyzer(settings, YtDlpMediaProbe(runtime))
    analyzer.analyze("https://www.youtube.com/watch?v=fOT0BUpITw8")
    wait_until(lambda: analyzer.state == "ready")
    assert analyzer.property("result")["kind"] == "video"
    sizes = analyzer.expectedSizes("video", 1080, "mp4", "mp3")
    assert len(sizes) == 2

    analyzer.analyze("https://www.youtube.com/playlist?list=PL1", True)
    wait_until(lambda: analyzer.state == "ready")
    assert analyzer.property("result")["kind"] == "playlist"
    assert analyzer.expectedSizes("video", 1080, "mp4", "mp3") == []


def test_analyzer_errors(settings, runtime, wait_until):
    analyzer = Analyzer(settings, YtDlpMediaProbe(runtime))
    analyzer.analyze("not a link")
    assert analyzer.state == "error" and analyzer.property("errorText") == "Isso não parece um link válido."
    analyzer.analyze("https://example.com/fail")
    wait_until(lambda: analyzer.state == "error")
    assert analyzer.property("errorText") == "Esse link não é suportado."

    missing = Analyzer(settings, YtDlpMediaProbe(YtDlpRuntime.prepare("/nonexistent/yt-dlp", runtime.home)))
    missing.analyze("https://example.com/video")
    wait_until(lambda: missing.state == "error")
    assert "Não foi possível iniciar o yt-dlp" in missing.property("errorText")


def test_shutdown_does_not_start_queued_jobs(make_manager, settings, tmp_path, wait_until, monkeypatch):
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_YTDLP_LOG", str(log))
    settings.update("maxConcurrent", 1)
    manager = make_manager(settings, tmp_path)
    manager.enqueue([entry("https://fake.test/a/slow"), entry("https://fake.test/b/slow")], VIDEO_OPTIONS)
    running = next(job for job in manager._model.jobs if job.status in RUNNING)
    wait_until(lambda: running.detail != "")
    manager.shutdown()
    pids = [json.loads(line)["pid"] for line in log.read_text().splitlines()]
    assert len(pids) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(pids[0], 0)
    assert manager.queuedCount == 1
    stored = json.loads((tmp_path / "history.json").read_text())
    assert sorted(job["status"] for job in stored["jobs"]) == ["downloading", "queued"]


def test_queued_jobs_keep_preferences_until_retried(make_manager, settings, tmp_path, wait_until):
    settings.update("maxConcurrent", 1)
    settings.update("cookiesBrowser", "firefox")
    manager = make_manager(settings, tmp_path)
    manager.enqueue([entry("https://fake.test/a/slow"), entry("https://fake.test/b/fail")], VIDEO_OPTIONS)
    settings.update("cookiesBrowser", "chrome")
    queued = next(job for job in manager._model.jobs if job.url == "https://fake.test/b/fail")
    assert queued.preferences.cookies_browser == "firefox"
    running = next(job for job in manager._model.jobs if job.url == "https://fake.test/a/slow")
    manager.cancel(running.id)
    wait_until(lambda: queued.status == Status.FAILED)
    manager.retry(queued.id)
    assert queued.preferences.cookies_browser == "chrome"
    manager.cancel(queued.id)
    wait_until(lambda: manager.pendingCount == 0)


def test_canceled_jobs_are_not_failures(make_manager, settings, tmp_path, wait_until):
    manager = make_manager(settings, tmp_path)
    manager.enqueue([entry("https://fake.test/video/slow"), entry("https://fake.test/video/fail")], VIDEO_OPTIONS)
    slow = next(job for job in manager._model.jobs if job.url.endswith("/slow"))
    wait_until(lambda: slow.detail != "")
    manager.cancel(slow.id)
    wait_until(lambda: manager.pendingCount == 0)
    assert manager.failedCount == 1
    manager.retryFailed()
    assert slow.status == Status.CANCELED
    for job in manager._model.jobs:
        manager.cancel(job.id)
    wait_until(lambda: manager.pendingCount == 0)


def test_analyzer_retry_keeps_playlist_mode(settings, runtime, wait_until, tmp_path, monkeypatch):
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_YTDLP_LOG", str(log))
    analyzer = Analyzer(settings, YtDlpMediaProbe(runtime))
    analyzer.analyze("https://www.youtube.com/watch?v=a&list=PL1/fail", True)
    wait_until(lambda: analyzer.state == "error")
    analyzer.retry()
    wait_until(lambda: analyzer.state == "error" and len(log.read_text().splitlines()) == 2)
    calls = [json.loads(line)["argv"] for line in log.read_text().splitlines()]
    assert all("--no-playlist" not in call for call in calls)
