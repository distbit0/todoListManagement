from pathlib import Path

import pytest

import pullTempNotes


class FakeNote:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def trash(self) -> None:
        self.events.append("trash")


class FakeKeep:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def sync(self) -> None:
        self.events.append("sync")


def test_sync_keep_notes_commits_only_after_url_side_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    note = FakeNote(events)
    keep = FakeKeep(events)
    temp_notes_path = tmp_path / "temp.md"
    temp_notes_path.write_text("existing\n")

    monkeypatch.setattr(
        pullTempNotes,
        "saveNotesFromKeep",
        lambda keep_arg: ("\nkeep text", ["https://example.com"], [note]),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls: events.append("lineate"),
    )

    def fail_append(urls, file_path):
        events.append("append")
        raise RuntimeError("append failed")

    monkeypatch.setattr(pullTempNotes, "append_opened_urls", fail_append)

    with pytest.raises(RuntimeError, match="append failed"):
        pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == ["lineate", "append"]
    assert temp_notes_path.read_text() == "existing\n"


def test_sync_keep_notes_orders_commit_steps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    note = FakeNote(events)
    keep = FakeKeep(events)
    temp_notes_path = tmp_path / "temp.md"
    temp_notes_path.write_text("existing\n")

    monkeypatch.setattr(
        pullTempNotes,
        "saveNotesFromKeep",
        lambda keep_arg: ("\nkeep text", ["https://example.com"], [note]),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls: events.append("lineate"),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "append_opened_urls",
        lambda urls, file_path: events.append("append"),
    )

    original_write_to_file = pullTempNotes.writeToFile

    def track_write(file_path, text):
        events.append("write")
        original_write_to_file(file_path, text)

    monkeypatch.setattr(pullTempNotes, "writeToFile", track_write)

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == ["lineate", "append", "write", "trash", "sync"]
    assert temp_notes_path.read_text() == "existing\nkeep text\n"


def test_acquire_script_lock_exits_when_another_run_is_active(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pullTempNotes, "LOCK_FILE", str(tmp_path / "pullTempNotes.lock"))

    first_lock = pullTempNotes.acquire_script_lock()
    try:
        with pytest.raises(SystemExit) as exit_info:
            pullTempNotes.acquire_script_lock()
    finally:
        first_lock.close()

    assert exit_info.value.code == 0
