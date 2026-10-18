import json
import logging
import threading

from pluck.adapters.storage import BackgroundWriter, JsonFile, write_json_atomically, write_logging_failures
from pluck.presentation.settings import Settings


def test_atomic_write_leaves_no_temporary_files(tmp_path):
    target = tmp_path / "nested" / "data.json"
    write_json_atomically(target, {"a": 1})
    write_json_atomically(target, {"a": 2})
    assert json.loads(target.read_text()) == {"a": 2}
    assert [path.name for path in target.parent.iterdir()] == ["data.json"]


def test_files_are_private_to_the_user(tmp_path):
    target = tmp_path / "history.json"
    write_json_atomically(target, {})
    assert target.stat().st_mode & 0o077 == 0


def test_failure_is_logged_not_raised(tmp_path, caplog):
    blocker = tmp_path / "file"
    blocker.write_text("")
    with caplog.at_level(logging.ERROR):
        assert write_logging_failures(blocker / "child.json", {}) is False
    assert "could not save" in caplog.text


def test_background_writer_runs_off_the_calling_thread_in_order(tmp_path):
    writer = BackgroundWriter()
    target = tmp_path / "out.json"
    caller = threading.get_ident()
    seen: list[int] = []
    original = write_json_atomically

    def spy(path, payload):
        seen.append(threading.get_ident())
        original(path, payload)

    import pluck.adapters.storage as storage

    storage.write_json_atomically = spy
    try:
        for index in range(20):
            writer.write(target, {"index": index})
        writer.close()
    finally:
        storage.write_json_atomically = original
    assert json.loads(target.read_text()) == {"index": 19}
    assert seen and caller not in seen


def test_writes_after_close_still_reach_disk(tmp_path):
    writer = BackgroundWriter()
    writer.close()
    writer.write(tmp_path / "late.json", {"ok": True})
    assert json.loads((tmp_path / "late.json").read_text()) == {"ok": True}


def test_settings_survive_an_unwritable_config_folder(tmp_path, qt_app, caplog):
    blocker = tmp_path / "config"
    blocker.write_text("")
    settings = Settings(JsonFile(blocker / "settings.json"))
    settings.update("maxConcurrent", 2)
    with caplog.at_level(logging.ERROR):
        settings.save()
    assert settings.value("maxConcurrent") == 2
    assert "could not save" in caplog.text
