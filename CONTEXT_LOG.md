# Pull Temp Notes

## Keep note commit boundary

- Lineate-backed Keep URL notes keep an explicit commit boundary: `run_lineate_for_urls` must succeed before those source notes are trashed/synced or their deferred temp-note text is written locally. Browser-routed URL notes additionally require `append_opened_urls` to succeed before commit.
- Overlapping cron runs are prevented with a non-blocking file lock instead of early `keep.sync()`. That preserves the old "do not re-fetch while another run is still active" property without committing URL-backed Keep state before its side effects finish.
- Infolio-routed Keep URL notes stay inside the Lineate commit boundary: `pullTempNotes.py` only trashes/syncs the source note after Lineate accepts the URL action with `--output-dest infolio`.

## Keep staged temp-note writes

- Plain Keep text now commits before any Lineate-backed URL conversion runs. The intent is to stop long or stuck Lineate jobs from blocking ordinary Keep notes from landing in `temp index.md`.
- This intentionally narrows the old single commit boundary: non-Lineate Keep notes are written, trashed, and synced in an early batch, while URL-only Keep notes that depend on Lineate still keep their own later boundary around conversion plus opened-URL logging.
- The trade-off is explicit: a later Lineate failure can no longer block earlier plain-note ingestion, but plain-note and URL-note commits from the same Keep sweep are no longer all-or-nothing together.

## MP3 temp-note cleanup boundary

- Processed audio files now commit on the same boundary as their temp-note text: once a transcription has been written to `temp index.md`, the source file is immediately renamed into the trash before any Keep URL/Lineate work starts.
- The goal is operational, not cosmetic: the capture folder should reflect only audio that has not been written into temp notes yet, so it stays easy to map trashed audio files back to the notes that already landed.

## Cosimo Substack failure debugging

- The April 18 Cosimo failures attributed to `pullTempNotes.py` were actually downstream Lineate extraction issues. The generated `lineate/data/summary_inputs/*cosimoresearch*` artifacts for the failed `open.substack.com` URLs contained only a markdown heading with the canonical URL, which means article extraction produced an empty shell before any summary/highlights call.
- Because Lineate still passed that shell through title/highlights/summary generation, some pages failed later on malformed summary output while others "succeeded" and cached hallucinated missing-content boilerplate. The root bug is therefore in Lineate's extraction/validation path, not in `pullTempNotes.py`'s URL routing.

## Keep URL-only suffix routing

- A Keep note ending with `..` only diverts to Lineate's `infolio` output destination when the note already qualifies as URL-only under the existing Keep ingestion rule. Mixed text + URL notes still go to `temp index.md`; the suffix is an extra routing signal, not a new broader URL extractor mode.
- URL extraction now strips trailing sentence punctuation before routing. This is necessary because the `..` suffix marker often sits directly on the final URL, and sending the raw regex match would otherwise include those dots in the URL payload.
- The `..` marker may also appear as whitespace-separated trailing content after the final URL, so the URL-only check must ignore a terminal run of periods before deciding whether the note contains only URLs.
- This marker used to send URL-only notes through `clipboardToPhone/send.py`; that path was removed from `pullTempNotes.py` once the marker became an Infolio ingestion signal instead.

## Keep text-fragment URLs

- Keep body lines that begin with `http` and contain `#:~:text=` are dropped before any Keep-note URL routing or markdown formatting. These are browser text-fragment URLs and should not be written into temp notes or treated as URL payloads.

## Keep URL conversion retry limit

- URL-only Keep notes that depend on lineate now persist a per-note failure count in `logs/keep_url_retry_counts.json`. After three conversion failures, `pullTempNotes.py` stops retrying, writes the raw Keep note text into the temp notes file, and trashes the source note so it cannot loop forever.

## Keep network hangs

- Google Keep auth/sync is now bounded by a hard 120s alarm in `keep_auth.py`. The concrete failure this addresses was a `pullTempNotes.py` process that stayed stuck overnight in an SSL socket read during Keep auth, which kept the file lock open and blocked every later cron/manual run from importing new notes.
