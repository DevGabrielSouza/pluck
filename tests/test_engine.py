import random

import pytest

from pluck.application.downloads import CANCELING_STAGE
from pluck.application.ports import Failure, RunListener, RunOutcome
from pluck.domain.jobs import RUNNING, DownloadJob, Status
from pluck.domain.options import AUDIO, DownloadOptions
from pluck.domain.progress import ProgressUpdate
from pluck.domain.retry import MAX_AUTOMATIC_RETRIES
from tests.test_application import FakeRun, FakeRunner, QueueHarness

TRANSIENT = Failure("Sem conexão com a internet.", "ERROR: timed out", transient=True)


RATE_LIMITED = Failure("O site limitou as requisições.", "ERROR: HTTP Error 429", transient=True, rate_limited=True)


PERMANENT = Failure("Vídeo privado.", "ERROR: Private video")


FINISHED_FILE = RunOutcome(file_size=2048, file_reported=True)


def update(status: str = "downloading", done: int = 50, total: int = 100, format_id: str = "137") -> ProgressUpdate:
    vcodec, acodec = {"137": ("avc1", "none"), "140": ("none", "mp4a")}.get(format_id, ("NA", "NA"))
    return ProgressUpdate(status, done, total, 2048.0, 3, None, None, format_id, vcodec, acodec)


def started(harness: QueueHarness, title: str) -> FakeRun:
    return [run for run in harness.runner.runs if run.job.title == title][-1]


def statuses_of(harness: QueueHarness, title: str) -> list[Status]:
    job_id = harness.job(title).id
    return [status for identifier, status in harness.jobs.statuses if identifier == job_id]


def test_a_download_walks_through_every_state_of_the_lifecycle():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update())
    run.listener.on_postprocess(run.job.id, "Juntando vídeo e áudio")
    run.exit(FINISHED_FILE)
    assert statuses_of(harness, "a") == [
        Status.RESOLVING,
        Status.DOWNLOADING,
        Status.POSTPROCESSING,
        Status.COMPLETED,
    ]


def test_an_already_downloaded_file_completes_straight_from_resolving():
    harness = QueueHarness()
    harness.add("a")
    started(harness, "a").exit(FINISHED_FILE)
    assert statuses_of(harness, "a") == [Status.RESOLVING, Status.COMPLETED]


def test_postprocessing_can_follow_resolving_directly():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_postprocess(run.job.id, "Embutindo capa")
    assert run.job.status == Status.POSTPROCESSING and run.job.progress is None
    run.exit(FINISHED_FILE)
    assert run.job.progress == 1.0


def test_a_late_finished_event_does_not_undo_postprocessing():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update())
    run.listener.on_postprocess(run.job.id, "Juntando vídeo e áudio")
    run.listener.on_progress(run.job.id, update("finished", 100))
    assert run.job.status == Status.POSTPROCESSING and run.job.stage == "Juntando vídeo e áudio"


def test_events_after_cancel_do_not_overwrite_the_canceling_state():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update(done=40))
    harness.queue.cancel(run.job.id)
    run.listener.on_progress(run.job.id, update(done=90))
    run.listener.on_postprocess(run.job.id, "Juntando vídeo e áudio")
    assert run.job.stage == "Cancelando" and run.job.speed == 0.0 and run.job.progress == pytest.approx(0.36)
    assert harness.queue.total_speed == 0.0


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (FINISHED_FILE, Status.COMPLETED),
        (RunOutcome(), Status.CANCELED),
        (RunOutcome(failure=PERMANENT), Status.CANCELED),
        (RunOutcome(failure=TRANSIENT), Status.CANCELED),
    ],
)
def test_cancel_ends_canceled_unless_the_file_was_already_finished(outcome, expected):
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    harness.queue.cancel(run.job.id)
    run.exit(outcome)
    assert run.job.status == expected
    assert run.job.error == ""
    assert len(harness.runner.runs) == 1
    assert harness.events.finished == [("a", expected)]


def test_a_transient_failure_retries_with_growing_backoff_and_then_gives_up():
    harness = QueueHarness()
    harness.add("a")
    delays = []
    for attempt in range(1, MAX_AUTOMATIC_RETRIES + 1):
        started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
        job = harness.job("a")
        assert job.status == Status.QUEUED and job.stage == f"Nova tentativa ({attempt} de {MAX_AUTOMATIC_RETRIES})"
        assert job.detail == TRANSIENT.message and harness.events.finished == []
        delay = harness.queue.next_retry_delay()
        assert delay is not None
        delays.append(delay)
        harness.now += delay - 0.01
        harness.queue.schedule()
        assert len(harness.runner.runs) == attempt
        harness.now += 0.01
        harness.queue.schedule()
        assert len(harness.runner.runs) == attempt + 1
    assert delays == [5.0, 15.0, 45.0]
    started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
    assert harness.job("a").status == Status.FAILED and harness.job("a").error == TRANSIENT.message
    assert harness.events.finished == [("a", Status.FAILED)]
    assert harness.queue.next_retry_delay() is None


