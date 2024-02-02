import gkeepapi


def fetch_notes_text(email, password):
    # Initialize the Keep API
    keep = gkeepapi.Keep()
    success = keep.login(email, password)

    if not success:
        return "Failed to log in to Google Keep"

    # Fetch all notes
    gnotes = keep.all()

    # Extract text from each note and compile into a newline-separated string
    notes_text = "\n".join(note.text for note in gnotes if note.text)

    return notes_text


email = ""
password = ""

# Fetch and print the notes text
notes_text = fetch_notes_text(email, password)
print(notes_text)
