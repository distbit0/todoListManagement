import re
import random
import gkeepapi
import glob
import utils.general as general

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
    hasSufficientWords = len(paragraphSansLinks.split()) >= 6

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
            )  ##split on two or more newlines
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
            with open(file, "w") as f:
                f.write(modified_text)
        except:
            continue


def getFileList():
    # List of files to search through
    file_list = general.getConfig()["questionFiles"]
    fileFilters = ["*tmp.md", "*[?].md"]
    for fileFilter in fileFilters:
        file_list += [
            path
            for path in glob.glob(
                general.getConfig()["toDoFolderPath"] + "**/" + fileFilter,
                recursive=True,
            )
        ]
    return file_list


def main():
    # Number of random matches to choose
    num_matches = 15
    # Call the function to find random matches from the files
    file_list = getFileList()
    questions = find_random_matches(
        file_list,
        general.getConfig()["questionWords"],
        num_matches,
    )
    statements = find_random_matches(file_list, [], num_matches)

    keep = gkeepapi.Keep()
    keep.resume(
        general.getConfig()["username"],
        general.getConfig()["masterKey"],
    )
    gnotes = list(keep.find(archived=False, trashed=False))
    questionsNote = next((note for note in gnotes if note.title == "Questions"), None)
    statementsNote = next((note for note in gnotes if note.title == "Statements"), None)

    # Create notes if they don't exist
    if not questionsNote:
        questionsNote = keep.createList("Questions", [])
    if not statementsNote:
        statementsNote = keep.createList("Statements", [])

    # Get checked questions and mark them as read in the source files
    checked_sentences = []
    for item in questionsNote.items:
        if item.checked:
            checked_sentences.append(item.text)
    for item in statementsNote.items:
        if item.checked:
            checked_sentences.append(item.text)
    mark_as_read(file_list, checked_sentences)

    for item in questionsNote.items:
        item.delete()
    for item in statementsNote.items:
        item.delete()

    # Add new items to the list
    for question in questions:
        questionsNote.add(question, False)
    for statement in statements:
        statementsNote.add(statement, False)

    keep.sync()


if __name__ == "__main__":
    main()
