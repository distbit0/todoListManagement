from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import pytest

import keep_auth
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


class FakeTimestamp:
    def timestamp(self) -> int:
        return 0


class FakeTimestamps:
    edited = FakeTimestamp()


class FakeKeepNote:
    def __init__(
        self,
        text: str,
        title: str = "",
        *,
        note_id: str | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.text = text
        self.title = title
        self.id = note_id
        self.events = events
        self.timestamps = FakeTimestamps()

    def trash(self) -> None:
        if self.events is not None:
            self.events.append("trash")


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
        "build_keep_sync_plan",
        lambda keep_arg: (
            "\nkeep text",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com",
                    browser_urls=["https://example.com"],
                    phone_urls=[],
                )
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls: events.append("lineate"),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "send_urls_to_phone",
        lambda urls: events.append("send"),
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
        "build_keep_sync_plan",
        lambda keep_arg: (
            "\nkeep text",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com",
                    browser_urls=["https://example.com"],
                    phone_urls=["https://phone.example"],
                )
            ],
            [],
        ),
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
    monkeypatch.setattr(
        pullTempNotes,
        "send_urls_to_phone",
        lambda urls: events.append("send"),
    )

    original_write_to_file = pullTempNotes.writeToFile

    def track_write(file_path, text):
        events.append("write")
        original_write_to_file(file_path, text)

    monkeypatch.setattr(pullTempNotes, "writeToFile", track_write)

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == ["lineate", "append", "send", "write", "trash", "sync"]
    assert temp_notes_path.read_text() == "existing\nkeep text\n"


def test_sync_keep_notes_does_not_apply_keep_timeout_to_lineate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    note = FakeNote(events)
    keep = FakeKeep(events)
    temp_notes_path = tmp_path / "temp.md"
    temp_notes_path.write_text("existing\n")

    monkeypatch.setattr(keep_auth, "KEEP_NETWORK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(
        pullTempNotes,
        "build_keep_sync_plan",
        lambda keep_arg: (
            "",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com",
                    browser_urls=["https://example.com"],
                    phone_urls=[],
                )
            ],
            [],
        ),
    )

    def slow_lineate(urls):
        time.sleep(0.1)
        events.append("lineate")

    monkeypatch.setattr(pullTempNotes, "run_lineate_for_urls", slow_lineate)
    monkeypatch.setattr(
        pullTempNotes,
        "append_opened_urls",
        lambda urls, file_path: events.append("append"),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "sync_keep",
        lambda keep_arg: keep_auth.run_with_keep_timeout(
            "Google Keep sync", lambda: events.append("sync")
        ),
    )

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == ["lineate", "append", "trash", "sync"]


def test_sync_keep_notes_writes_raw_text_after_third_lineate_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    note = FakeKeepNote(
        "https://example.com",
        note_id="keep-note-1",
        events=events,
    )
    keep = FakeKeep(events)
    temp_notes_path = tmp_path / "temp.md"
    temp_notes_path.write_text("existing\n")
    retry_counts_path = tmp_path / "keep_url_retry_counts.json"

    monkeypatch.setattr(
        pullTempNotes,
        "KEEP_URL_RETRY_COUNTS_FILE",
        str(retry_counts_path),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "build_keep_sync_plan",
        lambda keep_arg: (
            "",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com",
                    browser_urls=["https://example.com"],
                    phone_urls=[],
                )
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, ["lineate"])
        ),
    )

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n"
    assert retry_counts_path.read_text().strip() == '{\n  "keep-note-1": 1\n}'
    assert events == ["sync"]

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n"
    assert retry_counts_path.read_text().strip() == '{\n  "keep-note-1": 2\n}'
    assert events == ["sync", "sync"]

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n\nhttps://example.com\n"
    assert retry_counts_path.read_text().strip() == "{}"
    assert events == ["sync", "sync", "trash", "sync"]


def test_save_notes_from_keep_sends_double_stop_url_only_notes_to_phone() -> None:
    note = FakeKeepNote("https://example.com\nhttps://slack.com/example ..")
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, browser_urls, phone_urls, notes_to_trash = pullTempNotes.saveNotesFromKeep(
        keep
    )

    assert keep_text == ""
    assert browser_urls == []
    assert phone_urls == ["https://example.com", "https://slack.com/example"]
    assert notes_to_trash == [note]


def test_save_notes_from_keep_keeps_mixed_double_stop_notes_in_markdown() -> None:
    note = FakeKeepNote("remember https://example.com..")
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, browser_urls, phone_urls, notes_to_trash = pullTempNotes.saveNotesFromKeep(
        keep
    )

    assert "remember https://example.com.." in keep_text
    assert browser_urls == []
    assert phone_urls == []
    assert notes_to_trash == [note]


def test_save_notes_from_keep_skips_text_fragment_url_lines() -> None:
    note = FakeKeepNote(
        "https://example.com/page#:~:text=skip%20me\nkeep this line\nhttp://ok.example"
    )
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, browser_urls, phone_urls, notes_to_trash = pullTempNotes.saveNotesFromKeep(
        keep
    )

    assert "#:~:text=" not in keep_text
    assert "keep this line" in keep_text
    assert "http://ok.example" in keep_text
    assert browser_urls == []
    assert phone_urls == []
    assert notes_to_trash == [note]


def test_send_urls_to_phone_uses_clipboard_queue_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper_calls: list[tuple[object, list[str], bool]] = []
    dummy_lineate = object()

    dummy_send_module = SimpleNamespace(
        _configure_logging=lambda: None,
        _load_lineate=lambda: dummy_lineate,
        _enqueue_and_send_url_jobs=lambda lineate, urls, *, convert: helper_calls.append(
            (lineate, urls, convert)
        ),
    )
    monkeypatch.setattr(
        pullTempNotes, "load_send_to_phone_module", lambda: dummy_send_module
    )

    pullTempNotes.send_urls_to_phone(
        ["https://example.com/one", "https://example.com/two"]
    )

    assert helper_calls == [
        (
            dummy_lineate,
            [
                "https://example.com/one",
                "https://example.com/two",
            ],
            True,
        )
    ]


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
