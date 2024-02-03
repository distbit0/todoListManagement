import gkeepapi
import json
import utils.general as general


def fetch_notes_text():
    keep = gkeepapi.Keep()
    keep.resume(
        general.getConfig()["username"],
        general.getConfig()["masterKey"],
    )

    gnotes = list(keep.find(archived=False, trashed=False))
    # Extract text from each note and compile into a newline-separated string
    seenNotes = json.load(open(general.getAbsPath("../seenNotes.json")))
    notes_text = "\n\n" + "\n\n".join(
        note.text for note in gnotes if note.text and note.id not in seenNotes
    )
    if notes_text.strip():
        with open(general.getConfig()["tempNotesPath"], "a") as f:
            f.write(notes_text)

    for note in gnotes:
        if note.id not in seenNotes:
            seenNotes.append(note.id)

    json.dump(seenNotes, open(general.getAbsPath("../seenNotes.json"), "w"))

    for gnote in gnotes:
        gnote.archived = True
        gnote._archived = True

    keep.sync()


fetch_notes_text()
