import importlib.util
import sys

from loguru import logger
from pydub.utils import mediainfo
import fcntl
import os
import re
import glob
import datetime
import time
import utils.general as general
from openai import OpenAI
import hashlib
import subprocess
from dotenv import load_dotenv
from send2trash import send2trash
from processed_hashes import ProcessedHashes
from keep_auth import authenticate_keep

load_dotenv()

# Initialize the hash tracker
HASH_FILE = os.path.join(os.path.dirname(__file__), "audio_hashes.json")
processed_hashes = ProcessedHashes(HASH_FILE)
SEND_TO_PHONE_SCRIPT_PATH = "/home/pimania/dev/clipboardToPhone/send.py"

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "pullTempNotes.log")
LOCK_FILE = os.path.join(LOG_DIR, "pullTempNotes.lock")
logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="10 days",
    enqueue=False,
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
        if line:
            line = line[0].lower() + line[1:]  # lowercase first caps letter
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
    urls_from_keep = []
    phone_urls_from_keep = []
    notes_to_trash = []
    url_pattern = re.compile(r"https?://\S+")

    for gnote in gnotes:
        isWatchNote = gnote.title in ["Questions", "Statements", "Notes"]
        isEmpty = (gnote.text + gnote.title).strip() == ""
        if isEmpty:
            notes_to_trash.append(gnote)
        if isEmpty or isWatchNote:
            continue
        noteText, noteTitle = (
            formatIncomingText(gnote.text.strip(), False),
            gnote.title.strip(),
        )
        trimmed_note_text = noteText.rstrip()
        has_phone_send_marker = trimmed_note_text.endswith("..")
        note_text_for_url_only_check = (
            trimmed_note_text.rstrip(".").rstrip()
            if has_phone_send_marker
            else trimmed_note_text
        )
        # The ".." suffix marker often sits directly on the final URL, so trim
        # trailing sentence punctuation off regex matches before routing.
        urls = [
            raw_url.rstrip(".,!?)]")
            for raw_url in url_pattern.findall(noteText.strip())
        ]
        is_url_only_note = (
            urls and url_pattern.sub("", note_text_for_url_only_check).strip() == ""
        )
        slack_urls = [url for url in urls if "slack.com" in url]
        non_slack_urls = [url for url in urls if "slack.com" not in url]
        should_send_urls_to_phone = is_url_only_note and has_phone_send_marker
        if should_send_urls_to_phone:
            phone_urls_from_keep.extend(urls)
            notes_to_trash.append(gnote)
            continue
        if is_url_only_note:
            if non_slack_urls:
                urls_from_keep.extend(non_slack_urls)
            if slack_urls:
                textToAddToFile += "\n\n" + "\n".join(slack_urls)
            notes_to_trash.append(gnote)
            continue
        logger.debug(
            f"Text from keep note {noteTitle if noteTitle else '[untitled]'}: {noteText}"
        )
        if noteText or noteTitle:
            textToAddToFile += "\n"
        noteTitle = ""
        if "http" not in noteText:
            textToAddToFile += "\n" + noteTitle if noteTitle else ""
            textToAddToFile += ":" if noteText and noteTitle else ""
        textToAddToFile += "\n" + noteText if noteText else ""
        notes_to_trash.append(gnote)

    return textToAddToFile, urls_from_keep, phone_urls_from_keep, notes_to_trash


def load_send_to_phone_module():
    module_name = "clipboard_to_phone_send"
    module_spec = importlib.util.spec_from_file_location(
        module_name, SEND_TO_PHONE_SCRIPT_PATH
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load send.py from {SEND_TO_PHONE_SCRIPT_PATH}")

    clipboard_to_phone_dir = os.path.dirname(SEND_TO_PHONE_SCRIPT_PATH)
    added_to_sys_path = clipboard_to_phone_dir not in sys.path
    if added_to_sys_path:
        sys.path.insert(0, clipboard_to_phone_dir)
    try:
        send_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(send_module)
        return send_module
    finally:
        if added_to_sys_path:
            sys.path.pop(0)


def send_urls_to_phone(urls):
    if not urls:
        return
    logger.info(f"Sending {len(urls)} keep url(s) to phone")
    send_module = load_send_to_phone_module()
    send_module._configure_logging()
    api_url = send_module._resolve_api_url_from_env()
    if not api_url:
        raise RuntimeError("clipboardToPhone send.py could not resolve NTFY_SEND_TOPIC")
    if not send_module._send_plain_messages(api_url, urls):
        raise RuntimeError("clipboardToPhone send.py failed to deliver keep URLs")


def run_lineate_for_urls(urls):
    if not urls:
        return
    urls_text = " ".join(urls)
    command = [
        "/home/pimania/dev/misc/automation/uvrun.sh",
        "/home/pimania/dev/lineate/src/lineate.py",
        "--force-convert-all",
        "--summarise",
        urls_text,
    ]
    logger.info(f"Running lineate for {len(urls)} urls")
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    subprocess.run(command, check=True, env=env)


def append_opened_urls(urls, file_path):
    if not urls:
        return
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a+") as file:
        file.seek(0, os.SEEK_END)
        if file.tell() > 0:
            file.seek(file.tell() - 1)
            if file.read(1) != "\n":
                file.write("\n")
        for url in urls:
            file.write(f"{timestamp} {url}\n")


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


def acquire_script_lock():
    lock_handle = open(LOCK_FILE, "a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.info("Another pullTempNotes.py run is active; exiting without work")
        lock_handle.close()
        raise SystemExit(0)
    return lock_handle


def sync_keep_notes(keep, temp_file_path, opened_urls_path):
    keep_text, keep_urls, phone_urls, keep_notes_to_trash = saveNotesFromKeep(keep)
    # Keep notes are only committed after all URL side effects succeed, so a
    # failing browser-send/phone-send step leaves the source notes retryable.
    run_lineate_for_urls(keep_urls)
    append_opened_urls(keep_urls, opened_urls_path)
    send_urls_to_phone(phone_urls)
    writeToFile(temp_file_path, keep_text)

    for gnote in keep_notes_to_trash:
        gnote.trash()

    keep.sync()


def delete_processed_mp3s(processed_mp3s, mp3_folder_path):
    for mp3File, mp3Outcome in processed_mp3s.items():
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
        tryDeleteFile(os.path.join(mp3_folder_path, mp3File), fileText)


def main():
    lock_handle = acquire_script_lock()
    try:
        keep = authenticate_keep()
        tempFilePath, mp3FolderPath = (
            general.getConfig()["tempNotesPath"],
            general.getConfig()["mp3CaptureFolder"],
        )
        delete_duplicate_files(mp3FolderPath)

        textToAddToFile, processedMp3s = saveNotesFromMp3s()
        writeToFile(tempFilePath, textToAddToFile)

        sync_keep_notes(keep, tempFilePath, "/home/pimania/notes/opened_urls.md")
        delete_processed_mp3s(processedMp3s, mp3FolderPath)
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
