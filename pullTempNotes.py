import gkeepapi
import os
import re
import glob
import json
import utils.general as general
from openai import OpenAI


def saveNotesFromKeep():
    keep = gkeepapi.Keep()
    keep.resume(
        general.getConfig()["username"],
        general.getConfig()["masterKey"],
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
    apiKey = general.getConfig()["openaiApiKey"]
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


saveNotesFromKeep()
saveNotesFromMp3s()
