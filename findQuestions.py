import re
import random
import gkeepapi
import glob
import utils.general as general
from dotenv import load_dotenv
import os
import frontmatter
import toml

load_dotenv()
markAsReadString = "[[read]]"


def checkParagraphSatisfiesConstraints(paragraph, matchingWords):
    validParagraph = not (
        "])" in paragraph or "http" in paragraph or paragraph.endswith(markAsReadString)
    )
    containsMatchingWords = (
        any(word.lower() + " " in paragraph.lower() for word in matchingWords)
        or not matchingWords
    )
    paragraphSansLinks = re.sub(r"\[\[[^\]]*\]\]|#\w+", "", paragraph).strip()
    paragraphSansLinks = paragraphSansLinks.replace("  ", " ").replace("  ", " ")
    hasSufficientWords = len(paragraphSansLinks.split()) >= 7

    return validParagraph and containsMatchingWords and hasSufficientWords


def find_random_matches(file_list, matchingWords, num_matches):
    matches = []
    for file in file_list:
        try:
            with open(file, "r") as f:
                text = f.read()
        except:
            continue
        else:
            paragraphs = re.split(
                r"\n{2,}", text.strip()
            )  # split on two or more newlines
            for i in range(1, len(paragraphs)):
                currentParagraph = paragraphs[i].strip()
                if checkParagraphSatisfiesConstraints(currentParagraph, matchingWords):
                    matches.append(currentParagraph)
    print("number of total matches: " + str(len(matches)))
    # Randomize order of the matches list
    random.shuffle(matches)
    random_matches = random.sample(matches, min(num_matches, len(matches)))
    return random_matches


def getTextOfLineContainingSubtring(file, substring):
    with open(file, "r") as f:
        text = f.read()
    indexOfSubstring = text.find(substring)
    indexOfEndOfLine = text.find("\n\n", indexOfSubstring)
    if indexOfSubstring == -1 or indexOfEndOfLine == -1:
        return None
    else:
        return text[indexOfSubstring:indexOfEndOfLine]


def mark_as_read(file_list, sentences):
    for file in file_list:
        try:
            with open(file, "r") as f:
                modified_text = f.read()
            for sentence in sentences:
                if markAsReadString in sentence:
                    continue
                textOfLineContainingSubstring = getTextOfLineContainingSubtring(
                    file, sentence
                )
                if textOfLineContainingSubstring:
                    if markAsReadString in textOfLineContainingSubstring:
                        continue
                modified_text = modified_text.replace(
                    sentence, sentence + " " + markAsReadString
                )
            currentText = open(file).read()
            if currentText == modified_text:
                continue
            with open(file, "w") as f:
                f.write(modified_text)
        except:
            continue


def getFileList():
    # List of files to search through
    filterList = general.getConfig()["questionFiles"]
    file_list = []
    for fileFilter in filterList:
        for path in glob.glob(
            general.getConfig()["toDoFolderPath"] + fileFilter,
            recursive=True,
        ):
            file_list.append(path)
    return file_list


def get_gist_url(path):
    with open(path, "r") as f:
        content = f.read()
    try:
        post = frontmatter.loads(content)
    except toml.decoder.TomlDecodeError:
        parts = content.split("+++++")
        if len(parts) >= 3:
            post = frontmatter.loads(parts[2])
        else:
            return None
    return post.metadata.get("gist_url")


def find_wikilinked_notes(file_list, num_matches):
    notes = []
    seen = set()
    for file in file_list:
        try:
            text = open(file, "r").read()
        except:
            continue
        print(f"Processing {file}")
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            if link in seen:
                continue
            # locate the note file matching this wikilink via os.walk
            wikilink_without_ext = link.replace(".md", "")
            target = None
            base_dir = general.getConfig()["toDoFolderPath"]
            for root, _, files in os.walk(base_dir):
                for file_name in files:
                    if file_name.lower().endswith(".md") and file_name[:-3].lower() == wikilink_without_ext.lower():
                        target = os.path.join(root, file_name)
                        break
                if target:
                    break
            if not target:
                continue
            url = get_gist_url(target)
            if url:
                notes.append(f"{link}: {url}")
                seen.add(link)
    notes = list(set(notes))
    random.shuffle(notes)
    print(f"Notes: {len(notes)}")
    return notes[:num_matches]


def main():
    # Number of random matches to choose
    num_matches = 15
    # Call the function to find random matches from the files
    file_list = getFileList()
    paragraphs = {
        # "Questions": find_random_matches(
        #     file_list, general.getConfig()["questionWords"], num_matches
        # ),
        "Statements": find_random_matches(file_list, [], num_matches),
        "Notes": find_wikilinked_notes(file_list, num_matches),
    }

    keep = gkeepapi.Keep()
    keep.authenticate(
        os.environ["username"],
        os.environ["masterKey"],
    )
    gnotes = list(keep.find(archived=False, trashed=False))
    for noteName in ["Statements", "Notes"]: # deleted questions
        note = next((note for note in gnotes if note.title == noteName), None)
        if not note:
            note = keep.createList(noteName, [])
        checked_sentences = []
        if note.items:
            for item in note.items:
                if item.checked:
                    checked_sentences.append(item.text)
                item.delete()
            mark_as_read(file_list, list(set(checked_sentences)))

        for paragraph in paragraphs[noteName]:
            note.add(paragraph, False)

    keep.sync()


if __name__ == "__main__":
    main()
