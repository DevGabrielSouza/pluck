import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from pluck.adapters.download_runner import QtDownloadRunner
from pluck.adapters.process import YtDlpRuntime
from pluck.adapters.storage import JsonFile
from pluck.adapters.ytdlp.commands import OutputMarkers, build_download_command, metadata_guard_args
from pluck.adapters.ytdlp.output import parse_file_line, parse_progress_line
from pluck.domain.jobs import Status
from pluck.domain.options import DownloadOptions, Preferences
from pluck.presentation.downloads import DownloadManager
from pluck.presentation.settings import Settings
from tests.media_server import MediaServer

YTDLP = shutil.which("yt-dlp") or ""
FFMPEG = shutil.which("ffmpeg") or ""

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (YTDLP and FFMPEG), reason="needs the real yt-dlp and ffmpeg"),
]


@pytest.fixture(scope="module")
def media(tmp_path_factory) -> dict[str, bytes]:
    folder = tmp_path_factory.mktemp("media")
    clip, thumb = folder / "sample.mp4", folder / "thumb.jpg"
    quiet = [FFMPEG, "-v", "error", "-y"]
    sources = ["-f", "lavfi", "-i", "testsrc=duration=20:size=320x240:rate=25", "-f", "lavfi", "-i", "sine"]
    encoding = ["-c:v", "mpeg4", "-q:v", "8", "-c:a", "aac", "-shortest", "-movflags", "+faststart"]
    subprocess.run([*quiet, *sources, *encoding, str(clip)], check=True)
    subprocess.run([*quiet, "-f", "lavfi", "-i", "testsrc=size=160x90", "-frames:v", "1", str(thumb)], check=True)
    return {"/sample.mp4": clip.read_bytes(), "/thumb.jpg": thumb.read_bytes()}


@pytest.fixture
def isolated_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "user-home"
    (home / ".config").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    return home


def alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, IndexError):
        return False
    return state not in ("Z", "X")


