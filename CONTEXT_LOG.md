# Pull Temp Notes

## Keep note commit boundary

- `pullTempNotes.py` now treats Google Keep ingestion as a single commit boundary: `run_lineate_for_urls` and `append_opened_urls` must both succeed before Keep text is written locally and the source notes are trashed/synced. This avoids duplicating Keep-derived temp-note content after partial failures.
- Overlapping cron runs are prevented with a non-blocking file lock instead of early `keep.sync()`. That preserves the old "do not re-fetch while another run is still active" property without committing Keep state before the URL side effects finish.
- Phone-routed Keep URL notes use a different boundary now: once `clipboardToPhone/send.py` has durably enqueued the URLs into its shared Lineate-backed queue, `pullTempNotes.py` can trash/sync the Keep note. Delivery/conversion retries after that point belong to the queue owner, not to Keep ingestion.

## Keep URL-only suffix routing

- A Keep note ending with `..` only diverts to `clipboardToPhone/send.py` when the note already qualifies as URL-only under the existing Keep ingestion rule. Mixed text + URL notes still go to `temp index.md`; the suffix is an extra routing signal, not a new broader URL extractor mode.
- URL extraction now strips trailing sentence punctuation before routing. This is necessary because the `..` suffix marker often sits directly on the final URL, and sending the raw regex match would otherwise include those dots in the URL payload.
- The `..` marker may also appear as whitespace-separated trailing content after the final URL, so the URL-only check must ignore a terminal run of periods before deciding whether the note contains only URLs.
 - The phone-send path now calls `clipboardToPhone/send.py`'s queue helper directly, so URL conversion, batching, queue claims, and ntfy delivery all stay under the same shared queue logic as normal clipboard sends.

## Keep text-fragment URLs

- Keep body lines that begin with `http` and contain `#:~:text=` are dropped before any Keep-note URL routing or markdown formatting. These are browser text-fragment URLs and should not be written into temp notes or treated as URL payloads.

## Keep URL conversion retry limit

- URL-only Keep notes that depend on lineate now persist a per-note failure count in `logs/keep_url_retry_counts.json`. After three conversion failures, `pullTempNotes.py` stops retrying, writes the raw Keep note text into the temp notes file, and trashes the source note so it cannot loop forever.

## Keep network hangs

- Google Keep auth/sync is now bounded by a hard 120s alarm in `keep_auth.py`. The concrete failure this addresses was a `pullTempNotes.py` process that stayed stuck overnight in an SSL socket read during Keep auth, which kept the file lock open and blocked every later cron/manual run from importing new notes.
