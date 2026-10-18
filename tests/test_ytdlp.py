import json

import pytest

from pluck.adapters.ytdlp.commands import (
    OutputMarkers,
    build_analyze_command,
    build_download_command,
)
from pluck.adapters.ytdlp.errors import friendly_error
from pluck.adapters.ytdlp.output import parse_file_line, parse_postprocess_line, parse_progress_line
from pluck.domain.formatting import format_bytes, format_count, format_duration, format_upload_date, format_views
from pluck.domain.media import (
    available_qualities,
    nested_playlist_url,
    pick_default_quality,
    stage_sizes,
)
from pluck.domain.options import AUDIO, BEST_QUALITY, VIDEO, DownloadOptions, Preferences, preview_filename
from pluck.domain.progress import ProgressTracker
from pluck.domain.urls import is_downloadable_url, is_inside_playlist, looks_like_url, normalize_url
from pluck.presentation.media_view import describe_media
from tests.conftest import FIXTURES


@pytest.fixture
def modern_video() -> dict:
    return json.loads((FIXTURES / "modern_video.json").read_text())


@pytest.fixture
def playlist() -> dict:
    return json.loads((FIXTURES / "playlist.json").read_text())


HOME = "/srv/pluck-home"


MARKERS = OutputMarkers("t0k3n")


def download_command(*arguments, **keywords):
    return build_download_command(*arguments, home=HOME, markers=MARKERS, **keywords)


def progress_line(body: str):
    return parse_progress_line(MARKERS.progress + body, MARKERS)


def analyze_command(*arguments, **keywords):
    return build_analyze_command(*arguments, home=HOME, **keywords)


def preferences(**overrides) -> Preferences:
    return Preferences(folder="/tmp/out", **overrides)


def test_video_command_limits_resolution_and_prefers_mp4():
    command = download_command("yt-dlp", "https://y/1", DownloadOptions(VIDEO, 1080, "mp4"), preferences())
    assert command[0] == "yt-dlp"
    assert command[-2:] == ["--", "https://y/1"]
    assert command[command.index("-S") + 1] == "res:1080,ext:mp4:m4a"
    assert command[command.index("-f") + 1] == "bv*+ba/b"
    assert command[command.index("--merge-output-format") + 1] == "mp4"
    assert set(MARKERS.arguments()) <= set(command)
    assert "--embed-chapters" in command and "--embed-thumbnail" in command


def test_best_mkv_has_no_sort_override():
    command = download_command("yt-dlp", "u", DownloadOptions(VIDEO, BEST_QUALITY, "mkv"), preferences())
    assert "-S" not in command
    assert command[command.index("--remux-video") + 1] == "mkv"


def test_audio_command_extracts_and_skips_video_only_flags():
    command = download_command(
        "yt-dlp", "u", DownloadOptions(AUDIO, audio_format="opus"), preferences(subtitles=True, embed_chapters=True)
    )
    assert command[command.index("--audio-format") + 1] == "opus"
    assert "-x" in command
    assert "--embed-chapters" not in command and "--write-subs" not in command


def test_optional_flags_follow_preferences():
    command = download_command(
        "yt-dlp",
        "u",
        DownloadOptions(VIDEO, 720, "mp4"),
        preferences(embed_thumbnail=False, embed_metadata=False, subtitles=True, cookies_browser="firefox"),
    )
    assert "--embed-thumbnail" not in command and "--embed-metadata" not in command
    assert command[command.index("--sub-langs") + 1] == "pt.*,en.*"
    assert command[command.index("--cookies-from-browser") + 1] == "firefox"


def test_unknown_cookie_browser_is_ignored():
    command = download_command("yt-dlp", "u", DownloadOptions(), preferences(cookies_browser="netscape"))
    assert "--cookies-from-browser" not in command


def test_analyze_command_respects_playlist_choice():
    single = analyze_command("yt-dlp", "u", include_playlist=False, cookies_browser="")
    whole = analyze_command("yt-dlp", "u", include_playlist=True, cookies_browser="brave")
    assert "--no-playlist" in single and "--flat-playlist" in single
    assert "--no-playlist" not in whole
    assert whole[whole.index("--cookies-from-browser") + 1] == "brave"


