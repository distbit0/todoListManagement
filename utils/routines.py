import utils.utils as utils


def sortRoutinesToTop(paths):
    outputPaths = []
    routines = []
    for path in paths:
        if "Routine" in path or "Distraction" in path:
            routines.append(path)
        else:
            outputPaths.append(path)
    routines.sort()
    routines.extend(outputPaths)
    return routines


def getDoneRoutines(routinesFile, routineType):
    doneRoutines = []
    routines = utils.readFromFile(routinesFile).split("\n")
    for routine in routines:
        if not routine.strip():
            continue
        routineName = routine.replace("- [x] ", "").replace("- [ ] ", "")
        if "[x]" in routine:
            doneRoutines.append(
                [routineType, "**" + routineType + ":** " + routineName]
            )
    return doneRoutines


def markRoutinesAsUnDone(routinesFile):
    outputText = ""
    routines = utils.readFromFile(routinesFile).split("\n")
    for routine in routines:
        if not routine.strip():
            continue
        routine = routine.replace("[x]", "[ ]")
        outputText += routine + "\n"
    utils.writeToFile(routinesFile, outputText)
