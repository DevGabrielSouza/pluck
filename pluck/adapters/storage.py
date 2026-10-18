from __future__ import annotations

import json
import logging
import os
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json_atomically(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    _sync_directory(path.parent)


def _sync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def write_logging_failures(path: Path, payload: Any) -> bool:
    try:
        write_json_atomically(path, payload)
    except OSError:
        log.exception("could not save %s", path)
        return False
    return True


class JsonWriter(Protocol):
    def write(self, path: Path, payload: Any) -> None: ...


class SynchronousWriter:
    def write(self, path: Path, payload: Any) -> None:
        write_logging_failures(path, payload)


@dataclass(frozen=True)
class JsonFile:
    path: Path
    writer: JsonWriter = field(default_factory=SynchronousWriter)

    def read(self) -> Any:
        return read_json(self.path)

    def write(self, payload: Any) -> None:
        self.writer.write(self.path, payload)


class BackgroundWriter:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pluck-storage")
        self._closed = False

    def write(self, path: Path, payload: Any) -> None:
        if self._closed:
            write_logging_failures(path, payload)
            return
        self._executor.submit(write_logging_failures, path, payload)

    def submit(self, path: Path, payload: Any) -> Future[bool]:
        return self._executor.submit(write_logging_failures, path, payload)

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=True)
