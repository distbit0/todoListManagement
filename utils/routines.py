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
    routines = open(routinesFile).read().split("\n")
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
    outputFile = ""
    routines = open(routinesFile).read().split("\n")
    for routine in routines:
        if not routine.strip():
            continue
        routine = routine.replace("[x]", "[ ]")
        outputFile += routine + "\n"
    with open(routinesFile, "w") as routinesF:
        routinesF.write(outputFile)
