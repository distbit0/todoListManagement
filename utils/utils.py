import json
from os import path
import glob
import re


def getAbsPath(relPath):
    basepath = path.dirname(__file__)
    return path.abspath(path.join(basepath, relPath))


def getConfig():
    configFileName = getAbsPath("../config.json")
    return json.loads(readFromFile(configFileName))


def readJson(text):
    return json.loads(text.strip().strip("`"))


def dumpJson(object):
    return json.dumps(object, indent=4)


def normalisePathElement(row):
    return row.lower().strip().replace("[x]", "[ ]")


def normalisePath(path):
    return normalisePathElement(" / ".join(path))


def normalisePaths(paths):
    return [normalisePath(path) for path in paths]


def checkForUnDoneSubtasks(curPos, currentIndent, totalTextLines):
    noUndoneSubTasks = True
    j = int(curPos) + 1

    while True:
        if len(totalTextLines) <= j:
            break
        tmpLine = totalTextLines[j]
        indent = tmpLine.count("\t")
        if indent > currentIndent:
            if "[ ]" in tmpLine:
                noUndoneSubTasks = False
        else:
            break
        j += 1
    return noUndoneSubTasks


def dedup(l):
    result = []
    for i in l:
        if i not in result:
            result.append(i)
    return result


def getAllToDosAndDoneText():
    returnList = []
    toDoFolderPath, doneToDoFile = (
        getConfig()["toDoFolderPath"],
        getConfig()["doneFilePath"],
    )
    toDoFiles = {}

    for filePath in glob.glob(toDoFolderPath + "**/1Todo*.md", recursive=True):
        isConflictFile = False
        filePathForSubject = str(filePath)
        if ".sync-conflict-" in filePath:
            filePathForSubject = filePath.split(".sync-conflict-")[0] + ".md"
            isConflictFile = True
        subject = (
            filePathForSubject.split("/")[-1]
            .replace("1Todo", "")
            .replace(".md", "")
            .strip()
        )
        toDoId = path.dirname(filePath) + "sbj:" + subject

        if not subject:
            continue
        text = readFromFile(filePath).replace("**", "")
        print(subject, filePath)
        fileObj = {"text": text, "path": filePath, "subject": subject}
        if isConflictFile:
            toDoFiles.setdefault(toDoId, {})["conflict"] = fileObj
        else:
            toDoFiles.setdefault(toDoId, {})["master"] = fileObj

    # doneToDoText = readFromFile(doneToDoFile).replace("**", "")

    return toDoFiles  # , doneToDoText


def prefixAllPaths(paths, prefix):
    prefixedPaths = []
    for path in paths:
        prefixedPaths.append(["- [ ] " + prefix] + path)

    return prefixedPaths


def unPrefixAllPaths(paths):
    unPrefixedPaths = []
    for path in paths:
        unPrefixedPaths.append(path[1:])

    return unPrefixedPaths


def stringSplit(strng, sep, pos):
    strng = strng.split(sep)
    return sep.join(strng[:pos]), sep.join(strng[pos:])


def writeToFile(fileName, fileText):
    with open(fileName, "r") as f:
        file_contents = f.read()

    # Check if file contains markdown front matter
    if file_contents.startswith("---"):
        # Split file contents by markdown front matter delimiter
        front_matter, file_contents = stringSplit(file_contents, "---", 2)
        front_matter += "---\n"
    else:
        front_matter = ""

    # Extract code blocks
    code_blocks = re.findall(r"```.*?```", file_contents, re.DOTALL)

    # Write text to file while preserving front matter and code blocks
    with open(fileName, "w") as f:
        f.write(front_matter)
        for block in code_blocks:
            f.write("\n" + block)
        f.write("\n\n" + fileText)


def readFromFile(fileName):
    with open(fileName, "r") as f:
        file_contents = f.read()

    # Check if file contains markdown front matter
    if file_contents.startswith("---"):
        # Split file contents by markdown front matter delimiter
        front_matter, file_contents = stringSplit(file_contents, "---", 2)
    else:
        front_matter = ""

    # Extract code blocks
    code_blocks = re.findall(r"```.*?```", file_contents, re.DOTALL)

    # Remove code blocks from file contents for return value
    for block in code_blocks:
        file_contents = file_contents.replace(block, "")

    return file_contents.strip()