def test_rate_limiting_waits_much_longer():
    harness = QueueHarness()
    harness.add("a")
    started(harness, "a").exit(RunOutcome(failure=RATE_LIMITED))
    assert harness.queue.next_retry_delay() == 60.0


def test_a_permanent_failure_is_not_retried():
    harness = QueueHarness()
    harness.add("a")
    started(harness, "a").exit(RunOutcome(failure=PERMANENT))
    assert harness.job("a").status == Status.FAILED
    assert harness.queue.next_retry_delay() is None


def test_a_manual_retry_restores_the_automatic_budget():
    harness = QueueHarness()
    harness.add("a")
    for _ in range(MAX_AUTOMATIC_RETRIES + 1):
        started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
        harness.now += 1000
        harness.queue.schedule()
    assert harness.job("a").status == Status.FAILED
    harness.queue.retry(harness.job("a").id)
    started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
    assert harness.job("a").stage == f"Nova tentativa (1 de {MAX_AUTOMATIC_RETRIES})"


def test_cancel_during_backoff_cancels_without_another_attempt():
    harness = QueueHarness()
    harness.add("a")
    started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
    harness.queue.cancel(harness.job("a").id)
    harness.now += 1000
    harness.queue.schedule()
    assert harness.job("a").status == Status.CANCELED and len(harness.runner.runs) == 1
    assert harness.queue.next_retry_delay() is None


def test_removing_a_job_in_backoff_forgets_its_timer():
    harness = QueueHarness()
    harness.add("a")
    started(harness, "a").exit(RunOutcome(failure=TRANSIENT))
    harness.queue.remove(harness.job("a").id)
    assert harness.queue.next_retry_delay() is None


def test_the_same_url_never_runs_twice_at_once():
    harness = QueueHarness(max_concurrent=3)
    url = "https://fake.test/same"
    harness.add("video", url=url)
    harness.add("audio", url=url, options=DownloadOptions(mode=AUDIO))
    harness.add("other")
    assert [run.job.title for run in harness.runner.runs] == ["video", "other"]
    started(harness, "video").exit(FINISHED_FILE)
    assert [run.job.title for run in harness.runner.runs] == ["video", "other", "audio"]


class LaunchFailingRun(FakeRun):
    def start(self) -> None:
        super().start()
        self.exit(RunOutcome(failure=PERMANENT, launched=False))


class LaunchFailingRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.failing: set[str] = set()

    def prepare(self, job: DownloadJob, listener: RunListener) -> FakeRun:
        if job.title not in self.failing:
            return super().prepare(job, listener)
        run = LaunchFailingRun(job, listener)
        self.runs.append(run)
        return run


def test_a_launch_failing_inside_start_does_not_let_one_url_run_twice():
    runner = LaunchFailingRunner()
    harness = QueueHarness(max_concurrent=3, runner=runner)
    url = "https://fake.test/same"
    harness.add("first")
    harness.add("video", url=url)
    harness.add("audio", url=url, options=DownloadOptions(mode=AUDIO))
    for title in ("first", "video", "audio"):
        started(harness, title).exit(RunOutcome(failure=PERMANENT))
    runner.failing.add("first")
    harness.queue.retry_failed()
    live = [run for run in runner.runs if run.started and not run.exited]
    assert [run.job.title for run in live] == ["video"]


def test_lowering_the_limit_stops_new_starts_without_killing_running_ones():
    harness = QueueHarness(max_concurrent=3)
    harness.add("a", "b", "c", "d")
    harness.settings.update("maxConcurrent", 1)
    started(harness, "a").exit(FINISHED_FILE)
    started(harness, "b").exit(FINISHED_FILE)
    assert not any(run.killed or run.interrupts for run in harness.runner.runs)
    assert [run.job.title for run in harness.runner.runs] == ["a", "b", "c"]
    started(harness, "c").exit(FINISHED_FILE)
    assert [run.job.title for run in harness.runner.runs] == ["a", "b", "c", "d"]


def test_progress_never_goes_backwards_within_an_attempt_and_restarts_on_the_next():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    for done in (10, 60, 30, 70):
        run.listener.on_progress(run.job.id, update(done=done))
    assert run.job.progress == pytest.approx(0.63)
    run.exit(RunOutcome(failure=PERMANENT))
    harness.queue.retry(run.job.id)
    assert started(harness, "a").job.progress is None


def test_postprocessing_between_streams_does_not_pin_progress_at_the_end():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update("finished", 100))
    run.listener.on_postprocess(run.job.id, "Convertendo legendas")
    assert run.job.status == Status.POSTPROCESSING and run.job.progress == pytest.approx(0.9)
    run.listener.on_progress(run.job.id, update(done=50, format_id="140"))
    assert run.job.status == Status.DOWNLOADING and run.job.progress == pytest.approx(0.95)
    run.exit(FINISHED_FILE)
    assert run.job.progress == 1.0


def test_subtitle_downloads_do_not_count_as_a_media_stream():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update("finished", 100, format_id="NA"))
    assert run.job.progress is None and run.job.stage == "Baixando legendas"
    run.listener.on_progress(run.job.id, update(done=50))
    assert run.job.progress == pytest.approx(0.45)


