import gkeepapi
from loguru import logger
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

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "pullTempNotes.log")
logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="10 days",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


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
                logger.info(f"Moved to trash due to duplicate hash: {file_path}")
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
        logger.debug(
            f"Text from keep note {noteTitle if noteTitle else '[untitled]'}: {noteText}"
        )
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
    newFileName = (
        "".join([char for char in fileText if char.isalnum() or char == " "][:120])
        + "."
        + fileExt
    )
    newFilePath = path.replace(oldFileName, newFileName)
    os.rename(path, newFilePath)
    try:
        send2trash(newFilePath)
        logger.info(f"Moved {newFilePath} to trash after successful transcription")
    except Exception as error:
        logger.exception(f"Failed moving {newFilePath} to trash: {error}")


def processMp3File(mp3FileName):
    # Get the duration of the audio file
    info = mediainfo(mp3FileName)

    if "duration" not in info:
        logger.error(f"Could not determine duration for {mp3FileName}")
        return "DURATION UNKNOWN", False

    duration = float(info["duration"])
    temp_file = None
    if duration > 1100:
        logger.info(f"Cropping {mp3FileName} to 1100 seconds")
        from pydub import AudioSegment

        audio = AudioSegment.from_file(mp3FileName)
        audio = audio[: 1100 * 1000]  # pydub works in milliseconds
        temp_file = mp3FileName + ".temp.mp3"
        audio.export(temp_file, format="mp3")
        mp3FileName = temp_file

    try:
        apiKey = os.environ["OPENAI_API_KEY"]
        client = OpenAI(api_key=apiKey)
        with open(mp3FileName, "rb") as audio_file:
            api_response = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                response_format="text",
            )
        transcribed_text = api_response
        success = True
        logger.info(f"Transcription completed for {mp3FileName}")
    except Exception as error:
        transcribed_text = f"transcription api error {time.time()}"
        success = False
        logger.exception(f"Transcription failed for {mp3FileName}: {error}")

    if temp_file:
        try:
            os.remove(temp_file)
            logger.debug(f"Removed temporary audio file {temp_file}")
        except Exception as error:
            logger.exception(f"Error removing temporary file {temp_file}: {error}")

    return transcribed_text, success


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
            logger.info(f"Skipping already processed file: {fileName}")
            processedMp3s[fileName] = {
                "raw_text": "ALREADY PROCESSED",
                "formatted_text": "ALREADY PROCESSED",
                "transcription_successful": True,
            }
            continue

        logger.info(f"Processing {fileName}")
        raw_text, transcription_successful = processMp3File(mp3File)
        formatted_text = formatIncomingText(raw_text, True) if raw_text else ""

        if transcription_successful:
            if formatted_text:
                textToAddToFile += "\n\n" + formatted_text
                logger.debug(f"Transcription output for {fileName}: {formatted_text}")

            # Record the processed file hash
            processed_hashes.add_hash(
                file_hash,
                {
                    "filename": fileName,
                    "processed_date": str(datetime.datetime.now()),
                },
            )
        else:
            logger.info(
                f"Transcription failed for {fileName}; leaving file in source folder for retry"
            )

        processedMp3s[fileName] = {
            "raw_text": raw_text,
            "formatted_text": formatted_text,
            "transcription_successful": transcription_successful,
        }

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
for mp3File, mp3Outcome in processedMp3s.items():
    if not mp3Outcome["transcription_successful"]:
        logger.info(
            f"Skipping deletion for {mp3File} because transcription failed; leaving for retry"
        )
        continue

    fileText = (
        mp3Outcome["formatted_text"]
        or mp3Outcome["raw_text"]
        or os.path.splitext(mp3File)[0]
    )
    logger.info(f"Deleting {mp3File}")
    tryDeleteFile(os.path.join(mp3FolderPath, mp3File), fileText)
