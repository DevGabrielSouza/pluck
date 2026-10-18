import pytest

from pluck.adapters.ytdlp.commands import metadata_guard_args
from pluck.adapters.ytdlp.errors import (
    CRASH_MESSAGE,
    StderrTail,
    download_failure,
    error_detail,
    friendly_error,
    redact,
)
from pluck.adapters.ytdlp.output import MAX_PENDING_LINE, split_lines
from pluck.domain.media import is_playable_file
from pluck.domain.options import (
    VIDEO,
    Preferences,
    directory_fields,
    is_inside,
    is_safe_filename_template,
    names_the_id,
    safe_subtitle_languages,
)
from pluck.domain.progress import ProgressTracker, ProgressUpdate
from pluck.domain.retry import retry_delay
from pluck.domain.urls import safe_image_url
from pluck.domain.versions import MINIMUM_VERSION, MINIMUM_VERSION_TEXT, is_outdated, parse_version


def test_redact_hides_tokens_and_ip_in_media_urls():
    raw = "ERROR: unable to fetch https://rr1.googlevideo.com/videoplayback?expire=1&ip=200.1.2.3&sig=AbC&id=7"
    detail = error_detail(raw)
    assert "200.1.2.3" not in detail and "AbC" not in detail
    assert "ip=[redacted]" in detail and "sig=[redacted]" in detail and "id=7" in detail


def test_friendly_error_never_leaks_query_secrets():
    assert "secret" not in friendly_error("ERROR: [generic] https://a.b/x?token=secret failed")


def test_redact_keeps_ordinary_text():
    assert redact("Video unavailable https://youtu.be/abc?t=10") == "Video unavailable https://youtu.be/abc?t=10"


def test_split_lines_keeps_partial_line_for_next_chunk():
    lines, rest = split_lines("PLUCK_PRO", "GRESS a|b\nPLUCK_F")
    assert lines == ["PLUCK_PROGRESS a|b"] and rest == "PLUCK_F"


def test_split_lines_drops_a_runaway_partial_line():
    lines, rest = split_lines("", "x" * (MAX_PENDING_LINE + 1))
    assert lines == [] and rest == ""


@pytest.mark.parametrize(
    ("text", "outdated"),
    [
        ("2026.08.19", False),
        (MINIMUM_VERSION_TEXT, False),
        ("2024.07.01", True),
        ("2026.06.09", True),
        ("2026.07.03", True),
        ("", False),
    ],
)
def test_outdated_ytdlp_versions_are_flagged(text, outdated):
    assert is_outdated(text) is outdated


def test_parse_version_matches_the_minimum_constant():
    assert parse_version(MINIMUM_VERSION_TEXT) == MINIMUM_VERSION
    assert parse_version("nightly") is None


@pytest.mark.parametrize(("path", "playable"), [("/a/b.MP4", True), ("/a/b.opus", True), ("/a/x.desktop", False)])
def test_only_media_files_are_opened_directly(path, playable):
    assert is_playable_file(path) is playable


def test_unsafe_values_from_history_are_neutralized():
    restored = Preferences.from_dict({"filenameTemplate": "../../.bashrc", "subtitleLanguages": "--exec=x"})
    assert is_safe_filename_template(restored.filename_template)
    assert restored.subtitle_languages == safe_subtitle_languages("")


@pytest.mark.parametrize(
    ("template", "fields"),
    [
        ("%(title)s [%(id)s].%(ext)s", ()),
        ("%(uploader)s/%(title)s.%(ext)s", ("uploader",)),
        ("%(uploader,channel)s/%(upload_date>%Y)s/%(title)s.%(ext)s", ("uploader", "channel", "upload_date")),
        ("%(uploader|Desconhecido)s/%(title)s.%(ext)s", ("uploader",)),
        ("%(uploader)s - canal/%(title)s.%(ext)s", ()),
        ("%(playlist_index)03d/%(title)s.%(ext)s", ("playlist_index",)),
        ("..%(uploader)s/%(title)s.%(ext)s", ("uploader",)),
        ("Música/%(title)s.%(ext)s", ()),
    ],
)
def test_directory_components_made_only_of_site_fields_are_guarded(template, fields):
    assert directory_fields(template) == fields
    assert is_safe_filename_template(template)
    guard = metadata_guard_args(template)
    expected = ["--no-restrict-filenames", "--no-windows-filenames", "--replace-in-metadata", ",".join(fields)]
    assert guard == ([*expected, r"^[\W_]*$", "_"] if fields else [])


@pytest.mark.parametrize(
    "template",
    [
        "%(uploader|..)s/%(title)s.%(ext)s",
        "%(uploader.0)s/%(title)s.%(ext)s",
        "%(uploader&..)s/%(title)s.%(ext)s",
        "%(uploader).2s/%(title)s.%(ext)s",
        "%(uploader)+U/%(title)s.%(ext)s",
        "%(uploader)S/%(title)s.%(ext)s",
        "%(uploader)c/%(title)s.%(ext)s",
    ],
)
def test_directory_fields_that_cannot_be_guarded_make_the_template_unsafe(template):
    assert directory_fields(template) is None
    assert not is_safe_filename_template(template)
    assert metadata_guard_args(template) == []