def test_speed_exists_only_while_downloading():
    harness = QueueHarness()
    harness.add("a")
    run = started(harness, "a")
    run.listener.on_progress(run.job.id, update())
    assert run.job.speed == 2048.0
    run.listener.on_postprocess(run.job.id, "Juntando vídeo e áudio")
    assert run.job.speed == 0.0 and harness.queue.total_speed == 0.0


class CheckingRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.harness: QueueHarness | None = None
        self.attempts: dict[str, int] = {}

    def prepare(self, job: DownloadJob, listener: RunListener) -> FakeRun:
        harness = self.harness
        assert harness is not None
        live = [run for run in self.runs if not run.exited]
        assert len(live) < harness.settings.max_concurrent
        assert job.url not in {run.job.url for run in live}
        assert harness.queue._retry_at.get(job.id, harness.now) <= harness.now
        self.attempts[job.id] = self.attempts.get(job.id, 0) + 1
        assert self.attempts[job.id] <= 1 + MAX_AUTOMATIC_RETRIES
        return super().prepare(job, listener)


OUTCOMES = [
    FINISHED_FILE,
    RunOutcome(),
    RunOutcome(failure=PERMANENT),
    RunOutcome(failure=TRANSIENT),
    RunOutcome(failure=RATE_LIMITED),
    RunOutcome(failure=Failure("missing", "FailedToStart"), launched=False),
]


def check_invariants(harness: QueueHarness, runner: CheckingRunner, shown: dict[str, float], completed: set[str]):
    live = {run.job.id: run for run in runner.runs if not run.exited}
    jobs = {job.id: job for job in harness.jobs.jobs}
    assert set(live) == {job_id for job_id, job in jobs.items() if job.status in RUNNING}
    for run in live.values():
        if run.interrupts:
            assert run.job.stage == CANCELING_STAGE and run.job.speed == 0.0
    assert len({run.job.url for run in live.values()}) == len(live)
    for job_id, job in jobs.items():
        assert job.speed == 0.0 or job.status == Status.DOWNLOADING
        if job.status == Status.CANCELED:
            assert job.error == ""
        if job.status == Status.FAILED:
            assert job.error != ""
        if job_id in completed:
            assert job.status == Status.COMPLETED and job.progress == 1.0
        if job.status == Status.COMPLETED:
            completed.add(job_id)
        if job.status in RUNNING and job.progress is not None:
            assert job.progress >= shown.get(job_id, 0.0)
            shown[job_id] = job.progress


@pytest.mark.parametrize("seed", range(60))
def test_random_interleavings_keep_every_invariant(seed):
    rng = random.Random(seed)
    runner = CheckingRunner()
    harness = QueueHarness(max_concurrent=rng.randint(1, 3), runner=runner)
    runner.harness = harness
    shown: dict[str, float] = {}
    completed: set[str] = set()
    for _ in range(400):
        live = [run for run in runner.runs if not run.exited]
        jobs = list(harness.jobs.jobs)
        action = rng.choice(["add", "cancel", "retry", "remove", "progress", "post", "exit", "exit", "clock", "limit"])
        if action == "add":
            options = DownloadOptions(mode=rng.choice(["video", AUDIO]))
            harness.add(f"t{rng.randint(0, 5)}", url=f"https://fake.test/{rng.randint(0, 4)}", options=options)
        elif action in ("cancel", "retry", "remove") and jobs:
            target = rng.choice(jobs)
            if action == "retry" and target.status in {Status.FAILED, Status.CANCELED, Status.INTERRUPTED}:
                runner.attempts.pop(target.id, None)
                shown.pop(target.id, None)
            getattr(harness.queue, action)(target.id)
        elif action == "progress" and live:
            run = rng.choice(live)
            fid = rng.choice(["137", "140", "NA"])
            run.listener.on_progress(
                run.job.id, update(rng.choice(["downloading", "finished"]), rng.randint(0, 100), 100, fid)
            )
        elif action == "post" and live:
            run = rng.choice(live)
            run.listener.on_postprocess(run.job.id, "Processando")
        elif action == "exit" and live:
            run = rng.choice(live)
            shown.pop(run.job.id, None)
            outcome = rng.choice(OUTCOMES)
            run.exit(outcome)
            if run.interrupts:
                assert run.job.status in {Status.CANCELED, Status.COMPLETED}
                assert run.job.status == Status.COMPLETED or not outcome.file_reported
        elif action == "clock":
            harness.now += rng.choice([1.0, 10.0, 100.0])
            harness.queue.schedule()
        elif action == "limit":
            harness.settings.update("maxConcurrent", rng.randint(1, 3))
            harness.queue.schedule()
        harness.queue.flush_progress()
        check_invariants(harness, runner, shown, completed)
    for job in [job for job in harness.jobs.jobs if job.status == Status.QUEUED]:
        harness.queue.cancel(job.id)
    for run in [run for run in runner.runs if not run.exited]:
        harness.queue.cancel(run.job.id)
        run.exit(RunOutcome(failure=PERMANENT))
    assert all(job.status not in RUNNING and job.status != Status.QUEUED for job in harness.jobs.jobs)
    assert not [run for run in runner.runs if not run.exited]
