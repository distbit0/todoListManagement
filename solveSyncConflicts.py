import sys
from os import path
import os
import glob
import time

sys.path.insert(0, path.dirname(__file__))

import utils.utils as utils
import utils.toDo as toDo

getConfig = utils.getConfig


def getAllToDos(conflictFilePath):
    mainToDoFile, doneToDoFile = (
        getConfig()["mainToDoFile"],
        getConfig()["doneToDoFile"],
    )
    mainToDoText = open(mainToDoFile).read().replace("**", "")
    doneToDoText = open(doneToDoFile).read().replace("**", "")
    conflictToDoText = open(conflictFilePath).read().replace("**", "")
    return mainToDoText, doneToDoText, conflictToDoText


def checkForConflicts():
    toDoConflictFileFilter = getConfig()["toDoConflictFileFilter"]
    isConflict = False
    conflictFilePath = ""

    conflictFilePaths = glob.glob(toDoConflictFileFilter)
    if conflictFilePaths:
        isConflict = True
        conflictFilePath = conflictFilePaths[0]
    return isConflict, conflictFilePath


def reconcilePaths(mainToDoPaths, conflictToDoPaths, doneToDoPaths):
    reconciledPaths = []

    normalisedMainToDoPaths = utils.normalisePaths(mainToDoPaths)
    normalisedConflictToDoPaths = utils.normalisePaths(conflictToDoPaths)
    normalisedDoneToDoPaths = utils.normalisePaths(doneToDoPaths)

    for path in mainToDoPaths:
        normalisedPath = utils.normalisePath(path)
        if normalisedPath in normalisedConflictToDoPaths:
            reconciledPaths.append(path)
        else:
            if normalisedPath not in normalisedDoneToDoPaths:
                reconciledPaths.append(path)

    for path in conflictToDoPaths:
        normalisedPath = utils.normalisePath(path)
        if normalisedPath not in normalisedMainToDoPaths:
            if normalisedPath not in normalisedDoneToDoPaths:
                reconciledPaths.append(path)

    return reconciledPaths


def deleteFile(conflictFilePath):
    if os.path.exists(conflictFilePath):
        os.remove(conflictFilePath)


def writeResolvedToDos(finalConstructedFile):
    mainToDoFile = getConfig()["mainToDoFile"]
    with open(mainToDoFile, "w") as unDoneFile:
        unDoneFile.write(finalConstructedFile)


def resolveSyncConflicts():
    isConflict, conflictFilePath = checkForConflicts()

    if not isConflict:
        return

    mainToDoText, doneToDoText, conflictToDoText = getAllToDos(conflictFilePath)

    mainToDoPathsUnDone, mainToDoPathsDone = toDo.getAllToDoPaths(mainToDoText)
    doneToDoPathsUnDone, doneToDoPathsDone = toDo.getAllToDoPaths(doneToDoText)
    conflictToDoPathsUnDone, conflictToDoPathsDone = toDo.getAllToDoPaths(
        conflictToDoText
    )
    mainToDoPaths = mainToDoPathsUnDone + mainToDoPathsDone
    doneToDoPaths = doneToDoPathsUnDone + doneToDoPathsDone
    conflictToDoPaths = conflictToDoPathsUnDone + conflictToDoPathsDone

    reconciledPaths = reconcilePaths(mainToDoPaths, conflictToDoPaths, doneToDoPaths)
    deleteFile(conflictFilePath)
    finalConstructedFile = toDo.constructFileFromPaths(reconciledPaths)
    writeResolvedToDos(finalConstructedFile)


if __name__ == "__main__":
    for i in range(5):
        resolveSyncConflicts()
        time.sleep(10)
