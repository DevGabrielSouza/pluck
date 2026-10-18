import json
from pathlib import Path

import pytest

VIDEO = {"mode": "video", "quality": 1080, "container": "mp4", "audioFormat": "mp3"}


@pytest.fixture
def settings(build_settings, tmp_path):
    instance = build_settings(tmp_path / "settings.json")
    instance.update("folder", str(tmp_path / "out"))
    return instance


def entry(url: str, title: str = "Fake") -> dict:
    return {"url": url, "title": title, "expectedSizes": [1000, 250]}


def rows(manager) -> list[dict]:
    view = manager.view
    roles = {bytes(name.data()).decode(): role for role, name in view.roleNames().items()}
    return [
        {name: view.data(view.index(row, 0), role) for name, role in roles.items()} for row in range(view.rowCount())
    ]


def row(manager, title: str) -> dict:
    return next(item for item in rows(manager) if item["title"] == title)


def finished_signals(manager) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    manager.jobFinished.connect(lambda _job_id, title, status: seen.append((title, status)))
    return seen


def done_record(index: int, folder: str) -> dict:
    return {
        "id": f"d{index}",
        "url": f"https://fake.test/done/{index}",
        "title": f"done {index}",
        "status": "done",
        "createdAt": 10_000 - index,
        "preferences": {"folder": folder},
    }


def test_save_keeps_pending_jobs_and_trims_the_oldest_finished(build_manager, settings, tmp_path, wait_until):
    history = tmp_path / "history.json"
    history.write_text(json.dumps({"version": 1, "jobs": [done_record(i, str(tmp_path)) for i in range(500)]}))
    settings.update("maxConcurrent", 1)
    manager = build_manager(settings, history)
    manager.enqueue([entry("https://fake.test/a/slow", "a"), entry("https://fake.test/b/slow", "b")], VIDEO)
    assert manager.totalCount == 502 and manager.pendingCount == 2
    manager.save()
    stored = json.loads(history.read_text())
    assert stored["version"] == 2
    ids = [job["id"] for job in stored["jobs"]]
    assert len(ids) == 500
    assert "d498" not in ids and "d499" not in ids and "d497" in ids
    assert [job["title"] for job in stored["jobs"][:2]] == ["a", "b"]
    assert manager.totalCount == 500
    for item in rows(manager)[:2]:
        manager.cancel(item["jobId"])
    wait_until(lambda: manager.pendingCount == 0)


def test_download_that_cannot_launch_fails_and_frees_the_slot(build_manager, settings, tmp_path, wait_until):
    settings.update("maxConcurrent", 1)
    manager = build_manager(settings, tmp_path / "history.json", "/nonexistent/yt-dlp")
    finished = finished_signals(manager)
    manager.enqueue([entry("https://fake.test/a/ok", "a"), entry("https://fake.test/b/ok", "b")], VIDEO)
    wait_until(lambda: len(finished) == 2)
    assert sorted(finished) == [("a", "failed"), ("b", "failed")]
    failed = row(manager, "a")
    assert failed["errorText"] == "Não foi possível iniciar o yt-dlp. Instale com: sudo dnf install yt-dlp"
    assert failed["errorDetail"] == "/nonexistent/yt-dlp: FailedToStart"
    assert failed["stage"] == "Falhou"
    assert manager.failedCount == 2 and manager.runningCount == 0


def test_download_without_stderr_reports_the_exit_code(build_manager, settings, tmp_path, wait_until):
    manager = build_manager(settings, tmp_path / "history.json")
    manager.enqueue([entry("https://fake.test/video/silent")], VIDEO)
    wait_until(lambda: manager.failedCount == 1)
    failed = rows(manager)[0]
    assert failed["errorText"] == "O yt-dlp encerrou com código 3."
    assert failed["errorDetail"] == ""
    assert failed["detail"] == ""


def test_download_error_detail_keeps_the_whole_stderr_tail(build_manager, settings, tmp_path, wait_until):
    manager = build_manager(settings, tmp_path / "history.json")
    manager.enqueue([entry("https://fake.test/video/fail")], VIDEO)
    wait_until(lambda: manager.failedCount == 1)
    assert rows(manager)[0]["errorDetail"] == (
        "WARNING: something odd\nERROR: [youtube] abc: Private video. Sign in if you've been granted access"
    )


