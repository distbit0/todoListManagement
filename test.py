import gkeepapi
import os
from dotenv import load_dotenv

load_dotenv()


def print_recently_edited_archived_notes(num_notes=50):
    keep = gkeepapi.Keep()
    keep.resume(
        os.environ["username"],
        os.environ["masterKey"],
    )

    archived_notes = list(keep.find(archived=True, trashed=False))
    archived_notes = sorted(
        archived_notes, key=lambda x: x.timestamps.edited.timestamp(), reverse=True
    )

    print(f"Most recently edited {num_notes} archived notes:")
    for i, gnote in enumerate(archived_notes[:num_notes], start=1):
        print(f"\n{i}. Title: {gnote.title}")
        print(f"   Text: {gnote.text}")
        print(f"   Edited: {gnote.timestamps.edited}")


print_recently_edited_archived_notes()
