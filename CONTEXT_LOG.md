# Pull Temp Notes

## Keep note commit boundary

- `pullTempNotes.py` now treats Google Keep ingestion as a single commit boundary: `run_lineate_for_urls` and `append_opened_urls` must both succeed before Keep text is written locally and the source notes are trashed/synced. This avoids duplicating Keep-derived temp-note content after partial failures.
- Overlapping cron runs are prevented with a non-blocking file lock instead of early `keep.sync()`. That preserves the old "do not re-fetch while another run is still active" property without committing Keep state before the URL side effects finish.
