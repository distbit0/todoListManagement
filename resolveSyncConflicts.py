import sys
from os import path
import os
import time

sys.path.insert(0, path.dirname(__file__))

import utils.utils as utils
import utils.toDo as toDo

getConfig = utils.getConfig


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


def resolveSyncConflicts():
    toDoFiles, doneToDoText = utils.getAllToDosAndDoneText()

    for toDoId in toDoFiles:
        toDoFileContents = toDoFiles[toDoId]

        if "conflict" not in toDoFileContents or "master" not in toDoFileContents:
            continue
        masterToDoText = toDoFileContents["master"]["text"]
        masterFilePath = toDoFileContents["master"]["path"]
        conflictToDoText = toDoFileContents["conflict"]["text"]
        conflictFilePath = toDoFileContents["conflict"]["path"]

        subject = toDoFileContents["conflict"]["subject"]

        masterToDoPathsUnDone, masterToDoPathsDone = toDo.getAllToDoPaths(
            masterToDoText, prefix=subject
        )
        conflictToDoPathsUnDone, conflictToDoPathsDone = toDo.getAllToDoPaths(
            conflictToDoText, prefix=subject
        )
        doneToDoPathsUnDone, doneToDoPathsDone = toDo.getAllToDoPaths(doneToDoText)

        mainToDoPaths = masterToDoPathsUnDone + masterToDoPathsDone
        doneToDoPaths = doneToDoPathsUnDone + doneToDoPathsDone
        conflictToDoPaths = conflictToDoPathsUnDone + conflictToDoPathsDone

        reconciledPaths = reconcilePaths(
            mainToDoPaths, conflictToDoPaths, doneToDoPaths
        )
        deleteFile(conflictFilePath)
        reconciledPaths = utils.unPrefixAllPaths(reconciledPaths)
        finalConstructedFile = toDo.constructFileFromPaths(reconciledPaths)
        utils.writeToFile(masterFilePath, finalConstructedFile)


if __name__ == "__main__":
    for i in range(5):
        resolveSyncConflicts()
        time.sleep(10)
