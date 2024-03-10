import re
import random
import gkeepapi
import utils.general as general


def find_random_matches(file_list, matchingWords, num_matches):
    matches = []
    excludedQuestions = general.readJson(
        open(general.getAbsPath("./../excludedQuestions.json")).read()
    )

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
                if not matchingWords or any(
                    word.lower() + " " in current_paragraph.lower()
                    for word in matchingWords
                ):
                    question = "1) " + previous_paragraph + "\n2) " + current_paragraph
                    if question not in excludedQuestions:
                        matches.append(question)

    # Select random matches
    print("number of total matches: " + str(len(matches)))

    # Randomize order of the matches list
    random.shuffle(matches)
    random_matches = random.sample(matches, min(num_matches, len(matches)))
    return random_matches


# List of files to search through
file_list = general.getConfig()["questionFiles"]

# Number of random matches to choose
num_matches = 15

# Call the function to find random matches from the files
questions = find_random_matches(
    file_list,
    ["when", "why", "how", "does", "what", "is", "where", "which", "could", "couldn't"],
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

# Get checked questions and add them to excludedQuestions.json
excludedQuestions = general.readJson(
    open(general.getAbsPath("./../excludedQuestions.json")).read()
)
for item in questionsNote.items:
    if item.checked:
        excludedQuestions.append(item.text)

for item in statementsNote.items:
    if item.checked:
        excludedQuestions.append(item.text)

jsonText = general.dumpJson(excludedQuestions)
with open(general.getAbsPath("./../excludedQuestions.json"), "w") as f:
    f.write(jsonText)

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
