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
                current_paragraph = paragraphs[i]
                previous_paragraph = paragraphs[i - 1]
                match = re.search(pattern, current_paragraph)
                if match:
                    matches.append(previous_paragraph + match.group())

    # Select random matches
    random_matches = random.sample(matches, min(num_matches, len(matches)))

    return random_matches


# List of files to search through
file_list = general.getConfig()["questionFiles"]

# Regular expression pattern
pattern = r".+?\?"

# Number of random matches to choose
num_matches = 5

# Call the function to find random matches from the files
random_matches = find_random_matches(file_list, pattern, num_matches)

# Print the selected random matches
outputString = ""
for match in random_matches:
    outputString += match.strip() + "\n\n"


keep = gkeepapi.Keep()
keep.resume(
    general.getConfig()["username"],
    general.getConfig()["masterKey"],
)

gnotes = list(keep.find(archived=False, trashed=False))

questionsNote = next((note for note in gnotes if note.title == "Questions"), None)

if questionsNote:
    questionsNote.text = outputString
    keep.sync()