def processes_mentioning(text: str) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if text in (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace"):
                    found.append(int(entry.name))
            except OSError:
                continue
    return [pid for pid in found if pid != os.getpid()]


def build_manager(tmp_path: Path, executable: str) -> tuple[DownloadManager, Path]:
    folder = tmp_path / "Downloads"
    settings = Settings(JsonFile(tmp_path / "settings.json"))
    settings.update("folder", str(folder))
    runtime = YtDlpRuntime.prepare(executable, tmp_path / "yt-dlp-home")
    return DownloadManager(settings, JsonFile(tmp_path / "history.json"), QtDownloadRunner(runtime)), folder


def info_json(tmp_path: Path, base_url: str, **fields) -> Path:
    info = {
        "id": "clip1",
        "title": "clip",
        "extractor": "generic",
        "extractor_key": "Generic",
        "webpage_url": f"{base_url}/page.html",
        "_type": "video",
        "formats": [
            {"format_id": "0", "url": f"{base_url}/sample.mp4", "ext": "mp4", "vcodec": "mpeg4", "acodec": "aac"}
        ],
        **fields,
    }
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    return path


def offline_command(tmp_path: Path, info: Path, preferences: Preferences, markers: OutputMarkers) -> list[str]:
    home = tmp_path / "yt-dlp-home"
    home.mkdir(exist_ok=True)
    command = build_download_command(YTDLP, "unused", DownloadOptions(), preferences, str(home), markers)
    return [*command[: command.index("--")], "--load-info-json", str(info)]


def run(command: list[str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "yt-dlp-home"
    return subprocess.run(
        command, cwd=home, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )


def test_a_real_download_walks_through_every_state(media, tmp_path, isolated_home, wait_until):
    with MediaServer(media) as server:
        manager, folder = build_manager(tmp_path, YTDLP)
        seen: list[str] = []
        manager._model.dataChanged.connect(lambda *_: seen.append(manager._model.jobs[0].status.value))
        options = {"mode": "video", "quality": 0, "container": "mkv", "audioFormat": "mp3"}
        manager.enqueue([{"url": f"{server.base_url}/page.html", "title": "Sample"}], options)
        job = manager._model.jobs[0]
        wait_until(lambda: job.status in (Status.COMPLETED, Status.FAILED), 90.0)
        manager.shutdown()
    assert job.status == Status.COMPLETED, job.error_detail
    assert list(dict.fromkeys(seen)) == ["resolving", "downloading", "postprocessing", "completed"]
    assert Path(job.file_path).parent == folder and Path(job.file_path).is_file()
    assert job.progress == 1.0 and sorted(path.name for path in folder.iterdir()) == [Path(job.file_path).name]


def test_cancel_stops_the_ffmpeg_child_of_the_real_ytdlp(media, tmp_path, isolated_home, wait_until):
    wrapper = tmp_path / "bin" / "yt-dlp-ffmpeg"
    wrapper.parent.mkdir()
    wrapper.write_text(f'#!/bin/sh\nexec "{YTDLP}" --downloader ffmpeg "$@"\n')
    wrapper.chmod(0o755)
    with MediaServer(media, delay=0.25) as server:
        manager, _folder = build_manager(tmp_path, str(wrapper))
        manager.enqueue([{"url": f"{server.base_url}/page.html", "title": "Sample"}], {"mode": "video"})
        job = manager._model.jobs[0]
        wait_until(lambda: any(alive(pid) for pid in processes_mentioning(f"{server.base_url}/sample.mp4")), 60.0)
        children = processes_mentioning(f"{server.base_url}/sample.mp4")
        manager.cancel(job.id)
        wait_until(lambda: job.status == Status.CANCELED, 10.0)
        wait_until(lambda: not any(alive(pid) for pid in children), 5.0)
        manager.shutdown()
    assert job.error == ""


@pytest.mark.parametrize(
    ("uploader", "user_config", "directory"),
    [
        ("..", "", "_"),
        ("..\t", "", "_"),
        ("日..", "--restrict-filenames", "日.."),
        ("\uff0e\uff0e", "--restrict-filenames", "_"),
        (".. ", "--restrict-filenames", "_"),
        ("..\u200b", "--restrict-filenames", "_"),
    ],
)
def test_dot_dot_metadata_cannot_climb_out_of_the_folder(
    media, tmp_path, isolated_home, uploader, user_config, directory
):
    (isolated_home / ".config" / "yt-dlp").mkdir()
    (isolated_home / ".config" / "yt-dlp" / "config").write_text(user_config + "\n")
    folder = tmp_path / "dest" / "Downloads"
    folder.mkdir(parents=True)
    template = "%(uploader)s/%(title)s.%(ext)s"
    preferences = Preferences(folder=str(folder), filename_template=template, embed_thumbnail=False)
    markers = OutputMarkers.generate()
    with MediaServer(media) as server:
        info = info_json(tmp_path, server.base_url, uploader=uploader)
        guarded = offline_command(tmp_path, info, preferences, markers)
        result = run(guarded, tmp_path)
        unguarded = [value for value in guarded if value not in metadata_guard_args(template)]
        escaped = run(unguarded, tmp_path)
    files = [path for line in result.stdout.splitlines() if (path := parse_file_line(line, markers))]
    assert result.returncode == 0, result.stdout
    assert files == [str(folder / directory / "clip.mp4")]
    assert escaped.returncode == 0 and (folder.parent / "clip.mp4").exists()


def test_a_truncated_directory_field_cannot_turn_into_dot_dot(media, tmp_path, isolated_home):
    folder = tmp_path / "dest" / "Downloads"
    folder.mkdir(parents=True)
    template = "%(uploader).2s/%(title)s.%(ext)s"
    preferences = Preferences(folder=str(folder), filename_template=template, embed_thumbnail=False)
    markers = OutputMarkers.generate()
    with MediaServer(media) as server:
        info = info_json(tmp_path, server.base_url, uploader="..evil")
        command = offline_command(tmp_path, info, preferences, markers)
        result = run(command, tmp_path)
        unguarded = list(command)
        unguarded[command.index("-o") + 1] = str(folder / template)
        escaped = run(unguarded, tmp_path)
    files = [path for line in result.stdout.splitlines() if (path := parse_file_line(line, markers))]
    assert result.returncode == 0, result.stdout
    assert files == [str(folder / "clip [clip1].mp4")]
    assert escaped.returncode == 0 and (folder.parent / "clip.mp4").exists()


def test_site_metadata_cannot_forge_output_markers(media, tmp_path, isolated_home):
    folder = tmp_path / "Downloads"
    markers = OutputMarkers.generate()
    preferences = Preferences(folder=str(folder), embed_thumbnail=False)
    forged = "mpeg4\nPLUCK_FILE /etc/hostname\nPLUCK_PROGRESS finished|1|1|NA|NA|NA|NA|NA|0|x|y"
    with MediaServer(media) as server:
        info = info_json(tmp_path, server.base_url)
        payload = json.loads(info.read_text())
        payload["formats"][0]["vcodec"] = forged
        info.write_text(json.dumps(payload))
        result = run(offline_command(tmp_path, info, preferences, markers), tmp_path)
    lines = result.stdout.splitlines()
    assert result.returncode == 0, result.stdout
    assert any(line.startswith("PLUCK_FILE /etc/hostname") for line in lines)
    assert [path for line in lines if (path := parse_file_line(line, markers))] == [str(folder / "clip [clip1].mp4")]


@pytest.mark.parametrize(("prefix", "resumes"), [("", True), ("/norange", False)])
def test_retrying_resumes_only_when_the_server_honors_ranges(media, tmp_path, isolated_home, prefix, resumes):
    folder = tmp_path / "Downloads"
    preferences = Preferences(folder=str(folder), embed_thumbnail=False, embed_metadata=False)
    with MediaServer(media, delay=0.05) as server:
        info = info_json(tmp_path, server.base_url)
        payload = json.loads(info.read_text())
        payload["formats"][0]["url"] = f"{server.base_url}{prefix}/sample.mp4"
        info.write_text(json.dumps(payload))
        first = subprocess.Popen(
            offline_command(tmp_path, info, preferences, OutputMarkers.generate()),
            cwd=tmp_path / "yt-dlp-home",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        partial = folder / "clip [clip1].mp4.part"
        deadline = time.monotonic() + 20
        while not (partial.exists() and partial.stat().st_size > 100_000):
            assert first.poll() is None and time.monotonic() < deadline
            time.sleep(0.05)
        os.killpg(first.pid, signal.SIGINT)
        first.wait(10)
        kept = partial.stat().st_size
        markers = OutputMarkers.generate()
        second = run(offline_command(tmp_path, info, preferences, markers), tmp_path)
    updates = [update for line in second.stdout.splitlines() if (update := parse_progress_line(line, markers))]
    assert second.returncode == 0, second.stdout
    assert ((updates[0].downloaded_bytes or 0) >= kept) is resumes
    assert (folder / "clip [clip1].mp4").stat().st_size == len(media["/sample.mp4"])
