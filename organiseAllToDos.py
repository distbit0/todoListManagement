import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from utils.utils import *
from utils.routines import *
from utils.toDo import *
from utils.dailyDone import *
from utils.prioritisedToDo import *


if __name__ == "__main__":
    routinesFile = getConfig()["routinesFile"]
    distractionsFile = getConfig()["distractionsFile"]

    dailyDonePaths = unDonePaths = donePaths = []
    mainToDoText, doneToDoText = getAllToDos()
    mainUnDonePaths, mainDonePaths = getAllToDoPaths(mainToDoText)
    doneUnDonePaths, doneDonePaths = getAllToDoPaths(doneToDoText)

    unDonePaths.extend(mainUnDonePaths)
    donePaths.extend(mainDonePaths)
    donePaths.extend(doneDonePaths)
    dailyDonePaths.extend(mainDonePaths)

    unDoneOutput = constructFileFromPaths(unDonePaths)
    doneOutput = constructFileFromPaths(donePaths)
    writeOutputToDos(doneOutput, unDoneOutput)
    addToDailyDoneFile(dailyDonePaths)
    addToReadableDailyDoneFile(dailyDonePaths)
    calcAndSavePrioritisedToDos(unDonePaths)
    print(unDoneOutput)
