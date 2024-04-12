import gkeepapi
import time
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


def saveNotesFromKeep(keep):
    gnotes = list(keep.find(archived=False, trashed=False))
    gnotes = sorted(gnotes, key=lambda x: x.timestamps.edited.timestamp())
    textToAddToFile = ""

    for gnote in gnotes:
        isWatchNote = gnote.title in ["Questions", "Statements"]
        isEmpty = (gnote.text + gnote.title).strip() == ""
        if isEmpty or isWatchNote:
            continue
        print("text from keep: {}".format(gnote.title + "\n" + gnote.text))
        if "http" not in gnote.text:
            textToAddToFile += "\n" + gnote.title if gnote.title else ""
            textToAddToFile += ":" if gnote.text and gnote.title else ""
        textToAddToFile += "\n" + gnote.text if gnote.text else ""
        gnote.archived = True

    return textToAddToFile


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
    textToAddToFile = ""

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
            if textFromMp3:
                textToAddToFile += "\n" + textFromMp3
                print("text from mp3: {}".format(textFromMp3))
            processedMp3s.append(fileName)

    return textToAddToFile, processedMp3s


def remove_duplicate_beginnings(text):
    lines = text.split("\n")
    stripped_lines = [line.strip().lower() for line in lines]
    result_lines = []

    for i, line in enumerate(lines):
        is_duplicate = False
        for j, other_line in enumerate(stripped_lines):
            if i != j and other_line.startswith(line.strip().lower()):
                is_duplicate = True
                break

        if not is_duplicate or line.strip() == "" or line.strip() == "---":
            result_lines.append(line)

    return "\n".join(result_lines)


def writeToFile(filePath, textToAddToFile):
    if not textToAddToFile.strip():
        return
    with open(filePath, "r") as f:
        text = f.read()
    existingText = text.strip()
    if existingText.split("\n")[-1][0] == "#":
        existingText += "\n"
    existingText += textToAddToFile
    existingText = remove_duplicate_beginnings(existingText)
    if existingText[-1] != "\n":
        existingText += "\n"
    if existingText.strip().split("\n")[-1][0] == "#":
        existingText += "\n"
    with open(filePath, "w") as f:
        f.write(existingText)


keep = gkeepapi.Keep()
keep.resume(
    os.environ["username"],
    os.environ["masterKey"],
)

tempFilePath, mp3FolderPath = (
    general.getConfig()["tempNotesPath"],
    general.getConfig()["mp3CaptureFolder"],
)
delete_duplicate_files(mp3FolderPath)

textToAddToFile, processedMp3s = saveNotesFromMp3s()
textToAddToFile += saveNotesFromKeep(keep)
writeToFile(tempFilePath, textToAddToFile)

## only now do we delete/archive synced notes and mp3s
keep.sync()
json.dump(processedMp3s, open(general.getAbsPath("../processedMp3s.json"), "w"))
