# Pull Temp Notes

## Keep note commit boundary

- `pullTempNotes.py` now treats Google Keep ingestion as a single commit boundary: `run_lineate_for_urls` and `append_opened_urls` must both succeed before Keep text is written locally and the source notes are trashed/synced. This avoids duplicating Keep-derived temp-note content after partial failures.
- Overlapping cron runs are prevented with a non-blocking file lock instead of early `keep.sync()`. That preserves the old "do not re-fetch while another run is still active" property without committing Keep state before the URL side effects finish.

## Keep URL-only suffix routing

- A Keep note ending with `..` only diverts to `clipboardToPhone/send.py` when the note already qualifies as URL-only under the existing Keep ingestion rule. Mixed text + URL notes still go to `temp index.md`; the suffix is an extra routing signal, not a new broader URL extractor mode.
- URL extraction now strips trailing sentence punctuation before routing. This is necessary because the `..` suffix marker often sits directly on the final URL, and sending the raw regex match would otherwise include those dots in the URL payload.
- The `..` marker may also appear as whitespace-separated trailing content after the final URL, so the URL-only check must ignore a terminal run of periods before deciding whether the note contains only URLs.