def test_parse_progress_line_with_estimate_and_missing_fields():
    update = progress_line("downloading|1024|NA|4096|2048.5|3|NA|NA|137|avc1|none")
    assert update is not None
    assert update is not None
    assert update.total_bytes == 4096
    assert update.fraction == 0.25
    assert update.video_only and not update.audio_only
    assert progress_line("broken|1") is None
    assert parse_progress_line("[download] 10%", MARKERS) is None


def test_parse_fragment_progress():
    update = progress_line("downloading|NA|NA|NA|NA|NA|3|12|hls-1|avc1|mp4a")
    assert update is not None
    assert update is not None and update.fraction == 0.25


def test_parse_postprocess_and_file_lines():
    assert parse_postprocess_line(MARKERS.postprocess + "started|Merger", MARKERS) == (
        "started",
        "Juntando vídeo e áudio",
    )
    assert parse_postprocess_line(MARKERS.postprocess + "started|FixupM3u8", MARKERS) == (
        "started",
        "Corrigindo o arquivo",
    )
    assert parse_postprocess_line(MARKERS.postprocess + "started|Unknown", MARKERS) == ("started", "Processando")
    assert parse_file_line(MARKERS.file + "/tmp/a b.mp4\n", MARKERS) == "/tmp/a b.mp4"
    assert parse_file_line(MARKERS.file + "", MARKERS) is None


def test_tracker_weights_video_and_audio_streams():
    tracker = ProgressTracker(VIDEO, [900, 100])
    halfway_video = progress_line("downloading|450|900|NA|10|1|NA|NA|137|avc1|none")
    assert halfway_video is not None
    audio_half = progress_line("downloading|50|100|NA|10|1|NA|NA|140|none|mp4a")
    assert audio_half is not None
    first = tracker.on_download(halfway_video)
    second = tracker.on_download(audio_half)
    assert first.fraction == pytest.approx(0.45)
    assert first.stage == "Baixando vídeo"
    assert second.fraction == pytest.approx(0.95)
    assert second.stage == "Baixando áudio"


def test_tracker_without_sizes_uses_fallback_share_and_handles_unknown_totals():
    tracker = ProgressTracker(VIDEO, [])
    done_video = progress_line("finished|10|10|NA|NA|NA|NA|NA|137|avc1|none")
    assert done_video is not None
    unknown = progress_line("downloading|5|NA|NA|NA|NA|NA|NA|140|none|mp4a")
    assert unknown is not None
    assert tracker.on_download(done_video).fraction == pytest.approx(0.9)
    assert tracker.on_download(unknown).fraction == pytest.approx(0.9)


def test_friendly_errors():
    assert "cookies" in friendly_error("ERROR: [youtube] x: Sign in to confirm you’re not a bot")
    assert "idade" in friendly_error("ERROR: [youtube] x: Sign in to confirm your age")
    assert friendly_error("ERROR: Unsupported URL: https://a.b") == "Esse link não é suportado."
    assert friendly_error("ERROR: [generic] something exotic") == "something exotic"


def test_url_helpers():
    assert normalize_url("  youtube.com/watch?v=1 extra") == "https://youtube.com/watch?v=1"
    assert looks_like_url("https://youtu.be/abc")
    assert not looks_like_url("hello world")
    assert not looks_like_url("file:///etc/passwd")
    assert not looks_like_url("https://a.b/\x00x")
    assert not looks_like_url("https://a.b/" + "x" * 5000)
    for malformed in ("https://[abc", "https://exa\uff0fmple.com/x"):
        assert not looks_like_url(malformed)
        assert not is_downloadable_url(malformed)
        assert not is_inside_playlist(malformed)
    assert is_inside_playlist("https://www.youtube.com/watch?v=a&list=PL1")
    assert not is_inside_playlist("https://www.youtube.com/playlist?list=PL1")


def test_qualities_and_sizes_from_real_formats(modern_video):
    formats = modern_video["formats"]
    qualities = available_qualities(formats)
    assert qualities[:4] == [BEST_QUALITY, 2160, 1440, 1080]
    sizes = stage_sizes(formats, modern_video["duration"], DownloadOptions(VIDEO, 1080, "mp4"))
    assert len(sizes) == 2 and all(size > 0 for size in sizes)
    assert stage_sizes(formats, modern_video["duration"], DownloadOptions(AUDIO))[0] > 0


