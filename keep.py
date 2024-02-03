import gkeepapi
import utils.general as general


def fetch_notes_text():
    keep = gkeepapi.Keep()
    keep.resume(
        general.getConfig()["username"],
        general.getConfig()["masterKey"],
    )

    gnotes = list(keep.find(archived=False, trashed=False))
    # Extract text from each note and compile into a newline-separated string
    notes_text = "\n\n"
    for note in gnotes:
        if note.text or note.title:
            notes_text += note.title + "\n" if note.title else ""
            notes_text += note.text if note.text else ""
            notes_text += "\n\n"

    notes_text = notes_text.replace("\n\n\n", "\n\n")
    if notes_text.strip():
        with open(general.getConfig()["tempNotesPath"], "a") as f:
            f.write(notes_text)

    for gnote in gnotes:
        gnote.archived = True

    keep.sync()


fetch_notes_text()
