import gkeepapi
import os
import re
import glob
import json
import utils.general as general
from openai import OpenAI
import hashlib
from dotenv import load_dotenv
from send2trash import send2trash

load_dotenv()


def calculate_file_hash(file_path, hash_algo="sha256"):
    """Calculate the hash of a chunk from the middle of a file."""
    hash_func = getattr(hashlib, hash_algo)()
    file_size = os.path.getsize(file_path)
    chunk_size = min(8192, file_size)
    middle_pos = file_size // 2

    with open(file_path, "rb") as file:
        file.seek(middle_pos - chunk_size // 2)
        chunk = file.read(chunk_size)
        hash_func.update(chunk)

    return hash_func.hexdigest()


def delete_duplicate_files(directory):
    """Delete files with matching hashes in a directory, sending them to trash."""
    if not os.path.isdir(directory):
        raise ValueError(f"The provided path {directory} is not a directory.")

    hashes = {}
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_hash = calculate_file_hash(file_path)
            if file_hash in hashes:
                # This file is a duplicate; send it to the trash
                send2trash(file_path)
                print(f"Moved to trash: {file_path}")
            else:
                # Record the hash of this unique file
                hashes[file_hash] = file_path


def saveNotesFromKeep():
    keep = gkeepapi.Keep()
    keep.resume(
        os.environ["username"],
        os.environ["masterKey"],
    )

    gnotes = list(keep.find(archived=False, trashed=False))
    gnotes = sorted(gnotes, key=lambda x: x.timestamps.edited.timestamp())
    # Extract text from each note and compile into a newline-separated string
    notes_text = "\n\n"
    for gnote in gnotes:
        if (gnote.text or gnote.title) and (
            gnote.title not in ["Questions", "Statements"]
        ):
            notes_text += gnote.title + "\n" if gnote.title else ""
            notes_text += gnote.text if gnote.text else ""
            notes_text += "\n\n"

    notes_text = notes_text.replace("\n\n\n", "\n\n")
    if notes_text.strip():
        with open(general.getConfig()["tempNotesPath"], "a") as f:
            f.write(notes_text)

    for gnote in gnotes:
        if not (gnote.title in ["Questions", "Statements"]):
            gnote.archived = True

    keep.sync()


def tryDeleteFile(path):
    try:
        os.remove(path)
    except:
        pass


def processMp3File(mp3FileName):
    apiKey = os.environ["openaiApiKey"]
    client = OpenAI(api_key=apiKey)
    api_response = client.audio.transcriptions.create(
        model="whisper-1",
        file=open(mp3FileName, "rb"),
        language="en",
        prompt="the transcription of my idea is as follows:",
    )
    return api_response.text


def sort_key(filename):
    match = re.search(r"(\d+)", os.path.basename(filename))
    if match:
        return int(match.group(1))
    return 0


def saveNotesFromMp3s():
    # 1. Get list of mp3 files
    # 2. for each mp3, check if it has been already processed by seeing if it is in processedMp3s.json
    # 3. if it has not already been, then process it and save its text to the file first, then delete the mp3 and mark it as processed in processedMp3s.json
    mp3FolderPath = general.getConfig()["mp3CaptureFolder"]
    processedMp3s = json.load(open(general.getAbsPath("../processedMp3s.json")))
    previousTempText = open(general.getConfig()["tempNotesPath"]).read()
    textToAddToFile = "\n\n"
    filesToDelete = []

    musicFiles = sorted(
        glob.glob(mp3FolderPath + "/*.mp3") + glob.glob(mp3FolderPath + "/*.m4a"),
        key=sort_key,
    )
    for mp3File in musicFiles:
        fileName = mp3File.split("/")[-1]
        if fileName in processedMp3s:
            pass  # tryDeleteFile(mp3File)
        else:
            print("processing {}".format(fileName))
            textFromMp3 = processMp3File(mp3File)
            if textFromMp3.lower() not in previousTempText.lower():
                textToAddToFile += textFromMp3 + "\n\n" if textFromMp3 else ""
            filesToDelete.append(fileName)

    notes_text = textToAddToFile.replace("\n\n\n", "\n\n")
    if notes_text.strip():
        with open(general.getConfig()["tempNotesPath"], "a") as f:
            f.write(notes_text)

    for fileName in filesToDelete:
        ## for the time being lets not delete any files but instead simply mark them as processed, to minimise risk of data loss
        processedMp3s.append(fileName)

    json.dump(processedMp3s, open(general.getAbsPath("../processedMp3s.json"), "w"))


delete_duplicate_files(general.getConfig()["mp3CaptureFolder"])
saveNotesFromKeep()
saveNotesFromMp3s()
