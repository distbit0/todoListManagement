import gkeepapi
import sys
from pydub.utils import mediainfo
import os
import re
import glob
import datetime
import time
import utils.general as general
from openai import OpenAI
import hashlib
from dotenv import load_dotenv
from send2trash import send2trash
from processed_hashes import ProcessedHashes

load_dotenv()

# Initialize the hash tracker
HASH_FILE = os.path.join(os.path.dirname(__file__), "audio_hashes.json")
processed_hashes = ProcessedHashes(HASH_FILE)


#### this should be moved to a separate repo that also contains findQuestions.py
# also move prioritiseHabits to separate repo


def formatIncomingText(text, isTranscription):
    pattern = re.compile(r"(^\d+\.\s*)http")
    modified_lines = []

    for line in text.split("\n"):
        line = pattern.sub("http", line)
        line = " ".join(
            word.lower() if isTranscription else word for word in line.split()
        )  # only convert transcribed text to lowercase. otherwise could clobber case sensitive text such as urls from gkeep
        line = line.strip(".!?") if isTranscription else line
        modified_lines.append(line)

    modified_text = "\n".join(modified_lines)
    return modified_text


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
                print(f"Moved to trash due to duplicate hash: {file_path}")
            else:
                # Record the hash of this unique file
                hashes[file_hash] = file_path


def saveNotesFromKeep(keep):
    gnotes = list(keep.find(archived=False, trashed=False))
    gnotes = sorted(gnotes, key=lambda x: x.timestamps.edited.timestamp())
    textToAddToFile = ""

    for gnote in gnotes:
        isWatchNote = gnote.title in ["Questions", "Statements", "Notes"]
        isEmpty = (gnote.text + gnote.title).strip() == ""
        if isEmpty:
            gnote.trash()
        if isEmpty or isWatchNote:
            continue
        noteText, noteTitle = (
            formatIncomingText(gnote.text.strip(), False),
            gnote.title.strip(),
        )
        print("text from keep: {}".format(noteTitle + "\n" + noteText))
        if noteText or noteTitle:
            textToAddToFile += "\n"
        if "http" not in noteText:
            textToAddToFile += "\n" + noteTitle if noteTitle else ""
            textToAddToFile += ":" if noteText and noteTitle else ""
        textToAddToFile += "\n" + noteText if noteText else ""
        gnote.trash()

    return textToAddToFile


def tryDeleteFile(path, fileText):
    fileExt = path.split(".")[-1]
    oldFileName = path.split("/")[-1]
    if "transcription api error" in fileText:
        return
    newFileName = (
        "".join([char for char in fileText if char.isalnum() or char == " "][:120])
        + "."
        + fileExt
    )
    newFilePath = path.replace(oldFileName, newFileName)
    os.rename(path, newFilePath)
    try:
        send2trash(newFilePath)
    except Exception as e:
        print(f"Error moving {newFilePath} to trash: {e}")
        pass


def processMp3File(mp3FileName):
    # Get the duration of the audio file
    info = mediainfo(mp3FileName)

    if "duration" not in info:
        print(f"Could not determine duration for {mp3FileName}")
        return "DURATION UNKNOWN"

    duration = float(info["duration"])
    temp_file = None
    if duration > 1100:
        print(f"Cropping {mp3FileName} to 1100 seconds")
        from pydub import AudioSegment

        audio = AudioSegment.from_file(mp3FileName)
        audio = audio[: 1100 * 1000]  # pydub works in milliseconds
        temp_file = mp3FileName + ".temp.mp3"
        audio.export(temp_file, format="mp3")
        mp3FileName = temp_file

    try:
        apiKey = os.environ["OPENAI_API_KEY"]
        client = OpenAI(api_key=apiKey)
        api_response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=open(mp3FileName, "rb"),
            response_format="text",
        )
        transcribed_text = api_response
    except Exception as e:
        print(sys.exc_info())
        transcribed_text = "transcription api error" + str(time.time())
        print(f"Error transcribing {mp3FileName}")

    if temp_file:
        try:
            os.remove(temp_file)
        except Exception as e:
            print(f"Error removing temporary file {temp_file}: {e}")

    return transcribed_text


def sort_key(filename):
    match = re.search(r"(\d+)", os.path.basename(filename))
    if match:
        return int(match.group(1))
    return 0


def saveNotesFromMp3s():
    mp3FolderPath = general.getConfig()["mp3CaptureFolder"]
    textToAddToFile = ""
    processedMp3s = {}

    musicFiles = sorted(
        glob.glob(mp3FolderPath + "/*.mp3") + glob.glob(mp3FolderPath + "/*.m4a"),
        key=sort_key,
    )
    for mp3File in musicFiles:
        fileName = mp3File.split("/")[-1]
        file_hash = calculate_file_hash(mp3File)

        # Check if we've already processed this file hash
        if processed_hashes.is_hash_processed(file_hash):
            print(f"Skipping already processed file: {fileName}")
            processedMp3s[fileName] = "ALREADY PROCESSED"
            continue

        print("processing {}".format(fileName))
        textFromMp3 = processMp3File(mp3File)
        textFromMp3 = formatIncomingText(textFromMp3, True)
        if textFromMp3:
            textToAddToFile += "\n\n" + textFromMp3
            print("text from mp3: {}".format(textFromMp3))

            # Record the processed file hash
            processed_hashes.add_hash(
                file_hash,
                {
                    "filename": fileName,
                    "processed_date": str(datetime.datetime.now()),
                },
            )

        processedMp3s[fileName] = textFromMp3

    return textToAddToFile, processedMp3s


def remove_duplicate_beginnings(text):
    lines = text.split("\n")
    stripped_lines = [line.strip() for line in lines]
    result_lines = []
    allowedDuplicates = ["---", ""]

    for i, line in enumerate(lines):
        is_duplicate = False
        for j, other_line in enumerate(stripped_lines):
            differentIndex = i != j
            sharedPrefix = other_line.startswith(line.strip())
            # only check earlier lines for exact matches, to avoid deleting all instances of a string present on multiple lines:
            exactMatchOnLaterLine = other_line.lower() == line.lower() and j > i
            if differentIndex and sharedPrefix and not exactMatchOnLaterLine:
                is_duplicate = True
                break

        if not is_duplicate or line.strip() in allowedDuplicates:
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
    existingText = existingText.replace("\n\n\n", "\n\n")
    with open(filePath, "w") as f:
        f.write(existingText)


keep = gkeepapi.Keep()
keep.authenticate(
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

# only now do we delete/archive synced notes and mp3s
keep.sync()
for mp3File in processedMp3s:
    fileText = processedMp3s[mp3File]
    print(f"Deleting {mp3File}")
    tryDeleteFile(os.path.join(mp3FolderPath, mp3File), fileText)
