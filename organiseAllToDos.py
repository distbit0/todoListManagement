import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

import utils.utils as utils
from utils.routines import *
from utils.toDo import *
from utils.dailyDone import *
from utils.prioritisedToDo import *


def organiseAndReturnTodos(toDoFile):
    toDoFileText, toDoFileSubject, toDoFilePath = (
        toDoFile["text"],
        toDoFile["subject"],
        toDoFile["path"],
    )

    fileUndonePaths, fileDonePaths = getAllToDoPaths(toDoFileText)
    unDoneOutput = constructFileFromPaths(fileUndonePaths)
    writeToFile(toDoFilePath, unDoneOutput)
    prefixedUndonePaths = prefixAllPaths(fileUndonePaths, toDoFileSubject)
    prefixedDonePaths = prefixAllPaths(fileDonePaths, toDoFileSubject)

    return prefixedUndonePaths, prefixedDonePaths


if __name__ == "__main__":
    newDonePaths = []
    unDonePaths = []
    allDonePaths = []
    toDoFiles, oldDoneText = utils.getAllToDosAndDoneText()[:2]
    alreadyDonePaths = getAllToDoPaths(oldDoneText)[1]
    allDonePaths.extend(alreadyDonePaths)

    for toDoId in toDoFiles:
        toDoFileContents = toDoFiles[toDoId]
        if "master" not in toDoFileContents:
            continue

        fileUnDonePaths, fileDonePaths = organiseAndReturnTodos(
            toDoFileContents["master"]
        )
        # store done paths
        newDonePaths.extend(fileDonePaths)
        allDonePaths.extend(fileDonePaths)
        # store unDone paths
        unDonePaths.extend(fileUnDonePaths)

    # generate and save various global done and undone files

    doneOutput = constructFileFromPaths(allDonePaths)

    writeToFile(getConfig()["doneFilePath"], doneOutput)
    calcAndSavePrioritisedToDos(unDonePaths)

    # add new done paths to daily one files
    addToDailyDoneFile(newDonePaths)
    addToReadableDailyDoneFile(newDonePaths)
