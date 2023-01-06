from utils.utils import *


def getAllToDoPaths(totalText):
    totalText = totalText.replace("**", "")
    path = {}
    donePaths = []
    unDonePaths = []
    totalTextLines = totalText.split("\n")
    for i, line in enumerate(totalTextLines):
        if not "".join(line.split()):
            continue
        currentIndent = line.count("\t")
        path[currentIndent] = line.strip("\t")
        currentPath = [path[indent] for indent in range(currentIndent + 1)]
        if "[x]" in line:
            noUndoneSubTasks = checkForUnDoneSubtasks(i, currentIndent, totalTextLines)
            if noUndoneSubTasks:
                donePaths.append(currentPath)
            else:
                unDonePaths.append(currentPath)
        else:
            unDonePaths.append(currentPath)

    unDonePaths = dedup(unDonePaths)

    return unDonePaths, donePaths


def groupRelatedPaths(paths):
    consolidatedPaths = []
    pathCounters = {}
    indexedPaths = {}

    for path in paths:

        constructedPath = [""]
        pathSortIndex = []
        for element in path:
            constructPathText = " / ".join(constructedPath)
            element = normalisePathElement(element)
            if not constructPathText in pathCounters:
                pathCounters[constructPathText] = {}
            existingPathChildren = pathCounters[constructPathText]
            if element in existingPathChildren:
                pathChildIndexOfElement = str(existingPathChildren[element])
            else:
                pathChildIndexOfElement = str(len(existingPathChildren))
                pathCounters[constructPathText][element] = pathChildIndexOfElement
            pathSortIndex.append(int(pathChildIndexOfElement))

            constructedPath.append(element)

        indexedPaths[tuple(pathSortIndex)] = path

    consolidatedPaths = [indexedPaths[index] for index in sorted(indexedPaths)]
    return consolidatedPaths


def convertRowToHeading(row, lastIndent):
    if "[" in row[:10] and "]" in row[:10]:
        prefixSize = len("- [ ] ")
    else:
        prefixSize = len("- ")

    rowText = row.strip()
    listPrefix = rowText[:prefixSize]
    itemText = rowText[prefixSize:]
    outputRow = "\t" * lastIndent + listPrefix + "**" + itemText + "**\n"
    return outputRow


def constructFileFromPaths(paths):
    expectedPath = []
    outputText = []
    currentIndent = 0

    paths = groupRelatedPaths(paths)
    for path in paths:
        for i, element in enumerate(path):
            if not element in expectedPath:
                newPathElements = path[i:]
                lastIndent = int(currentIndent)
                currentIndent = i
                expectedPath = path
                break
        currentIndent -= 1
        for element in newPathElements:
            currentIndent += 1
            if lastIndent < currentIndent:
                outputText[-1] = convertRowToHeading(outputText[-1], lastIndent)
            outputText.append("\t" * currentIndent + element + "\n")
            lastIndent = int(currentIndent)

    return "".join(outputText)


def getAllToDos():
    mainToDoFile, doneToDoFile = (
        getConfig()["mainToDoFile"],
        getConfig()["doneToDoFile"],
    )
    mainToDoText = open(mainToDoFile).read()
    doneToDoText = open(doneToDoFile).read()
    return mainToDoText, doneToDoText


def writeOutputToDos(doneOutput, unDoneOutput):
    mainToDoFile, doneToDoFile = (
        getConfig()["mainToDoFile"],
        getConfig()["doneToDoFile"],
    )
    with open(mainToDoFile, "w") as unDoneFile:
        unDoneFile.write(unDoneOutput)
    with open(doneToDoFile, "w") as doneFile:
        doneFile.write(doneOutput)
