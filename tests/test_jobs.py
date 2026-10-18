import itertools

import pytest

from pluck.application.history import HISTORY_VERSION, decode_history, encode_history
from pluck.domain.jobs import (
    PENDING,
    RUNNING,
    TRANSITIONS,
    DownloadJob,
    InvalidTransitionError,
    Status,
    can_transition,
)
from pluck.domain.options import DownloadOptions, Preferences

ENDINGS = {Status.COMPLETED, Status.FAILED, Status.CANCELED, Status.INTERRUPTED}

ALLOWED = {
    (Status.QUEUED, Status.RESOLVING),
    (Status.QUEUED, Status.FAILED),
    (Status.QUEUED, Status.CANCELED),
    (Status.QUEUED, Status.INTERRUPTED),
    *((Status.RESOLVING, target) for target in {Status.DOWNLOADING, Status.POSTPROCESSING, *ENDINGS}),
    *((Status.DOWNLOADING, target) for target in {Status.POSTPROCESSING, *ENDINGS}),
    *((Status.POSTPROCESSING, target) for target in {Status.DOWNLOADING, *ENDINGS}),
    (Status.FAILED, Status.QUEUED),
    (Status.CANCELED, Status.QUEUED),
    (Status.INTERRUPTED, Status.QUEUED),
}


def make_job(status: Status = Status.QUEUED) -> DownloadJob:
    return DownloadJob(
        url="https://example.com/v",
        title="t",
        options=DownloadOptions(),
        preferences=Preferences(folder="/tmp"),
        status=status,
    )


def test_every_status_has_an_entry():
    assert set(TRANSITIONS) == set(Status)


def test_the_requested_lifecycle_states_exist():
    expected = {"queued", "resolving", "downloading", "postprocessing", "completed", "failed", "canceled"}
    assert expected <= {status.value for status in Status}


@pytest.mark.parametrize(("current", "target"), list(itertools.product(Status, Status)))
def test_transition_table_is_exactly_the_documented_one(current, target):
    assert can_transition(current, target) == ((current, target) in ALLOWED)
    job = make_job(current)
    if (current, target) in ALLOWED:
        job.transition(target)
        assert job.status == target
    else:
        with pytest.raises(InvalidTransitionError):
            job.transition(target)
        assert job.status == current


def test_completed_is_terminal():
    assert TRANSITIONS[Status.COMPLETED] == frozenset()


def test_canceled_is_never_reached_through_failed():
    assert Status.CANCELED not in TRANSITIONS[Status.FAILED]
    assert Status.FAILED not in TRANSITIONS[Status.CANCELED]


def test_requeue_clears_previous_outcome():
    job = make_job(Status.FAILED)
    job.error, job.error_detail, job.detail, job.progress, job.finished_at = "x", "y", "z", 0.5, 10.0
    job.transition(Status.QUEUED)
    assert (job.error, job.error_detail, job.detail, job.progress, job.finished_at) == ("", "", "", 0.0, 0)
    assert job.stage == "Na fila"


def test_every_attempt_starts_clean():
    job = make_job(Status.QUEUED)
    job.file_path, job.detail = "/tmp/old.mp4", "old"
    job.transition(Status.RESOLVING)
    assert (job.progress, job.file_path, job.detail, job.stage) == (None, "", "", "Preparando")


def test_finishing_records_time_and_stops_speed():
    job = make_job(Status.DOWNLOADING)
    job.speed = 1000.0
    job.transition(Status.COMPLETED)
    assert job.finished_at > 0 and job.speed == 0.0


@pytest.mark.parametrize("status", sorted(PENDING))
def test_unfinished_records_load_as_interrupted(status):
    record = make_job(status).to_record()
    loaded = DownloadJob.from_record(record)
    assert loaded is not None and loaded.status == Status.INTERRUPTED


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [("done", Status.COMPLETED), ("error", Status.FAILED), ("processing", Status.INTERRUPTED)],
)
def test_version_one_statuses_still_load(legacy, expected):
    record = {**make_job().to_record(), "status": legacy}
    loaded = DownloadJob.from_record(record)
    assert loaded is not None and loaded.status == expected


def test_history_round_trip_writes_the_current_version():
    jobs = [make_job(Status.COMPLETED), make_job(Status.FAILED)]
    payload = encode_history(jobs)
    assert payload["version"] == HISTORY_VERSION == 2
    assert [job.status for job in decode_history(payload)] == [Status.COMPLETED, Status.FAILED]


def test_repeated_ids_in_a_tampered_history_are_made_unique():
    first, second = make_job(Status.INTERRUPTED), make_job(Status.INTERRUPTED)
    second.id = first.id
    jobs = decode_history(encode_history([first, second]))
    assert len({job.id for job in jobs}) == 2 and jobs[0].id == first.id


def test_running_group_is_exactly_the_three_process_states():
    assert {Status.RESOLVING, Status.DOWNLOADING, Status.POSTPROCESSING} == RUNNING


@pytest.mark.parametrize(
    "record",
    [{}, {"url": "u", "status": "exploded"}, {"url": "u", "duration": "long"}, {"url": "u", "status": ["done"]}],
)
def test_malformed_records_are_skipped(record):
    assert DownloadJob.from_record(record) is None


@pytest.mark.parametrize(
    "thumbnail", ["file:///etc/passwd", "image://icon/x", "qrc:/a.png", "data:image/png;base64,AA"]
)
def test_tampered_history_cannot_point_thumbnails_at_local_resources(thumbnail):
    record = {**make_job(Status.COMPLETED).to_record(), "thumbnail": thumbnail}
    loaded = DownloadJob.from_record(record)
    assert loaded is not None and loaded.thumbnail == ""
