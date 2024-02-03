import gkeepapi
import utils.general as general


def fetch_notes_text():
    keep = gkeepapi.Keep()
    keep.resume(
        general.getConfig()["username"],
        general.getConfig()["masterKey"],
    )

    gnotes = keep.find(archived=False, trashed=False)
    # Extract text from each note and compile into a newline-separated string
    notes_text = "\n\n" + "\n\n".join(note.text for note in gnotes if note.text)
    if notes_text.strip():
        with open(general.getConfig()["tempNotesPath"], "a") as f:
            f.write(notes_text)

    for gnote in gnotes:
        gnote.archived = True
        gnote._archived = True

    keep.sync()


fetch_notes_text()
