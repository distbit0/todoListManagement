from pathlib import Path
import subprocess
import time

import pytest

import keep_auth
import pullTempNotes


class FakeNote:
    def __init__(self, events: list[str], trash_event: str = "trash") -> None:
        self.events = events
        self.trash_event = trash_event

    def trash(self) -> None:
        self.events.append(self.trash_event)


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


def test_sync_keep_notes_commits_plain_keep_text_before_url_side_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    plain_keep_note = FakeNote(events, "plain_trash")
    url_note = FakeNote(events, "url_trash")
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
                    note=url_note,
                    note_title="",
                    raw_text="https://example.com",
                    lineate_urls=["https://example.com"],
                )
            ],
            [plain_keep_note],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls, output_dest="browser": events.append("lineate"),
    )

    def fail_append(urls, file_path):
        events.append("append")
        raise RuntimeError("append failed")

    monkeypatch.setattr(pullTempNotes, "append_opened_urls", fail_append)
    original_write_to_file = pullTempNotes.writeToFile

    def track_write(file_path, text):
        events.append("write")
        original_write_to_file(file_path, text)

    monkeypatch.setattr(pullTempNotes, "writeToFile", track_write)

    with pytest.raises(RuntimeError, match="append failed"):
        pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == ["write", "plain_trash", "sync", "lineate", "append"]
    assert temp_notes_path.read_text() == "existing\nkeep text\n"


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
            "",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com",
                    lineate_urls=["https://example.com"],
                    success_text="\nkeep text",
                )
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls, output_dest="browser": events.append("lineate"),
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
                    lineate_urls=["https://example.com"],
                )
            ],
            [],
        ),
    )

    def slow_lineate(urls, output_dest="browser"):
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


def test_main_commits_processed_mp3s_before_keep_url_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class DummyLock:
        def close(self) -> None:
            events.append("lock_close")

    monkeypatch.setattr(pullTempNotes, "acquire_script_lock", lambda: DummyLock())
    monkeypatch.setattr(
        pullTempNotes, "authenticate_keep", lambda: events.append("auth") or object()
    )
    monkeypatch.setattr(
        pullTempNotes, "delete_duplicate_files", lambda path: events.append("dedupe")
    )
    monkeypatch.setattr(
        pullTempNotes,
        "saveNotesFromMp3s",
        lambda: ("\n\ntranscribed note", {"note.mp3": {"transcription_successful": True}}),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "commit_processed_mp3_batch",
        lambda temp_path, text, processed, mp3_path: events.append("commit_mp3"),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "sync_keep_notes",
        lambda keep, temp_path, opened_urls_path: events.append("sync_keep_notes"),
    )
    monkeypatch.setattr(
        pullTempNotes.general,
        "getConfig",
        lambda: {
            "tempNotesPath": "/tmp/temp index.md",
            "mp3CaptureFolder": "/tmp/mp3s",
        },
    )

    pullTempNotes.main()

    assert events == [
        "auth",
        "dedupe",
        "commit_mp3",
        "sync_keep_notes",
        "lock_close",
    ]


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
                    lineate_urls=["https://example.com"],
                )
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls, output_dest="browser": (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, ["lineate"])
        ),
    )

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n"
    assert retry_counts_path.read_text().strip() == '{\n  "keep-note-1": 1\n}'
    assert events == []

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n"
    assert retry_counts_path.read_text().strip() == '{\n  "keep-note-1": 2\n}'
    assert events == []

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))
    assert temp_notes_path.read_text() == "existing\n\nhttps://example.com\n"
    assert retry_counts_path.read_text().strip() == "{}"
    assert events == ["trash", "sync"]


def test_build_keep_sync_plan_routes_double_stop_url_only_notes_to_infolio() -> None:
    note = FakeKeepNote("https://example.com\nhttps://slack.com/example ..")
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, url_actions, notes_to_trash = pullTempNotes.build_keep_sync_plan(keep)

    assert keep_text == ""
    assert len(url_actions) == 1
    assert url_actions[0].lineate_urls == [
        "https://example.com",
        "https://slack.com/example",
    ]
    assert url_actions[0].output_dest == "infolio"
    assert notes_to_trash == []


def test_build_keep_sync_plan_keeps_mixed_double_stop_notes_in_markdown() -> None:
    note = FakeKeepNote("remember https://example.com..")
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, url_actions, notes_to_trash = pullTempNotes.build_keep_sync_plan(keep)

    assert "remember https://example.com.." in keep_text
    assert url_actions == []
    assert notes_to_trash == [note]


def test_build_keep_sync_plan_skips_text_fragment_url_lines() -> None:
    note = FakeKeepNote(
        "https://example.com/page#:~:text=skip%20me\nkeep this line\nhttp://ok.example"
    )
    keep = type("Keep", (), {"find": lambda self, **kwargs: [note]})()

    keep_text, url_actions, notes_to_trash = pullTempNotes.build_keep_sync_plan(keep)

    assert "#:~:text=" not in keep_text
    assert "keep this line" in keep_text
    assert "http://ok.example" in keep_text
    assert url_actions == []
    assert notes_to_trash == [note]


def test_sync_keep_notes_sends_infolio_actions_to_lineate_without_opened_url_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[tuple[str, object]] = []
    note = FakeNote([])
    keep = FakeKeep([])
    temp_notes_path = tmp_path / "temp.md"
    temp_notes_path.write_text("existing\n")

    monkeypatch.setattr(
        pullTempNotes,
        "build_keep_sync_plan",
        lambda keep_arg: (
            "",
            [
                pullTempNotes.KeepUrlAction(
                    note=note,
                    note_title="",
                    raw_text="https://example.com.",
                    lineate_urls=["https://example.com"],
                    output_dest="infolio",
                )
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "run_lineate_for_urls",
        lambda urls, output_dest="browser": events.append(
            ("lineate", (urls, output_dest))
        ),
    )
    monkeypatch.setattr(
        pullTempNotes,
        "append_opened_urls",
        lambda urls, file_path: events.append(("append", urls)),
    )

    pullTempNotes.sync_keep_notes(keep, str(temp_notes_path), str(tmp_path / "urls.md"))

    assert events == [("lineate", (["https://example.com"], "infolio"))]


def test_run_lineate_for_urls_passes_output_dest_to_lineate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], bool, str]] = []

    def track_subprocess_run(command, *, check, env):
        calls.append((command, check, env["DISPLAY"]))

    monkeypatch.setattr(pullTempNotes.subprocess, "run", track_subprocess_run)

    pullTempNotes.run_lineate_for_urls(["https://example.com"], "infolio")

    assert calls == [
        (
            [
                "/home/pimania/dev/misc/automation/uvrun.sh",
                "/home/pimania/dev/lineate/src/lineate.py",
                "--force-convert-all",
                "--summarise",
                "--output-dest",
                "infolio",
                "https://example.com",
            ],
            True,
            ":0",
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