def test_successful_download_goes_through_processing(build_manager, settings, tmp_path, wait_until):
    manager = build_manager(settings, tmp_path / "history.json")
    finished = finished_signals(manager)
    seen_statuses: list[str] = []
    manager.countsChanged.connect(lambda: seen_statuses.extend(item["status"] for item in rows(manager)))
    manager.enqueue([entry("https://fake.test/video/ok")], VIDEO)
    wait_until(lambda: finished == [("Fake", "completed")])
    assert {"resolving", "downloading", "postprocessing"} <= set(seen_statuses)
    done = rows(manager)[0]
    assert done["stage"] == "Concluído"
    assert done["progress"] == 1.0
    assert done["detail"] == "2,0 KB"
    assert done["filePath"].endswith("Fake video [abc].mp4")
    assert manager.filePath(done["jobId"]) == done["filePath"]


def test_running_jobs_cannot_be_removed_and_clear_finished_keeps_the_rest(
    build_manager, settings, tmp_path, wait_until
):
    manager = build_manager(settings, tmp_path / "history.json")
    manager.enqueue([entry("https://fake.test/video/slow", "slow"), entry("https://fake.test/video/ok", "ok")], VIDEO)
    wait_until(lambda: manager.completedCount == 1)
    slow = row(manager, "slow")
    manager.remove(slow["jobId"])
    assert manager.totalCount == 2
    manager.clearFinished()
    assert [item["title"] for item in rows(manager)] == ["slow"]
    manager.cancel(slow["jobId"])
    wait_until(lambda: manager.pendingCount == 0)
    manager.remove(slow["jobId"])
    assert manager.totalCount == 0


def test_retry_interrupted_restarts_jobs_from_history(build_manager, settings, tmp_path, wait_until):
    history = tmp_path / "history.json"
    record = {
        "id": "x",
        "url": "https://fake.test/video/ok",
        "title": "resumed",
        "status": "downloading",
        "options": VIDEO,
        "preferences": {"folder": str(tmp_path / "elsewhere")},
    }
    history.write_text(json.dumps({"version": 1, "jobs": [record]}))
    manager = build_manager(settings, history)
    assert manager.startupInterrupted == 1 and manager.interruptedCount == 1
    assert rows(manager)[0]["stage"] == "Interrompido"
    manager.retryInterrupted()
    wait_until(lambda: manager.completedCount == 1)
    done = rows(manager)[0]
    assert done["folder"] == str(tmp_path / "elsewhere")
    assert Path(done["filePath"]).parent == tmp_path / "elsewhere"


def test_total_speed_follows_running_downloads(build_manager, settings, tmp_path, wait_until):
    manager = build_manager(settings, tmp_path / "history.json")
    manager.enqueue([entry("https://fake.test/video/slow")], VIDEO)
    wait_until(lambda: manager.totalSpeedText == "1,0 MB/s")
    manager.cancel(rows(manager)[0]["jobId"])
    wait_until(lambda: manager.totalSpeedText == "")


def test_cancel_is_immediate_for_queued_and_graceful_for_running(build_manager, settings, tmp_path, wait_until):
    settings.update("maxConcurrent", 1)
    manager = build_manager(settings, tmp_path / "history.json")
    finished = finished_signals(manager)
    manager.enqueue([entry("https://fake.test/a/slow", "a"), entry("https://fake.test/b/slow", "b")], VIDEO)
    wait_until(lambda: row(manager, "a")["detail"] != "")
    manager.cancel(row(manager, "b")["jobId"])
    assert row(manager, "b")["status"] == "canceled" and finished == []
    manager.cancel(row(manager, "a")["jobId"])
    assert row(manager, "a")["stage"] == "Cancelando"
    wait_until(lambda: finished == [("a", "canceled")])
    assert row(manager, "a")["stage"] == "Cancelado"
    assert manager.runningCount == 0 and manager.queuedCount == 0


