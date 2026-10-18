from collections.abc import Callable, Sequence
from typing import Any

import pytest

from pluck.adapters.desktop_shell import parse_tool_version
from pluck.adapters.media_probe import probe_result
from pluck.adapters.ytdlp.errors import StderrTail, analysis_failure, download_failure
from pluck.application.analysis import INVALID_URL_MESSAGE, MediaAnalysis
from pluck.application.downloads import INVALID_FOLDER_MESSAGE, DownloadQueue, JobRequest
from pluck.application.history import beyond_limit
from pluck.application.ports import Failure, ProbeResult, RunListener, RunOutcome
from pluck.application.settings import SettingsStore
from pluck.domain.jobs import DownloadJob, Status
from pluck.domain.options import DownloadOptions, InvalidFolderError, Preferences
from pluck.domain.progress import ProgressUpdate


class MemoryStore:
    def __init__(self, payload: Any = None):
        self.payload = payload
        self.writes = 0

    def read(self) -> Any:
        return self.payload

    def write(self, payload: Any) -> None:
        self.payload = payload
        self.writes += 1


class MemoryJobList:
    def __init__(self) -> None:
        self._jobs: list[DownloadJob] = []
        self.refreshed: list[str] = []
        self.statuses: list[tuple[str, Status]] = []

    @property
    def jobs(self) -> Sequence[DownloadJob]:
        return self._jobs

    def reset_with(self, jobs: list[DownloadJob]) -> None:
        self._jobs = list(jobs)

    def prepend(self, jobs: list[DownloadJob]) -> None:
        self._jobs[0:0] = jobs

    def refresh(self, job: DownloadJob) -> None:
        self.refreshed.append(job.id)
        if not self.statuses or self.statuses[-1] != (job.id, job.status):
            self.statuses.append((job.id, job.status))

    def remove(self, job: DownloadJob) -> None:
        self._jobs.remove(job)


class FakeRun:
    def __init__(self, job: DownloadJob, listener: RunListener):
        self.job = job
        self.listener = listener
        self.started = False
        self.interrupts = 0
        self.killed = False
        self.exited = False

    def start(self) -> None:
        self.started = True

    def interrupt(self) -> None:
        self.interrupts += 1

    def kill(self) -> None:
        self.killed = True

    def progress(self, status: str = "downloading", done: int = 50, format_id: str = "137") -> None:
        update = ProgressUpdate(status, done, 100, 2048.0, 3, None, None, format_id, "avc1", "none")
        self.listener.on_progress(self.job.id, update)

    def exit(self, outcome: RunOutcome) -> None:
        self.exited = True
        self.listener.on_exit(self.job.id, outcome)


class FakeRunner:
    def __init__(self) -> None:
        self.runs: list[FakeRun] = []

    def prepare(self, job: DownloadJob, listener: RunListener) -> FakeRun:
        if not job.folder.startswith("/"):
            raise InvalidFolderError(f"download folder must be absolute: {job.folder!r}")
        run = FakeRun(job, listener)
        self.runs.append(run)
        return run

    def run_for(self, title: str) -> FakeRun:
        return next(run for run in self.runs if run.job.title == title)


class Recorder:
    def __init__(self) -> None:
        self.counts = 0
        self.settled = 0
        self.finished: list[tuple[str, Status]] = []

    def on_counts_changed(self) -> None:
        self.counts += 1

    def on_statuses_settled(self) -> None:
        self.settled += 1

    def on_job_finished(self, job: DownloadJob) -> None:
        self.finished.append((job.title, job.status))


class QueueHarness:
    def __init__(self, max_concurrent: int = 3, history: Any = None, runner: FakeRunner | None = None):
        self.now = 0.0
        self.settings = SettingsStore(MemoryStore({"maxConcurrent": max_concurrent}), "/downloads")
        self.jobs = MemoryJobList()
        self.runner = runner or FakeRunner()
        self.history = MemoryStore(history)
        self.events = Recorder()
        self.queue = DownloadQueue(
            self.jobs, self.runner, self.settings, self.history, self.events, clock=lambda: self.now, jitter=lambda: 0.0
        )

    def add(self, *titles: str, options: DownloadOptions | None = None, url: str | None = None) -> int:
        requests = [JobRequest(url=url or f"https://fake.test/{title}", title=title) for title in titles]
        return self.queue.enqueue(requests, options or DownloadOptions())

    def job(self, title: str) -> DownloadJob:
        return next(job for job in self.jobs.jobs if job.title == title)


def test_queue_starts_the_oldest_jobs_up_to_the_limit():
    harness = QueueHarness(max_concurrent=2)
    assert harness.add("a", "b", "c") == 3
    assert [run.job.title for run in harness.runner.runs] == ["a", "b"]
    assert all(run.started for run in harness.runner.runs)
    assert harness.job("a").stage == "Preparando" and harness.job("a").progress is None
    assert harness.job("c").status == Status.QUEUED
    harness.runner.run_for("a").exit(RunOutcome(file_size=2048))
    assert harness.job("a").status == Status.COMPLETED and harness.job("a").detail == "2,0 KB"
    assert harness.runner.runs[-1].job.title == "c"
    assert harness.events.finished == [("a", Status.COMPLETED)]