def test_default_quality_falls_back_to_closest_lower():
    assert pick_default_quality([0, 720, 480], 1080) == 720
    assert pick_default_quality([0, 2160, 1440], 1080) == 0
    assert pick_default_quality([0, 1080], 1080) == 1080


def test_describe_video(modern_video):
    url = "https://www.youtube.com/watch?v=fOT0BUpITw8&list=PL1"
    info = describe_media(modern_video, url, 1080)
    assert info["kind"] == "video"
    assert info["partOfPlaylist"] is True
    assert info["defaultQuality"] == 1080
    assert info["qualities"][0]["label"] == "Melhor"
    assert info["audioFormats"][2]["label"] == "Opus"
    assert info["durationText"] == "3:54"


def test_describe_playlist(playlist):
    info = describe_media(playlist, playlist["webpage_url"], 1080)
    assert info["kind"] == "playlist"
    assert info["totalCount"] == 182
    assert len(info["entries"]) == 12
    assert info["entries"][0]["thumbnail"].endswith("/mqdefault.jpg")
    assert info["entries"][0]["url"].startswith("https://www.youtube.com/watch?v=")


def test_nested_channel_tabs_are_detected():
    channel = {"_type": "playlist", "entries": [{"ie_key": "YoutubeTab", "url": "https://youtube.com/@a/videos"}]}
    assert nested_playlist_url(channel) == "https://youtube.com/@a/videos"
    assert nested_playlist_url({"_type": "playlist", "entries": [{"ie_key": "Youtube", "url": "x"}]}) is None


def test_preview_filename():
    assert preview_filename("%(channel)s - %(title)s.%(ext)s") == "jawed - Me at the zoo.mp4"
    assert preview_filename("%(unknown)s.%(ext)s") == "NA.mp4"
    assert preview_filename("  ") == "Me at the zoo [jNQXAC9IVRw].mp4"


def test_formatting_in_portuguese():
    assert format_bytes(0) == ""
    assert format_bytes(512) == "512 B"
    assert format_bytes(1536) == "1,5 KB"
    assert format_bytes(150 * 1024 * 1024) == "150 MB"
    assert format_duration(19) == "0:19"
    assert format_duration(3723) == "1:02:03"
    assert format_count(1000) == "1 mil"
    assert format_count(44_487_338) == "44,5 mi"
    assert format_count(444_873_386) == "445 mi"
    assert format_views(1) == "1 visualização"
    assert format_upload_date("20050424") == "24/04/2005"
    assert format_upload_date("2005") == ""


def test_m4a_prefers_native_aac_source(modern_video):
    command = download_command("yt-dlp", "u", DownloadOptions(AUDIO, audio_format="m4a"), preferences())
    assert command[command.index("-f") + 1] == "ba[ext=m4a]/ba/b"
    mp3 = download_command("yt-dlp", "u", DownloadOptions(AUDIO, audio_format="mp3"), preferences())
    assert mp3[mp3.index("-f") + 1] == "ba/b"


def test_preferences_round_trip_and_sanitize():
    original = Preferences(folder="/x", filename_template="%(title)s.%(ext)s", subtitles=True, cookies_browser="brave")
    assert Preferences.from_dict(original.to_dict()) == original
    assert Preferences.from_dict({"subtitles": "yes", "filenameTemplate": " "}) == Preferences(folder="")


@pytest.mark.parametrize(
    ("url", "accepted"),
    [
        ("https://www.youtube.com/watch?v=abc", True),
        ("http://vimeo.com/1", True),
        ("file:///etc/passwd", False),
        ("ytsearch:cats", False),
        ("https://", False),
        ("https://exa mple.com/v", False),
        ("https://example.com/\x00", False),
        ("https://example.com/" + "a" * 5000, False),
        ("", False),
    ],
)
def test_only_plain_web_urls_are_downloadable(url, accepted):
    assert is_downloadable_url(url) is accepted
