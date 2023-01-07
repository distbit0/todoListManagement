import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from utils.utils import *
from utils.toDo import *


def getChildPaths(paths, curPos, currentIndent):
    childPaths = []
    j = int(curPos) + 1
    while True:
        if len(paths) <= j:
            break
        path = paths[j]
        indent = len(path)
        if indent > currentIndent:
            childPaths.append(path)
        else:
            break
        j += 1
    return childPaths


def trimBeginningOfPaths(paths, elementsToTrim):
    trimmedPaths = [path[elementsToTrim:] for path in paths]
    return trimmedPaths


def removePriorityFromPaths(paths, priority):
    editedPaths = []
    for path in paths:
        newPath = []
        for element in path:
            newPath.append(element.rstrip("1234567890 "))
        editedPaths.append(newPath)
    return editedPaths


def getPriorityOfPath(path):
    priority = False
    lastWordInLastPathElement = path[-1].split()[-1]
    if lastWordInLastPathElement.isnumeric():
        priority = lastWordInLastPathElement
    return priority


def getPrioritisedToDos(paths):
    prioritisedPaths = {}
    paths = groupRelatedPaths(paths)
    for i, path in enumerate(paths):
        priority = getPriorityOfPath(path)
        if priority:
            currentIndent = len(path)
            elementsToTrim = currentIndent - 1
            childPaths = getChildPaths(paths, i, currentIndent)
            childPaths.insert(0, path)
            if priority not in prioritisedPaths:
                prioritisedPaths[priority] = []

            childPaths = trimBeginningOfPaths(childPaths, elementsToTrim)
            childPaths = removePriorityFromPaths(childPaths, priority)
            prioritisedPaths[priority].extend(childPaths)
    return prioritisedPaths


def savePrioritisedToDos(prioritisedPaths):
    priorityTexts = {}
    finalText = ""
    prioritisedTodoFilePath = getConfig()["prioritisedTodoFilePath"]
    for priority in sorted(prioritisedPaths, reverse=True, key=lambda x: int(x)):
        paths = prioritisedPaths[priority]
        priorityTexts[priority] = constructFileFromPaths(paths)

    for priority in priorityTexts:
        finalText += (
            "**Priority: " + priority + "**\n" + priorityTexts[priority] + "\n\n\n\n"
        )

    finalText = finalText.replace(" [ ]", "")
    writeToFile(prioritisedTodoFilePath, finalText)


def calcAndSavePrioritisedToDos(paths):
    prioritisedToDos = getPrioritisedToDos(paths)
    savePrioritisedToDos(prioritisedToDos)