def test_analyzer_follows_a_nested_playlist_and_keeps_the_typed_url(
    build_analyzer, settings, tmp_path, wait_until, monkeypatch
):
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_YTDLP_LOG", str(log))
    analyzer = build_analyzer(settings)
    analyzer.analyze("https://www.youtube.com/@someone/channel")
    wait_until(lambda: analyzer.state == "ready")
    assert analyzer.property("result")["kind"] == "playlist"
    assert analyzer.property("url") == "https://www.youtube.com/@someone/channel"
    calls = [json.loads(line)["argv"] for line in log.read_text().splitlines()]
    assert [call[-1] for call in calls] == [
        "https://www.youtube.com/@someone/channel",
        "https://www.youtube.com/playlist?list=PLnested",
    ]
    assert "--no-playlist" in calls[0] and "--no-playlist" not in calls[1]


@pytest.mark.parametrize(
    ("url", "text", "detail"),
    [
        ("https://example.com/fail", "Esse link não é suportado.", "Unsupported URL: https://example.com/fail"),
        ("https://example.com/garbage", "not json", "not json"),
        ("https://example.com/silent", "O yt-dlp encerrou com código 3.", ""),
    ],
)
def test_analyzer_failure_messages(build_analyzer, settings, wait_until, url, text, detail):
    analyzer = build_analyzer(settings)
    analyzer.analyze(url)
    wait_until(lambda: analyzer.state == "error")
    assert analyzer.property("errorText") == text
    assert analyzer.property("errorDetail") == detail


def test_analyzer_cannot_launch(build_analyzer, settings, wait_until):
    analyzer = build_analyzer(settings, "/nonexistent/yt-dlp")
    analyzer.analyze("https://example.com/video")
    wait_until(lambda: analyzer.state == "error")
    assert analyzer.property("errorText") == "Não foi possível iniciar o yt-dlp. Instale com: sudo dnf install yt-dlp"
    assert analyzer.property("errorDetail") == "/nonexistent/yt-dlp: FailedToStart"


def test_analyzer_cancel_clear_and_loading_state(build_analyzer, settings, wait_until):
    analyzer = build_analyzer(settings)
    analyzer.analyze("https://example.com/fail")
    wait_until(lambda: analyzer.state == "error")
    analyzer.analyze("example.com/hang")
    assert analyzer.state == "loading"
    assert analyzer.property("url") == "https://example.com/hang"
    assert analyzer.property("errorText") == ""
    analyzer.cancel()
    assert analyzer.state == "idle" and analyzer.property("url") == "https://example.com/hang"
    analyzer.analyze("https://example.com/hang")
    analyzer.clear()
    assert analyzer.state == "idle" and analyzer.property("url") == "" and analyzer.property("result") == {}


def test_analyzer_rejects_text_that_is_not_a_link(build_analyzer, settings):
    analyzer = build_analyzer(settings)
    changes: list[str] = []
    analyzer.stateChanged.connect(lambda: changes.append(analyzer.state))
    analyzer.analyze("  not a link  ")
    assert changes == ["error"]
    assert analyzer.property("errorText") == "Isso não parece um link válido."
    assert analyzer.property("errorDetail") == "not a link"
    assert analyzer.expectedSizes("video", 1080, "mp4", "mp3") == []


def test_settings_emit_only_real_changes_and_reset_to_defaults(settings, tmp_path):
    changes: list[int] = []
    settings.changed.connect(lambda: changes.append(1))
    settings.update("maxConcurrent", 2)
    settings.update("maxConcurrent", 2)
    settings.update("maxConcurrent", 0)
    assert settings.value("maxConcurrent") == 1 and len(changes) == 2
    settings.resetValue("maxConcurrent")
    settings.resetValue("unknown")
    assert settings.value("maxConcurrent") == 3 and len(changes) == 3
    assert settings.preferences().folder == str(tmp_path / "out")
    assert settings.preferences("/elsewhere").folder == "/elsewhere"
    settings.update("filenameTemplate", "../%(title)s.%(ext)s")
    assert settings.preferences().filename_template == "%(title)s [%(id)s].%(ext)s"
    assert settings.isFilenameTemplateSafe("../x") is False
    assert settings.previewFilename("%(uploader)s - %(title)s.%(ext)s") == "jawed - Me at the zoo.mp4"


def test_media_description_matches_the_recorded_snapshot():
    from pluck.presentation.media_view import describe_media
    from tests.conftest import FIXTURES

    recorded = json.loads((FIXTURES / "described_media.json").read_text())
    for name, case in recorded.items():
        data = json.loads((FIXTURES / f"{name}.json").read_text())
        assert describe_media(data, case["url"], case["quality"]) == case["described"], name