@pytest.mark.parametrize(
    "template",
    [
        "%(uploader|Sem/Canal)s/%(title)s.%(ext)s",
        "%(uploader|a/..)s/%(title)s.%(ext)s",
        "%(upload_date>%Y/%m)s.%(ext)s",
    ],
)
def test_a_path_separator_inside_a_field_makes_the_template_unsafe(template):
    assert not is_safe_filename_template(template)
    assert metadata_guard_args(template) == []


@pytest.mark.parametrize(
    ("path", "inside"),
    [
        ("/srv/out/a.mp4", True),
        ("/srv/out/canal/a.mp4", True),
        ("/srv/out/../etc/passwd", False),
        ("/srv/out", False),
        ("/srv/outside/a.mp4", False),
        ("/etc/hostname|none", False),
        ("relative/a.mp4", False),
        ("//srv/out/a.mp4", True),
    ],
)
def test_reported_files_must_live_inside_the_download_folder(path, inside):
    assert is_inside("/srv/out", path) is inside


@pytest.mark.parametrize(
    ("template", "unique"),
    [
        ("%(title)s [%(id)s].%(ext)s", True),
        ("%(id)s.%(ext)s", True),
        ("%(id)s/%(title)s.%(ext)s", True),
        ("%(id|x)s.%(ext)s", True),
        ("%(title)s.%(ext)s", False),
        ("%%(id)s.%(ext)s", False),
        ("%(id).0s.%(ext)s", False),
        ("%(title,id)s.%(ext)s", False),
        ("%(idx)s.%(ext)s", False),
    ],
)
def test_only_a_rendered_id_counts_as_a_unique_name(template, unique):
    assert names_the_id(template) is unique


def test_a_folder_spelled_with_a_double_slash_still_contains_its_files():
    assert is_inside("//srv/out", "//srv/out/a.mp4")
    assert is_inside("//srv/out", "/srv/out/a.mp4")
    assert not is_inside("//srv/out", "//srv/outside/a.mp4")


def test_a_relative_folder_contains_nothing():
    assert not is_inside("Downloads", "/home/a/Downloads/x.mp4")


@pytest.mark.parametrize(
    ("url", "kept"),
    [
        ("https://i.ytimg.com/vi/x/mqdefault.jpg", True),
        ("http://127.0.0.1:8080/t.jpg", True),
        ("file:///etc/passwd", False),
        ("image://icon/folder", False),
        ("qrc:/pluck.svg", False),
        ("data:image/png;base64,AAAA", False),
        ("javascript:alert(1)", False),
        ("", False),
    ],
)
def test_thumbnails_only_load_from_the_web(url, kept):
    assert safe_image_url(url) == (url if kept else "")


def test_retry_delays_grow_and_jitter_stays_bounded():
    assert [retry_delay(attempt, False, 0.0) for attempt in (1, 2, 3)] == [5.0, 15.0, 45.0]
    assert retry_delay(1, True, 0.0) == 60.0
    assert retry_delay(1, False, 1.0) == pytest.approx(6.0)
    assert retry_delay(1, False, -5.0) == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("headline", "transient", "rate_limited"),
    [
        ("ERROR: [youtube] x: Private video", False, False),
        ("ERROR: Unable to download webpage: HTTP Error 404: Not Found", False, False),
        (
            "ERROR: Unable to download webpage: <urlopen error [Errno -3] Temporary failure in name resolution>",
            True,
            False,
        ),
        ("ERROR: unable to download video data: HTTP Error 503: Service Unavailable", True, False),
        ("ERROR: [youtube] x: HTTP Error 429: Too Many Requests", True, True),
        ("ERROR: The read operation timed out", True, False),
        ("ERROR: [download] Got error: Connection reset by peer", True, False),
        ("ERROR: Video unavailable", False, False),
        ("ERROR: Postprocessing: Conversion failed!", False, False),
        ("ERROR: unable to write data: [Errno 28] No space left on device", False, False),
    ],
)
def test_only_network_and_server_failures_are_retried(headline, transient, rate_limited):
    tail = StderrTail()
    tail.add(headline)
    failure = download_failure(tail, 1)
    assert (failure.transient, failure.rate_limited) == (transient, rate_limited)


def test_a_crash_is_never_retried():
    tail = StderrTail()
    tail.add("ERROR: The read operation timed out")
    failure = download_failure(tail, 9, crashed=True)
    assert failure.message == CRASH_MESSAGE and not failure.transient


def test_eta_covers_the_streams_still_to_come_and_needs_a_speed():
    tracker = ProgressTracker(VIDEO, [1000, 500])
    video = ProgressUpdate("downloading", 500, 1000, 100.0, 5, None, None, "137", "avc1", "none")
    assert tracker.on_download(video).detail.endswith("faltam 0:10")
    stalled = ProgressUpdate("downloading", 600, 1000, None, 5, None, None, "137", "avc1", "none")
    assert "faltam" not in tracker.on_download(stalled).detail
    audio = ProgressUpdate("downloading", 250, 500, 100.0, 3, None, None, "140", "none", "mp4a")
    assert tracker.on_download(audio).detail.endswith("faltam 0:03")