def test_queue_skips_invalid_and_duplicate_urls():
    harness = QueueHarness()
    harness.add("a")
    requests = [JobRequest("https://fake.test/a", "again"), JobRequest("file:///etc/passwd", "local")]
    assert harness.queue.enqueue(requests, DownloadOptions()) == 0
    assert harness.queue.enqueue([JobRequest("https://fake.test/a", "audio")], DownloadOptions(mode="audio")) == 1


def test_postprocessing_moves_between_stages_and_notifies_counts():
    harness = QueueHarness()
    harness.add("a")
    run = harness.runner.run_for("a")
    counts_before = harness.events.counts
    harness.queue.on_postprocess(run.job.id, "Juntando vídeo e áudio")
    assert run.job.status == Status.POSTPROCESSING
    assert run.job.stage == "Juntando vídeo e áudio" and run.job.progress is None
    assert harness.events.counts == counts_before + 1
    run.progress()
    assert run.job.status == Status.DOWNLOADING


def test_progress_reaches_the_list_only_when_flushed():
    harness = QueueHarness()
    harness.add("a")
    run = harness.runner.run_for("a")
    run.progress()
    assert run.job.status == Status.DOWNLOADING
    harness.queue.flush_progress()
    harness.jobs.refreshed.clear()
    run.progress()
    assert harness.jobs.refreshed == []
    assert harness.queue.total_speed == 2048.0
    harness.queue.flush_progress()
    assert harness.jobs.refreshed == [run.job.id]
    harness.jobs.refreshed.clear()
    harness.queue.flush_progress()
    assert harness.jobs.refreshed == []


def test_cancel_interrupts_once_and_wins_over_the_exit_code():
    harness = QueueHarness()
    harness.add("a")
    run = harness.runner.run_for("a")
    harness.queue.cancel(run.job.id)
    harness.queue.cancel(run.job.id)
    assert run.interrupts == 1 and run.job.stage == "Cancelando"
    run.exit(RunOutcome(failure=Failure("boom", "detail")))
    assert run.job.status == Status.CANCELED and run.job.error == ""
    assert harness.events.finished == [("a", Status.CANCELED)]


def test_cancel_wins_even_when_the_launch_fails():
    harness = QueueHarness()
    harness.add("a")
    run = harness.runner.run_for("a")
    harness.queue.cancel(run.job.id)
    run.exit(RunOutcome(failure=Failure("missing", "/bin/yt-dlp: FailedToStart"), launched=False))
    assert run.job.status == Status.CANCELED and run.job.error == ""


def test_invalid_folder_fails_the_job_and_frees_the_slot_in_the_same_pass():
    harness = QueueHarness(max_concurrent=1)
    harness.add("blocker", "invalid", "next")
    harness.job("invalid").preferences = Preferences(folder="relative/dir")
    harness.runner.run_for("blocker").exit(RunOutcome())
    invalid = harness.job("invalid")
    assert invalid.status == Status.FAILED and invalid.error == INVALID_FOLDER_MESSAGE
    assert "relative/dir" in invalid.error_detail
    assert [run.job.title for run in harness.runner.runs] == ["blocker", "next"]
    assert ("invalid", Status.FAILED) in harness.events.finished


def test_events_after_shutdown_are_ignored_and_runs_are_killed():
    harness = QueueHarness(max_concurrent=1)
    harness.add("a", "b")
    run = harness.runner.run_for("a")
    harness.queue.shutdown()
    assert run.killed
    assert harness.history.writes == 1
    run.progress()
    run.exit(RunOutcome())
    assert run.job.status == Status.RESOLVING
    assert len(harness.runner.runs) == 1


def test_retry_requeues_with_current_preferences_but_keeps_the_folder():
    harness = QueueHarness(max_concurrent=1)
    harness.add("a")
    run = harness.runner.run_for("a")
    run.exit(RunOutcome(failure=Failure("x", "y")))
    run.job.preferences = Preferences(folder="/elsewhere", cookies_browser="firefox")
    harness.settings.update("cookiesBrowser", "chrome")
    harness.queue.retry(run.job.id)
    assert run.job.preferences.folder == "/elsewhere"
    assert run.job.preferences.cookies_browser == "chrome"
    assert harness.runner.runs[-1].job is run.job


def test_history_is_loaded_with_pending_jobs_interrupted():
    record = {"id": "x", "url": "https://fake.test/x", "status": "processing", "preferences": {"folder": "/f"}}
    harness = QueueHarness(history={"version": 1, "jobs": [record, {"url": "https://fake.test/y"}]})
    assert harness.queue.interrupted_at_startup == 2
    assert harness.queue.count({Status.INTERRUPTED}) == 2
    assert harness.runner.runs == []


