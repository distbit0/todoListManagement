import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

import utils.utils as utils
from utils.toDo import *


def organiseAndReturnTodos(toDoFile):
    toDoFileText, toDoFilePath = (
        toDoFile["text"],
        toDoFile["path"],
    )
    fileUndonePaths = getAllToDoPaths(toDoFileText)
    unDoneOutput = constructFileFromPaths(fileUndonePaths)
    writeToFile(toDoFilePath, unDoneOutput)


if __name__ == "__main__":
    toDoFiles = utils.getAllToDos()

    for toDoId in toDoFiles:
        toDoFileContents = toDoFiles[toDoId]
        if "master" not in toDoFileContents:
            continue

        organiseAndReturnTodos(toDoFileContents["master"])
