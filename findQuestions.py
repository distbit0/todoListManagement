import re
import random
import gkeepapi
import utils.general as general


def find_random_matches(file_list, pattern, num_matches):
    matches = []

    for file in file_list:
        try:
            with open(file, "r") as f:
                text = f.read()
        except:
            continue
        else:
            paragraphs = re.split(r"\n{2,}", text.strip())
            for i in range(1, len(paragraphs)):
                if "])" in paragraphs[i] or "http" in paragraphs[i]:
                    continue
                current_paragraph = paragraphs[i]
                previous_paragraph = paragraphs[i - 1]
                match = re.search(pattern, current_paragraph)
                if match:
                    matches.append(previous_paragraph + "  " + match.group())

    # Select random matches
    random_matches = random.sample(matches, min(num_matches, len(matches)))

    return random_matches


# List of files to search through
file_list = general.getConfig()["questionFiles"]

# Number of random matches to choose
num_matches = 5

# Call the function to find random matches from the files
questions = find_random_matches(file_list, r".+?\?", 10)
statements = find_random_matches(file_list, r".*", 10)

# Print the selected random matches
questionString = ""
for match in questions:
    questionString += match.strip() + "\n\n"


statementString = ""
for match in statements:
    statementString += match.strip() + "\n\n"


keep = gkeepapi.Keep()
keep.resume(
    general.getConfig()["username"],
    general.getConfig()["masterKey"],
)

gnotes = list(keep.find(archived=False, trashed=False))

questionsNote = next((note for note in gnotes if note.title == "Questions"), None)
statementsNote = next((note for note in gnotes if note.title == "Statements"), None)

if questionsNote:
    questionsNote.text = questionString
    keep.sync()

if statementsNote:
    statementsNote.text = statementString
    keep.sync()