def test_history_trim_never_drops_pending_jobs():
    def job(index: int, status: Status) -> DownloadJob:
        return DownloadJob(f"u{index}", f"t{index}", DownloadOptions(), Preferences("/f"), status=status)

    jobs = [job(0, Status.QUEUED), job(1, Status.COMPLETED), job(2, Status.DOWNLOADING), job(3, Status.FAILED)]
    assert [item.title for item in beyond_limit(jobs, limit=2)] == ["t3", "t1"]
    assert beyond_limit(jobs, limit=4) == []


class FakeProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool, str]] = []
        self.pending: list[tuple[FakeProbeRun, Callable[[ProbeResult], None]]] = []

    def prepare(
        self, url: str, include_playlist: bool, cookies_browser: str, on_done: Callable[[ProbeResult], None]
    ) -> "FakeProbeRun":
        self.calls.append((url, include_playlist, cookies_browser))
        run = FakeProbeRun()
        self.pending.append((run, on_done))
        return run

    def answer(self, result: ProbeResult, index: int = -1) -> None:
        self.pending[index][1](result)


class FakeProbeRun:
    def __init__(self) -> None:
        self.started = False
        self.canceled = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.canceled = True


class AnalysisRecorder:
    def __init__(self) -> None:
        self.started = 0
        self.results: list[ProbeResult] = []

    def on_analysis_started(self) -> None:
        self.started += 1

    def on_analysis_finished(self, result: ProbeResult) -> None:
        self.results.append(result)


@pytest.fixture
def analysis():
    probe = FakeProbe()
    events = AnalysisRecorder()
    settings = SettingsStore(MemoryStore({"cookiesBrowser": "firefox"}), "/downloads")
    return MediaAnalysis(probe, settings, events), probe, events


def test_analysis_rejects_text_without_probing(analysis):
    media, probe, events = analysis
    assert media.start("  not a link ", True) == Failure(INVALID_URL_MESSAGE, "not a link")
    assert probe.calls == [] and events.started == 0 and media.include_playlist is False


def test_analysis_follows_nested_playlists(analysis):
    media, probe, events = analysis
    assert media.start("youtube.com/@x", False) is None
    assert probe.calls == [("https://youtube.com/@x", False, "firefox")]
    nested = {"_type": "playlist", "entries": [{"ie_key": "YoutubeTab", "url": "https://youtube.com/playlist?list=1"}]}
    probe.answer(nested)
    assert probe.calls[-1] == ("https://youtube.com/playlist?list=1", True, "firefox")
    assert events.started == 2 and events.results == []
    probe.answer({"_type": "playlist", "entries": []})
    assert events.results == [{"_type": "playlist", "entries": []}]
    assert media.url == "https://youtube.com/@x" and media.include_playlist is True


def test_analysis_ignores_results_from_canceled_probes(analysis):
    media, probe, events = analysis
    media.start("https://a.test/1", False)
    media.start("https://a.test/2", False)
    assert probe.pending[0][0].canceled
    probe.answer({"title": "old"}, index=0)
    assert events.results == []
    probe.answer({"title": "new"})
    assert events.results == [{"title": "new"}]
    assert media.cancel() is False


@pytest.mark.parametrize(
    ("stdout", "stderr", "code", "expected"),
    [
        ('{"title": "ok"}', "", 0, {"title": "ok"}),
        ("", "ERROR: Unsupported URL: x", 1, Failure("Esse link não é suportado.", "Unsupported URL: x")),
        ("not json", "", 0, Failure("not json", "not json")),
        ("[1, 2]", "", 0, Failure("O yt-dlp encerrou com erro.", "[1, 2]")),
        ("", "", 3, Failure("O yt-dlp encerrou com código 3.", "")),
    ],
)
def test_probe_output_becomes_data_or_failure(stdout, stderr, code, expected):
    assert probe_result(stdout, stderr, code) == expected


def test_stderr_tail_keeps_the_last_lines_and_the_last_error():
    tail = StderrTail(limit=3)
    for line in ["ERROR: first", "  ", "WARNING: a", "b", "c"]:
        tail.add(line)
    assert tail.text == "WARNING: a\nb\nc"
    assert tail.headline == "ERROR: first"
    assert download_failure(tail, 1) == Failure("first", "WARNING: a\nb\nc")
    assert analysis_failure("ERROR: [yt] token=abc", 1).detail == "[yt] token=abc"
    assert analysis_failure("https://x.test/?sig=secret", 1).detail == "https://x.test/?sig=[redacted]"


@pytest.mark.parametrize(
    ("tool", "output", "version"),
    [
        ("yt-dlp", "2026.07.04\n", "2026.07.04"),
        ("ffmpeg", "ffmpeg version 7.1.1 Copyright (c) 2000-2025\nbuilt with gcc", "7.1.1"),
        ("ffmpeg", "ffmpeg version n7.0-3-gabc Copyright", "7.0-3-gabc"),
        ("ffmpeg", "", ""),
    ],
)
def test_tool_versions_are_read_from_the_first_line(tool, output, version):
    assert parse_tool_version(tool, output) == version
