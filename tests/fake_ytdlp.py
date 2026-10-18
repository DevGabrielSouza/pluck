#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


IGNORING_CHILD = "import signal, time; signal.signal(signal.SIGINT, signal.SIG_IGN); time.sleep(60)"


def emit(line: str) -> None:
    print(line, flush=True)


def emit_error(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


def template_prefix(arguments: list[str], option: str, stage: str) -> str:
    for index, value in enumerate(arguments[:-1]):
        if value == option and arguments[index + 1].startswith(stage + ":"):
            template = arguments[index + 1][len(stage) + 1 :]
            return template[: template.index("%(")]
    return ""


class Markers:
    def __init__(self, arguments: list[str]):
        self.progress = template_prefix(arguments, "--progress-template", "download")
        self.postprocess = template_prefix(arguments, "--progress-template", "postprocess")
        self.file = template_prefix(arguments, "--print", "after_move")


def progress(markers: Markers, status: str, done: int, total: int, format_id: str, vcodec: str, acodec: str) -> None:
    emit(f"{markers.progress}{status}|{done}|{total}|NA|1048576.0|1|NA|NA|{format_id}|{vcodec}|{acodec}")


def postprocess(markers: Markers, name: str) -> None:
    emit_error(f"{markers.postprocess}started|{name}")
    emit_error(f"{markers.postprocess}finished|{name}")


def folder_from(arguments: list[str]) -> Path:
    return Path(arguments[arguments.index("-o") + 1]).parent


def log_record(record: dict) -> None:
    log = os.environ.get("FAKE_YTDLP_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


def record_invocation(arguments: list[str]) -> None:
    log_record({"cwd": os.getcwd(), "argv": arguments, "pid": os.getpid(), "pgid": os.getpgid(0)})


def previous_attempts(url: str) -> int:
    log = os.environ.get("FAKE_YTDLP_LOG")
    if not log or not os.path.exists(log):
        return 0
    records = [json.loads(line) for line in Path(log).read_text().splitlines()]
    return sum(1 for record in records if record.get("argv", [""])[-1:] == [url]) - 1


def spawn_ignoring_child() -> None:
    child = subprocess.Popen([sys.executable, "-c", IGNORING_CHILD])
    log_record({"child": child.pid})


def finish_successfully(markers: Markers, arguments: list[str]) -> int:
    target = folder_from(arguments) / "Fake video [abc].mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * 2048)
    sys.stdout.write(f"{markers.file}{target}")
    sys.stdout.flush()
    return 0


def download(url: str, arguments: list[str]) -> int:
    markers = Markers(arguments)
    if url.endswith("/fail"):
        emit_error("WARNING: something odd")
        emit_error("ERROR: [youtube] abc: Private video. Sign in if you've been granted access")
        return 1
    if url.endswith("/silent"):
        return 3
    if url.endswith("/flaky") and previous_attempts(url) < 1:
        emit_error("ERROR: Unable to download webpage: <urlopen error [Errno -3] Temporary failure in name resolution>")
        return 1
    if url.endswith("/slow"):
        signal.signal(signal.SIGINT, lambda *_: sys.exit(1))
        progress(markers, "downloading", 10, 1000, "137", "avc1", "none")
        time.sleep(30)
        return 0
    if url.endswith("/child"):
        signal.signal(signal.SIGINT, lambda *_: sys.exit(1))
        spawn_ignoring_child()
        progress(markers, "downloading", 10, 1000, "137", "avc1", "none")
        time.sleep(30)
        return 0
    if url.endswith("/stubborn"):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        spawn_ignoring_child()
        progress(markers, "downloading", 10, 1000, "137", "avc1", "none")
        time.sleep(30)
        return 0
    if url.endswith("/crash"):
        progress(markers, "downloading", 10, 1000, "137", "avc1", "none")
        os.kill(os.getpid(), signal.SIGKILL)
    if url.endswith("/forged"):
        emit("PLUCK_FILE /etc/passwd")
        emit("PLUCK_PROGRESS downloading|1|1|NA|1.0|1|NA|NA|137|avc1|none")
        progress(markers, "downloading", 5, 10, "137", "avc1\nPLUCK_FILE /etc/hostname", "none")
    for done in (0, 500, 1000):
        progress(markers, "downloading" if done < 1000 else "finished", done, 1000, "137", "avc1", "none")
    for done in (0, 250):
        progress(markers, "downloading" if done < 250 else "finished", done, 250, "140", "none", "mp4a")
    postprocess(markers, "Merger")
    if url.endswith("/forged"):
        finish_successfully(markers, arguments)
        emit("")
        emit("PLUCK_FILE /etc/passwd")
        emit(f"{markers.file}/etc/passwd")
        emit(f"{markers.file}{folder_from(arguments)}/../outside.mp4")
        return 0
    return finish_successfully(markers, arguments)


NESTED_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLnested"


def analyze(url: str) -> int:
    if url.endswith("/fail"):
        print("ERROR: Unsupported URL: " + url, file=sys.stderr)
        return 1
    if url.endswith("/silent"):
        return 3
    if url.endswith("/garbage"):
        sys.stdout.write("not json")
        return 0
    if url.endswith("/hang"):
        time.sleep(30)
        return 0
    if url.endswith("/hang-child"):
        spawn_ignoring_child()
        time.sleep(30)
        return 0
    if url.endswith("/channel"):
        entries = [{"_type": "url", "ie_key": "YoutubeTab", "url": NESTED_PLAYLIST_URL, "title": "Videos"}]
        sys.stdout.write(json.dumps({"_type": "playlist", "title": "Channel", "entries": entries}))
        return 0
    fixture = "playlist.json" if "playlist" in url else "modern_video.json"
    sys.stdout.write(json.dumps(json.loads((FIXTURES / fixture).read_text())))
    return 0


def main() -> int:
    arguments = sys.argv[1:]
    record_invocation(arguments)
    url = arguments[-1]
    if "-J" in arguments:
        return analyze(url)
    return download(url, arguments)


if __name__ == "__main__":
    sys.exit(main())
